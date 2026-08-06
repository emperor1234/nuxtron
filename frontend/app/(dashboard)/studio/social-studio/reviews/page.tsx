'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type ReviewItem = {
  id: number;
  platform: string;
  author: string;
  rating: number;
  text: string;
  status: 'open' | 'responded' | 'resolved';
  sentiment?: string;
  created_at: string;
};

type CareCase = {
  id: number;
  source_review_id: number;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'new' | 'in_progress' | 'resolved';
  owner: string;
  created_at: string;
};

export default function SocialReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [cases, setCases] = useState<CareCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewId, setReviewId] = useState('');
  const [replyText, setReplyText] = useState('Thanks for the feedback. Our team is already on it.');
  const [status, setStatus] = useState<'open' | 'responded' | 'resolved'>('responded');

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [reviewsRes, casesRes] = await Promise.all([
        apiGet<{ reviews?: ReviewItem[] }>('/social/reviews', DEFAULT_TENANT_ID),
        apiGet<{ cases?: CareCase[] }>('/social/care/cases', DEFAULT_TENANT_ID),
      ]);
      setReviews(reviewsRes.reviews || []);
      setCases(casesRes.cases || []);
      if ((reviewsRes.reviews || []).length > 0) setReviewId(String(reviewsRes.reviews?.[0]?.id || ''));
    } catch (err) {
      console.error('Failed to load reviews module:', err);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Failed to load review operations in strict no-mock mode.'
          : 'Failed to load review operations in fail-closed mode.'
      );
      setReviews([]);
      setCases([]);
      setReviewId('');
    } finally {
      setLoading(false);
    }
  }

  async function handleReply() {
    const id = Number.parseInt(reviewId, 10);
    if (!Number.isFinite(id)) return;
    const response = await apiSend(
      `/social/reviews/${id}/reply`,
      'POST',
      { reply_text: replyText },
      DEFAULT_TENANT_ID
    ).catch(() => null);
    if (!response) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? `Unable to reply to review #${id} in strict no-mock mode.`
          : `Unable to reply to review #${id} in fail-closed mode.`
      );
      return;
    }
    setReviews((current) => current.map((item) => (item.id === id ? { ...item, status: 'responded' } : item)));
  }

  async function handleStatusUpdate() {
    const id = Number.parseInt(reviewId, 10);
    if (!Number.isFinite(id)) return;
    const response = await apiSend(`/social/reviews/${id}/status`, 'PATCH', { status }, DEFAULT_TENANT_ID).catch(
      () => null
    );
    if (!response) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? `Unable to update review #${id} in strict no-mock mode.`
          : `Unable to update review #${id} in fail-closed mode.`
      );
      return;
    }
    setReviews((current) => current.map((item) => (item.id === id ? { ...item, status } : item)));
  }

  async function handleCreateCase() {
    const id = Number.parseInt(reviewId, 10);
    if (!Number.isFinite(id)) return;
    const response = await apiSend(
      '/social/care/cases',
      'POST',
      { source_review_id: id, priority: 'high', owner: 'social-care' },
      DEFAULT_TENANT_ID
    ).catch(() => null);
    if (!response) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? `Unable to create case from review #${id} in strict no-mock mode.`
          : `Unable to create case from review #${id} in fail-closed mode.`
      );
      return;
    }
    setCases((current) => [
      {
        id: Date.now(),
        source_review_id: id,
        priority: 'high',
        status: 'new',
        owner: 'social-care',
        created_at: new Date().toISOString(),
      },
      ...current,
    ]);
  }

  const openCount = useMemo(() => reviews.filter((item) => item.status === 'open').length, [reviews]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Review Management</h1>
          <p style={styles.subtitle}>
            Unify review intake, reply workflows, and escalation cases across customer surfaces.
          </p>
        </div>
        <button onClick={() => void loadData()} style={styles.refreshBtn}>
          Refresh
        </button>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      <div style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <span style={styles.kpiLabel}>Total Reviews</span>
          <strong style={styles.kpiValue}>{reviews.length}</strong>
        </div>
        <div style={styles.kpiCard}>
          <span style={styles.kpiLabel}>Open Queue</span>
          <strong style={styles.kpiValue}>{openCount}</strong>
        </div>
        <div style={styles.kpiCard}>
          <span style={styles.kpiLabel}>Care Cases</span>
          <strong style={styles.kpiValue}>{cases.length}</strong>
        </div>
      </div>

      <div style={styles.grid}>
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Reply & Resolve</h2>
          <div style={styles.field}>
            <label style={styles.label}>Review ID</label>
            <input value={reviewId} onChange={(e) => setReviewId(e.target.value)} style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Reply text</label>
            <textarea
              rows={4}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              style={styles.textarea}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as 'open' | 'responded' | 'resolved')}
              style={styles.input}
            >
              <option value="open">Open</option>
              <option value="responded">Responded</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          <div style={styles.actionRow}>
            <button onClick={() => void handleReply()} style={styles.primaryBtn}>
              Reply
            </button>
            <button onClick={() => void handleStatusUpdate()} style={styles.secondaryBtn}>
              Update Status
            </button>
            <button onClick={() => void handleCreateCase()} style={styles.secondaryBtn}>
              Create Case
            </button>
          </div>
        </section>

        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Review Stream</h2>
          {loading ? (
            <p style={styles.muted}>Loading reviews...</p>
          ) : (
            reviews.map((item) => (
              <article key={item.id} style={styles.listItem}>
                <strong>
                  #{item.id} • {item.platform} • {item.rating}/5
                </strong>
                <span style={styles.muted}>
                  {item.author} • {item.status}
                </span>
                <p style={styles.copy}>{item.text}</p>
              </article>
            ))
          )}
        </section>
      </div>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Escalation Cases</h2>
        {cases.length === 0 ? (
          <p style={styles.muted}>No open cases.</p>
        ) : (
          cases.map((item) => (
            <article key={item.id} style={styles.listItem}>
              <strong>Case #{item.id}</strong>
              <span style={styles.muted}>
                Review #{item.source_review_id} • {item.priority} • {item.status} • {item.owner}
              </span>
            </article>
          ))
        )}
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', padding: '32px 24px 60px' },
  header: { display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 24 },
  backLink: { color: '#8fb4ff', textDecoration: 'none', fontSize: 14, display: 'inline-block', marginBottom: 12 },
  title: { margin: 0, fontSize: 34, lineHeight: 1.1 },
  subtitle: { margin: '8px 0 0', color: '#9fb0d1', maxWidth: 780 },
  refreshBtn: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 16px',
    cursor: 'pointer',
  },
  errorBanner: {
    background: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: 14,
    borderRadius: 16,
    marginBottom: 20,
  },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 16, marginBottom: 20 },
  kpiCard: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: 18,
    display: 'grid',
    gap: 8,
  },
  kpiLabel: { color: '#8ea4ca', fontSize: 13 },
  kpiValue: { fontSize: 28 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginBottom: 20 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 16, padding: 20 },
  sectionTitle: { margin: '0 0 16px', fontSize: 20 },
  field: { display: 'grid', gap: 8, marginBottom: 14 },
  label: { fontSize: 13, color: '#9fb0d1' },
  input: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 14px',
  },
  textarea: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 14px',
    resize: 'vertical',
  },
  actionRow: { display: 'flex', flexWrap: 'wrap', gap: 10 },
  primaryBtn: {
    background: '#f97316',
    color: '#fff',
    border: 0,
    borderRadius: 12,
    padding: '12px 16px',
    cursor: 'pointer',
  },
  secondaryBtn: {
    background: 'var(--card)',
    color: '#d7e6ff',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 16px',
    cursor: 'pointer',
  },
  listItem: { display: 'grid', gap: 6, padding: '14px 0', borderTop: '1px solid #1e2a48' },
  muted: { color: '#8ea4ca', fontSize: 13 },
  copy: { margin: 0, color: '#d7e6ff' },
};
