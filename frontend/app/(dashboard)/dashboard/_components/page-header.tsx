import styles from '../dashboard.module.css';
import { DownloadIcon, SlidersIcon } from './icons';

type PageHeaderProps = {
  title: string;
  domain: string;
  scope: string;
  updatedLabel: string;
  sourceLabel?: string;
  onRefresh?: () => void;
  refreshing?: boolean;
  onExport?: () => void;
};

export default function PageHeader({ title, domain, scope, updatedLabel, sourceLabel, onRefresh, refreshing, onExport }: PageHeaderProps) {
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
          {sourceLabel ? (
            <>
              <span className={styles.pageMetaDivider} aria-hidden="true">
                •
              </span>
              <span>Source: {sourceLabel}</span>
            </>
          ) : null}
        </div>
      </div>
      <div className={styles.headerActions}>
        {onExport ? (
          <button type="button" className={`${styles.btn} ${styles.btnGhost}`} onClick={onExport}>
            <DownloadIcon size={15} style={{ color: '#5b6478' }} />
            Export
          </button>
        ) : null}
        {onRefresh ? (
          <button type="button" className={`${styles.btn} ${styles.btnGhost}`} onClick={onRefresh} disabled={refreshing}>
            <SlidersIcon size={15} style={{ color: '#5b6478' }} />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        ) : null}
      </div>
    </header>
  );
}
