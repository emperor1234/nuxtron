'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  apiDelete,
  apiGet,
  apiPost,
  DEFAULT_TENANT_ID,
  setSuperAdminKeySession,
  STORAGE_SUPER_ADMIN_KEY,
} from '@/app/lib/api-client';
import { Page, PageHeader, Card, CardTitle, Button, Field } from '../../_ui/kit';

type SiemPayload = {
  total_logs: number;
  security_events: number;
  critical_alerts: number;
  retention_days: number;
  tenant_isolation: boolean;
  sources: Record<string, number>;
};

type FinancePayload = {
  monthly_revenue_estimate: number;
  monthly_payout_estimate: number;
  profit_estimate: number;
  orders: number;
  wallet_transactions: number;
  hmrc_quickbooks_xero_ready: boolean;
};

type AccountsPayload = {
  profiles: number;
  mfa_ready: boolean;
  rbac_ready: boolean;
  abac_ready: boolean;
};

type ModuleItem = {
  id: string;
  name: string;
  ready: boolean;
  count: number;
  path: string;
};

type SubscriptionPayload = {
  active_plan: string;
  available_plans: string[];
  totals: Record<string, number>;
  upgrade_assist_copy: string;
};

type UpdatesPayload = {
  new_available: number;
  in_progress: number;
  pending: number;
  installed_up_to_date: boolean;
};

type AccountingPayload = {
  integrations_count: number;
  providers_connected: string[];
  exports_count: number;
  recent_exports: Array<Record<string, unknown>>;
  module_settings_count: number;
};

type DashboardPayload = {
  status: string;
  tenant_id: string;
  generated_at: string;
  siem: SiemPayload;
  finance: FinancePayload;
  accounts: AccountsPayload;
  modules: ModuleItem[];
  subscription: SubscriptionPayload;
  updates: UpdatesPayload;
  accounting: AccountingPayload;
};

type IntegrationRecord = {
  id: number;
  provider: string;
  status: string;
  account_name?: string;
  updated_at?: string;
};

type ExportRecord = {
  id: number;
  provider: string;
  export_type: string;
  period_label: string;
  status: string;
  submitted_at?: string;
  detail?: string;
};

type AuditItem = {
  id: number;
  action: string;
  detail?: Record<string, unknown>;
  recorded_at?: string;
};

const PAGE_LINKS: Record<string, string> = {
  crm: '/account/profile',
  security: '/ai-security',
  account_balance: '/account/wallet',
  profit_loss: '/platform/backend',
  orders: '/account/orders',
  wallet_credits: '/account/wallet',
  disputes: '/disputes',
  messages: '/studio',
  affiliate: '/affiliate',
  notifications: '/studio',
  files_content: '/studio',
  marketing_tools: '/playbooks',
  module_settings: '/platform',
};

function ratio(value: number, max: number): string {
  if (max <= 0) return '0%';
  const normalized = Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  return `${normalized}%`;
}

