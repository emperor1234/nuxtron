'use client';

import { useEffect, useMemo, useState } from 'react';
import AnalyticsExecutiveBoard from '@/app/components/analytics-executive-board';
import { SecretInput } from '@/app/components/secret-input';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Provider = {
  id: number;
  name: string;
  status: string;
  revenue_usd: number;
  cost_usd: number;
  profit_usd: number;
  margin_pct: number;
  tokens_remaining: number;
  credits_remaining: number;
  recommended_sell_price_per_token_usd: number;
  recommended_sell_price_per_credit_usd: number;
};

type KpiPayload = {
  kpis: {
    providers_total: number;
    providers_active: number;
    providers_disabled: number;
    usage_events: number;
    revenue_total_usd: number;
    cost_total_usd: number;
    profit_total_usd: number;
    profit_margin_pct: number;
    critical_incidents: number;
  };
};

type AnalyticsPayload = {
  line_profit: number[];
  line_margin_pct: number[];
  bars_profit_by_provider: Array<{ label: string; value: number }>;
  avg_margin_pct: number;
  events_analyzed: number;
};

type EncryptionPosture = {
  encryption: {
    at_rest: { enabled: boolean; algorithm: string };
    in_transit: { enabled: boolean; requirements: string[] };
    in_use: { enabled: boolean; control_plane: string };
    in_memory: { enabled: boolean; controls: string[] };
    quantum_nist: {
      enabled: boolean;
      algorithm: string;
      provider: string;
      mode: string;
      detail: string;
    };
    vaults: {
      hashicorp: { enabled: boolean; backend: string; address?: string };
      supabase: { enabled: boolean; backend: string };
    };
  };
};

type Incident = {
  id: number;
  title: string;
  detail: string;
  severity: string;
  created_at: string;
};

type GovernanceSectionKey = 'kpi' | 'analytics' | 'providers' | 'posture' | 'incidents';
type GovernanceSectionStatus = 'idle' | 'loading' | 'ready' | 'error';

const GOVERNANCE_SECTIONS: Array<{ key: GovernanceSectionKey; label: string }> = [
  { key: 'kpi', label: 'KPI' },
  { key: 'analytics', label: 'Analytics' },
  { key: 'providers', label: 'Provider Economics' },
  { key: 'posture', label: 'Encryption Posture' },
  { key: 'incidents', label: 'Incidents' },
];

const INITIAL_SECTION_STATUS: Record<GovernanceSectionKey, GovernanceSectionStatus> = {
  kpi: 'idle',
  analytics: 'idle',
  providers: 'idle',
  posture: 'idle',
  incidents: 'idle',
};

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });

