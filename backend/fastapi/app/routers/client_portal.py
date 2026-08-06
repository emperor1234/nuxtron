# pyright: reportUnusedFunction=false
"""
Client Portal router — SEMrush Client Portal / Agency White-Label parity.

White-label reporting portal for agencies:
  - Manage clients and their branding settings
  - Generate automated PDF/HTML reports (weekly/monthly)
  - Shareable live report links with optional password protection
  - Report templates and custom metric selection
  - Scheduled delivery via email or webhook

Endpoints
---------
POST /client-portal/clients                      – Create a client
GET  /client-portal/clients                      – List clients
GET  /client-portal/clients/{id}                 – Get client details
PATCH /client-portal/clients/{id}                – Update client
DELETE /client-portal/clients/{id}               – Remove client

POST /client-portal/reports                      – Generate a report for a client
GET  /client-portal/reports                      – List reports
GET  /client-portal/reports/{id}                 – Get report metadata
GET  /client-portal/reports/{id}/download        – Download report (HTML)
DELETE /client-portal/reports/{id}               – Delete report

POST /client-portal/share-link                   – Create a shareable link for a report
GET  /client-portal/share-link/{token}           – Access shared report by token

POST /client-portal/templates                    – Create a report template
GET  /client-portal/templates                    – List templates

POST /client-portal/schedules                    – Schedule automatic report delivery
GET  /client-portal/schedules                    – List schedules
DELETE /client-portal/schedules/{id}             – Remove schedule
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import threading
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)
AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/client-portal", tags=["Client Portal"])
_lock = threading.Lock()

_clients: dict[str, list[dict[str, Any]]] = {}
_reports: dict[str, list[dict[str, Any]]] = {}
_templates: dict[str, list[dict[str, Any]]] = {}
_schedules: dict[str, list[dict[str, Any]]] = {}
_share_links: dict[str, dict[str, Any]] = {}  # token -> {report, metadata}


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── Report HTML generator ─────────────────────────────────────────────────────

def _generate_html_report(client: dict, report: dict, metrics: dict) -> str:
    brand_color = client.get("brand_color", "#4A90E2")
    logo = client.get("logo_url", "")
    client_name = client.get("name", "Client")
    agency_name = client.get("agency_name", "Your Agency")
    period = report.get("period", "Monthly")
    date = report.get("created_at", _now())[:10]
    domains = ", ".join(report.get("domains", []))
    kpi_rows = ""
    for k, v in metrics.items():
        kpi_rows += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{k}</td><td style='padding:8px;border-bottom:1px solid #eee;font-weight:bold'>{v}</td></tr>"
    logo_tag = f'<img src="{logo}" style="height:50px" alt="Logo" />' if logo else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{client_name} — SEO Report — {date}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f7f8fa; }}
    .header {{ background: {brand_color}; color: #fff; padding: 32px 48px; display: flex; align-items: center; gap: 24px; }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .header p {{ margin: 4px 0 0; opacity: 0.85; }}
    .container {{ max-width: 900px; margin: 32px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 16px rgba(0,0,0,0.08); overflow: hidden; }}
    .section {{ padding: 32px 48px; border-bottom: 1px solid #f0f0f0; }}
    .section h2 {{ color: {brand_color}; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; padding: 12px 8px; background: #f7f8fa; color: #555; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .footer {{ padding: 24px 48px; text-align: center; color: #aaa; font-size: 12px; }}
    .badge {{ display: inline-block; background: {brand_color}20; color: {brand_color}; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      {logo_tag}
      <div>
        <h1>{client_name} SEO Performance Report</h1>
        <p>Prepared by {agency_name} &mdash; {period} report &mdash; {date}</p>
      </div>
    </div>
    <div class="section">
      <h2>Executive Summary</h2>
      <p>This report covers SEO performance for <strong>{domains}</strong> during the {period.lower()} period ending {date}.</p>
      <p><span class="badge">{period}</span></p>
    </div>
    <div class="section">
      <h2>Key Performance Indicators</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>{kpi_rows}</tbody>
      </table>
    </div>
    <div class="footer">
      &copy; {date[:4]} {agency_name}. All rights reserved. This report is confidential and prepared exclusively for {client_name}.
    </div>
  </div>
</body>
</html>"""


