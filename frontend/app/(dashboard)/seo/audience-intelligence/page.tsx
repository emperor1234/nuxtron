import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './audience-intelligence.module.css';

export default function AudienceIntelligencePage() {
  return (
    <Page>
      <PageHeader
        title="Audience Intelligence"
        subtitle="Provider-backed audience insights require a verified data connection for this workspace."
      />
      <Card>
        <Badge tone="neutral">Audience source not connected</Badge>
        <CardTitle sub="Audience demographics, interests, and ad-targeting estimates are unavailable until a permitted provider is configured.">
          No verified audience data yet
        </CardTitle>
        <p className={styles.explanation}>
          This page will not infer a customer profile from a domain name. Synthetic audience distributions and estimated reach are disabled, so unavailable data is not presented as a measured result.
        </p>
        <ul className={styles.scopeList}>
          <li>Demographics and interests: not available</li>
          <li>Behavior and audience-size estimates: not available</li>
          <li>Ad-targeting suggestions: not available</li>
        </ul>
        <p className={styles.availabilityNote}>Workspace-specific audience provider setup is not available in this dashboard yet.</p>
      </Card>
    </Page>
  );
}
