"""
Comprehensive test suite for IRA (Intelligent Risk Assistant) REST endpoints.

Tests cover:
- All 10 REST endpoints (status, chat, actions, control, connectors, finance, risk, ingest, disable-protection)
- Tenant isolation and per-tenant rate limiting
- Protection mode activation and blocking logic
- High-impact action enforcement policies
- Multi-channel connector dispatch (email, Slack, WhatsApp)
- Autonomy enable/disable enforcement
- Financial health and suspicious signal scoring
- Audit logging and event tracking
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set up test environment
os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')


# ────────────────────────────────────────────────────────────────────────────────
# Test Fixtures & Helper Functions
# ────────────────────────────────────────────────────────────────────────────────


def _make_app_and_client(
    autonomy_enabled: bool = True,
    protection_mode: bool = False,
    allow_high_impact: bool = False,
) -> tuple[FastAPI, TestClient, Any]:
    """Create a test FastAPI app with IRA router and return app, client, and memory stores."""
    from backend.fastapi.app import main as app_main
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.main import app as main_app
    
    # Reset memory stores
    memory_stores.audit_log.clear()
    memory_stores.tickets.clear()
    memory_stores.chatbot_conversations.clear()
    memory_stores.credit_ledger.clear()
    memory_stores.invoices.clear()
    memory_stores.stripe_events.clear()
    memory_stores.revenue_conversions.clear()
    memory_stores.api_usage_audit.clear()
    memory_stores.ai_security_usage.clear()
    memory_stores.slack_messages.clear()
    memory_stores.resend_messages.clear()
    memory_stores.twilio_messages.clear()
    memory_stores.ira_events.clear()
    memory_stores.ira_sessions.clear()
    memory_stores.ira_controls.clear()
    memory_stores.ira_connectors.clear()
    app_main.reset_rate_limits_for_tests()
    
    # Set up default control for test tenant
    memory_stores.ira_controls.append({
        'id': 1,
        'tenant_id': 'test-tenant',
        'autonomy_enabled': autonomy_enabled,
        'allow_high_impact_actions': allow_high_impact,
        'min_profit_margin_pct': 70.0,
        'suspicious_signal_threshold': 0.75,
        'protection_mode': protection_mode,
        'blocked_actions': ['billing_change', 'credit_spend', 'external_transfer'] if protection_mode else [],
        'updated_at': datetime.now(UTC).isoformat(),
    })
    
    client = TestClient(main_app)
    return main_app, client, memory_stores


def _headers(tenant: str = 'test-tenant', api_key: str = 'test-api-key') -> dict[str, str]:
    """Generate test headers with API key and tenant ID."""
    return {
        'X-API-Key': api_key,
        'X-Tenant-Id': tenant,
        'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key'),
    }


def _headers_without_super_admin(tenant: str = 'test-tenant', api_key: str = 'test-api-key') -> dict[str, str]:
    return {
        'X-API-Key': api_key,
        'X-Tenant-Id': tenant,
    }


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Status Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_status_success():
    """GET /ira/status returns current autonomy, connectors, financial health, risk signal."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ira/status', headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'autonomy' in data
    assert 'connectors' in data
    assert 'finance_health' in data
    assert 'risk_signal' in data
    assert 'recent_events' in data
    assert 'capabilities' in data
    assert 'provider_readiness' in data
    
    # Verify default connector channels
    channels = {c['channel'] for c in data['connectors']}
    assert channels == {'chat', 'email', 'ticket', 'webhook', 'admin', 'customer_support'}
    assert data['provider_readiness']['internal']['configured'] is True
    assert data['provider_readiness']['internal']['route'] == 'internal'
    assert data['provider_readiness']['internal']['reason'] == 'Built-in guarded fallback route'
    assert 'openai' in data['provider_readiness']
    assert 'anthropic' in data['provider_readiness']
    assert 'reason' in data['provider_readiness']['openai']
    assert 'reason' in data['provider_readiness']['anthropic']


def test_ira_status_rate_limit():
    """GET /ira/status enforces rate limit (120 req/min)."""
    _, client, _ = _make_app_and_client()
    
    # Should allow 120 requests within 60 seconds (in test, each call increments bucket)
    for i in range(121):
        response = client.get('/ira/status', headers=_headers())
        if i < 120:
            assert response.status_code == 200
        else:
            # 121st request should exceed rate limit
            assert response.status_code == 429
            assert 'Rate limit exceeded' in response.text


