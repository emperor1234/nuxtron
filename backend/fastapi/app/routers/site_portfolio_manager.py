# pyright: reportUnusedFunction=false
"""
Site Portfolio Manager — Alli AI multi-site parity.

Enables agencies and enterprise teams to manage 100+ client sites from a single
dashboard and deploy SEO automation rules across the entire portfolio at once.

Features
--------
  • Site portfolio CRUD (domains, CMS type, team members, tags)
  • SEO automation rule templates:
      - Title tag formulas        (e.g. "{product_name} — Buy {category} Online")
      - Meta description formulas
      - H1 transformation patterns
      - Schema type injection       (Article, Product, LocalBusiness, FAQ, …)
      - Canonical URL rules
      - hreflang injection
  • Bulk rule deployment: 1 rule → N sites → M pages (async job)
  • Deployment history and per-job status tracking
  • Portfolio-wide SEO analytics aggregation
  • White-label configuration (agency branding) per portfolio

Endpoints
---------
POST   /portfolio/sites                              – Add a site
GET    /portfolio/sites                              – List sites
PATCH  /portfolio/sites/{site_id}                   – Update site metadata
DELETE /portfolio/sites/{site_id}                   – Remove site

POST   /portfolio/rules                              – Create automation rule
GET    /portfolio/rules                              – List rules
GET    /portfolio/rules/templates                   – Get pre-built rule templates
POST   /portfolio/rules/templates/{template_id}/apply – Apply template
PUT    /portfolio/rules/{rule_id}                   – Update rule
DELETE /portfolio/rules/{rule_id}                   – Delete rule

POST   /portfolio/rules/{rule_id}/deploy            – Deploy rule (async bulk job)
GET    /portfolio/deployments                        – List deployment jobs
GET    /portfolio/deployments/{job_id}              – Get job status + results

GET    /portfolio/analytics                          – Aggregate portfolio analytics
POST   /portfolio/bulk-optimize                     – Trigger bulk on-page optimization
GET    /portfolio/white-label                        – Get white-label config
PUT    /portfolio/white-label                        – Update white-label config
"""

from __future__ import annotations

import re
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

# ---------------------------------------------------------------------------
# Pre-built rule templates (mirrors Alli AI rule categories)
# ---------------------------------------------------------------------------

