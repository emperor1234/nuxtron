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
  vendor_inventory?: Array<{
    domain: string;
    vendor: string;
    capability: string;
    configured: boolean;
    evidence: string;
  }>;
};

type VerificationResponse = {
  status: string;
  verification: {
    slice_ready: boolean;
    slice_gate: {
      passed: boolean;
      blockers: string[];
    };
    validation_boundaries: {
      validated_slice: string;
      not_validated: string[];
    };
    evidence_table: Array<{ key: string; product: string; premium_features_total: number; vendors: string[] }>;
    feature_evidence_table: Array<{ key: string; feature: string; product: string; automation_depth: string }>;
  };
};

type GateResponse = {
  status: string;
  gate: {
    passed: boolean;
    blockers: string[];
  };
};

export default function WritesonicReadinessPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [verification, setVerification] = useState<VerificationResponse | null>(null);

  async function loadReadiness() {
    setLoading(true);
    setError('');
    try {
      const [parityData, gateData, verificationData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/writesonic/parity-audit', tenantId),
        apiGet<GateResponse>('/search-everywhere/writesonic/production-gate', tenantId),
        apiGet<VerificationResponse>('/search-everywhere/writesonic/verification-report', tenantId),
      ]);
      setParity(parityData);
      setGate(gateData);
      setVerification(verificationData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Writesonic readiness');
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
        <p className="eyebrow">Writesonic Readiness</p>
        <h1>Writesonic End-to-End Readiness Hub</h1>
        <p>
          Track implementation completeness, integration wiring, vendor coverage, and gate status for the Writesonic
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
          <a className="card" href="/seo/writesonic-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Automation</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Project runs, product blueprint execution, and production gate controls.
            </p>
          </a>
          <a className="card" href="/seo/writesonic-integrations" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Integrations</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Provider checklist, wiring apply, remediation, and export actions.
            </p>
          </a>
          <a className="card" href="/seo/writesonic-assist" style={{ textDecoration: 'none' }}>
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
              {parity?.vendor_inventory?.length ?? 0}
            </p>
            <p style={{ opacity: 0.8 }}>third-party vendor references</p>
          </article>
        </section>
      ) : null}

      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate</h3>
          <p>
            Current status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          {gate.gate.passed ? null : (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {verification ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Verification Boundaries</h3>
          <p>
            Slice ready: <strong>{verification.verification.slice_ready ? 'Yes' : 'No'}</strong> | Gate:{' '}
            <strong>{verification.verification.slice_gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          <p style={{ opacity: 0.85 }}>{verification.verification.validation_boundaries.validated_slice}</p>
          <ul className="bullet-list">
            {verification.verification.validation_boundaries.not_validated.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p style={{ opacity: 0.8 }}>
            Evidence rows: {verification.verification.evidence_table.length} | Feature evidence rows:{' '}
            {verification.verification.feature_evidence_table.length}
          </p>
        </section>
      ) : null}
    </main>
  );
}