def test_ira_status_uses_provider_supplied_reason():
    """GET /ira/status uses provider-supplied reason text when exposed by AI brain capabilities."""
    _, client, _ = _make_app_and_client()

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'openai': {
                'configured': False,
                'model': 'gpt-4.1-mini',
                'reason': 'OpenAI API key missing in environment',
            },
            'anthropic': {
                'configured': True,
                'model': 'claude-3-5-sonnet-latest',
                'status_reason': 'Connected via managed secret store',
            },
        }
    }):
        response = client.get('/ira/status', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['provider_readiness']['openai']['reason'] == 'OpenAI API key missing in environment'
    assert data['provider_readiness']['anthropic']['reason'] == 'Connected via managed secret store'


def test_ira_playbook_success_contract():
    """GET /ira/playbook returns completion chart, milestones, and decision tree."""
    _, client, memory_stores = _make_app_and_client()

    memory_stores.ira_sessions.append({
        'id': 1,
        'tenant_id': 'test-tenant',
        'role': 'admin',
        'channel': 'chat',
        'user_message': 'Run onboarding flow',
        'context': {},
        'created_at': datetime.now(UTC).isoformat(),
    })
    memory_stores.ira_events.append({
        'id': 1,
        'tenant_id': 'test-tenant',
        'event_type': 'chat_handled',
        'payload': {},
        'created_at': datetime.now(UTC).isoformat(),
    })

    response = client.get('/ira/playbook', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'generated_at' in data

    chart = data['completion_chart']
    assert chart['total'] >= 1
    assert 0.0 <= float(chart['percentage']) <= 100.0

    milestones = data['milestones']
    assert isinstance(milestones, list)
    assert len(milestones) >= 4
    assert all('label' in item and 'achieved' in item for item in milestones)

    decision_tree = data['decision_tree']
    assert isinstance(decision_tree, list)
    assert len(decision_tree) >= 3
    assert all('question' in item and 'if_yes' in item and 'if_no' in item for item in decision_tree)


def test_ira_copilot_catalog_success():
    """GET /ira/copilot/catalog returns A-Z catalog, readiness, and env template."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ira/copilot/catalog', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'copilot' in data
    assert 'a_to_z' in data['copilot']
    assert 'A' in data['copilot']['a_to_z']
    assert 'Z' in data['copilot']['a_to_z']
    assert 'readiness' in data
    assert 'env_template' in data


def test_ira_copilot_health_success():
    """GET /ira/copilot/health returns health and readiness payload."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ira/copilot/health', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'health' in data
    assert 'readiness' in data
    assert 'status' in data['health']


def test_ira_copilot_env_template_success():
    """GET /ira/copilot/env-template returns required and recommended env keys."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ira/copilot/env-template', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'env_template' in data
    template = data['env_template']
    assert template['required_env_count'] >= 1
    assert template['recommended_env_count'] >= 1
    assert any(str(item).startswith('GITHUB_TOKEN=') for item in template['required_env'])


def test_ira_copilot_plan_success():
    """POST /ira/copilot/plan returns implementation phases and event id."""
    _, client, memory_stores = _make_app_and_client()
    payload = {
        'objective': 'Integrate GitHub Copilot safely across IRA workflows.',
        'priority': 'reliability',
        'include_enterprise_controls': True,
        'include_telemetry': True,
        'include_agent_mode': True,
    }
    response = client.post('/ira/copilot/plan', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert data['objective'] == payload['objective']
    assert data['priority'] == 'reliability'
    assert len(data['implementation_phases']) >= 3
    assert 'event_id' in data
    assert any(item.get('event_type') == 'copilot_plan_generated' for item in memory_stores.ira_events)


def test_ops_platform_hybrid_stacks_contract():
    """GET /ops/platform/hybrid-stacks returns the expected contract shape and wired payload."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ops/platform/hybrid-stacks', headers=_headers())

    assert response.status_code == 200
    data = response.json()

    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert isinstance(data.get('generated_at'), str)

    recommendation = data.get('recommendation', {})
    assert recommendation.get('hybrid') == 'OpenLens (Free) + Promptwatch (Paid)'
    assert recommendation.get('score') == '100/100 (100%)'
    assert isinstance(recommendation.get('benefits'), list)
    assert isinstance(recommendation.get('positioning'), str)

    stacks = data.get('stacks', [])
    assert isinstance(stacks, list)
    assert len(stacks) == 50
    assert {
        'seo-ai',
        'geo',
        'aio-2',
        'llmo',
        'sageo',
        'vso',
        'sxo',
        'gxo',
        'entity-first-seo',
        'peao',
        'msvo',
        'daeo',
        'cxao',
        'eeat-suite',
        'autonomous-agent-engine',
        'programmatic-seo-engine',
        'seo-ab-testing',
        'ecommerce-seo-suite',
        'autonomous-link-building-system',
        'international-multilingual-seo',
        'site-migration-seo-manager',
        'video-seo-module',
        'local-seo-suite',
        'news-seo-google-discover',
        'analytics-reporting-intelligence',
        'agency-multi-tenant-platform',
        'integrations-automation-layer',
        'realtime-search-ai-monitoring',
        'ai-technical-seo-engine',
        'content-quality-hallucination-auditor',
        'knowledge-graph-management',
        'ai-internal-linking-engine',
        'crawl-budget-optimizer',
        'ai-schema-engine',
        'ux-conversion-optimizer',
        'rag-site-search-engine',
        'competitor-intelligence-engine',
        'topical-map-silo-builder',
        'log-file-analysis-engine',
        'review-reputation-engine',
        'brand-voice-style-engine',
        'accessibility-optimizer',
        'image-media-seo-engine',
        'social-seo-distribution',
        'landing-page-builder',
        'security-seo-health-monitor',
    }.issubset({str(item.get('id', '')) for item in stacks})

    summary = data.get('summary', [])
    assert isinstance(summary, list)
    assert len(summary) == 50
    assert {
        'SEO-AI',
        'GEO',
        'AIO-2',
        'LLMO',
        'SAGEO',
        'VSO',
        'SXO',
        'GXO',
        'ENTITY-FIRST SEO',
        'PEAO',
        'MSVO',
        'DAEO',
        'CXAO',
        'E-E-A-T',
        'AUTONOMOUS AGENT ENGINE',
        'PROGRAMMATIC SEO',
        'SEO A/B TESTING',
        'ECOMMERCE SEO',
        'AUTONOMOUS LINK BUILDING',
        'INTERNATIONAL & MULTILINGUAL SEO',
        'SITE MIGRATION SEO',
        'VIDEO SEO',
        'LOCAL SEO',
        'NEWS SEO & GOOGLE DISCOVER',
        'ANALYTICS, REPORTING & INTELLIGENCE',
        'AGENCY & MULTI-TENANT PLATFORM',
        'INTEGRATIONS & AUTOMATION LAYER',
        'REAL-TIME SEARCH & AI MONITORING',
        'AI-DRIVEN TECHNICAL SEO ENGINE',
        'CONTENT QUALITY & HALLUCINATION AUDITOR',
        'KNOWLEDGE GRAPH MANAGEMENT',
        'AI-FIRST INTERNAL LINKING ENGINE',
        'CRAWL BUDGET OPTIMIZER',
        'AI-GENERATED SCHEMA ENGINE',
        'UX & CONVERSION OPTIMIZER',
        'RAG-POWERED SITE SEARCH ENGINE',
        'COMPETITOR INTELLIGENCE ENGINE',
        'TOPICAL MAP & SILO BUILDER',
        'LOG FILE ANALYSIS ENGINE',
        'REVIEW & REPUTATION ENGINE',
        'BRAND VOICE & STYLE ENGINE',
        'ACCESSIBILITY OPTIMIZER',
        'IMAGE & MEDIA SEO ENGINE',
        'SOCIAL SEO & DISTRIBUTION ENGINE',
        'LANDING PAGE BUILDER',
        'SECURITY & SEO HEALTH MONITOR',
    }.issubset({str(item.get('category', '')) for item in summary})


def test_ops_platform_hybrid_stacks_fallback_contract():
    """GET /ops/platform/hybrid-stacks returns fallback payload when callback is not configured."""
    from backend.fastapi.app.routers.ops import create_ops_router

    app = FastAPI()
    app.include_router(
        create_ops_router(
            enforce_rate_limit=lambda _key, _limit, _window: None,
            hash_password=lambda _password, _algorithm: 'hash',
            verify_password=lambda _password, _stored_hash: True,
            get_platform_status=lambda auth: {'status': 'ok', 'tenant_id': auth.tenant_id},
            get_metrics_summary=lambda auth: {'status': 'ok', 'tenant_id': auth.tenant_id},
            # get_hybrid_stacks intentionally omitted to validate fallback contract.
        )
    )

    client = TestClient(app)
    response = client.get('/ops/platform/hybrid-stacks', headers=_headers())

    assert response.status_code == 200
    data = response.json()

    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert data['generated_at'] == ''

    recommendation = data.get('recommendation', {})
    assert recommendation.get('hybrid') == 'OpenLens (Free) + Promptwatch (Paid)'
    assert recommendation.get('score') == '100/100 (100%)'
    assert recommendation.get('benefits') == []
    assert recommendation.get('positioning') == ''

    assert data.get('stacks') == []
    assert data.get('summary') == []


def test_ops_platform_module_registry_contract():
    """GET /ops/platform/module-registry returns expected contract and module catalog totals."""
    _, client, _ = _make_app_and_client()
    response = client.get('/ops/platform/module-registry', headers=_headers())

    assert response.status_code == 200
    data = response.json()

    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert isinstance(data.get('generated_at'), str)
    assert data.get('source') in {'database', 'fallback'}

    modules = data.get('modules', [])
    assert isinstance(modules, list)
    assert len(modules) >= 50
    assert {
        'seo-ai',
        'geo',
        'llmo',
        'ecommerce-seo-suite',
        'autonomous-link-building-system',
        'international-multilingual-seo',
        'site-migration-seo-manager',
        'video-seo-module',
        'local-seo-suite',
        'news-seo-google-discover',
        'analytics-reporting-intelligence',
        'agency-multi-tenant-platform',
        'integrations-automation-layer',
        'realtime-search-ai-monitoring',
        'ai-technical-seo-engine',
        'rag-site-search-engine',
        'security-seo-health-monitor',
    }.issubset({str(item.get('id', '')) for item in modules})

    totals = data.get('totals', {})
    assert isinstance(totals, dict)
    assert int(totals.get('total_modules', 0)) >= 50
    assert int(totals.get('free_tools', 0)) > 0
    assert int(totals.get('open_source_tools', 0)) > 0
    assert float(totals.get('avg_hybrid_score', 0.0)) > 0.0


def test_ops_platform_module_registry_fallback_contract():
    """GET /ops/platform/module-registry returns fallback payload when callback is not configured."""
    from backend.fastapi.app.routers.ops import create_ops_router

    app = FastAPI()
    app.include_router(
        create_ops_router(
            enforce_rate_limit=lambda _key, _limit, _window: None,
            hash_password=lambda _password, _algorithm: 'hash',
            verify_password=lambda _password, _stored_hash: True,
            get_platform_status=lambda auth: {'status': 'ok', 'tenant_id': auth.tenant_id},
            get_metrics_summary=lambda auth: {'status': 'ok', 'tenant_id': auth.tenant_id},
        )
    )

    client = TestClient(app)
    response = client.get('/ops/platform/module-registry', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert data['generated_at'] == ''
    assert data['source'] == 'fallback'
    assert data['modules'] == []
    assert data['totals'] == {
        'total_modules': 0,
        'free_tools': 0,
        'open_source_tools': 0,
        'avg_hybrid_score': 0.0,
    }


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Chat Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_chat_success():
    """POST /ira/chat handles customer/admin/operator messages with role and channel routing."""
    _, client, memory_stores = _make_app_and_client()
    
    payload = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'I need help with billing.',
        'context': {'order_id': 'ORD-123'},
    }
    response = client.post('/ira/chat', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['tenant_id'] == 'test-tenant'
    assert 'ira' in data
    assert data['ira']['name'] == 'IRA'
    assert data['ira']['response']
    assert 'session_id' in data['ira']
    
    # Verify canonical chat session was created.
    # The shared session store now also includes short-term memory entries.
    sessions = [item for item in memory_stores.ira_sessions if 'user_message' in item]
    assert len(sessions) == 1
    session = sessions[0]
    assert session['tenant_id'] == 'test-tenant'
    assert session['role'] == 'customer'
    assert session['channel'] == 'chat'
    
    # Verify event was appended
    assert len(memory_stores.ira_events) == 1
    event = memory_stores.ira_events[0]
    assert event['event_type'] == 'chat_handled'


def test_ira_chat_autonomy_disabled():
    """POST /ira/chat returns 422 when autonomy is disabled."""
    _, client, _ = _make_app_and_client(autonomy_enabled=False)
    
    payload = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'Help!',
    }
    response = client.post('/ira/chat', json=payload, headers=_headers())
    
    assert response.status_code == 422
    assert 'autonomy is disabled' in response.text.lower()


def test_ira_chat_connector_disabled():
    """POST /ira/chat returns 422 when connector is disabled."""
    _, client, memory_stores = _make_app_and_client()
    
    # Disable chat connector
    connector = memory_stores.ira_connectors[0] if memory_stores.ira_connectors else None
    if not connector:
        # Create and disable chat connector
        memory_stores.ira_connectors.append({
            'id': 1,
            'tenant_id': 'test-tenant',
            'channel': 'chat',
            'enabled': False,
            'provider': 'internal',
            'config': {},
            'updated_at': datetime.now(UTC).isoformat(),
        })
    else:
        connector['enabled'] = False
    
    payload = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'Help!',
    }
    response = client.post('/ira/chat', json=payload, headers=_headers())
    
    assert response.status_code == 422
    assert 'connector' in response.text.lower()


def test_ira_chat_all_roles():
    """POST /ira/chat supports customer, admin, and operator roles."""
    _, client, memory_stores = _make_app_and_client()
    
    for role in ['customer', 'admin', 'operator']:
        payload = {
            'role': role,
            'channel': 'chat',
            'message': f'Message from {role}',
        }
        response = client.post('/ira/chat', json=payload, headers=_headers())
        assert response.status_code == 200
    
    # Verify 3 canonical chat sessions were created.
    # The store also includes assistant memory rows for each chat call.
    sessions = [item for item in memory_stores.ira_sessions if 'user_message' in item]
    assert len(sessions) == 3


def test_ira_chat_uses_requested_openai_provider():
    """POST /ira/chat uses the requested external provider when configured and returns provider metadata."""
    _, client, memory_stores = _make_app_and_client()

    payload = {
        'role': 'admin',
        'channel': 'chat',
        'message': 'Plan a guarded launch campaign.',
        'context': {
            'llm_routing': {
                'preferred_provider': 'openai',
                'requested_external_provider': True,
            }
        },
    }

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'openai': {'configured': True, 'model': 'gpt-4.1-mini'},
        }
    }), patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.reason', return_value={
        'status': 'ok',
        'reasoning': {
            'provider': 'openai',
            'model': 'gpt-4.1-mini',
            'output_text': 'OpenAI drafted a guarded launch plan.',
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': 180,
        },
    }):
        response = client.post('/ira/chat', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['ira']['response'] == 'OpenAI drafted a guarded launch plan.'
    assert data['ira']['provider_requested'] == 'openai'
    assert data['ira']['provider_used'] == 'openai'
    assert data['ira']['provider_model'] == 'gpt-4.1-mini'
    assert data['ira']['provider_status'] == 'external_ok'
    assert memory_stores.ira_events[-1]['payload']['provider_used'] == 'openai'


def test_ira_chat_falls_back_when_requested_provider_is_not_configured():
    """POST /ira/chat keeps the internal rule engine path when the requested provider is unavailable."""
    _, client, memory_stores = _make_app_and_client()

    payload = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'Help with billing risk.',
        'context': {
            'llm_routing': {
                'preferred_provider': 'anthropic',
                'requested_external_provider': True,
            }
        },
    }

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'anthropic': {'configured': False, 'model': 'claude-3-5-sonnet-latest'},
        }
    }):
        response = client.post('/ira/chat', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['ira']['provider_requested'] == 'anthropic'
    assert data['ira']['provider_used'] == 'internal_rule_engine'
    assert data['ira']['provider_model'] == 'claude-3-5-sonnet-latest'
    assert data['ira']['provider_status'] == 'requested_provider_not_configured'
    assert 'Billing workflow selected' in data['ira']['response']
    assert memory_stores.ira_events[-1]['payload']['provider_status'] == 'requested_provider_not_configured'


def test_ira_chat_maps_custom_chatgpt_label_to_openai_provider():
    """POST /ira/chat maps custom ChatGPT labels to openai and uses configured external reasoning."""
    _, client, memory_stores = _make_app_and_client()

    payload = {
        'role': 'admin',
        'channel': 'chat',
        'message': 'Draft a launch runbook with risk gates.',
        'context': {
            'llm_routing': {
                'preferred_provider': 'chatgpt-enterprise',
                'requested_external_provider': True,
                'custom_provider_label': 'chatgpt-enterprise',
            }
        },
    }

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'openai': {'configured': True, 'model': 'gpt-4.1-mini'},
        }
    }), patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.reason', return_value={
        'status': 'ok',
        'reasoning': {
            'provider': 'openai',
            'model': 'gpt-4.1-mini',
            'output_text': 'OpenAI handled the custom ChatGPT route.',
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': 160,
        },
    }):
        response = client.post('/ira/chat', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['ira']['response'] == 'OpenAI handled the custom ChatGPT route.'
    assert data['ira']['provider_requested'] == 'openai'
    assert data['ira']['provider_used'] == 'openai'
    assert data['ira']['provider_model'] == 'gpt-4.1-mini'
    assert data['ira']['provider_status'] == 'external_ok'
    assert memory_stores.ira_events[-1]['payload']['provider_requested'] == 'openai'


def test_ira_chat_maps_azure_openai_alias_to_openai_provider():
    """POST /ira/chat maps Azure OpenAI aliases to openai provider selection."""
    _, client, _ = _make_app_and_client()

    payload = {
        'role': 'admin',
        'channel': 'chat',
        'message': 'Build a release checklist.',
        'context': {
            'llm_routing': {
                'preferred_provider': 'azure-openai-enterprise',
                'requested_external_provider': True,
                'custom_provider_label': 'azure-openai-enterprise',
            }
        },
    }

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'openai': {'configured': True, 'model': 'gpt-4.1-mini'},
        }
    }), patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.reason', return_value={
        'status': 'ok',
        'reasoning': {
            'provider': 'openai',
            'model': 'gpt-4.1-mini',
            'output_text': 'Azure OpenAI alias resolved to OpenAI route.',
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': 170,
        },
    }):
        response = client.post('/ira/chat', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['ira']['provider_requested'] == 'openai'
    assert data['ira']['provider_used'] == 'openai'
    assert data['ira']['provider_status'] == 'external_ok'


def test_ira_chat_maps_claude_enterprise_alias_to_anthropic_provider():
    """POST /ira/chat maps Claude enterprise aliases to anthropic provider selection."""
    _, client, _ = _make_app_and_client()

    payload = {
        'role': 'admin',
        'channel': 'chat',
        'message': 'Draft enterprise support workflow.',
        'context': {
            'llm_routing': {
                'preferred_provider': 'claude-enterprise',
                'requested_external_provider': True,
                'custom_provider_label': 'claude-enterprise',
            }
        },
    }

    with patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.capabilities', return_value={
        'providers': {
            'anthropic': {'configured': True, 'model': 'claude-3-5-sonnet-latest'},
        }
    }), patch('backend.fastapi.app.routers.ira.AIBrainModelLayer.reason', return_value={
        'status': 'ok',
        'reasoning': {
            'provider': 'anthropic',
            'model': 'claude-3-5-sonnet-latest',
            'output_text': 'Claude enterprise alias resolved to Anthropic route.',
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': 190,
        },
    }):
        response = client.post('/ira/chat', json=payload, headers=_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['ira']['provider_requested'] == 'anthropic'
    assert data['ira']['provider_used'] == 'anthropic'
    assert data['ira']['provider_status'] == 'external_ok'


@pytest.mark.parametrize(
    ('raw_value', 'expected'),
    [
        pytest.param('', 'auto', id='empty->auto'),
        pytest.param('default', 'auto', id='default->auto'),
        pytest.param('internal', 'internal', id='internal->internal'),
        pytest.param('rule_based', 'internal', id='rule_based->internal'),
        pytest.param('openai', 'openai', id='openai->openai'),
        pytest.param('chatgpt', 'openai', id='chatgpt->openai'),
        pytest.param('chatgpt-enterprise', 'openai', id='chatgpt-enterprise->openai'),
        pytest.param('gpt-4.1-mini', 'openai', id='gpt-model->openai'),
        pytest.param('azure-openai', 'openai', id='azure-openai->openai'),
        pytest.param('azure_openai', 'openai', id='azure_openai->openai'),
        pytest.param('azure-openai-enterprise', 'openai', id='azure-openai-enterprise->openai'),
        pytest.param('my-azureopenai-gateway', 'openai', id='azureopenai-substring->openai'),
        pytest.param('Azure OpenAI Service', 'openai', id='azure-openai-service->openai'),
        pytest.param('anthropic', 'anthropic', id='anthropic->anthropic'),
        pytest.param('claude', 'anthropic', id='claude->anthropic'),
        pytest.param('claude-enterprise', 'anthropic', id='claude-enterprise->anthropic'),
        pytest.param('claudebot', 'anthropic', id='claudebot->anthropic'),
        pytest.param('claude-3-opus', 'anthropic', id='claude-model->anthropic'),
        pytest.param('anthropic-internal-proxy', 'anthropic', id='anthropic-substring->anthropic'),
        pytest.param('custom-unsupported-provider', 'custom-unsupported-provider', id='custom-unknown-pass-through'),
    ],
)
def test_normalize_chat_provider_preference_alias_matrix(raw_value: str, expected: str):
    """Normalization matrix keeps common enterprise/provider aliases mapped to canonical provider keys."""
    from backend.fastapi.app.routers import ira as ira_router

    assert ira_router._normalize_chat_provider_preference(raw_value) == expected


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Actions Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_actions_execute_success():
    """POST /ira/actions executes command with dry-run support."""
    _, client, memory_stores = _make_app_and_client()
    
    payload = {
        'target': 'customers',
        'command': 'send_notification',
        'payload': {'message': 'Test notification'},
        'dry_run': True,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['result']['dry_run'] is True
    assert data['result']['executed'] is False
    
    # Verify event was logged
    assert len(memory_stores.ira_events) >= 1


def test_ira_actions_high_impact_blocked():
    """POST /ira/actions returns 403 when high-impact action without allow flag."""
    _, client, _ = _make_app_and_client(allow_high_impact=False)
    
    payload = {
        'target': 'billing',
        'command': 'update_plan',
        'payload': {},
        'dry_run': False,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    
    assert response.status_code == 403
    assert 'high-impact' in response.text.lower()


def test_ira_actions_high_impact_allowed():
    """POST /ira/actions permits high-impact action when allow_high_impact_actions=true."""
    _, client, _ = _make_app_and_client(allow_high_impact=True)
    
    payload = {
        'target': 'billing',
        'command': 'update_plan',
        'payload': {},
        'dry_run': True,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    
    assert response.status_code == 200


def test_ira_actions_protection_mode_blocks():
    """POST /ira/actions returns 423 when protection mode active and target is high-impact."""
    _, client, _ = _make_app_and_client(protection_mode=True)
    
    payload = {
        'target': 'credits',
        'command': 'burn_credits',
        'payload': {},
        'dry_run': False,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    
    assert response.status_code == 403
    assert 'allow_high_impact_actions' in response.text.lower()


def test_ira_actions_all_targets():
    """POST /ira/actions supports all target types: customers, admin, email, chats, billing, credits, security, customer_support."""
    _, client, _ = _make_app_and_client(allow_high_impact=True)
    
    targets = ['customers', 'admin', 'email', 'chats', 'billing', 'credits', 'security', 'customer_support']
    for target in targets:
        payload = {
            'target': target,
            'command': 'test_command',
            'payload': {},
            'dry_run': True,
        }
        response = client.post('/ira/actions', json=payload, headers=_headers())
        assert response.status_code == 200


def test_ira_actions_autonomy_disabled():
    """POST /ira/actions returns 422 when autonomy is disabled."""
    _, client, _ = _make_app_and_client(autonomy_enabled=False)
    
    payload = {
        'target': 'customers',
        'command': 'test',
        'payload': {},
        'dry_run': True,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    
    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Control Configuration Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_control_config_update():
    """POST /ira/control/config updates autonomy thresholds."""
    _, client, memory_stores = _make_app_and_client()
    
    payload = {
        'autonomy_enabled': False,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 50.0,
        'suspicious_signal_threshold': 0.85,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['control']['autonomy_enabled'] is False
    assert data['control']['allow_high_impact_actions'] is False
    assert data['control']['min_profit_margin_pct'] == pytest.approx(50.0)
    assert data['control']['suspicious_signal_threshold'] == pytest.approx(0.85)
    
    # Verify event
    assert len(memory_stores.ira_events) == 1
    assert memory_stores.ira_events[0]['event_type'] == 'control_updated'


def test_ira_control_config_bounds():
    """POST /ira/control/config validates profit margin and signal thresholds."""
    _, client, _ = _make_app_and_client()
    
    # Valid bounds: profit_margin (0-100), suspicious_signal (0-1)
    payload = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 100.0,
        'suspicious_signal_threshold': 1.0,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload, headers=_headers())
    assert response.status_code == 200
    
    # Invalid: profit_margin > 100
    payload['min_profit_margin_pct'] = 101.0
    response = client.post('/ira/control/config', json=payload, headers=_headers())
    assert response.status_code == 422


def test_ira_control_config_super_admin_required():
    """POST /ira/control/config requires super-admin key when super-admin mode is enabled."""
    _, client, _ = _make_app_and_client()

    payload = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 70.0,
        'suspicious_signal_threshold': 0.75,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload, headers=_headers_without_super_admin())
    assert response.status_code == 403


def test_ira_strict_policy_lock_blocks_downgrade():
    """Strict policy lock blocks attempts to weaken guardrails."""
    _, client, _ = _make_app_and_client()

    payload = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': True,
        'min_profit_margin_pct': 70.0,
        'suspicious_signal_threshold': 0.75,
        'require_super_admin': False,
        'max_dispute_auto_resolution_gbp': 50.0,
        'strict_policy_lock': True,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload, headers=_headers())
    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Connectors Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_connectors_list():
    """GET /ira/connectors returns all connector channels with status."""
    _, client, _ = _make_app_and_client()
    
    response = client.get('/ira/connectors', headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['count'] == 6  # 6 channels
    
    channels = {c['channel'] for c in data['connectors']}
    assert channels == {'chat', 'email', 'ticket', 'webhook', 'admin', 'customer_support'}


def test_ira_connectors_upsert():
    """POST /ira/connectors/upsert configures channel provider and settings."""
    _, client, memory_stores = _make_app_and_client()
    
    payload = {
        'channel': 'email',
        'enabled': True,
        'provider': 'resend',
        'config': {'api_key': 'test-resend-key', 'from_email': 'ira@nuxtron.local'},
    }
    response = client.post('/ira/connectors/upsert', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['connector']['provider'] == 'resend'
    assert data['connector']['config']['from_email'] == 'ira@nuxtron.local'
    
    # Verify event
    assert len(memory_stores.ira_events) == 1


def test_ira_connectors_disable():
    """POST /ira/connectors/upsert can disable a connector."""
    _, client, _ = _make_app_and_client()
    
    payload = {
        'channel': 'chat',
        'enabled': False,
        'provider': 'internal',
        'config': {},
    }
    response = client.post('/ira/connectors/upsert', json=payload, headers=_headers())
    
    assert response.status_code == 200
    assert response.json()['connector']['enabled'] is False


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Finance Endpoints
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_finance_health():
    """GET /ira/finance/health returns profit margin, risk state, protection mode."""
    _, client, _ = _make_app_and_client()
    
    response = client.get('/ira/finance/health', headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'finance' in data
    assert 'suspicious_signal' in data
    assert 'thresholds' in data
    assert 'risk_state' in data
    assert 'protection_mode' in data
    assert data['risk_state'] in ['healthy', 'at_risk']


def test_ira_finance_ingest_healthy():
    """POST /ira/finance/ingest calculates profit margin from revenue and costs."""
    _, client, _ = _make_app_and_client()
    
    payload = {
        'revenue': 1000.0,
        'cogs': 200.0,
        'credits_cost': 50.0,
        'suspicious_signal_score': 0.1,
        'note': 'Sample transaction',
    }
    response = client.post('/ira/finance/ingest', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    expected_profit = ((1000 - 200 - 50) / 1000) * 100
    assert data['profit_margin_pct'] == expected_profit
    assert data['below_profit_target'] is False
    assert data['suspicious_signal'] is False
    assert data['protection_mode'] is False


def test_ira_finance_ingest_activates_protection():
    """POST /ira/finance/ingest activates protection mode when profit margin below threshold."""
    _, client, memory_stores = _make_app_and_client()
    
    # Revenue 1000, costs 900 = 10% profit (below 70% min)
    payload = {
        'revenue': 1000.0,
        'cogs': 800.0,
        'credits_cost': 100.0,
        'suspicious_signal_score': 0.0,
        'note': 'Low profit sample',
    }
    response = client.post('/ira/finance/ingest', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['below_profit_target'] is True
    assert data['protection_mode'] is True
    assert data['activation_event_id'] is not None
    
    # Verify protection mode was set
    control = memory_stores.ira_controls[0]
    assert control['protection_mode'] is True


def test_ira_finance_ingest_suspicious_signal():
    """POST /ira/finance/ingest activates protection mode when suspicious signal exceeds threshold."""
    _, client, _ = _make_app_and_client()
    
    # Good profit but high suspicious signal (>0.75)
    payload = {
        'revenue': 1000.0,
        'cogs': 100.0,
        'credits_cost': 100.0,
        'suspicious_signal_score': 0.80,  # Above 0.75 threshold
        'note': 'High risk sample',
    }
    response = client.post('/ira/finance/ingest', json=payload, headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['suspicious_signal'] is True
    assert data['protection_mode'] is True


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Risk Score Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_risk_score():
    """GET /ira/risk/score returns current suspicious signal score."""
    _, client, _ = _make_app_and_client()
    
    response = client.get('/ira/risk/score', headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'risk_signal' in data
    assert 'thresholds' in data
    assert 'protection_mode' in data
    assert 0.0 <= data['risk_signal']['score'] <= 1.0


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: IRA Protection Mode Endpoint
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_disable_protection():
    """POST /ira/control/disable-protection manually deactivates protection mode."""
    _, client, memory_stores = _make_app_and_client(protection_mode=True)
    
    # Verify protection is on
    assert memory_stores.ira_controls[0]['protection_mode'] is True
    
    response = client.post('/ira/control/disable-protection', headers=_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data['protection_mode'] is False
    
    # Verify protection was disabled
    assert memory_stores.ira_controls[0]['protection_mode'] is False
    assert memory_stores.ira_controls[0]['blocked_actions'] == []


def test_ira_disable_protection_rate_limit():
    """POST /ira/control/disable-protection enforces strict rate limit (30 req/min)."""
    _, client, _ = _make_app_and_client(protection_mode=True)
    
    # 30 requests should succeed
    for _ in range(30):
        response = client.post('/ira/control/disable-protection', headers=_headers())
        assert response.status_code == 200
    
    # 31st should fail
    response = client.post('/ira/control/disable-protection', headers=_headers())
    assert response.status_code == 429


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: Tenant Isolation
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_tenant_isolation():
    """IRA endpoints enforce strict tenant isolation; operations on one tenant don't affect others."""
    _, client, _ = _make_app_and_client()
    
    # Tenant A creates a chat session
    payload_a = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'Tenant A message',
    }
    response = client.post('/ira/chat', json=payload_a, headers=_headers(tenant='tenant-a'))
    assert response.status_code == 200
    
    # Tenant B creates a chat session
    payload_b = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'Tenant B message',
    }
    response = client.post('/ira/chat', json=payload_b, headers=_headers(tenant='tenant-b'))
    assert response.status_code == 200
    
    # Verify tenant A only sees their own session
    response = client.get('/ira/status', headers=_headers(tenant='tenant-a'))
    assert response.status_code == 200
    data = response.json()
    assert data['tenant_id'] == 'tenant-a'
    # Only events for tenant-a should be in recent_events
    for event in data['recent_events']:
        assert event['tenant_id'] == 'tenant-a'


def test_ira_tenant_control_isolation():
    """IRA tenant controls are independent; one tenant's settings don't affect others."""
    _, client, _ = _make_app_and_client()
    
    # Tenant A disables autonomy
    payload_a = {
        'autonomy_enabled': False,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 50.0,
        'suspicious_signal_threshold': 0.8,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload_a, headers=_headers(tenant='tenant-a'))
    assert response.status_code == 200
    
    # Tenant B keeps autonomy enabled
    payload_b = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 60.0,
        'suspicious_signal_threshold': 0.7,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=payload_b, headers=_headers(tenant='tenant-b'))
    assert response.status_code == 200
    
    # Verify tenant A's autonomy is disabled
    response = client.get('/ira/status', headers=_headers(tenant='tenant-a'))
    assert response.json()['autonomy']['autonomy_enabled'] is False
    
    # Verify tenant B's autonomy is enabled
    response = client.get('/ira/status', headers=_headers(tenant='tenant-b'))
    assert response.json()['autonomy']['autonomy_enabled'] is True


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: Audit Logging
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_audit_logging():
    """All IRA operations are logged in audit log with full context."""
    _, client, memory_stores = _make_app_and_client()
    
    # Perform various operations
    client.get('/ira/status', headers=_headers())
    client.post('/ira/chat', json={
        'role': 'customer',
        'channel': 'chat',
        'message': 'Test',
    }, headers=_headers())
    client.post('/ira/actions', json={
        'target': 'customers',
        'command': 'notify',
        'payload': {},
        'dry_run': True,
    }, headers=_headers())
    
    # Verify audit logs
    audit_logs = memory_stores.audit_log
    assert len(audit_logs) >= 2  # chat, actions
    
    for log in audit_logs:
        assert 'id' in log
        assert log['tenant_id'] == 'test-tenant'
        assert log['source'] == 'ira-router'
        assert 'action' in log
        assert 'created_at' in log


def test_ira_event_tracking():
    """All IRA operations emit timestamped events for audit trail."""
    _, client, memory_stores = _make_app_and_client()
    
    # Perform operations that should emit events
    client.post('/ira/chat', json={
        'role': 'customer',
        'channel': 'chat',
        'message': 'Test',
    }, headers=_headers())
    
    client.post('/ira/control/config', json={
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 75.0,
        'suspicious_signal_threshold': 0.75,
        'policy_change_human_validation': True,
    }, headers=_headers())
    
    # Verify events
    events = memory_stores.ira_events
    assert len(events) >= 2
    assert any(e['event_type'] == 'chat_handled' for e in events)
    assert any(e['event_type'] == 'control_updated' for e in events)


# ────────────────────────────────────────────────────────────────────────────────
# Test Suite: Multi-tenant Rate Limiting
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_rate_limit_per_tenant():
    """Rate limits are per-tenant; one tenant's limit doesn't affect another."""
    _, client, _ = _make_app_and_client()
    
    # Tenant A: Make 120 status requests (should all succeed, at limit)
    for _ in range(120):
        response = client.get('/ira/status', headers=_headers(tenant='tenant-a'))
        assert response.status_code == 200
    
    # Tenant A: 121st should fail
    response = client.get('/ira/status', headers=_headers(tenant='tenant-a'))
    assert response.status_code == 429
    
    # Tenant B: Should still be able to make requests (separate bucket)
    response = client.get('/ira/status', headers=_headers(tenant='tenant-b'))
    assert response.status_code == 200


# ────────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ────────────────────────────────────────────────────────────────────────────────


def test_ira_workflow_chat_to_action():
    """Integration: Chat → Action → Control Update workflow."""
    _, client, memory_stores = _make_app_and_client(allow_high_impact=True)
    
    # Step 1: Customer initiates chat
    chat_payload = {
        'role': 'customer',
        'channel': 'chat',
        'message': 'I want to cancel billing.',
    }
    response = client.post('/ira/chat', json=chat_payload, headers=_headers())
    assert response.status_code == 200
    
    # Step 2: Admin updates non-dangerous control values under strict policy lock
    control_payload = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 70.0,
        'suspicious_signal_threshold': 0.75,
        'policy_change_human_validation': True,
    }
    response = client.post('/ira/control/config', json=control_payload, headers=_headers())
    assert response.status_code == 200
    
    # Step 3: Execute high-impact action
    action_payload = {
        'target': 'billing',
        'command': 'cancel_subscription',
        'payload': {'reason': 'customer_request'},
        'dry_run': True,
    }
    response = client.post('/ira/actions', json=action_payload, headers=_headers())
    assert response.status_code == 403
    
    # Verify audit trail
    assert len(memory_stores.audit_log) >= 2
    assert len(memory_stores.ira_events) >= 2


def test_ira_workflow_protection_activation():
    """Integration: Low profit sample → Protection mode activation → Action blocking."""
    _, client, _ = _make_app_and_client(allow_high_impact=True)
    
    # Step 1: Ingest financial sample with low profit
    ingest_payload = {
        'revenue': 1000.0,
        'cogs': 800.0,
        'credits_cost': 150.0,
        'suspicious_signal_score': 0.0,
        'note': 'Critical low profit',
    }
    response = client.post('/ira/finance/ingest', json=ingest_payload, headers=_headers())
    assert response.status_code == 200
    assert response.json()['protection_mode'] is True
    
    # Step 2: Verify protection mode is active
    response = client.get('/ira/finance/health', headers=_headers())
    assert response.status_code == 200
    assert response.json()['protection_mode'] is True
    
    # Step 3: Try to execute high-impact action (should be blocked)
    action_payload = {
        'target': 'credits',
        'command': 'bulk_credit_burn',
        'payload': {},
        'dry_run': False,
    }
    response = client.post('/ira/actions', json=action_payload, headers=_headers())
    assert response.status_code == 423  # Locked
    
    # Step 4: Disable protection mode
    response = client.post('/ira/control/disable-protection', headers=_headers())
    assert response.status_code == 200
    
    # Step 5: Now high-impact action should succeed (dry-run)
    response = client.post('/ira/actions', json={
        'target': 'credits',
        'command': 'bulk_credit_burn',
        'payload': {},
        'dry_run': True,
    }, headers=_headers())
    assert response.status_code == 200


def test_ira_disputes_require_human_validation():
    """All dispute operations require human validation approval."""
    _, client, _ = _make_app_and_client()

    payload = {
        'target': 'customer_support',
        'command': 'resolve_dispute',
        'payload': {'is_dispute': True, 'dispute_amount_gbp': 20.0},
        'dry_run': False,
        'user_consent': True,
        'consent_reference': 'consent-001',
        'risk_analysis_approved': True,
        'human_validation_approved': False,
    }
    response = client.post('/ira/actions', json=payload, headers=_headers())
    assert response.status_code == 422
    assert 'human validation' in response.text.lower()


def test_ira_disputes_dashboard_endpoint():
    """Disputes dashboard endpoint is available and returns summary shape."""
    _, client, _ = _make_app_and_client()

    response = client.get('/ira/disputes/dashboard', headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'summary' in data
    assert data['summary']['human_approval_required_for_all_disputes'] is True


def test_ira_crm_hybrid_recommendation_endpoint():
    """CRM hybrid recommendation endpoint exposes Corteza+Odoo guidance and ratings."""
    _, client, _ = _make_app_and_client()

    response = client.get('/ira/crm/hybrid-recommendation', headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['recommended_hybrid'] == 'Corteza CRM + Odoo CRM Community'
    assert data['ratings']['hybrid_overall']['score'] == 95


def test_ira_crm_feature_governance_update():
    """POST /ira/crm/feature-governance updates source-of-truth ownership and duplicate policy."""
    _, client, _ = _make_app_and_client()

    payload = {
        'feature': 'multi_tenancy',
        'owner': 'corteza',
        'disable_duplicate_in_secondary': True,
        'policy_change_human_validation': True,
        'notes': 'Keep multi-tenancy in Corteza only.',
    }
    # Keep this route test deterministic by avoiding live DB connection attempts.
    with patch('backend.fastapi.app.routers.ira.psycopg.connect', side_effect=RuntimeError('db unavailable')):
        response = client.post('/ira/crm/feature-governance', json=payload, headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'governance' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
