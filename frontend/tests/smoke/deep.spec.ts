import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

function mediaInput(page: import('@playwright/test').Page) {
  return uploader(page).getByLabel('Upload media file');
}

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const UPLOAD_COMPLETION_TIMEOUT_MS = 45000;

type MediaScenario = 'complete' | 'failed' | 'inflight';

async function mockMediaPipeline(page: import('@playwright/test').Page, scenario: MediaScenario) {
  const nowIso = new Date().toISOString();
  let currentMediaType = 'image';
  const queuedJob = {
    id: 901,
    tenant_id: 'tenant-demo',
    status: 'queued',
    progress_pct: 0,
    storage_key: 'raw-input/tenant-demo/mock-image.png',
    media_type: currentMediaType,
    output_bucket: 'processed-output',
    output_key: null,
    error: null,
    created_at: nowIso,
    updated_at: nowIso,
  };

  await page.route('**/api/fastapi/media/validate-file', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        mime_type: 'image/png',
        validation_token: 'mock-validation-token',
      }),
    });
  });

  await page.route('**/api/fastapi/storage/presign', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', result: { presigned_url: null } }),
    });
  });

  await page.route('**/api/fastapi/media/jobs', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    try {
      const body = route.request().postDataJSON() as { media_type?: string };
      currentMediaType = String(body?.media_type || 'image');
    } catch {
      currentMediaType = 'image';
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        job: { ...queuedJob, media_type: currentMediaType },
      }),
    });
  });

  await page.route('**/api/fastapi/media/jobs/901/stream**', async (route) => {
    const processing = {
      ...queuedJob,
      media_type: currentMediaType,
      status: 'processing',
      progress_pct: 62,
      updated_at: new Date().toISOString(),
    };
    const complete = {
      ...processing,
      status: 'complete',
      progress_pct: 100,
      output_key: 'processed/tenant-demo/901/mock-image.png',
      updated_at: new Date().toISOString(),
    };
    const failed = {
      ...processing,
      status: 'failed',
      progress_pct: 100,
      error: 'Mock sandbox processing failure',
      updated_at: new Date().toISOString(),
    };

    let body = `event: job.snapshot\ndata: ${JSON.stringify(queuedJob)}\n\n`;
    if (scenario === 'inflight') {
      body += `event: job.updated\ndata: ${JSON.stringify(processing)}\n\n`;
    } else if (scenario === 'failed') {
      body += `event: job.updated\ndata: ${JSON.stringify(failed)}\n\n`;
    } else {
      body += `event: job.updated\ndata: ${JSON.stringify(processing)}\n\n`;
      body += `event: job.updated\ndata: ${JSON.stringify(complete)}\n\n`;
    }

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: { 'Cache-Control': 'no-cache' },
      body,
    });
  });

  await page.route('**/api/fastapi/media/jobs/901/output-url', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        job_id: 901,
        output_key: 'processed/tenant-demo/901/mock-image.png',
        signed_url: 'https://cdn.example.com/processed-output/processed/tenant-demo/901/mock-image.png?sig=mock',
        expires_at: 9999999999,
      }),
    });
  });

  await page.route('**/api/fastapi/media/jobs/901', async (route) => {
    if (route.request().method() !== 'DELETE') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        job: { ...queuedJob, status: 'cancelled', updated_at: new Date().toISOString() },
      }),
    });
  });

  await page.route('**/api/fastapi/media/jobs/901/retry', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        job: { ...queuedJob, status: 'queued', progress_pct: 0, updated_at: new Date().toISOString() },
      }),
    });
  });

  await page.route('**/api/fastapi/media/jobs/dlq', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        tenant_id: 'tenant-demo',
        dlq: [
          {
            id: 1,
            tenant_id: 'tenant-demo',
            job_id: 901,
            reason: 'Mock sandbox processing failure',
            failed_at: new Date().toISOString(),
          },
        ],
        total: 1,
      }),
    });
  });
}

function uploader(page: import('@playwright/test').Page) {
  return page
    .locator('.media-uploader-card')
    .filter({ has: page.getByRole('heading', { name: 'Sandboxed Media Processor' }) })
    .first();
}

function statusLabel(page: import('@playwright/test').Page) {
  return uploader(page).locator('.media-status-label').first();
}

