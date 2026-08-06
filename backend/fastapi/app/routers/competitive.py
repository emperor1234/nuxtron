# pyright: reportUnusedFunction=false
"""
Competitive Benchmarking — SproutSocial Blueprint §5.4
ADDED: Competitor profile tracking and side-by-side benchmarking.
Tracks competitor social profiles and periodic metric snapshots,
then computes share-of-voice and comparison reports.
NO duplication: existing /analytics/benchmarks returns INDUSTRY averages only.
This module tracks SPECIFIC COMPETITOR PROFILES chosen by the tenant.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

PROFILE_NOT_FOUND = 'Competitor profile not found.'
VALID_NETWORKS = {'linkedin', 'x', 'instagram', 'facebook', 'tiktok', 'youtube', 'pinterest', 'reddit'}


# ── Request models ──────────────────────────────────────────────────────────────

class CompetitorProfileRequest(BaseModel):
    """ADDED: Add a competitor social profile to track (§5.4)."""
    name: str = Field(min_length=1, max_length=160, description='Brand / competitor name.')
    network: str = Field(min_length=2, max_length=40)
    handle: str = Field(min_length=1, max_length=120, description='@handle or username on the platform.')
    profile_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class MetricSnapshotRequest(BaseModel):
    """
    ADDED: Record a periodic metric snapshot for a tracked competitor.
    Capture weekly or monthly for trend analysis.
    """
    # ADDED: Growth and audience metrics
    followers: int = Field(default=0, ge=0)
    following: int = Field(default=0, ge=0)
    # ADDED: Content velocity (§5.4 Competitive benchmarking metrics)
    posts_last_30d: int = Field(default=0, ge=0, description='Number of posts published in last 30 days.')
    avg_likes_last_30d: float = Field(default=0.0, ge=0)
    avg_comments_last_30d: float = Field(default=0.0, ge=0)
    avg_shares_last_30d: float = Field(default=0.0, ge=0)
    avg_views_last_30d: float = Field(default=0.0, ge=0, description='Average video views — YouTube/TikTok only.')
    # ADDED: Engagement rate (§5.4 KPIs)
    engagement_rate: float = Field(default=0.0, ge=0.0, le=100.0, description='Percentage, e.g. 3.5 means 3.5%')
    estimated_reach: int = Field(default=0, ge=0, description='Estimated monthly reach.')
    # ADDED: Optional share of voice input
    estimated_mentions: int = Field(default=0, ge=0, description='Estimated brand mentions for SoV calculation.')
    snapshot_date: str | None = Field(default=None, max_length=40, description='ISO date for the snapshot; defaults to now.')


class OwnProfileSnapshotRequest(BaseModel):
    """ADDED: Record your own brand's metrics for comparison in the competitive report."""
    network: str = Field(min_length=2, max_length=40)
    followers: int = Field(default=0, ge=0)
    following: int = Field(default=0, ge=0)
    posts_last_30d: int = Field(default=0, ge=0)
    avg_likes_last_30d: float = Field(default=0.0, ge=0)
    avg_comments_last_30d: float = Field(default=0.0, ge=0)
    avg_shares_last_30d: float = Field(default=0.0, ge=0)
    avg_views_last_30d: float = Field(default=0.0, ge=0)
    engagement_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_reach: int = Field(default=0, ge=0)
    estimated_mentions: int = Field(default=0, ge=0)
    snapshot_date: str | None = Field(default=None, max_length=40)


# ── Share of voice helper ───────────────────────────────────────────────────────

def _share_of_voice(mentions_map: dict[str, int]) -> dict[str, float]:
    """
    ADDED: Compute Share of Voice percentages from a {name: mentions} dict (§5.4).
    Returns {name: percentage} normalised to 100%.
    """
    total = sum(mentions_map.values())
    if total == 0:
        return dict.fromkeys(mentions_map, 0.0)
    return {k: round(v / total * 100, 2) for k, v in mentions_map.items()}


# ── Router factory ──────────────────────────────────────────────────────────────

