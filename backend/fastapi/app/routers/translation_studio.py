from __future__ import annotations

import asyncio
import base64
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

BASELINE_LANGUAGES = [
    {"language": "EN", "name": "English", "supports_formality": False},
    {"language": "DE", "name": "German", "supports_formality": True},
    {"language": "FR", "name": "French", "supports_formality": True},
    {"language": "ES", "name": "Spanish", "supports_formality": True},
    {"language": "IT", "name": "Italian", "supports_formality": True},
    {"language": "PT", "name": "Portuguese", "supports_formality": True},
    {"language": "NL", "name": "Dutch", "supports_formality": True},
    {"language": "PL", "name": "Polish", "supports_formality": True},
    {"language": "JA", "name": "Japanese", "supports_formality": True},
    {"language": "RU", "name": "Russian", "supports_formality": True},
    {"language": "ZH", "name": "Chinese", "supports_formality": False},
]


class TranslationRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=50)
    target_lang: str = Field(min_length=2, max_length=16)
    source_lang: str | None = Field(default=None, max_length=16)
    context: str | None = Field(default=None, max_length=20_000)
    formality: str | None = Field(default=None, max_length=20)
    preserve_formatting: bool = False
    model_type: str | None = Field(default=None, max_length=40)
    split_sentences: str | None = Field(default=None, max_length=32)
    tag_handling: str | None = Field(default=None, max_length=16)
    tag_handling_version: str | None = Field(default=None, max_length=16)
    outline_detection: bool | None = None
    non_splitting_tags: list[str] | None = None
    splitting_tags: list[str] | None = None
    ignore_tags: list[str] | None = None
    style_id: str | None = Field(default=None, max_length=120)
    custom_instructions: list[str] | None = None
    translation_memory_id: str | None = Field(default=None, max_length=120)
    translation_memory_threshold: int | None = Field(default=None, ge=0, le=100)
    glossary_id: str | None = None
    provider: str = Field(default="auto", max_length=20)


class GlossaryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    source_lang: str = Field(min_length=2, max_length=16)
    target_lang: str = Field(min_length=2, max_length=16)
    entries: dict[str, str] = Field(default_factory=dict)
    deepl_glossary_id: str | None = None


class GlossaryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    entries: dict[str, str] | None = None
    deepl_glossary_id: str | None = None


class TranslationMemoryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    source_lang: str = Field(min_length=2, max_length=16)
    target_lang: str = Field(min_length=2, max_length=16)
    description: str | None = Field(default=None, max_length=500)
    deepl_translation_memory_id: str | None = Field(default=None, max_length=120)


class TranslationMemoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    source_lang: str | None = Field(default=None, min_length=2, max_length=16)
    target_lang: str | None = Field(default=None, min_length=2, max_length=16)
    description: str | None = Field(default=None, max_length=500)
    deepl_translation_memory_id: str | None = Field(default=None, max_length=120)


