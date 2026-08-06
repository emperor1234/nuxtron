import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

function headers() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-this-fastapi-key',
    'X-Tenant-Id': 'tenant-deep-reviews',
  };
}

async function ingestReview(page: import('@playwright/test').Page, overrides: Record<string, unknown> = {}) {
  return page.evaluate(
    async ({ base, hdrs, data }) => {
      const res = await fetch(`${base}/reviews/ingest`, {
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
        platform: 'google',
        reviewer: 'Test Reviewer',
        rating: 4,
        text: 'Great platform overall.',
        category: 'general',
        ...overrides,
      },
    }
  );
}

test.describe('Deep reviews engine coverage', () => {
  test('5-star review ingested with positive sentiment', async ({ page }) => {
    await page.goto('/');

    const resp = await ingestReview(page, { rating: 5, text: 'Absolutely excellent.', platform: 'google' });
    expect(resp.review.sentiment).toBe('positive');
    expect(resp.review.rating).toBe(5);
    expect(resp.review.responded).toBe(false);
    expect(resp.review.response).toBeNull();
  });

  test('1-star review ingested with negative sentiment', async ({ page }) => {
    await page.goto('/');

    const resp = await ingestReview(page, { rating: 1, text: 'Terrible experience.', platform: 'trustpilot' });
    expect(resp.review.sentiment).toBe('negative');
    expect(resp.review.rating).toBe(1);
    expect(resp.review.platform).toBe('trustpilot');
  });

  test('3-star review ingested with neutral sentiment', async ({ page }) => {
    await page.goto('/');

    const resp = await ingestReview(page, { rating: 3, text: 'Average, nothing special.', platform: 'yelp' });
    expect(resp.review.sentiment).toBe('neutral');
    expect(resp.review.rating).toBe(3);
  });

  test('respond to a review marks it as responded with response text', async ({ page }) => {
    await page.goto('/');

    const ingestResp = await ingestReview(page, { rating: 2, text: 'Disappointed with the service.' });
    const reviewId = ingestResp.review.id;

    const respondResp = await page.evaluate(
      async ({ base, hdrs, id }) => {
        const res = await fetch(`${base}/reviews/${id}/respond`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ response: 'We are sorry to hear that. Please contact our support team.' }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(), id: reviewId }
    );

    expect(respondResp.review.responded).toBe(true);
    expect(respondResp.review.response).toContain('sorry to hear');
    expect(respondResp.review.response_at).not.toBeNull();
  });

  test('reviews list returns all ingested reviews in recency order', async ({ page }) => {
    await page.goto('/');

    await ingestReview(page, { rating: 5, reviewer: 'Alice' });
    await ingestReview(page, { rating: 2, reviewer: 'Bob' });

    const listResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/reviews`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(listResp.count).toBeGreaterThanOrEqual(2);
    // Most recent first
    expect(new Date(listResp.reviews[0].created_at).getTime()).toBeGreaterThanOrEqual(
      new Date(listResp.reviews[1].created_at).getTime()
    );
  });

  test('summary calculates reputation score, avg_rating and responded_ratio correctly', async ({ page }) => {
    await page.goto('/');

    // Ingest a mix: one 5-star (positive) and respond, one 1-star (negative) no response
    const r1 = await ingestReview(page, { rating: 5 });
    await page.evaluate(
      async ({ base, hdrs, id }) => {
        await fetch(`${base}/reviews/${id}/respond`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ response: 'Thank you!' }),
        });
      },
      { base: fastapiBase, hdrs: headers(), id: r1.review.id }
    );
    await ingestReview(page, { rating: 1 });

    const summaryResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/reviews/summary`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    const s = summaryResp.summary;
    expect(s.total_reviews).toBeGreaterThanOrEqual(2);
    expect(s.avg_rating).toBeGreaterThan(0);
    expect(s.reputation_score).toBeGreaterThan(0);
    expect(s.reputation_score).toBeLessThanOrEqual(100);
    expect(s.responded_ratio).toBeGreaterThan(0);
    expect(s.sentiment.positive).toBeGreaterThanOrEqual(1);
    expect(s.sentiment.negative).toBeGreaterThanOrEqual(1);
  });

  test('platform breakdown in summary groups reviews by source correctly', async ({ page }) => {
    await page.goto('/');

    await ingestReview(page, { platform: 'google', rating: 4 });
    await ingestReview(page, { platform: 'google', rating: 5 });
    await ingestReview(page, { platform: 'trustpilot', rating: 3 });

    const summaryResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/reviews/summary`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(summaryResp.summary.platforms.google).toBeGreaterThanOrEqual(2);
    expect(summaryResp.summary.platforms.trustpilot).toBeGreaterThanOrEqual(1);
  });
});
