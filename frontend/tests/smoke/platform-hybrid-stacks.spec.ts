import { expect, test } from '@playwright/test';

const okJson = {
  status: 200,
  contentType: 'application/json',
};

const basePayloads: Record<string, unknown> = {
  '/ops/platform/status': {
    status: 'ok',
    db_ready: true,
    integrations: {
      hashicorp_vault_configured: true,
      supabase_configured: true,
      supabase_vault_ready: true,
    },
  },
  '/ops/platform/use-case-coverage': {
    coverage_percent: 100,
    covered_count: 10,
    total_use_cases: 10,
  },
  '/ops/platform/metrics-summary': {
    queues: {
      twilio_messages_memory: 3,
      slack_messages_memory: 2,
      resend_messages_memory: 1,
    },
    rate_limiter: { active_keys: 2, sample_count: 8 },
  },
  '/ops/platform/anti-failure-status': {
    summary: { total: 6, healthy_count: 6, degraded_count: 0 },
  },
  '/ops/platform/system-overview': {
    generated_at: '2026-04-29T10:00:00Z',
    frontend: { status: 'ready' },
    backend: { status: 'ready' },
    database: { status: 'ready' },
    security: { strict_mode: true, jwt_configured: true, vault_configured: true },
    integrations: { ready: 3, total: 3, ratio: 1 },
    queues: { total_events: 6, active_queues: 3 },
    capabilities: { coverage_percent: 100, features_ready_estimate: 10, features_total: 10 },
  },
  '/ops/platform/system-overview/history': {
    count: 1,
    items: [],
    trends: {
      time_labels: ['10:00'],
      queue_events: [6],
      integration_ratio_percent: [100],
      coverage_percent: [100],
    },
  },
  '/ops/platform/capabilities': {
    categories: [],
    totals: { features: 10, categories: 1, db_ready: true },
  },
  '/analytics/revenue-attribution/report': {
    totals: {
      conversions: 0,
      tracked_conversions: 0,
      revenue: 0,
      attributed_revenue: 0,
      unattributed_revenue: 0,
    },
    channels: [],
    top_posts: [],
  },
  '/ops/platform/growth-suite': {
    features: [],
    totals: { features: 0, configured: 0, db_ready: true },
  },
};

async function mockPlatformApis(
  page: import('@playwright/test').Page,
  hybridStacksStatus = 200,
  hybridCategory = 'LIVE-CHECK'
) {
  await page.route('**/api/fastapi/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/api/fastapi', '');

    if (path === '/ops/platform/hybrid-stacks') {
      if (hybridStacksStatus === 204) {
        await route.fulfill({
          ...okJson,
          body: JSON.stringify({}),
        });
        return;
      }

      if (hybridStacksStatus !== 200) {
        await route.fulfill({
          status: hybridStacksStatus,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'forced failure for fallback smoke' }),
        });
        return;
      }

      await route.fulfill({
        ...okJson,
        body: JSON.stringify({
          recommendation: {
            hybrid: 'Live API smoke stack',
            score: '100/100 (100%)',
            benefits: ['Live payload applied'],
            positioning: 'Live API payload check',
          },
          stacks: [
            {
              id: 'live-check',
              category: hybridCategory,
              goal: 'Smoke-test category from live payload',
              constraint: '100% free + open-source.',
              free_tools: [{ name: 'Live Free Tool', score: 100, capabilities: ['live'] }],
              open_source_tools: [{ name: 'Live OSS Tool', score: 100, capabilities: ['live'] }],
              hybrid_stack: 'Live Stack',
              outcomes: ['Live outcome'],
              hybrid_score: '100/100 (100%)',
            },
          ],
          summary: [{ category: hybridCategory, stack: 'Live Stack', score: '100/100' }],
        }),
      });
      return;
    }

    if (path === '/ops/platform/system-overview/history' && url.searchParams.get('limit') === '24') {
      await route.fulfill({
        ...okJson,
        body: JSON.stringify(basePayloads['/ops/platform/system-overview/history']),
      });
      return;
    }

    if (basePayloads[path]) {
      await route.fulfill({
        ...okJson,
        body: JSON.stringify(basePayloads[path]),
      });
      return;
    }

    await route.fulfill({ ...okJson, body: JSON.stringify({}) });
  });
}

test('platform page renders hybrid stacks from live API payload', async ({ page }) => {
  await mockPlatformApis(page, 200, 'LIVE-CHECK');
  await page.goto('/platform');

  await expect(page.getByRole('heading', { name: '100/100 Hybrid Stacks (Free + Open-Source Only)' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'LIVE-CHECK' })).toBeVisible();
  await expect(page.getByText('Live API smoke stack')).toBeVisible();
});

test('platform page keeps fallback hybrid stacks when live endpoint fails', async ({ page }) => {
  await mockPlatformApis(page, 204, 'LIVE-CHECK');
  await page.goto('/platform');

  await expect(page.getByRole('heading', { name: '100/100 Hybrid Stacks (Free + Open-Source Only)' })).toBeVisible();
  await expect(page.getByText('LIVE-CHECK')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Entity-First SEO' })).toBeVisible();
});
