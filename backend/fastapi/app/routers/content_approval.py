# pyright: reportUnusedFunction=false
"""
Content Approval Workflows — Hootsuite Blueprint §4.5
Multi-level approval chain before social post publishing.
Approval requests reference scheduled post IDs from /social/schedule.

Requests, comments and chain configuration are stored in tenant-scoped
PostgreSQL tables under forced row-level security, so they survive restarts
and are shared by every worker. Sign-off authority comes from the verified
JWT ``roles`` claim: a caller may only record a decision for a level they hold
(``admin``/``super_admin`` may act for any level), and only an admin may change
the tenant's approval chain.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..authz import has_any_role
from ..database import organization_scoped_session
from ..deps import AuthContext, require_auth
from ..models import ContentApprovalComment, ContentApprovalConfig, ContentApprovalRequest, Tenant

AuthDep = Annotated[AuthContext, Depends(require_auth)]
SessionScope = Callable[[str], AbstractContextManager[Session]]

APPROVAL_REQUEST_NOT_FOUND = 'Approval request not found.'
APPROVAL_CONFIG_NOT_FOUND = 'Approval configuration not found for this tenant.'
DEFAULT_LEVELS = ['manager']
DEFAULT_EXPIRY_HOURS = 48

# Approval states
APPROVAL_STATES = {'pending', 'approved', 'rejected', 'expired'}

_APPROVAL_TABLES = (
    Tenant.__table__,
    ContentApprovalConfig.__table__,
    ContentApprovalRequest.__table__,
    ContentApprovalComment.__table__,
)
_sqlite_schema_lock = threading.Lock()
_sqlite_schema_ready: set[int] = set()

# ── Request models ─────────────────────────────────────────────────────────────

class ApprovalConfigRequest(BaseModel):
    """Configure per-tenant approval chain (up to 5 approver levels)."""
    levels: list[str] = Field(
        min_length=1,
        max_length=5,
        description='Ordered list of approver role names (e.g. ["editor", "legal", "ceo"]).',
    )
    require_all_levels: bool = Field(
        default=True,
        description='If True, all levels must approve. If False, any one level approval suffices.',
    )
    expiry_hours: int = Field(
        default=DEFAULT_EXPIRY_HOURS,
        ge=1,
        le=720,
        description='Hours before a pending approval request expires.',
    )


class ApprovalSubmitRequest(BaseModel):
    """Submit a scheduled post (by its ID) for approval before publishing."""
    scheduled_post_id: int = Field(ge=1, description='ID of the scheduled post from /social/schedule.')
    platform: str = Field(min_length=1, max_length=40, description='Target platform (linkedin, x, etc.).')
    content_preview: str = Field(min_length=1, max_length=500, description='Short preview of the post content.')
    campaign_tag: str | None = Field(default=None, max_length=80, description='Optional campaign tag.')
    requested_by: str = Field(min_length=1, max_length=120, description='Name or handle of the submitter.')
    due_at: str | None = Field(
        default=None,
        max_length=40,
        description='ISO datetime for review deadline (optional).',
    )


class ApprovalDecisionRequest(BaseModel):
    """Approve or reject a pending approval request with optional inline comment."""
    decision: Literal['approved', 'rejected']
    reviewer_role: str = Field(min_length=1, max_length=80, description='Approval level being signed off; the caller must hold this role.')
    comment: str | None = Field(default=None, max_length=1000, description='Inline reviewer comment for creator feedback.')


# ── Persistence helpers ────────────────────────────────────────────────────────

def _normalize_levels(levels: list[str]) -> list[str]:
    seen: list[str] = []
    for level in levels:
        value = level.strip().lower()
        if value and value not in seen:
            seen.append(value)
    return seen


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _config_dict(row: ContentApprovalConfig) -> dict[str, Any]:
    return {
        'id': row.id,
        'tenant_id': row.tenant_id,
        'levels': list(row.levels or []),
        'require_all_levels': row.require_all_levels,
        'expiry_hours': row.expiry_hours,
        'created_at': _iso(row.created_at),
        'updated_at': _iso(row.updated_at),
    }


def _request_dict(row: ContentApprovalRequest) -> dict[str, Any]:
    return {
        'id': row.id,
        'tenant_id': row.tenant_id,
        'scheduled_post_id': row.scheduled_post_id,
        'platform': row.platform,
        'content_preview': row.content_preview,
        'campaign_tag': row.campaign_tag,
        'requested_by': row.requested_by,
        'status': row.status,
        'approval_levels': list(row.approval_levels or []),
        'approvals_received': list(row.approvals_received or []),
        'require_all_levels': row.require_all_levels,
        'due_at': row.due_at,
        'expires_at': _iso(row.expires_at),
        'approved_at': _iso(row.approved_at),
        'rejection_reason': row.rejection_reason,
        'rejected_by': row.rejected_by,
        'created_at': _iso(row.created_at),
        'updated_at': _iso(row.updated_at),
    }


def _comment_dict(row: ContentApprovalComment) -> dict[str, Any]:
    return {
        'id': row.id,
        'tenant_id': row.tenant_id,
        'request_id': row.request_id,
        'reviewer_role': row.reviewer_role,
        'decision': row.decision,
        'comment': row.comment,
        'created_at': _iso(row.created_at),
    }


def _expire_if_due(row: ContentApprovalRequest, now: datetime) -> None:
    if row.status == 'pending' and _aware(row.expires_at) <= now:
        row.status = 'expired'
        row.updated_at = now


def _ensure_sqlite_schema(session: Session) -> None:
    """Create the approval tables on SQLite dev/test engines.

    Mirrors ``database.init_db``: SQLite gets ``create_all``; PostgreSQL schema
    comes only from Alembic (revision 3b5d7f9a1c24).
    """
    bind = session.get_bind()
    if bind.dialect.name != 'sqlite':
        return
    key = id(bind)
    if key in _sqlite_schema_ready:
        return
    with _sqlite_schema_lock:
        if key not in _sqlite_schema_ready:
            ContentApprovalRequest.metadata.create_all(bind, tables=list(_APPROVAL_TABLES))
            _sqlite_schema_ready.add(key)


def count_approval_requests(tenant_id: str, session_scope: SessionScope = organization_scoped_session) -> int:
    """Number of approval requests stored for ``tenant_id``."""
    with session_scope(tenant_id) as session:
        _ensure_sqlite_schema(session)
        return int(
            session.scalar(
                select(func.count()).select_from(ContentApprovalRequest).where(
                    ContentApprovalRequest.tenant_id == tenant_id
                )
            )
            or 0
        )


# ── Router factory ─────────────────────────────────────────────────────────────

def create_content_approval_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    session_scope: SessionScope = organization_scoped_session,
) -> APIRouter:
    """Create the content approval router."""
    router = APIRouter()
    _audit_lock = threading.Lock()

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _audit_lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'content-approval-router',
            })

    @contextmanager
    def _session(tenant_id: str) -> Iterator[Session]:
        with session_scope(tenant_id) as session:
            _ensure_sqlite_schema(session)
            yield session

    def _get_config(session: Session, tenant_id: str) -> ContentApprovalConfig | None:
        return session.scalar(select(ContentApprovalConfig).where(ContentApprovalConfig.tenant_id == tenant_id))

    def _get_request(session: Session, tenant_id: str, request_id: int) -> ContentApprovalRequest | None:
        return session.scalar(
            select(ContentApprovalRequest).where(
                ContentApprovalRequest.tenant_id == tenant_id,
                ContentApprovalRequest.id == request_id,
            )
        )

    # ── Routes ─────────────────────────────────────────────────────────────────

    @router.put('/content/approval/config', responses={403: {'description': 'Only an admin can change the approval chain.'}})
    def configure_approval_chain(payload: ApprovalConfigRequest, auth: AuthDep) -> dict[str, Any]:
        """Configure the approval chain for the authenticated tenant (admins only)."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:config', 30, 60)
        # Otherwise any member could redefine the chain as a role they already
        # hold and then sign off their own content.
        if not has_any_role(auth, 'admin'):
            raise HTTPException(status_code=403, detail='Only an admin can change the approval chain.')
        levels = _normalize_levels(payload.levels)
        if not levels:
            raise HTTPException(status_code=422, detail='At least one non-empty approval level is required.')

        with _session(auth.tenant_id) as session:
            row = _get_config(session, auth.tenant_id)
            if row is None:
                row = ContentApprovalConfig(tenant_id=auth.tenant_id)
                session.add(row)
            row.levels = levels
            row.require_all_levels = payload.require_all_levels
            row.expiry_hours = payload.expiry_hours
            row.updated_at = datetime.now(UTC)
            session.flush()
            config = _config_dict(row)

        _audit(auth.tenant_id, 'approval_config_updated')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'config': config}

    @router.get('/content/approval/config')
    def get_approval_config(auth: AuthDep) -> dict[str, Any]:
        """Retrieve approval chain configuration for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:config:get', 120, 60)
        with _session(auth.tenant_id) as session:
            row = _get_config(session, auth.tenant_id)
            config = _config_dict(row) if row is not None else None
        if config is None:
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'config': None,
                'message': 'No approval chain configured. Use PUT /content/approval/config to configure.',
            }
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'config': config}

    @router.post('/content/approval/requests', responses={400: {'description': 'Post already has a pending approval.'}})
    def submit_for_approval(payload: ApprovalSubmitRequest, auth: AuthDep) -> dict[str, Any]:
        """Submit a scheduled post for approval before publishing."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:submit', 60, 60)
        duplicate_detail = (
            f'A pending approval request already exists for scheduled post {payload.scheduled_post_id}.'
        )
        now = datetime.now(UTC)
        try:
            with _session(auth.tenant_id) as session:
                pending = session.scalars(
                    select(ContentApprovalRequest).where(
                        ContentApprovalRequest.tenant_id == auth.tenant_id,
                        ContentApprovalRequest.scheduled_post_id == payload.scheduled_post_id,
                        ContentApprovalRequest.status == 'pending',
                    )
                ).all()
                for existing in pending:
                    _expire_if_due(existing, now)
                if any(existing.status == 'pending' for existing in pending):
                    raise HTTPException(status_code=400, detail=duplicate_detail)
                session.flush()

                config = _get_config(session, auth.tenant_id)
                levels = list(config.levels) if config else list(DEFAULT_LEVELS)
                expiry_hours = config.expiry_hours if config else DEFAULT_EXPIRY_HOURS
                row = ContentApprovalRequest(
                    tenant_id=auth.tenant_id,
                    scheduled_post_id=payload.scheduled_post_id,
                    platform=payload.platform.strip(),
                    content_preview=payload.content_preview,
                    campaign_tag=payload.campaign_tag,
                    requested_by=payload.requested_by.strip(),
                    requested_by_subject=auth.subject,
                    status='pending',
                    approval_levels=levels,
                    approvals_received=[],
                    require_all_levels=config.require_all_levels if config else True,
                    due_at=payload.due_at,
                    expires_at=now + timedelta(hours=expiry_hours),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
                created = _request_dict(row)
        except IntegrityError as exc:
            # Lost a race with a concurrent submit for the same post.
            raise HTTPException(status_code=400, detail=duplicate_detail) from exc

        _audit(auth.tenant_id, 'approval_request_submitted', created['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'request': created}

    @router.get('/content/approval/requests')
    def list_approval_requests(
        auth: AuthDep,
        approval_status: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List approval requests for this tenant, optionally filtered by status."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:list', 180, 60)
        status_filter = approval_status.strip().lower() if approval_status else None
        now = datetime.now(UTC)
        with _session(auth.tenant_id) as session:
            due = session.scalars(
                select(ContentApprovalRequest).where(
                    ContentApprovalRequest.tenant_id == auth.tenant_id,
                    ContentApprovalRequest.status == 'pending',
                    ContentApprovalRequest.expires_at <= now,
                )
            ).all()
            for row in due:
                _expire_if_due(row, now)
            session.flush()

            conditions = [ContentApprovalRequest.tenant_id == auth.tenant_id]
            if status_filter is not None:
                conditions.append(ContentApprovalRequest.status == status_filter)
            total = int(
                session.scalar(select(func.count()).select_from(ContentApprovalRequest).where(*conditions)) or 0
            )
            rows = session.scalars(
                select(ContentApprovalRequest)
                .where(*conditions)
                .order_by(ContentApprovalRequest.created_at.desc(), ContentApprovalRequest.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            items = [_request_dict(row) for row in rows]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': total,
            'requests': items,
            'limit': limit,
            'offset': offset,
        }

    @router.post(
        '/content/approval/requests/{request_id}/decision',
        responses={
            404: {'description': APPROVAL_REQUEST_NOT_FOUND},
            400: {'description': 'Request is not in pending state.'},
            403: {'description': 'Caller does not hold the reviewer role.'},
            422: {'description': 'reviewer_role does not match any configured approval level.'},
        },
    )
    def decide_approval(request_id: int, payload: ApprovalDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        """
        Approve or reject a pending approval request.
        - The caller must hold ``reviewer_role`` on their verified token.
        - Rejection immediately marks the request as rejected.
        - Approval records the level; with require_all_levels the request is
          approved once every level has signed off.
        """
        enforce_rate_limit(f'{auth.tenant_id}:approval:decide', 120, 60)
        role = payload.reviewer_role.strip().lower()
        now = datetime.now(UTC)
        with _session(auth.tenant_id) as session:
            row = _get_request(session, auth.tenant_id, request_id)
            if row is None:
                raise HTTPException(status_code=404, detail=APPROVAL_REQUEST_NOT_FOUND)
            _expire_if_due(row, now)
            if row.status != 'pending':
                raise HTTPException(status_code=400, detail=f"Request is already in '{row.status}' state.")

            levels = [str(level).lower() for level in row.approval_levels or []]
            if role not in levels:
                raise HTTPException(
                    status_code=422,
                    detail=f"reviewer_role '{payload.reviewer_role}' is not a configured approval level.",
                )
            if not has_any_role(auth, role):
                raise HTTPException(
                    status_code=403,
                    detail=f"You do not hold the '{role}' role required to sign off this level.",
                )

            if payload.comment:
                session.add(
                    ContentApprovalComment(
                        tenant_id=auth.tenant_id,
                        request_id=row.id,
                        reviewer_role=role,
                        reviewer_subject=auth.subject,
                        decision=payload.decision,
                        comment=payload.comment,
                        created_at=now,
                        updated_at=now,
                    )
                )

            if payload.decision == 'rejected':
                row.status = 'rejected'
                row.rejection_reason = payload.comment or '(no reason given)'
                row.rejected_by = role
            else:
                approvals = [str(level).lower() for level in row.approvals_received or []]
                if role not in approvals:
                    approvals.append(role)
                row.approvals_received = approvals
                if not row.require_all_levels or all(level in approvals for level in levels):
                    row.status = 'approved'
                    row.approved_at = now
            row.updated_at = now
            session.flush()
            updated = _request_dict(row)

        _audit(auth.tenant_id, f'approval_request_{payload.decision}', request_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'request': updated,
            'decision': payload.decision,
        }

    @router.get(
        '/content/approval/requests/{request_id}/comments',
        responses={404: {'description': APPROVAL_REQUEST_NOT_FOUND}},
    )
    def list_approval_comments(request_id: int, auth: AuthDep) -> dict[str, Any]:
        """Retrieve all inline reviewer comments for an approval request."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:comments:list', 180, 60)
        with _session(auth.tenant_id) as session:
            if _get_request(session, auth.tenant_id, request_id) is None:
                raise HTTPException(status_code=404, detail=APPROVAL_REQUEST_NOT_FOUND)
            rows = session.scalars(
                select(ContentApprovalComment)
                .where(
                    ContentApprovalComment.tenant_id == auth.tenant_id,
                    ContentApprovalComment.request_id == request_id,
                )
                .order_by(ContentApprovalComment.id)
            ).all()
            comments = [_comment_dict(row) for row in rows]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'request_id': request_id,
            'count': len(comments),
            'comments': comments,
        }

    return router
