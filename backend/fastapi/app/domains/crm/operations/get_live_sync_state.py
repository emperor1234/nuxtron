"""Crm use cases: get live sync state."""

from ....database import get_db_session
from ....integrations.vendor_manager import VendorCredentials
from ....integrations.vendor_manager import VendorType
from ....models import Company
from ....models import Contact
from ....models import Deal
from ..constants import AuthDep
from ..constants import CONTACT_NOT_FOUND
from ..constants import PIPELINE_STAGES
from ..runtime import ContextRuntime
from ..schemas import CompanyCreateRequest
from ..schemas import ContactCreateRequest
from ..schemas import ContactDedupeRequest
from ..schemas import ContactScoreRequest
from ..schemas import DealCreateRequest
from ..schemas import HubSpotConnectRequest
from ..schemas import HubSpotSyncContactsRequest
from .contact_to_dict import helper_company_to_dict
from .contact_to_dict import helper_contact_to_dict
from .contact_to_dict import helper_deal_to_dict
from .contact_to_dict import helper_upsert_contact_from_vendor
from .task_to_dict import helper_audit
from .task_to_dict import helper_dedupe_contacts_impl
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import or_
from starlette.concurrency import run_in_threadpool
from typing import Annotated
from typing import Any


def helper_get_live_sync_state(runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    existing = next((row for row in runtime.live_sync_state_memory if row.get("tenant_id") == tenant_id), None)
    now_iso = datetime.now(UTC).isoformat()
    if existing is not None:
        return existing
    state = {
        "id": len(runtime.live_sync_state_memory) + 1,
        "tenant_id": tenant_id,
        "enabled": True,
        "interval_seconds": 30,
        "last_sync_at": None,
        "last_success_at": None,
        "lag_seconds": 0,
        "events_processed_24h": 0,
        "conflict_queue": 0,
        "updated_at": now_iso,
        "provider_status": {"crm_core": "healthy", "billing": "healthy", "automation": "healthy", "inbox": "healthy"},
    }
    runtime.live_sync_state_memory.append(state)
    return state


def helper_parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) == 10:
        raw = f"{raw}T00:00:00+00:00"
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def helper_is_in_window(value: Any, window_start: datetime) -> bool:
    parsed = helper_parse_iso_datetime(value)
    return parsed is not None and parsed >= window_start


def helper_to_window_days(days: int) -> int:
    if days <= 7:
        return 7
    if days >= 365:
        return 365
    return days


