import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]


class DependencyAdvanceRequest(BaseModel):
    action: str = Field(default='complete_milestone', max_length=60)
    points: int = Field(default=12, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class CommunityCircleRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    topic: str = Field(default='growth', max_length=80)
    description: str = Field(default='', max_length=320)


class CommunityPostRequest(BaseModel):
    circle_id: int
    content: str = Field(min_length=3, max_length=2000)
    kind: str = Field(default='win', max_length=40)


class CommunityAmaRequest(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    host_name: str = Field(min_length=2, max_length=80)
    starts_at: str = Field(min_length=10, max_length=40)


@dataclass
class DependencyCommunityContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    dependency_stages: list[str]
    dependency_profiles_memory: list[dict[str, Any]]
    dependency_events_memory: list[dict[str, Any]]
    community_circles_memory: list[dict[str, Any]]
    community_posts_memory: list[dict[str, Any]]
    community_amas_memory: list[dict[str, Any]]
    community_circle_not_found: str
    get_dependency_profile_fn: Callable[[str], dict[str, Any]]
    compute_dependency_score_fn: Callable[[str, int], tuple[int, dict[str, int]]]
    target_stage_for_score_fn: Callable[[int], str]
    stage_index_fn: Callable[[str], int]
    get_default_circle_fn: Callable[[str], dict[str, Any]]
    tenant_display_name_fn: Callable[[str], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]


def register_dependency_community_routes(*, router: APIRouter, context: DependencyCommunityContext) -> None:
    _register_dependency_routes(router, context)
    _register_community_routes(router, context)


def _register_dependency_routes(router: APIRouter, ctx: DependencyCommunityContext) -> None:
    @router.get('/engagement/dependency-creator')
    def dependency_creator(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:dependency:get', 240, 60)
        with ctx.lock:
            profile = ctx.get_dependency_profile_fn(auth.tenant_id)
            score, signals = ctx.compute_dependency_score_fn(auth.tenant_id, int(profile.get('manual_points', 0)))
            target_stage = ctx.target_stage_for_score_fn(score)

            profile['dependency_score'] = score
            profile['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'dependency_creator': {
                'profile': snapshot,
                'target_stage': target_stage,
                'stages': ctx.dependency_stages,
                'signals': signals,
            },
        }

    @router.post('/engagement/dependency-creator/advance')
    def dependency_creator_advance(payload: DependencyAdvanceRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:dependency:advance', 120, 60)
        with ctx.lock:
            profile = ctx.get_dependency_profile_fn(auth.tenant_id)
            previous_stage = str(profile.get('stage', 'explorer'))
            profile['manual_points'] = int(profile.get('manual_points', 0)) + int(payload.points)

            score, signals = ctx.compute_dependency_score_fn(auth.tenant_id, int(profile.get('manual_points', 0)))
            target_stage = ctx.target_stage_for_score_fn(score)
            progressed = ctx.stage_index_fn(target_stage) > ctx.stage_index_fn(previous_stage)

            profile['dependency_score'] = score
            profile['stage'] = target_stage if progressed else previous_stage
            profile['last_action'] = payload.action
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']

            event: dict[str, Any] = {
                'id': len(ctx.dependency_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'action': payload.action,
                'points_added': int(payload.points),
                'note': payload.note,
                'from_stage': previous_stage,
                'to_stage': profile['stage'],
                'dependency_score': score,
                'signals': signals,
                'created_at': profile['last_action_at'],
            }
            ctx.dependency_events_memory.append(event)

            credits_awarded = 0
            if progressed:
                delta = ctx.stage_index_fn(profile['stage']) - ctx.stage_index_fn(previous_stage)
                credits_awarded = 25 * max(1, delta)
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'dependency_creator_stage_advance')
                ctx.append_notification_fn(
                    auth.tenant_id,
                    'Dependency Stage Advanced',
                    f'You advanced from {previous_stage} to {profile["stage"]} and earned {credits_awarded} AI credits.',
                    'dependency_creator',
                )

            ctx.append_audit_fn(
                auth.tenant_id,
                'dependency_creator_advance',
                {
                    'event_id': event['id'],
                    'from_stage': previous_stage,
                    'to_stage': profile['stage'],
                    'dependency_score': score,
                    'progressed': progressed,
                },
            )
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'progressed': progressed,
            'credits_awarded': credits_awarded,
            'profile': snapshot,
            'event': event,
        }

    @router.get('/engagement/dependency-creator/timeline')
    def dependency_creator_timeline(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:dependency:timeline', 240, 60)
        with ctx.lock:
            items = [item.copy() for item in ctx.dependency_events_memory if item.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'timeline': items[:limit]}


def _register_community_routes(router: APIRouter, ctx: DependencyCommunityContext) -> None:
    @router.get('/engagement/community')
    def community_overview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:community:get', 240, 60)
        with ctx.lock:
            ctx.get_default_circle_fn(auth.tenant_id)
            circles = [item.copy() for item in ctx.community_circles_memory if item.get('tenant_id') == auth.tenant_id]
            posts = [item.copy() for item in ctx.community_posts_memory if item.get('tenant_id') == auth.tenant_id]
            upcoming_amas = [item.copy() for item in ctx.community_amas_memory if item.get('tenant_id') == auth.tenant_id]

        circles.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        posts.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        upcoming_amas.sort(key=lambda item: str(item.get('starts_at', '')))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'community': {
                'circles': circles[:10],
                'recent_posts': posts[:10],
                'upcoming_amas': upcoming_amas[:10],
            },
        }

    @router.post('/engagement/community/circles')
    def create_community_circle(payload: CommunityCircleRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:community:circles:create', 90, 60)
        with ctx.lock:
            now_iso = datetime.now(UTC).isoformat()
            circle: dict[str, Any] = {
                'id': len(ctx.community_circles_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'topic': payload.topic,
                'description': payload.description,
                'members': 1,
                'is_default': False,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.community_circles_memory.append(circle)
            ctx.append_audit_fn(auth.tenant_id, 'community_circle_created', {'circle_id': circle['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'circle': circle}

    @router.post('/engagement/community/posts', responses={404: {'description': 'Community circle not found.'}})
    def create_community_post(payload: CommunityPostRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:community:posts:create', 120, 60)
        with ctx.lock:
            ctx.get_default_circle_fn(auth.tenant_id)
            circle = next(
                (
                    item for item in ctx.community_circles_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.circle_id)
                ),
                None,
            )
            if circle is None:
                raise HTTPException(status_code=404, detail=ctx.community_circle_not_found)

            post: dict[str, Any] = {
                'id': len(ctx.community_posts_memory) + 1,
                'tenant_id': auth.tenant_id,
                'circle_id': int(circle['id']),
                'circle_name': circle.get('name'),
                'author': ctx.tenant_display_name_fn(auth.tenant_id),
                'content': payload.content,
                'kind': payload.kind,
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.community_posts_memory.append(post)

            ctx.append_notification_fn(
                auth.tenant_id,
                'Community Post Published',
                f"Your {payload.kind} post is now visible in {circle.get('name')}.",
                'community',
            )
            ctx.append_audit_fn(auth.tenant_id, 'community_post_created', {'post_id': post['id'], 'circle_id': circle['id']})

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'post': post}

    @router.post('/engagement/community/amas')
    def schedule_community_ama(payload: CommunityAmaRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:community:amas:create', 60, 60)
        with ctx.lock:
            ama: dict[str, Any] = {
                'id': len(ctx.community_amas_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'host_name': payload.host_name,
                'starts_at': payload.starts_at,
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.community_amas_memory.append(ama)
            ctx.append_audit_fn(auth.tenant_id, 'community_ama_scheduled', {'ama_id': ama['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ama': ama}

    @router.get('/engagement/community/feed')
    def community_feed(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:community:feed', 240, 60)
        with ctx.lock:
            posts = [item.copy() for item in ctx.community_posts_memory]
        posts.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(posts), 'feed': posts[:limit]}
