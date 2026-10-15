import Link from 'next/link';
import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './competitor-monitoring.module.css';

const REQUIRED_CAPABILITIES = [
  'Durable, tenant-scoped storage for monitored domains and their history',
  'An authorized competitor-data source with documented coverage and freshness',
  'A scheduled collection service that records each observation and its source',
  'Reliable alert delivery with customer-controlled destinations and thresholds',
];

export default function CompetitorActivityMonitorPage() {
  return (
    <Page>
      <PageHeader
        title="Competitor Activity Monitor"
        subtitle="Track verified changes only when a real source and collection history are connected."
      />

      <Card className={styles.unavailableCard}>
        <div className={styles.headingRow}>
          <CardTitle sub="No monitored-domain list, activity timeline, or alert state is reported from temporary memory or sample events.">
            Monitoring sources are not connected
          </CardTitle>
          <Badge tone="neutral">Unavailable</Badge>
        </div>
        <p className={styles.explanation} role="status">
          This workspace does not yet have durable monitor storage, an authorized competitor-data source, or scheduled collection. Adding domains, creating alerts, and displaying activity events are disabled; no sample events are shown.
        </p>
      </Card>

      <section className={styles.details} aria-labelledby="monitor-prerequisites-title">
        <Card>
          <CardTitle sub="Each event needs a traceable source, collection time, and workspace scope.">
            <span id="monitor-prerequisites-title">What is required before monitoring can be enabled</span>
          </CardTitle>
          <ul className={styles.requirements}>
            {REQUIRED_CAPABILITIES.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </Card>
        <p className={styles.manualNote}>
          For manually recorded competitor observations, use{' '}
          <Link href="/competitive-benchmarking">Competitive Benchmarking</Link>. It is not an automated monitor and does not provide search or ad measurements.
        </p>
      </section>
    </Page>
  );
}
