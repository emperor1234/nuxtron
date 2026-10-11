"""Crm service: apply segment filters."""

from ....database import get_db_session
from ....models import Contact
from typing import Any


def _apply_segment_filters(
    tenant_id: str, filters: dict[str, Any], contacts_memory: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply segment filters to contacts and return matching copies."""
    if contacts_memory:
        items = [dict(c) for c in contacts_memory if str(c.get("tenant_id", "")) == str(tenant_id)]
    else:
        with get_db_session() as session:
            items = []
            contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).all()
            for contact in contacts:
                data = dict(contact.data or {})
                tags = data.get("tags", [])
                items.append(
                    {
                        "id": contact.id,
                        "tenant_id": contact.tenant_id,
                        "email": contact.email,
                        "first_name": contact.first_name,
                        "last_name": contact.last_name,
                        "company": contact.company,
                        "phone": contact.phone,
                        "lifecycle_stage": contact.lifecycle_stage,
                        "lead_score": contact.score,
                        "tags": tags if isinstance(tags, list) else [],
                        "properties": data.get("properties", {}),
                        "created_at": contact.created_at.isoformat(),
                        "updated_at": contact.updated_at.isoformat(),
                        "source": data.get("source", "api"),
                    }
                )
    if not filters:
        return items
    if "lifecycle_stage" in filters:
        items = [c for c in items if str(c.get("lifecycle_stage", "")) == str(filters["lifecycle_stage"])]
    if "min_lead_score" in filters:
        items = [c for c in items if int(c.get("lead_score", 0)) >= int(filters["min_lead_score"])]
    if "tag" in filters:
        tag = str(filters["tag"])
        items = [c for c in items if tag in [str(t) for t in c.get("tags", [])]]
    if "company" in filters:
        cq = str(filters["company"]).lower()
        items = [c for c in items if cq in str(c.get("company", "")).lower()]
    return items
