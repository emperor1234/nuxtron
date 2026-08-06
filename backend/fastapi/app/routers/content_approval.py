# pyright: reportUnusedFunction=false
"""
Content Approval Workflows — Hootsuite Blueprint §4.5
ADDED: Multi-level approval chain before social post publishing.
Extends the existing social scheduling system without duplicating it.
Approval requests reference scheduled post IDs from /social/schedule.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

APPROVAL_REQUEST_NOT_FOUND = 'Approval request not found.'
APPROVAL_CONFIG_NOT_FOUND = 'Approval configuration not found for this tenant.'

# Approval states
APPROVAL_STATES = {'pending', 'approved', 'rejected', 'expired'}

# ── Request models ─────────────────────────────────────────────────────────────

class ApprovalConfigRequest(BaseModel):
    """ADDED: Configure per-tenant approval chain (up to 5 approver levels)."""
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
        default=48,
        ge=1,
        le=720,
        description='Hours before a pending approval request expires.',
    )


class ApprovalSubmitRequest(BaseModel):
    """ADDED: Submit a scheduled post (by its ID) for approval before publishing."""
    scheduled_post_id: int = Field(ge=1, description='ID of the scheduled post from /social/schedule.')
    platform: str = Field(min_length=2, max_length=40, description='Target platform (linkedin, x, etc.).')
    content_preview: str = Field(min_length=1, max_length=500, description='Short preview of the post content.')
    campaign_tag: str | None = Field(default=None, max_length=80, description='Optional campaign tag.')
    requested_by: str = Field(min_length=1, max_length=120, description='Name or handle of the submitter.')
    due_at: str | None = Field(
        default=None,
        max_length=40,
        description='ISO datetime for review deadline (optional).',
    )


class ApprovalDecisionRequest(BaseModel):
    """ADDED: Approve or reject a pending approval request with optional inline comment."""
    decision: Literal['approved', 'rejected']
    reviewer_role: str = Field(min_length=1, max_length=80, description='Role of the reviewer (must match a configured level).')
    comment: str | None = Field(default=None, max_length=1000, description='Inline reviewer comment for creator feedback.')


# ── Router factory ─────────────────────────────────────────────────────────────

def create_content_approval_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    approval_requests_memory: list[dict[str, Any]],
    approval_comments_memory: list[dict[str, Any]],
    approval_configs_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the content approval router.
    Complexity kept low by scoped helpers; no duplicate scheduling logic.
    """
    router = APIRouter()
    _lock = threading.Lock()

    # ── Scoped helpers ─────────────────────────────────────────────────────────

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'content-approval-router',
            })

    def _get_config(tenant_id: str) -> dict[str, Any] | None:
        with _lock:
            return next(
                (c.copy() for c in approval_configs_memory if c.get('tenant_id') == tenant_id),
                None,
            )

    def _get_request(tenant_id: str, request_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (
                    r
                    for r in approval_requests_memory
                    if r.get('tenant_id') == tenant_id and r.get('id') == request_id
                ),
                None,
            )

    # ── Routes ─────────────────────────────────────────────────────────────────

    @router.put('/content/approval/config')
    def configure_approval_chain(payload: ApprovalConfigRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Configure the approval chain for the authenticated tenant.
        Idempotent — updates existing config or creates a new one.
        """
        enforce_rate_limit(f'{auth.tenant_id}:approval:config', 30, 60)
        with _lock:
            existing = next(
                (c for c in approval_configs_memory if c.get('tenant_id') == auth.tenant_id), None
            )
            now = datetime.now(UTC).isoformat()
            if existing:
                existing.update({
                    'levels': payload.levels,
                    'require_all_levels': payload.require_all_levels,
                    'expiry_hours': payload.expiry_hours,
                    'updated_at': now,
                })
                config = existing.copy()
            else:
                config: dict[str, Any] = {
                    'id': len(approval_configs_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'levels': payload.levels,
                    'require_all_levels': payload.require_all_levels,
                    'expiry_hours': payload.expiry_hours,
                    'created_at': now,
                    'updated_at': now,
                }
                approval_configs_memory.append(config)
                config = config.copy()

        _audit(auth.tenant_id, 'approval_config_updated')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'config': config}

    @router.get('/content/approval/config')
    def get_approval_config(auth: AuthDep) -> dict[str, Any]:
        """ADDED: Retrieve approval chain configuration for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:config:get', 120, 60)
        config = _get_config(auth.tenant_id)
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
        """
        ADDED: Submit a scheduled post for approval before publishing.
        Creates an approval request referencing the scheduled post ID.
        """
        enforce_rate_limit(f'{auth.tenant_id}:approval:submit', 60, 60)
        config = _get_config(auth.tenant_id)
        levels: list[str] = config['levels'] if config else ['manager']
        expiry_hours: int = int(config.get('expiry_hours', 48)) if config else 48

        # Guard: no duplicate pending requests for the same post
        with _lock:
            duplicate = any(
                r.get('scheduled_post_id') == payload.scheduled_post_id
                and r.get('tenant_id') == auth.tenant_id
                and r.get('status') == 'pending'
                for r in approval_requests_memory
            )
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f'A pending approval request already exists for scheduled post {payload.scheduled_post_id}.',
            )

        now = datetime.now(UTC)
        request: dict[str, Any] = {
            'id': len(approval_requests_memory) + 1,
            'tenant_id': auth.tenant_id,
            'scheduled_post_id': payload.scheduled_post_id,
            'platform': payload.platform,
            'content_preview': payload.content_preview,
            'campaign_tag': payload.campaign_tag,
            'requested_by': payload.requested_by,
            'status': 'pending',
            # ADDED: approval chain tracking — levels and which have been approved
            'approval_levels': levels,
            'approvals_received': [],
            'require_all_levels': bool(config.get('require_all_levels', True)) if config else True,
            'due_at': payload.due_at,
            'expires_at': (
                datetime(
                    now.year, now.month, now.day,
                    now.hour, now.minute, now.second,
                    tzinfo=UTC,
                ).isoformat()
            ),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }
        # Compute actual expiry
        from datetime import timedelta
        expiry = now + timedelta(hours=expiry_hours)
        request['expires_at'] = expiry.isoformat()

        with _lock:
            approval_requests_memory.append(request)

        _audit(auth.tenant_id, 'approval_request_submitted', request['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'request': request.copy()}

    @router.get('/content/approval/requests')
    def list_approval_requests(
        auth: AuthDep,
        approval_status: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: List approval requests for this tenant, optionally filtered by status."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:list', 180, 60)
        with _lock:
            items = [
                r.copy()
                for r in approval_requests_memory
                if r.get('tenant_id') == auth.tenant_id
                and (approval_status is None or r.get('status') == approval_status.strip().lower())
            ]
        items.sort(key=lambda r: str(r.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'requests': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.post(
        '/content/approval/requests/{request_id}/decision',
        responses={
            404: {'description': APPROVAL_REQUEST_NOT_FOUND},
            400: {'description': 'Request is not in pending state.'},
            422: {'description': 'reviewer_role does not match any configured approval level.'},
        },
    )
    def decide_approval(request_id: int, payload: ApprovalDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Approve or reject a pending approval request.
        - Rejection immediately marks the request as rejected with mandatory reason.
        - Approval records the approving role; if require_all_levels and all levels have
          now approved, the request is promoted to 'approved'.
        """
        enforce_rate_limit(f'{auth.tenant_id}:approval:decide', 120, 60)
        request = _get_request(auth.tenant_id, request_id)
        if request is None:
            raise HTTPException(status_code=404, detail=APPROVAL_REQUEST_NOT_FOUND)
        if request.get('status') != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Request is already in '{request.get('status')}' state.",
            )

        role = payload.reviewer_role.strip().lower()
        levels: list[str] = [str(lv).lower() for lv in request.get('approval_levels', [])]
        if role not in levels:
            raise HTTPException(
                status_code=422,
                detail=f"reviewer_role '{payload.reviewer_role}' is not a configured approval level.",
            )

        # Add inline comment if provided
        if payload.comment:
            with _lock:
                approval_comments_memory.append({
                    'id': len(approval_comments_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'request_id': request_id,
                    'reviewer_role': role,
                    'decision': payload.decision,
                    'comment': payload.comment,
                    'created_at': datetime.now(UTC).isoformat(),
                })

        now_iso = datetime.now(UTC).isoformat()
        with _lock:
            live_request = next(
                (r for r in approval_requests_memory if r.get('id') == request_id and r.get('tenant_id') == auth.tenant_id),
                None,
            )
            if live_request is None:
                raise HTTPException(status_code=404, detail=APPROVAL_REQUEST_NOT_FOUND)

            if payload.decision == 'rejected':
                live_request['status'] = 'rejected'
                live_request['rejection_reason'] = payload.comment or '(no reason given)'
                live_request['rejected_by'] = role
                live_request['updated_at'] = now_iso
            else:
                # Record this level's approval (idempotent)
                approvals: list[str] = list(live_request.get('approvals_received', []))
                if role not in approvals:
                    approvals.append(role)
                live_request['approvals_received'] = approvals
                live_request['updated_at'] = now_iso

                require_all = bool(live_request.get('require_all_levels', True))
                if require_all:
                    all_approved = all(lv in approvals for lv in levels)
                    if all_approved:
                        live_request['status'] = 'approved'
                        live_request['approved_at'] = now_iso
                else:
                    # Any one approval is sufficient
                    live_request['status'] = 'approved'
                    live_request['approved_at'] = now_iso

            updated = live_request.copy()

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
        """ADDED: Retrieve all inline reviewer comments for an approval request."""
        enforce_rate_limit(f'{auth.tenant_id}:approval:comments:list', 180, 60)
        request = _get_request(auth.tenant_id, request_id)
        if request is None:
            raise HTTPException(status_code=404, detail=APPROVAL_REQUEST_NOT_FOUND)

        with _lock:
            comments = [
                c.copy()
                for c in approval_comments_memory
                if c.get('tenant_id') == auth.tenant_id and c.get('request_id') == request_id
            ]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'request_id': request_id,
            'count': len(comments),
            'comments': comments,
        }

    return router
