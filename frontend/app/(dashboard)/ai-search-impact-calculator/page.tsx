'use client';

import { useState } from 'react';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type CostSavingsResponse = {
  output: {
    automated_monthly_hours_saved: number;
    monthly_labor_cost_saved_usd: number;
    net_monthly_savings_usd: number;
    annual_net_savings_usd: number;
    payback_days: number;
  };
};

type AiImpactResponse = {
  output: {
    incremental_clicks_monthly: number;
    incremental_conversions_monthly: number;
    incremental_revenue_monthly_usd: number;
    incremental_revenue_annual_usd: number;
  };
};

type VendorsResponse = {
  configured: number;
  total: number;
  vendors: Array<{
    key: string;
    display_name: string;
    category: string;
    configured: boolean;
    mode: string;
  }>;
};

type ReadinessResponse = {
  readiness: {
    configured_pct: number;
    grade: string;
    production_ready: boolean;
  };
};

export default function AiSearchImpactCalculatorPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [costSavings, setCostSavings] = useState<CostSavingsResponse | null>(null);
  const [aiImpact, setAiImpact] = useState<AiImpactResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);

  async function runCalculators() {
    setLoading(true);
    setError('');
    try {
      const [costRes, impactRes, vendorRes, readinessRes] = await Promise.all([
        apiSend<CostSavingsResponse>(
          '/search-everywhere/cost-savings-calculator',
          'POST',
          {
            sites_count: 75,
            pages_per_site: 1200,
            monthly_deployments: 6,
            manual_minutes_per_page: 1.2,
            hourly_rate_usd: 95,
            automation_coverage_pct: 88,
            tool_monthly_cost_usd: 899,
          },
          tenantId
        ),
        apiSend<AiImpactResponse>(
          '/search-everywhere/ai-search-impact-calculator',
          'POST',
          {
            monthly_sessions: 250000,
            current_ai_visibility_pct: 2,
            target_ai_visibility_pct: 14,
            ai_ctr_pct: 16,
            conversion_rate_pct: 2.8,
            avg_order_value_usd: 140,
            gross_margin_pct: 62,
          },
          tenantId
        ),
        apiGet<VendorsResponse>('/search-everywhere/vendors', tenantId),
        apiGet<ReadinessResponse>('/search-everywhere/readiness', tenantId),
      ]);

      setCostSavings(costRes);
      setAiImpact(impactRes);
      setVendors(vendorRes);
      setReadiness(readinessRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run impact calculators');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Search Everywhere Automation</p>
        <h1>AI Search Impact And Cost Savings Calculator</h1>
        <p>Calculate labor savings, AI-search revenue lift, and live vendor readiness in one end-to-end workflow.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>Run End-to-End Projection</h2>
        <p style={{ marginTop: 0, opacity: 0.85 }}>
          This runs both calculators and fetches integration readiness + third-party vendor status from live backend
          APIs.
        </p>
        <button onClick={() => void runCalculators()} disabled={loading}>
          {loading ? 'Running...' : 'Run Calculators'}
        </button>
        {error ? <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p> : null}
      </section>

      {costSavings ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Monthly Hours Saved</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {costSavings.output.automated_monthly_hours_saved.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Net Monthly Savings</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              ${costSavings.output.net_monthly_savings_usd.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Net Annual Savings</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              ${costSavings.output.annual_net_savings_usd.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Payback</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{costSavings.output.payback_days.toLocaleString()} days</p>
          </article>
        </section>
      ) : null}

      {aiImpact ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Incremental AI Clicks</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {aiImpact.output.incremental_clicks_monthly.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Incremental Conversions</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {aiImpact.output.incremental_conversions_monthly.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Monthly AI Revenue Lift</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              ${aiImpact.output.incremental_revenue_monthly_usd.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Annual AI Revenue Lift</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              ${aiImpact.output.incremental_revenue_annual_usd.toLocaleString()}
            </p>
          </article>
        </section>
      ) : null}

      {vendors ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Third-Party Vendors</h3>
          <p style={{ marginTop: 0 }}>
            Configured: {vendors.configured}/{vendors.total}
            {readiness ? ` (${readiness.readiness.configured_pct}% • Grade ${readiness.readiness.grade})` : ''}
          </p>
          <ul className="bullet-list">
            {vendors.vendors.map((vendor) => (
              <li key={vendor.key}>
                <strong>{vendor.display_name}</strong> ({vendor.category}) -{' '}
                {vendor.configured ? 'configured' : 'not configured'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
