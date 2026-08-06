import { expect, test } from '@playwright/test';

function geoptieApiResponse(pathname: string, method: string) {
  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/parity-audit') {
    return {
      status: 'ok',
      summary: {
        implementation_pct: 100,
        integration_configured_pct: 100,
        modules_total: 8,
        modules_implemented: 8,
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/production-gate') {
    return {
      status: 'ok',
      gate: {
        passed: true,
        blockers: [],
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/vendors') {
    return {
      status: 'ok',
      vendors_total: 18,
      vendors_configured: 18,
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/projects') {
    return {
      status: 'ok',
      projects: [
        {
          id: 'geoptie-proj-1',
          name: 'Geoptie Automation Project',
          primary_domain: 'nuxtron.ai',
        },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/runs') {
    return {
      status: 'ok',
      runs: [
        {
          id: 'geoptie-run-1',
          project_id: 'geoptie-proj-1',
          strict_probe_status: 'passed',
          completed_at: new Date().toISOString(),
        },
      ],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/geoptie/full-automation') {
    return {
      status: 'ok',
      geoptie_modules: {
        geo_audit: ['readiness scoring', 'critical blockers'],
        rank_tracker: ['model position tracking', 'visibility score'],
      },
      third_parties_and_vendors: [{ vendor: 'Geoptie' }, { vendor: 'OpenAI ChatGPT' }],
      how_it_works: [
        'GEO Audit baselines current AI-search readiness.',
        'Rank Tracker monitors visibility across major AI model surfaces.',
        'Optimization modules convert gaps into prioritized actions.',
        'Provider checklist and production gate verify tenant readiness.',
      ],
      production_gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/geoptie/projects') {
    return {
      status: 'ok',
      project: {
        id: 'geoptie-proj-new',
        name: 'Geoptie Automation Project',
        primary_domain: 'nuxtron.ai',
      },
    };
  }

  if (
    method === 'POST' &&
    pathname.startsWith('/api/fastapi/search-everywhere/geoptie/projects/') &&
    pathname.endsWith('/run')
  ) {
    return {
      status: 'ok',
      run: {
        id: 'geoptie-run-new',
        project_id: 'geoptie-proj-1',
        strict_probe_status: 'passed',
        completed_at: new Date().toISOString(),
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/provider-checklist') {
    return {
      status: 'ok',
      configured: 12,
      total: 12,
      configured_pct: 100,
      checklist: [
        { provider: 'Geoptie', kind: 'core', configured: true, required_missing: [] },
        { provider: 'OpenAI ChatGPT', kind: 'ai_provider', configured: true, required_missing: [] },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/geoptie/preflight') {
    return {
      status: 'ok',
      configured_pct: 100,
      missing_provider_steps: [],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/geoptie/wiring/apply') {
    return {
      status: 'ok',
      checklist_summary: { configured_pct: 100 },
      gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/geoptie/remediation-bundle') {
    return {
      status: 'ok',
      remediation_steps: [{ provider: 'Geoptie', priority: 'high', required_missing: [] }],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/geoptie/assist/chat') {
    return {
      status: 'ok',
      assist: {
        answer_summary: 'Geoptie rollout is healthy and production ready for this tenant.',
        recommended_actions: ['Rotate provider credentials quarterly and monitor gate drift.'],
        workflow_handoffs: ['Content ops -> GEO release ops'],
      },
    };
  }

  return null;
}

async function mockGeoptieApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/geoptie/**', async (route) => {
    const url = new URL(route.request().url());
    const body = geoptieApiResponse(url.pathname, route.request().method());
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

test.describe('Geoptie command center', () => {
  test('readiness page renders gate and navigation cards', async ({ page }) => {
    await mockGeoptieApis(page);
    await page.goto('/seo/geoptie-readiness');
    const main = page.locator('main');

    await expect(main.getByRole('heading', { name: 'Geoptie End-to-End Readiness Hub' })).toBeVisible();
    await expect(main.getByText('Current status:')).toContainText('PASSED');
    await expect(main.locator('a[href="/seo/geoptie-automation"]').first()).toBeVisible();
    await expect(main.locator('a[href="/seo/geoptie-integrations"]').first()).toBeVisible();
  });

  test('automation page runs full blueprint flow', async ({ page }) => {
    await mockGeoptieApis(page);
    await page.goto('/seo/geoptie-automation');

    await expect(page.getByRole('heading', { name: 'Geoptie Run And Product Control' })).toBeVisible();
    const runBlueprintButton = page.getByRole('button', { name: 'Run Full Automation Blueprint' });
    const blueprintHeading = page.getByRole('heading', { name: 'Automation Blueprint' });
    await runBlueprintButton.click();
    if (!(await blueprintHeading.isVisible())) {
      await runBlueprintButton.click();
    }
    await expect(blueprintHeading).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Rank Tracker monitors visibility across major AI model surfaces.')).toBeVisible();
    await expect(page.getByText('Vendors referenced: 2')).toBeVisible();
  });

  test('integrations page can apply wiring', async ({ page }) => {
    await mockGeoptieApis(page);
    await page.goto('/seo/geoptie-integrations');

    await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();
    await page.getByRole('button', { name: 'Apply All Missing Wiring' }).click();
    await expect(page.getByText('Wiring result: 100% configured, gate PASSED.')).toBeVisible();
  });

  test('assist page returns operational guidance', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockGeoptieApis(page);
    await page.goto('/seo/geoptie-assist');

    const assistHeading = page.getByRole('heading', { name: 'Assist Prompt Console' });
    const runAssistButton = page.getByRole('button', { name: 'Run Assist' });
    await expect(assistHeading).toBeVisible();
    await runAssistButton.click();
    if (new URL(page.url()).search) {
      await page.goto('/seo/geoptie-assist', { waitUntil: 'commit' });
      await expect(assistHeading).toBeVisible();
      await runAssistButton.click();
    }
    await expect(page.getByRole('heading', { name: 'Assist Response' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Geoptie rollout is healthy and production ready for this tenant.')).toBeVisible();
  });
});
