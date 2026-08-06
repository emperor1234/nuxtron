'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type PeaoWatchlistItem = {
  signal?: string;
  likelihood?: string;
  recommended_response?: string;
};

type PeaoDriver =
  | string
  | {
      driver?: string;
      weight?: number;
      direction?: string;
      confidence?: number;
    };

type PeaoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  predictive_score?: number;
  volatility_risk?: string;
  trend_forecast?: {
    direction?: string;
    confidence?: number;
    time_horizon_days?: number;
  };
  algorithm_watchlist?: PeaoWatchlistItem[];
  forecast_drivers?: PeaoDriver[];
  next_actions?: Array<string | { action?: string; priority?: string }>;
  fallback?: boolean;
};

function formatDriver(item: PeaoDriver): string {
  if (typeof item === 'string') return item;
  const direction = item.direction ? ` (${item.direction})` : '';
  return `${item.driver ?? 'Forecast driver'}${direction}`;
}

export default function PeaoPage() {
  const [domain, setDomain] = useState('');
  const [primaryKeyword, setPrimaryKeyword] = useState('');
  const [recentSignals, setRecentSignals] = useState('');
  const [forecastHorizonDays, setForecastHorizonDays] = useState(30);
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<PeaoResult | null>(null);
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
      const data = await apiSend<PeaoResult>(
        '/seo-platform/peao/analyze',
        'POST',
        {
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          recent_signals: recentSignals.trim(),
          forecast_horizon_days: forecastHorizonDays,
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
      setError(e instanceof Error ? e.message : 'PEAO analysis failed');
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
        <h1 style={{ marginTop: 0 }}>PEAO</h1>
        <p style={{ color: 'var(--muted)' }}>
          Predictive engine algorithm optimization using trend and anomaly forecasting.
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

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Recent Signals</label>
          <textarea
            style={{ ...input, minHeight: 110 }}
            value={recentSignals}
            onChange={(e) => setRecentSignals(e.target.value)}
            placeholder="Ranking changes, crawl anomalies, competitor moves, CTR shifts"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Forecast Horizon (days)
          </label>
          <input
            style={{ ...input, width: 180 }}
            type="number"
            min={7}
            max={180}
            value={forecastHorizonDays}
            onChange={(e) => setForecastHorizonDays(Number(e.target.value || 30))}
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Seasonality, releases, known SERP experiments"
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
            {loading ? 'Forecasting...' : 'Analyze PEAO'}
          </button>
        </section>

        {result && (
          <>
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Predictive Score</div>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{result.predictive_score ?? '--'}</div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (signal forecasting)'}
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Volatility Risk</div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{result.volatility_risk ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Trend Forecast</div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{result.trend_forecast?.direction ?? '--'}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                  confidence {result.trend_forecast?.confidence ?? '--'}
                </div>
              </div>
            </section>

            {(result.algorithm_watchlist ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Algorithm Watchlist</h3>
                {(result.algorithm_watchlist ?? []).map((item, index) => (
                  <div
                    key={`watch-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.algorithm_watchlist ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.signal ?? '--'} · {item.likelihood ?? 'medium'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.recommended_response ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.forecast_drivers ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Forecast Drivers</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.forecast_drivers ?? []).map((item, index) => (
                    <li key={`driver-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatDriver(item)}
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
