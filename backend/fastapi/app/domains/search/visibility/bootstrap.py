"""Search/Visibility HTTP composition and legacy import exports."""

from __future__ import annotations
from .constants import StoreList
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from .api import (
    list_engines,
    list_viral_briefs,
    network_superconnectors,
    swarm_status,
    content_score,
    paid_amplify,
    simulate,
)
from .services.uid import _uid as _uid
from .services.uid import _now as _now
from .services.uid import _viral_probability_score as _viral_probability_score
from .services.uid import _normalise_text as _normalise_text
from .services.uid import _token_jaccard_similarity as _token_jaccard_similarity
from .services.uid import _topic_fingerprint as _topic_fingerprint
from .services.uid import _build_content_body as _build_content_body
from .schemas import ImmortaliseRequest as ImmortaliseRequest
from .schemas import ContentScoreRequest as ContentScoreRequest
from .schemas import TrendHijackRequest as TrendHijackRequest
from .schemas import ViralBriefRequest as ViralBriefRequest
from .schemas import ViralContentVariantsRequest as ViralContentVariantsRequest
from .schemas import DarkSocialAttributionRequest as DarkSocialAttributionRequest
from .schemas import PaidAssessRequest as PaidAssessRequest
from .schemas import SwarmComposeRequest as SwarmComposeRequest
from .schemas import MomentumStartRequest as MomentumStartRequest
from .schemas import MomentumInjectRequest as MomentumInjectRequest
from .schemas import CascadeSimulateRequest as CascadeSimulateRequest
from .schemas import SwarmActivateRequest as SwarmActivateRequest
from .schemas import TriggerAnalyzeRequest as TriggerAnalyzeRequest
from .schemas import DetonationPlanRequest as DetonationPlanRequest
from .schemas import PaidAmplifyRequest as PaidAmplifyRequest
from .schemas import NetworkMapRequest as NetworkMapRequest
from .schemas import AlgorithmOptimizeRequest as AlgorithmOptimizeRequest
from .schemas import DarkSocialSeedRequest as DarkSocialSeedRequest
from .schemas import EmotionEngineerRequest as EmotionEngineerRequest
from .schemas import HooksRequest as HooksRequest
from .schemas import ViralContentRequest as ViralContentRequest
from .schemas import EmotionAnalyzeRequest as EmotionAnalyzeRequest
from .constants import AuthDep as AuthDep
import json
import random
import string
from datetime import UTC
from datetime import datetime
from hashlib import sha256
from typing import Annotated
from typing import Any
import psycopg
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth


