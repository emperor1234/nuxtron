'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type LocaleTarget = {
  locale: string;
  status?: string;
  focus_keyword?: string;
};

type RegionalGap = {
  locale?: string;
  gap?: string;
  severity?: string;
};

type IntlResult = {
  readiness_score?: number;
  hreflang_coverage_pct?: number;
  canonical_consistency_pct?: number;
  locale_targets?: LocaleTarget[];
  regional_gaps?: RegionalGap[];
  priority_actions?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function InternationalMultilingualPage() {
  const [domain, setDomain] = useState('');
  const [locales, setLocales] = useState('en-us, en-gb, es-es');
  const [hreflangMap, setHreflangMap] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<IntlResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!domain.trim()) {
      setError('Domain is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<IntlResult>(
        '/seo-platform/international-multilingual/analyze',
        'POST',
        {
          domain: domain.trim(),
          locales: locales
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          current_hreflang_map: hreflangMap,
          notes,
        },
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
      setError(e instanceof Error ? e.message : 'International SEO analysis failed');
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
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>International & Multilingual SEO</h1>
        <p style={{ color: 'var(--muted)' }}>
          Regionalization, hreflang quality, and locale-level optimization planning.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Locales (comma-separated)
          </label>
          <input
            style={input}
            value={locales}
            onChange={(e) => setLocales(e.target.value)}
            placeholder="en-us, en-gb, es-es, de-de"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Current hreflang map (optional)
          </label>
          <textarea
            style={{ ...input, minHeight: 90 }}
            value={hreflangMap}
            onChange={(e) => setHreflangMap(e.target.value)}
            placeholder="Paste hreflang snippets or mapping notes"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Target regions, priority markets, rollout constraints"
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
            {loading ? 'Analyzing multilingual SEO...' : 'Analyze International SEO'}
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
            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Readiness Score</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.readiness_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>hreflang Coverage</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.hreflang_coverage_pct ?? '--'}%</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Canonical Consistency</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.canonical_consistency_pct ?? '--'}%</div>
              </div>
            </section>

            {(result.locale_targets ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Locale Targets</h3>
                {(result.locale_targets ?? []).map((item, index) => (
                  <div
                    key={`${item.locale ?? 'locale'}-${index}`}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 12,
                      padding: '8px 0',
                      borderBottom: index < (result.locale_targets ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: 13 }}>{item.locale ?? '--'}</strong>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.focus_keyword ?? ''}</div>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--brand)' }}>{item.status ?? 'planned'}</span>
                  </div>
                ))}
              </section>
            )}

            {(result.regional_gaps ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Regional Gaps</h3>
                {(result.regional_gaps ?? []).map((gap, index) => (
                  <div
                    key={`gap-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.regional_gaps ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {gap.locale ?? 'Global'} · {gap.severity ?? 'info'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{gap.gap ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.priority_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Priority Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.priority_actions ?? []).map((action, index) => (
                    <li key={`action-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {action}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