def _normalize_lang(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned or None


def _resolve_deepl_base_url() -> str:
    return (os.getenv("DEEPL_API_URL", "https://api.deepl.com/v2").strip() or "https://api.deepl.com/v2").rstrip("/")


def _build_provider_status() -> dict[str, bool]:
    return {
        "deepl": bool(os.getenv("DEEPL_API_KEY", "").strip()),
    }


def _require_deepl_key() -> str:
    key = os.getenv("DEEPL_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="DEEPL_API_KEY is not configured. Translation endpoints only run against real vendors.",
        )
    return key


def _clean_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [item.strip() for item in values if item.strip()]
    return cleaned or None


def create_translation_studio_router() -> APIRouter:
    router = APIRouter(prefix="/translations", tags=["translations"])
    glossaries: list[dict[str, Any]] = []
    translation_memories: list[dict[str, Any]] = []
    usage_events: list[dict[str, Any]] = []

    def resolve_glossary(glossary_id: str | None) -> dict[str, Any] | None:
        if not glossary_id:
            return None
        for item in glossaries:
            if item["id"] == glossary_id:
                return item
        return None

    def resolve_translation_memory(memory_id: str | None) -> dict[str, Any] | None:
        if not memory_id:
            return None
        for item in translation_memories:
            if item["id"] == memory_id:
                return item
            if item.get("deepl_translation_memory_id") == memory_id:
                return item
        return None

    async def deepl_translate(payload: TranslationRequest) -> dict[str, Any]:
        api_key = _require_deepl_key()
        glossary = resolve_glossary(payload.glossary_id)
        translation_memory = resolve_translation_memory(payload.translation_memory_id)

        normalized_model_type = (payload.model_type or "").strip().lower() or None
        has_quality_optimized_feature = bool(
            payload.style_id
            or (payload.custom_instructions and len(payload.custom_instructions) > 0)
            or payload.translation_memory_id
        )
        if normalized_model_type == "latency_optimized" and has_quality_optimized_feature:
            raise HTTPException(
                status_code=400,
                detail="style_id, custom_instructions, and translation_memory_id require quality-optimized model behavior",
            )

        custom_instructions = _clean_list(payload.custom_instructions)
        if custom_instructions and len(custom_instructions) > 10:
            raise HTTPException(status_code=400, detail="custom_instructions supports up to 10 instructions")
        if custom_instructions and any(len(item) > 300 for item in custom_instructions):
            raise HTTPException(status_code=400, detail="Each custom instruction supports up to 300 characters")

        non_splitting_tags = _clean_list(payload.non_splitting_tags)
        splitting_tags = _clean_list(payload.splitting_tags)
        ignore_tags = _clean_list(payload.ignore_tags)

        request_payload: dict[str, Any] = {
            "text": payload.texts,
            "target_lang": _normalize_lang(payload.target_lang),
            "show_billed_characters": True,
            "preserve_formatting": payload.preserve_formatting,
        }
        if payload.source_lang:
            request_payload["source_lang"] = _normalize_lang(payload.source_lang)
        if payload.context:
            request_payload["context"] = payload.context
        if payload.formality:
            request_payload["formality"] = payload.formality
        if normalized_model_type:
            request_payload["model_type"] = normalized_model_type
        if payload.split_sentences:
            request_payload["split_sentences"] = payload.split_sentences.strip()
        if payload.tag_handling:
            request_payload["tag_handling"] = payload.tag_handling.strip()
        if payload.tag_handling_version:
            request_payload["tag_handling_version"] = payload.tag_handling_version.strip()
        if payload.outline_detection is not None:
            request_payload["outline_detection"] = payload.outline_detection
        if non_splitting_tags:
            request_payload["non_splitting_tags"] = non_splitting_tags
        if splitting_tags:
            request_payload["splitting_tags"] = splitting_tags
        if ignore_tags:
            request_payload["ignore_tags"] = ignore_tags
        if payload.style_id:
            request_payload["style_id"] = payload.style_id.strip()
        if custom_instructions:
            request_payload["custom_instructions"] = custom_instructions
        if payload.translation_memory_id:
            if translation_memory and translation_memory.get("deepl_translation_memory_id"):
                request_payload["translation_memory_id"] = str(translation_memory["deepl_translation_memory_id"])
            else:
                request_payload["translation_memory_id"] = payload.translation_memory_id.strip()
        if payload.translation_memory_threshold is not None:
            request_payload["translation_memory_threshold"] = payload.translation_memory_threshold
        if glossary and glossary.get("deepl_glossary_id"):
            request_payload["glossary_id"] = glossary["deepl_glossary_id"]

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{_resolve_deepl_base_url()}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                json=request_payload,
            )
        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code >= 400:
            detail = response.text.strip() or "DeepL translation request failed"
            raise HTTPException(status_code=response.status_code, detail=detail)

        data = response.json()
        translations = data.get("translations") or []
        usage_events.append(
            {
                "id": str(uuid.uuid4()),
                "type": "text_translation",
                "provider": "deepl",
                "created_at": datetime.now(UTC).isoformat(),
                "latency_ms": latency_ms,
                "input_count": len(payload.texts),
                "billed_characters": int(data.get("billed_characters") or 0),
            }
        )

        return {
            "provider_used": "deepl",
            "latency_ms": latency_ms,
            "translations": translations,
            "billed_characters": int(data.get("billed_characters") or 0),
            "model_type_used": data.get("model_type_used"),
        }

    async def deepl_supported_languages() -> dict[str, Any]:
        api_key = os.getenv("DEEPL_API_KEY", "").strip()
        if not api_key:
            return {
                "provider": "baseline",
                "source": BASELINE_LANGUAGES,
                "target": BASELINE_LANGUAGES,
                "note": "Configured vendor keys not found. Showing baseline language catalog only.",
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            source_res = await client.get(
                f"{_resolve_deepl_base_url()}/languages",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                params={"type": "source"},
            )
            target_res = await client.get(
                f"{_resolve_deepl_base_url()}/languages",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                params={"type": "target"},
            )

        if source_res.status_code >= 400:
            raise HTTPException(status_code=source_res.status_code, detail=source_res.text.strip() or "DeepL languages(source) failed")
        if target_res.status_code >= 400:
            raise HTTPException(status_code=target_res.status_code, detail=target_res.text.strip() or "DeepL languages(target) failed")

        source_data = source_res.json()
        target_data = target_res.json()
        target_map = {item.get("language"): item for item in target_data if isinstance(item, dict)}

        normalized_source: list[dict[str, Any]] = []
        for item in source_data:
            if not isinstance(item, dict):
                continue
            code = str(item.get("language") or "").strip().upper()
            if not code:
                continue
            normalized_source.append(
                {
                    "language": code,
                    "name": str(item.get("name") or code),
                    "supports_formality": bool(target_map.get(code, {}).get("supports_formality", False)),
                }
            )

        normalized_target: list[dict[str, Any]] = []
        for item in target_data:
            if not isinstance(item, dict):
                continue
            code = str(item.get("language") or "").strip().upper()
            if not code:
                continue
            normalized_target.append(
                {
                    "language": code,
                    "name": str(item.get("name") or code),
                    "supports_formality": bool(item.get("supports_formality", False)),
                }
            )

        return {
            "provider": "deepl",
            "source": normalized_source,
            "target": normalized_target,
        }

    @router.get("/health")
    async def translation_health() -> dict[str, Any]:
        providers = _build_provider_status()
        return {
            "status": "ok" if providers["deepl"] else "degraded",
            "providers": providers,
            "glossaries": len(glossaries),
            "translation_memories": len(translation_memories),
            "usage_events": len(usage_events),
        }

    @router.get("/vendors")
    async def translation_vendors() -> dict[str, Any]:
        providers = _build_provider_status()
        return {
            "active_provider": "deepl" if providers["deepl"] else None,
            "vendors": [
                {
                    "id": "deepl",
                    "configured": providers["deepl"],
                    "capabilities": [
                        "text translation",
                        "auto language detection",
                        "formality",
                        "model_type control",
                        "style_id passthrough",
                        "custom_instructions passthrough",
                        "translation_memory passthrough",
                        "xml/html tag handling controls",
                        "document translation",
                        "glossary passthrough",
                        "language metadata",
                        "billed characters",
                    ],
                    "env_keys": ["DEEPL_API_KEY", "DEEPL_API_URL"],
                }
            ],
        }

    @router.get("/languages")
    async def list_languages() -> dict[str, Any]:
        return await deepl_supported_languages()

    @router.post("/text")
    async def translate_text(payload: TranslationRequest) -> dict[str, Any]:
        provider = payload.provider.strip().lower()
        if provider not in {"auto", "deepl"}:
            raise HTTPException(status_code=400, detail="Unsupported provider. Allowed values: auto, deepl")

        if sum(len(item) for item in payload.texts) > 120_000:
            raise HTTPException(status_code=413, detail="Input text too large for a single request")

        return await deepl_translate(payload)

    @router.get("/glossaries")
    async def list_glossaries() -> dict[str, Any]:
        return {"items": glossaries, "total": len(glossaries)}

    @router.post("/glossaries")
    async def create_glossary(payload: GlossaryCreateRequest) -> dict[str, Any]:
        glossary = {
            "id": str(uuid.uuid4()),
            "name": payload.name.strip(),
            "source_lang": _normalize_lang(payload.source_lang),
            "target_lang": _normalize_lang(payload.target_lang),
            "entries": {k.strip(): v.strip() for k, v in payload.entries.items() if k.strip() and v.strip()},
            "deepl_glossary_id": payload.deepl_glossary_id.strip() if payload.deepl_glossary_id else None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        glossaries.append(glossary)
        return glossary

    @router.patch("/glossaries/{glossary_id}")
    async def update_glossary(glossary_id: str, payload: GlossaryUpdateRequest) -> dict[str, Any]:
        glossary = resolve_glossary(glossary_id)
        if not glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")

        if payload.name is not None:
            glossary["name"] = payload.name.strip()
        if payload.entries is not None:
            glossary["entries"] = {
                k.strip(): v.strip()
                for k, v in payload.entries.items()
                if k.strip() and v.strip()
            }
        if payload.deepl_glossary_id is not None:
            glossary["deepl_glossary_id"] = payload.deepl_glossary_id.strip() or None

        glossary["updated_at"] = datetime.now(UTC).isoformat()
        return glossary

    @router.delete("/glossaries/{glossary_id}")
    async def delete_glossary(glossary_id: str) -> dict[str, Any]:
        for index, item in enumerate(glossaries):
            if item["id"] == glossary_id:
                glossaries.pop(index)
                return {"deleted": True, "id": glossary_id}
        raise HTTPException(status_code=404, detail="Glossary not found")

    @router.get("/translation-memories")
    async def list_translation_memories() -> dict[str, Any]:
        return {"items": translation_memories, "total": len(translation_memories)}

    @router.post("/translation-memories")
    async def create_translation_memory(payload: TranslationMemoryCreateRequest) -> dict[str, Any]:
        memory = {
            "id": str(uuid.uuid4()),
            "name": payload.name.strip(),
            "source_lang": _normalize_lang(payload.source_lang),
            "target_lang": _normalize_lang(payload.target_lang),
            "description": payload.description.strip() if payload.description else None,
            "deepl_translation_memory_id": payload.deepl_translation_memory_id.strip()
            if payload.deepl_translation_memory_id
            else None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        translation_memories.append(memory)
        return memory

    @router.patch("/translation-memories/{memory_id}")
    async def update_translation_memory(memory_id: str, payload: TranslationMemoryUpdateRequest) -> dict[str, Any]:
        memory = resolve_translation_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Translation memory not found")

        if payload.name is not None:
            memory["name"] = payload.name.strip()
        if payload.source_lang is not None:
            memory["source_lang"] = _normalize_lang(payload.source_lang)
        if payload.target_lang is not None:
            memory["target_lang"] = _normalize_lang(payload.target_lang)
        if payload.description is not None:
            memory["description"] = payload.description.strip() if payload.description.strip() else None
        if payload.deepl_translation_memory_id is not None:
            memory["deepl_translation_memory_id"] = (
                payload.deepl_translation_memory_id.strip() or None
            )

        memory["updated_at"] = datetime.now(UTC).isoformat()
        return memory

    @router.delete("/translation-memories/{memory_id}")
    async def delete_translation_memory(memory_id: str) -> dict[str, Any]:
        for index, item in enumerate(translation_memories):
            if item["id"] == memory_id:
                translation_memories.pop(index)
                return {"deleted": True, "id": memory_id}
        raise HTTPException(status_code=404, detail="Translation memory not found")

    @router.get("/usage")
    async def translation_usage(limit: int = 50) -> dict[str, Any]:
        safe_limit = max(1, min(limit, 200))
        items = list(reversed(usage_events))[:safe_limit]
        return {
            "items": items,
            "total": len(usage_events),
            "summary": {
                "text_translations": sum(1 for item in usage_events if item.get("type") == "text_translation"),
                "document_translations": sum(1 for item in usage_events if item.get("type") == "document_translation"),
                "billed_characters": sum(int(item.get("billed_characters") or 0) for item in usage_events),
            },
        }

    @router.post("/documents")
    async def translate_document(
        file: UploadFile = File(...),
        target_lang: str = Form(...),
        source_lang: str | None = Form(default=None),
        formality: str | None = Form(default=None),
        glossary_id: str | None = Form(default=None),
    ) -> dict[str, Any]:
        api_key = _require_deepl_key()
        glossary = resolve_glossary(glossary_id)

        file_name = (file.filename or "document.bin").strip() or "document.bin"
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        upload_payload: dict[str, Any] = {
            "target_lang": _normalize_lang(target_lang),
        }
        if source_lang:
            upload_payload["source_lang"] = _normalize_lang(source_lang)
        if formality:
            upload_payload["formality"] = formality
        if glossary and glossary.get("deepl_glossary_id"):
            upload_payload["glossary_id"] = glossary["deepl_glossary_id"]

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=90.0) as client:
            upload_res = await client.post(
                f"{_resolve_deepl_base_url()}/document",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                data=upload_payload,
                files={"file": (file_name, file_bytes, file.content_type or "application/octet-stream")},
            )

            if upload_res.status_code >= 400:
                raise HTTPException(status_code=upload_res.status_code, detail=upload_res.text.strip() or "DeepL document upload failed")

            upload_data = upload_res.json()
            document_id = str(upload_data.get("document_id") or "")
            document_key = str(upload_data.get("document_key") or "")
            if not document_id or not document_key:
                raise HTTPException(status_code=502, detail="DeepL did not return document_id/document_key")

            status_data: dict[str, Any] = {}
            for _ in range(40):
                status_res = await client.post(
                    f"{_resolve_deepl_base_url()}/document/{document_id}",
                    headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                    data={"document_key": document_key},
                )
                if status_res.status_code >= 400:
                    raise HTTPException(status_code=status_res.status_code, detail=status_res.text.strip() or "DeepL document status failed")

                status_data = status_res.json()
                status = str(status_data.get("status") or "").lower()
                if status == "done":
                    break
                if status == "error":
                    raise HTTPException(status_code=502, detail=str(status_data.get("error_message") or "DeepL document translation failed"))
                await asyncio.sleep(2)
            else:
                raise HTTPException(status_code=504, detail="Timed out waiting for DeepL document translation")

            result_res = await client.post(
                f"{_resolve_deepl_base_url()}/document/{document_id}/result",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                data={"document_key": document_key},
            )
            if result_res.status_code >= 400:
                raise HTTPException(status_code=result_res.status_code, detail=result_res.text.strip() or "DeepL document download failed")

        latency_ms = int((time.perf_counter() - start) * 1000)
        output_bytes = result_res.content
        output_b64 = base64.b64encode(output_bytes[:2_500_000]).decode("ascii")

        usage_events.append(
            {
                "id": str(uuid.uuid4()),
                "type": "document_translation",
                "provider": "deepl",
                "created_at": datetime.now(UTC).isoformat(),
                "latency_ms": latency_ms,
                "input_file_name": file_name,
                "input_bytes": len(file_bytes),
                "output_bytes": len(output_bytes),
                "billed_characters": int(status_data.get("billed_characters") or 0),
            }
        )

        return {
            "provider_used": "deepl",
            "latency_ms": latency_ms,
            "input_file_name": file_name,
            "output_file_name": file_name,
            "output_size_bytes": len(output_bytes),
            "billed_characters": int(status_data.get("billed_characters") or 0),
            "download_payload_base64": output_b64,
            "note": "Base64 payload is truncated for API safety. Use direct provider-side storage for very large documents.",
        }

    return router
