'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, DEFAULT_TENANT_ID, PROXY_BASE_URL } from '@/app/lib/api-client';
import { Page, PageHeader, Card, CardTitle, Button, Badge, Stat, StatGrid, Field } from '../_ui/kit';

const selectStyle: React.CSSProperties = {
  height: 38,
  width: '100%',
  padding: '0 12px',
  border: '1px solid var(--nx-border)',
  borderRadius: 10,
  background: 'var(--nx-card)',
  color: 'var(--nx-ink)',
  fontFamily: 'inherit',
  fontSize: 13.5,
};

type JsonObject = Record<string, unknown>;

type SecurityAnalytics = {
  status: string;
  tenant_id: string;
  kpi: {
    total_calls: number;
    success_calls: number;
    success_rate: number;
    avg_roi: number;
    avg_latency_ms: number;
    total_estimated_cost: number;
    total_estimated_value: number;
    is_blocked: boolean;
    blocked_until_ts: number;
  };
  provider_graph: Array<{
    provider: string;
    calls: number;
    avg_roi: number;
    color: string;
    status: string;
  }>;
  timeline: Array<{
    ts: number;
    provider: string;
    model: string;
    roi: number;
    latency_ms: number;
    estimated_cost: number;
    status: string;
  }>;
  alerts: Array<{
    id: number;
    severity: string;
    title: string;
    created_at: string;
    details: JsonObject;
  }>;
};

type IdsState = {
  total_events: number;
  by_source: Record<string, number>;
  by_severity: Record<string, number>;
  security_email_delivery?: Record<string, number>;
  recent_events: JsonObject[];
};

type SecurityQueueItem = {
  id: number;
  provider: string;
  to: string;
  subject: string;
  status: 'queued' | 'sending' | 'retry' | 'sent' | 'failed';
  attempts: number;
  delivery_detail: string;
  requeued_by?: string;
  requeued_source_ip?: string;
  requeued_at?: string | null;
  updated_at?: string | null;
  queue_source: 'db' | 'memory';
};

type SecurityQueueResponse = {
  status: string;
  queue_source: 'db' | 'memory';
  filter_status: string;
  limit: number;
  cursor_before_id: number;
  has_more: boolean;
  next_cursor_before_id: number | null;
  count: number;
  items: SecurityQueueItem[];
};

type ChartPoint = {
  label: string;
  value: number;
  accent?: string;
  note?: string;
};

function accentForAlertSeverity(label: string) {
  if (label === 'critical') return 'linear-gradient(90deg, #ef4444, #b91c1c)';
  if (label === 'warning') return 'linear-gradient(90deg, #f59e0b, #f97316)';
  return 'linear-gradient(90deg, #0ea5e9, #22c55e)';
}

function accentForIdsSeverity(label: string) {
  if (label === 'critical') return 'linear-gradient(90deg, #ef4444, #b91c1c)';
  if (label === 'high') return 'linear-gradient(90deg, #f97316, #ea580c)';
  return 'linear-gradient(90deg, #0ea5e9, #14b8a6)';
}

function accentForDelivery(label: string) {
  if (label === 'failed') return 'linear-gradient(90deg, #ef4444, #b91c1c)';
  if (label === 'sent') return 'linear-gradient(90deg, #22c55e, #10b981)';
  return 'linear-gradient(90deg, #0ea5e9, #14b8a6)';
}

function ChartCard({
  title,
  subtitle,
  children,
}: Readonly<{ title: string; subtitle?: string; children: React.ReactNode }>) {
  return (
    <Card>
      <div style={{ marginBottom: 12 }}>
        <CardTitle sub={subtitle}>{title}</CardTitle>
      </div>
      {children}
    </Card>
  );
}

