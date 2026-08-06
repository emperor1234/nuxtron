import { expect, test } from '@playwright/test';

function parityResponse() {
  return {
    status: 'ok',
    surfer_parity_chart: [
      {
        module: 'content_editor_and_content_score',
        implemented: true,
        coverage_pct: 100,
        evidence: ['POST /seo-platform/content/brief', 'POST /seo-platform/content/write'],
      },
      {
        module: 'keyword_research_and_serp_analysis',
        implemented: true,
        coverage_pct: 100,
        evidence: ['POST /rank-tracker/keyword-research/discover', 'GET /rank-tracker/positions'],
      },
    ],
    summary: {
      modules_total: 8,
      modules_implemented: 8,
      implementation_pct: 100,
      integration_configured_units: 12,
      integration_total_units: 12,
      integration_configured_pct: 100,
    },
    vendor_inventory: [
      { vendor: 'DataForSEO', module: 'keyword_provider', type: 'integration', configured: true, evidence: 'mock' },
      { vendor: 'OpenAI', module: 'ai_content_generation', type: 'integration', configured: true, evidence: 'mock' },
    ],
    validation_note: 'Implementation percentage reflects feature availability; integration percentage reflects provider wiring completeness.',
  };
}

function checklistResponse() {
  return {
    status: 'ok',
    configured: 12,
    total: 12,
    configured_pct: 100,
    checklist: [
      {
        provider: 'DataForSEO',
        kind: 'keyword_provider',
        configured: true,
        required_missing: [],
        remediation: 'Configure missing required env vars and validate strict-live probe.',
      },
      {
        provider: 'OpenAI',
        kind: 'ai_content_generation',
        configured: true,
        required_missing: [],
        remediation: 'Configure missing required env vars and validate strict-live probe.',
      },
    ],
  };
}

function wiringPlanResponse() {
  return {
    status: 'ok',
    wiring_plan: {
      configured: 12,
      total: 12,
      integration_configured_pct: 100,
      stages: {
        stage_1_strict_live_foundation: { providers: [] },
        stage_2_runtime_reliability: { providers: [] },
        stage_3_full_automation_coverage: { providers: [] },
      },
      prioritized_missing_providers: [],
    },
  };
}

function setupPlaybookResponse() {
  return {
    status: 'ok',
    setup_playbook: {
      summary: { configured: 12, total: 12, integration_configured_pct: 100 },
      providers: [
        {
          provider: 'DataForSEO',
          priority: 'P0',
          kind: 'keyword_provider',
          gate_impact_score: 100,
          integration_pct_if_added: 100,
          required_missing: [],
          setup_notes: ['Create DataForSEO account credentials and whitelist your backend egress IPs.'],
          preflight_commands_powershell: ['Test-Path Env:DATAFORSEO_LOGIN'],
          verify_with: ['POST /search-everywhere/surfer/provider-probes', 'POST /search-everywhere/surfer/production-gate'],
        },
      ],
      final_validation: [
        'GET /search-everywhere/surfer/provider-checklist',
        'POST /search-everywhere/surfer/provider-probes',
        'POST /search-everywhere/surfer/production-gate',
      ],
    },
  };
}

function productionGateResponse() {
  return {
    status: 'ok',
    gate: { passed: true, implementation_ok: true, integration_ok: true, strict_probe_ok: true, blockers: [] },
    strict_live_probe: { status: 'passed', run_mode: 'strict_live_only', provider_selected: 'dataforseo' },
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
      { provider: 'Serper.dev', kind: 'keyword_provider', required_missing: [] },
    ],
    next: { run_checklist: 'GET /search-everywhere/surfer/provider-checklist', run_gate: 'POST /search-everywhere/surfer/production-gate' },
  };
}

function probeResponse() {
  return {
    status: 'ok',
    summary: { providers_requested: 4, passed: 4, failed: 0, skipped: 0, strict_live_ready: true },
    probes: [
      { provider: 'DataForSEO', status: 'passed' },
      { provider: 'Serper.dev', status: 'passed' },
    ],
  };
}

function envTemplateResponse() {
  return {
    status: 'ok',
    include_optional: true,
    include_configured: false,
    providers_included: ['DataForSEO', 'Serper.dev', 'OpenAI'],
    missing_keys: ['DATAFORSEO_LOGIN', 'DATAFORSEO_API_KEY'],
    filename: 'surfer-provider-template-tenant-demo.env',
    env_template: 'DATAFORSEO_LOGIN=\nDATAFORSEO_API_KEY=\nSERPER_API_KEY=',
  };
}

