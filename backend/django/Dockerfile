# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Multi-stage build for the Nuxtron Django backend.
#   Stage 1 (builder): install deps into a venv without build tools in final.
#   Stage 2 (runtime): slim image, non-root, tuned gunicorn, healthcheck.
# ---------------------------------------------------------------------------

ARG PYTHON_VERSION=3.13

# ---------- Stage 1: builder ------------------------------------------------ #
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Build deps for wheels (bcrypt/argon2/cryptography/psycopg compile C here only).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: runtime ----------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings \
    PYTHONPATH=/app

# Runtime libs only: libpq for psycopg. No build-essential, no compilers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (created here so UID is deterministic across image layers).
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

# Persistent dirs for static + media, owned by the runtime user.
RUN install -d -o app -g app /app/staticfiles /app/media

USER app

EXPOSE 8000

# Gunicorn tuning for containers:
#   - workers: 2x CPU + 1 is conventional; we let Gunicorn's default pick CPU
#     count and override via $WEB_CONCURRENCY (set by the orchestrator).
#   - timeout: 30s, matches ALB/nginx default idle.
#   - graceful-timeout: lets in-flight requests finish on SIGTERM.
#   - access-logfile -: request logs to stdout for the collector.
#   - preload: import app once before forking -> lower RSS, faster boot.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads ${WEB_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-30} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" req_id=%({X-Request-Id}i)s' \
    --preload"]

# Container health: hit the liveness probe. Readiness (dep checks) is separate
# so the orchestrator can drain without killing the process.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health/ || exit 1
