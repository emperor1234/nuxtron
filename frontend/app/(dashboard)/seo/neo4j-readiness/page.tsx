'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

type CompletionChartResponse = {
  status: string;
  chart: Array<{ area: string; implemented: boolean; verified: boolean }>;
  summary: {
    implemented: string;
    verified_live: string;
    implementation_pct: number;
    verified_live_pct: number;
  };
  note?: string;
};

type ProductionGateResponse = {
  status: string;
  gate: {
    passed: boolean;
    score: string;
    completion_pct: number;
    checks: Array<{ id: string; passed: boolean; detail: string }>;
  };
};

type VendorsResponse = {
  status: string;
  vendors: Array<{
    name: string;
    role: string;
    integration_mode: string;
  }>;
};

export default function Neo4jReadinessPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [chart, setChart] = useState<CompletionChartResponse | null>(null);
  const [gate, setGate] = useState<ProductionGateResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);

  async function refreshReadiness() {
    setLoading(true);
    setError('');
    try {
      const [chartData, gateData, vendorData] = await Promise.all([
        apiGet<CompletionChartResponse>('/search-everywhere/neo4j/completion-chart', tenantId),
        apiGet<ProductionGateResponse>('/search-everywhere/neo4j/production-gate', tenantId),
        apiGet<VendorsResponse>('/search-everywhere/neo4j/vendors', tenantId),
      ]);
      setChart(chartData);
      setGate(gateData);
      setVendors(vendorData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Neo4j readiness');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshReadiness();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Neo4j Readiness</p>
        <h1>Neo4j End-to-End Readiness Hub</h1>
        <p>
          Live implementation and production-gate visibility for Neo4j graph intelligence, including vendor mapping,
          environment wiring checks, and runtime readiness.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}
        >
          <h2 style={{ margin: 0 }}>Quick Navigation</h2>
          <button onClick={() => void refreshReadiness()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
        <div
          style={{
            display: 'grid',
            gap: 12,
            marginTop: 14,
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
          }}
        >
          <a className="card" href="/seo/neo4j-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Automation</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Run graph upsert, Cypher query, and GraphRAG context retrieval workflows.
            </p>
          </a>
          <a className="card" href="/seo/neo4j-integrations" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Integrations</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Review third-party vendors and run a live Neo4j connectivity probe.
            </p>
          </a>
        </div>
      </section>

      {chart ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Implementation</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{chart.summary.implementation_pct}%</p>
            <p style={{ opacity: 0.8 }}>{chart.summary.implemented}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Live Verification</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{chart.summary.verified_live_pct}%</p>
            <p style={{ opacity: 0.8 }}>{chart.summary.verified_live}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Production Gate</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{gate?.gate.completion_pct ?? 0}%</p>
            <p style={{ opacity: 0.8 }}>{gate?.gate.score ?? '--'}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Vendors</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{vendors?.vendors?.length ?? 0}</p>
            <p style={{ opacity: 0.8 }}>third-party mappings</p>
          </article>
        </section>
      ) : null}

      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate Checks</h3>
          <p>
            Current status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          <ul className="bullet-list">
            {gate.gate.checks.map((check) => (
              <li key={check.id}>
                <strong>{check.id}</strong> - {check.passed ? 'passed' : 'failed'}: {check.detail}
              </li>
            ))}
          </ul>
          {chart?.note ? <p style={{ opacity: 0.8 }}>{chart.note}</p> : null}
        </section>
      ) : null}
    </main>
  );
}
