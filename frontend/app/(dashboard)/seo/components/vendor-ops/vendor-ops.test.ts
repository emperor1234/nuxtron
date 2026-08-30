import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { VENDOR_REGISTRY } from './vendor-registry';

const SEO_ROOT = join(__dirname, '..', '..');

describe('vendor operations routes', () => {
  it('keeps every declared view on its stable URL', () => {
    const missing: string[] = [];
    let bindings = 0;
    for (const vendor of Object.values(VENDOR_REGISTRY)) {
      for (const view of vendor.sharedViews) {
        const routeName = `${vendor.slug}-${view}`;
        const file = join(SEO_ROOT, routeName, 'page.tsx');
        try {
          const source = readFileSync(file, 'utf8');
          expect(source).toContain('VendorOpsPage');
          expect(source).toContain(`vendorSpec('${vendor.slug}')`);
          expect(source).toContain(`view="${view}"`);
          bindings += 1;
        } catch {
          missing.push(routeName);
        }
      }
    }
    expect(missing).toEqual([]);
    expect(bindings).toBe(29);
  });

  it('does not expose internal production-gate or parity metrics', () => {
    const source = readFileSync(join(__dirname, 'vendor-ops-page.tsx'), 'utf8');
    expect(source).not.toContain('production-gate');
    expect(source).not.toContain('parity-audit');
    expect(source).not.toContain('implementation_pct');
    expect(source).not.toContain('DEFAULT_TENANT_ID');
  });

  it('never creates demo projects against Nuxtron domains', () => {
    const source = readFileSync(join(__dirname, 'vendor-ops-page.tsx'), 'utf8');
    expect(source).not.toContain('nuxtron.ai');
    expect(source).not.toContain('Create Demo Project');
    expect(source).not.toContain('require_live_providers: false');
  });
});
