'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type Json = Record<string, unknown>;

function asString(v: unknown, fb = ''): string {
  return typeof v === 'string' ? v : fb;
}
function asNumber(v: unknown, fb = 0): number {
  return typeof v === 'number' ? v : fb;
}
function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

const VERTICAL_COLORS: Record<string, string> = {
  ecommerce: '#f59e0b',
  saas: '#6366f1',
  agency: '#6366f1',
  media: '#ec4899',
  fintech: '#22c55e',
  healthtech: '#06b6d4',
  nonprofit: '#84cc16',
  education: '#f97316',
  marketplace: '#8b5cf6',
  other: 'var(--muted)',
};

export default function PlaybooksPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [playbooks, setPlaybooks] = useState<unknown[]>([]);
  const [runs, setRuns] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [runMsg, setRunMsg] = useState('');
  const [runningId, setRunningId] = useState('');
  const [filterVertical, setFilterVertical] = useState('all');
  const [selectedPlaybook, setSelectedPlaybook] = useState<Json | null>(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [pbData, runsData] = await Promise.all([
        apiGet('/playbooks', tenantId),
        apiGet('/playbooks/runs/list', tenantId),
      ]);
      setPlaybooks(asArray((pbData as Json).playbooks));
      setRuns(asArray((runsData as Json).runs));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  const verticals = [
    'all',
    ...Array.from(new Set(playbooks.map((p) => asString((p as Json).vertical)).filter(Boolean))),
  ];

  const filtered =
    filterVertical === 'all' ? playbooks : playbooks.filter((p) => asString((p as Json).vertical) === filterVertical);

  async function runPlaybook(playbookId: string, dryRun = true) {
    setRunningId(playbookId);
    setRunMsg('');
    try {
      const res = await apiPost('/playbooks/run', { playbook_id: playbookId, dry_run: dryRun, config: {} }, tenantId);
      const r = res as Json;
      setRunMsg(`${dryRun ? 'Preview' : 'Activated'}: ${asString((r.playbook as Json | null)?.name ?? r.run_id)}`);
      await load();
    } catch (e) {
      setRunMsg(`Error: ${String(e)}`);
    } finally {
      setRunningId('');
    }
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '0.5rem' }}>Integration Playbooks</h1>
      <p style={{ color: '#888', marginBottom: '1.5rem' }}>
        10 prebuilt playbooks with measurable ROI targets — activate any in one click to start the Integration Flywheel.
      </p>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem', alignItems: 'center' }}>
        <input
          value={tenantId}
          readOnly
          placeholder="Tenant ID"
          style={{
            padding: '0.5rem 0.8rem',
            borderRadius: 6,
            border: '1px solid #333',
            background: '#111',
            color: '#fff',
            minWidth: 200,
          }}
        />
        <select
          value={filterVertical}
          onChange={(e) => setFilterVertical(e.target.value)}
          style={{
            padding: '0.5rem 0.8rem',
            borderRadius: 6,
            border: '1px solid #333',
            background: '#111',
            color: '#fff',
          }}
        >
          {verticals.map((v) => (
            <option key={v} value={v}>
              {v === 'all' ? 'All verticals' : v.charAt(0).toUpperCase() + v.slice(1)}
            </option>
          ))}
        </select>
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '0.5rem 1.2rem',
            borderRadius: 6,
            background: '#6366f1',
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</p>}
      {runMsg && <p style={{ color: 'var(--brand)', marginBottom: '1rem', fontSize: '14px' }}>{runMsg}</p>}

      {/* Playbook grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
          gap: '1rem',
          marginBottom: '2.5rem',
        }}
      >
        {filtered.map((p, idx) => {
          const pb = p as Json;
          const roi = pb.roi_target as Json | undefined;
          const vertColor = VERTICAL_COLORS[asString(pb.vertical)] ?? 'var(--muted)';
          return (
            <div
              key={`${asString(pb.id)}-${idx}`}
              style={{
                background: 'var(--card)',
                border: `1px solid ${pb.id === selectedPlaybook?.id ? '#6366f1' : '#222'}`,
                borderRadius: 10,
                padding: '1.25rem',
                transition: 'border-color 0.15s',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '0.5rem',
                }}
              >
                <button
                  onClick={() => setSelectedPlaybook(selectedPlaybook?.id === pb.id ? null : pb)}
                  style={{
                    fontWeight: 600,
                    fontSize: '16px',
                    margin: 0,
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    padding: 0,
                    textAlign: 'left',
                  }}
                >
                  {asString(pb.name)}
                </button>
                <span
                  style={{
                    fontSize: '11px',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 16,
                    background: vertColor + '22',
                    color: vertColor,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                  }}
                >
                  {asString(pb.vertical)}
                </span>
              </div>
              <p style={{ color: '#aaa', fontSize: '13px', marginBottom: '0.75rem' }}>{asString(pb.description)}</p>

              {roi && (
                <div style={{ fontSize: '13px', color: '#22c55e', marginBottom: '0.5rem' }}>
                  🎯 ROI target: {asNumber(roi.value)} {asString(roi.metric).replaceAll('_', ' ')}
                </div>
              )}
              <div style={{ fontSize: '12px', color: '#888', marginBottom: '0.75rem' }}>
                ⏱ Time to value: {asNumber(pb.time_to_value_days)} day(s)
              </div>

              {selectedPlaybook?.id === pb.id && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ fontSize: '13px', color: '#888', marginBottom: '0.5rem', fontWeight: 600 }}>
                    Steps:
                  </div>
                  <ol style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '13px', color: '#ccc' }}>
                    {asArray(pb.steps).map((step, si) => (
                      <li key={`${asString(step).slice(0, 30)}-${si}`} style={{ marginBottom: '0.2rem' }}>
                        {asString(step)}
                      </li>
                    ))}
                  </ol>
                  <div style={{ fontSize: '12px', color: '#888', marginTop: '0.5rem' }}>
                    Integrations:{' '}
                    {asArray(pb.integrations)
                      .map((i) => asString(i))
                      .join(', ')}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void runPlaybook(asString(pb.id), true);
                      }}
                      disabled={runningId === asString(pb.id)}
                      style={{
                        padding: '0.4rem 0.8rem',
                        borderRadius: 6,
                        background: '#6366f1',
                        color: '#fff',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '13px',
                      }}
                    >
                      Preview
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void runPlaybook(asString(pb.id), false);
                      }}
                      disabled={runningId === asString(pb.id)}
                      style={{
                        padding: '0.4rem 0.8rem',
                        borderRadius: 6,
                        background: '#16a34a',
                        color: '#fff',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 600,
                      }}
                    >
                      {runningId === asString(pb.id) ? 'Activating…' : '▶ Activate'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Recent runs */}
      {runs.length > 0 && (
        <section>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>Recent Runs</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #333' }}>
                {['Playbook', 'Status', 'Dry Run', 'Steps', 'Date'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.6rem', color: '#888' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 20).map((r, idx) => {
                const run = r as Json;
                return (
                  <tr key={`${asString(run.id)}-${idx}`} style={{ borderBottom: '1px solid #1a1a1a' }}>
                    <td style={{ padding: '0.4rem 0.6rem' }}>{asString(run.playbook_name)}</td>
                    <td
                      style={{
                        padding: '0.4rem 0.6rem',
                        color: asString(run.status).includes('dry') ? '#f59e0b' : '#22c55e',
                      }}
                    >
                      {asString(run.status)}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', color: '#888' }}>
                      {(() => {
                        // NOSONAR
                        if (run.dry_run === true) return 'true';
                        if (run.dry_run === false) return 'false';
                        return 'n/a';
                      })()}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem' }}>
                      {asNumber(run.steps_completed)}/{asNumber(run.steps_total)}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', color: '#888', fontSize: '12px' }}>
                      {asString(run.created_at).slice(0, 10)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
