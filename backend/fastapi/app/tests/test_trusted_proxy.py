"""Tests for the trusted-proxy header-stripping middleware (WO-3).

The middleware strips ``X-Client-Cert-Verified`` / ``X-Forwarded-Proto`` /
``X-Forwarded-For`` unless the direct TCP peer is inside
``TRUSTED_PROXY_CIDRS``. The security-critical property is that spoofed
headers from an *untrusted* peer are never seen downstream.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.trusted_proxy import (
    TrustedProxyMiddleware,
    _load_trusted_proxy_networks,
)


@pytest.fixture(autouse=True)
def _reset_trusted_cidrs_env() -> Iterator[None]:
    yield
    os.environ.pop("TRUSTED_PROXY_CIDRS", None)


def _make_app(trusted_cidrs: str) -> FastAPI:
    os.environ["TRUSTED_PROXY_CIDRS"] = trusted_cidrs
    app = FastAPI()
    app.add_middleware(TrustedProxyMiddleware, require_mtls=True, enforce_https_header=True)

    @app.get("/whoami")
    def whoami(request: Request) -> dict:
        return {
            "cert_verified": request.headers.get("x-client-cert-verified"),
            "proto": request.headers.get("x-forwarded-proto"),
        }

    return app


class TestTrustedProxyStartupGuard:
    def test_startup_fails_without_trusted_cidrs_when_flags_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A misconfigured deploy (flags on, no CIDRs) must refuse to serve."""
        monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
        app = FastAPI()
        app.add_middleware(
            TrustedProxyMiddleware, require_mtls=True, enforce_https_header=True
        )
        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(RuntimeError, match="TRUSTED_PROXY_CIDRS is empty"):
            client.get("/whoami")

    def test_invalid_cidr_rejected_at_load(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "not-a-network")
        with pytest.raises(RuntimeError, match="invalid CIDR"):
            _load_trusted_proxy_networks()


class TestHeaderStrippingFromUntrustedPeer:
    def test_untrusted_peer_has_spoofed_headers_stripped(self) -> None:
        """The TestClient peer ("testclient") is not a trusted IP, so the
        middleware must strip the spoofable headers before they reach routing."""
        app = _make_app(trusted_cidrs="10.0.0.0/8")
        client = TestClient(app)
        response = client.get(
            "/whoami",
            headers={"x-client-cert-verified": "true", "x-forwarded-proto": "https"},
        )
        body = response.json()
        assert body["cert_verified"] is None
        assert body["proto"] is None


class TestTrustedPeerPassthrough:
    """Validates the *helper* that decides trust, against real IP literals,
    since the TestClient presents a non-IP peer string ("testclient")."""

    def _mw(self) -> TrustedProxyMiddleware:
        os.environ["TRUSTED_PROXY_CIDRS"] = "10.0.0.0/8,127.0.0.0/8"
        # __init__ only enforces non-empty CIDRs when flags are on; both True.
        return TrustedProxyMiddleware(app=MagicMock(), require_mtls=True, enforce_https_header=True)  # type: ignore[arg-type]

    def test_ip_inside_trusted_cidr_is_trusted(self) -> None:
        mw = self._mw()
        req = MagicMock()
        req.client.host = "10.5.3.2"
        assert mw._peer_is_trusted_proxy(req) is True

    def test_ip_outside_trusted_cidr_is_untrusted(self) -> None:
        mw = self._mw()
        req = MagicMock()
        req.client.host = "203.0.113.9"  # public TEST-NET-3
        assert mw._peer_is_trusted_proxy(req) is False

    def test_unparseable_peer_is_untrusted(self) -> None:
        mw = self._mw()
        req = MagicMock()
        req.client.host = "testclient"  # what FastAPI's TestClient reports
        assert mw._peer_is_trusted_proxy(req) is False

    def test_missing_client_is_untrusted(self) -> None:
        mw = self._mw()
        req = MagicMock()
        req.client = None
        assert mw._peer_is_trusted_proxy(req) is False


class TestFlagsOffInert:
    def test_no_mtls_no_https_means_no_trusted_cidr_required(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When neither security flag is on, the app must boot without any
        TRUSTED_PROXY_CIDRS config (it's optional, not enforced)."""
        monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
        # Construction must NOT raise when both flags are False.
        TrustedProxyMiddleware(
            app=MagicMock(), require_mtls=False, enforce_https_header=False  # type: ignore[arg-type]
        )
