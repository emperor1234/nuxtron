"""Notifications/Delivery constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

NOTIFICATION_NOT_FOUND = "Notification not found."

PRIORITY_VALUES = {"info", "warning", "error", "success", "critical"}

DIGEST_FREQUENCY_VALUES = {"realtime", "daily", "weekly"}
