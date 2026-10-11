"""Search/Visibility explicit runtime dependencies."""

from __future__ import annotations
from .constants import StoreList
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _analytics_table_ready: Any
    _db_dsn_fn: Any
    _db_ready_fn: Any
    audit_log_memory: StoreList
    enforce_rate_limit: Callable[[str, int, int], None]
    vse_briefs_memory: Any
    vse_cascade_simulations_memory: Any
    vse_content_factory_memory: Any
    vse_dark_social_seeds_memory: Any
    vse_detonations_memory: Any
    vse_emotion_analyses_memory: Any
    vse_immortal_assets_memory: Any
    vse_momentum_events_memory: Any
    vse_network_maps_memory: Any
    vse_paid_events_memory: Any
    vse_swarms_memory: Any
    vse_trend_alerts_memory: Any
    vse_trend_hijacks_memory: Any
    vse_trigger_analyses_memory: Any
    vse_viral_events_memory: Any
    vse_viral_vault_memory: Any
