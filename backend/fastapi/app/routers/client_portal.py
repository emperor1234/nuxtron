"""Client Portal compatibility routes.

This customer-facing reporting surface is unavailable until durable, tenant-scoped
client/report storage, verified analytics inputs, a delivery worker, and production
share-link configuration are connected. The routes remain registered so existing
API clients receive an explicit typed error instead of fabricated success data.
"""

from __future__ import annotations

import html
import ipaddress
import re
from typing import Any, NoReturn
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..deps import AuthContext, require_auth


class ClientPortalUnavailableDetail(BaseModel):
    code: str
    message: str


class ClientPortalUnavailableEnvelope(BaseModel):
    detail: ClientPortalUnavailableDetail


_UNAVAILABLE_MESSAGE = (
    "Client portal reporting is unavailable until durable workspace storage, verified analytics sources, "
    "scheduled delivery, and production share-link configuration are connected. No sample metrics are generated."
)
_UNAVAILABLE_RESPONSE = {
    501: {
        "model": ClientPortalUnavailableEnvelope,
        "description": "Client Portal is unavailable; no sample reports, metrics, or share links are generated.",
    }
}

router = APIRouter(prefix="/client-portal", tags=["Client Portal"])


def _raise_unavailable() -> NoReturn:
    raise HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": _UNAVAILABLE_MESSAGE},
    )


def _escape_html(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _safe_report_brand_color(value: object) -> str:
    candidate = str(value or "")
    return candidate if re.fullmatch(r"#[0-9A-Fa-f]{6}", candidate) else "#4A90E2"


def _safe_report_logo_src(value: object) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
        if (
            parsed.scheme.lower() != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return ""
        normalized_hostname = hostname.lower().rstrip(".")
        if normalized_hostname in {"localhost", "localhost.localdomain"}:
            return ""
        try:
            if not ipaddress.ip_address(hostname).is_global:
                return ""
        except ValueError:
            if (
                not normalized_hostname
                or "." not in normalized_hostname
                or normalized_hostname.endswith((".local", ".internal", ".lan", ".home", ".test"))
            ):
                return ""
    except ValueError:
        return ""
    return _escape_html(candidate)


def _generate_html_report(client: dict[str, Any], report: dict[str, Any], metrics: dict[str, Any]) -> str:
    """Render supplied values safely; this helper does not calculate business metrics."""
    brand_color = _safe_report_brand_color(client.get("brand_color", "#4A90E2"))
    logo = _safe_report_logo_src(client.get("logo_url", ""))
    client_name = _escape_html(client.get("name", "Client"))
    agency_name = _escape_html(client.get("agency_name", "Your Agency"))
    period = _escape_html(report.get("period", "Monthly"))
    date = _escape_html(str(report.get("created_at", ""))[:10])
    domains = _escape_html(", ".join(str(domain) for domain in report.get("domains", [])))
    kpi_rows = "".join(
        "<tr><td style='padding:8px;border-bottom:1px solid #eee'>"
        f"{_escape_html(key)}</td><td style='padding:8px;border-bottom:1px solid #eee;font-weight:bold'>"
        f"{_escape_html(value)}</td></tr>"
        for key, value in metrics.items()
    )
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


class ClientCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(default="", max_length=320)
    website: str = Field(default="", max_length=2000)
    domains: list[str] = Field(default_factory=list)
    brand_color: str = Field(default="#4A90E2", max_length=10)
    logo_url: str = Field(default="", max_length=2000)
    agency_name: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, value: str) -> str:
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError("brand_color must use #RRGGBB format")
        return value

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str) -> str:
        if value and not _safe_report_logo_src(value):
            raise ValueError("logo_url must be an HTTPS URL on a public hostname")
        return value.strip()


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    website: str | None = Field(default=None, max_length=2000)
    domains: list[str] | None = None
    brand_color: str | None = Field(default=None, max_length=10)
    logo_url: str | None = Field(default=None, max_length=2000)
    agency_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError("brand_color must use #RRGGBB format")
        return value

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str | None) -> str | None:
        if value is not None and value and not _safe_report_logo_src(value):
            raise ValueError("logo_url must be an HTTPS URL on a public hostname")
        return value.strip() if value is not None else None


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


@router.post("/clients", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def create_client(payload: ClientCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/clients", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def list_clients(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/clients/{client_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def get_client(client_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.patch("/clients/{client_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def update_client(
    client_id: str,
    payload: ClientUpdateRequest,
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    return _raise_unavailable()


@router.delete("/clients/{client_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def delete_client(client_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.post("/reports", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def generate_report(payload: ReportCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/reports", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def list_reports(
    client_id: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/reports/{report_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def get_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/reports/{report_id}/download", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def download_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> NoReturn:
    return _raise_unavailable()


@router.delete("/reports/{report_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def delete_report(report_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.post("/share-link", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def create_share_link(payload: ShareLinkRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/share-link/{token}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def access_shared_report(token: str, password: str = Query(default="")) -> NoReturn:
    return _raise_unavailable()


@router.post("/templates", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def create_template(payload: TemplateCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/templates", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def list_templates(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.post("/schedules", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def create_schedule(payload: ScheduleCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.get("/schedules", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def list_schedules(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()


@router.delete("/schedules/{schedule_id}", status_code=501, response_model=None, responses=_UNAVAILABLE_RESPONSE)
def delete_schedule(schedule_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    return _raise_unavailable()
