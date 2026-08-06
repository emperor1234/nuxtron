import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

// Use a unique tenant per describe block to keep state isolated
function headers(tenant = 'tenant-deep-notify') {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-this-fastapi-key',
    'X-Tenant-Id': tenant,
  };
}

async function createNotification(
  page: import('@playwright/test').Page,
  overrides: Record<string, unknown> = {},
  tenant = 'tenant-deep-notify'
) {
  return page.evaluate(
    async ({ base, hdrs, data }) => {
      const res = await fetch(`${base}/notifications`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify(data),
      });
      return res.json();
    },
    {
      base: fastapiBase,
      hdrs: headers(tenant),
      data: { title: 'Default Title', message: 'Default message.', category: 'deep', ...overrides },
    }
  );
}

test.describe('Deep notification system coverage', () => {
  test('individual mark-read decrements unread count by exactly one', async ({ page }) => {
    const tenant = 'tenant-notify-read';
    await page.goto('/');

    // Create two unread notifications
    const n1 = await createNotification(page, { title: 'Read Me', message: 'Message A.' }, tenant);
    await createNotification(page, { title: 'Keep Unread', message: 'Message B.' }, tenant);

    const countBefore = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/notifications/unread-count`, { method: 'GET', headers: hdrs });
        const data = await res.json();
        return data.unreadCount;
      },
      { base: fastapiBase, hdrs: headers(tenant) }
    );
    expect(countBefore).toBeGreaterThanOrEqual(2);

    // Mark just n1 as read
    await page.evaluate(
      async ({ base, hdrs, id }) => {
        await fetch(`${base}/notifications/${id}/read`, { method: 'POST', headers: hdrs });
      },
      { base: fastapiBase, hdrs: headers(tenant), id: n1.notification.id }
    );

    const countAfter = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/notifications/unread-count`, { method: 'GET', headers: hdrs });
        const data = await res.json();
        return data.unreadCount;
      },
      { base: fastapiBase, hdrs: headers(tenant) }
    );
    expect(countAfter).toBe(countBefore - 1);
  });

  test('individual dismiss (DELETE) removes notification from list', async ({ page }) => {
    const tenant = 'tenant-notify-delete';
    await page.goto('/');

    const n1 = await createNotification(page, { title: 'Delete Me', message: 'Will be deleted.' }, tenant);
    await createNotification(page, { title: 'Keep Me', message: 'Will remain.' }, tenant);

    // Delete n1
    const deleteResp = await page.evaluate(
      async ({ base, hdrs, id }) => {
        const res = await fetch(`${base}/notifications/${id}`, { method: 'DELETE', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(tenant), id: n1.notification.id }
    );
    expect(deleteResp.deleted).toBe(true);

    // Confirm it's gone from the list
    const listResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/notifications`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(tenant) }
    );

    const ids = listResp.notifications.map((n: { id: number }) => n.id);
    expect(ids).not.toContain(n1.notification.id);
    expect(ids).toContain(n1.notification.id + 1); // the second one remains
  });

  test('mark-all-read sets every notification to read=true', async ({ page }) => {
    const tenant = 'tenant-notify-mark-all';
    await page.goto('/');

    await createNotification(page, { title: 'A' }, tenant);
    await createNotification(page, { title: 'B' }, tenant);
    await createNotification(page, { title: 'C' }, tenant);

    const readAllResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/notifications/read-all`, { method: 'POST', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(tenant) }
    );
    expect(readAllResp.updated).toBeGreaterThanOrEqual(3);

    const countResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/notifications/unread-count`, { method: 'GET', headers: hdrs });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(tenant) }
    );
    expect(countResp.unreadCount).toBe(0);
  });

  test('notifications are tenant-isolated — tenant B cannot see tenant A items', async ({ page }) => {
    const tenantA = 'tenant-iso-a';
    const tenantB = 'tenant-iso-b';
    await page.goto('/');

    await createNotification(page, { title: 'Tenant A Private', message: 'Secret A.' }, tenantA);

    const listB = await page.evaluate(
      async ({ base, hdrsB }) => {
        const res = await fetch(`${base}/notifications`, { method: 'GET', headers: hdrsB });
        return res.json();
      },
      { base: fastapiBase, hdrsB: headers(tenantB) }
    );

    const titlesB = listB.notifications.map((n: { title: string }) => n.title);
    expect(titlesB).not.toContain('Tenant A Private');
  });

  test('notification snapshot delivered via SSE stream on connect', async ({ page }) => {
    const tenant = 'tenant-notify-sse';
    await page.goto('/');

    // Pre-seed notification so snapshot is non-empty
    await createNotification(page, { title: 'SSE Probe', message: 'Should appear in snapshot.' }, tenant);

    // Open an EventSource connection and collect the first snapshot event
    const snapshot = await page.evaluate(
      async ({ base, tenant: t }) => {
        return new Promise<{ event: string; data: unknown }>((resolve, reject) => {
          const url = `${base}/notifications/stream?tenant_id=${t}`;
          const es = new EventSource(url);
          const timer = setTimeout(() => {
            es.close();
            reject(new Error('SSE snapshot timeout'));
          }, 5000);

          es.addEventListener('notifications.snapshot', (e) => {
            clearTimeout(timer);
            es.close();
            resolve({ event: 'notifications.snapshot', data: JSON.parse(e.data) });
          });

          es.onerror = () => {
            clearTimeout(timer);
            es.close();
            reject(new Error('SSE connection error'));
          };
        });
      },
      { base: fastapiBase, tenant }
    );

    expect(snapshot.event).toBe('notifications.snapshot');
    const payload = snapshot.data as { notifications: { title: string }[]; unreadCount: number };
    const titles = payload.notifications.map((n) => n.title);
    expect(titles).toContain('SSE Probe');
    expect(payload.unreadCount).toBeGreaterThanOrEqual(1);
  });

  test('notifications.updated SSE event fires when a new notification is created', async ({ page }) => {
    const tenant = 'tenant-notify-update-sse';
    await page.goto('/');

    // Subscribe to SSE stream, then create a notification and verify the update fires
    const updated = await page.evaluate(
      async ({ base, tenant: t }) => {
        return new Promise<{ event: string; unreadCount: number }>((resolve, reject) => {
          const url = `${base}/notifications/stream?tenant_id=${t}`;
          const es = new EventSource(url);
          const timer = setTimeout(() => {
            es.close();
            reject(new Error('SSE updated timeout'));
          }, 6000);

          // Wait for snapshot first, then trigger a create
          es.addEventListener('notifications.snapshot', () => {
            fetch(`${base}/notifications`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'change-this-fastapi-key',
                'X-Tenant-Id': t,
              },
              body: JSON.stringify({ title: 'Live Update', message: 'Via SSE.', category: 'deep' }),
            });
          });

          es.addEventListener('notifications.updated', (e) => {
            clearTimeout(timer);
            es.close();
            const data = JSON.parse(e.data);
            resolve({ event: 'notifications.updated', unreadCount: data.unreadCount });
          });

          es.onerror = () => {
            clearTimeout(timer);
            es.close();
            reject(new Error('SSE error'));
          };
        });
      },
      { base: fastapiBase, tenant }
    );

    expect(updated.event).toBe('notifications.updated');
    expect(updated.unreadCount).toBeGreaterThanOrEqual(1);
  });
});
