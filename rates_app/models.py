from django.db import models
from django.db.models import Q
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)


class RateProvider(models.Model):
    """A financial institution or data provider."""
    name = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rate_providers'
        ordering = ['name']

    def __str__(self):
        return self.name


class RateType(models.Model):
    """Type of financial rate (mortgage_30yr, savings_apy, etc.)."""
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rate_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class Rate(models.Model):
    """A financial rate record."""
    provider = models.ForeignKey(RateProvider, on_delete=models.CASCADE, related_name='rates')
    rate_type = models.ForeignKey(RateType, on_delete=models.CASCADE, related_name='rates')
    rate_value = models.DecimalField(max_digits=10, decimal_places=4, db_index=True)
    effective_date = models.DateField(db_index=True)
    ingestion_timestamp = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rates'
        unique_together = ('provider', 'rate_type', 'effective_date')
        indexes = [
            models.Index(fields=['provider', 'rate_type', '-effective_date'], name='idx_provider_type_date'),
            models.Index(fields=['provider', 'rate_type', '-ingestion_timestamp'], name='idx_provider_type_ingestion'),
            models.Index(fields=['effective_date'], name='idx_effective_date'),
            models.Index(fields=['ingestion_timestamp'], name='idx_ingestion_timestamp'),
        ]
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.provider.name} - {self.rate_type.name}: {self.rate_value}% on {self.effective_date}"


class RawIngestionRecord(models.Model):
    """Store raw responses for replay and debugging."""
    source = models.CharField(max_length=255)
    raw_data = models.JSONField()
    parsed_successfully = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    related_rates = models.ManyToManyField(Rate, blank=True)
    ingestion_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'raw_ingestion_records'
        ordering = ['-ingestion_timestamp']
        indexes = [
            models.Index(fields=['source', '-ingestion_timestamp'], name='idx_source_ingestion'),
            models.Index(fields=['parsed_successfully', '-ingestion_timestamp'], name='idx_parse_success'),
        ]

    def __str__(self):
        status = "✓" if self.parsed_successfully else "✗"
        return f"{status} {self.source} - {self.ingestion_timestamp}"


class IngestionJob(models.Model):
    """Track batch ingestion job execution."""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    PARTIAL = 'partial'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (RUNNING, 'Running'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (PARTIAL, 'Partial'),
    ]
    
    job_id = models.CharField(max_length=255, unique=True, db_index=True)
    source = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    total_records = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ingestion_jobs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', '-started_at'], name='idx_job_status_date'),
        ]

    def __str__(self):
        return f"Job {self.job_id} - {self.status}"

    def mark_complete(self, status, error_msg=None):
        self.status = status
        self.completed_at = timezone.now()
        if error_msg:
            self.error_message = error_msg
        self.save()
