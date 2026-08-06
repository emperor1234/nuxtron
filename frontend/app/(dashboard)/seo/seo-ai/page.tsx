'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SeoAiKeywordOpportunity = {
  keyword?: string;
  intent?: string;
  priority?: string;
};

type SeoAiAction = {
  issue?: string;
  impact?: string;
  fix?: string;
};

type SeoAiContentPriority = {
  topic?: string;
  reason?: string;
  expected_lift?: string;
};

type SeoAiResult = {
  analysis_id?: string;
  seo_ai_score?: number;
  analysis_mode?: 'llm' | 'heuristic';
  ai_available?: boolean;
  cached?: boolean;
  fallback?: boolean;
  keyword_opportunities?: SeoAiKeywordOpportunity[];
  content_priorities?: SeoAiContentPriority[];
  technical_priorities?: SeoAiAction[];
  serp_strategy?: {
    primary_surface?: string;
    ctr_focus?: string;
    snippet_angle?: string;
  };
  next_actions?: string[];
  page_signals?: {
    url?: string;
    fetch_ok?: boolean;
    status_code?: number;
  };
};

export default function SeoAiCorePage() {
  const [domain, setDomain] = useState('');
  const [primaryKeyword, setPrimaryKeyword] = useState('');
  const [businessGoal, setBusinessGoal] = useState('growth');
  const [contentExcerpt, setContentExcerpt] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<SeoAiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!domain.trim() || !primaryKeyword.trim()) {
      setError('Domain and primary keyword are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<SeoAiResult>(
        '/seo-platform/seo-ai/analyze',
        'POST',
        {
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          business_goal: businessGoal.trim(),
          content_excerpt: contentExcerpt.trim(),
          notes: notes.trim(),
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
      setError(e instanceof Error ? e.message : 'SEO-AI analysis failed');
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
        <h1 style={{ marginTop: 0 }}>SEO-AI</h1>
        <p style={{ color: 'var(--muted)' }}>
          AI-enhanced traditional SEO workflows spanning keyword research, content, and technical signals.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Primary Keyword</label>
          <input
            style={input}
            value={primaryKeyword}
            onChange={(e) => setPrimaryKeyword(e.target.value)}
            placeholder="best crm for startups"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Business Goal</label>
          <input
            style={input}
            value={businessGoal}
            onChange={(e) => setBusinessGoal(e.target.value)}
            placeholder="growth"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Content Excerpt</label>
          <textarea
            style={{ ...input, minHeight: 100 }}
            value={contentExcerpt}
            onChange={(e) => setContentExcerpt(e.target.value)}
            placeholder="Paste a current landing page or article excerpt"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Business constraints, seasonality, SERP pressure"
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
            {loading ? 'Building SEO-AI plan...' : 'Analyze SEO-AI Core'}
          </button>
        </section>

        {result && (
          <>
            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>SEO-AI Score</div>
                <div style={{ fontSize: 28, fontWeight: 800 }}>{result.seo_ai_score ?? '--'}</div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (page signals)'}
                  {result.page_signals?.fetch_ok === false ? ' · homepage not crawled' : ''}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>SERP Strategy</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  <strong>Surface:</strong> {result.serp_strategy?.primary_surface ?? '--'}
                </div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  <strong>CTR Focus:</strong> {result.serp_strategy?.ctr_focus ?? '--'}
                </div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  <strong>Snippet Angle:</strong> {result.serp_strategy?.snippet_angle ?? '--'}
                </div>
              </div>
            </section>

            {(result.keyword_opportunities ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Keyword Opportunities</h3>
                {(result.keyword_opportunities ?? []).map((item, index) => (
                  <div
                    key={`kw-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.keyword_opportunities ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.keyword ?? '--'} · {item.intent ?? '--'} · {item.priority ?? 'medium'}
                    </div>
                  </div>
                ))}
              </section>
            )}

            {(result.content_priorities ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Content Priorities</h3>
                {(result.content_priorities ?? []).map((item, index) => (
                  <div
                    key={`content-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.content_priorities ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{item.topic ?? '--'}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.reason ?? ''}</div>
                    <div style={{ fontSize: 12, color: 'var(--brand)' }}>{item.expected_lift ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.technical_priorities ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Technical Priorities</h3>
                {(result.technical_priorities ?? []).map((item, index) => (
                  <div
                    key={`tech-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.technical_priorities ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.issue ?? '--'} · {item.impact ?? '--'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.fix ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.next_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Next Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.next_actions ?? []).map((item, index) => (
                    <li key={`next-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
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
