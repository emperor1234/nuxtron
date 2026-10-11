"""Search use cases: platform now iso."""

from ..runtime import SearchRuntime
from ..schemas import VendorStatus
from ..values import coerce_int as _coerce_int
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
import os


def helper_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def helper_env_configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def helper_ace_inventory(runtime: SearchRuntime, tenant_id: str) -> dict[str, Any]:
    tenant_sites = [s.copy() for s in runtime.ace_sites_memory if s.get("tenant_id") == tenant_id]
    operation_vendors = [
        {
            "vendor": "Nuxtron CDN",
            "category": "delivery",
            "integration": "snippet_loader",
            "configured_units": len(tenant_sites),
            "total_units": len(tenant_sites),
            "runtime_dependency": True,
        },
        {
            "vendor": "Cloudflare",
            "category": "security",
            "integration": "cloudflare_firewall_rules_api",
            "configured_units": sum((1 for s in tenant_sites if bool(s.get("cloudflare_zone_id")))),
            "total_units": len(tenant_sites),
            "runtime_dependency": False,
        },
        {
            "vendor": "CMS/Platform Webhook",
            "category": "deployment",
            "integration": "deployment_webhook",
            "configured_units": sum((1 for s in tenant_sites if bool(s.get("deployment_webhook_url")))),
            "total_units": len(tenant_sites),
            "runtime_dependency": False,
        },
    ]
    return {
        "sites": len(tenant_sites),
        "vendors": operation_vendors,
        "configured_integrations": sum((_coerce_int(v.get("configured_units", 0)) for v in operation_vendors)),
        "total_integrations": sum((_coerce_int(v.get("total_units", 0)) for v in operation_vendors)),
    }


def helper_cms_inventory(runtime: SearchRuntime, tenant_id: str) -> dict[str, Any]:
    connections = [c.copy() for c in runtime.cms_connections_memory if c.get("tenant_id") == tenant_id]
    total_connections = len(connections)
    operation_vendors = [
        {
            "vendor": "CMS APIs",
            "category": "cms",
            "integration": "cms_api",
            "configured_units": sum((1 for c in connections if bool(c.get("api_key_configured")))),
            "total_units": total_connections,
            "runtime_dependency": True,
        },
        {
            "vendor": "CRM Bridge",
            "category": "crm",
            "integration": "crm_attribution_bridge",
            "configured_units": total_connections,
            "total_units": total_connections,
            "runtime_dependency": False,
        },
        {
            "vendor": "Crawler Analytics",
            "category": "analytics",
            "integration": "analytics_events",
            "configured_units": total_connections,
            "total_units": total_connections,
            "runtime_dependency": False,
        },
    ]
    return {
        "connections": total_connections,
        "vendors": operation_vendors,
        "configured_integrations": sum((_coerce_int(v.get("configured_units", 0)) for v in operation_vendors)),
        "total_integrations": sum((_coerce_int(v.get("total_units", 0)) for v in operation_vendors)),
    }


def helper_platform_inventory(runtime: SearchRuntime) -> dict[str, Any]:
    platform_vendor_map = {
        "twitter": ("twitter_api", "X / Twitter API"),
        "facebook": ("meta_graph_api", "Meta Graph API"),
        "instagram": ("meta_graph_api", "Meta Graph API"),
        "linkedin": ("linkedin_api", "LinkedIn API"),
        "tiktok": ("tiktok_api", "TikTok Business API"),
    }
    operation_vendors: list[dict[str, Any]] = []
    for platform, (vendor_id, display_name) in platform_vendor_map.items():
        credentials = runtime.vendor_manager.get_credentials(vendor_id)
        operation_vendors.append(
            {
                "vendor": display_name,
                "category": "social_media",
                "integration": platform,
                "configured_units": 1 if credentials is not None else 0,
                "total_units": 1,
                "runtime_dependency": True,
                "has_refresh_token": bool(credentials.refresh_token) if credentials else False,
            }
        )
    return {
        "accounts_connected": sum((int(v["configured_units"]) for v in operation_vendors)),
        "vendors": operation_vendors,
        "configured_integrations": sum((int(v["configured_units"]) for v in operation_vendors)),
        "total_integrations": sum((int(v["total_units"]) for v in operation_vendors)),
    }