def execute_create_contact(runtime: ContextRuntime, payload: ContactCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:contacts:create", 120, 60)
    with get_db_session() as session:
        existing = session.query(Contact).filter_by(tenant_id=auth.tenant_id, email=str(payload.email)).first()
        if existing is not None:
            return {
                "status": "ok",
                "tenant_id": auth.tenant_id,
                "contact": helper_contact_to_dict(existing),
                "duplicate": True,
            }
        contact = Contact(
            tenant_id=auth.tenant_id,
            email=str(payload.email),
            first_name=payload.first_name,
            last_name=payload.last_name,
            company=payload.company,
            phone=payload.phone,
            lifecycle_stage=payload.lifecycle_stage,
            score=0,
            data={"tags": payload.tags, "properties": payload.properties, "source": "api"},
        )
        session.add(contact)
        session.flush()
        snapshot = helper_contact_to_dict(contact)
    helper_audit(runtime, auth.tenant_id, "crm_contact_created", int(snapshot["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "contact": snapshot}


async def execute_connect_hubspot(
    runtime: ContextRuntime, payload: HubSpotConnectRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:hubspot:connect", 60, 60)
    token = (payload.access_token or payload.api_key or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Provide access_token or api_key.")
    endpoint_url = (payload.endpoint_url or "").strip() or None
    credentials = VendorCredentials(
        vendor_type=VendorType.CRM,
        platform="hubspot",
        api_key=token,
        access_token=token,
        endpoint_url=endpoint_url,
        additional_config={"portal_id": payload.portal_id or ""},
    )
    runtime.vendor_manager.store_credentials("hubspot_api", credentials)
    verified = False
    if payload.verify_live:
        response = await runtime.vendor_manager.make_request(
            "hubspot_api",
            "GET",
            "/crm/v3/objects/contacts",
            params={"limit": 1, "properties": "email,firstname,lastname"},
        )
        verified = isinstance(response, dict)
    helper_audit(runtime, auth.tenant_id, "crm_hubspot_connected", payload.portal_id or "portal_not_set")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "integration": {"provider": "hubspot", "connected": True, "verified": verified, "portal_id": payload.portal_id},
    }


def execute_hubspot_status(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:hubspot:status", 120, 60)
    credentials = runtime.vendor_manager.get_credentials("hubspot_api")
    config = credentials.additional_config if credentials and isinstance(credentials.additional_config, dict) else {}
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "integration": {
            "provider": "hubspot",
            "connected": credentials is not None,
            "portal_id": config.get("portal_id") if config else None,
        },
    }


async def execute_sync_hubspot_contacts(
    runtime: ContextRuntime, payload: HubSpotSyncContactsRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:hubspot:sync:contacts", 30, 60)
    if not runtime.vendor_manager.has_credentials("hubspot_api"):
        raise HTTPException(status_code=400, detail="HubSpot integration is not connected.")
    response = await runtime.vendor_manager.make_request(
        "hubspot_api",
        "GET",
        "/crm/v3/objects/contacts",
        params={"limit": payload.limit, "properties": "email,firstname,lastname,phone,company,lifecyclestage"},
    )
    rows = response.get("results", []) if isinstance(response, dict) else []
    created = 0
    updated = 0
    skipped = 0
    for row in rows:
        properties = row.get("properties", {}) if isinstance(row, dict) else {}
        mapped = {
            "email": properties.get("email", ""),
            "first_name": properties.get("firstname", ""),
            "last_name": properties.get("lastname", ""),
            "company": properties.get("company", ""),
            "phone": properties.get("phone", ""),
            "lifecycle_stage": properties.get("lifecyclestage", payload.lifecycle_stage),
            "source": payload.source,
        }
        result = await run_in_threadpool(helper_upsert_contact_from_vendor, auth.tenant_id, mapped)
        if result == "created":
            created += 1
        elif result == "updated":
            updated += 1
        else:
            skipped += 1
    helper_audit(
        runtime, auth.tenant_id, "crm_hubspot_contacts_synced", f"created={created},updated={updated},skipped={skipped}"
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "provider": "hubspot",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "fetched": len(rows),
    }


def execute_list_contacts(
    runtime: ContextRuntime,
    auth: AuthDep,
    q: Annotated[str | None, Query(max_length=160)] = None,
    lifecycle_stage: Annotated[str | None, Query(max_length=40)] = None,
    min_lead_score: Annotated[int, Query(ge=0, le=100)] = 0,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:contacts:list", 240, 60)
    query_text = (q or "").strip().lower()
    stage_filter = (lifecycle_stage or "").strip().lower()
    with get_db_session() as session:
        query = session.query(Contact).filter(Contact.tenant_id == auth.tenant_id)
        if stage_filter:
            query = query.filter(Contact.lifecycle_stage == stage_filter)
        if min_lead_score > 0:
            query = query.filter(Contact.score >= min_lead_score)
        if query_text:
            like_query = f"%{query_text}%"
            query = query.filter(
                or_(
                    Contact.email.ilike(like_query),
                    Contact.first_name.ilike(like_query),
                    Contact.last_name.ilike(like_query),
                    Contact.company.ilike(like_query),
                )
            )
        total = query.count()
        contacts = query.order_by(Contact.created_at.desc()).offset(offset).limit(limit).all()
        window = [helper_contact_to_dict(contact) for contact in contacts]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(window),
        "total": total,
        "limit": limit,
        "offset": offset,
        "contacts": window,
    }


def execute_dedupe_contacts(runtime: ContextRuntime, payload: ContactDedupeRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:contacts:dedupe", 30, 60)
    return helper_dedupe_contacts_impl(runtime, payload, auth)


def execute_get_contact(runtime: ContextRuntime, contact_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:contacts:get", 300, 60)
    with get_db_session() as session:
        item = session.query(Contact).filter_by(id=contact_id, tenant_id=auth.tenant_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail=CONTACT_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "contact": helper_contact_to_dict(item)}


def execute_score_contact(
    runtime: ContextRuntime, contact_id: int, payload: ContactScoreRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:contacts:score", 120, 60)
    with get_db_session() as session:
        item = session.query(Contact).filter_by(id=contact_id, tenant_id=auth.tenant_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail=CONTACT_NOT_FOUND)
        data = dict(item.data or {})
        data["score_reason"] = payload.reason
        item.score = payload.score
        item.data = data
        session.flush()
        snapshot = helper_contact_to_dict(item)
    helper_audit(runtime, auth.tenant_id, "crm_contact_scored", contact_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "contact": snapshot}


def execute_create_company(runtime: ContextRuntime, payload: CompanyCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:companies:create", 120, 60)
    with get_db_session() as session:
        company = Company(
            tenant_id=auth.tenant_id,
            name=payload.name,
            domain=payload.domain,
            industry=payload.industry,
            employee_count=payload.employee_count,
            annual_revenue=payload.annual_revenue,
            data={"account_health": "green", "properties": payload.properties, "source": "api"},
        )
        session.add(company)
        session.flush()
        snapshot = helper_company_to_dict(company)
    helper_audit(runtime, auth.tenant_id, "crm_company_created", int(snapshot["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "company": snapshot}


def execute_list_companies(
    runtime: ContextRuntime,
    auth: AuthDep,
    q: Annotated[str | None, Query(max_length=160)] = None,
    industry: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:companies:list", 240, 60)
    query_text = (q or "").strip().lower()
    industry_filter = (industry or "").strip().lower()
    with get_db_session() as session:
        query = session.query(Company).filter(Company.tenant_id == auth.tenant_id)
        if industry_filter:
            query = query.filter(Company.industry.ilike(industry_filter))
        if query_text:
            like_query = f"%{query_text}%"
            query = query.filter(or_(Company.name.ilike(like_query), Company.domain.ilike(like_query)))
        total = query.count()
        companies = query.order_by(Company.created_at.desc()).offset(offset).limit(limit).all()
        window = [helper_company_to_dict(company) for company in companies]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(window),
        "total": total,
        "limit": limit,
        "offset": offset,
        "companies": window,
    }


def execute_create_deal(runtime: ContextRuntime, payload: DealCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:deals:create", 120, 60)
    probability = next((s["probability"] for s in PIPELINE_STAGES if s["stage"] == payload.stage), 10)
    with get_db_session() as session:
        deal = Deal(
            tenant_id=auth.tenant_id,
            title=payload.title,
            value=payload.value,
            currency=payload.currency,
            stage=payload.stage,
            contact_id=payload.contact_id,
            company_id=payload.company_id,
            close_date=payload.close_date,
            data={"probability": probability, "properties": payload.properties, "source": "api"},
        )
        session.add(deal)
        session.flush()
        snapshot = helper_deal_to_dict(deal)
    helper_audit(runtime, auth.tenant_id, "crm_deal_created", int(snapshot["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "deal": snapshot}
