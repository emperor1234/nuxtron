'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type Json = Record<string, unknown>;

function asNumber(v: unknown, fb = 0): number {
  return typeof v === 'number' ? v : fb;
}
function asString(v: unknown, fb = ''): string {
  return typeof v === 'string' ? v : fb;
}
function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function asObject(v: unknown): Json {
  return v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : {};
}

const BAND_COLOR: Record<string, string> = {
  excellent: 'var(--success)',
  good: 'var(--brand)',
  fair: 'var(--warning)',
  poor: 'var(--danger)',
};

const OUTCOME_BADGE: Record<string, string> = {
  conversion: '💰',
  churn_saved: '🛡',
  dispute_resolved: '✅',
  fraud_blocked: '🚫',
  upsell_accepted: '📈',
  support_deflected: '🤖',
  campaign_attributed: '📣',
  no_outcome: '⏳',
};

export default function OutcomeGraphPage() {
  // Bound to the authenticated session; not user-editable (A01/IDOR).
  const [tenantId] = useState(resolveSessionTenant);
  const [graph, setGraph] = useState<Json>({});
  const [qualityScores, setQualityScores] = useState<unknown[]>([]);
  const [pendingActions, setPendingActions] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Record action form
  const [actionType, setActionType] = useState('ira_recommendation');
  const [actionTarget, setActionTarget] = useState('customers');
  const [actionCommand, setActionCommand] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  // Submit quality form
  const [qualityActionId, setQualityActionId] = useState('');
  const [accuracy, setAccuracy] = useState(85);
  const [safety, setSafety] = useState(90);
  const [speedMs, setSpeedMs] = useState(500);
  const [revenueImpact, setRevenueImpact] = useState(0);
  const [qualityMsg, setQualityMsg] = useState('');

  const totalActions = asNumber(graph.total_actions, 0);
  const attributed = asNumber(graph.attributed_outcomes, 0);
  const totalRevenue = asNumber(graph.total_revenue_impact_gbp, 0);
  const avgQuality = asNumber(graph.avg_decision_quality_score, 0);
  const outcomeDist = asObject(graph.outcome_distribution);
  const bandDist = asObject(graph.quality_band_distribution);

  const attributionRate = useMemo(
    () => (totalActions > 0 ? Math.round((attributed / totalActions) * 100) : 0),
    [totalActions, attributed]
  );

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [graphData, qualData, pendData] = await Promise.all([
        apiGet('/outcome/graph', tenantId),
        apiGet('/outcome/quality', tenantId),
        apiGet('/outcome/actions/pending', tenantId),
      ]);
      setGraph(graphData as Json);
      setQualityScores(asArray((qualData as Json).scores));
      setPendingActions(asArray((pendData as Json).pending));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  async function recordAction() {
    if (!actionCommand.trim()) return;
    setActionMsg('');
    try {
      const res = await apiPost(
        '/outcome/actions',
        {
          action_type: actionType,
          target: actionTarget,
          command: actionCommand,
          actor_role: 'ira_autonomous',
          dry_run: false,
        },
        tenantId
      );
      const id = asString((res as Json).action_id);
      setActionMsg(`Recorded action ${id}`);
      setQualityActionId(id);
      setActionCommand('');
      await load();
    } catch (e) {
      setActionMsg(`Error: ${String(e)}`);
    }
  }

  async function submitQuality() {
    if (!qualityActionId.trim()) return;
    setQualityMsg('');
    try {
      const res = await apiPost(
        '/outcome/quality',
        {
          action_id: qualityActionId,
          accuracy,
          safety,
          speed_ms: speedMs,
          revenue_impact_gbp: revenueImpact,
          human_override: false,
        },
        tenantId
      );
      const r = res as Json;
      setQualityMsg(`Score: ${asNumber(r.score)} (${asString(r.band)})`);
      await load();
    } catch (e) {
      setQualityMsg(`Error: ${String(e)}`);
    }
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '1100px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '0.5rem' }}>Outcome Graph</h1>
      <p style={{ color: 'var(--neutral)', marginBottom: '1.5rem' }}>
        Action-to-outcome attribution and Decision Quality scores — the core of the Outcome Data Flywheel.
      </p>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '0.5rem 1.2rem',
            borderRadius: 6,
            background: "var(--brand)",
            color: 'var(--on-brand)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <p style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</p>}

      {/* KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        {[
          { label: 'Total Actions', value: totalActions, color: 'var(--brand)' },
          { label: 'Attributed', value: attributed, color: 'var(--success)' },
          { label: 'Attribution Rate', value: `${attributionRate}%`, color: 'var(--brand)' },
          { label: 'Revenue Impact £', value: `£${totalRevenue.toFixed(2)}`, color: 'var(--warning)' },
          { label: 'Avg Quality Score', value: avgQuality, color: 'var(--success)' },
        ].map((kpi) => (
          <div
            key={kpi.label}
            style={{
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: 8,
              padding: '0.75rem 1rem',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '28px', fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
            <div style={{ fontSize: '12px', color: 'var(--neutral)' }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* Outcome distribution */}
      {Object.keys(outcomeDist).length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '0.75rem' }}>Outcome Distribution</h2>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {Object.entries(outcomeDist).map(([outcome, count]) => (
              <div
                key={outcome}
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '0.6rem 1rem',
                  minWidth: 130,
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '18px' }}>{OUTCOME_BADGE[outcome] ?? '📊'}</div>
                <div style={{ fontWeight: 600 }}>{count as number}</div>
                <div style={{ fontSize: '12px', color: 'var(--neutral)' }}>{outcome.replaceAll('_', ' ')}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Quality band distribution */}
      {Object.keys(bandDist).length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '0.75rem' }}>Decision Quality Bands</h2>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            {(['excellent', 'good', 'fair', 'poor'] as const).map((band) => (
              <div
                key={band}
                style={{
                  background: 'var(--card)',
                  border: `1px solid ${BAND_COLOR[band]}`,
                  borderRadius: 8,
                  padding: '0.6rem 1rem',
                  minWidth: 100,
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '22px', fontWeight: 700, color: BAND_COLOR[band] }}>
                  {(bandDist[band] as number) ?? 0}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--neutral)', textTransform: 'capitalize' }}>{band}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Record action form */}
      <section
        style={{
          marginBottom: '2rem',
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 8,
          padding: '1.25rem',
        }}
      >
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>Record Autonomous Action</h2>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          <input
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            placeholder="Action type"
            style={{
              width: 180,
              padding: '0.4rem 0.7rem',
              borderRadius: 6,
              border: '1px solid var(--line)',
              background: 'var(--card)',
              color: 'var(--text)',
            }}
          />
          <input
            value={actionTarget}
            onChange={(e) => setActionTarget(e.target.value)}
            placeholder="Target"
            style={{
              width: 130,
              padding: '0.4rem 0.7rem',
              borderRadius: 6,
              border: '1px solid var(--line)',
              background: 'var(--card)',
              color: 'var(--text)',
            }}
          />
          <input
            value={actionCommand}
            onChange={(e) => setActionCommand(e.target.value)}
            placeholder="Command description"
            style={{
              flex: 1,
              minWidth: 200,
              padding: '0.4rem 0.7rem',
              borderRadius: 6,
              border: '1px solid var(--line)',
              background: 'var(--card)',
              color: 'var(--text)',
            }}
          />
          <button
            onClick={recordAction}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 6,
              background: 'var(--success)',
              color: 'var(--on-status)',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Record
          </button>
        </div>
        {actionMsg && <p style={{ color: 'var(--brand)', fontSize: '14px' }}>{actionMsg}</p>}
      </section>

      {/* Submit quality score */}
      <section
        style={{
          marginBottom: '2rem',
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 8,
          padding: '1.25rem',
        }}
      >
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>Submit Decision Quality Score</h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
            gap: '0.5rem',
            marginBottom: '0.75rem',
          }}
        >
          <div>
            <label htmlFor="quality-action-id" style={{ fontSize: '12px', color: 'var(--neutral)' }}>
              Action ID
            </label>
            <input
              id="quality-action-id"
              value={qualityActionId}
              onChange={(e) => setQualityActionId(e.target.value)}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="quality-accuracy" style={{ fontSize: '12px', color: 'var(--neutral)' }}>
              Accuracy (0-100)
            </label>
            <input
              id="quality-accuracy"
              type="number"
              min={0}
              max={100}
              value={accuracy}
              onChange={(e) => setAccuracy(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="quality-safety" style={{ fontSize: '12px', color: 'var(--neutral)' }}>
              Safety (0-100)
            </label>
            <input
              id="quality-safety"
              type="number"
              min={0}
              max={100}
              value={safety}
              onChange={(e) => setSafety(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="quality-speed" style={{ fontSize: '12px', color: 'var(--neutral)' }}>
              Speed (ms)
            </label>
            <input
              id="quality-speed"
              type="number"
              min={0}
              value={speedMs}
              onChange={(e) => setSpeedMs(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="quality-revenue" style={{ fontSize: '12px', color: 'var(--neutral)' }}>
              Revenue Impact £
            </label>
            <input
              id="quality-revenue"
              type="number"
              value={revenueImpact}
              onChange={(e) => setRevenueImpact(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
        </div>
        <button
          onClick={submitQuality}
          style={{
            padding: '0.5rem 1.2rem',
            borderRadius: 6,
            background: "var(--brand)",
            color: 'var(--on-brand)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Submit Score
        </button>
        {qualityMsg && <p style={{ color: 'var(--brand)', fontSize: '14px', marginTop: '0.5rem' }}>{qualityMsg}</p>}
      </section>

      {/* Recent quality scores */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '0.75rem' }}>Recent Quality Scores</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--line)', }}>
              {['Action ID', 'Score', 'Band', 'Accuracy', 'Safety', 'Revenue £', 'Date'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.6rem', color: 'var(--neutral)' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {qualityScores.slice(0, 20).map((q, idx) => {
              const qs = q as Json;
              const band = asString(qs.band, 'poor');
              return (
                <tr key={`${asString(qs.id)}-${idx}`} style={{ borderBottom: '1px solid var(--line-soft)' }}>
                  <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'monospace', fontSize: '12px', color: 'var(--neutral)' }}>
                    {asString(qs.action_id).slice(0, 12)}…
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700, color: BAND_COLOR[band] }}>
                    {asNumber(qs.score)}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem', color: BAND_COLOR[band], textTransform: 'capitalize' }}>
                    {band}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{asNumber(qs.accuracy)}</td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{asNumber(qs.safety)}</td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>£{asNumber(qs.revenue_impact_gbp).toFixed(2)}</td>
                  <td style={{ padding: '0.4rem 0.6rem', color: 'var(--neutral)', fontSize: '12px' }}>
                    {asString(qs.created_at).slice(0, 10)}
                  </td>
                </tr>
              );
            })}
            {qualityScores.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: '1rem', color: 'var(--neutral)', textAlign: 'center' }}>
                  No quality scores yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {/* Pending attribution */}
      {pendingActions.length > 0 && (
        <section>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '0.75rem' }}>
            Pending Attribution ({pendingActions.length})
          </h2>
          <p style={{ color: 'var(--neutral)', fontSize: '14px', marginBottom: '0.75rem' }}>
            These actions have no attributed outcome yet. Use <code>/outcome/outcomes</code> to close them.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {pendingActions.slice(0, 10).map((a, idx) => {
              const act = a as Json;
              return (
                <div
                  key={`${asString(act.id)}-${idx}`}
                  style={{
                    background: 'var(--card)',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    padding: '0.5rem 0.75rem',
                    fontSize: '13px',
                  }}
                >
                  <div style={{ fontFamily: 'monospace', color: 'var(--neutral)' }}>{asString(act.id).slice(0, 14)}…</div>
                  <div>{asString(act.action_type)}</div>
                  <div style={{ color: 'var(--neutral)' }}>{asString(act.command).slice(0, 40)}</div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}