function fullAutomationResponse() {
  return {
    status: 'ok',
    run_mode: 'hybrid_with_resilient_fallback',
    results: {
      keyword_discovery: { provider_selected: 'DataForSEO', fallback_used: false, keywords_analyzed: 42, clusters_found: 7 },
      content_gap: { provider_selected: 'DataForSEO', fallback_used: false, total_opportunities: 18, high_coverage_gaps: 6 },
      backlink_audit: { risk_level: 'low', overall_risk_pct: 10, toxic_count: 1, suspicious_count: 1 },
      backlink_gap: { unique_opportunities: 24, competitors_analyzed: 3 },
    },
    providers: {
      keyword_discovery_attempts: [{ provider: 'dataforseo', status: 'passed' }],
      content_gap_attempts: [{ provider: 'dataforseo', status: 'passed' }],
      vendor_inventory: [
        { vendor: 'DataForSEO', module: 'keyword_provider', type: 'integration', configured: true, evidence: 'mock' },
        { vendor: 'OpenAI', module: 'ai_content_generation', type: 'integration', configured: true, evidence: 'mock' },
      ],
    },
  };
}

function surferApiResponse(pathname: string, method: string) {
  const responseMap: Record<string, unknown> = {
    'GET /api/fastapi/search-everywhere/surfer/parity-audit': parityResponse(),
    'GET /api/fastapi/search-everywhere/surfer/provider-checklist': checklistResponse(),
    'GET /api/fastapi/search-everywhere/surfer/wiring-plan': wiringPlanResponse(),
    'GET /api/fastapi/search-everywhere/surfer/setup-playbook': setupPlaybookResponse(),
    'POST /api/fastapi/search-everywhere/surfer/production-gate': productionGateResponse(),
    'POST /api/fastapi/search-everywhere/surfer/provider-bootstrap': bootstrapResponse(),
    'POST /api/fastapi/search-everywhere/surfer/provider-probes': probeResponse(),
    'POST /api/fastapi/search-everywhere/surfer/env-template': envTemplateResponse(),
    'POST /api/fastapi/search-everywhere/surfer/full-automation': fullAutomationResponse(),
  };

  return responseMap[`${method} ${pathname}`] ?? null;
}

async function mockSurferApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/surfer/**', async (route) => {
    const url = new URL(route.request().url());
    const body = surferApiResponse(url.pathname, route.request().method());
    if (body === null) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'mock route not found' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

test.describe('Surfer command center', () => {
  test('renders parity, checklist, wiring plan, and playbook sections', async ({ page }) => {
    await mockSurferApis(page);
    await page.goto('/seo/surfer-command-center');

    await expect(page.getByRole('heading', { name: 'Surfer End-to-End SEO Operations' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Surfer Parity Chart' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Provider Checklist' }).first()).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Wiring Plan', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Setup Playbook', exact: true })).toBeVisible();
    await expect(page.getByText('8/8')).toBeVisible();
  });

  test('runs gate, bootstrap, probes, env template, and full automation actions', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockSurferApis(page);
    await page.goto('/seo/surfer-command-center');

    await page.getByRole('button', { name: 'Run Production Gate' }).click();
    const gateCard = page.getByRole('heading', { name: 'Production Gate' }).first().locator('xpath=ancestor::article[1]');
    await expect(gateCard).toBeVisible({ timeout: 20000 });
    await expect(gateCard).toContainText('PASSED');

    await page.getByRole('button', { name: 'Bootstrap Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Bootstrap', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('2 steps for 2 requested providers.')).toBeVisible();

    await page.getByRole('button', { name: 'Probe Providers' }).click();
    await expect(page.getByRole('heading', { name: 'Provider Probes', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Strict live ready: Yes')).toBeVisible();

    await page.getByRole('button', { name: 'Generate Env Template' }).click();
    await expect(page.getByRole('heading', { name: 'Environment Template', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('surfer-provider-template-tenant-demo.env')).toBeVisible();

    await page.getByRole('button', { name: 'Run Full Automation Blueprint' }).click();
    await expect(page.getByRole('heading', { name: 'Automation Blueprint', exact: true })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Keyword discovery starts with provider-backed research and clustering.')).toBeVisible();
    await expect(page.getByText('Vendor inventory: 2')).toBeVisible();
  });
});
