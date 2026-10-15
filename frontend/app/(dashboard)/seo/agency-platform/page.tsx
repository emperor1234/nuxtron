import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './agency-platform.module.css';

const REQUIRED_EVIDENCE = [
  'An authorized workspace inventory and membership scope',
  'Verified role assignments and policy records',
  'Auditable activity, ownership, and service-level observations',
];

export default function AgencyPlatformPage() {
  return (
    <Page>
      <PageHeader
        title="Agency Workspace Health"
        subtitle="A verified overview of agency workspace governance is not available in this customer dashboard yet."
      />

      <Card className={styles.unavailableCard}>
        <div className={styles.headingRow}>
          <CardTitle sub="No workspace names, health percentages, or risk findings are generated from sample inputs.">
            Workspace evidence is not connected
          </CardTitle>
          <Badge tone="neutral">Unavailable</Badge>
        </div>
        <p className={styles.explanation} role="status">
          This view cannot currently verify an agency’s workspace inventory, member access, policies, audit trail, owners, or service levels. It therefore shows no governance or workspace-health scores.
        </p>
      </Card>

      <section className={styles.requirements} aria-labelledby="agency-evidence-title">
        <Card>
          <CardTitle sub="A reliable report requires data linked to the signed-in workspace, not a manually typed list.">
            <span id="agency-evidence-title">Evidence required before this report can be enabled</span>
          </CardTitle>
          <ul className={styles.evidenceList}>
            {REQUIRED_EVIDENCE.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </Card>
        <p className={styles.boundaryNote}>
          Workspace administration and staff controls belong to a separate service; this customer page does not expose admin tools.
        </p>
      </section>
    </Page>
  );
}
