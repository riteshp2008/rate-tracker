from django.urls import path
from . import views

app_name = 'rates'

urlpatterns = [
    path('latest/', views.LatestRatesView.as_view(), name='latest_rates'),
    path('history/', views.RateHistoryView.as_view(), name='rate_history'),
    path('ingest/', views.IngestRatesView.as_view(), name='ingest_rates'),
    path('providers/', views.ProvidersListView.as_view(), name='providers_list'),
    path('types/', views.RateTypesListView.as_view(), name='rate_types_list'),
]
