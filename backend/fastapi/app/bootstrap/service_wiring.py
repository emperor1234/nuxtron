"""Typed wiring for extracted legacy services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..domains.content import campaigns as content_generation_service, storage
from ..domains.notifications import email_campaigns
from ..domains.billing import checkout as stripe
from ..services import platform, social_reviews, social_scheduling


@dataclass(frozen=True)
class LegacyServiceCallbacks:
    """Small boundary containing callbacks not yet extracted from legacy_main."""

    coerce_int: Callable[[object, int], int]
    coerce_float: Callable[[object, float], float]
    minio_presign: Callable[..., Any]
    verify_stripe_signature: Callable[..., Any]
    run_optional_ai_generation: Callable[..., Any]
    generate_media_asset_bundle: Callable[..., Any]
    note_content_generation_telemetry: Callable[..., Any]
    content_generation_strict_mode: Callable[[], bool]
    db_dsn: Callable[[], str]
    encrypt: Callable[[str], str]
    decrypt: Callable[[str], str | None]


def wire_extracted_services(callbacks: LegacyServiceCallbacks, *, db_ready: bool) -> None:
    """Wire only dependencies that are not already canonical module imports."""
    platform.set_helpers(
        callbacks.coerce_int,
        callbacks.coerce_float,
        lambda value: dict(value) if isinstance(value, dict) else None,
    )
    platform.set_db_ready(db_ready)
    storage.set_memory_stores(minio_presign=callbacks.minio_presign)
    stripe.set_memory_stores(verify_stripe_signature=callbacks.verify_stripe_signature)
    social_reviews.set_memory_stores(coerce_int=callbacks.coerce_int)
    content_generation_service.set_memory_stores(
        run_optional_ai_generation=callbacks.run_optional_ai_generation,
        generate_media_asset_bundle=callbacks.generate_media_asset_bundle,
        json_object=dict,
        content_generation_note_telemetry=callbacks.note_content_generation_telemetry,
        content_generation_strict_production_mode=callbacks.content_generation_strict_mode,
    )
    email_campaigns.set_memory_stores(
        db_ready=db_ready,
        db_dsn_fn=callbacks.db_dsn,
        te_encrypt=callbacks.encrypt,
        te_decrypt=callbacks.decrypt,
        coerce_int=callbacks.coerce_int,
    )
    social_scheduling.set_memory_stores(
        db_ready=db_ready,
        db_dsn_fn=callbacks.db_dsn,
        te_encrypt=callbacks.encrypt,
        te_decrypt=callbacks.decrypt,
    )
