from django.apps import AppConfig


class RatesAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rates_app'

    def ready(self):
        import rates_app.signals
