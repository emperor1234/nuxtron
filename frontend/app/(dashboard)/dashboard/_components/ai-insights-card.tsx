import styles from '../dashboard.module.css';
import type { AiInsight } from '../_data/marketing-data';
import { SparkleIcon } from './icons';

export default function AiInsightsCard({ insights }: { insights: AiInsight[] }) {
  return (
    <div className={styles.aiCard}>
      <div className={styles.aiHead}>
        <span className={styles.aiIcon} style={{ color: '#fff' }}>
          <SparkleIcon size={16} />
        </span>
        <h3 className={styles.aiTitle}>Marketing insights</h3>
        <span className={styles.aiBadge}>{insights.length} live</span>
      </div>

      <div className={styles.aiList}>
        {insights.length === 0 ? (
          <p className={styles.aiText}>Not enough live data yet to generate insights.</p>
        ) : (
          insights.map((insight) => (
            <div key={insight.tag} className={styles.aiItem}>
              <div className={styles.aiItemTop}>
                <span className={styles.aiTag} style={{ background: insight.tagBg, color: insight.tagColor }}>
                  {insight.tag}
                </span>
                <span className={styles.aiImpact}>{insight.impact}</span>
              </div>
              <p className={styles.aiText}>{insight.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
