'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type BrandNode = {
  brand_key: string;
  child_brand_name: string;
  parent_brand_key: string;
  region?: string;
  industry?: string;
  voice_profile_key?: string;
  created_at?: string;
};

type HierarchyResult = { brands?: BrandNode[] };

function buildTree(nodes: BrandNode[]): Map<string, BrandNode[]> {
  const map = new Map<string, BrandNode[]>();
  for (const n of nodes) {
    const parent = n.parent_brand_key ?? 'root';
    if (!map.has(parent)) map.set(parent, []);
    const children = map.get(parent);
    if (children) children.push(n);
  }
  return map;
}

function TreeNode({ node, tree, depth }: Readonly<{ node: BrandNode; tree: Map<string, BrandNode[]>; depth: number }>) {
  const [open, setOpen] = useState(true);
  const children = tree.get(node.brand_key) ?? [];
  let toggleIndicator = '·';
  if (children.length > 0) {
    toggleIndicator = open ? '▼' : '▶';
  }

  return (
    <div style={{ marginLeft: depth * 24 }}>
      <div style={ts.node}>
        <button onClick={() => setOpen((o) => !o)} style={ts.toggle}>
          {toggleIndicator}
        </button>
        <div style={ts.nodeBody}>
          <span style={ts.nodeName}>{node.child_brand_name}</span>
          <span style={ts.nodeKey}>{node.brand_key}</span>
          {node.region ? <span style={ts.badge}>{node.region}</span> : null}
          {node.industry ? <span style={{ ...ts.badge, background: 'rgba(251,191,36,0.1)', color: '#fbbf24', borderColor: 'rgba(251,191,36,0.2)' }}>{node.industry}</span> : null}
          {node.voice_profile_key ? (
            <span style={{ ...ts.badge, background: 'rgba(99,102,241,0.1)', color: 'var(--brand)', borderColor: 'rgba(99,102,241,0.2)' }}>
              voice: {node.voice_profile_key}
            </span>
          ) : null}
        </div>
      </div>
      {open && children.map((c) => (
        <TreeNode key={c.brand_key} node={c} tree={tree} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function BrandHierarchyPage() {
  const [brands, setBrands] = useState<BrandNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [view, setView] = useState<'tree' | 'list'>('tree');

  // Form state
  const [childName, setChildName] = useState('');
  const [parentKey, setParentKey] = useState('root');
  const [region, setRegion] = useState('');
  const [industry, setIndustry] = useState('');
  const [voiceProfileKey, setVoiceProfileKey] = useState('');

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<HierarchyResult>('/brand-hierarchy', DEFAULT_TENANT_ID);
      setBrands(res.brands ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load brand hierarchy');
    } finally {
      setLoading(false);
    }
  }

  async function createBrand() {
    if (!childName.trim() || childName.trim().length < 2) {
      setError('Brand name must be at least 2 characters.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiSend(
        '/brand-hierarchy',
        'POST',
        {
          child_brand_name: childName.trim(),
          parent_brand_key: parentKey.trim() || 'root',
          region: region.trim() || undefined,
          industry: industry.trim() || undefined,
          voice_profile_key: voiceProfileKey.trim() || undefined,
        },
        DEFAULT_TENANT_ID
      );
      setChildName('');
      setRegion('');
      setIndustry('');
      setVoiceProfileKey('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create brand');
    } finally {
      setSubmitting(false);
    }
  }

  const tree = buildTree(brands);
  const roots = brands.filter((b) => b.parent_brand_key === 'root' || !brands.some((p) => p.brand_key === b.parent_brand_key));
  const parentOptions = [{ brand_key: 'root', child_brand_name: 'Root (Top-Level)' }, ...brands];
  const orphanRoots = brands.filter(
    (b) => b.parent_brand_key !== 'root' && !brands.some((p) => p.brand_key === b.parent_brand_key)
  );

  let hierarchyContent: React.ReactNode;
  if (loading) {
    hierarchyContent = <div style={s.skeleton}>Loading brand hierarchy…</div>;
  } else if (brands.length === 0) {
    hierarchyContent = <div style={s.empty}>No brands yet. Add one below.</div>;
  } else if (view === 'tree') {
    hierarchyContent = (
      <div style={s.treeContainer}>
        {brands
          .filter((b) => b.parent_brand_key === 'root')
          .map((b) => (
            <TreeNode key={b.brand_key} node={b} tree={tree} depth={0} />
          ))}
        {orphanRoots.map((b) => (
          <TreeNode key={b.brand_key} node={b} tree={tree} depth={0} />
        ))}
      </div>
    );
  } else {
    hierarchyContent = (
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Brand Key</th>
            <th style={s.th}>Name</th>
            <th style={s.th}>Parent</th>
            <th style={s.th}>Region</th>
            <th style={s.th}>Industry</th>
            <th style={s.th}>Voice Profile</th>
          </tr>
        </thead>
        <tbody>
          {brands.map((b) => (
            <tr key={b.brand_key}>
              <td style={s.td}><code style={s.code}>{b.brand_key}</code></td>
              <td style={{ ...s.td, fontWeight: 600, color: 'var(--text)' }}>{b.child_brand_name}</td>
              <td style={s.td}><code style={s.code}>{b.parent_brand_key}</code></td>
              <td style={s.td}>{b.region ?? '—'}</td>
              <td style={s.td}>{b.industry ?? '—'}</td>
              <td style={s.td}>{b.voice_profile_key ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>Parent-Child Brand Hierarchy</h1>
        <p style={s.subtitle}>
          Enterprise brand management: coordinate messaging across regions, franchises, subsidiaries, and employee
          networks from a single parent dashboard. Each child brand inherits and can customise its own voice profile.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      {/* Stats Row */}
      <div style={s.statsRow}>
        <div style={s.stat}>
          <span style={s.statValue}>{brands.length}</span>
          <span style={s.statLabel}>Total Brands</span>
        </div>
        <div style={s.stat}>
          <span style={s.statValue}>{roots.length}</span>
          <span style={s.statLabel}>Root Brands</span>
        </div>
        <div style={s.stat}>
          <span style={s.statValue}>{brands.filter((b) => b.region).length}</span>
          <span style={s.statLabel}>With Region</span>
        </div>
        <div style={s.stat}>
          <span style={s.statValue}>{brands.filter((b) => b.voice_profile_key).length}</span>
          <span style={s.statLabel}>Voice Profiles Assigned</span>
        </div>
      </div>

      {/* Tree / List View */}
      <section style={s.card}>
        <div style={s.cardHeader}>
          <h2 style={s.sectionTitle}>Brand Hierarchy</h2>
          <div style={s.viewToggle}>
            <button
              onClick={() => setView('tree')}
              style={{ ...s.viewBtn, ...(view === 'tree' ? s.viewBtnActive : {}) }}
            >
              🌲 Tree
            </button>
            <button
              onClick={() => setView('list')}
              style={{ ...s.viewBtn, ...(view === 'list' ? s.viewBtnActive : {}) }}
            >
              📋 List
            </button>
          </div>
        </div>

        {hierarchyContent}
      </section>

      {/* Add Brand Form */}
      <section style={s.card}>
        <h2 style={s.sectionTitle}>Add Child Brand</h2>
        <p style={s.hint}>
          Create a child brand under an existing parent. Child brands inherit the parent voice profile unless you assign
          one. Used for franchises, regional offices, subsidiaries, or white-label partners.
        </p>
        <div style={s.formGrid}>
          <div style={s.field}>
            <label htmlFor="brand-name" style={s.label}>Brand Name *</label>
            <input
              id="brand-name"
              value={childName}
              onChange={(e) => setChildName(e.target.value)}
              style={s.input}
              placeholder="e.g. Acme Corp — EMEA"
            />
          </div>
          <div style={s.field}>
            <label htmlFor="brand-parent" style={s.label}>Parent Brand</label>
            <select id="brand-parent" value={parentKey} onChange={(e) => setParentKey(e.target.value)} style={s.input}>
              {parentOptions.map((p) => (
                <option key={p.brand_key} value={p.brand_key}>
                  {p.child_brand_name} ({p.brand_key})
                </option>
              ))}
            </select>
          </div>
          <div style={s.field}>
            <label htmlFor="brand-region" style={s.label}>Region</label>
            <input
              id="brand-region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              style={s.input}
              placeholder="e.g. EMEA, APAC, US-West"
            />
          </div>
          <div style={s.field}>
            <label htmlFor="brand-industry" style={s.label}>Industry</label>
            <input
              id="brand-industry"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              style={s.input}
              placeholder="e.g. SaaS, Retail, Healthcare"
            />
          </div>
          <div style={s.field}>
            <label htmlFor="brand-voice-profile" style={s.label}>Voice Profile Key (optional)</label>
            <input
              id="brand-voice-profile"
              value={voiceProfileKey}
              onChange={(e) => setVoiceProfileKey(e.target.value)}
              style={s.input}
              placeholder="e.g. primary-voice (from Brand Voice DNA)"
            />
          </div>
        </div>
        <button onClick={createBrand} disabled={submitting} style={s.btn}>
          {submitting ? 'Creating…' : '🏢 Add Brand'}
        </button>
      </section>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { maxWidth: 1000, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 32 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 28, fontWeight: 800, margin: '10px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 14, color: 'var(--muted)', maxWidth: 720 },
  errorBanner: { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8, padding: '10px 14px', color: '#dc2626', marginBottom: 20, fontSize: 13 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 12, marginBottom: 24 },
  stat: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '14px 20px', display: 'flex', flexDirection: 'column' as const, gap: 4 },
  statValue: { fontSize: 28, fontWeight: 800, color: 'var(--brand)' },
  statLabel: { fontSize: 12, color: 'var(--muted)' },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 24 },
  cardHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--text)' },
  viewToggle: { display: 'flex', gap: 6 },
  viewBtn: { background: 'var(--card)', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 },
  viewBtnActive: { background: 'rgba(99,102,241,0.2)', color: 'var(--brand)', borderColor: '#6366f1' },
  skeleton: { color: 'var(--muted)', fontSize: 13, padding: 20 },
  empty: { color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 40 },
  treeContainer: { background: 'var(--card)', borderRadius: 8, padding: 16 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { background: 'var(--card)', color: 'var(--muted)', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--line)', fontWeight: 600 },
  td: { padding: '8px 12px', borderBottom: '1px solid var(--line)', color: 'var(--muted)' },
  code: { background: 'var(--card)', borderRadius: 4, padding: '1px 5px', fontSize: 11, fontFamily: 'monospace' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', gap: 14, marginBottom: 16 },
  field: {},
  label: { fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'block' },
  input: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box' as const, width: '100%' },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  hint: { fontSize: 12, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.6 },
};

const ts: Record<string, React.CSSProperties> = {
  node: { display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0' },
  toggle: { background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', fontSize: 12, width: 16 },
  nodeBody: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' as const },
  nodeName: { fontWeight: 600, color: 'var(--text)', fontSize: 13 },
  nodeKey: { fontFamily: 'monospace', fontSize: 11, color: 'var(--muted)', background: 'var(--card)', padding: '1px 6px', borderRadius: 4 },
  badge: { fontSize: 11, background: 'rgba(34,197,94,0.1)', color: '#15803d', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 4, padding: '1px 6px' },
};
