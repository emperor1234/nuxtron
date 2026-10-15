import { describe, expect, it } from 'vitest';
import { parseRevenueAttributionReport } from './report-model';

function baseReport(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ok',
    tenant_id: 'private-workspace-id',
    window_days: 30,
    persistence_mode: 'postgres',
    currency_status: 'none',
    currency_codes: [],
    currency_totals: [],
    totals: {
      conversions: 0,
      tracked_conversions: 0,
      currency: null,
      revenue: 0,
      attributed_revenue: 0,
      unattributed_revenue: 0,
    },
    channels: [],
    ...overrides,
  };
}

describe('Revenue Attribution report parser', () => {
  it('accepts a true empty result, persistence mode, and omits the backend tenant identifier', () => {
    const parsed = parseRevenueAttributionReport(baseReport());
    expect(parsed).toMatchObject({
      persistence_mode: 'postgres',
      currency_status: 'none',
      currency_totals: [],
      totals: { conversions: 0, revenue: 0 },
    });
    expect(parsed).not.toHaveProperty('tenant_id');
  });

  it('keeps mixed-currency values in separate buckets and withholds combined totals', () => {
    const parsed = parseRevenueAttributionReport(baseReport({
      currency_status: 'mixed',
      currency_codes: ['EUR', 'USD'],
      currency_totals: [
        { currency: 'EUR', currency_supported: true, conversions: 1, tracked_conversions: 1, revenue: 200, attributed_revenue: 200, unattributed_revenue: 0 },
        { currency: 'USD', currency_supported: true, conversions: 1, tracked_conversions: 0, revenue: 100, attributed_revenue: 0, unattributed_revenue: 100 },
      ],
      totals: { conversions: 2, tracked_conversions: 1, currency: null, revenue: null, attributed_revenue: null, unattributed_revenue: null },
      channels: [{ channel: 'search', currency: 'EUR', currency_supported: true, attributed_revenue: 200 }],
    }));
    expect(parsed.currency_totals.map((row) => [row.currency, row.revenue])).toEqual([['EUR', 200], ['USD', 100]]);
    expect(parsed.totals.revenue).toBeNull();
  });

  it('accepts unsupported currency buckets only when amounts are withheld', () => {
    const parsed = parseRevenueAttributionReport(baseReport({
      currency_status: 'unsupported',
      currency_totals: [
        { currency: 'US$', currency_supported: false, conversions: 1, tracked_conversions: 0, revenue: null, attributed_revenue: null, unattributed_revenue: null },
      ],
      totals: { conversions: 1, tracked_conversions: 0, currency: null, revenue: null, attributed_revenue: null, unattributed_revenue: null },
    }));
    expect(parsed.currency_totals[0].currency_supported).toBe(false);
    expect(parsed.currency_totals[0].revenue).toBeNull();
  });

  it('rejects mismatched counts, malformed amounts, and unknown persistence modes', () => {
    expect(() => parseRevenueAttributionReport(baseReport({
      totals: { conversions: -1, tracked_conversions: 0, currency: null, revenue: 0, attributed_revenue: 0, unattributed_revenue: 0 },
    }))).toThrow(/conversions/i);
    expect(() => parseRevenueAttributionReport(baseReport({
      persistence_mode: 'cache',
    }))).toThrow(/persistence/i);
    expect(() => parseRevenueAttributionReport(baseReport({
      currency_totals: [
        { currency: 'USD', currency_supported: true, conversions: 1, tracked_conversions: 0, revenue: Number.NaN, attributed_revenue: 0, unattributed_revenue: 0 },
      ],
      totals: { conversions: 1, tracked_conversions: 0, currency: 'USD', revenue: 10, attributed_revenue: 0, unattributed_revenue: 10 },
      currency_status: 'single',
      currency_codes: ['USD'],
    }))).toThrow(/revenue/i);
  });
});
