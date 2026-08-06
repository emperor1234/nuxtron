import { expect, test } from '@playwright/test';

function parityResponse() {
  return {
    status: 'ok',
    ahrefs_parity_chart: [
      {
        module: 'site_explorer_and_crawl_intelligence',
        implemented: true,
        coverage_pct: 100,
        evidence: ['GET /ai-crawler/sites', 'GET /search-everywhere/readiness'],
      },
      {
        module: 'keyword_explorer_and_serp_monitoring',
        implemented: true,
        coverage_pct: 100,
        evidence: ['POST /rank-tracker/keyword-research/discover'],
      },
    ],
    ahrefs_core_tools: [
      {
        tool_key: 'site-explorer',
        tool_name: 'Site Explorer',
        route_path: '/seo/site-explorer',
        parity_module_key: 'ahrefs-site-explorer',
        counterpart_module_key: 'domain-overview',
        coverage_pct: 100,
        vendors: ['DataForSEO'],
      },
      {
        tool_key: 'keywords-explorer',
        tool_name: 'Keywords Explorer',
        route_path: '/seo/keywords-explorer',
        parity_module_key: 'ahrefs-keywords-explorer',
        counterpart_module_key: 'seo-ai',
        coverage_pct: 100,
        vendors: ['Serper.dev'],
      },
    ],
    completion_chart: {
      core_tools: { done: 19, total: 19, pct: 100 },
      automation_layers: { done: 6, total: 6, pct: 100 },
      provider_wiring: { done: 4, total: 4, pct: 100 },
    },
    summary: {
      modules_total: 6,
      modules_implemented: 6,
      implementation_pct: 100,
      integration_configured_units: 4,
      integration_total_units: 4,
      integration_configured_pct: 100,
      core_tools_total: 19,
      core_tools_fully_covered: 19,
      core_tools_average_coverage_pct: 100,
    },
    vendor_inventory: [
      { domain: 'search-everywhere', vendor: 'DataForSEO', capability: 'keyword research', configured: true, evidence: 'mock' },
      { domain: 'search-everywhere', vendor: 'Serper.dev', capability: 'serp intelligence', configured: true, evidence: 'mock' },
    ],
    validation_note: 'Implementation percentage reflects feature availability.',
  };
}

function checklistResponse() {
  return {
    status: 'ok',
    configured: 4,
    total: 4,
    configured_pct: 100,
    checklist: [
      { provider: 'DataForSEO', kind: 'keyword_provider', configured: true, required_missing: [] },
      { provider: 'Serper.dev', kind: 'search_provider', configured: true, required_missing: [] },
    ],
  };
}

function e2eVerificationResponse() {
  return {
    status: 'ok',
    framework: 'ahrefs',
    automation_endpoints: [
      'GET /search-everywhere/ahrefs/parity-audit',
      'GET /search-everywhere/ahrefs/e2e-verification',
      'GET /search-everywhere/ahrefs/provider-checklist',
      'POST /search-everywhere/ahrefs/provider-bootstrap',
      'POST /search-everywhere/ahrefs/provider-probes',
      'POST /search-everywhere/ahrefs/env-template',
      'POST /search-everywhere/ahrefs/production-gate',
      'POST /search-everywhere/ahrefs/full-automation',
    ],
    provider_wiring_summary: { configured: 4, total: 4, configured_pct: 100 },
  };
}

function productionGateResponse() {
  return {
    status: 'ok',
    gate: { passed: true, implementation_ok: true, integration_ok: true, strict_probe_ok: true, blockers: [] },
    strict_live_probe: { status: 'passed', run_mode: 'strict_live_only', provider_selected: 'dataforseo' },
    provider_checklist_summary: { configured: 4, total: 4, missing_requirements: [] },
  };
}

function bootstrapResponse() {
  return {
    status: 'ok',
    requested_providers: ['dataforseo', 'serper.dev'],
    steps_total: 2,
    steps: [
      { step: 1, provider: 'DataForSEO', kind: 'keyword_provider', status: 'configured', required_missing: [] },
      { step: 2, provider: 'Serper.dev', kind: 'search_provider', status: 'configured', required_missing: [] },
    ],
    next: { run_checklist: 'GET /search-everywhere/ahrefs/provider-checklist', run_gate: 'POST /search-everywhere/ahrefs/production-gate' },
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
    providers_included: ['DataForSEO', 'Serper.dev', 'Google Ads Keyword Planner', 'Google Search Console'],
    missing_keys: ['DATAFORSEO_LOGIN', 'DATAFORSEO_API_KEY'],
    filename: 'ahrefs-provider-template-tenant-demo.env',
    env_template: 'DATAFORSEO_LOGIN=\nDATAFORSEO_API_KEY=\nSERPER_API_KEY=',
  };
}

