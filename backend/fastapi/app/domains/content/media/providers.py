"""Media provider dispatch registry; data constants never import adapters."""

from .services.adobe_pdf import _dispatch_adobe_pdf
from .services.dispatch_deepgram import _dispatch_deepgram
from .services.processing import _dispatch_assemblyai
from .services.processing import _dispatch_bunny
from .services.processing import _dispatch_cloudinary
from .services.processing import _dispatch_mux
from typing import Any

_PROVIDER_DISPATCH: dict[str, Any] = {
    "cloudinary": _dispatch_cloudinary,
    "mux": _dispatch_mux,
    "bunny": _dispatch_bunny,
    "assemblyai": _dispatch_assemblyai,
    "deepgram": _dispatch_deepgram,
    "adobe_pdf": _dispatch_adobe_pdf,
}
