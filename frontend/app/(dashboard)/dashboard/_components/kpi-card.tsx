import styles from '../dashboard.module.css';
import type { Kpi } from '../_data/marketing-data';
import { KPI_ICONS } from './icons';
import NumberTicker from './number-ticker';
import Sparkline from './sparkline';

export default function KpiCard({ kpi }: { kpi: Kpi }) {
  const Icon = KPI_ICONS[kpi.icon];
  const deltaColor = kpi.up ? 'var(--d-green)' : 'var(--d-red)';

  return (
    <article className={`${styles.card} ${styles.kpiCard}`}>
      <div className={styles.kpiTop}>
        <div className={styles.kpiLabelWrap}>
          <span className={styles.kpiIcon} style={{ background: kpi.iconBg, color: kpi.color }}>
            <Icon size={16} />
          </span>
          <span className={styles.kpiLabel}>{kpi.label}</span>
        </div>
        {kpi.delta !== undefined ? (
          <span className={styles.kpiDelta} style={{ color: deltaColor }}>
            {kpi.up ? '▲' : '▼'}
            {kpi.delta}%
          </span>
        ) : null}
      </div>
      <div className={`${styles.kpiValue} ${styles.tabular}`}>
        <NumberTicker value={kpi.value} suffix={kpi.suffix} decimals={kpi.decimals ?? 0} />
      </div>
      {kpi.data && kpi.data.length > 1 ? (
        <Sparkline values={kpi.data} color={kpi.color} className={styles.kpiSpark} gradientId={`spark-${kpi.key}`} />
      ) : null}
    </article>
  );
}