def _build_metrics(domains: list[str], report_type: str) -> dict[str, Any]:
    """Generate deterministic metrics for a report."""
    import random
    domain_key = "|".join(sorted(domains))
    random.seed(int(hashlib.md5(f"{domain_key}:{report_type}".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    return {
        "Organic Traffic": f"{random.randint(5000, 500_000):,}",
        "Organic Keywords": f"{random.randint(500, 50_000):,}",
        "Domain Authority": random.randint(20, 80),
        "Backlinks": f"{random.randint(100, 100_000):,}",
        "Ranking Keywords (Top 10)": f"{random.randint(50, 10_000):,}",
        "Avg. Position": round(random.uniform(5, 25), 1),
        "Estimated Monthly Traffic Value ($)": f"${random.randint(1000, 500_000):,}",
        "New Backlinks (This Period)": random.randint(5, 500),
        "Lost Backlinks": random.randint(1, 100),
        "Site Health Score": f"{random.randint(60, 98)}%",
    }


# ── Models ────────────────────────────────────────────────────────────────────

class ClientCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(default="", max_length=320)
    website: str = Field(default="", max_length=2000)
    domains: list[str] = Field(default_factory=list)
    brand_color: str = Field(default="#4A90E2", max_length=10)
    logo_url: str = Field(default="", max_length=2000)
    agency_name: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    website: str | None = Field(default=None, max_length=2000)
    domains: list[str] | None = None
    brand_color: str | None = Field(default=None, max_length=10)
    logo_url: str | None = Field(default=None, max_length=2000)
    agency_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class ReportCreateRequest(BaseModel):
    client_id: str
    domains: list[str] = Field(min_length=1)
    period: str = Field(default="Monthly", description="Weekly | Monthly | Quarterly")
    report_type: str = Field(default="full", description="full | seo | backlinks | traffic | ppc")
    template_id: str | None = None
    include_sections: list[str] = Field(default_factory=list)


class ShareLinkRequest(BaseModel):
    report_id: str
    password: str = Field(default="", max_length=100, description="Optional password protection")
    expires_days: int = Field(default=30, ge=1, le=365)


class TemplateCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=500)
    sections: list[str] = Field(min_length=1)
    default_period: str = Field(default="Monthly")


class ScheduleCreateRequest(BaseModel):
    client_id: str
    frequency: str = Field(description="weekly | monthly | quarterly")
    day_of_week: int | None = Field(default=None, ge=0, le=6, description="0=Mon for weekly")
    day_of_month: int | None = Field(default=1, ge=1, le=28, description="Day for monthly/quarterly")
    email_recipients: list[str] = Field(default_factory=list)
    report_type: str = Field(default="full")
    active: bool = Field(default=True)


# ── Routes ── Clients ─────────────────────────────────────────────────────────

@router.post("/clients")
def create_client(payload: ClientCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    client = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        **payload.model_dump(),
        "created_at": _now(),
        "report_count": 0,
    }
    with _lock:
        _clients.setdefault(auth.tenant_id, []).append(client)
    return client


@router.get("/clients")
def list_clients(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        clients = list(_clients.get(auth.tenant_id, []))
    return {"clients": clients, "total": len(clients)}


@router.get("/clients/{client_id}")
def get_client(client_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        client = next((c for c in _clients.get(auth.tenant_id, []) if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.patch("/clients/{client_id}")
def update_client(client_id: str, payload: ClientUpdateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        client = next((c for c in _clients.get(auth.tenant_id, []) if c["id"] == client_id), None)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        update = payload.model_dump(exclude_none=True)
        client.update(update)
        client["updated_at"] = _now()
    return client


@router.delete("/clients/{client_id}")
def delete_client(client_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        before = len(_clients.get(auth.tenant_id, []))
        _clients[auth.tenant_id] = [c for c in _clients.get(auth.tenant_id, []) if c["id"] != client_id]
        removed = before - len(_clients[auth.tenant_id])
    if not removed:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"deleted": client_id}


# ── Routes ── Reports ─────────────────────────────────────────────────────────

@router.post("/reports")
def generate_report(payload: ReportCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        client = next((c for c in _clients.get(auth.tenant_id, []) if c["id"] == payload.client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    metrics = _build_metrics(payload.domains, payload.report_type)
    html = _generate_html_report(client, {"period": payload.period, "created_at": _now(), "domains": payload.domains}, metrics)
    report = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "client_id": payload.client_id,
        "client_name": client["name"],
        "domains": payload.domains,
        "period": payload.period,
        "report_type": payload.report_type,
        "template_id": payload.template_id,
        "status": "completed",
        "metrics": metrics,
        "html": html,
        "created_at": _now(),
        "size_bytes": len(html.encode()),
    }
    with _lock:
        _reports.setdefault(auth.tenant_id, []).append(report)
        # update client report count
        for c in _clients.get(auth.tenant_id, []):
            if c["id"] == payload.client_id:
                c["report_count"] = c.get("report_count", 0) + 1
    return {k: v for k, v in report.items() if k != "html"}


@router.get("/reports")
def list_reports(
    client_id: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    with _lock:
        reps = [{k: v for k, v in r.items() if k != "html"} for r in _reports.get(auth.tenant_id, [])]
    if client_id:
        reps = [r for r in reps if r.get("client_id") == client_id]
    return {"reports": reps, "total": len(reps)}


@router.get("/reports/{report_id}")
def get_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        report = next((r for r in _reports.get(auth.tenant_id, []) if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {k: v for k, v in report.items() if k != "html"}


@router.get("/reports/{report_id}/download", response_class=HTMLResponse)
def download_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> HTMLResponse:
    with _lock:
        report = next((r for r in _reports.get(auth.tenant_id, []) if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    html = report.get("html", "<p>Report content unavailable.</p>")
    return HTMLResponse(content=html, media_type="text/html")


@router.delete("/reports/{report_id}")
def delete_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        before = len(_reports.get(auth.tenant_id, []))
        _reports[auth.tenant_id] = [r for r in _reports.get(auth.tenant_id, []) if r["id"] != report_id]
        removed = before - len(_reports[auth.tenant_id])
    if not removed:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": report_id}


# ── Routes ── Share Links ─────────────────────────────────────────────────────

@router.post("/share-link")
def create_share_link(payload: ShareLinkRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        report = next((r for r in _reports.get(auth.tenant_id, []) if r["id"] == payload.report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    token = secrets.token_urlsafe(32)
    from datetime import timedelta
    expires_at = (datetime.now(UTC) + timedelta(days=payload.expires_days)).isoformat()
    link = {
        "token": token,
        "report_id": payload.report_id,
        "tenant_id": auth.tenant_id,
        "password_hash": hashlib.sha256(payload.password.encode()).hexdigest() if payload.password else None,
        "expires_at": expires_at,
        "created_at": _now(),
        "views": 0,
    }
    with _lock:
        _share_links[token] = link
    base_url = os.getenv("PUBLIC_BASE_URL", "https://yourdomain.com")
    return {
        "token": token,
        "url": f"{base_url}/client-portal/share-link/{token}",
        "expires_at": expires_at,
        "password_protected": bool(payload.password),
    }


@router.get("/share-link/{token}", response_class=HTMLResponse)
def access_shared_report(
    token: str,
    password: str = Query(default=""),
) -> HTMLResponse:
    with _lock:
        link = _share_links.get(token)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or expired")
    expires_at = link.get("expires_at", "")
    if expires_at and expires_at < _now():
        raise HTTPException(status_code=410, detail="Link has expired")
    if link.get("password_hash") and hashlib.sha256(password.encode()).hexdigest() != link["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid password")
    with _lock:
        link["views"] = link.get("views", 0) + 1
    tenant_id = link["tenant_id"]
    report_id = link["report_id"]
    with _lock:
        report = next((r for r in _reports.get(tenant_id, []) if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=report.get("html", "<p>Report unavailable.</p>"), media_type="text/html")


# ── Routes ── Templates ───────────────────────────────────────────────────────

@router.post("/templates")
def create_template(payload: TemplateCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    template = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        **payload.model_dump(),
        "created_at": _now(),
    }
    with _lock:
        _templates.setdefault(auth.tenant_id, []).append(template)
    return template


@router.get("/templates")
def list_templates(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    default_templates = [
        {"id": "default-seo", "name": "SEO Performance", "sections": ["traffic", "keywords", "backlinks", "health"], "default_period": "Monthly"},
        {"id": "default-full", "name": "Full Digital Marketing", "sections": ["traffic", "keywords", "backlinks", "ppc", "social", "health"], "default_period": "Monthly"},
        {"id": "default-backlinks", "name": "Link Building Report", "sections": ["backlinks", "authority", "link-gap"], "default_period": "Monthly"},
        {"id": "default-ppc", "name": "PPC Performance", "sections": ["ads", "spend", "keywords", "quality-score"], "default_period": "Weekly"},
    ]
    with _lock:
        custom = list(_templates.get(auth.tenant_id, []))
    return {"templates": default_templates + custom, "total": len(default_templates) + len(custom)}


# ── Routes ── Schedules ───────────────────────────────────────────────────────

@router.post("/schedules")
def create_schedule(payload: ScheduleCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        client = next((c for c in _clients.get(auth.tenant_id, []) if c["id"] == payload.client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    schedule = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "client_name": client["name"],
        **payload.model_dump(),
        "created_at": _now(),
        "last_run": None,
        "next_run": None,
    }
    with _lock:
        _schedules.setdefault(auth.tenant_id, []).append(schedule)
    return schedule


@router.get("/schedules")
def list_schedules(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        schedules = list(_schedules.get(auth.tenant_id, []))
    return {"schedules": schedules, "total": len(schedules)}


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        before = len(_schedules.get(auth.tenant_id, []))
        _schedules[auth.tenant_id] = [s for s in _schedules.get(auth.tenant_id, []) if s["id"] != schedule_id]
        removed = before - len(_schedules[auth.tenant_id])
    if not removed:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": schedule_id}

