"""Django management command to seed rates from parquet file."""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from rates_app.models import Rate, RateProvider, RateType, RawIngestionRecord, IngestionJob
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed rate data from parquet file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/rates_seed.parquet',
            help='Path to parquet file'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for bulk operations'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = Path(options['file'])
        batch_size = options['batch_size']

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Loading rates from {file_path}'))
        job = IngestionJob.objects.create(
            job_id=f'seed_{datetime.now().timestamp()}',
            source='seed_data_command',
            status=IngestionJob.RUNNING
        )

        try:
            logger.info(f"Starting data ingestion from {file_path}")

            # Read parquet file
            table = pq.read_table(file_path)
            df = table.to_pandas()

            logger.info(f"Read {len(df)} rows from parquet file")

            # Expected columns: provider, rate_type, rate_value, effective_date, ingestion_timestamp
            required_cols = {'provider', 'rate_type', 'rate_value', 'effective_date', 'ingestion_timestamp'}
            if not required_cols.issubset(set(df.columns)):
                raise ValueError(f'Missing required columns. Expected: {required_cols}, Got: {set(df.columns)}')

            total_records = len(df)
            successful = 0
            failed = 0
            skipped = 0

            # Convert timestamps
            df['effective_date'] = pd.to_datetime(df['effective_date']).dt.date
            df['ingestion_timestamp'] = pd.to_datetime(df['ingestion_timestamp'])

            # Process in batches
            for batch_start in range(0, len(df), batch_size):
                batch_end = min(batch_start + batch_size, len(df))
                batch = df.iloc[batch_start:batch_end]

                providers_data = {}
                types_data = {}
                rates_to_create = []

                for idx, row in batch.iterrows():
                    try:
                        provider_name = str(row['provider']).strip()
                        rate_type_name = str(row['rate_type']).strip()
                        rate_value = Decimal(str(row['rate_value']))
                        effective_date = row['effective_date']
                        ingestion_timestamp = row['ingestion_timestamp']

                        # Validate
                        if rate_value < 0 or rate_value > 100:
                            logger.warning(f"Invalid rate value {rate_value}, skipping")
                            skipped += 1
                            failed += 1
                            continue

                        # Get or create provider and type
                        if provider_name not in providers_data:
                            provider, _ = RateProvider.objects.get_or_create(name=provider_name)
                            providers_data[provider_name] = provider
                        else:
                            provider = providers_data[provider_name]

                        if rate_type_name not in types_data:
                            rate_type, _ = RateType.objects.get_or_create(name=rate_type_name)
                            types_data[rate_type_name] = rate_type
                        else:
                            rate_type = types_data[rate_type_name]

                        # Create or update rate
                        rate, created = Rate.objects.update_or_create(
                            provider=provider,
                            rate_type=rate_type,
                            effective_date=effective_date,
                            defaults={
                                'rate_value': rate_value,
                                'ingestion_timestamp': ingestion_timestamp,
                            }
                        )
                        successful += 1

                        # Store raw record
                        raw_record = RawIngestionRecord.objects.create(
                            source='seed_parquet',
                            raw_data={
                                'provider': provider_name,
                                'rate_type': rate_type_name,
                                'rate_value': str(rate_value),
                                'effective_date': str(effective_date),
                                'ingestion_timestamp': ingestion_timestamp.isoformat(),
                            },
                            parsed_successfully=True,
                        )
                        raw_record.related_rates.add(rate)

                    except IntegrityError as e:
                        logger.warning(f"Integrity error at row {idx}: {e}")
                        failed += 1
                    except Exception as e:
                        logger.error(f"Error processing row {idx}: {e}")
                        failed += 1

                self.stdout.write(f"Processed batch: {batch_start}-{batch_end} ({successful + failed}/{total_records})")

            job.total_records = total_records
            job.successful_records = successful
            job.failed_records = failed
            job.mark_complete(IngestionJob.SUCCESS if failed == 0 else IngestionJob.PARTIAL)

            self.stdout.write(self.style.SUCCESS(
                f'Successfully loaded {successful} rates from {file_path}'
            ))
            logger.info(f"Data ingestion completed: {successful} successful, {failed} failed, {skipped} skipped")

        except Exception as e:
            logger.exception(f"Error during data ingestion: {e}")
            job.mark_complete(IngestionJob.FAILED, str(e))
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
