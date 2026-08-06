import styles from '../dashboard.module.css';
import { SOCIAL, SOCIAL_DELTA } from '../_data/marketing-data';

export default function SocialEngagementCard() {
  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Social engagement</h3>
          <div className={styles.cardSub}>By platform · 30 days</div>
        </div>
        <span className={styles.deltaPill}>{SOCIAL_DELTA}</span>
      </div>

      <div className={styles.barList}>
        {SOCIAL.map((platform, index) => (
          <div key={platform.name}>
            <div className={styles.barHead}>
              <span className={styles.barName}>{platform.name}</span>
              <span className={`${styles.barValue} ${styles.tabular}`}>{platform.value}</span>
            </div>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{
                  width: `${platform.pct}%`,
                  background: platform.color,
                  animationDelay: `${index * 60}ms`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