function fullAutomationResponse() {
  return {
    status: 'ok',
    run_mode: 'hybrid_with_resilient_fallback',
    results: {
      keyword_discovery: { provider_selected: 'DataForSEO', keywords_analyzed: 42, clusters_found: 7 },
      content_gap: { provider_selected: 'DataForSEO', total_opportunities: 18, high_coverage_gaps: 6 },
      backlink_overview: { authority_score: 65, referring_domains: 320, toxic_count: 2, suspicious_count: 1 },
      backlink_audit: { risk_level: 'low', overall_risk_pct: 12, toxic_count: 2, suspicious_count: 1 },
      backlink_gap: { unique_opportunities: 24, competitors_analyzed: 3 },
      rank_tracking: { tracked_keywords: 500, visibility_score: 71.4, top_10: 221 },
    },
    providers: {
      vendor_inventory: [
        { domain: 'search-everywhere', vendor: 'DataForSEO', capability: 'keyword research', configured: true, evidence: 'mock' },
        { domain: 'search-everywhere', vendor: 'Serper.dev', capability: 'serp intelligence', configured: true, evidence: 'mock' },
      ],
    },
    how_it_works: [
      { stage: 1, name: 'discover_and_cluster', description: 'Resolve keywords with live provider intelligence.' },
      { stage: 2, name: 'compare_and_gap_analyze', description: 'Compare domain and competitors for ranked opportunities.' },
    ],
  };
}

function ahrefsApiResponse(pathname: string, method: string) {
  const responseMap: Record<string, unknown> = {
    'GET /api/fastapi/search-everywhere/ahrefs/parity-audit': parityResponse(),
    'GET /api/fastapi/search-everywhere/ahrefs/provider-checklist': checklistResponse(),
    'GET /api/fastapi/search-everywhere/ahrefs/e2e-verification': e2eVerificationResponse(),
    'POST /api/fastapi/search-everywhere/ahrefs/production-gate': productionGateResponse(),
    'POST /api/fastapi/search-everywhere/ahrefs/provider-bootstrap': bootstrapResponse(),
    'POST /api/fastapi/search-everywhere/ahrefs/provider-probes': probeResponse(),
    'POST /api/fastapi/search-everywhere/ahrefs/env-template': envTemplateResponse(),
    'POST /api/fastapi/search-everywhere/ahrefs/full-automation': fullAutomationResponse(),
  };

  return responseMap[`${method} ${pathname}`] ?? null;
}

async function mockAhrefsApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/ahrefs/**', async (route) => {
    const url = new URL(route.request().url());
    const body = ahrefsApiResponse(url.pathname, route.request().method());
    if (body === null) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'mock route not found' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

test.describe('Ahrefs command center', () => {
  test('renders parity and e2e verification sections', async ({ page }) => {
    await mockAhrefsApis(page);
    await page.goto('/seo/ahrefs-command-center');

    await expect(page.getByRole('heading', { name: 'Ahrefs End-to-End SEO Operations' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Ahrefs Parity Chart' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'E2E Verification Surface' })).toBeVisible();
    await expect(page.getByText('19/19')).toBeVisible();
  });

  test('runs gate, bootstrap, probes, env template, and full automation actions', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockAhrefsApis(page);
    await page.goto('/seo/ahrefs-command-center');

    await page.getByRole('button', { name: 'Run Production Gate' }).click();
    const gateCard = page.getByRole('heading', { name: 'Production Gate' }).first().locator('xpath=ancestor::article[1]');
    await expect(gateCard).toBeVisible({ timeout: 20000 });
    await expect(gateCard).toContainText('PASSED');

    await page.getByRole('button', { name: 'Bootstrap Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Bootstrap', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('DataForSEO').first()).toBeVisible();

    await page.getByRole('button', { name: 'Probe Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Probes', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Strict live ready: Yes')).toBeVisible();

    await page.getByRole('button', { name: 'Generate Env Template' }).click();
    await expect(page.getByRole('heading', { name: 'Environment Template', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('ahrefs-provider-template-tenant-demo.env')).toBeVisible();

    await page.getByRole('button', { name: 'Run Full Automation Blueprint' }).click();
    await expect(page.getByRole('heading', { name: 'Automation Blueprint', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('discover_and_cluster')).toBeVisible();
    await expect(page.getByText('Vendor inventory: 2')).toBeVisible();
  });
});
