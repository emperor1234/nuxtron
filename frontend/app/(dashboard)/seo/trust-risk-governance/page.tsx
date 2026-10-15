import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './trust-risk-governance.module.css';

export default function TrustRiskGovernancePage() {
  return (
    <Page>
      <PageHeader
        title="Trust & Risk Governance"
        subtitle="Verified workspace evidence is required; no assessment is currently available."
      />
      <Card className={styles.card}>
        <div className={styles.statusRow} role="status">
          <Badge tone="neutral">Assessment unavailable</Badge>
          <span>Not a certification or attestation</span>
        </div>
        <CardTitle sub="Policy posture, control coverage, and incident findings must come from connected, auditable sources.">
          No evidence-backed assessment
        </CardTitle>
        <p className={styles.explanation}>
          A domain name, a list of control labels, or a manually entered incident count cannot verify a workspace’s actual configuration or history. Until verified policy inventories, control states, incident records, and audit evidence are connected and validated, Nuxtron does not produce governance scores, compliance percentages, risk ratings, or remediation recommendations.
        </p>
        <ul className={styles.evidenceList} aria-label="Evidence required for a governance assessment">
          <li><strong>Policy inventory</strong><span>Current policies and their authoritative owners</span></li>
          <li><strong>Control evidence</strong><span>Verified state and audit history for each applicable control</span></li>
          <li><strong>Incident records</strong><span>Scoped events with provenance and an explicit reporting window</span></li>
        </ul>
        <p className={styles.disclaimer}>
          This page does not collect domain, control, incident, or note inputs while the evidence service is unavailable.
        </p>
      </Card>
    </Page>
  );
}
