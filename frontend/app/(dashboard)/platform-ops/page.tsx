'use client';

import { useEffect, useState } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Json = Record<string, unknown>;
type VerifyCriterion = {
  id: string;
  description: string;
  pass: boolean;
  details?: unknown;
};

type Severity = 'critical' | 'high' | 'medium';

function criterionSeverity(id: string): Severity {
  if (id === 'database-ready' || id === 'strict-no-mock-enabled') return 'critical';
  if (id === 'content-generation-verify-passed' || id === 'critical-module-buffers-below-limit') return 'high';
  return 'medium';
}

function severityBadgeStyle(severity: Severity): React.CSSProperties {
  if (severity === 'critical') {
    return { background: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' };
  }
  if (severity === 'high') {
    return { background: '#fef3c7', color: '#b45309', border: '1px solid #fcd34d' };
  }
  return { background: '#dbeafe', color: '#6366f1', border: '1px solid #93c5fd' };
}

function readFailedCriteria(payload: Json): VerifyCriterion[] {
  const verification = payload.verification;
  if (!verification || typeof verification !== 'object') return [];
  const criteria = (verification as Json).criteria;
  if (!Array.isArray(criteria)) return [];

  return criteria
    .map((item): VerifyCriterion | null => {
      if (!item || typeof item !== 'object') return null;
      const row = item as Json;
      if (typeof row.id !== 'string' || typeof row.description !== 'string') return null;
      return {
        id: row.id,
        description: row.description,
        pass: Boolean(row.pass),
        details: row.details,
      };
    })
    .filter((row): row is VerifyCriterion => row !== null)
    .filter((row) => !row.pass);
}

function Box({ title, data }: { title: string; data: unknown }) {
  return (
    <section style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <pre style={{ margin: 0, color: 'var(--muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </section>
  );
}

export default function PlatformOpsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [status, setStatus] = useState<Json>({});
  const [metrics, setMetrics] = useState<Json>({});
  const [antiFailure, setAntiFailure] = useState<Json>({});
  const [apiUsage, setApiUsage] = useState<Json>({});
  const [capabilities, setCapabilities] = useState<Json>({});
  const [noMockVerify, setNoMockVerify] = useState<Json>({});
  const [error, setError] = useState('');
  const failedCriteria = readFailedCriteria(noMockVerify);

  async function load() {
    try {
      setError('');
      const [statusRes, metricsRes, antiRes, apiRes, capsRes, noMockRes] = await Promise.all([
        apiGet<Json>('/ops/platform/status', tenantId),
        apiGet<Json>('/ops/platform/metrics-summary', tenantId),
        apiGet<Json>('/ops/platform/anti-failure-status', tenantId),
        apiGet<Json>('/ops/security/api-usage?limit=25', tenantId),
        apiGet<Json>('/ops/platform/capabilities', tenantId),
        apiGet<Json>('/production/no-mock/verify', tenantId),
      ]);
      setStatus(statusRes);
      setMetrics(metricsRes);
      setAntiFailure(antiRes);
      setApiUsage(apiRes);
      setCapabilities(capsRes);
      setNoMockVerify(noMockRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load ops');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Platform Ops</h1>
        <p style={{ color: 'var(--muted)' }}>
          Operational health, metrics summary, anti-failure systems, API usage, and capability coverage.
        </p>
        {error && (
          <div
            style={{
              background: 'var(--bg-soft)',
              border: '1px solid #ef444488',
              borderRadius: 12,
              padding: 12,
              color: '#f87171',
              marginBottom: 10,
            }}
          >
            {error}
          </div>
        )}
        <section
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 16,
            marginBottom: 10,
          }}
        >
          <h3 style={{ marginTop: 0 }}>Strict No-Mock Verification</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
            <span>
              Status: <strong>{String(noMockVerify.status || 'unknown')}</strong>
            </span>
            <span>
              Source:{' '}
              <strong
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 999,
                  padding: '2px 8px',
                  display: 'inline-block',
                }}
              >
                {String(noMockVerify.source || 'n/a')}
              </strong>
            </span>
            <span>
              Route family: <strong>{String(noMockVerify.route_family || 'n/a')}</strong>
            </span>
            <span>
              Fallback blocked: <strong>{String(noMockVerify.fallback_blocked || false)}</strong>
            </span>
          </div>
          <p style={{ margin: 0, color: 'var(--muted)' }}>
            {String(noMockVerify.detail || 'No diagnostics available yet.')}
          </p>
          {failedCriteria.length > 0 && (
            <div style={{ marginTop: 12, overflowX: 'auto' }}>
              <h4 style={{ margin: '0 0 8px 0' }}>Failed Criteria</h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid var(--line)', padding: '6px 8px' }}>ID</th>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid var(--line)', padding: '6px 8px' }}>
                      Severity
                    </th>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid var(--line)', padding: '6px 8px' }}>
                      Description
                    </th>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid var(--line)', padding: '6px 8px' }}>
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {failedCriteria.map((criterion) => {
                    const severity = criterionSeverity(criterion.id);
                    return (
                      <tr key={criterion.id}>
                        <td style={{ borderBottom: '1px solid var(--line)', padding: '6px 8px', whiteSpace: 'nowrap' }}>
                          {criterion.id}
                        </td>
                        <td style={{ borderBottom: '1px solid var(--line)', padding: '6px 8px', whiteSpace: 'nowrap' }}>
                          <span
                            style={{
                              ...severityBadgeStyle(severity),
                              borderRadius: 999,
                              padding: '2px 8px',
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              fontSize: 11,
                              letterSpacing: 0.4,
                            }}
                          >
                            {severity}
                          </span>
                        </td>
                        <td style={{ borderBottom: '1px solid var(--line)', padding: '6px 8px' }}>
                          {criterion.description}
                        </td>
                        <td
                          style={{ borderBottom: '1px solid var(--line)', padding: '6px 8px', color: 'var(--muted)' }}
                        >
                          {criterion.details === undefined ? '-' : JSON.stringify(criterion.details)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <Box title="Platform Status" data={status} />
          <Box title="Metrics Summary" data={metrics} />
          <Box title="Anti-failure Systems" data={antiFailure} />
          <Box title="Security API Usage" data={apiUsage} />
        </div>
        <div style={{ marginTop: 10 }}>
          <Box title="No-Mock Verify Payload" data={noMockVerify} />
        </div>
        <div style={{ marginTop: 10 }}>
          <Box title="Capabilities Contract" data={capabilities} />
        </div>
      </div>
    </main>
  );
}
