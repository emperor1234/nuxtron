# pyright: reportUnusedFunction=false
"""
AI Crawler Enablement Platform — Alli AI parity.

Enables AI search crawlers (GPTBot, ClaudeBot, PerplexityBot, and 50+ others)
to access JavaScript-rendered sites by providing:

  1. Site registration and JS snippet generation
  2. SSR / pre-rendering proxy integration (configurable via SSR_PROXY_URL)
  3. Real-time crawler activity tracking and analytics dashboard
  4. Cloudflare / WAF whitelist management (via Cloudflare API)
  5. Per-site crawler access rules (allow / deny / prioritize)
  6. Visibility audit — detect what AI crawlers can and cannot see
  7. Bulk snippet deployment across the site portfolio

Endpoints
---------
POST   /ai-crawler/sites                     – Register a new site
GET    /ai-crawler/sites                     – List registered sites
DELETE /ai-crawler/sites/{site_id}           – Unregister a site

GET    /ai-crawler/sites/{site_id}/snippet   – Get JS snippet for a site
POST   /ai-crawler/sites/{site_id}/snippet/verify – Verify snippet is installed

GET    /ai-crawler/crawlers                  – List known AI/search crawlers
POST   /ai-crawler/crawlers/detect           – Detect crawler from User-Agent

POST   /ai-crawler/events                    – Ingest a crawler visit event
GET    /ai-crawler/events                    – Get recent crawler events (real-time feed)
GET    /ai-crawler/dashboard                 – Aggregate crawler analytics dashboard

POST   /ai-crawler/ssr/render                – Request SSR pre-render of a URL
GET    /ai-crawler/ssr/cache                 – List cached SSR renders

POST   /ai-crawler/cloudflare/sync           – Sync AI crawler whitelist to Cloudflare WAF
GET    /ai-crawler/cloudflare/status         – Check Cloudflare WAF rule status

POST   /ai-crawler/rules                     – Create a crawler access rule
GET    /ai-crawler/rules                     – List rules for a site
DELETE /ai-crawler/rules/{rule_id}           – Delete a rule

POST   /ai-crawler/audit                     – Run a visibility audit on a URL
GET    /ai-crawler/audit/{audit_id}          – Get audit results
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

# ---------------------------------------------------------------------------
# Known AI / search crawler user-agent patterns
# Source: public bot documentation + crawl logs
# ---------------------------------------------------------------------------
KNOWN_CRAWLERS: list[dict[str, Any]] = [
    # AI Search platforms
    {"name": "GPTBot", "owner": "OpenAI", "ua_pattern": r"GPTBot", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "ClaudeBot", "owner": "Anthropic", "ua_pattern": r"ClaudeBot|Claude-Web", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "PerplexityBot", "owner": "Perplexity", "ua_pattern": r"PerplexityBot", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "GoogleExtendedBot", "owner": "Google", "ua_pattern": r"Google-Extended", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "CohereBot", "owner": "Cohere", "ua_pattern": r"cohere-ai", "category": "ai_search", "enabled": True, "priority": "medium"},
    {"name": "YouBot", "owner": "You.com", "ua_pattern": r"YouBot", "category": "ai_search", "enabled": True, "priority": "medium"},
    {"name": "BingBot-AI", "owner": "Microsoft", "ua_pattern": r"bingbot.*copilot|msnbot.*copilot", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "PetalBot", "owner": "Huawei", "ua_pattern": r"PetalBot", "category": "ai_search", "enabled": True, "priority": "low"},
    {"name": "OmgiliBot", "owner": "Omgili", "ua_pattern": r"omgilibot", "category": "ai_search", "enabled": True, "priority": "low"},
    {"name": "BrightbotAI", "owner": "Brightbot", "ua_pattern": r"BrightBot", "category": "ai_search", "enabled": True, "priority": "low"},
    {"name": "MetaExternalAgent", "owner": "Meta", "ua_pattern": r"meta-externalagent", "category": "ai_search", "enabled": True, "priority": "high"},
    {"name": "TikTokBot", "owner": "TikTok", "ua_pattern": r"Bytespider|TikTokBot", "category": "ai_search", "enabled": True, "priority": "medium"},
    {"name": "AppleBot-Extended", "owner": "Apple", "ua_pattern": r"Applebot-Extended", "category": "ai_search", "enabled": True, "priority": "medium"},
    {"name": "iAskBot", "owner": "iAsk.ai", "ua_pattern": r"iaskspider", "category": "ai_search", "enabled": True, "priority": "low"},
    {"name": "NeevaBot", "owner": "Neeva", "ua_pattern": r"NeevaBot", "category": "ai_search", "enabled": False, "priority": "low"},
    # Traditional search engines (also serve AI overviews)
    {"name": "Googlebot", "owner": "Google", "ua_pattern": r"Googlebot(?!-Image|-Video|-News|-Mobile)", "category": "search", "enabled": True, "priority": "high"},
    {"name": "Bingbot", "owner": "Microsoft", "ua_pattern": r"bingbot", "category": "search", "enabled": True, "priority": "high"},
    {"name": "DuckDuckBot", "owner": "DuckDuckGo", "ua_pattern": r"DuckDuckBot", "category": "search", "enabled": True, "priority": "medium"},
    {"name": "Slurp", "owner": "Yahoo", "ua_pattern": r"Yahoo! Slurp", "category": "search", "enabled": True, "priority": "medium"},
    {"name": "YandexBot", "owner": "Yandex", "ua_pattern": r"YandexBot", "category": "search", "enabled": True, "priority": "medium"},
    {"name": "Baiduspider", "owner": "Baidu", "ua_pattern": r"Baiduspider", "category": "search", "enabled": True, "priority": "medium"},
    {"name": "SemrushBot", "owner": "Semrush", "ua_pattern": r"SemrushBot", "category": "seo_tool", "enabled": True, "priority": "low"},
    {"name": "AhrefsBot", "owner": "Ahrefs", "ua_pattern": r"AhrefsBot", "category": "seo_tool", "enabled": True, "priority": "low"},
    {"name": "MajesticBot", "owner": "Majestic", "ua_pattern": r"MJ12bot", "category": "seo_tool", "enabled": True, "priority": "low"},
    {"name": "DataForSeoBot", "owner": "DataForSeo", "ua_pattern": r"DataForSeoBot", "category": "seo_tool", "enabled": True, "priority": "low"},
    # Content aggregators / AI training
    {"name": "CCBot", "owner": "Common Crawl", "ua_pattern": r"CCBot", "category": "ai_training", "enabled": True, "priority": "low"},
    {"name": "FacebookExternalHit", "owner": "Meta", "ua_pattern": r"facebookexternalhit", "category": "social", "enabled": True, "priority": "medium"},
    {"name": "TwitterBot", "owner": "Twitter/X", "ua_pattern": r"Twitterbot", "category": "social", "enabled": True, "priority": "medium"},
    {"name": "LinkedInBot", "owner": "LinkedIn", "ua_pattern": r"LinkedInBot", "category": "social", "enabled": True, "priority": "medium"},
    {"name": "WhatsApp", "owner": "Meta", "ua_pattern": r"WhatsApp", "category": "social", "enabled": True, "priority": "medium"},
    {"name": "TelegramBot", "owner": "Telegram", "ua_pattern": r"TelegramBot", "category": "social", "enabled": True, "priority": "low"},
    # Monitoring / uptime
    {"name": "UptimeRobot", "owner": "UptimeRobot", "ua_pattern": r"UptimeRobot", "category": "monitoring", "enabled": False, "priority": "low"},
    {"name": "Pingdom", "owner": "Pingdom", "ua_pattern": r"Pingdom", "category": "monitoring", "enabled": False, "priority": "low"},
    # Academic / Research
    {"name": "PaperliBot", "owner": "Paper.li", "ua_pattern": r"PaperliBot", "category": "research", "enabled": True, "priority": "low"},
    {"name": "ScoutJet", "owner": "Exalead", "ua_pattern": r"ScoutJet", "category": "research", "enabled": True, "priority": "low"},
]

_CRAWLER_COMPILED = [
    {**c, "_re": re.compile(c["ua_pattern"], re.IGNORECASE)}
    for c in KNOWN_CRAWLERS
]


def _detect_crawler(user_agent: str) -> dict[str, Any] | None:
    """Return first matching crawler record or None if no match."""
    for crawler in _CRAWLER_COMPILED:
        if crawler["_re"].search(user_agent):
            return {k: v for k, v in crawler.items() if k != "_re"}
    return None


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SiteRegisterRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253, description="Root domain, e.g. example.com")
    display_name: str = Field(min_length=1, max_length=120)
    cms_type: Literal[
        "wordpress", "shopify", "wix", "webflow", "next_js", "nuxt",
        "angular", "vue", "react", "gatsby", "hugo", "jekyll", "custom"
    ] = "custom"
    js_framework: Literal["none", "react", "vue", "angular", "next", "nuxt", "svelte", "other"] = "none"
    cloudflare_zone_id: str | None = Field(default=None, max_length=40)
    deployment_webhook_url: HttpUrl | None = Field(default=None, description="Optional CMS/platform webhook for automated snippet deployment")


class SnippetVerifyRequest(BaseModel):
    page_url: str = Field(min_length=10, max_length=2048)


class CrawlerDetectRequest(BaseModel):
    user_agent: str = Field(min_length=1, max_length=1024)


class CrawlerEventIngestRequest(BaseModel):
    site_id: str = Field(min_length=1, max_length=80)
    crawler_name: str = Field(min_length=1, max_length=120)
    page_url: str = Field(min_length=1, max_length=2048)
    user_agent: str | None = Field(default=None, max_length=1024)
    status_code: int = Field(default=200, ge=100, le=599)
    response_type: Literal["ssr", "cached", "live", "blocked", "error"] = "live"
    render_time_ms: int = Field(default=0, ge=0, le=120000)
    ip_address: str | None = Field(default=None, max_length=64)


class SsrRenderRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    site_id: str = Field(min_length=1, max_length=80)
    crawler_hint: str | None = Field(default=None, max_length=120)
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    force_refresh: bool = False


class CloudflareSyncRequest(BaseModel):
    site_id: str = Field(min_length=1, max_length=80)
    action: Literal["allow_ai_crawlers", "block_ai_crawlers", "reset"] = "allow_ai_crawlers"


class CloudflareAutoSyncRequest(BaseModel):
    site_ids: list[str] = Field(default_factory=list, max_length=500, description="Empty = all registered tenant sites")
    action: Literal["allow_ai_crawlers", "block_ai_crawlers", "reset"] = "allow_ai_crawlers"
    dry_run: bool = False


class BulkSnippetDeployRequest(BaseModel):
    site_ids: list[str] = Field(default_factory=list, max_length=500, description="Empty = all registered tenant sites")
    dry_run: bool = Field(default=False, description="If true, only compute deployment plan")


class CrawlerRuleRequest(BaseModel):
    site_id: str = Field(min_length=1, max_length=80)
    crawler_name: str = Field(min_length=1, max_length=120)
    rule: Literal["allow", "deny", "ssr_only", "rate_limit"] = "allow"
    rate_limit_rpm: int | None = Field(default=None, ge=1, le=10000)
    note: str | None = Field(default=None, max_length=500)


class VisibilityAuditRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    site_id: str | None = Field(default=None, max_length=80)
    crawlers_to_test: list[str] = Field(
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"],
        max_length=20,
    )


class AutomationRunRequest(BaseModel):
    site_id: str = Field(min_length=1, max_length=80)
    page_url: str = Field(min_length=10, max_length=2048)
    dry_run: bool = False
    deploy_snippet: bool = True
    verify_snippet: bool = True
    sync_cloudflare: bool = True
    cloudflare_action: Literal["allow_ai_crawlers", "block_ai_crawlers", "reset"] = "allow_ai_crawlers"
    run_visibility_audit: bool = True
    crawlers_to_test: list[str] = Field(
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"],
        max_length=20,
    )


class AutomationScheduleCreateRequest(BaseModel):
    site_id: str = Field(min_length=1, max_length=80)
    page_url: str = Field(min_length=10, max_length=2048)
    interval_minutes: int = Field(default=60, ge=5, le=10080)
    enabled: bool = True
    deploy_snippet: bool = True
    verify_snippet: bool = True
    sync_cloudflare: bool = True
    cloudflare_action: Literal["allow_ai_crawlers", "block_ai_crawlers", "reset"] = "allow_ai_crawlers"
    run_visibility_audit: bool = True
    crawlers_to_test: list[str] = Field(
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"],
        max_length=20,
    )


class AutomationScheduleUpdateRequest(BaseModel):
    page_url: str | None = Field(default=None, min_length=10, max_length=2048)
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    enabled: bool | None = None
    deploy_snippet: bool | None = None
    verify_snippet: bool | None = None
    sync_cloudflare: bool | None = None
    cloudflare_action: Literal["allow_ai_crawlers", "block_ai_crawlers", "reset"] | None = None
    run_visibility_audit: bool | None = None
    crawlers_to_test: list[str] | None = Field(default=None, max_length=20)


class AutomationSchedulesExecuteRequest(BaseModel):
    schedule_ids: list[str] = Field(default_factory=list, max_length=500)
    due_only: bool = True
    max_schedules: int = Field(default=50, ge=1, le=500)
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_ai_crawler_enablement_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    sites_memory: list[dict[str, Any]],
    crawler_events_memory: list[dict[str, Any]],
    ssr_cache_memory: list[dict[str, Any]],
    crawler_rules_memory: list[dict[str, Any]],
    audit_results_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/ai-crawler", tags=["AI Crawler Enablement"])
    _lock = threading.Lock()
    automation_schedules_memory: list[dict[str, Any]] = []
    automation_runs_memory: list[dict[str, Any]] = []

    # ── helpers ──────────────────────────────────────────────────────────────

    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _snippet_id(tenant_id: str, domain: str) -> str:
        return hashlib.sha256(f"{tenant_id}:{domain}".encode()).hexdigest()[:16]

    def _generate_snippet(site_id: str, snippet_key: str, domain: str) -> str:
        cdn_base = os.getenv("ALLI_CDN_BASE_URL", "https://cdn.nuxtron.ai").rstrip("/")
        return f"""<!-- Nuxtron AI Crawler Enablement Snippet | site={domain} -->
