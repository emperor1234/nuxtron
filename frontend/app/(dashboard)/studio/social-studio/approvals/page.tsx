"use client";

import { useMemo, useState } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, CardTitle, EmptyState, ErrorState, Field, FieldSelect, FieldTextarea, Kpi, KpiGrid, LoadingState, Modal, Page, PageHeader, Section } from "../../../_ui/kit";
import { formatDateTime } from "../../../_ui/format";
import { useResource, useTenant } from "../../../_ui/use-resource";

// Same contract as the Content Queue and Post Planner, so a request created here
// is the one reviewers see everywhere else.
type ApprovalRequest = {
  id: number;
  status: string;
  scheduled_post_id: number;
  platform?: string;
  content_preview?: string;
  requested_by?: string;
  approval_levels?: string[];
  approvals_received?: string[];
  rejection_reason?: string;
  created_at?: string;
};

type QueuePost = {
  id: string | number;
  title?: string;
  caption?: string;
  text?: string;
  platform?: string;
  platforms?: string[];
  status?: string;
};

type Loaded = { requests: ApprovalRequest[]; posts: QueuePost[]; levels: string[] };

const REQUESTABLE_STATUSES = new Set(["draft", "scheduled", "queued"]);
const PREVIEW_LIMIT = 500;

const postText = (post: QueuePost) => (post.caption || post.text || post.title || "").trim();
const postPlatform = (post: QueuePost) => (post.platforms?.[0] || post.platform || "").trim();

function outstandingLevels(request: ApprovalRequest): string[] {
  const received = new Set((request.approvals_received ?? []).map((level) => level.toLowerCase()));
  return (request.approval_levels ?? []).filter((level) => !received.has(level.toLowerCase()));
}

