import styles from '../dashboard.module.css';
import { buildDonutSegments, TRAFFIC_SOURCES, TRAFFIC_SOURCES_TOTAL } from '../_data/marketing-data';

export default function TrafficSourcesDonut() {
  const segments = buildDonutSegments(TRAFFIC_SOURCES);

  return (
    <div className={`${styles.card} ${styles.cardPad} ${styles.donutCard}`}>
      <h3 className={styles.cardTitle}>Traffic sources</h3>
      <div className={styles.cardSub} style={{ marginBottom: 14 }}>
        Channel distribution
      </div>

      <div className={styles.donutWrap}>
        <svg width="172" height="172" viewBox="0 0 180 180" role="img" aria-label="Traffic sources by channel">
          <g transform="rotate(-90 90 90)">
            {segments.map((s) => (
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
          <text x="90" y="84" textAnchor="middle" style={{ fontFamily: 'var(--d-font-display)', fontSize: 28, fontWeight: 700, fill: '#0e1525' }}>
            {TRAFFIC_SOURCES_TOTAL}
          </text>
          <text x="90" y="104" textAnchor="middle" style={{ fontSize: 12, fontWeight: 600, fill: '#9aa1b2' }}>
            total visits
          </text>
        </svg>
      </div>

      <ul className={styles.donutLegend}>
        {segments.map((s) => (
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
