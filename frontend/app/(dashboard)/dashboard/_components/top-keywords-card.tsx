import styles from '../dashboard.module.css';
import { INTENT_STYLE, KEYWORDS } from '../_data/marketing-data';

const CHANGE_COLOR: Record<'up' | 'down' | 'flat', string> = {
  up: 'var(--d-green)',
  down: 'var(--d-red)',
  flat: 'var(--d-faint)',
};

export default function TopKeywordsCard() {
  return (
    <div className={`${styles.card} ${styles.tableCard}`}>
      <div className={styles.tableHeadRow}>
        <div>
          <h3 className={styles.cardTitle}>Top ranking keywords</h3>
          <div className={styles.cardSub}>Tracked positions this week</div>
        </div>
        <button type="button" className={styles.viewAll}>
          View all →
        </button>
      </div>

      <div className={`${styles.kwGrid} ${styles.kwColHead}`} role="row">
        <span role="columnheader">Keyword</span>
        <span role="columnheader" className={styles.alignCenter}>
          Pos.
        </span>
        <span role="columnheader" className={styles.alignRight}>
          Volume
        </span>
        <span role="columnheader" className={styles.alignRight}>
          Intent
        </span>
      </div>

      {KEYWORDS.map((row) => {
        const intent = INTENT_STYLE[row.intent];
        return (
          <div key={row.keyword} className={`${styles.kwGrid} ${styles.kwRow}`} role="row">
            <span className={styles.kwName}>{row.keyword}</span>
            <div className={styles.kwPosCell}>
              <span className={`${styles.kwPos} ${styles.tabular}`}>{row.position}</span>
              <span className={styles.kwChange} style={{ color: CHANGE_COLOR[row.trend] }}>
                {row.change}
              </span>
            </div>
            <span className={`${styles.kwVol} ${styles.tabular}`}>{row.volume}</span>
            <div className={styles.kwIntentCell}>
              <span className={styles.kwIntent} style={{ background: intent.bg, color: intent.color }}>
                {row.intent}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
