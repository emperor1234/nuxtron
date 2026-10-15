export type PersistenceMode = 'postgres' | 'process-memory';
export type CurrencyStatus = 'none' | 'single' | 'mixed' | 'unsupported';

export type RoiMetrics = {
  revenue: number | null;
  spend: number | null;
  netProfit: number | null;
  roas: number | null;
  roiPct: number | null;
};

export type RoiSummary = {
  windowDays: number;
  persistenceMode: PersistenceMode;
  currencyStatus: CurrencyStatus;
  currencyCodes: string[];
  invalidCurrencyRecords: number;
  totals: RoiMetrics & {
    conversions: number;
    trackedConversions: number;
    touchpoints: number;
    spendEntries: number;
    trackingCoveragePct: number | null;
  };
  channels: Array<RoiMetrics & { name: string }>;
  campaigns: Array<RoiMetrics & { name: string }>;
};

export type SpendEntry = {
  id: number;
  channel: string;
  campaign: string;
  currency: string;
  amount: number;
  notes: string;
  spentAt: string;
};

export type CalculatorResult = RoiMetrics;

export type TrackedLinkResult = {
  trackedUrl: string;
  persistenceMode: PersistenceMode;
};

export type RoiDraft = {
  postId: string;
  platform: string;
  campaign: string;
  destinationUrl: string;
};

export type SpendDraft = {
  channel: string;
  campaign: string;
  amount: string;
  currency: string;
};

export type CalculatorDraft = {
  revenue: string;
  paidSpend: string;
  teamCost: string;
  toolsCost: string;
  agencyCost: string;
};

type RecordValue = Record<string, unknown>;
const MONEY_KEYS = ['revenue', 'spend', 'net_profit', 'roas', 'roi_pct'] as const;

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function nonNegativeInteger(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null;
}

function nullableMetric(value: unknown): number | null | undefined {
  if (value === null) return null;
  return finiteNumber(value) ?? undefined;
}

function parseMetrics(value: unknown): RoiMetrics | null {
  if (!isRecord(value)) return null;
  const revenue = nullableMetric(value.revenue);
  const spend = nullableMetric(value.spend);
  const netProfit = nullableMetric(value.net_profit);
  const roas = nullableMetric(value.roas);
  const roiPct = nullableMetric(value.roi_pct);
  if (revenue === undefined || spend === undefined || netProfit === undefined || roas === undefined || roiPct === undefined) return null;
  return { revenue, spend, netProfit, roas, roiPct };
}

function parseBreakdown(value: unknown, key: 'channel' | 'campaign'): Array<RoiMetrics & { name: string }> | null {
  if (!Array.isArray(value)) return null;
  const rows: Array<RoiMetrics & { name: string }> = [];
  const names = new Set<string>();
  for (const candidate of value) {
    if (!isRecord(candidate) || typeof candidate[key] !== 'string' || !candidate[key].trim()) return null;
    const name = candidate[key].trim();
    if (names.has(name)) return null;
    names.add(name);
    const metrics = parseMetrics(candidate);
    if (!metrics) return null;
    rows.push({ name, ...metrics });
  }
  return rows;
}

