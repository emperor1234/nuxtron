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

type MediaIssue = {
  type: string;
  element: string;
  description: string;
  fix: string;
  impact: string;
};

type MediaSeoAuditResponse = {
  analysis_id: string;
  url: string;
  media_seo_score: number;
  total_images_estimated: number;
  issues: MediaIssue[];
  compression: {
    average_size_kb: number;
    optimizable_pct: number;
    recommended_format: string;
  };
  schema_coverage: { image_objects_with_schema_pct: number };
  video_seo: { has_video_sitemap: boolean; transcript_coverage_pct: number };
  quick_wins: string[];
  recommended_tools: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

const IMPACT_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f97316',
  low: '#eab308',
};

export default function MediaSeoEnginePage() {
  const [url, setUrl] = useState('https://example.com');
  const [checkCompression, setCheckCompression] = useState(true);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<MediaSeoAuditResponse | null>(null);

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

  async function runAudit() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<MediaSeoAuditResponse>(
        '/seo-platform/media/audit',
        'POST',
        { url: url.trim(), check_compression: checkCompression, notes: notes.trim() },
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
      setError(err instanceof Error ? err.message : 'Media SEO audit failed.');
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
        <h1 style={{ marginTop: 12, marginBottom: 6 }}>Image & Media SEO Engine</h1>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 18 }}>
          Audit alt text, image metadata, compression opportunities, and media search signals.
        </p>

        <section style={{ ...card, marginBottom: 14, display: 'grid', gap: 10 }}>
          <div>
            <label htmlFor="media-url" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              URL
            </label>
            <input id="media-url" value={url} onChange={(e) => setUrl(e.target.value)} style={input} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              id="media-compress"
              type="checkbox"
              checked={checkCompression}
              onChange={(e) => setCheckCompression(e.target.checked)}
            />
            <label htmlFor="media-compress" style={{ fontSize: 13 }}>
              Analyse compression opportunities
            </label>
          </div>
          <div>
            <label htmlFor="media-notes" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Notes (optional)
            </label>
            <input
              id="media-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={input}
              placeholder="Focus areas..."
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
            {loading ? 'Running Audit…' : 'Run Media SEO Audit'}
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
              <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 15 }}>Media SEO Summary</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Media SEO Score</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>
                    {result.media_seo_score}
                    <span style={{ fontSize: 14 }}>/100</span>
                  </div>
                </div>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Images Detected</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>{result.total_images_estimated}</div>
                </div>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Avg Size (KB)</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>{result.compression.average_size_kb}</div>
                </div>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Optimisable</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>{result.compression.optimizable_pct}%</div>
                </div>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Schema Coverage</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>
                    {result.schema_coverage.image_objects_with_schema_pct}%
                  </div>
                </div>
                <div style={card}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Best Format</div>
                  <div style={{ fontSize: 20, fontWeight: 800 }}>
                    {result.compression.recommended_format.toUpperCase()}
                  </div>
                </div>
              </div>
            </section>

            {result.issues.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 15 }}>Issues ({result.issues.length})</h2>
                <div style={{ display: 'grid', gap: 8 }}>
                  {result.issues.map((issue, i) => (
                    <div
                      key={`item-${i}`}
                      style={{ ...card, borderLeft: `4px solid ${IMPACT_COLORS[issue.impact] ?? '#6366f1'}` }}
                    >
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            background: '#eef0f4',
                            color: 'var(--muted)',
                            borderRadius: 4,
                            padding: '1px 5px',
                          }}
                        >
                          {issue.type.replace(/_/g, ' ')}
                        </span>
                        <span
                          style={{ fontSize: 10, fontWeight: 700, color: IMPACT_COLORS[issue.impact] ?? '#6366f1' }}
                        >
                          {issue.impact} impact
                        </span>
                      </div>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{issue.description}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>
                        Element:{' '}
                        <code style={{ background: 'var(--bg)', padding: '1px 4px', borderRadius: 4 }}>
                          {issue.element}
                        </code>
                      </div>
                      <div style={{ fontSize: 12, color: '#86efac' }}>Fix: {issue.fix}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

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
