import styles from '../dashboard.module.css';
import type { Kpi } from '../_data/marketing-data';
import KpiCard from './kpi-card';

export default function KpiRow({ kpis }: { kpis: Kpi[] }) {
  return (
    <section className={styles.kpiRow} aria-label="Key performance indicators">
      {kpis.map((kpi) => (
        <KpiCard key={kpi.key} kpi={kpi} />
      ))}
    </section>
  );
}
