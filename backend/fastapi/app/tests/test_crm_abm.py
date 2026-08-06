"""CRM ABM tests: target accounts, committee, engagement events, and reports."""

# pyright: reportMissingImports=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_create_target_account(client: TestClient) -> None:
    r = client.post(
        "/crm/abm/target-accounts",
        headers=H,
        json={
            "name": "Acme Strategic",
            "owner": "revops@example.com",
            "tier": "tier_1",
            "icp_fit_score": 82,
            "intent_score": 76,
            "tags": ["enterprise", "abm"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("target_account", {}).get("id", 0) >= 1


def test_list_target_accounts(client: TestClient) -> None:
    r = client.get("/crm/abm/target-accounts", headers=H)
    assert r.status_code == 200
    assert isinstance(r.json().get("target_accounts"), list)


def test_committee_and_event_flow(client: TestClient) -> None:
    created = client.post(
        "/crm/abm/target-accounts",
        headers=H,
        json={"name": "Globex Expansion", "tier": "tier_2", "icp_fit_score": 70, "intent_score": 64},
    )
    assert created.status_code == 200
    account_id = int(created.json()["target_account"]["id"])

    member = client.post(
        f"/crm/abm/target-accounts/{account_id}/committee",
        headers=H,
        json={
            "name": "Pat Morgan",
            "role": "decision_maker",
            "influence_score": 90,
            "buying_power_score": 88,
            "engagement_level": "high",
        },
    )
    assert member.status_code == 200

    event = client.post(
        f"/crm/abm/target-accounts/{account_id}/engagement-events",
        headers=H,
        json={"channel": "meeting", "event_type": "discovery_call", "weight": 35, "actor": "sdr-02"},
    )
    assert event.status_code == 200

    committee = client.get(f"/crm/abm/target-accounts/{account_id}/committee", headers=H)
    timeline = client.get(f"/crm/abm/target-accounts/{account_id}/engagement-timeline", headers=H)
    score = client.get(f"/crm/abm/target-accounts/{account_id}/score", headers=H)

    assert committee.status_code == 200
    assert timeline.status_code == 200
    assert score.status_code == 200
    assert isinstance(score.json().get("score", {}).get("composite_score"), (int, float))


def test_abm_report(client: TestClient) -> None:
    r = client.get("/crm/reports/abm", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "top_accounts" in data
