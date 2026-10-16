"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, DataTable, EmptyState, ErrorState, Field, FieldSelect, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, SearchField, Tabs, Toolbar, type Column } from "../_ui/kit";
import { formatCurrency, formatDate, formatNumber } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Contact = { id: number; first_name: string; last_name?: string; email?: string; company?: string; phone?: string; lifecycle_stage?: string; lead_score?: number; created_at?: string };
type Deal = { id: number; title: string; value: number; currency?: string; stage: string; close_date?: string | null; created_at?: string };

const LIFECYCLE = ["lead", "marketing_qualified", "sales_qualified", "opportunity", "customer", "evangelist", "other"];
const STAGES = [
  { value: "prospect", label: "Prospect" }, { value: "qualified", label: "Qualified" }, { value: "proposal", label: "Proposal" },
  { value: "negotiation", label: "Negotiation" }, { value: "closed_won", label: "Closed won" }, { value: "closed_lost", label: "Closed lost" },
];
const label = (value: string) => value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function ContactForm({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (open: boolean) => void; onDone: () => void }) {
  const tenant = useTenant();
  const [values, setValues] = useState({ first_name: "", last_name: "", email: "", company: "", phone: "", lifecycle_stage: "lead" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof values) => (event: { target: { value: string } }) => setValues((current) => ({ ...current, [key]: event.target.value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!values.first_name.trim()) found.first_name = "Enter a first name.";
    if (values.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.email.trim())) found.email = "Enter a valid email address.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/crm/contacts", "POST", Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()])), tenant);
      setValues({ first_name: "", last_name: "", email: "", company: "", phone: "", lifecycle_stage: "lead" });
      onOpenChange(false);
      onDone();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Add a contact">
      <form onSubmit={submit} noValidate style={{ display: "grid", gap: 16 }}>
        <Field label="First name" value={values.first_name} error={errors.first_name} maxLength={120} onChange={set("first_name")} />
        <Field label="Last name" value={values.last_name} maxLength={120} onChange={set("last_name")} />
        <Field label="Email" type="email" value={values.email} error={errors.email} maxLength={255} onChange={set("email")} />
        <Field label="Company" value={values.company} maxLength={180} onChange={set("company")} />
        <Field label="Phone" type="tel" value={values.phone} maxLength={40} onChange={set("phone")} />
        <FieldSelect label="Stage" value={values.lifecycle_stage} onChange={set("lifecycle_stage")}>{LIFECYCLE.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
        {failure ? <ErrorState error={failure} title="Not saved" /> : null}
        <FormActions><Button onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add contact</Button></FormActions>
      </form>
    </Modal>
  );
}

function DealForm({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (open: boolean) => void; onDone: () => void }) {
  const tenant = useTenant();
  const [title, setTitle] = useState("");
  const [value, setValue] = useState("");
  const [stage, setStage] = useState("prospect");
  const [closeDate, setCloseDate] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!title.trim()) found.title = "Name the deal.";
    if (value && (Number.isNaN(Number(value)) || Number(value) < 0)) found.value = "Enter an amount of zero or more.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/crm/deals", "POST", { title: title.trim(), value: Number(value || 0), stage, close_date: closeDate || null }, tenant);
      setTitle("");
      setValue("");
      setCloseDate("");
      onOpenChange(false);
      onDone();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Add a deal">
      <form onSubmit={submit} noValidate style={{ display: "grid", gap: 16 }}>
        <Field label="Deal name" value={title} error={errors.title} maxLength={180} onChange={(event) => setTitle(event.target.value)} />
        <Field label="Value (USD)" inputMode="decimal" value={value} error={errors.value} onChange={(event) => setValue(event.target.value)} />
        <FieldSelect label="Stage" value={stage} onChange={(event) => setStage(event.target.value)}>{STAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</FieldSelect>
        <Field label="Expected close date" type="date" value={closeDate} onChange={(event) => setCloseDate(event.target.value)} />
        {failure ? <ErrorState error={failure} title="Not saved" /> : null}
        <FormActions><Button onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add deal</Button></FormActions>
      </form>
    </Modal>
  );
}

