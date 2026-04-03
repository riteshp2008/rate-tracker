import logging
from celery import shared_task
from django.utils import timezone
from .models import Rate, IngestionJob, RateProvider, RateType, RawIngestionRecord
from django.db import transaction
import json

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def ingest_rates(self):
    """Celery task for hourly rate ingestion."""
    job_id = self.request.id
    job = IngestionJob.objects.create(
        job_id=job_id,
        source='scheduler',
        status=IngestionJob.RUNNING
    )

    try:
        logger.info(f"Starting rate ingestion job {job_id}")
        
        from datetime import date
        current_date = date.today()
        ingestion_time = timezone.now()

        # Ensure providers exist
        bank_of_america, _ = RateProvider.objects.get_or_create(name='Bank of America')
        chase, _ = RateProvider.objects.get_or_create(name='Chase')
        wells_fargo, _ = RateProvider.objects.get_or_create(name='Wells Fargo')
        
        # Ensure rate types exist
        mortgage_30, _ = RateType.objects.get_or_create(
            name='Mortgage 30-Year',
            defaults={'description': '30-year fixed rate mortgage'}
        )
        savings_apy, _ = RateType.objects.get_or_create(
            name='Savings APY',
            defaults={'description': 'High-yield savings account APY'}
        )
        cd_6month, _ = RateType.objects.get_or_create(
            name='CD 6-Month',
            defaults={'description': '6-month certificate of deposit'}
        )
        
        # Create dummy rates
        rates_to_create = [
            Rate(provider=bank_of_america, rate_type=mortgage_30, rate_value=6.85, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=bank_of_america, rate_type=savings_apy, rate_value=4.25, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=bank_of_america, rate_type=cd_6month, rate_value=4.30, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=chase, rate_type=mortgage_30, rate_value=6.75, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=chase, rate_type=savings_apy, rate_value=4.35, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=chase, rate_type=cd_6month, rate_value=4.40, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=wells_fargo, rate_type=mortgage_30, rate_value=6.90, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=wells_fargo, rate_type=savings_apy, rate_value=4.15, effective_date=current_date, ingestion_timestamp=ingestion_time),
            Rate(provider=wells_fargo, rate_type=cd_6month, rate_value=4.20, effective_date=current_date, ingestion_timestamp=ingestion_time),
        ]
        
        # Bulk create with ignore conflicts
        created_rates = Rate.objects.bulk_create(rates_to_create, ignore_conflicts=True)
        
        # Update job with results
        job.total_records = len(rates_to_create)
        job.successful_records = len(created_rates)
        job.failed_records = len(rates_to_create) - len(created_rates)
        
        logger.info(f"Completed rate ingestion job {job_id}")

        job.mark_complete(IngestionJob.SUCCESS)
        return {'status': 'success', 'job_id': job_id}

    except Exception as e:
        logger.exception(f"Error in rate ingestion job {job_id}: {e}")
        job.mark_complete(IngestionJob.FAILED, str(e))
        raise
