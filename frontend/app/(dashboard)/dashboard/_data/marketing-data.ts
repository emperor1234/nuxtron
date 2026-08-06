/**
 * Static demo data for the Marketing Overview dashboard.
 * Mirrors the approved reference. Replace these literals with live
 * fetches (e.g. server actions / route handlers) when wiring real data —
 * the component contracts below are intentionally serialisable.
 */

export type TrendMetric = 'traffic' | 'keywords' | 'cost';

export type SparkPath = {
  /** SVG path "d" for the stroked line. */
  line: string;
  /** SVG path "d" for the filled area below the line. */
  area: string;
  /** Final point [x, y], handy for an end-of-series marker. */
  last: readonly [number, number];
};

/** Build a line + area path from a series of values within a w×h box. */
export function buildSparkPath(values: readonly number[], w: number, h: number, pad: number): SparkPath {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = values.length;
  const pts = values.map((v, i) => {
    const x = n === 1 ? w / 2 : (i / (n - 1)) * w;
    const y = pad + (1 - (v - min) / range) * (h - pad * 2);
    return [Number(x.toFixed(1)), Number(y.toFixed(1))] as const;
  });
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]} ${p[1]}`).join(' ');
  const area = `${line} L${w} ${h} L0 ${h} Z`;
  return { line, area, last: pts[pts.length - 1] };
}

export type DonutSegment = {
  label: string;
  pct: number;
  color: string;
  /** stroke-dasharray for an r=64 ring. */
  dash: string;
  /** stroke-dashoffset for an r=64 ring. */
  offset: string;
};

/** Convert percentage slices into stroke dash/offset values for a donut ring. */
export function buildDonutSegments(
  slices: readonly { label: string; pct: number; color: string }[],
  radius = 64
): DonutSegment[] {
  const circumference = 2 * Math.PI * radius;
  let acc = 0;
  return slices.map((s) => {
    const len = (s.pct / 100) * circumference;
    const segment: DonutSegment = {
      ...s,
      dash: `${len.toFixed(1)} ${(circumference - len).toFixed(1)}`,
      offset: (-acc).toFixed(1),
    };
    acc += len;
    return segment;
  });
}

export type Kpi = {
  key: string;
  label: string;
  /** numeric magnitude used for the count-up animation. */
  value: number;
  /** suffix appended after the animated number (e.g. "K", "M"). */
  suffix?: string;
  decimals?: number;
  delta: number;
  up: boolean;
  color: string;
  iconBg: string;
  icon: 'authority' | 'traffic' | 'keywords' | 'backlinks' | 'social';
  data: number[];
};

export const KPIS: readonly Kpi[] = [
  {
    key: 'authority',
    label: 'Authority Score',
    value: 68,
    delta: 4.2,
    up: true,
    color: '#6d5efc',
    iconBg: '#efeefe',
    icon: 'authority',
    data: [54, 56, 55, 58, 60, 59, 63, 62, 65, 66, 68],
  },
  {
    key: 'traffic',
    label: 'Organic Traffic',
    value: 241,
    suffix: 'K',
    delta: 12.8,
    up: true,
    color: '#10b981',
    iconBg: '#e7f8f1',
    icon: 'traffic',
    data: [180, 188, 182, 196, 205, 210, 222, 219, 231, 236, 241],
  },
  {
    key: 'keywords',
    label: 'Keywords',
    value: 12.4,
    suffix: 'K',
    decimals: 1,
    delta: 6.1,
    up: true,
    color: '#0ea5e9',
    iconBg: '#e4f4fd',
    icon: 'keywords',
    data: [9.8, 10.2, 10.6, 10.4, 11, 11.3, 11.6, 11.9, 12, 12.2, 12.4],
  },
  {
    key: 'backlinks',
    label: 'Backlinks',
    value: 89.2,
    suffix: 'K',
    decimals: 1,
    delta: 2.4,
    up: false,
    color: '#f59e0b',
    iconBg: '#fef3e0',
    icon: 'backlinks',
    data: [92, 91, 93, 90, 91, 89.8, 90.5, 89.6, 90, 89.4, 89.2],
  },
  {
    key: 'social',
    label: 'Social Reach',
    value: 1.9,
    suffix: 'M',
    decimals: 1,
    delta: 18.4,
    up: true,
    color: '#ec4899',
    iconBg: '#fde7f2',
    icon: 'social',
    data: [1.2, 1.3, 1.35, 1.4, 1.5, 1.55, 1.62, 1.7, 1.78, 1.85, 1.9],
  },
] as const;

export const TREND_SERIES: Record<TrendMetric, number[]> = {
  traffic: [148, 162, 151, 176, 192, 184, 205, 228, 216, 239, 247, 261],
  keywords: [8.2, 8.6, 9.1, 9.4, 9.9, 10.3, 10.8, 11.2, 11.6, 11.9, 12.1, 12.4],
  cost: [88, 94, 99, 110, 121, 118, 132, 145, 151, 162, 170, 181],
};

export const TREND_SUMMARY: Record<TrendMetric, { label: string; value: string; delta: string }> = {
  traffic: { label: 'Traffic', value: '261K', delta: '12.8%' },
  keywords: { label: 'Keywords', value: '12.4K', delta: '6.1%' },
  cost: { label: 'Traffic cost', value: '$181K', delta: '9.4%' },
};

export const TREND_TABS: readonly { id: TrendMetric; label: string }[] = [
  { id: 'traffic', label: 'Traffic' },
  { id: 'keywords', label: 'Keywords' },
  { id: 'cost', label: 'Traffic cost' },
];

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;

export const TRAFFIC_SOURCES = [
  { label: 'Organic search', pct: 47, color: '#6d5efc' },
  { label: 'Social', pct: 19, color: '#ec4899' },
  { label: 'Direct', pct: 14, color: '#0ea5e9' },
  { label: 'Referral', pct: 12, color: '#10b981' },
  { label: 'Paid', pct: 8, color: '#f59e0b' },
] as const;

export const TRAFFIC_SOURCES_TOTAL = '241K';

export type Intent = 'Commercial' | 'Informational' | 'Transactional';

export const INTENT_STYLE: Record<Intent, { bg: string; color: string }> = {
  Commercial: { bg: '#efeefe', color: '#6d5efc' },
  Informational: { bg: '#e4f4fd', color: '#0284c7' },
  Transactional: { bg: '#e7f8f1', color: '#059669' },
};

export type KeywordRow = {
  keyword: string;
  position: number;
  change: string;
  trend: 'up' | 'down' | 'flat';
  volume: string;
  intent: Intent;
};

export const KEYWORDS: readonly KeywordRow[] = [
  { keyword: 'ai marketing tools', position: 3, change: '▲2', trend: 'up', volume: '22.4K', intent: 'Commercial' },
  { keyword: 'seo automation platform', position: 1, change: '▲1', trend: 'up', volume: '14.8K', intent: 'Informational' },
  { keyword: 'social media scheduler', position: 5, change: '▼1', trend: 'down', volume: '33.1K', intent: 'Commercial' },
  { keyword: 'content optimization ai', position: 2, change: '▲4', trend: 'up', volume: '9.6K', intent: 'Informational' },
  { keyword: 'keyword research tool', position: 7, change: '▲3', trend: 'up', volume: '18.2K', intent: 'Transactional' },
  { keyword: 'marketing analytics dashboard', position: 4, change: '—', trend: 'flat', volume: '27.5K', intent: 'Commercial' },
] as const;

export type SocialBar = { name: string; value: string; pct: number; color: string };

export const SOCIAL: readonly SocialBar[] = [
  { name: 'Instagram', value: '486K', pct: 100, color: 'linear-gradient(90deg,#f59e0b,#ec4899)' },
  { name: 'LinkedIn', value: '392K', pct: 81, color: '#0a66c2' },
  { name: 'TikTok', value: '331K', pct: 68, color: '#0e1525' },
  { name: 'X', value: '248K', pct: 51, color: '#3d4456' },
  { name: 'YouTube', value: '187K', pct: 38, color: '#ef4444' },
  { name: 'Facebook', value: '142K', pct: 29, color: '#1877f2' },
] as const;

export const SOCIAL_DELTA = '▲ 18.4%';

export type FunnelStage = { stage: string; value: string; pct: number; rate: string; color: string };

export const FUNNEL: readonly FunnelStage[] = [
  { stage: 'Impressions', value: '4.2M', pct: 100, rate: '100%', color: 'linear-gradient(90deg,#6d5efc,#8b5cf6)' },
  { stage: 'Visits', value: '241K', pct: 74, rate: '5.7%', color: 'linear-gradient(90deg,#7c6ffc,#a855f7)' },
  { stage: 'Leads', value: '38.6K', pct: 52, rate: '16%', color: 'linear-gradient(90deg,#a855f7,#c026d3)' },
  { stage: 'Signups', value: '14.2K', pct: 34, rate: '37%', color: 'linear-gradient(90deg,#c026d3,#db2777)' },
  { stage: 'Customers', value: '4.8K', pct: 20, rate: '34%', color: 'linear-gradient(90deg,#db2777,#ec4899)' },
] as const;

export const FUNNEL_SUMMARY = '2.8% end-to-end';

export type AiInsight = { tag: string; tagBg: string; tagColor: string; impact: string; text: string };

export const AI_INSIGHTS: readonly AiInsight[] = [
  {
    tag: 'Opportunity',
    tagBg: 'rgba(16,185,129,.18)',
    tagColor: '#5eead4',
    impact: 'High impact',
    text: '14 keywords sit on page 2 — a content refresh could lift them into the top 10 and add ~31K visits/mo.',
  },
  {
    tag: 'Content',
    tagBg: 'rgba(109,94,252,.22)',
    tagColor: '#b9aef9',
    impact: 'Medium',
    text: 'Reels on “AI marketing” outperform static posts 3.4×. Shift 30% of the calendar to short-form video.',
  },
  {
    tag: 'Alert',
    tagBg: 'rgba(245,158,11,.18)',
    tagColor: '#fcd34d',
    impact: 'Watch',
    text: 'Backlinks dipped 2.4% — 6 referring domains went stale. Reach out to reclaim lost links.',
  },
] as const;
