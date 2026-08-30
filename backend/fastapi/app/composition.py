"""Backwards-compatible alias for the bootstrap composition root.

Application creation and router wiring moved to ``app.bootstrap``: this module
now only re-exports that single application so existing
``from .composition import app`` importers keep working.
"""

from __future__ import annotations

from .bootstrap.application import app, create_app
from .rate_limiter import reset_rate_limits_for_tests

__all__ = ["app", "create_app", "reset_rate_limits_for_tests"]
