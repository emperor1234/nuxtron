"""Admin IP-allowlist middleware (WO-10).

Restricts ``/admin/`` (and any other configured protected prefix) to requests
originating from a configured network CIDR allowlist. When
``ADMIN_IP_ALLOWLIST`` is unset the middleware is inert (no restriction), so it
is safe by default and opt-in via environment.

The peer IP is taken from ``REMOTE_ADDR``; behind a proxy that sets
``X-Forwarded-For`` the trusted-proxy layer (WO-3 / the edge LB) must overwrite
that header — never trust a client-supplied forwarded-for directly.
"""
from __future__ import annotations

import ipaddress
import logging
import os
from collections.abc import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger('nuxtron.security.admin_allowlist')

_PROTECTED_PREFIXES: tuple[str, ...] = ('/admin/', '/api/metrics/')


def _allowlisted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    raw = os.environ.get('ADMIN_IP_ALLOWLIST', '')
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in (c.strip() for c in raw.split(',') if c.strip()):
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError as exc:
            logger.warning('ignoring invalid ADMIN_IP_ALLOWLIST entry %r: %s', cidr, exc)
    return networks


class AdminIPAllowlistMiddleware:
    """Reject requests to protected prefixes from non-allowlisted peers."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.networks = _allowlisted_networks()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.networks and any(request.path.startswith(p) for p in _PROTECTED_PREFIXES):
            peer_raw = request.META.get('REMOTE_ADDR', '0.0.0.0')
            try:
                peer = ipaddress.ip_address(peer_raw)
            except ValueError:
                logger.warning('unparseable REMOTE_ADDR %r; denying admin access', peer_raw)
                raise PermissionDenied('Admin access restricted to allowlisted networks.')
            if not any(peer in net for net in self.networks):
                logger.info(
                    'admin_access_denied_for_peer',
                    extra={'peer': peer_raw, 'path': request.path},
                )
                raise PermissionDenied('Admin access restricted to allowlisted networks.')
        return self.get_response(request)
