from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "X-API-Key": os.environ.get("FASTAPI_API_KEY", "test-api-key"),
    }


def test_ai_crawler_visibility_dashboard_flow(client: TestClient) -> None:
    tenant_id = "tenant-visibility-dashboard"
    headers = _headers(tenant_id)

    register = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "example.com",
            "display_name": "Example",
            "cms_type": "custom",
            "js_framework": "react",
        },
    )
    assert register.status_code == 201, register.text
    site_id = register.json()["site"]["id"]

    ingest = client.post(
        "/ai-crawler/events",
        headers=headers,
        json={
            "site_id": site_id,
            "crawler_name": "GPTBot",
            "page_url": "https://example.com/pricing",
            "user_agent": "GPTBot/1.0",
            "status_code": 200,
            "response_type": "ssr",
            "render_time_ms": 130,
        },
    )
    assert ingest.status_code == 201, ingest.text

    dashboard = client.get("/ai-crawler/dashboard?window_hours=24", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert payload["status"] == "ok"
    assert payload["summary"]["total_hits"] >= 1
    assert payload["summary"]["ai_crawler_hits"] >= 1
    assert isinstance(payload["top_crawlers"], list)

    sites = client.get("/ai-crawler/sites", headers=headers)
    assert sites.status_code == 200, sites.text
    sites_payload = sites.json()
    assert sites_payload["status"] == "ok"
    assert sites_payload["count"] >= 1


def test_ai_crawler_bulk_snippet_deploy_and_readiness(client: TestClient) -> None:
    tenant_id = "tenant-visibility-automation"
    headers = _headers(tenant_id)

    site_one = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "alpha.example.com",
            "display_name": "Alpha",
            "cms_type": "custom",
            "js_framework": "react",
        },
    )
    assert site_one.status_code == 201, site_one.text
    site_one_id = site_one.json()["site"]["id"]

    site_two = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "beta.example.com",
            "display_name": "Beta",
            "cms_type": "custom",
            "js_framework": "next",
            "deployment_webhook_url": "https://example.com/deploy-snippet",
        },
    )
    assert site_two.status_code == 201, site_two.text
    site_two_id = site_two.json()["site"]["id"]

    dry_plan = client.post(
        "/ai-crawler/snippets/deploy-bulk",
        headers=headers,
        json={
            "site_ids": [site_one_id, site_two_id],
            "dry_run": True,
        },
    )
    assert dry_plan.status_code == 200, dry_plan.text
    dry_plan_payload = dry_plan.json()
    assert dry_plan_payload["status"] == "ok"
    assert dry_plan_payload["summary"]["sites_targeted"] == 2
    assert dry_plan_payload["summary"]["planned"] == 2

    readiness = client.get("/ai-crawler/readiness", headers=headers)
    assert readiness.status_code == 200, readiness.text
    readiness_payload = readiness.json()
    assert readiness_payload["status"] == "ok"
    assert "grade" in readiness_payload["readiness"]
    assert readiness_payload["readiness"]["total_sites"] >= 2


def test_ai_crawler_cloudflare_auto_sync_dry_run(client: TestClient) -> None:
    tenant_id = "tenant-cloudflare-auto-sync"
    headers = _headers(tenant_id)

    register = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "gamma.example.com",
            "display_name": "Gamma",
            "cms_type": "custom",
            "js_framework": "vue",
            "cloudflare_zone_id": "zone-12345",
        },
    )
    assert register.status_code == 201, register.text

    auto_sync = client.post(
        "/ai-crawler/cloudflare/auto-sync",
        headers=headers,
        json={
            "action": "allow_ai_crawlers",
            "dry_run": True,
        },
    )
    assert auto_sync.status_code == 200, auto_sync.text
    payload = auto_sync.json()
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert payload["sites_targeted"] >= 1
    assert isinstance(payload["results"], list)


def test_ai_crawler_automation_run_dry_run_with_vendor_matrix(client: TestClient) -> None:
    tenant_id = "tenant-automation-e2e"
    headers = _headers(tenant_id)

    register = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "automation.example.com",
            "display_name": "Automation",
            "cms_type": "custom",
            "js_framework": "next",
            "deployment_webhook_url": "https://example.com/deploy",
            "cloudflare_zone_id": "zone-automation-1",
        },
    )
    assert register.status_code == 201, register.text
    site_id = register.json()["site"]["id"]

    automation = client.post(
        "/ai-crawler/automation/run",
        headers=headers,
        json={
            "site_id": site_id,
            "page_url": "https://automation.example.com/pricing",
            "dry_run": True,
            "deploy_snippet": True,
            "verify_snippet": True,
            "sync_cloudflare": True,
            "run_visibility_audit": True,
        },
    )
    assert automation.status_code == 200, automation.text
    payload = automation.json()
    assert payload["status"] == "ok"
    assert payload["summary"]["total_steps"] == 4
    assert payload["summary"]["planned"] == 4
    assert payload["summary"]["completed"] == 0
    assert isinstance(payload["vendors"], list)
    assert any(v.get("vendor") == "Cloudflare" for v in payload["vendors"])
    assert any(step.get("step") == "visibility_audit" for step in payload["steps"])

    vendors = client.get(f"/ai-crawler/vendors?site_id={site_id}", headers=headers)
    assert vendors.status_code == 200, vendors.text
    vendors_payload = vendors.json()
    assert vendors_payload["status"] == "ok"
    assert vendors_payload["site_id"] == site_id
    assert isinstance(vendors_payload["vendors"], list)
    assert any(v.get("integration") == "deployment_webhook" for v in vendors_payload["vendors"])
    assert isinstance(vendors_payload.get("vendor_chart"), list)
    assert vendors_payload.get("summary", {}).get("sites") == 1
    assert vendors_payload.get("summary", {}).get("vendors", 0) >= 1


