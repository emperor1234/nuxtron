"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, DataTable, EmptyState, Field, FieldSelect, FieldTextarea, Modal, Page, PageHeader, StatusBadge, type Column } from "../../../_ui/kit";
import { formatDateTime, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import { SCHEDULE_PLATFORMS } from "../_lib/social";

type Capture = { id: number; source_url: string; title: string; selected_text?: string; note?: string; suggested_network: string; tags: string[]; status: string; created_at: string };

export default function BrowserCapturePage() {
  const tenant = useTenant();
  const resource = useResource<Capture[]>(async (id) => (await apiGet<{ captures?: Capture[] }>("/social/extensions/browser/captures", id)).captures ?? []);
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [selected, setSelected] = useState("");
  const [note, setNote] = useState("");
  const [network, setNetwork] = useState<string>(SCHEDULE_PLATFORMS[0].value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      new URL(url);
    } catch {
      return setError("Enter a valid web address, including https://.");
    }
    if (!title.trim()) return setError("Add a title.");
    setBusy(true);
    try {
      await apiSend("/social/extensions/browser/captures", "POST", { source_url: url.trim(), title: title.trim(), selected_text: selected.trim() || null, note: note.trim() || null, suggested_network: network }, tenant);
      setOpen(false);
      setUrl("");
      setTitle("");
      setSelected("");
      setNote("");
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The capture could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Capture>[] = [
    { key: "title", header: "Capture", strong: true, sortValue: (capture) => capture.title, render: (capture) => <span>{capture.title}<br /><a href={capture.source_url} target="_blank" rel="noreferrer noopener" style={{ fontWeight: 400, fontSize: 12.5 }}>{truncate(capture.source_url, 60)}</a></span> },
    { key: "text", header: "Saved text", render: (capture) => (capture.selected_text ? truncate(capture.selected_text, 100) : "—") },
    { key: "network", header: "For", render: (capture) => <Badge>{capture.suggested_network}</Badge> },
    { key: "status", header: "Status", render: (capture) => <StatusBadge status={capture.status} /> },
    { key: "when", header: "Captured", sortValue: (capture) => capture.created_at, render: (capture) => formatDateTime(capture.created_at) },
  ];

  return (
    <Page>
      <PageHeader
        title="Browser Capture"
        subtitle="Save an article or quote you want to share later, with a note, so it is ready when you plan a post."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => { setOpen(true); setError(null); }}>New capture</Button>}
      />
      <ResourceView
        resource={resource}
        isEmpty={(captures) => captures.length === 0}
        empty={<EmptyState title="Nothing captured yet" description="Save a link and the passage you want to quote." action={<Button variant="primary" onClick={() => setOpen(true)}>New capture</Button>} />}
      >
        {(captures) => <DataTable columns={columns} rows={captures} getKey={(capture) => capture.id} caption="Captures" pageSize={15} />}
      </ResourceView>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="New capture"
        footer={
          <>
            <Button onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
            <Button variant="primary" loading={busy} onClick={() => void save()}>Save capture</Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Web address" type="url" value={url} placeholder="https://example.com/article" onChange={(event) => setUrl(event.target.value)} />
          <Field label="Title" value={title} maxLength={240} onChange={(event) => setTitle(event.target.value)} />
          <FieldTextarea label="Passage to quote" rows={3} value={selected} onChange={(event) => setSelected(event.target.value)} />
          <FieldTextarea label="Note" rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
          <FieldSelect label="Best for" value={network} onChange={(event) => setNetwork(event.target.value)}>
            {SCHEDULE_PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </FieldSelect>
        </div>
      </Modal>
    </Page>
  );
}
