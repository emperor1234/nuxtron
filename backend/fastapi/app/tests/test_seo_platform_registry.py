"""
Targeted tests for the SEO platform module registry and performance audit endpoints.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')


def _make_client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=True)


def _headers() -> dict[str, str]:
    return {
        'X-API-Key': os.getenv('FASTAPI_API_KEY', 'test-api-key'),
        'X-Tenant-Id': 'test-tenant',
    }


@pytest.fixture
def client() -> TestClient:
    return _make_client()


def test_seo_module_registry_returns_all_catalog_entries(client: TestClient) -> None:
    response = client.get('/seo-platform/modules', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    assert data['total'] == len(data['modules'])
    assert data['total'] >= 51
    assert any(module['key'] == 'performance-audit' for module in data['modules'])
    assert any(group['group'] for group in data['groups'])


def test_seo_module_detail_returns_gtmetrix_style_module(client: TestClient) -> None:
    response = client.get('/seo-platform/modules/performance-audit', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    module = data['module']
    assert module['key'] == 'performance-audit'
    assert module['display_name'] == 'GTmetrix-Style Performance Audit'
    assert module['route_path'] == '/seo/performance'
    assert 'lighthouse' in module['integrations']


def test_ahrefs_parity_audit_endpoint_returns_tool_matrix(client: TestClient) -> None:
    response = client.get('/seo-platform/ahrefs/parity', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    audit = data['audit']
    assert audit['total_tools'] >= 10
    assert any(row['tool_key'] == 'site-explorer' for row in audit['rows'])
    assert all(row['route_path'].startswith('/seo/') for row in audit['rows'])


def test_seo_performance_audit_returns_structured_payload(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        return {
            'performance_score': 91,
            'core_web_vitals': {
                'lcp_ms': 1800,
                'inp_ms': 120,
                'cls': 0.03,
                'ttfb_ms': 280,
            },
            'lighthouse': {
                'performance': 91,
                'seo': 98,
                'best_practices': 94,
            },
            'waterfall': {
                'requests': 32,
                'transfer_kb': 540,
                'render_blocking': ['main.css'],
            },
            'opportunities': [
                {
                    'priority': 'high',
                    'issue': 'Reduce CSS payload',
                    'impact': 'Improve LCP by ~180ms',
                }
            ],
            'recommended_stack': ['lighthouse', 'playwright_cdp', 'web_vitals'],
        }

    async def fake_free_stack(req):
        return None

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)
    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    response = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={
            'url': 'https://example.com',
            'target_device': 'mobile',
            'target_region': 'lhr1',
            'notes': 'baseline run',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['analysis_id']
    assert data['url'] == 'https://example.com'
    assert data['target_device'] == 'mobile'
    assert data['performance_score'] == 91
    assert data['core_web_vitals']['lcp_ms'] == 1800
    assert 'lighthouse' in data['recommended_stack']


def test_seo_performance_audit_merges_free_provider_data(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        return {
            'performance_score': 64,
            'core_web_vitals': {'lcp_ms': 2600, 'inp_ms': 210, 'cls': 0.11, 'ttfb_ms': 410},
            'field_web_vitals': {'source': 'ai_estimate'},
            'lighthouse': {'performance': 64, 'seo': 90, 'best_practices': 88},
            'waterfall': {'requests': 48},
            'recommended_stack': ['ollama'],
        }

    async def fake_free_stack(req):
        return {
            'performance_score': 96,
            'core_web_vitals': {'lcp_ms': 1500, 'inp_ms': 90, 'cls': 0.02, 'ttfb_ms': 190},
            'field_web_vitals': {'source': 'crux'},
            'lighthouse': {'performance': 96, 'seo': 99, 'best_practices': 97},
            'waterfall': {'requests': 28},
            'filmstrip': [{'label': 'fcp', 'timestamp_ms': 800}],
            'rum_summary': {'sessions': 1234},
            'history': {'trend': 'improving'},
            'recommended_stack': ['lighthouse_cli', 'pagespeed_insights_api', 'web_vitals_rum'],
            'vendor_stack': [{'vendor': 'Lighthouse CLI', 'usage': 'Local synthetic audits'}],
            'free_provider_status': {
                'lighthouse_cli': True,
                'pagespeed_api': True,
                'crux_api': True,
                'webpagetest_public': False,
            },
            'data_provenance': {'source': 'free_providers', 'at': '2026-05-24T00:00:00+00:00'},
        }

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)
    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    response = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={
            'url': 'https://example.com',
            'target_device': 'mobile',
            'target_region': 'lhr1',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['performance_score'] == 96
    assert data['core_web_vitals']['lcp_ms'] == 1500
    assert data['field_web_vitals']['source'] == 'crux'
    assert data['free_provider_status']['pagespeed_api'] is True
    assert data['data_provenance']['source'] == 'free_providers'
    assert data['recommended_stack'][0] == 'lighthouse_cli'


def test_seo_performance_audit_sets_explicit_provenance_without_free_providers(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        return {
            'performance_score': 77,
            'field_web_vitals': {'source': 'web_vitals_rum'},
        }

    async def fake_free_stack(req):
        return None

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)
    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    response = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={
            'url': 'https://example.com',
            'target_device': 'mobile',
            'target_region': 'lhr1',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['performance_score'] == 77
    assert data['free_provider_status'] == {
        'lighthouse_cli': False,
        'pagespeed_api': False,
        'crux_api': False,
        'webpagetest_public': False,
        'web_vitals_rum': False,
    }
    assert data['data_provenance']['source'] == 'ai_only'


def test_performance_rum_ingest_summary_and_audit_merge(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        return {
            'performance_score': 71,
            'lighthouse': {'performance': 71, 'seo': 92, 'best_practices': 90},
        }

    async def fake_free_stack(req):
        return None

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)
    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    url = 'https://rum-merge.example.com'
    for metric_name, value, rating in [('LCP', 1800, 'good'), ('INP', 120, 'good'), ('CLS', 0.03, 'good')]:
        ingested = client.post(
            '/seo-platform/performance/rum/ingest',
            headers=_headers(),
            json={
                'url': url,
                'page_url': f'{url}/landing',
                'metric_name': metric_name,
                'value': value,
                'rating': rating,
                'session_id': 'rum-session-1',
                'device_type': 'desktop',
                'effective_connection_type': '4g',
            },
        )
        assert ingested.status_code == 200
        assert ingested.json()['accepted'] is True

    summary = client.get(f'/seo-platform/performance/rum/summary?url={url}', headers=_headers())
    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data['available'] is True
    assert summary_data['rollup']['field_web_vitals']['source'] == 'web_vitals_rum'
    assert summary_data['rollup']['rum_summary']['sessions'] == 1

    audit = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={
            'url': url,
            'target_device': 'mobile',
            'target_region': 'lhr1',
        },
    )
    assert audit.status_code == 200
    audit_data = audit.json()
    assert audit_data['field_web_vitals']['source'] == 'web_vitals_rum'
    assert audit_data['rum_summary']['sessions'] == 1
    assert audit_data['free_provider_status']['web_vitals_rum'] is True
    assert audit_data['data_provenance']['source'] == 'rum+ai'
    assert audit_data['performance_score'] == 96


def test_performance_capabilities_and_catalog_endpoints(client: TestClient) -> None:
    capabilities = client.get('/seo-platform/performance/capabilities', headers=_headers())
    assert capabilities.status_code == 200
    cap_data = capabilities.json()
    assert cap_data['coverage_pct'] >= 90
    assert any(row['feature'] == 'Recurring monitor configuration' for row in cap_data['features'])
    assert any(row['feature'] == 'Free provider stack orchestration' for row in cap_data['features'])
    assert any(source['name'] == 'PageSpeed Insights API' for source in cap_data['data_sources']['free_provider_stack'])

    locations = client.get('/seo-platform/performance/test-locations', headers=_headers())
    assert locations.status_code == 200
    assert locations.json()['count'] >= 8

    browsers = client.get('/seo-platform/performance/browser-profiles', headers=_headers())
    assert browsers.status_code == 200
    assert browsers.json()['count'] >= 4


def test_performance_monitor_create_run_and_report(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        return {
            'performance_score': 93,
            'core_web_vitals': {'lcp_ms': 1700, 'inp_ms': 110, 'cls': 0.02, 'ttfb_ms': 250},
            'lighthouse': {'performance': 93, 'seo': 97, 'best_practices': 95},
            'waterfall': {'requests': 30, 'transfer_kb': 520, 'render_blocking': ['main.css']},
            'recommended_stack': ['lighthouse', 'playwright_cdp', 'web_vitals'],
        }

    async def fake_free_stack(req):
        return None

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)
    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    created = client.post(
        '/seo-platform/performance/monitor/create',
        headers=_headers(),
        json={
            'name': 'Checkout Daily',
            'url': 'https://example.com/checkout',
            'schedule': 'daily',
            'target_device': 'mobile',
            'target_region': 'iad1',
            'connection': '4g',
            'browser': 'chrome',
            'include_video': True,
            'adblock_enabled': False,
            'capture_har': True,
            'alerts_enabled': True,
        },
    )
    assert created.status_code == 200
    monitor_id = created.json()['monitor_id']

    listed = client.get('/seo-platform/performance/monitors', headers=_headers())
    assert listed.status_code == 200
    assert any(m['monitor_id'] == monitor_id for m in listed.json()['monitors'])

    ran = client.post(f'/seo-platform/performance/monitors/{monitor_id}/run', headers=_headers())
    assert ran.status_code == 200
    run_data = ran.json()
    assert run_data['analysis_id']
    assert run_data['performance_score'] == 93

    report = client.get(f"/seo-platform/performance/report/{run_data['analysis_id']}", headers=_headers())
    assert report.status_code == 200
    report_data = report.json()
    assert report_data['module'] == 'performance_audit'
    assert report_data['result']['performance_score'] == 93

    history = client.get('/seo-platform/performance/history?url=https://example.com/checkout', headers=_headers())
    assert history.status_code == 200
    assert history.json()['count'] >= 1


def test_performance_advanced_parity_endpoints(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import seo_platform

    async def fake_ollama_json(system: str, prompt: str):
        if 'candidate' in prompt.lower():
            return {
                'performance_score': 88,
                'core_web_vitals': {'lcp_ms': 2100, 'inp_ms': 180, 'cls': 0.06, 'ttfb_ms': 350},
                'lighthouse': {'performance': 88, 'seo': 95, 'best_practices': 92},
                'waterfall': {'requests': 34, 'transfer_kb': 560, 'render_blocking': ['main.css']},
            }
        return {
            'performance_score': 94,
            'core_web_vitals': {'lcp_ms': 1650, 'inp_ms': 105, 'cls': 0.02, 'ttfb_ms': 230},
            'field_web_vitals': {'lcp_p75_ms': 1700, 'inp_p75_ms': 110, 'cls_p75': 0.03, 'sample_size': 1200},
            'lighthouse': {'performance': 94, 'seo': 97, 'best_practices': 96},
            'waterfall': {'requests': 29, 'transfer_kb': 490, 'render_blocking': ['main.css']},
        }

    monkeypatch.setattr(seo_platform, '_ollama_json', fake_ollama_json)

    async def fake_free_stack(req):
        return None

    monkeypatch.setattr(seo_platform, '_run_free_performance_stack', fake_free_stack)

    vendors = client.get('/seo-platform/performance/vendors', headers=_headers())
    assert vendors.status_code == 200
    assert any(v['name'] == 'Chrome UX Report (CrUX)' for v in vendors.json()['third_parties'])
    assert any(v['name'] == 'web-vitals RUM' for v in vendors.json()['free_provider_stack'])

    baseline = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={'url': 'https://example.com/checkout', 'target_device': 'mobile', 'target_region': 'lhr1', 'notes': 'baseline'},
    )
    assert baseline.status_code == 200
    base_id = baseline.json()['analysis_id']

    candidate = client.post(
        '/seo-platform/performance/audit',
        headers=_headers(),
        json={'url': 'https://example.com/checkout', 'target_device': 'mobile', 'target_region': 'lhr1', 'notes': 'candidate'},
    )
    assert candidate.status_code == 200
    cand_id = candidate.json()['analysis_id']

    compare = client.post(
        '/seo-platform/performance/reports/compare',
        headers=_headers(),
        json={'baseline_analysis_id': base_id, 'candidate_analysis_id': cand_id},
    )
    assert compare.status_code == 200
    assert compare.json()['baseline_analysis_id'] == base_id
    assert 'core_web_vitals_delta' in compare.json()

    share = client.post(
        f'/seo-platform/performance/report/{base_id}/share',
        headers=_headers(),
        json={'expires_hours': 24, 'visibility': 'token'},
    )
    assert share.status_code == 200
    share_token = share.json()['share_token']
    shared = client.get(f'/seo-platform/performance/report/shared/{share_token}', headers=_headers())
    assert shared.status_code == 200
    assert shared.json()['analysis_id'] == base_id

    test_create = client.post(
        '/seo-platform/performance/tests',
        headers=_headers(),
        json={'url': 'https://example.com/checkout', 'target_device': 'mobile', 'target_region': 'lhr1'},
    )
    assert test_create.status_code == 200
    test_id = test_create.json()['test_id']
    final_status = None
    for _ in range(30):
        polled = client.get(f'/seo-platform/performance/tests/{test_id}', headers=_headers())
        assert polled.status_code == 200
        status = polled.json()['status']
        final_status = status
        if status in {'completed', 'failed'}:
            break
    assert final_status == 'completed'

    crux = client.get('/seo-platform/performance/crux/history?url=https://example.com/checkout&months=6', headers=_headers())
    assert crux.status_code == 200
    assert crux.json()['source'] == 'crux-style'

    monitor = client.post(
        '/seo-platform/performance/monitor/create',
        headers=_headers(),
        json={
            'name': 'Checkout Alert Monitor',
            'url': 'https://example.com/checkout',
            'schedule': 'daily',
            'target_device': 'mobile',
            'target_region': 'iad1',
            'alert_channels': ['email', 'slack'],
            'alert_targets': ['ops@example.com'],
            'alert_lcp_ms_threshold': 1200,
            'alert_inp_ms_threshold': 100,
            'alert_cls_threshold': 0.01,
        },
    )
    assert monitor.status_code == 200
    monitor_id = monitor.json()['monitor_id']
    run_monitor = client.post(f'/seo-platform/performance/monitors/{monitor_id}/run', headers=_headers())
    assert run_monitor.status_code == 200
    events = client.get('/seo-platform/performance/alerts/events', headers=_headers())
    assert events.status_code == 200
    assert isinstance(events.json()['events'], list)