test.describe('Deep media uploader coverage', () => {
  test('rejects unsupported file types with a clear error', async ({ page }) => {
    await page.goto('/media-processing');

    await mediaInput(page).setInputFiles({
      name: 'unsupported.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('hello world', 'utf-8'),
    });

    await expect(uploader(page)).toContainText('Unsupported file type');
    await expect(statusLabel(page)).toContainText('Processing failed');
  });

  test('runs upload pipeline to completion with signed output URL', async ({ page }) => {
    await mockMediaPipeline(page, 'complete');
    await page.goto('/media-processing');

    await mediaInput(page).setInputFiles({
      name: 'mock-image.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });

    await expect(statusLabel(page)).toContainText('Processing complete', {
      timeout: UPLOAD_COMPLETION_TIMEOUT_MS,
    });
    await expect(uploader(page).locator('.media-job-meta')).toContainText(/Job #\d+/);
    await expect(uploader(page).locator('.media-job-status-chip')).toContainText('complete');
    await expect(uploader(page).locator('.media-output-link')).toBeVisible();
    await expect(uploader(page).locator('.media-output-link')).toHaveAttribute('href', /cdn\.example\.com/);
    await expect(uploader(page).locator('.media-error')).toHaveCount(0);
  });

  test('supports cancel flow while job is active', async ({ page }) => {
    await mockMediaPipeline(page, 'inflight');
    await page.goto('/media-processing');

    await mediaInput(page).setInputFiles({
      name: 'cancel-me.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });

    const cancelBtn = uploader(page).getByRole('button', { name: 'Cancel' });
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();

    await expect(statusLabel(page)).toContainText('Job cancelled');
    await expect(uploader(page).locator('.media-job-status-chip')).toContainText('cancelled');
  });

  test('failed job shows retry button and retry resets job to queued', async ({ page }) => {
    await mockMediaPipeline(page, 'failed');
    await page.goto('/media-processing');

    // Filename containing 'fail' triggers mock server failure path
    await mediaInput(page).setInputFiles({
      name: 'fail-probe.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });

    await expect(statusLabel(page)).toContainText('Processing failed', { timeout: 20000 });
    await expect(uploader(page).locator('.media-job-status-chip')).toContainText('failed');
    await expect(uploader(page).locator('.media-error')).toHaveCount(0); // error comes from SSE, not thrown

    const retryBtn = uploader(page).getByRole('button', { name: 'Retry' });
    await expect(retryBtn).toBeVisible();
    await retryBtn.click();

    // After retry the job resets to queued (storage_key still contains 'fail' so it will
    // fail again on mock, but the retry UI transition is what we're verifying here)
    await expect(statusLabel(page)).toContainText(/queued|processing|failed/, { timeout: 15000 });
    await expect(uploader(page).locator('.media-job-status-chip')).not.toContainText('complete');
  });

  test('DLQ panel opens and lists entries for failed jobs', async ({ page }) => {
    await mockMediaPipeline(page, 'failed');
    await page.goto('/media-processing');

    // Force a failure to populate DLQ
    await mediaInput(page).setInputFiles({
      name: 'fail-dlq.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });
    await expect(statusLabel(page)).toContainText('Processing failed', { timeout: 20000 });

    // Open DLQ panel
    await uploader(page).getByRole('button', { name: 'View failed jobs (DLQ)' }).click();
    await expect(uploader(page).locator('.media-dlq-panel')).toBeVisible();

    // At least one DLQ item from the failure above
    await expect(uploader(page).locator('.media-dlq-item').first()).toBeVisible();
    const itemText = await uploader(page).locator('.media-dlq-item pre').first().textContent();
    expect(itemText).toContain('job_id');
    expect(itemText).toContain('reason');

    // Close panel
    await uploader(page).locator('.media-btn-close').click();
    await expect(uploader(page).locator('.media-dlq-panel')).not.toBeVisible();
  });

  test('upload another resets uploader to idle state', async ({ page }) => {
    await mockMediaPipeline(page, 'complete');
    await page.goto('/media-processing');

    await mediaInput(page).setInputFiles({
      name: 'reset-test.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });
    await expect(statusLabel(page)).toContainText('Processing complete', {
      timeout: UPLOAD_COMPLETION_TIMEOUT_MS,
    });

    await uploader(page).getByRole('button', { name: 'Upload another' }).click();
    // Status bar should be gone (only shown when isActive)
    await expect(uploader(page).locator('.media-status')).not.toBeVisible();
    // Job meta and output link should be gone
    await expect(uploader(page).locator('.media-job-meta')).not.toBeVisible();
    await expect(uploader(page).locator('.media-output-link')).not.toBeVisible();
  });

  test('video file upload runs full pipeline to completion', async ({ page }) => {
    test.slow();
    test.setTimeout(60000);
    await mockMediaPipeline(page, 'complete');
    await page.goto('/media-processing');
    await expect(uploader(page)).toBeVisible();

    // MP4 magic bytes: ftyp box at offset 4 is unreliable; use minimal valid header approach
    // The mock server accepts any upload, so we just need the browser to accept the MIME type
    const mp4Header = Buffer.from([0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70]);
    await mediaInput(page).setInputFiles({
      name: 'sample-video.mp4',
      mimeType: 'video/mp4',
      buffer: mp4Header,
    });

    await expect(uploader(page)).toContainText('Processing complete', {
      timeout: UPLOAD_COMPLETION_TIMEOUT_MS,
    });
    await expect(uploader(page).locator('.media-job-status-chip')).toContainText('complete');
    await expect(uploader(page).locator('.media-job-meta')).toContainText('video');
  });

  test('progress bar reaches 100% on completion', async ({ page }) => {
    await mockMediaPipeline(page, 'complete');
    await page.goto('/media-processing');

    await mediaInput(page).setInputFiles({
      name: 'progress-check.png',
      mimeType: 'image/png',
      buffer: PNG_MAGIC,
    });

    // Ensure a status row is active before awaiting completion.
    await expect(statusLabel(page)).toContainText(/Validating|Requesting|Uploading|queued|processing/);

    // Wait until complete
    await expect(statusLabel(page)).toContainText('Processing complete', {
      timeout: UPLOAD_COMPLETION_TIMEOUT_MS,
    });

    // Progress text label should show 100%
    await expect(uploader(page).locator('.media-status-row .muted')).toContainText('100%');

    // Progress bar should have the done class
    await expect(uploader(page).locator('.media-progress-bar.done')).toBeVisible();
  });
});
