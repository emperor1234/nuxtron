"""Integrations/Platforms constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from ....integrations.vendor_manager import get_vendor_manager
from fastapi import Depends
from typing import Annotated
from typing import Any
import logging
import threading

logger = logging.getLogger(__name__)
AuthDep = Annotated[AuthContext, Depends(require_auth)]
_lock = threading.Lock()
_platform_clients: dict[str, dict[str, Any]] = {}
_scheduled_posts: dict[str, list[dict[str, Any]]] = {}
_inbox_messages: dict[str, list[dict[str, Any]]] = {}
_SUPPORTED_PLATFORMS = ("twitter", "facebook", "instagram", "linkedin", "tiktok")
_vendor_manager = get_vendor_manager()
