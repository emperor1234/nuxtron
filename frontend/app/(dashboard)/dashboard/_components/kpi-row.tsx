import styles from '../dashboard.module.css';
import { KPIS } from '../_data/marketing-data';
import KpiCard from './kpi-card';

export default function KpiRow() {
  return (
    <section className={styles.kpiRow} aria-label="Key performance indicators">
      {KPIS.map((kpi) => (
        <KpiCard key={kpi.key} kpi={kpi} />
      ))}
    </section>
  );
}
