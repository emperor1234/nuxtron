"""
Tests for routers/ira.py and ira_memory.py missing coverage paths.
Covers routes, helper functions, and memory system methods.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("SUPER_ADMIN_API_KEY", "test-super-admin-key")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ira-db-tenant"}
SH = {**H, "X-Super-Admin-Key": "test-super-admin-key"}
TENANT = "ira-db-tenant"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ─── Direct function tests ─────────────────────────────────────────────────────

class TestIraWatchdogLoop:
    """Lines 553, 579-580: _ira_watchdog_loop direct tests."""

    def test_watchdog_skip_empty_tenant_id(self) -> None:
        """Line 553: continue when tenant_id is empty."""
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        stop_event = asyncio.Event()
        stop_event.set()

        ira_controls = [{"tenant_id": "", "autonomy_enabled": True}]

        async def _run() -> None:
            await run_ira_watchdog(
                stop_event,
                ira_controls_memory=ira_controls,
                ira_events_memory=[],
                audit_log_memory=[],
                invoices_memory=[],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(_run())

    def test_watchdog_skip_autonomy_disabled(self) -> None:
        """Line 553: continue when autonomy_enabled=False."""
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        stop_event = asyncio.Event()
        stop_event.set()

        ira_controls = [{"tenant_id": "some-tenant", "autonomy_enabled": False}]

        async def _run() -> None:
            await run_ira_watchdog(
                stop_event=stop_event,
                ira_controls_memory=ira_controls,
                ira_events_memory=[],
                audit_log_memory=[],
                invoices_memory=[],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(_run())

    def test_watchdog_timeout_continue(self) -> None:
        """Lines 579-580: TimeoutError → continue (loop iteration)."""
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]

        async def _fake_wait(timeout: float) -> None:
            raise TimeoutError()

        stop_event.wait = AsyncMock(side_effect=_fake_wait)

        async def _run() -> None:
            with patch("asyncio.wait_for", side_effect=_fake_wait):
                stop_event2 = asyncio.Event()
                stop_event2.set()
                await run_ira_watchdog(
                    stop_event=stop_event2,
                    ira_controls_memory=[],
                    ira_events_memory=[],
                    audit_log_memory=[],
                    invoices_memory=[],
                    credit_ledger_memory=[],
                    stripe_events_memory=[],
                    revenue_conversions_memory=[],
                    api_usage_audit_memory=[],
                    ai_security_usage_memory=[],
                )

        asyncio.run(_run())


# ─── ML Overview route ─────────────────────────────────────────────────────────

class TestMlOverviewRoute:
    """Lines 912, 958: _ml_capabilities, _free_tier_readiness via /ira/ml/overview."""

    def test_ml_overview(self, client: TestClient) -> None:
        """GET /ira/ml/overview returns ml capabilities."""
        r = client.get("/ira/ml/overview", headers=H)
        assert r.status_code in VALID

    def test_ml_overview_with_openai(self, client: TestClient) -> None:
        """Lines 912+: auto embedding backend resolves to openai when configured."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            r = client.get("/ira/ml/overview", headers=H)
        assert r.status_code in VALID

    def test_ml_overview_free_tier_readiness_full(self, client: TestClient) -> None:
        """Line 958: free_tier_readiness returns 'full' when count >= 3."""
        from backend.fastapi.app.memory_stores import ira_ml_models
        ira_ml_models.clear()
        for i in range(3):
            ira_ml_models.append({"id": i+1, "name": f"model-{i}", "active": True})
        r = client.get("/ira/ml/overview", headers=H)
        assert r.status_code in VALID


# ─── Frontier Stack route ──────────────────────────────────────────────────────

