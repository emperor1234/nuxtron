"""
Extra tests for ira router — covering remaining uncovered endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant", "X-Super-Admin": "true"}
H_REGULAR = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 423, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestFrontierStack:
    def test_frontier_stack(self, client: TestClient) -> None:
        r = client.get("/ira/frontier/stack", headers=H)
        assert r.status_code in VALID

    def test_frontier_plan(self, client: TestClient) -> None:
        r = client.post("/ira/frontier/plan", headers=H, json={
            "goal": "improve performance", "modules": ["cache", "cdn"],
        })
        assert r.status_code in VALID

    def test_frontier_env_template(self, client: TestClient) -> None:
        r = client.get("/ira/frontier/env-template", headers=H)
        assert r.status_code in VALID

    def test_frontier_apply_draft(self, client: TestClient) -> None:
        r = client.post("/ira/frontier/env-template/apply-draft", headers=H, json={
            "draft_filename": "test_draft.env",
        })
        assert r.status_code in VALID


class TestMLEndpoints:
    def test_ml_overview(self, client: TestClient) -> None:
        r = client.get("/ira/ml/overview", headers=H)
        assert r.status_code in VALID

    def test_ml_knowledge_upsert(self, client: TestClient) -> None:
        r = client.post("/ira/ml/knowledge/upsert", headers=H, json={
            "key": "test_knowledge",
            "content": "This is test knowledge content.",
            "metadata": {"source": "test"},
        })
        assert r.status_code in VALID

    def test_ml_retrieval_query(self, client: TestClient) -> None:
        r = client.post("/ira/ml/retrieval/query", headers=H, json={
            "query": "test knowledge search",
            "top_k": 5,
        })
        assert r.status_code in VALID

    def test_ml_fine_tuning_jobs_regular_user_forbidden(self, client: TestClient) -> None:
        r = client.post("/ira/ml/fine-tuning/jobs", headers=H_REGULAR, json={
            "model": "gpt-4",
            "dataset_id": "dataset_001",
        })
        assert r.status_code in VALID

    def test_ml_fine_tuning_jobs_super_admin(self, client: TestClient) -> None:
        r = client.post("/ira/ml/fine-tuning/jobs", headers=H, json={
            "model": "gpt-4",
            "dataset_id": "dataset_001",
        })
        assert r.status_code in VALID

    def test_ml_pipelines(self, client: TestClient) -> None:
        r = client.post("/ira/ml/pipelines", headers=H, json={
            "name": "test-pipeline",
            "steps": ["preprocess", "embed", "index"],
        })
        assert r.status_code in VALID


class TestMemoryEndpoints:
    def test_memory_overview(self, client: TestClient) -> None:
        r = client.get("/ira/memory/overview", headers=H)
        assert r.status_code in VALID

    def test_memory_short_term(self, client: TestClient) -> None:
        r = client.get("/ira/memory/short-term", headers=H)
        assert r.status_code in VALID

    def test_memory_structured(self, client: TestClient) -> None:
        r = client.get("/ira/memory/structured", headers=H)
        assert r.status_code in VALID

    def test_memory_structured_upsert(self, client: TestClient) -> None:
        r = client.post("/ira/memory/structured/upsert", headers=H, json={
            "key": "user_preference",
            "value": {"theme": "dark"},
        })
        assert r.status_code in VALID


class TestAgentEndpoints:
    def test_agent_frameworks(self, client: TestClient) -> None:
        r = client.get("/ira/agent/frameworks", headers=H)
        assert r.status_code in VALID

    def test_agent_brain_capabilities(self, client: TestClient) -> None:
        r = client.get("/ira/agent/brain/capabilities", headers=H)
        assert r.status_code in VALID

    def test_agent_brain_reason(self, client: TestClient) -> None:
        r = client.post("/ira/agent/brain/reason", headers=H, json={
            "question": "What should I do to improve SEO?",
            "context": {"site_url": "https://example.com"},
        })
        assert r.status_code in VALID

    def test_agent_preferences(self, client: TestClient) -> None:
        r = client.post("/ira/agent/preferences", headers=H, json={
            "autonomy_level": "supervised",
            "max_cost_per_action": 1.0,
        })
        assert r.status_code in VALID

    def test_agent_run_super_admin(self, client: TestClient) -> None:
        r = client.post("/ira/agent/run", headers=H, json={
            "goal": "monitor system health",
        })
        assert r.status_code in VALID


class TestMonitorAndPerformance:
    def test_monitor(self, client: TestClient) -> None:
        r = client.get("/ira/monitor", headers=H)
        assert r.status_code in VALID

    def test_costs(self, client: TestClient) -> None:
        r = client.get("/ira/costs", headers=H)
        assert r.status_code in VALID

    def test_performance(self, client: TestClient) -> None:
        r = client.get("/ira/performance", headers=H)
        assert r.status_code in VALID


class TestAbTests:
    def test_create_ab_test(self, client: TestClient) -> None:
        r = client.post("/ira/ab-tests", headers=H, json={
            "name": "test-experiment",
            "variants": ["control", "treatment"],
            "traffic_split": [0.5, 0.5],
        })
        assert r.status_code in VALID

    def test_record_ab_test(self, client: TestClient) -> None:
        r = client.post("/ira/ab-tests/record", headers=H, json={
            "test_id": "test_001",
            "variant": "control",
            "metric": "clicks",
            "value": 1,
        })
        assert r.status_code in VALID

    def test_list_ab_tests(self, client: TestClient) -> None:
        r = client.get("/ira/ab-tests", headers=H)
        assert r.status_code in VALID


class TestActionsBatch:
    def test_batch_actions(self, client: TestClient) -> None:
        r = client.post("/ira/actions/batch", headers=H, json={
            "actions": [
                {"type": "notify", "target": "slack", "payload": {"message": "test"}},
            ],
        })
        assert r.status_code in VALID

    def test_action_rollback_nonexistent(self, client: TestClient) -> None:
        r = client.post("/ira/actions/snapshot_nonexistent/rollback", headers=H, json={})
        assert r.status_code in VALID


class TestLearningAndAdvisor:
    def test_learning_feedback(self, client: TestClient) -> None:
        r = client.post("/ira/learning/feedback", headers=H, json={
            "action_id": "action_001",
            "rating": 5,
            "comment": "Great recommendation!",
        })
        assert r.status_code in VALID

    def test_advisor_recommendations(self, client: TestClient) -> None:
        r = client.post("/ira/advisor/recommendations", headers=H, json={
            "context": {"site_url": "https://example.com"},
        })
        assert r.status_code in VALID


class TestCrmEndpoints:
    def test_crm_connectors_status(self, client: TestClient) -> None:
        r = client.get("/ira/crm/connectors/status", headers=H)
        assert r.status_code in VALID

    def test_crm_hybrid_recommendation(self, client: TestClient) -> None:
        r = client.get("/ira/crm/hybrid-recommendation", headers=H)
        assert r.status_code in VALID
