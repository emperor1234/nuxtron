import { expect, test } from '@playwright/test';

test.describe('IRA Control Center', () => {
  test('renders backend chat analysis and action metadata', async ({ page }) => {
    await page.route('**/api/fastapi/**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;

      if (path.endsWith('/ira/status')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'ok',
            autonomy: { autonomy_enabled: true, protection_mode: false },
            connectors: [{ channel: 'chat', enabled: true, provider: 'internal' }],
            provider_readiness: {
              internal: { key: 'internal', label: 'Internal IRA', configured: true, model: 'rule_based', route: 'internal' },
              openai: {
                key: 'openai',
                label: 'OpenAI',
                configured: false,
                model: 'gpt-4.1-mini',
                route: 'openai',
                reason: 'Missing provider credentials/configuration',
              },
              anthropic: {
                key: 'anthropic',
                label: 'Anthropic',
                configured: true,
                model: 'claude-3-5-sonnet-latest',
                route: 'anthropic',
                reason: 'Configured and available',
              },
            },
            finance_health: { profit_margin_pct: 82 },
            risk_signal: { score: 0.12 },
            recent_events: [],
          }),
        });
        return;
      }

      if (path.endsWith('/ira/disputes/dashboard')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ cases: [] }) });
        return;
      }

      if (path.endsWith('/ira/crm/hybrid-recommendation')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ recommendation: 'corteza' }),
        });
        return;
      }

      if (path.endsWith('/ira/crm/connectors/status')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ connectors: [] }) });
        return;
      }

      if (path.endsWith('/crm/ops/live-sync')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ sync: { enabled: true, interval_seconds: 30, last_sync_at: '2026-05-30T10:00:00Z' } }),
        });
        return;
      }

      if (path.endsWith('/crm/ops/backup')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ schedule_health: 'healthy', next_runs: {} }),
        });
        return;
      }

      if (path.endsWith('/ira/playbook')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'ok',
            completion_chart: { achieved: 4, total: 6, percentage: 66.67 },
            milestones: [
              { key: 'first_session', label: 'First IRA session', target: 'Week 1', achieved: true, detail: 'Sessions observed: 2' },
              { key: 'profit_guard', label: 'Profit margin target met', target: 'Week 4', achieved: false, detail: 'Margin 62% vs target 70%' },
            ],
            decision_tree: [
              {
                question: 'Do you have paying users?',
                if_yes: 'Optimize retention and expansion; do not pause shipping.',
                if_no: 'Refine positioning and run customer interviews before adding scope.',
              },
            ],
          }),
        });
        return;
      }

      if (path.endsWith('/ira/chat')) {
        const requestBody = route.request().postDataJSON() as {
          context?: { llm_routing?: { preferred_provider?: string } };
        };
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'ok',
            ira: {
              response: `IRA prepared a campaign execution workflow via ${requestBody.context?.llm_routing?.preferred_provider ?? 'auto'}.`,
              confidence: 0.94,
              provider_requested: requestBody.context?.llm_routing?.preferred_provider ?? 'auto',
              provider_used: requestBody.context?.llm_routing?.preferred_provider ?? 'internal_rule_engine',
              provider_model: 'claude-3-5-sonnet-latest',
              provider_status: 'external_ok',
              intent: 'campaign_planning',
              domain: 'marketing',
              risk_assessment: { risk_level: 'low' },
              action_plan: {
                recommended_actions: [
                  { label: 'Create IRA autonomous run plan' },
                  { label: 'Execute low-risk operational action' },
                ],
              },
              knowledge_hits: [{ title: 'Summer launch brief' }],
            },
          }),
        });
        return;
      }

      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
    });

    await page.goto('/ira');
    await expect(page.getByRole('heading', { name: 'IRA Control Center' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Provider Readiness' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Extreme Success Playbook' })).toBeVisible();
    await expect(page.getByText('66.67%')).toBeVisible();
    await expect(page.getByText('First IRA session')).toBeVisible();
    await expect(page.getByText('Do you have paying users?')).toBeVisible();
    await expect(page.getByText('Internal IRA')).toBeVisible();
    await expect(page.getByText('OpenAI: not configured | Claude: ready')).toBeVisible();
    await expect(page.getByText('Reason: Missing provider credentials/configuration')).toBeVisible();
    await expect(page.getByText('Reason: Configured and available')).toBeVisible();
    await expect(page.getByText('OpenAI: Missing provider credentials/configuration')).toBeVisible();
    await expect(page.locator('select[aria-label="IRA control center provider route"] option[value="openai"]')).toHaveAttribute(
      'disabled',
      ''
    );
    await expect(
      page.locator('select[aria-label="IRA control center provider route"] option[value="anthropic"]')
    ).not.toHaveAttribute('disabled', '');

    await page.getByLabel('IRA control center provider route').selectOption('anthropic');
    await page.getByPlaceholder('Tell IRA what to do').fill('Draft a launch campaign workflow');
    await page.getByRole('button', { name: 'Send To IRA' }).click();

    const result = page.getByLabel('IRA chat result');
    await expect(result).toBeVisible();
    await expect(result.getByText('IRA prepared a campaign execution workflow via anthropic.')).toBeVisible();
    await expect(result.getByText('94% confidence')).toBeVisible();
    await expect(result.getByText('Intent: campaign_planning')).toBeVisible();
    await expect(result.getByText('Domain: marketing')).toBeVisible();
    await expect(result.getByText('Risk: low')).toBeVisible();
    await expect(result.getByText('Provider: anthropic')).toBeVisible();
    await expect(result.getByText('Route: external_ok')).toBeVisible();
    await expect(result.getByText('Model: claude-3-5-sonnet-latest')).toBeVisible();
    await expect(result.getByText('Create IRA autonomous run plan')).toBeVisible();
    await expect(result.getByText('Summer launch brief')).toBeVisible();
  });
});