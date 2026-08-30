"""FastAPI application entrypoint.

The application is built by ``app.bootstrap.application``; this module only
re-exports it so ASGI servers can keep pointing at ``app.main:app``.
"""

from .bootstrap.application import app, create_app
from .rate_limiter import reset_rate_limits_for_tests

__all__ = ["app", "create_app", "reset_rate_limits_for_tests"]
