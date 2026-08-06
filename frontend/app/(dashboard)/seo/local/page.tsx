'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type LocalSeoResult = {
  local_seo_score?: number;
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  local_keywords?: Array<{ keyword: string; monthly_searches: number }>;
  [key: string]: unknown;
};

export default function LocalSEOPage() {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [location, setLocation] = useState('');
  const [website, setWebsite] = useState('');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState<LocalSeoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!name) {
      setError('Business name is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<LocalSeoResult>(
        '/seo-platform/local/optimize',
        'POST',
        { business_name: name, category, location, website, description },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Local SEO failed');
    } finally {
      setLoading(false);
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  };
  const inp = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };
  const localKWs = result?.local_keywords as Array<{ keyword: string; monthly_searches: number }> | undefined;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Local SEO Optimizer</h1>
        <p style={{ color: 'var(--muted)' }}>
          GMB optimization, local keyword strategy, citation opportunities, and review acquisition.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Business Name</label>
              <input
                style={inp}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Sunrise Dental"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                Business Category
              </label>
              <input
                style={inp}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g. Dental Clinic"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Location</label>
              <input
                style={inp}
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Austin, TX"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Website</label>
              <input
                style={inp}
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                placeholder="your-site.com"
              />
            </div>
          </div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Description</label>
          <textarea
            style={{ ...inp, minHeight: 80 }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe your business..."
          />
          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Optimizing…' : 'Optimize Local SEO'}
          </button>
        </section>
        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)', color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)' }}>
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.12)', color: '#38bdf8' }}>Cached result</span>
                )}
              </div>
            )}
            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  border: '1px solid var(--line)',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Local SEO Score</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{(result.local_seo_score as number) ?? '—'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  border: '1px solid var(--line)',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>GMB Score</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>
                  {(result.gmb_optimization as Record<string, number>)?.score ?? '—'}
                </div>
              </div>
            </section>
            {localKWs && localKWs.length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Local Keywords</h3>
                <div style={{ display: 'grid', gap: 6 }}>
                  {localKWs.map((kw, i) => (
                    <div
                      key={`item-${i}`}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '6px 0',
                        borderBottom: i < localKWs.length - 1 ? '1px solid var(--line)' : 'none',
                      }}
                    >
                      <span style={{ fontSize: 13 }}>{kw.keyword}</span>
                      <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {kw.monthly_searches?.toLocaleString() ?? '—'} / mo
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
