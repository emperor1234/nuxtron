"""
Trusted-proxy header-stripping middleware.

Strips security-relevant headers unless the request arrived from a known,
configured edge proxy IP/CIDR. Without this, any client can set
``X-Client-Cert-Verified: true`` or ``X-Forwarded-Proto: https`` directly and
bypass mTLS/HTTPS enforcement (PDR §6.3).

Trusted-proxy contract (must be true of the deployment, not just the app):
  - The load balancer / reverse proxy is the ONLY thing that can reach this
    service's listening port. Direct access from the internet must be
    network-blocked (security group / firewall), not just header-stripped.
  - The proxy always sets ``X-Forwarded-Proto`` and (when mTLS is terminated
    at the proxy) ``X-Client-Cert-Verified`` itself, overwriting anything a
    client sent — this middleware is defense-in-depth for the case where that
    proxy contract is ever violated (misconfiguration, new ingress path, etc).
"""
from __future__ import annotations

import ipaddress
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger('nuxtron.security.trusted_proxy')

# Headers that influence security decisions downstream. These must only be
# trusted when the direct TCP peer is a configured proxy that we control.
_SECURITY_SENSITIVE_HEADERS = (
    'x-client-cert-verified',
    'x-forwarded-proto',
    'x-forwarded-for',
)


def _load_trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse ``TRUSTED_PROXY_CIDRS`` into network objects; raise on bad input."""
    raw = os.environ.get('TRUSTED_PROXY_CIDRS', '')
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in (e.strip() for e in raw.split(',') if e.strip()):
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError as exc:
            raise RuntimeError(
                f"TRUSTED_PROXY_CIDRS contains an invalid CIDR '{entry}': {exc}"
            ) from exc
    return networks


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """
    If the direct TCP peer is NOT in ``TRUSTED_PROXY_CIDRS``, strip all
    security-sensitive inbound headers before the request reaches routing —
    downstream code then correctly treats the connection as plain HTTP /
    unverified mTLS, which is the safe default.
    """

    def __init__(self, app, *, require_mtls: bool, enforce_https_header: bool) -> None:
        super().__init__(app)
        self._trusted_networks = _load_trusted_proxy_networks()
        self._require_mtls = require_mtls
        self._enforce_https_header = enforce_https_header

        if (require_mtls or enforce_https_header) and not self._trusted_networks:
            raise RuntimeError(
                'REQUIRE_MTLS or ENFORCE_HTTPS_HEADER is set but '
                'TRUSTED_PROXY_CIDRS is empty. Refusing to start: this '
                'configuration would trust client-supplied headers for '
                'security decisions, which is the exact hole PDR §6.3 '
                'identifies. Set TRUSTED_PROXY_CIDRS to your LB/proxy CIDR '
                "range, e.g. '10.0.0.0/16' for an internal ALB."
            )

    def _peer_is_trusted_proxy(self, request: Request) -> bool:
        client = request.client
        if client is None:
            return False
        try:
            peer_ip = ipaddress.ip_address(client.host)
        except ValueError:
            return False
        return any(peer_ip in net for net in self._trusted_networks)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if not self._peer_is_trusted_proxy(request):
            mutable_headers = request.headers.mutablecopy()
            stripped: list[str] = []
            for header in _SECURITY_SENSITIVE_HEADERS:
                if header in mutable_headers:
                    del mutable_headers[header]
                    stripped.append(header)
            if stripped:
                logger.info(
                    'stripped_security_sensitive_headers_from_untrusted_peer',
                    extra={'peer': request.client.host if request.client else None,
                           'headers': stripped},
                )
            request.scope['headers'] = mutable_headers.raw
        return await call_next(request)
