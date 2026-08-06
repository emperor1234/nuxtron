"""Root URL configuration for the Nuxtron Django backend."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
    TokenVerifyView,
)

from platform_api.views import ThrottledTokenObtainPairView

urlpatterns = [
    path('', RedirectView.as_view(url='/api/health/', permanent=False)),
    path('admin/', admin.site.urls),

    # API surface.
    path('api/', include('platform_api.urls')),
    path('api/intelligence/', include('apps.intelligence.urls')),

    # Token auth endpoints (explicit views; simplejwt 5.x ships no urls.py):
    #   POST /api/auth/token/         -> obtain access+refresh pair
    #   POST /api/auth/token/refresh/ -> rotate refresh, blacklist old
    #   POST /api/auth/token/verify/  -> verify a token is still valid
    #   POST /api/auth/token/blacklist/ -> revoke a refresh token (logout)
    path('api/auth/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # OpenAPI schema + interactive docs.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]
