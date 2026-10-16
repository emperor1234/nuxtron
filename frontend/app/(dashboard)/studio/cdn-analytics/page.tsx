"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, DataTable, EmptyState, Field, FieldSelect, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, Section, Tabs, type Column } from "../../_ui/kit";
import { formatNumber, formatPercent } from "../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../_ui/use-resource";

type ProviderMetrics = {
  provider?: string;
  total_requests?: number;
  bandwidth_gb?: number;
  cache_hit_ratio?: number;
  avg_latency_ms?: number;
  error_rate?: number;
  threat_count?: number;
};
type Dashboard = {
  period_days: number;
  providers: Record<string, ProviderMetrics>;
  costs: Record<string, number>;
  recommendations: Array<{ priority?: string; category?: string; recommendation?: string }>;
};

const PROVIDERS = ["cloudflare", "cloudfront", "fastly", "vercel", "netlify", "akamai", "google-cdn", "stackpath", "imperva"];
const RANGES = [{ id: "7", label: "7 days" }, { id: "30", label: "30 days" }, { id: "90", label: "90 days" }];

export default function CdnAnalyticsPage() {
  const tenant = useTenant();
  const [days, setDays] = useState("7");
  const [open, setOpen] = useState(false);
  const [provider, setProvider] = useState("cloudflare");
  const [apiKey, setApiKey] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const resource = useResource<Dashboard>((id) => apiGet<Dashboard>(`/api/v1/cdn/dashboard?days=${days}`, id), [days]);

  async function register(event: FormEvent) {
    event.preventDefault();
    if (!apiKey.trim()) return setError("Enter the API key for this provider.");
    setBusy(true);
    setError("");
    try {
      await apiSend("/api/v1/cdn/register", "POST", { provider, api_key: apiKey.trim(), api_token: apiToken.trim() || null }, tenant);
      setOpen(false);
      setApiKey("");
      setApiToken("");
      resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The provider could not be registered.");
    } finally {
      setBusy(false);
    }
  }

  const rows = (data: Dashboard) => Object.entries(data.providers).map(([name, metrics]) => ({ name, ...metrics, cost: data.costs?.[name] }));
  type Row = ReturnType<typeof rows>[number];
  const columns: Column<Row>[] = [
    { key: "name", header: "Provider", strong: true, render: (row) => row.name, sortValue: (row) => row.name },
    { key: "requests", header: "Requests", numeric: true, render: (row) => formatNumber(row.total_requests), sortValue: (row) => row.total_requests ?? 0 },
    { key: "bandwidth", header: "Bandwidth", numeric: true, render: (row) => `${(row.bandwidth_gb ?? 0).toFixed(1)} GB`, sortValue: (row) => row.bandwidth_gb ?? 0 },
    { key: "cache", header: "Cache hit", numeric: true, render: (row) => formatPercent((row.cache_hit_ratio ?? 0) * 100), sortValue: (row) => row.cache_hit_ratio ?? 0 },
    { key: "latency", header: "Latency", numeric: true, render: (row) => `${Math.round(row.avg_latency_ms ?? 0)} ms`, sortValue: (row) => row.avg_latency_ms ?? 0 },
    { key: "errors", header: "Errors", numeric: true, render: (row) => formatPercent((row.error_rate ?? 0) * 100), sortValue: (row) => row.error_rate ?? 0 },
  ];

  return (
    <Page width="wide">
      <PageHeader
        title="CDN Analytics"
        subtitle="Traffic, caching and latency from the CDNs you connect with your own API credentials."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Connect a CDN</Button>}
        tabs={<Tabs items={RANGES} value={days} onChange={setDays} label="Period" />}
      />
      <ResourceView resource={resource} isEmpty={(data) => Object.keys(data.providers).length === 0} empty={
        <EmptyState title="No CDN connected" description="Connect a provider with its API key to see traffic and cache performance here." action={<Button variant="primary" onClick={() => setOpen(true)}>Connect a CDN</Button>} />
      }>
        {(data) => {
          const list = rows(data);
          const total = list.reduce((sum, row) => sum + (row.total_requests ?? 0), 0);
          return (
            <>
              <KpiGrid>
                <Kpi label="Providers" value={list.length} />
                <Kpi label="Requests" value={formatNumber(total)} hint={`Last ${data.period_days} days`} />
              </KpiGrid>
              <Section title="By provider"><DataTable columns={columns} rows={list} getKey={(row) => row.name} caption="CDN providers" /></Section>
              {data.recommendations.length ? (
                <Section title="Recommendations">
                  <div style={{ display: "grid", gap: 8 }}>
                    {data.recommendations.map((item, index) => <Callout key={index} tone="info" title={item.category}>{item.priority ? <Badge>{item.priority}</Badge> : null} {item.recommendation}</Callout>)}
                  </div>
                </Section>
              ) : null}
            </>
          );
        }}
      </ResourceView>
      <Modal open={open} onOpenChange={setOpen} title="Connect a CDN">
        <form onSubmit={register} noValidate style={{ display: "grid", gap: 16 }}>
          <FieldSelect label="Provider" value={provider} onChange={(event) => setProvider(event.target.value)}>{PROVIDERS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
          <Field label="API key" type="password" autoComplete="off" value={apiKey} error={error} onChange={(event) => setApiKey(event.target.value)} />
          <Field label="API token (optional)" type="password" autoComplete="off" value={apiToken} onChange={(event) => setApiToken(event.target.value)} hint="Some providers need a second credential." />
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Connect</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
