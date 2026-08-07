"""
Enterprise production settings for the Nuxtron Django backend.

Design goals
------------
* Fail loud in production: never start with an unset secret, wildcard hosts,
  or an open CORS policy.
* Layered infrastructure: PostgreSQL (psycopg3 + pool) + Redis (cache, rate
  limit, sessions) + HashiCorp Vault (pepper / app encryption keys).
* Defense in depth: TLS-only cookies, HSTS, CSP, security headers, request
  throttling, no Basic auth, JWT for token auth, structured logging.
* 12-factor: every environment-specific knob is read from the environment with
  a safe *non-secret* default only for local development.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Tiny timedelta helpers (kept here so JWT settings below stay readable).
# --------------------------------------------------------------------------- #
def _td_minutes(n: int) -> timedelta:
    return timedelta(minutes=n)


def _td_days(n: int) -> timedelta:
    return timedelta(days=n)

# --------------------------------------------------------------------------- #
# Environment / deployment metadata
# --------------------------------------------------------------------------- #
DEBUG: bool = os.getenv('DJANGO_DEBUG', '0') == '1'
# Explicit production flag (separate from DEBUG so staging can be non-debug
# but still identifiable). Default to "production" posture when unset.
IS_PRODUCTION: bool = os.getenv('DJANGO_ENV', 'production').lower() == 'production'

# --------------------------------------------------------------------------- #
# Secret key — mandatory, never defaulted. Generated once per environment.
# --------------------------------------------------------------------------- #
SECRET_KEY: str = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG and not IS_PRODUCTION:
        # Dev-only fallback so a fresh checkout boots without setup. This key
        # MUST be replaced before any non-local deployment.
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY environment variable is not set. '
            'Generate one (e.g. `python -c "import secrets;print(secrets.token_urlsafe(64))"`) '
            'and inject it via your secret manager (Vault / k8s secret / env).'
        )

# --------------------------------------------------------------------------- #
# Hosts / CORS
# --------------------------------------------------------------------------- #
_ALLOWED_HOSTS_RAW = os.getenv('DJANGO_ALLOWED_HOSTS', '').strip()
if _ALLOWED_HOSTS_RAW:
    ALLOWED_HOSTS: list[str] = [h.strip() for h in _ALLOWED_HOSTS_RAW.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']
else:
    # Fail closed: wildcard hosts in production is a classic host-header injection
    # vector. Operators must declare the exact hostnames they serve.
    raise RuntimeError(
        'DJANGO_ALLOWED_HOSTS is required in production. '
        'Comma-separated list of hostnames, e.g. "api.nuxtron.com,nuxtron.com".'
    )

CORS_ALLOW_ALL_ORIGINS = False  # Hard-off; explicit allow-list only.
CORS_ALLOW_CREDENTIALS = True

_cors_origins_raw = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS', '').strip()
if _cors_origins_raw:
    CORS_ALLOWED_ORIGINS: list[str] = [o.strip() for o in _cors_origins_raw.split(',') if o.strip()]
elif DEBUG:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:4173',
        'http://127.0.0.1:4173',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]
else:
    CORS_ALLOWED_ORIGINS = []  # Must be populated in production via env.

CORS_EXPOSE_HEADERS = ['Content-Length', 'X-Request-ID']
CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'user-agent',
    'x-csrftoken',
    'x-request-id',
]

# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_ratelimit',
    'platform_api',
    'apps.intelligence',
    'apps.accounts',
]

MIDDLEWARE = [
    # CORS first so preflight responses are unencumbered.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # CSP must run early so the header is always emitted on every response.
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Restrict /admin/ to ADMIN_IP_ALLOWLIST networks when configured (WO-10).
    'config.middleware.admin_allowlist.AdminIPAllowlistMiddleware',
    # Request ID propagation + structured logging context.
    'platform_api.middleware.RequestIDMiddleware',
    # Last-resort 500 handler; never leaks a traceback to the client (WO-9).
    'platform_api.exception_middleware.UncaughtExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES: list[dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# --------------------------------------------------------------------------- #
# Database — PostgreSQL via psycopg3 with optional connection pooling.
# Falls back to SQLite only when explicitly requested for local dev/tests.
# --------------------------------------------------------------------------- #
def _parse_database_url(url: str) -> dict[str, Any]:
    """Parse a postgres://user:pass@host:port/dbname?sslmode=... URL.

    Mirrors what app.database._get_database_url does on the FastAPI side —
    DATABASE_URL takes priority over discrete POSTGRES_* vars there too, so
    a single Coolify-provided connection string works the same way for both
    services instead of needing to be split into parts for one of them.
    """
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query))
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/') or 'nuxtron',
        'USER': unquote(parsed.username) if parsed.username else '',
        'PASSWORD': unquote(parsed.password) if parsed.password else '',
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or 5432),
        'sslmode': query.get('sslmode'),
    }


def _build_databases() -> dict[str, dict[str, Any]]:
    database_url = os.getenv('DATABASE_URL', '').strip()
    pg_host = os.getenv('POSTGRES_HOST', '').strip()
    if database_url or pg_host:
        if database_url:
            parsed_url = _parse_database_url(database_url)
            db_name = parsed_url['NAME']
            db_user = parsed_url['USER']
            db_password = parsed_url['PASSWORD']
            db_host = parsed_url['HOST']
            db_port = parsed_url['PORT']
            url_sslmode = parsed_url['sslmode']
        else:
            db_name = os.getenv('POSTGRES_DB', 'nuxtron')
            db_user = os.getenv('POSTGRES_USER', 'nuxtron')
            db_password = os.getenv('POSTGRES_PASSWORD', '')
            db_host = pg_host
            db_port = os.getenv('POSTGRES_PORT', '5432')
            url_sslmode = None

        default: dict[str, Any] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                # Application_name makes DB-side debugging tractable in ops.
                'application_name': os.getenv('POSTGRES_APPLICATION_NAME', 'nuxtron-django'),
                # Default to encrypted Postgres connections in production so a
                # misconfigured network path can't silently fall back to
                # plaintext. Local/dev can relax this via POSTGRES_SSLMODE, or
                # a ?sslmode=... query param on DATABASE_URL (takes priority).
                'sslmode': url_sslmode or os.getenv('POSTGRES_SSLMODE', 'require' if IS_PRODUCTION else 'prefer'),
            },
        }
        # Use server-side pooling when psycopg-pool is available.
        if os.getenv('POSTGRES_USE_POOL', '1') == '1':
            try:
                import psycopg_pool  # noqa: F401
                default['OPTIONS']['pool'] = {
                    'min_size': int(os.getenv('POSTGRES_POOL_MIN', '2')),
                    'max_size': int(os.getenv('POSTGRES_POOL_MAX', '10')),
                    'timeout': float(os.getenv('POSTGRES_POOL_TIMEOUT', '30')),
                }
            except ImportError:
                pass
        return {'default': default}

    # Local dev fallback (opt-in via DJANGO_USE_SQLITE=1 or no PG host).
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'ATOMIC_REQUESTS': True,
        }
    }


DATABASES = _build_databases()

# --------------------------------------------------------------------------- #
# Redis — cache, rate-limit backing store, and optional session backend.
# --------------------------------------------------------------------------- #
_REDIS_URL = os.getenv('REDIS_URL', '').strip()
if not _REDIS_URL:
    _redis_host = os.getenv('REDIS_HOST', '').strip()
    if _redis_host:
        _REDIS_URL = (
            f"redis://:{os.getenv('REDIS_PASSWORD', '')}"
            f"@{_redis_host}:{os.getenv('REDIS_PORT', '6379')}"
            f"/{os.getenv('REDIS_DB', '0')}"
        )
    elif DEBUG:
        _REDIS_URL = 'redis://127.0.0.1:6379/1'

REDIS_URL = _REDIS_URL

if REDIS_URL:
    CACHES: dict[str, dict[str, Any]] = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300')),
            'OPTIONS': {
                # Health-check the connection before use; avoid cryptic timeouts.
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'CONNECTION_POOL_KWARGS': {'max_connections': 50},
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': os.getenv('CACHE_KEY_PREFIX', 'nuxtron'),
        }
    }
    # Store sessions in Redis for horizontal scaling + automatic expiry.
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
else:
    CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'nuxtron'}
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default' if REDIS_URL else 'default'

# --------------------------------------------------------------------------- #
# HashiCorp Vault — secret resolution (password pepper, app encryption key).
# --------------------------------------------------------------------------- #
VAULT_ADDR = os.getenv('VAULT_ADDR', '').strip()
VAULT_TOKEN = os.getenv('VAULT_TOKEN', '').strip()
VAULT_NAMESPACE = os.getenv('VAULT_NAMESPACE', '').strip()
VAULT_PASSWORD_PEPPER_PATH = os.getenv('VAULT_PASSWORD_PEPPER_PATH', 'nuxtron/security')
VAULT_PASSWORD_PEPPER_FIELD = os.getenv('VAULT_PASSWORD_PEPPER_FIELD', 'password_pepper')
VAULT_APP_ENC_KEY_PATH = os.getenv('VAULT_APP_ENC_KEY_PATH', 'nuxtron/security')
VAULT_APP_ENC_KEY_FIELD = os.getenv('VAULT_APP_ENC_KEY_FIELD', 'app_enc_key')

# In-process caches for Vault-resolved secrets; rotated via SIGHUP / redeploy.
PASSWORD_PEPPER = os.getenv('PASSWORD_PEPPER', '').strip()
APP_ENC_KEY = os.getenv('APP_ENC_KEY', '').strip()

# --------------------------------------------------------------------------- #
# Authentication & password security
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': int(os.getenv('AUTH_PASSWORD_MIN_LENGTH', '12'))},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Strong hashers first. The Django PBKDF2 fallback stays for backwards compat.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_USER_MODEL = 'accounts.User'

# --------------------------------------------------------------------------- #
# DRF + SimpleJWT
# --------------------------------------------------------------------------- #
REST_FRAMEWORK: dict[str, Any] = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Accepts bearer JWTs issued by the FastAPI service (shared
        # JWT_SIGNING_KEY secret) so a token minted by FastAPI's /auth/login
        # also authenticates against Django endpoints — see
        # platform_api/authentication.py for the full rationale. Tried after
        # simplejwt so Django-native tokens are unaffected; it only claims a
        # token if it carries FastAPI's iss=='nuxtron-fastapi' marker.
        'platform_api.authentication.FastAPIJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    # BasicAuthentication deliberately removed: sends credentials on every
    # request and is trivially cacheable by proxies / browser history.
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '30/minute'),
        'user': os.getenv('THROTTLE_USER', '300/minute'),
        'login': os.getenv('THROTTLE_LOGIN', '10/minute'),
    },
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.getenv('API_PAGE_SIZE', '50')),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
}

SIMPLE_JWT: dict[str, Any] = {
    'ACCESS_TOKEN_LIFETIME': _td_minutes(15),
    'REFRESH_TOKEN_LIFETIME': _td_days(7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

SPECTACULAR_SETTINGS: dict[str, Any] = {
    'TITLE': 'Nuxtron Platform API',
    'DESCRIPTION': 'Enterprise social/SEO intelligence platform.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SECURITY': [{'jwtAuth': []}],
}

# --------------------------------------------------------------------------- #
# Security headers / TLS posture
# --------------------------------------------------------------------------- #
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SSL redirect defaults to ON in production, OFF in DEBUG. The env var lets a
# staging deployment behind a TLS-terminating proxy override either way.
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', '1' if not DEBUG else '0') == '1'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')


def _require_csrf_trusted_origins(debug: bool) -> list[str]:
    """
    Parse ``DJANGO_CSRF_TRUSTED_ORIGINS`` (comma-separated, full scheme+host,
    e.g. ``"https://app.nuxtron.io,https://admin.nuxtron.io"``).

    Fails closed: in production an empty list means Django rejects every unsafe
    (POST/PUT/PATCH/DELETE) browser request, including the admin — so we refuse
    to boot rather than serve a silently broken app. Plain ``http://`` origins
    are rejected in production because they cannot be trusted behind a
    TLS-terminating proxy.
    """
    from django.core.exceptions import ImproperlyConfigured

    raw = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
    origins = [o.strip() for o in raw.split(',') if o.strip()]

    if not debug:
        if not origins:
            raise ImproperlyConfigured(
                'DJANGO_CSRF_TRUSTED_ORIGINS is required when DEBUG=False. '
                'Set it to the comma-separated list of externally-facing '
                'origins that serve this app, e.g. '
                "'https://app.nuxtron.io,https://admin.nuxtron.io'."
            )
        for origin in origins:
            if not origin.startswith('https://'):
                raise ImproperlyConfigured(
                    f"CSRF trusted origin '{origin}' must use https:// in "
                    'production — plain http origins cannot be trusted '
                    'behind a TLS-terminating proxy.'
                )
    return origins


CSRF_TRUSTED_ORIGINS = _require_csrf_trusted_origins(DEBUG)
CSRF_COOKIE_HTTPONLY = True  # JS never reads the CSRF cookie directly; the token
                             # is delivered via template/meta tag or the
                             # X-CSRFToken header pattern for API clients.
CSRF_USE_SESSIONS = False    # cookie-based CSRF is fine given SameSite + HTTPS

SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000')) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# --------------------------------------------------------------------------- #
# Content-Security-Policy — enforced by csp.middleware.CSPMiddleware.
# Policy lives in config/csp.py so it is independently testable and reviewable.
# In production DJANGO_CSP_REPORT_URI is required (fail-closed) so violations
# are observable.
# --------------------------------------------------------------------------- #
from config.csp import build_csp_settings  # noqa: E402

globals().update(build_csp_settings(debug=DEBUG))

# --------------------------------------------------------------------------- #
# Cookies / sessions
# --------------------------------------------------------------------------- #
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', str(60 * 60 * 8)))  # 8h
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# --------------------------------------------------------------------------- #
# i18n / static / media
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


def _build_media_storage(*, is_production: bool) -> dict[str, Any]:
    """Media storage backend: S3 in production, local filesystem in dev.

    Local `FileSystemStorage` doesn't survive container restarts or scale-out
    (each replica would see a different disk), so production requires a real
    object store. Fails closed — same pattern as SECRET_KEY/ALLOWED_HOSTS —
    rather than silently falling back to ephemeral local storage.
    """
    from django.core.exceptions import ImproperlyConfigured

    bucket = os.getenv('AWS_STORAGE_BUCKET_NAME', '').strip()
    if not is_production:
        return {'BACKEND': 'django.core.files.storage.FileSystemStorage'}

    if not bucket:
        if os.getenv('ALLOW_LOCAL_MEDIA_STORAGE', '').strip().lower() in {'1', 'true', 'yes'}:
            import logging

            logging.getLogger(__name__).warning(
                'ALLOW_LOCAL_MEDIA_STORAGE=1: using local FileSystemStorage in '
                'production. Uploaded files will NOT survive container '
                'restarts, redeploys, or scale-out. Set AWS_STORAGE_BUCKET_NAME '
                '(+ credentials) and remove this flag before relying on file '
                'uploads for real.'
            )
            return {'BACKEND': 'django.core.files.storage.FileSystemStorage'}
        raise ImproperlyConfigured(
            'AWS_STORAGE_BUCKET_NAME is required in production. Local media '
            "storage doesn't survive container restarts or scale-out — set "
            'the bucket plus AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY (or rely '
            'on an IAM instance role) and AWS_S3_REGION_NAME. To deploy '
            'without S3 for now, set ALLOW_LOCAL_MEDIA_STORAGE=1 instead — '
            'file uploads will be lost on every restart until you configure S3.'
        )
    return {'BACKEND': 'storages.backends.s3.S3Storage'}


STORAGES: dict[str, Any] = {
    'default': _build_media_storage(is_production=IS_PRODUCTION),
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        )
    },
}

if STORAGES['default']['BACKEND'] == 'storages.backends.s3.S3Storage':
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '').strip()
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', '').strip() or None
    # Credentials are optional here on purpose: omitting them lets boto3 fall
    # back to an IAM instance/task role, which is preferred over static keys.
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '').strip() or None
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '').strip() or None
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', '').strip() or None
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', '').strip() or None
    AWS_DEFAULT_ACL = None  # bucket policy governs access; don't set per-object ACLs
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = os.getenv('AWS_QUERYSTRING_AUTH', '1') == '1'
    MEDIA_URL = (
        f'https://{AWS_S3_CUSTOM_DOMAIN}/'
        if AWS_S3_CUSTOM_DOMAIN
        else f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'
    )
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------------------------------------------------- #
# Email (console in dev; SMTP in prod via env).
# --------------------------------------------------------------------------- #
if DEBUG and not os.getenv('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1') == '1'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', '0') == '1'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@nuxtron.local')

# --------------------------------------------------------------------------- #
# Logging — structured JSON in production, human-readable in dev.
# --------------------------------------------------------------------------- #
_LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'INFO').upper()
_logger_fmt = '%(asctime)s %(levelname)s [%(name)s] request_id=%(request_id)s %(message)s'

LOGGING: dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {'()': 'platform_api.logging_filters.RequestIDFilter'},
    },
    'formatters': {
        'json': {
            '()': 'platform_api.logging_filters.JsonFormatter',
        },
        'verbose': {'format': _logger_fmt},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['request_id'],
            'formatter': 'json' if IS_PRODUCTION else 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': _LOG_LEVEL},
    'loggers': {
        'django': {'handlers': ['console'], 'level': _LOG_LEVEL, 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'django.security': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'platform_api': {'handlers': ['console'], 'level': _LOG_LEVEL, 'propagate': False},
        'apps.intelligence': {'handlers': ['console'], 'level': _LOG_LEVEL, 'propagate': False},
    },
}

# --------------------------------------------------------------------------- #
# Misc production hardening
# --------------------------------------------------------------------------- #
# Disallow serving the admin via a model-less superuser shell only; ensure
# default permissions are applied to every view (IsAuthenticated by default).
DEFAULT_PERMISSION = 'rest_framework.permissions.IsAuthenticated'

# How long to keep uploaded files before cleanup sweep (seconds).
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(2 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(5 * 1024 * 1024)))

# --------------------------------------------------------------------------- #
# Error tracking (Sentry)
# --------------------------------------------------------------------------- #
# Unlike SECRET_KEY/ALLOWED_HOSTS, a missing SENTRY_DSN is not a security gap —
# it just means errors only go to the structured JSON logs above. So this is
# opt-in (skip quietly if unset) rather than fail-closed.
_SENTRY_DSN = os.getenv('SENTRY_DSN', '').strip()
if _SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            # Our own LOGGING config already emits structured JSON at INFO+;
            # only forward ERROR+ to Sentry as events to avoid noise/cost.
            LoggingIntegration(level=None, event_level='ERROR'),
        ],
        environment=os.getenv('DJANGO_ENV', 'production'),
        release=os.getenv('APP_VERSION', 'unknown'),
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
        send_default_pii=False,
    )
