import styles from '../dashboard.module.css';
import type { FunnelStage } from '../_data/marketing-data';

export default function ConversionFunnelCard({ funnel }: { funnel: FunnelStage[] }) {
  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Deal funnel</h3>
          <div className={styles.cardSub}>CRM pipeline, prospect to closed-won</div>
        </div>
      </div>

      {funnel.length === 0 ? (
        <p className="muted">No deals in the pipeline yet.</p>
      ) : (
        <div className={styles.funnelList}>
          {funnel.map((stage, index) => (
            <div key={stage.stage} className={styles.funnelRow}>
              <span className={styles.funnelStage}>{stage.stage}</span>
              <div className={styles.funnelTrack}>
                <div
                  className={styles.funnelFill}
                  style={{ width: `${stage.pct}%`, background: stage.color, animationDelay: `${index * 70}ms` }}
                >
                  <span className={`${styles.funnelValue} ${styles.tabular}`}>{stage.value}</span>
                </div>
              </div>
              <span className={`${styles.funnelRate} ${styles.tabular}`}>{stage.rate}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
