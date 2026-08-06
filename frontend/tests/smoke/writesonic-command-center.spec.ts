import { expect, test } from '@playwright/test';

const WRITESONIC_ROUTE = '/api/fastapi/search-everywhere/writesonic';

function writesonicParityAuditResponse() {
  return {
    status: 'ok',
    summary: {
      implementation_pct: 100,
      integration_configured_pct: 100,
      modules_total: 7,
      modules_implemented: 7,
    },
    writesonic_feature_chart: [
      {
        key: 'chatsonic-research',
        feature: 'Chatsonic real-time research',
        product: 'Chatsonic',
        vendors: ['Writesonic', 'OpenAI'],
        production_grade_ready: true,
        automation_depth: 'full',
      },
    ],
    writesonic_parity_chart: [
      {
        key: 'chatsonic',
        product: 'Chatsonic',
        implemented: true,
        e2e_verified: true,
        integration_ready: true,
        production_grade_ready: true,
        premium_features_total: 5,
        vendors: ['Writesonic', 'OpenAI', 'Anthropic', 'Google'],
      },
    ],
    vendor_inventory: [
      { domain: 'ai-content', vendor: 'Writesonic', capability: 'AI content orchestration', configured: true, evidence: 'mock' },
      { domain: 'ai-content', vendor: 'OpenAI', capability: 'Generation backend', configured: true, evidence: 'mock' },
    ],
  };
}

function writesonicProductsResponse() {
  return {
    status: 'ok',
    count: 7,
    products: [
      {
        key: 'chatsonic',
        name: 'Chatsonic',
        description: 'Conversational research and brand-safe answer generation for search and content teams.',
        premium_features: ['Grounded web + knowledge retrieval', 'Brand voice and policy controls'],
        vendors: ['Writesonic', 'OpenAI', 'Anthropic', 'Google'],
        implemented: true,
        e2e_verified: true,
        production_grade_ready: true,
      },
      {
        key: 'article-writer',
        name: 'Article Writer',
        description: 'Long-form SEO and AEO content pipeline with briefs, drafts, optimization, and publishing handoff.',
        premium_features: ['SERP-grounded article briefs', 'Entity and intent coverage checks'],
        vendors: ['Writesonic', 'WordPress', 'Shopify', 'Google Search Console'],
      },
    ],
  };
}

function writesonicProductDetailResponse() {
  return {
    status: 'ok',
    product: {
      key: 'chatsonic',
      name: 'Chatsonic',
      description: 'Conversational research and brand-safe answer generation for search and content teams.',
      premium_features: ['Grounded web + knowledge retrieval', 'Brand voice and policy controls'],
      vendors: ['Writesonic', 'OpenAI', 'Anthropic', 'Google'],
      implemented: true,
      e2e_verified: true,
      production_grade_ready: true,
    },
  };
}

function writesonicCompletionChartResponse() {
  return {
    status: 'ok',
    chart: [
      {
        key: 'chatsonic',
        product: 'Chatsonic',
        implemented: true,
        e2e_verified: true,
        integration_ready: true,
        production_grade_ready: true,
        premium_features_total: 5,
        vendors: ['Writesonic', 'OpenAI', 'Anthropic', 'Google'],
      },
    ],
    summary: {
      modules_total: 7,
      modules_implemented: 7,
      modules_e2e_verified: 7,
      implementation_pct: 100,
      e2e_verified_pct: 100,
      integration_configured_pct: 100,
      products_total: 7,
      premium_features_total: 35,
    },
  };
}

function writesonicVerificationResponse() {
  return {
    status: 'ok',
    verification: {
      slice_ready: true,
      slice_gate: { passed: true, blockers: [] },
      evidence_table: [
        {
          key: 'chatsonic',
          product: 'Chatsonic',
          implemented: true,
          e2e_verified: true,
          integration_ready: true,
          production_grade_ready: true,
          premium_features_total: 5,
          vendors: ['Writesonic', 'OpenAI', 'Anthropic', 'Google'],
        },
      ],
      feature_evidence_table: [
        {
          key: 'chatsonic-research',
          feature: 'Chatsonic real-time research',
          product: 'Chatsonic',
          automation_depth: 'full',
          vendors: ['Writesonic', 'OpenAI'],
        },
      ],
      validation_boundaries: {
        validated_slice: 'search_everywhere writesonic product suite',
        not_validated: ['external vendor billing state', 'third-party quota constraints'],
      },
    },
  };
}

function writesonicWiringResponse() {
  return {
    status: 'ok',
    wired_providers: ['Writesonic', 'OpenAI'],
    wired_count: 2,
    missing_providers: [],
  };
}

