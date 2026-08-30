"""
Reference PG-backed notification store (WO-4 reference implementation).

This is the template for migrating the in-memory ``app.state.notifications``
list. The same shape applies to every store enumerated in the WO-4 inventory;
see ``app/stores/base.py`` for the contract.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..database import Base
from .base import PersistentStore

# Reuse the shared declarative base (app.database.Base) so this model
# participates in the same metadata/create_all/Alembic migrations as the rest
# of the app. This previously called declarative_base() again here, which
# created a SECOND, disconnected metadata registry — NotificationRow was
# never actually created by init_db()/create_all() as a result, silently.


class NotificationRow(Base):
    __tablename__ = 'store_notifications'

    id = Column(String(36), primary_key=True)  # uuid4 hex, supplied by caller
    # String(255) to match Tenant.tenant_id (models.py) exactly — FK columns
    # must agree in type with what they reference.
    tenant_id = Column(String(255), ForeignKey('tenant_profiles.tenant_id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NotificationStore(PersistentStore[dict[str, Any]]):
    async def _write_to_db(self, session: AsyncSession, tenant_id: str, item: dict[str, Any]) -> None:
        row = NotificationRow(
            id=item['id'],
            tenant_id=tenant_id,
            user_id=item['user_id'],
            message=item['message'],
        )
        session.add(row)

    async def _read_from_db(self, session: AsyncSession, tenant_id: str) -> list[dict[str, Any]]:
        result = await session.execute(
            select(NotificationRow)
            .where(NotificationRow.tenant_id == tenant_id)
            .order_by(NotificationRow.created_at.desc())
            .limit(200)
        )
        return [
            {
                'id': r.id,
                'user_id': r.user_id,
                'message': r.message,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]


# Module-level singleton; callers get it via this import.
notification_store = NotificationStore()
