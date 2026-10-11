"""Integrations/Platforms explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    enforce_rate_limit: Callable[[str, int, int], None]
