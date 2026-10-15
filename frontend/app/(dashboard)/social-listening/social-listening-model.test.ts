import { describe, expect, it } from 'vitest';
import {
  parseListeningAlerts,
  parseListeningMentions,
  parseListeningRules,
  parseListeningSummary,
} from './social-listening-model';

const emptySummary = {
  status: 'ok',
  totals: { mentions: 0, alerts: 0, open_alerts: 0, rules: 0 },
  sentiment_breakdown: {},
  platform_distribution: {},
  top_queries: [],
  clusters: [],
  crisis_level: 'normal',
};

const mention = {
  id: 4,
  platform: 'linkedin',
  query: 'brand mention',
  author_handle: '@customer',
  text: 'A manually captured mention.',
  sentiment: 'neutral',
  engagement_count: 0,
  created_at: '2026-10-12T12:00:00Z',
  persistence: 'memory-fallback',
};

describe('Social Listening API model', () => {
  it('treats a complete empty summary as genuine zero counts', () => {
    expect(parseListeningSummary(emptySummary)).toEqual({
      totalMentions: 0,
      alertCount: 0,
      openAlerts: 0,
      ruleCount: 0,
      sentiment: { positive: 0, neutral: 0, negative: 0 },
    });
  });

  it('rejects missing summary totals instead of turning them into zeroes', () => {
    expect(parseListeningSummary({ status: 'ok', sentiment_breakdown: {} })).toBeNull();
    expect(parseListeningSummary({ ...emptySummary, totals: { ...emptySummary.totals, mentions: '0' } })).toBeNull();
  });

  it('accepts empty mention, alert, and rule lists from valid envelopes', () => {
    expect(parseListeningMentions({ status: 'ok', count: 0, mentions: [] })).toEqual([]);
    expect(parseListeningAlerts({ status: 'ok', count: 0, alerts: [] })).toEqual([]);
    expect(parseListeningRules({ status: 'ok', count: 0, persistence: 'memory-fallback', rules: [] })).toEqual([]);
  });

  it('preserves real zero engagement and ignores internal persistence metadata', () => {
    expect(parseListeningMentions({ status: 'ok', mentions: [mention] })).toEqual([{
      id: 4,
      platform: 'linkedin',
      query: 'brand mention',
      authorHandle: '@customer',
      text: 'A manually captured mention.',
      sentiment: 'neutral',
      engagementCount: 0,
      createdAt: '2026-10-12T12:00:00Z',
    }]);
  });

  it('rejects malformed identifiers or incomplete records rather than rendering partial business data', () => {
    expect(parseListeningMentions({ status: 'ok', mentions: [{ ...mention, id: '4' }] })).toBeNull();
    expect(parseListeningAlerts({ status: 'ok', alerts: [{ id: 1, mention_id: 0 }] })).toBeNull();
    expect(parseListeningRules({ status: 'ok', rules: [{ id: 2, name: 'Watch' }] })).toBeNull();
  });

  it('parses tenant-safe alert and rule views without exposing workspace identifiers', () => {
    expect(parseListeningAlerts({ status: 'ok', tenant_id: 'private-id', alerts: [{
      id: 3, rule_name: 'Negative mentions', mention_id: 4, severity: 'high', status: 'open', created_at: '2026-10-12T12:00:00Z',
    }] })?.[0]).toMatchObject({ id: 3, mentionId: 4, severity: 'high', status: 'open' });
    expect(parseListeningRules({ status: 'ok', tenant_id: 'private-id', rules: [{
      id: 7, name: 'Brand review', query: null, platform: null, min_engagement: 20, negative_only: true, enabled: true, created_at: '2026-10-12T12:00:00Z',
    }] })?.[0]).toMatchObject({ id: 7, name: 'Brand review', minEngagement: 20, negativeOnly: true });
  });
});