def create_competitive_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    profiles_memory: list[dict[str, Any]],
    snapshots_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the Competitive Benchmarking router (SproutSocial §5.4).
    No duplication: /analytics/benchmarks covers industry-level stats only.
    """
    router = APIRouter()
    _lock = threading.Lock()

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'competitive-router',
            })

    def _get_profile(tenant_id: str, profile_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (p for p in profiles_memory if p.get('tenant_id') == tenant_id and p.get('id') == profile_id),
                None,
            )

    # ── Competitor profile management ───────────────────────────────────────────

    @router.post('/competitive/profiles')
    def add_competitor(payload: CompetitorProfileRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Add a competitor social profile to monitor (§5.4 Competitive Monitoring)."""
        enforce_rate_limit(f'{auth.tenant_id}:competitive:profiles:add', 60, 60)
        network = payload.network.strip().lower()

        # Prevent duplicate handle+network entries per tenant
        with _lock:
            duplicate = next(
                (
                    p for p in profiles_memory
                    if p.get('tenant_id') == auth.tenant_id
                    and p.get('network') == network
                    and p.get('handle', '').lower() == payload.handle.strip().lstrip('@').lower()
                ),
                None,
            )
            if duplicate:
                return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': duplicate.copy(), 'created': False}

            profile: dict[str, Any] = {
                'id': len(profiles_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'network': network,
                'handle': payload.handle.strip().lstrip('@'),
                'profile_url': payload.profile_url,
                'industry': payload.industry,
                'notes': payload.notes,
                'snapshot_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            profiles_memory.append(profile)

        _audit(auth.tenant_id, 'competitor_profile_added', profile['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': profile.copy(), 'created': True}

    @router.get('/competitive/profiles')
    def list_competitors(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        """ADDED: List all tracked competitor profiles."""
        enforce_rate_limit(f'{auth.tenant_id}:competitive:profiles:list', 240, 60)
        network_f = network.strip().lower() if network else None
        with _lock:
            items = [
                p.copy() for p in profiles_memory
                if p.get('tenant_id') == auth.tenant_id
                and (network_f is None or p.get('network') == network_f)
            ]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'profiles': items,
        }

    @router.delete(
        '/competitive/profiles/{profile_id}',
        responses={404: {'description': PROFILE_NOT_FOUND}},
    )
    def remove_competitor(profile_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Remove a competitor from tracking (also deletes associated snapshots)."""
        enforce_rate_limit(f'{auth.tenant_id}:competitive:profiles:delete', 30, 60)
        with _lock:
            p_idx = next(
                (i for i, p in enumerate(profiles_memory) if p.get('tenant_id') == auth.tenant_id and p.get('id') == profile_id),
                None,
            )
            if p_idx is None:
                raise HTTPException(status_code=404, detail=PROFILE_NOT_FOUND)
            profiles_memory.pop(p_idx)
            # ADDED: cascade delete snapshots
            to_remove = [i for i, s in enumerate(snapshots_memory) if s.get('tenant_id') == auth.tenant_id and s.get('competitor_id') == profile_id]
            for idx in sorted(to_remove, reverse=True):
                snapshots_memory.pop(idx)

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile_id': profile_id, 'deleted': True}

    # ── Metric snapshots ────────────────────────────────────────────────────────

    @router.post(
        '/competitive/profiles/{profile_id}/snapshots',
        responses={404: {'description': PROFILE_NOT_FOUND}},
    )
    def add_snapshot(profile_id: int, payload: MetricSnapshotRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Record a competitor metric snapshot for trend tracking (§5.4).
        Typically called weekly via automated data collection or manually.
        """
        enforce_rate_limit(f'{auth.tenant_id}:competitive:snapshots:add', 120, 60)
        profile = _get_profile(auth.tenant_id, profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail=PROFILE_NOT_FOUND)

        snapshot_date = payload.snapshot_date or datetime.now(UTC).date().isoformat()
        with _lock:
            snapshot: dict[str, Any] = {
                'id': len(snapshots_memory) + 1,
                'tenant_id': auth.tenant_id,
                'competitor_id': profile_id,
                'competitor_name': profile.get('name'),
                'network': profile.get('network'),
                'snapshot_date': snapshot_date,
                'followers': payload.followers,
                'following': payload.following,
                'posts_last_30d': payload.posts_last_30d,
                'avg_likes_last_30d': payload.avg_likes_last_30d,
                'avg_comments_last_30d': payload.avg_comments_last_30d,
                'avg_shares_last_30d': payload.avg_shares_last_30d,
                'avg_views_last_30d': payload.avg_views_last_30d,
                'engagement_rate': payload.engagement_rate,
                'estimated_reach': payload.estimated_reach,
                'estimated_mentions': payload.estimated_mentions,
                'created_at': datetime.now(UTC).isoformat(),
            }
            snapshots_memory.append(snapshot)
            # Update snapshot count on profile
            for p in profiles_memory:
                if p.get('tenant_id') == auth.tenant_id and p.get('id') == profile_id:
                    p['snapshot_count'] = p.get('snapshot_count', 0) + 1
                    p['last_snapshot_date'] = snapshot_date
                    p['last_followers'] = payload.followers
                    p['last_engagement_rate'] = payload.engagement_rate
                    break

        _audit(auth.tenant_id, 'competitor_snapshot_recorded', snapshot['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'snapshot': snapshot.copy()}

    @router.post('/competitive/own-profile')
    def record_own_profile(payload: OwnProfileSnapshotRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Record your brand's own metrics for side-by-side comparison (§5.4).
        Stored as a special competitor profile with id=0 for report inclusion.
        """
        enforce_rate_limit(f'{auth.tenant_id}:competitive:own-profile', 60, 60)
        network = payload.network.strip().lower()
        snapshot_date = payload.snapshot_date or datetime.now(UTC).date().isoformat()
        with _lock:
            own_entry: dict[str, Any] = {
                'id': len(snapshots_memory) + 1,
                'tenant_id': auth.tenant_id,
                'competitor_id': 0,  # 0 = own brand
                'competitor_name': '__OWN_BRAND__',
                'network': network,
                'snapshot_date': snapshot_date,
                'followers': payload.followers,
                'following': payload.following,
                'posts_last_30d': payload.posts_last_30d,
                'avg_likes_last_30d': payload.avg_likes_last_30d,
                'avg_comments_last_30d': payload.avg_comments_last_30d,
                'avg_shares_last_30d': payload.avg_shares_last_30d,
                'avg_views_last_30d': payload.avg_views_last_30d,
                'engagement_rate': payload.engagement_rate,
                'estimated_reach': payload.estimated_reach,
                'estimated_mentions': payload.estimated_mentions,
                'created_at': datetime.now(UTC).isoformat(),
            }
            snapshots_memory.append(own_entry)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'record': own_entry.copy()}

    # ── Reports ─────────────────────────────────────────────────────────────────

    @router.get('/competitive/report')
    def comparison_report(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        """
        ADDED: Side-by-side competitive comparison report (§5.4 Competitive Reports).
        Returns each tracked competitor's latest snapshot vs. your own brand.
        """
        enforce_rate_limit(f'{auth.tenant_id}:competitive:report', 60, 60)
        network_f = network.strip().lower() if network else None

        with _lock:
            profiles = [
                p.copy() for p in profiles_memory
                if p.get('tenant_id') == auth.tenant_id
                and (network_f is None or p.get('network') == network_f)
            ]
            # Latest snapshot per competitor_id
            all_snaps = [
                s.copy() for s in snapshots_memory
                if s.get('tenant_id') == auth.tenant_id
                and (network_f is None or s.get('network') == network_f)
            ]

        # Get latest snapshot per competitor_id
        latest: dict[int, dict[str, Any]] = {}
        for snap in all_snaps:
            cid = int(snap.get('competitor_id', -1))
            if cid not in latest or str(snap.get('snapshot_date', '')) > str(latest[cid].get('snapshot_date', '')):
                latest[cid] = snap

        own_latest = latest.get(0)
        competitors_report: list[dict[str, Any]] = []
        for profile in profiles:
            pid = int(profile.get('id', -1))
            snap: dict[str, Any] | None = latest.get(pid)
            entry: dict[str, Any] = {
                'profile': profile,
                'latest_snapshot': snap,
            }
            if snap and own_latest:
                own_er = float(own_latest.get('engagement_rate', 0))
                comp_er = float(snap.get('engagement_rate', 0))
                own_followers = int(own_latest.get('followers', 0))
                comp_followers = int(snap.get('followers', 0))
                # ADDED: vs-own deltas for quick-scan heatmap in report UI
                entry['vs_own'] = {
                    'followers_delta': comp_followers - own_followers,
                    'engagement_rate_delta': round(comp_er - own_er, 4),
                    'ahead': comp_er > own_er,
                }
            competitors_report.append(entry)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'network_filter': network_f or 'all',
            'generatedAt': datetime.now(UTC).isoformat(),
            'own_brand': own_latest,
            'competitors': competitors_report,
            'competitor_count': len(competitors_report),
        }

    @router.get('/competitive/share-of-voice')
    def share_of_voice(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        """
        ADDED: Share of Voice calculation based on estimated_mentions (§5.4 SoV).
        Returns percentage split across own brand + all tracked competitors.
        """
        enforce_rate_limit(f'{auth.tenant_id}:competitive:sov', 120, 60)
        network_f = network.strip().lower() if network else None

        with _lock:
            profiles = {
                p['id']: p.get('name', f'Competitor {p["id"]}')
                for p in profiles_memory
                if p.get('tenant_id') == auth.tenant_id
                and (network_f is None or p.get('network') == network_f)
            }
            all_snaps = [
                s for s in snapshots_memory
                if s.get('tenant_id') == auth.tenant_id
                and (network_f is None or s.get('network') == network_f)
            ]

        # Latest snapshot per competitor (including own brand = id 0)
        latest: dict[int, dict[str, Any]] = {}
        for snap in all_snaps:
            cid = int(snap.get('competitor_id', -1))
            if cid not in latest or str(snap.get('snapshot_date', '')) > str(latest[cid].get('snapshot_date', '')):
                latest[cid] = snap

        mentions_map: dict[str, int] = {}
        if 0 in latest:
            mentions_map['Your Brand'] = int(latest[0].get('estimated_mentions', 0))
        for cid, snap in latest.items():
            if cid != 0:
                name = profiles.get(cid, f'Competitor {cid}')
                mentions_map[name] = int(snap.get('estimated_mentions', 0))

        sov = _share_of_voice(mentions_map)
        total_mentions = sum(mentions_map.values())

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'network_filter': network_f or 'all',
            'generatedAt': datetime.now(UTC).isoformat(),
            'total_estimated_mentions': total_mentions,
            'share_of_voice': sov,
            'breakdown': [
                {
                    'brand': k,
                    'estimated_mentions': mentions_map[k],
                    'share_pct': sov[k],
                }
                for k in sov
            ],
        }

    return router
