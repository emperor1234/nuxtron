'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';

// Same contract as the Publishing Queue and Social Studio approval panels, so a
// request created here is the one reviewers see everywhere else.
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
  expires_at?: string;
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

type ApprovalConfig = { levels?: string[] } | null;

const REQUESTABLE_STATUSES = new Set(['draft', 'scheduled', 'queued']);
const PREVIEW_LIMIT = 500;

function postText(post: QueuePost): string {
  return (post.caption || post.text || post.title || '').trim();
}

function postPlatform(post: QueuePost): string {
  return (post.platforms?.[0] || post.platform || '').trim();
}

function outstandingLevels(request: ApprovalRequest): string[] {
  const received = new Set((request.approvals_received ?? []).map((level) => level.toLowerCase()));
  return (request.approval_levels ?? []).filter((level) => !received.has(level.toLowerCase()));
}

function formatWhen(value?: string): string {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString();
}

export default function ApprovalsPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [posts, setPosts] = useState<QueuePost[]>([]);
  const [config, setConfig] = useState<ApprovalConfig>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState('');
  const [requestedBy, setRequestedBy] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [busyRequestId, setBusyRequestId] = useState<number | null>(null);
  const [reviewerRoles, setReviewerRoles] = useState<Record<number, string>>({});
  const [comments, setComments] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [requestRes, queueRes, configRes] = await Promise.all([
        apiGet<{ requests?: ApprovalRequest[] }>('/content/approval/requests', tenantId),
        apiGet<{ queue?: QueuePost[] }>('/social/queue?status=all', tenantId),
        apiGet<{ config?: ApprovalConfig }>('/content/approval/config', tenantId),
      ]);
      setRequests(requestRes.requests ?? []);
      setPosts(queueRes.queue ?? []);
      setConfig(configRes.config ?? null);
    } catch (err) {
      setRequests([]);
      setLoadError(err instanceof Error ? err.message : 'Approvals are unavailable right now.');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const pendingPostIds = useMemo(
    () => new Set(requests.filter((r) => r.status === 'pending').map((r) => String(r.scheduled_post_id))),
    [requests]
  );

  const requestablePosts = useMemo(
    () =>
      posts.filter((post) => {
        const id = Number(post.id);
        return (
          Number.isInteger(id) &&
          id > 0 &&
          REQUESTABLE_STATUSES.has((post.status || '').toLowerCase()) &&
          postText(post).length > 0 &&
          postPlatform(post).length > 0 &&
          !pendingPostIds.has(String(post.id))
        );
      }),
    [posts, pendingPostIds]
  );

  const selectedPost = requestablePosts.find((post) => String(post.id) === selectedPostId);
  const canSubmit = Boolean(selectedPost) && requestedBy.trim().length > 0 && !submitting;

  async function submitRequest() {
    if (!selectedPost || !requestedBy.trim()) return;
    setSubmitting(true);
    setActionError('');
    try {
      await apiSend(
        '/content/approval/requests',
        'POST',
        {
          scheduled_post_id: Number(selectedPost.id),
          platform: postPlatform(selectedPost),
          content_preview: postText(selectedPost).slice(0, PREVIEW_LIMIT),
          requested_by: requestedBy.trim(),
        },
        tenantId
      );
      setSelectedPostId('');
      setShowForm(false);
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to submit the approval request.');
    } finally {
      setSubmitting(false);
    }
  }

  async function decide(request: ApprovalRequest, decision: 'approved' | 'rejected') {
    const role = reviewerRoles[request.id] || outstandingLevels(request)[0] || '';
    const comment = (comments[request.id] || '').trim();
    if (!role) {
      setActionError('This request has no outstanding approval level to sign off.');
      return;
    }
    if (decision === 'rejected' && !comment) {
      setActionError('Add a reason so the creator knows what to change.');
      return;
    }
    setBusyRequestId(request.id);
    setActionError('');
    try {
      const res = await apiSend<{ request?: ApprovalRequest }>(
        `/content/approval/requests/${request.id}/decision`,
        'POST',
        { decision, reviewer_role: role, comment: comment || null },
        tenantId
      );
      // Show the server's resulting state: a multi-level chain stays pending
      // until every level has signed off.
      if (res.request) {
        const updated = res.request;
        setRequests((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      } else {
        await load();
      }
      setComments((current) => ({ ...current, [request.id]: '' }));
      setReviewerRoles((current) => ({ ...current, [request.id]: '' }));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to record the decision.');
    } finally {
      setBusyRequestId(null);
    }
  }

  const pending = requests.filter((r) => r.status === 'pending');
  const approved = requests.filter((r) => r.status === 'approved');
  const closed = requests.filter((r) => r.status !== 'pending' && r.status !== 'approved');
  const configuredLevels = config?.levels ?? [];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Social Studio
          </Link>
          <h1 style={styles.title}>Content Approvals</h1>
          <p style={styles.subtitle}>
            Send scheduled posts for review and record sign-off from each approval level.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          disabled={loading || Boolean(loadError)}
          style={styles.requestBtn}
        >
          {showForm ? 'Cancel' : 'Request approval'}
        </button>
      </div>

      {loadError ? (
        <div role="alert" style={styles.errorBanner}>
          Approvals could not be loaded: {loadError}{' '}
          <button type="button" onClick={() => void load()} style={styles.linkBtn}>
            Retry
          </button>
        </div>
      ) : null}
      {actionError ? (
        <div role="alert" style={styles.errorBanner}>
          {actionError}
        </div>
      ) : null}

      {!loading && !loadError ? (
        <p style={styles.configNote}>
          {configuredLevels.length
            ? `Approval chain: ${configuredLevels.join(' → ')}`
            : 'No approval chain configured yet. New requests require a manager sign-off until you configure one in Social Studio.'}
        </p>
      ) : null}

      {showForm ? (
        <div style={styles.formCard}>
          <h2 style={styles.formTitle}>Request content approval</h2>
          {requestablePosts.length === 0 ? (
            <p style={styles.muted}>
              No draft or scheduled posts are waiting for review. Create or schedule a post first, then request approval.
            </p>
          ) : (
            <>
              <div style={styles.formGroup}>
                <label htmlFor="approval-post" style={styles.label}>
                  Post
                </label>
                <select
                  id="approval-post"
                  style={styles.field}
                  value={selectedPostId}
                  onChange={(e) => setSelectedPostId(e.target.value)}
                >
                  <option value="">Choose a post…</option>
                  {requestablePosts.map((post) => (
                    <option key={String(post.id)} value={String(post.id)}>
                      #{post.id} · {postPlatform(post)} · {postText(post).slice(0, 80)}
                    </option>
                  ))}
                </select>
              </div>
              <div style={styles.formGroup}>
                <label htmlFor="approval-requested-by" style={styles.label}>
                  Requested by
                </label>
                <input
                  id="approval-requested-by"
                  style={styles.field}
                  value={requestedBy}
                  maxLength={120}
                  onChange={(e) => setRequestedBy(e.target.value)}
                  placeholder="Your name or handle"
                />
              </div>
              <button
                type="button"
                style={styles.submitBtn}
                disabled={!canSubmit}
                onClick={() => void submitRequest()}
              >
                {submitting ? 'Sending…' : 'Send for approval'}
              </button>
            </>
          )}
        </div>
      ) : null}

      {loading ? (
        <p style={styles.muted} aria-live="polite">
          Loading approval requests…
        </p>
      ) : loadError ? null : requests.length === 0 ? (
        <div style={styles.emptyState}>
          <h3 style={styles.formTitle}>No approval requests yet</h3>
          <p style={styles.muted}>Requests you send for review will appear here.</p>
        </div>
      ) : (
        <>
          <section style={styles.section} aria-labelledby="approvals-pending">
            <h2 id="approvals-pending" style={styles.sectionTitle}>
              Pending ({pending.length})
            </h2>
            {pending.length === 0 ? <p style={styles.muted}>Nothing is waiting for review.</p> : null}
            <div style={styles.requestsList}>
              {pending.map((req) => {
                const levels = outstandingLevels(req);
                const busy = busyRequestId === req.id;
                return (
                  <article key={req.id} style={styles.requestCard}>
                    <div style={styles.requestHeader}>
                      <div>
                        <h3 style={styles.contentPreview}>{req.content_preview || `Post #${req.scheduled_post_id}`}</h3>
                        <div style={styles.requestMeta}>
                          <span>Post #{req.scheduled_post_id}</span>
                          {req.platform ? <span>{req.platform}</span> : null}
                          {req.requested_by ? <span>Requested by {req.requested_by}</span> : null}
                          {formatWhen(req.created_at) ? <span>{formatWhen(req.created_at)}</span> : null}
                        </div>
                      </div>
                    </div>
                    <p style={styles.levels}>
                      Signed off: {(req.approvals_received ?? []).join(', ') || 'none yet'} · Waiting on:{' '}
                      {levels.join(', ') || 'none'}
                    </p>
                    <div style={styles.decisionRow}>
                      <label style={styles.srOnly} htmlFor={`role-${req.id}`}>
                        Reviewing as
                      </label>
                      <select
                        id={`role-${req.id}`}
                        style={{ ...styles.field, maxWidth: 200 }}
                        value={reviewerRoles[req.id] || levels[0] || ''}
                        onChange={(e) => setReviewerRoles((current) => ({ ...current, [req.id]: e.target.value }))}
                        disabled={levels.length === 0}
                      >
                        {levels.map((level) => (
                          <option key={level} value={level}>
                            Review as {level}
                          </option>
                        ))}
                      </select>
                      <label style={styles.srOnly} htmlFor={`comment-${req.id}`}>
                        Reviewer comment
                      </label>
                      <input
                        id={`comment-${req.id}`}
                        style={{ ...styles.field, flex: 1 }}
                        value={comments[req.id] || ''}
                        maxLength={1000}
                        onChange={(e) => setComments((current) => ({ ...current, [req.id]: e.target.value }))}
                        placeholder="Comment (required to reject)"
                      />
                    </div>
                    <div style={styles.actions}>
                      <button
                        type="button"
                        onClick={() => void decide(req, 'approved')}
                        style={styles.approveBtn}
                        disabled={busy || levels.length === 0}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => void decide(req, 'rejected')}
                        style={styles.rejectBtn}
                        disabled={busy || levels.length === 0}
                      >
                        Reject
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {approved.length > 0 ? (
            <section style={styles.section} aria-labelledby="approvals-approved">
              <h2 id="approvals-approved" style={styles.sectionTitle}>
                Approved ({approved.length})
              </h2>
              <div style={styles.requestsList}>
                {approved.map((req) => (
                  <article key={req.id} style={{ ...styles.requestCard, borderLeftColor: 'var(--success)' }}>
                    <h3 style={styles.contentPreview}>{req.content_preview || `Post #${req.scheduled_post_id}`}</h3>
                    <div style={styles.requestMeta}>
                      <span>Post #{req.scheduled_post_id}</span>
                      <span>Signed off by {(req.approvals_received ?? []).join(', ')}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {closed.length > 0 ? (
            <section style={styles.section} aria-labelledby="approvals-closed">
              <h2 id="approvals-closed" style={styles.sectionTitle}>
                Rejected or expired ({closed.length})
              </h2>
              <div style={styles.requestsList}>
                {closed.map((req) => (
                  <article key={req.id} style={{ ...styles.requestCard, borderLeftColor: 'var(--danger)' }}>
                    <h3 style={styles.contentPreview}>{req.content_preview || `Post #${req.scheduled_post_id}`}</h3>
                    <div style={styles.requestMeta}>
                      <span>Post #{req.scheduled_post_id}</span>
                      <span style={{ color: 'var(--danger)' }}>{req.status}</span>
                      {req.rejection_reason ? <span>Reason: {req.rejection_reason}</span> : null}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    color: 'var(--text)',
    padding: '32px 24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    flexWrap: 'wrap',
    marginBottom: '24px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--muted)',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--muted)',
    margin: 0,
  },
  requestBtn: {
    padding: '10px 20px',
    backgroundColor: 'var(--brand)',
    color: 'var(--on-brand)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  errorBanner: {
    backgroundColor: 'var(--danger-soft)',
    border: '1px solid var(--danger)',
    color: 'var(--text)',
    padding: '12px 14px',
    borderRadius: '10px',
    marginBottom: '16px',
  },
  linkBtn: {
    background: 'none',
    border: 'none',
    padding: 0,
    color: 'var(--brand)',
    textDecoration: 'underline',
    cursor: 'pointer',
    font: 'inherit',
  },
  configNote: {
    fontSize: '13px',
    color: 'var(--muted)',
    margin: '0 0 24px',
  },
  formCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '32px',
  },
  formTitle: {
    fontSize: '18px',
    fontWeight: 600,
    margin: '0 0 16px',
  },
  formGroup: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
  },
  field: {
    width: '100%',
    padding: '8px 10px',
    backgroundColor: 'var(--bg)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  submitBtn: {
    padding: '10px 20px',
    backgroundColor: 'var(--brand)',
    color: 'var(--on-brand)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  muted: {
    color: 'var(--muted)',
    fontSize: '14px',
    margin: 0,
  },
  section: {
    marginBottom: '32px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '12px',
  },
  requestsList: {
    display: 'grid',
    gap: '12px',
  },
  requestCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderLeft: '4px solid var(--warning)',
    borderRadius: '8px',
    padding: '16px',
  },
  requestHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '8px',
    gap: '12px',
  },
  contentPreview: {
    margin: '0 0 6px',
    fontSize: '14px',
    fontWeight: 600,
    overflowWrap: 'anywhere',
  },
  requestMeta: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
    fontSize: '12px',
    color: 'var(--muted)',
  },
  levels: {
    fontSize: '12px',
    color: 'var(--muted)',
    margin: '0 0 12px',
  },
  decisionRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  actions: {
    display: 'flex',
    gap: '12px',
  },
  approveBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: 'var(--success-soft)',
    color: 'var(--success-ink)',
    border: '1px solid var(--success)',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  rejectBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: 'var(--danger-soft)',
    color: 'var(--danger)',
    border: '1px solid var(--danger)',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  emptyState: {
    textAlign: 'center',
    padding: '48px 24px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    border: '1px dashed var(--line)',
  },
  srOnly: {
    position: 'absolute',
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)',
    whiteSpace: 'nowrap',
    border: 0,
  },
};
