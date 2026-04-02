import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rate_tracker.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    execute_from_command_line(sys.argv)
