import Link from 'next/link';
import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './content-auditor.module.css';

const evidenceRequirements = [
  'Retrieve and retain traceable primary sources for each factual claim.',
  'Show claim-level quotations, source URLs, and publication dates.',
  'Separate editorial risk signals from verified or contradicted facts.',
  'Anchor every report to its input, run time, and analysis method.',
];

export default function ContentAuditorPage() {
  return (
    <Page>
      <PageHeader
        title="Content Review"
        subtitle="Evidence-backed factuality and citation review for editorial teams."
      />

      <Card className={styles.statusCard}>
        <div className={styles.statusHeader}>
          <Badge tone="danger">Unavailable</Badge>
          <span className={styles.statusText}>No verifiable source pipeline is configured</span>
        </div>
        <CardTitle sub="We’ve paused this workflow rather than label generated estimates as verified facts.">
          Claim-level evidence is not available
        </CardTitle>
        <p className={styles.copy}>
          The current service does not fetch the submitted URL or retrieve primary sources for individual claims. Its former “verified” labels, confidence values, quality scores, and E-E-A-T values were model or heuristic outputs without traceable evidence. New reviews are disabled until each finding can be tied to a source a human can inspect.
        </p>
        <div className={styles.requirements}>
          <h3>What a review must include before it is enabled</h3>
          <ul>
            {evidenceRequirements.map((requirement) => <li key={requirement}>{requirement}</li>)}
          </ul>
        </div>
        <div className={styles.actions}>
          <Link className={`${styles.actionLink} ${styles.primaryLink}`} href="/content-generation">Open Content Generator</Link>
          <Link className={`${styles.actionLink} ${styles.secondaryLink}`} href="/seo">Return to SEO Overview</Link>
        </div>
      </Card>
    </Page>
  );
}
