# pyright: reportUnusedFunction=false
"""AI model integration router — connects frontend to Ollama, ComfyUI, WhisperX, voice workers."""

import asyncio
import base64
import io
import json
import logging
import os
import re
import secrets
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

try:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat

    _PIL_AVAILABLE = True
except Exception:
    Image: Any = None
    ImageChops: Any = None
    ImageDraw: Any = None
    ImageEnhance: Any = None
    ImageFilter: Any = None
    ImageOps: Any = None
    ImageStat: Any = None
    _PIL_AVAILABLE = False

from ..deps import AuthContext, require_auth
from ..redis_cache import get_redis

logger = logging.getLogger(__name__)

# ─── AI Service Base URLs ─────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://localhost:8188")
WHISPERX_BASE_URL = os.getenv("WHISPERX_BASE_URL", "http://localhost:9005")
OPENVOICE_WORKER_URL = os.getenv("OPENVOICE_WORKER_URL", "http://localhost:9011")
BARK_WORKER_URL = os.getenv("BARK_WORKER_URL", "http://localhost:9012")
RVC_WORKER_URL = os.getenv("RVC_WORKER_URL", "http://localhost:9013")

# ─── In-memory async job store ────────────────────────────────────────────────
# Maps job_id -> {status, result, error}
_image_jobs: dict[str, dict[str, Any]] = {}
_AI_JOB_STORE_PREFIX = "nuxtron:ai:job:"
_AI_JOB_TTL_SECONDS = max(int(os.getenv("AI_JOB_TTL_SECONDS", "86400")), 600)
_AI_TASK_NAME_BY_MEDIA = {
    "image": "nuxtron.tasks.ai.process_image",
    "text": "nuxtron.tasks.ai.process_text",
    "video": "nuxtron.tasks.ai.process_video",
    "voice": "nuxtron.tasks.ai.process_voice",
}
_AI_QUEUE_BY_MEDIA = {
    "image": "ai-image",
    "text": "ai-text",
    "video": "ai-video",
    "voice": "ai-voice",
}
_AI_PRIORITY_BY_MEDIA = {
    "text": 9,
    "image": 8,
    "voice": 6,
    "video": 4,
}
_AI_EXPIRES_SECONDS_BY_MEDIA = {
    "text": 10 * 60,
    "image": 20 * 60,
    "voice": 30 * 60,
    "video": 60 * 60,
}

_SUSPICIOUS_PROMPT_PATTERNS = (
    r"<\s*script\b",
    r"javascript:",
    r"<\?php",
    r"\b(__import__|subprocess\.|os\.system|eval\(|exec\()",
    r"\b(drop\s+table|delete\s+from|truncate\s+table|union\s+select)\b",
)
_MODEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]{1,100}$")
_MEDIA_UPLOAD_BASE = Path("backend/fastapi/app/runtime_uploads/social_studio")
_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav"}


async def _persist_ai_job(job_id: str, payload: dict[str, Any]) -> None:
    _image_jobs[job_id] = payload
    client = await get_redis()
    if client is None:
        return
    try:
        await client.setex(f"{_AI_JOB_STORE_PREFIX}{job_id}", _AI_JOB_TTL_SECONDS, json.dumps(payload, default=str))
    except Exception:
        logger.debug("Failed to persist AI job %s to Redis", job_id, exc_info=True)


async def _load_ai_job(job_id: str) -> dict[str, Any] | None:
    if job_id in _image_jobs:
        return _image_jobs[job_id]
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(f"{_AI_JOB_STORE_PREFIX}{job_id}")
        if not raw:
            return None
        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            _image_jobs[job_id] = decoded
            return decoded
    except Exception:
        logger.debug("Failed to load AI job %s from Redis", job_id, exc_info=True)
    return None


def _resolve_celery_runtime():
    if os.getenv("ENABLE_CELERY_AI_JOBS", "1").strip().lower() not in {"1", "true", "yes", "on"}:
        return None, None
    try:
        from celery.result import AsyncResult

        from ..worker import celery_app

        return celery_app, AsyncResult
    except Exception:
        logger.debug("Celery runtime unavailable for AI jobs", exc_info=True)
        return None, None


class AIGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    media_type: str = Field(..., pattern="^(image|video|voice|text)$")
    model: str = Field(default="")
    style: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    creative_mode: str | None = Field(default=None, max_length=64)
    prompt_description: str | None = Field(default=None, max_length=5000)
    aspect_ratio: str | None = Field(default=None, max_length=20)
    resolution: str | None = Field(default=None, max_length=20)
    contains_real_people: bool = False
    return_last_frame: bool = False
    seed_enabled: bool = False
    seed: str | None = Field(default=None, max_length=32)
    reference_images: list[str] = Field(default_factory=list)
    reference_videos: list[str] = Field(default_factory=list)
    reference_audios: list[str] = Field(default_factory=list)
    portrait_library: dict[str, Any] = Field(default_factory=dict)
    capability: str | None = Field(default=None, max_length=80)
    delivery_mode: str | None = Field(default=None, max_length=80)
    orchestration_goal: str | None = Field(default=None, max_length=160)
    complexity: str | None = Field(default='auto', max_length=20)
    auto_route: bool = True
    use_case: str | None = Field(default=None, max_length=80)
    target_channels: list[str] = Field(default_factory=list)
    candidate_models: list[str] = Field(default_factory=list)
    edit_tools: list[str] = Field(default_factory=list)
    brand_rules: list[str] = Field(default_factory=list)


class AIGenerationResponse(BaseModel):
    status: str
    job_id: str | None = None
    content: str | None = None
    media_url: str | None = None
    error: str | None = None
    orchestration_plan: dict[str, Any] | None = None
    estimated_credits: int | None = None


class AIImageEditRequest(BaseModel):
    image_data: str = Field(..., min_length=32)
    mask_data: str | None = None
    prompt: str | None = Field(default=None, max_length=2000)
    filter_name: str | None = Field(default=None, max_length=64)
    upscale_factor: int = Field(default=2, ge=1, le=4)
    target_width: int | None = Field(default=None, ge=64, le=4096)
    target_height: int | None = Field(default=None, ge=64, le=4096)


