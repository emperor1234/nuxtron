"""Explicit process-global infrastructure wiring.

Object construction is lazy and side-effect free beyond local memory. Database,
network, workers, and service mutation remain outside module import time.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .. import memory_stores
from ..domains.content import generation as content_generation
from ..domains.content.generation import ContentGenerationService
from .service_wiring import LegacyServiceCallbacks, wire_extracted_services


@dataclass(frozen=True)
class ProcessInfrastructure:
    """Canonical process-global state intentionally shared by app instances."""

    content_generation: ContentGenerationService


_infrastructure: ProcessInfrastructure | None = None
_infrastructure_lock = threading.Lock()


def get_process_infrastructure() -> ProcessInfrastructure:
    """Create the canonical process infrastructure once, on explicit demand."""
    global _infrastructure
    with _infrastructure_lock:
        if _infrastructure is None:
            _infrastructure = ProcessInfrastructure(
                content_generation=ContentGenerationService(memory_stores.content_generation_jobs)
            )
        return _infrastructure


def wire_process_infrastructure() -> ProcessInfrastructure:
    """Bind extracted-service compatibility shims to canonical owners."""
    infrastructure = get_process_infrastructure()
    content_generation.configure_content_generation_service(infrastructure.content_generation)

    from .. import legacy_main

    wire_extracted_services(
        LegacyServiceCallbacks(
            coerce_int=legacy_main._coerce_int,
            coerce_float=legacy_main._coerce_float,
            minio_presign=lambda *args, **kwargs: legacy_main._minio_presign(*args, **kwargs),
            verify_stripe_signature=lambda *args, **kwargs: legacy_main._verify_stripe_signature(*args, **kwargs),
            run_optional_ai_generation=lambda *args, **kwargs: legacy_main._run_optional_ai_generation(*args, **kwargs),
            generate_media_asset_bundle=lambda *args, **kwargs: legacy_main._generate_media_asset_bundle(*args, **kwargs),
            note_content_generation_telemetry=content_generation._content_generation_note_telemetry,
            content_generation_strict_mode=lambda: legacy_main._content_generation_strict_production_mode(),
            db_dsn=lambda: legacy_main._db_dsn(),
            encrypt=lambda value: legacy_main.te_encrypt(value),
            decrypt=lambda value: legacy_main.te_decrypt(value),
        ),
        db_ready=legacy_main._db_ready,
    )
    return infrastructure