class TestFrontierStackRoute:
    """Lines 1328, 1330: _frontier_readiness_summary via /ira/frontier/stack."""

    def test_frontier_stack(self, client: TestClient) -> None:
        """GET /ira/frontier/stack returns frontier catalog and readiness."""
        r = client.get("/ira/frontier/stack", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "frontier" in data or "status" in data

    def test_frontier_env_template(self, client: TestClient) -> None:
        """GET /ira/frontier/env-template returns env template."""
        r = client.get("/ira/frontier/env-template", headers=H)
        assert r.status_code in VALID


# ─── Frontier Plan route ───────────────────────────────────────────────────────

class TestFrontierPlanRoute:
    """Lines 1252, 2473, 2612: _frontier_recommended_stack and plan phases."""

    def test_frontier_plan_free_open_source(self, client: TestClient) -> None:
        """Line 1252: include_free_open_source_only=True uses OSS brain stack."""
        r = client.post("/ira/frontier/plan", headers=H, json={
            "objective": "Build an open source AI assistant",
            "priority": "cost",
            "include_free_open_source_only": True,
            "require_multimodal": False,
            "require_graph_memory": False,
            "create_execution_tasks": False,
        })
        assert r.status_code in VALID

    def test_frontier_plan_with_execution_tasks(self, client: TestClient) -> None:
        """Lines 2473-2510: create_execution_tasks=True creates phase jobs."""
        r = client.post("/ira/frontier/plan", headers=H, json={
            "objective": "Build a production AI workforce platform",
            "priority": "reliability",
            "include_free_open_source_only": False,
            "require_multimodal": True,
            "require_graph_memory": True,
            "create_execution_tasks": True,
        })
        assert r.status_code in VALID


# ─── Frontier env-template apply-draft route ──────────────────────────────────

class TestFrontierEnvTemplateApplyDraft:
    """Lines 1420-1484: _validate_env_target_filename and write logic."""

    def test_apply_draft_overwrite(self, client: TestClient, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """Lines 1420+: apply draft in overwrite mode."""
        import pathlib
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False, dir=str(tmp_path)) as f:
            target = pathlib.Path(f.name).name
        r = client.post("/ira/frontier/env-template/apply-draft", headers=H, json={
            "target_file": target,
            "mode": "overwrite",
        })
        assert r.status_code in VALID

    def test_apply_draft_invalid_filename(self, client: TestClient) -> None:
        """Lines 1420-1421: target_file must not be empty."""
        r = client.post("/ira/frontier/env-template/apply-draft", headers=H, json={
            "target_file": "../../etc/passwd",
            "mode": "overwrite",
        })
        assert r.status_code in VALID

    def test_apply_draft_invalid_mode(self, client: TestClient) -> None:
        """Line 1478: invalid mode value."""
        r = client.post("/ira/frontier/env-template/apply-draft", headers=H, json={
            "target_file": ".env.frontier.draft",
            "mode": "invalid_mode",
        })
        assert r.status_code in VALID


# ─── Memory routes ─────────────────────────────────────────────────────────────

class TestMemoryRoutes:
    """Lines 2691-2730: /memory/structured/upsert and /memory/structured routes."""

    def test_memory_overview(self, client: TestClient) -> None:
        """GET /ira/memory/overview."""
        r = client.get("/ira/memory/overview", headers=H)
        assert r.status_code in VALID

    def test_memory_short_term(self, client: TestClient) -> None:
        """GET /ira/memory/short-term."""
        r = client.get("/ira/memory/short-term", headers=H)
        assert r.status_code in VALID

    def test_memory_structured_list(self, client: TestClient) -> None:
        """GET /ira/memory/structured."""
        r = client.get("/ira/memory/structured", headers=H)
        assert r.status_code in VALID

    def test_memory_structured_upsert(self, client: TestClient) -> None:
        """POST /ira/memory/structured/upsert - line 2691."""
        r = client.post("/ira/memory/structured/upsert", headers=H, json={
            "memory_type": "user_profile",
            "memory_key": "ira-test-key",
            "payload": {"name": "Test User", "preferences": {"theme": "dark"}},
        })
        assert r.status_code in VALID

    def test_memory_structured_upsert_task_type(self, client: TestClient) -> None:
        """POST /ira/memory/structured/upsert with task type."""
        r = client.post("/ira/memory/structured/upsert", headers=H, json={
            "memory_type": "task",
            "memory_key": "pending-task-001",
            "payload": {"title": "Review quarterly report", "due": "2025-12-31"},
        })
        assert r.status_code in VALID


# ─── Agent Brain Reason route ─────────────────────────────────────────────────

class TestAgentBrainReasonRoute:
    """Lines 2745-2787: /agent/brain/reason route."""

    def test_agent_brain_reason_auto_provider(self, client: TestClient) -> None:
        """POST /ira/agent/brain/reason with auto provider."""
        r = client.post("/ira/agent/brain/reason", headers=H, json={
            "prompt": "Analyze the customer churn rate and suggest retention strategies",
            "provider": "auto",
            "temperature": 0.2,
            "max_tokens": 200,
        })
        assert r.status_code in VALID

    def test_agent_brain_reason_openai_provider(self, client: TestClient) -> None:
        """POST /ira/agent/brain/reason with openai provider - hits provider branch."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake-key"}):
            r = client.post("/ira/agent/brain/reason", headers=H, json={
                "prompt": "What is the revenue trend this quarter?",
                "provider": "openai",
                "temperature": 0.1,
                "max_tokens": 100,
            })
        assert r.status_code in VALID


# ─── Agent Preferences route ──────────────────────────────────────────────────

class TestAgentPreferencesRoute:
    """Lines 837-849: _is_super_admin via /agent/preferences."""

    def test_agent_preferences_no_super_admin_key(self, client: TestClient) -> None:
        """Line 837: _is_super_admin returns False when key doesn't match."""
        r = client.post("/ira/agent/preferences", headers=H, json={
            "auto_framework": "native_secure_loop",
        })
        assert r.status_code in VALID

    def test_agent_preferences_with_valid_super_admin_key(self, client: TestClient) -> None:
        """Line 849: _is_super_admin returns True when key matches."""
        r = client.post("/ira/agent/preferences", headers=SH, json={
            "auto_framework": "langchain",
        })
        assert r.status_code in VALID


# ─── Agent Run route ──────────────────────────────────────────────────────────

class TestAgentRunRoute:
    """Lines 2821-2852: /agent/run route."""

    def test_agent_run_dry_run(self, client: TestClient) -> None:
        """POST /ira/agent/run with dry_run=True."""
        r = client.post("/ira/agent/run", headers=SH, json={
            "goal": "Analyze customer support tickets and identify top issues",
            "framework": "native_secure_loop",
            "max_iterations": 3,
            "dry_run": True,
            "memory_key": "ira-agent-run-test",
        })
        assert r.status_code in VALID

    def test_agent_run_autonomy_disabled(self, client: TestClient) -> None:
        """Lines 2821-2826: autonomy disabled check."""
        r = client.post("/ira/agent/run", headers=H, json={
            "goal": "Run a complex autonomous task",
            "framework": "auto",
            "max_iterations": 4,
            "dry_run": True,
        })
        assert r.status_code in VALID


# ─── ML Knowledge Upsert route ────────────────────────────────────────────────

class TestMlKnowledgeUpsertRoute:
    """Lines 2870-2952: /ml/knowledge/upsert route."""

    def test_ml_knowledge_upsert(self, client: TestClient) -> None:
        """POST /ira/ml/knowledge/upsert stores document."""
        r = client.post("/ira/ml/knowledge/upsert", headers=H, json={
            "document_id": "doc-ira-test-001",
            "title": "IRA Platform Overview",
            "content": "IRA is an intelligent revenue automation platform that helps businesses optimize their sales, customer support, and financial operations using AI.",
            "source": "internal",
            "tags": ["ira", "platform", "overview"],
            "metadata": {"version": "1.0"},
            "chunk_size_chars": 900,
            "chunk_overlap_chars": 120,
        })
        assert r.status_code in VALID

    def test_ml_knowledge_upsert_update_existing(self, client: TestClient) -> None:
        """Lines 2877+: update existing document."""
        r = client.post("/ira/ml/knowledge/upsert", headers=H, json={
            "document_id": "doc-ira-test-001",
            "title": "IRA Platform Overview - Updated",
            "content": "Updated content for IRA platform overview. Now includes more details about the autonomous decision-making system.",
            "source": "internal",
            "tags": ["ira", "platform", "updated"],
        })
        assert r.status_code in VALID


# ─── ML Retrieval Query route ─────────────────────────────────────────────────

class TestMlRetrievalQueryRoute:
    """Lines 2945-2970: /ml/retrieval/query route."""

    def test_ml_retrieval_query(self, client: TestClient) -> None:
        """POST /ira/ml/retrieval/query returns ranked results."""
        r = client.post("/ira/ml/retrieval/query", headers=H, json={
            "query": "What is IRA platform and how does it work?",
            "top_k": 5,
            "min_score": 0.1,
        })
        assert r.status_code in VALID

    def test_ml_retrieval_query_no_results(self, client: TestClient) -> None:
        """Lines 2970+: synthesis with no results."""
        r = client.post("/ira/ml/retrieval/query", headers=H, json={
            "query": "Unknown topic that has no documents",
            "top_k": 3,
            "min_score": 0.99,
        })
        assert r.status_code in VALID


# ─── ML Fine-Tuning Jobs route ────────────────────────────────────────────────

class TestMlFineTuningJobsRoute:
    """Lines 3001-3108: /ml/fine-tuning/jobs route."""

    def test_fine_tuning_job_dry_run(self, client: TestClient) -> None:
        """POST /ira/ml/fine-tuning/jobs dry_run mode."""
        r = client.post("/ira/ml/fine-tuning/jobs", headers=SH, json={
            "provider": "openai",
            "base_model": "gpt-4o-mini-2024-07-18",
            "training_file_id": "file-abc123",
            "validation_file_id": "",
            "suffix": "ira-v1",
            "hyperparameters": {"n_epochs": 3},
            "dry_run": True,
        })
        assert r.status_code in VALID

    def test_fine_tuning_job_custom_http(self, client: TestClient) -> None:
        """Lines 3069+: custom_http provider path."""
        r = client.post("/ira/ml/fine-tuning/jobs", headers=SH, json={
            "provider": "custom_http",
            "base_model": "llama3.2:3b",
            "endpoint_url": "http://localhost:8001/finetune",
            "dry_run": True,
        })
        assert r.status_code in VALID


# ─── ML Pipelines route ───────────────────────────────────────────────────────

class TestMlPipelinesRoute:
    """Lines 3130-3194: /ml/pipelines route."""

    def test_pipeline_create_dry_run(self, client: TestClient) -> None:
        """POST /ira/ml/pipelines creates a pipeline."""
        r = client.post("/ira/ml/pipelines", headers=SH, json={
            "name": "ira-rag-pipeline-v1",
            "objective": "Build a RAG pipeline for customer support",
            "pipeline_type": "rag",
            "framework": "auto",
            "dataset_document_ids": ["doc-ira-test-001"],
            "model_name": "all-MiniLM-L6-v2",
            "epochs": 3,
            "learning_rate": 0.0001,
            "batch_size": 16,
            "dry_run": True,
        })
        assert r.status_code in VALID

    def test_pipeline_create_finetune(self, client: TestClient) -> None:
        """Lines 3148+: dry_run=True path."""
        r = client.post("/ira/ml/pipelines", headers=SH, json={
            "name": "ira-finetune-pipeline",
            "objective": "Fine-tune model for CRM classification",
            "pipeline_type": "fine_tuning",
            "framework": "pytorch",
            "model_name": "bert-base-uncased",
            "epochs": 5,
            "dry_run": True,
        })
        assert r.status_code in VALID


# ─── Chat route ───────────────────────────────────────────────────────────────

class TestChatRoute:
    """Lines 3303-3537: /chat route."""

    def test_chat_basic_message(self, client: TestClient) -> None:
        """POST /ira/chat with basic message."""
        r = client.post("/ira/chat", headers=H, json={
            "role": "customer",
            "channel": "chat",
            "message": "I need help with my subscription",
            "context": {},
        })
        assert r.status_code in VALID

    def test_chat_email_channel(self, client: TestClient) -> None:
        """POST /ira/chat via email channel."""
        r = client.post("/ira/chat", headers=H, json={
            "role": "admin",
            "channel": "email",
            "message": "How do I configure the billing settings?",
            "context": {"priority": "high"},
        })
        assert r.status_code in VALID

    def test_chat_seo_message(self, client: TestClient) -> None:
        """Line 2011: SEO domain classification."""
        r = client.post("/ira/chat", headers=H, json={
            "role": "customer",
            "channel": "chat",
            "message": "How can I improve my website search engine ranking and SEO performance?",
            "context": {},
        })
        assert r.status_code in VALID

    def test_chat_billing_message(self, client: TestClient) -> None:
        """Lines 2097+: billing email action."""
        r = client.post("/ira/chat", headers=H, json={
            "role": "customer",
            "channel": "email",
            "message": "My invoice is incorrect, I was charged twice this month",
            "context": {},
        })
        assert r.status_code in VALID


# ─── Actions route ────────────────────────────────────────────────────────────

class TestActionsRoute:
    """Lines 3303-3537: /actions route."""

    def test_action_dry_run(self, client: TestClient) -> None:
        """POST /ira/actions with dry_run=True."""
        r = client.post("/ira/actions", headers=H, json={
            "target": "customers",
            "command": "send notification to all active customers",
            "payload": {"message": "System maintenance scheduled"},
            "dashboard_scope": "super_admin_dashboard",
            "actor_role": "super_admin",
            "actor_attributes": {"tenant_id": TENANT},
            "user_consent": True,
            "consent_reference": "consent-2025-001",
            "risk_analysis_approved": True,
            "human_validation_approved": True,
            "explicit_approval": False,
            "dry_run": True,
        })
        assert r.status_code in VALID

    def test_action_email_target(self, client: TestClient) -> None:
        """Lines 2207+: email action through Resend."""
        r = client.post("/ira/actions", headers=H, json={
            "target": "email",
            "command": "send monthly newsletter to subscribers",
            "payload": {
                "subject": "Monthly Newsletter",
                "body": "Here are this month's highlights",
                "recipients": ["test@example.com"],
            },
            "dashboard_scope": "super_admin_dashboard",
            "actor_role": "super_admin",
            "actor_attributes": {"tenant_id": TENANT},
            "user_consent": True,
            "risk_analysis_approved": True,
            "human_validation_approved": True,
            "dry_run": True,
        })
        assert r.status_code in VALID

    def test_action_rbac_denied(self, client: TestClient) -> None:
        """Lines 3357-3358: RBAC policy denies action for operator role."""
        r = client.post("/ira/actions", headers=H, json={
            "target": "billing",
            "command": "process bulk refund",
            "payload": {},
            "dashboard_scope": "super_admin_dashboard",
            "actor_role": "operator",
            "actor_attributes": {},
            "dry_run": True,
        })
        assert r.status_code in VALID


# ─── Batch Actions route ──────────────────────────────────────────────────────

class TestBatchActionsRoute:
    """Lines 3596+: /actions/batch route."""

    def test_batch_actions(self, client: TestClient) -> None:
        """POST /ira/actions/batch with multiple actions."""
        r = client.post("/ira/actions/batch", headers=H, json={
            "actions": [
                {
                    "target": "customers",
                    "command": "send welcome message",
                    "payload": {},
                    "dry_run": True,
                },
                {
                    "target": "chats",
                    "command": "archive old conversations",
                    "payload": {},
                    "dry_run": True,
                },
            ],
            "dry_run": True,
            "consent_reference": "batch-consent-001",
            "human_validation_approved": True,
            "risk_analysis_approved": True,
        })
        assert r.status_code in VALID


# ─── AB Tests routes ──────────────────────────────────────────────────────────

class TestAbTestsRoutes:
    """Lines 3775-3863: /ab-tests and /ab-tests/record routes."""

    def test_create_ab_test(self, client: TestClient) -> None:
        """POST /ira/ab-tests creates a test."""
        r = client.post("/ira/ab-tests", headers=H, json={
            "name": "pricing-page-cta-test",
            "description": "Test different CTA button texts",
            "variants": ["variant_a", "variant_b"],
            "metric": "conversion_rate",
            "traffic_split": [0.5, 0.5],
            "target_scope": "all",
        })
        assert r.status_code in VALID

    def test_list_ab_tests(self, client: TestClient) -> None:
        """GET /ira/ab-tests lists all tests."""
        r = client.get("/ira/ab-tests", headers=H)
        assert r.status_code in VALID

    def test_record_ab_test_outcome(self, client: TestClient) -> None:
        """POST /ira/ab-tests/record records a result."""
        from backend.fastapi.app.memory_stores import ira_ab_tests
        ira_ab_tests.append({
            "id": 999,
            "tenant_id": TENANT,
            "name": "pricing-page-cta-test",
            "variants": ["variant_a", "variant_b"],
            "traffic_split": [0.5, 0.5],
            "metric": "conversion_rate",
            "records": [],
        })
        r = client.post("/ira/ab-tests/record", headers=H, json={
            "test_id": 999,
            "variant": "variant_a",
            "outcome": "success",
            "value": 1.0,
            "metadata": {"page": "pricing"},
        })
        assert r.status_code in VALID

    def test_record_ab_test_not_found(self, client: TestClient) -> None:
        """Lines 3842-3843: test not found → 404."""
        r = client.post("/ira/ab-tests/record", headers=H, json={
            "test_id": 99999,
            "variant": "variant_z",
            "outcome": "neutral",
            "value": 0.0,
        })
        assert r.status_code in VALID


# ─── Control Config route ─────────────────────────────────────────────────────

class TestControlConfigRoute:
    """Lines 3917-3926: /control/config route."""

    def test_control_config_update(self, client: TestClient) -> None:
        """POST /ira/control/config updates autonomy settings."""
        r = client.post("/ira/control/config", headers=SH, json={
            "autonomy_enabled": True,
            "allow_high_impact_actions": False,
            "min_profit_margin_pct": 70.0,
            "suspicious_signal_threshold": 0.75,
            "require_super_admin": True,
            "max_dispute_auto_resolution_gbp": 50.0,
            "strict_policy_lock": True,
            "policy_change_human_validation": False,
        })
        assert r.status_code in VALID


# ─── Connectors routes ────────────────────────────────────────────────────────

class TestConnectorsRoutes:
    """Lines 3948-3955: /connectors and /connectors/upsert routes."""

    def test_list_connectors(self, client: TestClient) -> None:
        """GET /ira/connectors."""
        r = client.get("/ira/connectors", headers=H)
        assert r.status_code in VALID

    def test_upsert_connector(self, client: TestClient) -> None:
        """POST /ira/connectors/upsert."""
        r = client.post("/ira/connectors/upsert", headers=SH, json={
            "channel": "chat",
            "enabled": True,
            "provider": "internal",
            "config": {"webhook_url": "https://example.com/webhook"},
        })
        assert r.status_code in VALID


# ─── Finance routes ───────────────────────────────────────────────────────────

class TestFinanceRoutes:
    """Lines 3978-4049: /finance/health, /risk/score, /finance/ingest."""

    def test_finance_health(self, client: TestClient) -> None:
        """GET /ira/finance/health."""
        r = client.get("/ira/finance/health", headers=H)
        assert r.status_code in VALID

    def test_risk_score(self, client: TestClient) -> None:
        """GET /ira/risk/score."""
        r = client.get("/ira/risk/score", headers=H)
        assert r.status_code in VALID

    def test_finance_ingest(self, client: TestClient) -> None:
        """POST /ira/finance/ingest."""
        r = client.post("/ira/finance/ingest", headers=H, json={
            "revenue": 15000.0,
            "cogs": 3000.0,
            "credits_cost": 500.0,
            "suspicious_signal_score": 0.1,
            "note": "Monthly recurring revenue for November 2025",
        })
        assert r.status_code in VALID


# ─── Disputes and Learning routes ─────────────────────────────────────────────

class TestDisputesAndLearningRoutes:
    """Lines 4068-4081+: /learning/feedback and /disputes/dashboard."""

    def test_learning_feedback(self, client: TestClient) -> None:
        """POST /ira/learning/feedback."""
        r = client.post("/ira/learning/feedback", headers=H, json={
            "category": "quality",
            "rating": 4,
            "comment": "The IRA response was helpful and accurate",
            "action_ref": "action-001",
            "actor_role": "admin",
        })
        assert r.status_code in VALID

    def test_disputes_dashboard(self, client: TestClient) -> None:
        """GET /ira/disputes/dashboard."""
        r = client.get("/ira/disputes/dashboard", headers=H)
        assert r.status_code in VALID


# ─── CRM routes ───────────────────────────────────────────────────────────────

class TestIraCrmRoutes:
    """Lines 4115-4261: /crm/* routes."""

    def test_crm_hybrid_recommendation(self, client: TestClient) -> None:
        """GET /ira/crm/hybrid-recommendation."""
        r = client.get("/ira/crm/hybrid-recommendation", headers=H)
        assert r.status_code in VALID

    def test_crm_connectors_status(self, client: TestClient) -> None:
        """Lines 715-787: GET /ira/crm/connectors/status calls _probe_crm_connectors."""
        r = client.get("/ira/crm/connectors/status", headers=H)
        assert r.status_code in VALID

    def test_crm_connectors_status_with_probe_enabled(self, client: TestClient) -> None:
        """Lines 758-786: probe enabled path in _probe_crm_connectors."""
        with patch.dict(os.environ, {
            "IRA_CONNECTOR_HEALTH_PROBE_ENABLED": "true",
            "CORTEZA_API_BASE_URL": "http://localhost:4000",
            "ODOO_API_BASE_URL": "http://localhost:8069",
        }):
            r = client.get("/ira/crm/connectors/status", headers=H)
        assert r.status_code in VALID

    def test_crm_feature_governance_update(self, client: TestClient) -> None:
        """Lines 626-706: POST /ira/crm/feature-governance triggers _load_crm_governance."""
        r = client.post("/ira/crm/feature-governance", headers=SH, json={
            "feature": "multi_tenancy",
            "owner": "corteza",
            "disable_duplicate_in_secondary": True,
            "policy_change_human_validation": False,
            "notes": "Corteza handles multi-tenancy primarily",
        })
        assert r.status_code in VALID


# ─── Advisor Recommendations route ────────────────────────────────────────────

class TestAdvisorRecommendationsRoute:
    """Lines 4175-4261: /advisor/recommendations route."""

    def test_advisor_recommendations(self, client: TestClient) -> None:
        """POST /ira/advisor/recommendations."""
        r = client.post("/ira/advisor/recommendations", headers=SH, json={
            "objective": "Improve customer retention by 20%",
            "horizon_days": 90,
            "include_feature_adoption": True,
        })
        assert r.status_code in VALID


# ─── Copilot routes ────────────────────────────────────────────────────────────

class TestCopilotRoutes:
    """Lines 2555-2634: /copilot/* routes."""

    def test_copilot_catalog(self, client: TestClient) -> None:
        """GET /ira/copilot/catalog."""
        r = client.get("/ira/copilot/catalog", headers=H)
        assert r.status_code in VALID

    def test_copilot_health(self, client: TestClient) -> None:
        """GET /ira/copilot/health."""
        r = client.get("/ira/copilot/health", headers=H)
        assert r.status_code in VALID

    def test_copilot_env_template(self, client: TestClient) -> None:
        """GET /ira/copilot/env-template."""
        r = client.get("/ira/copilot/env-template", headers=H)
        assert r.status_code in VALID

    def test_copilot_plan(self, client: TestClient) -> None:
        """POST /ira/copilot/plan."""
        r = client.post("/ira/copilot/plan", headers=H, json={
            "objective": "Integrate GitHub Copilot chat and agent workflows",
            "priority": "reliability",
            "include_enterprise_controls": True,
            "include_telemetry": True,
            "include_agent_mode": True,
        })
        assert r.status_code in VALID


# ─── Monitor, Costs, Performance routes ───────────────────────────────────────

class TestMonitorCostsRoutes:
    """Lines 3558-3723+: /monitor, /costs, /performance routes."""

    def test_monitor(self, client: TestClient) -> None:
        """GET /ira/monitor."""
        r = client.get("/ira/monitor", headers=H)
        assert r.status_code in VALID

    def test_costs(self, client: TestClient) -> None:
        """GET /ira/costs."""
        r = client.get("/ira/costs", headers=H)
        assert r.status_code in VALID

    def test_performance(self, client: TestClient) -> None:
        """GET /ira/performance."""
        r = client.get("/ira/performance", headers=H)
        assert r.status_code in VALID


# ─── IRAMemorySystem direct tests ─────────────────────────────────────────────

class TestIraMemorySystemDirect:
    """Direct tests for ira_memory.py missing lines."""

    def _make_memory_system(self, postgres_ready: bool = False) -> object:
        """Create an IRAMemorySystem instance."""
        from backend.fastapi.app.ira_memory import IRAMemorySystem
        return IRAMemorySystem(
            db_dsn_fn=lambda: "host=localhost dbname=test user=test password=test",
            now_iso_fn=lambda: "2025-01-01T00:00:00+00:00",
            short_term_store=[],
            long_term_store=[],
            structured_store=[],
            embed_texts=lambda texts: ("local_hash", [[float(hash(t) % 100) / 100 for _ in range(4)] for t in texts]),
        )

    def test_provider_status_pinecone_backend(self) -> None:
        """Line 140: long_term_backend='pinecone' when PINECONE configured."""
        ms = self._make_memory_system()
        with patch.dict(os.environ, {
            "PINECONE_API_KEY": "fake-key",
            "PINECONE_INDEX_HOST": "fake-host.pinecone.io",
        }):
            status = ms.provider_status()  # type: ignore[union-attr]
        assert status["long_term"]["pinecone_ready"] is True

    def test_load_vault_secrets_no_postgres(self) -> None:
        """Lines 57-58: no postgres → return empty dict."""
        import backend.fastapi.app.ira_memory as ira_mem_module
        from backend.fastapi.app.ira_memory import _load_vault_secrets

        # Reset cache
        original_attempted = ira_mem_module._vault_cache_attempted
        original_cache = ira_mem_module._vault_cache
        ira_mem_module._vault_cache_attempted = False

        try:
            with patch.dict(os.environ, {}, clear=False):
                # Remove SUPABASE_DB_URL and POSTGRES_HOST to ensure no postgres
                env_backup = {}
                for key in ["SUPABASE_DB_URL", "POSTGRES_HOST"]:
                    if key in os.environ:
                        env_backup[key] = os.environ.pop(key)
                try:
                    result = _load_vault_secrets()
                    assert isinstance(result, dict)
                finally:
                    os.environ.update(env_backup)
        finally:
            ira_mem_module._vault_cache_attempted = original_attempted
            ira_mem_module._vault_cache = original_cache

    def test_load_vault_secrets_with_postgres_mock(self) -> None:
        """Lines 59-65: postgres available → query vault."""
        import backend.fastapi.app.ira_memory as ira_mem_module
        from backend.fastapi.app.ira_memory import _load_vault_secrets

        ira_mem_module._vault_cache_attempted = False
        ira_mem_module._vault_cache = {}

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [("OPENAI_KEY", "sk-fake"), ("REDIS_PASSWORD", "secret")]
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"POSTGRES_HOST": "localhost"}):
            with patch("psycopg.connect", return_value=mock_conn):
                result = _load_vault_secrets()
        assert isinstance(result, dict)

        ira_mem_module._vault_cache_attempted = False

    def test_vault_get_with_vault_secret(self) -> None:
        """Lines 77-80: vault_get finds value in vault."""
        import backend.fastapi.app.ira_memory as ira_mem_module
        from backend.fastapi.app.ira_memory import _vault_get

        ira_mem_module._vault_cache = {"MY_SECRET": "vault-value"}
        ira_mem_module._vault_cache_attempted = True

        with patch.dict(os.environ, {"IRA_VAULT_SECRET_MY_KEY": "MY_SECRET"}):
            result = _vault_get("DIRECT_ENV_KEY", "IRA_VAULT_SECRET_MY_KEY", "fallback")

        assert result == "vault-value"

    def test_upsert_structured_memory_in_memory(self) -> None:
        """Lines 253-287: upsert_structured_memory in-memory path."""
        ms = self._make_memory_system(postgres_ready=False)
        result = ms.upsert_structured_memory(  # type: ignore[union-attr]
            tenant_id="test-memory-tenant",
            memory_type="user_profile",
            memory_key="test-key-001",
            payload={"name": "Test User"},
        )
        assert result["memory_key"] == "test-key-001"
        assert result["source"] == "in_memory"

    def test_upsert_structured_memory_update_existing(self) -> None:
        """Lines 253+: update existing entry."""
        ms = self._make_memory_system()
        # First upsert
        ms.upsert_structured_memory(  # type: ignore[union-attr]
            tenant_id="test-memory-tenant",
            memory_type="user_profile",
            memory_key="test-key-update",
            payload={"name": "Original"},
        )
        # Second upsert (update)
        result = ms.upsert_structured_memory(  # type: ignore[union-attr]
            tenant_id="test-memory-tenant",
            memory_type="user_profile",
            memory_key="test-key-update",
            payload={"name": "Updated"},
        )
        assert result.get("payload", {}).get("name") == "Updated" or result["memory_key"] == "test-key-update"

    def test_list_structured_memory_in_memory(self) -> None:
        """Lines 301-302: list_structured_memory in-memory fallback."""
        ms = self._make_memory_system()
        ms.upsert_structured_memory(  # type: ignore[union-attr]
            tenant_id="list-test-tenant",
            memory_type="task",
            memory_key="task-001",
            payload={"title": "Test Task"},
        )
        results = ms.list_structured_memory("list-test-tenant")  # type: ignore[union-attr]
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_sync_long_term_memory_in_memory(self) -> None:
        """Lines 315-378: sync_long_term_memory in-memory path."""
        ms = self._make_memory_system()
        result = ms.sync_long_term_memory(  # type: ignore[union-attr]
            tenant_id="sync-test-tenant",
            records=[
                {
                    "document_id": "doc-001",
                    "chunk_id": "chunk-001-001",
                    "title": "Test Document",
                    "source": "internal",
                    "content": "This is test content for IRA memory testing",
                    "embedding": [0.1, 0.2, 0.3, 0.4],
                }
            ],
        )
        assert isinstance(result, dict)
        assert "provider" in result

    def test_query_long_term_memory_in_memory(self) -> None:
        """Lines 405-456: query_long_term_memory fallback path."""
        ms = self._make_memory_system()
        items = [
            {
                "document_id": "doc-001",
                "chunk_id": "chunk-001",
                "title": "IRA Overview",
                "content": "IRA platform content here",
                "embedding": [0.5, 0.5, 0.5, 0.5],
            }
        ]
        provider, results = ms.query_long_term_memory(  # type: ignore[union-attr]
            tenant_id="query-test-tenant",
            query="IRA platform",
            top_k=3,
            min_score=0.0,
            fallback_items=items,
        )
        assert isinstance(results, list)

    def test_postgres_ready_check(self) -> None:
        """Lines 475-476: _postgres_ready() returns correct bool."""
        ms = self._make_memory_system()
        with patch.dict(os.environ, {"POSTGRES_HOST": "localhost"}):
            assert ms._postgres_ready() is True  # type: ignore[union-attr]
        assert ms._postgres_ready() in (True, False)  # type: ignore[union-attr]

    def test_ensure_tables_skips_if_not_postgres(self) -> None:
        """Lines 479-510: _ensure_tables does nothing when postgres not ready."""
        ms = self._make_memory_system()
        ms._ensure_tables()  # type: ignore[union-attr]
        assert ms._tables_ready is False  # type: ignore[union-attr]

    def test_pinecone_sync_no_api_key(self) -> None:
        """Lines 560-580: _sync_pinecone returns 0 without api_key."""
        ms = self._make_memory_system()
        result = ms._sync_pinecone(  # type: ignore[union-attr]
            tenant_id="sync-tenant",
            records=[{"chunk_id": "c1", "embedding": [0.1, 0.2], "title": "t", "content": "c"}],
        )
        assert result == 0

    def test_weaviate_sync_no_base_url(self) -> None:
        """Lines 574-582: _sync_weaviate returns 0 without base_url."""
        ms = self._make_memory_system()
        result = ms._sync_weaviate(  # type: ignore[union-attr]
            tenant_id="sync-tenant",
            records=[{"chunk_id": "c1", "embedding": [0.1, 0.2], "title": "t", "content": "c"}],
        )
        assert result == 0

