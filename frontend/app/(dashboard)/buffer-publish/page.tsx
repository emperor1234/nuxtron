'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type QueuePost = {
  id: string | number;
  title?: string;
  caption?: string;
  text?: string;
  platform?: string;
  platforms?: string[];
  status?: string;
  scheduled_for?: string;
  publish_at?: string;
  created_at?: string;
  content_type?: string;
  first_comment?: string;
  thread_count?: number;
};

type ApprovalRequest = {
  id: number;
  status: string;
  platform?: string;
  content_preview?: string;
  requested_by?: string;
  approvals_received?: string[];
  approval_levels?: string[];
  created_at?: string;
};

type PostingSchedule = {
  id: string;
  network: string;
  timezone: string;
  slots: Array<{ day: string; time: string }>;
};

const sectionCard = {
  background: 'var(--bg-soft, #f8fafc)',
  border: '1px solid var(--line, #e2e8f0)',
  borderRadius: 12,
  padding: 16,
} as const;

const field = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 8,
  border: '1px solid var(--line, #cbd5e1)',
  background: 'var(--bg, #fff)',
  color: 'var(--text, #0f172a)',
  boxSizing: 'border-box' as const,
} as const;

function postPlatforms(post: QueuePost): string[] {
  if (post.platforms?.length) return post.platforms;
  if (post.platform) return [post.platform];
  return [];
}

function postWhen(post: QueuePost): string {
  return post.scheduled_for || post.publish_at || post.created_at || '';
}

function approvalTone(status: string): { background: string; color: string } {
  if (status === 'pending') return { background: '#fef3c7', color: '#92400e' };
  if (status === 'approved') return { background: '#dcfce7', color: '#166534' };
  return { background: '#fee2e2', color: '#b91c1c' };
}

