'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type ScheduledPost = {
  id: string;
  title: string;
  caption: string;
  platforms: string[];
  scheduled_for: string | null;
  status: string;
};

export default function SocialSchedulingPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [platform, setPlatform] = useState('linkedin');
  const [text, setText] = useState('Launching new workflow automations this week.');
  // eslint-disable-next-line react-hooks/purity
  const [publishAt, setPublishAt] = useState(new Date(Date.now() + 3_600_000).toISOString().slice(0, 16));
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const res = await apiGet<{
        items?: Array<{
          id: string;
          title: string;
          caption?: string;
          platforms: string[];
          scheduled_for?: string | null;
          status: string;
        }>;
      }>('/api/v1/social/content/list', tenantId);
      setPosts(
        (res.items ?? []).map((item) => ({
          id: item.id,
          title: item.title,
          caption: item.caption ?? item.title,
          platforms: item.platforms,
          scheduled_for: item.scheduled_for ?? null,
          status: item.status,
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load scheduled posts');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function schedule() {
    try {
      await apiSend(
        '/api/v1/social/content/create',
        'POST',
        {
          title: text.length > 72 ? `${text.slice(0, 69)}...` : text,
          caption: text,
          media_assets: [],
          platforms: [platform],
          requires_approval: false,
          scheduled_for: new Date(publishAt).toISOString(),
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Schedule failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Social Scheduling</h1>
        <p style={{ color: 'var(--muted)' }}>
          Queue posts with publish windows and manage the upcoming content calendar.
        </p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}
        <section style={card}>
          <select style={input} value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="linkedin">linkedin</option>
            <option value="x">x</option>
            <option value="instagram">instagram</option>
            <option value="facebook">facebook</option>
          </select>
          <textarea style={{ ...input, minHeight: 90 }} value={text} onChange={(e) => setText(e.target.value)} />
          <input style={input} type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} />
          <button
            onClick={() => void schedule()}
            style={{
              padding: '8px 12px',
              border: 'none',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
            }}
          >
            Schedule Post
          </button>
        </section>
        <section style={{ ...card, marginTop: 10 }}>
          <h3 style={{ marginTop: 0 }}>Scheduled Posts ({posts.length})</h3>
          {posts.map((p) => (
            <div key={p.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
              <div style={{ fontWeight: 700 }}>
                {p.platforms.join(', ')} · {p.status}
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                {p.scheduled_for ? new Date(p.scheduled_for).toLocaleString() : 'Not scheduled'}
              </div>
              <div style={{ fontSize: 13 }}>{p.caption}</div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
