'use client';

import { useMemo, useState } from 'react';
import styles from '../dashboard.module.css';
import {
  buildSparkPath,
  MONTHS,
  TREND_SERIES,
  TREND_SUMMARY,
  TREND_TABS,
  type TrendMetric,
} from '../_data/marketing-data';

const CHART_W = 680;
const CHART_H = 220;
const GRID_LINES = [40, 93, 146, 199];

export default function TrafficTrendCard() {
  const [metric, setMetric] = useState<TrendMetric>('traffic');

  const { line, area, last } = useMemo(
    () => buildSparkPath(TREND_SERIES[metric], CHART_W, CHART_H, 14),
    [metric]
  );
  const summary = TREND_SUMMARY[metric];

  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Organic traffic trend</h3>
          <div className={styles.cardSub}>Estimated visits from search over 12 months</div>
        </div>
        <div className={styles.trendTabs} role="tablist" aria-label="Trend metric">
          {TREND_TABS.map((tab) => {
            const active = metric === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                className={`${styles.trendTab} ${active ? styles.trendTabActive : ''}`}
                onClick={() => setMetric(tab.id)}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className={styles.trendValueRow}>
        <span className={`${styles.trendValue} ${styles.tabular}`}>{summary.value}</span>
        <span className={styles.trendDelta}>▲ {summary.delta}</span>
        <span className={styles.trendNote}>vs previous period</span>
      </div>

      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        preserveAspectRatio="none"
        className={styles.trendChart}
        role="img"
        aria-label={`${summary.label} trend, up ${summary.delta} versus the previous period`}
      >
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6d5efc" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#6d5efc" stopOpacity="0" />
          </linearGradient>
        </defs>
        {GRID_LINES.map((y) => (
          <line key={y} x1="0" y1={y} x2={CHART_W} y2={y} stroke="#eef0f4" strokeWidth="1" />
        ))}
        <path d={area} fill="url(#trendFill)" />
        <path d={line} fill="none" stroke="#6d5efc" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle className={styles.trendDot} cx={last[0]} cy={last[1]} r="5" fill="#6d5efc" stroke="#fff" strokeWidth="2.5" />
      </svg>

      <div className={styles.trendMonths}>
        {MONTHS.map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>
    </div>
  );
}