// eslint-disable-next-line sonarjs/cognitive-complexity
export default function BufferPublishPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [tab, setTab] = useState<'queue' | 'drafts' | 'approvals' | 'sent' | 'calendar' | 'schedules'>('queue');
  const [posts, setPosts] = useState<QueuePost[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [schedules, setSchedules] = useState<PostingSchedule[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [editingNetwork, setEditingNetwork] = useState('instagram');
  const [editingTimezone, setEditingTimezone] = useState('UTC');
  const [editingSlots, setEditingSlots] = useState('Monday 09:00\nWednesday 12:00\nFriday 17:00');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [queueRes, approvalRes, scheduleRes] = await Promise.all([
        apiGet<{ queue?: QueuePost[] }>('/social/queue?status=all', tenantId),
        apiGet<{ requests?: ApprovalRequest[] }>('/content/approval/requests', tenantId),
        apiGet<{ schedules?: PostingSchedule[] }>('/social/posting-schedules', tenantId),
      ]);
      setPosts(queueRes.queue ?? []);
      setApprovals(approvalRes.requests ?? []);
      setSchedules(scheduleRes.schedules ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load publishing data');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => {
    const queue = posts.filter(
      (post) => (post.status || '').toLowerCase() === 'scheduled' || (post.status || '').toLowerCase() === 'queued'
    );
    const drafts = posts.filter((post) => (post.status || '').toLowerCase() === 'draft');
    const sent = posts.filter(
      (post) => (post.status || '').toLowerCase() === 'sent' || (post.status || '').toLowerCase() === 'published'
    );
    return { queue, drafts, sent };
  }, [posts]);

  const calendarItems = useMemo(() => [...posts].sort((a, b) => postWhen(a).localeCompare(postWhen(b))), [posts]);

  async function reorder(postsToShow: QueuePost[], index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= postsToShow.length) return;
    const reordered = [...postsToShow];
    const [moved] = reordered.splice(index, 1);
    reordered.splice(target, 0, moved);
    try {
      await apiSend(
        '/social/queue/reorder',
        'POST',
        {
          post_ids: reordered.map((post) => String(post.id)),
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reorder failed');
    }
  }

  async function saveSchedule() {
    const slots = editingSlots
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [day, time] = line.split(/\s+/);
        return { day, time };
      })
      .filter((slot) => slot.day && slot.time);

    try {
      await apiSend(
        `/social/posting-schedules/${editingNetwork}`,
        'PUT',
        {
          account_id: 1,
          network: editingNetwork,
          slots,
          timezone: editingTimezone,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Saving schedule failed');
    }
  }

  function renderPost(post: QueuePost, index: number, items: QueuePost[], showReorder: boolean) {
    return (
      <div key={String(post.id)} style={{ ...sectionCard, padding: 14, marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>
              {post.title || post.caption || post.text || 'Untitled post'}
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {postPlatforms(post).join(', ') || 'No platforms'} · {(post.status || 'unknown').toUpperCase()} ·{' '}
              {postWhen(post) ? new Date(postWhen(post)).toLocaleString() : 'No publish time'}
            </div>
            {(post.caption || post.text) && (
              <div style={{ fontSize: 13, color: '#334155', marginTop: 8, whiteSpace: 'pre-wrap' }}>
                {post.caption || post.text}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
              {post.first_comment ? (
                <span
                  style={{
                    fontSize: 11,
                    background: '#fef3c7',
                    color: '#92400e',
                    borderRadius: 999,
                    padding: '3px 8px',
                  }}
                >
                  First comment attached
                </span>
              ) : null}
              {post.thread_count ? (
                <span
                  style={{
                    fontSize: 11,
                    background: '#dbeafe',
                    color: '#6366f1',
                    borderRadius: 999,
                    padding: '3px 8px',
                  }}
                >
                  {post.thread_count} posts in thread
                </span>
              ) : null}
              {post.content_type ? (
                <span
                  style={{
                    fontSize: 11,
                    background: '#dcfce7',
                    color: '#166534',
                    borderRadius: 999,
                    padding: '3px 8px',
                  }}
                >
                  {post.content_type}
                </span>
              ) : null}
            </div>
          </div>
          {showReorder ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <button
                onClick={() => void reorder(items, index, -1)}
                style={{
                  border: 'none',
                  borderRadius: 8,
                  padding: '6px 10px',
                  background: '#e2e8f0',
                  cursor: 'pointer',
                }}
              >
                ↑
              </button>
              <button
                onClick={() => void reorder(items, index, 1)}
                style={{
                  border: 'none',
                  borderRadius: 8,
                  padding: '6px 10px',
                  background: '#e2e8f0',
                  cursor: 'pointer',
                }}
              >
                ↓
              </button>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg, #f8fafc)', color: 'var(--text, #0f172a)', padding: 24 }}>
      <div style={{ maxWidth: 1240, margin: '0 auto' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 16,
            alignItems: 'flex-start',
            marginBottom: 20,
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 28 }}>Publish</h1>
            <p style={{ margin: '6px 0 0', color: '#64748b' }}>
              Manage queue order, approvals, posting schedules, and the live calendar.
            </p>
          </div>
          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))', gap: 10, minWidth: 380 }}
          >
            <div style={sectionCard}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Queued</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{grouped.queue.length}</div>
            </div>
            <div style={sectionCard}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Drafts</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{grouped.drafts.length}</div>
            </div>
            <div style={sectionCard}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Approvals</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>
                {approvals.filter((item) => item.status === 'pending').length}
              </div>
            </div>
          </div>
        </div>

        {error ? <div style={{ ...sectionCard, color: '#b91c1c', marginBottom: 14 }}>{error}</div> : null}

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
          {[
            ['queue', 'Queue'],
            ['drafts', 'Drafts'],
            ['approvals', 'Approvals'],
            ['sent', 'Sent'],
            ['calendar', 'Calendar'],
            ['schedules', 'Schedules'],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() => setTab(value as typeof tab)}
              style={{
                border: 'none',
                borderRadius: 999,
                padding: '8px 14px',
                background: tab === value ? '#6366f1' : '#e2e8f0',
                color: tab === value ? '#fff' : '#334155',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ color: '#64748b', padding: 40, textAlign: 'center' }}>Loading publish workspace…</div>
        ) : null}

        {!loading && tab === 'queue' ? (
          <section>
            {grouped.queue.map((post, index) => renderPost(post, index, grouped.queue, true))}
            {grouped.queue.length === 0 ? <div style={sectionCard}>No queued posts yet.</div> : null}
          </section>
        ) : null}
        {!loading && tab === 'drafts' ? (
          <section>
            {grouped.drafts.map((post, index) => renderPost(post, index, grouped.drafts, false))}
            {grouped.drafts.length === 0 ? <div style={sectionCard}>No drafts yet.</div> : null}
          </section>
        ) : null}
        {!loading && tab === 'sent' ? (
          <section>
            {grouped.sent.map((post, index) => renderPost(post, index, grouped.sent, false))}
            {grouped.sent.length === 0 ? <div style={sectionCard}>No sent posts recorded yet.</div> : null}
          </section>
        ) : null}

        {!loading && tab === 'approvals' ? (
          <section style={{ display: 'grid', gap: 12 }}>
            {approvals.map((request) => (
              <div key={request.id} style={sectionCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{request.content_preview || 'Approval request'}</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      {request.platform || 'unknown'} · requested by {request.requested_by || 'unknown'} ·{' '}
                      {request.created_at ? new Date(request.created_at).toLocaleString() : 'no date'}
                    </div>
                  </div>
                  <span
                    style={{ fontSize: 12, borderRadius: 999, padding: '4px 10px', ...approvalTone(request.status) }}
                  >
                    {request.status}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: '#475569', marginTop: 10 }}>
                  Approved by: {(request.approvals_received || []).join(', ') || 'none yet'}
                </div>
                <div style={{ fontSize: 12, color: '#475569' }}>
                  Required roles: {(request.approval_levels || []).join(', ') || 'none configured'}
                </div>
              </div>
            ))}
            {approvals.length === 0 ? <div style={sectionCard}>No approval requests yet.</div> : null}
          </section>
        ) : null}

        {!loading && tab === 'calendar' ? (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 12 }}>
            {calendarItems.map((post) => (
              <div key={String(post.id)} style={sectionCard}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
                  {postWhen(post) ? new Date(postWhen(post)).toLocaleDateString() : 'Unscheduled'}
                </div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>{post.title || post.caption || 'Untitled'}</div>
                <div style={{ fontSize: 12, color: '#475569' }}>{postPlatforms(post).join(', ') || 'No platforms'}</div>
              </div>
            ))}
            {calendarItems.length === 0 ? <div style={sectionCard}>No calendar items yet.</div> : null}
          </section>
        ) : null}

        {!loading && tab === 'schedules' ? (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <div>
              <h2 style={{ marginTop: 0 }}>Posting Schedules</h2>
              <div style={{ display: 'grid', gap: 10 }}>
                {schedules.map((schedule) => (
                  <div key={schedule.id} style={sectionCard}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <strong>{schedule.network}</strong>
                      <span style={{ fontSize: 12, color: '#64748b' }}>{schedule.timezone}</span>
                    </div>
                    <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {schedule.slots.map((slot) => (
                        <span
                          key={`${schedule.id}-${slot.day}-${slot.time}`}
                          style={{
                            fontSize: 12,
                            background: '#dbeafe',
                            color: '#6366f1',
                            borderRadius: 999,
                            padding: '4px 8px',
                          }}
                        >
                          {slot.day} {slot.time}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
                {schedules.length === 0 ? <div style={sectionCard}>No posting schedules configured.</div> : null}
              </div>
            </div>
            <div style={sectionCard}>
              <h2 style={{ marginTop: 0 }}>Edit Schedule</h2>
              <div style={{ display: 'grid', gap: 10 }}>
                <select
                  value={editingNetwork}
                  onChange={(event) => setEditingNetwork(event.target.value)}
                  style={field}
                >
                  {['instagram', 'facebook', 'linkedin', 'x', 'tiktok'].map((network) => (
                    <option key={network} value={network}>
                      {network}
                    </option>
                  ))}
                </select>
                <input
                  value={editingTimezone}
                  onChange={(event) => setEditingTimezone(event.target.value)}
                  style={field}
                  placeholder="Timezone"
                />
                <textarea
                  value={editingSlots}
                  onChange={(event) => setEditingSlots(event.target.value)}
                  style={{ ...field, minHeight: 180 }}
                  placeholder="One slot per line: Monday 09:00"
                />
                <button
                  onClick={() => void saveSchedule()}
                  style={{
                    border: 'none',
                    borderRadius: 10,
                    padding: '10px 14px',
                    background: '#6366f1',
                    color: '#fff',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Save schedule
                </button>
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