function writesonicProductionGateResponse() {
  return {
    status: 'ok',
    gate: {
      passed: true,
      blockers: [],
    },
  };
}

function writesonicProjectsResponse() {
  return {
    status: 'ok',
    projects: [
      {
        id: 'writesonic-proj-1',
        name: 'Writesonic Automation Project',
        primary_domain: 'nuxtron.ai',
      },
    ],
  };
}

function writesonicRunsResponse() {
  return {
    status: 'ok',
    runs: [
      {
        id: 'writesonic-run-1',
        project_id: 'writesonic-proj-1',
        strict_probe_status: 'passed',
        completed_at: new Date().toISOString(),
      },
    ],
  };
}

function writesonicFeaturesResponse() {
  return {
    status: 'ok',
    summary: {
      features_total: 18,
      features_implemented: 18,
      features_e2e_verified: 18,
      implementation_pct: 100,
      e2e_verified_pct: 100,
      integration_configured_pct: 100,
      vendors_covered: 22,
    },
    chart: [
      {
        key: 'chatsonic-research',
        feature: 'Chatsonic real-time research',
        product: 'Chatsonic',
        vendors: ['Writesonic', 'OpenAI'],
        production_grade_ready: true,
        automation_depth: 'full',
      },
      {
        key: 'audiosonic-tts',
        feature: 'Audiosonic text-to-speech',
        product: 'Audiosonic',
        vendors: ['Writesonic', 'ElevenLabs'],
        production_grade_ready: true,
        automation_depth: 'full',
      },
    ],
  };
}

function writesonicFullAutomationResponse() {
  return {
    status: 'ok',
    writesonic_modules: {
      chatsonic: ['research prompts', 'brand-safe responses'],
      article_writer: ['seo briefs', 'draft generation'],
      photosonic: ['creative prompt generation', 'variant assets'],
      audiosonic: ['script to audio', 'voice profile'],
    },
    third_parties_and_vendors: [{ vendor: 'Writesonic' }, { vendor: 'OpenAI' }],
    feature_registry_summary: {
      features_total: 18,
    },
    how_it_works: [
      'Demand and prompt intelligence identify high-impact opportunities.',
      'Chatsonic and Article Writer generate governed drafts.',
      'Publishing and automation integrations route approved assets.',
      'Provider checklist and production gate confirm tenant readiness.',
    ],
    production_gate: { passed: true, blockers: [] },
  };
}

function writesonicRemediationResponse() {
  return {
    status: 'ok',
    remediation_steps: [{ provider: 'Writesonic', priority: 'high', required_missing: [] }],
  };
}

function writesonicProviderChecklistResponse() {
  return {
    status: 'ok',
    configured: 12,
    total: 12,
    configured_pct: 100,
    checklist: [
      { provider: 'Writesonic', kind: 'core', configured: true, required_missing: [] },
      { provider: 'OpenAI', kind: 'ai_provider', configured: true, required_missing: [] },
    ],
  };
}

function writesonicPreflightResponse() {
  return {
    status: 'ok',
    configured_pct: 100,
    missing_provider_steps: [],
  };
}

function writesonicWiringApplyResponse() {
  return {
    status: 'ok',
    checklist_summary: { configured_pct: 100 },
    gate: { passed: true, blockers: [] },
  };
}

function writesonicAssistResponse() {
  return {
    status: 'ok',
    assist: {
      answer_summary: 'Writesonic rollout is healthy and production ready for this tenant.',
      recommended_actions: ['Rotate provider credentials quarterly and monitor gate drift.'],
      workflow_handoffs: ['Content ops -> publishing ops'],
    },
  };
}

