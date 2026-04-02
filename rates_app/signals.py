# Signals for cache invalidation
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Rate

@receiver(post_save, sender=Rate)
def invalidate_rate_cache(sender, instance, created, **kwargs):
    """Invalidate cache when a rate is saved."""
    cache_keys = [
        'rates:latest_all',
        f'rates:latest_type:{instance.rate_type.name}',
    ]
    for key in cache_keys:
        cache.delete(key)
