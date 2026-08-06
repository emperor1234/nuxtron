import { expect, test } from '@playwright/test';

function parityResponse() {
  return {
    status: 'ok',
    semrush_parity_chart: [
      {
        module: 'site_audit_and_crawler_enablement',
        implemented: true,
        coverage_pct: 100,
        evidence: ['ai_crawler sites/snippet/verify/events/dashboard'],
      },
      {
        module: 'keyword_research',
        implemented: true,
        coverage_pct: 100,
        evidence: ['rank_tracker keyword-research sources and vendors endpoints'],
      },
    ],
    summary: {
      modules_total: 5,
      modules_implemented: 5,
      implementation_pct: 100,
      integration_configured_units: 12,
      integration_total_units: 12,
      integration_configured_pct: 100,
    },
    vendor_inventory: [
      { domain: 'search-everywhere', vendor: 'Cloudflare', capability: 'crawler enablement', configured: true, evidence: 'mock' },
      { domain: 'search-everywhere', vendor: 'DataForSEO', capability: 'keyword research', configured: true, evidence: 'mock' },
    ],
    validation_note: 'Parity reflects live backend feature coverage.',
  };
}

function checklistResponse() {
  return {
    status: 'ok',
    configured: 12,
    total: 12,
    configured_pct: 100,
    checklist: [
      { provider: 'DataForSEO', kind: 'keyword_provider', configured: true, required_missing: [] },
      { provider: 'Cloudflare', kind: 'crawler_enablement', configured: true, required_missing: [] },
    ],
  };
}

function projectsResponse() {
  return {
    status: 'ok',
    projects: [{ id: 'semrush-proj-1', name: 'Semrush Command Center Project', primary_domain: 'nuxtron.ai' }],
  };
}

function runsResponse() {
  return {
    status: 'ok',
    runs: [{ id: 'semrush-run-1', project_id: 'semrush-proj-1', strict_probe_status: 'passed', completed_at: new Date().toISOString() }],
  };
}

function productionGateResponse() {
  return {
    status: 'ok',
    gate: { passed: true, implementation_ok: true, integration_ok: true, strict_probe_ok: true, blockers: [] },
    provider_checklist_summary: { configured: 12, total: 12, missing_requirements: [] },
  };
}

function bootstrapResponse() {
  return {
    status: 'ok',
    requested_providers: ['dataforseo', 'serper.dev'],
    steps_total: 2,
    steps: [
      { provider: 'DataForSEO', kind: 'keyword_provider', required_missing: [] },
      { provider: 'Cloudflare', kind: 'crawler_enablement', required_missing: [] },
    ],
    next: { run_checklist: 'GET /search-everywhere/semrush/provider-checklist', run_gate: 'POST /search-everywhere/semrush/production-gate' },
  };
}

function probeResponse() {
  return {
    status: 'ok',
    summary: { providers_requested: 4, passed: 4, failed: 0, skipped: 0, strict_live_ready: true },
    probes: [{ provider: 'dataforseo', status: 'passed' }, { provider: 'serper', status: 'passed' }],
  };
}

function envTemplateResponse() {
  return {
    status: 'ok',
    include_optional: true,
    include_configured: false,
    providers_included: ['DataForSEO', 'Serper.dev', 'Cloudflare'],
    missing_keys: ['DATAFORSEO_LOGIN', 'DATAFORSEO_API_KEY'],
    filename: 'semrush-provider-template-tenant-demo.env',
    env_template: 'DATAFORSEO_LOGIN=\nDATAFORSEO_API_KEY=\nSERPER_API_KEY=',
  };
}

