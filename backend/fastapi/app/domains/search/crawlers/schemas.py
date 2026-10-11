"""Search/Crawlers request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from typing import Literal


class SiteRegisterRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253, description="Root domain, e.g. example.com")
    display_name: str = Field(min_length=1, max_length=120)
    cms_type: Literal[
        "wordpress",
        "shopify",
        "wix",
        "webflow",
        "next_js",
        "nuxt",
        "angular",
        "vue",
        "react",
        "gatsby",
        "hugo",
        "jekyll",
        "custom",
    ] = "custom"
    js_framework: Literal["none", "react", "vue", "angular", "next", "nuxt", "svelte", "other"] = "none"
    cloudflare_zone_id: str | None = Field(default=None, max_length=40)
    deployment_webhook_url: HttpUrl | None = Field(
        default=None, description="Optional CMS/platform webhook for automated snippet deployment"
    )


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
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"], max_length=20
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
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"], max_length=20
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
        default_factory=lambda: ["GPTBot", "ClaudeBot", "PerplexityBot", "Googlebot"], max_length=20
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
