"""Search use cases: surfer provider probe payload."""

from ....deps import AuthContext
from ..runtime import SearchRuntime
from .platform_now_iso import helper_env_configured
from typing import Any
from typing import cast


def helper_surfer_provider_probe_payload(provider_key: str, max_results: int) -> dict[str, Any]:
    if provider_key == "google_search_console":
        return {"seed_keyword": "", "location": "United States", "language": "en", "max_results": max_results}
    return {
        "seed_keyword": "social media management",
        "location": "United States",
        "language": "en",
        "max_results": max_results,
    }


def helper_surfer_provider_probe_display(provider_key: str) -> str:
    labels = {
        "dataforseo": "DataForSEO",
        "serper": "Serper.dev",
        "google_keyword_planner": "Google Ads Keyword Planner",
        "google_search_console": "Google Search Console",
    }
    return labels.get(provider_key, provider_key)


def helper_surfer_configured_provider_keys(checklist: list[dict[str, Any]]) -> set[str]:
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


def helper_surfer_provider_priority(provider: str, kind: str) -> tuple[str, str, int]:
    provider_key = provider.strip().lower()
    if provider_key in {"dataforseo", "serper.dev", "google ads keyword planner", "google search console"}:
        return ("P0", "Required for strict-live keyword probes and production gate progress.", 100)
    if provider_key in {"openai", "ollama"}:
        return ("P1", "Required for AI-assisted content generation and optimization workflows.", 70)
    if provider_key in {"posthog", "sentry", "upstash redis"}:
        return ("P1", "Required for observability, analytics, and runtime reliability in production.", 60)
    if kind in {"publishing_integration", "automation_integration"}:
        return ("P2", "Required for publishing and orchestration automation completeness.", 40)
    return ("P2", "Recommended for full platform completeness.", 30)


def helper_surfer_provider_setup_notes(provider: str) -> list[str]:
    key = provider.strip().lower()
    notes_map = {
        "dataforseo": [
            "Create DataForSEO account credentials and whitelist your backend egress IPs.",
            "Set both login and API key as environment variables.",
        ],
        "serper.dev": [
            "Create Serper.dev key and set usage limits for production safety.",
            "Store the API key in backend runtime environment.",
        ],
        "google ads keyword planner": [
            "Configure Google Ads developer token and customer ID.",
            "Set OAuth token flow for API access before strict-live probes.",
        ],
        "google search console": [
            "Set verified site URL in Search Console.",
            "Configure service account JSON or OAuth token for API access.",
        ],
        "openai": [
            "Create production-scoped OpenAI key with usage caps.",
            "Store key in secret manager and runtime env.",
        ],
        "ollama": [
            "Deploy Ollama endpoint reachable by FastAPI runtime.",
            "Set model name and timeout defaults for predictable behavior.",
        ],
        "wordpress": [
            "Create WordPress application password for publishing account.",
            "Register CMS connection via /cms/connections for tenant-scoped readiness.",
        ],
        "contentful": [
            "Create Contentful delivery/management token pair.",
            "Register CMS connection via /cms/connections for tenant-scoped readiness.",
        ],
        "zapier": [
            "Create Zapier webhook endpoint for automation handoff.",
            "Set retry and dead-letter handling in workflow.",
        ],
        "posthog": ["Configure PostHog host and project API key.", "Validate event ingestion using readiness checks."],
        "sentry": [
            "Create Sentry project DSN for backend environment.",
            "Enable release and environment tagging for triage.",
        ],
        "upstash redis": [
            "Create Upstash Redis REST URL/token pair.",
            "Set low network timeout for resilient cache behavior.",
        ],
    }
    return notes_map.get(key, ["Configure required provider credentials and run preflight checks."])


def helper_surfer_provider_verify_endpoints(provider: str) -> list[str]:
    key = provider.strip().lower()
    if key in {"dataforseo", "serper.dev", "google ads keyword planner", "google search console"}:
        return ["POST /search-everywhere/surfer/provider-probes", "POST /search-everywhere/surfer/production-gate"]
    return ["GET /search-everywhere/surfer/provider-checklist", "GET /search-everywhere/surfer/wiring-plan"]


