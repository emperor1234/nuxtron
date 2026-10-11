"""Content/Media constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated
from typing import Any
import os

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JOB_NOT_FOUND = "Media job not found."
JOB_NOT_CANCELLABLE = "Only queued jobs can be cancelled."
JOB_NOT_RETRYABLE = "Only failed jobs can be retried."
JSON_CONTENT_TYPE = "application/json"
MUX_ASSET_API_ENDPOINT = "https://api.mux.com/video/v1/assets"
ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT = "https://api.assemblyai.com/v2/transcript"
MEDIA_TYPES = frozenset({"image", "video", "audio", "document"})
MAX_CONCURRENT_JOBS_PER_TENANT = int(os.getenv("MEDIA_MAX_CONCURRENT_PER_TENANT", "5"))
MANAGED_PROVIDERS: dict[str, dict[str, Any]] = {
    "cloudinary": {
        "name": "Cloudinary",
        "media_types": ["image", "video"],
        "what_it_replaces": "Sharp, ImageMagick, FFmpeg + CDN",
        "best_for": "Transformation, resizing, format conversion",
        "env_vars": ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"],
        "api_endpoint": "https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload",
        "docs_url": "https://cloudinary.com/documentation",
        "isolation": "managed-sandbox",
        "supports_operations": ["resize", "crop", "format", "compress", "watermark", "transcode"],
    },
    "mux": {
        "name": "Mux",
        "media_types": ["video"],
        "what_it_replaces": "FFmpeg, video encoding pipeline",
        "best_for": "Streaming, adaptive bitrate, player analytics",
        "env_vars": ["MUX_TOKEN_ID", "MUX_TOKEN_SECRET"],
        "api_endpoint": MUX_ASSET_API_ENDPOINT,
        "docs_url": "https://docs.mux.com",
        "isolation": "managed-sandbox",
        "supports_operations": ["transcode", "stream", "thumbnail", "playback"],
    },
    "bunny": {
        "name": "Bunny.net",
        "media_types": ["image", "video"],
        "what_it_replaces": "FFmpeg + CDN layer",
        "best_for": "Cost-effective video streaming at scale",
        "env_vars": ["BUNNY_API_KEY", "BUNNY_STORAGE_ZONE", "BUNNY_CDN_HOSTNAME"],
        "api_endpoint": "https://storage.bunnycdn.com",
        "docs_url": "https://docs.bunny.net",
        "isolation": "managed-sandbox",
        "supports_operations": ["stream", "resize", "optimize"],
    },
    "assemblyai": {
        "name": "AssemblyAI",
        "media_types": ["audio"],
        "what_it_replaces": "Whisper, transcription pipeline",
        "best_for": "Transcription, speaker diarisation, sentiment",
        "env_vars": ["ASSEMBLYAI_API_KEY"],
        "api_endpoint": ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT,
        "docs_url": "https://www.assemblyai.com/docs",
        "isolation": "managed-sandbox",
        "supports_operations": ["transcribe", "diarize", "sentiment", "summarize"],
    },
    "deepgram": {
        "name": "Deepgram",
        "media_types": ["audio"],
        "what_it_replaces": "Whisper, real-time audio pipeline",
        "best_for": "Real-time transcription, low-latency voice apps",
        "env_vars": ["DEEPGRAM_API_KEY"],
        "api_endpoint": "https://api.deepgram.com/v1/listen",
        "docs_url": "https://developers.deepgram.com/docs",
        "isolation": "managed-sandbox",
        "supports_operations": ["transcribe", "stream", "detect_language", "punctuate"],
    },
    "adobe_pdf": {
        "name": "Adobe PDF Services",
        "media_types": ["document"],
        "what_it_replaces": "LibreOffice, Pandoc, Tika",
        "best_for": "Enterprise document conversion and extraction",
        "env_vars": ["ADOBE_PDF_CLIENT_ID", "ADOBE_PDF_CLIENT_SECRET"],
        "api_endpoint": "https://pdf-services.adobe.io",
        "docs_url": "https://developer.adobe.com/document-services/docs/overview",
        "isolation": "managed-sandbox",
        "supports_operations": ["convert", "extract", "compress", "merge", "split", "ocr"],
    },
}
_MAGIC_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/png": [(0, b"\x89PNG\r\n\x1a\n")],
    "image/gif": [(0, b"GIF87a"), (0, b"GIF89a")],
    "image/webp": [(0, b"RIFF"), (8, b"WEBP")],
    "video/mp4": [(4, b"ftyp")],
    "video/webm": [(0, b"\x1aE\xdf\xa3")],
    "audio/mpeg": [(0, b"\xff\xfb"), (0, b"\xff\xf3"), (0, b"\xff\xf2"), (0, b"ID3")],
    "audio/wav": [(0, b"RIFF"), (8, b"WAVE")],
    "audio/ogg": [(0, b"OggS")],
    "application/pdf": [(0, b"%PDF")],
}
