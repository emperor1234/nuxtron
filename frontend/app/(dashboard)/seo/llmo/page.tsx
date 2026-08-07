'use client';

import { useState } from 'react';
import DegradedModeBanner from '@/app/components/degraded-mode-banner';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const LLMO_AUDIT_PHASES = [
  'Capture brand narrative and claims baseline',
  'Evaluate model accuracy and representation risk',
  'Build correction and citation action strategy',
];

export default function LLMOPage() {
  const [brand, setBrand] = useState('');
  const [domain, setDomain] = useState('');
  const [claims, setClaims] = useState('');
  const [competitors, setCompetitors] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!brand) {
      setError('Brand name is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<Record<string, unknown>>(
        '/seo-platform/llmo/analyze',
        'POST',
        {
          brand,
          domain,
          key_claims: claims
            .split('\n')
            .map((c) => c.trim())
            .filter(Boolean),
          competitors: competitors
            .split(',')
            .map((c) => c.trim())
            .filter(Boolean),
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
      setError(e instanceof Error ? e.message : 'LLMO analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  const card = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(37, 99, 235, 0.65)',
  };
  const inp = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };
  let accuracyRiskColor = '#22c55e';
  if (result?.accuracy_risk === 'high') {
    accuracyRiskColor = '#ef4444';
  } else if (result?.accuracy_risk === 'medium') {
    accuracyRiskColor = '#f59e0b';
  }

  return (
    <main style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid var(--line)',
            background: 'var(--card)',
            boxShadow: 'var(--shadow-sm)',
            padding: '22px 24px',
            marginBottom: 20,
          }}
        >
          <div
            style={{
              display: 'grid',
              gap: 16,
              alignItems: 'end',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
            }}
          >
            <div>
              <div style={{ display: 'inline-flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: 'var(--brand)',
                    border: '1px solid rgba(147,197,253,0.45)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(37,99,235,0.14)',
                  }}
                >
                  LLMO Engine
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: 'var(--muted)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(148,163,184,0.12)',
                  }}
                >
                  Brand Narrative Control
                </span>
              </div>
              <h1 style={{ margin: '0 0 4px', fontSize: 30, fontWeight: 800, color: 'var(--text)' }}>LLMO</h1>
              <p style={{ color: 'var(--muted)', margin: 0 }}>
                Analyze and optimize brand representation across GPT-4, Claude, and Gemini. Identify misinformation
                risks and build a reliable citation strategy.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Brand
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--brand)' }}>
                  {brand.trim() || 'Pending'}
                </div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Claims
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                  {claims
                    .split('\n')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}
                </div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Competitors
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                  {competitors
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}
                </div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Output
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Correction Plan</div>
              </div>
            </div>
          </div>
        </section>
        <DegradedModeBanner message="Fail-closed mode is active. Only live backend analysis results are shown." />
        {error && <div style={{ ...card, color: '#b91c1c' }}>{error}</div>}
        <div
          style={{
            display: 'grid',
            gap: 16,
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
            marginBottom: 16,
          }}
        >
          <form style={{ ...card, marginBottom: 0 }} onSubmit={handleSubmit}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                marginBottom: 10,
              }}
            >
              <div>
                <h2 style={{ margin: 0, fontSize: 16, color: 'var(--text)' }}>Brand Inputs</h2>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Define positioning context for model representation analysis
                </p>
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: 'var(--brand)',
                  border: '1px solid rgba(147,197,253,0.35)',
                  borderRadius: 8,
                  padding: '4px 8px',
                  background: 'rgba(37,99,235,0.12)',
                }}
              >
                Advanced Mode
              </div>
            </div>

            <label htmlFor="llmo-brand" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Brand Name
            </label>
            <input
              id="llmo-brand"
              style={inp}
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="e.g. Acme Corp"
            />
            <label htmlFor="llmo-domain" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Domain (optional)
            </label>
            <input
              id="llmo-domain"
              style={inp}
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="acmecorp.com"
            />
            <label htmlFor="llmo-claims" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Key Brand Claims (one per line)
            </label>
            <textarea
              id="llmo-claims"
              style={{ ...inp, minHeight: 80 }}
              value={claims}
              onChange={(e) => setClaims(e.target.value)}
              placeholder="We are the market leader in enterprise CRM&#10;Founded in 2010&#10;500+ enterprise customers"
            />
            <label
              htmlFor="llmo-competitors"
              style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
            >
              Competitors (comma-separated)
            </label>
            <input
              id="llmo-competitors"
              style={inp}
              value={competitors}
              onChange={(e) => setCompetitors(e.target.value)}
              placeholder="CompetitorA, CompetitorB, CompetitorC"
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid rgba(147,197,253,0.45)',
                background: 'linear-gradient(90deg, rgba(37,99,235,0.9) 0%, rgba(99,102,241,0.85) 100%)',
                color: '#eef2ff',
                fontWeight: 700,
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Analyzing brand in AI models...' : 'Analyze LLM Brand Presence'}
            </button>
          </form>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Execution map for LLM representation and risk control.
              </p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {LLMO_AUDIT_PHASES.map((phase, index) => (
                <div
                  key={phase}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                    border: '1px solid rgba(148,163,184,0.16)',
                    borderRadius: 10,
                    padding: '8px 10px',
                    background: '#f4f5f8',
                  }}
                >
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 999,
                      border: '1px solid rgba(147,197,253,0.4)',
                      background: 'rgba(37,99,235,0.16)',
                      color: 'var(--brand)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    {index + 1}
                  </div>
                  <div style={{ fontSize: 12, lineHeight: 1.4, color: 'var(--muted)' }}>{phase}</div>
                </div>
              ))}
            </div>
            <div
              style={{
                marginTop: 12,
                border: '1px solid rgba(148,163,184,0.16)',
                borderRadius: 10,
                padding: '10px 12px',
                background: '#f4f5f8',
              }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Current Scope
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                <span
                  style={{
                    border: '1px solid rgba(147,197,253,0.35)',
                    background: 'rgba(37,99,235,0.14)',
                    color: 'var(--brand)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {domain.trim() || 'Domain optional'}
                </span>
                <span
                  style={{
                    border: '1px solid rgba(148,163,184,0.35)',
                    background: 'rgba(148,163,184,0.12)',
                    color: 'var(--text)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {competitors
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}{' '}
                  competitors
                </span>
              </div>
            </div>
          </aside>
        </div>
        {result && (
          <>
            <section
              style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 10 }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Brand AI Score</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#22c55e' }}>
                  {(result.brand_ai_score as number) ?? '—'}
                  <span style={{ fontSize: 13, fontWeight: 400 }}>/100</span>
                </div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (claims + domain signals)'}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Accuracy Risk</div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 800,
                    textTransform: 'capitalize',
                    color: accuracyRiskColor,
                  }}
                >
                  {(result.accuracy_risk as string) ?? '—'}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Knowledge Gaps</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#f59e0b' }}>
                  {(result.knowledge_gap_topics as string[] | undefined)?.length ?? 0}
                </div>
              </div>
            </section>
            {(result.model_representations as Record<string, string> | undefined) && (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 14 }}>
                  🤖 How AI Models Represent Your Brand
                </p>
                {Object.entries(result.model_representations as Record<string, string>).map(([model, text]) => (
                  <div
                    key={model}
                    style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 10,
                      padding: 14,
                      marginBottom: 10,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        marginBottom: 6,
                      }}
                    >
                      {model.replaceAll('_', ' ')}
                    </div>
                    <div style={{ fontSize: 13, lineHeight: 1.6 }}>{text}</div>
                  </div>
                ))}
              </section>
            )}
            {(result.correction_strategy as string[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>🛡️ Correction Strategy</p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.correction_strategy as string[]).map((s) => (
                    <li key={s} style={{ fontSize: 13, marginBottom: 8 }}>
                      {s}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {(result.citation_building_plan as string[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>
                  📚 Citation Building Plan
                </p>
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.citation_building_plan as string[]).map((s) => (
                    <li key={s} style={{ fontSize: 13, marginBottom: 8 }}>
                      {s}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
            {(result.knowledge_gap_topics as string[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 10 }}>🔍 Knowledge Gap Topics</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {(result.knowledge_gap_topics as string[]).map((t) => (
                    <span
                      key={t}
                      style={{
                        fontSize: 12,
                        padding: '4px 12px',
                        background: 'rgba(239,68,68,0.1)',
                        border: '1px solid rgba(239,68,68,0.3)',
                        borderRadius: 99,
                        color: '#b91c1c',
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
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
