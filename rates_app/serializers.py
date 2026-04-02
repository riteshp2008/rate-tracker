from rest_framework import serializers
from .models import Rate, RateProvider, RateType, RawIngestionRecord
from django.utils import timezone


class RateProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateProvider
        fields = ['id', 'name']


class RateTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateType
        fields = ['id', 'name', 'description']


class RateSerializer(serializers.ModelSerializer):
    provider = RateProviderSerializer(read_only=True)
    provider_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=RateProvider.objects.all(),
        source='provider'
    )
    rate_type = RateTypeSerializer(read_only=True)
    rate_type_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=RateType.objects.all(),
        source='rate_type'
    )

    class Meta:
        model = Rate
        fields = [
            'id', 'provider', 'provider_id', 'rate_type', 'rate_type_id',
            'rate_value', 'effective_date', 'ingestion_timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_rate_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Rate value cannot be negative")
        if value > 100:
            raise serializers.ValidationError("Rate value seems unreasonably high (>100%)")
        return value

    def validate_effective_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Effective date cannot be in the future")
        return value


class RateIngestSerializer(serializers.Serializer):
    """Serializer for the POST /rates/ingest webhook endpoint."""
    provider_name = serializers.CharField(max_length=255)
    rate_type_name = serializers.CharField(max_length=255)
    rate_value = serializers.DecimalField(max_digits=10, decimal_places=4)
    effective_date = serializers.DateField()
    ingestion_timestamp = serializers.DateTimeField(required=False)

    def validate_rate_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Rate value cannot be negative")
        if value > 100:
            raise serializers.ValidationError("Rate value seems unreasonably high (>100%)")
        return value

    def validate_effective_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Effective date cannot be in the future")
        return value


class RateHistorySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    rate_type_name = serializers.CharField(source='rate_type.name', read_only=True)

    class Meta:
        model = Rate
        fields = ['id', 'provider_name', 'rate_type_name', 'rate_value', 'effective_date', 'ingestion_timestamp']
        ordering = ['-effective_date']
