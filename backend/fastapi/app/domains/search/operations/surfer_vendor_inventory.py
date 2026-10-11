"""Search use cases: surfer vendor inventory."""

from ....deps import AuthContext
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SurferEnvTemplateRequest
from ..schemas import SurferProviderBootstrapRequest
from ..schemas import SurferProviderProbeRequest
from .platform_now_iso import helper_bootstrap_plan
from .platform_now_iso import helper_now_iso
from .surfer_provider_probe_payload import helper_surfer_configured_provider_keys
from .surfer_provider_probe_payload import helper_surfer_provider_priority
from .surfer_provider_probe_payload import helper_surfer_provider_probe_display
from .surfer_provider_probe_payload import helper_surfer_provider_probe_payload
from .surfer_provider_probe_payload import helper_surfer_provider_requirements
from typing import Any


def helper_surfer_vendor_inventory(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    checklist = helper_surfer_provider_requirements(runtime, auth)
    return [
        {
            "vendor": item["provider"],
            "module": item["kind"],
            "type": "integration",
            "configured": item["configured"],
            "evidence": "search_everywhere surfer provider checklist",
        }
        for item in checklist
    ]


def helper_surfer_run_provider_probes(
    runtime: SearchRuntime, auth: AuthContext, payload: SurferProviderProbeRequest
) -> dict[str, Any]:
    all_keys = ["dataforseo", "serper", "google_keyword_planner", "google_search_console"]
    requested = [p.strip().lower() for p in payload.providers if p and p.strip()]
    provider_keys = requested if requested else all_keys
    provider_keys = [key for key in provider_keys if key in all_keys]
    checklist = helper_surfer_provider_requirements(runtime, auth)
    configured_keys = helper_surfer_configured_provider_keys(checklist)
    probes: list[dict[str, Any]] = []
    for provider_key in provider_keys:
        is_configured = provider_key in configured_keys
        if not is_configured and (not payload.include_unconfigured):
            probes.append(
                {
                    "provider": helper_surfer_provider_probe_display(provider_key),
                    "provider_key": provider_key,
                    "status": "skipped",
                    "reason": "not_configured",
                    "configured": False,
                }
            )
            continue
        try:
            result = rank_tracker_router._fetch_provider_keywords(
                provider_key=provider_key,
                operation="probe",
                payload=helper_surfer_provider_probe_payload(provider_key, payload.max_results),
                tenant_id=auth.tenant_id,
            )
            keywords = list(result.get("keywords", []))
            probes.append(
                {
                    "provider": helper_surfer_provider_probe_display(provider_key),
                    "provider_key": provider_key,
                    "status": "passed" if len(keywords) > 0 else "failed",
                    "configured": is_configured,
                    "keywords_returned": len(keywords),
                    "cache_hit": bool(result.get("cache_hit", False)),
                }
            )
        except rank_tracker_router.ProviderCallError as exc:
            probes.append(
                {
                    "provider": helper_surfer_provider_probe_display(provider_key),
                    "provider_key": provider_key,
                    "status": "failed",
                    "configured": is_configured,
                    "error_code": exc.code,
                    "error_message": exc.message,
                }
            )
        except Exception as exc:
            probes.append(
                {
                    "provider": helper_surfer_provider_probe_display(provider_key),
                    "provider_key": provider_key,
                    "status": "failed",
                    "configured": is_configured,
                    "error_code": "unexpected_error",
                    "error_message": str(exc)[:300],
                }
            )
    passed = sum((1 for probe in probes if probe.get("status") == "passed"))
    failed = sum((1 for probe in probes if probe.get("status") == "failed"))
    skipped = sum((1 for probe in probes if probe.get("status") == "skipped"))
    return {
        "providers_requested": provider_keys,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "strict_live_ready": passed > 0,
        "probes": probes,
    }


def helper_surfer_env_template(
    runtime: SearchRuntime, auth: AuthContext, payload: SurferEnvTemplateRequest
) -> dict[str, Any]:
    checklist = helper_surfer_provider_requirements(runtime, auth)
    lines: list[str] = []
    missing_keys: list[str] = []
    providers_included: list[str] = []
    for item in checklist:
        configured = bool(item.get("configured"))
        if configured and (not payload.include_configured):
            continue
        provider_name = str(item.get("provider", ""))
        providers_included.append(provider_name)
        lines.append(f"# {provider_name}")
        required_missing = list(item.get("required_missing", []))
        required_present = list(item.get("required_present", []))
        required_all = required_missing + required_present
        for env_name in required_all:
            if env_name in required_present and (not payload.include_configured):
                continue
            if env_name in required_missing:
                missing_keys.append(env_name)
            lines.append(f"{env_name}=")
        if payload.include_optional:
            for env_name in list(item.get("optional_present", [])):
                if payload.include_configured:
                    lines.append(f"{env_name}=")
        lines.append("")
    content = "\n".join(lines).strip() + "\n" if lines else ""
    return {"providers_included": providers_included, "missing_keys": sorted(set(missing_keys)), "content": content}


def helper_surfer_wiring_plan(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    checklist = helper_surfer_provider_requirements(runtime, auth)
    total = len(checklist)
    configured = sum((1 for item in checklist if item.get("configured")))
    integration_pct = round(configured / max(total, 1) * 100.0, 1)
    increment_per_provider = round(100.0 / max(total, 1), 2)
    missing_rows: list[dict[str, Any]] = []
    for item in checklist:
        if item.get("configured"):
            continue
        provider = str(item.get("provider", ""))
        kind = str(item.get("kind", "integration"))
        priority, rationale, gate_impact_score = helper_surfer_provider_priority(provider, kind)
        missing_rows.append(
            {
                "provider": provider,
                "kind": kind,
                "priority": priority,
                "gate_impact_score": gate_impact_score,
                "integration_pct_if_added": round(min(100.0, integration_pct + increment_per_provider), 2),
                "required_missing": list(item.get("required_missing", [])),
                "optional_present": list(item.get("optional_present", [])),
                "rationale": rationale,
            }
        )
    missing_rows.sort(
        key=lambda row: (
            0 if row["priority"] == "P0" else 1 if row["priority"] == "P1" else 2,
            -int(row["gate_impact_score"]),
            row["provider"],
        )
    )
    stage_1 = [row["provider"] for row in missing_rows if row["priority"] == "P0"]
    stage_2 = [row["provider"] for row in missing_rows if row["priority"] == "P1"]
    stage_3 = [row["provider"] for row in missing_rows if row["priority"] == "P2"]
    return {
        "configured": configured,
        "total": total,
        "integration_configured_pct": integration_pct,
        "integration_increment_per_provider_pct": increment_per_provider,
        "stages": {
            "stage_1_strict_live_foundation": {
                "goal": "Unblock strict-live keyword provider readiness.",
                "providers": stage_1,
            },
            "stage_2_runtime_reliability": {
                "goal": "Wire AI + reliability providers for resilient production operation.",
                "providers": stage_2,
            },
            "stage_3_full_automation_coverage": {
                "goal": "Complete publishing and long-tail automation integrations.",
                "providers": stage_3,
            },
        },
        "prioritized_missing_providers": missing_rows,
    }


def operation_surfer_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:provider-checklist", 60, 60)
    checklist = helper_surfer_provider_requirements(runtime, auth)
    configured = sum((1 for item in checklist if item["configured"]))
    total = len(checklist)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "configured": configured,
        "total": total,
        "configured_pct": round(configured / max(total, 1) * 100.0, 1),
        "checklist": checklist,
        "generated_at": helper_now_iso(),
    }


def operation_surfer_provider_bootstrap(
    runtime: SearchRuntime, payload: SurferProviderBootstrapRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:provider-bootstrap", 60, 60)
    checklist = helper_surfer_provider_requirements(runtime, auth)
    provider_filter = {p.strip().lower() for p in payload.providers if p and p.strip()}
    plan = helper_bootstrap_plan(
        checklist=checklist, include_configured=payload.include_configured, provider_filter=provider_filter
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "requested_providers": sorted(provider_filter),
        "include_configured": payload.include_configured,
        "steps_total": len(plan),
        "steps": plan,
        "next": {
            "run_checklist": "GET /search-everywhere/surfer/provider-checklist",
            "run_gate": "POST /search-everywhere/surfer/production-gate",
        },
        "generated_at": helper_now_iso(),
    }
