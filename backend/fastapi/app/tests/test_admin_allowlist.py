from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.fastapi.app.middleware import admin_allowlist


def _run(awaitable: Awaitable[None]) -> None:
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(awaitable)
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def reset_allowlist_cache() -> Iterator[None]:
    admin_allowlist._NETWORKS = None
    yield
    admin_allowlist._NETWORKS = None


def _request(client: tuple[str, int] | None) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/admin",
            "raw_path": b"/admin",
            "query_string": b"",
            "headers": [],
            "client": client,
            "server": ("nuxtron.test", 443),
        }
    )


def test_configured_allowlist_rejects_missing_peer_even_for_unspecified_cidr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIVILEGED_IP_ALLOWLIST", "0.0.0.0/0")

    with pytest.raises(HTTPException) as error:
        _run(admin_allowlist.require_privileged_ip(_request(None)))

    assert error.value.status_code == 403
    assert error.value.detail == "Privileged route: client address is unavailable."


def test_configured_allowlist_accepts_peer_inside_allowed_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIVILEGED_IP_ALLOWLIST", "10.0.0.0/8")

    _run(admin_allowlist.require_privileged_ip(_request(("10.2.3.4", 4242))))
