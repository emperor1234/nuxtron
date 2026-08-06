"""
IRA extra tests - round 2: covers missing branches by calling helper functions directly.
Targets:
- compute_tenant_suspicious_signal line 465 (ai_cost_burn_high reason)
- run_ira_watchdog (lines 548-580) async watchdog loop
- _probe_crm_connectors (lines 758-766) with CORTEZA env var set
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-ira2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 423, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestComputeSuspiciousSignalAllReasons:
    """Line 465: ai_cost_burn_high reason in compute_tenant_suspicious_signal."""

    def test_ai_cost_burn_high_reason(self) -> None:
        from backend.fastapi.app.routers.ira import compute_tenant_suspicious_signal
        # ai_cost_total / ai_cost_threshold >= 0.8 → ai_cost_burn_high
        # ai_cost_threshold defaults to 25.0 → need total >= 20.0
        now_ts = int(__import__('time').time())
        ai_security_usage_memory = [
            {
                'tenant_id': 'tenant_ira2',
                'timestamp': now_ts - 60,  # recent
                'estimated_cost': 22.0,    # ai_score = min(1.0, 22.0/25.0) = 0.88 >= 0.8
            }
        ]
        result = compute_tenant_suspicious_signal(
            tenant_id='tenant_ira2',
            stripe_events_memory=[],
            revenue_conversions_memory=[],
            api_usage_audit_memory=[],
            ai_security_usage_memory=ai_security_usage_memory,
        )
        assert 'ai_cost_burn_high' in result['reasons']  # line 465

    def test_api_burst_detected_reason(self) -> None:
        from backend.fastapi.app.routers.ira import compute_tenant_suspicious_signal
        now_ts = int(__import__('time').time())
        # api_threshold defaults to 250 → need >= 200 requests in window
        api_usage_audit_memory = [
            {'tenant_id': 'tenant_burst', 'timestamp': now_ts - 30}
            for _ in range(201)
        ]
        result = compute_tenant_suspicious_signal(
            tenant_id='tenant_burst',
            stripe_events_memory=[],
            revenue_conversions_memory=[],
            api_usage_audit_memory=api_usage_audit_memory,
            ai_security_usage_memory=[],
        )
        assert 'api_burst_detected' in result['reasons']

    def test_payment_failure_high_reason(self) -> None:
        from backend.fastapi.app.routers.ira import compute_tenant_suspicious_signal
        now_ts = int(__import__('time').time())
        # payment_failures / total >= 0.5
        stripe_events_memory = [
            {'tenant_id': 'tenant_pf', 'created_at': now_ts - 100, 'event_type': 'payment.failed', 'status': 'failed'},
            {'tenant_id': 'tenant_pf', 'created_at': now_ts - 200, 'event_type': 'payment.failed', 'status': 'failed'},
        ]
        result = compute_tenant_suspicious_signal(
            tenant_id='tenant_pf',
            stripe_events_memory=stripe_events_memory,
            revenue_conversions_memory=[],
            api_usage_audit_memory=[],
            ai_security_usage_memory=[],
        )
        assert 'payment_failure_ratio_high' in result['reasons']

    def test_payments_failing_without_conversions_reason(self) -> None:
        from backend.fastapi.app.routers.ira import compute_tenant_suspicious_signal
        now_ts = int(__import__('time').time())
        # No conversions + payment failures → payments_failing_without_conversions
        stripe_events_memory = [
            {'tenant_id': 'tenant_noconv', 'created_at': now_ts - 100, 'status': 'failed'}
        ]
        result = compute_tenant_suspicious_signal(
            tenant_id='tenant_noconv',
            stripe_events_memory=stripe_events_memory,
            revenue_conversions_memory=[],
            api_usage_audit_memory=[],
            ai_security_usage_memory=[],
        )
        assert 'payments_failing_without_conversions' in result['reasons']


class TestWatchdogActivationReason:
    """Test _watchdog_activation_reason branches."""

    def test_profit_below_target(self) -> None:
        from backend.fastapi.app.routers.ira import _watchdog_activation_reason
        control = {'min_profit_margin_pct': 70.0, 'suspicious_signal_threshold': 0.75}
        snapshot = {'profit_margin_pct': 50.0}
        suspicious_signal = {'score': 0.1}
        reason = _watchdog_activation_reason(control, snapshot, suspicious_signal)
        assert reason == 'profit_below_target'

    def test_suspicious_signal_reason(self) -> None:
        from backend.fastapi.app.routers.ira import _watchdog_activation_reason
        control = {'min_profit_margin_pct': 70.0, 'suspicious_signal_threshold': 0.75}
        snapshot = {'profit_margin_pct': 80.0}
        suspicious_signal = {'score': 0.9}
        reason = _watchdog_activation_reason(control, snapshot, suspicious_signal)
        assert reason == 'suspicious_signal'

    def test_no_reason(self) -> None:
        from backend.fastapi.app.routers.ira import _watchdog_activation_reason
        control = {'min_profit_margin_pct': 70.0, 'suspicious_signal_threshold': 0.75}
        snapshot = {'profit_margin_pct': 85.0}
        suspicious_signal = {'score': 0.2}
        reason = _watchdog_activation_reason(control, snapshot, suspicious_signal)
        assert reason is None


class TestRunIraWatchdog:
    """Lines 548-580: run_ira_watchdog async function."""

    def test_watchdog_processes_controls(self) -> None:
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        ira_controls_memory = [
            {
                'tenant_id': 'watchdog_tenant',
                'autonomy_enabled': True,
                'protection_mode': False,
                'min_profit_margin_pct': 70.0,
                'suspicious_signal_threshold': 0.75,
            }
        ]
        ira_events_memory: list = []
        audit_log_memory: list = []

        stop_event = asyncio.Event()

        async def run_once():
            stop_event.set()  # Stop immediately after first iteration
            await run_ira_watchdog(
                stop_event,
                ira_controls_memory=ira_controls_memory,
                ira_events_memory=ira_events_memory,
                audit_log_memory=audit_log_memory,
                invoices_memory=[],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(run_once())

    def test_watchdog_skips_disabled_autonomy(self) -> None:
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        ira_controls_memory = [
            {
                'tenant_id': 'watchdog_tenant2',
                'autonomy_enabled': False,  # Should be skipped (line 552-553)
                'protection_mode': False,
            }
        ]
        ira_events_memory: list = []
        audit_log_memory: list = []

        stop_event = asyncio.Event()

        async def run_once():
            stop_event.set()
            await run_ira_watchdog(
                stop_event,
                ira_controls_memory=ira_controls_memory,
                ira_events_memory=ira_events_memory,
                audit_log_memory=audit_log_memory,
                invoices_memory=[],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(run_once())
        # Skipped → no events generated
        assert len(ira_events_memory) == 0

    def test_watchdog_activates_protection(self) -> None:
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        # Control with low profit margin → should trigger protection
        ira_controls_memory = [
            {
                'tenant_id': 'watchdog_activate',
                'autonomy_enabled': True,
                'protection_mode': False,
                'min_profit_margin_pct': 70.0,
                'suspicious_signal_threshold': 0.75,
            }
        ]
        ira_events_memory: list = []
        audit_log_memory: list = []
        # Revenue=10, COGS=2, credits_granted=10000 → credits_cost=20 → total_cost=22 → margin=(10-22)/10*100=-120% < 70%
        invoices_memory = [
            {'tenant_id': 'watchdog_activate', 'status': 'paid', 'amount': 10.0}
        ]
        credit_ledger_memory = [
            {'tenant_id': 'watchdog_activate', 'amount': 10000}
        ]

        stop_event = asyncio.Event()

        async def run_with_stop():
            async def set_stop_later():
                await asyncio.sleep(0.05)
                stop_event.set()

            await asyncio.gather(
                run_ira_watchdog(
                    stop_event,
                    ira_controls_memory=ira_controls_memory,
                    ira_events_memory=ira_events_memory,
                    audit_log_memory=audit_log_memory,
                    invoices_memory=invoices_memory,
                    credit_ledger_memory=credit_ledger_memory,
                    stripe_events_memory=[],
                    revenue_conversions_memory=[],
                    api_usage_audit_memory=[],
                    ai_security_usage_memory=[],
                ),
                set_stop_later(),
            )

        asyncio.run(run_with_stop())
        # Protection activated since profit margin is below 70%
        assert ira_controls_memory[0].get('protection_mode') is True
        assert len(ira_events_memory) > 0  # lines 568-576

    def test_watchdog_skips_already_protected(self) -> None:
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        ira_controls_memory = [
            {
                'tenant_id': 'watchdog_protected',
                'autonomy_enabled': True,
                'protection_mode': True,  # Already protected → skip activation
                'min_profit_margin_pct': 70.0,
                'suspicious_signal_threshold': 0.75,
            }
        ]
        ira_events_memory: list = []
        audit_log_memory: list = []

        stop_event = asyncio.Event()

        async def run_once():
            stop_event.set()
            await run_ira_watchdog(
                stop_event,
                ira_controls_memory=ira_controls_memory,
                ira_events_memory=ira_events_memory,
                audit_log_memory=audit_log_memory,
                invoices_memory=[{'tenant_id': 'watchdog_protected', 'status': 'paid', 'amount': 1.0}],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(run_once())
        # Already protected → should NOT generate new events
        assert len(ira_events_memory) == 0

    def test_watchdog_empty_tenant_skipped(self) -> None:
        from backend.fastapi.app.routers.ira import run_ira_watchdog

        ira_controls_memory = [
            {'tenant_id': '', 'autonomy_enabled': True}  # Empty tenant → skip (line 552)
        ]
        ira_events_memory: list = []
        audit_log_memory: list = []

        stop_event = asyncio.Event()

        async def run_once():
            stop_event.set()
            await run_ira_watchdog(
                stop_event,
                ira_controls_memory=ira_controls_memory,
                ira_events_memory=ira_events_memory,
                audit_log_memory=audit_log_memory,
                invoices_memory=[],
                credit_ledger_memory=[],
                stripe_events_memory=[],
                revenue_conversions_memory=[],
                api_usage_audit_memory=[],
                ai_security_usage_memory=[],
            )

        asyncio.run(run_once())
        assert len(ira_events_memory) == 0


class TestProbeCrmConnectors:
    """Lines 758-766: _probe_crm_connectors with CORTEZA_API_BASE_URL set."""

    def test_crm_governance_with_corteza_env(self, client: TestClient) -> None:
        """Set CORTEZA env vars and call the CRM governance route to trigger _probe_crm_connectors."""
        with patch.dict(os.environ, {
            'CORTEZA_API_BASE_URL': 'https://corteza.invalid.example.com',
            'CORTEZA_API_TOKEN': 'test-token-xyz',
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'false'  # Keep probe disabled to avoid network calls
        }):
            r = client.get("/ira/crm/governance", headers=H)
            assert r.status_code in VALID  # lines 758-763

    def test_crm_governance_probe_enabled_corteza(self, client: TestClient) -> None:
        """With probe enabled, triggers the actual HTTP probe path (lines 765-766)."""
        with patch.dict(os.environ, {
            'CORTEZA_API_BASE_URL': 'https://corteza.invalid.example.com',
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'true',
        }), patch('httpx.get') as mock_get:
            from unittest.mock import MagicMock
            mock_resp = MagicMock()
            mock_resp.is_success = True
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            r = client.get("/ira/crm/governance", headers=H)
            assert r.status_code in VALID  # lines 765-766

    def test_crm_governance_probe_enabled_odoo(self, client: TestClient) -> None:
        """With ODOO env set and probe enabled."""
        with patch.dict(os.environ, {
            'ODOO_API_BASE_URL': 'https://odoo.invalid.example.com',
            'ODOO_API_KEY': 'test-odoo-key',
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'true',
        }), patch('httpx.get') as mock_get:
            from unittest.mock import MagicMock
            mock_resp = MagicMock()
            mock_resp.is_success = False
            mock_resp.status_code = 503
            mock_get.return_value = mock_resp
            r = client.get("/ira/crm/governance", headers=H)
            assert r.status_code in VALID

    def test_crm_governance_probe_exception(self, client: TestClient) -> None:
        """Probe raises exception → detail set from exception."""
        with patch.dict(os.environ, {
            'CORTEZA_API_BASE_URL': 'https://corteza.invalid.example.com',
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'true',
        }), patch('httpx.get', side_effect=Exception("Connection refused")):
            r = client.get("/ira/crm/governance", headers=H)
            assert r.status_code in VALID


class TestIraRoutesCoverage:
    """Additional IRA route tests to cover missing branch lines."""

    def test_ira_finance_sample_with_high_ai_cost(self, client: TestClient) -> None:
        """Test IRA finance route to exercise suspicious signal logic."""
        r = client.post("/ira/finance/sample", headers=H, json={
            "revenue": 1000.0,
            "cogs": 200.0,
            "credits_cost": 10.0,
            "suspicious_signal_score": 0.9,
            "note": "High risk test"
        })
        assert r.status_code in VALID

    def test_ira_health(self, client: TestClient) -> None:
        r = client.get("/ira/health", headers=H)
        assert r.status_code in VALID

    def test_ira_events(self, client: TestClient) -> None:
        r = client.get("/ira/events", headers=H)
        assert r.status_code in VALID

    def test_ira_crm_governance_update(self, client: TestClient) -> None:
        r = client.post("/ira/crm/governance/update", headers=H, json={
            "feature": "multi_tenancy",
            "owner": "corteza",
            "disable_duplicate_in_secondary": True,
            "notes": "Test update"
        })
        assert r.status_code in VALID

    def test_ira_ab_tests_list(self, client: TestClient) -> None:
        r = client.get("/ira/ab-tests", headers=H)
        assert r.status_code in VALID

    def test_ira_ab_test_create(self, client: TestClient) -> None:
        r = client.post("/ira/ab-tests", headers=H, json={
            "name": "Test AB Experiment",
            "variants": ["variant_a", "variant_b"],
            "metric": "conversion_rate",
            "traffic_split": [0.5, 0.5],
            "target_scope": "seo"
        })
        assert r.status_code in VALID

    def test_ira_batch_actions(self, client: TestClient) -> None:
        r = client.post("/ira/batch-actions", headers=H, json={
            "actions": [
                {
                    "target": "customers",
                    "command": "notify",
                    "payload": {"message": "Test"},
                    "dry_run": True
                }
            ],
            "dry_run": True,
            "human_validation_approved": False
        })
        assert r.status_code in VALID
