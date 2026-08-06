import { expect, test } from '@playwright/test';

test.describe('IRA Chat Widget', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.locator('.ira-trigger').waitFor({ state: 'visible', timeout: 20000 });
  });

  test('IRA trigger button is visible on dashboard', async ({ page }) => {
    const trigger = page.locator('.ira-trigger');
    await expect(trigger).toBeVisible();
  });

  test('IRA panel opens with interactive open state class', async ({ page }) => {
    await page.locator('.ira-trigger').click();
    const panel = page.locator('.ira-panel.ira-panel-open');
    await expect(panel).toBeVisible();
    await expect(page.locator('.ira-head')).toBeVisible();
  });

  test('IRA input sends message with Enter key', async ({ page }) => {
    await page.route('**/api/fastapi/ira/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          ira: {
            response: 'Mocked response from IRA via Enter',
          },
        }),
      });
    });

    await page.locator('.ira-trigger').click();
    const input = page.getByLabel('Message IRA');
    await input.fill('Help me with SEO');
    await page.keyboard.press('Enter');

    await expect(page.getByText('Help me with SEO')).toBeVisible();
    await expect(page.getByText('Mocked response from IRA via Enter')).toBeVisible();
  });

  test('IRA send button click submits message', async ({ page }) => {
    await page.route('**/api/fastapi/ira/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          provider_readiness: {
            internal: { key: 'internal', label: 'Internal IRA', configured: true, model: 'rule_based', route: 'internal' },
            openai: {
              key: 'openai',
              label: 'OpenAI',
              configured: true,
              model: 'gpt-4.1-mini',
              route: 'openai',
              reason: 'Configured and available',
            },
            anthropic: {
              key: 'anthropic',
              label: 'Anthropic',
              configured: false,
              model: 'claude-3-5-sonnet-latest',
              route: 'anthropic',
              reason: 'Missing provider credentials/configuration',
            },
          },
        }),
      });
    });

    await page.route('**/api/fastapi/ira/playbook', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          completion_chart: { achieved: 4, total: 6, percentage: 66.67 },
          decision_tree: [
            {
              question: 'Do you have paying users?',
              if_yes: 'Optimize retention and expansion; do not pause shipping.',
              if_no: 'Refine positioning and run customer interviews before adding scope.',
            },
          ],
        }),
      });
    });

    await page.route('**/api/fastapi/ira/chat', async (route) => {
      const rawBody = route.request().postData();
      const requestBody = (rawBody ? JSON.parse(rawBody) : {}) as {
        message?: string;
        context?: { llm_routing?: { preferred_provider?: string } };
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          ira: {
            response: `Mocked click response: ${requestBody.message ?? ''} (${requestBody.context?.llm_routing?.preferred_provider ?? 'auto'})`,
          },
        }),
      });
    });

    await page.locator('.ira-trigger').click();
    await page.getByLabel('IRA provider route').selectOption('openai');
    const input = page.getByLabel('Message IRA');
    await input.fill('Plan an ads sprint');

    const sendButton = page.getByRole('button', { name: 'Send' });
    await expect(sendButton).toBeEnabled();
    const chatResponsePromise = page.waitForResponse((response) => response.url().includes('/api/fastapi/ira/chat') && response.ok());
    await sendButton.click();
    await chatResponsePromise;

    await expect(page.locator('.ira-msg.ira-msg-user', { hasText: 'Plan an ads sprint' })).toBeVisible();
    await expect(page.locator('.ira-msg.ira-msg-assistant').last()).toContainText('Mocked click response: Plan an ads sprint (openai)', {
      timeout: 20000,
    });
  });

  test('IRA renders backend confidence, domain, risk, and action plan metadata', async ({ page }) => {
    await page.route('**/api/fastapi/ira/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          provider_readiness: {
            internal: { key: 'internal', label: 'Internal IRA', configured: true, model: 'rule_based', route: 'internal' },
            openai: {
              key: 'openai',
              label: 'OpenAI',
              configured: true,
              model: 'gpt-4.1-mini',
              route: 'openai',
              reason: 'Configured and available',
            },
            anthropic: {
              key: 'anthropic',
              label: 'Anthropic',
              configured: false,
              model: 'claude-3-5-sonnet-latest',
              route: 'anthropic',
              reason: 'Missing provider credentials/configuration',
            },
          },
        }),
      });
    });

    await page.route('**/api/fastapi/ira/playbook', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          completion_chart: { achieved: 4, total: 6, percentage: 66.67 },
          decision_tree: [
            {
              question: 'Do you have paying users?',
              if_yes: 'Optimize retention and expansion; do not pause shipping.',
              if_no: 'Refine positioning and run customer interviews before adding scope.',
            },
          ],
        }),
      });
    });

    await page.route('**/api/fastapi/ira/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          ira: {
            response: 'Production workflow drafted.',
            confidence: 0.91,
            provider_requested: 'openai',
            provider_used: 'openai',
            provider_model: 'gpt-4.1-mini',
            provider_status: 'external_ok',
            intent: 'campaign_planning',
            domain: 'marketing',
            risk_assessment: {
              risk_level: 'low',
            },
            action_plan: {
              recommended_actions: [
                { label: 'Create IRA autonomous run plan' },
                { label: 'Execute low-risk operational action' },
              ],
            },
            knowledge_hits: [{ title: 'Q2 campaign brief' }],
          },
        }),
      });
    });

    await page.locator('.ira-trigger').click();
    await expect(page.getByText('OpenAI: ready | Claude: not configured')).toBeVisible();
    await expect(page.getByText('OpenAI reason: Configured and available')).toBeVisible();
    await expect(page.getByText('Claude reason: Missing provider credentials/configuration')).toBeVisible();
    await expect(page.getByText('Playbook completion: 66.67% (4/6)')).toBeVisible();
    await expect(page.getByText('Playbook focus: Do you have paying users?')).toBeVisible();
    await expect(page.getByText('Claude: Missing provider credentials/configuration')).toBeVisible();
    await expect(page.locator('select[aria-label="IRA provider route"] option[value="anthropic"]')).toHaveAttribute('disabled', '');
    await expect(page.locator('select[aria-label="IRA provider route"] option[value="openai"]')).not.toHaveAttribute('disabled', '');
    await page.getByLabel('Message IRA').fill('Plan a campaign sprint');
    await page.getByRole('button', { name: 'Send' }).click();

    await expect(page.getByText('Production workflow drafted.')).toBeVisible();
    await expect(page.getByText('91% confidence')).toBeVisible();
    await expect(page.getByText('Intent: campaign_planning')).toBeVisible();
    await expect(page.getByText('Domain: marketing')).toBeVisible();
    await expect(page.getByText('Risk: low')).toBeVisible();
    await expect(page.getByText('Provider: openai')).toBeVisible();
    await expect(page.getByText('Route: external_ok')).toBeVisible();
    await expect(page.getByText('Model: gpt-4.1-mini')).toBeVisible();
    await expect(page.getByText('Create IRA autonomous run plan')).toBeVisible();
    await expect(page.getByText('Knowledge hits: Q2 campaign brief')).toBeVisible();
  });

  test('IRA refresh button re-fetches status and playbook summary', async ({ page }) => {
    let statusCalls = 0;
    let playbookCalls = 0;

    await page.route('**/api/fastapi/ira/status', async (route) => {
      statusCalls += 1;
      const firstResponse = statusCalls === 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          provider_readiness: {
            internal: {
              key: 'internal',
              label: 'Internal IRA',
              configured: true,
              model: 'rule_based',
              route: 'internal',
              reason: 'Configured and available',
            },
            openai: {
              key: 'openai',
              label: 'OpenAI',
              configured: true,
              model: 'gpt-4.1-mini',
              route: 'openai',
              reason: firstResponse ? 'Configured and available' : 'Refreshed and available',
            },
            anthropic: {
              key: 'anthropic',
              label: 'Anthropic',
              configured: true,
              model: 'claude-3-5-sonnet-latest',
              route: 'anthropic',
              reason: firstResponse ? 'Configured and available' : 'Refreshed and available',
            },
          },
        }),
      });
    });

    await page.route('**/api/fastapi/ira/playbook', async (route) => {
      playbookCalls += 1;
      const firstResponse = playbookCalls === 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          completion_chart: firstResponse ? { achieved: 4, total: 6, percentage: 66.67 } : { achieved: 6, total: 6, percentage: 100 },
          decision_tree: [
            {
              question: firstResponse ? 'Do you have paying users?' : 'Can you scale paid channels now?',
              if_yes: 'Proceed with focused expansion.',
              if_no: 'Fix retention before acquisition scaling.',
            },
          ],
        }),
      });
    });

    await page.locator('.ira-trigger').click();
    await expect(page.getByText('Playbook completion: 66.67% (4/6)')).toBeVisible();
    await expect(page.getByText('Playbook focus: Do you have paying users?')).toBeVisible();

    await page.getByLabel('Refresh IRA status').click();

    await expect(page.getByText('Playbook completion: 100.00% (6/6)')).toBeVisible();
    await expect(page.getByText('Playbook focus: Can you scale paid channels now?')).toBeVisible();
    await expect(page.getByText('OpenAI reason: Refreshed and available')).toBeVisible();
  });
});
