from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import json

from .models import Rate, RateProvider, RateType, RawIngestionRecord
from .serializers import (
    RateSerializer, RateIngestSerializer, RateHistorySerializer,
    RateProviderSerializer, RateTypeSerializer
)

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 300  # 5 minutes
CACHE_KEY_LATEST = 'rates:latest:{provider}:{rate_type}'
CACHE_KEY_HISTORY = 'rates:history:{provider}:{rate_type}:{from}:{to}'


class LatestRatesView(APIView):
    """GET /rates/latest - Return most recent rate per provider."""
    permission_classes = [AllowAny]

    def get(self, request):
        rate_type = request.query_params.get('type')

        # Try cache first
        cache_key = f'rates:latest_all' if not rate_type else f'rates:latest_type:{rate_type}'
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for {cache_key}")
            return Response(cached)

        query = Rate.objects.select_related('provider', 'rate_type')

        if rate_type:
            query = query.filter(rate_type__name=rate_type)

        # Get latest per provider-type combination
        rates_dict = {}
        for rate in query.order_by('-effective_date'):
            key = (rate.provider_id, rate.rate_type_id)
            if key not in rates_dict:
                rates_dict[key] = rate

        rates = list(rates_dict.values())
        serializer = RateSerializer(rates, many=True)

        # Cache the result
        cache.set(cache_key, serializer.data, CACHE_TIMEOUT)
        logger.info(f"Cached {len(serializer.data)} latest rates")

        return Response(serializer.data)


class RateHistoryView(APIView):
    """GET /rates/history - Paginated time-series for provider+type."""
    permission_classes = [AllowAny]

    def get(self, request):
        provider_name = request.query_params.get('provider')
        rate_type_name = request.query_params.get('type')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        page = request.query_params.get('page', 1)

        if not provider_name or not rate_type_name:
            return Response(
                {'error': 'provider and type query parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cache key
        cache_key = f'rates:history:{provider_name}:{rate_type_name}:{from_date}:{to_date}:{page}'
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for history: {provider_name}/{rate_type_name}")
            return Response(cached)

        try:
            query = Rate.objects.filter(
                provider__name=provider_name,
                rate_type__name=rate_type_name
            ).select_related('provider', 'rate_type').order_by('-effective_date')

            if from_date:
                from_dt = datetime.fromisoformat(from_date).date()
                query = query.filter(effective_date__gte=from_dt)

            if to_date:
                to_dt = datetime.fromisoformat(to_date).date()
                query = query.filter(effective_date__lte=to_dt)

            # Pagination
            page_size = 100
            offset = (int(page) - 1) * page_size
            total = query.count()
            rates = query[offset:offset + page_size]

            serializer = RateHistorySerializer(rates, many=True)
            response_data = {
                'count': total,
                'page': page,
                'page_size': page_size,
                'results': serializer.data
            }

            cache.set(cache_key, response_data, CACHE_TIMEOUT)
            return Response(response_data)

        except Exception as e:
            logger.exception(f"Error fetching rate history: {e}")
            return Response(
                {'error': 'Failed to fetch rate history'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IngestRatesView(APIView):
    """POST /rates/ingest - Authenticated webhook for ingesting rates."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RateIngestSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(f"Invalid ingest data: {serializer.errors}")
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = serializer.validated_data
            provider_name = data['provider_name']
            rate_type_name = data['rate_type_name']
            rate_value = data['rate_value']
            effective_date = data['effective_date']
            ingestion_timestamp = data.get('ingestion_timestamp', timezone.now())

            # Get or create provider and rate_type
            provider, _ = RateProvider.objects.get_or_create(name=provider_name)
            rate_type, _ = RateType.objects.get_or_create(name=rate_type_name)

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

            # Store raw record
            RawIngestionRecord.objects.create(
                source='webhook',
                raw_data=request.data,
                parsed_successfully=True,
            ).related_rates.add(rate)

            # Invalidate cache
            self._invalidate_caches(provider_name, rate_type_name)

            logger.info(f"Rate ingested: {provider_name}/{rate_type_name} = {rate_value}%")

            return Response(
                {
                    'id': rate.id,
                    'message': f"Rate {'created' if created else 'updated'} successfully"
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f"Error ingesting rate: {e}")
            return Response(
                {'error': 'Failed to ingest rate'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _invalidate_caches(self, provider_name, rate_type_name):
        """Invalidate relevant cache keys when rates are updated."""
        patterns = [
            f'rates:latest_all',
            f'rates:latest_type:{rate_type_name}',
            f'rates:history:{provider_name}:{rate_type_name}:*',
        ]
        for pattern in patterns:
            if '*' in pattern:
                # Need to invalidate all matching keys
                for key in cache._cache.keys(pattern):
                    cache.delete(key)
            else:
                cache.delete(pattern)
        logger.debug(f"Cache invalidated for {provider_name}/{rate_type_name}")


class ProvidersListView(APIView):
    """GET /rates/providers - List all providers."""
    permission_classes = [AllowAny]

    def get(self, request):
        providers = RateProvider.objects.all()
        serializer = RateProviderSerializer(providers, many=True)
        return Response(serializer.data)


class RateTypesListView(APIView):
    """GET /rates/types - List all rate types."""
    permission_classes = [AllowAny]

    def get(self, request):
        types = RateType.objects.all()
        serializer = RateTypeSerializer(types, many=True)
        return Response(serializer.data)
