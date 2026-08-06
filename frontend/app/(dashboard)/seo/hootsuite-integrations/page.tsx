'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type ChecklistItem = {
  provider: string;
  kind: string;
  configured: boolean;
  required_missing: string[];
};

type ChecklistResponse = {
  status: string;
  configured: number;
  total: number;
  configured_pct: number;
  checklist: ChecklistItem[];
};

type PreflightResponse = {
  status: string;
  configured_pct: number;
  missing_provider_steps: Array<{
    provider: string;
    priority: string;
    required_missing: string[];
  }>;
};

type RemediationResponse = {
  status: string;
  remediation_steps: Array<{
    provider: string;
    priority: string;
    required_missing: string[];
  }>;
};

type WiringApplyResponse = {
  status: string;
  checklist_summary?: {
    configured_pct: number;
  };
  gate?: {
    passed: boolean;
    blockers?: string[];
  };
};

type VendorsResponse = {
  status: string;
  vendor_chart: Array<{
    vendor: string;
    configured?: boolean;
    role?: string;
  }>;
};

type EnvTemplateResponse = {
  status: string;
  providers_included: string[];
  missing_keys: string[];
  env_template: string;
};

export default function HootsuiteIntegrationsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [remediation, setRemediation] = useState<RemediationResponse | null>(null);
  const [wiringApply, setWiringApply] = useState<WiringApplyResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);
  const [envTemplate, setEnvTemplate] = useState<EnvTemplateResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [checklistData, preflightData, vendorData] = await Promise.all([
        apiGet<ChecklistResponse>('/search-everywhere/hootsuite/provider-checklist', tenantId),
        apiGet<PreflightResponse>('/search-everywhere/hootsuite/preflight', tenantId),
        apiGet<VendorsResponse>('/search-everywhere/hootsuite/vendors', tenantId),
      ]);
      setChecklist(checklistData);
      setPreflight(preflightData);
      setVendors(vendorData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load integration state');
    } finally {
      setLoading(false);
    }
  }

  async function buildRemediationBundle() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<RemediationResponse>(
        '/search-everywhere/hootsuite/remediation-bundle',
        'POST',
        {
          include_optional: false,
          include_configured: false,
          top_steps: 12,
        },
        tenantId
      );
      setRemediation(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to build remediation bundle');
    } finally {
      setLoading(false);
    }
  }

  async function applyAllMissingWiring() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<WiringApplyResponse>(
        '/search-everywhere/hootsuite/wiring/apply',
        'POST',
        {
          providers: [],
          include_all_missing: true,
          include_optional_auth: true,
        },
        tenantId
      );
      setWiringApply(response);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply Hootsuite wiring');
    } finally {
      setLoading(false);
    }
  }

  async function generateEnvTemplate() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<EnvTemplateResponse>(
        '/search-everywhere/hootsuite/env-template',
        'POST',
        {
          include_optional: true,
          include_configured: true,
        },
        tenantId
      );
      setEnvTemplate(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate env template');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Hootsuite Integrations</p>
        <h1>Provider Wiring And Remediation</h1>
        <p>Review provider checklist, preflight gaps, and generate actionable remediation steps.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshAll()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button onClick={() => void buildRemediationBundle()} disabled={loading}>
            {loading ? 'Building...' : 'Build Remediation Bundle'}
          </button>
          <button onClick={() => void applyAllMissingWiring()} disabled={loading}>
            {loading ? 'Applying...' : 'Apply All Missing Wiring'}
          </button>
          <button onClick={() => void generateEnvTemplate()} disabled={loading}>
            {loading ? 'Generating...' : 'Generate Env Template'}
          </button>
          <a
            className="button"
            href="/api/fastapi/search-everywhere/hootsuite/remediation-bundle/export?format=csv"
            style={{ textDecoration: 'none' }}
          >
            Export CSV
          </a>
        </div>
        {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
        {wiringApply ? (
          <p style={{ marginTop: 10, opacity: 0.85 }}>
            Wiring result: {wiringApply.checklist_summary?.configured_pct ?? '--'}% configured, gate{' '}
            {wiringApply.gate?.passed ? 'PASSED' : 'FAILED'}.
          </p>
        ) : null}
      </section>

      {checklist ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Provider Checklist</h3>
          <p style={{ opacity: 0.8 }}>
            {checklist.configured}/{checklist.total} configured ({checklist.configured_pct}%)
          </p>
          <ul className="bullet-list">
            {checklist.checklist.slice(0, 16).map((item) => (
              <li key={item.provider}>
                <strong>{item.provider}</strong> ({item.kind}) -{' '}
                {item.configured ? 'configured' : `missing: ${item.required_missing.join(', ') || 'oauth dependency'}`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {preflight ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Preflight</h3>
          <p style={{ opacity: 0.8 }}>Configured: {preflight.configured_pct}%</p>
          <ul className="bullet-list">
            {preflight.missing_provider_steps.slice(0, 12).map((step) => (
              <li key={step.provider}>
                <strong>{step.provider}</strong> [{step.priority}] -{' '}
                {step.required_missing.join(', ') || 'oauth dependency'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {remediation ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Remediation Bundle</h3>
          <ul className="bullet-list">
            {remediation.remediation_steps.map((step) => (
              <li key={step.provider}>
                <strong>{step.provider}</strong> [{step.priority}] -{' '}
                {step.required_missing.join(', ') || 'oauth dependency'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {vendors ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Third-Party Vendors</h3>
          <ul className="bullet-list">
            {vendors.vendor_chart.slice(0, 20).map((vendor) => (
              <li key={vendor.vendor}>
                <strong>{vendor.vendor}</strong> - {vendor.role || 'provider'} ({vendor.configured ? 'configured' : 'pending'})
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {envTemplate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Environment Template</h3>
          <p style={{ opacity: 0.8 }}>Providers included: {envTemplate.providers_included.length}</p>
          <p style={{ opacity: 0.8 }}>Missing keys: {envTemplate.missing_keys.length}</p>
          <pre
            style={{
              marginTop: 12,
              maxHeight: 240,
              overflow: 'auto',
              background: '#f6f7fa',
              border: '1px solid var(--line)',
              borderRadius: 8,
              padding: 12,
            }}
          >
            {envTemplate.env_template}
          </pre>
        </section>
      ) : null}
    </main>
  );
}
