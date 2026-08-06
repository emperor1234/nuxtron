'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type BriefResult = {
  analysis_id: string;
  brief_score: number;
  title: string;
  meta_description: string;
  target_word_count: number;
  primary_keyword: string;
  tone?: string;
  outline?: Array<{ heading: string; word_count: number; key_points: string[] }>;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function ContentBriefPage() {
  const [topic, setTopic] = useState('');
  const [keywords, setKeywords] = useState('');
  const [wordCount, setWordCount] = useState(1500);
  const [audience, setAudience] = useState('');
  const [result, setResult] = useState<BriefResult | null>(null);
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
      const data = await apiSend<BriefResult>(
        '/seo-platform/content/brief',
        'POST',
        {
          topic,
          keywords: keywords
            .split(',')
            .map((k) => k.trim())
            .filter(Boolean),
          word_count: wordCount,
          audience,
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
      setError(e instanceof Error ? e.message : 'Brief generation failed');
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
  const outline = result?.outline;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Content Brief Generator</h1>
        <p style={{ color: 'var(--muted)' }}>
          Data-driven SEO content briefs — H2/H3 outlines, word count targets, internal links, and content angle.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Topic / Title</label>
          <input
            style={inp}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Best practices for B2B content marketing"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Keywords (comma-separated)
          </label>
          <input
            style={inp}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="content marketing, B2B SEO, lead generation"
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                Target Word Count
              </label>
              <input
                type="number"
                style={inp}
                value={wordCount}
                onChange={(e) => setWordCount(Number(e.target.value))}
                min={300}
                max={10000}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                Target Audience
              </label>
              <input
                style={inp}
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder="e.g. B2B marketing managers"
              />
            </div>
          </div>
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
            {loading ? 'Generating Brief…' : 'Generate Content Brief'}
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
              <div style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>{result.brief_score}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 12 }}>Brief Score</div>
              <h2 style={{ marginTop: 0, fontSize: 16 }}>{result.title}</h2>
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>{result.meta_description}</p>
              <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                <span>
                  <strong>Word count:</strong> {result.target_word_count}
                </span>
                <span>
                  <strong>Primary KW:</strong> {result.primary_keyword}
                </span>
                {result.tone && (
                  <span>
                    <strong>Tone:</strong> {result.tone}
                  </span>
                )}
              </div>
            </section>
            {outline && outline.length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Content Outline</h3>
                {outline.map((section, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      marginBottom: 12,
                      paddingBottom: 12,
                      borderBottom: i < outline.length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <strong style={{ fontSize: 13 }}>{section.heading}</strong>
                    <span style={{ fontSize: 11, color: 'var(--muted)', marginLeft: 8 }}>
                      {section.word_count} words
                    </span>
                    {section.key_points?.length > 0 && (
                      <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--muted)' }}>
                        {section.key_points.map((pt, j) => (
                          <li key={`item-${j}`}>{pt}</li>
                        ))}
                      </ul>
                    )}
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