const WRITESONIC_RESPONSE_BUILDERS: Record<string, () => unknown> = {
  [`GET:${WRITESONIC_ROUTE}/parity-audit`]: writesonicParityAuditResponse,
  [`GET:${WRITESONIC_ROUTE}/products`]: writesonicProductsResponse,
  [`GET:${WRITESONIC_ROUTE}/products/detail/chatsonic`]: writesonicProductDetailResponse,
  [`GET:${WRITESONIC_ROUTE}/products/completion-chart`]: writesonicCompletionChartResponse,
  [`GET:${WRITESONIC_ROUTE}/verification-report`]: writesonicVerificationResponse,
  [`GET:${WRITESONIC_ROUTE}/wiring`]: writesonicWiringResponse,
  [`GET:${WRITESONIC_ROUTE}/production-gate`]: writesonicProductionGateResponse,
  [`GET:${WRITESONIC_ROUTE}/vendors`]: () => ({ status: 'ok', vendors_total: 16, vendors_configured: 16 }),
  [`GET:${WRITESONIC_ROUTE}/projects`]: writesonicProjectsResponse,
  [`GET:${WRITESONIC_ROUTE}/runs`]: writesonicRunsResponse,
  [`GET:${WRITESONIC_ROUTE}/features`]: writesonicFeaturesResponse,
  [`POST:${WRITESONIC_ROUTE}/full-automation`]: writesonicFullAutomationResponse,
  [`POST:${WRITESONIC_ROUTE}/projects`]: () => ({
    status: 'ok',
    project: {
      id: 'writesonic-proj-new',
      name: 'Writesonic Automation Project',
      primary_domain: 'nuxtron.ai',
    },
  }),
  [`POST:${WRITESONIC_ROUTE}/wiring/apply`]: writesonicWiringApplyResponse,
  [`POST:${WRITESONIC_ROUTE}/remediation-bundle`]: writesonicRemediationResponse,
  [`POST:${WRITESONIC_ROUTE}/assist/chat`]: writesonicAssistResponse,
};

function writesonicApiResponse(pathname: string, method: string) {
  return WRITESONIC_RESPONSE_BUILDERS[`${method}:${pathname}`]?.() ?? null;
}

async function mockWritesonicApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/writesonic/**', async (route) => {
    const url = new URL(route.request().url());
    const body = writesonicApiResponse(url.pathname, route.request().method());
    if (body === null) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'mock route not found' }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test.describe('Writesonic command center', () => {
  test('readiness page renders gate and navigation cards', async ({ page }) => {
    await mockWritesonicApis(page);
    await page.goto('/seo/writesonic-readiness');
    const main = page.locator('main');

    await expect(main.getByRole('heading', { name: 'Writesonic End-to-End Readiness Hub' })).toBeVisible();
    await expect(main.getByText('Current status:')).toContainText('PASSED');
    await expect(main.getByRole('heading', { name: 'Verification Boundaries' })).toBeVisible();
    await expect(main.locator('a[href="/seo/writesonic-automation"]').first()).toBeVisible();
    await expect(main.locator('a[href="/seo/writesonic-integrations"]').first()).toBeVisible();
  });

  test('automation page runs full blueprint flow', async ({ page }) => {
    await mockWritesonicApis(page);
    await page.goto('/seo/writesonic-automation');

    await expect(page.getByRole('heading', { name: 'Writesonic Run And Product Control' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Product Catalog' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Chatsonic Detail' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Product Completion Chart' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Verification Report' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Feature Completion Chart' })).toBeVisible();
    const featureRegistrySection = page
      .locator('section.card')
      .filter({ has: page.getByRole('heading', { name: 'Feature Completion Chart' }) })
      .first();
    await expect(featureRegistrySection).toContainText('Features: 18/18');
    const runBlueprintButton = page.getByRole('button', { name: 'Run Full Automation Blueprint' });
    const blueprintHeading = page.getByRole('heading', { name: 'Automation Blueprint' });
    await runBlueprintButton.click();
    if (!(await blueprintHeading.isVisible())) {
      await runBlueprintButton.click();
    }
    await expect(blueprintHeading).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Chatsonic and Article Writer generate governed drafts.')).toBeVisible();
    await expect(page.getByText('Vendors referenced: 2')).toBeVisible();
  });

  test('integrations page can apply wiring', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockWritesonicApis(page);
    await page.goto('/seo/writesonic-integrations');

    await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();
    const applyButton = page.getByRole('button', { name: 'Apply All Missing Wiring' });
    await expect(applyButton).toBeEnabled({ timeout: 20000 });
    await applyButton.click();
    const actionCard = page.locator('section.card').first();
    await expect(actionCard).toContainText('Wiring result:', { timeout: 30000 });
    await expect(actionCard).toContainText('100% configured', { timeout: 30000 });
    await expect(actionCard).toContainText('gate PASSED', { timeout: 30000 });
  });

  test('assist page returns operational guidance', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockWritesonicApis(page);
    await page.goto('/seo/writesonic-assist');

    const assistHeading = page.getByRole('heading', { name: 'Assist Prompt Console' });
    const runAssistButton = page.getByRole('button', { name: 'Run Assist' });
    await expect(assistHeading).toBeVisible();
    await runAssistButton.click();
    if (new URL(page.url()).search) {
      await page.goto('/seo/writesonic-assist', { waitUntil: 'commit' });
      await expect(assistHeading).toBeVisible();
      await runAssistButton.click();
    }
    await expect(page.getByRole('heading', { name: 'Assist Response' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Writesonic rollout is healthy and production ready for this tenant.')).toBeVisible();
  });
});
