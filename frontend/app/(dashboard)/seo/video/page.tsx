'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type VideoSeoResult = {
  seo_score?: number;
  video_seo_score?: number;
  optimized_title?: string;
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  chapters?: Array<{ time: string; title: string }>;
  tags?: string[];
  [key: string]: unknown;
};

export default function VideoSEOPage() {
  const [title, setTitle] = useState('');
  const [keywords, setKeywords] = useState('');
  const [description, setDescription] = useState('');
  const [transcript, setTranscript] = useState('');
  const [platform, setPlatform] = useState('youtube');
  const [result, setResult] = useState<VideoSeoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!title) {
      setError('Title is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<VideoSeoResult>(
        '/seo-platform/video/optimize',
        'POST',
        {
          title,
          keywords: keywords
            .split(',')
            .map((k) => k.trim())
            .filter(Boolean),
          description,
          transcript,
          platform,
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
      setError(e instanceof Error ? e.message : 'Video SEO failed');
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
  const chapters = result?.chapters as Array<{ time: string; title: string }> | undefined;
  const tags = result?.tags as string[] | undefined;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Video SEO Optimizer</h1>
        <p style={{ color: 'var(--muted)' }}>
          Optimize YouTube / video content — title, description, tags, chapters, thumbnail tips, and VideoObject schema.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Video Title</label>
              <input
                style={inp}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. How to do keyword research in 2025"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                style={{ ...inp, cursor: 'pointer' }}
              >
                <option value="youtube">YouTube</option>
                <option value="tiktok">TikTok</option>
                <option value="linkedin">LinkedIn</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>
          </div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Target Keywords (comma-separated)
          </label>
          <input
            style={inp}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="keyword research, SEO tutorial, how to rank"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Current Description (optional)
          </label>
          <textarea
            style={{ ...inp, minHeight: 80 }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Existing video description..."
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Transcript / Notes (optional)
          </label>
          <textarea
            style={{ ...inp, minHeight: 100 }}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste video transcript for chapter generation..."
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
            {loading ? 'Optimizing video…' : 'Optimize Video SEO'}
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
            <section style={card}>
              <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 4 }}>Optimized Title</div>
              <strong style={{ fontSize: 15 }}>{result.optimized_title as string}</strong>
              <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 12, marginBottom: 4 }}>
                Optimized Description
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: 10,
                  fontSize: 12,
                  color: 'var(--muted)',
                  border: '1px solid var(--line)',
                  maxHeight: 140,
                  overflowY: 'auto',
                }}
              >
                {result.optimized_description as string}
              </div>
            </section>
            {tags && tags.length > 0 && (
              <section style={card}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Tags</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {tags.map((t, i) => (
                    <span
                      key={`item-${i}`}
                      style={{
                        padding: '2px 8px',
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        borderRadius: 12,
                        fontSize: 11,
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </section>
            )}
            {chapters && chapters.length > 0 && (
              <section style={card}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Chapters</div>
                {chapters.map((ch, i) => (
                  <div key={`item-${i}`} style={{ display: 'flex', gap: 12, padding: '4px 0', fontSize: 13 }}>
                    <span style={{ color: 'var(--brand)', fontWeight: 700, minWidth: 45 }}>{ch.time}</span>
                    <span>{ch.title}</span>
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
