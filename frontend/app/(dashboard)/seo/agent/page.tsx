'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AgentPhase = {
  phase: string;
  description?: string;
  tasks: (string | { task: string; tool?: string; priority?: string; hours?: number })[];
  kpis?: string[];
  expected_outcome?: string;
};

export default function AgentPage() {
  const [goal, setGoal] = useState('');
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!goal) {
      setError('SEO goal is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<Record<string, unknown>>(
        '/seo-platform/agent/run',
        'POST',
        { goal, domain },
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
      setError(e instanceof Error ? e.message : 'Agent run failed');
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
  const phases = result?.phases as AgentPhase[] | undefined;
  const PHASE_COLORS = [
    'rgba(27,199,255,0.1)',
    'rgba(37,99,235,0.1)',
    'rgba(34,197,94,0.1)',
    'rgba(234,179,8,0.1)',
    'rgba(239,68,68,0.1)',
  ];
  const PHASE_BORDERS = [
    'rgba(27,199,255,0.3)',
    'rgba(37,99,235,0.3)',
    'rgba(34,197,94,0.3)',
    'rgba(234,179,8,0.3)',
    'rgba(239,68,68,0.3)',
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <h1 style={{ margin: 0 }}>Autonomous SEO Agent</h1>
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
            AI-Powered
          </span>
        </div>
        <p style={{ color: 'var(--muted)', marginBottom: 20 }}>
          Describe your SEO goal and let the AI agent create a complete multi-phase execution plan with tasks, KPIs, and
          expected outcomes.
        </p>
        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}
        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>SEO Goal</label>
          <textarea
            style={{ ...inp, minHeight: 80 }}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Increase organic traffic by 50% in 6 months for our SaaS product targeting mid-market companies"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain (optional)</label>
          <input style={inp} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="your-site.com" />
          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
              fontSize: 14,
            }}
          >
            {loading ? '⚡ Agent is planning your SEO strategy…' : '⚡ Run SEO Agent'}
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
              ⏳ AI agent is generating your multi-phase execution plan — this typically takes 20–40 s on local
              inference. Please wait…
            </div>
          )}
        </section>
        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {typeof result.analysis_mode === 'string' && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background:
                        result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached === true && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: 'rgba(56,189,248,0.12)',
                      color: '#38bdf8',
                    }}
                  >
                    Cached result
                  </span>
                )}
              </div>
            )}

            <section
              style={{ ...card, background: 'linear-gradient(135deg, rgba(27,199,255,0.05), rgba(37,99,235,0.05))' }}
            >
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Strategic Goal</div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{(result.goal as string) || goal}</div>
              {typeof result.domain === 'string' && result.domain && (
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>Domain: {result.domain}</div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginTop: 12 }}>
                <div
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>Estimated Timeframe</div>
                  <div style={{ fontSize: 16, fontWeight: 800 }}>{(result.estimated_timeframe as string) ?? '—'}</div>
                </div>
                <div
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>Priority Score</div>
                  <div style={{ fontSize: 16, fontWeight: 800 }}>
                    {(result.overall_priority_score as number) ?? '—'}
                  </div>
                </div>
              </div>
            </section>
            {phases && phases.length > 0 && (
              <div>
                <h2 style={{ fontSize: 15, marginBottom: 12 }}>Execution Plan — {phases.length} Phases</h2>
                {phases.map((ph, i) => (
                  <section
                    key={`item-${i}`}
                    style={{
                      ...card,
                      borderLeft: `4px solid ${PHASE_BORDERS[i % PHASE_BORDERS.length]}`,
                      background: PHASE_COLORS[i % PHASE_COLORS.length],
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 8,
                      }}
                    >
                      <div>
                        <span
                          style={{ fontSize: 10, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase' }}
                        >
                          Phase {i + 1}
                        </span>
                        <h3 style={{ margin: '2px 0 0', fontSize: 15 }}>{ph.phase}</h3>
                      </div>
                    </div>
                    <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--muted)' }}>{ph.description}</p>
                    {ph.tasks && ph.tasks.length > 0 && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: 'var(--text)' }}>
                          TASKS
                        </div>
                        {ph.tasks.map((t, j) => (
                          <div key={`item-${j}`} style={{ display: 'flex', gap: 8, marginBottom: 4, fontSize: 12 }}>
                            <span style={{ color: 'var(--brand)', flexShrink: 0 }}>→</span>
                            <span>
                              {typeof t === 'string'
                                ? t
                                : `${t.task}${t.tool ? ` (${t.tool.replace(/_/g, ' ')})` : ''}${t.hours ? ` — ${t.hours}h` : ''}`}
                            </span>
                            {typeof t !== 'string' && t.priority && (
                              <span
                                style={{
                                  fontSize: 10,
                                  padding: '1px 6px',
                                  borderRadius: 99,
                                  fontWeight: 700,
                                  background: t.priority === 'high' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                                  color: t.priority === 'high' ? '#ef4444' : '#f59e0b',
                                }}
                              >
                                {t.priority}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {ph.kpis && ph.kpis.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: 'var(--text)' }}>KPIs</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {ph.kpis.map((k, j) => (
                            <span
                              key={`item-${j}`}
                              style={{
                                fontSize: 11,
                                padding: '2px 8px',
                                background: 'var(--bg)',
                                border: '1px solid var(--line)',
                                borderRadius: 12,
                              }}
                            >
                              {k}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {ph.expected_outcome && (
                      <div
                        style={{
                          marginTop: 8,
                          padding: 8,
                          background: 'var(--bg)',
                          borderRadius: 6,
                          fontSize: 12,
                          color: 'var(--muted)',
                          fontStyle: 'italic',
                        }}
                      >
                        Expected: {ph.expected_outcome}
                      </div>
                    )}
                  </section>
                ))}
              </div>
            )}
            {result.success_metrics !== undefined && result.success_metrics !== null && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>📊 Success Metrics</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {Array.isArray(result.success_metrics) ? (
                    (result.success_metrics as string[]).map((m) => (
                      <span
                        key={m}
                        style={{
                          fontSize: 12,
                          padding: '4px 12px',
                          background: 'rgba(27,199,255,0.1)',
                          border: '1px solid rgba(27,199,255,0.3)',
                          borderRadius: 99,
                          color: '#22d3ee',
                        }}
                      >
                        {m}
                      </span>
                    ))
                  ) : (
                    <pre style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                      {JSON.stringify(result.success_metrics, null, 2)}
                    </pre>
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