def helper_build_unified_vendor_chart(
    search_vendors: list[VendorStatus],
    ace_inventory: dict[str, Any],
    cms_inventory: dict[str, Any],
    platform_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    chart: list[dict[str, Any]] = []
    for vendor in search_vendors:
        chart.append(
            {
                "vendor": vendor.display_name,
                "source": "search_everywhere",
                "category": vendor.category,
                "integration": vendor.key,
                "configured_units": 1 if vendor.configured else 0,
                "total_units": 1,
                "runtime_dependency": vendor.mode in {"api", "sdk"},
            }
        )
    for source_name, inventory in (
        ("ai_crawler_enablement", ace_inventory),
        ("cms", cms_inventory),
        ("platform_integration", platform_inventory),
    ):
        for vendor in inventory.get("vendors", []):
            chart.append({**vendor, "source": source_name})
    chart.sort(key=lambda item: (str(item.get("source", "")), str(item.get("vendor", ""))))
    return chart


def helper_vendor_report_csv(export_rows: list[dict[str, Any]]) -> str:
    if not export_rows:
        return ""
    headers = ["source", "vendor", "category", "integration", "configured_units", "total_units", "runtime_dependency"]
    lines = [",".join(headers)]
    for row in export_rows:
        values: list[str] = []
        for key in headers:
            value = str(row.get(key, "")).replace('"', '""')
            values.append(f'"{value}"')
        lines.append(",".join(values))
    return "\n".join(lines)


def helper_bootstrap_plan(
    checklist: list[dict[str, Any]], include_configured: bool, provider_filter: set[str]
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    step_id = 1
    for item in checklist:
        provider_name = str(item.get("provider", "")).strip()
        if provider_filter and provider_name.lower() not in provider_filter:
            continue
        if not include_configured and item.get("configured"):
            continue
        required_missing = list(item.get("required_missing", []))
        required_present = list(item.get("required_present", []))
        optional_present = list(item.get("optional_present", []))
        kind = str(item.get("kind", "integration"))
        plan.append(
            {
                "step": step_id,
                "provider": provider_name,
                "kind": kind,
                "status": "configured" if item.get("configured") else "needs_configuration",
                "required_missing": required_missing,
                "required_present": required_present,
                "optional_present": optional_present,
                "action": "Set missing required environment variables and then run production gate.",
                "verify_with": [
                    "GET /search-everywhere/semrush/provider-checklist",
                    "POST /search-everywhere/semrush/production-gate",
                ],
            }
        )
        step_id += 1
    return plan


def helper_provider_probe_payload(provider_key: str, max_results: int) -> dict[str, Any]:
    if provider_key == "google_search_console":
        return {"seed_keyword": "", "location": "United States", "language": "en", "max_results": max_results}
    return {
        "seed_keyword": "social media management",
        "location": "United States",
        "language": "en",
        "max_results": max_results,
    }


def helper_provider_probe_display(provider_key: str) -> str:
    labels = {
        "dataforseo": "DataForSEO",
        "serper": "Serper.dev",
        "google_keyword_planner": "Google Ads Keyword Planner",
        "google_search_console": "Google Search Console",
    }
    return labels.get(provider_key, provider_key)


def helper_configured_provider_keys(checklist: list[dict[str, Any]]) -> set[str]:
    reverse = {
        "DataForSEO": "dataforseo",
        "Serper.dev": "serper",
        "Google Ads Keyword Planner": "google_keyword_planner",
        "Google Search Console": "google_search_console",
    }
    configured: set[str] = set()
    for item in checklist:
        if not item.get("configured"):
            continue
        key = reverse.get(str(item.get("provider", "")), "")
        if key:
            configured.add(key)
    return configured


def helper_airanklab_wiring_required_keys() -> dict[str, Any]:
    common_keys = {
        "DATAFORSEO_LOGIN",
        "DATAFORSEO_API_KEY",
        "SERPER_API_KEY",
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
        "GSC_SITE_URL",
        "CLOUDFLARE_API_TOKEN",
        "SSR_PROXY_URL",
        "POSTHOG_HOST",
        "POSTHOG_API_KEY",
        "SENTRY_DSN",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "AHREFS_API_TOKEN",
        "OPENAI_API_KEY",
        "OLLAMA_BASE_URL",
        "WORDPRESS_SITE_URL",
        "WORDPRESS_APP_PASSWORD",
        "CONTENTFUL_SPACE_ID",
        "CONTENTFUL_ACCESS_TOKEN",
        "ZAPIER_WEBHOOK_URL",
    }
    option_groups = [
        {
            "name": "google_ads_auth",
            "one_of": [
                "GOOGLE_OAUTH_ACCESS_TOKEN",
                "GOOGLE_ADS_ACCESS_TOKEN",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
            ],
        },
        {
            "name": "google_search_console_auth",
            "one_of": ["GSC_SERVICE_ACCOUNT_JSON", "GOOGLE_OAUTH_ACCESS_TOKEN", "GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN"],
        },
    ]
    optional_keys = {"SEO_AI_MODEL", "WORDPRESS_USERNAME", "CONTENTFUL_ENVIRONMENT", "AHREFS_BASE_URL"}
    allowlist = sorted(common_keys | optional_keys | {key for group in option_groups for key in group["one_of"]})
    return {
        "required_keys": sorted(common_keys),
        "optional_keys": sorted(optional_keys),
        "option_groups": option_groups,
        "allowlist": allowlist,
    }


def helper_slice_project_lookup(
    memory: list[dict[str, Any]], tenant_id: str, project_id: str, code: str
) -> dict[str, Any]:
    project = next(
        (item for item in memory if item.get("tenant_id") == tenant_id and item.get("id") == project_id), None
    )
    if project is None:
        raise HTTPException(status_code=404, detail={"code": code, "project_id": project_id})
    return project


def helper_slice_run_lookup(memory: list[dict[str, Any]], tenant_id: str, run_id: str, code: str) -> dict[str, Any]:
    run = next((item for item in memory if item.get("tenant_id") == tenant_id and item.get("id") == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": code, "run_id": run_id})
    return run


def helper_shopify_credentials() -> tuple[str, str]:
    domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
    token = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
    if not domain or not token:
        raise HTTPException(
            status_code=412,
            detail={
                "code": "shopify_not_configured",
                "message": "SHOPIFY_SHOP_DOMAIN and SHOPIFY_ACCESS_TOKEN are required.",
            },
        )
    return (domain, token)


def helper_tenant_scoped_hubspot_store(store: dict[str, list[dict[str, Any]]], tenant_id: str) -> list[dict[str, Any]]:
    if tenant_id not in store:
        store[tenant_id] = []
    return store[tenant_id]
