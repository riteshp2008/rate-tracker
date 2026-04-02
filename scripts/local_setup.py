#!/usr/bin/env python
"""
Django setup script for local development without Docker.
Run after: virtual environment is active
"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rate_tracker.settings')
django.setup()

if __name__ == '__main__':
    from django.core.management import call_command
    
    print("Rate-Tracker Local Setup")
    print("========================\n")
    
    # Run migrations
    print("1. Running migrations...")
    call_command('migrate', verbosity=1)
    
    # Create superuser
    print("\n2. Creating superuser...")
    call_command('createsuperuser', interactive=True)
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("  python manage.py runserver")
    print("  celery -A rate_tracker worker")
    print("  celery -A rate_tracker beat")
    print("\nThen visit: http://localhost:8000/admin/")
