"""Search/Crawlers use cases: now iso."""

from __future__ import annotations
from ..constants import KNOWN_CRAWLERS
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import SiteRegisterRequest
from ..services.detect_crawler import _detect_crawler
from ....identity.secure_egress import OutboundTarget
from ....identity.secure_egress import UnsafeOutboundURL
from ....identity.secure_egress import resolve_outbound_target
from ....identity.secure_egress import safe_outbound_get
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
import hashlib
import httpx
import os
import time
import uuid
from urllib.parse import urlsplit


def helper_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def helper_snippet_id(tenant_id: str, domain: str) -> str:
    return hashlib.sha256(f"{tenant_id}:{domain}".encode()).hexdigest()[:16]


def helper_generate_snippet(site_id: str, snippet_key: str, domain: str) -> str:
    cdn_base = os.getenv("ALLI_CDN_BASE_URL", "https://cdn.nuxtron.ai").rstrip("/")
    return f"<!-- Nuxtron AI Crawler Enablement Snippet | site={domain} -->\n<script>\n(function(w,d,s,k,id){{\n  if(w.__NUXTRON_ACE__)return;\n  w.__NUXTRON_ACE__=1;\n  var t=d.createElement(s);t.async=1;\n  t.src='{cdn_base}/ace.js?k='+k+'&s='+id;\n  d.head.appendChild(t);\n}})(window,document,'script','{snippet_key}','{site_id}');\n</script>"


def helper_get_site(runtime: ContextRuntime, tenant_id: str, site_id: str) -> dict[str, Any]:
    with runtime._lock:
        site = next((s for s in runtime.sites_memory if s["id"] == site_id and s["tenant_id"] == tenant_id), None)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return site


def helper_audit(runtime: ContextRuntime, tenant_id: str, action: str, detail: str = "") -> None:
    with runtime._lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "detail": detail,
                "source": "ai-crawler",
                "created_at": helper_now_iso(),
            }
        )


def helper_parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def helper_sync_cloudflare_site(site: dict[str, Any], action: str) -> dict[str, Any]:
    zone_id = str(site.get("cloudflare_zone_id") or "").strip()
    cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    site_id = str(site.get("id") or "")
    domain = str(site.get("domain") or "")
    if not zone_id:
        return {"site_id": site_id, "domain": domain, "synced": False, "reason": "missing_cloudflare_zone_id"}
    if not cf_token:
        return {"site_id": site_id, "domain": domain, "synced": False, "reason": "missing_cloudflare_api_token"}
    ai_ua_patterns = [c["name"] for c in KNOWN_CRAWLERS if c["category"] == "ai_search" and c["enabled"]]
    expression = " or ".join((f'(http.user_agent contains "{name}")' for name in ai_ua_patterns[:20]))
    rule_action = "skip" if action == "allow_ai_crawlers" else "block"
    rule_description = f"Nuxtron ACE - {action.replace('_', ' ').title()}"
    try:
        with httpx.Client(timeout=15.0, trust_env=False, follow_redirects=False) as client:
            list_resp = client.get(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules",
                headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                params={"description": "Nuxtron ACE", "per_page": 5},
            )
            existing_rules = list_resp.json().get("result", []) if list_resp.is_success else []
            existing_rule_id = existing_rules[0]["id"] if existing_rules else None
            filter_body = {"expression": expression, "description": f"ACE filter - {action}"}
            rule_body = {"filter": filter_body, "action": rule_action, "description": rule_description}
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


def helper_validate_site_url(site_domain: str, page_url: str) -> OutboundTarget:
    """Require a public URL on the registered site and return its pinned destination."""
    target = resolve_outbound_target(page_url, allow_http=True)
    domain = str(site_domain or "").strip().rstrip(".").lower()
    if "://" in domain:
        domain = urlsplit(domain).hostname or ""
    try:
        domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UnsafeOutboundURL("Registered site hostname is invalid.") from exc
    if not domain or not (target.host == domain or target.host.endswith(f".{domain}")):
        raise UnsafeOutboundURL("Page URL must belong to the registered site.")
    return target


def helper_verify_snippet_installation(
    snippet_key: str,
    page_url: str,
    *,
    site_domain: str,
    pinned_target: OutboundTarget | None = None,
) -> tuple[bool, str]:
    installed = False
    detail = ""
    try:
        timeout = float(os.getenv("ACE_VERIFY_TIMEOUT", "8"))
        headers = {"User-Agent": "NuxtronACEVerifier/1.0"}
        target = pinned_target or helper_validate_site_url(site_domain, page_url)
        resp = safe_outbound_get(
            target,
            headers=headers,
            timeout=timeout,
            allow_http=True,
            allowed_host_suffix=site_domain,
            max_response_bytes=2_000_000,
        )
        body = resp.text or ""
        installed = snippet_key in body or "__NUXTRON_ACE__" in body
        detail = "Snippet detected in page source." if installed else "Snippet not found in page source."
    except Exception as exc:
        detail = f"Verification request failed ({type(exc).__name__})."
    return (installed, detail)


