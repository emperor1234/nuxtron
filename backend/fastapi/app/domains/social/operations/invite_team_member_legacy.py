"""Social use cases: invite team member legacy."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_db_enabled
from ..constants import AuthDep
from ..constants import OAUTH_PROVIDERS
from ..extended_schemas import TeamMemberInviteRequest
from ..services.capabilities import _strict_social_mode_enabled
from ..services.oauth import _oauth_mode
from .build_capability_matrix import operation__build_capability_matrix
from .download_report import operation__vendor_registry
from .download_report import operation_invite_team_member
from .integration_growth_specs import operation__integration_growth_specs
from fastapi import APIRouter
from typing import Any
from typing import cast
import os


def operation_invite_team_member_legacy(
    st: _SocialWorkspaceState, router: APIRouter, payload: TeamMemberInviteRequest, auth: AuthDep
) -> dict[str, Any]:
    """Legacy compatibility endpoint used by existing tests and older clients."""
    result = operation_invite_team_member(st, router, payload, auth)
    return {"success": True, "invite": result["member"], "status": result["status"], "tenant_id": result["tenant_id"]}


def operation__build_growth_matrix(
    st: _SocialWorkspaceState, router: APIRouter, *, available_paths: set[str], strict_mode_enabled: bool
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = operation__integration_growth_specs(st, router)
    matrix: list[dict[str, Any]] = []
    for spec in specs:
        routes = cast(list[str], spec.get("route_dependencies") or [])
        available_routes = [route for route in routes if route in available_paths]
        missing_routes = [route for route in routes if route not in available_paths]
        route_coverage = int(round(len(available_routes) / len(routes) * 100)) if routes else 100
        required_env_keys = cast(list[str], spec.get("required_env_keys") or [])
        configured_env_keys = [key for key in required_env_keys if bool(os.getenv(key, "").strip())]
        configured = len(configured_env_keys) == len(required_env_keys) if required_env_keys else True
        missing_env_keys = [key for key in required_env_keys if key not in configured_env_keys]
        completion = route_coverage
        if not configured:
            completion -= 20
        if strict_mode_enabled and (not configured):
            completion -= 10
        completion = max(0, min(100, completion))
        implementation_status = "done" if completion == 100 and (not missing_routes) else "partial"
        if completion < 60:
            implementation_status = "missing"
        left_to_complete: list[str] = []
        if missing_routes:
            left_to_complete.append(f"Missing route wiring: {', '.join(missing_routes)}")
        if missing_env_keys:
            left_to_complete.append(f"Missing vendor credentials: {', '.join(missing_env_keys)}")
        matrix.append(
            {
                "integration": spec["integration"],
                "integration_key": spec["integration_key"],
                "best_practice_required": True,
                "category": spec["category"],
                "phase": spec["phase"],
                "impact_stars": spec["impact_stars"],
                "roi_priority": spec["roi_priority"],
                "completion_percent": completion,
                "implementation_status": implementation_status,
                "configured": configured,
                "vendors": spec["vendors"],
                "how_it_works": spec["how_it_works"],
                "why_it_drives_growth": spec["why_it_drives_growth"],
                "required_env_keys": required_env_keys,
                "configured_env_keys": configured_env_keys,
                "missing_env_keys": missing_env_keys,
                "route_dependencies": routes,
                "available_routes": available_routes,
                "missing_routes": missing_routes,
                "left_to_complete": left_to_complete,
            }
        )
    matrix.sort(key=lambda item: (int(item.get("roi_priority") or 999), -int(item.get("completion_percent") or 0)))
    done_count = sum((1 for item in matrix if item.get("implementation_status") == "done"))
    partial_count = sum((1 for item in matrix if item.get("implementation_status") == "partial"))
    missing_count = sum((1 for item in matrix if item.get("implementation_status") == "missing"))
    required_total = sum((1 for item in matrix if item.get("best_practice_required")))
    required_done = sum(
        (1 for item in matrix if item.get("best_practice_required") and item.get("implementation_status") == "done")
    )
    avg_completion = (
        int(round(sum((int(item["completion_percent"]) for item in matrix)) / len(matrix))) if matrix else 0
    )
    summary = {
        "total_integrations": len(matrix),
        "required_integrations": required_total,
        "required_done": required_done,
        "done": done_count,
        "partial": partial_count,
        "missing": missing_count,
        "average_completion_percent": avg_completion,
        "target": "100% end-to-end production-grade implementation with live vendor credentials and route coverage",
        "highest_roi_next": [item["integration_key"] for item in matrix if item["completion_percent"] < 100][:5],
    }
    return (matrix, summary)


def operation_social_production_readiness(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    """Return explicit production-readiness signals for social workspace integrations and fallback paths."""
    st.enforce_rate_limit(f"{auth.tenant_id}:production-readiness", 120, 60)
    strict_mode_enabled = _strict_social_mode_enabled()
    oauth_mode = _oauth_mode()
    openai_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    ai_policy_configured = bool(
        os.getenv("SOCIAL_AI_POLICY_JSON", "").strip() or os.getenv("SOCIAL_AI_POLICY_PATH", "").strip()
    )
    sentry_configured = bool(os.getenv("SENTRY_DSN", "").strip())
    stripe_configured = bool(os.getenv("STRIPE_SECRET_KEY", "").strip())
    canva_configured = bool(os.getenv("CANVA_ACCESS_TOKEN", "").strip())
    db_backing_enabled = _sw_db_enabled(st)
    oauth_vendor_keys: dict[str, bool] = {}
    for network, meta in OAUTH_PROVIDERS.items():
        env_key = str(meta.get("client_id_env") or "").strip()
        oauth_vendor_keys[network] = bool(os.getenv(env_key, "").strip()) if env_key else False
    shortener_config = {
        "bitly": bool(os.getenv("BITLY_ACCESS_TOKEN", "").strip()),
        "tinyurl": bool(os.getenv("TINYURL_API_TOKEN", "").strip()),
        "rebrandly": bool(os.getenv("REBRANDLY_API_KEY", "").strip()),
    }
    vendor_registry = operation__vendor_registry(st, router, oauth_vendor_keys, shortener_config)
    vendor_flags = {item["vendor_key"]: bool(item["configured"]) for item in vendor_registry}
    available_paths = {str(getattr(route, "path", "")) for route in router.routes}
    capability_matrix = operation__build_capability_matrix(
        st,
        router,
        available_paths=available_paths,
        vendor_flags=vendor_flags,
        oauth_mode=oauth_mode,
        db_backing_enabled=db_backing_enabled,
    )
    active_fallback_paths = {
        "oauth_mock_mode": oauth_mode != "live",
        "ai_assistant_fallback": not openai_configured,
        "dm_chatbot_fallback": not openai_configured,
        "longform_repurpose_fallback": not openai_configured,
        "seeded_in_memory_state": not db_backing_enabled,
    }
    if strict_mode_enabled:
        active_fallback_paths = {key: False for key in active_fallback_paths}
    blocking_items: list[str] = []
    if oauth_mode != "live":
        blocking_items.append("SOCIAL_OAUTH_MODE is not set to live.")
    if not openai_configured:
        blocking_items.append("OPENAI_API_KEY is not configured for AI assistant and repurpose flows.")
    if not ai_policy_configured:
        blocking_items.append("AI policy is not externalized via SOCIAL_AI_POLICY_JSON or SOCIAL_AI_POLICY_PATH.")
    if not sentry_configured:
        blocking_items.append("SENTRY_DSN is not configured for backend/frontend/LLM failure telemetry.")
    if not stripe_configured:
        blocking_items.append("STRIPE_SECRET_KEY is not configured for billing and subscription sync.")
    if not canva_configured:
        blocking_items.append("CANVA_ACCESS_TOKEN is not configured for Canva import.")
    if not db_backing_enabled:
        blocking_items.append("Durable social database backing is not configured; in-memory seed data remains active.")
    if not any(shortener_config.values()):
        blocking_items.append("No URL shortener key configured (Bitly, TinyURL, or Rebrandly).")
    configured_oauth_networks = sum((1 for configured in oauth_vendor_keys.values() if configured))
    fallback_count = sum((1 for enabled in active_fallback_paths.values() if enabled))
    capability_completion = [int(item["completion_percent"]) for item in capability_matrix]
    capability_average = (
        int(round(sum(capability_completion) / len(capability_completion))) if capability_completion else 0
    )
    fully_wired_count = sum((1 for item in capability_matrix if item.get("fully_wired")))
    missing_required_vendor_map: dict[str, list[str]] = {}
    for item in capability_matrix:
        missing = cast(list[str], item.get("required_vendors_missing") or [])
        if missing:
            missing_required_vendor_map[str(item.get("capability_key") or "unknown")] = missing
    for capability_key, missing_vendors in missing_required_vendor_map.items():
        blocking_items.append(
            f"Required vendor credentials missing for {capability_key}: {', '.join(missing_vendors)}."
        )
    readiness_score = max(0, 100 - len(blocking_items) * 10 - fallback_count * 5)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "production_ready": len(blocking_items) == 0 and fallback_count == 0,
        "readiness_score": readiness_score,
        "capability_summary": {
            "total_capabilities": len(capability_matrix),
            "fully_wired_capabilities": fully_wired_count,
            "average_completion_percent": capability_average,
            "target": "100% end-to-end production-grade with no mock-only dependencies",
        },
        "signals": {
            "strict_social_mode_enabled": strict_mode_enabled,
            "oauth_mode": oauth_mode,
            "openai_configured": openai_configured,
            "ai_policy_configured": ai_policy_configured,
            "sentry_configured": sentry_configured,
            "stripe_configured": stripe_configured,
            "canva_configured": canva_configured,
            "db_backing_enabled": db_backing_enabled,
            "oauth_vendor_networks_configured": configured_oauth_networks,
            "oauth_vendor_networks_total": len(oauth_vendor_keys),
        },
        "vendors": {"oauth": oauth_vendor_keys, "shorteners": shortener_config, "registry": vendor_registry},
        "capability_matrix": capability_matrix,
        "active_fallback_paths": active_fallback_paths,
        "blocking_items": blocking_items,
    }