function fullAutomationResponse() {
  return {
    status: 'ok',
    run_mode: 'hybrid_with_resilient_fallback',
    results: {
      keyword_discovery: { provider_selected: 'DataForSEO', keywords_analyzed: 42, clusters_found: 7 },
      content_gap: { total_opportunities: 18, high_coverage_gaps: 6 },
      backlink_audit: { risk_level: 'low', toxic_count: 1, suspicious_count: 0 },
      backlink_gap: { unique_opportunities: 24, competitors_analyzed: 3 },
    },
    providers: {
      vendor_inventory: [
        { domain: 'search-everywhere', vendor: 'DataForSEO', capability: 'keyword research', configured: true, evidence: 'mock' },
        { domain: 'search-everywhere', vendor: 'Cloudflare', capability: 'crawler enablement', configured: true, evidence: 'mock' },
      ],
    },
    how_it_works: [
      'Keyword discovery starts with live provider-backed research.',
      'Content gap and backlink workflows turn signal deltas into prioritized actions.',
      'Parity and provider inventories keep implementation and wiring visible.',
      'The production gate separates feature coverage from strict live readiness.',
    ],
    production_gate: { passed: true, blockers: [] },
  };
}

function semrushApiResponse(pathname: string, method: string) {
  if (method === 'POST' && pathname.startsWith('/api/fastapi/search-everywhere/semrush/projects/') && pathname.endsWith('/run')) {
    return { status: 'ok', run: { id: 'semrush-run-new', project_id: 'semrush-proj-1', strict_probe_status: 'passed', completed_at: new Date().toISOString() } };
  }

  const responseMap: Record<string, unknown> = {
    'GET /api/fastapi/search-everywhere/semrush/parity-audit': parityResponse(),
    'GET /api/fastapi/search-everywhere/semrush/provider-checklist': checklistResponse(),
    'GET /api/fastapi/search-everywhere/semrush/projects': projectsResponse(),
    'GET /api/fastapi/search-everywhere/semrush/runs': runsResponse(),
    'POST /api/fastapi/search-everywhere/semrush/projects': { status: 'ok', project: { id: 'semrush-proj-new', name: 'Semrush Command Center Project', primary_domain: 'nuxtron.ai' } },
    'POST /api/fastapi/search-everywhere/semrush/production-gate': productionGateResponse(),
    'POST /api/fastapi/search-everywhere/semrush/provider-bootstrap': bootstrapResponse(),
    'POST /api/fastapi/search-everywhere/semrush/provider-probes': probeResponse(),
    'POST /api/fastapi/search-everywhere/semrush/env-template': envTemplateResponse(),
    'POST /api/fastapi/search-everywhere/semrush/full-automation': fullAutomationResponse(),
  };

  return responseMap[`${method} ${pathname}`] ?? null;
}

async function mockSemrushApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/semrush/**', async (route) => {
    const url = new URL(route.request().url());
    const body = semrushApiResponse(url.pathname, route.request().method());
    if (body === null) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'mock route not found' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

test.describe('Semrush command center', () => {
  test('renders live parity and production gate controls', async ({ page }) => {
    await mockSemrushApis(page);
    await page.goto('/seo/semrush-command-center');

    await expect(page.getByRole('heading', { name: 'Semrush End-to-End SEO Operations' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Semrush Parity Chart' })).toBeVisible();
    await expect(page.getByText('5/5')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Rank Tracking' }).first()).toBeVisible();

    await page.getByRole('button', { name: 'Run Production Gate' }).click();
    const gateCard = page.getByRole('heading', { name: 'Production Gate', exact: true }).first().locator('xpath=ancestor::article[1]');
    await expect(gateCard).toBeVisible({ timeout: 20000 });
    await expect(gateCard).toContainText('PASSED');
  });

  test('runs bootstrap, probes, env template, and full automation', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockSemrushApis(page);
    await page.goto('/seo/semrush-command-center');

    await page.getByRole('button', { name: 'Bootstrap Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Bootstrap', exact: true }).first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole('listitem').filter({ hasText: 'DataForSEO' }).first()).toBeVisible();

    await page.getByRole('button', { name: 'Probe Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Probes' })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Strict live ready: Yes')).toBeVisible();

    await page.getByRole('button', { name: 'Generate Env Template' }).click();
    await expect(page.getByRole('heading', { name: 'Environment Template' })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('semrush-provider-template-tenant-demo.env')).toBeVisible();

    await page.getByRole('button', { name: 'Run Full Automation Blueprint' }).click();
    await expect(page.getByRole('heading', { name: 'Automation Blueprint' })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Keyword discovery starts with live provider-backed research.')).toBeVisible();
    await expect(page.getByText('Vendor inventory: 2')).toBeVisible();
  });
});