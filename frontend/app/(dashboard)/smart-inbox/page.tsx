"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, DataTable, Drawer, EmptyState, ErrorState, Field, FieldSelect, FieldTextarea, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, Toolbar, type Column } from "../_ui/kit";
import { formatDateTime, formatNumber, truncate } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Message = {
  id: number; network: string; author_handle: string; author_display_name?: string | null; text: string; message_type: string; sentiment: string;
  priority_score: number; suggested_replies?: string[]; status: string; replied: boolean; read: boolean; created_at: string;
};
type Stats = { total: number; unread: number; replied: number };
type Note = { id?: number; author: string; note: string; created_at?: string };

const STATUSES = ["pending", "in_progress", "requires_approval", "flagged", "complete"];
const NETWORKS = ["twitter", "instagram", "facebook", "linkedin", "tiktok", "youtube", "email"];
const label = (value: string) => value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const SENTIMENT_TONE = { positive: "success", negative: "danger", neutral: "neutral" } as const;

function Detail({ message, onChanged }: { message: Message; onChanged: () => void }) {
  const tenant = useTenant();
  const notes = useResource<Note[]>(async (id) => (await apiGet<{ notes?: Note[] }>(`/inbox/messages/${message.id}/notes`, id)).notes ?? [], [message.id]);
  const [note, setNote] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function setStatus(status: string) {
    setFailure(null);
    try {
      await apiSend(`/inbox/messages/${message.id}`, "PATCH", { status }, tenant);
      onChanged();
    } catch (caught) {
      setFailure(caught);
    }
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!note.trim()) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(`/inbox/messages/${message.id}/notes`, "POST", { author: "Team", note: note.trim() }, tenant);
      setNote("");
      notes.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <p style={{ margin: 0, fontSize: 15, lineHeight: 1.55 }}>{message.text}</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Badge>{message.network}</Badge><Badge>{label(message.message_type)}</Badge>
        <Badge tone={SENTIMENT_TONE[message.sentiment as keyof typeof SENTIMENT_TONE] ?? "neutral"}>{message.sentiment}</Badge>
      </div>
      <FieldSelect label="Status" value={message.status} onChange={(event) => void setStatus(event.target.value)}>{STATUSES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
      {message.suggested_replies?.length ? (
        <div>
          <h3 style={{ margin: "0 0 8px", fontSize: 14 }}>Reply templates</h3>
          <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 14 }}>{message.suggested_replies.map((reply) => <li key={reply}>{reply}</li>)}</ul>
          <p style={{ margin: "8px 0 0", fontSize: 12.5, color: "var(--nx-muted)" }}>Generic templates chosen by message type. Edit them before you reply on the network.</p>
        </div>
      ) : null}
      <div>
        <h3 style={{ margin: "0 0 8px", fontSize: 14 }}>Internal notes</h3>
        <ResourceView resource={notes} isEmpty={(rows) => rows.length === 0} empty={<p style={{ margin: 0, color: "var(--nx-muted)", fontSize: 14 }}>No notes yet.</p>}>
          {(rows) => <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 14 }}>{rows.map((item, index) => <li key={item.id ?? index}>{item.note} <span style={{ color: "var(--nx-muted)" }}>· {formatDateTime(item.created_at)}</span></li>)}</ul>}
        </ResourceView>
        <form onSubmit={addNote} noValidate style={{ display: "grid", gap: 10, marginTop: 12 }}>
          <FieldTextarea label="Add a note" rows={2} value={note} maxLength={1000} onChange={(event) => setNote(event.target.value)} />
          <FormActions><Button type="submit" loading={busy}>Save note</Button></FormActions>
        </form>
      </div>
      {failure ? <ErrorState error={failure} title="The change failed" /> : null}
    </div>
  );
}