<script>
(function(w,d,s,k,id){{
  if(w.__NUXTRON_ACE__)return;
  w.__NUXTRON_ACE__=1;
  var t=d.createElement(s);t.async=1;
  t.src='{cdn_base}/ace.js?k='+k+'&s='+id;
  d.head.appendChild(t);
}})(window,document,'script','{snippet_key}','{site_id}');
</script>"""

    def _get_site(tenant_id: str, site_id: str) -> dict[str, Any]:
        with _lock:
            site = next(
                (s for s in sites_memory if s["id"] == site_id and s["tenant_id"] == tenant_id),
                None,
            )
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found.")
        return site

    def _audit(tenant_id: str, action: str, detail: str = "") -> None:
        with _lock:
            audit_log_memory.append({
                "id": len(audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "detail": detail,
                "source": "ai-crawler",
                "created_at": _now_iso(),
            })

    def _parse_iso_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _sync_cloudflare_site(site: dict[str, Any], action: str) -> dict[str, Any]:
        zone_id = str(site.get("cloudflare_zone_id") or "").strip()
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        site_id = str(site.get("id") or "")
        domain = str(site.get("domain") or "")

        if not zone_id:
            return {
                "site_id": site_id,
                "domain": domain,
                "synced": False,
                "reason": "missing_cloudflare_zone_id",
            }
        if not cf_token:
            return {
                "site_id": site_id,
                "domain": domain,
                "synced": False,
                "reason": "missing_cloudflare_api_token",
            }

        ai_ua_patterns = [
            c["name"] for c in KNOWN_CRAWLERS
            if c["category"] == "ai_search" and c["enabled"]
        ]
        expression = " or ".join(
            f'(http.user_agent contains "{name}")' for name in ai_ua_patterns[:20]
        )
        rule_action = "skip" if action == "allow_ai_crawlers" else "block"
        rule_description = f"Nuxtron ACE - {action.replace('_', ' ').title()}"

        try:
            with httpx.Client(timeout=15.0) as client:
                list_resp = client.get(
                    f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules",
                    headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                    params={"description": "Nuxtron ACE", "per_page": 5},
                )
                existing_rules = list_resp.json().get("result", []) if list_resp.is_success else []
                existing_rule_id = existing_rules[0]["id"] if existing_rules else None

                filter_body = {"expression": expression, "description": f"ACE filter - {action}"}
                rule_body = {
                    "filter": filter_body,
                    "action": rule_action,
                    "description": rule_description,
                }

                if existing_rule_id:
                    resp = client.put(
                        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules/{existing_rule_id}",
                        headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                        json=[rule_body],
                    )
                else:
                    resp = client.post(
                        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules",
                        headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                        json=[rule_body],
                    )

                cf_result = resp.json() if resp.content else {}
                synced = bool(resp.is_success and cf_result.get("success", False))
                return {
                    "site_id": site_id,
                    "domain": domain,
                    "synced": synced,
                    "reason": "ok" if synced else "cloudflare_api_rejected",
                    "cloudflare_success": bool(cf_result.get("success", False)),
                }
        except Exception as exc:
            return {
                "site_id": site_id,
                "domain": domain,
                "synced": False,
                "reason": "cloudflare_sync_exception",
                "error": str(exc)[:300],
            }

    def _verify_snippet_installation(snippet_key: str, page_url: str) -> tuple[bool, str]:
        installed = False
        detail = ""
        try:
            ssr_proxy_url = os.getenv("SSR_PROXY_URL", "").strip()
            timeout = float(os.getenv("ACE_VERIFY_TIMEOUT", "8"))
            headers = {"User-Agent": "NuxtronACEVerifier/1.0"}
            fetch_url = (
                f"{ssr_proxy_url.rstrip('/')}/verify?url={page_url}&key={snippet_key}"
                if ssr_proxy_url
                else page_url
            )
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(fetch_url, headers=headers)
            body = resp.text or ""
            installed = snippet_key in body or "__NUXTRON_ACE__" in body
            detail = "Snippet detected in page source." if installed else "Snippet not found in page source."
        except Exception as exc:
            detail = f"Verification request failed: {str(exc)[:200]}"
        return installed, detail

    def _run_visibility_audit_for_url(
        tenant_id: str,
        *,
        site_id: str,
        page_url: str,
        crawlers_to_test: list[str],
    ) -> dict[str, Any]:
        ssr_proxy = os.getenv("SSR_PROXY_URL", "").strip()
        results: list[dict[str, Any]] = []

        for crawler_name in crawlers_to_test[:10]:
            crawler_info = _detect_crawler(crawler_name) or {"name": crawler_name, "category": "unknown"}
            ua = f"{crawler_name}/1.0"
            html_content = ""
            status_code = 0
            render_time_ms = 0
            is_js_rendered = False
            issue = None

            try:
                started = time.perf_counter()
                if ssr_proxy:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.get(
                            page_url,
                            headers={"User-Agent": ua},
                            follow_redirects=True,
                        )
                    status_code = resp.status_code
                    html_content = resp.text
                else:
                    status_code = 200
                    html_content = f"<html><body>Stub content for {crawler_name}</body></html>"
                render_time_ms = round((time.perf_counter() - started) * 1000)

                content_ratio = len(html_content.strip()) < 500
                has_js_framework_markers = any(
                    m in html_content for m in ["__NEXT_DATA__", "nuxt", "__vue__", "ng-version", "data-reactroot"]
                )
                is_js_rendered = content_ratio or has_js_framework_markers
                if is_js_rendered:
                    issue = "Page appears to be JS-rendered and may be invisible to AI crawlers without SSR."
            except Exception as exc:
                issue = f"Request failed: {str(exc)[:200]}"
                status_code = 0

            results.append({
                "crawler_name": crawler_name,
                "crawler_category": crawler_info.get("category", "unknown"),
                "status_code": status_code,
                "render_time_ms": render_time_ms,
                "content_length": len(html_content),
                "is_js_rendered": is_js_rendered,
                "visible_to_crawler": not is_js_rendered and status_code == 200,
                "issue": issue,
                "recommendation": (
                    "Enable SSR/pre-rendering via AI Crawler Enablement snippet." if is_js_rendered
                    else "Content is accessible." if status_code == 200
                    else "Fix HTTP error before optimizing for AI crawlers."
                ),
            })

        visible_count = sum(1 for r in results if r.get("visible_to_crawler"))
        visibility_pct = round(visible_count / max(len(results), 1) * 100, 1)
        return {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "site_id": site_id,
            "url": page_url,
            "crawlers_tested": len(results),
            "visible_count": visible_count,
            "visibility_score": visibility_pct,
            "results": results,
            "created_at": _now_iso(),
        }

    def _vendor_matrix_for_site(site: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "vendor": "Nuxtron CDN",
                "purpose": "AI crawler snippet delivery",
                "integration": "snippet_loader",
                "configured": True,
                "runtime_dependency": True,
            },
            {
                "vendor": "Cloudflare",
                "purpose": "WAF crawler allow/block policy sync",
                "integration": "cloudflare_firewall_rules_api",
                "configured": bool(site.get("cloudflare_zone_id")) and bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip()),
                "runtime_dependency": False,
            },
            {
                "vendor": "SSR Proxy",
                "purpose": "pre-rendering for crawler visibility",
                "integration": "ssr_proxy_http",
                "configured": bool(os.getenv("SSR_PROXY_URL", "").strip()),
                "runtime_dependency": False,
            },
            {
                "vendor": "CMS/Platform Webhook",
                "purpose": "automated snippet deployment",
                "integration": "deployment_webhook",
                "configured": bool(site.get("deployment_webhook_url")),
                "runtime_dependency": False,
            },
        ]

    def _vendor_chart_for_sites(tenant_sites: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
        chart_index: dict[str, dict[str, Any]] = {}
        total_integrations = 0
        configured_integrations = 0

        for site in tenant_sites:
            vendors = _vendor_matrix_for_site(site)
            for vendor in vendors:
                total_integrations += 1
                if bool(vendor.get("configured")):
                    configured_integrations += 1

                key = str(vendor.get("vendor", "unknown"))
                row = chart_index.get(key)
                if row is None:
                    row = {
                        "vendor": key,
                        "purpose": str(vendor.get("purpose", "")),
                        "integration": str(vendor.get("integration", "")),
                        "runtime_dependency": bool(vendor.get("runtime_dependency")),
                        "sites_using": 0,
                        "sites_configured": 0,
                    }
                    chart_index[key] = row
                row["sites_using"] = int(row.get("sites_using", 0)) + 1
                if bool(vendor.get("configured")):
                    row["sites_configured"] = int(row.get("sites_configured", 0)) + 1

        chart = sorted(chart_index.values(), key=lambda r: str(r.get("vendor", "")))
        summary = {
            "sites": len(tenant_sites),
            "total_integrations": total_integrations,
            "configured_integrations": configured_integrations,
            "vendors": len(chart),
        }
        return chart, summary

    # ── Site management ───────────────────────────────────────────────────────

    @router.post("/sites", status_code=201)
    def register_site(payload: SiteRegisterRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:sites:create", 30, 60)
        domain_clean = payload.domain.lower().strip().removeprefix("https://").removeprefix("http://").split("/")[0]
        site_id = str(uuid.uuid4())
        snippet_key = _snippet_id(auth.tenant_id, domain_clean)
        snippet = _generate_snippet(site_id, snippet_key, domain_clean)
        site: dict[str, Any] = {
            "id": site_id,
            "tenant_id": auth.tenant_id,
            "domain": domain_clean,
            "display_name": payload.display_name,
            "cms_type": payload.cms_type,
            "js_framework": payload.js_framework,
            "cloudflare_zone_id": payload.cloudflare_zone_id or "",
            "deployment_webhook_url": str(payload.deployment_webhook_url) if payload.deployment_webhook_url else "",
            "snippet_key": snippet_key,
            "snippet_installed": False,
            "snippet_last_verified_at": None,
            "ssr_enabled": payload.js_framework != "none",
            "crawlers_detected_total": 0,
            "ai_crawlers_detected_total": 0,
            "visibility_score": 0,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        with _lock:
            sites_memory.append(site)
        _audit(auth.tenant_id, "site_registered", domain_clean)
        return {"status": "ok", "site": site, "snippet": snippet}

    @router.get("/sites")
    def list_sites(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:sites:list", 120, 60)
        with _lock:
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]
        return {"status": "ok", "count": len(tenant_sites), "sites": tenant_sites}

    @router.delete("/sites/{site_id}", status_code=200)
    def unregister_site(site_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:sites:delete", 20, 60)
        with _lock:
            before = len(sites_memory)
            sites_memory[:] = [
                s for s in sites_memory
                if not (s["id"] == site_id and s["tenant_id"] == auth.tenant_id)
            ]
            removed = before - len(sites_memory)
        if removed == 0:
            raise HTTPException(status_code=404, detail="Site not found.")
        _audit(auth.tenant_id, "site_unregistered", site_id)
        return {"status": "ok", "site_id": site_id, "removed": True}

    # ── Snippet ───────────────────────────────────────────────────────────────

    @router.get("/sites/{site_id}/snippet")
    def get_snippet(site_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:snippet:get", 60, 60)
        site = _get_site(auth.tenant_id, site_id)
        snippet = _generate_snippet(site_id, site["snippet_key"], site["domain"])
        return {"status": "ok", "site_id": site_id, "domain": site["domain"], "snippet": snippet}

    @router.post("/snippets/deploy-bulk")
    def deploy_snippets_bulk(payload: BulkSnippetDeployRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:snippets:deploy-bulk", 20, 60)
        with _lock:
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]
        if payload.site_ids:
            requested = set(payload.site_ids)
            tenant_sites = [s for s in tenant_sites if s["id"] in requested]

        deployments: list[dict[str, Any]] = []
        updated_site_ids: list[str] = []
        for site in tenant_sites:
            site_id = str(site["id"])
            snippet = _generate_snippet(site_id, str(site["snippet_key"]), str(site["domain"]))
            webhook_url = str(site.get("deployment_webhook_url") or "").strip()

            if payload.dry_run:
                deployments.append({
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "planned",
                    "mode": "webhook" if webhook_url else "manual",
                    "webhook_configured": bool(webhook_url),
                })
                continue

            if not webhook_url:
                deployments.append({
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "manual_required",
                    "detail": "No deployment_webhook_url configured; install snippet manually.",
                })
                continue

            try:
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(
                        webhook_url,
                        json={
                            "site_id": site_id,
                            "domain": site.get("domain", ""),
                            "snippet": snippet,
                            "snippet_key": site.get("snippet_key", ""),
                            "source": "nuxtron-ai-crawler-enablement",
                        },
                        headers={"X-Tenant-Id": auth.tenant_id},
                    )
                if resp.is_success:
                    deployments.append({
                        "site_id": site_id,
                        "domain": site.get("domain", ""),
                        "status": "deployed",
                        "mode": "webhook",
                    })
                    updated_site_ids.append(site_id)
                else:
                    deployments.append({
                        "site_id": site_id,
                        "domain": site.get("domain", ""),
                        "status": "failed",
                        "mode": "webhook",
                        "detail": f"Webhook returned HTTP {resp.status_code}",
                    })
            except Exception as exc:
                deployments.append({
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "failed",
                    "mode": "webhook",
                    "detail": str(exc)[:300],
                })

        if updated_site_ids:
            now = _now_iso()
            with _lock:
                for s in sites_memory:
                    if s.get("tenant_id") == auth.tenant_id and str(s.get("id")) in updated_site_ids:
                        s["snippet_installed"] = True
                        s["snippet_last_verified_at"] = now
                        s["updated_at"] = now

        deployed_count = sum(1 for d in deployments if d.get("status") == "deployed")
        failed_count = sum(1 for d in deployments if d.get("status") == "failed")
        manual_count = sum(1 for d in deployments if d.get("status") == "manual_required")
        planned_count = sum(1 for d in deployments if d.get("status") == "planned")

        _audit(auth.tenant_id, "bulk_snippet_deploy", f"sites={len(deployments)} deployed={deployed_count}")
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "dry_run": payload.dry_run,
            "summary": {
                "sites_targeted": len(deployments),
                "deployed": deployed_count,
                "failed": failed_count,
                "manual_required": manual_count,
                "planned": planned_count,
            },
            "deployments": deployments,
            "generated_at": _now_iso(),
        }

    @router.post("/sites/{site_id}/snippet/verify")
    def verify_snippet(site_id: str, payload: SnippetVerifyRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:snippet:verify", 30, 60)
        site = _get_site(auth.tenant_id, site_id)
        snippet_key = site["snippet_key"]
        installed, detail = _verify_snippet_installation(snippet_key, payload.page_url)

        with _lock:
            for s in sites_memory:
                if s["id"] == site_id and s["tenant_id"] == auth.tenant_id:
                    s["snippet_installed"] = installed
                    s["snippet_last_verified_at"] = _now_iso()
        return {"status": "ok", "site_id": site_id, "installed": installed, "detail": detail}

    # ── Crawler database ──────────────────────────────────────────────────────

    @router.get("/crawlers")
    def list_crawlers(
        auth: AuthDep,
        category: str | None = Query(default=None),
        enabled_only: bool = Query(default=False),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:crawlers:list", 120, 60)
        crawlers = [
            {k: v for k, v in c.items() if k != "_re"}
            for c in _CRAWLER_COMPILED
            if (not category or c["category"] == category)
            and (not enabled_only or c["enabled"])
        ]
        return {"status": "ok", "count": len(crawlers), "crawlers": crawlers}

    @router.post("/crawlers/detect")
    def detect_crawler(payload: CrawlerDetectRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:crawlers:detect", 300, 60)
        match = _detect_crawler(payload.user_agent)
        return {
            "status": "ok",
            "user_agent": payload.user_agent,
            "is_known_crawler": match is not None,
            "crawler": match,
        }

    # ── Crawler event ingestion ───────────────────────────────────────────────

    @router.post("/events", status_code=201)
    def ingest_crawler_event(payload: CrawlerEventIngestRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:events:ingest", 1000, 60)
        # Detect if this is a known AI crawler
        ua = payload.user_agent or payload.crawler_name
        crawler_info = _detect_crawler(ua) or {"name": payload.crawler_name, "category": "unknown"}
        is_ai_crawler = crawler_info.get("category") == "ai_search"
        now = _now_iso()
        event: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "site_id": payload.site_id,
            "crawler_name": payload.crawler_name,
            "crawler_category": crawler_info.get("category", "unknown"),
            "is_ai_crawler": is_ai_crawler,
            "page_url": payload.page_url,
            "status_code": payload.status_code,
            "response_type": payload.response_type,
            "render_time_ms": payload.render_time_ms,
            "ip_hash": hashlib.sha256((payload.ip_address or "").encode()).hexdigest()[:16] if payload.ip_address else "",
            "timestamp": int(time.time()),
            "created_at": now,
        }
        with _lock:
            crawler_events_memory.append(event)
            if len(crawler_events_memory) > 50000:
                del crawler_events_memory[:10000]
            # Update site counters
            for s in sites_memory:
                if s["id"] == payload.site_id and s["tenant_id"] == auth.tenant_id:
                    s["crawlers_detected_total"] = int(s.get("crawlers_detected_total", 0)) + 1
                    if is_ai_crawler:
                        s["ai_crawlers_detected_total"] = int(s.get("ai_crawlers_detected_total", 0)) + 1
        return {"status": "ok", "event_id": event["id"], "is_ai_crawler": is_ai_crawler}

    @router.get("/events")
    def get_crawler_events(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
        crawler_name: str | None = Query(default=None),
        ai_only: bool = Query(default=False),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:events:list", 120, 60)
        with _lock:
            events = [
                e.copy() for e in crawler_events_memory
                if e["tenant_id"] == auth.tenant_id
                and (not site_id or e["site_id"] == site_id)
                and (not crawler_name or e["crawler_name"] == crawler_name)
                and (not ai_only or e.get("is_ai_crawler"))
            ]
        events = events[-limit:]
        return {"status": "ok", "count": len(events), "events": events}

    # ── Analytics Dashboard ───────────────────────────────────────────────────

    @router.get("/dashboard")
    def crawler_dashboard(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
        window_hours: int = Query(default=24, ge=1, le=168),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:dashboard", 60, 60)
        cutoff = int(time.time()) - window_hours * 3600
        with _lock:
            events = [
                e for e in crawler_events_memory
                if e["tenant_id"] == auth.tenant_id
                and e.get("timestamp", 0) >= cutoff
                and (not site_id or e["site_id"] == site_id)
            ]
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]

        total_hits = len(events)
        ai_hits = sum(1 for e in events if e.get("is_ai_crawler"))
        ssr_hits = sum(1 for e in events if e.get("response_type") == "ssr")
        blocked = sum(1 for e in events if e.get("response_type") == "blocked")
        avg_render = (
            round(sum(e.get("render_time_ms", 0) for e in events) / total_hits, 1)
            if total_hits else 0
        )

        # Crawler breakdown
        by_crawler: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_page: dict[str, int] = {}
        for e in events:
            cn = str(e.get("crawler_name", "unknown"))
            cat = str(e.get("crawler_category", "unknown"))
            page = str(e.get("page_url", ""))[:120]
            by_crawler[cn] = by_crawler.get(cn, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
            by_page[page] = by_page.get(page, 0) + 1

        top_crawlers = sorted(by_crawler.items(), key=lambda x: -x[1])[:20]
        top_pages = sorted(by_page.items(), key=lambda x: -x[1])[:10]

        # Visibility score: % of AI crawler hits served as SSR vs live JS
        ai_events = [e for e in events if e.get("is_ai_crawler")]
        ai_ssr = sum(1 for e in ai_events if e.get("response_type") in {"ssr", "cached"})
        visibility_score = round((ai_ssr / max(len(ai_events), 1)) * 100, 1)

        return {
            "status": "ok",
            "window_hours": window_hours,
            "site_id": site_id,
            "summary": {
                "total_hits": total_hits,
                "ai_crawler_hits": ai_hits,
                "ssr_served_hits": ssr_hits,
                "blocked_hits": blocked,
                "avg_render_time_ms": avg_render,
                "visibility_score": visibility_score,
                "sites_registered": len(tenant_sites),
                "sites_with_snippet": sum(1 for s in tenant_sites if s.get("snippet_installed")),
            },
            "by_category": by_category,
            "top_crawlers": [{"name": n, "hits": c} for n, c in top_crawlers],
            "top_pages": [{"url": u, "hits": c} for u, c in top_pages],
            "recent_events": events[-20:],
        }

    # ── SSR Pre-rendering ─────────────────────────────────────────────────────

    @router.post("/ssr/render")
    def request_ssr_render(payload: SsrRenderRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:ssr:render", 100, 60)
        ssr_proxy = os.getenv("SSR_PROXY_URL", "").strip()
        cache_key = hashlib.sha256(payload.url.encode()).hexdigest()[:24]
        now = _now_iso()

        # Check existing cache
        with _lock:
            existing = next(
                (c for c in ssr_cache_memory
                 if c["cache_key"] == cache_key and c["tenant_id"] == auth.tenant_id
                 and not payload.force_refresh),
                None,
            )
        if existing:
            age_seconds = int(time.time()) - int(existing.get("rendered_at_ts", 0))
            if age_seconds < payload.cache_ttl_seconds:
                return {"status": "ok", "source": "cache", "cache_key": cache_key, "render": existing}

        # Perform SSR render
        rendered_html = ""
        render_time_ms = 0
        source = "proxy"
        error = None
        if ssr_proxy:
            try:
                started = time.perf_counter()
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(
                        f"{ssr_proxy.rstrip('/')}/render",
                        params={"url": payload.url, "crawler": payload.crawler_hint or "GPTBot"},
                        headers={"X-Tenant-Id": auth.tenant_id},
                    )
                render_time_ms = round((time.perf_counter() - started) * 1000)
                if resp.is_success:
                    rendered_html = resp.text
                else:
                    error = f"SSR proxy returned {resp.status_code}"
                    source = "error"
            except Exception as exc:
                error = str(exc)[:200]
                source = "error"
        else:
            source = "stub"
            rendered_html = f"<html><head><title>SSR Stub</title></head><body><!-- SSR render of {payload.url} --></body></html>"

        render_record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "site_id": payload.site_id,
            "url": payload.url,
            "cache_key": cache_key,
            "rendered_html_length": len(rendered_html),
            "render_time_ms": render_time_ms,
            "cache_ttl_seconds": payload.cache_ttl_seconds,
            "rendered_at_ts": int(time.time()),
            "rendered_at": now,
            "source": source,
            "error": error,
        }
        with _lock:
            # Remove old entry for same URL
            ssr_cache_memory[:] = [c for c in ssr_cache_memory if c["cache_key"] != cache_key]
            ssr_cache_memory.append(render_record)
            if len(ssr_cache_memory) > 5000:
                del ssr_cache_memory[:1000]

        return {"status": "ok", "source": source, "cache_key": cache_key, "render": render_record}

    @router.get("/ssr/cache")
    def list_ssr_cache(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:ssr:cache:list", 60, 60)
        with _lock:
            items = [
                c.copy() for c in ssr_cache_memory
                if c["tenant_id"] == auth.tenant_id
                and (not site_id or c.get("site_id") == site_id)
            ]
        return {"status": "ok", "count": len(items), "items": items[-limit:]}

    # ── Cloudflare WAF integration ────────────────────────────────────────────

    @router.post("/cloudflare/sync")
    def cloudflare_sync(payload: CloudflareSyncRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:sync", 10, 60)
        site = _get_site(auth.tenant_id, payload.site_id)
        sync_result = _sync_cloudflare_site(site, payload.action)
        _audit(auth.tenant_id, "cloudflare_waf_synced", f"site={payload.site_id} action={payload.action}")

        if not sync_result.get("synced", False):
            reason = str(sync_result.get("reason", "unknown"))
            if reason in {"missing_cloudflare_zone_id", "missing_cloudflare_api_token"}:
                return {
                    "status": "ok",
                    "synced": False,
                    "detail": (
                        "Cloudflare sync skipped: zone_id not set on site or CLOUDFLARE_API_TOKEN not configured. "
                        "Set CLOUDFLARE_API_TOKEN and cloudflare_zone_id on the site to enable WAF rule sync."
                    ),
                    "result": sync_result,
                }
            return {
                "status": "error",
                "synced": False,
                "detail": str(sync_result.get("error") or sync_result.get("reason") or "Cloudflare sync failed"),
                "result": sync_result,
            }

        ai_ua_patterns = [
            c["name"] for c in KNOWN_CRAWLERS
            if c["category"] == "ai_search" and c["enabled"]
        ]
        return {
            "status": "ok",
            "synced": True,
            "action": payload.action,
            "crawlers_whitelisted": ai_ua_patterns[:20],
            "result": sync_result,
        }

    @router.post("/cloudflare/auto-sync")
    def cloudflare_auto_sync(payload: CloudflareAutoSyncRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:auto-sync", 10, 60)
        with _lock:
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]
        if payload.site_ids:
            requested = set(payload.site_ids)
            tenant_sites = [s for s in tenant_sites if s["id"] in requested]

        if payload.dry_run:
            planned = []
            for site in tenant_sites:
                planned.append({
                    "site_id": site.get("id", ""),
                    "domain": site.get("domain", ""),
                    "eligible": bool(site.get("cloudflare_zone_id")) and bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip()),
                })
            return {
                "status": "ok",
                "dry_run": True,
                "action": payload.action,
                "sites_targeted": len(planned),
                "results": planned,
                "generated_at": _now_iso(),
            }

        results = [_sync_cloudflare_site(site, payload.action) for site in tenant_sites]
        synced = sum(1 for item in results if item.get("synced"))
        skipped = sum(1 for item in results if item.get("reason") in {"missing_cloudflare_zone_id", "missing_cloudflare_api_token"})
        failed = max(0, len(results) - synced - skipped)

        _audit(auth.tenant_id, "cloudflare_auto_sync", f"sites={len(results)} synced={synced}")
        return {
            "status": "ok",
            "dry_run": False,
            "action": payload.action,
            "summary": {
                "sites_targeted": len(results),
                "synced": synced,
                "skipped": skipped,
                "failed": failed,
            },
            "results": results,
            "generated_at": _now_iso(),
        }

    @router.get("/readiness")
    def readiness(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:readiness", 60, 60)
        with _lock:
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]

        total_sites = len(tenant_sites)
        snippet_installed = sum(1 for s in tenant_sites if bool(s.get("snippet_installed")))
        ssr_enabled = sum(1 for s in tenant_sites if bool(s.get("ssr_enabled")))
        cf_zone_configured = sum(1 for s in tenant_sites if bool(s.get("cloudflare_zone_id")))
        webhook_configured = sum(1 for s in tenant_sites if bool(s.get("deployment_webhook_url")))
        token_configured = bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip())

        snippet_pct = round((snippet_installed / max(total_sites, 1)) * 100.0, 1)
        ssr_pct = round((ssr_enabled / max(total_sites, 1)) * 100.0, 1)
        cf_pct = round((cf_zone_configured / max(total_sites, 1)) * 100.0, 1)
        webhook_pct = round((webhook_configured / max(total_sites, 1)) * 100.0, 1)

        score = round((snippet_pct * 0.4) + (ssr_pct * 0.2) + (cf_pct * 0.2) + (webhook_pct * 0.2), 1)
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "readiness": {
                "score": score,
                "grade": grade,
                "production_ready": score >= 70 and token_configured,
                "total_sites": total_sites,
            },
            "coverage": {
                "snippet_installed_pct": snippet_pct,
                "ssr_enabled_pct": ssr_pct,
                "cloudflare_zone_configured_pct": cf_pct,
                "deployment_webhook_configured_pct": webhook_pct,
            },
            "checks": {
                "cloudflare_api_token_configured": token_configured,
            },
            "generated_at": _now_iso(),
        }

    @router.get("/cloudflare/status")
    def cloudflare_status(
        auth: AuthDep,
        site_id: str = Query(...),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:status", 30, 60)
        site = _get_site(auth.tenant_id, site_id)
        zone_id = site.get("cloudflare_zone_id") or ""
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

        if not zone_id or not cf_token:
            return {"status": "ok", "configured": False, "rules": []}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules",
                    headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                    params={"description": "Nuxtron ACE", "per_page": 10},
                )
            rules = resp.json().get("result", []) if resp.is_success else []
        except Exception as exc:
            return {"status": "error", "configured": True, "rules": [], "error": str(exc)[:200]}

        return {"status": "ok", "configured": True, "zone_id": zone_id, "rules": rules}

    # ── Crawler access rules ──────────────────────────────────────────────────

    @router.post("/rules", status_code=201)
    def create_rule(payload: CrawlerRuleRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:rules:create", 60, 60)
        _get_site(auth.tenant_id, payload.site_id)  # validate site ownership
        rule: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "site_id": payload.site_id,
            "crawler_name": payload.crawler_name,
            "rule": payload.rule,
            "rate_limit_rpm": payload.rate_limit_rpm,
            "note": payload.note or "",
            "created_at": _now_iso(),
        }
        with _lock:
            crawler_rules_memory.append(rule)
        return {"status": "ok", "rule": rule}

    @router.get("/rules")
    def list_rules(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:rules:list", 120, 60)
        with _lock:
            rules = [
                r.copy() for r in crawler_rules_memory
                if r["tenant_id"] == auth.tenant_id
                and (not site_id or r["site_id"] == site_id)
            ]
        return {"status": "ok", "count": len(rules), "rules": rules}

    @router.delete("/rules/{rule_id}")
    def delete_rule(rule_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:rules:delete", 30, 60)
        with _lock:
            before = len(crawler_rules_memory)
            crawler_rules_memory[:] = [
                r for r in crawler_rules_memory
                if not (r["id"] == rule_id and r["tenant_id"] == auth.tenant_id)
            ]
            removed = before - len(crawler_rules_memory)
        if removed == 0:
            raise HTTPException(status_code=404, detail="Rule not found.")
        return {"status": "ok", "rule_id": rule_id, "removed": True}

    # ── Visibility audit ──────────────────────────────────────────────────────

    @router.post("/audit", status_code=201)
    def run_visibility_audit(payload: VisibilityAuditRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:audit:run", 20, 60)
        audit_id = str(uuid.uuid4())
        now = _now_iso()
        ssr_proxy = os.getenv("SSR_PROXY_URL", "").strip()
        results: list[dict[str, Any]] = []

        for crawler_name in payload.crawlers_to_test[:10]:
            crawler_info = _detect_crawler(crawler_name) or {"name": crawler_name, "category": "unknown"}
            ua = f"{crawler_name}/1.0"
            html_content = ""
            status_code = 0
            render_time_ms = 0
            is_js_rendered = False
            issue = None

            try:
                started = time.perf_counter()
                if ssr_proxy:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.get(
                            payload.url,
                            headers={"User-Agent": ua},
                            follow_redirects=True,
                        )
                    status_code = resp.status_code
                    html_content = resp.text
                else:
                    # Stub: simulate audit
                    status_code = 200
                    html_content = f"<html><body>Stub content for {crawler_name}</body></html>"
                render_time_ms = round((time.perf_counter() - started) * 1000)

                # Heuristics: detect JS-only rendering
                content_ratio = len(html_content.strip()) < 500
                has_js_framework_markers = any(
                    m in html_content for m in ["__NEXT_DATA__", "nuxt", "__vue__", "ng-version", "data-reactroot"]
                )
                is_js_rendered = content_ratio or has_js_framework_markers
                if is_js_rendered:
                    issue = "Page appears to be JS-rendered and may be invisible to AI crawlers without SSR."
            except Exception as exc:
                issue = f"Request failed: {str(exc)[:200]}"
                status_code = 0

            results.append({
                "crawler_name": crawler_name,
                "crawler_category": crawler_info.get("category", "unknown"),
                "status_code": status_code,
                "render_time_ms": render_time_ms,
                "content_length": len(html_content),
                "is_js_rendered": is_js_rendered,
                "visible_to_crawler": not is_js_rendered and status_code == 200,
                "issue": issue,
                "recommendation": (
                    "Enable SSR/pre-rendering via AI Crawler Enablement snippet." if is_js_rendered
                    else "Content is accessible." if status_code == 200
                    else "Fix HTTP error before optimizing for AI crawlers."
                ),
            })

        visible_count = sum(1 for r in results if r.get("visible_to_crawler"))
        visibility_pct = round(visible_count / max(len(results), 1) * 100, 1)

        audit_record: dict[str, Any] = {
            "id": audit_id,
            "tenant_id": auth.tenant_id,
            "site_id": payload.site_id or "",
            "url": payload.url,
            "crawlers_tested": len(results),
            "visible_count": visible_count,
            "visibility_score": visibility_pct,
            "results": results,
            "created_at": now,
        }
        with _lock:
            audit_results_memory.append(audit_record)
            if len(audit_results_memory) > 2000:
                del audit_results_memory[:500]

        return {"status": "ok", "audit": audit_record}

    @router.get("/audit/{audit_id}")
    def get_audit(audit_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:audit:get", 120, 60)
        with _lock:
            record = next(
                (a.copy() for a in audit_results_memory
                 if a["id"] == audit_id and a["tenant_id"] == auth.tenant_id),
                None,
            )
        if record is None:
            raise HTTPException(status_code=404, detail="Audit not found.")
        return {"status": "ok", "audit": record}

    @router.get("/vendors")
    def list_vendors(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:vendors", 120, 60)
        with _lock:
            tenant_sites = [s.copy() for s in sites_memory if s["tenant_id"] == auth.tenant_id]

        if site_id:
            site = next((s for s in tenant_sites if s["id"] == site_id), None)
            if site is None:
                raise HTTPException(status_code=404, detail="Site not found.")
            site_vendors = _vendor_matrix_for_site(site)
            vendor_chart, summary = _vendor_chart_for_sites([site])
            return {
                "status": "ok",
                "site_id": site_id,
                "domain": site.get("domain", ""),
                "vendors": site_vendors,
                "vendor_chart": vendor_chart,
                "summary": summary,
                "generated_at": _now_iso(),
            }

        vendor_chart, summary = _vendor_chart_for_sites(tenant_sites)

        return {
            "status": "ok",
            "sites": [
                {
                    "site_id": s.get("id", ""),
                    "domain": s.get("domain", ""),
                    "vendors": _vendor_matrix_for_site(s),
                }
                for s in tenant_sites
            ],
            "vendor_chart": vendor_chart,
            "summary": summary,
            "generated_at": _now_iso(),
        }

    def _execute_automation_run(
        tenant_id: str,
        payload: AutomationRunRequest,
        *,
        trigger: str,
        schedule_id: str | None = None,
    ) -> dict[str, Any]:
        site = _get_site(tenant_id, payload.site_id)
        now = _now_iso()
        steps: list[dict[str, Any]] = []

        if payload.deploy_snippet:
            webhook_url = str(site.get("deployment_webhook_url") or "").strip()
            if payload.dry_run:
                steps.append({
                    "step": "deploy_snippet",
                    "status": "planned",
                    "mode": "webhook" if webhook_url else "manual",
                })
            elif webhook_url:
                snippet = _generate_snippet(str(site["id"]), str(site["snippet_key"]), str(site["domain"]))
                try:
                    with httpx.Client(timeout=20.0) as client:
                        resp = client.post(
                            webhook_url,
                            json={
                                "site_id": site.get("id", ""),
                                "domain": site.get("domain", ""),
                                "snippet": snippet,
                                "snippet_key": site.get("snippet_key", ""),
                                "source": "nuxtron-ai-crawler-enablement",
                            },
                            headers={"X-Tenant-Id": tenant_id},
                        )
                    if resp.is_success:
                        with _lock:
                            for s in sites_memory:
                                if s.get("id") == payload.site_id and s.get("tenant_id") == tenant_id:
                                    s["snippet_installed"] = True
                                    s["snippet_last_verified_at"] = now
                                    s["updated_at"] = now
                        steps.append({"step": "deploy_snippet", "status": "completed", "mode": "webhook"})
                    else:
                        steps.append({
                            "step": "deploy_snippet",
                            "status": "failed",
                            "mode": "webhook",
                            "detail": f"Webhook returned HTTP {resp.status_code}",
                        })
                except Exception as exc:
                    steps.append({
                        "step": "deploy_snippet",
                        "status": "failed",
                        "mode": "webhook",
                        "detail": str(exc)[:300],
                    })
            else:
                steps.append({
                    "step": "deploy_snippet",
                    "status": "manual_required",
                    "mode": "manual",
                    "detail": "No deployment_webhook_url configured; install snippet manually.",
                })

        if payload.verify_snippet:
            if payload.dry_run:
                steps.append({"step": "verify_snippet", "status": "planned"})
            else:
                installed, detail = _verify_snippet_installation(str(site["snippet_key"]), payload.page_url)
                with _lock:
                    for s in sites_memory:
                        if s.get("id") == payload.site_id and s.get("tenant_id") == tenant_id:
                            s["snippet_installed"] = installed
                            s["snippet_last_verified_at"] = _now_iso()
                            s["updated_at"] = _now_iso()
                steps.append({
                    "step": "verify_snippet",
                    "status": "completed" if installed else "warning",
                    "installed": installed,
                    "detail": detail,
                })

        if payload.sync_cloudflare:
            if payload.dry_run:
                steps.append({"step": "sync_cloudflare", "status": "planned", "action": payload.cloudflare_action})
            else:
                sync_result = _sync_cloudflare_site(site, payload.cloudflare_action)
                steps.append({
                    "step": "sync_cloudflare",
                    "status": "completed" if sync_result.get("synced") else "warning",
                    "action": payload.cloudflare_action,
                    "result": sync_result,
                })

        audit_record: dict[str, Any] | None = None
        if payload.run_visibility_audit:
            if payload.dry_run:
                steps.append({"step": "visibility_audit", "status": "planned", "crawlers": payload.crawlers_to_test[:10]})
            else:
                audit_record = _run_visibility_audit_for_url(
                    tenant_id,
                    site_id=payload.site_id,
                    page_url=payload.page_url,
                    crawlers_to_test=payload.crawlers_to_test,
                )
                with _lock:
                    audit_results_memory.append(audit_record)
                    if len(audit_results_memory) > 2000:
                        del audit_results_memory[:500]
                steps.append({
                    "step": "visibility_audit",
                    "status": "completed",
                    "audit_id": audit_record["id"],
                    "visibility_score": audit_record["visibility_score"],
                })

        completed = sum(1 for s in steps if s.get("status") == "completed")
        planned = sum(1 for s in steps if s.get("status") == "planned")
        warnings = sum(1 for s in steps if s.get("status") == "warning")
        failed = sum(1 for s in steps if s.get("status") == "failed")
        manual_required = sum(1 for s in steps if s.get("status") == "manual_required")
        total = len(steps)
        completion_pct = round((completed / max(total, 1)) * 100.0, 1)
        run_id = str(uuid.uuid4())

        with _lock:
            automation_runs_memory.append({
                "id": run_id,
                "tenant_id": tenant_id,
                "trigger": trigger,
                "schedule_id": schedule_id,
                "site_id": payload.site_id,
                "page_url": payload.page_url,
                "dry_run": payload.dry_run,
                "steps": steps,
                "summary": {
                    "total_steps": total,
                    "completed": completed,
                    "planned": planned,
                    "warning": warnings,
                    "failed": failed,
                    "manual_required": manual_required,
                    "completion_pct": completion_pct,
                },
                "created_at": _now_iso(),
            })
            if len(automation_runs_memory) > 4000:
                del automation_runs_memory[:1000]

        _audit(
            tenant_id,
            "automation_run",
            f"site={payload.site_id} trigger={trigger} completed={completed}/{total} dry_run={payload.dry_run}",
        )

        return {
            "status": "ok",
            "run_id": run_id,
            "tenant_id": tenant_id,
            "site_id": payload.site_id,
            "dry_run": payload.dry_run,
            "page_url": payload.page_url,
            "trigger": trigger,
            "schedule_id": schedule_id,
            "steps": steps,
            "summary": {
                "total_steps": total,
                "completed": completed,
                "planned": planned,
                "warning": warnings,
                "failed": failed,
                "manual_required": manual_required,
                "completion_pct": completion_pct,
            },
            "vendors": _vendor_matrix_for_site(site),
            "audit": {
                "audit_id": audit_record["id"],
                "visibility_score": audit_record["visibility_score"],
            } if audit_record else None,
            "generated_at": _now_iso(),
        }

    @router.post("/automation/schedules", status_code=201)
    def create_automation_schedule(payload: AutomationScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:create", 40, 60)
        _get_site(auth.tenant_id, payload.site_id)
        schedule_id = str(uuid.uuid4())
        now = _now_iso()
        record = {
            "id": schedule_id,
            "tenant_id": auth.tenant_id,
            "site_id": payload.site_id,
            "page_url": payload.page_url,
            "interval_minutes": payload.interval_minutes,
            "enabled": payload.enabled,
            "deploy_snippet": payload.deploy_snippet,
            "verify_snippet": payload.verify_snippet,
            "sync_cloudflare": payload.sync_cloudflare,
            "cloudflare_action": payload.cloudflare_action,
            "run_visibility_audit": payload.run_visibility_audit,
            "crawlers_to_test": payload.crawlers_to_test[:10],
            "last_run_at": None,
            "next_run_at": now,
            "created_at": now,
            "updated_at": now,
        }
        with _lock:
            automation_schedules_memory.append(record)
        _audit(auth.tenant_id, "automation_schedule_created", f"schedule_id={schedule_id} site={payload.site_id}")
        return {"status": "ok", "schedule": record}

    @router.get("/automation/schedules")
    def list_automation_schedules(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:list", 120, 60)
        with _lock:
            items = [s.copy() for s in automation_schedules_memory if s.get("tenant_id") == auth.tenant_id]
        items.sort(key=lambda s: str(s.get("created_at", "")), reverse=True)
        return {"status": "ok", "count": len(items), "schedules": items}

    @router.patch("/automation/schedules/{schedule_id}")
    def update_automation_schedule(schedule_id: str, payload: AutomationScheduleUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:update", 60, 60)
        with _lock:
            record = next(
                (s for s in automation_schedules_memory if s.get("id") == schedule_id and s.get("tenant_id") == auth.tenant_id),
                None,
            )
            if record is None:
                raise HTTPException(status_code=404, detail="Automation schedule not found.")
            if payload.page_url is not None:
                record["page_url"] = payload.page_url
            if payload.interval_minutes is not None:
                record["interval_minutes"] = payload.interval_minutes
            if payload.enabled is not None:
                record["enabled"] = payload.enabled
            if payload.deploy_snippet is not None:
                record["deploy_snippet"] = payload.deploy_snippet
            if payload.verify_snippet is not None:
                record["verify_snippet"] = payload.verify_snippet
            if payload.sync_cloudflare is not None:
                record["sync_cloudflare"] = payload.sync_cloudflare
            if payload.cloudflare_action is not None:
                record["cloudflare_action"] = payload.cloudflare_action
            if payload.run_visibility_audit is not None:
                record["run_visibility_audit"] = payload.run_visibility_audit
            if payload.crawlers_to_test is not None:
                record["crawlers_to_test"] = payload.crawlers_to_test[:10]
            if record.get("enabled"):
                record["next_run_at"] = _now_iso()
            record["updated_at"] = _now_iso()
            snapshot = record.copy()
        _audit(auth.tenant_id, "automation_schedule_updated", f"schedule_id={schedule_id}")
        return {"status": "ok", "schedule": snapshot}

    @router.delete("/automation/schedules/{schedule_id}")
    def delete_automation_schedule(schedule_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:delete", 60, 60)
        with _lock:
            before = len(automation_schedules_memory)
            automation_schedules_memory[:] = [
                s for s in automation_schedules_memory
                if not (s.get("id") == schedule_id and s.get("tenant_id") == auth.tenant_id)
            ]
            removed = before - len(automation_schedules_memory)
        if removed == 0:
            raise HTTPException(status_code=404, detail="Automation schedule not found.")
        _audit(auth.tenant_id, "automation_schedule_deleted", f"schedule_id={schedule_id}")
        return {"status": "ok", "removed": True, "schedule_id": schedule_id}

    @router.post("/automation/schedules/execute")
    def execute_automation_schedules(payload: AutomationSchedulesExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:execute", 20, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_schedules = [s for s in automation_schedules_memory if s.get("tenant_id") == auth.tenant_id]

        if payload.schedule_ids:
            wanted = set(payload.schedule_ids)
            tenant_schedules = [s for s in tenant_schedules if str(s.get("id")) in wanted]

        if payload.due_only:
            filtered: list[dict[str, Any]] = []
            for schedule in tenant_schedules:
                if not bool(schedule.get("enabled", True)):
                    continue
                due_at = _parse_iso_datetime(str(schedule.get("next_run_at") or ""))
                if due_at is None or due_at <= now:
                    filtered.append(schedule)
            tenant_schedules = filtered

        tenant_schedules = tenant_schedules[: payload.max_schedules]

        run_results: list[dict[str, Any]] = []
        for schedule in tenant_schedules:
            run_payload = AutomationRunRequest(
                site_id=str(schedule.get("site_id") or ""),
                page_url=str(schedule.get("page_url") or ""),
                dry_run=payload.dry_run,
                deploy_snippet=bool(schedule.get("deploy_snippet", True)),
                verify_snippet=bool(schedule.get("verify_snippet", True)),
                sync_cloudflare=bool(schedule.get("sync_cloudflare", True)),
                cloudflare_action=str(schedule.get("cloudflare_action") or "allow_ai_crawlers"),
                run_visibility_audit=bool(schedule.get("run_visibility_audit", True)),
                crawlers_to_test=list(schedule.get("crawlers_to_test", []))[:10],
            )
            result = _execute_automation_run(
                auth.tenant_id,
                run_payload,
                trigger="schedule_executor",
                schedule_id=str(schedule.get("id") or ""),
            )
            run_results.append(result)

            with _lock:
                record = next(
                    (
                        s for s in automation_schedules_memory
                        if s.get("id") == schedule.get("id") and s.get("tenant_id") == auth.tenant_id
                    ),
                    None,
                )
                if record is not None:
                    record["last_run_at"] = _now_iso()
                    record["last_run_id"] = result.get("run_id")
                    record["last_status"] = "ok" if result.get("summary", {}).get("failed", 0) == 0 else "warning"
                    interval = int(record.get("interval_minutes", 60) or 60)
                    if bool(record.get("enabled", True)):
                        record["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=interval)).isoformat()
                    record["updated_at"] = _now_iso()

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "requested": {
                "schedule_count": len(payload.schedule_ids),
                "due_only": payload.due_only,
                "max_schedules": payload.max_schedules,
                "dry_run": payload.dry_run,
            },
            "summary": {
                "targeted": len(tenant_schedules),
                "runs_created": len(run_results),
                "completed": sum(1 for r in run_results if r.get("summary", {}).get("failed", 0) == 0),
                "warnings": sum(1 for r in run_results if r.get("summary", {}).get("warning", 0) > 0),
                "failed": sum(1 for r in run_results if r.get("summary", {}).get("failed", 0) > 0),
            },
            "runs": run_results,
            "generated_at": _now_iso(),
        }

    @router.get("/automation/history")
    def list_automation_history(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:history", 120, 60)
        with _lock:
            items = [r.copy() for r in automation_runs_memory if r.get("tenant_id") == auth.tenant_id]
        if site_id:
            items = [r for r in items if str(r.get("site_id") or "") == site_id]
        items.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return {"status": "ok", "count": len(items[:limit]), "history": items[:limit]}

    @router.post("/automation/run")
    def run_automation(payload: AutomationRunRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:ace:automation:run", 20, 60)
        return _execute_automation_run(auth.tenant_id, payload, trigger="manual")

    return router
