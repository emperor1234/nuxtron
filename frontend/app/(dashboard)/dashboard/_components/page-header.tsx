import styles from '../dashboard.module.css';
import { DownloadIcon, SlidersIcon } from './icons';

type PageHeaderProps = {
  title: string;
  domain: string;
  scope: string;
  updatedLabel: string;
};

export default function PageHeader({ title, domain, scope, updatedLabel }: PageHeaderProps) {
  return (
    <header className={styles.pageHeader}>
      <div>
        <div className={styles.pageTitleRow}>
          <h1 className={styles.pageTitle}>{title}</h1>
          <span className={styles.livePill}>
            <span className={styles.liveDot} aria-hidden="true" />
            Live
          </span>
        </div>
        <div className={styles.pageMeta}>
          <span className={styles.pageMetaSwatch} aria-hidden="true" />
          <span className={styles.pageMetaStrong}>{domain}</span>
          <span className={styles.pageMetaDivider} aria-hidden="true">
            •
          </span>
          <span>{scope}</span>
          <span className={styles.pageMetaDivider} aria-hidden="true">
            •
          </span>
          <span>{updatedLabel}</span>
        </div>
      </div>
      <div className={styles.headerActions}>
        <button type="button" className={`${styles.btn} ${styles.btnGhost}`}>
          <DownloadIcon size={15} style={{ color: '#5b6478' }} />
          Export
        </button>
        <button type="button" className={`${styles.btn} ${styles.btnGhost}`}>
          <SlidersIcon size={15} style={{ color: '#5b6478' }} />
          Customize
        </button>
      </div>
    </header>
  );
}
