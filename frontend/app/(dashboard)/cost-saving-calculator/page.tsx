'use client';

import { useState } from 'react';

import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type CostSavingsResponse = {
  output: {
    total_pages_in_scope: number;
    manual_monthly_hours: number;
    automated_monthly_hours_saved: number;
    monthly_labor_cost_saved_usd: number;
    net_monthly_savings_usd: number;
    annual_net_savings_usd: number;
    payback_days: number;
  };
};

export default function CostSavingCalculatorPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<CostSavingsResponse | null>(null);

  async function runCalculation() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<CostSavingsResponse>(
        '/search-everywhere/cost-savings-calculator',
        'POST',
        {
          sites_count: 50,
          pages_per_site: 1500,
          monthly_deployments: 5,
          manual_minutes_per_page: 1.4,
          hourly_rate_usd: 90,
          automation_coverage_pct: 86,
          tool_monthly_cost_usd: 799,
        },
        tenantId
      );
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to calculate savings');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Calculator</p>
        <h1>SEO Automation Cost Saving Calculator</h1>
        <p>Estimate labor hours replaced by portfolio-wide automation and compute monthly plus annual net savings.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <button onClick={() => void runCalculation()} disabled={loading}>
          {loading ? 'Calculating...' : 'Run Cost Saving Model'}
        </button>
        {error ? <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p> : null}
      </section>

      {result ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Pages In Scope</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{result.output.total_pages_in_scope.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Monthly Manual Hours</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{result.output.manual_monthly_hours.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Hours Saved</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {result.output.automated_monthly_hours_saved.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Monthly Labor Saved</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              ${result.output.monthly_labor_cost_saved_usd.toLocaleString()}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Net Monthly Savings</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>${result.output.net_monthly_savings_usd.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Net Annual Savings</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>${result.output.annual_net_savings_usd.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Payback</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{result.output.payback_days.toLocaleString()} days</p>
          </article>
        </section>
      ) : null}
    </main>
  );
}
