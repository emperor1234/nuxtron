import { expect, test } from '@playwright/test';

test.describe('Studio editor parity calendar wiring', () => {
  test('drag scheduling and move call parity endpoints', async ({ page }) => {
    test.slow();
    test.setTimeout(90000);

    async function dispatchDragDropByIndex(sourceSelector: string, targetSelector: string, targetIndex: number) {
      const dragged = await page.evaluate(
        ({ source, target, index }) => {
          const src = document.querySelector(source);
          const destinations = document.querySelectorAll(target);
          const dst = destinations.item(index);
          if (!src || !dst) return false;

          const dataTransfer = new DataTransfer();
          src.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer }));
          dst.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer }));
          dst.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer }));
          src.dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer }));
          return true;
        },
        { source: sourceSelector, target: targetSelector, index: targetIndex }
      );

      expect(dragged).toBe(true);
    }

    const now = new Date();
    const dayIndex = now.getDay();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - dayIndex);
    weekStart.setHours(9, 0, 0, 0);
    const scheduledIso = weekStart.toISOString();

    let createPayload: Record<string, unknown> | null = null;
    let reschedulePayload: Record<string, unknown> | null = null;

    await page.route('**/api/fastapi/api/v1/social/content/list?status=scheduled*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'post-1',
              title: 'Calendar Test Post',
              caption: 'Calendar Test Post caption',
              platforms: ['instagram'],
              status: 'scheduled',
              scheduled_for: scheduledIso,
            },
          ],
          total: 1,
          skip: 0,
          limit: 50,
        }),
      });
    });

    await page.route('**/api/fastapi/api/v1/social/content/create', async (route) => {
      createPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'post-new',
          status: 'scheduled',
          scheduled_for:
            typeof createPayload?.['scheduled_for'] === 'string'
              ? createPayload['scheduled_for']
              : '2026-01-10T10:00:00Z',
        }),
      });
    });

    await page.route('**/api/fastapi/api/v1/social/content/post-1/reschedule', async (route) => {
      reschedulePayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          content_id: 'post-1',
          scheduled_for:
            typeof reschedulePayload?.['new_scheduled_time'] === 'string'
              ? reschedulePayload['new_scheduled_time']
              : '2026-01-10T12:00:00Z',
          status: 'scheduled',
        }),
      });
    });

    await page.goto('/studio/editor');
    const draftCard = page.locator('.draft-card[data-slide-index="0"]').first();
    const dropCells = page.locator('.calendar-drop-cell');

    await expect(draftCard).toBeVisible();
    await expect.poll(async () => await dropCells.count()).toBeGreaterThan(1);

    await dispatchDragDropByIndex('.draft-card[data-slide-index="0"]', '.calendar-drop-cell', 0);

    await expect.poll(() => createPayload !== null).toBe(true);
    expect(Array.isArray(createPayload?.['platforms'])).toBe(true);
    expect(typeof createPayload?.['scheduled_for']).toBe('string');

    const scheduledPost = page.locator('.scheduled-post[data-post-id="post-1"]').first();
    await expect(scheduledPost).toBeVisible();
    await dispatchDragDropByIndex('.scheduled-post[data-post-id="post-1"]', '.calendar-drop-cell', 1);

    await expect.poll(() => reschedulePayload !== null).toBe(true);
    expect(typeof reschedulePayload?.['new_scheduled_time']).toBe('string');
  });
});
