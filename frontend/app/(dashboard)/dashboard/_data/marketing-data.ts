/**
 * Shape + pure helpers for the Marketing Overview dashboard.
 * All values are populated at runtime from live backend endpoints (see
 * `use-marketing-overview.ts`) — nothing here is sample/demo data.
 */

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
  if (values.length === 0) {
    return { line: '', area: '', last: [0, h] };
  }
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

export type KpiIcon = 'authority' | 'traffic' | 'keywords' | 'backlinks' | 'social';

export type Kpi = {
  key: string;
  label: string;
  /** numeric magnitude used for the count-up animation. */
  value: number;
  /** suffix appended after the animated number (e.g. "K", "M"). */
  suffix?: string;
  decimals?: number;
  /** Percent change — only set when a real time series backs it. */
  delta?: number;
  up?: boolean;
  color: string;
  iconBg: string;
  icon: KpiIcon;
  /** Historical series for the sparkline — only set when real history exists. */
  data?: number[];
};

export type TrendPoint = { label: string; value: number };

export type PipelineStage = {
  stage: string;
  display: string;
  count: number;
  totalValue: number;
  probability: number;
};

export type DonutSlice = { label: string; pct: number; color: string };

export type Difficulty = 'Low' | 'Medium' | 'High';

export const DIFFICULTY_STYLE: Record<Difficulty, { bg: string; color: string }> = {
  Low: { bg: '#e7f8f1', color: '#059669' },
  Medium: { bg: '#fef3e0', color: '#b45309' },
  High: { bg: '#fdecec', color: '#dc2626' },
};

export function difficultyFromScore(score: number): Difficulty {
  if (score < 34) return 'Low';
  if (score < 67) return 'Medium';
  return 'High';
}

export type KeywordRow = {
  keyword: string;
  position: number;
  volume: number;
  difficulty: Difficulty;
  cpc: number;
};

export type SocialPlatform = { name: string; posts: number; pct: number; color: string };

export type FunnelStage = { stage: string; value: string; pct: number; rate: string; color: string };

export type AiInsight = { tag: string; tagBg: string; tagColor: string; impact: string; text: string };