RULE_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "ecommerce_product",
        "name": "E-commerce Product Pages",
        "description": "Optimize title, meta, and schema for product pages",
        "url_pattern": r"/products?/|/shop/|/store/",
        "page_type": "product",
        "actions": [
            {"type": "set_title", "formula": "{product_name} — Buy {category} Online | {brand}"},
            {"type": "set_meta_description", "formula": "Shop {product_name} at {brand}. Free shipping on orders over £50. {short_description}"},
            {"type": "add_schema", "schema_type": "Product"},
            {"type": "add_schema", "schema_type": "BreadcrumbList"},
        ],
        "priority": 100,
    },
    {
        "id": "blog_article",
        "name": "Blog Articles",
        "description": "Optimize title and schema for blog posts",
        "url_pattern": r"/blog/|/articles?/|/posts?/|/news/",
        "page_type": "article",
        "actions": [
            {"type": "set_title", "formula": "{article_title} | {site_name} Blog"},
            {"type": "set_meta_description", "formula": "{article_excerpt}"},
            {"type": "add_schema", "schema_type": "Article"},
            {"type": "add_schema", "schema_type": "BreadcrumbList"},
        ],
        "priority": 90,
    },
    {
        "id": "local_business",
        "name": "Local Business / Location Pages",
        "description": "Optimize for local SEO and maps",
        "url_pattern": r"/locations?/|/branches?/|/stores?/|/contact",
        "page_type": "local",
        "actions": [
            {"type": "set_title", "formula": "{business_name} in {city} — {service}"},
            {"type": "set_meta_description", "formula": "Visit {business_name} in {city}. {service} available. Call {phone}. {opening_hours}."},
            {"type": "add_schema", "schema_type": "LocalBusiness"},
        ],
        "priority": 85,
    },
    {
        "id": "faq_page",
        "name": "FAQ Pages",
        "description": "Add FAQPage schema to Q&A pages",
        "url_pattern": r"/faq|/faqs|/help/|/support/|/questions?",
        "page_type": "faq",
        "actions": [
            {"type": "set_title", "formula": "Frequently Asked Questions — {site_name}"},
            {"type": "add_schema", "schema_type": "FAQPage"},
        ],
        "priority": 80,
    },
    {
        "id": "category_page",
        "name": "Category / Collection Pages",
        "description": "Optimize category listing pages",
        "url_pattern": r"/categor|/collections?/|/browse/",
        "page_type": "category",
        "actions": [
            {"type": "set_title", "formula": "{category_name} — Shop {site_name}"},
            {"type": "set_meta_description", "formula": "Browse {category_name} at {site_name}. {product_count} products available."},
            {"type": "add_schema", "schema_type": "CollectionPage"},
        ],
        "priority": 70,
    },
    {
        "id": "service_page",
        "name": "Service Pages",
        "description": "Optimize B2B / agency service pages",
        "url_pattern": r"/services?/|/solutions?/|/offerings?/",
        "page_type": "service",
        "actions": [
            {"type": "set_title", "formula": "{service_name} Services — {company_name}"},
            {"type": "set_meta_description", "formula": "Expert {service_name} services from {company_name}. {unique_value_prop}. Get a free quote."},
            {"type": "add_schema", "schema_type": "Service"},
        ],
        "priority": 75,
    },
]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class PortfolioSiteRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    display_name: str = Field(min_length=1, max_length=120)
    cms_type: Literal[
        "wordpress", "shopify", "wix", "webflow", "next_js", "nuxt",
        "squarespace", "drupal", "contentful", "strapi", "custom"
    ] = "custom"
    tags: list[str] = Field(default_factory=list, max_length=20)
    team_members: list[str] = Field(default_factory=list, max_length=50)
    client_name: str | None = Field(default=None, max_length=120)
    monthly_traffic_estimate: int | None = Field(default=None, ge=0)


class PortfolioSitePatchRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    cms_type: Literal[
        "wordpress", "shopify", "wix", "webflow", "next_js", "nuxt",
        "squarespace", "drupal", "contentful", "strapi", "custom"
    ] | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    team_members: list[str] | None = Field(default=None, max_length=50)
    client_name: str | None = Field(default=None, max_length=120)
    monthly_traffic_estimate: int | None = Field(default=None, ge=0)


class RuleActionModel(BaseModel):
    type: Literal[
        "set_title", "set_meta_description", "set_h1",
        "set_canonical", "add_schema", "add_hreflang",
        "set_og_title", "set_og_description"
    ]
    formula: str | None = Field(default=None, max_length=1000)
    schema_type: str | None = Field(default=None, max_length=80)
    hreflang_lang: str | None = Field(default=None, max_length=10)
    hreflang_url_pattern: str | None = Field(default=None, max_length=500)


class AutomationRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    url_pattern: str = Field(min_length=1, max_length=500, description="Regex pattern to match page URLs")
    page_type: Literal[
        "product", "article", "category", "local", "faq",
        "service", "landing", "home", "other"
    ] = "other"
    content_type: Literal["all", "html", "json_ld"] = "all"
    actions: list[RuleActionModel] = Field(min_length=1, max_length=20)
    target_site_ids: list[str] = Field(
        default_factory=list,
        max_length=200,
        description="Empty = apply to all portfolio sites",
    )
    priority: int = Field(default=50, ge=1, le=200)
    enabled: bool = True


class TemplateApplyRequest(BaseModel):
    target_site_ids: list[str] = Field(default_factory=list, max_length=200)
    overrides: dict[str, Any] = Field(default_factory=dict)


