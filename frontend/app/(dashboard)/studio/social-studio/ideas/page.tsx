'use client';

import { useEffect, useState, useCallback } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Idea = {
  id: string;
  tenant_id?: string;
  title: string;
  body?: string;
  status: string;
  tags?: string[];
  networks?: string[];
  created_at?: string;
};

type Template = {
  id: string;
  name: string;
  content_type: string;
  body: string;
  networks: string[];
  tags: string[];
};

type HashtagGroup = {
  id: string;
  name: string;
  hashtags: string[];
  description: string;
};

const KANBAN_COLUMNS: { key: string; label: string; color: string }[] = [
  { key: 'new', label: 'Ideas', color: "var(--brand)" },
  { key: 'researching', label: 'In Progress', color: 'var(--warning)' },
  { key: 'ready', label: 'Ready to Post', color: 'var(--success)' },
  { key: 'queued', label: 'Queued', color: "var(--brand)" },
];

const NETWORK_OPTIONS = [
  'instagram',
  'facebook',
  'linkedin',
  'x',
  'tiktok',
  'youtube',
  'threads',
  'bluesky',
  'pinterest',
];

const card: React.CSSProperties = {
  background: 'var(--bg-soft)',
  border: '1px solid var(--line)',
  borderRadius: 10,
  padding: 14,
};

const btn = (color = 'var(--info)'): React.CSSProperties => ({
  background: color,
  color: 'var(--on-status)',
  border: 'none',
  borderRadius: 8,
  padding: '8px 14px',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 600,
});

const input: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 8,
  border: '1px solid var(--line)',
  background: 'var(--bg)',
  color: 'var(--text)',
  marginBottom: 8,
  boxSizing: 'border-box',
};

function tabLabel(tab: 'board' | 'list' | 'templates' | 'hashtags'): string {
  if (tab === 'board') return '📋 Board';
  if (tab === 'list') return '☰ List';
  if (tab === 'templates') return '📄 Templates';
  return '#️⃣ Hashtags';
}

function statusTone(status: string): { background: string; color: string } {
  if (status === 'queued') return { background: 'var(--info-soft)', color: "var(--brand)" };
  if (status === 'ready') return { background: 'var(--success-soft)', color: 'var(--success-ink)' };
  if (status === 'researching') return { background: 'var(--warning-line)', color: 'var(--warning-ink)' };
  return { background: 'var(--bg-soft)', color: 'var(--ink-2)' };
}

