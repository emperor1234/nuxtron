'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

type ParityResponse = {
  status: string;
  summary: {
    implementation_pct: number;
    integration_configured_pct: number;
    modules_total: number;
    modules_implemented: number;
  };
};

type GateResponse = {
  status: string;
  gate: {
    passed: boolean;
    blockers: string[];
  };
};

type VendorsResponse = {
  status: string;
  vendors_total: number;
  vendors_configured: number;
};

export default function GeoptieReadinessPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);

  async function loadReadiness() {
    setLoading(true);
    setError('');
    try {
      const [parityData, gateData, vendorData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/geoptie/parity-audit', tenantId),
        apiGet<GateResponse>('/search-everywhere/geoptie/production-gate', tenantId),
        apiGet<VendorsResponse>('/search-everywhere/geoptie/vendors', tenantId),
      ]);
      setParity(parityData);
      setGate(gateData);
      setVendors(vendorData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Geoptie readiness');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadReadiness();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Geoptie Readiness</p>
        <h1>Geoptie End-to-End Readiness Hub</h1>
        <p>
          Track implementation completeness, integration wiring, vendor coverage, and gate status for the Geoptie
          automation slice.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}
        >
          <h2 style={{ margin: 0 }}>Quick Navigation</h2>
          <button onClick={() => void loadReadiness()} disabled={loading}>
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
          <a className="card" href="/seo/geoptie-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Automation</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Project runs, product blueprint execution, and production gate controls.
            </p>
          </a>
          <a className="card" href="/seo/geoptie-integrations" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Integrations</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Provider checklist, wiring apply, remediation, and export actions.
            </p>
          </a>
          <a className="card" href="/seo/geoptie-assist" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Assist Console</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Prompt-based release guidance with vendor-aware workflow handoffs.
            </p>
          </a>
        </div>
      </section>

      {parity ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Implementation</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{parity.summary.implementation_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Integration Wiring</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{parity.summary.integration_configured_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Modules</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {parity.summary.modules_implemented}/{parity.summary.modules_total}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Vendors</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {vendors?.vendors_configured ?? 0}/{vendors?.vendors_total ?? 0}
            </p>
          </article>
        </section>
      ) : null}

      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate</h3>
          <p>
            Current status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          {!gate.gate.passed ? (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
