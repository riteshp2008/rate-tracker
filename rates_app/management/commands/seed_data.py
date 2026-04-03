"""Django management command to seed rates from parquet file."""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from rates_app.models import Rate, RateProvider, RateType, IngestionJob
from django.utils import timezone


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

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        batch_size = options['batch_size']

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f'Loading rates from {file_path}')
        
        # Create job record
        job = IngestionJob.objects.create(
            job_id=f'seed_{datetime.now().timestamp()}',
            source='seed_data_command',
            status=IngestionJob.RUNNING
        )
        self.stdout.write(f'Created job {job.id}')

        try:
            # Read parquet
            self.stdout.write('Reading parquet file...')
            df = pd.read_parquet(file_path)
            self.stdout.write(f'Read {len(df)} rows')

            # Prepare timestamp
            if 'ingestion_ts' in df.columns:
                df['ingestion_timestamp'] = pd.to_datetime(df['ingestion_ts'])
            else:
                df['ingestion_timestamp'] = timezone.now()

            if df['ingestion_timestamp'].dt.tz is None:
                df['ingestion_timestamp'] = df['ingestion_timestamp'].dt.tz_localize('UTC')

            df['effective_date'] = pd.to_datetime(df['effective_date']).dt.date
            
            # Handle NaN values in rate_value - skip rows with NaN
            initial_len = len(df)
            df = df.dropna(subset=['rate_value'])
            skipped = initial_len - len(df)
            if skipped > 0:
                self.stdout.write(f'Skipped {skipped} rows with NaN rate values')
            
            df['rate_value'] = df['rate_value'].apply(lambda x: Decimal(str(x)))

            # Pre-create providers and types
            self.stdout.write('Creating providers and types...')
            providers_map = {}
            for name in df['provider'].unique():
                p, _ = RateProvider.objects.get_or_create(name=str(name))
                providers_map[name] = p

            types_map = {}
            for name in df['rate_type'].unique():
                t, _ = RateType.objects.get_or_create(name=str(name))
                types_map[name] = t

            self.stdout.write(f'Created {len(providers_map)} providers, {len(types_map)} types')

            # Process batches
            total = len(df)
            successful = 0
            failed = 0

            self.stdout.write('Processing batches...')
            for batch_start in range(0, len(df), batch_size):
                batch_end = min(batch_start + batch_size, len(df))
                batch = df.iloc[batch_start:batch_end]

                rates_list = []
                for _, row in batch.iterrows():
                    try:
                        rate = Rate(
                            provider=providers_map[row['provider']],
                            rate_type=types_map[row['rate_type']],
                            rate_value=row['rate_value'],
                            effective_date=row['effective_date'],
                            ingestion_timestamp=row['ingestion_timestamp'],
                        )
                        rates_list.append(rate)
                        successful += 1
                    except Exception as e:
                        self.stdout.write(f'Row error: {e}')
                        failed += 1

                # Bulk insert
                if rates_list:
                    with transaction.atomic():
                        Rate.objects.bulk_create(rates_list, batch_size=1000, ignore_conflicts=True)
                        self.stdout.write(f'Batch {batch_start//batch_size + 1}: {len(rates_list)} rates ({successful+failed}/{total})')

            # Update job
            job.total_records = total
            job.successful_records = successful
            job.failed_records = failed
            job.mark_complete(IngestionJob.SUCCESS if failed == 0 else IngestionJob.PARTIAL)

            self.stdout.write(self.style.SUCCESS(f'Loaded {successful} rates'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            job.mark_complete(IngestionJob.FAILED, str(e))
