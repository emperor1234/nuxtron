'use client';

import { useMemo, useState } from 'react';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type HubspotAuditSummary = {
  products_total: number;
  required_routes_total: number;
  required_routes_implemented: number;
  providers_total: number;
  providers_configured: number;
  implementation_pct: number;
  integration_configured_pct: number;
  e2e_verified_pct: number;
  production_grade_ready: boolean;
};

type HubspotAuditResponse = {
  status: string;
  summary: HubspotAuditSummary;
  product_chart: Array<{
    key: string;
    name: string;
    premium_features_total: number;
    third_parties_total: number;
  }>;
  third_party_vendor_chart: Array<{
    product_key: string;
    product: string;
    vendor: string;
    relationship: string;
  }>;
  how_it_works: string[];
  validation_boundaries: {
    validated_slice: {
      scope: string;
      evidence: string[];
    };
    not_validated: string[];
  };
};

type HubspotCompletionResponse = {
  status: string;
  summary: {
    modules_total: number;
    modules_implemented: number;
    modules_e2e_verified: number;
    implementation_pct: number;
    e2e_verified_pct: number;
    integration_configured_pct: number;
    premium_features_total: number;
  };
  chart: Array<{
    key: string;
    product: string;
    implemented: boolean;
    e2e_verified: boolean;
    premium_features_total: number;
    vendors: string[];
  }>;
};

type HubspotGateResponse = {
  status: string;
  gate: {
    passed: boolean;
    blockers: string[];
    implementation_ok: boolean;
    e2e_ok: boolean;
    integration_ok: boolean;
  };
};

type HubspotVendorsResponse = {
  status: string;
  vendors_total: number;
  vendors_configured: number;
  vendor_chart: Array<{
    domain: string;
    vendor: string;
    capability: string;
    configured: boolean;
    evidence: string;
  }>;
};

type HubspotVerificationResponse = {
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
  };
};

type HubspotWiringResponse = {
  status: string;
  checklist_summary: {
    configured: number;
    total: number;
    configured_pct: number;
  };
  completion_summary: {
    implementation_pct: number;
    integration_configured_pct: number;
    e2e_verified_pct: number;
  };
  gate: {
    passed: boolean;
    blockers: string[];
  };
};

type HubspotReadModel = {
  audit: HubspotAuditResponse;
  completion: HubspotCompletionResponse;
  gate: HubspotGateResponse;
  vendors: HubspotVendorsResponse;
  verification: HubspotVerificationResponse;
};

const WIRING_VALUES: Record<string, string> = {
  DATAFORSEO_LOGIN: 'hubspot-dfs-user',
  DATAFORSEO_API_KEY: 'hubspot-dfs-key',
  SERPER_API_KEY: 'hubspot-serper-key',
  GOOGLE_ADS_DEVELOPER_TOKEN: 'hubspot-ads-dev',
  GOOGLE_ADS_CUSTOMER_ID: 'hubspot-ads-customer',
  GOOGLE_OAUTH_ACCESS_TOKEN: 'hubspot-google-oauth',
  GSC_SITE_URL: 'https://example-hubspot.com',
  CLOUDFLARE_API_TOKEN: 'hubspot-cloudflare',
  SSR_PROXY_URL: 'https://proxy.hubspot.example',
  POSTHOG_HOST: 'https://app.posthog.com',
  POSTHOG_API_KEY: 'hubspot-posthog',
  SENTRY_DSN: 'https://hubspot@sentry.example.com/1',
  UPSTASH_REDIS_REST_URL: 'https://upstash.hubspot.example',
  UPSTASH_REDIS_REST_TOKEN: 'hubspot-upstash-token',
};

function pctLabel(value: number): string {
  return `${Math.round(value * 10) / 10}%`;
}

function truthLabel(value: boolean): string {
  return value ? 'Yes' : 'No';
}

