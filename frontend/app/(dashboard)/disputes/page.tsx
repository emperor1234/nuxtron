"use client";

import { apiGet } from "@/app/lib/platform-api";
import { Badge, Callout, DataTable, EmptyState, Kpi, KpiGrid, Page, PageHeader, Section, type Column } from "../_ui/kit";
import { formatDateTime, formatNumber } from "../_ui/format";
import { ResourceView, useResource } from "../_ui/use-resource";

type Ticket = { id?: string | number; ticket_id?: string; status?: string; reason?: string; customer?: string; created_at?: string; summary?: string };
type Dashboard = {
  summary: { total_dispute_events: number; total_dispute_tickets: number; open_dispute_tickets: number; queued_for_human_validation: number };
  tickets: Ticket[];
  reputation_guardrail?: string;
};

export default function DisputesPage() {
  const resource = useResource<Dashboard>((tenant) => apiGet<Dashboard>("/ira/disputes/dashboard", tenant), []);
  const columns: Column<Ticket>[] = [
    { key: "id", header: "Ticket", strong: true, render: (row) => String(row.ticket_id ?? row.id ?? "—") },
    { key: "reason", header: "Reason", render: (row) => row.reason || row.summary || "—" },
    { key: "status", header: "Status", render: (row) => <Badge>{row.status ?? "open"}</Badge> },
    { key: "when", header: "Opened", render: (row) => formatDateTime(row.created_at), sortValue: (row) => row.created_at ?? "" },
  ];
  return (
    <Page width="wide">
      <PageHeader title="Disputes" subtitle="Customer disputes raised against your workspace. A person approves every outcome." />
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Open tickets" value={formatNumber(data.summary.open_dispute_tickets)} />
              <Kpi label="Waiting for a person" value={formatNumber(data.summary.queued_for_human_validation)} />
              <Kpi label="All tickets" value={formatNumber(data.summary.total_dispute_tickets)} />
              <Kpi label="Dispute events" value={formatNumber(data.summary.total_dispute_events)} />
            </KpiGrid>
            <Section title="Tickets">
              {data.tickets.length ? <DataTable columns={columns} rows={data.tickets} getKey={(row, index) => String(row.ticket_id ?? row.id ?? index)} caption="Dispute tickets" pageSize={15} /> : <EmptyState title="No disputes" description="Disputes appear here when a payment or service dispute is reported to Nuxtron." />}
            </Section>
            {data.reputation_guardrail ? <Callout tone="info" title="Handling guidance">{data.reputation_guardrail}</Callout> : null}
          </>
        )}
      </ResourceView>
    </Page>
  );
}
