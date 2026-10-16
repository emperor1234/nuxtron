"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, DataTable, EmptyState, ErrorState, Field, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, Section, type Column } from "../../_ui/kit";
import { formatCurrency, formatNumber } from "../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../_ui/use-resource";

type Channel = { channel?: string; platform?: string; conversions?: number; revenue?: number; attributed_revenue?: number };
type Report = { window_days: number; currency_totals: Array<{ currency: string; revenue: number }>; totals: { conversions: number; tracked_conversions: number; revenue: number; attributed_revenue: number; unattributed_revenue: number; currency: string | null }; channels: Channel[] };

function Form({ title, endpoint, fields, build, open, onOpenChange, onDone }: { title: string; endpoint: string; fields: Array<{ key: string; label: string; hint?: string; numeric?: boolean }>; build: (v: Record<string, string>) => Record<string, unknown>; open: boolean; onOpenChange: (open: boolean) => void; onDone: () => void }) {
  const tenant = useTenant();
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    for (const field of fields) {
      const value = (values[field.key] ?? "").trim();
      if (!value) found[field.key] = `${field.label} is required.`;
      else if (field.numeric && Number.isNaN(Number(value))) found[field.key] = "Enter a number.";
    }
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(endpoint, "POST", build(values), tenant);
      setValues({});
      onOpenChange(false);
      onDone();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title}>
      <form onSubmit={submit} noValidate style={{ display: "grid", gap: 16 }}>
        {fields.map((field) => <Field key={field.key} label={field.label} hint={field.hint} error={errors[field.key]} value={values[field.key] ?? ""} onChange={(event) => setValues({ ...values, [field.key]: event.target.value })} />)}
        {failure ? <ErrorState error={failure} title="Not saved" /> : null}
        <FormActions><Button onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Save</Button></FormActions>
      </form>
    </Modal>
  );
}

export default function RevenueAttributionPage() {
  const resource = useResource<Report>((tenant) => apiGet<Report>("/analytics/revenue-attribution/report", tenant), []);
  const [touch, setTouch] = useState(false);
  const [sale, setSale] = useState(false);
  const columns: Column<Channel>[] = [
    { key: "channel", header: "Channel", strong: true, render: (row) => row.channel ?? row.platform ?? "—" },
    { key: "conv", header: "Conversions", numeric: true, render: (row) => formatNumber(row.conversions), sortValue: (row) => row.conversions ?? 0 },
    { key: "rev", header: "Attributed revenue", numeric: true, render: (row) => formatCurrency(row.attributed_revenue ?? row.revenue ?? 0), sortValue: (row) => row.attributed_revenue ?? row.revenue ?? 0 },
  ];
  return (
    <Page width="wide">
      <PageHeader title="Revenue Attribution" subtitle="Tie orders back to the posts and campaigns that sent the visitor." actions={<><Button onClick={() => setTouch(true)}>Record a tracked link</Button><Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setSale(true)}>Record an order</Button></>} />
      <ResourceView resource={resource} isEmpty={(data) => data.totals.conversions === 0 && data.channels.length === 0} empty={<EmptyState title="No orders recorded" description="Record the tracked links you publish, then the orders that follow, to see revenue by channel." action={<Button variant="primary" onClick={() => setSale(true)}>Record an order</Button>} />}>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Orders" value={formatNumber(data.totals.conversions)} hint={`Last ${data.window_days} days`} />
              <Kpi label="Revenue" value={formatCurrency(data.totals.revenue, data.totals.currency ?? "USD")} />
              <Kpi label="Attributed" value={formatCurrency(data.totals.attributed_revenue, data.totals.currency ?? "USD")} />
              <Kpi label="Not attributed" value={formatCurrency(data.totals.unattributed_revenue, data.totals.currency ?? "USD")} />
            </KpiGrid>
            <Section title="By channel"><DataTable columns={columns} rows={data.channels} getKey={(row, index) => row.channel ?? row.platform ?? index} caption="Revenue by channel" /></Section>
          </>
        )}
      </ResourceView>
      <Callout tone="info">Only orders you record or that a connected store sends are counted.</Callout>
      <Form open={touch} onOpenChange={setTouch} onDone={resource.reload} title="Record a tracked link" endpoint="/analytics/revenue-attribution/touchpoints"
        fields={[{ key: "post_id", label: "Post or asset ID" }, { key: "platform", label: "Platform" }, { key: "campaign", label: "Campaign" }, { key: "destination_url", label: "Destination URL", hint: "Include the https:// part." }]}
        build={(v) => ({ post_id: v.post_id.trim(), platform: v.platform.trim(), campaign: v.campaign.trim(), destination_url: v.destination_url.trim() })} />
      <Form open={sale} onOpenChange={setSale} onDone={resource.reload} title="Record an order" endpoint="/analytics/revenue-attribution/conversions/ingest"
        fields={[{ key: "provider", label: "Store or provider" }, { key: "order", label: "Order ID" }, { key: "amount", label: "Amount", numeric: true }]}
        build={(v) => ({ provider: v.provider.trim(), external_order_id: v.order.trim(), amount: Number(v.amount) })} />
    </Page>
  );
}
