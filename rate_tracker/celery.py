import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rate_tracker.settings')

app = Celery('rate_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'ingest-rates-hourly': {
        'task': 'rates_app.tasks.ingest_rates',
        'schedule': crontab(minute=0),  # Every hour
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
