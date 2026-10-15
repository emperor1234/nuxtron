import Link from 'next/link';
import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './technical.module.css';

const requirements = [
  'A crawl that records the actual pages and response outcomes it discovers.',
  'Page-level issue evidence, including affected URL samples and counts.',
  'Measured Core Web Vitals from a configured field or lab data provider.',
  'A run timestamp and source for every reported measurement.',
];

export default function TechnicalSEOPage() {
  return (
    <Page>
      <PageHeader
        title="Technical SEO Audit"
        subtitle="Crawlability, indexability, and measured page-health findings."
      />

      <Card className={styles.statusCard}>
        <div className={styles.statusHeader}>
          <Badge tone="danger">Unavailable</Badge>
          <span className={styles.statusText}>No verified crawl data is available</span>
        </div>
        <CardTitle sub="We’ve paused this workflow rather than present generated estimates as a site audit.">
          A verified crawler is not connected
        </CardTitle>
        <p className={styles.copy}>
          The current service does not crawl the submitted website or measure its Core Web Vitals. Its former scores and findings were generated from heuristic or model output, not observed site evidence, so the audit action is disabled until a real crawler and measurement source are integrated.
        </p>
        <div className={styles.requirements}>
          <h3>What a report must include before it is enabled</h3>
          <ul>
            {requirements.map((requirement) => <li key={requirement}>{requirement}</li>)}
          </ul>
        </div>
        <div className={styles.actions}>
          <Link className={`${styles.actionLink} ${styles.secondaryLink}`} href="/seo/security">Open Security &amp; SEO Health</Link>
        </div>
      </Card>
    </Page>
  );
}
