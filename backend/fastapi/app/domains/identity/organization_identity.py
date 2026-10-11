"""Resolve external identity-provider organizations to internal tenants."""

from __future__ import annotations


import os
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import text

from ...database import get_db_session_sync


@dataclass(frozen=True, slots=True)
class ResolvedOrganization:
    external_organization_id: str
    tenant_id: str


def mapping_required() -> bool:
    return os.getenv("ORG_IDENTITY_MAPPING_REQUIRED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def resolve_external_organization(external_organization_id: str) -> ResolvedOrganization:
    """Resolve a verified external organization claim to a tenant profile.

    The compatibility mode is intentionally explicit. It allows existing local
    deployments to roll out the migration before enabling strict mapping, while
    production can set ``ORG_IDENTITY_MAPPING_REQUIRED=true`` to reject unknown
    or unmigrated organizations.
    """
    external_id = external_organization_id.strip()
    if not external_id:
        raise HTTPException(status_code=401, detail="Organization identity is required.")

    session = None
    try:
        session = get_db_session_sync()
        row = (
            session.execute(
                text(
                    """
                SELECT external_organization_id, tenant_id, status
                FROM organization_identity_mappings
                WHERE external_organization_id = :external_id
                """
                ),
                {"external_id": external_id},
            )
            .mappings()
            .first()
        )
    except Exception as exc:
        if mapping_required():
            raise HTTPException(status_code=503, detail="Organization identity service unavailable.") from exc
        return ResolvedOrganization(external_organization_id=external_id, tenant_id=external_id)
    finally:
        if session is not None:
            session.close()
    if row is None:
        if mapping_required():
            raise HTTPException(status_code=403, detail="Organization is not provisioned.")
        return ResolvedOrganization(external_organization_id=external_id, tenant_id=external_id)
    if row["status"] != "active":
        raise HTTPException(status_code=403, detail="Organization is suspended.")
    return ResolvedOrganization(
        external_organization_id=str(row["external_organization_id"]),
        tenant_id=str(row["tenant_id"]),
    )