export default function ApprovalsPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [requests, queue, config] = await Promise.all([
      apiGet<{ requests?: ApprovalRequest[] }>("/content/approval/requests", id),
      apiGet<{ queue?: QueuePost[] }>("/social/queue?status=all", id),
      apiGet<{ config?: { levels?: string[] } | null }>("/content/approval/config", id),
    ]);
    return { requests: requests.requests ?? [], posts: queue.queue ?? [], levels: config.config?.levels ?? [] };
  });

  const [showForm, setShowForm] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState("");
  const [requestedBy, setRequestedBy] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [busyRequestId, setBusyRequestId] = useState<number | null>(null);
  const [reviewerRoles, setReviewerRoles] = useState<Record<number, string>>({});
  const [comments, setComments] = useState<Record<number, string>>({});
  const [updated, setUpdated] = useState<Record<number, ApprovalRequest>>({});

  const requests = useMemo(
    () => (resource.data?.requests ?? []).map((request) => updated[request.id] ?? request),
    [resource.data, updated],
  );
  const pendingPostIds = useMemo(() => new Set(requests.filter((r) => r.status === "pending").map((r) => String(r.scheduled_post_id))), [requests]);

  const requestablePosts = useMemo(
    () =>
      (resource.data?.posts ?? []).filter((post) => {
        const id = Number(post.id);
        return (
          Number.isInteger(id) &&
          id > 0 &&
          REQUESTABLE_STATUSES.has((post.status || "").toLowerCase()) &&
          postText(post).length > 0 &&
          postPlatform(post).length > 0 &&
          !pendingPostIds.has(String(post.id))
        );
      }),
    [resource.data, pendingPostIds],
  );

  const selectedPost = requestablePosts.find((post) => String(post.id) === selectedPostId);
  const canSubmit = Boolean(selectedPost) && requestedBy.trim().length > 0 && !submitting;

  async function submitRequest() {
    if (!selectedPost || !requestedBy.trim()) return;
    setSubmitting(true);
    setActionError("");
    try {
      await apiSend(
        "/content/approval/requests",
        "POST",
        {
          scheduled_post_id: Number(selectedPost.id),
          platform: postPlatform(selectedPost),
          content_preview: postText(selectedPost).slice(0, PREVIEW_LIMIT),
          requested_by: requestedBy.trim(),
        },
        tenant,
      );
      setSelectedPostId("");
      setShowForm(false);
      await resource.reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to submit the approval request.");
    } finally {
      setSubmitting(false);
    }
  }

  async function decide(request: ApprovalRequest, decision: "approved" | "rejected") {
    const role = reviewerRoles[request.id] || outstandingLevels(request)[0] || "";
    const comment = (comments[request.id] || "").trim();
    if (!role) {
      setActionError("This request has no outstanding approval level to sign off.");
      return;
    }
    if (decision === "rejected" && !comment) {
      setActionError("Add a reason so the creator knows what to change.");
      return;
    }
    setBusyRequestId(request.id);
    setActionError("");
    try {
      const res = await apiSend<{ request?: ApprovalRequest }>(
        `/content/approval/requests/${request.id}/decision`,
        "POST",
        { decision, reviewer_role: role, comment: comment || null },
        tenant,
      );
      // Show the server's resulting state: a multi-level chain stays pending
      // until every level has signed off.
      const next = res.request;
      if (next) setUpdated((current) => ({ ...current, [next.id]: next }));
      else await resource.reload();
      setComments((current) => ({ ...current, [request.id]: "" }));
      setReviewerRoles((current) => ({ ...current, [request.id]: "" }));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to record the decision.");
    } finally {
      setBusyRequestId(null);
    }
  }

  const pending = requests.filter((r) => r.status === "pending");
  const approved = requests.filter((r) => r.status === "approved");
  const closed = requests.filter((r) => r.status !== "pending" && r.status !== "approved");
  const loading = resource.status === "loading" && resource.data === null;
  const failed = resource.status === "error" && resource.data === null;

  return (
    <Page>
      <PageHeader
        title="Content Approvals"
        subtitle="Send planned posts for review and record sign-off from each approval level."
        actions={
          <Button variant="primary" onClick={() => setShowForm(true)} disabled={loading || failed}>
            Request approval
          </Button>
        }
      />

      {actionError ? <Callout tone="danger">{actionError}</Callout> : null}

      {!loading && !failed ? (
        <Callout tone="info">
          {resource.data?.levels.length
            ? `Approval chain: ${resource.data.levels.join(" → ")}`
            : "No approval chain configured yet. New requests require a manager sign-off until an admin sets up a chain."}
        </Callout>
      ) : null}

      {loading ? <LoadingState label="Loading approval requests" /> : null}
      {failed ? <ErrorState error={resource.error} onRetry={() => void resource.reload()} title="Approvals could not be loaded" /> : null}

      {!loading && !failed && requests.length === 0 ? (
        <EmptyState title="No approval requests yet" description="Requests you send for review will appear here." />
      ) : null}

      {!loading && !failed && requests.length > 0 ? (
        <>
          <KpiGrid>
            <Kpi label="Pending" value={pending.length} />
            <Kpi label="Approved" value={approved.length} />
            <Kpi label="Rejected or expired" value={closed.length} />
          </KpiGrid>

          <Section title={`Pending (${pending.length})`}>
            {pending.length === 0 ? <p style={{ margin: 0, color: "var(--nx-muted)" }}>Nothing is waiting for review.</p> : null}
            {pending.map((req) => {
              const levels = outstandingLevels(req);
              const busy = busyRequestId === req.id;
              return (
                <Card key={req.id}>
                  <CardTitle sub={`Post #${req.scheduled_post_id}${req.platform ? ` · ${req.platform}` : ""}${req.requested_by ? ` · requested by ${req.requested_by}` : ""} · ${formatDateTime(req.created_at)}`}>
                    {req.content_preview || `Post #${req.scheduled_post_id}`}
                  </CardTitle>
                  <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--nx-muted)" }}>
                    Signed off: {(req.approvals_received ?? []).join(", ") || "none yet"} · Waiting on: {levels.join(", ") || "none"}
                  </p>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
                    <div style={{ minWidth: 200 }}>
                      <FieldSelect label="Reviewing as" value={reviewerRoles[req.id] || levels[0] || ""} disabled={levels.length === 0} onChange={(event) => setReviewerRoles((current) => ({ ...current, [req.id]: event.target.value }))}>
                        {levels.map((level) => (
                          <option key={level} value={level}>
                            Review as {level}
                          </option>
                        ))}
                      </FieldSelect>
                    </div>
                    <div style={{ flex: 1, minWidth: 220 }}>
                      <Field label="Reviewer comment" value={comments[req.id] || ""} maxLength={1000} placeholder="Comment (required to reject)" onChange={(event) => setComments((current) => ({ ...current, [req.id]: event.target.value }))} />
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <Button variant="primary" onClick={() => void decide(req, "approved")} disabled={busy || levels.length === 0}>
                      Approve
                    </Button>
                    <Button variant="danger" onClick={() => void decide(req, "rejected")} disabled={busy || levels.length === 0}>
                      Reject
                    </Button>
                  </div>
                </Card>
              );
            })}
          </Section>

          {approved.length > 0 ? (
            <Section title={`Approved (${approved.length})`}>
              {approved.map((req) => (
                <Card key={req.id}>
                  <CardTitle sub={`Post #${req.scheduled_post_id} · signed off by ${(req.approvals_received ?? []).join(", ")}`}>{req.content_preview || `Post #${req.scheduled_post_id}`}</CardTitle>
                </Card>
              ))}
            </Section>
          ) : null}

          {closed.length > 0 ? (
            <Section title={`Rejected or expired (${closed.length})`}>
              {closed.map((req) => (
                <Card key={req.id}>
                  <CardTitle sub={`Post #${req.scheduled_post_id}${req.rejection_reason ? ` · Reason: ${req.rejection_reason}` : ""}`}>{req.content_preview || `Post #${req.scheduled_post_id}`}</CardTitle>
                  <Badge tone="danger">{req.status}</Badge>
                </Card>
              ))}
            </Section>
          ) : null}
        </>
      ) : null}

      <Modal
        open={showForm}
        onOpenChange={setShowForm}
        title="Request content approval"
        description="Choose a planned post and who is asking. Reviewers see it in this list."
        footer={
          <>
            <Button onClick={() => setShowForm(false)} disabled={submitting}>Cancel</Button>
            <Button variant="primary" disabled={!canSubmit} loading={submitting} onClick={() => void submitRequest()}>
              Send for approval
            </Button>
          </>
        }
      >
        {requestablePosts.length === 0 ? (
          <p style={{ margin: 0, color: "var(--nx-muted)" }}>No draft or scheduled posts are waiting for review. Plan a post first, then request approval.</p>
        ) : (
          <div style={{ display: "grid", gap: 14 }}>
            <FieldSelect label="Post" value={selectedPostId} onChange={(event) => setSelectedPostId(event.target.value)}>
              <option value="">Choose a post…</option>
              {requestablePosts.map((post) => (
                <option key={String(post.id)} value={String(post.id)}>
                  #{post.id} · {postPlatform(post)} · {postText(post).slice(0, 80)}
                </option>
              ))}
            </FieldSelect>
            <Field label="Requested by" value={requestedBy} maxLength={120} placeholder="Your name or handle" onChange={(event) => setRequestedBy(event.target.value)} />
            <FieldTextarea label="Selected text" rows={3} value={selectedPost ? postText(selectedPost) : ""} readOnly />
          </div>
        )}
      </Modal>
    </Page>
  );
}
