"""Search use cases: platform run provider probes."""

from ....deps import AuthContext
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushEnvTemplateRequest
from ..schemas import SemrushProviderProbeRequest
from .ahrefs_provider_probe_payload import helper_ahrefs_provider_requirements
from .platform_now_iso import helper_ace_inventory
from .platform_now_iso import helper_airanklab_wiring_required_keys
from .platform_now_iso import helper_build_unified_vendor_chart
from .platform_now_iso import helper_cms_inventory
from .platform_now_iso import helper_configured_provider_keys
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .platform_now_iso import helper_platform_inventory
from .platform_now_iso import helper_provider_probe_display
from .platform_now_iso import helper_provider_probe_payload
from .platform_now_iso import helper_vendor_report_csv
from .platform_search_vendors import helper_provider_requirements
from .platform_search_vendors import helper_search_vendors
from .surfer_provider_probe_payload import helper_surfer_provider_requirements
from typing import Any


def helper_run_provider_probes(auth: AuthContext, payload: SemrushProviderProbeRequest) -> dict[str, Any]:
    all_keys = ["dataforseo", "serper", "google_keyword_planner", "google_search_console"]
    requested = [p.strip().lower() for p in payload.providers if p and p.strip()]
    provider_keys = requested if requested else all_keys
    provider_keys = [key for key in provider_keys if key in all_keys]
    checklist = helper_provider_requirements()
    configured_keys = helper_configured_provider_keys(checklist)
    probes: list[dict[str, Any]] = []
    for provider_key in provider_keys:
        is_configured = provider_key in configured_keys
        if not is_configured and (not payload.include_unconfigured):
            probes.append(
                {
                    "provider": helper_provider_probe_display(provider_key),
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
                payload=helper_provider_probe_payload(provider_key, payload.max_results),
                tenant_id=auth.tenant_id,
            )
            keywords = list(result.get("keywords", []))
            probes.append(
                {
                    "provider": helper_provider_probe_display(provider_key),
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
                    "provider": helper_provider_probe_display(provider_key),
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
                    "provider": helper_provider_probe_display(provider_key),
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


def helper_env_template(payload: SemrushEnvTemplateRequest) -> dict[str, Any]:
    checklist = helper_provider_requirements()
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
        optional_missing = list(item.get("optional_missing", []))
        optional_present = list(item.get("optional_present", []))
        required_all = required_missing + required_present
        for env_name in required_all:
            if env_name in required_present and (not payload.include_configured):
                continue
            if env_name in required_missing:
                missing_keys.append(env_name)
            lines.append(f"{env_name}=")
        if payload.include_optional:
            optional_all = optional_missing + optional_present
            for env_name in optional_all:
                if env_name in optional_present and (not payload.include_configured):
                    continue
                lines.append(f"{env_name}=")
        lines.append("")
    content = "\n".join(lines).strip() + "\n" if lines else ""
    return {"providers_included": providers_included, "missing_keys": sorted(set(missing_keys)), "content": content}


def operation_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:vendors", 120, 60)
    integrations = helper_search_vendors()
    ace_inventory = helper_ace_inventory(runtime, auth.tenant_id)
    cms_inventory = helper_cms_inventory(runtime, auth.tenant_id)
    platform_inventory = helper_platform_inventory(runtime)
    unified_vendor_chart = helper_build_unified_vendor_chart(
        integrations, ace_inventory, cms_inventory, platform_inventory
    )
    configured = sum((1 for item in integrations if item.configured))
    total = len(integrations)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total": total,
        "configured": configured,
        "vendors": [item.model_dump() for item in integrations],
        "inventory_summary": {
            "search_everywhere": {"configured": configured, "total": total},
            "ai_crawler_enablement": {
                "configured_integrations": ace_inventory["configured_integrations"],
                "total_integrations": ace_inventory["total_integrations"],
                "sites": ace_inventory["sites"],
            },
            "cms": {
                "configured_integrations": cms_inventory["configured_integrations"],
                "total_integrations": cms_inventory["total_integrations"],
                "connections": cms_inventory["connections"],
            },
            "platform_integration": {
                "configured_integrations": platform_inventory["configured_integrations"],
                "total_integrations": platform_inventory["total_integrations"],
                "accounts_connected": platform_inventory["accounts_connected"],
            },
        },
        "domain_inventory": {
            "search_everywhere": {"vendors": [item.model_dump() for item in integrations]},
            "ai_crawler_enablement": ace_inventory,
            "cms": cms_inventory,
            "platform_integration": platform_inventory,
        },
        "unified_vendor_chart": unified_vendor_chart,
        "generated_at": helper_now_iso(),
    }


def operation_airanklab_wiring_required_keys(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:airanklab:wiring:required-keys", 60, 60)
    payload = helper_airanklab_wiring_required_keys()
    checklist = {
        "semrush": helper_provider_requirements(),
        "ahrefs": helper_ahrefs_provider_requirements(runtime, auth),
        "surfer": helper_surfer_provider_requirements(runtime, auth),
        "frase": helper_surfer_provider_requirements(runtime, auth),
    }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wiring_contract": payload,
        "current_checklists": checklist,
        "generated_at": helper_now_iso(),
    }


def helper_slice_provider_checklist(auth: AuthContext, force_configured: bool = False) -> dict[str, Any]:
    checklist = [dict(item) for item in helper_provider_requirements()]
    if force_configured:
        for item in checklist:
            item["configured"] = True
            item["required_missing"] = []
    configured = sum((1 for item in checklist if item.get("configured")))
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


def helper_build_vendor_report(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    vendors_payload = operation_vendors(runtime, auth)
    inventory_summary = vendors_payload.get("inventory_summary", {})
    unified_vendor_chart = [dict(item) for item in vendors_payload.get("unified_vendor_chart", [])]
    category_index: dict[str, dict[str, Any]] = {}
    for item in unified_vendor_chart:
        category = str(item.get("category") or "unknown")
        row = category_index.get(category)
        if row is None:
            row = {"category": category, "vendors": 0, "configured_units": 0, "total_units": 0}
            category_index[category] = row
        row["vendors"] = int(row.get("vendors", 0)) + 1
        row["configured_units"] = int(row.get("configured_units", 0)) + int(item.get("configured_units", 0) or 0)
        row["total_units"] = int(row.get("total_units", 0)) + int(item.get("total_units", 0) or 0)
    domain_chart: list[dict[str, Any]] = []
    for domain, summary in inventory_summary.items():
        configured_units = int(summary.get("configured_integrations", summary.get("configured", 0)) or 0)
        total_units = int(summary.get("total_integrations", summary.get("total", 0)) or 0)
        domain_chart.append(
            {
                "domain": domain,
                "configured_units": configured_units,
                "total_units": total_units,
                "coverage_pct": round(configured_units / max(total_units, 1) * 100.0, 1),
            }
        )
    category_chart = sorted(category_index.values(), key=lambda item: str(item.get("category", "")))
    export_rows = [
        {
            "source": str(item.get("source", "")),
            "vendor": str(item.get("vendor", "")),
            "category": str(item.get("category", "")),
            "integration": str(item.get("integration", "")),
            "configured_units": int(item.get("configured_units", 0) or 0),
            "total_units": int(item.get("total_units", 0) or 0),
            "runtime_dependency": bool(item.get("runtime_dependency")),
        }
        for item in unified_vendor_chart
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "domains": len(domain_chart),
            "vendors": len(unified_vendor_chart),
            "categories": len(category_chart),
        },
        "domain_chart": domain_chart,
        "category_chart": category_chart,
        "vendor_chart": unified_vendor_chart,
        "export_rows": export_rows,
        "generated_at": helper_now_iso(),
    }


def operation_readiness(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:readiness", 60, 60)
    vendors_payload = operation_vendors(runtime, auth)
    configured = int(vendors_payload["configured"])
    total = int(vendors_payload["total"])
    configured_pct = round(configured / max(total, 1) * 100.0, 1)
    unified_vendor_chart = vendors_payload.get("unified_vendor_chart", [])
    inventory_summary = vendors_payload.get("inventory_summary", {})
    grade = "A" if configured_pct >= 85 else "B" if configured_pct >= 65 else "C" if configured_pct >= 45 else "D"
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "readiness": {
            "configured_integrations": configured,
            "total_integrations": total,
            "configured_pct": configured_pct,
            "grade": grade,
            "production_ready": configured_pct >= 65,
        },
        "inventory_summary": inventory_summary,
        "cross_domain_inventory": {"unified_vendors": len(unified_vendor_chart), "domains": len(inventory_summary)},
        "checks": {
            "cloudflare_waf_sync": helper_env_configured("CLOUDFLARE_API_TOKEN"),
            "ssr_proxy_configured": helper_env_configured("SSR_PROXY_URL"),
            "ollama_configured": helper_env_configured("OLLAMA_BASE_URL"),
            "upstash_cache_configured": helper_env_configured("UPSTASH_REDIS_REST_URL")
            and helper_env_configured("UPSTASH_REDIS_REST_TOKEN"),
            "posthog_configured": helper_env_configured("POSTHOG_HOST") and helper_env_configured("POSTHOG_API_KEY"),
        },
        "generated_at": helper_now_iso(),
    }


def helper_vendor_report_export(runtime: SearchRuntime, auth: AuthContext, format: str) -> dict[str, Any]:
    report = helper_build_vendor_report(runtime, auth)
    export_rows = list(report.get("export_rows", []))
    if format == "csv":
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "format": format,
            "count": len(export_rows),
            "filename": f"vendor-inventory-report-{auth.tenant_id}.csv",
            "csv": helper_vendor_report_csv(export_rows),
            "generated_at": report["generated_at"],
        }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "format": format,
        "count": len(export_rows),
        "filename": f"vendor-inventory-report-{auth.tenant_id}.json",
        "json": export_rows,
        "generated_at": report["generated_at"],
    }
