"""Assistant use cases: get ira recommendations."""

from ..constants import AuthDep
from ..constants import DEFAULT_BLOCKED_ACTIONS
from ..runtime import ContextRuntime
from ..schemas import IRAAdviceRequest
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_require_super_admin_for_control
from .db_dsn import helper_tenant_revenue_snapshot
from .frontier_stack_catalog import helper_tenant_suspicious_signal
from fastapi import Header
from typing import Annotated
from typing import Any


def execute_get_ira_recommendations(
    context_runtime: ContextRuntime,
    payload: IRAAdviceRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:advisor:recommendations", 90, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    helper_require_super_admin_for_control(
        control=control,
        x_super_admin_key=x_super_admin_key,
        detail="IRA advisor recommendations are restricted to super admin sessions.",
    )
    feedback_events = [
        item
        for item in context_runtime.ira_events_memory
        if item.get("tenant_id") == auth.tenant_id and item.get("event_type") == "learning_feedback_collected"
    ]
    ratings = [int(item.get("payload", {}).get("rating", 0) or 0) for item in feedback_events]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    snapshot = helper_tenant_revenue_snapshot(context_runtime, auth.tenant_id)
    risk_signal = helper_tenant_suspicious_signal(context_runtime, auth.tenant_id)
    recommendations: list[dict[str, Any]] = [
        {
            "id": "guardrail-1",
            "title": "Keep strict financial guardrails",
            "reason": "Autonomous billing changes, credit burns, and external transfers stay blocked without explicit approval.",
            "category": "safety",
        },
        {
            "id": "growth-1",
            "title": "Convert conversations into qualified leads",
            "reason": "Capture intent, budget, timeline, and preferred channel for every customer action request.",
            "category": "revenue",
        },
        {
            "id": "adoption-1",
            "title": "Guide users feature-by-feature",
            "reason": "Use IRA chat to provide role-aware onboarding for all platform modules.",
            "category": "feature_adoption",
        },
    ]
    if risk_signal.get("score", 0.0) >= float(control.get("suspicious_signal_threshold", 0.75)):
        recommendations.append(
            {
                "id": "risk-1",
                "title": "Increase human validation frequency",
                "reason": "Current suspicious signal is elevated; keep bulk/ticket/compliance workflows human-approved.",
                "category": "risk",
            }
        )
    if snapshot.get("profit_margin_pct", 0.0) < float(control.get("min_profit_margin_pct", 70.0)):
        recommendations.append(
            {
                "id": "margin-1",
                "title": "Prioritize retention scripts before refunds",
                "reason": "Margin is below threshold. For disputes <= GBP 50, offer value-preserving alternatives first.",
                "category": "revenue",
            }
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "horizon_days": payload.horizon_days,
        "metrics": {
            "avg_feedback_rating": avg_rating,
            "feedback_count": len(feedback_events),
            "profit_margin_pct": snapshot.get("profit_margin_pct", 0.0),
            "risk_score": risk_signal.get("score", 0.0),
        },
        "recommendations": recommendations,
        "limits": {
            "dashboard_scope": "super_admin_dashboard",
            "require_super_admin": bool(control.get("require_super_admin", True)),
            "blocked_autonomous_actions": list(DEFAULT_BLOCKED_ACTIONS),
            "max_dispute_auto_resolution_gbp": float(control.get("max_dispute_auto_resolution_gbp", 50.0)),
        },
    }
