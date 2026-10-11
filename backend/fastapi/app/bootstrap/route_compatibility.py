"""Frozen compatibility policy for historically shadowed HTTP routes.

The earliest registration remains the runtime winner and keeps its route-list
position, endpoint and name. The latest registration remains the OpenAPI winner
and supplies its operation ID, dependencies, schemas, tags and deprecation data.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

RouteKey = tuple[str, str]

FROZEN_MERGED_HTTP_ROUTE_KEYS: frozenset[RouteKey] = frozenset(
    {
        ('GET', '/analytics/export'),
        ('GET', '/social/calendar'),
        ('GET', '/social/listening/mentions'),
        ('POST', '/social/team/invite'),
        ('GET', '/social/team/members'),
    }
)


def _pin_openapi_summary(route: APIRoute) -> None:
    """Freeze FastAPI's last-writer default before restoring the runtime name."""
    if route.summary is None:
        route.summary = route.name.replace('_', ' ').title()


def merge_frozen_http_route_overlaps(app: FastAPI) -> None:
    """Merge only the frozen first-runtime/last-OpenAPI route overlaps."""
    seen: set[RouteKey] = set()
    first_routes: dict[RouteKey, tuple[int, APIRoute]] = {}
    merged: set[RouteKey] = set()
    retained: list[BaseRoute] = []

    for route in app.router.routes:
        if not isinstance(route, APIRoute) or not route.methods:
            retained.append(route)
            continue

        keys = {(str(method).upper(), route.path) for method in route.methods}
        overlap = keys & seen
        if not overlap:
            position = len(retained)
            retained.append(route)
            seen.update(keys)
            first_routes.update((key, (position, route)) for key in keys)
            continue

        if overlap != keys:
            raise RuntimeError(f'Partially shadowed HTTP route registration: {sorted(overlap)}')
        if not keys <= FROZEN_MERGED_HTTP_ROUTE_KEYS:
            raise RuntimeError(f'Unexpected shadowed HTTP route registration: {sorted(keys)}')
        position, runtime_route = first_routes[next(iter(keys))]
        if any(first_routes[key][0] != position or first_routes[key][1] is not runtime_route for key in keys):
            raise RuntimeError(f'Inconsistent shadowed HTTP route registration: {sorted(keys)}')

        _pin_openapi_summary(route)
        route.app, route.endpoint, route.name = runtime_route.app, runtime_route.endpoint, runtime_route.name
        retained[position] = route
        merged.update(keys)

    missing = FROZEN_MERGED_HTTP_ROUTE_KEYS - merged
    if missing:
        raise RuntimeError(f'Expected shadowed HTTP routes are absent: {sorted(missing)}')
    app.router.routes[:] = retained
    app.state.merged_http_route_keys = frozenset(merged)
