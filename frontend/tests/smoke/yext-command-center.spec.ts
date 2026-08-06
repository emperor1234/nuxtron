import { expect, test } from '@playwright/test';

function yextApiResponse(pathname: string, method: string) {
  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/parity-audit') {
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

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/production-gate') {
    return {
      status: 'ok',
      gate: {
        passed: true,
        blockers: [],
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/vendors') {
    return {
      status: 'ok',
      vendors_total: 18,
      vendors_configured: 18,
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/projects') {
    return {
      status: 'ok',
      projects: [
        {
          id: 'yext-proj-1',
          name: 'Yext Automation Project',
          primary_domain: 'nuxtron.ai',
        },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/runs') {
    return {
      status: 'ok',
      runs: [
        {
          id: 'yext-run-1',
          project_id: 'yext-proj-1',
          strict_probe_status: 'passed',
          completed_at: new Date().toISOString(),
        },
      ],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/yext/full-automation') {
    return {
      status: 'ok',
      yext_modules: {
        presence: ['listings sync', 'publisher health'],
        reputation: ['review response', 'sentiment clustering'],
      },
      third_parties_and_vendors: [{ vendor: 'Yext' }, { vendor: 'Google Business Profile' }],
      how_it_works: [
        'Knowledge Graph is the source of truth.',
        'Listings and reviews are synchronized.',
        'Pages, search, and chat share entity context.',
        'Gate checks separate code-complete and integration-ready.',
      ],
      production_gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/yext/projects') {
    return {
      status: 'ok',
      project: {
        id: 'yext-proj-new',
        name: 'Yext Automation Project',
        primary_domain: 'nuxtron.ai',
      },
    };
  }

  if (
    method === 'POST' &&
    pathname.startsWith('/api/fastapi/search-everywhere/yext/projects/') &&
    pathname.endsWith('/run')
  ) {
    return {
      status: 'ok',
      run: {
        id: 'yext-run-new',
        project_id: 'yext-proj-1',
        strict_probe_status: 'passed',
        completed_at: new Date().toISOString(),
      },
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/provider-checklist') {
    return {
      status: 'ok',
      configured: 12,
      total: 12,
      configured_pct: 100,
      checklist: [
        { provider: 'Yext', kind: 'core', configured: true, required_missing: [] },
        { provider: 'Google Business Profile', kind: 'publisher', configured: true, required_missing: [] },
      ],
    };
  }

  if (method === 'GET' && pathname === '/api/fastapi/search-everywhere/yext/preflight') {
    return {
      status: 'ok',
      configured_pct: 100,
      missing_provider_steps: [],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/yext/wiring/apply') {
    return {
      status: 'ok',
      checklist_summary: { configured_pct: 100 },
      gate: { passed: true, blockers: [] },
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/yext/remediation-bundle') {
    return {
      status: 'ok',
      remediation_steps: [{ provider: 'Yext', priority: 'high', required_missing: [] }],
    };
  }

  if (method === 'POST' && pathname === '/api/fastapi/search-everywhere/yext/assist/chat') {
    return {
      status: 'ok',
      assist: {
        answer_summary: 'Yext rollout is healthy and production ready for this tenant.',
        recommended_actions: ['Keep publisher auth rotated quarterly.'],
        workflow_handoffs: ['Listings operations -> publisher provisioning'],
      },
    };
  }

  return null;
}

async function mockYextApis(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/yext/**', async (route) => {
    const url = new URL(route.request().url());
    const body = yextApiResponse(url.pathname, route.request().method());
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

test.describe('Yext command center', () => {
  test('readiness page renders gate and navigation cards', async ({ page }) => {
    await mockYextApis(page);
    await page.goto('/seo/yext-readiness');

    await expect(page.getByRole('heading', { name: 'Yext End-to-End Readiness Hub' })).toBeVisible();
    await expect(page.getByText('Current status:')).toContainText('PASSED');
    await expect(page.locator('a[href="/seo/yext-automation"]')).toBeVisible();
    await expect(page.locator('a[href="/seo/yext-integrations"]')).toBeVisible();
  });

  test('automation page runs full blueprint flow', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockYextApis(page);
    await page.goto('/seo/yext-automation');

    await expect(page.getByRole('heading', { name: 'Yext Run And Product Control' })).toBeVisible();
    const runButton = page.getByRole('button', { name: 'Run Full Automation Blueprint' });
    await expect(runButton).toBeEnabled({ timeout: 20000 });
    const automationResponse = page.waitForResponse(
      (response) =>
        response.url().includes('/api/fastapi/search-everywhere/yext/full-automation') &&
        response.request().method() === 'POST'
    );
    await runButton.click();
    await automationResponse;
    await expect(
      page
        .locator('section.card')
        .filter({ hasText: /Automation Blueprint/ })
        .first()
    ).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Knowledge Graph is the source of truth.')).toBeVisible();
    await expect(page.getByText('Vendors referenced: 2')).toBeVisible();
  });

  test('integrations page can apply wiring', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockYextApis(page);
    await page.goto('/seo/yext-integrations');

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
    await mockYextApis(page);
    await page.goto('/seo/yext-assist');

    const assistHeading = page.getByRole('heading', { name: 'Assist Prompt Console' });
    const runAssistButton = page.getByRole('button', { name: 'Run Assist' });
    await expect(assistHeading).toBeVisible();
    await runAssistButton.click();
    if (new URL(page.url()).search) {
      await page.goto('/seo/yext-assist', { waitUntil: 'commit' });
      await expect(assistHeading).toBeVisible();
      await runAssistButton.click();
    }
    await expect(page.getByRole('heading', { name: 'Assist Response' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Yext rollout is healthy and production ready for this tenant.')).toBeVisible();
  });
});
