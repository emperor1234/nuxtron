import { describe, expect, it } from 'vitest';
import {
  buildCalculatorPayload,
  buildSpendPayload,
  buildTrackedLinkPayload,
  formatCurrencyAmount,
  parseCalculatorResult,
  parseRoiSummary,
  parseSpendList,
  parseSpendWriteResult,
  parseTrackedLinkResult,
} from './social-roi-model';

const metrics = (revenue: number | null, spend: number | null, net: number | null, roas: number | null, roi: number | null) => ({
  revenue,
  spend,
  net_profit: net,
  roas,
  roi_pct: roi,
});

function summary(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ok',
    tenant_id: 'private-workspace',
    window_days: 90,
    persistence_mode: 'postgres',
    currency_status: 'single',
    currency_codes: ['USD'],
    invalid_currency_records: 0,
    totals: {
      ...metrics(0, 0, 0, null, null),
      conversions: 0,
      tracked_conversions: 0,
      touchpoints: 0,
      spend_entries: 0,
      tracking_coverage_pct: 0,
    },
    channels: [],
    campaigns: [],
    ...overrides,
  };
}

describe('Social Media ROI model', () => {
  it('preserves a real zero and unavailable zero-spend ratios for one reported currency', () => {
    const parsed = parseRoiSummary(summary());
    expect(parsed?.currencyStatus).toBe('single');
    expect(parsed?.currencyCodes).toEqual(['USD']);
    expect(parsed?.totals.revenue).toBe(0);
    expect(parsed?.totals.spend).toBe(0);
    expect(parsed?.totals.roas).toBeNull();
    expect(parsed?.totals.roiPct).toBeNull();
  });

  it('rejects missing fields and incomplete monetary metrics instead of substituting zero', () => {
    const missingSpend = summary({ totals: { ...metrics(0, null, 0, null, null), conversions: 0, tracked_conversions: 0, touchpoints: 0, spend_entries: 0, tracking_coverage_pct: 0 } });
    expect(parseRoiSummary(missingSpend)).toBeNull();
    expect(parseRoiSummary(summary({ channels: [{ channel: 'linkedin', ...metrics(null, null, null, null, null) }] }))).toBeNull();
    expect(parseRoiSummary({ status: 'ok', window_days: 90 })).toBeNull();
  });

  it('accepts explicit mixed-currency metadata only when combined financial totals are withheld', () => {
    const parsed = parseRoiSummary(summary({
      currency_status: 'mixed',
      currency_codes: ['EUR', 'USD'],
      totals: {
        ...metrics(null, null, null, null, null),
        conversions: 2,
        tracked_conversions: 2,
        touchpoints: 2,
        spend_entries: 1,
        tracking_coverage_pct: 100,
      },
      channels: [{ channel: 'linkedin', ...metrics(null, null, null, null, null) }],
      campaigns: [{ campaign: 'spring launch', ...metrics(null, null, null, null, null) }],
    }));
    expect(parsed?.currencyStatus).toBe('mixed');
    expect(parsed?.totals.revenue).toBeNull();
    expect(parsed?.channels[0]?.revenue).toBeNull();
    expect(parseRoiSummary(summary({ currency_status: 'mixed', currency_codes: ['EUR', 'USD'] }))).toBeNull();
  });

  it('requires a storage mode and retains process-memory fallback as explicit state', () => {
    expect(parseRoiSummary(summary({ persistence_mode: 'process-memory' }))?.persistenceMode).toBe('process-memory');
    expect(parseRoiSummary(summary({ persistence_mode: 'unknown' }))).toBeNull();
  });

  it('parses valid empty spend history separately from malformed and unavailable history', () => {
    expect(parseSpendList({ status: 'ok', persistence_mode: 'postgres', count: 0, items: [] })?.items).toEqual([]);
    expect(parseSpendList({ status: 'ok', persistence_mode: 'postgres', count: 0, items: [{}] })).toBeNull();
    expect(parseSpendList({ status: 'error', persistence_mode: 'postgres', count: 0, items: [] })).toBeNull();
    expect(parseSpendWriteResult({
      status: 'ok', persistence_mode: 'postgres', spend: { id: 2, amount: 10, channel: 'linkedin', campaign: 'Launch', currency: 'USD', spent_at: '2026-10-12T12:00:00Z' },
    })).toEqual({ persistenceMode: 'postgres' });
    expect(parseSpendWriteResult({ status: 'ok', persistence_mode: 'postgres', spend: { amount: 10 } })).toBeNull();
  });

  it('validates tracking input and rejects unsafe destination protocols', () => {
    const input = { postId: 'post-1', platform: 'LinkedIn', campaign: 'Launch', destinationUrl: 'https://example.com/pricing?plan=team' };
    expect(buildTrackedLinkPayload(input)).toEqual({
      post_id: 'post-1', platform: 'linkedin', campaign: 'Launch', destination_url: 'https://example.com/pricing?plan=team',
    });
    expect(buildTrackedLinkPayload({ ...input, destinationUrl: 'javascript:alert(1)' })).toBeNull();
    expect(buildTrackedLinkPayload({ ...input, destinationUrl: 'https://user:secret@example.com/path' })).toBeNull();
    expect(buildTrackedLinkPayload({ ...input, campaign: '' })).toBeNull();
  });

  it('parses only valid HTTP tracked links and records persistence provenance', () => {
    expect(parseTrackedLinkResult({
      status: 'ok', persistence_mode: 'process-memory', touchpoint: { tracked_url: 'https://example.com/?nux_touchpoint=tp_abcdefgh' },
    })).toEqual({ trackedUrl: 'https://example.com/?nux_touchpoint=tp_abcdefgh', persistenceMode: 'process-memory' });
    expect(parseTrackedLinkResult({ status: 'ok', persistence_mode: 'postgres', touchpoint: { tracked_url: 'javascript:alert(1)' } })).toBeNull();
  });

  it('builds a spend payload only from deliberate positive amount and explicit currency inputs', () => {
    expect(buildSpendPayload({ channel: 'LinkedIn', campaign: 'Launch', amount: '0', currency: 'USD' })).toBeNull();
    expect(buildSpendPayload({ channel: 'LinkedIn', campaign: 'Launch', amount: '12.50', currency: 'eur' })).toEqual({
      channel: 'linkedin', campaign: 'Launch', amount: 12.5, currency: 'EUR',
    });
  });

  it('requires every calculator assumption, while allowing true zero values', () => {
    expect(buildCalculatorPayload({ revenue: '100', paidSpend: '0', teamCost: '0', toolsCost: '0', agencyCost: '0' })).toEqual({
      attributed_revenue: 100, paid_social_spend: 0, team_cost: 0, tools_cost: 0, agency_cost: 0,
    });
    expect(buildCalculatorPayload({ revenue: '', paidSpend: '0', teamCost: '0', toolsCost: '0', agencyCost: '0' })).toBeNull();
    expect(parseCalculatorResult({ status: 'ok', totals: metrics(100, 0, 100, null, null) })?.roas).toBeNull();
    expect(parseCalculatorResult({ status: 'ok', totals: metrics(100, null, 100, null, null) })).toBeNull();
  });

  it('formats available ISO currency codes with a stable fallback for formatter gaps', () => {
    expect(formatCurrencyAmount(10, 'USD')).toContain('$10');
    expect(formatCurrencyAmount(10, 'XYZ')).toContain('XYZ');
  });
});