export default function SmartInboxPage() {
  const tenant = useTenant();
  const [status, setStatus] = useState("");
  const [network, setNetwork] = useState("");
  const [selected, setSelected] = useState<Message | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ network: "twitter", author_handle: "", text: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const stats = useResource<Stats>((id) => apiGet<Stats>("/inbox/stats", id), []);
  const messages = useResource<Message[]>(async (id) => {
    const params = new URLSearchParams({ limit: "200" });
    if (status) params.set("status", status);
    if (network) params.set("network", network);
    return (await apiGet<{ messages: Message[] }>(`/inbox/messages?${params}`, id)).messages;
  }, [status, network]);

  function reloadAll() {
    stats.reload();
    messages.reload();
  }

  async function log(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (form.author_handle.trim().length < 1) found.author_handle = "Enter who wrote it.";
    if (form.text.trim().length < 1) found.text = "Paste the message.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/inbox/messages", "POST", { network: form.network, author_handle: form.author_handle.trim(), text: form.text.trim() }, tenant);
      setForm({ network: form.network, author_handle: "", text: "" });
      setOpen(false);
      reloadAll();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Message>[] = [
    { key: "from", header: "From", strong: true, render: (row) => <span>{row.author_display_name || row.author_handle}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{row.network}</span></span>, sortValue: (row) => row.author_handle },
    { key: "text", header: "Message", render: (row) => <span style={{ fontWeight: row.read ? 400 : 700 }}>{truncate(row.text, 110)}</span> },
    { key: "type", header: "Type", render: (row) => label(row.message_type) },
    { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "complete" ? "success" : row.status === "flagged" ? "danger" : "neutral"}>{label(row.status)}</Badge>, sortValue: (row) => row.status },
    { key: "priority", header: "Priority", numeric: true, render: (row) => row.priority_score, sortValue: (row) => row.priority_score },
    { key: "when", header: "Received", render: (row) => formatDateTime(row.created_at), sortValue: (row) => row.created_at },
  ];
  const filtered = Boolean(status || network);

  return (
    <Page width="wide">
      <PageHeader title="Smart Inbox" subtitle="Comments, mentions and messages in one queue. Type and priority are worked out from the text with simple rules." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Log a message</Button>} />
      {stats.data ? (
        <KpiGrid>
          <Kpi label="Messages" value={formatNumber(stats.data.total)} />
          <Kpi label="Unread" value={formatNumber(stats.data.unread)} />
          <Kpi label="Replied" value={formatNumber(stats.data.replied)} />
        </KpiGrid>
      ) : null}
      <Toolbar>
        <FieldSelect label="Status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All</option>{STATUSES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
        <FieldSelect label="Network" value={network} onChange={(event) => setNetwork(event.target.value)}><option value="">All</option>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
      </Toolbar>
      <ResourceView resource={messages} isEmpty={(rows) => rows.length === 0} empty={
        <EmptyState title={filtered ? "No messages match" : "Your inbox is empty"} description={filtered ? "Change the filters." : "Messages appear when a connected network sends them to Nuxtron. You can also log one by hand."} action={filtered ? undefined : <Button variant="primary" onClick={() => setOpen(true)}>Log a message</Button>} />
      }>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} onRowClick={setSelected} caption="Inbox messages" pageSize={20} />}
      </ResourceView>
      <Callout tone="info">Replies are sent on the network itself. Nuxtron does not post for you.</Callout>
      <Drawer open={Boolean(selected)} onOpenChange={(next) => !next && setSelected(null)} title={selected ? `${selected.author_display_name || selected.author_handle}` : ""} description={selected ? formatDateTime(selected.created_at) : undefined}>
        {selected ? <Detail message={selected} onChanged={() => { reloadAll(); setSelected(null); }} /> : null}
      </Drawer>
      <Modal open={open} onOpenChange={setOpen} title="Log a message">
        <form onSubmit={log} noValidate style={{ display: "grid", gap: 16 }}>
          <FieldSelect label="Network" value={form.network} onChange={(event) => setForm({ ...form, network: event.target.value })}>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
          <Field label="From (handle or name)" value={form.author_handle} error={errors.author_handle} maxLength={120} onChange={(event) => setForm({ ...form, author_handle: event.target.value })} />
          <FieldTextarea label="Message" rows={4} value={form.text} error={errors.text} maxLength={4000} onChange={(event) => setForm({ ...form, text: event.target.value })} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Save</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
