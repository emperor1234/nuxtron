# pyright: reportUnusedFunction=false
"""
Employee Advocacy (Hootsuite Amplify equivalent) — Hootsuite Blueprint §9
ADDED: Brand ambassador content sharing, gamification, and advocacy analytics.
Employees register as advocates, share brand-approved content, and earn points.
No duplication: this is separate from the general social scheduling system.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

CONTENT_NOT_FOUND = 'Advocacy content item not found.'
PARTICIPANT_NOT_FOUND = 'Advocate not registered for this tenant.'
CAMPAIGN_NOT_FOUND = 'Advocacy campaign not found.'

# Estimated earned media value: $0.015 per social impression (industry benchmark)
EARNED_MEDIA_VALUE_PER_IMPRESSION = 0.015

# ── Request models ──────────────────────────────────────────────────────────────

class AdvocacyCampaignRequest(BaseModel):
    """ADDED: Create a named advocacy campaign for organising shareable content."""
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    starts_at: str | None = Field(default=None, max_length=40, description='ISO datetime.')
    ends_at: str | None = Field(default=None, max_length=40, description='ISO datetime (optional).')


class AdvocacyContentRequest(BaseModel):
    """ADDED: Add brand-approved content to the advocacy content hub."""
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=2200, description='Pre-approved shareable post body.')
    platform: str = Field(min_length=2, max_length=40, description='Target platform (linkedin, x, instagram, etc.).')
    media_url: str | None = Field(default=None, max_length=2048)
    campaign_id: int | None = Field(default=None, description='Assign to an advocacy campaign.')
    expires_at: str | None = Field(default=None, max_length=40, description='Auto-expire date for time-sensitive content.')
    # ADDED: targeting metadata (mirrors Hootsuite Amplify segment targeting)
    target_departments: list[str] = Field(default_factory=list, max_length=20)
    target_regions: list[str] = Field(default_factory=list, max_length=20)


class ParticipantRegisterRequest(BaseModel):
    """ADDED: Register an employee as an advocate."""
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=5, max_length=254)
    department: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    # Social following is used to compute estimated reach
    linkedin_followers: int = Field(default=0, ge=0, le=10_000_000)
    x_followers: int = Field(default=0, ge=0, le=10_000_000)
    instagram_followers: int = Field(default=0, ge=0, le=10_000_000)


class AdvocacyShareRequest(BaseModel):
    """ADDED: Record an employee share event for a content item."""
    content_id: int = Field(ge=1)
    platform: str = Field(min_length=2, max_length=40)
    # Estimated reach and engagement reported by the employee or integration
    estimated_reach: int = Field(default=0, ge=0, le=50_000_000)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    # ADDED: optional personalised commentary the employee added
    custom_commentary: str | None = Field(default=None, max_length=500)


# ── Router factory ──────────────────────────────────────────────────────────────

def create_employee_advocacy_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    advocacy_content_memory: list[dict[str, Any]],
    advocacy_shares_memory: list[dict[str, Any]],
    advocacy_participants_memory: list[dict[str, Any]],
    advocacy_campaigns_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the employee advocacy (Amplify) router.
    All data is tenant-scoped. No duplication of general social scheduling logic.
    """
    router = APIRouter()
    _lock = threading.Lock()

    # ── Scoped helpers ──────────────────────────────────────────────────────────

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'employee-advocacy-router',
            })

    def _get_content(tenant_id: str, content_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (c for c in advocacy_content_memory if c.get('tenant_id') == tenant_id and c.get('id') == content_id),
                None,
            )

    def _get_participant(tenant_id: str, participant_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (p for p in advocacy_participants_memory if p.get('tenant_id') == tenant_id and p.get('id') == participant_id),
                None,
            )

    # ── Campaign routes ─────────────────────────────────────────────────────────

    @router.post('/advocacy/campaigns')
    def create_campaign(payload: AdvocacyCampaignRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Create a named advocacy campaign (product launch, event, recruitment, etc.)."""
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:campaigns:create', 60, 60)
        with _lock:
            campaign: dict[str, Any] = {
                'id': len(advocacy_campaigns_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'description': payload.description,
                'starts_at': payload.starts_at,
                'ends_at': payload.ends_at,
                'content_count': 0,
                'total_shares': 0,
                'created_at': datetime.now(UTC).isoformat(),
            }
            advocacy_campaigns_memory.append(campaign)

        _audit(auth.tenant_id, 'advocacy_campaign_created', campaign['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': campaign.copy()}

    @router.get('/advocacy/campaigns')
    def list_campaigns(auth: AuthDep) -> dict[str, Any]:
        """ADDED: List advocacy campaigns for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:campaigns:list', 180, 60)
        with _lock:
            items = [c.copy() for c in advocacy_campaigns_memory if c.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'campaigns': items}

    # ── Content hub routes ──────────────────────────────────────────────────────

    @router.post(
        '/advocacy/content',
        responses={404: {'description': CAMPAIGN_NOT_FOUND}},
    )
    def add_content(payload: AdvocacyContentRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Add brand-approved content to the advocacy content hub.
        Only pre-approved content can be added here — no free-form employee posting.
        """
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:content:create', 120, 60)
        if payload.campaign_id is not None:
            with _lock:
                campaign = next(
                    (c for c in advocacy_campaigns_memory if c.get('tenant_id') == auth.tenant_id and c.get('id') == payload.campaign_id),
                    None,
                )
            if campaign is None:
                raise HTTPException(status_code=404, detail=CAMPAIGN_NOT_FOUND)

        with _lock:
            content: dict[str, Any] = {
                'id': len(advocacy_content_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title.strip(),
                'body': payload.body,
                'platform': payload.platform.strip().lower(),
                'media_url': payload.media_url,
                'campaign_id': payload.campaign_id,
                'expires_at': payload.expires_at,
                # ADDED: segment targeting for curated feeds (mirrors Hootsuite Amplify)
                'target_departments': [d.strip().lower() for d in payload.target_departments],
                'target_regions': [r.strip().lower() for r in payload.target_regions],
                'total_shares': 0,
                'total_reach': 0,
                'total_engagement': 0,
                # ADDED: status allows admins to disable/archive without deleting
                'status': 'active',
                'created_at': datetime.now(UTC).isoformat(),
            }
            advocacy_content_memory.append(content)
            # Update campaign content count
            if payload.campaign_id is not None:
                for camp in advocacy_campaigns_memory:
                    if camp.get('tenant_id') == auth.tenant_id and camp.get('id') == payload.campaign_id:
                        camp['content_count'] = int(camp.get('content_count', 0)) + 1

        _audit(auth.tenant_id, 'advocacy_content_added', content['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'content': content.copy()}

    @router.get('/advocacy/content')
    def list_content(
        auth: AuthDep,
        campaign_id: Annotated[int | None, Query(ge=1)] = None,
        platform: Annotated[str | None, Query(max_length=40)] = None,
        department: Annotated[str | None, Query(max_length=120)] = None,
        active_only: Annotated[bool, Query()] = True,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: Browse advocacy content hub with optional filters."""
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:content:list', 240, 60)
        platform_filter = platform.strip().lower() if platform else None
        dept_filter = department.strip().lower() if department else None
        now_iso = datetime.now(UTC).isoformat()

        with _lock:
            items = [
                c.copy()
                for c in advocacy_content_memory
                if c.get('tenant_id') == auth.tenant_id
                and (campaign_id is None or c.get('campaign_id') == campaign_id)
                and (platform_filter is None or c.get('platform') == platform_filter)
                and (dept_filter is None or dept_filter in [str(d) for d in c.get('target_departments', [])] or not c.get('target_departments'))
                and (not active_only or c.get('status') == 'active')
                and (c.get('expires_at') is None or str(c.get('expires_at', '')) >= now_iso)
            ]
        items.sort(key=lambda c: str(c.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'content': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    # ── Participant (advocate) routes ────────────────────────────────────────────

    @router.post('/advocacy/participants')
    def register_participant(payload: ParticipantRegisterRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Register an employee as a brand advocate."""
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:participants:register', 120, 60)
        with _lock:
            # Guard: one registration per email per tenant
            existing = next(
                (
                    p for p in advocacy_participants_memory
                    if p.get('tenant_id') == auth.tenant_id and str(p.get('email', '')).lower() == payload.email.lower()
                ),
                None,
            )
            if existing:
                return {'status': 'ok', 'tenant_id': auth.tenant_id, 'participant': existing.copy(), 'created': False}

            participant: dict[str, Any] = {
                'id': len(advocacy_participants_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'email': payload.email.strip().lower(),
                'department': payload.department,
                'region': payload.region,
                'linkedin_followers': payload.linkedin_followers,
                'x_followers': payload.x_followers,
                'instagram_followers': payload.instagram_followers,
                # ADDED: combined reach potential for earned media value calculation
                'total_following': payload.linkedin_followers + payload.x_followers + payload.instagram_followers,
                # ADDED: gamification fields
                'points': 0,
                'total_shares': 0,
                'total_reach_generated': 0,
                'created_at': datetime.now(UTC).isoformat(),
            }
            advocacy_participants_memory.append(participant)

        _audit(auth.tenant_id, 'advocacy_participant_registered', participant['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'participant': participant.copy(), 'created': True}

    @router.get('/advocacy/participants')
    def list_participants(
        auth: AuthDep,
        department: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: List registered advocates, optionally filtered by department."""
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:participants:list', 180, 60)
        dept_filter = department.strip().lower() if department else None
        with _lock:
            items = [
                p.copy()
                for p in advocacy_participants_memory
                if p.get('tenant_id') == auth.tenant_id
                and (dept_filter is None or str(p.get('department', '')).lower() == dept_filter)
            ]
        # ADDED: gamification leaderboard — sorted by total points
        items.sort(key=lambda p: int(p.get('points', 0)), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'participants': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    # ── Share event routes ───────────────────────────────────────────────────────

    @router.post(
        '/advocacy/participants/{participant_id}/share',
        responses={
            404: {'description': f'{PARTICIPANT_NOT_FOUND} / {CONTENT_NOT_FOUND}'},
        },
    )
    def record_share(participant_id: int, payload: AdvocacyShareRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Record an employee share event.
        - Updates content aggregate stats (total_shares, total_reach, total_engagement).
        - Awards gamification points to the advocate (10 pts per share, 1 pt per 100 reach).
        - Computes earned media value at $0.015 per impression.
        """
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:share', 300, 60)
        participant = _get_participant(auth.tenant_id, participant_id)
        if participant is None:
            raise HTTPException(status_code=404, detail=PARTICIPANT_NOT_FOUND)

        content = _get_content(auth.tenant_id, payload.content_id)
        if content is None:
            raise HTTPException(status_code=404, detail=CONTENT_NOT_FOUND)

        engagement = payload.likes + payload.comments + payload.clicks
        # ADDED: earned media value calculation (§9.3 in blueprint)
        emv = round(payload.estimated_reach * EARNED_MEDIA_VALUE_PER_IMPRESSION, 4)
        # ADDED: gamification points
        points_earned = 10 + (payload.estimated_reach // 100)

        with _lock:
            share: dict[str, Any] = {
                'id': len(advocacy_shares_memory) + 1,
                'tenant_id': auth.tenant_id,
                'participant_id': participant_id,
                'content_id': payload.content_id,
                'platform': payload.platform.strip().lower(),
                'estimated_reach': payload.estimated_reach,
                'likes': payload.likes,
                'comments': payload.comments,
                'clicks': payload.clicks,
                'total_engagement': engagement,
                # ADDED: earned media value for ROI reporting
                'earned_media_value': emv,
                'custom_commentary': payload.custom_commentary,
                'created_at': datetime.now(UTC).isoformat(),
            }
            advocacy_shares_memory.append(share)

            # Update content aggregate stats
            for c in advocacy_content_memory:
                if c.get('tenant_id') == auth.tenant_id and c.get('id') == payload.content_id:
                    c['total_shares'] = int(c.get('total_shares', 0)) + 1
                    c['total_reach'] = int(c.get('total_reach', 0)) + payload.estimated_reach
                    c['total_engagement'] = int(c.get('total_engagement', 0)) + engagement

            # Update participant stats + gamification points
            for p in advocacy_participants_memory:
                if p.get('tenant_id') == auth.tenant_id and p.get('id') == participant_id:
                    p['total_shares'] = int(p.get('total_shares', 0)) + 1
                    p['total_reach_generated'] = int(p.get('total_reach_generated', 0)) + payload.estimated_reach
                    p['points'] = int(p.get('points', 0)) + points_earned

            # Update campaign aggregate stats
            campaign_id = content.get('campaign_id')
            if campaign_id is not None:
                for camp in advocacy_campaigns_memory:
                    if camp.get('tenant_id') == auth.tenant_id and camp.get('id') == campaign_id:
                        camp['total_shares'] = int(camp.get('total_shares', 0)) + 1

        _audit(auth.tenant_id, 'advocacy_share_recorded', share['id'])
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'share': share,
            'points_earned': points_earned,
            'earned_media_value': emv,
        }

    # ── Analytics routes ─────────────────────────────────────────────────────────

    @router.get('/advocacy/analytics')
    def advocacy_analytics(auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Advocacy analytics dashboard — shares, reach, earned media value,
        active advocates, leaderboard, and per-campaign summary (§9.3).
        """
        enforce_rate_limit(f'{auth.tenant_id}:advocacy:analytics', 120, 60)
        with _lock:
            shares = [s for s in advocacy_shares_memory if s.get('tenant_id') == auth.tenant_id]
            participants = [p for p in advocacy_participants_memory if p.get('tenant_id') == auth.tenant_id]
            campaigns = [c for c in advocacy_campaigns_memory if c.get('tenant_id') == auth.tenant_id]

        total_shares = len(shares)
        total_reach = sum(int(s.get('estimated_reach', 0)) for s in shares)
        total_engagement = sum(int(s.get('total_engagement', 0)) for s in shares)
        total_clicks = sum(int(s.get('clicks', 0)) for s in shares)
        # ADDED: earned media value aggregate for ROI reporting
        total_emv = round(sum(float(s.get('earned_media_value', 0)) for s in shares), 4)
        active_advocates = sum(1 for p in participants if int(p.get('total_shares', 0)) > 0)

        # ADDED: per-platform breakdown of share activity
        by_platform: dict[str, int] = {}
        for share in shares:
            plat = str(share.get('platform', 'unknown'))
            by_platform[plat] = by_platform.get(plat, 0) + 1

        # ADDED: leaderboard (top 10 advocates by points)
        sorted_participants = sorted(participants, key=lambda p: int(p.get('points', 0)), reverse=True)
        leaderboard: list[dict[str, Any]] = [
            {
                'rank': i + 1,
                'participant_id': p.get('id'),
                'name': p.get('name'),
                'department': p.get('department'),
                'points': p.get('points'),
                'total_shares': p.get('total_shares'),
            }
            for i, p in enumerate(sorted_participants[:10])
        ]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': datetime.now(UTC).isoformat(),
            'totalShares': total_shares,
            'totalReach': total_reach,
            'totalEngagement': total_engagement,
            'totalClicks': total_clicks,
            # ADDED: earned media value — dollar value of employee-generated impressions
            'totalEarnedMediaValue': total_emv,
            'activeAdvocates': active_advocates,
            'totalRegisteredAdvocates': len(participants),
            'activeCampaigns': len(campaigns),
            'byPlatform': by_platform,
            'leaderboard': leaderboard,
        }

    return router
