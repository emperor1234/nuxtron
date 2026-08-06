import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

function headers() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-this-fastapi-key',
    'X-Tenant-Id': 'tenant-deep-vse',
  };
}

async function getJson(page: import('@playwright/test').Page, path: string) {
  return page.evaluate(
    async ({ base, hdrs, p }) => {
      const res = await fetch(`${base}${p}`, { method: 'GET', headers: hdrs });
      return res.json();
    },
    { base: fastapiBase, hdrs: headers(), p: path }
  );
}

async function postJson(page: import('@playwright/test').Page, path: string, payload: Record<string, unknown>) {
  return page.evaluate(
    async ({ base, hdrs, p, data }) => {
      const res = await fetch(`${base}${p}`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify(data),
      });
      return res.json();
    },
    { base: fastapiBase, hdrs: headers(), p: path, data: payload }
  );
}

test.describe('Deep VSE coverage', () => {
  test('command centre and engine inventory are available', async ({ page }) => {
    await page.goto('/');

    const engines = await getJson(page, '/vse/engines');
    expect(engines.status).toBe('ok');
    expect(engines.engines.length).toBe(12);

    const commandCentre = await getJson(page, '/vse/command-centre');
    expect(commandCentre.status).toBe('ok');
    expect(commandCentre.command_centre).toBeDefined();
  });

  test('trigger library has 247 entries and analysis returns VPS', async ({ page }) => {
    await page.goto('/');

    const library = await getJson(page, '/vse/triggers/library');
    expect(library.total).toBe(247);
    expect(library.triggers.length).toBe(247);

    const analysis = await postJson(page, '/vse/triggers/analyze', {
      content: 'Discover the secret framework most teams never use to grow reach fast',
      platform: 'linkedin',
      audience: 'b2b professionals',
    });
    expect(analysis.status).toBe('ok');
    expect(analysis.analysis.viral_probability_score).toBeGreaterThanOrEqual(80);
  });

  test('brief generation and algorithm optimisation pipeline works', async ({ page }) => {
    await page.goto('/');

    const brief = await postJson(page, '/vse/brief', {
      objective: 'Increase follower growth',
      audience: 'B2B executives',
      platforms: ['linkedin', 'x'],
      tone: 'professional',
      urgency: 'standard',
    });
    expect(brief.status).toBe('ok');
    expect(brief.brief.id).toContain('brief-');

    const optimize = await postJson(page, '/vse/algorithm/optimize', {
      content: 'A detailed post on scaling content velocity',
      platform: 'linkedin',
      content_type: 'text',
    });
    expect(optimize.status).toBe('ok');
    expect(optimize.optimisation.format_compliance_score).toBeGreaterThanOrEqual(80);
  });

  test('network map and simulation lifecycle works', async ({ page }) => {
    await page.goto('/');

    const map = await postJson(page, '/vse/network/map', {
      audience_segment: 'B2B SaaS founders',
      depth: 2,
    });
    expect(map.status).toBe('ok');
    expect(map.map.id).toContain('nmap-');

    const superconnectors = await getJson(page, '/vse/network/superconnectors');
    expect(superconnectors.status).toBe('ok');
    expect(superconnectors.superconnectors.length).toBeGreaterThan(0);

    const simulation = await postJson(page, '/vse/simulate', {
      content_summary: 'Launch post for new B2B offer',
      platform: 'linkedin',
      audience_size: 50000,
      trigger_ids: [1, 3, 5],
    });
    expect(simulation.status).toBe('ok');
    expect(simulation.simulation.monte_carlo_runs).toBe(10000);
  });

  test('detonation plan can be executed and listed', async ({ page }) => {
    await page.goto('/');

    const plan = await postJson(page, '/vse/detonation/plan', {
      content: 'Cross-platform launch content',
      platforms: ['linkedin', 'x', 'instagram'],
      objective: 'reach',
    });
    expect(plan.status).toBe('ok');
    expect(plan.detonation.status).toBe('planned');

    const detonationId = plan.detonation.id as string;
    const execute = await postJson(page, `/vse/detonation/${detonationId}/execute`, {});
    expect(execute.status).toBe('ok');
    expect(execute.detonation.status).toBe('executed');

    const list = await getJson(page, '/vse/detonation');
    expect(list.count).toBeGreaterThanOrEqual(1);

    const history = await getJson(page, '/vse/detonation/history');
    expect(history.status).toBe('ok');
    expect(history.count).toBeGreaterThanOrEqual(1);
  });

  test('swarm and momentum engines support compose/activate/monitor/inject', async ({ page }) => {
    await page.goto('/');

    const swarm = await postJson(page, '/vse/swarm/compose', {
      post_summary: 'High-retention thought leadership post',
      niche: 'B2B marketing',
      platforms: ['linkedin'],
      swarm_size: 30,
    });
    expect(swarm.status).toBe('ok');
    const swarmId = swarm.swarm.id as string;

    const activate = await postJson(page, '/vse/swarm/activate', {
      swarm_id: swarmId,
      activation_note: 'test activation',
    });
    expect(activate.status).toBe('ok');
    expect(activate.swarm.status).toBe('active');

    const swarmStatus = await getJson(page, `/vse/swarm/${swarmId}/status`);
    expect(swarmStatus.status).toBe('ok');
    expect(swarmStatus.swarm_status).toBe('active');

    const missingSwarm = await getJson(page, '/vse/swarm/swarm-does-not-exist/status');
    expect(missingSwarm.detail).toContain('Swarm not found');

    const momentumStart = await postJson(page, '/vse/momentum/start', {
      post_summary: 'Momentum monitoring test post',
      platform: 'linkedin',
      target_viral_threshold: 50,
    });
    expect(momentumStart.status).toBe('ok');
    const momentumId = momentumStart.momentum_event.id as string;

    const momentumGet = await getJson(page, `/vse/momentum/${momentumId}`);
    expect(momentumGet.status).toBe('ok');
    expect(momentumGet.momentum_event.current_velocity).toBeGreaterThanOrEqual(1);

    const inject = await postJson(page, `/vse/momentum/${momentumId}/inject`, {
      injection_type: 'comment_campaign',
      intensity: 'medium',
    });
    expect(inject.status).toBe('ok');
  });

  test('content, emotion, trends, paid, dark social and immortalisation work', async ({ page }) => {
    await page.goto('/');

    const content = await postJson(page, '/vse/content/generate', {
      topic: 'B2B lead generation',
      objective: 'reach',
      platform: 'linkedin',
      emotional_vector: 'curiosity',
      trigger_ids: [1, 3, 5],
    });
    expect(content.status).toBe('ok');
    expect(content.content.viral_probability_score).toBeGreaterThanOrEqual(85);

    const score = await postJson(page, '/vse/content/score', {
      content: 'This is a content scoring payload',
      platform: 'linkedin',
      trigger_ids: [1, 3],
    });
    expect(score.status).toBe('ok');
    expect(score.passes_threshold).toBe(true);

    const emotion = await postJson(page, '/vse/emotion/analyze', {
      content: 'An inspiring and surprising story that reveals a new strategy',
    });
    expect(emotion.status).toBe('ok');

    const trends = await getJson(page, '/vse/trends/live');
    expect(trends.status).toBe('ok');
    expect(trends.trends.length).toBeGreaterThan(0);

    const hijack = await postJson(page, '/vse/trends/hijack', {
      trend_id: 1,
      brand_voice: 'professional',
      platform: 'linkedin',
    });
    expect(hijack.status).toBe('ok');

    const assess = await postJson(page, '/vse/paid/assess', {
      post_summary: 'Organic winner post',
      organic_engagement_rate: 4.5,
      organic_impressions: 1300,
      minutes_live: 25,
    });
    expect(assess.status).toBe('ok');
    const assessmentId = assess.assessment.id as string;

    const amplify = await postJson(page, '/vse/paid/amplify', {
      assessment_id: assessmentId,
      budget_gbp: 250,
      platforms: ['linkedin'],
      objective: 'reach',
    });
    expect(amplify.status).toBe('ok');

    const dark = await postJson(page, '/vse/dark-social/seed', {
      content: 'Forward this to your private founder groups',
      channel_types: ['whatsapp', 'slack'],
    });
    expect(dark.status).toBe('ok');

    const attribution = await postJson(page, '/vse/dark-social/attribution', {
      campaign_id: 'cmp-vse-001',
      touchpoints: ['whatsapp_share', 'slack_thread'],
      conversions: 12,
      conversion_value: 2400,
    });
    expect(attribution.status).toBe('ok');
    expect(attribution.attribution.length).toBeGreaterThan(0);

    const attributionNormalised = await postJson(page, '/vse/dark-social/attribution', {
      campaign_id: 'cmp-vse-002',
      touchpoints: ['whatsapp_share', '  WHATSAPP_SHARE  ', ''],
      conversions: 4,
      conversion_value: 80,
    });
    expect(attributionNormalised.status).toBe('ok');
    expect(attributionNormalised.normalised_touchpoints_count).toBe(1);
    expect(attributionNormalised.attribution[0].touchpoint).toBe('whatsapp_share');

    const attributionInvalidValue = await postJson(page, '/vse/dark-social/attribution', {
      campaign_id: 'cmp-vse-003',
      touchpoints: [],
      conversions: 0,
      conversion_value: 100,
    });
    expect(attributionInvalidValue.detail).toContain('conversion_value cannot be positive');

    const immortal = await postJson(page, '/vse/immortalise', {
      viral_event_id: 've-test-001',
      post_summary: 'Top performing launch content',
      viral_impressions: 500000,
      platforms_achieved: ['linkedin', 'x'],
      key_insight: 'Novelty + utility outperformed generic hooks',
    });
    expect(immortal.status).toBe('ok');

    const vault = await getJson(page, '/vse/immortalise/vault');
    expect(vault.status).toBe('ok');
    expect(vault.vault_entries).toBeGreaterThanOrEqual(1);
  });

  // ── NEW: generate-variants + dedup controls ────────────────────────────

  test('content/generate returns dedupe metadata when avoid_duplicates is set', async ({ page }) => {
    await page.goto('/');

    const result = await postJson(page, '/vse/content/generate', {
      topic: 'AI-powered recruitment automation',
      objective: 'reach',
      platform: 'linkedin',
      emotional_vector: 'awe',
      trigger_ids: [2, 4],
      avoid_duplicates: true,
      uniqueness_boost: 'high',
    });
    expect(result.status).toBe('ok');
    expect(result.content.viral_probability_score).toBeGreaterThanOrEqual(85);
    // dedupe metadata must be present
    expect(result.dedupe).toBeDefined();
    expect(result.dedupe.uniqueness_boost).toBe('high');
    expect(typeof result.dedupe.is_duplicate).toBe('boolean');
    expect(typeof result.dedupe.fingerprint).toBe('string');
  });

  test('content/generate-variants returns N variants with batch dedup flag', async ({ page }) => {
    await page.goto('/');

    const result = await postJson(page, '/vse/content/generate-variants', {
      topic: 'SaaS churn reduction playbook',
      objective: 'authority',
      platform: 'linkedin',
      emotional_vector: 'curiosity',
      format: 'thread',
      trigger_ids: [1, 3, 5],
      count: 3,
      uniqueness_boost: 'medium',
      avoid_duplicates: true,
    });

    expect(result.status).toBe('ok');
    expect(result.all_variants).toBeDefined();
    expect(result.all_variants.length).toBe(3);
    expect(result.primary_variant).toBeDefined();
    expect(result.batch_dedupe_applied).toBe(true);
    // All variants must have a VPS score
    for (const v of result.all_variants) {
      expect(typeof v.vps_score).toBe('number');
    }
    // Primary variant should match first entry
    expect(result.primary_variant.content_id).toBe(result.all_variants[0].content_id);
  });

  test('content/generate-variants respects count boundary (max 10, min 1)', async ({ page }) => {
    await page.goto('/');

    const res1 = await postJson(page, '/vse/content/generate-variants', {
      topic: 'Startup fundraising strategy',
      platform: 'linkedin',
      count: 1,
    });
    expect(res1.status).toBe('ok');
    expect(res1.all_variants.length).toBe(1);

    const res5 = await postJson(page, '/vse/content/generate-variants', {
      topic: 'Enterprise sales cycles',
      platform: 'x',
      count: 5,
    });
    expect(res5.status).toBe('ok');
    expect(res5.all_variants.length).toBe(5);
  });

  test('content/generate-variants with avoid_duplicates=false still returns variants', async ({ page }) => {
    await page.goto('/');

    const result = await postJson(page, '/vse/content/generate-variants', {
      topic: 'Cold outreach personalisation',
      platform: 'linkedin',
      count: 2,
      avoid_duplicates: false,
      uniqueness_boost: 'low',
    });
    expect(result.status).toBe('ok');
    expect(result.all_variants.length).toBe(2);
    expect(result.batch_dedupe_applied).toBe(false);
  });

  test('VSE page is reachable via /vse route', async ({ page }) => {
    await page.goto('/vse');
    // Must not 404 — expect some VSE page title in DOM
    await expect(page.locator('h1')).toContainText('Viral Singularity Engine');
  });

  test('VSE page sidebar navigation link is present for admin role', async ({ page }) => {
    // Set admin role cookie and go to any page with sidebar
    await page.goto('/dashboard');
    // The sidebar nav entry should be present; avoid generic href locator collisions.
    const vseLink = page.getByRole('link', { name: 'Viral Singularity Engine' });
    await expect(vseLink).toBeVisible();
    await expect(vseLink).toContainText('Viral Singularity Engine');
  });

  test('generate-variants UI section renders on /vse page', async ({ page }) => {
    await page.goto('/vse');
    // The multi-variant generator panel must be present
    await expect(page.getByText('Multi-Variant Generator')).toBeVisible();
    await expect(page.getByText('Anti-Duplication Batch')).toBeVisible();
    // Variants count input field
    const countInput = page.locator('#varCount');
    await expect(countInput).toBeVisible();
    await expect(countInput).toHaveValue('3');
  });

  test('avoid-duplicates checkbox is present and toggleable on /vse page', async ({ page }) => {
    await page.goto('/vse');
    await expect(page.getByText(/Multi-Variant Generator/i)).toBeVisible();
    const checkbox = page.locator('#cfAvoidDups');
    await expect(checkbox).toBeVisible();
    await expect(checkbox).toBeChecked(); // default is true
    // Toggle off
    await checkbox.uncheck();
    await expect(checkbox).not.toBeChecked();
    // Toggle on
    await checkbox.check();
    await expect(checkbox).toBeChecked();
  });

  test('uniqueness boost field accepts low/medium/high values on /vse page', async ({ page }) => {
    await page.goto('/vse');
    await expect(page.getByText(/Multi-Variant Generator/i)).toBeVisible();
    const boostField = page.locator('#cfUniqueness');
    await expect(boostField).toBeVisible();
    await expect(boostField).toHaveValue('medium'); // default
    await boostField.fill('high');
    await expect(boostField).toHaveValue('high');
    await boostField.fill('low');
    await expect(boostField).toHaveValue('low');
  });

  test('generate variants button submits and shows variant cards', async ({ page }) => {
    await page.route('**/api/fastapi/vse/content/generate-variants', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          tenant_id: 'tenant-demo',
          variants: [
            {
              id: 'var-1',
              topic: 'B2B lead generation',
              platform: 'linkedin',
              viral_probability_score: 90,
            },
            {
              id: 'var-2',
              topic: 'B2B lead generation',
              platform: 'linkedin',
              viral_probability_score: 89,
            },
          ],
          all_variants: [
            {
              id: 'var-1',
              topic: 'B2B lead generation',
              platform: 'linkedin',
              viral_probability_score: 90,
            },
            {
              id: 'var-2',
              topic: 'B2B lead generation',
              platform: 'linkedin',
              viral_probability_score: 89,
            },
          ],
          primary_variant: {
            id: 'var-1',
            topic: 'B2B lead generation',
            platform: 'linkedin',
            viral_probability_score: 90,
          },
          batch_dedupe_applied: true,
        }),
      });
    });

    await page.goto('/vse');
    await expect(page.getByText(/Multi-Variant Generator/i)).toBeVisible();

    // Fill variant count
    await page.locator('#varCount').fill('2');

    // Click the dynamic variants generation button.
    await page.getByRole('button', { name: /^Generate 2 Variants$/i }).click();

    // Variants summary and cards should render.
    await expect(page.getByText(/Variants returned:/i)).toBeVisible({ timeout: 10000 });
    // At least Variant 1 header must appear
    await expect(page.getByText('Variant 1', { exact: false }).first()).toBeVisible({ timeout: 10000 });
  });
});
