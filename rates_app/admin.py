from django.contrib import admin
from .models import Rate, RateProvider, RateType, RawIngestionRecord, IngestionJob


@admin.register(RateProvider)
class RateProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(RateType)
class RateTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Rate)
class RateAdmin(admin.ModelAdmin):
    list_display = ['provider', 'rate_type', 'rate_value', 'effective_date', 'ingestion_timestamp']
    list_filter = ['provider', 'rate_type', 'effective_date']
    search_fields = ['provider__name', 'rate_type__name']
    ordering = ['-effective_date']


@admin.register(RawIngestionRecord)
class RawIngestionRecordAdmin(admin.ModelAdmin):
    list_display = ['source', 'parsed_successfully', 'ingestion_timestamp']
    list_filter = ['source', 'parsed_successfully', 'ingestion_timestamp']
    search_fields = ['source']
    readonly_fields = ['raw_data', 'ingestion_timestamp']


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'source', 'status', 'total_records', 'successful_records', 'started_at']
    list_filter = ['status', 'source', 'started_at']
    search_fields = ['job_id', 'source']
    readonly_fields = ['started_at', 'completed_at']
