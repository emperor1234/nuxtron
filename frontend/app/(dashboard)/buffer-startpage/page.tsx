'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type StartPageLink = {
  id: string;
  label: string;
  url: string;
  active?: boolean;
  clicks?: number;
  emoji?: string;
};

type SocialLink = {
  network: string;
  url: string;
};

type StartPage = {
  id: string;
  title: string;
  bio: string;
  theme: string;
  accent_color: string;
  background_color: string;
  avatar_url?: string | null;
  slug?: string;
  links: StartPageLink[];
  social_links: SocialLink[];
  views?: number;
};

const card = {
  background: 'var(--bg-soft, #f8fafc)',
  border: '1px solid var(--line, #e2e8f0)',
  borderRadius: 12,
  padding: 16,
} as const;

export default function BufferStartPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [page, setPage] = useState<StartPage | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiGet<{ start_page?: StartPage }>('/social/start-page', tenantId);
      setPage(res.start_page ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Start Page');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  function updatePage<K extends keyof StartPage>(key: K, value: StartPage[K]) {
    setPage((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function updateLink(index: number, key: keyof StartPageLink, value: string) {
    setPage((prev) => {
      if (!prev) return prev;
      const links = [...prev.links];
      links[index] = { ...links[index], [key]: value };
      return { ...prev, links };
    });
  }

  function addLink() {
    setPage((prev) =>
      prev
        ? {
            ...prev,
            links: [
              ...prev.links,
              { id: `draft-${Date.now()}`, label: 'New link', url: 'https://', active: true, clicks: 0, emoji: '🔗' },
            ],
          }
        : prev
    );
  }

  async function save() {
    if (!page) return;
    try {
      await apiSend(
        '/social/start-page',
        'PUT',
        {
          title: page.title,
          bio: page.bio,
          theme: page.theme,
          accent_color: page.accent_color,
          background_color: page.background_color,
          avatar_url: page.avatar_url,
          links: page.links,
          social_links: page.social_links,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg, #f8fafc)', color: 'var(--text, #0f172a)', padding: 24 }}>
      <div style={{ maxWidth: 1260, margin: '0 auto' }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ margin: 0, fontSize: 28 }}>Start Page</h1>
          <p style={{ margin: '6px 0 0', color: '#64748b' }}>
            Build and publish your link-in-bio destination with themes, links, and social handles.
          </p>
        </div>

        {error ? <div style={{ ...card, color: '#b91c1c', marginBottom: 14 }}>{error}</div> : null}
        {loading ? <div style={{ color: '#64748b', padding: 30, textAlign: 'center' }}>Loading Start Page…</div> : null}

        {page ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <section style={{ display: 'grid', gap: 16 }}>
              <div style={card}>
                <h2 style={{ marginTop: 0 }}>Page settings</h2>
                <div style={{ display: 'grid', gap: 10 }}>
                  <input
                    value={page.title}
                    onChange={(event) => updatePage('title', event.target.value)}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '8px 10px',
                      borderRadius: 8,
                      border: '1px solid #cbd5e1',
                    }}
                    placeholder="Title"
                  />
                  <textarea
                    value={page.bio}
                    onChange={(event) => updatePage('bio', event.target.value)}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      minHeight: 90,
                      padding: '8px 10px',
                      borderRadius: 8,
                      border: '1px solid #cbd5e1',
                    }}
                    placeholder="Bio"
                  />
                  <select
                    value={page.theme}
                    onChange={(event) => updatePage('theme', event.target.value)}
                    style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
                  >
                    {['minimal', 'bold', 'elegant', 'creator'].map((theme) => (
                      <option key={theme} value={theme}>
                        {theme}
                      </option>
                    ))}
                  </select>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <label style={{ fontSize: 13, color: '#475569' }}>
                      Accent color
                      <input
                        type="color"
                        value={page.accent_color}
                        onChange={(event) => updatePage('accent_color', event.target.value)}
                        style={{
                          width: '100%',
                          height: 42,
                          border: '1px solid #cbd5e1',
                          borderRadius: 8,
                          marginTop: 4,
                        }}
                      />
                    </label>
                    <label style={{ fontSize: 13, color: '#475569' }}>
                      Background color
                      <input
                        type="color"
                        value={page.background_color}
                        onChange={(event) => updatePage('background_color', event.target.value)}
                        style={{
                          width: '100%',
                          height: 42,
                          border: '1px solid #cbd5e1',
                          borderRadius: 8,
                          marginTop: 4,
                        }}
                      />
                    </label>
                  </div>
                  <input
                    value={page.avatar_url || ''}
                    onChange={(event) => updatePage('avatar_url', event.target.value)}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '8px 10px',
                      borderRadius: 8,
                      border: '1px solid #cbd5e1',
                    }}
                    placeholder="Avatar URL"
                  />
                </div>
              </div>

              <div style={card}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 10,
                    alignItems: 'center',
                    marginBottom: 12,
                  }}
                >
                  <h2 style={{ margin: 0 }}>Links</h2>
                  <button
                    onClick={addLink}
                    style={{
                      border: 'none',
                      borderRadius: 10,
                      padding: '8px 12px',
                      background: '#6366f1',
                      color: '#fff',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Add link
                  </button>
                </div>
                <div style={{ display: 'grid', gap: 10 }}>
                  {page.links.map((link, index) => (
                    <div key={link.id} style={{ padding: 12, borderRadius: 10, background: '#fff' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '70px 1fr', gap: 10, marginBottom: 10 }}>
                        <input
                          value={link.emoji || ''}
                          onChange={(event) => updateLink(index, 'emoji', event.target.value)}
                          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
                          placeholder="Icon"
                        />
                        <input
                          value={link.label}
                          onChange={(event) => updateLink(index, 'label', event.target.value)}
                          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
                          placeholder="Label"
                        />
                      </div>
                      <input
                        value={link.url}
                        onChange={(event) => updateLink(index, 'url', event.target.value)}
                        style={{
                          width: '100%',
                          boxSizing: 'border-box',
                          padding: '8px 10px',
                          borderRadius: 8,
                          border: '1px solid #cbd5e1',
                        }}
                        placeholder="URL"
                      />
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 8 }}>Clicks: {link.clicks || 0}</div>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => void save()}
                style={{
                  border: 'none',
                  borderRadius: 10,
                  padding: '11px 14px',
                  background: '#10b981',
                  color: '#fff',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Save Start Page
              </button>
            </section>

            <aside>
              <div style={{ ...card, position: 'sticky', top: 24 }}>
                <h2 style={{ marginTop: 0 }}>Live preview</h2>
                <div
                  style={{
                    borderRadius: 24,
                    padding: 24,
                    background: page.background_color,
                    color: 'var(--text)',
                    border: `2px solid ${page.accent_color}`,
                  }}
                >
                  {page.avatar_url ? (
                    <img
                      src={page.avatar_url}
                      alt={page.title}
                      style={{
                        width: 84,
                        height: 84,
                        borderRadius: '50%',
                        objectFit: 'cover',
                        display: 'block',
                        margin: '0 auto 16px',
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: 84,
                        height: 84,
                        borderRadius: '50%',
                        background: page.accent_color,
                        margin: '0 auto 16px',
                        display: 'grid',
                        placeItems: 'center',
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: 24,
                      }}
                    >
                      {page.title.slice(0, 1) || 'S'}
                    </div>
                  )}
                  <div style={{ textAlign: 'center', marginBottom: 20 }}>
                    <div style={{ fontSize: 22, fontWeight: 700 }}>{page.title}</div>
                    <div style={{ color: '#475569', marginTop: 6 }}>{page.bio}</div>
                    <div style={{ color: '#64748b', fontSize: 12, marginTop: 6 }}>
                      /{page.slug || 'start-page'} · {page.views || 0} views
                    </div>
                  </div>
                  <div style={{ display: 'grid', gap: 10 }}>
                    {page.links.map((link) => (
                      <div
                        key={link.id}
                        style={{
                          borderRadius: 16,
                          padding: '12px 14px',
                          background: '#fff',
                          border: '1px solid rgba(15, 23, 42, 0.08)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <span>
                          {link.emoji || '🔗'} {link.label}
                        </span>
                        <span style={{ color: page.accent_color }}>↗</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </aside>
          </div>
        ) : null}
      </div>
    </main>
  );
}
