import { describe, expect, it } from 'vitest';
import {
  buildSnapshotPayload,
  formatCompetitiveDate,
  parseComparisonReport,
  parseCompetitorProfiles,
  parseShareOfVoice,
  type SnapshotDraft,
} from './competitive-model';

const profile = { id: 4, name: 'Northwind', network: 'linkedin', handle: 'northwind', snapshot_count: 1 };
const blankDraft: SnapshotDraft = { followers: '', engagementRate: '', estimatedMentions: '', snapshotDate: '' };

describe('competitive benchmarking model', () => {
  it('accepts a real empty profile list but rejects missing or inconsistent envelopes', () => {
    expect(parseCompetitorProfiles({ status: 'ok', count: 0, profiles: [] })).toEqual([]);
    expect(parseCompetitorProfiles({ status: 'ok', profiles: [] })).toBeNull();
    expect(parseCompetitorProfiles({ status: 'ok', count: 1, profiles: [] })).toBeNull();
  });

  it('rejects malformed profile identifiers and duplicate records', () => {
    expect(parseCompetitorProfiles({ status: 'ok', count: 1, profiles: [{ ...profile, id: 0 }] })).toBeNull();
    expect(parseCompetitorProfiles({ status: 'ok', count: 2, profiles: [profile, profile] })).toBeNull();
  });

  it('preserves actual zeroes while leaving unreported comparison metrics unavailable', () => {
    const report = parseComparisonReport({
      status: 'ok',
      own_brand: { followers: 0, engagement_rate: 0, estimated_mentions: 0, snapshot_date: '2026-10-12' },
      competitors: [
        { profile, latest_snapshot: { followers: 0, engagement_rate: 0, estimated_mentions: 0, snapshot_date: '2026-10-12' } },
        { profile: { ...profile, id: 5 }, latest_snapshot: null },
      ],
    });
    expect(report?.ownBrand?.followers).toBe(0);
    expect(report?.competitors[0].latestSnapshot?.estimatedMentions).toBe(0);
    expect(report?.competitors[1].latestSnapshot).toBeNull();
    expect(parseComparisonReport({ status: 'ok', competitors: [], own_brand: undefined })).toBeNull();
  });

  it('accepts zero share only when the backend reports real zero totals and rejects missing metrics', () => {
    expect(parseShareOfVoice({ status: 'ok', total_estimated_mentions: 0, breakdown: [] })).toEqual({ totalEstimatedMentions: 0, breakdown: [] });
    expect(parseShareOfVoice({ status: 'ok', total_estimated_mentions: 0, breakdown: [{ brand: 'Your brand', estimated_mentions: 0, share_pct: 0 }] })?.breakdown[0].sharePct).toBe(0);
    expect(parseShareOfVoice({ status: 'ok', breakdown: [] })).toBeNull();
    expect(parseShareOfVoice({ status: 'ok', total_estimated_mentions: 2, breakdown: [{ brand: 'Northwind', estimated_mentions: 2 }] })).toBeNull();
  });

  it('requires explicit manual values but allows an intentional zero snapshot', () => {
    expect(buildSnapshotPayload(blankDraft)).toBeNull();
    expect(buildSnapshotPayload({ ...blankDraft, followers: '0', engagementRate: '0', estimatedMentions: '0' })).toEqual({ followers: 0, engagement_rate: 0, estimated_mentions: 0 });
    expect(buildSnapshotPayload({ ...blankDraft, followers: '4.5', engagementRate: '2', estimatedMentions: '0' })).toBeNull();
    expect(buildSnapshotPayload({ ...blankDraft, followers: '4', engagementRate: '101', estimatedMentions: '0' })).toBeNull();
  });

  it('formats invalid dates as unavailable', () => {
    expect(formatCompetitiveDate('not-a-date')).toBeNull();
    expect(formatCompetitiveDate(null)).toBeNull();
  });
});