export default function IdeasDraftsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [view, setView] = useState<'board' | 'list' | 'templates' | 'hashtags'>('board');
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [hashtagGroups, setHashtagGroups] = useState<HashtagGroup[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // New idea form
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newNetworks, setNewNetworks] = useState<string[]>(['instagram']);
  const [newTags, setNewTags] = useState('');
  const [showForm, setShowForm] = useState(false);

  // AI assistant
  const [aiText, setAiText] = useState('');
  const [aiAction, setAiAction] = useState('rephrase');
  const [aiResult, setAiResult] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showAI, setShowAI] = useState(false);

  // Hashtag group form
  const [hgName, setHgName] = useState('');
  const [hgTags, setHgTags] = useState('');
  const [hgDesc, setHgDesc] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ideasRes, tmplRes, hgRes] = await Promise.all([
        apiGet<{ items?: Idea[] }>('/social/ideas', tenantId),
        apiGet<{ templates?: Template[] }>('/social/templates', tenantId),
        apiGet<{ hashtag_groups?: HashtagGroup[] }>('/social/hashtag-groups', tenantId),
      ]);
      setIdeas(ideasRes.items ?? []);
      setTemplates(tmplRes.templates ?? []);
      setHashtagGroups(hgRes.hashtag_groups ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    // Fetch on mount and whenever the filters behind `load` change.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function createIdea() {
    if (!newTitle.trim()) return;
    try {
      await apiSend(
        '/social/ideas',
        'POST',
        {
          title: newTitle.trim(),
          body: newBody.trim(),
          source: newNetworks[0] || 'manual',
          tags: newTags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean),
        },
        tenantId
      );
      setNewTitle('');
      setNewBody('');
      setNewTags('');
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  async function queueIdea(ideaId: string) {
    try {
      await apiSend(
        `/social/ideas/${ideaId}/queue`,
        'POST',
        {
          network: newNetworks[0] || 'instagram',
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Queue failed');
    }
  }

  async function runAI() {
    if (!aiText.trim()) return;
    setAiLoading(true);
    try {
      const res = await apiSend<{ result?: string }>(
        '/social/ai-assistant',
        'POST',
        {
          text: aiText,
          action: aiAction,
        },
        tenantId
      );
      setAiResult(res.result ?? '');
    } catch (e) {
      setAiResult(`Error: ${e instanceof Error ? e.message : 'AI call failed'}`);
    } finally {
      setAiLoading(false);
    }
  }

  async function createHashtagGroup() {
    if (!hgName.trim() || !hgTags.trim()) return;
    try {
      await apiSend(
        '/social/hashtag-groups',
        'POST',
        {
          name: hgName.trim(),
          hashtags: hgTags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean),
          description: hgDesc.trim(),
        },
        tenantId
      );
      setHgName('');
      setHgTags('');
      setHgDesc('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create hashtag group failed');
    }
  }

  async function deleteHashtagGroup(id: string) {
    try {
      await apiSend(`/social/hashtag-groups/${id}`, 'DELETE', undefined, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  function applyTemplate(tmpl: Template) {
    setNewTitle(tmpl.name);
    setNewBody(tmpl.body);
    setNewNetworks(tmpl.networks.length ? tmpl.networks : ['instagram']);
    setView('board');
    setShowForm(true);
  }

  function toggleNetwork(network: string) {
    setNewNetworks((prev) => (prev.includes(network) ? prev.filter((item) => item !== network) : [...prev, network]));
  }

  const ideasByStatus = KANBAN_COLUMNS.reduce<Record<string, Idea[]>>((acc, col) => {
    acc[col.key] = ideas.filter((i) => i.status === col.key);
    return acc;
  }, {});

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 18px',
    borderRadius: 8,
    border: 'none',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 13,
    background: active ? "var(--brand)" : 'var(--bg-soft)',
    color: active ? 'var(--on-status)' : 'var(--text)',
  });

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1300, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700 }}>Ideas &amp; Drafts</h1>
            <p style={{ margin: '4px 0 0', color: "var(--muted)", fontSize: 14 }}>
              Dream up, gather, and polish your content ideas in one place.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              style={btn('var(--success)')}
              onClick={() => {
                setShowForm(true);
                setView('board');
              }}
            >
              + New Idea
            </button>
            <button style={btn('var(--info)')} onClick={() => setShowAI(!showAI)}>
              ✨ AI Assistant
            </button>
          </div>
        </div>

        {error && <div style={{ ...card, color: 'var(--danger)', marginBottom: 12 }}>{error}</div>}

        {/* AI Assistant Panel */}
        {showAI && (
          <div style={{ ...card, marginBottom: 20, borderColor: "var(--brand)", borderWidth: 2 }}>
            <h3 style={{ margin: '0 0 12px', color: "var(--brand)" }}>✨ AI Assistant</h3>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              {(['rephrase', 'shorten', 'expand', 'casual', 'formal', 'generate'] as const).map((a) => (
                <button
                  key={a}
                  onClick={() => setAiAction(a)}
                  style={{
                    ...btn(aiAction === a ? 'var(--info)' : 'var(--neutral-soft)'),
                    color: aiAction === a ? 'var(--on-status)' : 'var(--ink-2)',
                    fontSize: 12,
                    padding: '6px 12px',
                  }}
                >
                  {a}
                </button>
              ))}
            </div>
            <textarea
              style={{ ...input, height: 80, resize: 'vertical', fontFamily: 'inherit' }}
              placeholder="Enter your post text or topic..."
              value={aiText}
              onChange={(e) => setAiText(e.target.value)}
            />
            <button style={btn('var(--info)')} onClick={runAI} disabled={aiLoading}>
              {aiLoading ? 'Processing…' : 'Generate'}
            </button>
            {aiResult && (
              <div
                style={{
                  marginTop: 12,
                  padding: 12,
                  background: 'var(--bg-soft)',
                  borderRadius: 8,
                  border: '1px solid var(--info-line)',
                }}
              >
                <div style={{ fontSize: 12, color: "var(--brand)", fontWeight: 600, marginBottom: 4 }}>Result</div>
                <div style={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>{aiResult}</div>
                <button
                  style={{ ...btn('var(--info)'), marginTop: 8, fontSize: 12, padding: '6px 10px' }}
                  onClick={() => {
                    setNewBody(aiResult);
                    setShowForm(true);
                  }}
                >
                  Use in new post
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {(['board', 'list', 'templates', 'hashtags'] as const).map((v) => (
            <button key={v} style={tabStyle(view === v)} onClick={() => setView(v)}>
              {tabLabel(v)}
            </button>
          ))}
        </div>

        {/* New idea form */}
        {showForm && view !== 'templates' && view !== 'hashtags' && (
          <div style={{ ...card, marginBottom: 20, borderColor: "var(--brand)", borderWidth: 2 }}>
            <h3 style={{ margin: '0 0 12px' }}>New Idea</h3>
            <input style={input} placeholder="Title *" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            <textarea
              style={{ ...input, height: 80, resize: 'vertical', fontFamily: 'inherit' }}
              placeholder="Body / content..."
              value={newBody}
              onChange={(e) => setNewBody(e.target.value)}
            />
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>Networks</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {NETWORK_OPTIONS.map((net) => (
                  <button
                    key={net}
                    onClick={() => toggleNetwork(net)}
                    style={{
                      ...btn(newNetworks.includes(net) ? 'var(--info)' : 'var(--neutral-soft)'),
                      color: newNetworks.includes(net) ? 'var(--on-status)' : 'var(--ink-2)',
                      fontSize: 12,
                      padding: '4px 10px',
                    }}
                  >
                    {net}
                  </button>
                ))}
              </div>
            </div>
            <input
              style={input}
              placeholder="Tags (comma-separated)"
              value={newTags}
              onChange={(e) => setNewTags(e.target.value)}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={btn('var(--success)')} onClick={createIdea}>
                Save Idea
              </button>
              <button style={btn('var(--neutral)')} onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {loading && <div style={{ color: "var(--muted)", textAlign: 'center', padding: 40 }}>Loading…</div>}

        {/* Board View */}
        {!loading && view === 'board' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 16 }}>
            {KANBAN_COLUMNS.map((col) => (
              <div key={col.key}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: col.color }} />
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{col.label}</span>
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: 12,
                      color: "var(--muted)",
                      background: 'var(--bg-soft)',
                      borderRadius: 16,
                      padding: '2px 8px',
                    }}
                  >
                    {ideasByStatus[col.key]?.length ?? 0}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 120 }}>
                  {(ideasByStatus[col.key] ?? []).map((idea) => (
                    <div key={idea.id} style={{ ...card, borderLeft: `3px solid ${col.color}`, cursor: 'default' }}>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{idea.title}</div>
                      {idea.body && (
                        <div
                          style={{
                            fontSize: 12,
                            color: "var(--muted)",
                            marginBottom: 6,
                            overflow: 'hidden',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                          }}
                        >
                          {idea.body}
                        </div>
                      )}
                      {idea.networks && idea.networks.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                          {idea.networks.map((n) => (
                            <span
                              key={n}
                              style={{
                                fontSize: 10,
                                background: 'var(--info-soft)',
                                color: "var(--brand)",
                                borderRadius: 4,
                                padding: '1px 6px',
                              }}
                            >
                              {n}
                            </span>
                          ))}
                        </div>
                      )}
                      {col.key === 'new' && (
                        <button
                          style={{ ...btn('var(--info)'), fontSize: 11, padding: '4px 8px' }}
                          onClick={() => queueIdea(idea.id)}
                        >
                          Add to Queue →
                        </button>
                      )}
                    </div>
                  ))}
                  {(ideasByStatus[col.key] ?? []).length === 0 && (
                    <div
                      style={{
                        padding: 20,
                        textAlign: 'center',
                        color: 'var(--neutral)',
                        fontSize: 13,
                        border: '2px dashed var(--neutral-soft)',
                        borderRadius: 8,
                      }}
                    >
                      No {col.label.toLowerCase()} yet
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* List View */}
        {!loading && view === 'list' && (
          <div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 1fr 1fr 80px',
                gap: 8,
                padding: '10px 14px',
                background: 'var(--bg-soft)',
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 12,
                color: 'var(--ink-2)',
                marginBottom: 8,
              }}
            >
              <span>Title</span>
              <span>Networks</span>
              <span>Status</span>
              <span>Tags</span>
              <span>Action</span>
            </div>
            {ideas.map((idea) => (
              <div
                key={idea.id}
                style={{
                  ...card,
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr 1fr 1fr 80px',
                  gap: 8,
                  alignItems: 'center',
                  marginBottom: 6,
                  padding: '10px 14px',
                }}
              >
                <span style={{ fontWeight: 600, fontSize: 13 }}>{idea.title}</span>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>{(idea.networks ?? []).join(', ') || '—'}</span>
                <span>
                  <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 16, ...statusTone(idea.status) }}>
                    {idea.status}
                  </span>
                </span>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>{(idea.tags ?? []).join(', ') || '—'}</span>
                {idea.status === 'new' && (
                  <button
                    style={{ ...btn('var(--info)'), fontSize: 11, padding: '4px 8px' }}
                    onClick={() => queueIdea(idea.id)}
                  >
                    Queue
                  </button>
                )}
              </div>
            ))}
            {ideas.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--neutral)', padding: 40 }}>
                No ideas yet. Create your first idea!
              </div>
            )}
          </div>
        )}

        {/* Templates View */}
        {!loading && view === 'templates' && (
          <div>
            <h2 style={{ marginTop: 0 }}>Content Templates</h2>
            <p style={{ color: "var(--muted)", marginBottom: 20 }}>
              Jump-start your posts with proven templates for every occasion.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: 16 }}>
              {templates.map((tmpl) => (
                <div key={tmpl.id} style={card}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      marginBottom: 8,
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{tmpl.name}</div>
                      <span
                        style={{
                          fontSize: 11,
                          background: 'var(--bg-soft)',
                          color: 'var(--ink-2)',
                          borderRadius: 4,
                          padding: '1px 8px',
                        }}
                      >
                        {tmpl.content_type}
                      </span>
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--muted)",
                      whiteSpace: 'pre-wrap',
                      marginBottom: 10,
                      maxHeight: 100,
                      overflow: 'hidden',
                    }}
                  >
                    {tmpl.body}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 10 }}>
                    {tmpl.networks.map((n) => (
                      <span
                        key={n}
                        style={{
                          fontSize: 10,
                          background: 'var(--info-soft)',
                          color: "var(--brand)",
                          borderRadius: 4,
                          padding: '1px 6px',
                        }}
                      >
                        {n}
                      </span>
                    ))}
                  </div>
                  <button style={btn('var(--info)')} onClick={() => applyTemplate(tmpl)}>
                    Use Template
                  </button>
                </div>
              ))}
              {templates.length === 0 && <div style={{ color: 'var(--neutral)' }}>No templates found.</div>}
            </div>
          </div>
        )}

        {/* Hashtag Manager */}
        {!loading && view === 'hashtags' && (
          <div>
            <h2 style={{ marginTop: 0 }}>Hashtag Manager</h2>
            <p style={{ color: "var(--muted)", marginBottom: 20 }}>Save groups of hashtags to quickly add to your posts.</p>

            {/* Create group form */}
            <div style={{ ...card, marginBottom: 20 }}>
              <h3 style={{ margin: '0 0 12px' }}>Create Hashtag Group</h3>
              <input
                style={input}
                placeholder="Group name *"
                value={hgName}
                onChange={(e) => setHgName(e.target.value)}
              />
              <input
                style={input}
                placeholder="Hashtags (comma-separated, e.g. #marketing, #growth) *"
                value={hgTags}
                onChange={(e) => setHgTags(e.target.value)}
              />
              <input
                style={input}
                placeholder="Description (optional)"
                value={hgDesc}
                onChange={(e) => setHgDesc(e.target.value)}
              />
              <button style={btn('var(--success)')} onClick={createHashtagGroup}>
                Create Group
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 16 }}>
              {hashtagGroups.map((hg) => (
                <div key={hg.id} style={card}>
                  <div
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}
                  >
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{hg.name}</div>
                    <button
                      style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: 16 }}
                      onClick={() => deleteHashtagGroup(hg.id)}
                    >
                      🗑
                    </button>
                  </div>
                  {hg.description && (
                    <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>{hg.description}</div>
                  )}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {hg.hashtags.map((tag) => (
                      <span
                        key={tag}
                        style={{
                          fontSize: 12,
                          background: 'var(--bg-soft)',
                          color: "var(--brand)",
                          borderRadius: 4,
                          padding: '2px 8px',
                        }}
                      >
                        #{tag.replace(/^#/, '')}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: 10, fontSize: 12, color: "var(--muted)" }}>{hg.hashtags.length} hashtags</div>
                  <button
                    style={{ ...btn('var(--info)'), fontSize: 12, marginTop: 8 }}
                    onClick={() => {
                      setNewTags(hg.hashtags.join(', '));
                      setView('board');
                      setShowForm(true);
                    }}
                  >
                    Use in new post
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
