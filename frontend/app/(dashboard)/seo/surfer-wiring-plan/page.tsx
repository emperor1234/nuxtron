'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

type WiringRow = {
  provider: string;
  kind: string;
  priority: 'P0' | 'P1' | 'P2';
  gate_impact_score: number;
  integration_pct_if_added: number;
  required_missing: string[];
  rationale: string;
};

type WiringPlanResponse = {
  status: string;
  wiring_plan: {
    configured: number;
    total: number;
    integration_configured_pct: number;
    stages: {
      stage_1_strict_live_foundation: { providers: string[] };
      stage_2_runtime_reliability: { providers: string[] };
      stage_3_full_automation_coverage: { providers: string[] };
    };
    prioritized_missing_providers: WiringRow[];
  };
};

export default function SurferWiringPlanPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<WiringPlanResponse | null>(null);

  async function loadPlan() {
    setLoading(true);
    setError('');
    try {
      const response = await apiGet<WiringPlanResponse>('/search-everywhere/surfer/wiring-plan', tenantId);
      setData(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load wiring plan');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPlan();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Surfer Readiness</p>
        <h1>Surfer Wiring Plan</h1>
        <p>Prioritized provider wiring plan grouped by gate impact.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <button onClick={() => void loadPlan()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      {data ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Execution Stages</h3>
          <ul className="bullet-list">
            <li>
              <strong>Stage 1:</strong>{' '}
              {data.wiring_plan.stages.stage_1_strict_live_foundation.providers.join(', ') || 'none'}
            </li>
            <li>
              <strong>Stage 2:</strong>{' '}
              {data.wiring_plan.stages.stage_2_runtime_reliability.providers.join(', ') || 'none'}
            </li>
            <li>
              <strong>Stage 3:</strong>{' '}
              {data.wiring_plan.stages.stage_3_full_automation_coverage.providers.join(', ') || 'none'}
            </li>
          </ul>
        </section>
      ) : null}

      {data ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Prioritized Missing Providers</h3>
          <ul className="bullet-list">
            {data.wiring_plan.prioritized_missing_providers.map((row) => (
              <li key={row.provider}>
                <strong>{row.priority}</strong> {row.provider} ({row.kind}) - impact {row.gate_impact_score} - next
                integration {row.integration_pct_if_added}%
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
