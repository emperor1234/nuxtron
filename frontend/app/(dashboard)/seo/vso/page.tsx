'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type VsoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  vso_score?: number;
  voice_query_coverage?: number;
  position_zero_probability?: number;
  voice_keywords?: Array<{ query: string; intent: string; answer: string }>;
  fallback?: boolean;
};

export default function VSOPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [localArea, setLocalArea] = useState('');
  const [result, setResult] = useState<VsoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!content || !topic) {
      setError('Topic and content are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<VsoResult>(
        '/seo-platform/vso/optimize',
        'POST',
        { topic, content, local_area: localArea },
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
      setError(e instanceof Error ? e.message : 'VSO optimization failed');
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
  const voiceKWs = result?.voice_keywords;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>VSO — Voice Search Optimization</h1>
        <p style={{ color: 'var(--muted)' }}>
          Optimize content for Siri, Google Assistant, Alexa, and Cortana voice queries.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Topic</label>
          <input
            style={inp}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. best coffee shops"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Local Area (optional)
          </label>
          <input
            style={inp}
            value={localArea}
            onChange={(e) => setLocalArea(e.target.value)}
            placeholder="e.g. London, New York"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Content</label>
          <textarea
            style={{ ...inp, minHeight: 160 }}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste your content here..."
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
            {loading ? 'Optimizing for Voice…' : 'Optimize for Voice Search'}
          </button>
        </section>
        {result && (
          <>
            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
              {[
                { label: 'VSO Score', value: `${result.vso_score ?? '—'}/100` },
                { label: 'Voice Coverage', value: `${result.voice_query_coverage ?? '—'}%` },
                {
                  label: 'Position-0 Prob.',
                  value: `${Math.round(((result.position_zero_probability as number) ?? 0) * 100)}%`,
                },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{m.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{m.value}</div>
                  {m.label === 'VSO Score' && (
                    <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                      {result.cached ? 'Cached · ' : ''}
                      {result.analysis_mode === 'llm'
                        ? 'AI model'
                        : 'Heuristic (voice + content signals)'}
                    </div>
                  )}
                </div>
              ))}
            </section>
            {voiceKWs && voiceKWs.length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Voice Query Targets</h3>
                {voiceKWs.map((kw, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: i < voiceKWs.length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                      <strong style={{ fontSize: 13 }}>&ldquo;{kw.query}&rdquo;</strong>
                      <span
                        style={{
                          fontSize: 10,
                          color: 'var(--muted)',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                          borderRadius: 4,
                          padding: '1px 5px',
                        }}
                      >
                        {kw.intent}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>{kw.answer}</p>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
