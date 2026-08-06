'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type ChannelAttribution = {
  channel?: string;
  pipeline_value?: number;
  won_revenue?: number;
  assisted_revenue?: number;
  confidence?: string;
};

type FunnelLeakage = {
  stage?: string;
  drop_off_pct?: number;
  primary_cause?: string;
  fix?: string;
};

type RevenueAttributionResult = {
  attribution_confidence_score?: number;
  revenue_influenced_pct?: number;
  channel_attribution?: ChannelAttribution[];
  funnel_leakage?: FunnelLeakage[];
  priority_actions?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function RevenueAttributionPage() {
  const [domain, setDomain] = useState('');
  const [channels, setChannels] = useState('organic_search, ai_referrals, email, social');
  const [conversionEvents, setConversionEvents] = useState('demo_request, trial_signup, checkout');
  const [windowDays, setWindowDays] = useState(30);
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<RevenueAttributionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!domain.trim()) {
      setError('Domain is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<RevenueAttributionResult>(
        '/seo-platform/revenue-attribution/analyze',
        'POST',
        {
          domain: domain.trim(),
          channels: channels
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          conversion_events: conversionEvents
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          revenue_window_days: windowDays,
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
      setError(e instanceof Error ? e.message : 'Revenue attribution analysis failed');
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
        <h1 style={{ marginTop: 0 }}>Revenue Attribution Intelligence</h1>
        <p style={{ color: 'var(--muted)' }}>Attribution from search and AI channels through to revenue outcomes.</p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Channels (comma-separated)
          </label>
          <input
            style={input}
            value={channels}
            onChange={(e) => setChannels(e.target.value)}
            placeholder="organic_search, ai_referrals, email"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Conversion Events</label>
          <input
            style={input}
            value={conversionEvents}
            onChange={(e) => setConversionEvents(e.target.value)}
            placeholder="demo_request, trial_signup"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Revenue Window (days)
          </label>
          <input
            style={input}
            type="number"
            min={1}
            max={365}
            value={windowDays}
            onChange={(e) => setWindowDays(Number(e.target.value || 30))}
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Attribution model notes and business context"
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
            {loading ? 'Analyzing attribution...' : 'Analyze Revenue Attribution'}
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
            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Attribution Confidence</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.attribution_confidence_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Revenue Influenced</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.revenue_influenced_pct ?? '--'}%</div>
              </div>
            </section>

            {(result.channel_attribution ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Channel Attribution</h3>
                {(result.channel_attribution ?? []).map((item, index) => (
                  <div
                    key={`channel-${index}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1.2fr 1fr 1fr 1fr auto',
                      gap: 8,
                      fontSize: 12,
                      padding: '6px 0',
                      borderBottom:
                        index < (result.channel_attribution ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <span style={{ fontWeight: 700 }}>{item.channel ?? '--'}</span>
                    <span style={{ color: 'var(--muted)' }}>
                      Pipeline ${(item.pipeline_value ?? 0).toLocaleString()}
                    </span>
                    <span>Won ${(item.won_revenue ?? 0).toLocaleString()}</span>
                    <span>Assist ${(item.assisted_revenue ?? 0).toLocaleString()}</span>
                    <span style={{ color: 'var(--brand)' }}>{item.confidence ?? 'n/a'}</span>
                  </div>
                ))}
              </section>
            )}

            {(result.funnel_leakage ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Funnel Leakage</h3>
                {(result.funnel_leakage ?? []).map((item, index) => (
                  <div
                    key={`leak-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.funnel_leakage ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.stage ?? 'stage'} · {item.drop_off_pct ?? 0}% drop-off
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.primary_cause ?? ''}</div>
                    <div style={{ fontSize: 12, color: 'var(--brand)' }}>{item.fix ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.priority_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Priority Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.priority_actions ?? []).map((action, index) => (
                    <li key={`action-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {action}
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
