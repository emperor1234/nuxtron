'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type DaeoProtocolOpportunity = {
  protocol?: string;
  benefit?: string;
  readiness?: string;
};

type DaeoFactPackItem =
  | string
  | {
      fact?: string;
      confidence?: number;
      source?: string;
      machine_readable_format?: string;
    };

type DaeoTrustPlanItem =
  | string
  | {
      phase?: number;
      action?: string;
      trust_gain?: string;
      timeline_weeks?: number;
    };

type DaeoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  decentralization_score?: number;
  federation_readiness_score?: number;
  interoperability_score?: number;
  protocol_opportunities?: DaeoProtocolOpportunity[];
  canonical_fact_pack?: DaeoFactPackItem[];
  self_hosting_gaps?: Array<string | { gap?: string; fix?: string }>;
  trust_distribution_plan?: DaeoTrustPlanItem[];
  next_actions?: Array<string | { action?: string; priority?: string }>;
  fallback?: boolean;
};

function formatFactPack(item: DaeoFactPackItem): string {
  if (typeof item === 'string') return item;
  const fact = item.fact ?? 'Canonical claim';
  const conf =
    item.confidence !== undefined ? ` · confidence ${Math.round(item.confidence * 100)}%` : '';
  const source = item.source ? ` · ${item.source}` : '';
  return `${fact}${conf}${source}`;
}

function formatTrustPlan(item: DaeoTrustPlanItem): string {
  if (typeof item === 'string') return item;
  const phase = item.phase !== undefined ? `Phase ${item.phase}: ` : '';
  const weeks = item.timeline_weeks ? ` (${item.timeline_weeks}w)` : '';
  const gain = item.trust_gain ? ` — ${item.trust_gain}` : '';
  return `${phase}${item.action ?? 'Action'}${weeks}${gain}`;
}

export default function DaeoPage() {
  const [domain, setDomain] = useState('');
  const [protocolTargets, setProtocolTargets] = useState('self_hosted_search, federated_index, knowledge_api');
  const [canonicalFacts, setCanonicalFacts] = useState('');
  const [federationNotes, setFederationNotes] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<DaeoResult | null>(null);
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
      const data = await apiSend<DaeoResult>(
        '/seo-platform/daeo/analyze',
        'POST',
        {
          domain: domain.trim(),
          protocol_targets: protocolTargets
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          canonical_facts: canonicalFacts
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
          federation_notes: federationNotes.trim(),
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
      setError(e instanceof Error ? e.message : 'DAEO analysis failed');
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

  const modeLabel =
    result?.analysis_mode === 'llm'
      ? 'LLM analysis'
      : result?.analysis_mode === 'heuristic'
        ? 'Heuristic analysis'
        : null;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>DAEO</h1>
        <p style={{ color: 'var(--muted)' }}>
          Decentralized answer engine optimization for self-hosted and federated search.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Protocol Targets</label>
          <input
            style={input}
            value={protocolTargets}
            onChange={(e) => setProtocolTargets(e.target.value)}
            placeholder="self_hosted_search, federated_index, knowledge_api"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Canonical Facts (one per line)
          </label>
          <textarea
            style={{ ...input, minHeight: 100 }}
            value={canonicalFacts}
            onChange={(e) => setCanonicalFacts(e.target.value)}
            placeholder="Product facts, brand truths, canonical definitions"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Federation Notes</label>
          <textarea
            style={{ ...input, minHeight: 100 }}
            value={federationNotes}
            onChange={(e) => setFederationNotes(e.target.value)}
            placeholder="Index ownership, trust distribution, API constraints"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Deployment and governance notes"
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
            {loading ? 'Assessing decentralization...' : 'Analyze DAEO'}
          </button>
        </section>

        {result && (
          <>
            {(modeLabel || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {modeLabel && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {modeLabel}
                  </span>
                )}
                {result.cached && (
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Decentralization Score</div>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{result.decentralization_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Federation Readiness</div>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{result.federation_readiness_score ?? '--'}</div>
              </div>
              {result.interoperability_score !== undefined && (
                <div
                  style={{
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 8,
                    padding: '10px 12px',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>Interoperability</div>
                  <div style={{ fontSize: 26, fontWeight: 800 }}>{result.interoperability_score}</div>
                </div>
              )}
            </section>

            {(result.protocol_opportunities ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Protocol Opportunities</h3>
                {(result.protocol_opportunities ?? []).map((item, index) => (
                  <div
                    key={`protocol-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.protocol_opportunities ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.protocol ?? '--'} · {item.readiness ?? 'medium'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.benefit ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.canonical_fact_pack ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Canonical Fact Pack</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.canonical_fact_pack ?? []).map((item, index) => (
                    <li key={`fact-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatFactPack(item)}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.trust_distribution_plan ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Trust Distribution Plan</h3>
                <ol style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.trust_distribution_plan ?? []).map((item, index) => (
                    <li key={`trust-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatTrustPlan(item)}
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
