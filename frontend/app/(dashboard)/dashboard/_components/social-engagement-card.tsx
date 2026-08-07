import styles from '../dashboard.module.css';
import type { SocialPlatform } from '../_data/marketing-data';

export default function SocialEngagementCard({ platforms }: { platforms: SocialPlatform[] }) {
  const totalPosts = platforms.reduce((sum, p) => sum + p.posts, 0);

  return (
    <div className={`${styles.card} ${styles.cardPad}`}>
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.cardTitle}>Social publishing</h3>
          <div className={styles.cardSub}>Posts by platform · 30 days</div>
        </div>
        <span className={styles.deltaPill}>{totalPosts} total</span>
      </div>

      <div className={styles.barList}>
        {platforms.map((platform, index) => (
          <div key={platform.name}>
            <div className={styles.barHead}>
              <span className={styles.barName}>{platform.name}</span>
              <span className={`${styles.barValue} ${styles.tabular}`}>{platform.posts}</span>
            </div>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{
                  width: `${Math.max(platform.pct, platform.posts > 0 ? 4 : 0)}%`,
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
