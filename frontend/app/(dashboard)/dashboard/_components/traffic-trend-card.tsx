'use client';

import { useMemo } from 'react';
import styles from '../dashboard.module.css';
import { buildSparkPath, type TrendPoint } from '../_data/marketing-data';

const CHART_W = 680;
const CHART_H = 220;
const GRID_LINES = [40, 93, 146, 199];
const BRAND = '#2563eb';

type TrafficTrendCardProps = {
  trend: TrendPoint[];
  deltaPct: number;
};

export default function TrafficTrendCard({ trend, deltaPct }: TrafficTrendCardProps) {
  const { line, area, last } = useMemo(
    () => buildSparkPath(trend.map((p) => p.value), CHART_W, CHART_H, 14),
    [trend]
  );
  const latestValue = trend.at(-1)?.value ?? 0;

  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Organic traffic trend</h3>
          <div className={styles.cardSub}>Estimated monthly organic visits, last 12 months</div>
        </div>
      </div>

      <div className={styles.trendValueRow}>
        <span className={`${styles.trendValue} ${styles.tabular}`}>{latestValue.toLocaleString('en-US')}</span>
        <span className={styles.trendDelta} style={{ color: deltaPct >= 0 ? 'var(--d-green)' : 'var(--d-red)' }}>
          {deltaPct >= 0 ? '▲' : '▼'} {Math.abs(deltaPct)}%
        </span>
        <span className={styles.trendNote}>vs previous month</span>
      </div>

      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        preserveAspectRatio="none"
        className={styles.trendChart}
        role="img"
        aria-label={`Organic traffic trend, ${deltaPct >= 0 ? 'up' : 'down'} ${Math.abs(deltaPct)}% versus the previous month`}
      >
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={BRAND} stopOpacity="0.28" />
            <stop offset="100%" stopColor={BRAND} stopOpacity="0" />
          </linearGradient>
        </defs>
        {GRID_LINES.map((y) => (
          <line key={y} x1="0" y1={y} x2={CHART_W} y2={y} stroke="#eef0f4" strokeWidth="1" />
        ))}
        {area ? <path d={area} fill="url(#trendFill)" /> : null}
        {line ? (
          <path d={line} fill="none" stroke={BRAND} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        ) : null}
        <circle className={styles.trendDot} cx={last[0]} cy={last[1]} r="5" fill={BRAND} stroke="#fff" strokeWidth="2.5" />
      </svg>

      <div className={styles.trendMonths}>
        {trend.map((p) => (
          <span key={p.label}>{p.label}</span>
        ))}
      </div>
    </div>
  );
}