def test_ai_crawler_vendors_chart_across_sites(client: TestClient) -> None:
    tenant_id = "tenant-vendor-chart"
    headers = _headers(tenant_id)

    one = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "chart-one.example.com",
            "display_name": "Chart One",
            "cms_type": "custom",
            "js_framework": "next",
            "deployment_webhook_url": "https://example.com/deploy-one",
            "cloudflare_zone_id": "zone-chart-1",
        },
    )
    assert one.status_code == 201, one.text

    two = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "chart-two.example.com",
            "display_name": "Chart Two",
            "cms_type": "custom",
            "js_framework": "react",
        },
    )
    assert two.status_code == 201, two.text

    vendors = client.get("/ai-crawler/vendors", headers=headers)
    assert vendors.status_code == 200, vendors.text
    payload = vendors.json()
    assert payload["status"] == "ok"
    assert payload.get("summary", {}).get("sites") == 2
    assert payload.get("summary", {}).get("vendors", 0) >= 1
    assert isinstance(payload.get("vendor_chart"), list)
    assert any(v.get("vendor") == "Cloudflare" for v in payload.get("vendor_chart", []))
    assert any(v.get("sites_using", 0) >= 2 for v in payload.get("vendor_chart", []))


def test_ai_crawler_automation_schedule_execute_and_history(client: TestClient) -> None:
    tenant_id = "tenant-automation-scheduler"
    headers = _headers(tenant_id)

    register = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "schedule.example.com",
            "display_name": "Schedule",
            "cms_type": "custom",
            "js_framework": "next",
        },
    )
    assert register.status_code == 201, register.text
    site_id = register.json()["site"]["id"]

    schedule_create = client.post(
        "/ai-crawler/automation/schedules",
        headers=headers,
        json={
            "site_id": site_id,
            "page_url": "https://schedule.example.com/pricing",
            "interval_minutes": 30,
            "deploy_snippet": True,
            "verify_snippet": True,
            "sync_cloudflare": True,
            "run_visibility_audit": True,
            "enabled": True,
        },
    )
    assert schedule_create.status_code == 201, schedule_create.text
    schedule_id = schedule_create.json()["schedule"]["id"]

    list_schedules = client.get("/ai-crawler/automation/schedules", headers=headers)
    assert list_schedules.status_code == 200, list_schedules.text
    schedules_payload = list_schedules.json()
    assert schedules_payload["count"] >= 1
    assert any(s.get("id") == schedule_id for s in schedules_payload["schedules"])

    run_due = client.post(
        "/ai-crawler/automation/schedules/execute",
        headers=headers,
        json={"due_only": True, "dry_run": True, "max_schedules": 10},
    )
    assert run_due.status_code == 200, run_due.text
    run_payload = run_due.json()
    assert run_payload["status"] == "ok"
    assert run_payload["summary"]["runs_created"] >= 1
    assert any(r.get("trigger") == "schedule_executor" for r in run_payload["runs"])

    history = client.get(f"/ai-crawler/automation/history?site_id={site_id}", headers=headers)
    assert history.status_code == 200, history.text
    history_payload = history.json()
    assert history_payload["count"] >= 1
    assert any(h.get("site_id") == site_id for h in history_payload["history"])


def test_ai_crawler_automation_schedule_update_and_delete(client: TestClient) -> None:
    tenant_id = "tenant-automation-scheduler-mutation"
    headers = _headers(tenant_id)

    register = client.post(
        "/ai-crawler/sites",
        headers=headers,
        json={
            "domain": "schedule-edit.example.com",
            "display_name": "Schedule Edit",
            "cms_type": "custom",
            "js_framework": "react",
        },
    )
    assert register.status_code == 201, register.text
    site_id = register.json()["site"]["id"]

    created = client.post(
        "/ai-crawler/automation/schedules",
        headers=headers,
        json={
            "site_id": site_id,
            "page_url": "https://schedule-edit.example.com/features",
            "interval_minutes": 120,
        },
    )
    assert created.status_code == 201, created.text
    schedule_id = created.json()["schedule"]["id"]

    updated = client.patch(
        f"/ai-crawler/automation/schedules/{schedule_id}",
        headers=headers,
        json={
            "enabled": False,
            "interval_minutes": 240,
            "run_visibility_audit": False,
        },
    )
    assert updated.status_code == 200, updated.text
    updated_payload = updated.json()["schedule"]
    assert updated_payload["enabled"] is False
    assert updated_payload["interval_minutes"] == 240
    assert updated_payload["run_visibility_audit"] is False

    deleted = client.delete(f"/ai-crawler/automation/schedules/{schedule_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["removed"] is True
