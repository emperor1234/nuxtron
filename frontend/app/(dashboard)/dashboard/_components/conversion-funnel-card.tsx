import styles from '../dashboard.module.css';
import { FUNNEL, FUNNEL_SUMMARY } from '../_data/marketing-data';

export default function ConversionFunnelCard() {
  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Conversion funnel</h3>
          <div className={styles.cardSub}>From impression to customer</div>
        </div>
        <span className={styles.funnelChip}>{FUNNEL_SUMMARY}</span>
      </div>

      <div className={styles.funnelList}>
        {FUNNEL.map((stage, index) => (
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
    </div>
  );
}