function Contacts() {
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("");
  const [open, setOpen] = useState(false);
  const resource = useResource<{ contacts: Contact[]; total: number }>(async (tenant) => {
    const params = new URLSearchParams({ limit: "100" });
    if (query.trim()) params.set("q", query.trim());
    if (stage) params.set("lifecycle_stage", stage);
    return apiGet(`/crm/contacts?${params}`, tenant);
  }, [query, stage]);
  const columns: Column<Contact>[] = [
    { key: "name", header: "Name", strong: true, render: (row) => `${row.first_name} ${row.last_name ?? ""}`.trim(), sortValue: (row) => row.first_name },
    { key: "email", header: "Email", render: (row) => row.email || "—" },
    { key: "company", header: "Company", render: (row) => row.company || "—", sortValue: (row) => row.company ?? "" },
    { key: "stage", header: "Stage", render: (row) => <Badge>{label(row.lifecycle_stage ?? "lead")}</Badge> },
    { key: "score", header: "Lead score", numeric: true, render: (row) => row.lead_score ?? 0, sortValue: (row) => row.lead_score ?? 0 },
    { key: "added", header: "Added", render: (row) => formatDate(row.created_at), sortValue: (row) => row.created_at ?? "" },
  ];
  const filtered = Boolean(query.trim() || stage);
  return (
    <>
      <Toolbar>
        <SearchField label="Search contacts" value={query} onChange={setQuery} placeholder="Name, email or company" />
        <FieldSelect label="Stage" value={stage} onChange={(event) => setStage(event.target.value)}><option value="">All stages</option>{LIFECYCLE.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
        <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add contact</Button>
      </Toolbar>
      <ResourceView resource={resource} isEmpty={(data) => data.contacts.length === 0} empty={
        <EmptyState title={filtered ? "No contacts match" : "No contacts yet"} description={filtered ? "Change the search or the stage filter." : "Add your first contact to start tracking leads."} action={filtered ? undefined : <Button variant="primary" onClick={() => setOpen(true)}>Add contact</Button>} />
      }>
        {(data) => <DataTable columns={columns} rows={data.contacts} getKey={(row) => row.id} caption={`Contacts (${formatNumber(data.total)})`} pageSize={20} />}
      </ResourceView>
      <ContactForm open={open} onOpenChange={setOpen} onDone={resource.reload} />
    </>
  );
}

function Deals() {
  const tenant = useTenant();
  const [stage, setStage] = useState("");
  const [open, setOpen] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const resource = useResource<{ deals: Deal[]; total: number }>((id) => apiGet(`/crm/deals?limit=100${stage ? `&stage=${stage}` : ""}`, id), [stage]);

  async function move(deal: Deal, next: string) {
    setFailure(null);
    try {
      await apiSend(`/crm/deals/${deal.id}`, "PATCH", { stage: next }, tenant);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    }
  }

  const columns: Column<Deal>[] = [
    { key: "title", header: "Deal", strong: true, render: (row) => row.title, sortValue: (row) => row.title },
    { key: "value", header: "Value", numeric: true, render: (row) => formatCurrency(row.value, row.currency || "USD"), sortValue: (row) => row.value },
    { key: "stage", header: "Stage", render: (row) => (
      <select aria-label={`Stage for ${row.title}`} value={row.stage} onChange={(event) => void move(row, event.target.value)} style={{ font: "inherit", padding: "4px 8px", borderRadius: 6, border: "1px solid var(--nx-line, #d9dce5)", background: "var(--nx-surface, #fff)", color: "inherit" }}>
        {STAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
      </select>
    ) },
    { key: "close", header: "Expected close", render: (row) => formatDate(row.close_date), sortValue: (row) => row.close_date ?? "" },
  ];

  return (
    <>
      <Toolbar>
        <FieldSelect label="Stage" value={stage} onChange={(event) => setStage(event.target.value)}><option value="">All stages</option>{STAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</FieldSelect>
        <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add deal</Button>
      </Toolbar>
      {failure ? <ErrorState error={failure} title="The stage was not changed" /> : null}
      <ResourceView resource={resource} isEmpty={(data) => data.deals.length === 0} empty={<EmptyState title={stage ? "No deals in this stage" : "No deals yet"} description={stage ? "Choose another stage." : "Add a deal to start your pipeline."} action={stage ? undefined : <Button variant="primary" onClick={() => setOpen(true)}>Add deal</Button>} />}>
        {(data) => {
          const open = data.deals.filter((deal) => !deal.stage.startsWith("closed"));
          const won = data.deals.filter((deal) => deal.stage === "closed_won");
          return (
            <>
              <KpiGrid>
                <Kpi label="Open deals" value={open.length} hint={formatCurrency(open.reduce((sum, deal) => sum + deal.value, 0))} />
                <Kpi label="Closed won" value={won.length} hint={formatCurrency(won.reduce((sum, deal) => sum + deal.value, 0))} />
              </KpiGrid>
              <DataTable columns={columns} rows={data.deals} getKey={(row) => row.id} caption="Deals" pageSize={20} />
            </>
          );
        }}
      </ResourceView>
      <DealForm open={open} onOpenChange={setOpen} onDone={resource.reload} />
    </>
  );
}

export default function CrmPage() {
  const [tab, setTab] = useState("contacts");
  return (
    <Page width="wide">
      <PageHeader title="CRM" subtitle="Your contacts and deals in one place." tabs={<Tabs items={[{ id: "contacts", label: "Contacts" }, { id: "deals", label: "Deals" }]} value={tab} onChange={setTab} label="CRM sections" />} />
      {tab === "contacts" ? <Contacts /> : <Deals />}
    </Page>
  );
}
