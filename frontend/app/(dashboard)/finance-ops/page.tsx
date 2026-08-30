'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type FinanceHub = {
  status: string;
  tenant_id: string;
  connected_integrations: number;
  exports_count: number;
  generated_at: string;
  credits: {
    current_balance: number;
    added_total: number;
    used_total: number;
    usage_by_source: Record<string, number>;
  };
  roi: {
    window_calls: number;
    avg_roi: number;
    total_estimated_cost: number;
    total_estimated_value: number;
  };
  profit_loss: {
    monthly_revenue_estimate: number;
    monthly_payout_estimate: number;
    api_cost_estimate: number;
    profit_estimate: number;
    margin_percent: number;
  };
  accounting: {
    providers: {
      quickbooks: boolean;
      xero: boolean;
      hmrc: boolean;
    };
    integration_count: number;
    exports_count: number;
  };
  provider_breakdown: Array<{
    provider: string;
    calls: number;
    total_cost: number;
    total_value: number;
    avg_roi: number;
    disabled: boolean;
  }>;
  api_security: {
    total_requests: number;
    api_key_requests: number;
    bearer_jwt_requests: number;
    unique_ip_hashes: number;
    unique_ua_hashes: number;
    https_header_enforced: boolean;
    mtls_required: boolean;
    cors_wildcard: boolean;
    frontend_public_api_key_detected: boolean;
    risk_score: number;
    risk_level: string;
    suspicious_signals: Array<{
      code: string;
      severity: string;
      message: string;
      recommended_action: string;
    }>;
    top_paths: Array<{ path: string; count: number }>;
  };
  profit_guard: {
    healthy: boolean;
    requires_key_rotation: boolean;
    recommended_action: string;
    auto_disable_candidate_provider: string;
  };
};

type LedgerEntry = {
  id: number;
  amount: number;
  reason: string;
  source: string;
  created_at: string;
  running_balance: number;
};

type AccountingIntegration = {
  id: number;
  provider: string;
  provider_alias?: string | null;
  status: string;
  account_name: string;
  updated_at: string;
};

type AccountingExport = {
  id: number;
  provider: string;
  provider_alias?: string | null;
  export_type: string;
  period_label: string;
  status: string;
  submitted_at: string;
};

type StripeSandbox = { enabled: boolean; test_price_id: string };

type SecurityIntelligence = {
  api_security: FinanceHub['api_security'];
  provider_breakdown: FinanceHub['provider_breakdown'];
  commercial: {
    total_estimated_cost: number;
    total_estimated_value: number;
    estimated_margin: number;
  };
};

