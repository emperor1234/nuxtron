"""Search use cases: ahrefs provider probe payload."""

from ....deps import AuthContext
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import AhrefsEnvTemplateRequest
from ..schemas import AhrefsProviderBootstrapRequest
from ..schemas import AhrefsProviderProbeRequest
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from typing import Any
from typing import cast


def helper_ahrefs_provider_probe_payload(provider_key: str, max_results: int) -> dict[str, Any]:
    if provider_key == "google_search_console":
        return {"seed_keyword": "", "location": "United States", "language": "en", "max_results": max_results}
    return {"seed_keyword": "seo analytics", "location": "United States", "language": "en", "max_results": max_results}


def helper_ahrefs_provider_probe_display(provider_key: str) -> str:
    labels = {
        "dataforseo": "DataForSEO",
        "serper": "Serper.dev",
        "google_keyword_planner": "Google Ads Keyword Planner",
        "google_search_console": "Google Search Console",
    }
    return labels.get(provider_key, provider_key)


def helper_ahrefs_configured_provider_keys(checklist: list[dict[str, Any]]) -> set[str]:
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


def helper_ahrefs_bootstrap_plan(
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
        plan.append(
            {
                "step": step_id,
                "provider": provider_name,
                "kind": str(item.get("kind", "integration")),
                "status": "configured" if item.get("configured") else "needs_configuration",
                "required_missing": list(item.get("required_missing", [])),
                "required_present": list(item.get("required_present", [])),
                "optional_present": list(item.get("optional_present", [])),
                "action": "Set missing required environment variables and then run production gate.",
                "verify_with": [
                    "GET /search-everywhere/ahrefs/provider-checklist",
                    "POST /search-everywhere/ahrefs/production-gate",
                ],
            }
        )
        step_id += 1
    return plan


def helper_ahrefs_provider_requirements(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    checklist = [
        {
            "provider": "DataForSEO",
            "kind": "keyword_provider",
            "required_env": ["DATAFORSEO_LOGIN", "DATAFORSEO_API_KEY"],
            "optional_env": [],
        },
        {"provider": "Serper.dev", "kind": "keyword_provider", "required_env": ["SERPER_API_KEY"], "optional_env": []},
        {
            "provider": "Google Ads Keyword Planner",
            "kind": "keyword_provider",
            "required_env": ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CUSTOMER_ID"],
            "optional_env": [
                "GOOGLE_OAUTH_ACCESS_TOKEN",
                "GOOGLE_ADS_ACCESS_TOKEN",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
            ],
        },
        {
            "provider": "Google Search Console",
            "kind": "keyword_provider",
            "required_env": ["GSC_SITE_URL"],
            "optional_env": [
                "GSC_SERVICE_ACCOUNT_JSON",
                "GOOGLE_OAUTH_ACCESS_TOKEN",
                "GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN",
            ],
        },
        {
            "provider": "Ahrefs API",
            "kind": "site_explorer_and_reporting",
            "required_env": ["AHREFS_API_TOKEN"],
            "optional_env": ["AHREFS_BASE_URL"],
        },
        {
            "provider": "Cloudflare",
            "kind": "crawler_enablement",
            "required_env": ["CLOUDFLARE_API_TOKEN"],
            "optional_env": [],
        },
        {
            "provider": "Nuxtron SSR Proxy",
            "kind": "crawler_enablement",
            "required_env": ["SSR_PROXY_URL"],
            "optional_env": [],
        },
        {
            "provider": "Upstash Redis",
            "kind": "cache",
            "required_env": ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"],
            "optional_env": [],
        },
        {
            "provider": "PostHog",
            "kind": "analytics",
            "required_env": ["POSTHOG_HOST", "POSTHOG_API_KEY"],
            "optional_env": [],
        },
        {"provider": "Sentry", "kind": "observability", "required_env": ["SENTRY_DSN"], "optional_env": []},
        {
            "provider": "OpenAI",
            "kind": "ai_insights",
            "required_env": ["OPENAI_API_KEY"],
            "optional_env": [],
            "configured_override": bool(runtime.vendor_manager.has_credentials("openai_api")),
        },
        {
            "provider": "Ollama",
            "kind": "ai_insights",
            "required_env": ["OLLAMA_BASE_URL"],
            "optional_env": ["SEO_AI_MODEL"],
        },
    ]
    output: list[dict[str, Any]] = []
    for item in checklist:
        row = cast(dict[str, Any], item)
        required = cast(list[str], row.get("required_env", []))
        optional = cast(list[str], row.get("optional_env", []))
        required_present = [env for env in required if helper_env_configured(env)]
        required_missing = [env for env in required if env not in required_present]
        optional_present = [env for env in optional if helper_env_configured(env)]
        has_optional_auth = len(optional_present) > 0
        if str(row.get("provider", "")) in {"Google Ads Keyword Planner", "Google Search Console"}:
            configured = len(required_missing) == 0 and has_optional_auth
        else:
            configured = len(required_missing) == 0
        configured_override = row.get("configured_override")
        if configured_override is not None:
            configured = bool(configured_override) or configured
        output.append(
            {
                "provider": row.get("provider", "unknown"),
                "kind": row.get("kind", "unknown"),
                "configured": configured,
                "required_present": required_present,
                "required_missing": required_missing,
                "optional_present": optional_present,
                "remediation": "Configure missing required env vars and validate strict-live probe.",
            }
        )
    return output


def helper_ahrefs_vendor_inventory(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    return [
        {
            "vendor": item["provider"],
            "module": item["kind"],
            "type": "integration",
            "configured": item["configured"],
            "evidence": "search_everywhere ahrefs provider checklist",
        }
        for item in checklist
    ]


def helper_ahrefs_run_provider_probes(
    runtime: SearchRuntime, auth: AuthContext, payload: AhrefsProviderProbeRequest
) -> dict[str, Any]:
    all_keys = ["dataforseo", "serper", "google_keyword_planner", "google_search_console"]
    requested = [p.strip().lower() for p in payload.providers if p and p.strip()]
    provider_keys = requested if requested else all_keys
    provider_keys = [key for key in provider_keys if key in all_keys]
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    configured_keys = helper_ahrefs_configured_provider_keys(checklist)
    probes: list[dict[str, Any]] = []
    for provider_key in provider_keys:
        is_configured = provider_key in configured_keys
        if not is_configured and (not payload.include_unconfigured):
            probes.append(
                {
                    "provider": helper_ahrefs_provider_probe_display(provider_key),
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
                payload=helper_ahrefs_provider_probe_payload(provider_key, payload.max_results),
                tenant_id=auth.tenant_id,
            )
            keywords = list(result.get("keywords", []))
            probes.append(
                {
                    "provider": helper_ahrefs_provider_probe_display(provider_key),
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
                    "provider": helper_ahrefs_provider_probe_display(provider_key),
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
                    "provider": helper_ahrefs_provider_probe_display(provider_key),
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


def helper_ahrefs_env_template(
    runtime: SearchRuntime, auth: AuthContext, payload: AhrefsEnvTemplateRequest
) -> dict[str, Any]:
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
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


def operation_ahrefs_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:provider-checklist", 60, 60)
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
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


def operation_ahrefs_provider_bootstrap(
    runtime: SearchRuntime, payload: AhrefsProviderBootstrapRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:provider-bootstrap", 60, 60)
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    provider_filter = {p.strip().lower() for p in payload.providers if p and p.strip()}
    plan = helper_ahrefs_bootstrap_plan(
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
            "run_checklist": "GET /search-everywhere/ahrefs/provider-checklist",
            "run_gate": "POST /search-everywhere/ahrefs/production-gate",
        },
        "generated_at": helper_now_iso(),
    }