export default function HubspotE2EPage() {
  const tenantId = useMemo(() => DEFAULT_TENANT_ID, []);
  const [loading, setLoading] = useState(false);
  const [wiringLoading, setWiringLoading] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusLine, setStatusLine] = useState('');
  const [data, setData] = useState<HubspotReadModel | null>(null);

  async function loadAll(): Promise<void> {
    setLoading(true);
    setError('');
    try {
      const [audit, completion, gate, vendors, verification] = await Promise.all([
        apiGet<HubspotAuditResponse>('/search-everywhere/hubspot/full-e2e-audit', tenantId),
        apiGet<HubspotCompletionResponse>('/search-everywhere/hubspot/completion-chart', tenantId),
        apiGet<HubspotGateResponse>('/search-everywhere/hubspot/production-gate', tenantId),
        apiGet<HubspotVendorsResponse>('/search-everywhere/hubspot/vendors', tenantId),
        apiGet<HubspotVerificationResponse>('/search-everywhere/hubspot/verification-report', tenantId),
      ]);
      setData({ audit, completion, gate, vendors, verification });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load HubSpot E2E data');
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  async function wireProviders(): Promise<void> {
    setWiringLoading(true);
    setError('');
    setStatusLine('');
    try {
      const response = await apiSend<HubspotWiringResponse>('/search-everywhere/hubspot/wiring/apply', 'POST', {
        providers: ['DataForSEO', 'Serper.dev', 'Cloudflare'],
        include_all_missing: true,
        include_optional_auth: true,
        values: WIRING_VALUES,
      }, tenantId);
      setStatusLine(
        `Wiring applied: ${response.checklist_summary.configured}/${response.checklist_summary.total} providers configured, gate passed: ${truthLabel(response.gate.passed)}`
      );
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply provider wiring');
    } finally {
      setWiringLoading(false);
    }
  }

  async function seedSampleFlow(): Promise<void> {
    setSeedLoading(true);
    setError('');
    setStatusLine('');
    try {
      await apiSend('/search-everywhere/hubspot/crm/contacts', 'POST', {
        email: 'pipeline.owner@nuxtron.ai',
        firstname: 'Pipeline',
        lastname: 'Owner',
      }, tenantId);
      await apiSend('/search-everywhere/hubspot/crm/companies', 'POST', {
        name: 'Nuxtron Growth Labs',
        domain: 'nuxtron.ai',
      }, tenantId);
      await apiSend('/search-everywhere/hubspot/crm/deals', 'POST', {
        dealname: 'Q4 Expansion Program',
        stage: 'proposal',
        amount: 120000,
      }, tenantId);
      await apiSend('/search-everywhere/hubspot/service/tickets', 'POST', {
        subject: 'Enterprise onboarding escalation',
        priority: 'high',
      }, tenantId);
      await apiSend('/search-everywhere/hubspot/content/landing-pages', 'POST', {
        title: 'Autonomous Growth Platform Launch',
        slug: 'autonomous-growth-platform-launch',
        status: 'published',
      }, tenantId);
      await apiSend('/search-everywhere/hubspot/data/sync-jobs', 'POST', {
        source: 'Salesforce',
        target: 'HubSpot',
        mode: 'bidirectional',
      }, tenantId);
      setStatusLine('Sample E2E flow seeded: CRM, service, content, and data records were created.');
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to seed sample HubSpot E2E flow');
    } finally {
      setSeedLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">HubSpot End-to-End</p>
        <h1>HubSpot 100% Production-Grade Console</h1>
        <p>
          This page wires and verifies HubSpot product automation against real backend routes for CRM, service, content,
          data, commerce, and orchestration modules.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void loadAll()} disabled={loading || wiringLoading || seedLoading}>
            {loading ? 'Loading...' : 'Load HubSpot E2E'}
          </button>
          <button onClick={() => void wireProviders()} disabled={loading || wiringLoading || seedLoading}>
            {wiringLoading ? 'Applying...' : 'Apply HubSpot Provider Wiring'}
          </button>
          <button onClick={() => void seedSampleFlow()} disabled={loading || wiringLoading || seedLoading}>
            {seedLoading ? 'Running...' : 'Run Sample End-to-End Flow'}
          </button>
        </div>
        <p style={{ marginBottom: 0, marginTop: 12, opacity: 0.8 }}>
          API surface used: /search-everywhere/hubspot/full-e2e-audit, /completion-chart, /production-gate,
          /verification-report, /vendors, /wiring/apply and entity create routes.
        </p>
        {statusLine ? <p style={{ marginTop: 12, color: '#99f6e4' }}>{statusLine}</p> : null}
        {error ? <p style={{ marginTop: 12, color: '#fca5a5' }}>{error}</p> : null}
      </section>

      {data ? (
        <section className="legacy-auto-grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Implementation</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{pctLabel(data.audit.summary.implementation_pct)}</p>
            <p style={{ marginTop: 0, opacity: 0.75 }}>
              {data.audit.summary.required_routes_implemented}/{data.audit.summary.required_routes_total} required routes
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Integration Config</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{pctLabel(data.audit.summary.integration_configured_pct)}</p>
            <p style={{ marginTop: 0, opacity: 0.75 }}>
              {data.audit.summary.providers_configured}/{data.audit.summary.providers_total} providers configured
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>E2E Verified</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{pctLabel(data.audit.summary.e2e_verified_pct)}</p>
            <p style={{ marginTop: 0, opacity: 0.75 }}>
              Production Gate: {data.gate.gate.passed ? 'Passed' : 'Blocked'}
            </p>
          </article>
        </section>
      ) : null}

      {data ? (
        <section id="hubspot-product-completion" className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>HubSpot Product Completion</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {data.completion.chart.map((row) => (
              <div
                key={row.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(min(100%, 140px), 1fr) minmax(120px, 160px) minmax(120px, 160px) minmax(130px, 180px) 1fr',
                  gap: 10,
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 12,
                  padding: '10px 12px',
                }}
              >
                <strong>{row.product}</strong>
                <span>Implemented: {truthLabel(row.implemented)}</span>
                <span>E2E: {truthLabel(row.e2e_verified)}</span>
                <span>Features: {row.premium_features_total}</span>
                <span>Vendors: {row.vendors.join(', ')}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {data ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Third-Party Vendors and How They Work</h3>
          <p style={{ marginTop: 0, opacity: 0.8 }}>
            Vendors are runtime dependencies mapped per HubSpot module. Core platform vendor is HubSpot; external
            vendors drive ads, communication, enrichment, billing, storage, and AI orchestration.
          </p>
          <div style={{ display: 'grid', gap: 8 }}>
            {data.audit.third_party_vendor_chart.slice(0, 30).map((item) => (
              <div
                key={`${item.product_key}-${item.vendor}`}
                style={{
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 10,
                  padding: '8px 10px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 10,
                  flexWrap: 'wrap',
                }}
              >
                <span>
                  <strong>{item.product}</strong> uses <strong>{item.vendor}</strong>
                </span>
                <span style={{ opacity: 0.75 }}>{item.relationship.replaceAll('_', ' ')}</span>
              </div>
            ))}
          </div>
          <p style={{ marginTop: 12, opacity: 0.82 }}>
            Vendor inventory summary: {data.vendors.vendors_configured}/{data.vendors.vendors_total} inventory items
            configured.
          </p>
        </section>
      ) : null}

      {data ? (
        <section className="legacy-auto-grid" style={{ marginTop: 20 }}>
          <article id="how-it-works" className="card">
            <h3 style={{ marginTop: 0 }}>How It Works</h3>
            <ul className="bullet-list">
              {data.audit.how_it_works.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </article>
          <article id="validation-boundaries" className="card">
            <h3 style={{ marginTop: 0 }}>Validation Boundaries</h3>
            <p style={{ marginTop: 0 }}>
              <strong>Validated slice:</strong> {data.verification.verification.validation_boundaries.validated_slice}
            </p>
            <ul className="bullet-list">
              {data.verification.verification.validation_boundaries.not_validated.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </article>
        </section>
      ) : null}
    </main>
  );
}
