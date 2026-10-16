"use client";

import { useState } from "react";
import { MessageSquareReply, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, CardTitle, DataTable, EmptyState, Field, FieldTextarea, IconButton, Kpi, KpiGrid, Modal, Page, PageHeader, Section, StatusBadge, Tabs, type Column } from "../../../_ui/kit";
import { formatDateTime, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type Comment = { id: string; network: string; post_title?: string; author: string; text: string; sentiment?: string; replied?: boolean; reply?: string; created_at?: string; status?: string };
type SavedReply = { id: string; label: string; text: string; shortcut?: string | null };
type Loaded = { comments: Comment[]; unanswered: number; replies: SavedReply[] };

export default function CommentRepliesPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [comments, replies] = await Promise.all([
      apiGet<{ comments?: Comment[]; unanswered_count?: number }>("/social/community/comments", id),
      apiGet<{ saved_replies?: SavedReply[] }>("/social/community/saved-replies", id),
    ]);
    return { comments: comments.comments ?? [], unanswered: comments.unanswered_count ?? 0, replies: replies.saved_replies ?? [] };
  });

  const [tab, setTab] = useState<"comments" | "replies">("comments");
  const [replying, setReplying] = useState<Comment | null>(null);
  const [replyText, setReplyText] = useState("");
  const [saveOpen, setSaveOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [savedText, setSavedText] = useState("");
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

  const commentColumns: Column<Comment>[] = [
    { key: "author", header: "From", strong: true, sortValue: (comment) => comment.author, render: (comment) => <span>{comment.author}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{comment.network}{comment.post_title ? ` · ${truncate(comment.post_title, 40)}` : ""}</span></span> },
    { key: "text", header: "Comment", render: (comment) => truncate(comment.text, 140) },
    { key: "sentiment", header: "Sentiment", render: (comment) => (comment.sentiment ? <Badge tone={comment.sentiment === "negative" ? "danger" : comment.sentiment === "positive" ? "success" : "neutral"}>{comment.sentiment}</Badge> : "—") },
    { key: "when", header: "Received", sortValue: (comment) => comment.created_at ?? "", render: (comment) => formatDateTime(comment.created_at) },
    { key: "status", header: "Status", render: (comment) => <StatusBadge status={comment.replied ? "replied" : "open"} /> },
    { key: "actions", header: "", render: (comment) => comment.replied ? null : <IconButton label="Reply" onClick={() => { setReplying(comment); setReplyText(""); setError(null); }}><MessageSquareReply size={15} aria-hidden="true" /></IconButton> },
  ];

  return (
    <Page>
      <PageHeader
        title="Comment Replies"
        subtitle="Comments from your connected accounts, with saved replies to answer quickly."
        tabs={<Tabs items={[{ id: "comments", label: "Comments", count: resource.data?.comments.length }, { id: "replies", label: "Saved replies", count: resource.data?.replies.length }]} value={tab} onChange={(id) => setTab(id as "comments" | "replies")} />}
        actions={tab === "replies" ? <Button variant="primary" onClick={() => { setSaveOpen(true); setError(null); }}>New saved reply</Button> : undefined}
      />
      <ResourceView resource={resource}>
        {(data) =>
          tab === "comments" ? (
            <>
              <KpiGrid>
                <Kpi label="Comments" value={data.comments.length} />
                <Kpi label="Waiting for a reply" value={data.unanswered} />
              </KpiGrid>
              {data.comments.length === 0 ? (
                <EmptyState title="No comments yet" description="Comments appear here once a connected account receives them." />
              ) : (
                <DataTable columns={commentColumns} rows={data.comments} getKey={(comment) => comment.id} caption="Comments" pageSize={15} />
              )}
            </>
          ) : data.replies.length === 0 ? (
            <EmptyState title="No saved replies" description="Save the answers you give often and reuse them in one click." action={<Button variant="primary" onClick={() => setSaveOpen(true)}>New saved reply</Button>} />
          ) : (
            <Section title="Saved replies">
              {data.replies.map((reply) => (
                <Card key={reply.id}>
                  <CardTitle sub={reply.shortcut ?? undefined} actions={<IconButton label={`Delete ${reply.label}`} variant="quiet" onClick={() => void run(() => apiSend(`/social/community/saved-replies/${reply.id}`, "DELETE", undefined, tenant), () => undefined)}><Trash2 size={15} aria-hidden="true" /></IconButton>}>{reply.label}</CardTitle>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{reply.text}</p>
                </Card>
              ))}
            </Section>
          )
        }
      </ResourceView>

      <Modal
        open={Boolean(replying)}
        onOpenChange={(open) => !open && setReplying(null)}
        title="Reply to comment"
        description={replying ? `${replying.author}: ${truncate(replying.text, 120)}` : undefined}
        footer={
          <>
            <Button onClick={() => setReplying(null)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                if (!replying || !replyText.trim()) return setError("Write a reply first.");
                void run(() => apiSend(`/social/community/comments/${replying.id}/reply`, "POST", { comment_id: replying.id, reply: replyText.trim(), platform: replying.network }, tenant), () => setReplying(null));
              }}
            >
              Send reply
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          {(resource.data?.replies.length ?? 0) > 0 ? (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {resource.data?.replies.map((reply) => <Button key={reply.id} size="sm" onClick={() => setReplyText(reply.text)}>{reply.label}</Button>)}
            </div>
          ) : null}
          <FieldTextarea label="Reply" rows={5} value={replyText} maxLength={2200} onChange={(event) => setReplyText(event.target.value)} />
        </div>
      </Modal>

      <Modal
        open={saveOpen}
        onOpenChange={setSaveOpen}
        title="New saved reply"
        footer={
          <>
            <Button onClick={() => setSaveOpen(false)} disabled={busy}>Cancel</Button>
            <Button variant="primary" loading={busy} onClick={() => { if (!label.trim() || !savedText.trim()) return setError("Add a name and the reply text."); void run(() => apiSend("/social/community/saved-replies", "POST", { label: label.trim(), text: savedText.trim() }, tenant), () => { setSaveOpen(false); setLabel(""); setSavedText(""); }); }}>Save reply</Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Name" value={label} maxLength={100} onChange={(event) => setLabel(event.target.value)} />
          <FieldTextarea label="Reply text" rows={5} value={savedText} maxLength={2200} onChange={(event) => setSavedText(event.target.value)} />
        </div>
      </Modal>
    </Page>
  );
}
