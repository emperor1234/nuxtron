from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.fastapi.app.routers.platform_integration import (
    _decode_oauth_state,
    _encode_oauth_state,
    _exchange_oauth_code,
)


def test_oauth_state_is_bound_to_tenant_platform_and_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OAUTH_STATE_SIGNING_KEY', 'test-oauth-state-secret')
    state = _encode_oauth_state(tenant_id='tenant-a', platform='twitter', redirect_uri='https://app.example/callback', expires_at=9999999999)
    _decode_oauth_state(state, tenant_id='tenant-a', platform='twitter', redirect_uri='https://app.example/callback')
    with pytest.raises(Exception):
        _decode_oauth_state(state, tenant_id='tenant-b', platform='twitter', redirect_uri='https://app.example/callback')


def test_oauth_state_expiry_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OAUTH_STATE_SIGNING_KEY', 'test-oauth-state-secret')
    state = _encode_oauth_state(tenant_id='tenant-a', platform='linkedin', redirect_uri='https://app.example/callback', expires_at=1)
    with pytest.raises(Exception):
        _decode_oauth_state(state, tenant_id='tenant-a', platform='linkedin', redirect_uri='https://app.example/callback')


def test_code_exchange_rejects_provider_without_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('TWITTER_CLIENT_ID', 'client-id')
    monkeypatch.setenv('TWITTER_CLIENT_SECRET', 'client-secret')
    response = MagicMock(is_success=True)
    response.json.return_value = {'token_type': 'bearer'}
    with patch('backend.fastapi.app.routers.platform_integration.httpx.post', return_value=response):
        with pytest.raises(Exception) as exc_info:
            _exchange_oauth_code('twitter', 'authorization-code', 'https://app.example/callback')
    assert getattr(exc_info.value, 'status_code', None) == 502