export default function FinanceOpsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [hub, setHub] = useState<FinanceHub | null>(null);
  const [securityIntelligence, setSecurityIntelligence] = useState<SecurityIntelligence | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [integrations, setIntegrations] = useState<AccountingIntegration[]>([]);
  const [exports, setExports] = useState<AccountingExport[]>([]);
  const [sandbox, setSandbox] = useState<StripeSandbox>({ enabled: true, test_price_id: '' });

  const [provider, setProvider] = useState<'xero' | 'quickbooks' | 'hmrc'>('xero');
  const [accountName, setAccountName] = useState('Finance Team');
  const [clientId, setClientId] = useState('client-xyz');
  const [exportType, setExportType] = useState<'pnl' | 'ledger' | 'invoice_batch' | 'vat_return' | 'balance_sheet'>(
    'pnl'
  );
  const [periodLabel, setPeriodLabel] = useState('2026-Q1');
  const [guardProvider, setGuardProvider] = useState<'openai' | 'anthropic' | 'google_vertex'>('openai');

  const [buyCredits, setBuyCredits] = useState('1000');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const [hubRes, ledgerRes, integrationsRes, exportsRes, sandboxRes] = await Promise.all([
        apiGet<FinanceHub>('/ops/finance/hub?usage_limit=600&ledger_limit=300', tenantId),
        apiGet<{ entries: LedgerEntry[] }>('/ops/finance/credits/ledger?limit=100', tenantId),
        apiGet<{ integrations: AccountingIntegration[] }>('/ops/finance/accounting/integrations', tenantId),
        apiGet<{ exports: AccountingExport[] }>('/ops/finance/accounting/exports?limit=20', tenantId),
        apiGet<{ sandbox: StripeSandbox }>('/ops/finance/stripe-sandbox', tenantId),
      ]);
      const intelligence = await apiGet<SecurityIntelligence>('/ops/finance/security/intelligence?limit=600', tenantId);
      setHub(hubRes);
      setSecurityIntelligence(intelligence);
      setLedger(ledgerRes.entries ?? []);
      setIntegrations(integrationsRes.integrations ?? []);
      setExports(exportsRes.exports ?? []);
      setSandbox(sandboxRes.sandbox ?? { enabled: true, test_price_id: '' });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load finance ops');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function connectAccounting() {
    try {
      await apiSend(
        '/ops/finance/accounting/integrations/connect',
        'POST',
        {
          provider,
          account_name: accountName,
          client_id: clientId,
        },
        tenantId
      );
      setStatus('Accounting integration connected.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect accounting integration');
    }
  }

  async function submitExport() {
    try {
      await apiSend(
        '/ops/finance/accounting/exports',
        'POST',
        {
          provider,
          export_type: exportType,
          period_label: periodLabel,
        },
        tenantId
      );
      setStatus('Accounting export submitted.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit export');
    }
  }

  async function remediate(action: 'disable_provider' | 'rotate_provider_key') {
    try {
      await apiSend(
        '/ops/finance/security/intelligence/remediate',
        'POST',
        {
          action,
          provider: guardProvider,
          reason: 'finance_ops_auto_guard',
        },
        tenantId
      );
      setStatus(
        action === 'disable_provider'
          ? `${guardProvider} provider disabled. Rotate with a fresh API key before re-enabling.`
          : `${guardProvider} provider marked for key rotation and disabled until new key is set.`
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run remediation action');
    }
  }

  async function updateSandbox(enabled: boolean) {
    try {
      await apiSend(
        '/ops/finance/stripe-sandbox',
        'POST',
        {
          enabled,
          test_price_id: sandbox.test_price_id,
        },
        tenantId
      );
      setStatus(`Stripe sandbox ${enabled ? 'enabled' : 'disabled'}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update stripe sandbox');
    }
  }

  async function buyCreditsViaStripe() {
    try {
      const quantity = Math.max(100, Number.parseInt(buyCredits, 10) || 100);
      const result = await apiSend<{ checkout_url?: string }>(
        '/billing/stripe/credit-checkout-session',
        'POST',
        {
          credits: quantity,
          request_id: crypto.randomUUID().replaceAll('-', ''),
        },
        tenantId
      );
      const checkoutUrl = result.checkout_url;
      if (checkoutUrl) {
        window.open(checkoutUrl, '_blank', 'noopener,noreferrer');
        setStatus('Stripe checkout opened in a new tab.');
      } else {
        setStatus('Stripe checkout request submitted. Check Stripe events for status.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create stripe checkout');
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  } as const;
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  } as const;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Finance Ops</h1>
        <p style={{ color: 'var(--muted)' }}>
          API ROI, current credits, per-generation credit burn, profit and loss, accounting integrations
          (Xero/QuickBooks/Qube), and Stripe sandbox controls.
        </p>

        {(error || status) && (
          <div style={{ ...card, marginBottom: 10, color: error ? '#f87171' : '#34d399' }}>{error || status}</div>
        )}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: 10,
            marginBottom: 10,
          }}
        >
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Current Credits</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{hub?.credits.current_balance ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Credits Used</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{hub?.credits.used_total ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Average API ROI</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{hub?.roi.avg_roi ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Profit Estimate</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>${hub?.profit_loss.profit_estimate ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Risk Score</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{hub?.api_security.risk_score ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Profit Margin</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{hub?.profit_loss.margin_percent ?? 0}%</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Credit Usage By Generation Source</h3>
            {Object.entries(hub?.credits.usage_by_source ?? {}).length === 0 && (
              <div style={{ color: 'var(--muted)' }}>No usage data yet.</div>
            )}
            {Object.entries(hub?.credits.usage_by_source ?? {}).map(([k, v]) => (
              <div key={k} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0' }}>
                <strong>{k}</strong>: {v} credits
              </div>
            ))}

            <h3 style={{ marginBottom: 8 }}>Provider Cost vs Value</h3>
            {(hub?.provider_breakdown ?? []).map((row) => {
              const cost = Math.max(0, row.total_cost);
              const value = Math.max(0, row.total_value);
              const widthCost = Math.max(3, Math.round(cost * 8000));
              const widthValue = Math.max(3, Math.round(value * 8000));
              return (
                <div key={row.provider} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>
                    <strong>{row.provider}</strong> · ROI {row.avg_roi} · {row.disabled ? 'disabled' : 'active'}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr 90px', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: 'var(--muted)' }}>Cost</span>
                    <div style={{ height: 8, background: 'rgba(239, 68, 68, 0.2)', borderRadius: 999 }}>
                      <div
                        style={{
                          width: `${Math.min(100, widthCost)}%`,
                          height: '100%',
                          background: '#ef4444',
                          borderRadius: 999,
                        }}
                      />
                    </div>
                    <span style={{ fontSize: 11, textAlign: 'right' }}>${cost.toFixed(4)}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr 90px', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: 'var(--muted)' }}>Value</span>
                    <div style={{ height: 8, background: 'rgba(52, 211, 153, 0.2)', borderRadius: 999 }}>
                      <div
                        style={{
                          width: `${Math.min(100, widthValue)}%`,
                          height: '100%',
                          background: '#34d399',
                          borderRadius: 999,
                        }}
                      />
                    </div>
                    <span style={{ fontSize: 11, textAlign: 'right' }}>${value.toFixed(4)}</span>
                  </div>
                </div>
              );
            })}

            <h3 style={{ marginBottom: 8 }}>Buy Credits (Stripe)</h3>
            <input
              style={input}
              type="number"
              min={1}
              value={buyCredits}
              onChange={(e) => setBuyCredits(e.target.value)}
            />
            <button
              onClick={() => void buyCreditsViaStripe()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Open Stripe Checkout
            </button>

            <h3>Stripe Sandbox</h3>
            <input
              style={input}
              value={sandbox.test_price_id}
              onChange={(e) => setSandbox((prev) => ({ ...prev, test_price_id: e.target.value }))}
              placeholder="price_test_credits_pack"
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => void updateSandbox(true)}
                style={{
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: 8,
                  background: '#34d399',
                  color: '#00110a',
                  fontWeight: 700,
                }}
              >
                Enable Sandbox
              </button>
              <button
                onClick={() => void updateSandbox(false)}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                Disable Sandbox
              </button>
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>
              Sandbox mode is currently <strong>{sandbox.enabled ? 'ON' : 'OFF'}</strong>.
            </div>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Accounting Integrations</h3>
            <select
              style={input}
              value={provider}
              onChange={(e) => setProvider(e.target.value as 'xero' | 'quickbooks' | 'hmrc')}
            >
              <option value="xero">xero</option>
              <option value="quickbooks">quickbooks</option>
              <option value="hmrc">hmrc</option>
            </select>
            <input
              style={input}
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              placeholder="Account name"
            />
            <input
              style={input}
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="Client ID"
            />
            <button
              onClick={() => void connectAccounting()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
                marginBottom: 10,
              }}
            >
              Connect Integration
            </button>

            {integrations.map((item) => (
              <div key={item.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0', fontSize: 13 }}>
                <strong>{item.provider_alias || item.provider}</strong> · {item.account_name} · {item.status}
              </div>
            ))}

            <h3 style={{ marginTop: 12 }}>Accountant P&L / Ledger Export</h3>
            <select
              style={input}
              value={exportType}
              onChange={(e) => setExportType(e.target.value as 'pnl' | 'ledger' | 'invoice_batch' | 'vat_return')}
            >
              <option value="pnl">pnl</option>
              <option value="ledger">ledger</option>
              <option value="invoice_batch">invoice_batch</option>
              <option value="vat_return">vat_return</option>
              <option value="balance_sheet">balance_sheet</option>
            </select>
            <input
              style={input}
              value={periodLabel}
              onChange={(e) => setPeriodLabel(e.target.value)}
              placeholder="Period label"
            />
            <button
              onClick={() => void submitExport()}
              style={{
                padding: '8px 12px',
                border: '1px solid var(--line)',
                borderRadius: 8,
                background: 'transparent',
                color: 'var(--text)',
              }}
            >
              Submit Export
            </button>

            {exports.map((item) => (
              <div
                key={item.id}
                style={{ borderBottom: '1px solid var(--line)', padding: '6px 0', fontSize: 12, color: 'var(--muted)' }}
              >
                #{item.id} · {item.provider_alias || item.provider} · {item.export_type} · {item.period_label} ·{' '}
                {item.status}
              </div>
            ))}

            <h3 style={{ marginTop: 14, marginBottom: 8 }}>Provider Guardrails</h3>
            <select
              style={input}
              value={guardProvider}
              onChange={(e) => setGuardProvider(e.target.value as 'openai' | 'anthropic' | 'google_vertex')}
            >
              <option value="openai">openai</option>
              <option value="anthropic">anthropic</option>
              <option value="google_vertex">google_vertex</option>
            </select>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => void remediate('disable_provider')}
                style={{
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: 8,
                  background: '#ef4444',
                  color: '#fff',
                  fontWeight: 700,
                }}
              >
                Disable Provider
              </button>
              <button
                onClick={() => void remediate('rotate_provider_key')}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                Disable + Require New API Key
              </button>
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>
              Use this when profitability drops or a key leak is suspected. Re-enable by rotating provider keys via AI
              Security admin endpoint.
            </div>
          </section>
        </div>

        <section style={{ ...card, marginTop: 10 }}>
          <h3 style={{ marginTop: 0 }}>Ultra Security Intelligence</h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
              gap: 10,
              marginBottom: 10,
            }}
          >
            <div style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Risk Level</div>
              <strong style={{ fontSize: 22 }}>{hub?.api_security.risk_level ?? 'low'}</strong>
            </div>
            <div style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>API Requests</div>
              <strong style={{ fontSize: 22 }}>{hub?.api_security.total_requests ?? 0}</strong>
            </div>
            <div style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Distinct IP Hashes</div>
              <strong style={{ fontSize: 22 }}>{hub?.api_security.unique_ip_hashes ?? 0}</strong>
            </div>
            <div style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Frontend API Exposure</div>
              <strong style={{ fontSize: 22 }}>
                {hub?.api_security.frontend_public_api_key_detected ? 'YES' : 'NO'}
              </strong>
            </div>
          </div>

          {(hub?.api_security.suspicious_signals ?? []).length === 0 && (
            <div style={{ color: 'var(--muted)' }}>No active suspicious signals detected.</div>
          )}

          {(hub?.api_security.suspicious_signals ?? []).map((signal) => (
            <div
              key={signal.code}
              style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 10, marginBottom: 8 }}
            >
              <div>
                <strong>{signal.code}</strong> · {signal.severity}
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>{signal.message}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                Action: {signal.recommended_action}
              </div>
            </div>
          ))}

          <h4 style={{ marginBottom: 6 }}>Top API Paths</h4>
          {(securityIntelligence?.api_security.top_paths ?? []).map((pathItem) => (
            <div
              key={pathItem.path}
              style={{ display: 'grid', gridTemplateColumns: '1fr 110px', gap: 8, marginBottom: 6 }}
            >
              <span style={{ fontSize: 12 }}>{pathItem.path}</span>
              <span style={{ fontSize: 12, textAlign: 'right' }}>{pathItem.count} calls</span>
            </div>
          ))}
        </section>

        <section style={{ ...card, marginTop: 10 }}>
          <h3 style={{ marginTop: 0 }}>Profit and Loss Command View</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 8 }}>
            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Revenue</div>
              <strong>${hub?.profit_loss.monthly_revenue_estimate ?? 0}</strong>
            </div>
            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Payouts</div>
              <strong>${hub?.profit_loss.monthly_payout_estimate ?? 0}</strong>
            </div>
            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>AI Cost</div>
              <strong>${hub?.profit_loss.api_cost_estimate ?? 0}</strong>
            </div>
            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Guardrail Status</div>
              <strong>{hub?.profit_guard.healthy ? 'Healthy' : 'At Risk'}</strong>
            </div>
          </div>
          {hub?.profit_guard.auto_disable_candidate_provider && (
            <div style={{ marginTop: 8, color: '#fbbf24', fontSize: 12 }}>
              Profit guard candidate to disable first: {hub.profit_guard.auto_disable_candidate_provider}
            </div>
          )}
        </section>

        <section style={{ ...card, marginTop: 10 }}>
          <h3 style={{ marginTop: 0 }}>Credit Ledger ({ledger.length})</h3>
          {ledger.map((entry) => (
            <div key={entry.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0', fontSize: 12 }}>
              <strong>#{entry.id}</strong> · {entry.reason} · {entry.amount > 0 ? '+' : ''}
              {entry.amount} · balance {entry.running_balance} · {new Date(entry.created_at).toLocaleString()}
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
