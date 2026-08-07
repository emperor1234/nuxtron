# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Multi-stage build for the Nuxtron FastAPI service.
#   Stage 1 (builder): compile wheels without build tools in the final image.
#   Stage 2 (runtime): slim, non-root, healthchecked, tuned uvicorn workers.
# ---------------------------------------------------------------------------

ARG PYTHON_VERSION=3.13

# ---------- Stage 1: builder ------------------------------------------------ #
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# No apt packages needed here: every dependency in requirements.txt installs
# from a prebuilt manylinux wheel on this Python/platform combo (confirmed —
# cryptography, bcrypt, pynacl, lxml, xmlsec, pqcrypto, argon2-cffi-bindings
# all ship wheels; psycopg[binary] bundles its own libpq, it doesn't need
# libpq-dev to build against). build-essential + libpq-dev were pure dead
# weight here — ~90MB of gcc/g++ downloaded and installed to compile nothing,
# adding build time and memory pressure for no benefit.
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
    PYTHONPATH=/monorepo

# Runtime libs only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Deterministic non-root user.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

# The test suite imports the package under backend.fastapi.app; mirror that
# path so both import styles resolve to the same module.
RUN mkdir -p /monorepo/backend/fastapi /monorepo/services \
    && ln -sf /app/app /monorepo/backend/fastapi/app \
    && touch /monorepo/services/__init__.py /monorepo/backend/fastapi/__init__.py \
    && chown -R app:app /app /monorepo

USER app

EXPOSE 8001

# uvicorn behind gunicorn gives graceful worker management (max-requests
# recycling, preloaded app). Use --workers from WEB_CONCURRENCY.
CMD ["sh", "-c", "exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8001 \
    --workers ${WEB_CONCURRENCY:-1} \
    --timeout ${GUNICORN_TIMEOUT:-30} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --preload"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8001/healthz || exit 1
