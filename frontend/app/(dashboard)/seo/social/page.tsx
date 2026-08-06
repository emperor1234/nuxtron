'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SocialSeoAuditResponse = {
  analysis_id: string;
  url: string;
  social_seo_score: number;
  open_graph: { title: string; description: string; image: string; type: string; issues: string[] };
  twitter_card: { card_type: string; title: string; description: string; image: string; issues: string[] };
  linkedin: { article_snippet: string; issues: string[] };
  canonical_alignment: { canonical_url: string; matches_og_url: boolean };
  distribution_opportunities: string[];
  quick_wins: string[];
  recommended_tools: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

const PLATFORMS = ['twitter', 'facebook', 'linkedin', 'pinterest'];

export default function SocialSeoPage() {
  const [url, setUrl] = useState('https://example.com');
  const [platforms, setPlatforms] = useState<string[]>(['twitter', 'facebook', 'linkedin']);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<SocialSeoAuditResponse | null>(null);

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box' as const,
  };

  function togglePlatform(p: string) {
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  }

  async function runAudit() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<SocialSeoAuditResponse>(
        '/seo-platform/social/audit',
        'POST',
        { url: url.trim(), platforms, notes: notes.trim() },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Social SEO audit failed.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <Link href={'/seo' as Route} style={{ color: 'var(--brand)', textDecoration: 'none', fontSize: 13 }}>
          ← Back to SEO Platform
        </Link>
        <h1 style={{ marginTop: 12, marginBottom: 6 }}>Social SEO & Distribution</h1>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 18 }}>
          Audit Open Graph tags, Twitter Cards, LinkedIn snippets, and multi-surface social distribution signals.
        </p>

        <section style={{ ...card, marginBottom: 14, display: 'grid', gap: 10 }}>
          <div>
            <label htmlFor="social-url" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              URL
            </label>
            <input id="social-url" value={url} onChange={(e) => setUrl(e.target.value)} style={input} />
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Platforms</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {PLATFORMS.map((p) => (
                <label
                  key={p}
                  style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 13, cursor: 'pointer' }}
                >
                  <input type="checkbox" checked={platforms.includes(p)} onChange={() => togglePlatform(p)} />
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="social-notes" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Notes (optional)
            </label>
            <input
              id="social-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={input}
              placeholder="Campaign context..."
            />
          </div>
          <button
            onClick={runAudit}
            disabled={loading}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Auditing…' : 'Run Social SEO Audit'}
          </button>
          {error && <div style={{ color: '#fca5a5', fontSize: 13 }}>{error}</div>}
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
            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 15 }}>
                Social SEO Score: {result.social_seo_score}/100
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 10 }}>
                {[
                  { label: 'Open Graph', data: result.open_graph },
                  { label: 'Twitter Card', data: result.twitter_card },
                ].map(({ label, data }) => (
                  <div key={label} style={card}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>{label}</div>
                    {(['title', 'description', 'image'] as const).map((field) => (
                      <div key={field} style={{ marginBottom: 4 }}>
                        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{field}: </span>
                        <span
                          style={{
                            fontSize: 12,
                            color:
                              (data as Record<string, string | string[]>)[field] === 'Missing'
                                ? '#fca5a5'
                                : 'var(--text)',
                          }}
                        >
                          {(data as Record<string, string | string[]>)[field]}
                        </span>
                      </div>
                    ))}
                    {data.issues.length > 0 && (
                      <ul style={{ margin: '8px 0 0', paddingLeft: 16 }}>
                        {data.issues.map((issue, i) => (
                          <li key={`item-${i}`} style={{ fontSize: 11, color: '#fca5a5', marginBottom: 2 }}>
                            {issue}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </section>

            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>Canonical Alignment</h2>
              <div style={{ fontSize: 13 }}>
                <span style={{ color: 'var(--muted)' }}>Canonical URL: </span>
                {result.canonical_alignment.canonical_url}
                {' — '}
                <span style={{ color: result.canonical_alignment.matches_og_url ? '#86efac' : '#fca5a5' }}>
                  {result.canonical_alignment.matches_og_url ? '✓ Matches og:url' : '✗ Mismatches og:url'}
                </span>
              </div>
            </section>

            {result.quick_wins.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>Quick Wins</h2>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {result.quick_wins.map((w, i) => (
                    <li key={`item-${i}`} style={{ fontSize: 13, marginBottom: 4 }}>
                      {w}
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