export function parseRoiSummary(value: unknown): RoiSummary | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  if (value.persistence_mode !== 'postgres' && value.persistence_mode !== 'process-memory') return null;
  if (value.currency_status !== 'none' && value.currency_status !== 'single' && value.currency_status !== 'mixed' && value.currency_status !== 'unsupported') return null;
  if (!Array.isArray(value.currency_codes) || !value.currency_codes.every((code) => typeof code === 'string' && /^[A-Z]{3}$/.test(code))) return null;
  const currencyCodes = [...new Set(value.currency_codes as string[])].sort();
  const invalidCurrencyRecords = nonNegativeInteger(value.invalid_currency_records);
  const windowDays = nonNegativeInteger(value.window_days);
  if (invalidCurrencyRecords === null || windowDays === null || windowDays < 1 || windowDays > 365) return null;

  const status = value.currency_status as CurrencyStatus;
  if (status === 'none' && (currencyCodes.length !== 0 || invalidCurrencyRecords !== 0)) return null;
  if (status === 'single' && (currencyCodes.length !== 1 || invalidCurrencyRecords !== 0)) return null;
  if (status === 'mixed' && (currencyCodes.length < 2 || invalidCurrencyRecords !== 0)) return null;
  if (status === 'unsupported' && invalidCurrencyRecords === 0) return null;

  if (!isRecord(value.totals)) return null;
  const rawTotals = value.totals;
  const metrics = parseMetrics(rawTotals);
  const conversions = nonNegativeInteger(rawTotals.conversions);
  const trackedConversions = nonNegativeInteger(rawTotals.tracked_conversions);
  const touchpoints = nonNegativeInteger(rawTotals.touchpoints);
  const spendEntries = nonNegativeInteger(rawTotals.spend_entries);
  const trackingCoveragePct = nullableMetric(rawTotals.tracking_coverage_pct);
  if (!metrics || conversions === null || trackedConversions === null || touchpoints === null || spendEntries === null || trackingCoveragePct === undefined) return null;
  if (trackingCoveragePct !== null && (trackingCoveragePct < 0 || trackingCoveragePct > 100)) return null;

  const channels = parseBreakdown(value.channels, 'channel');
  const campaigns = parseBreakdown(value.campaigns, 'campaign');
  if (!channels || !campaigns) return null;
  if (status !== 'single') {
    if (MONEY_KEYS.some((key) => rawTotals[key] !== null)) return null;
    if ([...channels, ...campaigns].some((row) => MONEY_KEYS.some((key) => row[metricKey(key)] !== null))) return null;
  } else {
    if (metrics.revenue === null || metrics.spend === null || metrics.netProfit === null) return null;
    if ([...channels, ...campaigns].some((row) => row.revenue === null || row.spend === null || row.netProfit === null)) return null;
  }

  return {
    windowDays,
    persistenceMode: value.persistence_mode,
    currencyStatus: status,
    currencyCodes,
    invalidCurrencyRecords,
    totals: { ...metrics, conversions, trackedConversions, touchpoints, spendEntries, trackingCoveragePct },
    channels,
    campaigns,
  };
}

function metricKey(key: (typeof MONEY_KEYS)[number]): keyof RoiMetrics {
  if (key === 'net_profit') return 'netProfit';
  if (key === 'roi_pct') return 'roiPct';
  return key;
}

function validPersistence(value: unknown): value is PersistenceMode {
  return value === 'postgres' || value === 'process-memory';
}

export function parseSpendList(value: unknown): { persistenceMode: PersistenceMode; items: SpendEntry[] } | null {
  if (!isRecord(value) || value.status !== 'ok' || !validPersistence(value.persistence_mode) || !Array.isArray(value.items)) return null;
  const count = nonNegativeInteger(value.count);
  if (count === null || count !== value.items.length) return null;
  const items: SpendEntry[] = [];
  const ids = new Set<number>();
  for (const candidate of value.items) {
    if (!isRecord(candidate)) return null;
    const id = nonNegativeInteger(candidate.id);
    const amount = finiteNumber(candidate.amount);
    const spentAt = typeof candidate.spent_at === 'string' ? candidate.spent_at : '';
    const currency = typeof candidate.currency === 'string' ? candidate.currency.trim().toUpperCase() : '';
    if (id === null || id < 1 || ids.has(id) || amount === null || amount <= 0 || !/^[A-Z]{3}$/.test(currency)) return null;
    if (typeof candidate.channel !== 'string' || !candidate.channel.trim() || typeof candidate.campaign !== 'string') return null;
    if (!spentAt || !Number.isFinite(Date.parse(spentAt))) return null;
    if (candidate.notes !== undefined && typeof candidate.notes !== 'string') return null;
    ids.add(id);
    items.push({ id, channel: candidate.channel.trim(), campaign: candidate.campaign.trim(), currency, amount, notes: typeof candidate.notes === 'string' ? candidate.notes : '', spentAt });
  }
  return { persistenceMode: value.persistence_mode, items };
}

