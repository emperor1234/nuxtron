"""
Celery worker for Nuxtron background task processing.

Start with:
    celery -A backend.fastapi.app.worker worker --loglevel=info -c 4

Or via RQ fallback:
    rq worker nuxtron-tasks --url redis://localhost:6379
"""
from __future__ import annotations

import logging
import os

from celery import Celery
from celery.utils.log import get_task_logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(int(value), minimum)
    except ValueError:
        return default


AI_IMAGE_SOFT_LIMIT = _env_int("AI_IMAGE_SOFT_TIME_LIMIT_SECONDS", 120, 30)
AI_IMAGE_HARD_LIMIT = _env_int("AI_IMAGE_HARD_TIME_LIMIT_SECONDS", 180, AI_IMAGE_SOFT_LIMIT)
AI_TEXT_SOFT_LIMIT = _env_int("AI_TEXT_SOFT_TIME_LIMIT_SECONDS", 45, 10)
AI_TEXT_HARD_LIMIT = _env_int("AI_TEXT_HARD_TIME_LIMIT_SECONDS", 75, AI_TEXT_SOFT_LIMIT)
AI_VIDEO_SOFT_LIMIT = _env_int("AI_VIDEO_SOFT_TIME_LIMIT_SECONDS", 600, 120)
AI_VIDEO_HARD_LIMIT = _env_int("AI_VIDEO_HARD_TIME_LIMIT_SECONDS", 900, AI_VIDEO_SOFT_LIMIT)
AI_VOICE_SOFT_LIMIT = _env_int("AI_VOICE_SOFT_TIME_LIMIT_SECONDS", 240, 60)
AI_VOICE_HARD_LIMIT = _env_int("AI_VOICE_HARD_TIME_LIMIT_SECONDS", 360, AI_VOICE_SOFT_LIMIT)

# ---------------------------------------------------------------------------
# App config
# ---------------------------------------------------------------------------
celery_app = Celery(
    "nuxtron",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=_env_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1, 1),
    worker_max_tasks_per_child=_env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 100, 10),
    worker_max_memory_per_child=_env_int("CELERY_WORKER_MAX_MEMORY_PER_CHILD_KB", 786432, 131072),
    task_acks_late=True,
    task_acks_on_failure_or_timeout=True,
    task_default_priority=5,
    task_queue_max_priority=10,
    task_inherit_parent_priority=True,
    task_default_delivery_mode="persistent",
    broker_pool_limit=_env_int("CELERY_BROKER_POOL_LIMIT", 20, 1),
    broker_transport_options={
        "queue_order_strategy": "priority",
        "priority_steps": list(range(10)),
        "sep": ":",
        "visibility_timeout": _env_int("CELERY_VISIBILITY_TIMEOUT_SECONDS", 7200, 300),
    },
    task_annotations={
        "nuxtron.tasks.ai.process_image": {
            "rate_limit": os.getenv("CELERY_RATE_LIMIT_AI_IMAGE", "30/m"),
            "soft_time_limit": AI_IMAGE_SOFT_LIMIT,
            "time_limit": AI_IMAGE_HARD_LIMIT,
        },
        "nuxtron.tasks.ai.process_text": {
            "rate_limit": os.getenv("CELERY_RATE_LIMIT_AI_TEXT", "120/m"),
            "soft_time_limit": AI_TEXT_SOFT_LIMIT,
            "time_limit": AI_TEXT_HARD_LIMIT,
        },
        "nuxtron.tasks.ai.process_video": {
            "rate_limit": os.getenv("CELERY_RATE_LIMIT_AI_VIDEO", "8/m"),
            "soft_time_limit": AI_VIDEO_SOFT_LIMIT,
            "time_limit": AI_VIDEO_HARD_LIMIT,
        },
        "nuxtron.tasks.ai.process_voice": {
            "rate_limit": os.getenv("CELERY_RATE_LIMIT_AI_VOICE", "24/m"),
            "soft_time_limit": AI_VOICE_SOFT_LIMIT,
            "time_limit": AI_VOICE_HARD_LIMIT,
        },
    },
    task_routes={
        "nuxtron.tasks.ai.process_image": {"queue": "ai-image"},
        "nuxtron.tasks.ai.process_text": {"queue": "ai-text"},
        "nuxtron.tasks.ai.process_video": {"queue": "ai-video"},
        "nuxtron.tasks.ai.process_voice": {"queue": "ai-voice"},
        "nuxtron.tasks.analytics.*": {"queue": "analytics"},
        "nuxtron.tasks.seo.*": {"queue": "seo"},
        "nuxtron.tasks.notifications.*": {"queue": "notifications"},
    },
)

task_logger = get_task_logger(__name__)
logger = logging.getLogger("nuxtron.worker")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="nuxtron.tasks.analytics.compute_metrics", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def compute_analytics_metrics(self, org_id: str, period: str = "7d") -> dict:  # type: ignore[misc]
    """Recompute aggregated analytics metrics for an org (background)."""
    task_logger.info("Computing analytics metrics org=%s period=%s", org_id, period)
    # Placeholder — wire real DB queries here
    return {"org_id": org_id, "period": period, "status": "queued"}


@celery_app.task(name="nuxtron.tasks.seo.refresh_scores", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def refresh_seo_scores(self, url: str) -> dict:  # type: ignore[misc]
    """Refresh SEO scores for a URL in the background."""
    task_logger.info("Refreshing SEO scores url=%s", url)
    return {"url": url, "status": "queued"}


@celery_app.task(name="nuxtron.tasks.notifications.send_digest", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def send_notification_digest(self, user_id: str) -> dict:  # type: ignore[misc]
    """Send daily digest notification for a user."""
    task_logger.info("Sending notification digest user_id=%s", user_id)
    return {"user_id": user_id, "status": "queued"}


def _run_ai_task(media_type: str, payload: dict) -> dict:
    """Run a specific AI generation modality inside worker process."""
    import asyncio

    from backend.fastapi.app.routers.ai import (
        AIGenerationRequest,
        _generate_image,
        _generate_text,
        _generate_video,
        _generate_voice,
    )

    task_logger.info("Processing AI generation media_type=%s", media_type)
    request_model = AIGenerationRequest(**payload)

    if media_type == "image":
        response = asyncio.run(_generate_image(request_model))
        return response.model_dump()
    if media_type == "text":
        response = asyncio.run(_generate_text(request_model))
        return response.model_dump()
    if media_type == "video":
        response = asyncio.run(_generate_video(request_model))
        return response.model_dump()
    if media_type == "voice":
        orchestration_plan = payload.get("orchestration_plan")
        if not isinstance(orchestration_plan, dict):
            orchestration_plan = None
        response = asyncio.run(_generate_voice(request_model, orchestration_plan))
        return response.model_dump()

    return {
        "status": "error",
        "error": f"Unsupported Celery media type: {media_type}",
    }


@celery_app.task(name="nuxtron.tasks.ai.process_image", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_image(self, payload: dict) -> dict:  # type: ignore[misc]
    return _run_ai_task("image", payload)


@celery_app.task(name="nuxtron.tasks.ai.process_text", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_text(self, payload: dict) -> dict:  # type: ignore[misc]
    return _run_ai_task("text", payload)


@celery_app.task(name="nuxtron.tasks.ai.process_video", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_video(self, payload: dict) -> dict:  # type: ignore[misc]
    return _run_ai_task("video", payload)


@celery_app.task(name="nuxtron.tasks.ai.process_voice", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_voice(self, payload: dict) -> dict:  # type: ignore[misc]
    return _run_ai_task("voice", payload)


if __name__ == "__main__":
    celery_app.start()