function BarChart({ data, emptyLabel }: Readonly<{ data: ChartPoint[]; emptyLabel: string }>) {
  if (data.length === 0) return <p className="muted">{emptyLabel}</p>;
  const maxValue = Math.max(1, ...data.map((item) => item.value));
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {data.map((item) => (
        <div key={item.label}>
          <div className="queue-head" style={{ marginBottom: 6 }}>
            <span>{item.label}</span>
            <strong>{item.note ? `${item.value} • ${item.note}` : item.value}</strong>
          </div>
          <div className="queue-track" style={{ height: 14 }}>
            <div
              className="queue-fill"
              style={{
                width: `${Math.max(6, Math.round((item.value / maxValue) * 100))}%`,
                background: item.accent || 'linear-gradient(90deg, #0ea5e9, #14b8a6)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function LineChart({
  data,
  emptyLabel,
  stroke,
  formatValue,
}: Readonly<{ data: ChartPoint[]; emptyLabel: string; stroke: string; formatValue?: (value: number) => string }>) {
  if (data.length === 0) return <p className="muted">{emptyLabel}</p>;
  const width = 760;
  const height = 240;
  const padding = 24;
  const values = data.map((item) => item.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(1, maxValue - minValue);
  const stepX = data.length > 1 ? (width - padding * 2) / (data.length - 1) : 0;
  const points = data.map((item, index) => {
    const x = padding + index * stepX;
    const normalized = (item.value - minValue) / range;
    const y = height - padding - normalized * (height - padding * 2);
    return { x, y, item };
  });
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', overflow: 'visible' }}
        aria-label="Line chart"
      >
        <title>Line chart</title>
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="rgba(148, 163, 184, 0.35)"
        />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(148, 163, 184, 0.35)" />
        <path d={path} fill="none" stroke={stroke} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((point) => (
          <g key={point.item.label}>
            <circle cx={point.x} cy={point.y} r="4" fill={stroke} />
          </g>
        ))}
      </svg>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))', gap: 10 }}>
        {points.map((point) => (
          <div key={point.item.label} className="card" style={{ padding: 10 }}>
            <p className="kpi-label">{point.item.label}</p>
            <strong>{formatValue ? formatValue(point.item.value) : point.item.value.toFixed(2)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTimeLabel(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function fetchIdsState(tenantId: string, superAdminKey: string): Promise<IdsState> {
  const idsResp = await fetch(`${PROXY_BASE_URL}/ai/security/admin/ids/state?window_minutes=60`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      'X-Super-Admin-Key': superAdminKey,
    },
    cache: 'no-store',
  });
  const payload = (await idsResp.json()) as JsonObject;
  const detail = typeof payload.detail === 'string' ? payload.detail : 'Failed to load IDS state';
  if (!idsResp.ok) throw new Error(detail);
  return payload as unknown as IdsState;
}

async function fetchAdminQueue(
  tenantId: string,
  superAdminKey: string,
  queueFilter: string,
  cursorBeforeId: number
): Promise<SecurityQueueResponse> {
  const query = new URLSearchParams({
    status: queueFilter,
    limit: '8',
    cursor_before_id: String(cursorBeforeId),
  }).toString();
  const resp = await fetch(`${PROXY_BASE_URL}/ai/security/admin/email-queue?${query}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      'X-Super-Admin-Key': superAdminKey,
    },
    cache: 'no-store',
  });
  const payload = (await resp.json()) as JsonObject;
  const detail = typeof payload.detail === 'string' ? payload.detail : 'Failed to load security email queue';
  if (!resp.ok) throw new Error(detail);
  return payload as unknown as SecurityQueueResponse;
}

async function postRequeue(tenantId: string, superAdminKey: string, id: number): Promise<void> {
  const resp = await fetch(`${PROXY_BASE_URL}/ai/security/admin/email-queue/${id}/requeue`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      'X-Super-Admin-Key': superAdminKey,
    },
  });
  const payload = (await resp.json()) as JsonObject;
  const detail = typeof payload.detail === 'string' ? payload.detail : 'Failed to requeue item';
  if (!resp.ok) throw new Error(detail);
}

async function loadAdminQueueState(
  tenantId: string,
  superAdminKey: string,
  queueFilter: string,
  cursorBeforeId: number
): Promise<SecurityQueueResponse | null> {
  if (!superAdminKey.trim()) return null;
  return fetchAdminQueue(tenantId, superAdminKey.trim(), queueFilter, cursorBeforeId);
}

async function loadAllState(
  tenantId: string,
  superAdminKey: string,
  queueFilter: string
): Promise<{ analytics: SecurityAnalytics; idsState: IdsState | null; queueData: SecurityQueueResponse | null }> {
  const analytics = (await apiGet(
    '/ai/security/analytics?window_minutes=60',
    tenantId
  )) as unknown as SecurityAnalytics;
  if (!superAdminKey.trim()) {
    return { analytics, idsState: null, queueData: null };
  }
  const idsState = await fetchIdsState(tenantId, superAdminKey.trim());
  const queueData = await fetchAdminQueue(tenantId, superAdminKey.trim(), queueFilter, 0);
  return { analytics, idsState, queueData };
}

function assertAdminKey(superAdminKey: string, message: string): void {
  if (!superAdminKey.trim()) throw new Error(message);
}

// NOSONAR: consolidated operator page container keeps stateful actions and telemetry rendering together.
export default function AiSecurityPage() {
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [superAdminKey, setSuperAdminKey] = useState('');
  const [analytics, setAnalytics] = useState<SecurityAnalytics | null>(null);
  const [idsState, setIdsState] = useState<IdsState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [rotateProvider, setRotateProvider] = useState<'openai' | 'anthropic'>('openai');
  const [rotateKey, setRotateKey] = useState('');
  const [idsSeverity, setIdsSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('high');
  const [idsAction, setIdsAction] = useState<'alert' | 'block-tenant' | 'disable-provider'>('alert');
  const [idsMessage, setIdsMessage] = useState('Suspicious API spike detected by operator');
  const [queueFilter, setQueueFilter] = useState<'all' | 'queued' | 'sending' | 'retry' | 'sent' | 'failed'>('failed');
  const [queueData, setQueueData] = useState<SecurityQueueResponse | null>(null);
  const [queueLoading, setQueueLoading] = useState(false);

  const providerChart = useMemo<ChartPoint[]>(() => {
    return (analytics?.provider_graph || []).map((provider) => ({
      label: `${provider.provider} (${provider.status})`,
      value: provider.calls,
      accent:
        provider.color === 'red'
          ? 'linear-gradient(90deg, #ef4444, #f97316)'
          : 'linear-gradient(90deg, #10b981, #22c55e)',
      note: `ROI ${provider.avg_roi.toFixed(3)}`,
    }));
  }, [analytics]);

  const roiTimeline = useMemo<ChartPoint[]>(() => {
    return (analytics?.timeline || []).slice(-12).map((item) => ({
      label: formatTimeLabel(item.ts),
      value: item.roi,
    }));
  }, [analytics]);

  const latencyTimeline = useMemo<ChartPoint[]>(() => {
    return (analytics?.timeline || []).slice(-12).map((item) => ({
      label: formatTimeLabel(item.ts),
      value: item.latency_ms,
    }));
  }, [analytics]);

  const alertSeverityChart = useMemo<ChartPoint[]>(() => {
    const counts = new Map<string, number>();
    for (const alert of analytics?.alerts || []) {
      counts.set(alert.severity, (counts.get(alert.severity) || 0) + 1);
    }
    return Array.from(counts.entries()).map(([label, value]) => ({
      label,
      value,
      accent: accentForAlertSeverity(label),
    }));
  }, [analytics]);

  const idsSourceChart = useMemo<ChartPoint[]>(() => {
    return Object.entries(idsState?.by_source || {}).map(([label, value]) => ({ label, value }));
  }, [idsState]);

  const idsSeverityChart = useMemo<ChartPoint[]>(() => {
    return Object.entries(idsState?.by_severity || {}).map(([label, value]) => ({
      label,
      value,
      accent: accentForIdsSeverity(label),
    }));
  }, [idsState]);

  const deliveryChart = useMemo<ChartPoint[]>(() => {
    return Object.entries(idsState?.security_email_delivery || {}).map(([label, value]) => ({
      label,
      value,
      accent: accentForDelivery(label),
    }));
  }, [idsState]);

  async function loadAdminQueue(cursorBeforeId = 0) {
    setQueueLoading(true);
    try {
      setQueueData(await loadAdminQueueState(tenantId, superAdminKey, queueFilter, cursorBeforeId));
    } catch (e) {
      setError((e as Error).message || 'Failed to load security email queue');
    } finally {
      setQueueLoading(false);
    }
  }

  async function requeueItem(id: number) {
    setError('');
    try {
      assertAdminKey(superAdminKey, 'Super admin key is required for requeue actions.');
      await postRequeue(tenantId, superAdminKey.trim(), id);
      await loadAll();
    } catch (e) {
      setError((e as Error).message || 'Failed to requeue item');
    }
  }

  async function loadAll() {
    setLoading(true);
    setError('');
    try {
      const nextState = await loadAllState(tenantId, superAdminKey, queueFilter);
      setAnalytics(nextState.analytics);
      setIdsState(nextState.idsState);
      setQueueData(nextState.queueData);
    } catch (e) {
      setError((e as Error).message || 'Failed to load AI security telemetry');
    } finally {
      setLoading(false);
    }
  }

  async function rotateProviderKey() {
    setError('');
    try {
      assertAdminKey(superAdminKey, 'Super admin key is required for provider key rotation.');
      if (!rotateKey.trim()) throw new Error('New provider key is required.');
      const resp = await fetch(`${PROXY_BASE_URL}/ai/security/admin/provider-keys/rotate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-Id': tenantId,
          'X-Super-Admin-Key': superAdminKey.trim(),
        },
        body: JSON.stringify({ provider: rotateProvider, api_key: rotateKey, label: `${rotateProvider}-rotated-ui` }),
      });
      const data = (await resp.json()) as JsonObject;
      const detail = typeof data.detail === 'string' ? data.detail : 'Failed to rotate provider key';
      if (!resp.ok) throw new Error(detail);
      setRotateKey('');
      await loadAll();
    } catch (e) {
      setError((e as Error).message || 'Rotation failed');
    }
  }

  async function ingestIdsevent() {
    setError('');
    try {
      assertAdminKey(superAdminKey, 'Super admin key is required for IDS ingestion.');
      const resp = await fetch(`${PROXY_BASE_URL}/ai/security/admin/ids/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-Id': tenantId,
          'X-Super-Admin-Key': superAdminKey.trim(),
        },
        body: JSON.stringify({
          source: 'manual',
          severity: idsSeverity,
          rule_id: 'manual-operator-rule',
          message: idsMessage,
          tenant_id: tenantId,
          provider: rotateProvider,
          action: idsAction,
        }),
      });
      const data = (await resp.json()) as JsonObject;
      const detail = typeof data.detail === 'string' ? data.detail : 'Failed to ingest IDS event';
      if (!resp.ok) throw new Error(detail);
      await loadAll();
    } catch (e) {
      setError((e as Error).message || 'IDS event ingestion failed');
    }
  }

  async function submitAppeal() {
    setError('');
    try {
      await apiPost(
        '/ai/security/appeals',
        { reason: 'Operator test appeal for blocked tenant verification.' },
        tenantId
      );
      await loadAll();
    } catch (e) {
      setError((e as Error).message || 'Appeal submission failed');
    }
  }

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Page>
      <PageHeader
        title="AI Security Center"
        subtitle="Live ROI, latency, provider containment, IDS telemetry, and security-alert delivery in one operator surface."
        actions={
          <>
            <Button onClick={() => void loadAll()} disabled={loading}>
              {loading ? 'Refreshing…' : 'Refresh Telemetry'}
            </Button>
            <Button variant="primary" onClick={() => void submitAppeal()}>
              Submit Appeal
            </Button>
          </>
        }
      />

      <Card>
        <CardTitle sub="Operator scope — admin charts and actions require the super-admin key.">Control Plane</CardTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 12, marginTop: 14 }}>
          <Field label="Tenant ID" value={tenantId} onChange={(e) => setTenantId(e.target.value)} />
          <Field
            label="Super Admin Key"
            type="password"
            value={superAdminKey}
            onChange={(e) => setSuperAdminKey(e.target.value)}
            placeholder="Required for admin charts and actions"
          />
        </div>
      </Card>

      {error ? (
        <Card>
          <Badge tone="danger">{error}</Badge>
        </Card>
      ) : null}

      {analytics ? (
        <>
          <StatGrid>
            <Stat label="Total Calls" value={analytics.kpi.total_calls} />
            <Stat label="Success Rate" value={`${Math.round(analytics.kpi.success_rate * 100)}%`} />
            <Stat label="Avg ROI" value={analytics.kpi.avg_roi.toFixed(3)} />
            <Stat label="Avg Latency" value={`${analytics.kpi.avg_latency_ms.toFixed(1)} ms`} />
            <Stat label="Cost" value={`$${analytics.kpi.total_estimated_cost.toFixed(4)}`} />
            <Stat label="Value" value={`$${analytics.kpi.total_estimated_value.toFixed(4)}`} />
            <Stat
              label="Tenant Block"
              value={<Badge tone={analytics.kpi.is_blocked ? 'danger' : 'success'}>{analytics.kpi.is_blocked ? 'Blocked' : 'Healthy'}</Badge>}
            />
          </StatGrid>

          <ChartCard
            title="Provider Call Volume"
            subtitle="Request share by provider with average ROI attached to each bar."
          >
            <BarChart data={providerChart} emptyLabel="No provider activity in the selected window." />
          </ChartCard>

          <ChartCard title="ROI Trend" subtitle="Last 12 AI gateway events for the selected tenant.">
            <LineChart
              data={roiTimeline}
              emptyLabel="No ROI points available yet."
              stroke="#22c55e"
              formatValue={(value) => value.toFixed(3)}
            />
          </ChartCard>

          <ChartCard title="Latency Trend" subtitle="End-to-end latency captured from the secured AI gateway path.">
            <LineChart
              data={latencyTimeline}
              emptyLabel="No latency points available yet."
              stroke="#0ea5e9"
              formatValue={(value) => `${value.toFixed(0)} ms`}
            />
          </ChartCard>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: 'var(--nx-gap)' }}>
            <Card>
              <CardTitle>Rotate Provider Key</CardTitle>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
                <select value={rotateProvider} onChange={(e) => setRotateProvider(e.target.value as 'openai' | 'anthropic')} style={selectStyle} aria-label="Provider">
                  <option value="openai">openai</option>
                  <option value="anthropic">anthropic</option>
                </select>
                <Field type="password" value={rotateKey} onChange={(e) => setRotateKey(e.target.value)} placeholder="New provider API key" />
                <Button variant="primary" onClick={() => void rotateProviderKey()}>
                  Rotate Key
                </Button>
              </div>
            </Card>
            <Card>
              <CardTitle>Inject IDS/IPS Event</CardTitle>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
                <select value={idsSeverity} onChange={(e) => setIdsSeverity(e.target.value as 'low' | 'medium' | 'high' | 'critical')} style={selectStyle} aria-label="Severity">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
                <select value={idsAction} onChange={(e) => setIdsAction(e.target.value as 'alert' | 'block-tenant' | 'disable-provider')} style={selectStyle} aria-label="Action">
                  <option value="alert">alert</option>
                  <option value="block-tenant">block-tenant</option>
                  <option value="disable-provider">disable-provider</option>
                </select>
                <textarea
                  value={idsMessage}
                  onChange={(e) => setIdsMessage(e.target.value)}
                  rows={3}
                  aria-label="IDS message"
                  style={{ ...selectStyle, height: 'auto', padding: '10px 12px', resize: 'vertical' }}
                />
                <Button variant="primary" onClick={() => void ingestIdsevent()}>
                  Submit IDS Event
                </Button>
              </div>
            </Card>
          </div>

          <ChartCard
            title="Alert Severity Mix"
            subtitle="Distribution of recorded AI security alerts in the current analytics window."
          >
            <BarChart data={alertSeverityChart} emptyLabel="No security alerts in the selected window." />
          </ChartCard>

          <ChartCard title="Recent Security Alerts" subtitle="Latest alert records as emitted by the guardrail engine.">
            <div className="queue-list">
              {analytics.alerts.length === 0 ? (
                <p className="muted">No alerts in selected window.</p>
              ) : (
                analytics.alerts
                  .slice()
                  .reverse()
                  .map((alert) => (
                    <div key={alert.id} className="queue-row">
                      <div className="queue-head">
                        <span>
                          {alert.severity.toUpperCase()} • {alert.title}
                        </span>
                        <strong>{new Date(alert.created_at).toLocaleString()}</strong>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </ChartCard>

          {idsState ? (
            <>
              <ChartCard
                title="IDS Event Sources"
                subtitle="Traffic seen by the IDS/IPS integrations during the selected admin window."
              >
                <BarChart data={idsSourceChart} emptyLabel="No IDS source data available." />
              </ChartCard>

              <ChartCard
                title="IDS Severity Distribution"
                subtitle="Operator and relay-fed events grouped by severity."
              >
                <BarChart data={idsSeverityChart} emptyLabel="No IDS severity data available." />
              </ChartCard>

              <ChartCard
                title="Security Alert Email Delivery"
                subtitle="Background worker status for platform-security alert notifications."
              >
                <BarChart data={deliveryChart} emptyLabel="No security alert deliveries recorded yet." />
              </ChartCard>

              <ChartCard
                title="Admin Queue Browser"
                subtitle="Inspect failed/queued deliveries and requeue failed alerts with audit metadata."
              >
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
                  <select
                    value={queueFilter}
                    onChange={(e) =>
                      setQueueFilter(e.target.value as 'all' | 'queued' | 'sending' | 'retry' | 'sent' | 'failed')
                    }
                    aria-label="Queue filter"
                    style={{ ...selectStyle, width: 'auto' }}
                  >
                    <option value="failed">failed</option>
                    <option value="queued">queued</option>
                    <option value="retry">retry</option>
                    <option value="sending">sending</option>
                    <option value="sent">sent</option>
                    <option value="all">all</option>
                  </select>
                  <Button onClick={() => void loadAdminQueue(0)} disabled={queueLoading}>
                    {queueLoading ? 'Loading…' : 'Load Queue'}
                  </Button>
                </div>

                {!queueData || queueData.items.length === 0 ? (
                  <p className="muted">No queue entries for the selected filter.</p>
                ) : (
                  <div className="queue-list">
                    {queueData.items.map((item) => (
                      <div key={item.id} className="queue-row">
                        <div className="queue-head">
                          <span>
                            #{item.id} • {item.status.toUpperCase()} • {item.provider}
                          </span>
                          <strong>{item.to}</strong>
                        </div>
                        <p className="muted" style={{ marginTop: 6 }}>
                          {item.subject}
                        </p>
                        <p className="muted" style={{ marginTop: 6 }}>
                          Attempts: {item.attempts} • {item.delivery_detail || 'No delivery detail'}
                        </p>
                        {item.requeued_at ? (
                          <p className="muted" style={{ marginTop: 6 }}>
                            Requeued: {new Date(item.requeued_at).toLocaleString()} • By:{' '}
                            {item.requeued_by || 'unknown'} • Source: {item.requeued_source_ip || 'unknown'}
                          </p>
                        ) : null}
                        {item.status === 'failed' ? (
                          <div style={{ marginTop: 8 }}>
                            <Button onClick={() => void requeueItem(item.id)}>Requeue Failed Item</Button>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}

                {queueData ? (
                  <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
                    <Button
                      onClick={() => void loadAdminQueue(queueData.next_cursor_before_id || 0)}
                      disabled={!queueData.has_more || queueLoading}
                    >
                      Load Older
                    </Button>
                    <Button onClick={() => void loadAdminQueue(0)} disabled={queueLoading}>
                      Back To Latest
                    </Button>
                    <p className="muted" style={{ margin: 0, alignSelf: 'center' }}>
                      Source: {queueData.queue_source} • Count: {queueData.count}
                    </p>
                  </div>
                ) : null}
              </ChartCard>
            </>
          ) : null}
        </>
      ) : null}
    </Page>
  );
}
