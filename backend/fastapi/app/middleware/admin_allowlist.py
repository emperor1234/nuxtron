"""FastAPI dependency: restrict privileged routes to an IP allowlist (WO-10).

Apply to sensitive routers (``/vault``, ``/siem``, ``/api-governance``,
``/super-admin``) via ``Depends(require_privileged_ip)``. The allowlist is the
``PRIVILEGED_IP_ALLOWLIST`` env var (comma-separated CIDRs); when unset the
dependency is inert (no restriction) so it is safe-by-default and opt-in.

The peer IP is taken from ``request.client.host``. Behind a proxy, the
TrustedProxyMiddleware (WO-3) must have already validated the connection.
"""
from __future__ import annotations

import ipaddress
import os

from fastapi import HTTPException, Request

_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None


def _load_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    global _NETWORKS
    if _NETWORKS is not None:
        return _NETWORKS
    raw = os.environ.get('PRIVILEGED_IP_ALLOWLIST', '')
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in (c.strip() for c in raw.split(',') if c.strip()):
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            pass  # ignore invalid entries; startup log elsewhere covers it
    _NETWORKS = networks
    return networks


async def require_privileged_ip(request: Request) -> None:
    """Reject the request with 403 if the peer is outside the allowlist.

    When ``PRIVILEGED_IP_ALLOWLIST`` is empty this is a no-op, so the control
    is opt-in per deployment rather than a hard global gate.
    """
    networks = _load_networks()
    if not networks:
        return  # not configured → no restriction
    client = request.client
    peer_raw = client.host if client else ''
    try:
        peer = ipaddress.ip_address(peer_raw or '0.0.0.0')
    except ValueError:
        raise HTTPException(status_code=403, detail='Privileged route: unparseable client address.')
    if not any(peer in net for net in networks):
        raise HTTPException(
            status_code=403,
            detail='Privileged route access restricted to allowlisted networks.',
        )
