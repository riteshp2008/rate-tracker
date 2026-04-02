import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from decimal import Decimal
from datetime import date
from django.utils import timezone
import json

from rates_app.models import Rate, RateProvider, RateType
from rates_app.serializers import RateSerializer, RateIngestSerializer


@pytest.mark.django_db
class TestRateAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.token = Token.objects.create(user=self.user)

        # Create test data
        self.provider_a = RateProvider.objects.create(name='Bank A')
        self.provider_b = RateProvider.objects.create(name='Bank B')
        self.mortgage_type = RateType.objects.create(name='Mortgage 30Y')
        self.savings_type = RateType.objects.create(name='Savings APY')

        # Create test rates
        Rate.objects.create(
            provider=self.provider_a,
            rate_type=self.mortgage_type,
            rate_value=Decimal('3.50'),
            effective_date=date(2024, 1, 15),
            ingestion_timestamp=timezone.now()
        )
        Rate.objects.create(
            provider=self.provider_b,
            rate_type=self.mortgage_type,
            rate_value=Decimal('3.75'),
            effective_date=date(2024, 1, 15),
            ingestion_timestamp=timezone.now()
        )
        Rate.objects.create(
            provider=self.provider_a,
            rate_type=self.savings_type,
            rate_value=Decimal('0.45'),
            effective_date=date(2024, 1, 15),
            ingestion_timestamp=timezone.now()
        )

    def test_get_latest_rates(self):
        """GET /rates/latest should return most recent rate per provider."""
        response = self.client.get('/api/rates/latest/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_latest_rates_filtered_by_type(self):
        """GET /rates/latest?type=Mortgage%2030Y should filter by type."""
        response = self.client.get('/api/rates/latest/', {'type': 'Mortgage 30Y'})
        assert response.status_code == 200
        data = response.json()
        for rate in data:
            assert rate['rate_type']['name'] == 'Mortgage 30Y'

    def test_get_rate_history(self):
        """GET /rates/history should return paginated time-series."""
        response = self.client.get('/api/rates/history/', {
            'provider': 'Bank A',
            'type': 'Mortgage 30Y'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'results' in data
        assert len(data['results']) > 0

    def test_get_rate_history_with_date_filter(self):
        """GET /rates/history with date filters."""
        response = self.client.get('/api/rates/history/', {
            'provider': 'Bank A',
            'type': 'Mortgage 30Y',
            'from': '2024-01-01',
            'to': '2024-01-31'
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) > 0

    def test_get_rate_history_missing_params(self):
        """GET /rates/history without required params should fail."""
        response = self.client.get('/api/rates/history/')
        assert response.status_code == 400

    def test_ingest_rate_unauthenticated(self):
        """POST /rates/ingest without auth should fail."""
        response = self.client.post('/api/rates/ingest/', {
            'provider_name': 'Bank C',
            'rate_type_name': 'Mortgage 30Y',
            'rate_value': 3.55,
            'effective_date': '2024-01-16'
        }, format='json')
        assert response.status_code == 401

    def test_ingest_rate_authenticated(self):
        """POST /rates/ingest with valid auth should create rate."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.post('/api/rates/ingest/', {
            'provider_name': 'Bank C',
            'rate_type_name': 'Mortgage 30Y',
            'rate_value': Decimal('3.55'),
            'effective_date': '2024-01-16'
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert 'id' in data
        assert RateProvider.objects.filter(name='Bank C').exists()

    def test_ingest_rate_invalid_data(self):
        """POST /rates/ingest with invalid data should return 400."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.post('/api/rates/ingest/', {
            'provider_name': 'Bank C',
            'rate_type_name': 'Mortgage 30Y',
            'rate_value': -1.50,  # Invalid: negative
            'effective_date': '2024-01-16'
        }, format='json')
        assert response.status_code == 400

    def test_get_providers_list(self):
        """GET /rates/providers should list all providers."""
        response = self.client.get('/api/rates/providers/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(p['name'] == 'Bank A' for p in data)

    def test_get_rate_types_list(self):
        """GET /rates/types should list all rate types."""
        response = self.client.get('/api/rates/types/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(r['name'] == 'Mortgage 30Y' for r in data)
