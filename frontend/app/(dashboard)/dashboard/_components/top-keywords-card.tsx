import styles from '../dashboard.module.css';
import { DIFFICULTY_STYLE, type KeywordRow } from '../_data/marketing-data';

export default function TopKeywordsCard({ keywords }: { keywords: KeywordRow[] }) {
  return (
    <div className={`${styles.card} ${styles.tableCard}`}>
      <div className={styles.tableHeadRow}>
        <div>
          <h3 className={styles.cardTitle}>Top ranking keywords</h3>
          <div className={styles.cardSub}>Tracked organic positions</div>
        </div>
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
          CPC
        </span>
        <span role="columnheader" className={styles.alignRight}>
          Difficulty
        </span>
      </div>

      {keywords.length === 0 ? (
        <p className="muted" style={{ padding: '16px 22px' }}>
          No tracked keywords yet.
        </p>
      ) : (
        keywords.map((row) => {
          const diff = DIFFICULTY_STYLE[row.difficulty];
          return (
            <div key={row.keyword} className={`${styles.kwGrid} ${styles.kwRow}`} role="row">
              <span className={styles.kwName}>{row.keyword}</span>
              <div className={styles.kwPosCell}>
                <span className={`${styles.kwPos} ${styles.tabular}`}>{row.position}</span>
              </div>
              <span className={`${styles.kwVol} ${styles.tabular}`}>{row.volume.toLocaleString('en-US')}</span>
              <span className={`${styles.kwVol} ${styles.tabular}`}>${row.cpc.toFixed(2)}</span>
              <div className={styles.kwIntentCell}>
                <span className={styles.kwIntent} style={{ background: diff.bg, color: diff.color }}>
                  {row.difficulty}
                </span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
