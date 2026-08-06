"""URL routing for the platform API."""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import health_view, metrics_view, profile_view, readiness_view

urlpatterns = [
    path('health/', health_view, name='health'),
    path('readiness/', readiness_view, name='readiness'),
    # metrics is a plain Django view returning text/plain; CSRF exempt since it
    # is GET-only and unauthenticated (scraped by Prometheus).
    path('metrics/', csrf_exempt(metrics_view), name='metrics'),
    path('profile/', profile_view, name='profile'),
]
