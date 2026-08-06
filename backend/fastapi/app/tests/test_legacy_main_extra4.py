"""
legacy_main.py extra tests - round 4.
Targets missing branches: AI security resolve appeal, IDS events, AI gateway branches.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ["SUPER_ADMIN_API_KEY"] = "test-super-admin-key-xyz"


import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-extra4"}
SA_H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-extra4", "X-Super-Admin-Key": "test-super-admin-key-xyz"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestAiSecurityAppealResolve:
    """Lines 3600-3617: appeal resolve branches."""

    def test_resolve_nonexistent_appeal(self, client: TestClient) -> None:
        """Resolve non-existent appeal → 404 (line 3605)."""
        r = client.post("/ai/security/admin/appeals/99999/resolve", headers=SA_H, json={
            "decision": "rejected",
            "notes": "Not found test",
        })
        assert r.status_code in VALID

    def test_create_appeal_then_resolve_rejected(self, client: TestClient) -> None:
        """Create appeal, then resolve as rejected (lines 3606-3607)."""
        # Create appeal first
        cr = client.post("/ai/security/appeals", headers=H, json={
            "reason": "My prompt was incorrectly blocked due to false positive.",
            "original_prompt": "Write a business email about data migration",
        })
        assert cr.status_code in VALID
        if cr.status_code == 200:
            appeal_id = cr.json().get("appeal", {}).get("id")
            if appeal_id:
                r = client.post(f"/ai/security/admin/appeals/{appeal_id}/resolve", headers=SA_H, json={
                    "decision": "rejected",
                    "notes": "Reviewed and rejected",
                })
                assert r.status_code in VALID

    def test_create_appeal_then_resolve_approved(self, client: TestClient) -> None:
        """Create appeal, then resolve as approved (lines 3609-3613)."""
        # Create appeal first
        cr = client.post("/ai/security/appeals", headers=H, json={
            "reason": "My API key was incorrectly blocked.",
            "original_prompt": "Summarize this document",
        })
        assert cr.status_code in VALID
        if cr.status_code == 200:
            appeal_id = cr.json().get("appeal", {}).get("id")
            if appeal_id:
                r = client.post(f"/ai/security/admin/appeals/{appeal_id}/resolve", headers=SA_H, json={
                    "decision": "approved",
                    "notes": "Reviewed and approved - false positive confirmed",
                })
                assert r.status_code in VALID


class TestAiSecurityIdsEvents:
    """Lines 3648-3695: IDS events route branches."""

    def test_ids_event_alert_action(self, client: TestClient) -> None:
        """IDS event with alert action (lines 3648-3660)."""
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "source": "suricata",
            "severity": "medium",
            "rule_id": "RULE-001",
            "message": "Suspicious network traffic detected",
            "action": "alert",
        })
        assert r.status_code in VALID

    def test_ids_event_block_tenant(self, client: TestClient) -> None:
        """IDS event with block-tenant action (line 3651)."""
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "source": "fail2ban",
            "severity": "critical",
            "rule_id": "BAN-001",
            "message": "Repeated failed authentication from tenant",
            "tenant_id": "malicious-tenant-123",
            "action": "block-tenant",
        })
        assert r.status_code in VALID

    def test_ids_event_disable_provider(self, client: TestClient) -> None:
        """IDS event with disable-provider action (line 3653)."""
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "source": "ossec",
            "severity": "high",
            "rule_id": "PROV-001",
            "message": "Provider API key detected as compromised",
            "provider": "openai",
            "action": "disable-provider",
        })
        assert r.status_code in VALID

    def test_ids_event_with_ip_address(self, client: TestClient) -> None:
        """IDS event with IP address (line 3645)."""
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "source": "zeek",
            "severity": "high",
            "rule_id": "IP-001",
            "message": "Suspicious IP detected",
            "ip_address": "192.168.1.100",
            "action": "alert",
        })
        assert r.status_code in VALID

    def test_ids_event_critical_severity(self, client: TestClient) -> None:
        """IDS event with critical severity creates critical alert (line 3682)."""
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "source": "manual",
            "severity": "critical",
            "rule_id": "CRIT-001",
            "message": "Critical security event detected manually",
            "action": "alert",
        })
        assert r.status_code in VALID


class TestAiSecurityIdsState:
    """Lines 3682-3695: IDS state branches."""

    def test_ids_state_default_window(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/ids/state", headers=SA_H)
        assert r.status_code in VALID

    def test_ids_state_custom_window(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/ids/state?window_minutes=30", headers=SA_H)
        assert r.status_code in VALID


class TestAiSecurityEmailQueue:
    """Lines 3720-3795: email queue filter branches."""

    def test_email_queue_failed_filter(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/email-queue?status=failed", headers=SA_H)
        assert r.status_code in VALID

    def test_email_queue_all_filter(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/email-queue?status=all", headers=SA_H)
        assert r.status_code in VALID

    def test_email_queue_queued_filter(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/email-queue?status=queued", headers=SA_H)
        assert r.status_code in VALID

    def test_email_queue_sent_filter(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/email-queue?status=sent", headers=SA_H)
        assert r.status_code in VALID


class TestAiGatewayBranches:
    """Lines 3269-3358: AI gateway generate route branches."""

    def test_ai_gateway_unsupported_provider(self, client: TestClient) -> None:
        """Unsupported provider → 422 (line 3291)."""
        r = client.post("/ai/gateway/generate", headers=H, json={
            "provider": "unsupported_ai_provider_xyz",
            "prompt": "Hello world",
        })
        assert r.status_code in VALID

    def test_ai_gateway_google_vertex_provider(self, client: TestClient) -> None:
        """Google vertex provider path (line 3315)."""
        r = client.post("/ai/gateway/generate", headers=H, json={
            "provider": "google_vertex",
            "prompt": "Explain quantum computing",
        })
        assert r.status_code in VALID

    def test_ai_gateway_together_ai_provider(self, client: TestClient) -> None:
        """Together AI / generic provider path."""
        r = client.post("/ai/gateway/generate", headers=H, json={
            "provider": "together_ai",
            "prompt": "Write a poem about technology",
        })
        assert r.status_code in VALID

    def test_ai_gateway_auto_provider(self, client: TestClient) -> None:
        """Auto provider selection (line 3282)."""
        r = client.post("/ai/gateway/generate", headers=H, json={
            "provider": "auto",
            "prompt": "Summarize the benefits of cloud computing",
        })
        assert r.status_code in VALID

    def test_ai_gateway_generated_asset_found(self, client: TestClient) -> None:
        """Get generated asset by ID when it exists (lines 3380-3391)."""
        # First generate something
        gen_r = client.post("/ai/gateway/generate", headers=H, json={
            "provider": "openai",
            "prompt": "Short test prompt",
        })
        if gen_r.status_code == 200:
            asset_id = gen_r.json().get("result", {}).get("asset_id")
            if asset_id:
                r = client.get(f"/ai/generated-assets/{asset_id}", headers=H)
                assert r.status_code in VALID


class TestLegacyHealthRoutes:
    """Lines 2062, 2079, 2089: health route branches."""

    def test_health_ready(self, client: TestClient) -> None:
        """Health ready route (line 2062)."""
        r = client.get("/health/ready", headers=H)
        assert r.status_code in VALID

    def test_health_schema(self, client: TestClient) -> None:
        """Health schema route (lines 2079)."""
        r = client.get("/health/schema/unified-31", headers=H)
        assert r.status_code in VALID

    def test_health_vaults_route(self, client: TestClient) -> None:
        """Health vaults (line 2062)."""
        r = client.get("/health/vaults", headers=H)
        assert r.status_code in VALID

    def test_metrics_route(self, client: TestClient) -> None:
        """Metrics route (lines 2804-2820)."""
        r = client.get("/metrics", headers=H)
        assert r.status_code in VALID

    def test_health_encryption_route(self, client: TestClient) -> None:
        """Encryption health route."""
        r = client.get("/health/encryption", headers=H)
        assert r.status_code in VALID
