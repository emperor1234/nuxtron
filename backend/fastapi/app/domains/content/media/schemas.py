"""Content/Media request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field
from typing import Any


class MediaJobCreateRequest(BaseModel):
    """Queue a new media processing job. Server only receives metadata — never file bytes."""

    storage_key: str = Field(
        min_length=1, max_length=1024, description="Object key in raw-input bucket (post presigned upload)"
    )
    media_type: str = Field(min_length=1, max_length=16, description="One of: image | video | audio | document")
    output_bucket: str = Field(default="processed-output", min_length=1, max_length=64)
    processing_options: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary processing hints (resize, format, quality…)"
    )
    validation_token: str | None = Field(
        default=None, max_length=256, description="Token issued by /media/validate-file — required in strict mode"
    )
    provider: str | None = Field(
        default=None,
        max_length=32,
        description="Managed provider: cloudinary | mux | bunny | assemblyai | deepgram | adobe_pdf",
    )


class MediaSandboxDispatchRequest(BaseModel):
    """Dispatch a file directly to a named managed provider."""

    storage_key: str = Field(min_length=1, max_length=1024, description="Storage key of the already-uploaded file")
    media_type: str = Field(min_length=1, max_length=16, description="One of: image | video | audio | document")
    provider: str = Field(min_length=1, max_length=32, description="Provider key from GET /media/providers")
    operation: str = Field(
        default="auto",
        min_length=1,
        max_length=32,
        description="Provider-specific operation (resize, transcode, transcribe…)",
    )
    operation_params: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific parameters (width, height, format, language…)"
    )
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Public URL of the source file (required by some providers that pull files)",
    )


class MediaValidateRequest(BaseModel):
    """Submit first-16-bytes of a file for magic-byte MIME detection."""

    first_bytes_b64: str = Field(
        min_length=1,
        max_length=64,
        description="Base64-encoded first 16 bytes of the file (read from browser before upload)",
    )
    expected_mime: str = Field(min_length=1, max_length=64, description="MIME type the client claims the file is")
    storage_key: str = Field(
        default="", max_length=1024, description="Object key to bind validation to; mandatory in production"
    )


class MediaOutputUrlRequest(BaseModel):
    expires_seconds: int = Field(default=900, ge=60, le=86400, description="Signed URL TTL in seconds (60–86400)")
