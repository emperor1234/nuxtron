import { expect, test } from '@playwright/test';

async function installHubspotMocks(page: import('@playwright/test').Page): Promise<void> {
  await page.route('**/api/fastapi/search-everywhere/hubspot/full-e2e-audit', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        summary: {
          products_total: 10,
          required_routes_total: 28,
          required_routes_implemented: 28,
          providers_total: 9,
          providers_configured: 9,
          implementation_pct: 100,
          integration_configured_pct: 100,
          e2e_verified_pct: 100,
          production_grade_ready: true,
        },
        product_chart: [],
        third_party_vendor_chart: [
          { product_key: 'marketing-hub', product: 'Marketing Hub', vendor: 'HubSpot', relationship: 'core_platform' },
          {
            product_key: 'marketing-hub',
            product: 'Marketing Hub',
            vendor: 'Google Ads',
            relationship: 'runtime_dependency',
          },
        ],
        how_it_works: ['Route contracts and provider checks enforce release readiness.'],
        validation_boundaries: {
          validated_slice: { scope: 'hubspot slice', evidence: ['route coverage'] },
          not_validated: ['live billing state'],
        },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/completion-chart', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        summary: {
          modules_total: 10,
          modules_implemented: 10,
          modules_e2e_verified: 10,
          implementation_pct: 100,
          e2e_verified_pct: 100,
          integration_configured_pct: 100,
          premium_features_total: 75,
        },
        chart: [
          {
            key: 'marketing-hub',
            product: 'Marketing Hub',
            implemented: true,
            e2e_verified: true,
            premium_features_total: 8,
            vendors: ['HubSpot', 'Google Ads'],
          },
        ],
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/production-gate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        gate: {
          passed: true,
          blockers: [],
          implementation_ok: true,
          e2e_ok: true,
          integration_ok: true,
        },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/vendors', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        vendors_total: 30,
        vendors_configured: 30,
        vendor_chart: [
          {
            domain: 'go-to-market',
            vendor: 'HubSpot',
            capability: 'CRM and automation',
            configured: true,
            evidence: 'inventory',
          },
        ],
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/verification-report', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        verification: {
          slice_ready: true,
          slice_gate: { passed: true, blockers: [] },
          validation_boundaries: {
            validated_slice: 'search_everywhere hubspot product suite',
            not_validated: ['external quotas'],
          },
        },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/wiring/apply', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        checklist_summary: { configured: 9, total: 9, configured_pct: 100 },
        completion_summary: {
          implementation_pct: 100,
          integration_configured_pct: 100,
          e2e_verified_pct: 100,
        },
        gate: { passed: true, blockers: [] },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/hubspot/crm/contacts', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
  await page.route('**/api/fastapi/search-everywhere/hubspot/crm/companies', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
  await page.route('**/api/fastapi/search-everywhere/hubspot/crm/deals', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
  await page.route('**/api/fastapi/search-everywhere/hubspot/service/tickets', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
  await page.route('**/api/fastapi/search-everywhere/hubspot/content/landing-pages', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
  await page.route('**/api/fastapi/search-everywhere/hubspot/data/sync-jobs', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });
}

test('hubspot e2e console loads and executes wiring plus sample flow', async ({ page }) => {
  test.slow();
  test.setTimeout(90000);
  await installHubspotMocks(page);

  await page.goto('/hubspot-e2e');

  await expect(page.getByRole('heading', { name: 'HubSpot 100% Production-Grade Console' })).toBeVisible();

  const loadResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/hubspot/full-e2e-audit') &&
      response.request().method() === 'GET'
  );
  await page.getByRole('button', { name: 'Load HubSpot E2E' }).click();
  await loadResponse;

  await expect(page.getByRole('heading', { name: 'Implementation' })).toBeVisible();
  await expect(page.getByText('HubSpot Product Completion')).toBeVisible();

  const wiringResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/hubspot/wiring/apply') &&
      response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Apply HubSpot Provider Wiring' }).click();
  await wiringResponse;

  await expect(page.getByText(/Wiring applied:/i)).toBeVisible({ timeout: 20000 });

  const seedResponses = Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/fastapi/search-everywhere/hubspot/crm/contacts') &&
        response.request().method() === 'POST'
    ),
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/fastapi/search-everywhere/hubspot/data/sync-jobs') &&
        response.request().method() === 'POST'
    ),
  ]);
  await page.getByRole('button', { name: 'Run Sample End-to-End Flow' }).click();
  await seedResponses;

  await expect(page.getByText(/Sample E2E flow seeded/i)).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('Third-Party Vendors and How They Work')).toBeVisible();
});
