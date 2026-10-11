"""Social use cases: social production readiness remediation plan."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from .create_best_stack_report import operation_social_growth_integration_matrix
from .invite_team_member_legacy import operation_social_production_readiness
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation_social_production_readiness_remediation_plan(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    """Return actionable remediation data required to reach 100% strict social production readiness."""
    st.enforce_rate_limit(f"{auth.tenant_id}:production-readiness:remediation", 120, 60)
    readiness = operation_social_production_readiness(st, router, auth)
    growth = operation_social_growth_integration_matrix(st, router, auth)
    signals = cast(dict[str, Any], readiness.get("signals") or {})
    oauth_mode = str(signals.get("oauth_mode") or "mock")
    db_backing_enabled = bool(signals.get("db_backing_enabled"))
    global_requirements: list[dict[str, Any]] = [
        {
            "key": "SOCIAL_OAUTH_MODE",
            "configured": oauth_mode == "live",
            "expected": "live",
            "category": "platform",
            "description": "Enforces live OAuth provider mode and disables mock OAuth behavior.",
        },
        {
            "key": "OPENAI_API_KEY",
            "configured": bool(signals.get("openai_configured")),
            "expected": "non-empty",
            "category": "ai",
            "description": "Required for AI assistant, DM chatbot, and longform repurpose flows without fallback.",
        },
        {
            "key": "SOCIAL_AI_POLICY_JSON|SOCIAL_AI_POLICY_PATH",
            "configured": bool(signals.get("ai_policy_configured")),
            "expected": "one configured",
            "category": "governance",
            "description": "Externalized AI policy required for strict mode controls and traceability.",
        },
        {
            "key": "SENTRY_DSN",
            "configured": bool(signals.get("sentry_configured")),
            "expected": "non-empty",
            "category": "observability",
            "description": "Centralized telemetry and incident observability for backend/frontend/LLM paths.",
        },
        {
            "key": "STRIPE_SECRET_KEY",
            "configured": bool(signals.get("stripe_configured")),
            "expected": "non-empty",
            "category": "billing",
            "description": "Billing and subscription-sync integration for production monetization workflows.",
        },
        {
            "key": "CANVA_ACCESS_TOKEN",
            "configured": bool(signals.get("canva_configured")),
            "expected": "non-empty",
            "category": "creative",
            "description": "Canva import and design-automation parity path for content creation.",
        },
        {
            "key": "DATABASE_BACKING",
            "configured": db_backing_enabled,
            "expected": "durable postgres connection",
            "category": "infrastructure",
            "description": "Disables seeded in-memory social state and enables durable production persistence.",
        },
        {
            "key": "BITLY_ACCESS_TOKEN|TINYURL_API_TOKEN|REBRANDLY_API_KEY",
            "configured": bool(any((readiness.get("vendors") or {}).get("shorteners", {}).values())),
            "expected": "at least one configured",
            "category": "distribution",
            "description": "Link shortener integration required for UTM-safe and measurable distribution.",
        },
    ]
    matrix = cast(list[dict[str, Any]], growth.get("matrix") or [])
    integration_requirements: list[dict[str, Any]] = []
    for row in matrix:
        missing_env = cast(list[str], row.get("missing_env_keys") or [])
        if not missing_env:
            continue
        integration_requirements.append(
            {
                "integration_key": row.get("integration_key"),
                "integration": row.get("integration"),
                "category": row.get("category"),
                "phase": row.get("phase"),
                "impact_stars": row.get("impact_stars"),
                "roi_priority": row.get("roi_priority"),
                "missing_env_keys": missing_env,
                "left_to_complete": row.get("left_to_complete") or [],
            }
        )
    missing_env_keys = sorted(
        {key for item in integration_requirements for key in cast(list[str], item.get("missing_env_keys") or [])}
    )
    unresolved_global = [item for item in global_requirements if not item["configured"]]
    next_actions: list[str] = []
    if unresolved_global:
        next_actions.append("Configure all unresolved global requirements in environment/secret manager.")
    if integration_requirements:
        next_actions.append("Configure missing integration credentials ordered by ROI priority.")
    if not db_backing_enabled:
        next_actions.append(
            "Provision/reach PostgreSQL so social workspace uses durable storage instead of in-memory seeds."
        )
    if oauth_mode != "live":
        next_actions.append("Set SOCIAL_OAUTH_MODE=live and re-run readiness checks in strict mode.")
    if not next_actions:
        next_actions.append("All readiness prerequisites are configured. Run strict end-to-end verification suite.")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "production_ready": bool(readiness.get("production_ready")),
        "readiness_score": int(readiness.get("readiness_score") or 0),
        "blocking_items": readiness.get("blocking_items") or [],
        "global_requirements": global_requirements,
        "integration_requirements": integration_requirements,
        "missing_env_keys": missing_env_keys,
        "next_actions": next_actions,
    }
