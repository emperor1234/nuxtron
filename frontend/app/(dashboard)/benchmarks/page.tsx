"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, DataTable, EmptyState, ErrorState, Field, FieldSelect, FieldTextarea, FormActions, Modal, Page, PageHeader, type Column } from "../_ui/kit";
import { formatDate } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Benchmark = { id?: number | string; metric: string; value: number; baseline_value?: number | null; period_label?: string; segment?: string; notes?: string; created_at?: string };

const SEGMENTS = ["all", "ecommerce", "saas", "agency", "media", "fintech", "healthtech", "nonprofit", "education", "marketplace"];

export default function BenchmarksPage() {
  const tenant = useTenant();
  const resource = useResource<Benchmark[]>(async (id) => (await apiGet<{ benchmarks: Benchmark[] }>("/benchmarks", id)).benchmarks, []);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ metric: "", value: "", baseline: "", period: "", segment: "all", notes: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (event: { target: { value: string } }) => setForm((current) => ({ ...current, [key]: event.target.value }));

  async function save(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!form.metric.trim()) found.metric = "Name the metric.";
    if (form.value === "" || Number.isNaN(Number(form.value))) found.value = "Enter a number.";
    if (form.baseline !== "" && Number.isNaN(Number(form.baseline))) found.baseline = "Enter a number or leave empty.";
    if (!form.period.trim()) found.period = "Say which period this covers, such as 2026-Q3.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/benchmarks", "POST", { metric: form.metric.trim(), value: Number(form.value), baseline_value: form.baseline === "" ? null : Number(form.baseline), period_label: form.period.trim(), segment: form.segment, notes: form.notes.trim() }, tenant);
      setForm({ metric: "", value: "", baseline: "", period: "", segment: "all", notes: "" });
      setOpen(false);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Benchmark>[] = [
    { key: "metric", header: "Metric", strong: true, render: (row) => row.metric, sortValue: (row) => row.metric },
    { key: "value", header: "Value", numeric: true, render: (row) => row.value.toLocaleString(), sortValue: (row) => row.value },
    { key: "baseline", header: "Baseline", numeric: true, render: (row) => (row.baseline_value ?? "—") },
    { key: "period", header: "Period", render: (row) => row.period_label || "—" },
    { key: "segment", header: "Segment", render: (row) => row.segment || "all" },
    { key: "when", header: "Recorded", render: (row) => formatDate(row.created_at), sortValue: (row) => row.created_at ?? "" },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Benchmarks" subtitle="Record your own results period by period, so you can see whether you are moving." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Record a result</Button>} />
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="Nothing recorded" description="Add a metric and its value for a period to start your own benchmark history." action={<Button variant="primary" onClick={() => setOpen(true)}>Record a result</Button>} />}>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row, index) => row.id ?? index} caption="Recorded results" pageSize={20} />}
      </ResourceView>
      <Callout tone="info">Industry comparison needs a benchmark dataset loaded for your segment. None is loaded, so only your own numbers are shown.</Callout>
      <Modal open={open} onOpenChange={setOpen} title="Record a result">
        <form onSubmit={save} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Metric" value={form.metric} error={errors.metric} maxLength={120} onChange={set("metric")} />
          <Field label="Value" inputMode="decimal" value={form.value} error={errors.value} onChange={set("value")} />
          <Field label="Baseline (optional)" inputMode="decimal" value={form.baseline} error={errors.baseline} onChange={set("baseline")} />
          <Field label="Period" value={form.period} error={errors.period} maxLength={80} onChange={set("period")} />
          <FieldSelect label="Segment" value={form.segment} onChange={set("segment")}>{SEGMENTS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
          <FieldTextarea label="Notes" rows={2} value={form.notes} maxLength={500} onChange={set("notes")} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Save</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