export function parseCalculatorResult(value: unknown): CalculatorResult | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  const result = parseMetrics(value.totals);
  return result && result.revenue !== null && result.spend !== null && result.netProfit !== null ? result : null;
}

export function parseSpendWriteResult(value: unknown): { persistenceMode: PersistenceMode } | null {
  if (!isRecord(value) || value.status !== 'ok' || !validPersistence(value.persistence_mode) || !isRecord(value.spend)) return null;
  const item = value.spend;
  const id = nonNegativeInteger(item.id);
  const amount = finiteNumber(item.amount);
  if (id === null || id < 1 || amount === null || amount <= 0) return null;
  if (typeof item.channel !== 'string' || !item.channel.trim() || typeof item.currency !== 'string' || !/^[A-Z]{3}$/.test(item.currency.trim().toUpperCase())) return null;
  if (typeof item.campaign !== 'string' || typeof item.spent_at !== 'string' || !Number.isFinite(Date.parse(item.spent_at))) return null;
  return { persistenceMode: value.persistence_mode };
}

export function parseTrackedLinkResult(value: unknown): TrackedLinkResult | null {
  if (!isRecord(value) || value.status !== 'ok' || !validPersistence(value.persistence_mode) || !isRecord(value.touchpoint)) return null;
  const trackedUrl = value.touchpoint.tracked_url;
  if (typeof trackedUrl !== 'string' || trackedUrl.length > 4096) return null;
  try {
    const parsed = new URL(trackedUrl);
    if ((parsed.protocol !== 'https:' && parsed.protocol !== 'http:') || !parsed.hostname || parsed.username || parsed.password) return null;
    if (!/^tp_[a-z0-9]{8,}$/.test(parsed.searchParams.get('nux_touchpoint') ?? '')) return null;
    return { trackedUrl: parsed.toString(), persistenceMode: value.persistence_mode };
  } catch {
    return null;
  }
}

function amountFromDraft(value: string, allowZero: boolean): number | null {
  if (!value.trim()) return null;
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount < 0 || (!allowZero && amount === 0)) return null;
  return amount;
}

function normalizedCurrency(value: string): string | null {
  const currency = value.trim().toUpperCase();
  return /^[A-Z]{3}$/.test(currency) ? currency : null;
}

export function buildTrackedLinkPayload(draft: RoiDraft): { post_id: string; platform: string; campaign: string; destination_url: string } | null {
  const postId = draft.postId.trim();
  const platform = draft.platform.trim().toLowerCase();
  const campaign = draft.campaign.trim();
  if (!postId || postId.length > 160 || !platform || platform.length > 80 || !campaign || campaign.length > 160) return null;
  if (draft.destinationUrl.trim().length > 2000) return null;
  try {
    const url = new URL(draft.destinationUrl.trim());
    if ((url.protocol !== 'https:' && url.protocol !== 'http:') || !url.hostname || url.username || url.password) return null;
    return { post_id: postId, platform, campaign, destination_url: url.toString() };
  } catch {
    return null;
  }
}

export function buildSpendPayload(draft: SpendDraft): { channel: string; campaign: string; amount: number; currency: string } | null {
  const channel = draft.channel.trim().toLowerCase();
  const campaign = draft.campaign.trim();
  const amount = amountFromDraft(draft.amount, false);
  const currency = normalizedCurrency(draft.currency);
  if (!channel || channel.length > 80 || campaign.length > 160 || amount === null || !currency) return null;
  return { channel, campaign, amount, currency };
}

export function buildCalculatorPayload(draft: CalculatorDraft): {
  attributed_revenue: number;
  paid_social_spend: number;
  team_cost: number;
  tools_cost: number;
  agency_cost: number;
} | null {
  const values = [draft.revenue, draft.paidSpend, draft.teamCost, draft.toolsCost, draft.agencyCost].map((value) => amountFromDraft(value, true));
  if (values.some((value) => value === null)) return null;
  const [attributed_revenue, paid_social_spend, team_cost, tools_cost, agency_cost] = values as [number, number, number, number, number];
  return { attributed_revenue, paid_social_spend, team_cost, tools_cost, agency_cost };
}

export function formatCurrencyAmount(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  }
}
