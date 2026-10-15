import Link from 'next/link';
import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './accessibility.module.css';

const evidenceRequirements = [
  'A rendered page DOM captured at the requested URL, including client-side content.',
  'Rule-based WCAG checks with criterion IDs and reproducible scanner versions.',
  'Affected elements and enough page context for a human to verify each finding.',
  'A clear run time, browser context, and coverage limits for the report.',
];

export default function AccessibilityOptimizerPage() {
  return (
    <Page>
      <PageHeader
        title="Accessibility Audit"
        subtitle="Evidence-based WCAG checks for rendered pages."
      />

      <Card className={styles.statusCard}>
        <div className={styles.statusHeader}>
          <Badge tone="danger">Unavailable</Badge>
          <span className={styles.statusText}>No rendered-page scanner is configured</span>
        </div>
        <CardTitle sub="We’ve paused this workflow rather than report model-generated estimates as measured accessibility findings.">
          A verified accessibility scanner is not connected
        </CardTitle>
        <p className={styles.copy}>
          The current service does not load the submitted page, inspect its rendered DOM, or run an accessibility rule engine. Its former compliance, readability, and assistive-technology scores were generated estimates, not WCAG test results, so new reports are disabled until page-specific evidence is available.
        </p>
        <div className={styles.requirements}>
          <h3>What a report must include before it is enabled</h3>
          <ul>
            {evidenceRequirements.map((requirement) => <li key={requirement}>{requirement}</li>)}
          </ul>
        </div>
        <div className={styles.actions}>
          <Link className={`${styles.actionLink} ${styles.primaryLink}`} href="/seo">Return to SEO Overview</Link>
        </div>
      </Card>
    </Page>
  );
}
