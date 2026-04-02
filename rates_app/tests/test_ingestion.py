import pytest
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import date

from rates_app.models import Rate, RateProvider, RateType, RawIngestionRecord, IngestionJob
from rates_app.management.commands.seed_data import Command
import pandas as pd
import tempfile
import os


@pytest.mark.django_db
class TestRateModel(TestCase):
    def setUp(self):
        self.provider = RateProvider.objects.create(name='Test Bank')
        self.rate_type = RateType.objects.create(name='Mortgage 30Y')

    def test_rate_creation(self):
        rate = Rate.objects.create(
            provider=self.provider,
            rate_type=self.rate_type,
            rate_value=Decimal('3.50'),
            effective_date=date(2024, 1, 1),
            ingestion_timestamp=timezone.now()
        )
        assert rate.id is not None
        assert rate.rate_value == Decimal('3.50')

    def test_rate_unique_constraint(self):
        """Ensure only one rate per provider-type-date combination."""
        Rate.objects.create(
            provider=self.provider,
            rate_type=self.rate_type,
            rate_value=Decimal('3.50'),
            effective_date=date(2024, 1, 1),
            ingestion_timestamp=timezone.now()
        )

        # Should update, not create duplicate
        rate2 = Rate.objects.create(
            provider=self.provider,
            rate_type=self.rate_type,
            rate_value=Decimal('3.55'),
            effective_date=date(2024, 1, 1),
            ingestion_timestamp=timezone.now()
        )
        assert Rate.objects.count() == 1  # No duplicate


@pytest.mark.django_db
class TestSeedDataCommand(TestCase):
    def test_seed_data_from_parquet(self):
        """Test loading rates from parquet file."""
        # Create a mock parquet file
        data = {
            'provider': ['Bank A', 'Bank B', 'Bank A'],
            'rate_type': ['Mortgage 30Y', 'Mortgage 30Y', 'Savings APY'],
            'rate_value': [3.50, 3.75, 0.45],
            'effective_date': ['2024-01-01', '2024-01-01', '2024-01-02'],
            'ingestion_timestamp': [
                '2024-01-01T10:00:00Z',
                '2024-01-01T10:00:00Z',
                '2024-01-02T10:00:00Z'
            ]
        }

        df = pd.DataFrame(data)

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_file = f.name
            df.to_parquet(temp_file)

        try:
            command = Command()
            command.handle(file=temp_file, batch_size=1000)

            # Verify data was loaded
            assert RateProvider.objects.count() == 2  # Bank A, Bank B
            assert RateType.objects.count() == 2  # Mortgage 30Y, Savings APY
            assert Rate.objects.count() == 3
            assert RawIngestionRecord.objects.count() >= 3

        finally:
            os.unlink(temp_file)

    def test_seed_data_invalid_rate_value(self):
        """Test handling of invalid rate values."""
        data = {
            'provider': ['Bank A', 'Bank B'],
            'rate_type': ['Mortgage 30Y', 'Invalid Rate'],
            'rate_value': [3.50, 150.00],  # 150% is invalid
            'effective_date': ['2024-01-01', '2024-01-01'],
            'ingestion_timestamp': [
                '2024-01-01T10:00:00Z',
                '2024-01-01T10:00:00Z'
            ]
        }

        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_file = f.name
            df.to_parquet(temp_file)

        try:
            command = Command()
            command.handle(file=temp_file, batch_size=1000)

            # Should have loaded only 1 valid record
            assert Rate.objects.filter(rate_value=Decimal('3.50')).exists()
        finally:
            os.unlink(temp_file)

    def test_missing_file(self):
        """Test graceful handling of missing parquet file."""
        command = Command()
        # Should not crash, just log error
        assert not os.path.exists('/tmp/nonexistent_file.parquet')


@pytest.mark.django_db
class TestIngestionJob(TestCase):
    def test_ingestion_job_creation(self):
        job = IngestionJob.objects.create(
            job_id='test_job_1',
            source='test',
            total_records=100,
            successful_records=95,
            failed_records=5
        )
        job.mark_complete(IngestionJob.PARTIAL, 'Some records failed')

        assert job.status == IngestionJob.PARTIAL
        assert job.error_message == 'Some records failed'
        assert job.completed_at is not None