def helper_surfer_provider_preflight_commands(required_missing: list[str]) -> list[str]:
    commands: list[str] = []
    for env_name in required_missing:
        commands.append(f"Test-Path Env:{env_name}")
        commands.append(f'if (-not $env:{env_name}) {{ Write-Output "MISSING:{env_name}" }}')
    return commands


def helper_surfer_provider_requirements(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    tenant_connections = [c.copy() for c in runtime.cms_connections_memory if c.get("tenant_id") == auth.tenant_id]
    has_wordpress_connection = any(
        (
            str(conn.get("cms_type", "")).strip().lower() == "wordpress" and bool(conn.get("api_key_configured"))
            for conn in tenant_connections
        )
    )
    has_contentful_connection = any(
        (
            str(conn.get("cms_type", "")).strip().lower() == "contentful" and bool(conn.get("api_key_configured"))
            for conn in tenant_connections
        )
    )
    requirements = [
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
            "provider": "Ollama",
            "kind": "ai_content_generation",
            "required_env": ["OLLAMA_BASE_URL"],
            "optional_env": ["SEO_AI_MODEL"],
        },
        {
            "provider": "OpenAI",
            "kind": "ai_content_generation",
            "required_env": ["OPENAI_API_KEY"],
            "optional_env": [],
            "configured_override": bool(runtime.vendor_manager.has_credentials("openai_api")),
        },
        {
            "provider": "WordPress",
            "kind": "publishing_integration",
            "required_env": ["WORDPRESS_SITE_URL", "WORDPRESS_APP_PASSWORD"],
            "optional_env": ["WORDPRESS_USERNAME"],
            "configured_override": has_wordpress_connection,
        },
        {
            "provider": "Contentful",
            "kind": "publishing_integration",
            "required_env": ["CONTENTFUL_SPACE_ID", "CONTENTFUL_ACCESS_TOKEN"],
            "optional_env": ["CONTENTFUL_ENVIRONMENT"],
            "configured_override": has_contentful_connection,
        },
        {
            "provider": "Zapier",
            "kind": "automation_integration",
            "required_env": ["ZAPIER_WEBHOOK_URL"],
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
            "provider": "Upstash Redis",
            "kind": "cache",
            "required_env": ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"],
            "optional_env": [],
        },
    ]
    output: list[dict[str, Any]] = []
    for item in requirements:
        row = cast(dict[str, Any], item)
        required = cast(list[str], row.get("required_env", []))
        optional = cast(list[str], row.get("optional_env", []))
        required_present = [env for env in required if helper_env_configured(env)]
        required_missing = [env for env in required if env not in required_present]
        optional_present = [env for env in optional if helper_env_configured(env)]
        optional_missing = [env for env in optional if env not in optional_present]
        has_optional_auth = len(optional_present) > 0
        if str(row.get("provider", "")) in {"Google Ads Keyword Planner", "Google Search Console"}:
            configured = len(required_missing) == 0 and has_optional_auth
        else:
            configured = len(required_missing) == 0
        configured_override = row.get("configured_override")
        if configured_override is not None:
            configured = bool(configured_override) or configured
        remediation = "Configure missing required env vars and validate strict-live probe."
        provider_name = str(row.get("provider", ""))
        if provider_name == "Google Ads Keyword Planner":
            remediation = "Set required Google Ads env vars and provide OAuth access token or refresh token + client id/client secret, then validate strict-live probe."
        elif provider_name == "Google Search Console":
            remediation = "Set GSC site URL and provide service-account JSON or OAuth token/refresh token, then validate strict-live probe."
        output.append(
            {
                "provider": row.get("provider", "unknown"),
                "kind": row.get("kind", "unknown"),
                "configured": configured,
                "required_present": required_present,
                "required_missing": required_missing,
                "optional_present": optional_present,
                "optional_missing": optional_missing,
                "remediation": remediation,
            }
        )
    return output
