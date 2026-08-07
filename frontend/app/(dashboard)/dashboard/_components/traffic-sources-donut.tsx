import styles from '../dashboard.module.css';
import { buildDonutSegments, type DonutSlice } from '../_data/marketing-data';

type PipelineDonutProps = {
  segments: DonutSlice[];
  totalValue: number;
};

export default function PipelineDonut({ segments, totalValue }: PipelineDonutProps) {
  const donut = buildDonutSegments(segments);
  const totalLabel =
    totalValue >= 1_000_000
      ? `$${(totalValue / 1_000_000).toFixed(1)}M`
      : totalValue >= 1_000
        ? `$${(totalValue / 1_000).toFixed(1)}K`
        : `$${Math.round(totalValue)}`;

  return (
    <div className={`${styles.card} ${styles.cardPad} ${styles.donutCard}`}>
      <h3 className={styles.cardTitle}>Deal pipeline by stage</h3>
      <div className={styles.cardSub} style={{ marginBottom: 14 }}>
        Open CRM deals, by stage
      </div>

      <div className={styles.donutWrap}>
        {donut.length === 0 ? (
          <p className="muted">No open deals yet.</p>
        ) : (
          <svg width="172" height="172" viewBox="0 0 180 180" role="img" aria-label="Deal pipeline by stage">
            <g transform="rotate(-90 90 90)">
              {donut.map((s) => (
                <circle
                  key={s.label}
                  cx="90"
                  cy="90"
                  r="64"
                  fill="none"
                  stroke={s.color}
                  strokeWidth="22"
                  strokeDasharray={s.dash}
                  strokeDashoffset={s.offset}
                  strokeLinecap="butt"
                />
              ))}
            </g>
            <text x="90" y="84" textAnchor="middle" style={{ fontFamily: 'var(--d-font-display)', fontSize: 24, fontWeight: 700, fill: '#0e1525' }}>
              {totalLabel}
            </text>
            <text x="90" y="104" textAnchor="middle" style={{ fontSize: 12, fontWeight: 600, fill: '#9aa1b2' }}>
              open value
            </text>
          </svg>
        )}
      </div>

      <ul className={styles.donutLegend}>
        {donut.map((s) => (
          <li key={s.label} className={styles.legendItem}>
            <span className={styles.legendSwatch} style={{ background: s.color }} aria-hidden="true" />
            <span className={styles.legendLabel}>{s.label}</span>
            <span className={`${styles.legendValue} ${styles.tabular}`}>{s.pct}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
