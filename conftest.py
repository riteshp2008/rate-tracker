"""
Pytest configuration and fixtures.
"""
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rate_tracker.settings')
django.setup()

import pytest
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """API client with authentication token."""
    client = APIClient()
    user = User.objects.create_user(username='testuser', password='testpass')
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def django_client():
    """Django test client."""
    return Client()
