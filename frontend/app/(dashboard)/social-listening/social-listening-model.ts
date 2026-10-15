export type SocialPlatform = 'linkedin' | 'x' | 'instagram' | 'facebook' | 'reddit' | 'youtube' | 'news';
export type MentionSentiment = 'positive' | 'neutral' | 'negative';

export type ListeningSummary = {
  totalMentions: number;
  alertCount: number;
  openAlerts: number;
  ruleCount: number;
  sentiment: Record<MentionSentiment, number>;
};

export type ListeningMention = {
  id: number;
  platform: SocialPlatform;
  query: string;
  authorHandle: string;
  text: string;
  sentiment: MentionSentiment;
  engagementCount: number;
  createdAt: string;
};

export type ListeningAlert = {
  id: number;
  ruleName: string;
  mentionId: number;
  severity: 'medium' | 'high';
  status: 'open' | 'closed';
  createdAt: string;
};

export type ListeningRule = {
  id: number;
  name: string;
  query: string | null;
  platform: SocialPlatform | null;
  minEngagement: number;
  negativeOnly: boolean;
  enabled: boolean;
  createdAt: string;
};

const PLATFORMS = new Set<SocialPlatform>(['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news']);
const SENTIMENTS = new Set<MentionSentiment>(['positive', 'neutral', 'negative']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

function positiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

function validDate(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0 && Number.isFinite(Date.parse(value));
}

function validPlatform(value: unknown): value is SocialPlatform {
  return typeof value === 'string' && PLATFORMS.has(value as SocialPlatform);
}

function validSentiment(value: unknown): value is MentionSentiment {
  return typeof value === 'string' && SENTIMENTS.has(value as MentionSentiment);
}

function sparseCount(source: Record<string, unknown>, key: MentionSentiment): number | null {
  const value = source[key];
  if (value === undefined) return 0;
  return nonNegativeInteger(value) ? value : null;
}

export function parseListeningSummary(value: unknown): ListeningSummary | null {
  if (!isRecord(value) || value.status !== 'ok' || !isRecord(value.totals) || !isRecord(value.sentiment_breakdown)) return null;
  const totals = value.totals;
  if (
    !nonNegativeInteger(totals.mentions) || !nonNegativeInteger(totals.alerts) ||
    !nonNegativeInteger(totals.open_alerts) || !nonNegativeInteger(totals.rules)
  ) return null;
  const sentiment = {
    positive: sparseCount(value.sentiment_breakdown, 'positive'),
    neutral: sparseCount(value.sentiment_breakdown, 'neutral'),
    negative: sparseCount(value.sentiment_breakdown, 'negative'),
  };
  if (sentiment.positive === null || sentiment.neutral === null || sentiment.negative === null) return null;
  return {
    totalMentions: totals.mentions,
    alertCount: totals.alerts,
    openAlerts: totals.open_alerts,
    ruleCount: totals.rules,
    sentiment: {
      positive: sentiment.positive,
      neutral: sentiment.neutral,
      negative: sentiment.negative,
    },
  };
}

function parseMention(value: unknown): ListeningMention | null {
  if (!isRecord(value) || !positiveInteger(value.id) || !validPlatform(value.platform) || !validSentiment(value.sentiment)) return null;
  if (
    typeof value.query !== 'string' || typeof value.author_handle !== 'string' || typeof value.text !== 'string' ||
    !nonNegativeInteger(value.engagement_count) || !validDate(value.created_at)
  ) return null;
  return {
    id: value.id,
    platform: value.platform,
    query: value.query,
    authorHandle: value.author_handle,
    text: value.text,
    sentiment: value.sentiment,
    engagementCount: value.engagement_count,
    createdAt: value.created_at,
  };
}

export function parseListeningMentions(value: unknown): ListeningMention[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.mentions)) return null;
  const mentions = value.mentions.map(parseMention);
  return mentions.every((mention): mention is ListeningMention => mention !== null) ? mentions : null;
}

export function parseListeningMentionResponse(value: unknown): ListeningMention | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  return parseMention(value.mention);
}

export function parseListeningAlerts(value: unknown): ListeningAlert[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.alerts)) return null;
  const alerts = value.alerts.map((item): ListeningAlert | null => {
    if (!isRecord(item) || !positiveInteger(item.id) || !positiveInteger(item.mention_id)) return null;
    if (
      typeof item.rule_name !== 'string' || (item.severity !== 'medium' && item.severity !== 'high') ||
      (item.status !== 'open' && item.status !== 'closed') || !validDate(item.created_at)
    ) return null;
    return {
      id: item.id,
      ruleName: item.rule_name,
      mentionId: item.mention_id,
      severity: item.severity,
      status: item.status,
      createdAt: item.created_at,
    };
  });
  return alerts.every((alert): alert is ListeningAlert => alert !== null) ? alerts : null;
}

export function parseListeningRules(value: unknown): ListeningRule[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.rules)) return null;
  const rules = value.rules.map((item): ListeningRule | null => {
    if (!isRecord(item) || !positiveInteger(item.id) || typeof item.name !== 'string' || !item.name.trim()) return null;
    if (
      (item.query !== null && typeof item.query !== 'string') ||
      (item.platform !== null && !validPlatform(item.platform)) ||
      !nonNegativeInteger(item.min_engagement) || typeof item.negative_only !== 'boolean' ||
      typeof item.enabled !== 'boolean' || !validDate(item.created_at)
    ) return null;
    return {
      id: item.id,
      name: item.name,
      query: item.query as string | null,
      platform: item.platform as SocialPlatform | null,
      minEngagement: item.min_engagement,
      negativeOnly: item.negative_only,
      enabled: item.enabled,
      createdAt: item.created_at,
    };
  });
  return rules.every((rule): rule is ListeningRule => rule !== null) ? rules : null;
}
