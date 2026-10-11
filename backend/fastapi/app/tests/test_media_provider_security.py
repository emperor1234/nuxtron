from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.fastapi.app.services.ai_providers import (
    _ai_generate_image_binary,
    _ai_generate_video_binary,
    _ai_generate_voice_binary,
)


@pytest.mark.parametrize(
    ("generator", "args"),
    [
        (_ai_generate_image_binary, ("production image", "auto")),
        (_ai_generate_voice_binary, ("production voice",)),
        (_ai_generate_video_binary, ("production video",)),
    ],
)
def test_production_media_generation_fails_closed_without_provider(monkeypatch: pytest.MonkeyPatch, generator, args) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    for key in (
        "GOOGLE_VERTEX_API_KEY",
        "GOOGLE_VERTEX_PROJECT_ID",
        "STABILITY_API_KEY",
        "STABILITY_AI_API_KEY",
        "ELEVENLABS_API_KEY",
        "REPLICATE_API_TOKEN",
        "OPENVOICE_API_URL",
        "BARK_API_URL",
        "RVC_API_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        generator(*args)

    assert exc_info.value.status_code == 503
    assert "provider unavailable" in str(exc_info.value.detail).lower()
