"""Targeted coverage for tool_integrations and utm_builder uncovered branches."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "tool-utm-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestToolIntegrationsCoverage:
    def test_update_tool_config_secondary_key(self, client: TestClient) -> None:
        payload = {"api_key": "sk-test-12345678", "secondary_key": "anth-test-87654321"}
        r = client.put(
            "/integrations/integrations/tools/openai_gpt4o",
            headers=H,
            json=payload,
        )
        if r.status_code in (404, 405):
            r = client.put(
                "/integrations/tools/openai_gpt4o",
                headers=H,
                json=payload,
            )
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            data = r.json()
            assert data["configured"] is True
            assert data["api_key_masked"].endswith("5678")

    def test_tool_test_skipped_when_no_public_endpoint(self, client: TestClient) -> None:
        r = client.post("/integrations/tools/screaming_frog/test", headers=H)
        assert r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "skipped"

    def test_tool_test_reachable_non_5xx(self, client: TestClient) -> None:
        response = MagicMock()
        response.status_code = 401

        async_client = AsyncMock()
        async_client.__aenter__.return_value = async_client
        async_client.__aexit__.return_value = False
        async_client.get.return_value = response

        with patch.dict(os.environ, {"SERPER_API_KEY": "serper-secret"}, clear=False), patch(
            "backend.fastapi.app.routers.tool_integrations.httpx.AsyncClient",
            return_value=async_client,
        ):
            r = client.post("/integrations/tools/serper/test", headers=H)
        assert r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok"
            assert data["http_status"] == 401

    def test_tool_test_http_5xx_error(self, client: TestClient) -> None:
        response = MagicMock()
        response.status_code = 503

        async_client = AsyncMock()
        async_client.__aenter__.return_value = async_client
        async_client.__aexit__.return_value = False
        async_client.get.return_value = response

        with patch(
            "backend.fastapi.app.routers.tool_integrations.httpx.AsyncClient",
            return_value=async_client,
        ):
            r = client.post("/integrations/tools/google_search_console/test", headers=H)
        assert r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "error"
            assert data["http_status"] == 503

    def test_tool_test_exception_path(self, client: TestClient) -> None:
        async_client = AsyncMock()
        async_client.__aenter__.return_value = async_client
        async_client.__aexit__.return_value = False
        async_client.get.side_effect = RuntimeError("network down")

        with patch(
            "backend.fastapi.app.routers.tool_integrations.httpx.AsyncClient",
            return_value=async_client,
        ):
            r = client.post("/integrations/tools/google_business_profile/test", headers=H)
        assert r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "error"
            assert "network down" in data["reason"]


class TestUtmBuilderCoverage:
    def test_create_list_update_delete_preset_success(self, client: TestClient) -> None:
        create_r = client.post(
            "/publishing/utm/presets",
            headers=H,
            json={
                "name": "LinkedIn Q3",
                "utm_source": "linkedin",
                "utm_medium": "social",
                "utm_campaign": "q3 pipeline",
                "utm_term": "enterprise ai",
                "utm_content": "variant a",
                "auto_lowercase": True,
                "replace_spaces": True,
                "description": "Primary Q3 preset",
            },
        )
        assert create_r.status_code in (200, 201)
        preset_id = create_r.json()["preset"]["id"]

        list_r = client.get("/publishing/utm/presets?search=linkedin&limit=5&offset=0", headers=H)
        assert list_r.status_code == 200
        if list_r.status_code == 200:
            assert list_r.json()["count"] >= 1

        update_r = client.patch(
            f"/publishing/utm/presets/{preset_id}",
            headers=H,
            json={
                "name": "LinkedIn Q3 Updated",
                "utm_campaign": "q3 pipeline updated",
                "replace_spaces": False,
                "description": "Updated preset",
            },
        )
        assert update_r.status_code == 200
        if update_r.status_code == 200:
            data = update_r.json()["preset"]
            assert data["name"] == "LinkedIn Q3 Updated"
            assert data["replace_spaces"] is False

        delete_r = client.delete(f"/publishing/utm/presets/{preset_id}", headers=H)
        assert delete_r.status_code == 200
        if delete_r.status_code == 200:
            assert delete_r.json()["deleted"] is True

    def test_update_and_delete_missing_preset(self, client: TestClient) -> None:
        update_r = client.patch(
            "/publishing/utm/presets/99999",
            headers=H,
            json={"utm_campaign": "missing"},
        )
        delete_r = client.delete("/publishing/utm/presets/99999", headers=H)
        assert update_r.status_code == 404
        assert delete_r.status_code == 404

    def test_build_utm_with_preset_overrides_and_campaign_tag(self, client: TestClient) -> None:
        preset_r = client.post(
            "/publishing/utm/presets",
            headers=H,
            json={
                "name": "Twitter Launch",
                "utm_source": "twitter",
                "utm_medium": "social",
                "utm_campaign": "spring launch",
                "auto_lowercase": True,
                "replace_spaces": True,
            },
        )
        assert preset_r.status_code in (200, 201)
        preset_id = preset_r.json()["preset"]["id"]

        build_r = client.post(
            "/publishing/utm/build",
            headers=H,
            json={
                "base_url": "https://example.com/landing?page=1",
                "preset_id": preset_id,
                "utm_content": "hero creative",
                "campaign_tag": "paid",
                "utm_source": "x",
            },
        )
        assert build_r.status_code == 200
        if build_r.status_code == 200:
            data = build_r.json()
            assert "tagged_url" in data
            assert "utm_campaign=spring_launch_paid" in data["tagged_url"]
            assert data["params"]["utm_source"] == "x"
            assert data["params"]["utm_content"] == "hero_creative"

    def test_build_utm_missing_preset_and_invalid_url(self, client: TestClient) -> None:
        missing_r = client.post(
            "/publishing/utm/build",
            headers=H,
            json={"base_url": "https://example.com", "preset_id": 99999},
        )
        invalid_url_r = client.post(
            "/publishing/utm/build",
            headers=H,
            json={
                "base_url": "not-a-url",
                "utm_source": "linkedin",
                "utm_medium": "social",
                "utm_campaign": "bad url",
            },
        )
        missing_fields_r = client.post(
            "/publishing/utm/build",
            headers=H,
            json={"base_url": "https://example.com", "utm_source": "linkedin"},
        )
        assert missing_r.status_code == 404
        assert invalid_url_r.status_code == 422
        assert missing_fields_r.status_code == 422

    def test_build_utm_with_shortener_enabled(self, client: TestClient) -> None:
        with patch(
            "backend.fastapi.app.routers.utm_builder._shorten_url",
            return_value=("https://bit.ly/nuxtron", "bitly"),
        ):
            r = client.post(
                "/publishing/utm/build",
                headers=H,
                json={
                    "base_url": "https://example.com/pricing",
                    "utm_source": "linkedin",
                    "utm_medium": "social",
                    "utm_campaign": "launch campaign",
                    "shorten": True,
                    "shortener_provider": "bitly",
                },
            )
        assert r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            assert data["short_url"] == "https://bit.ly/nuxtron"
            assert data["shortener_provider"] == "bitly"

    def test_shorten_url_endpoint_success_and_invalid(self, client: TestClient) -> None:
        with patch(
            "backend.fastapi.app.routers.utm_builder._shorten_url",
            return_value=("https://tinyurl.com/nuxtron", "tinyurl"),
        ):
            ok_r = client.post(
                "/publishing/utm/shorten",
                headers=H,
                json={"url": "https://example.com/landing", "provider": "auto"},
            )
        assert ok_r.status_code == 200
        if ok_r.status_code == 200:
            payload = ok_r.json()
            assert payload["short_url"] == "https://tinyurl.com/nuxtron"
            assert payload["provider"] == "tinyurl"

        invalid_r = client.post(
            "/publishing/utm/shorten",
            headers=H,
            json={"url": "not-a-url", "provider": "auto"},
        )
        assert invalid_r.status_code == 422
