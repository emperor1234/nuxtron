'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type PlanResult = {
  analysis_id: string;
  content_strategy_score: number;
  pillar_topics: { pillar: string; content_angle: string; internal_link_hub: string }[];
  content_calendar: { week: number; topics: string[]; publishing_dates: string[]; content_types: string[] }[];
  seo_brief: { title: string; meta_description: string; target_keywords: string[]; outline: string[] }[];
  multimedia_plan: Record<string, unknown>;
  promotion_strategy: string[];
  measurement_framework: { kpis: string[]; tracking_plan: string };
  next_actions: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function ContentCreationBloggingPage() {
  const [topic, setTopic] = useState('');
  const [contentPillars, setContentPillars] = useState('');
  const [targetKeywords, setTargetKeywords] = useState('');
  const [aiModel, setAiModel] = useState('llama3.2');
  const [wordCount, setWordCount] = useState('2000');
  const [publicationFrequency, setPublicationFrequency] = useState('weekly');
  const [includeMultimedia, setIncludeMultimedia] = useState(false);
  const [seoBrief, setSeoBrief] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<PlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function runPlanning() {
    if (!topic) {
      setError('Topic is required');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await apiSend<PlanResult>(
        '/seo-platform/content-creation-blogging/plan',
        'POST',
        {
          topic,
          content_pillars: contentPillars
            .split('\n')
            .map((p) => p.trim())
            .filter(Boolean),
          target_keywords: targetKeywords
            .split('\n')
            .map((k) => k.trim())
            .filter(Boolean),
          ai_model: aiModel,
          word_count_target: parseInt(wordCount, 10),
          include_multimedia_plan: includeMultimedia,
          publication_frequency: publicationFrequency,
          seo_brief: seoBrief,
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
      setError(e instanceof Error ? e.message : 'Planning failed');
    } finally {
      setLoading(false);
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Content Creation & Blogging</h1>
        <p style={{ color: 'var(--muted)' }}>Plan and strategize your SEO-driven content calendar.</p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Topic</label>
          <input style={input} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Content topic" />
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Content Pillars (one per line)</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={contentPillars}
            onChange={(e) => setContentPillars(e.target.value)}
            placeholder="Pillar 1\nPillar 2\nPillar 3"
          />
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Target Keywords (one per line)</label>
          <textarea
            style={{ ...input, minHeight: 60 }}
            value={targetKeywords}
            onChange={(e) => setTargetKeywords(e.target.value)}
            placeholder="keyword 1\nkeyword 2"
          />
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>AI Model</label>
          <select style={input} value={aiModel} onChange={(e) => setAiModel(e.target.value)}>
            <option value="llama3.2">Llama 3.2 (Fast, Local)</option>
            <option value="claude-opus">Claude Opus (Premium)</option>
            <option value="gpt-4">GPT-4 (Advanced)</option>
            <option value="deepseek-r1">DeepSeek R1 (Reasoning)</option>
          </select>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Word Count Target</label>
          <select style={input} value={wordCount} onChange={(e) => setWordCount(e.target.value)}>
            <option value="800">800 words</option>
            <option value="1200">1200 words</option>
            <option value="2000">2000 words</option>
            <option value="2500">2500 words</option>
            <option value="3000">3000+ words</option>
          </select>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Publication Frequency</label>
          <select style={input} value={publicationFrequency} onChange={(e) => setPublicationFrequency(e.target.value)}>
            <option value="daily">Daily</option>
            <option value="3x-weekly">3x Weekly</option>
            <option value="weekly">Weekly</option>
            <option value="bi-weekly">Bi-Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', marginBottom: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={includeMultimedia}
              onChange={(e) => setIncludeMultimedia(e.target.checked)}
              style={{ marginRight: 8 }}
            />
            Include Multimedia Plan
          </label>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>SEO Brief</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={seoBrief}
            onChange={(e) => setSeoBrief(e.target.value)}
            placeholder="Brief description of SEO goals..."
          />
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 60 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any notes..."
          />
          <button
            onClick={() => void runPlanning()}
            disabled={loading}
            style={{
              padding: '8px 12px',
              border: 'none',
              borderRadius: 8,
              background: loading ? 'var(--muted)' : 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Planning...' : 'Create Content Plan'}
          </button>
        </section>
        {result && (
          <div style={{ marginTop: 16, display: 'grid', gap: 16 }}>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
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
              <p style={{ fontSize: 32, fontWeight: 800, margin: 0 }}>{result.content_strategy_score}</p>
              <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0' }}>Content Strategy Score</p>
            </section>
            {result.pillar_topics?.length > 0 && (
              <section style={card}>
                <h2 style={{ marginTop: 0, fontSize: 16 }}>Pillar Topics</h2>
                {result.pillar_topics.map((p) => (
                  <div key={p.pillar} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid var(--line)' }}>
                    <strong>{p.pillar}</strong>
                    <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--muted)' }}>{p.content_angle}</p>
                  </div>
                ))}
              </section>
            )}
            {result.next_actions?.length > 0 && (
              <section style={card}>
                <h2 style={{ marginTop: 0, fontSize: 16 }}>Next Actions</h2>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {result.next_actions.map((a) => (
                    <li key={a} style={{ marginBottom: 6, fontSize: 13 }}>
                      {a}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
