"use client";

import { useState } from "react";
import { apiGet } from "@/app/lib/platform-api";
import { Callout, DataTable, EmptyState, Kpi, KpiGrid, Page, PageHeader, Section, Tabs, type Column } from "../../_ui/kit";
import { formatNumber } from "../../_ui/format";
import { ResourceView, useResource } from "../../_ui/use-resource";

type Dashboard = {
  period_days: number;
  total_requests: number;
  unique_bots: number;
  total_crawled_pages: number;
  requests_by_bot: Array<{ bot: string; count: number }>;
  avg_response_time_ms: number;
  total_bandwidth_gb: number;
  top_pages: string[];
  status_codes: Array<{ code: number; count: number }>;
};

const RANGES = [{ id: "7", label: "7 days" }, { id: "30", label: "30 days" }, { id: "90", label: "90 days" }];

export default function AgentAnalyticsPage() {
  const [days, setDays] = useState("7");
  const resource = useResource<Dashboard>((tenant) => apiGet<Dashboard>(`/api/v1/agent-analytics/dashboard?days=${days}`, tenant), [days]);

  const bots: Column<{ bot: string; count: number }>[] = [
    { key: "bot", header: "AI crawler", strong: true, render: (row) => row.bot, sortValue: (row) => row.bot },
    { key: "count", header: "Requests", numeric: true, render: (row) => formatNumber(row.count), sortValue: (row) => row.count },
  ];
  const codes: Column<{ code: number; count: number }>[] = [
    { key: "code", header: "Status", strong: true, render: (row) => row.code, sortValue: (row) => row.code },
    { key: "count", header: "Requests", numeric: true, render: (row) => formatNumber(row.count), sortValue: (row) => row.count },
  ];

  return (
    <Page width="wide">
      <PageHeader
        title="AI Crawler Analytics"
        subtitle="Which AI bots read your site, and what they ask for. Data comes from the crawl events your server sends to Nuxtron."
        tabs={<Tabs items={RANGES} value={days} onChange={setDays} label="Period" />}
      />
      <ResourceView resource={resource} isEmpty={(data) => data.total_requests === 0} empty={
        <EmptyState title="No crawler events received" description="Send crawl events from your web server or CDN logs to the AI crawler log endpoint. Results appear here as soon as the first event arrives." />
      }>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Requests" value={formatNumber(data.total_requests)} />
              <Kpi label="Distinct AI bots" value={formatNumber(data.unique_bots)} />
              <Kpi label="Pages crawled" value={formatNumber(data.total_crawled_pages)} />
              <Kpi label="Avg response" value={`${Math.round(data.avg_response_time_ms)} ms`} />
            </KpiGrid>
            <Section title="Requests by bot"><DataTable columns={bots} rows={data.requests_by_bot} getKey={(row) => row.bot} caption="Requests by AI crawler" pageSize={15} /></Section>
            <Section title="Response codes"><DataTable columns={codes} rows={data.status_codes} getKey={(row) => row.code} caption="Response codes" /></Section>
            {data.top_pages.length ? (
              <Section title="Most requested pages">
                <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 14 }}>{data.top_pages.map((page) => <li key={page}><code>{page}</code></li>)}</ul>
              </Section>
            ) : null}
          </>
        )}
      </ResourceView>
      <Callout tone="info">Only requests your server reports are counted. Nuxtron does not infer crawler visits.</Callout>
    </Page>
  );
}
