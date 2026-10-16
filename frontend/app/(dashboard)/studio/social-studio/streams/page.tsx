"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, CardTitle, ConfirmModal, EmptyState, Field, Grid, IconButton, Modal, Page, PageHeader } from "../../../_ui/kit";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type FeedItem = { id: string; author?: string; network?: string; text?: string; posted_at?: string };
type Stream = { id: number; name: string; stream_type: string; query: string; networks: string[]; feed: FeedItem[] };

export default function MonitoringStreamsPage() {
  const tenant = useTenant();
  const resource = useResource<Stream[]>(async (id) => (await apiGet<{ streams?: Stream[] }>("/social/streams", id)).streams ?? []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [deleting, setDeleting] = useState<Stream | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, done: () => void) {
    setBusy(true);
    setError(null);
    try {
      await action();
      done();
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page>
      <PageHeader
        title="Monitoring Streams"
        subtitle="Watch a search term or account across networks. Items appear here when a connected account reports a match."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => { setOpen(true); setError(null); }}>New stream</Button>}
      />
      <ResourceView
        resource={resource}
        isEmpty={(streams) => streams.length === 0}
        empty={<EmptyState title="No streams yet" description="Create a stream for a brand name, hashtag or account you want to watch." action={<Button variant="primary" onClick={() => setOpen(true)}>New stream</Button>} />}
      >
        {(streams) => (
          <Grid cols={3}>
            {streams.map((stream) => (
              <Card key={stream.id}>
                <CardTitle
                  sub={`“${stream.query}” · ${stream.networks.join(", ")}`}
                  actions={<IconButton label={`Delete ${stream.name}`} variant="quiet" onClick={() => { setDeleting(stream); setError(null); }}><Trash2 size={15} aria-hidden="true" /></IconButton>}
                >
                  {stream.name}
                </CardTitle>
                {stream.feed.length === 0 ? (
                  <p style={{ margin: 0, fontSize: 13.5, color: "var(--nx-muted)" }}>No matches yet.</p>
                ) : (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 10 }}>
                    {stream.feed.slice(0, 5).map((item) => (
                      <li key={item.id} style={{ fontSize: 13.5 }}>
                        <Badge>{item.network}</Badge> <strong>{item.author}</strong>
                        <div style={{ color: "var(--nx-ink-2)" }}>{item.text}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            ))}
          </Grid>
        )}
      </ResourceView>

      <Modal
        open={open}
        onOpenChange={setOpen}
        title="New stream"
        footer={
          <>
            <Button onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                if (name.trim().length < 2 || !query.trim()) return setError("Add a name and a search term.");
                void run(() => apiSend("/social/streams", "POST", { name: name.trim(), query: query.trim(), stream_type: "keyword" }, tenant), () => { setOpen(false); setName(""); setQuery(""); });
              }}
            >
              Create stream
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Name" value={name} maxLength={140} onChange={(event) => setName(event.target.value)} />
          <Field label="Search term" value={query} maxLength={300} onChange={(event) => setQuery(event.target.value)} hint="A brand name, hashtag or account handle." />
        </div>
      </Modal>
      <ConfirmModal
        open={Boolean(deleting)}
        onOpenChange={(next) => !next && setDeleting(null)}
        title="Delete this stream?"
        description={deleting ? `“${deleting.name}” will stop being monitored.` : ""}
        pending={busy}
        error={error}
        onConfirm={() => deleting && void run(() => apiSend(`/social/streams/${deleting.id}`, "DELETE", undefined, tenant), () => setDeleting(null))}
      />
    </Page>
  );
}