class DeployRequest(BaseModel):
    target_urls: list[str] = Field(
        default_factory=list,
        max_length=10000,
        description="URLs to apply the rule to. Empty = discover from sitemap.",
    )
    dry_run: bool = Field(default=True, description="Simulate without making changes")
    max_pages: int = Field(default=1000, ge=1, le=100000)


class BulkOptimizeRequest(BaseModel):
    site_ids: list[str] = Field(default_factory=list, max_length=200)
    optimization_types: list[Literal[
        "title_tags", "meta_descriptions", "schema_markup",
        "internal_links", "page_speed", "all"
    ]] = Field(default_factory=lambda: ["all"])
    dry_run: bool = True


class WhiteLabelConfigRequest(BaseModel):
    agency_name: str = Field(min_length=1, max_length=120)
    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, max_length=10, description="Hex color, e.g. #1a73e8")
    custom_domain: str | None = Field(default=None, max_length=253)
    support_email: str | None = Field(default=None, max_length=320)
    hide_nuxtron_branding: bool = False
    custom_footer_text: str | None = Field(default=None, max_length=300)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_site_portfolio_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    portfolio_sites_memory: list[dict[str, Any]],
    portfolio_rules_memory: list[dict[str, Any]],
    portfolio_deployments_memory: list[dict[str, Any]],
    white_label_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/portfolio", tags=["Site Portfolio Manager"])
    _lock = threading.Lock()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _audit(tenant_id: str, action: str, detail: str = "") -> None:
        with _lock:
            audit_log_memory.append({
                "id": len(audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "detail": detail,
                "source": "portfolio",
                "created_at": _now_iso(),
            })

    def _get_site(tenant_id: str, site_id: str) -> dict[str, Any]:
        with _lock:
            site = next(
                (s for s in portfolio_sites_memory if s["id"] == site_id and s["tenant_id"] == tenant_id),
                None,
            )
        if site is None:
            raise HTTPException(status_code=404, detail="Portfolio site not found.")
        return site

    def _get_rule(tenant_id: str, rule_id: str) -> dict[str, Any]:
        with _lock:
            rule = next(
                (r for r in portfolio_rules_memory if r["id"] == rule_id and r["tenant_id"] == tenant_id),
                None,
            )
        if rule is None:
            raise HTTPException(status_code=404, detail="Automation rule not found.")
        return rule

    def _resolve_target_sites(tenant_id: str, site_ids: list[str]) -> list[dict[str, Any]]:
        """Return sites from portfolio matching site_ids, or all if empty."""
        with _lock:
            all_sites = [s for s in portfolio_sites_memory if s["tenant_id"] == tenant_id]
        if not site_ids:
            return all_sites
        return [s for s in all_sites if s["id"] in site_ids]

    def _apply_rule_to_url(rule: dict[str, Any], url: str) -> dict[str, Any] | None:
        """Check if rule matches URL and return simulated change record."""
        try:
            if not re.search(rule["url_pattern"], url, re.IGNORECASE):
                return None
        except re.error:
            return None
        changes: list[dict[str, Any]] = []
        for action in rule.get("actions", []):
            changes.append({
                "action_type": action.get("type"),
                "formula": action.get("formula", ""),
                "schema_type": action.get("schema_type", ""),
                "applied": True,
            })
        return {"url": url, "changes": changes}

    # ── Sites ─────────────────────────────────────────────────────────────────

    @router.post("/sites", status_code=201)
    def add_site(payload: PortfolioSiteRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:sites:create", 60, 60)
        domain = payload.domain.lower().strip().removeprefix("https://").removeprefix("http://").split("/")[0]
        site: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "domain": domain,
            "display_name": payload.display_name,
            "cms_type": payload.cms_type,
            "tags": payload.tags,
            "team_members": payload.team_members,
            "client_name": payload.client_name or "",
            "monthly_traffic_estimate": payload.monthly_traffic_estimate,
            "rules_applied": 0,
            "last_optimized_at": None,
            "organic_traffic_delta_pct": 0,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        with _lock:
            portfolio_sites_memory.append(site)
        _audit(auth.tenant_id, "portfolio_site_added", domain)
        return {"status": "ok", "site": site}

    @router.get("/sites")
    def list_sites(
        auth: AuthDep,
        tag: str | None = Query(default=None),
        cms_type: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:sites:list", 120, 60)
        with _lock:
            sites = [
                s.copy() for s in portfolio_sites_memory
                if s["tenant_id"] == auth.tenant_id
                and (not tag or tag in s.get("tags", []))
                and (not cms_type or s.get("cms_type") == cms_type)
            ]
        total = len(sites)
        return {"status": "ok", "total": total, "offset": offset, "limit": limit, "sites": sites[offset:offset + limit]}

    @router.patch("/sites/{site_id}")
    def update_site(site_id: str, payload: PortfolioSitePatchRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:sites:update", 60, 60)
        with _lock:
            site = next(
                (s for s in portfolio_sites_memory if s["id"] == site_id and s["tenant_id"] == auth.tenant_id),
                None,
            )
        if site is None:
            raise HTTPException(status_code=404, detail="Portfolio site not found.")
        updates = payload.model_dump(exclude_none=True)
        site.update(updates)
        site["updated_at"] = _now_iso()
        return {"status": "ok", "site": site}

    @router.delete("/sites/{site_id}")
    def remove_site(site_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:sites:delete", 30, 60)
        with _lock:
            before = len(portfolio_sites_memory)
            portfolio_sites_memory[:] = [
                s for s in portfolio_sites_memory
                if not (s["id"] == site_id and s["tenant_id"] == auth.tenant_id)
            ]
        if len(portfolio_sites_memory) == before:
            raise HTTPException(status_code=404, detail="Portfolio site not found.")
        _audit(auth.tenant_id, "portfolio_site_removed", site_id)
        return {"status": "ok", "site_id": site_id, "removed": True}

    # ── Automation rules ──────────────────────────────────────────────────────

    @router.get("/rules/templates")
    def list_rule_templates(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:templates:list", 120, 60)
        return {"status": "ok", "count": len(RULE_TEMPLATES), "templates": RULE_TEMPLATES}

    @router.post("/rules/templates/{template_id}/apply", status_code=201)
    def apply_template(template_id: str, payload: TemplateApplyRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:templates:apply", 30, 60)
        template = next((t for t in RULE_TEMPLATES if t["id"] == template_id), None)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found.")
        # Build rule from template, applying overrides
        actions = [RuleActionModel(**a) for a in template["actions"]]
        rule_payload = AutomationRuleRequest(
            name=str(payload.overrides.get("name", template["name"])),
            description=str(payload.overrides.get("description", template.get("description", ""))),
            url_pattern=str(payload.overrides.get("url_pattern", template["url_pattern"])),
            page_type=payload.overrides.get("page_type", template["page_type"]),  # type: ignore[arg-type]
            actions=actions,
            target_site_ids=payload.target_site_ids,
            priority=int(payload.overrides.get("priority", template.get("priority", 50))),
        )
        now = _now_iso()
        rule: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "name": rule_payload.name,
            "description": rule_payload.description,
            "url_pattern": rule_payload.url_pattern,
            "page_type": rule_payload.page_type,
            "content_type": "all",
            "actions": [a.model_dump() for a in actions],
            "target_site_ids": rule_payload.target_site_ids,
            "priority": rule_payload.priority,
            "enabled": True,
            "from_template": template_id,
            "deployments_count": 0,
            "pages_affected_total": 0,
            "created_at": now,
            "updated_at": now,
        }
        with _lock:
            portfolio_rules_memory.append(rule)
        _audit(auth.tenant_id, "rule_created_from_template", template_id)
        return {"status": "ok", "rule": rule}

    @router.post("/rules", status_code=201)
    def create_rule(payload: AutomationRuleRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:rules:create", 60, 60)
        # Validate regex pattern
        try:
            re.compile(payload.url_pattern)
        except re.error as exc:
            raise HTTPException(status_code=422, detail=f"Invalid url_pattern regex: {exc}") from exc
        now = _now_iso()
        rule: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description or "",
            "url_pattern": payload.url_pattern,
            "page_type": payload.page_type,
            "content_type": payload.content_type,
            "actions": [a.model_dump() for a in payload.actions],
            "target_site_ids": payload.target_site_ids,
            "priority": payload.priority,
            "enabled": payload.enabled,
            "from_template": None,
            "deployments_count": 0,
            "pages_affected_total": 0,
            "created_at": now,
            "updated_at": now,
        }
        with _lock:
            portfolio_rules_memory.append(rule)
        _audit(auth.tenant_id, "rule_created", payload.name)
        return {"status": "ok", "rule": rule}

    @router.get("/rules")
    def list_rules(
        auth: AuthDep,
        page_type: str | None = Query(default=None),
        enabled_only: bool = Query(default=False),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:rules:list", 120, 60)
        with _lock:
            rules = [
                r.copy() for r in portfolio_rules_memory
                if r["tenant_id"] == auth.tenant_id
                and (not page_type or r.get("page_type") == page_type)
                and (not enabled_only or r.get("enabled"))
            ]
        return {"status": "ok", "count": len(rules), "rules": sorted(rules, key=lambda r: -r.get("priority", 50))}

    @router.put("/rules/{rule_id}")
    def update_rule(rule_id: str, payload: AutomationRuleRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:rules:update", 60, 60)
        try:
            re.compile(payload.url_pattern)
        except re.error as exc:
            raise HTTPException(status_code=422, detail=f"Invalid url_pattern regex: {exc}") from exc
        with _lock:
            rule = next(
                (r for r in portfolio_rules_memory if r["id"] == rule_id and r["tenant_id"] == auth.tenant_id),
                None,
            )
        if rule is None:
            raise HTTPException(status_code=404, detail="Automation rule not found.")
        rule.update({
            "name": payload.name,
            "description": payload.description or "",
            "url_pattern": payload.url_pattern,
            "page_type": payload.page_type,
            "content_type": payload.content_type,
            "actions": [a.model_dump() for a in payload.actions],
            "target_site_ids": payload.target_site_ids,
            "priority": payload.priority,
            "enabled": payload.enabled,
            "updated_at": _now_iso(),
        })
        return {"status": "ok", "rule": rule}

    @router.delete("/rules/{rule_id}")
    def delete_rule(rule_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:rules:delete", 30, 60)
        with _lock:
            before = len(portfolio_rules_memory)
            portfolio_rules_memory[:] = [
                r for r in portfolio_rules_memory
                if not (r["id"] == rule_id and r["tenant_id"] == auth.tenant_id)
            ]
        if len(portfolio_rules_memory) == before:
            raise HTTPException(status_code=404, detail="Automation rule not found.")
        return {"status": "ok", "rule_id": rule_id, "removed": True}

    # ── Deployments ───────────────────────────────────────────────────────────

    @router.post("/rules/{rule_id}/deploy", status_code=201)
    def deploy_rule(rule_id: str, payload: DeployRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:deploy", 20, 60)
        rule = _get_rule(auth.tenant_id, rule_id)
        target_sites = _resolve_target_sites(auth.tenant_id, rule.get("target_site_ids", []))

        if not target_sites:
            raise HTTPException(status_code=422, detail="No sites in portfolio to deploy to. Add sites first.")

        job_id = str(uuid.uuid4())
        now = _now_iso()
        urls = payload.target_urls or [f"https://{s['domain']}/sitemap.xml" for s in target_sites]
        # Apply the rule to each URL (simulate — real implementation would call CMS APIs)
        changes: list[dict[str, Any]] = []
        pages_processed = 0
        pages_changed = 0
        for url in urls[:payload.max_pages]:
            result = _apply_rule_to_url(rule, url)
            pages_processed += 1
            if result:
                changes.append(result)
                pages_changed += 1

        job: dict[str, Any] = {
            "id": job_id,
            "tenant_id": auth.tenant_id,
            "rule_id": rule_id,
            "rule_name": rule["name"],
            "dry_run": payload.dry_run,
            "status": "completed",
            "target_sites": [s["domain"] for s in target_sites],
            "sites_count": len(target_sites),
            "pages_processed": pages_processed,
            "pages_changed": pages_changed,
            "changes": changes[:200],  # cap result set for memory
            "changes_total": pages_changed,
            "created_at": now,
            "completed_at": _now_iso(),
        }

        with _lock:
            portfolio_deployments_memory.append(job)
            if len(portfolio_deployments_memory) > 5000:
                del portfolio_deployments_memory[:1000]
            # Update rule stats (only for real deployments)
            if not payload.dry_run:
                for r in portfolio_rules_memory:
                    if r["id"] == rule_id:
                        r["deployments_count"] = int(r.get("deployments_count", 0)) + 1
                        r["pages_affected_total"] = int(r.get("pages_affected_total", 0)) + pages_changed
                # Update site last_optimized_at
                for s in portfolio_sites_memory:
                    if s["tenant_id"] == auth.tenant_id and s["domain"] in (job["target_sites"] or []):
                        s["last_optimized_at"] = _now_iso()
                        s["rules_applied"] = int(s.get("rules_applied", 0)) + 1

        _audit(auth.tenant_id, "rule_deployed", f"rule={rule_id} job={job_id} pages={pages_changed} dry_run={payload.dry_run}")
        return {"status": "ok", "job": job}

    @router.get("/deployments")
    def list_deployments(
        auth: AuthDep,
        rule_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:deployments:list", 60, 60)
        with _lock:
            jobs = [
                {k: v for k, v in j.items() if k != "changes"}
                for j in portfolio_deployments_memory
                if j["tenant_id"] == auth.tenant_id
                and (not rule_id or j.get("rule_id") == rule_id)
            ]
        return {"status": "ok", "count": len(jobs), "jobs": jobs[-limit:]}

    @router.get("/deployments/{job_id}")
    def get_deployment(job_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:deployments:get", 120, 60)
        with _lock:
            job = next(
                (j.copy() for j in portfolio_deployments_memory
                 if j["id"] == job_id and j["tenant_id"] == auth.tenant_id),
                None,
            )
        if job is None:
            raise HTTPException(status_code=404, detail="Deployment job not found.")
        return {"status": "ok", "job": job}

    # ── Portfolio analytics ───────────────────────────────────────────────────

    @router.get("/analytics")
    def portfolio_analytics(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:analytics", 60, 60)
        with _lock:
            sites = [
                s for s in portfolio_sites_memory
                if s["tenant_id"] == auth.tenant_id
                and (not site_id or s["id"] == site_id)
            ]
            deployments = [
                j for j in portfolio_deployments_memory
                if j["tenant_id"] == auth.tenant_id
                and (not site_id or any(s["domain"] in j.get("target_sites", []) for s in sites))
            ]
            rules = [r for r in portfolio_rules_memory if r["tenant_id"] == auth.tenant_id]

        total_pages_optimized = sum(j.get("pages_changed", 0) for j in deployments if not j.get("dry_run"))
        total_deployments = sum(1 for j in deployments if not j.get("dry_run"))
        active_rules = sum(1 for r in rules if r.get("enabled"))
        total_traffic = sum(
            int(s.get("monthly_traffic_estimate") or 0) for s in sites
        )
        # Per-site summary
        site_summaries: list[dict[str, Any]] = []
        for s in sites[:50]:
            site_deps = [
                j for j in deployments
                if s["domain"] in j.get("target_sites", []) and not j.get("dry_run")
            ]
            site_summaries.append({
                "site_id": s["id"],
                "domain": s["domain"],
                "rules_applied": s.get("rules_applied", 0),
                "pages_optimized": sum(j.get("pages_changed", 0) for j in site_deps),
                "last_optimized_at": s.get("last_optimized_at"),
                "monthly_traffic": s.get("monthly_traffic_estimate"),
            })

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "summary": {
                "sites_total": len(sites),
                "active_rules": active_rules,
                "total_deployments": total_deployments,
                "total_pages_optimized": total_pages_optimized,
                "total_monthly_traffic": total_traffic,
            },
            "sites": site_summaries,
            "generated_at": _now_iso(),
        }

    # ── Bulk optimization ─────────────────────────────────────────────────────

    @router.post("/bulk-optimize", status_code=201)
    def bulk_optimize(payload: BulkOptimizeRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:bulk-optimize", 10, 60)
        target_sites = _resolve_target_sites(auth.tenant_id, payload.site_ids)
        if not target_sites:
            raise HTTPException(status_code=422, detail="No portfolio sites found for bulk optimize.")

        with _lock:
            active_rules = [
                r for r in portfolio_rules_memory
                if r["tenant_id"] == auth.tenant_id and r.get("enabled")
            ]

        job_id = str(uuid.uuid4())
        optimization_types = payload.optimization_types
        if "all" in optimization_types:
            optimization_types = ["title_tags", "meta_descriptions", "schema_markup", "internal_links", "page_speed"]

        jobs_created: list[str] = []
        total_pages = 0
        for site in target_sites[:50]:
            # Simulate creating a deployment job per site
            site_urls = [f"https://{site['domain']}/"]
            for rule in active_rules:
                job: dict[str, Any] = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": auth.tenant_id,
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "dry_run": payload.dry_run,
                    "status": "completed",
                    "target_sites": [site["domain"]],
                    "sites_count": 1,
                    "pages_processed": len(site_urls),
                    "pages_changed": len([u for u in site_urls if _apply_rule_to_url(rule, u)]),
                    "changes": [],
                    "changes_total": 0,
                    "bulk_optimize_job_id": job_id,
                    "optimization_types": optimization_types,
                    "created_at": _now_iso(),
                    "completed_at": _now_iso(),
                }
                with _lock:
                    portfolio_deployments_memory.append(job)
                jobs_created.append(job["id"])
                total_pages += job["pages_processed"]

        _audit(auth.tenant_id, "bulk_optimize_started", f"sites={len(target_sites)} job={job_id}")
        return {
            "status": "ok",
            "bulk_job_id": job_id,
            "dry_run": payload.dry_run,
            "sites_targeted": len(target_sites),
            "optimization_types": optimization_types,
            "deployment_jobs_created": len(jobs_created),
            "total_pages_queued": total_pages,
        }

    # ── White label ───────────────────────────────────────────────────────────

    @router.get("/white-label")
    def get_white_label(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:wl:get", 120, 60)
        with _lock:
            config = next(
                (w.copy() for w in white_label_memory if w["tenant_id"] == auth.tenant_id),
                None,
            )
        if config is None:
            return {"status": "ok", "configured": False, "config": None}
        return {"status": "ok", "configured": True, "config": config}

    @router.put("/white-label")
    def update_white_label(payload: WhiteLabelConfigRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:portfolio:wl:update", 30, 60)
        now = _now_iso()
        with _lock:
            existing = next(
                (w for w in white_label_memory if w["tenant_id"] == auth.tenant_id),
                None,
            )
            if existing:
                existing.update(payload.model_dump())
                existing["updated_at"] = now
                config = existing
            else:
                config = {
                    "tenant_id": auth.tenant_id,
                    **payload.model_dump(),
                    "created_at": now,
                    "updated_at": now,
                }
                white_label_memory.append(config)
        _audit(auth.tenant_id, "white_label_updated", payload.agency_name)
        return {"status": "ok", "config": config}

    return router
