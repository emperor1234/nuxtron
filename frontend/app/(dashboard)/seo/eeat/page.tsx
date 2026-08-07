'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

function getEeatScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
}

type EeatGap =
  | string
  | {
      signal?: string;
      gap?: string;
      severity?: string;
      fix?: string;
    };

type EeatImprovement =
  | string
  | {
      signal?: string;
      action?: string;
      impact?: number;
      implementation?: string;
    };

type EeatResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  eeat_score?: number;
  experience_score?: number;
  expertise_score?: number;
  authority_score?: number;
  trust_score?: number;
  critical_gaps?: EeatGap[];
  improvements?: EeatImprovement[];
  author_bio_suggestions?: string[];
  trust_signals_missing?: string[];
  fallback?: boolean;
};

function formatGap(item: EeatGap): string {
  if (typeof item === 'string') return item;
  return item.gap ?? item.fix ?? 'Address missing E-E-A-T signal';
}

function formatImprovement(item: EeatImprovement): string {
  if (typeof item === 'string') return item;
  const signal = item.signal ? `[${item.signal}] ` : '';
  return `${signal}${item.action ?? 'Improve E-E-A-T signals'}`;
}

export default function EEATPage() {
  const [content, setContent] = useState('');
  const [authorBio, setAuthorBio] = useState('');
  const [domain, setDomain] = useState('');
  const [niche, setNiche] = useState('');
  const [result, setResult] = useState<EeatResult | null>(null);
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
      const data = await apiSend<EeatResult>(
        '/seo-platform/eeat/score',
        'POST',
        { content, author_bio: authorBio, domain, niche },
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
      setError(e instanceof Error ? e.message : 'E-E-A-T scoring failed');
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
    { key: 'experience_score', label: 'Experience' },
    { key: 'expertise_score', label: 'Expertise' },
    { key: 'authority_score', label: 'Authority' },
    { key: 'trust_score', label: 'Trust' },
  ] as const;

  type EeatDimKey = (typeof DIMS)[number]['key'];
  const dimScore = (result: EeatResult, key: EeatDimKey): number | undefined => result[key];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>E-E-A-T Scorer</h1>
        <p style={{ color: 'var(--muted)' }}>
          Score your content on Experience, Expertise, Authoritativeness, and Trustworthiness — Google&apos;s quality
          framework.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label htmlFor="eeat-domain" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                Domain
              </label>
              <input
                id="eeat-domain"
                style={inp}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="your-site.com"
              />
            </div>
            <div>
              <label htmlFor="eeat-niche" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                Niche / Industry
              </label>
              <input
                id="eeat-niche"
                style={inp}
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                placeholder="e.g. personal finance, health, SaaS"
              />
            </div>
          </div>
          <label htmlFor="eeat-author-bio" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Author Bio (optional)
          </label>
          <textarea
            id="eeat-author-bio"
            style={{ ...inp, minHeight: 60 }}
            value={authorBio}
            onChange={(e) => setAuthorBio(e.target.value)}
            placeholder="Jane Doe is a CPA with 15 years experience in corporate finance..."
          />
          <label htmlFor="eeat-content" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Content to Score
          </label>
          <textarea
            id="eeat-content"
            style={{ ...inp, minHeight: 180 }}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste your article or page content here..."
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
            {loading ? 'Scoring E-E-A-T…' : 'Score E-E-A-T'}
          </button>
          {loading && (
            <div
              style={{
                marginTop: 12,
                padding: '10px 14px',
                borderRadius: 8,
                background: 'rgba(27,199,255,0.08)',
                border: '1px solid rgba(27,199,255,0.2)',
                fontSize: 13,
                color: 'var(--muted)',
              }}
            >
              ⏳ AI is scoring your content — this typically takes 20–40 s on local inference. Please wait…
            </div>
          )}
        </section>
        {result && (
          <>
            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))', gap: 10 }}>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>E-E-A-T Score</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: getEeatScoreColor(result.eeat_score ?? 0) }}>
                  {result.eeat_score ?? '—'}
                </div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm'
                    ? 'AI model'
                    : 'Heuristic (author + trust signals)'}
                </div>
              </div>
              {DIMS.map((d) => (
                <div
                  key={d.key}
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '12px 14px',
                    border: '1px solid var(--line)',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{d.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{dimScore(result, d.key) ?? '—'}</div>
                  <div style={{ background: 'var(--line)', borderRadius: 4, height: 4, marginTop: 6 }}>
                    <div
                      style={{
                        width: `${dimScore(result, d.key) ?? 0}%`,
                        height: '100%',
                        background: '#2563eb',
                        borderRadius: 4,
                      }}
                    />
                  </div>
                </div>
              ))}
            </section>
            {(result.critical_gaps ?? []).length > 0 ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12, color: '#ef4444' }}>
                  🚨 Critical Gaps
                </p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.critical_gaps ?? []).map((g, index) => (
                    <li key={`gap-${index}`} style={{ fontSize: 13, marginBottom: 6, color: 'var(--text)' }}>
                      {formatGap(g)}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {(result.improvements ?? []).length > 0 ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>🔧 Improvements</p>
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.improvements ?? []).map((imp, index) => (
                    <li key={`imp-${index}`} style={{ fontSize: 13, marginBottom: 8, lineHeight: 1.5 }}>
                      {formatImprovement(imp)}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
            {(result.author_bio_suggestions ?? []).length > 0 ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 10 }}>
                  👤 Author Bio Suggestions
                </p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.author_bio_suggestions ?? []).map((s, index) => (
                    <li key={`bio-${index}`} style={{ fontSize: 13, marginBottom: 6 }}>
                      {s}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {(result.trust_signals_missing ?? []).length > 0 ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 10 }}>
                  ⚠️ Missing Trust Signals
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {(result.trust_signals_missing ?? []).map((s, index) => (
                    <span
                      key={`trust-${index}`}
                      style={{
                        fontSize: 12,
                        padding: '4px 12px',
                        background: 'rgba(239,68,68,0.1)',
                        border: '1px solid rgba(239,68,68,0.3)',
                        borderRadius: 99,
                        color: '#ef4444',
                      }}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </section>
            ) : null}
            <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>
              Analysis ID: {result.analysis_id ?? '—'}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
