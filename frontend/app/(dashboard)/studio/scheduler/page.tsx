'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type ScheduledPost = {
  id: string;
  title: string;
  caption?: string;
  platform: string;
  platforms?: string[];
  time: string;
  status: string;
};

export default function SchedulerPage() {
  const tenantId = DEFAULT_TENANT_ID || 'tenant-demo';
  const [scheduled, setScheduled] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const [platform, setPlatform] = useState('twitter');
  const [datetime, setDatetime] = useState('');

  async function loadScheduled() {
    setLoading(true);
    try {
      const data = await apiGet<{ items: Array<Record<string, unknown>> }>(
        '/social/content/list?status=scheduled&limit=50',
        tenantId
      );
      const items: ScheduledPost[] = (data.items || []).map((item) => ({
        id: String(item.id ?? ''),
        title: String(item.title ?? ''),
        caption: item.caption ? String(item.caption) : undefined,
        platform: Array.isArray(item.platforms) ? ((item.platforms as string[])[0] ?? '') : '',
        platforms: Array.isArray(item.platforms) ? (item.platforms as string[]) : [],
        time: item.scheduled_for ? new Date(String(item.scheduled_for)).toLocaleString() : 'TBD',
        status: String(item.status ?? 'scheduled'),
      }));
      setScheduled(items);
    } catch {
      setError('Failed to load scheduled posts');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadScheduled();
  }, []);

  async function schedulePost() {
    if (!content.trim() || !datetime) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiSend(
        '/social/content/create',
        'POST',
        {
          title: content.slice(0, 80),
          caption: content,
          media_assets: [],
          platforms: [platform],
          requires_approval: false,
          scheduled_for: new Date(datetime).toISOString(),
        },
        tenantId
      );
      setContent('');
      setDatetime('');
      await loadScheduled();
    } catch {
      setError('Failed to schedule post. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Autonomous Scheduler</p>
        <h1>Cross-Platform Content Scheduling</h1>
        <p>Smart timing intelligence and campaign orchestration across all your channels.</p>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginTop: 20 }}>
        <section className="card" style={{ height: 'fit-content', padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Schedule Post</h3>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            >
              <option value="twitter">Twitter/X</option>
              <option value="linkedin">LinkedIn</option>
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
              <option value="tiktok">TikTok</option>
            </select>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your post..."
              rows={5}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Publish Time</label>
            <input
              type="datetime-local"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>

          {error && <p style={{ color: '#f44', fontSize: 12, marginBottom: 8 }}>{error}</p>}

          <button
            onClick={() => void schedulePost()}
            disabled={submitting || !content.trim() || !datetime}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: 8,
              border: 'none',
              background: submitting || !content.trim() || !datetime ? 'var(--muted)' : 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: submitting || !content.trim() || !datetime ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? 'Scheduling…' : 'Schedule Post'}
          </button>
        </section>

        <section className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Scheduled Posts ({loading ? '…' : scheduled.length})</h3>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>Loading…</p>
            </div>
          ) : scheduled.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>No scheduled posts. Schedule one now!</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {scheduled.map((post) => (
                <div
                  key={post.id}
                  style={{
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: 12,
                    background: 'rgba(255, 255, 255, 0.03)',
                  }}
                >
                  <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}
                  >
                    <strong style={{ textTransform: 'uppercase', fontSize: 11, color: 'var(--muted)' }}>
                      {post.platforms?.join(', ') || post.platform}
                    </strong>
                    <span style={{ fontSize: 11, color: 'var(--brand)' }}>{post.status}</span>
                  </div>
                  <p style={{ margin: '0 0 8px', fontSize: 13 }}>{post.title}</p>
                  {post.caption && (
                    <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--muted)' }}>{post.caption}</p>
                  )}
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>📅 {post.time}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