class AIImageEditResponse(BaseModel):
    status: str
    image_url: str | None = None
    mask_url: str | None = None
    operation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_ai_router(enforce_rate_limit, audit_log_memory, credit_ledger_memory) -> APIRouter:
    """Factory for AI router with dependency injection."""
    router = APIRouter(prefix="/ai", tags=["ai"])
    ledger_lock = threading.Lock()

    def _credit_balance(tenant_id: str) -> int:
        with ledger_lock:
            return sum(int(entry.get("amount", 0)) for entry in credit_ledger_memory if entry.get("tenant_id") == tenant_id)

    def _append_credit_entry(tenant_id: str, amount: int, reason: str, metadata: dict[str, Any]) -> None:
        with ledger_lock:
            credit_ledger_memory.append(
                {
                    "id": len(credit_ledger_memory) + 1,
                    "tenant_id": tenant_id,
                    "amount": amount,
                    "reason": reason,
                    "created_at": datetime.now(UTC).isoformat(),
                    **metadata,
                }
            )

    @router.post("/social-studio/plan")
    async def plan_social_studio_generation(
        payload: AIGenerationRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ai:plan", limit=90, window_seconds=60)
        try:
            plan = await _build_social_studio_plan(payload)
        except RuntimeError as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "credit_balance": _credit_balance(auth.tenant_id),
            "plan": plan,
        }

    @router.post("/social-studio/generate")
    async def generate_content(
        request: Request,
        background_tasks: BackgroundTasks,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIGenerationResponse:
        """Generate AI content (images, videos, voice, copy)."""
        enforce_rate_limit(f"{auth.tenant_id}:ai:generate", limit=30, window_seconds=60)

        payload, parse_error = await _parse_generation_request(request, auth.tenant_id)
        if payload is None:
            return AIGenerationResponse(status="error", error=parse_error or "Invalid generation payload")

        sanitized_prompt = _sanitize_prompt(payload.prompt)
        if sanitized_prompt is None:
            return AIGenerationResponse(
                status="error",
                error="Prompt contains blocked or potentially malicious content.",
            )
        payload.prompt = sanitized_prompt

        if payload.style:
            sanitized_style = _sanitize_prompt(payload.style)
            if sanitized_style is None:
                return AIGenerationResponse(
                    status="error",
                    error="Style contains blocked or potentially malicious content.",
                )
            payload.style = sanitized_style

        if payload.prompt_description:
            sanitized_description = _sanitize_prompt(payload.prompt_description)
            if sanitized_description is None:
                return AIGenerationResponse(
                    status="error",
                    error="Prompt description contains blocked or potentially malicious content.",
                )
            payload.prompt_description = sanitized_description

        if payload.model.strip().lower() == "auto choose model":
            payload.model = ""

        payload.reference_images = [str(name)[:200] for name in payload.reference_images[:9]]
        payload.reference_videos = [str(name)[:200] for name in payload.reference_videos[:3]]
        payload.reference_audios = [str(name)[:200] for name in payload.reference_audios[:3]]

        if payload.seed_enabled:
            normalized_seed = re.sub(r"[^0-9]", "", payload.seed or "")[:12]
            payload.seed = normalized_seed or str(secrets.randbelow(1_000_000_000))
        else:
            payload.seed = ""

        if payload.media_type == "text" and payload.model and not _MODEL_NAME_PATTERN.fullmatch(payload.model):
            return AIGenerationResponse(
                status="error",
                error="Invalid model name format.",
            )

        try:
            orchestration_plan = await _build_social_studio_plan(payload)
        except RuntimeError as exc:
            return AIGenerationResponse(status="error", error=str(exc))
        estimated_credits = int(orchestration_plan["estimated_credits"])
        current_balance = _credit_balance(auth.tenant_id)
        if current_balance < estimated_credits:
            return AIGenerationResponse(
                status="error",
                error=(
                    f"Insufficient paid credits. Required {estimated_credits}, available {current_balance}. "
                    "Complete billing confirmation before starting this workload."
                ),
                orchestration_plan=orchestration_plan,
                estimated_credits=estimated_credits,
            )

        if payload.media_type in _AI_TASK_NAME_BY_MEDIA:
            job_id = str(uuid.uuid4())
            reservation_reference = f"ai_{auth.tenant_id}_{job_id}"
            _append_credit_entry(
                auth.tenant_id,
                -estimated_credits,
                "ai_generation_reserved",
                {
                    "job_id": job_id,
                    "reservation_reference": reservation_reference,
                    "capability": orchestration_plan["capability"],
                    "provider": orchestration_plan["recommended_provider"]["provider"],
                },
            )
            job_record: dict[str, Any] = {
                "status": "pending",
                "tenant_id": auth.tenant_id,
                "estimated_credits": estimated_credits,
                "reservation_reference": reservation_reference,
                "orchestration_plan": orchestration_plan,
            }
            celery_app, _ = _resolve_celery_runtime()  # type: ignore[no-untyped-call]
            used_celery = False
            if celery_app is not None:
                try:
                    celery_task = celery_app.send_task(
                        _AI_TASK_NAME_BY_MEDIA[payload.media_type],
                        kwargs={
                            "payload": payload.model_dump(),
                        },
                        queue=_AI_QUEUE_BY_MEDIA[payload.media_type],
                        priority=_AI_PRIORITY_BY_MEDIA[payload.media_type],
                        expires=_AI_EXPIRES_SECONDS_BY_MEDIA[payload.media_type],
                    )
                    job_record["celery_task_id"] = celery_task.id
                    job_record["execution_mode"] = "celery"
                    used_celery = True
                except Exception:
                    logger.exception("Failed to enqueue Celery AI job; falling back to in-process background task")

            if not used_celery:
                if payload.media_type == "image":
                    background_tasks.add_task(
                        _run_image_job,
                        job_id,
                        payload,
                        auth.tenant_id,
                        estimated_credits,
                        reservation_reference,
                        credit_ledger_memory,
                        ledger_lock,
                    )
                elif payload.media_type == "text":
                    background_tasks.add_task(
                        _run_text_job,
                        job_id,
                        payload,
                        auth.tenant_id,
                        estimated_credits,
                        reservation_reference,
                        credit_ledger_memory,
                        ledger_lock,
                    )
                elif payload.media_type == "video":
                    background_tasks.add_task(
                        _run_video_job,
                        job_id,
                        payload,
                        auth.tenant_id,
                        estimated_credits,
                        reservation_reference,
                        credit_ledger_memory,
                        ledger_lock,
                    )
                else:
                    background_tasks.add_task(
                        _run_voice_job,
                        job_id,
                        payload,
                        orchestration_plan,
                        auth.tenant_id,
                        estimated_credits,
                        reservation_reference,
                        credit_ledger_memory,
                        ledger_lock,
                    )
                job_record["execution_mode"] = "in-process"

            await _persist_ai_job(job_id, job_record)
            content_msg = f"{payload.media_type.capitalize()} generation started. Poll /ai/social-studio/job/{{job_id}} for result."
            audit_log_memory.append(
                {
                    "id": len(audit_log_memory) + 1,
                    "tenant_id": auth.tenant_id,
                    "action": "social_studio_generation_started",
                    "created_at": datetime.now(UTC).isoformat(),
                    "job_id": job_id,
                    "provider": orchestration_plan["recommended_provider"]["provider"],
                    "estimated_credits": estimated_credits,
                }
            )
            return AIGenerationResponse(
                status="pending",
                job_id=job_id,
                content=content_msg,
                orchestration_plan=orchestration_plan,
                estimated_credits=estimated_credits,
            )

        return AIGenerationResponse(
            status="error",
            error=f"Unsupported media type: {payload.media_type}",
            orchestration_plan=orchestration_plan,
            estimated_credits=estimated_credits,
        )

    @router.get("/social-studio/job/{job_id}")
    async def get_job_status(
        job_id: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIGenerationResponse:
        """Poll status of a background image generation job."""
        job = await _load_ai_job(job_id)
        if job is None:
            return AIGenerationResponse(status="error", error="Job not found.")

        if job.get("execution_mode") == "celery" and job.get("status") == "pending":
            celery_app, async_result_cls = _resolve_celery_runtime()  # type: ignore[no-untyped-call]
            task_id = str(job.get("celery_task_id") or "")
            if celery_app is not None and async_result_cls is not None and task_id:
                task_result = async_result_cls(task_id, app=celery_app)
                if task_result.ready():
                    if task_result.successful():
                        result_payload = task_result.result or {}
                        if not isinstance(result_payload, dict):
                            result_payload = {"error": f"Unexpected task result type: {type(task_result.result).__name__}"}
                        if result_payload.get("status") == "success":
                            job = {
                                **job,
                                "status": "success",
                                "content": result_payload.get("content"),
                                "media_url": result_payload.get("media_url"),
                            }
                        else:
                            _refund_reserved_credits(
                                str(job.get("tenant_id", auth.tenant_id)),
                                int(job.get("estimated_credits", 0)),
                                str(job.get("reservation_reference", "")),
                                credit_ledger_memory,
                                ledger_lock,
                            )
                            job = {
                                **job,
                                "status": "error",
                                "error": str(result_payload.get("error") or "AI job failed."),
                            }
                    else:
                        _refund_reserved_credits(
                            str(job.get("tenant_id", auth.tenant_id)),
                            int(job.get("estimated_credits", 0)),
                            str(job.get("reservation_reference", "")),
                            credit_ledger_memory,
                            ledger_lock,
                        )
                        job = {
                            **job,
                            "status": "error",
                            "error": str(task_result.result or "AI worker task failed."),
                        }
                    await _persist_ai_job(job_id, job)

        if job["status"] == "pending":
            return AIGenerationResponse(
                status="pending",
                job_id=job_id,
                content="Still generating…",
                orchestration_plan=job.get("orchestration_plan"),
                estimated_credits=job.get("estimated_credits"),
            )
        if job["status"] == "error":
            return AIGenerationResponse(
                status="error",
                job_id=job_id,
                error=job.get("error"),
                orchestration_plan=job.get("orchestration_plan"),
                estimated_credits=job.get("estimated_credits"),
            )
        return AIGenerationResponse(
            status="success",
            job_id=job_id,
            content=job.get("content"),
            media_url=job.get("media_url"),
            orchestration_plan=job.get("orchestration_plan"),
            estimated_credits=job.get("estimated_credits"),
        )

    @router.get("/health")
    async def health_check() -> dict:
        """Check AI service health."""
        health = {
            "ollama": await _check_service(OLLAMA_BASE_URL),
            "comfyui": await _check_service(COMFYUI_BASE_URL),
            "whisperx": await _check_service(WHISPERX_BASE_URL),
            "openvoice": await _check_service(OPENVOICE_WORKER_URL),
            "bark": await _check_service(BARK_WORKER_URL),
            "rvc": await _check_service(RVC_WORKER_URL),
        }
        return health

    @router.post("/image/select-subject", response_model=AIImageEditResponse)
    async def image_select_subject(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:select-subject", limit=30, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        mask = _build_subject_mask(image)
        return AIImageEditResponse(
            status="success",
            operation="select-subject",
            image_url=_encode_png_data_url(image),
            mask_url=_encode_png_data_url(mask.convert("RGB")),
            metadata={"width": image.width, "height": image.height},
        )

    @router.post("/image/sky-segment", response_model=AIImageEditResponse)
    async def image_sky_segment(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:sky-segment", limit=30, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        mask = _build_sky_mask(image)
        return AIImageEditResponse(
            status="success",
            operation="sky-segment",
            image_url=_encode_png_data_url(image),
            mask_url=_encode_png_data_url(mask.convert("RGB")),
            metadata={"width": image.width, "height": image.height},
        )

    @router.post("/image/gen-fill", response_model=AIImageEditResponse)
    async def image_gen_fill(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:gen-fill", limit=25, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        mask = _decode_mask_or_raise(payload.mask_data, image.size, "gen-fill")
        prompt = _sanitize_prompt(payload.prompt or "")
        if payload.prompt and prompt is None:
            raise HTTPException(status_code=422, detail="Prompt contains blocked or potentially malicious content.")
        filled = _apply_gen_fill(image, mask, prompt or "")
        return AIImageEditResponse(
            status="success",
            operation="gen-fill",
            image_url=_encode_png_data_url(filled),
            mask_url=_encode_png_data_url(mask.convert("RGB")),
            metadata={"width": image.width, "height": image.height},
        )

    @router.post("/image/upscale", response_model=AIImageEditResponse)
    async def image_upscale(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:upscale", limit=25, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        target_width = payload.target_width or min(4096, image.width * payload.upscale_factor)
        target_height = payload.target_height or min(4096, image.height * payload.upscale_factor)
        upscaled = _resize_and_sharpen(image, target_width, target_height)
        return AIImageEditResponse(
            status="success",
            operation="upscale",
            image_url=_encode_png_data_url(upscaled),
            metadata={"width": upscaled.width, "height": upscaled.height, "upscale_factor": payload.upscale_factor},
        )

    @router.post("/image/neural-filter", response_model=AIImageEditResponse)
    async def image_neural_filter(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:neural-filter", limit=35, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        filtered = _apply_neural_filter(image, payload.filter_name or "clarity")
        return AIImageEditResponse(
            status="success",
            operation="neural-filter",
            image_url=_encode_png_data_url(filtered),
            metadata={"filter_name": (payload.filter_name or "clarity").lower(), "width": image.width, "height": image.height},
        )

    @router.post("/image/harmonize", response_model=AIImageEditResponse)
    async def image_harmonize(
        payload: AIImageEditRequest,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> AIImageEditResponse:
        enforce_rate_limit(f"{auth.tenant_id}:ai:image:harmonize", limit=30, window_seconds=60)
        image = _decode_data_url_image(payload.image_data)
        mask = _decode_optional_mask(payload.mask_data, image.size)
        harmonized, used_mask = _harmonize_image(image, mask)
        return AIImageEditResponse(
            status="success",
            operation="harmonize",
            image_url=_encode_png_data_url(harmonized),
            mask_url=_encode_png_data_url(used_mask.convert("RGB")),
            metadata={"width": harmonized.width, "height": harmonized.height},
        )

    return router


# ─── AI Service Implementations ────────────────────────────────────────────────


async def _check_service(base_url: str) -> dict:
    """Check if an AI service is running."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base_url}/health", follow_redirects=True)
            if response.status_code < 500:
                return {"status": "ok", "code": response.status_code}

            fallback = await client.get(f"{base_url}/", follow_redirects=True)
            return {"status": "ok", "code": fallback.status_code}
    except Exception as e:
        return {"status": "error", "message": f"{type(e).__name__}: {e}"}


def _decode_data_url_image(value: str) -> Any:
    if not _PIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pillow is required for image editing operations.")
    if not isinstance(value, str) or "," not in value:
        raise HTTPException(status_code=422, detail="Expected base64 data URL for image_data.")

    try:
        _, encoded = value.split(",", 1)
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid base64 image payload: {type(exc).__name__}") from exc

    try:
        with Image.open(io.BytesIO(raw)) as opened:
            return opened.convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to decode image payload: {type(exc).__name__}") from exc


def _encode_png_data_url(image: Any) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _decode_optional_mask(mask_data: str | None, image_size: tuple[int, int]) -> Any | None:
    if not mask_data:
        return None
    mask_image = _decode_data_url_image(mask_data).convert("L")
    if mask_image.size != image_size:
        resampling = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
        mask_image = mask_image.resize(image_size, resampling)
    return mask_image


def _decode_mask_or_raise(mask_data: str | None, image_size: tuple[int, int], operation: str) -> Any:
    mask_image = _decode_optional_mask(mask_data, image_size)
    if mask_image is None:
        raise HTTPException(status_code=422, detail=f"{operation} requires mask_data as a base64 image data URL.")
    return mask_image


def _build_subject_mask(image: Any) -> Any:
    gray = ImageOps.autocontrast(image.convert("L"))
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.2))
    centered = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(centered)
    margin_x = max(10, image.width // 8)
    margin_y = max(10, image.height // 8)
    draw.ellipse((margin_x, margin_y, image.width - margin_x, image.height - margin_y), fill=170)
    mixed = ImageChops.screen(edges, centered)
    return mixed.point(lambda px: 255 if px >= 96 else 0).filter(ImageFilter.GaussianBlur(1.0))


def _build_sky_mask(image: Any) -> Any:
    rgb = image.convert("RGB")
    r, g, b = rgb.split()
    blue_bias = ImageChops.subtract(b, ImageChops.add(r, g, scale=2.0))
    color_mask = blue_bias.point(lambda px: 255 if px > 18 else 0)

    top_band = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(top_band)
    draw.rectangle((0, 0, image.width, int(image.height * 0.62)), fill=255)
    return ImageChops.multiply(color_mask, top_band).filter(ImageFilter.GaussianBlur(1.2))


def _resize_and_sharpen(image: Any, target_width: int, target_height: int) -> Any:
    target_width = max(64, min(target_width, 4096))
    target_height = max(64, min(target_height, 4096))
    resampling = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    upscaled = image.resize((target_width, target_height), resampling)
    contrast = ImageEnhance.Contrast(upscaled).enhance(1.05)
    return contrast.filter(ImageFilter.UnsharpMask(radius=1.6, percent=165, threshold=2))


def _apply_gen_fill(image: Any, mask: Any, prompt: str) -> Any:
    blur_radius = 24 if max(image.width, image.height) >= 1200 else 16
    background_fill = image.filter(ImageFilter.GaussianBlur(blur_radius))
    if prompt:
        tint = (sum(ord(ch) for ch in prompt) % 155) + 40
        overlay = Image.new("RGB", image.size, (tint, min(255, tint + 20), min(255, tint + 35)))
        background_fill = Image.blend(background_fill, overlay, 0.14)
    return Image.composite(background_fill, image, mask)


def _apply_neural_filter(image: Any, filter_name: str) -> Any:
    normalized = filter_name.strip().lower() or "clarity"
    if normalized == "cinematic":
        warmed = ImageEnhance.Color(image).enhance(1.15)
        contrast = ImageEnhance.Contrast(warmed).enhance(1.18)
        return contrast.filter(ImageFilter.UnsharpMask(radius=1.2, percent=145, threshold=2))
    if normalized in {"mono", "black-white", "bw"}:
        return ImageOps.colorize(image.convert("L"), black="#151515", white="#f1f1f1").convert("RGB")
    if normalized == "vivid":
        vivid = ImageEnhance.Color(image).enhance(1.34)
        return ImageEnhance.Contrast(vivid).enhance(1.1)
    if normalized in {"soft-glow", "glow"}:
        blur = image.filter(ImageFilter.GaussianBlur(3.0))
        return Image.blend(image, blur, 0.32)

    sharp = image.filter(ImageFilter.UnsharpMask(radius=1.8, percent=180, threshold=2))
    return ImageEnhance.Contrast(sharp).enhance(1.08)


def _harmonize_image(image: Any, mask: Any | None) -> tuple[Any, Any]:
    active_mask = mask or _build_subject_mask(image)
    inverse_mask = ImageOps.invert(active_mask)

    subject = Image.composite(image, Image.new("RGB", image.size, (0, 0, 0)), active_mask)
    background = Image.composite(image, Image.new("RGB", image.size, (0, 0, 0)), inverse_mask)

    subject_mean = ImageStat.Stat(subject).mean
    background_mean = ImageStat.Stat(background).mean
    adjustment = tuple(max(-18.0, min(18.0, (background_mean[idx] - subject_mean[idx]) * 0.22)) for idx in range(3))

    harmonized_subject = Image.merge(
        "RGB",
        [
            channel.point(lambda px, delta=adjustment[idx]: max(0, min(255, int(px + delta))))
            for idx, channel in enumerate(subject.split())
        ],
    )
    merged = Image.composite(harmonized_subject, image, active_mask)
    return merged, active_mask


def _refund_reserved_credits(
    tenant_id: str,
    amount: int,
    reservation_reference: str,
    credit_ledger_memory,
    ledger_lock: threading.Lock,
) -> None:
    with ledger_lock:
        credit_ledger_memory.append(
            {
                "id": len(credit_ledger_memory) + 1,
                "tenant_id": tenant_id,
                "amount": amount,
                "reason": "ai_generation_refund",
                "created_at": datetime.now(UTC).isoformat(),
                "reservation_reference": reservation_reference,
            }
        )


async def _provider_available(provider_name: str, health_cache: dict[str, bool]) -> bool:
    if provider_name in health_cache:
        return health_cache[provider_name]

    if provider_name == "openvoice":
        available = (await _check_service(OPENVOICE_WORKER_URL)).get("status") == "ok"
    elif provider_name == "bark":
        available = (await _check_service(BARK_WORKER_URL)).get("status") == "ok"
    elif provider_name == "ollama":
        available = (await _check_service(OLLAMA_BASE_URL)).get("status") == "ok"
    elif provider_name == "comfyui-sdxl":
        available = (await _check_service(COMFYUI_BASE_URL)).get("status") == "ok"
    elif provider_name == "elevenlabs":
        available = bool(os.getenv("ELEVENLABS_API_KEY", "").strip())
    elif provider_name == "gpt-4.1-mini":
        available = bool(os.getenv("OPENAI_API_KEY", "").strip())
    elif provider_name == "claude-3.5-sonnet":
        available = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    else:
        available = True

    health_cache[provider_name] = available
    return available


async def _filter_available_providers(media_type: str, provider_options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    health_cache: dict[str, bool] = {}
    filtered: list[dict[str, Any]] = []
    for provider in provider_options:
        if await _provider_available(str(provider.get("provider", "")), health_cache):
            filtered.append(provider)

    if filtered:
        return filtered

    raise RuntimeError(
        f"No healthy or configured {media_type} providers are available right now. Restore a provider before starting this workload."
    )


async def _build_social_studio_plan(payload: AIGenerationRequest) -> dict[str, Any]:
    reference_count = len(payload.reference_images) + len(payload.reference_videos) + len(payload.reference_audios)
    prompt = (payload.prompt or "").strip()
    prompt_length = len(prompt)
    requested_complexity = (payload.complexity or "auto").strip().lower()
    capability = (
        (payload.capability or payload.use_case or payload.creative_mode or payload.media_type or "content")
        .strip()
        .lower()
        .replace("_", "-")
    )

    score = 1
    if payload.media_type in {"video", "voice"}:
        score += 2
    if reference_count >= 3:
        score += 1
    if prompt_length >= 240:
        score += 1
    if payload.contains_real_people or payload.return_last_frame:
        score += 1
    if capability in {"ar", "vr", "hologram", "faceless-video", "avatar", "reels", "short-video", "music"}:
        score += 1

    if requested_complexity in {"simple", "standard", "advanced"}:
        complexity = requested_complexity
    elif score <= 2:
        complexity = "simple"
    elif score <= 4:
        complexity = "standard"
    else:
        complexity = "advanced"

    provider_catalog = {
        "image": [
            {"provider": "comfyui-sdxl", "quality": "high", "cost_rank": 1, "supports": ["image", "slides", "template"]},
            {"provider": "flux-pro", "quality": "premium", "cost_rank": 2, "supports": ["image", "avatar", "brand-edit"]},
            {"provider": "imagen-4", "quality": "premium", "cost_rank": 3, "supports": ["image", "product", "campaign"]},
        ],
        "video": [
            {"provider": "seedance-2", "quality": "premium", "cost_rank": 1, "supports": ["reels", "short-video", "faceless-video", "video"]},
            {"provider": "veo-3.1", "quality": "premium", "cost_rank": 2, "supports": ["video", "ar", "vr", "hologram"]},
            {"provider": "runway-gen4", "quality": "high", "cost_rank": 3, "supports": ["video", "edit", "storyboard"]},
        ],
        "voice": [
            {"provider": "openvoice", "quality": "high", "cost_rank": 1, "supports": ["voice", "avatar", "podcast"]},
            {"provider": "bark", "quality": "standard", "cost_rank": 2, "supports": ["voice", "sound"]},
            {"provider": "elevenlabs", "quality": "premium", "cost_rank": 3, "supports": ["voice", "music", "narration"]},
        ],
        "text": [
            {"provider": "ollama", "quality": "high", "cost_rank": 1, "supports": ["blog", "caption", "campaign"]},
            {"provider": "gpt-4.1-mini", "quality": "premium", "cost_rank": 2, "supports": ["strategy", "multimodal-planning"]},
            {"provider": "claude-3.5-sonnet", "quality": "premium", "cost_rank": 3, "supports": ["brand", "editorial", "longform"]},
        ],
    }
    provider_options = await _filter_available_providers(
        payload.media_type,
        provider_catalog.get(payload.media_type, provider_catalog["text"]),
    )
    recommended_provider = provider_options[0]
    if complexity == "advanced" and len(provider_options) > 1:
        recommended_provider = provider_options[1]
    elif capability in {"ar", "vr", "hologram", "music"} and len(provider_options) > 1:
        recommended_provider = provider_options[min(1, len(provider_options) - 1)]

    base_credits = {"image": 22, "video": 48, "voice": 16, "text": 12}.get(payload.media_type, 18)
    complexity_modifier = {"simple": 0, "standard": 8, "advanced": 18}[complexity]
    reference_modifier = min(reference_count * 3, 18)
    premium_modifier = 10 if recommended_provider["quality"] == "premium" else 0
    estimated_credits = base_credits + complexity_modifier + reference_modifier + premium_modifier

    return {
        "capability": capability,
        "media_type": payload.media_type,
        "complexity": complexity,
        "estimated_credits": estimated_credits,
        "recommended_provider": recommended_provider,
        "provider_candidates": provider_options,
        "workflow": [
            "ingest-brief",
            "validate-paid-credits",
            "auto-route-model",
            "generate-core-asset",
            "post-process-and-edit",
            "package-for-channel-delivery",
        ],
        "quality_policy": "Prefer the lowest cost provider that still satisfies the requested complexity and modality.",
        "channel_targets": payload.target_channels,
        "edit_tools": payload.edit_tools,
        "brand_rules": payload.brand_rules,
    }


async def _run_image_job(
    job_id: str,
    payload: AIGenerationRequest,
    tenant_id: str | None = None,
    estimated_credits: int = 0,
    reservation_reference: str = '',
    credit_ledger_memory=None,
    ledger_lock=None,
) -> None:
    """Background task: run ComfyUI image generation and store result in _image_jobs."""
    image_timeout_seconds = max(int(os.getenv("AI_IMAGE_JOB_TIMEOUT_SECONDS", "900")), 300)
    try:
        result = await asyncio.wait_for(_generate_image(payload), timeout=image_timeout_seconds)
        if result.status == "success":
            _image_jobs[job_id] = {
                "status": "success",
                "content": result.content,
                "media_url": result.media_url,
                "estimated_credits": estimated_credits,
                "orchestration_plan": _image_jobs.get(job_id, {}).get("orchestration_plan"),
            }
        else:
            if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
                _refund_reserved_credits(
                    tenant_id,
                    estimated_credits,
                    reservation_reference,
                    credit_ledger_memory,
                    ledger_lock,
                )
            _image_jobs[job_id] = {"status": "error", "error": result.error}
    except TimeoutError:
        if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
        _image_jobs[job_id] = {
            "status": "error",
            "error": f"Image generation timed out after {image_timeout_seconds} seconds.",
        }
    except Exception as exc:
        logger.exception("Background image job failed")
        if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
        _image_jobs[job_id] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


async def _run_text_job(
    job_id: str,
    payload: AIGenerationRequest,
    tenant_id: str | None = None,
    estimated_credits: int = 0,
    reservation_reference: str = '',
    credit_ledger_memory=None,
    ledger_lock=None,
) -> None:
    """Background task: run Ollama text generation and store result in _image_jobs."""
    text_timeout_seconds = max(int(os.getenv("AI_TEXT_JOB_TIMEOUT_SECONDS", "420")), 30)
    try:
        result = await asyncio.wait_for(_generate_text(payload), timeout=text_timeout_seconds)
        if result.status == "success":
            _image_jobs[job_id] = {
                "status": "success",
                "content": result.content,
                "estimated_credits": estimated_credits,
                "orchestration_plan": _image_jobs.get(job_id, {}).get("orchestration_plan"),
            }
        else:
            if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
                _refund_reserved_credits(
                    tenant_id,
                    estimated_credits,
                    reservation_reference,
                    credit_ledger_memory,
                    ledger_lock,
                )
            _image_jobs[job_id] = {"status": "error", "error": result.error}
    except TimeoutError:
        if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
        _image_jobs[job_id] = {
            "status": "error",
            "error": f"Text generation timed out after {text_timeout_seconds} seconds.",
        }
    except Exception as exc:
        logger.exception("Background text job failed")
        if tenant_id and reservation_reference and credit_ledger_memory is not None and ledger_lock is not None:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
        _image_jobs[job_id] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


async def _run_video_job(
    job_id: str,
    payload: AIGenerationRequest,
    tenant_id: str,
    estimated_credits: int,
    reservation_reference: str,
    credit_ledger_memory,
    ledger_lock: threading.Lock,
) -> None:
    """Background task: run video generation and store result."""
    video_timeout_seconds = max(int(os.getenv("AI_VIDEO_JOB_TIMEOUT_SECONDS", "1500")), 120)
    try:
        result = await asyncio.wait_for(_generate_video(payload), timeout=video_timeout_seconds)
        if result.status == "success":
            _image_jobs[job_id] = {
                "status": "success",
                "content": result.content,
                "media_url": result.media_url,
                "estimated_credits": estimated_credits,
                "orchestration_plan": _image_jobs.get(job_id, {}).get("orchestration_plan"),
            }
        else:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
            _image_jobs[job_id] = {"status": "error", "error": result.error}
    except TimeoutError:
        _refund_reserved_credits(
            tenant_id,
            estimated_credits,
            reservation_reference,
            credit_ledger_memory,
            ledger_lock,
        )
        _image_jobs[job_id] = {
            "status": "error",
            "error": f"Video generation timed out after {video_timeout_seconds} seconds.",
        }
    except Exception as exc:
        logger.exception("Background video job failed")
        _refund_reserved_credits(
            tenant_id,
            estimated_credits,
            reservation_reference,
            credit_ledger_memory,
            ledger_lock,
        )
        _image_jobs[job_id] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


async def _run_voice_job(
    job_id: str,
    payload: AIGenerationRequest,
    orchestration_plan: dict[str, Any],
    tenant_id: str,
    estimated_credits: int,
    reservation_reference: str,
    credit_ledger_memory,
    ledger_lock: threading.Lock,
) -> None:
    """Background task: run voice generation and store result."""
    voice_timeout_seconds = max(int(os.getenv("AI_VOICE_JOB_TIMEOUT_SECONDS", "900")), 60)
    try:
        result = await asyncio.wait_for(_generate_voice(payload, orchestration_plan), timeout=voice_timeout_seconds)
        if result.status == "success":
            _image_jobs[job_id] = {
                "status": "success",
                "content": result.content,
                "media_url": result.media_url,
                "estimated_credits": estimated_credits,
                "orchestration_plan": _image_jobs.get(job_id, {}).get("orchestration_plan"),
            }
        else:
            _refund_reserved_credits(
                tenant_id,
                estimated_credits,
                reservation_reference,
                credit_ledger_memory,
                ledger_lock,
            )
            _image_jobs[job_id] = {"status": "error", "error": result.error}
    except TimeoutError:
        _refund_reserved_credits(
            tenant_id,
            estimated_credits,
            reservation_reference,
            credit_ledger_memory,
            ledger_lock,
        )
        _image_jobs[job_id] = {
            "status": "error",
            "error": f"Voice generation timed out after {voice_timeout_seconds} seconds.",
        }
    except Exception as exc:
        logger.exception("Background voice job failed")
        _refund_reserved_credits(
            tenant_id,
            estimated_credits,
            reservation_reference,
            credit_ledger_memory,
            ledger_lock,
        )
        _image_jobs[job_id] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


async def _generate_image(payload: AIGenerationRequest) -> AIGenerationResponse:
    """Generate image using ComfyUI (SDXL, ControlNet, ESRGAN)."""
    checkpoint_name = _resolve_checkpoint_name()
    if checkpoint_name is None:
        return AIGenerationResponse(
            status="error",
            error="No ComfyUI checkpoint found in deploy/ai/models/checkpoints.",
        )

    is_sdxl = "sdxl" in checkpoint_name.lower() or "sd_xl" in checkpoint_name.lower()
    force_4k = os.getenv("AI_IMAGE_FORCE_4K", "true").strip().lower() in {"1", "true", "yes", "on"}
    default_base_size = 768 if is_sdxl else 512
    default_width = 3840 if force_4k else default_base_size
    default_height = 2160 if force_4k else default_base_size
    width = int(os.getenv("AI_IMAGE_WIDTH", str(default_width)))
    height = int(os.getenv("AI_IMAGE_HEIGHT", str(default_height)))
    render_default_width = 1280 if force_4k else width
    render_default_height = 704 if force_4k else height
    render_width = int(os.getenv("AI_IMAGE_RENDER_WIDTH", str(render_default_width)))
    render_height = int(os.getenv("AI_IMAGE_RENDER_HEIGHT", str(render_default_height)))
    steps = int(os.getenv("AI_IMAGE_STEPS", "18"))
    width = max(384, min(width, 4096))
    height = max(384, min(height, 4096))
    render_width = max(384, min(render_width, 2048))
    render_height = max(384, min(render_height, 2048))
    render_width = (render_width // 64) * 64
    render_height = (render_height // 64) * 64
    steps = max(8, min(steps, 30))
    cfg = float(os.getenv("AI_IMAGE_CFG", "7.5"))
    sampler_name = os.getenv("AI_IMAGE_SAMPLER", "dpmpp_2m")
    scheduler = os.getenv("AI_IMAGE_SCHEDULER", "karras")

    style_hint = f", style: {payload.style}" if payload.style else ""
    description_hint = f", details: {payload.prompt_description}" if payload.prompt_description else ""
    mode_hint = f", mode: {payload.creative_mode}" if payload.creative_mode else ""
    ratio_hint = f", aspect ratio: {payload.aspect_ratio}" if payload.aspect_ratio else ""
    resolution_hint = f", output resolution: {payload.resolution}" if payload.resolution else ""
    people_hint = ", realistic human features" if payload.contains_real_people else ""
    positive_prompt = (
        f"{payload.prompt}{description_hint}{style_hint}{mode_hint}{ratio_hint}{resolution_hint}{people_hint}, "
        "high quality, highly detailed"
    )
    negative_prompt = (
        "blurry, distorted, low quality, artifacts, jpeg artifacts, bad anatomy, "
        "deformed, extra limbs, out of frame, low contrast"
    )
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint_name,
            },
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": positive_prompt,
                "clip": ["1", 1],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": render_width,
                "height": render_height,
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(payload.seed) if payload.seed else secrets.randbits(32),
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "nuxtron_social_studio",
                "images": ["6", 0],
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            queue_response: httpx.Response | None = None
            queue_error: Exception | None = None
            for _ in range(5):
                try:
                    queue_response = await client.post(
                        f"{COMFYUI_BASE_URL}/prompt",
                        json={
                            "client_id": "nuxtron-fastapi",
                            "prompt": workflow,
                        },
                        timeout=45,
                    )
                    break
                except (httpx.TimeoutException, httpx.ReadError, httpx.ConnectError) as exc:
                    queue_error = exc
                    await asyncio.sleep(2)

            if queue_response is None:
                return AIGenerationResponse(
                    status="error",
                    error=(
                        "ComfyUI is currently overloaded/unreachable for image jobs "
                        f"({type(queue_error).__name__ if queue_error else 'UnknownError'}). "
                        "On CPU with SDXL this can happen frequently; retry or use GPU mode."
                    ),
                )

            if queue_response.status_code != 200:
                return AIGenerationResponse(
                    status="error",
                    error=f"ComfyUI queue error: {queue_response.text}",
                )

            prompt_id = queue_response.json().get("prompt_id")
            if not isinstance(prompt_id, str) or not prompt_id:
                return AIGenerationResponse(status="error", error="ComfyUI did not return a prompt_id.")

            image_meta, wait_error = await _wait_for_comfyui_image(client, prompt_id)
            if wait_error:
                return AIGenerationResponse(status="error", error=wait_error)
            if image_meta is None:
                return AIGenerationResponse(
                    status="error",
                    error="ComfyUI finished without image output. Check workflow/models.",
                )

            view_response = await client.get(
                f"{COMFYUI_BASE_URL}/view",
                params={
                    "filename": image_meta["filename"],
                    "subfolder": image_meta["subfolder"],
                    "type": image_meta["type"],
                },
                timeout=300,
            )
            if view_response.status_code != 200:
                return AIGenerationResponse(
                    status="error",
                    error=f"ComfyUI image fetch failed: {view_response.text}",
                )

            final_bytes = view_response.content
            mime = view_response.headers.get("content-type", "image/png")
            if force_4k:
                processed = _upscale_and_sharpen_image(final_bytes, width, height)
                if processed is not None:
                    final_bytes, mime = processed

            encoded = base64.b64encode(final_bytes).decode("ascii")
            return AIGenerationResponse(
                status="success",
                content=f"Generated image from: {payload.prompt}",
                media_url=f"data:{mime};base64,{encoded}",
            )
    except Exception as exc:
        logger.exception("Image generation failed")
        return AIGenerationResponse(status="error", error=f"Image generation failed: {type(exc).__name__}: {exc}")


def _resolve_checkpoint_name() -> str | None:
    checkpoints_dir = Path("deploy/ai/models/checkpoints")
    if not checkpoints_dir.exists():
        return None

    candidates = sorted(
        [p.name for p in checkpoints_dir.iterdir() if p.is_file() and p.suffix.lower() in {".safetensors", ".ckpt", ".pt"}]
    )
    if not candidates:
        return None

    preferred = [name for name in candidates if "sd_xl_base" in name.lower() or "sdxl" in name.lower()]
    return preferred[0] if preferred else candidates[0]


def _upscale_and_sharpen_image(image_bytes: bytes, target_width: int, target_height: int) -> tuple[bytes, str] | None:
    if not _PIL_AVAILABLE:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            rgb = source.convert("RGB")
            resampling = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
            upscaled = rgb.resize((target_width, target_height), resampling)
            contrast = ImageEnhance.Contrast(upscaled).enhance(1.06)
            sharpened = contrast.filter(ImageFilter.UnsharpMask(radius=1.8, percent=165, threshold=2))

            output = io.BytesIO()
            sharpened.save(output, format="PNG", optimize=True, compress_level=6)
            return output.getvalue(), "image/png"
    except Exception:
        logger.exception("4K upscaling/sharpening failed")
        return None


async def _wait_for_comfyui_image(
    client: httpx.AsyncClient,
    prompt_id: str,
) -> tuple[dict[str, str] | None, str | None]:
    max_wait_seconds = max(int(os.getenv("AI_IMAGE_MAX_WAIT_SECONDS", "840")), 300)
    max_polls = max_wait_seconds
    transient_errors = 0
    for _ in range(max_polls):
        try:
            history_response = await client.get(f"{COMFYUI_BASE_URL}/history/{prompt_id}", timeout=60)
        except (httpx.TimeoutException, httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError):
            transient_errors += 1
            if transient_errors > 30:
                return None, "ComfyUI history endpoint was unreachable for too long."
            await asyncio.sleep(1)
            continue
        if history_response.status_code == 200:
            history = history_response.json()
            outputs = None
            status_payload = None
            if isinstance(history, dict):
                direct_outputs = history.get("outputs")
                if isinstance(direct_outputs, dict):
                    outputs = direct_outputs
                direct_status = history.get("status")
                if isinstance(direct_status, dict):
                    status_payload = direct_status
                else:
                    prompt_entry = history.get(prompt_id)
                    if isinstance(prompt_entry, dict):
                        prompt_outputs = prompt_entry.get("outputs")
                        if isinstance(prompt_outputs, dict):
                            outputs = prompt_outputs
                        prompt_status = prompt_entry.get("status")
                        if isinstance(prompt_status, dict):
                            status_payload = prompt_status

            if isinstance(status_payload, dict):
                status_text = str(status_payload.get("status_str", "")).lower()
                if status_text in {"error", "failed"}:
                    return None, f"ComfyUI generation failed for prompt {prompt_id}."

                messages = status_payload.get("messages")
                if isinstance(messages, list):
                    for message in messages:
                        if isinstance(message, list) and len(message) > 1:
                            body = message[1]
                            if isinstance(body, dict):
                                message_type = str(body.get("message", "")).lower()
                                if message_type in {"execution_error", "execution_interrupted", "execution_failed"}:
                                    detail = body.get("exception_message") or body.get("error") or "Execution error"
                                    return None, f"ComfyUI execution failed: {detail}"
            if isinstance(outputs, dict):
                for node_data in outputs.values():
                    if isinstance(node_data, dict):
                        images = node_data.get("images")
                        if isinstance(images, list) and images:
                            first = images[0]
                            if isinstance(first, dict):
                                filename = str(first.get("filename", ""))
                                subfolder = str(first.get("subfolder", ""))
                                file_type = str(first.get("type", "output"))
                                if filename:
                                    return {
                                        "filename": filename,
                                        "subfolder": subfolder,
                                        "type": file_type,
                                    }, None
        await asyncio.sleep(1)

    return None, f"ComfyUI did not produce an image within {max_wait_seconds} seconds."


def _sanitize_prompt(value: str) -> str | None:
    """Normalize and block clearly malicious prompt payloads before forwarding to AI services."""
    normalized = " ".join(value.replace("\x00", " ").split())
    if not normalized:
        return None

    lowered = normalized.lower()
    for pattern in _SUSPICIOUS_PROMPT_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return None
    return normalized


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name.strip())
    return safe[:180] or "upload.bin"


async def _persist_reference_uploads(
    tenant_id: str,
    bucket_name: str,
    files: list[UploadFile],
    allowed_exts: set[str],
    max_count: int,
) -> tuple[list[str], str | None]:
    selected = files[:max_count]
    if len(files) > max_count:
        return [], f"{bucket_name} exceeds max count of {max_count}."

    _MEDIA_UPLOAD_BASE.mkdir(parents=True, exist_ok=True)
    request_dir = _MEDIA_UPLOAD_BASE / tenant_id / uuid.uuid4().hex
    request_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for upload in selected:
        original_name = upload.filename or "upload.bin"
        ext = Path(original_name).suffix.lower()
        if ext not in allowed_exts:
            return [], f"Unsupported file extension for {bucket_name}: {ext or 'unknown'}"

        target = request_dir / _sanitize_filename(original_name)
        content = await upload.read()
        target.write_bytes(content)
        saved_paths.append(str(target.as_posix()))

    return saved_paths, None


async def _parse_generation_request(request: Request, tenant_id: str) -> tuple[AIGenerationRequest | None, str | None]:
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" not in content_type:
        try:
            raw = await request.json()
            payload = AIGenerationRequest.model_validate(raw)
            return payload, None
        except Exception as exc:
            return None, f"Invalid JSON payload: {type(exc).__name__}: {exc}"

    try:
        form = await request.form()
        image_uploads = [item for item in form.getlist("reference_images") if isinstance(item, UploadFile)]
        video_uploads = [item for item in form.getlist("reference_videos") if isinstance(item, UploadFile)]
        audio_uploads = [item for item in form.getlist("reference_audios") if isinstance(item, UploadFile)]

        image_paths, image_error = await _persist_reference_uploads(
            tenant_id,
            "reference_images",
            image_uploads,
            _ALLOWED_IMAGE_EXTENSIONS,
            9,
        )
        if image_error:
            return None, image_error

        video_paths, video_error = await _persist_reference_uploads(
            tenant_id,
            "reference_videos",
            video_uploads,
            _ALLOWED_VIDEO_EXTENSIONS,
            3,
        )
        if video_error:
            return None, video_error

        audio_paths, audio_error = await _persist_reference_uploads(
            tenant_id,
            "reference_audios",
            audio_uploads,
            _ALLOWED_AUDIO_EXTENSIONS,
            3,
        )
        if audio_error:
            return None, audio_error

        portrait_library_raw = str(form.get("portrait_library") or "{}").strip()
        try:
            portrait_library = json.loads(portrait_library_raw) if portrait_library_raw else {}
        except json.JSONDecodeError:
            portrait_library = {}

        payload = AIGenerationRequest(
            prompt=str(form.get("prompt") or "").strip(),
            media_type=str(form.get("media_type") or "image").strip().lower(),
            model=str(form.get("model") or "").strip(),
            style=str(form.get("style") or "").strip() or None,
            temperature=float(form.get("temperature") or 0.7),
            creative_mode=str(form.get("creative_mode") or "").strip() or None,
            prompt_description=str(form.get("prompt_description") or "").strip() or None,
            aspect_ratio=str(form.get("aspect_ratio") or "").strip() or None,
            resolution=str(form.get("resolution") or "").strip() or None,
            contains_real_people=_as_bool(form.get("contains_real_people")),
            return_last_frame=_as_bool(form.get("return_last_frame")),
            seed_enabled=_as_bool(form.get("seed_enabled")),
            seed=str(form.get("seed") or "").strip() or None,
            reference_images=image_paths,
            reference_videos=video_paths,
            reference_audios=audio_paths,
            portrait_library=portrait_library if isinstance(portrait_library, dict) else {},
            capability=str(form.get("capability") or "").strip() or None,
            delivery_mode=str(form.get("delivery_mode") or "").strip() or None,
            orchestration_goal=str(form.get("orchestration_goal") or "").strip() or None,
            complexity=str(form.get("complexity") or "auto").strip() or None,
            auto_route=_as_bool(form.get("auto_route")),
            use_case=str(form.get("use_case") or "").strip() or None,
            target_channels=[str(value).strip() for value in form.getlist("target_channels") if str(value).strip()],
            candidate_models=[str(value).strip() for value in form.getlist("candidate_models") if str(value).strip()],
            edit_tools=[str(value).strip() for value in form.getlist("edit_tools") if str(value).strip()],
            brand_rules=[str(value).strip() for value in form.getlist("brand_rules") if str(value).strip()],
        )
        return payload, None
    except Exception as exc:
        return None, f"Invalid multipart payload: {type(exc).__name__}: {exc}"


def _compose_generation_prompt(payload: AIGenerationRequest) -> str:
    parts = [payload.prompt]

    if payload.prompt_description:
        parts.append(f"Details: {payload.prompt_description}")
    if payload.creative_mode:
        parts.append(f"Mode: {payload.creative_mode}")
    if payload.aspect_ratio:
        parts.append(f"Aspect ratio: {payload.aspect_ratio}")
    if payload.resolution:
        parts.append(f"Resolution: {payload.resolution}")
    if payload.contains_real_people:
        parts.append("Contains real people")
    if payload.return_last_frame:
        parts.append("Return last frame enabled")
    if payload.reference_images:
        parts.append(f"Reference images: {', '.join(payload.reference_images)}")
    if payload.reference_videos:
        parts.append(f"Reference videos: {', '.join(payload.reference_videos)}")
    if payload.reference_audios:
        parts.append(f"Reference audios: {', '.join(payload.reference_audios)}")
    if payload.capability:
        parts.append(f"Capability: {payload.capability}")
    if payload.delivery_mode:
        parts.append(f"Delivery mode: {payload.delivery_mode}")
    if payload.target_channels:
        parts.append(f"Target channels: {', '.join(payload.target_channels)}")
    if payload.edit_tools:
        parts.append(f"Edit tools: {', '.join(payload.edit_tools)}")
    if payload.brand_rules:
        parts.append(f"Brand rules: {', '.join(payload.brand_rules)}")

    return " | ".join(parts)


async def _generate_video(payload: AIGenerationRequest) -> AIGenerationResponse:
    """Generate video using ComfyUI (SVD, FILM interpolation)."""
    try:
        resolved_prompt = _compose_generation_prompt(payload)
        # Placeholder: would integrate with ComfyUI video nodes
        return AIGenerationResponse(
            status="success",
            content=f"Generated video from: {resolved_prompt}",
            media_url=f"data:video/mp4;base64,{await _placeholder_video()}",
        )
    except Exception as e:
        return AIGenerationResponse(
            status="error",
            error=f"Video generation failed: {str(e)}",
        )


async def _generate_voice(payload: AIGenerationRequest, orchestration_plan: dict[str, Any] | None = None) -> AIGenerationResponse:
    """Generate voice using the routed provider order."""
    resolved_prompt = _compose_generation_prompt(payload)
    provider_order: list[str] = []
    if orchestration_plan:
        recommended = orchestration_plan.get("recommended_provider", {}).get("provider")
        if isinstance(recommended, str) and recommended:
            provider_order.append(recommended)
        for candidate in orchestration_plan.get("provider_candidates", []):
            provider_name = str(candidate.get("provider", "")).strip()
            if provider_name and provider_name not in provider_order:
                provider_order.append(provider_name)
    if not provider_order:
        provider_order = ["openvoice", "bark", "elevenlabs"]

    errors: list[str] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for provider_name in provider_order:
            try:
                if provider_name == "openvoice":
                    response = await client.post(
                        f"{OPENVOICE_WORKER_URL}/v1/tts",
                        json={"text": resolved_prompt, "model": "default"},
                    )
                    if response.status_code == 200 and response.content:
                        return AIGenerationResponse(
                            status="success",
                            content=f"Generated voice with openvoice for: {resolved_prompt}",
                            media_url=f"data:audio/wav;base64,{base64.b64encode(response.content).decode()}",
                        )
                    errors.append(f"openvoice:{response.status_code}")
                elif provider_name == "bark":
                    response = await client.post(
                        f"{BARK_WORKER_URL}/v1/tts",
                        json={"text": resolved_prompt, "model": "default"},
                    )
                    if response.status_code == 200 and response.content:
                        return AIGenerationResponse(
                            status="success",
                            content=f"Generated voice with bark for: {resolved_prompt}",
                            media_url=f"data:audio/wav;base64,{base64.b64encode(response.content).decode()}",
                        )
                    errors.append(f"bark:{response.status_code}")
                elif provider_name == "elevenlabs":
                    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
                    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip() or "EXAVITQu4vr4xnSDxMaL"
                    if not api_key:
                        errors.append("elevenlabs:not_configured")
                        continue
                    response = await client.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        headers={"xi-api-key": api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
                        json={
                            "text": resolved_prompt,
                            "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip() or "eleven_multilingual_v2",
                            "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
                        },
                    )
                    if response.status_code == 200 and response.content:
                        return AIGenerationResponse(
                            status="success",
                            content=f"Generated voice with elevenlabs for: {resolved_prompt}",
                            media_url=f"data:audio/mpeg;base64,{base64.b64encode(response.content).decode()}",
                        )
                    errors.append(f"elevenlabs:{response.status_code}")
            except Exception as exc:
                errors.append(f"{provider_name}:{type(exc).__name__}")

    return AIGenerationResponse(
        status="error",
        error="Voice generation failed: no routed voice provider responded successfully.",
    )


async def _generate_text(payload: AIGenerationRequest) -> AIGenerationResponse:
    """Generate copy text using Ollama (LLM) — uses streaming to avoid blocking timeouts."""
    import json as _json

    try:
        model_candidates = [
            payload.model,
            *payload.candidate_models,
            os.getenv("OLLAMA_DEFAULT_MODEL", "").strip(),
            "deepseek-r1:8b",
            "llama3.2:3b",
            "llama3.2",
            "llama3",
            "mistral:7b",
        ]
        installed_models: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    payload_json = response.json()
                    installed_models = [
                        str(item.get("name", "")).strip()
                        for item in payload_json.get("models", [])
                        if str(item.get("name", "")).strip()
                    ]
        except Exception:
            installed_models = []

        model = ""
        seen_models: set[str] = set()
        for candidate in model_candidates:
            normalized_candidate = str(candidate or "").strip()
            if not normalized_candidate or normalized_candidate in seen_models:
                continue
            seen_models.add(normalized_candidate)
            if installed_models and normalized_candidate not in installed_models:
                continue
            model = normalized_candidate
            break

        if not model:
            model = installed_models[0] if installed_models else "deepseek-r1:8b"

        resolved_prompt = _compose_generation_prompt(payload)
        # Use unlimited read timeout because CPU-only model loading/generation can exceed 10 minutes.
        timeout = httpx.Timeout(connect=30.0, read=None, write=60.0, pool=60.0)
        last_error: Exception | None = None

        for attempt in range(3):
            tokens: list[str] = []
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": model,
                            "prompt": resolved_prompt,
                            "stream": True,
                            "keep_alive": "30m",
                        },
                    ) as response:
                        if response.status_code != 200:
                            text = await response.aread()
                            raise Exception(f"Ollama error {response.status_code}: {text.decode()}")

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = _json.loads(line)
                            except _json.JSONDecodeError:
                                continue

                            tokens.append(chunk.get("response", ""))
                            if chunk.get("done"):
                                break

                generated_text = "".join(tokens).strip()
                if generated_text:
                    return AIGenerationResponse(status="success", content=generated_text)

                raise Exception("Ollama returned an empty response")
            except (httpx.TimeoutException, httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                break
            except Exception as exc:
                last_error = exc
                break

        raise Exception(f"{type(last_error).__name__}: {last_error}" if last_error else "Unknown Ollama error")

    except Exception as e:
        return AIGenerationResponse(
            status="error",
            error=f"Text generation failed: {type(e).__name__}: {e}",
        )


async def _placeholder_video() -> str:
    """Generate a simple placeholder video in base64."""
    # Minimal MP4 header (not a valid video, just a placeholder)
    return "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAACKmtYXBsAAACAGZyZWU="
