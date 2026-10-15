import Link from 'next/link';
import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './competitor.module.css';

const REQUIRED_EVIDENCE = [
  'Authorized SERP snapshots with location, device, query, and collection date',
  'Verified keyword, traffic, and backlink datasets from connected sources',
  'Sampled AI-answer observations with prompt, model, market, and timestamp',
];

export default function CompetitorPage() {
  return (
    <Page>
      <PageHeader
        title="SEO Competitor Research"
        subtitle="A reliable search competitor comparison needs traceable observations—not generated estimates."
      />

      <Card className={styles.unavailableCard}>
        <div className={styles.headingRow}>
          <CardTitle sub="This route does not estimate positions, traffic, authority, keyword opportunity, content gaps, or AI-answer visibility.">
            Verified search evidence is not connected
          </CardTitle>
          <Badge tone="neutral">Unavailable</Badge>
        </div>
        <p className={styles.explanation} role="status">
          No authorized SERP or competitor-data source is configured for this workspace. No competitor rankings or scores are generated from typed domain names or notes.
        </p>
      </Card>

      <section className={styles.details} aria-labelledby="competitor-evidence-title">
        <Card>
          <CardTitle sub="Reports can be enabled only when every displayed metric can be traced to its source and collection time.">
            <span id="competitor-evidence-title">Evidence required</span>
          </CardTitle>
          <ul className={styles.evidenceList}>
            {REQUIRED_EVIDENCE.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </Card>
        <p className={styles.manualNote}>
          For manually recorded competitor observations, visit{' '}
          <Link href="/competitive-benchmarking">Competitive Benchmarking</Link>. That workspace does not provide SERP positions or traffic measurements.
        </p>
      </section>
    </Page>
  );
}
