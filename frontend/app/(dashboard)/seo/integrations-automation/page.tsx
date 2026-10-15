import { Badge, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './integrations-automation.module.css';

export default function IntegrationsAutomationPage() {
  return (
    <Page>
      <PageHeader
        title="Integrations & Automation Layer"
        subtitle="Connector status and workflow health require verified, workspace-scoped integration data."
      />
      <Card>
        <Badge tone="neutral">Connector data unavailable</Badge>
        <CardTitle sub="This workspace does not have a connected integration inventory and health-check service.">
          No verified connector inventory
        </CardTitle>
        <p className={styles.explanation}>
          A domain name and a list of system names cannot verify which connectors are connected, measure their uptime or latency, or identify actual automation gaps. Coverage scores, connector-health results, and generated backlog items are disabled until those facts can be read from authorized workspace integrations.
        </p>
        <ul className={styles.scopeList}>
          <li>Connected systems and permissions: unavailable</li>
          <li>Connector health and event-flow evidence: unavailable</li>
          <li>Measured automation coverage and prioritized backlog: unavailable</li>
        </ul>
      </Card>
    </Page>
  );
}