def helper_run_visibility_audit_for_url(
    tenant_id: str,
    *,
    site_id: str,
    page_url: str,
    crawlers_to_test: list[str],
    site_domain: str | None = None,
    pinned_target: OutboundTarget | None = None,
) -> dict[str, Any]:
    if pinned_target is None and site_domain:
        pinned_target = helper_validate_site_url(site_domain, page_url)
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
            resp = safe_outbound_get(
                pinned_target or page_url,
                headers={"User-Agent": ua},
                timeout=15.0,
                allow_http=True,
                allowed_host_suffix=site_domain,
                max_response_bytes=2_000_000,
            )
            status_code = resp.status_code
            html_content = resp.text
            render_time_ms = round((time.perf_counter() - started) * 1000)
            content_ratio = len(html_content.strip()) < 500
            has_js_framework_markers = any(
                (m in html_content for m in ["__NEXT_DATA__", "nuxt", "__vue__", "ng-version", "data-reactroot"])
            )
            is_js_rendered = content_ratio or has_js_framework_markers
            if is_js_rendered:
                issue = "Page appears to be JS-rendered and may be invisible to AI crawlers without SSR."
        except Exception as exc:
            issue = f"Page fetch failed ({type(exc).__name__})."
            status_code = 0
        results.append(
            {
                "crawler_name": crawler_name,
                "crawler_category": crawler_info.get("category", "unknown"),
                "status_code": status_code,
                "render_time_ms": render_time_ms,
                "content_length": len(html_content),
                "is_js_rendered": is_js_rendered,
                "visible_to_crawler": not is_js_rendered and status_code == 200,
                "issue": issue,
                "recommendation": "Enable SSR/pre-rendering via AI Crawler Enablement snippet."
                if is_js_rendered
                else "Content is accessible."
                if status_code == 200
                else "Fix HTTP error before optimizing for AI crawlers.",
            }
        )
    visible_count = sum((1 for r in results if r.get("visible_to_crawler")))
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
        "created_at": helper_now_iso(),
    }


def helper_vendor_matrix_for_site(site: dict[str, Any]) -> list[dict[str, Any]]:
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


def helper_vendor_chart_for_sites(tenant_sites: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    chart_index: dict[str, dict[str, Any]] = {}
    total_integrations = 0
    configured_integrations = 0
    for site in tenant_sites:
        vendors = helper_vendor_matrix_for_site(site)
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
    return (chart, summary)


def execute_register_site(runtime: ContextRuntime, payload: SiteRegisterRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:sites:create", 30, 60)
    domain_clean = payload.domain.lower().strip().removeprefix("https://").removeprefix("http://").split("/")[0]
    site_id = str(uuid.uuid4())
    snippet_key = helper_snippet_id(auth.tenant_id, domain_clean)
    snippet = helper_generate_snippet(site_id, snippet_key, domain_clean)
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
        "created_at": helper_now_iso(),
        "updated_at": helper_now_iso(),
    }
    with runtime._lock:
        runtime.sites_memory.append(site)
    helper_audit(runtime, auth.tenant_id, "site_registered", domain_clean)
    return {"status": "ok", "site": site, "snippet": snippet}


def execute_list_sites(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:sites:list", 120, 60)
    with runtime._lock:
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    return {"status": "ok", "count": len(tenant_sites), "sites": tenant_sites}


def execute_unregister_site(runtime: ContextRuntime, site_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:sites:delete", 20, 60)
    with runtime._lock:
        before = len(runtime.sites_memory)
        runtime.sites_memory[:] = [
            s for s in runtime.sites_memory if not (s["id"] == site_id and s["tenant_id"] == auth.tenant_id)
        ]
        removed = before - len(runtime.sites_memory)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Site not found.")
    helper_audit(runtime, auth.tenant_id, "site_unregistered", site_id)
    return {"status": "ok", "site_id": site_id, "removed": True}


def execute_get_snippet(runtime: ContextRuntime, site_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:snippet:get", 60, 60)
    site = helper_get_site(runtime, auth.tenant_id, site_id)
    snippet = helper_generate_snippet(site_id, site["snippet_key"], site["domain"])
    return {"status": "ok", "site_id": site_id, "domain": site["domain"], "snippet": snippet}
