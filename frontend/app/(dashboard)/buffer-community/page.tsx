'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type CommunityComment = {
  id: string;
  network: string;
  post_title?: string;
  author: string;
  text: string;
  sentiment?: string;
  replied?: boolean;
  reply?: string;
  created_at?: string;
  status?: string;
  likes?: number;
};

type SavedReply = {
  id: string;
  label: string;
  text: string;
  shortcut?: string;
};

type CommentScore = {
  response_rate: number;
  avg_response_time_minutes: number;
  consistency_score: number;
  total_comments: number;
  replied_count: number;
  pending_count: number;
  grade: string;
};

const box = {
  background: 'var(--bg-soft, #f8fafc)',
  border: '1px solid var(--line, #e2e8f0)',
  borderRadius: 12,
  padding: 16,
} as const;

export default function BufferCommunityPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('newest');
  const [comments, setComments] = useState<CommunityComment[]>([]);
  const [savedReplies, setSavedReplies] = useState<SavedReply[]>([]);
  const [score, setScore] = useState<CommentScore | null>(null);
  const [draftReplies, setDraftReplies] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [commentRes, scoreRes, replyRes] = await Promise.all([
        apiGet<{ comments?: CommunityComment[] }>(`/social/community/comments?sort=${sort}`, tenantId),
        apiGet<{ comment_score?: CommentScore }>('/social/community/score', tenantId),
        apiGet<{ saved_replies?: SavedReply[] }>('/social/community/saved-replies', tenantId),
      ]);
      setComments(commentRes.comments ?? []);
      setScore(scoreRes.comment_score ?? null);
      setSavedReplies(replyRes.saved_replies ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load community data');
    } finally {
      setLoading(false);
    }
  }, [sort, tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (filter === 'all') return comments;
    if (filter === 'unanswered') return comments.filter((comment) => !comment.replied);
    return comments.filter((comment) => comment.network === filter);
  }, [comments, filter]);

  function setReply(commentId: string, text: string) {
    setDraftReplies((prev) => ({ ...prev, [commentId]: text }));
  }

  async function replyToComment(comment: CommunityComment) {
    const reply = (draftReplies[comment.id] || '').trim();
    if (!reply) return;
    try {
      await apiSend(
        `/social/community/comments/${comment.id}/reply`,
        'POST',
        {
          comment_id: comment.id,
          reply,
          platform: comment.network,
        },
        tenantId
      );
      setDraftReplies((prev) => ({ ...prev, [comment.id]: '' }));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reply failed');
    }
  }

  async function createPost(commentId: string) {
    try {
      await apiSend(`/social/community/comments/${commentId}/create-post`, 'POST', undefined, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create post failed');
    }
  }

  function applySavedReply(commentId: string, text: string) {
    setReply(commentId, text);
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg, #f8fafc)', color: 'var(--text, #0f172a)', padding: 24 }}>
      <div style={{ maxWidth: 1240, margin: '0 auto' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 18,
            alignItems: 'flex-start',
            marginBottom: 20,
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 28 }}>Community</h1>
            <p style={{ margin: '6px 0 0', color: '#64748b' }}>
              Reply across networks, reuse saved answers, and track response performance.
            </p>
          </div>
          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 110px), 1fr))', gap: 10, minWidth: 500 }}
          >
            <div style={box}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Grade</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{score?.grade || '—'}</div>
            </div>
            <div style={box}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Response rate</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{score ? `${score.response_rate}%` : '—'}</div>
            </div>
            <div style={box}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Avg speed</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{score ? `${score.avg_response_time_minutes}m` : '—'}</div>
            </div>
            <div style={box}>
              <div style={{ fontSize: 12, color: '#64748b' }}>Pending</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{score?.pending_count || 0}</div>
            </div>
          </div>
        </div>

        {error ? <div style={{ ...box, color: '#b91c1c', marginBottom: 14 }}>{error}</div> : null}

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 12,
            alignItems: 'center',
            marginBottom: 18,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              'all',
              'unanswered',
              'instagram',
              'facebook',
              'linkedin',
              'x',
              'tiktok',
              'youtube',
              'threads',
              'bluesky',
              'mastodon',
            ].map((value) => (
              <button
                key={value}
                onClick={() => setFilter(value)}
                style={{
                  border: 'none',
                  borderRadius: 999,
                  padding: '8px 14px',
                  cursor: 'pointer',
                  background: filter === value ? '#6366f1' : '#e2e8f0',
                  color: filter === value ? '#fff' : '#334155',
                  fontWeight: 700,
                }}
              >
                {value}
              </button>
            ))}
          </div>
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value)}
            style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>

        {loading ? (
          <div style={{ color: '#64748b', padding: 30, textAlign: 'center' }}>Loading community inbox…</div>
        ) : null}

        {loading ? null : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <section style={{ display: 'grid', gap: 12 }}>
              {filtered.map((comment) => (
                <div key={comment.id} style={box}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                    <div>
                      <div style={{ fontWeight: 700 }}>{comment.author}</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>
                        {comment.network} · {comment.post_title || 'Untitled post'} ·{' '}
                        {comment.created_at ? new Date(comment.created_at).toLocaleString() : 'no date'}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span
                        style={{
                          fontSize: 11,
                          borderRadius: 999,
                          padding: '4px 10px',
                          background: comment.replied ? '#dcfce7' : '#fef3c7',
                          color: comment.replied ? '#166534' : '#92400e',
                        }}
                      >
                        {comment.replied ? 'Replied' : 'Waiting'}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          borderRadius: 999,
                          padding: '4px 10px',
                          background: '#e2e8f0',
                          color: '#334155',
                        }}
                      >
                        {comment.sentiment || 'neutral'}
                      </span>
                    </div>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', color: '#334155', marginBottom: 10 }}>{comment.text}</div>
                  {comment.reply ? (
                    <div
                      style={{
                        padding: 12,
                        borderRadius: 10,
                        background: '#eff6ff',
                        color: '#6366f1',
                        marginBottom: 10,
                      }}
                    >
                      Your reply: {comment.reply}
                    </div>
                  ) : null}
                  <textarea
                    value={draftReplies[comment.id] || ''}
                    onChange={(event) => setReply(comment.id, event.target.value)}
                    placeholder="Write a reply…"
                    style={{
                      width: '100%',
                      minHeight: 90,
                      boxSizing: 'border-box',
                      borderRadius: 10,
                      border: '1px solid #cbd5e1',
                      padding: 10,
                      marginBottom: 10,
                    }}
                  />
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                    {savedReplies.map((reply) => (
                      <button
                        key={reply.id}
                        onClick={() => applySavedReply(comment.id, reply.text)}
                        style={{
                          border: 'none',
                          borderRadius: 999,
                          padding: '6px 10px',
                          cursor: 'pointer',
                          background: '#dbeafe',
                          color: '#1d4ed8',
                          fontSize: 12,
                        }}
                      >
                        {reply.label}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      onClick={() => void replyToComment(comment)}
                      style={{
                        border: 'none',
                        borderRadius: 10,
                        padding: '9px 12px',
                        background: '#6366f1',
                        color: '#fff',
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      Send reply
                    </button>
                    <button
                      onClick={() => void createPost(comment.id)}
                      style={{
                        border: 'none',
                        borderRadius: 10,
                        padding: '9px 12px',
                        background: '#10b981',
                        color: '#fff',
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      Create post from reply
                    </button>
                  </div>
                </div>
              ))}
              {filtered.length === 0 ? <div style={box}>No comments match this filter.</div> : null}
            </section>

            <aside style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
              <div style={box}>
                <h2 style={{ marginTop: 0, fontSize: 18 }}>Saved Replies</h2>
                <div style={{ display: 'grid', gap: 10 }}>
                  {savedReplies.map((reply) => (
                    <div key={reply.id} style={{ padding: 12, borderRadius: 10, background: '#fff' }}>
                      <div style={{ fontWeight: 700 }}>{reply.label}</div>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                        {reply.shortcut || 'no shortcut'}
                      </div>
                      <div style={{ fontSize: 13, color: '#334155', marginTop: 8 }}>{reply.text}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={box}>
                <h2 style={{ marginTop: 0, fontSize: 18 }}>Comment Score</h2>
                <div style={{ fontSize: 13, color: '#475569', display: 'grid', gap: 8 }}>
                  <div>Total comments: {score?.total_comments || 0}</div>
                  <div>Replied: {score?.replied_count || 0}</div>
                  <div>Consistency: {score?.consistency_score || 0}</div>
                </div>
              </div>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
