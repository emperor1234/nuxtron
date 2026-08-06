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
  feature_summary?: {
    implementation_pct: number;
    e2e_verified_pct: number;
    features_total: number;
    features_implemented: number;
  };
  feature_coverage_chart?: Array<{
    category: string;
    features_total: number;
    features_implemented: number;
    implementation_pct: number;
  }>;
};

type GateResponse = {
  status: string;
  gate: {
    passed: boolean;
    blockers: string[];
  };
};

type CompletionChartResponse = {
  status: string;
  chart: Array<{
    key: string;
    product: string;
    implemented: boolean;
    e2e_verified: boolean;
    premium_features_total: number;
  }>;
};

type VerificationResponse = {
  status: string;
  verification?: {
    slice_gate?: {
      passed?: boolean;
      blockers?: string[];
    };
    validation_boundaries?: {
      validated_slice?: string;
      not_validated?: string[];
    };
  };
};

type VendorsResponse = {
  status: string;
  vendors_total: number;
  vendors_configured_pct: number;
  vendor_chart: Array<{
    vendor: string;
    role?: string;
    configured?: boolean;
  }>;
};

export default function HootsuiteReadinessPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [completion, setCompletion] = useState<CompletionChartResponse | null>(null);
  const [verification, setVerification] = useState<VerificationResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);

  async function loadReadiness() {
    setLoading(true);
    setError('');
    try {
      const [parityData, gateData, completionData, verificationData, vendorData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/hootsuite/parity-audit', tenantId),
        apiGet<GateResponse>('/search-everywhere/hootsuite/production-gate', tenantId),
        apiGet<CompletionChartResponse>('/search-everywhere/hootsuite/completion-chart', tenantId),
        apiGet<VerificationResponse>('/search-everywhere/hootsuite/verification-report', tenantId),
        apiGet<VendorsResponse>('/search-everywhere/hootsuite/vendors', tenantId),
      ]);
      setParity(parityData);
      setGate(gateData);
      setCompletion(completionData);
      setVerification(verificationData);
      setVendors(vendorData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Hootsuite readiness');
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
        <p className="eyebrow">Hootsuite Readiness</p>
        <h1>Hootsuite End-to-End Readiness Hub</h1>
        <p>Track implementation completeness, integration wiring, and gate status for Hootsuite automation.</p>
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
          <a className="card" href="/seo/hootsuite-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Automation</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>Project runs, schedules, and production gate controls.</p>
          </a>
          <a className="card" href="/seo/hootsuite-integrations" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Integrations</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Provider checklist, preflight, remediation, and export actions.
            </p>
          </a>
          <a className="card" href="/seo/hootsuite-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>How It Works</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Run full automation blueprint to view module flow and vendor execution path.
            </p>
          </a>
          <a className="card" href="/seo/sproutsocial-automation" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Sprout Social Console</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>
              Compare Sprout-style production readiness, growth matrix, and vendor wiring coverage.
            </p>
          </a>
          <a className="card" href="/vendor-inventory-report" style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>Vendor Inventory</h3>
            <p style={{ opacity: 0.8, marginBottom: 0 }}>Review third-party and provider evidence for release gates.</p>
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
            <h3 style={{ marginTop: 0 }}>Feature E2E</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{parity.feature_summary?.e2e_verified_pct ?? 0}%</p>
          </article>
        </section>
      ) : null}

      {completion ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Product Completion Chart</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '8px 6px' }}>Product</th>
                  <th style={{ textAlign: 'left', padding: '8px 6px' }}>Implemented</th>
                  <th style={{ textAlign: 'left', padding: '8px 6px' }}>E2E Verified</th>
                  <th style={{ textAlign: 'left', padding: '8px 6px' }}>Premium Features</th>
                </tr>
              </thead>
              <tbody>
                {completion.chart.map((item) => (
                  <tr key={item.key} style={{ borderTop: '1px solid rgba(148, 163, 184, 0.2)' }}>
                    <td style={{ padding: '8px 6px' }}>{item.product}</td>
                    <td style={{ padding: '8px 6px' }}>{item.implemented ? 'Yes' : 'No'}</td>
                    <td style={{ padding: '8px 6px' }}>{item.e2e_verified ? 'Yes' : 'No'}</td>
                    <td style={{ padding: '8px 6px' }}>{item.premium_features_total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {parity?.feature_coverage_chart?.length ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Feature Coverage By Category</h3>
          <ul className="bullet-list">
            {parity.feature_coverage_chart.map((row) => (
              <li key={row.category}>
                <strong>{row.category}</strong>: {row.features_implemented}/{row.features_total} ({row.implementation_pct}%)
              </li>
            ))}
          </ul>
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

      {vendors ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Third-Party Vendors</h3>
          <p style={{ opacity: 0.8 }}>
            {vendors.vendors_total} vendors, {vendors.vendors_configured_pct}% configured
          </p>
          <ul className="bullet-list">
            {vendors.vendor_chart.slice(0, 16).map((item) => (
              <li key={item.vendor}>
                <strong>{item.vendor}</strong> - {item.role || 'provider'} ({item.configured ? 'configured' : 'pending'})
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {verification?.verification ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Verification Boundaries</h3>
          <p>
            Validated slice: <strong>{verification.verification.validation_boundaries?.validated_slice || 'n/a'}</strong>
          </p>
          {verification.verification.slice_gate?.passed ? null : (
            <ul className="bullet-list">
              {(verification.verification.slice_gate?.blockers || []).map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
          {(verification.verification.validation_boundaries?.not_validated || []).length ? (
            <>
              <h4 style={{ marginBottom: 6 }}>Not Validated Here</h4>
              <ul className="bullet-list">
                {(verification.verification.validation_boundaries?.not_validated || []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
