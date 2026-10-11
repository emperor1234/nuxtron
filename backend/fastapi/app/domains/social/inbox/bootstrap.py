"""Social/Inbox HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    ingest_message,
    inbox_stats,
    list_delivery_failure_replay_runs,
    list_saved_replies,
)
from .services.classify_message import _classify_message as _classify_message
from .services.classify_message import _priority_score as _priority_score
from .services.classify_message import _build_suggested_replies as _build_suggested_replies
from .schemas import ResponseRejectionRequest as ResponseRejectionRequest
from .schemas import InternalNoteRequest as InternalNoteRequest
from .schemas import MessageUpdateRequest as MessageUpdateRequest
from .schemas import ResponseReplayRequest as ResponseReplayRequest
from .schemas import DeliveryFailureBulkReplayRequest as DeliveryFailureBulkReplayRequest
from .schemas import InboxMessageIngestRequest as InboxMessageIngestRequest
from .schemas import DeliveryFailureResolveRequest as DeliveryFailureResolveRequest
from .schemas import DeliveryFailureBulkResolveRequest as DeliveryFailureBulkResolveRequest
from .schemas import DeliveryFailureReplayPendingRequest as DeliveryFailureReplayPendingRequest
from .schemas import SavedReplyUpdateRequest as SavedReplyUpdateRequest
from .schemas import ResponseApprovalRequest as ResponseApprovalRequest
from .schemas import AutoResponseRequest as AutoResponseRequest
from .schemas import LockRequest as LockRequest
from .schemas import SavedReplyRequest as SavedReplyRequest
from .constants import MESSAGE_NOT_FOUND as MESSAGE_NOT_FOUND
from .constants import AuthDep as AuthDep
import asyncio
import hashlib
import os
import time
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth
from ....integrations.vendor_manager import get_vendor_manager


def create_smart_inbox_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    messages_memory: list[dict[str, Any]],
    notes_memory: list[dict[str, Any]],
    locks_memory: list[dict[str, Any]],
    saved_replies_memory: list[dict[str, Any]],
    delivery_failures_memory: list[dict[str, Any]],
    delivery_replay_runs_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the Smart Inbox router (SproutSocial §3).
    No duplication: notifications.py handles outbound/internal notifications;
    social_listening handles keyword monitoring. This handles INBOUND social engagement.
    """
    router = APIRouter()
    _lock = threading.Lock()
    runtime = ContextRuntime(
        _lock=_lock,
        audit_log_memory=audit_log_memory,
        delivery_failures_memory=delivery_failures_memory,
        delivery_replay_runs_memory=delivery_replay_runs_memory,
        enforce_rate_limit=enforce_rate_limit,
        locks_memory=locks_memory,
        messages_memory=messages_memory,
        notes_memory=notes_memory,
        saved_replies_memory=saved_replies_memory,
    )
    ingest_message.register(router, runtime)
    inbox_stats.register(router, runtime)
    list_delivery_failure_replay_runs.register(router, runtime)
    list_saved_replies.register(router, runtime)
    return router


# Deprecated helper names retain one canonical callable owner.
_ai_classify = _classify_message
_suggested_replies = _build_suggested_replies
