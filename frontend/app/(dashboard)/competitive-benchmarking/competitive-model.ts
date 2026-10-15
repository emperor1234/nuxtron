export type CompetitorProfile = {
  id: number;
  name: string;
  network: string;
  handle: string;
  snapshotCount: number | null;
};

export type MetricSnapshot = {
  followers: number | null;
  engagementRate: number | null;
  estimatedMentions: number | null;
  snapshotDate: string | null;
};

export type CompetitorComparison = {
  profile: CompetitorProfile;
  latestSnapshot: MetricSnapshot | null;
};

export type ComparisonReport = {
  ownBrand: MetricSnapshot | null;
  competitors: CompetitorComparison[];
};

export type ShareOfVoiceEntry = {
  brand: string;
  estimatedMentions: number;
  sharePct: number;
};

export type SnapshotDraft = {
  followers: string;
  engagementRate: string;
  estimatedMentions: string;
  snapshotDate: string;
};

export type SnapshotPayload = {
  followers: number;
  engagement_rate: number;
  estimated_mentions: number;
  snapshot_date?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function positiveId(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

function nonNegativeCount(value: unknown): number | null | undefined {
  if (value === undefined || value === null) return null;
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : undefined;
}

function percent(value: unknown): number | null | undefined {
  if (value === undefined || value === null) return null;
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100 ? value : undefined;
}

function parseProfile(value: unknown): CompetitorProfile | null {
  if (!isRecord(value) || !positiveId(value.id)) return null;
  if (typeof value.name !== 'string' || !value.name.trim()) return null;
  if (typeof value.network !== 'string' || !value.network.trim()) return null;
  if (typeof value.handle !== 'string' || !value.handle.trim()) return null;
  const snapshotCount = nonNegativeCount(value.snapshot_count);
  if (snapshotCount === undefined) return null;
  return {
    id: value.id,
    name: value.name.trim(),
    network: value.network.trim(),
    handle: value.handle.trim(),
    snapshotCount,
  };
}

function parseSnapshot(value: unknown): MetricSnapshot | null {
  if (!isRecord(value)) return null;
  const followers = nonNegativeCount(value.followers);
  const engagementRate = percent(value.engagement_rate);
  const estimatedMentions = nonNegativeCount(value.estimated_mentions);
  if (followers === undefined || engagementRate === undefined || estimatedMentions === undefined) return null;
  if (value.snapshot_date !== undefined && value.snapshot_date !== null && typeof value.snapshot_date !== 'string') return null;
  return {
    followers,
    engagementRate,
    estimatedMentions,
    snapshotDate: typeof value.snapshot_date === 'string' && value.snapshot_date.trim() ? value.snapshot_date : null,
  };
}

export function parseCompetitorProfiles(value: unknown): CompetitorProfile[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.profiles)) return null;
  if (value.count !== value.profiles.length) return null;
  const profiles: CompetitorProfile[] = [];
  const ids = new Set<number>();
  for (const raw of value.profiles) {
    const profile = parseProfile(raw);
    if (!profile || ids.has(profile.id)) return null;
    ids.add(profile.id);
    profiles.push(profile);
  }
  return profiles;
}

export function parseComparisonReport(value: unknown): ComparisonReport | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.competitors)) return null;
  const ownBrand = value.own_brand === null ? null : parseSnapshot(value.own_brand);
  if (value.own_brand !== null && ownBrand === null) return null;
  const competitors: CompetitorComparison[] = [];
  const ids = new Set<number>();
  for (const raw of value.competitors) {
    if (!isRecord(raw)) return null;
    const profile = parseProfile(raw.profile);
    if (!profile || ids.has(profile.id)) return null;
    const latestSnapshot = raw.latest_snapshot === null ? null : parseSnapshot(raw.latest_snapshot);
    if (raw.latest_snapshot !== null && latestSnapshot === null) return null;
    ids.add(profile.id);
    competitors.push({ profile, latestSnapshot });
  }
  return { ownBrand, competitors };
}

export function parseShareOfVoice(value: unknown): { totalEstimatedMentions: number; breakdown: ShareOfVoiceEntry[] } | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.breakdown)) return null;
  const totalEstimatedMentions = nonNegativeCount(value.total_estimated_mentions);
  if (totalEstimatedMentions === null || totalEstimatedMentions === undefined) return null;
  const breakdown: ShareOfVoiceEntry[] = [];
  for (const raw of value.breakdown) {
    if (!isRecord(raw) || typeof raw.brand !== 'string' || !raw.brand.trim()) return null;
    const estimatedMentions = nonNegativeCount(raw.estimated_mentions);
    const sharePct = percent(raw.share_pct);
    if (estimatedMentions === null || estimatedMentions === undefined || sharePct === null || sharePct === undefined) return null;
    breakdown.push({ brand: raw.brand === '__OWN_BRAND__' ? 'Your brand' : raw.brand.trim(), estimatedMentions, sharePct });
  }
  return { totalEstimatedMentions, breakdown };
}

export function buildSnapshotPayload(draft: SnapshotDraft): SnapshotPayload | null {
  const followersText = draft.followers.trim();
  const engagementText = draft.engagementRate.trim();
  const mentionsText = draft.estimatedMentions.trim();
  if (!followersText || !engagementText || !mentionsText) return null;
  const followers = Number(followersText);
  const engagementRate = Number(engagementText);
  const estimatedMentions = Number(mentionsText);
  if (!Number.isInteger(followers) || followers < 0) return null;
  if (!Number.isFinite(engagementRate) || engagementRate < 0 || engagementRate > 100) return null;
  if (!Number.isInteger(estimatedMentions) || estimatedMentions < 0) return null;
  return {
    followers,
    engagement_rate: engagementRate,
    estimated_mentions: estimatedMentions,
    ...(draft.snapshotDate.trim() ? { snapshot_date: draft.snapshotDate.trim() } : {}),
  };
}

export function formatCompetitiveDate(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toLocaleDateString();
}
