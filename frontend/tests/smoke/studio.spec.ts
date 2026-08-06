import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

async function cardForHeading(page: Page, heading: string) {
  return page.getByRole('heading', { name: heading, exact: true }).locator('xpath=..');
}

test('studio loads metrics and provider bridge actions', async ({ page }) => {
  await page.goto('/studio');

  await expect(page.getByRole('heading', { name: 'Nuxtron Studio' })).toBeVisible();
  await expect(page.getByText('FastAPI base URL: http://127.0.0.1:4101')).toBeVisible();

  const metricsCard = await cardForHeading(page, 'Platform Metrics Summary');
  await metricsCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(metricsCard.locator('pre')).toContainText('tenant-demo');
  await expect(metricsCard.locator('pre')).toContainText('twilio_messages_memory');

  const smsCard = await cardForHeading(page, 'Twilio — Send SMS');
  await smsCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(smsCard.locator('pre')).toContainText('SM1234567890abcdef');
  await expect(smsCard.locator('pre')).toContainText('queued');

  const slackCard = await cardForHeading(page, 'Slack — Send Message');
  await slackCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(slackCard.locator('pre')).toContainText('#nuxtron-alerts');
  await expect(slackCard.locator('pre')).toContainText('true');

  const listeningCard = await cardForHeading(page, 'Social Listening Demo');
  await listeningCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(listeningCard.locator('pre')).toContainText('mention');
  await expect(listeningCard.locator('pre')).toContainText('@growth_signal');
  await expect(listeningCard.locator('pre')).toContainText('positive');

  const listeningAlertsCard = await cardForHeading(page, 'Listening Alerts Sweep');
  await listeningAlertsCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(listeningAlertsCard.locator('pre').first()).toContainText('alerts');

  const reviewsCard = await cardForHeading(page, 'Reviews Engine');
  await reviewsCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(reviewsCard.locator('pre')).toContainText('reputation_score');
  await expect(reviewsCard.locator('pre')).toContainText('response');

  const resendCard = await cardForHeading(page, 'Resend — Send Transactional Email');
  await resendCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(resendCard.locator('pre')).toContainText('re_mock_1234567890');
  await expect(resendCard.locator('pre')).toContainText('queued');

  const totpSetupCard = await cardForHeading(page, 'Auth — TOTP Setup');
  await totpSetupCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(totpSetupCard.locator('pre')).toContainText('JBSWY3DPEHPK3PXP');
  await expect(totpSetupCard.locator('pre')).toContainText('otpauth://totp/');

  const totpVerifyCard = await cardForHeading(page, 'Auth — TOTP Verify');
  await totpVerifyCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(totpVerifyCard.locator('pre')).toContainText('"valid": true');

  const jwtIssueCard = await cardForHeading(page, 'Auth — JWT Issue');
  await jwtIssueCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(jwtIssueCard.locator('pre')).toContainText('mock.header.signature');
  await expect(jwtIssueCard.locator('pre')).toContainText('mock-jti-1234567890');

  const jwtVerifyCard = await cardForHeading(page, 'Auth — JWT Verify');
  await jwtVerifyCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(jwtVerifyCard.locator('pre')).toContainText('"valid": true');
  await expect(jwtVerifyCard.locator('pre')).toContainText('tenant-demo-studio-user');

  const tenantCreateCard = await cardForHeading(page, 'Tenant — Create Profile');
  await tenantCreateCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(tenantCreateCard.locator('pre')).toContainText('tenant-demo Workspace');
  await expect(tenantCreateCard.locator('pre')).toContainText('application-level');

  const tenantListCard = await cardForHeading(page, 'Tenant — List Profiles');
  await tenantListCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(tenantListCard.locator('pre')).toContainText('"count": 1');
  await expect(tenantListCard.locator('pre')).toContainText('tenant-demo Workspace');

  const tenantUpdateCard = await cardForHeading(page, 'Tenant — Update Profile');
  await tenantUpdateCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(tenantUpdateCard.locator('pre')).toContainText('tenant-demo Workspace Updated');
  await expect(tenantUpdateCard.locator('pre')).toContainText('eu-west-1');

  const tenantDeleteCard = await cardForHeading(page, 'Tenant — Delete Profile');
  await tenantDeleteCard.getByRole('button', { name: 'Run Demo' }).click();
  await expect(tenantDeleteCard.locator('pre')).toContainText('"deleted": true');
});

test('studio editor library flow supports insert, layers, and history', async ({ page }) => {
  await page.goto('/studio/editor');
  await page.waitForLoadState('domcontentloaded');

  await expect(page.getByRole('heading', { name: 'Content Library' })).toBeVisible();
  await page.goto('/studio/editor?view=editor&template=blank');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('.editor-workspace-modern')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('button', { name: 'Back to Library' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.canvas-stage').getByRole('heading', { name: 'BLACK FRIDAY' })).toBeVisible();

  await page.getByRole('button', { name: 'Buttons' }).click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toBeVisible();

  await page.getByRole('button', { name: 'Layers' }).click();
  const ctaLayerRow = page.locator('.editor-stack-item', { has: page.getByRole('button', { name: 'CTA button' }) });
  await expect(ctaLayerRow).toBeVisible();
  await ctaLayerRow.getByRole('button', { name: 'Visible' }).click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toHaveCount(0);
  await ctaLayerRow.getByRole('button', { name: 'Hidden' }).click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toBeVisible();

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Added CTA button')).toBeVisible();
  await expect(page.getByText('Hidden CTA button')).toBeVisible();
  await expect(page.getByText('Showed CTA button')).toBeVisible();
});
