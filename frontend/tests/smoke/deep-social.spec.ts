import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

function headers() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-this-fastapi-key',
    'X-Tenant-Id': 'tenant-deep-social',
  };
}

async function ingestMention(page: import('@playwright/test').Page, overrides: Record<string, unknown> = {}) {
  return page.evaluate(
    async ({ base, hdrs, data }) => {
      const res = await fetch(`${base}/social/listening/ingest`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify(data),
      });
      return res.json();
    },
    {
      base: fastapiBase,
      hdrs: headers(),
      data: {
        platform: 'x',
        query: 'nuxtron',
        author_handle: '@test_user',
        text: 'Test mention text',
        sentiment: 'neutral',
        engagement_count: 5,
        ...overrides,
      },
    }
  );
}

test.describe('Deep social listening coverage', () => {
  test('ingest positive mention and verify summary reflects correct sentiment', async ({ page }) => {
    await page.goto('/');

    const mentionResp = await ingestMention(page, { sentiment: 'positive', engagement_count: 20 });
    expect(mentionResp.mention.sentiment).toBe('positive');
    expect(mentionResp.mention.engagement_count).toBe(20);

    const summaryResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/summary`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(summaryResp.summary.total_mentions).toBeGreaterThanOrEqual(1);
    expect(summaryResp.summary.sentiment.positive).toBeGreaterThanOrEqual(1);
  });

  test('ingest negative high-engagement mention triggers crisis watch signal', async ({ page }) => {
    await page.goto('/');

    // Ingest enough high-engagement negative mentions to trigger crisis=watch
    for (let i = 0; i < 3; i++) {
      await ingestMention(page, {
        tenant_id_override: 'tenant-deep-social',
        query: 'crisis-test',
        platform: 'x',
        sentiment: 'negative',
        engagement_count: 60,
      });
    }

    const summaryResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/summary`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    // 3+ high-negative-engagement mentions should activate crisis watch
    expect(summaryResp.summary.crisis.triggered).toBe(true);
    expect(['watch', 'high', 'critical']).toContain(summaryResp.summary.crisis.level);
    expect(summaryResp.summary.crisis.high_negative_mentions).toBeGreaterThanOrEqual(3);
  });

  test('create alert rule and verify triggered alert appears after matching mention', async ({ page }) => {
    await page.goto('/');

    // Create alert rule: fire on negative x mentions
    const ruleResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/rules`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({
            name: 'Negative X Alert',
            query: 'nuxtron',
            platform: 'x',
            min_engagement: 0,
            negative_only: true,
          }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(ruleResp.rule.id).toBeGreaterThan(0);
    expect(ruleResp.rule.negative_only).toBe(true);

    // Ingest matching negative mention
    await ingestMention(page, { platform: 'x', query: 'nuxtron', sentiment: 'negative', engagement_count: 10 });

    // Alerts list should contain an entry from our rule
    const alertsResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/alerts`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(alertsResp.alerts.length).toBeGreaterThanOrEqual(1);
    expect(alertsResp.alerts[0].status).toBe('open');
  });

  test('mentions list is filterable by tenant and ordered by recency', async ({ page }) => {
    await page.goto('/');

    await ingestMention(page, { text: 'First mention', platform: 'instagram', query: 'brand' });
    await ingestMention(page, { text: 'Second mention', platform: 'linkedin', query: 'brand' });

    const mentionsResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/mentions`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(mentionsResp.count).toBeGreaterThanOrEqual(2);
    // Most recent first
    expect(new Date(mentionsResp.mentions[0].created_at).getTime()).toBeGreaterThanOrEqual(
      new Date(mentionsResp.mentions[1].created_at).getTime()
    );
  });

  test('clusters endpoint groups mentions by query, platform and sentiment', async ({ page }) => {
    await page.goto('/');

    await ingestMention(page, { platform: 'x', query: 'cluster-a', sentiment: 'positive' });
    await ingestMention(page, { platform: 'x', query: 'cluster-a', sentiment: 'positive' });
    await ingestMention(page, { platform: 'instagram', query: 'cluster-b', sentiment: 'negative' });

    const clustersResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/clusters`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(clustersResp.clusters.length).toBeGreaterThanOrEqual(2);
    const xPositive = clustersResp.clusters.find(
      (c: { platform: string; sentiment: string; query: string }) =>
        c.platform === 'x' && c.sentiment === 'positive' && c.query === 'cluster-a'
    );
    expect(xPositive).toBeDefined();
    expect(xPositive.mentions).toBeGreaterThanOrEqual(2);
  });

  test('summary top_queries lists most mentioned queries first', async ({ page }) => {
    await page.goto('/');

    // Ingest more of top-query than other-query
    for (let i = 0; i < 3; i++) {
      await ingestMention(page, { query: 'top-query', platform: 'x' });
    }
    await ingestMention(page, { query: 'other-query', platform: 'x' });

    const summaryResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/social/listening/summary`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(summaryResp.summary.top_queries.length).toBeGreaterThanOrEqual(1);
    // The most ingested query should rank first
    const topQuery = summaryResp.summary.top_queries[0];
    expect(topQuery.mentions).toBeGreaterThanOrEqual(3);
  });
});
