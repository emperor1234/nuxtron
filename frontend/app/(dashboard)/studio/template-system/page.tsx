'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Template = {
  id: string;
  name: string;
  category: string;
  platforms: string[];
  source: string;
  thumbnail: string;
  format: string;
  slides?: number;
  editable?: boolean;
  imported_at?: string;
};

type TemplatesResponse = {
  templates: Template[];
};

type TemplateImportResponse = {
  template: Template;
};

const CATEGORIES = ['all', 'product', 'promotion', 'engagement', 'video', 'education', 'event', 'social-proof', 'custom'];
const PLATFORM_FILTERS = ['all', 'instagram', 'facebook', 'tiktok', 'linkedin', 'youtube', 'twitter'];
const SOURCE_TYPES = [
  { id: 'canva', label: 'Canva', icon: '🎨', hint: 'Paste a Canva share URL' },
  { id: 'figma', label: 'Figma', icon: '✏️', hint: 'Paste a Figma file URL' },
  { id: 'adobe', label: 'Adobe Express', icon: '🅰️', hint: 'Paste an Adobe Express URL' },
  { id: 'url', label: 'Direct URL', icon: '🔗', hint: 'Any image/template URL' },
];

export default function TemplateSystemPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'gallery' | 'import'>('gallery');

  // Import form
  const [importUrl, setImportUrl] = useState('');
  const [importName, setImportName] = useState('');
  const [importSource, setImportSource] = useState('url');
  const [importCategory, setImportCategory] = useState('custom');
  const [importPlatforms, setImportPlatforms] = useState<string[]>(['instagram']);

  useEffect(() => { loadTemplates(); }, [categoryFilter, platformFilter]);

  async function loadTemplates() {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ tenant_id: DEFAULT_TENANT_ID });
      if (categoryFilter !== 'all') params.set('category', categoryFilter);
      if (platformFilter !== 'all') params.set('platform', platformFilter);
      const data = await apiGet<TemplatesResponse>(`/ai/social-studio/templates?${params}`, DEFAULT_TENANT_ID);
      setTemplates(data.templates ?? []);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); }
  }

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    if (!importUrl.trim()) { setError('Source URL is required.'); return; }
    if (!importName.trim()) { setError('Template name is required.'); return; }
    setImporting(true); setError(null);
    try {
      const data = await apiSend<TemplateImportResponse>('/ai/social-studio/template-import', 'POST', {
        source_url: importUrl,
        source_type: importSource,
        name: importName,
        category: importCategory,
        platforms: importPlatforms,
      }, DEFAULT_TENANT_ID);
      setSuccessMsg(`✅ "${data.template.name}" imported successfully!`);
      setTimeout(() => setSuccessMsg(null), 5000);
      setImportUrl(''); setImportName('');
      setActiveTab('gallery');
      loadTemplates();
    } catch (e: unknown) { setError(String(e)); }
    finally { setImporting(false); }
  }

  const filtered = templates.filter((t) => {
    if (searchQuery && !t.name.toLowerCase().includes(searchQuery.toLowerCase()) && !t.category.includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const sourceHint = SOURCE_TYPES.find((s) => s.id === importSource)?.hint ?? '';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>📐 Template System</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>CANVA · FIGMA · ADOBE</span>
        </div>
        <button onClick={() => setActiveTab('import')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
          + Import Template
        </button>
      </div>

      {/* Tabs */}
      <div style={{ padding: '0 32px', borderBottom: '1px solid var(--line)', background: 'var(--card)', display: 'flex' }}>
        {(['gallery', 'import'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: 'none', border: 'none', color: activeTab === tab ? 'var(--brand)' : 'var(--muted)', padding: '14px 20px', cursor: 'pointer', fontSize: 14, fontWeight: activeTab === tab ? 600 : 400, borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent' }}>
            {{ gallery: '🖼 Template Gallery', import: '⬆ Import from Canva/Figma/Adobe' }[tab]}
          </button>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1400, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}
        {successMsg && <div style={{ background: '#dcfce733', border: '1px solid #22c55e', borderRadius: 8, padding: 12, marginBottom: 16, color: '#15803d' }}>{successMsg}</div>}

        {activeTab === 'gallery' && (
          <div>
            {/* Filters */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' }}>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="🔍 Search templates…"
                style={{ background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '8px 14px', borderRadius: 8, fontSize: 14, minWidth: 200 }}
              />
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {CATEGORIES.map((cat) => (
                  <button key={cat} onClick={() => setCategoryFilter(cat)} style={{ background: categoryFilter === cat ? '#6366f133' : '#eef0f4', border: `1px solid ${categoryFilter === cat ? '#6366f1' : '#e7e9ef'}`, color: categoryFilter === cat ? 'var(--brand)' : 'var(--muted)', padding: '5px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12, textTransform: 'capitalize' }}>
                    {cat}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {PLATFORM_FILTERS.map((p) => (
                  <button key={p} onClick={() => setPlatformFilter(p)} style={{ background: platformFilter === p ? '#F59E0B33' : '#eef0f4', border: `1px solid ${platformFilter === p ? '#F59E0B' : '#e7e9ef'}`, color: platformFilter === p ? '#F59E0B' : 'var(--muted)', padding: '5px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12, textTransform: 'capitalize' }}>
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--muted)' }}>Loading templates…</div>
            ) : filtered.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>📐</div>
                <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No templates found</div>
                <button onClick={() => setActiveTab('import')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>Import Template</button>
              </div>
            ) : (
              <>
                <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>{filtered.length} templates</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 16 }}>
                  {filtered.map((t) => (
                    <div key={t.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden', cursor: 'pointer', transition: 'border-color 0.15s' }}>
                      <div style={{ height: 160, background: `#e7e9ef url(${t.thumbnail}) center/cover no-repeat`, position: 'relative' }}>
                        <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 4 }}>
                          <span style={{ background: '#000000aa', color: '#fff', fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>{t.format}</span>
                          {t.slides && <span style={{ background: '#6366f1aa', color: '#fff', fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>{t.slides} slides</span>}
                        </div>
                        <div style={{ position: 'absolute', top: 8, right: 8 }}>
                          <span style={{ background: t.source === 'built-in' ? '#22C55E33' : '#818CF833', color: t.source === 'built-in' ? '#22c55e' : 'var(--brand)', fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>
                            {t.source === 'built-in' ? 'Built-in' : t.source}
                          </span>
                        </div>
                      </div>
                      <div style={{ padding: 12 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{t.name}</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'capitalize' }}>{t.category}</span>
                          <div style={{ display: 'flex', gap: 4 }}>
                            {t.platforms.slice(0, 3).map((p) => (
                              <span key={p} style={{ background: '#e7e9ef', color: 'var(--muted)', fontSize: 9, padding: '1px 5px', borderRadius: 3 }}>{p.slice(0, 2).toUpperCase()}</span>
                            ))}
                          </div>
                        </div>
                        <button style={{ marginTop: 8, width: '100%', background: '#6366f133', color: 'var(--brand)', border: '1px solid #6366f144', padding: '6px 0', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                          Use Template →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'import' && (
          <div style={{ maxWidth: 700, margin: '0 auto' }}>
            <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 32 }}>
              <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Import Template</div>
              <div style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 24 }}>Import designs from Canva, Figma, Adobe Express, or any image URL.</div>

              <form onSubmit={handleImport}>
                {/* Source Type */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 10, fontWeight: 600 }}>SOURCE PLATFORM</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 10 }}>
                    {SOURCE_TYPES.map((s) => (
                      <button key={s.id} type="button" onClick={() => setImportSource(s.id)} style={{ background: importSource === s.id ? '#6366f133' : '#eef0f4', border: `1px solid ${importSource === s.id ? '#6366f1' : '#e7e9ef'}`, borderRadius: 10, padding: 14, cursor: 'pointer', textAlign: 'center', color: importSource === s.id ? 'var(--brand)' : 'var(--muted)' }}>
                        <div style={{ fontSize: 24, marginBottom: 6 }}>{s.icon}</div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{s.label}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* URL */}
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>SOURCE URL *</label>
                  <input value={importUrl} onChange={(e) => setImportUrl(e.target.value)} placeholder={sourceHint || 'https://...'} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
                  {sourceHint && <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{sourceHint}</div>}
                </div>

                {/* Name */}
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>TEMPLATE NAME *</label>
                  <input value={importName} onChange={(e) => setImportName(e.target.value)} placeholder="e.g. Summer Sale Banner" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
                </div>

                {/* Category & Platforms */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 24 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>CATEGORY</label>
                    <select value={importCategory} onChange={(e) => setImportCategory(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                      {CATEGORIES.filter((c) => c !== 'all').map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PLATFORMS</label>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {PLATFORM_FILTERS.filter((p) => p !== 'all').map((p) => (
                        <button key={p} type="button" onClick={() => setImportPlatforms((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p])} style={{ background: importPlatforms.includes(p) ? '#6366f133' : '#eef0f4', border: `1px solid ${importPlatforms.includes(p) ? '#6366f1' : '#e7e9ef'}`, color: importPlatforms.includes(p) ? 'var(--brand)' : 'var(--muted)', padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11, textTransform: 'capitalize' }}>
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <button type="submit" disabled={importing} style={{ width: '100%', background: importing ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: importing ? 'not-allowed' : 'pointer' }}>
                  {importing ? '⏳ Importing…' : '⬆ Import Template'}
                </button>
              </form>
            </div>

            {/* Vendor info */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginTop: 20 }}>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12, fontWeight: 600, letterSpacing: 1 }}>SUPPORTED INTEGRATIONS</div>
              {[
                { name: 'Canva Connect API', env: 'CANVA_CLIENT_ID + CANVA_CLIENT_SECRET', desc: 'Import Canva designs, auto-sync on update' },
                { name: 'Figma REST API', env: 'FIGMA_ACCESS_TOKEN', desc: 'Import Figma frames as editable templates' },
                { name: 'Adobe Creative SDK', env: 'ADOBE_CLIENT_ID', desc: 'Import Adobe Express exports' },
                { name: 'Direct URL', env: 'No env required', desc: 'Import any publicly accessible image/template URL' },
              ].map((v) => (
                <div key={v.name} style={{ marginBottom: 12, padding: 12, background: 'var(--card)', borderRadius: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{v.name}</div>
                  <div style={{ fontSize: 11, color: '#6366f1', marginBottom: 2 }}>{v.env}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>{v.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
