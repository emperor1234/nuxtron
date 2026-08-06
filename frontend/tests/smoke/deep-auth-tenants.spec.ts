import { expect, test } from '@playwright/test';

const fastapiBase = 'http://127.0.0.1:4101';

function headers(tenant = 'tenant-deep-auth') {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-this-fastapi-key',
    'X-Tenant-Id': tenant,
  };
}

test.describe('Deep auth coverage', () => {
  test('TOTP setup returns well-formed secret and otpauth URL', async ({ page }) => {
    await page.goto('/');

    const resp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/totp/setup`, { method: 'POST', headers: hdrs, body: JSON.stringify({}) });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(resp.result.secret).toMatch(/^[A-Z2-7]+=*$/);
    expect(resp.result.otpauth_url).toMatch(/^otpauth:\/\/totp\//);
    expect(resp.result.issuer).toBe('Nuxtron');
  });

  test('TOTP verify with correct secret returns valid=true', async ({ page }) => {
    await page.goto('/');

    // Setup first to capture the server-side secret state
    const setup = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/totp/setup`, { method: 'POST', headers: hdrs, body: JSON.stringify({}) });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );
    const secret = setup.result.secret;

    const verifyResp = await page.evaluate(
      async ({ base, hdrs, s }) => {
        const res = await fetch(`${base}/auth/totp/verify`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ secret: s }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(), s: secret }
    );

    expect(verifyResp.valid).toBe(true);
  });

  test('TOTP verify with wrong secret returns valid=false', async ({ page }) => {
    await page.goto('/');

    // Setup to establish correct secret
    await page.evaluate(
      async ({ base, hdrs }) => {
        await fetch(`${base}/auth/totp/setup`, { method: 'POST', headers: hdrs, body: JSON.stringify({}) });
      },
      { base: fastapiBase, hdrs: headers() }
    );

    const verifyResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/totp/verify`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ secret: 'WRONGSECRETVALUE' }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(verifyResp.valid).toBe(false);
  });

  test('JWT issue returns token, expiry, jti and signing_source', async ({ page }) => {
    await page.goto('/');

    const resp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/jwt/issue`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ subject: 'test-user', roles: ['admin'] }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(resp.result.token).toBeTruthy();
    expect(resp.result.jti).toBeTruthy();
    expect(resp.result.expires_at).toBeTruthy();
    expect(resp.result.signing_source).toBeTruthy();
  });

  test('JWT verify with correct token returns valid=true and claims', async ({ page }) => {
    await page.goto('/');

    const issue = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/jwt/issue`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ subject: 'verify-user', roles: ['editor'] }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    const verifyResp = await page.evaluate(
      async ({ base, hdrs, token }) => {
        const res = await fetch(`${base}/auth/jwt/verify`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ token }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers(), token: issue.result.token }
    );

    expect(verifyResp.valid).toBe(true);
    expect(verifyResp.claims).not.toBeNull();
    expect(verifyResp.claims.sub).toBeTruthy();
    expect(verifyResp.error).toBeNull();
  });

  test('JWT verify with wrong token returns valid=false and error message', async ({ page }) => {
    await page.goto('/');

    // Issue a real token first (sets server-side state)
    await page.evaluate(
      async ({ base, hdrs }) => {
        await fetch(`${base}/auth/jwt/issue`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ subject: 'bad-token-test' }),
        });
      },
      { base: fastapiBase, hdrs: headers() }
    );

    const verifyResp = await page.evaluate(
      async ({ base, hdrs }) => {
        const res = await fetch(`${base}/auth/jwt/verify`, {
          method: 'POST',
          headers: hdrs,
          body: JSON.stringify({ token: 'completely.wrong.token' }),
        });
        return res.json();
      },
      { base: fastapiBase, hdrs: headers() }
    );

    expect(verifyResp.valid).toBe(false);
    expect(verifyResp.claims).toBeNull();
    expect(verifyResp.error).toBeTruthy();
  });
});

test.describe('Deep tenant management coverage', () => {
  test('full tenant lifecycle: create → list → update → delete → verify empty', async ({ page }) => {
    const tenant = 'tenant-lifecycle';
    const hdrs = headers(tenant);
    await page.goto('/');

    // Create
    const createResp = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants`, {
          method: 'POST',
          headers: h,
          body: JSON.stringify({ display_name: 'Lifecycle Workspace', plan: 'growth', status: 'active' }),
        });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );
    expect(createResp.tenant.display_name).toBe('Lifecycle Workspace');
    expect(createResp.tenant.plan).toBe('growth');
    expect(createResp.tenant.encryption).toBe('application-level');

    // List — count = 1
    const listResp = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants`, { method: 'GET', headers: h });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );
    expect(listResp.count).toBe(1);
    expect(listResp.items[0].display_name).toBe('Lifecycle Workspace');

    // Update
    const updateResp = await page.evaluate(
      async ({ base, h, tid }) => {
        const res = await fetch(`${base}/tenants/${tid}`, {
          method: 'PATCH',
          headers: h,
          body: JSON.stringify({ display_name: 'Lifecycle Workspace Renamed', settings: { region: 'us-east-1' } }),
        });
        return res.json();
      },
      { base: fastapiBase, h: hdrs, tid: tenant }
    );
    expect(updateResp.tenant.display_name).toContain('Renamed');
    expect(updateResp.tenant.settings.region).toBe('us-east-1');

    // Delete
    const deleteResp = await page.evaluate(
      async ({ base, h, tid }) => {
        const res = await fetch(`${base}/tenants/${tid}`, { method: 'DELETE', headers: h });
        return res.json();
      },
      { base: fastapiBase, h: hdrs, tid: tenant }
    );
    expect(deleteResp.deleted).toBe(true);

    // List after delete — count = 0
    const listAfterResp = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants`, { method: 'GET', headers: h });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );
    expect(listAfterResp.count).toBe(0);
    expect(listAfterResp.items).toHaveLength(0);
  });

  test('tenant profile includes persistence and encryption metadata', async ({ page }) => {
    const hdrs = headers('tenant-meta-check');
    await page.goto('/');

    const resp = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants`, {
          method: 'POST',
          headers: h,
          body: JSON.stringify({ display_name: 'Meta Check Workspace' }),
        });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );

    expect(resp.tenant.persistence).toBe('memory-fallback');
    expect(resp.tenant.encryption).toBe('application-level');
    expect(resp.tenant.created_at).toBeTruthy();
  });

  test('tenant update preserves original created_at timestamp', async ({ page }) => {
    const hdrs = headers('tenant-timestamp');
    await page.goto('/');

    const created = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants`, {
          method: 'POST',
          headers: h,
          body: JSON.stringify({ display_name: 'Timestamp Test' }),
        });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );
    const originalCreatedAt = created.tenant.created_at;

    const updated = await page.evaluate(
      async ({ base, h }) => {
        const res = await fetch(`${base}/tenants/tenant-timestamp`, {
          method: 'PATCH',
          headers: h,
          body: JSON.stringify({ display_name: 'Timestamp Test Updated' }),
        });
        return res.json();
      },
      { base: fastapiBase, h: hdrs }
    );

    expect(updated.tenant.created_at).toBe(originalCreatedAt);
    expect(updated.tenant.updated_at).toBeTruthy();
  });
});
