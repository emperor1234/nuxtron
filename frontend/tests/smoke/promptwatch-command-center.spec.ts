import { expect, test } from '@playwright/test';

function promptwatchApiResponse(pathname: string, method: string) {
  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/parity-audit') {
    return {
      status: 'ok',
      summary: {
        implementation_pct: 100,
        integration_configured_pct: 100,
        modules_total: 7,
        modules_implemented: 7,
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/production-gate') {
    return {
      status: 'ok',
      gate: {
        passed: true,
        blockers: [],
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/vendors') {
    return {
      status: 'ok',
      vendors_total: 12,
      vendors_configured: 12,
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/projects') {
    return {
      status: 'ok',
      projects: [
        {
          id: 'promptwatch-proj-1',
          name: 'Promptwatch Automation Project',
          primary_domain: 'nuxtron.ai',
        },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/runs') {
    return {
      status: 'ok',
      runs: [
        {
          id: 'promptwatch-run-1',
          project_id: 'promptwatch-proj-1',
          strict_probe_status: 'passed',
          completed_at: new Date().toISOString(),
        },
      ],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/promptwatch/full-automation') {
    return {
      status: 'ok',
      promptwatch_modules: {
        prompt_tracing: ['timeline capture', 'session correlation'],
        eval_pipelines: ['rubric scoring', 'release scorecards'],
      },
      third_parties_and_vendors: [{ vendor: 'PromptWatch' }, { vendor: 'OpenAI' }],
      how_it_works: [
        'Prompt and response traces are recorded with latency and token context.',
        'Evaluation and regression suites benchmark candidate prompts before promotion.',
        'Anomaly and incident flows route alerts to operations channels.',
        'Provider checklist and production gate verify tenant readiness.',
      ],
      production_gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/promptwatch/projects') {
    return {
      status: 'ok',
      project: {
        id: 'promptwatch-proj-new',
        name: 'Promptwatch Automation Project',
        primary_domain: 'nuxtron.ai',
      },
    };
  }

  if (
    method === 'POST' &&
    pathname.startsWith('/api/fastapi/search-everywhere/promptwatch/projects/') &&
    pathname.endsWith('/run')
  ) {
    return {
      status: 'ok',
      run: {
        id: 'promptwatch-run-new',
        project_id: 'promptwatch-proj-1',
        strict_probe_status: 'passed',
        completed_at: new Date().toISOString(),
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/provider-checklist') {
    return {
      status: 'ok',
      configured: 10,
      total: 10,
      configured_pct: 100,
      checklist: [
        { provider: 'PromptWatch', kind: 'core', configured: true, required_missing: [] },
        { provider: 'OpenAI', kind: 'ai_provider', configured: true, required_missing: [] },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/promptwatch/preflight') {
    return {
      status: 'ok',
      configured_pct: 100,
      missing_provider_steps: [],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/promptwatch/wiring/apply') {
    return {
      status: 'ok',
      checklist_summary: { configured_pct: 100 },
      gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/promptwatch/remediation-bundle') {
    return {
      status: 'ok',
      remediation_steps: [{ provider: 'PromptWatch', priority: 'high', required_missing: [] }],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/promptwatch/assist/chat') {
    return {
      status: 'ok',
      assist: {
        answer_summary: 'Promptwatch rollout is healthy and production ready for this tenant.',
        recommended_actions: ['Run nightly regression suites and monitor anomaly budgets.'],
        workflow_handoffs: ['Prompt engineering -> release governance'],
      },
    };
  }

  return null;
}

async function mockPromptwatchApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/promptwatch/**', async (route) => {
    const url = new URL(route.request().url());
    const body = promptwatchApiResponse(url.pathname, route.request().method());
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

test.describe('Promptwatch command center', () => {
  test('readiness page renders gate and navigation cards', async ({ page }) => {
    await mockPromptwatchApis(page);
    await page.goto('/seo/promptwatch-readiness');

    await expect(page.getByRole('heading', { name: 'Promptwatch End-to-End Readiness Hub' })).toBeVisible();
    await expect(page.getByText('Current status:')).toContainText('PASSED');
    await expect(page.locator('a[href="/seo/promptwatch-automation"]')).toBeVisible();
    await expect(page.locator('a[href="/seo/promptwatch-integrations"]')).toBeVisible();
  });

  test('automation page runs full blueprint flow', async ({ page }) => {
    await mockPromptwatchApis(page);
    await page.goto('/seo/promptwatch-automation');

    await expect(page.getByRole('heading', { name: 'Promptwatch Run And Product Control' })).toBeVisible();
    const runBlueprintButton = page.getByRole('button', { name: 'Run Full Automation Blueprint' });
    const blueprintHeading = page.getByRole('heading', { name: 'Automation Blueprint' });
    await runBlueprintButton.click();
    if (!(await blueprintHeading.isVisible())) {
      await runBlueprintButton.click();
    }
    await expect(blueprintHeading).toBeVisible({ timeout: 20000 });
    await expect(
      page.getByText('Evaluation and regression suites benchmark candidate prompts before promotion.')
    ).toBeVisible();
    await expect(page.getByText('Vendors referenced: 2')).toBeVisible();
  });

  test('integrations page can apply wiring', async ({ page }) => {
    await mockPromptwatchApis(page);
    await page.goto('/seo/promptwatch-integrations');

    await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();
    await page.getByRole('button', { name: 'Apply All Missing Wiring' }).click();
    await expect(page.getByText(/Wiring result:\s*\d+% configured, gate PASSED\.?/i)).toBeVisible({ timeout: 30_000 });
  });

  test('assist page returns operational guidance', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockPromptwatchApis(page);
    await page.goto('/seo/promptwatch-assist');

    const assistHeading = page.getByRole('heading', { name: 'Assist Prompt Console' });
    const runAssistButton = page.getByRole('button', { name: 'Run Assist' });
    await expect(assistHeading).toBeVisible();
    await runAssistButton.click();
    if (new URL(page.url()).search) {
      await page.goto('/seo/promptwatch-assist', { waitUntil: 'commit' });
      await expect(assistHeading).toBeVisible();
      await runAssistButton.click();
    }
    await expect(page.getByRole('heading', { name: 'Assist Response' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Promptwatch rollout is healthy and production ready for this tenant.')).toBeVisible();
  });
});
