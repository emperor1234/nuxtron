# pyright: reportUnusedFunction=false
"""
Tool Integrations Router — manage and status-check third-party tool connections.

Supported tools (20 total):
    PAYG/Paid: DataForSEO, Serper.dev, PromptWatch, GPT-4o/Claude, Cloudflare Pro, Deepgram
    Free:      ScreamingFrog SEO Spider, Google Analytics, Whisper, Google Business Profile,
                         Google Keyword Planner, Google Discover, Google Search Console,
                         Lighthouse, Playwright CDP, Web Vitals RUM, OpenSearch, Prometheus,
                         Grafana, Metabase

Endpoints:
  GET  /integrations/tools              - list all tools + their current status
  GET  /integrations/tools/{tool_key}   - detail for a single tool
  PUT  /integrations/tools/{tool_key}   - update config / API key
  POST /integrations/tools/{tool_key}/test - live connectivity test
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

FREE_OPEN_SOURCE = "Free (open-source)"

# ---------------------------------------------------------------------------
# Tool catalogue (single source of truth)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    # ── PAYG / Paid ──────────────────────────────────────────────────────────
    {
        "key": "dataforseo",
        "display_name": "DataForSEO",
        "category": "seo_data",
        "tier": "payg",
        "cost_label": "PAYG",
        "why": "Best SERP/keyword/backlink API",
        "env_key": "DATAFORSEO_API_KEY",
        "env_login": "DATAFORSEO_LOGIN",
        "test_url": "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        "docs_url": "https://docs.dataforseo.com/",
    },
    {
        "key": "serper",
        "display_name": "Serper.dev",
        "category": "seo_data",
        "tier": "payg",
        "cost_label": "PAYG",
        "why": "Cheap SERP API",
        "env_key": "SERPER_API_KEY",
        "test_url": "https://google.serper.dev/search",
        "docs_url": "https://serper.dev/",
    },
    {
        "key": "promptwatch",
        "display_name": "PromptWatch",
        "category": "observability",
        "tier": "paid",
        "cost_label": "£30–£50/mo",
        "why": "LLM observability",
        "env_key": "PROMPTWATCH_API_KEY",
        "test_url": "https://api.promptwatch.io/v1/health",
        "docs_url": "https://docs.promptwatch.io/",
    },
    {
        "key": "openai_gpt4o",
        "display_name": "GPT-4o / Claude",
        "category": "ai",
        "tier": "payg",
        "cost_label": "PAYG",
        "why": "Best reasoning",
        "env_key": "OPENAI_API_KEY",
        "env_secondary": "ANTHROPIC_API_KEY",
        "test_url": "https://api.openai.com/v1/models",
        "docs_url": "https://platform.openai.com/docs/",
    },
    {
        "key": "cloudflare_pro",
        "display_name": "Cloudflare Pro",
        "category": "security",
        "tier": "paid",
        "cost_label": "£20/mo",
        "why": "Security + speed",
        "env_key": "CLOUDFLARE_API_TOKEN",
        "env_zone": "CLOUDFLARE_ZONE_ID",
        "test_url": "https://api.cloudflare.com/client/v4/user/tokens/verify",
        "docs_url": "https://developers.cloudflare.com/",
    },
    {
        "key": "deepgram",
        "display_name": "Deepgram",
        "category": "speech",
        "tier": "payg",
        "cost_label": "PAYG",
        "why": "Speech/video intelligence",
        "env_key": "DEEPGRAM_API_KEY",
        "test_url": "https://api.deepgram.com/v1/auth/token",
        "docs_url": "https://developers.deepgram.com/",
    },
    # ── Free ─────────────────────────────────────────────────────────────────
    {
        "key": "screaming_frog",
        "display_name": "ScreamingFrog SEO Spider",
        "category": "seo_data",
        "tier": "free",
        "cost_label": "Free (500 URL limit)",
        "why": "Free tier is enough for technical SEO crawls",
        "env_key": "SCREAMING_FROG_LICENSE_KEY",  # optional paid licence key
        "test_url": None,  # desktop app, no public API
        "docs_url": "https://www.screamingfrog.co.uk/seo-spider/",
    },
    {
        "key": "google_analytics",
        "display_name": "Google Analytics",
        "category": "analytics",
        "tier": "free",
        "cost_label": "Free",
        "why": "Core analytics",
        "env_key": "GA4_MEASUREMENT_ID",
        "env_secondary": "GA4_API_SECRET",
        "test_url": None,
        "docs_url": "https://developers.google.com/analytics",
    },
    {
        "key": "whisper",
        "display_name": "Whisper (OpenAI)",
        "category": "speech",
        "tier": "free",
        "cost_label": "Free (self-hosted)",
        "why": "Open-source speech-to-text",
        "env_key": "WHISPER_MODEL_PATH",
        "test_url": None,
        "docs_url": "https://openai.com/research/whisper",
    },
    {
        "key": "google_business_profile",
        "display_name": "Google Business Profile",
        "category": "seo_data",
        "tier": "free",
        "cost_label": "Free",
        "why": "Required for Local SEO",
        "env_key": "GOOGLE_BUSINESS_API_KEY",
        "test_url": "https://mybusinessbusinessinformation.googleapis.com/v1/accounts",
        "docs_url": "https://developers.google.com/my-business",
    },
    {
        "key": "google_keyword_planner",
        "display_name": "Google Keyword Planner",
        "category": "seo_data",
        "tier": "free",
        "cost_label": "Free",
        "why": "PPC-grade keyword data",
        "env_key": "GOOGLE_ADS_DEVELOPER_TOKEN",
        "env_secondary": "GOOGLE_ADS_CUSTOMER_ID",
        "test_url": None,
        "docs_url": "https://developers.google.com/google-ads/api/",
    },
    {
        "key": "google_discover",
        "display_name": "Google Discover",
        "category": "analytics",
        "tier": "free",
        "cost_label": "Free",
        "why": "GSC Discover data for content performance",
        "env_key": "GSC_SERVICE_ACCOUNT_JSON",  # shared with GSC
        "test_url": None,
        "docs_url": "https://developers.google.com/search/docs/appearance/google-discover",
    },
    {
        "key": "google_search_console",
        "display_name": "Google Search Console",
        "category": "seo_data",
        "tier": "free",
        "cost_label": "Free",
        "why": "Mandatory — impressions, clicks, indexing",
        "env_key": "GSC_SERVICE_ACCOUNT_JSON",
        "env_secondary": "GSC_SITE_URL",
        "test_url": "https://searchconsole.googleapis.com/v1/sites",
        "docs_url": "https://developers.google.com/webmaster-tools",
    },
    {
        "key": "lighthouse",
        "display_name": "Google Lighthouse",
        "category": "performance",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Core GTmetrix-style performance audits",
        "env_key": "LIGHTHOUSE_CI_SERVER_URL",
        "test_url": None,
        "docs_url": "https://github.com/GoogleChrome/lighthouse",
    },
    {
        "key": "playwright_cdp",
        "display_name": "Playwright CDP Waterfall",
        "category": "performance",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Waterfall + filmstrip via Chrome DevTools Protocol",
        "env_key": "PLAYWRIGHT_CDP_ENABLED",
        "test_url": None,
        "docs_url": "https://playwright.dev/docs/api/class-cdpsession",
    },
    {
        "key": "web_vitals",
        "display_name": "Web Vitals RUM",
        "category": "performance",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Real-user CWV collection (LCP/CLS/INP/TTFB)",
        "env_key": "WEB_VITALS_ENABLED",
        "test_url": None,
        "docs_url": "https://github.com/GoogleChrome/web-vitals",
    },
    {
        "key": "opensearch",
        "display_name": "OpenSearch",
        "category": "observability",
        "tier": "free",
        "cost_label": "Free (self-hosted)",
        "why": "Waterfalls/logs/history indexing",
        "env_key": "OPENSEARCH_URL",
        "test_url": None,
        "docs_url": "https://opensearch.org/docs/latest/",
    },
    {
        "key": "prometheus",
        "display_name": "Prometheus",
        "category": "observability",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Performance metrics + alerting",
        "env_key": "PROMETHEUS_URL",
        "test_url": None,
        "docs_url": "https://prometheus.io/docs/introduction/overview/",
    },
    {
        "key": "grafana",
        "display_name": "Grafana",
        "category": "observability",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Dashboards and regression visualization",
        "env_key": "GRAFANA_URL",
        "test_url": None,
        "docs_url": "https://grafana.com/docs/",
    },
    {
        "key": "metabase",
        "display_name": "Metabase",
        "category": "analytics",
        "tier": "free",
        "cost_label": FREE_OPEN_SOURCE,
        "why": "Historical performance reporting",
        "env_key": "METABASE_URL",
        "test_url": None,
        "docs_url": "https://www.metabase.com/docs/latest/",
    },
]

_TOOL_MAP: dict[str, dict[str, Any]] = {t["key"]: t for t in TOOLS}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ToolConfigRequest(BaseModel):
    api_key: str = Field(default="", max_length=512)
    secondary_key: str = Field(default="", max_length=512)
    endpoint_override: str = Field(default="", max_length=512)
    notes: str = Field(default="", max_length=1000)
    config: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask(key: str) -> str:
    """Return last-4 chars mask, safe for storage."""
    if not key or len(key) < 4:
        return "****"
    return "****" + key[-4:]


def _configured(tool_key: str) -> bool:
    """True if the primary env var for this tool is non-empty."""
    spec = _TOOL_MAP.get(tool_key)
    if not spec:
        return False
    env_key = spec.get("env_key", "")
    return bool(os.getenv(env_key, "").strip())


def _tool_status(spec: dict[str, Any]) -> dict[str, Any]:
    key = spec["key"]
    env_val = os.getenv(spec.get("env_key", ""), "")
    configured = bool(env_val.strip())
    return {
        "key": key,
        "display_name": spec["display_name"],
        "category": spec["category"],
        "tier": spec["tier"],
        "cost_label": spec["cost_label"],
        "why": spec["why"],
        "configured": configured,
        "api_key_masked": _mask(env_val) if configured else None,
        "test_url": spec.get("test_url"),
        "docs_url": spec.get("docs_url"),
        "last_test_status": "untested",
    }


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_tool_integrations_router() -> APIRouter:
    router = APIRouter(prefix="/integrations", tags=["integrations"])

    @router.get("/tools")
    async def list_tools() -> dict[str, Any]:
        """List all configured tools with their configuration status."""
        tools_out = [_tool_status(spec) for spec in TOOLS]
        configured_count = sum(1 for t in tools_out if t["configured"])
        return {
            "total": len(tools_out),
            "configured": configured_count,
            "tools": tools_out,
        }

    @router.get("/tools/{tool_key}")
    async def get_tool(tool_key: str) -> dict[str, Any]:
        """Detail for a single tool."""
        spec = _TOOL_MAP.get(tool_key)
        if not spec:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_key}")
        return _tool_status(spec)

    @router.put("/integrations/tools/{tool_key}")
    async def update_tool_config(tool_key: str, body: ToolConfigRequest) -> dict[str, Any]:
        """
        Persist tool config — API keys are written to the runtime environment
        (in-process only; for production, use a secrets manager and restart).
        Only the masked key is returned.
        """
        spec = _TOOL_MAP.get(tool_key)
        if not spec:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_key}")
        if body.api_key:
            os.environ[spec["env_key"]] = body.api_key
        if body.secondary_key and spec.get("env_secondary"):
            os.environ[spec["env_secondary"]] = body.secondary_key
        return {
            "tool_key": tool_key,
            "configured": True,
            "api_key_masked": _mask(body.api_key) if body.api_key else None,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    @router.post("/tools/{tool_key}/test")
    async def test_tool(tool_key: str) -> dict[str, Any]:
        """
        Attempt a lightweight connectivity check against the tool's API.
        Returns status='ok'|'error'|'skipped'.
        """
        spec = _TOOL_MAP.get(tool_key)
        if not spec:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_key}")

        test_url: str | None = spec.get("test_url")
        if not test_url:
            return {
                "tool_key": tool_key,
                "status": "skipped",
                "reason": "No public API test endpoint (desktop/local tool)",
                "latency_ms": None,
                "tested_at": datetime.now(UTC).isoformat(),
            }

        # Build minimal headers depending on tool
        headers: dict[str, str] = {}
        env_val = os.getenv(spec.get("env_key", ""), "")

        if tool_key == "dataforseo":
            login = os.getenv("DATAFORSEO_LOGIN", "")
            if login and env_val:
                import base64
                token = base64.b64encode(f"{login}:{env_val}".encode()).decode()
                headers["Authorization"] = f"Basic {token}"
        elif tool_key == "serper":
            if env_val:
                headers["X-API-KEY"] = env_val
        elif tool_key == "openai_gpt4o" or tool_key == "cloudflare_pro":
            if env_val:
                headers["Authorization"] = f"Bearer {env_val}"
        elif tool_key == "deepgram":
            if env_val:
                headers["Authorization"] = f"Token {env_val}"
        elif tool_key == "promptwatch":
            if env_val:
                headers["Authorization"] = f"Bearer {env_val}"
        elif tool_key == "google_search_console":
            # OAuth not wired here; just check the endpoint is reachable
            pass
        elif tool_key == "google_business_profile":
            if env_val:
                headers["X-Goog-Api-Key"] = env_val

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(test_url, headers=headers)
            latency_ms = int((time.monotonic() - t0) * 1000)
            # 200/401/403 all mean the endpoint is reachable
            if resp.status_code < 500:
                return {
                    "tool_key": tool_key,
                    "status": "ok",
                    "http_status": resp.status_code,
                    "latency_ms": latency_ms,
                    "tested_at": datetime.now(UTC).isoformat(),
                }
            return {
                "tool_key": tool_key,
                "status": "error",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
                "tested_at": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.warning("Tool test failed for %s: %s", tool_key, exc)
            return {
                "tool_key": tool_key,
                "status": "error",
                "reason": str(exc),
                "latency_ms": latency_ms,
                "tested_at": datetime.now(UTC).isoformat(),
            }

    return router