export default function ApiGovernancePage() {
  const tenantId = DEFAULT_TENANT_ID;
  const [kpi, setKpi] = useState<KpiPayload | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [posture, setPosture] = useState<EncryptionPosture | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [providerId, setProviderId] = useState('1');
  const [disableReason, setDisableReason] = useState('Manual emergency stop by root admin.');
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState('');
  const [loadWarning, setLoadWarning] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sectionStatus, setSectionStatus] =
    useState<Record<GovernanceSectionKey, GovernanceSectionStatus>>(INITIAL_SECTION_STATUS);

  // ── Add-provider form state ──────────────────────────────────────────────
  const [addForm, setAddForm] = useState({
    name: '',
    vendor: '',
    endpoint: '',
    model: 'default',
    billing_unit: 'token' as 'token' | 'credit',
    token: '', // handled by SecretInput — never logged
    cost_per_token_usd: '0',
    tokens_purchased: '100000',
    target_margin: '0.67',
  });
  const [addFormError, setAddFormError] = useState('');
  const [addFormSuccess, setAddFormSuccess] = useState('');
  const [addFormBusy, setAddFormBusy] = useState(false);

  const formatSectionStatus = (status: GovernanceSectionStatus) => {
    if (status === 'ready') return { label: 'Ready', color: '#10b981', border: '#10b981' };
    if (status === 'error') return { label: 'Unavailable', color: '#ef4444', border: '#ef4444' };
    if (status === 'loading') return { label: 'Loading', color: '#f59e0b', border: '#f59e0b' };
    return { label: 'Idle', color: 'var(--muted)', border: 'var(--line)' };
  };

  const setAllSections = (status: GovernanceSectionStatus) => {
    setSectionStatus({
      kpi: status,
      analytics: status,
      providers: status,
      posture: status,
      incidents: status,
    });
  };

  const refresh = async () => {
    setIsRefreshing(true);
    setAllSections('loading');

    const failedSections: string[] = [];
    const [kpiResult, analyticsResult, providersResult, postureResult, incidentsResult] = await Promise.allSettled([
      apiGet<KpiPayload>('/api-governance/kpi', tenantId),
      apiGet<AnalyticsPayload>('/api-governance/analytics', tenantId),
      apiGet<{ providers: Provider[] }>('/api-governance/third-party-profit', tenantId),
      apiGet<EncryptionPosture>('/api-governance/security/encryption-posture', tenantId),
      apiGet<{ incidents: Incident[] }>('/api-governance/incidents', tenantId),
    ] as const);

    if (kpiResult.status === 'fulfilled') {
      setKpi(kpiResult.value);
      setSectionStatus((prev) => ({ ...prev, kpi: 'ready' }));
    } else {
      failedSections.push('KPI');
      setSectionStatus((prev) => ({ ...prev, kpi: 'error' }));
    }

    if (analyticsResult.status === 'fulfilled') {
      setAnalytics(analyticsResult.value);
      setSectionStatus((prev) => ({ ...prev, analytics: 'ready' }));
    } else {
      failedSections.push('Analytics');
      setSectionStatus((prev) => ({ ...prev, analytics: 'error' }));
    }

    if (providersResult.status === 'fulfilled') {
      setProviders(providersResult.value.providers ?? []);
      setSectionStatus((prev) => ({ ...prev, providers: 'ready' }));
    } else {
      failedSections.push('Provider Economics');
      setSectionStatus((prev) => ({ ...prev, providers: 'error' }));
    }

    if (postureResult.status === 'fulfilled') {
      setPosture(postureResult.value);
      setSectionStatus((prev) => ({ ...prev, posture: 'ready' }));
    } else {
      failedSections.push('Encryption Posture');
      setSectionStatus((prev) => ({ ...prev, posture: 'error' }));
    }

    if (incidentsResult.status === 'fulfilled') {
      setIncidents(incidentsResult.value.incidents ?? []);
      setSectionStatus((prev) => ({ ...prev, incidents: 'ready' }));
    } else {
      failedSections.push('Incidents');
      setSectionStatus((prev) => ({ ...prev, incidents: 'error' }));
    }

    if (failedSections.length === 0) {
      setLoadWarning('');
      setIsRefreshing(false);
      return;
    }

    const failedSummary = failedSections.join(', ');
    if (failedSections.length === 5) {
      setError('Unable to load API Governance data right now. Verify the FastAPI service is running and retry.');
      setLoadWarning('');
      setIsRefreshing(false);
      return;
    }

    setError('');
    setLoadWarning(`Some sections are temporarily unavailable: ${failedSummary}.`);
    setIsRefreshing(false);
  };

  useEffect(() => {
    setError('');
    setStatusMessage('');
    setLoadWarning('');
    void refresh();
  }, []);

  const boardKpis = useMemo(() => {
    if (!kpi) return [];
    return [
      {
        label: 'Providers Active',
        value: `${kpi.kpis.providers_active}/${kpi.kpis.providers_total}`,
        trend: 'up' as const,
      },
      {
        label: 'Profit Margin',
        value: `${kpi.kpis.profit_margin_pct.toFixed(2)}%`,
        trend: kpi.kpis.profit_margin_pct >= 65 ? ('up' as const) : ('down' as const),
      },
      {
        label: 'Profit Total',
        value: currency.format(kpi.kpis.profit_total_usd),
        trend: kpi.kpis.profit_total_usd >= 0 ? ('up' as const) : ('down' as const),
      },
      {
        label: 'Critical Incidents',
        value: `${kpi.kpis.critical_incidents}`,
        trend: kpi.kpis.critical_incidents ? ('down' as const) : ('flat' as const),
      },
    ];
  }, [kpi]);

  const ring = useMemo(() => {
    if (!kpi) return [];
    return [
      { label: 'Revenue', value: Math.max(0, kpi.kpis.revenue_total_usd), color: '#16a34a' },
      { label: 'Cost', value: Math.max(0, kpi.kpis.cost_total_usd), color: '#ef4444' },
      { label: 'Profit', value: Math.max(0, kpi.kpis.profit_total_usd), color: '#6366f1' },
    ];
  }, [kpi]);

  const disableProvider = async () => {
    setError('');
    setStatusMessage('');
    try {
      await apiSend(
        `/api-governance/providers/${Number.parseInt(providerId, 10)}/disable`,
        'POST',
        { reason: disableReason },
        tenantId
      );
      setStatusMessage('Provider disabled and emergency notifications dispatched to admin, IRA, and SIEM.');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to disable provider.');
    }
  };

  const submitAddProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddFormError('');
    setAddFormSuccess('');
    if (!addForm.token || addForm.token.length < 8) {
      setAddFormError('API token must be at least 8 characters.');
      return;
    }
    setAddFormBusy(true);
    try {
      await apiSend(
        '/api-governance/providers',
        'POST',
        {
          name: addForm.name,
          vendor: addForm.vendor,
          endpoint: addForm.endpoint,
          model: addForm.model,
          billing_unit: addForm.billing_unit,
          token: addForm.token,
          cost_per_token_usd: Number(addForm.cost_per_token_usd),
          cost_per_credit_usd: 0,
          credits_purchased: 0,
          tokens_purchased: Number(addForm.tokens_purchased),
          target_margin: Number(addForm.target_margin),
        },
        tenantId
      );
      setAddFormSuccess('Provider added. Token encrypted at rest — plaintext never stored.');
      setAddForm((prev) => ({ ...prev, token: '', name: '' }));
      await refresh();
    } catch (err) {
      setAddFormError(err instanceof Error ? err.message : 'Failed to add provider.');
    } finally {
      setAddFormBusy(false);
    }
  };

  return (
    <main style={{ padding: 24, display: 'grid', gap: 18 }}>
      <header>
        <h1 style={{ marginTop: 0 }}>API Governance And Third-Party Economics</h1>
        <p style={{ color: 'var(--muted)', maxWidth: 980 }}>
          Token-only API control plane with transparent encryption posture, third-party usage economics, dynamic pricing
          for 65-70% target margin, and automatic emergency escalation when profitability drops or credits are
          exhausted.
        </p>
      </header>

      {error ? (
        <div
          style={{
            border: '1px solid #ef4444',
            borderRadius: 10,
            padding: 12,
            color: '#ef4444',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 10,
            alignItems: 'center',
          }}
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={isRefreshing}
            style={{ opacity: isRefreshing ? 0.6 : 1 }}
          >
            {isRefreshing ? 'Retrying…' : 'Retry'}
          </button>
        </div>
      ) : null}
      {loadWarning ? (
        <div
          style={{
            border: '1px solid #f59e0b',
            borderRadius: 10,
            padding: 12,
            color: '#f59e0b',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 10,
            alignItems: 'center',
          }}
        >
          <span>{loadWarning}</span>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={isRefreshing}
            style={{ opacity: isRefreshing ? 0.6 : 1 }}
          >
            {isRefreshing ? 'Retrying…' : 'Retry'}
          </button>
        </div>
      ) : null}
      {statusMessage ? (
        <div style={{ border: '1px solid #10b981', borderRadius: 10, padding: 12, color: '#10b981' }}>
          {statusMessage}
        </div>
      ) : null}

      <section style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {GOVERNANCE_SECTIONS.map((section) => {
          const statusToken = formatSectionStatus(sectionStatus[section.key]);
          return (
            <div
              key={section.key}
              style={{
                border: `1px solid ${statusToken.border}`,
                color: statusToken.color,
                borderRadius: 999,
                padding: '4px 10px',
                fontSize: 12,
                display: 'inline-flex',
                gap: 6,
                alignItems: 'center',
              }}
            >
              <span>{section.label}</span>
              <strong>{statusToken.label}</strong>
            </div>
          );
        })}
      </section>

      <AnalyticsExecutiveBoard
        title="API Security And Profitability Command"
        subtitle="Deep KPI view for provider economics, token usage, and security incidents"
        kpis={boardKpis}
        bars={analytics?.bars_profit_by_provider ?? []}
        line={analytics?.line_profit?.length ? analytics.line_profit : [10, 22, 18, 29, 34, 41]}
        ring={ring}
      />

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 }}>
        <article style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 14 }}>
          <h2 style={{ marginTop: 0 }}>Encryption Posture</h2>
          <ul style={{ lineHeight: 1.7 }}>
            <li>
              At Rest: {posture?.encryption.at_rest.enabled ? 'enabled' : 'disabled'} (
              {posture?.encryption.at_rest.algorithm ?? 'n/a'})
            </li>
            <li>In Transit: {posture?.encryption.in_transit.enabled ? 'enabled' : 'disabled'}</li>
            <li>In Use: {posture?.encryption.in_use.enabled ? 'enabled' : 'disabled'}</li>
            <li>In Memory: {posture?.encryption.in_memory.enabled ? 'enabled' : 'disabled'}</li>
            <li>
              NIST PQC: {posture?.encryption.quantum_nist.enabled ? 'enabled' : 'fallback'} (
              {posture?.encryption.quantum_nist.algorithm ?? 'ML-KEM-768'})
            </li>
            <li>HashiCorp Vault: {posture?.encryption.vaults.hashicorp.enabled ? 'connected' : 'not connected'}</li>
            <li>Supabase Vault: {posture?.encryption.vaults.supabase.enabled ? 'connected' : 'not connected'}</li>
          </ul>
        </article>

        <article style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 14 }}>
          <h2 style={{ marginTop: 0 }}>Emergency Provider Control</h2>
          <label style={{ display: 'grid', gap: 6, marginBottom: 10 }}>
            <span>Provider ID</span>
            <input value={providerId} onChange={(e) => setProviderId(e.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 6, marginBottom: 10 }}>
            <span>Reason</span>
            <textarea value={disableReason} onChange={(e) => setDisableReason(e.target.value)} rows={3} />
          </label>
          <button onClick={() => void disableProvider()}>Disable Provider And Alert Root Admin</button>
          <p style={{ color: 'var(--muted)', marginBottom: 0 }}>
            This action opens SIEM case, writes IRA emergency event, and creates critical notification.
          </p>
        </article>
      </section>

      {/* ── Add Provider Form ─────────────────────────────────────────────── */}
      <section style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 14 }}>
        <h2 style={{ marginTop: 0 }}>Register Third-Party API Provider</h2>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 14, fontSize: 13 }}>
          API tokens are encrypted immediately on submission using AES-256-GCM transparent encryption. The plaintext
          token is never stored, logged, or echoed back. The field masks all typed and pasted characters.
        </p>
        {addFormError && (
          <div
            style={{
              border: '1px solid #ef4444',
              borderRadius: 8,
              padding: '8px 12px',
              marginBottom: 12,
              color: '#ef4444',
              fontSize: 13,
            }}
          >
            {addFormError}
          </div>
        )}
        {addFormSuccess && (
          <div
            style={{
              border: '1px solid #10b981',
              borderRadius: 8,
              padding: '8px 12px',
              marginBottom: 12,
              color: '#10b981',
              fontSize: 13,
            }}
          >
            {addFormSuccess}
          </div>
        )}
        <form
          onSubmit={(e) => void submitAddProvider(e)}
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 }}
        >
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Provider Name *</span>
            <input
              required
              minLength={2}
              value={addForm.name}
              onChange={(e) => setAddForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="OpenAI GPT-4 Turbo"
            />
          </label>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Vendor *</span>
            <input
              required
              minLength={2}
              value={addForm.vendor}
              onChange={(e) => setAddForm((p) => ({ ...p, vendor: e.target.value }))}
              placeholder="OpenAI"
            />
          </label>
          <label style={{ display: 'grid', gap: 5, gridColumn: '1 / -1' }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>API Endpoint *</span>
            <input
              required
              minLength={5}
              value={addForm.endpoint}
              onChange={(e) => setAddForm((p) => ({ ...p, endpoint: e.target.value }))}
              placeholder="https://api.openai.com/v1/chat/completions"
            />
          </label>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Model</span>
            <input
              value={addForm.model}
              onChange={(e) => setAddForm((p) => ({ ...p, model: e.target.value }))}
              placeholder="gpt-4-turbo"
            />
          </label>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Billing Unit</span>
            <select
              value={addForm.billing_unit}
              onChange={(e) => setAddForm((p) => ({ ...p, billing_unit: e.target.value as 'token' | 'credit' }))}
            >
              <option value="token">Token</option>
              <option value="credit">Credit</option>
            </select>
          </label>
          <div style={{ gridColumn: '1 / -1' }}>
            <SecretInput
              label="API Token / Secret Key *"
              value={addForm.token}
              onChange={(v: string) => setAddForm((p) => ({ ...p, token: v }))}
              required
              placeholder="Paste or type your API key — shown as bullets"
              hint="Your key is encrypted with AES-256-GCM before storage. It will never be shown again after saving."
              hasError={Boolean(addFormError && addForm.token.length < 8 && addForm.token.length > 0)}
              errorMessage="Token must be at least 8 characters."
              revealDurationMs={4000}
            />
          </div>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Cost per Token (USD)</span>
            <input
              type="number"
              min="0"
              step="0.000001"
              value={addForm.cost_per_token_usd}
              onChange={(e) => setAddForm((p) => ({ ...p, cost_per_token_usd: e.target.value }))}
            />
          </label>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Tokens Purchased</span>
            <input
              type="number"
              min="0"
              value={addForm.tokens_purchased}
              onChange={(e) => setAddForm((p) => ({ ...p, tokens_purchased: e.target.value }))}
            />
          </label>
          <label style={{ display: 'grid', gap: 5 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Target Margin (0.65–0.70)</span>
            <input
              type="number"
              min="0.65"
              max="0.70"
              step="0.01"
              value={addForm.target_margin}
              onChange={(e) => setAddForm((p) => ({ ...p, target_margin: e.target.value }))}
            />
          </label>
          <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 10, alignItems: 'center' }}>
            <button type="submit" disabled={addFormBusy} style={{ opacity: addFormBusy ? 0.6 : 1 }}>
              {addFormBusy ? 'Saving…' : 'Add Provider (Encrypt And Store)'}
            </button>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>
              Token will be encrypted immediately. Plaintext is never persisted or logged.
            </span>
          </div>
        </form>
      </section>

      <section style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 14 }}>
        <h2 style={{ marginTop: 0 }}>Third-Party API Profit And Usage Table</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th align="left">Provider</th>
                <th align="right">Revenue</th>
                <th align="right">Cost</th>
                <th align="right">Profit</th>
                <th align="right">Margin %</th>
                <th align="right">Tokens Left</th>
                <th align="right">Credits Left</th>
                <th align="left">Status</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.id}>
                  <td>{provider.name}</td>
                  <td align="right">{currency.format(provider.revenue_usd)}</td>
                  <td align="right">{currency.format(provider.cost_usd)}</td>
                  <td align="right">{currency.format(provider.profit_usd)}</td>
                  <td align="right">{provider.margin_pct.toFixed(2)}%</td>
                  <td align="right">{provider.tokens_remaining}</td>
                  <td align="right">{provider.credits_remaining.toFixed(2)}</td>
                  <td>{provider.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 14 }}>
        <h2 style={{ marginTop: 0 }}>Security Incident Stream</h2>
        {incidents.length === 0 ? <p style={{ color: 'var(--muted)' }}>No incidents recorded.</p> : null}
        <div style={{ display: 'grid', gap: 8 }}>
          {incidents
            .slice(-8)
            .reverse()
            .map((incident) => (
              <article key={incident.id} style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10 }}>
                <strong>{incident.title}</strong>
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>{incident.detail}</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  Severity: {incident.severity} | {new Date(incident.created_at).toLocaleString()}
                </div>
              </article>
            ))}
        </div>
      </section>
    </main>
  );
}