def create_vse_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    memory_stores: dict[str, StoreList] | None = None,
    audit_log_memory: StoreList,
    db_ready_fn: Callable[[], bool] | None = None,
    db_dsn_fn: Callable[[], str] | None = None,
    **legacy_memory_stores: StoreList,
) -> APIRouter:
    router = APIRouter(prefix="/vse", tags=["Viral Singularity Engine"])
    if memory_stores is None:
        required_legacy = {
            "vse_viral_events_memory": legacy_memory_stores.get("vse_viral_events_memory"),
            "vse_briefs_memory": legacy_memory_stores.get("vse_briefs_memory"),
            "vse_trigger_analyses_memory": legacy_memory_stores.get("vse_trigger_analyses_memory"),
            "vse_algorithm_models_memory": legacy_memory_stores.get("vse_algorithm_models_memory"),
            "vse_algorithm_updates_memory": legacy_memory_stores.get("vse_algorithm_updates_memory"),
            "vse_network_maps_memory": legacy_memory_stores.get("vse_network_maps_memory"),
            "vse_cascade_simulations_memory": legacy_memory_stores.get("vse_cascade_simulations_memory"),
            "vse_detonations_memory": legacy_memory_stores.get("vse_detonations_memory"),
            "vse_swarms_memory": legacy_memory_stores.get("vse_swarms_memory"),
            "vse_momentum_events_memory": legacy_memory_stores.get("vse_momentum_events_memory"),
            "vse_content_factory_memory": legacy_memory_stores.get("vse_content_factory_memory"),
            "vse_emotion_analyses_memory": legacy_memory_stores.get("vse_emotion_analyses_memory"),
            "vse_trend_alerts_memory": legacy_memory_stores.get("vse_trend_alerts_memory"),
            "vse_trend_hijacks_memory": legacy_memory_stores.get("vse_trend_hijacks_memory"),
            "vse_paid_events_memory": legacy_memory_stores.get("vse_paid_events_memory"),
            "vse_dark_social_seeds_memory": legacy_memory_stores.get("vse_dark_social_seeds_memory"),
            "vse_immortal_assets_memory": legacy_memory_stores.get("vse_immortal_assets_memory"),
            "vse_viral_vault_memory": legacy_memory_stores.get("vse_viral_vault_memory"),
        }
        missing = [name for name, value in required_legacy.items() if value is None]
        if missing:
            raise ValueError(f"Missing VSE memory stores: {', '.join(missing)}")
        memory_stores = {name: value for name, value in required_legacy.items() if value is not None}
    vse_viral_events_memory = memory_stores["vse_viral_events_memory"]
    vse_briefs_memory = memory_stores["vse_briefs_memory"]
    vse_trigger_analyses_memory = memory_stores["vse_trigger_analyses_memory"]
    vse_algorithm_models_memory = memory_stores["vse_algorithm_models_memory"]
    vse_algorithm_updates_memory = memory_stores["vse_algorithm_updates_memory"]
    vse_network_maps_memory = memory_stores["vse_network_maps_memory"]
    vse_cascade_simulations_memory = memory_stores["vse_cascade_simulations_memory"]
    vse_detonations_memory = memory_stores["vse_detonations_memory"]
    vse_swarms_memory = memory_stores["vse_swarms_memory"]
    vse_momentum_events_memory = memory_stores["vse_momentum_events_memory"]
    vse_content_factory_memory = memory_stores["vse_content_factory_memory"]
    vse_emotion_analyses_memory = memory_stores["vse_emotion_analyses_memory"]
    vse_trend_alerts_memory = memory_stores["vse_trend_alerts_memory"]
    vse_trend_hijacks_memory = memory_stores["vse_trend_hijacks_memory"]
    vse_paid_events_memory = memory_stores["vse_paid_events_memory"]
    vse_dark_social_seeds_memory = memory_stores["vse_dark_social_seeds_memory"]
    vse_immortal_assets_memory = memory_stores["vse_immortal_assets_memory"]
    vse_viral_vault_memory = memory_stores["vse_viral_vault_memory"]
    _db_ready_fn = db_ready_fn if db_ready_fn is not None else lambda: False
    _db_dsn_fn = db_dsn_fn if db_dsn_fn is not None else lambda: ""
    _analytics_table_ready = False
    _ = (vse_algorithm_models_memory, vse_algorithm_updates_memory)
    runtime = ContextRuntime(
        _analytics_table_ready=_analytics_table_ready,
        _db_dsn_fn=_db_dsn_fn,
        _db_ready_fn=_db_ready_fn,
        audit_log_memory=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        vse_briefs_memory=vse_briefs_memory,
        vse_cascade_simulations_memory=vse_cascade_simulations_memory,
        vse_content_factory_memory=vse_content_factory_memory,
        vse_dark_social_seeds_memory=vse_dark_social_seeds_memory,
        vse_detonations_memory=vse_detonations_memory,
        vse_emotion_analyses_memory=vse_emotion_analyses_memory,
        vse_immortal_assets_memory=vse_immortal_assets_memory,
        vse_momentum_events_memory=vse_momentum_events_memory,
        vse_network_maps_memory=vse_network_maps_memory,
        vse_paid_events_memory=vse_paid_events_memory,
        vse_swarms_memory=vse_swarms_memory,
        vse_trend_alerts_memory=vse_trend_alerts_memory,
        vse_trend_hijacks_memory=vse_trend_hijacks_memory,
        vse_trigger_analyses_memory=vse_trigger_analyses_memory,
        vse_viral_events_memory=vse_viral_events_memory,
        vse_viral_vault_memory=vse_viral_vault_memory,
    )
    list_engines.register(router, runtime)
    list_viral_briefs.register(router, runtime)
    network_superconnectors.register(router, runtime)
    swarm_status.register(router, runtime)
    content_score.register(router, runtime)
    paid_amplify.register(router, runtime)
    simulate.register(router, runtime)
    return router
