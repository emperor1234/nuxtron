"""
Celery worker for Nuxtron background task processing.

Start with:
    celery -A backend.fastapi.app.celery_app:celery_app worker --loglevel=INFO -c 4

AI task adapters are registered here; Workforce execution is explicitly gated off in production.
"""
from __future__ import annotations

import logging
import os

from celery.utils.log import get_task_logger

from .celery_app import celery_app
from .durable_jobs import claim_pending_outbox, load_job, mark_outbox_failed, mark_outbox_published, update_job


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
    },
)
celery_app.conf.beat_schedule = {
    "publish-ai-job-outbox": {
        "task": "nuxtron.tasks.ai.publish_outbox",
        "schedule": 30.0,
    },
}

task_logger = get_task_logger(__name__)
logger = logging.getLogger("nuxtron.worker")

# Import task modules so the same canonical app used by producers registers
# workforce tasks when the documented worker entrypoint is loaded.
from .tasks import workforce_tasks as _workforce_tasks  # noqa: F401,E402

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def _run_ai_task(media_type: str, job_reference: str) -> dict:
    """Run a modality from durable storage; no prompt is accepted from Celery."""
    import asyncio

    from backend.fastapi.app.routers.ai import (
        AIGenerationRequest,
        _generate_image,
        _generate_text,
        _generate_video,
        _generate_voice,
    )

    job, _ = load_job(job_reference)
    payload = dict(job.job_params or {})
    update_job(job_reference, status="running")
    try:
        task_logger.info("Processing durable AI job media_type=%s", media_type)
        request_model = AIGenerationRequest(**payload)
        if media_type == "image":
            response = asyncio.run(_generate_image(request_model))
        elif media_type == "text":
            response = asyncio.run(_generate_text(request_model))
        elif media_type == "video":
            response = asyncio.run(_generate_video(request_model))
        elif media_type == "voice":
            plan = payload.get("orchestration_plan")
            response = asyncio.run(_generate_voice(request_model, plan if isinstance(plan, dict) else None))
        else:
            raise ValueError(f"Unsupported Celery media type: {media_type}")
        result = response.model_dump()
        if result.get("status") == "success":
            update_job(job_reference, status="completed", result=result)
        else:
            update_job(job_reference, status="failed", result=result, error_message=str(result.get("error") or "AI worker task failed"))
        return result
    except Exception as exc:
        update_job(job_reference, status="failed", error_message=f"{type(exc).__name__}: {exc}")
        raise


@celery_app.task(name="nuxtron.tasks.ai.process_image", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_image(self, job_reference: str) -> dict:  # type: ignore[misc]
    return _run_ai_task("image", job_reference)


@celery_app.task(name="nuxtron.tasks.ai.process_text", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_text(self, job_reference: str) -> dict:  # type: ignore[misc]
    return _run_ai_task("text", job_reference)


@celery_app.task(name="nuxtron.tasks.ai.process_video", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_video(self, job_reference: str) -> dict:  # type: ignore[misc]
    return _run_ai_task("video", job_reference)


@celery_app.task(name="nuxtron.tasks.ai.process_voice", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def process_ai_voice(self, job_reference: str) -> dict:  # type: ignore[misc]
    return _run_ai_task("voice", job_reference)


@celery_app.task(name="nuxtron.tasks.ai.publish_outbox")  # type: ignore[untyped-decorator]
def publish_pending_ai_jobs() -> dict[str, int]:
    """Relay committed outbox messages that were not published by the API."""
    published = 0
    failed = 0
    for item in claim_pending_outbox():
        try:
            task = celery_app.send_task(
                item["task_name"],
                kwargs={"job_reference": item["reference"]},
                queue=item["queue"],
            )
            mark_outbox_published(item["reference"], task.id)
            published += 1
        except Exception as exc:
            mark_outbox_failed(item["reference"], f"Outbox relay failed: {exc}")
            failed += 1
            task_logger.exception("Failed to relay AI outbox message")
    return {"published": published, "failed": failed}


if __name__ == "__main__":
    celery_app.start()
