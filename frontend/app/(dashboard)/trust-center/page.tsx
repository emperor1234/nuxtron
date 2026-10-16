"use client";

import { apiGet } from "@/app/lib/platform-api";
import { Badge, DataTable, EmptyState, Kpi, KpiGrid, Page, PageHeader, Section, type Column } from "../_ui/kit";
import { formatDateTime } from "../_ui/format";
import { ResourceView, useResource } from "../_ui/use-resource";

type Posture = { open_incidents: number; critical_open_incidents: number; active_approval_chains: number };
type Incident = { id?: number | string; title: string; severity?: string; resolved?: boolean; affected_module?: string; created_at?: string };

export default function TrustCenterPage() {
  const posture = useResource<Posture>((tenant) => apiGet<Posture>("/trust-center/posture", tenant), []);
  const incidents = useResource<Incident[]>(async (tenant) => (await apiGet<{ incidents: Incident[] }>("/trust-center/incidents", tenant)).incidents, []);
  const columns: Column<Incident>[] = [
    { key: "title", header: "Incident", strong: true, render: (row) => row.title },
    { key: "severity", header: "Severity", render: (row) => <Badge tone={row.severity === "critical" || row.severity === "high" ? "danger" : "neutral"}>{row.severity ?? "medium"}</Badge> },
    { key: "module", header: "Area", render: (row) => row.affected_module || "—" },
    { key: "state", header: "State", render: (row) => (row.resolved ? "Resolved" : "Open") },
    { key: "when", header: "Reported", render: (row) => formatDateTime(row.created_at) },
  ];
  return (
    <Page width="wide">
      <PageHeader title="Trust Center" subtitle="Incidents and approval chains recorded for your workspace." />
      <ResourceView resource={posture}>
        {(data) => (
          <KpiGrid>
            <Kpi label="Open incidents" value={data.open_incidents} />
            <Kpi label="Critical and open" value={data.critical_open_incidents} />
            <Kpi label="Approval chains" value={data.active_approval_chains} />
          </KpiGrid>
        )}
      </ResourceView>
      <Section title="Incidents">
        <ResourceView resource={incidents} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No incidents recorded" description="Incidents you log appear here." />}>
          {(rows) => <DataTable columns={columns} rows={rows} getKey={(row, index) => row.id ?? index} caption="Incidents" pageSize={15} />}
        </ResourceView>
      </Section>
    </Page>
  );
}
