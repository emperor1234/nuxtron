'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type WriterResult = {
  analysis_id: string;
  seo_score: number;
  readability_score: number;
  title: string;
  article: string;
  word_count: number;
  meta_description: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function AIWriterPage() {
  const [topic, setTopic] = useState('');
  const [keywords, setKeywords] = useState('');
  const [wordCount, setWordCount] = useState(1200);
  const [tone, setTone] = useState('professional');
  const [brief, setBrief] = useState('');
  const [result, setResult] = useState<WriterResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!topic) {
      setError('Topic is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<WriterResult>(
        '/seo-platform/content/write',
        'POST',
        {
          topic,
          keywords: keywords
            .split(',')
            .map((k) => k.trim())
            .filter(Boolean),
          word_count: wordCount,
          tone,
          brief,
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
      setError(e instanceof Error ? e.message : 'Writing failed');
    } finally {
      setLoading(false);
    }
  }

  const TONES = ['professional', 'conversational', 'authoritative', 'friendly', 'technical', 'journalistic'];
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

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>AI Article Writer</h1>
        <p style={{ color: 'var(--muted)' }}>
          Generate E-E-A-T quality, human-like SEO articles powered by your local Ollama AI.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Article Topic</label>
          <input
            style={inp}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. How to build an SEO strategy for SaaS in 2025"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Keywords (comma-separated)
          </label>
          <input
            style={inp}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="SaaS SEO, B2B SEO strategy, organic traffic"
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Word Count</label>
              <input
                type="number"
                style={inp}
                value={wordCount}
                onChange={(e) => setWordCount(Number(e.target.value))}
                min={300}
                max={5000}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Tone</label>
              <select value={tone} onChange={(e) => setTone(e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
                {TONES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Brief / Guidance (optional)
          </label>
          <textarea
            style={{ ...inp, minHeight: 80 }}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Any specific angle, stats to include, competitor differentiation..."
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
            {loading ? 'Writing article… (this may take up to 60s)' : 'Write Article'}
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
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.15)', color: '#38bdf8' }}>
                    Cached result
                  </span>
                )}
              </div>
            )}
          <section style={card}>
            <div style={{ display: 'flex', gap: 16, fontSize: 12, marginBottom: 14 }}>
              {[
                { label: 'SEO Score', value: `${result.seo_score}/100` },
                { label: 'Readability', value: `${result.readability_score}/100` },
                { label: 'Word Count', value: result.word_count },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{m.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 800 }}>{m.value}</div>
                </div>
              ))}
            </div>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>{result.title}</h2>
            <p style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>
              {result.meta_description}
            </p>
            <div
              style={{
                background: 'var(--bg)',
                borderRadius: 8,
                padding: 16,
                border: '1px solid var(--line)',
                fontSize: 13,
                lineHeight: 1.7,
                whiteSpace: 'pre-wrap',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {result.article}
            </div>
          </section>
          </>
        )}
      </div>
    </main>
  );
}