export default function BackendAdminDashboardPage() {
  // NOSONAR
  // NOSONAR
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [keyInput, setKeyInput] = useState('');
  const [integrationProvider, setIntegrationProvider] = useState('quickbooks');
  const [integrationClientId, setIntegrationClientId] = useState('nuxtron-client');
  const [integrationAccountName, setIntegrationAccountName] = useState('Finance Workspace');
  const [exportProvider, setExportProvider] = useState('hmrc');
  const [exportType, setExportType] = useState('vat_return');
  const [exportPeriod, setExportPeriod] = useState('2026-Q2');
  const [moduleKey, setModuleKey] = useState('marketing_tools');
  const [moduleEnabled, setModuleEnabled] = useState(true);
  const [moduleValue, setModuleValue] = useState('priority=normal');
  const [actionMessage, setActionMessage] = useState('');
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationRecord[]>([]);
  const [exportsList, setExportsList] = useState<ExportRecord[]>([]);
  const [auditItems, setAuditItems] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  async function fetchOperationalPanels(currentTenantId: string) {
    const [integrationData, exportData, auditData] = await Promise.all([
      apiGet('/ops/platform/super-admin/accounting/integrations', currentTenantId),
      apiGet('/ops/platform/super-admin/accounting/exports', currentTenantId),
      apiGet('/ops/platform/super-admin/audit-log?limit=20', currentTenantId),
    ]);

    return {
      integrations: (integrationData.integrations as IntegrationRecord[] | undefined) || [],
      exportsList: (exportData.exports as ExportRecord[] | undefined) || [],
      auditItems: (auditData.items as AuditItem[] | undefined) || [],
    };
  }

  async function loadDashboard(showLoader: boolean) {
    const currentTenantId = tenantId;
    if (showLoader) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError('');

    try {
      const [data, panels] = await Promise.all([
        apiGet('/ops/platform/super-admin/dashboard', currentTenantId),
        fetchOperationalPanels(currentTenantId),
      ]);

      setPayload(data as unknown as DashboardPayload);
      setIntegrations(panels.integrations);
      setExportsList(panels.exportsList);
      setAuditItems(panels.auditItems);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Unable to load super admin backend dashboard.');
      setPayload(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    if (globalThis.window) {
      const current = globalThis.sessionStorage?.getItem(STORAGE_SUPER_ADMIN_KEY) || '';
      if (current) setKeyInput(current);
    }
    void loadDashboard(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const topSources = useMemo(() => {
    const entries = Object.entries(payload?.siem.sources || {}).sort((a, b) => b[1] - a[1]);
    return entries.slice(0, 6);
  }, [payload]);

  const maxSource = useMemo(() => {
    if (!topSources.length) return 1;
    return Math.max(1, ...topSources.map(([, value]) => value));
  }, [topSources]);

  async function refreshOperationalPanels() {
    const panels = await fetchOperationalPanels(tenantId);
    setIntegrations(panels.integrations);
    setExportsList(panels.exportsList);
    setAuditItems(panels.auditItems);
  }

  async function connectAccountingIntegration() {
    setActionMessage('');
    setError('');
    try {
      await apiPost(
        '/ops/platform/super-admin/accounting/integrations/connect',
        {
          provider: integrationProvider,
          client_id: integrationClientId,
          account_name: integrationAccountName,
        },
        tenantId
      );
      setActionMessage(`Connected ${integrationProvider} integration.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to connect accounting integration.');
    }
  }

  async function submitAccountingExport() {
    setActionMessage('');
    setError('');
    try {
      await apiPost(
        '/ops/platform/super-admin/accounting/exports',
        {
          provider: exportProvider,
          export_type: exportType,
          period_label: exportPeriod,
        },
        tenantId
      );
      setActionMessage(`Submitted ${exportType} export to ${exportProvider}.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to submit accounting export.');
    }
  }

  async function saveModuleSetting() {
    setActionMessage('');
    setError('');
    try {
      await apiPost(
        '/ops/platform/super-admin/module-settings',
        {
          key: moduleKey,
          enabled: moduleEnabled,
          value: moduleValue,
        },
        tenantId
      );
      setActionMessage(`Updated module setting: ${moduleKey}.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to update module setting.');
    }
  }

  async function disconnectIntegration(provider: string) {
    setActionMessage('');
    setError('');
    try {
      await apiPost('/ops/platform/super-admin/accounting/integrations/disconnect', { provider }, tenantId);
      setActionMessage(`Disconnected ${provider} integration.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to disconnect integration.');
    }
  }

  async function deleteIntegration(provider: string) {
    setActionMessage('');
    setError('');
    try {
      await apiDelete(`/ops/platform/super-admin/accounting/integrations/${provider}`, tenantId);
      setActionMessage(`Deleted ${provider} integration.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to delete integration.');
    }
  }

  async function retryExport(exportId: number) {
    setActionMessage('');
    setError('');
    try {
      await apiPost(`/ops/platform/super-admin/accounting/exports/${exportId}/retry`, {}, tenantId);
      setActionMessage(`Retried export #${exportId}.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to retry export.');
    }
  }

  async function cancelExport(exportId: number) {
    setActionMessage('');
    setError('');
    try {
      await apiPost(`/ops/platform/super-admin/accounting/exports/${exportId}/cancel`, {}, tenantId);
      setActionMessage(`Cancelled export #${exportId}.`);
      await loadDashboard(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to cancel export.');
    }
  }

  return (
    <Page>
      <PageHeader
        title="Super Admin Backend"
        subtitle="Backend command center for SIEM, subscriptions, wallet credits, disputes, inbox, files/content, marketing tooling, and module governance."
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setSuperAdminKeySession(keyInput);
              void loadDashboard(false);
            }}
          >
            Save Key & Refresh
          </Button>
        }
      />

      <Card>
        <CardTitle sub="Operator scope — actions require a valid super-admin key.">Control Plane</CardTitle>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginTop: 14 }}>
          <Field label="Tenant ID" value={tenantId} onChange={(event) => setTenantId(event.target.value)} placeholder="Tenant ID" style={{ minWidth: 210 }} />
          <Field
            label="Super admin key"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
            placeholder="Super admin key"
            type="password"
            style={{ minWidth: 250 }}
          />
          <Button onClick={() => void loadDashboard(false)} disabled={refreshing || loading}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>
      </Card>

      {loading ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3>Loading backend dashboard...</h3>
        </section>
      ) : null}

      {error ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3>Access denied or unavailable</h3>
          <p className="muted">{error}</p>
          <p className="muted">Set a valid super admin key and make sure your source IP is allowlisted.</p>
        </section>
      ) : null}

      {actionMessage ? (
        <section className="card" style={{ marginTop: 20 }}>
          <p className="muted">{actionMessage}</p>
        </section>
      ) : null}

      {!loading && payload ? (
        <>
          <section className="grid dashboard-kpis" style={{ marginTop: 20 }}>
            <article className="card kpi-card">
              <p className="kpi-label">Tenant</p>
              <h3>{payload.tenant_id}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">SIEM Total Logs</p>
              <h3>{payload.siem.total_logs}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Critical Alerts</p>
              <h3>{payload.siem.critical_alerts}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Monthly Profit Estimate</p>
              <h3>£{payload.finance.profit_estimate.toLocaleString()}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Active Plan</p>
              <h3>{payload.subscription.active_plan.toUpperCase()}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Updated At</p>
              <h3>{new Date(payload.generated_at).toLocaleString()}</h3>
            </article>
          </section>

          <section
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 320px), 1fr))', gap: '1rem', marginTop: 20 }}
          >
            <article className="card">
              <h3>SIEM Log Sources</h3>
              <p className="muted">Custom log collection, normalization, alerting and retention overview.</p>
              <div className="queue-list">
                {topSources.map(([name, value]) => (
                  <div key={name} className="queue-row">
                    <div className="queue-head">
                      <span>{name.replaceAll('_', ' ')}</span>
                      <strong>{value}</strong>
                    </div>
                    <div className="queue-track">
                      <div className="queue-fill" style={{ width: ratio(value, maxSource) }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="muted" style={{ marginTop: '0.75rem' }}>
                Retention: {payload.siem.retention_days} days | Tenant isolation:{' '}
                {payload.siem.tenant_isolation ? 'Enabled' : 'Disabled'}
              </p>
            </article>

            <article className="card">
              <h3>Finance and Account Balance</h3>
              <ul className="status-list">
                <li>
                  <span>Revenue estimate</span>
                  <strong>£{payload.finance.monthly_revenue_estimate.toLocaleString()}</strong>
                </li>
                <li>
                  <span>Payout estimate</span>
                  <strong>£{payload.finance.monthly_payout_estimate.toLocaleString()}</strong>
                </li>
                <li>
                  <span>Profit estimate</span>
                  <strong>£{payload.finance.profit_estimate.toLocaleString()}</strong>
                </li>
                <li>
                  <span>Orders</span>
                  <strong>{payload.finance.orders}</strong>
                </li>
                <li>
                  <span>Wallet transactions</span>
                  <strong>{payload.finance.wallet_transactions}</strong>
                </li>
                <li>
                  <span>HMRC-ready exports</span>
                  <strong>{payload.finance.hmrc_quickbooks_xero_ready ? 'Ready' : 'Pending'}</strong>
                </li>
              </ul>
            </article>

            <article className="card">
              <h3>Identity and Security</h3>
              <ul className="status-list">
                <li>
                  <span>Profiles</span>
                  <strong>{payload.accounts.profiles}</strong>
                </li>
                <li>
                  <span>MFA</span>
                  <strong>{payload.accounts.mfa_ready ? 'Ready' : 'Not ready'}</strong>
                </li>
                <li>
                  <span>RBAC</span>
                  <strong>{payload.accounts.rbac_ready ? 'Ready' : 'Not ready'}</strong>
                </li>
                <li>
                  <span>ABAC</span>
                  <strong>{payload.accounts.abac_ready ? 'Ready' : 'Not ready'}</strong>
                </li>
              </ul>
              <a href="/account/settings" className="cta-link" style={{ marginTop: 12, display: 'inline-flex' }}>
                Open Account Settings
              </a>
            </article>
          </section>

          <section className="card" style={{ marginTop: 20 }}>
            <h3>Modules and Operations</h3>
            <p className="muted">
              CRM analytics, security, wallet credits, disputes, inbox, affiliate, marketing, notifications, and
              files/content.
            </p>
            <div
              className="grid"
              style={{
                gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 230px), 1fr))',
                gap: '0.75rem',
                marginTop: '0.75rem',
              }}
            >
              {payload.modules.map((moduleItem) => {
                const href = PAGE_LINKS[moduleItem.id] || '/platform';
                return (
                  <a key={moduleItem.id} href={href} className="card" style={{ textDecoration: 'none' }}>
                    <p className="kpi-label">{moduleItem.ready ? 'Ready' : 'Needs setup'}</p>
                    <h3 style={{ fontSize: '16px' }}>{moduleItem.name}</h3>
                    <p className="muted">Count: {moduleItem.count}</p>
                  </a>
                );
              })}
            </div>
          </section>

          <section
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 320px), 1fr))', gap: '1rem', marginTop: 20 }}
          >
            <article className="card">
              <h3>HMRC / QuickBooks / Xero Connectors</h3>
              <p className="muted">
                Connected providers: {(payload.accounting.providers_connected || []).join(', ') || 'none'}
              </p>
              <div className="auth-grid" style={{ marginTop: '0.75rem' }}>
                <label>
                  <span>Provider</span>
                  <select value={integrationProvider} onChange={(event) => setIntegrationProvider(event.target.value)}>
                    <option value="quickbooks">QuickBooks</option>
                    <option value="xero">Xero</option>
                    <option value="hmrc">HMRC</option>
                  </select>
                </label>
                <label>
                  <span>Client Id</span>
                  <input value={integrationClientId} onChange={(event) => setIntegrationClientId(event.target.value)} />
                </label>
                <label>
                  <span>Account Name</span>
                  <input
                    value={integrationAccountName}
                    onChange={(event) => setIntegrationAccountName(event.target.value)}
                  />
                </label>
                <button type="button" className="cta-link" onClick={() => void connectAccountingIntegration()}>
                  Connect Provider
                </button>
              </div>
            </article>

            <article className="card">
              <h3>Accounting Export And Filing</h3>
              <p className="muted">One-click ready submissions for VAT return, P&L, ledger, and invoice batches.</p>
              <div className="auth-grid" style={{ marginTop: '0.75rem' }}>
                <label>
                  <span>Export Provider</span>
                  <select value={exportProvider} onChange={(event) => setExportProvider(event.target.value)}>
                    <option value="hmrc">HMRC</option>
                    <option value="quickbooks">QuickBooks</option>
                    <option value="xero">Xero</option>
                  </select>
                </label>
                <label>
                  <span>Export Type</span>
                  <select value={exportType} onChange={(event) => setExportType(event.target.value)}>
                    <option value="vat_return">VAT Return</option>
                    <option value="pnl">Profit And Loss</option>
                    <option value="ledger">Ledger</option>
                    <option value="invoice_batch">Invoice Batch</option>
                  </select>
                </label>
                <label>
                  <span>Period</span>
                  <input value={exportPeriod} onChange={(event) => setExportPeriod(event.target.value)} />
                </label>
                <button type="button" className="cta-link" onClick={() => void submitAccountingExport()}>
                  Submit Export
                </button>
              </div>
              <p className="muted" style={{ marginTop: '0.75rem' }}>
                Export jobs: {payload.accounting.exports_count}
              </p>
            </article>

            <article className="card">
              <h3>Module Settings Control</h3>
              <p className="muted">Manage feature/module behavior centrally for super-admin operations.</p>
              <div className="auth-grid" style={{ marginTop: '0.75rem' }}>
                <label>
                  <span>Setting Key</span>
                  <input value={moduleKey} onChange={(event) => setModuleKey(event.target.value)} />
                </label>
                <label>
                  <span>Setting Value</span>
                  <input value={moduleValue} onChange={(event) => setModuleValue(event.target.value)} />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={moduleEnabled}
                    onChange={(event) => setModuleEnabled(event.target.checked)}
                  />{' '}
                  Enabled
                </label>
                <button type="button" className="cta-link" onClick={() => void saveModuleSetting()}>
                  Save Module Setting
                </button>
              </div>
              <p className="muted" style={{ marginTop: '0.75rem' }}>
                Stored settings: {payload.accounting.module_settings_count}
              </p>
            </article>
          </section>

          <section
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 320px), 1fr))', gap: '1rem', marginTop: 20 }}
          >
            <article className="card">
              <h3>Subscription Plans And Upgrade Assistant</h3>
              <p className="muted">{payload.subscription.upgrade_assist_copy}</p>
              <div
                className="grid"
                style={{
                  gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 90px), 1fr))',
                  gap: '0.5rem',
                  marginTop: '0.75rem',
                }}
              >
                {payload.subscription.available_plans.map((plan) => (
                  <div key={plan} className="card" style={{ padding: '0.6rem' }}>
                    <strong>{plan.toUpperCase()}</strong>
                    <div className="muted">{payload.subscription.totals[plan] ?? 0} accounts</div>
                  </div>
                ))}
              </div>
              <a href="/pricing" className="cta-link" style={{ marginTop: 12, display: 'inline-flex' }}>
                Manage plan and upgrades
              </a>
            </article>

            <article className="card">
              <h3>Platform Updates Center</h3>
              <ul className="status-list">
                <li>
                  <span>New updates available</span>
                  <strong>{payload.updates.new_available}</strong>
                </li>
                <li>
                  <span>In process updates</span>
                  <strong>{payload.updates.in_progress}</strong>
                </li>
                <li>
                  <span>Pending updates</span>
                  <strong>{payload.updates.pending}</strong>
                </li>
                <li>
                  <span>Installed and up to date</span>
                  <strong>{payload.updates.installed_up_to_date ? 'Verified' : 'Needs review'}</strong>
                </li>
              </ul>
              <a href="/platform" className="cta-link" style={{ marginTop: 12, display: 'inline-flex' }}>
                Open module settings
              </a>
            </article>
          </section>

          <section
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%, 320px), 1fr))', gap: '1rem', marginTop: 20 }}
          >
            <article className="card">
              <h3>Connector Lifecycle</h3>
              <p className="muted">
                Disconnect or remove provider bindings when rotating integrations or decommissioning access.
              </p>
              <div className="queue-list" style={{ marginTop: '0.75rem' }}>
                {integrations.length ? (
                  integrations.map((integration) => (
                    <div
                      key={integration.id}
                      className="queue-row"
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.55rem' }}
                    >
                      <div className="queue-head">
                        <span>
                          {integration.provider.toUpperCase()} ({integration.status})
                        </span>
                        <strong>{integration.account_name || 'Unknown account'}</strong>
                      </div>
                      <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.45rem', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          className="cta-link"
                          onClick={() => void disconnectIntegration(integration.provider)}
                        >
                          Disconnect
                        </button>
                        <button
                          type="button"
                          className="cta-link"
                          onClick={() => void deleteIntegration(integration.provider)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="muted">No integrations found for this tenant.</p>
                )}
              </div>
            </article>

            <article className="card">
              <h3>Export Lifecycle</h3>
              <p className="muted">Retry failed or stale jobs, or cancel jobs before provider processing completes.</p>
              <div className="queue-list" style={{ marginTop: '0.75rem' }}>
                {exportsList.length ? (
                  exportsList.slice(0, 8).map((job) => (
                    <div
                      key={job.id}
                      className="queue-row"
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.55rem' }}
                    >
                      <div className="queue-head">
                        <span>
                          #{job.id} {job.provider.toUpperCase()} {job.export_type}
                        </span>
                        <strong>{job.status}</strong>
                      </div>
                      <p className="muted" style={{ marginTop: '0.35rem' }}>
                        {job.period_label} | {job.detail || 'No detail'}
                      </p>
                      <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.45rem', flexWrap: 'wrap' }}>
                        <button type="button" className="cta-link" onClick={() => void retryExport(job.id)}>
                          Retry
                        </button>
                        <button type="button" className="cta-link" onClick={() => void cancelExport(job.id)}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="muted">No export jobs found for this tenant.</p>
                )}
              </div>
            </article>

            <article className="card">
              <h3>Super Admin Audit Trail</h3>
              <p className="muted">Recent connector and export admin actions recorded for operations transparency.</p>
              <div className="queue-list" style={{ marginTop: '0.75rem' }}>
                {auditItems.length ? (
                  auditItems.map((item) => (
                    <div
                      key={item.id}
                      className="queue-row"
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.55rem' }}
                    >
                      <div className="queue-head">
                        <span>{item.action}</span>
                        <strong>{item.recorded_at ? new Date(item.recorded_at).toLocaleString() : '-'}</strong>
                      </div>
                      <p className="muted" style={{ marginTop: '0.35rem' }}>
                        {JSON.stringify(item.detail || {})}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="muted">No recent super-admin finance audit events.</p>
                )}
              </div>
            </article>
          </section>
        </>
      ) : null}
    </Page>
  );
}
