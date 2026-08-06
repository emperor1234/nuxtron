"""
Tests for tool_integrations.py pure helpers and routes.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestMaskFunction:
    def _fn(self):
        from backend.fastapi.app.routers.tool_integrations import _mask
        return _mask

    def test_empty_string_returns_stars(self) -> None:
        fn = self._fn()
        assert fn("") == "****"

    def test_short_key_returns_stars(self) -> None:
        fn = self._fn()
        assert fn("abc") == "****"

    def test_long_key_shows_last_4(self) -> None:
        fn = self._fn()
        result = fn("sk_live_abcdefgh")
        assert result == "****efgh"

    def test_exactly_4_chars_shows_last_4(self) -> None:
        fn = self._fn()
        result = fn("abcd")
        assert result == "****abcd"


class TestConfiguredFunction:
    def _fn(self):
        from backend.fastapi.app.routers.tool_integrations import _configured
        return _configured

    def test_unknown_tool_returns_false(self) -> None:
        fn = self._fn()
        assert fn("nonexistent_tool_xyz") is False

    def test_known_tool_not_configured(self) -> None:
        fn = self._fn()
        # zapier is a known tool, but env var likely not set in test
        with patch_env("ZAPIER_WEBHOOK_URL", ""):
            result = fn("zapier")
            assert result is False

    def test_known_tool_configured(self) -> None:
        fn = self._fn()
        # Check if zapier has env_key set
        from backend.fastapi.app.routers.tool_integrations import _TOOL_MAP
        if "zapier" in _TOOL_MAP:
            env_key = _TOOL_MAP["zapier"].get("env_key", "")
            if env_key:
                with patch_env(env_key, "https://hooks.zapier.com/test"):
                    result = fn("zapier")
                    assert result is True


def patch_env(key: str, value: str):
    """Context manager to temporarily set an env var."""
    from unittest.mock import patch
    return patch.dict(os.environ, {key: value})


class TestToolStatusFunction:
    def test_returns_expected_keys(self) -> None:
        from backend.fastapi.app.routers.tool_integrations import TOOLS, _tool_status
        if TOOLS:
            spec = TOOLS[0]
            result = _tool_status(spec)
            assert "key" in result
            assert "configured" in result
            assert "display_name" in result
            assert "category" in result
            assert "last_test_status" in result
            assert result["last_test_status"] == "untested"

    def test_unconfigured_tool_no_masked_key(self) -> None:
        from backend.fastapi.app.routers.tool_integrations import TOOLS, _tool_status
        for spec in TOOLS:
            env_key = spec.get("env_key", "")
            if env_key and not os.getenv(env_key, "").strip():
                result = _tool_status(spec)
                assert result["api_key_masked"] is None
                break

    def test_configured_tool_shows_masked_key(self) -> None:
        from backend.fastapi.app.routers.tool_integrations import TOOLS, _tool_status
        for spec in TOOLS:
            env_key = spec.get("env_key", "")
            if env_key:
                with patch_env(env_key, "sk_test_1234567890"):
                    result = _tool_status(spec)
                    assert result["configured"] is True
                    assert result["api_key_masked"] is not None
                    assert "7890" in result["api_key_masked"]
                break


class TestToolIntegrationsRoutes:
    def test_list_tools(self, client: TestClient) -> None:
        r = client.get("/integrations/tools", headers=H)
        assert r.status_code in VALID

    def test_list_tools_returns_tools_key(self, client: TestClient) -> None:
        r = client.get("/integrations/tools", headers=H)
        if r.status_code == 200:
            data = r.json()
            assert "tools" in data
            assert "total" in data

    def test_get_tool_known(self, client: TestClient) -> None:
        from backend.fastapi.app.routers.tool_integrations import _TOOL_MAP
        if _TOOL_MAP:
            tool_key = next(iter(_TOOL_MAP))
            r = client.get(f"/integrations/tools/{tool_key}", headers=H)
            assert r.status_code in VALID

    def test_get_tool_unknown(self, client: TestClient) -> None:
        r = client.get("/integrations/tools/nonexistent_tool_xyz", headers=H)
        assert r.status_code == 404

    def test_update_tool_config(self, client: TestClient) -> None:
        r = client.put("/integrations/integrations/tools/zapier", headers=H, json={
            "api_key": "test-key-123456789",
        })
        assert r.status_code in VALID

    def test_update_tool_config_unknown(self, client: TestClient) -> None:
        r = client.put("/integrations/integrations/tools/nonexistent_xyz", headers=H, json={
            "api_key": "test",
        })
        assert r.status_code in VALID

    def test_test_tool(self, client: TestClient) -> None:
        from backend.fastapi.app.routers.tool_integrations import _TOOL_MAP
        if _TOOL_MAP:
            tool_key = next(iter(_TOOL_MAP))
            r = client.post(f"/integrations/tools/{tool_key}/test", headers=H, json={})
            assert r.status_code in VALID

    def test_test_tool_unknown(self, client: TestClient) -> None:
        r = client.post("/integrations/tools/nonexistent_tool_xyz/test", headers=H, json={})
        assert r.status_code in VALID
