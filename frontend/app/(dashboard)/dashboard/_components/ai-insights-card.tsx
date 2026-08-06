import styles from '../dashboard.module.css';
import { AI_INSIGHTS } from '../_data/marketing-data';
import { SparkleIcon } from './icons';

export default function AiInsightsCard() {
  return (
    <div className={styles.aiCard}>
      <div className={styles.aiHead}>
        <span className={styles.aiIcon} style={{ color: '#fff' }}>
          <SparkleIcon size={16} />
        </span>
        <h3 className={styles.aiTitle}>AI marketing insights</h3>
        <span className={styles.aiBadge}>3 new</span>
      </div>

      <div className={styles.aiList}>
        {AI_INSIGHTS.map((insight) => (
          <div key={insight.tag} className={styles.aiItem}>
            <div className={styles.aiItemTop}>
              <span className={styles.aiTag} style={{ background: insight.tagBg, color: insight.tagColor }}>
                {insight.tag}
              </span>
              <span className={styles.aiImpact}>{insight.impact}</span>
            </div>
            <p className={styles.aiText}>{insight.text}</p>
          </div>
        ))}
      </div>

      <button type="button" className={styles.aiCta}>
        Generate content plan
      </button>
    </div>
  );
}
