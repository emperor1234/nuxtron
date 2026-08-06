'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AioResult = {
  aio_score?: number;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  [key: string]: unknown;
};

export default function AIOPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [result, setResult] = useState<AioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!content) {
      setError('Content is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<AioResult>(
        '/seo-platform/aio/score',
        'POST',
        { topic, content },
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
      setError(e instanceof Error ? e.message : 'Scoring failed');
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
  const DIMS = [
    { key: 'machine_readability', label: 'Machine Readability' },
    { key: 'entity_clarity', label: 'Entity Clarity' },
    { key: 'structure_score', label: 'Structure' },
    { key: 'extractability_score', label: 'Extractability' },
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <h1 style={{ margin: 0 }}>AIO</h1>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              background: 'var(--brand)',
              color: '#00101e',
              borderRadius: 4,
              padding: '2px 7px',
            }}
          >
            AI Content Optimization
          </span>
        </div>
        <p style={{ color: 'var(--muted)' }}>
          Score content for machine readability, entity clarity, and extractability for AI systems.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Topic (optional)</label>
          <input
            style={inp}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Enterprise AI adoption"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Content</label>
          <textarea
            style={{ ...inp, minHeight: 200 }}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste your content to score for AI readability..."
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
            {loading ? 'Scoring…' : 'Score AI Readability'}
          </button>
        </section>
        {result && (
          <>
            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))', gap: 10 }}>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  border: '1px solid var(--line)',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>AIO Score</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#22c55e' }}>
                  {(result.aio_score as number) ?? '—'}
                </div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (content structure)'}
                </div>
              </div>
              {DIMS.map((d) => (
                <div
                  key={d.key}
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{d.label}</div>
                  <div style={{ fontSize: 20, fontWeight: 800 }}>{(result[d.key] as number) ?? '—'}</div>
                  <div style={{ background: 'var(--line)', borderRadius: 4, height: 4, marginTop: 6 }}>
                    <div
                      style={{
                        width: `${(result[d.key] as number) ?? 0}%`,
                        height: '100%',
                        background: '#22c55e',
                        borderRadius: 4,
                      }}
                    />
                  </div>
                </div>
              ))}
            </section>
            {(result.improvements as { before?: string; after?: string; reason?: string }[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 14 }}>✏️ Improvement Actions</p>
                {(result.improvements as { before?: string; after?: string; reason?: string }[]).map((imp, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 10,
                      padding: 14,
                      marginBottom: 10,
                    }}
                  >
                    {imp.before && (
                      <div style={{ fontSize: 12, color: '#ef4444', marginBottom: 4 }}>
                        Before: <em>{imp.before}</em>
                      </div>
                    )}
                    {imp.after && (
                      <div style={{ fontSize: 12, color: '#22c55e', marginBottom: 4 }}>
                        After: <em>{imp.after}</em>
                      </div>
                    )}
                    {imp.reason && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{imp.reason}</div>}
                  </div>
                ))}
              </section>
            ) : null}
            {(result.optimized_paragraphs as string[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>📝 Optimized Content</p>
                {(result.optimized_paragraphs as string[]).map((p, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      fontSize: 13,
                      padding: '10px 14px',
                      background: 'var(--bg)',
                      borderRadius: 8,
                      border: '1px solid var(--line)',
                      marginBottom: 8,
                      lineHeight: 1.6,
                    }}
                  >
                    {p}
                  </div>
                ))}
              </section>
            ) : null}
            <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>
              Analysis ID: {result.analysis_id as string}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
