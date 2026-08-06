'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, DEFAULT_TENANT_ID, setSuperAdminKeySession } from '@/app/lib/api-client';
import {
  buildIraChatContext,
  extractIraBackendMeta,
  extractIraBackendReply,
  type IraBackendMeta,
  type IraChatProviderPreference,
} from '@/app/components/ira-chat-utils';

type Json = Record<string, unknown>;

type IraStatus = {
  autonomy?: Json;
  connectors?: Json[];
  finance_health?: Json;
  risk_signal?: Json;
  recent_events?: Json[];
  provider_readiness?: Json;
};

type IraProviderReadiness = {
  key?: string;
  label?: string;
  configured?: boolean;
  model?: string;
  route?: string;
  reason?: string;
};

type CrmSyncStatus = {
  enabled?: boolean;
  interval_seconds?: number;
  last_sync_at?: string | null;
  events_processed_24h?: number;
};

type CrmBackupOps = {
  schedule_health?: string;
  next_runs?: { incremental_at?: string; full_at?: string };
  latest_incremental?: { completed_at?: string | null } | null;
  latest_full?: { completed_at?: string | null } | null;
};

type IraAssistanceLink = {
  title: string;
  href: string;
  description: string;
  accent: string;
};

type IraChatResult = {
  response: string;
  meta: IraBackendMeta | null;
};

type IraProviderReadinessMap = Record<string, IraProviderReadiness>;

type IraPlaybookMilestone = {
  key?: string;
  label?: string;
  target?: string;
  achieved?: boolean;
  detail?: string;
};

type IraPlaybookDecisionNode = {
  question?: string;
  if_yes?: string;
  if_no?: string;
};

type IraPlaybook = {
  completion_chart?: { achieved?: number; total?: number; percentage?: number };
  milestones?: IraPlaybookMilestone[];
  decision_tree?: IraPlaybookDecisionNode[];
};

const IRA_ASSISTANCE_LINKS: IraAssistanceLink[] = [
  {
    title: 'AI Social Studio',
    href: '/studio/social-studio',
    description: 'Launch the operator hub for publishing, trends, inbox, and content generation.',
    accent: '#22c55e',
  },
  {
    title: 'Automation Engine',
    href: '/studio/social-automation',
    description: 'Manage queue controls, pause-all safety, and rule-based automation.',
    accent: '#14b8a6',
  },
  {
    title: 'Smart Inbox',
    href: '/studio/social-inbox',
    description: 'Claim conversations, use saved replies, and inspect message history.',
    accent: '#6366f1',
  },
  {
    title: 'Campaign Calendar',
    href: '/studio/social-calendar',
    description: 'Review scheduled posts and control publishing cadence.',
    accent: '#a855f7',
  },
  {
    title: 'Review Management',
    href: '/studio/social-reviews',
    description: 'Track review replies, escalations, and care cases.',
    accent: '#f97316',
  },
  {
    title: 'Influencer CRM',
    href: '/studio/social-influencers',
    description: 'Search creators, shortlist matches, and manage partner discovery.',
    accent: '#8b5cf6',
  },
  {
    title: 'Employee Advocacy',
    href: '/studio/social-advocacy',
    description: 'Publish ready-to-share advocacy assets for internal amplification.',
    accent: '#16a34a',
  },
];

const EMPTY_STATUS: IraStatus = {};

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function formatConfidence(confidence: number | undefined): string | null {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) {
    return null;
  }

  return `${Math.round(confidence * 100)}% confidence`;
}

function isProviderReady(readiness: IraProviderReadinessMap, providerKey: 'openai' | 'anthropic'): boolean {
  return readiness[providerKey]?.configured === true;
}

function getUnavailableRouteReason(
  providerPreference: IraChatProviderPreference,
  openaiReady: boolean,
  anthropicReady: boolean
): string {
  if (providerPreference === 'openai' && !openaiReady) {
    return 'OpenAI route unavailable until provider is configured.';
  }
  if (providerPreference === 'anthropic' && !anthropicReady) {
    return 'Claude route unavailable until provider is configured.';
  }
  return '';
}

function optionLabel(label: string, ready: boolean): string {
  return ready ? label : `${label} (unavailable)`;
}

function buildUnavailableProviderBadges(readiness: IraProviderReadinessMap): string[] {
  const badges: string[] = [];
  if (readiness.openai?.configured !== true) {
    badges.push(`OpenAI: ${readiness.openai?.reason || 'Missing provider credentials/configuration'}`);
  }
  if (readiness.anthropic?.configured !== true) {
    badges.push(`Claude: ${readiness.anthropic?.reason || 'Missing provider credentials/configuration'}`);
  }
  return badges;
}

function normalizeIraStatusPayload(payload: Json): IraStatus {
  return {
    autonomy: typeof payload.autonomy === 'object' ? (payload.autonomy as Json) : {},
    connectors: Array.isArray(payload.connectors) ? (payload.connectors as Json[]) : [],
    finance_health: typeof payload.finance_health === 'object' ? (payload.finance_health as Json) : {},
    risk_signal: typeof payload.risk_signal === 'object' ? (payload.risk_signal as Json) : {},
    recent_events: Array.isArray(payload.recent_events) ? (payload.recent_events as Json[]) : [],
    provider_readiness: typeof payload.provider_readiness === 'object' ? (payload.provider_readiness as Json) : {},
  };
}

function ProviderReadinessSection({ providerReadiness }: Readonly<{ providerReadiness: IraProviderReadinessMap }>) {
  return (
    <section className="card" style={{ marginTop: 18 }}>
      <h3>Provider Readiness</h3>
      <p className="muted">See which chat routes are live before sending IRA to a specific provider.</p>
      <div className="grid dashboard-kpis">
        {Object.entries(providerReadiness).map(([key, provider]) => (
          <article key={key} className="card kpi-card">
            <p className="kpi-label">{provider.label || key}</p>
            <h3>{provider.configured ? 'ready' : 'not configured'}</h3>
            <p className="muted">Route: {provider.route || key}</p>
            <p className="muted">Model: {provider.model || 'n/a'}</p>
            <p className="muted">Reason: {provider.reason || 'n/a'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function IraChatResultPanel({ chatResult }: Readonly<{ chatResult: IraChatResult | null }>) {
  if (!chatResult) {
    return null;
  }

  return (
    <div aria-label="IRA chat result" style={{ display: 'grid', gap: 12, marginTop: 12 }}>
      <pre>{chatResult.response}</pre>
      {chatResult.meta ? (
        <div className="workspace-io-grid" style={{ alignItems: 'stretch' }}>
          <article className="card kpi-card">
            <p className="kpi-label">Conversation Analysis</p>
            <p>{formatConfidence(chatResult.meta.confidence) || 'Confidence unavailable'}</p>
            <p className="muted">Intent: {chatResult.meta.intent || 'n/a'}</p>
            <p className="muted">Domain: {chatResult.meta.domain || 'n/a'}</p>
            <p className="muted">Risk: {chatResult.meta.riskLevel || 'n/a'}</p>
            <p className="muted">Provider: {chatResult.meta.providerUsed || 'internal_rule_engine'}</p>
            <p className="muted">Route: {chatResult.meta.providerStatus || 'internal_default'}</p>
            <p className="muted">Model: {chatResult.meta.providerModel || 'rule_based'}</p>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Recommended Actions</p>
            {chatResult.meta.actionLabels.length ? (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {chatResult.meta.actionLabels.map((label) => (
                  <li key={label}>{label}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No action plan returned.</p>
            )}
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Knowledge Hits</p>
            {chatResult.meta.knowledgeHits.length ? (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {chatResult.meta.knowledgeHits.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No supporting knowledge retrieved.</p>
            )}
          </article>
        </div>
      ) : null}
    </div>
  );
}

export default function IraControlCenterPage() {
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [status, setStatus] = useState<IraStatus>(EMPTY_STATUS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [chatPrompt, setChatPrompt] = useState(
    'Handle customer onboarding questions and route billing concerns to admin workflow.'
  );
  const [chatResult, setChatResult] = useState<IraChatResult | null>(null);
  const [chatProviderPreference, setChatProviderPreference] = useState<IraChatProviderPreference>('auto');
  const [chatCustomProvider, setChatCustomProvider] = useState('');
  const [profitRevenue, setProfitRevenue] = useState(1000);
  const [profitCogs, setProfitCogs] = useState(200);
  const [profitCreditsCost, setProfitCreditsCost] = useState(50);
  const [suspiciousScoreInput, setSuspiciousScoreInput] = useState(0.2);
  const [superAdminKey, setSuperAdminKey] = useState('');
  const [disputesDashboard, setDisputesDashboard] = useState<Json>({});
  const [crmRecommendation, setCrmRecommendation] = useState<Json>({});
  const [crmConnectorHealth, setCrmConnectorHealth] = useState<Json>({});
  const [crmSyncStatus, setCrmSyncStatus] = useState<CrmSyncStatus>({});
  const [crmBackupOps, setCrmBackupOps] = useState<CrmBackupOps>({});
  const [playbook, setPlaybook] = useState<IraPlaybook>({});
  const [crmFeature, setCrmFeature] = useState('multi_tenancy');
  const [crmOwner, setCrmOwner] = useState('corteza');
  const [crmNotes, setCrmNotes] = useState('Policy update from IRA control center');

  const autonomy = useMemo(() => status.autonomy || {}, [status]);
  const connectors = useMemo(() => (Array.isArray(status.connectors) ? status.connectors : []), [status]);
  const finance = useMemo(() => status.finance_health || {}, [status]);
  const riskSignal = useMemo(() => status.risk_signal || {}, [status]);
  const providerReadiness = useMemo(() => {
    const readiness = status.provider_readiness;
    return typeof readiness === 'object' && readiness !== null ? (readiness as Record<string, IraProviderReadiness>) : {};
  }, [status]);
  const marginValue = asNumber(finance.profit_margin_pct, -1);
  const suspiciousScore = asNumber(riskSignal.score, -1);
  const openaiReady = isProviderReady(providerReadiness, 'openai');
  const anthropicReady = isProviderReady(providerReadiness, 'anthropic');
  const unavailableRouteBadges = buildUnavailableProviderBadges(providerReadiness);
  const unavailableRouteReason = getUnavailableRouteReason(chatProviderPreference, openaiReady, anthropicReady);

  async function refreshStatus() {
    setLoading(true);
    setError('');
    try {
      const payload = await apiGet('/ira/status', tenantId);
      setStatus(normalizeIraStatusPayload(payload));

      const disputes = await apiGet('/ira/disputes/dashboard', tenantId);
      setDisputesDashboard(disputes);

      const crm = await apiGet('/ira/crm/hybrid-recommendation', tenantId);
      setCrmRecommendation(crm);

      const crmConnectors = await apiGet('/ira/crm/connectors/status', tenantId);
      setCrmConnectorHealth(crmConnectors);

      const sync = await apiGet('/crm/ops/live-sync', tenantId);
      setCrmSyncStatus((sync.sync as Json) || {});

      const backup = await apiGet('/crm/ops/backup', tenantId);
      setCrmBackupOps(backup);

      const playbookPayload = await apiGet('/ira/playbook', tenantId);
      setPlaybook({
        completion_chart:
          typeof playbookPayload.completion_chart === 'object' && playbookPayload.completion_chart !== null
            ? playbookPayload.completion_chart
            : {},
        milestones: Array.isArray(playbookPayload.milestones) ? (playbookPayload.milestones as IraPlaybookMilestone[]) : [],
        decision_tree: Array.isArray(playbookPayload.decision_tree)
          ? (playbookPayload.decision_tree as IraPlaybookDecisionNode[])
          : [],
      });
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to load IRA status.');
    } finally {
      setLoading(false);
    }
  }

  function applySuperAdminKey() {
    setSuperAdminKeySession(superAdminKey);
    void refreshStatus();
  }

  async function updateCrmGovernance() {
    setLoading(true);
    setError('');
    try {
      await apiPost(
        '/ira/crm/feature-governance',
        {
          feature: crmFeature,
          owner: crmOwner,
          disable_duplicate_in_secondary: true,
          policy_change_human_validation: true,
          notes: crmNotes,
        },
        tenantId
      );
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'CRM governance update failed.');
    } finally {
      setLoading(false);
    }
  }

  async function sendChat() {
    setLoading(true);
    setError('');
    try {
      const payload = await apiPost(
        '/ira/chat',
        {
          role: 'admin',
          channel: 'chat',
          message: chatPrompt,
          context: buildIraChatContext(
            { source: 'ira-control-center' },
            {
              providerPreference: chatProviderPreference,
              customProvider: chatCustomProvider,
            }
          ),
        },
        tenantId
      );
      setChatResult({
        response: extractIraBackendReply(payload) || 'IRA responded with no message body.',
        meta: extractIraBackendMeta(payload),
      });
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'IRA chat failed.');
    } finally {
      setLoading(false);
    }
  }

  async function setProtection(enabled: boolean) {
    setLoading(true);
    setError('');
    try {
      if (enabled) {
        await apiPost(
          '/ira/finance/ingest',
          {
            revenue: profitRevenue,
            cogs: profitCogs,
            credits_cost: profitCreditsCost,
            suspicious_signal_score: suspiciousScoreInput,
            note: 'Manual trigger from control center',
          },
          tenantId
        );
      } else {
        await apiPost('/ira/control/disable-protection', {}, tenantId);
      }
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Protection mode update failed.');
    } finally {
      setLoading(false);
    }
  }

  async function updateConnector(channel: string, enabled: boolean) {
    setLoading(true);
    setError('');
    try {
      await apiPost(
        '/ira/connectors/upsert',
        {
          channel,
          enabled,
          provider: 'internal',
          config: { updated_from: 'ira-control-center' },
        },
        tenantId
      );
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Connector update failed.');
    } finally {
      setLoading(false);
    }
  }

  async function runCrmSyncNow() {
    setLoading(true);
    setError('');
    try {
      await apiPost('/crm/ops/live-sync/run', {}, tenantId);
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'CRM live sync run failed.');
    } finally {
      setLoading(false);
    }
  }

  async function toggleCrmSync() {
    setLoading(true);
    setError('');
    try {
      await apiPost(
        '/crm/ops/live-sync/toggle',
        {
          enabled: !crmSyncStatus.enabled,
          interval_seconds: Number(crmSyncStatus.interval_seconds) || 30,
        },
        tenantId
      );
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'CRM live sync toggle failed.');
    } finally {
      setLoading(false);
    }
  }

  async function runCrmBackup(mode: 'incremental' | 'full') {
    setLoading(true);
    setError('');
    try {
      await apiPost(`/crm/ops/backup/run?mode=${mode}&source=ira-control-center`, {}, tenantId);
      await refreshStatus();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : `CRM ${mode} backup failed.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshStatus();
  }, [tenantId]);

  useEffect(() => {
    if (chatProviderPreference === 'openai' && !openaiReady) {
      setChatProviderPreference('auto');
      return;
    }
    if (chatProviderPreference === 'anthropic' && !anthropicReady) {
      setChatProviderPreference('auto');
    }
  }, [chatProviderPreference, openaiReady, anthropicReady]);

  return (
    <main>
      <section className="hero dashboard-hero">
        <p className="eyebrow">IRA Command</p>
        <h1>IRA Control Center</h1>
        <p>
          Configure autonomous controls, monitor financial risk, manage connectors, and run 24/7 IRA operations for
          customers, admin, email, and chat.
        </p>
      </section>

      <section className="grid dashboard-kpis" style={{ marginTop: 18 }}>
        <article className="card kpi-card">
          <p className="kpi-label">Tenant</p>
          <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Super Admin Key</p>
          <input
            type="password"
            value={superAdminKey}
            onChange={(event) => setSuperAdminKey(event.target.value)}
            placeholder="X-Super-Admin-Key"
          />
          <button style={{ marginTop: 8 }} onClick={applySuperAdminKey}>
            Apply
          </button>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Autonomy</p>
          <h3>{String(Boolean(autonomy.autonomy_enabled))}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Protection Mode</p>
          <h3>{String(Boolean(autonomy.protection_mode))}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Profit Margin</p>
          <h3>{marginValue >= 0 ? `${marginValue}%` : 'n/a'}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Suspicious Signal</p>
          <h3>{suspiciousScore >= 0 ? suspiciousScore.toFixed(2) : 'n/a'}</h3>
        </article>
      </section>

      <ProviderReadinessSection providerReadiness={providerReadiness} />

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Extreme Success Playbook</h3>
        <p className="muted">Live progress chart for resilience milestones plus the operator decision tree.</p>
        <div className="workspace-io-grid">
          <div>
            <p className="kpi-label">Completion</p>
            <h4>{Number(playbook.completion_chart?.percentage || 0).toFixed(2)}%</h4>
            <p className="muted">
              {Number(playbook.completion_chart?.achieved || 0)} / {Number(playbook.completion_chart?.total || 0)} milestones
            </p>
          </div>
          <div>
            <p className="kpi-label">Milestones</p>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {(playbook.milestones || []).map((milestone) => (
                <li key={milestone.key || milestone.label || 'milestone'}>
                  <strong>{milestone.label || 'Milestone'}</strong> - {milestone.achieved ? 'done' : 'pending'}
                  {milestone.target ? ` (${milestone.target})` : ''}
                  {milestone.detail ? ` - ${milestone.detail}` : ''}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <p className="kpi-label">Decision Tree</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {(playbook.decision_tree || []).map((node) => (
              <li key={node.question || 'decision-node'}>
                <strong>{node.question || 'Decision question'}</strong>
                <div className="muted">If yes: {node.if_yes || 'n/a'}</div>
                <div className="muted">If no: {node.if_no || 'n/a'}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 16,
            alignItems: 'flex-start',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <p className="eyebrow">IRA Assistance</p>
            <h3>Social operations shortcuts</h3>
            <p className="muted">
              Jump directly into the new Social Studio surfaces from IRA so the left rail and the control center stay in
              sync.
            </p>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <span className="chip">Automation</span>
            <span className="chip">Inbox</span>
            <span className="chip">Calendar</span>
            <span className="chip">Reviews</span>
            <span className="chip">Influencers</span>
            <span className="chip">Advocacy</span>
          </div>
        </div>
        <div className="grid dashboard-kpis" style={{ marginTop: 16 }}>
          {IRA_ASSISTANCE_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="card kpi-card"
              style={{
                textDecoration: 'none',
                borderLeft: `4px solid ${item.accent}`,
                minHeight: 120,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: 8,
              }}
            >
              <div>
                <p className="kpi-label">{item.title}</p>
                <h4 style={{ margin: '4px 0 8px' }}>Open feature</h4>
                <p className="muted" style={{ margin: 0 }}>
                  {item.description}
                </p>
              </div>
              <span style={{ color: item.accent, fontWeight: 600 }}>Launch →</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Risk Signal</h3>
        <pre>{JSON.stringify(riskSignal, null, 2)}</pre>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Live IRA Chat</h3>
        <p className="muted">
          Chat and status checks are available for all tenants. Governance and connector mutations require a super admin
          key.
        </p>
        <textarea
          rows={4}
          value={chatPrompt}
          onChange={(event) => setChatPrompt(event.target.value)}
          placeholder="Tell IRA what to do"
        />
        <div className="workspace-io-grid" style={{ marginTop: 12 }}>
          <div>
            <label htmlFor="ira-provider-route">Provider route</label>
            <select
              id="ira-provider-route"
              aria-label="IRA control center provider route"
              value={chatProviderPreference}
              onChange={(event) => setChatProviderPreference(event.target.value as IraChatProviderPreference)}
            >
              <option value="auto">Auto / internal default</option>
              <option value="internal">Internal only</option>
              <option value="openai" disabled={!openaiReady}>
                {optionLabel('ChatGPT / OpenAI', openaiReady)}
              </option>
              <option value="anthropic" disabled={!anthropicReady}>
                {optionLabel('Claude / Anthropic', anthropicReady)}
              </option>
              <option value="custom">Custom provider key</option>
            </select>
          </div>
          {chatProviderPreference === 'custom' ? (
            <div>
              <label htmlFor="ira-custom-provider">Custom provider key</label>
              <input
                id="ira-custom-provider"
                aria-label="IRA custom provider"
                value={chatCustomProvider}
                onChange={(event) => setChatCustomProvider(event.target.value)}
                placeholder="claude-enterprise"
              />
            </div>
          ) : (
            <div>
              <p className="kpi-label">Routing note</p>
              <p className="muted" style={{ margin: 0 }}>
                Auto preserves the current internal path while keeping OpenAI and Claude routing hints ready.
              </p>
              <p className="muted" style={{ margin: '8px 0 0' }}>
                OpenAI: {providerReadiness.openai?.configured ? 'ready' : 'not configured'} | Claude:{' '}
                {providerReadiness.anthropic?.configured ? 'ready' : 'not configured'}
              </p>
              {unavailableRouteBadges.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {unavailableRouteBadges.map((badge) => (
                    <span
                      key={badge}
                      style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 999,
                        border: '1px solid rgba(245, 158, 11, 0.35)',
                        background: 'rgba(245, 158, 11, 0.12)',
                      }}
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              ) : null}
              {unavailableRouteReason ? <p className="muted">{unavailableRouteReason}</p> : null}
            </div>
          )}
        </div>
        <div className="workspace-actions">
          <button
            onClick={() => {
              void sendChat();
            }}
            disabled={loading}
          >
            Send To IRA
          </button>
          <button
            onClick={() => {
              void refreshStatus();
            }}
            disabled={loading}
          >
            Refresh Status
          </button>
        </div>
        <IraChatResultPanel chatResult={chatResult} />
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Protection Controls</h3>
        <div className="workspace-io-grid">
          <div>
            <label htmlFor="ira-revenue">Revenue</label>
            <input
              id="ira-revenue"
              type="number"
              value={profitRevenue}
              onChange={(event) => setProfitRevenue(Number(event.target.value) || 0)}
            />
          </div>
          <div>
            <label htmlFor="ira-cogs">COGS</label>
            <input
              id="ira-cogs"
              type="number"
              value={profitCogs}
              onChange={(event) => setProfitCogs(Number(event.target.value) || 0)}
            />
          </div>
          <div>
            <label htmlFor="ira-credits-cost">Credits Cost</label>
            <input
              id="ira-credits-cost"
              type="number"
              value={profitCreditsCost}
              onChange={(event) => setProfitCreditsCost(Number(event.target.value) || 0)}
            />
          </div>
          <div>
            <label htmlFor="ira-suspicious">Suspicious Signal (0-1)</label>
            <input
              id="ira-suspicious"
              type="number"
              step="0.01"
              value={suspiciousScoreInput}
              onChange={(event) => setSuspiciousScoreInput(Number(event.target.value) || 0)}
            />
          </div>
        </div>
        <div className="workspace-actions">
          <button
            onClick={() => {
              void setProtection(true);
            }}
            disabled={loading}
          >
            Evaluate / Activate Protection
          </button>
          <button
            onClick={() => {
              void setProtection(false);
            }}
            disabled={loading}
          >
            Disable Protection
          </button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>CRM Enterprise Orchestration</h3>
        <p className="muted">
          Run live CRM sync, trigger backups, and inspect cadence health directly from IRA control center.
        </p>
        <div className="workspace-io-grid">
          <div>
            <p className="kpi-label">Sync Enabled</p>
            <h4>{String(Boolean(crmSyncStatus.enabled))}</h4>
            <p className="muted">Interval: {Number(crmSyncStatus.interval_seconds) || 30}s</p>
            <p className="muted">Last Sync: {asString(crmSyncStatus.last_sync_at, 'never')}</p>
          </div>
          <div>
            <p className="kpi-label">Backup Health</p>
            <h4>{asString(crmBackupOps.schedule_health, 'unknown')}</h4>
            <p className="muted">Next incremental: {asString(crmBackupOps.next_runs?.incremental_at, 'n/a')}</p>
            <p className="muted">Next full: {asString(crmBackupOps.next_runs?.full_at, 'n/a')}</p>
          </div>
        </div>
        <div className="workspace-actions">
          <button
            onClick={() => {
              void runCrmSyncNow();
            }}
            disabled={loading}
          >
            Run CRM Sync Now
          </button>
          <button
            onClick={() => {
              void toggleCrmSync();
            }}
            disabled={loading}
          >
            {crmSyncStatus.enabled ? 'Pause CRM Sync' : 'Resume CRM Sync'}
          </button>
          <button
            onClick={() => {
              void runCrmBackup('incremental');
            }}
            disabled={loading}
          >
            Run Incremental Backup
          </button>
          <button
            onClick={() => {
              void runCrmBackup('full');
            }}
            disabled={loading}
          >
            Run Full Backup
          </button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Connectors</h3>
        <div className="grid dashboard-kpis">
          {connectors.map((connector, index) => {
            const channel = asString(connector.channel, 'unknown');
            const enabled = Boolean(connector.enabled);
            const provider = asString(connector.provider, 'internal');
            return (
              <article key={`${channel}-${index}`} className="card kpi-card">
                <p className="kpi-label">{channel}</p>
                <h3>{enabled ? 'enabled' : 'disabled'}</h3>
                <p className="muted">provider: {provider}</p>
                <div className="workspace-actions">
                  <button
                    onClick={() => {
                      void updateConnector(channel, true);
                    }}
                    disabled={loading}
                  >
                    Enable
                  </button>
                  <button
                    onClick={() => {
                      void updateConnector(channel, false);
                    }}
                    disabled={loading}
                  >
                    Disable
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Recent IRA Events</h3>
        <pre>{JSON.stringify(status.recent_events || [], null, 2)}</pre>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Disputes Dashboard</h3>
        <pre>{JSON.stringify(disputesDashboard, null, 2)}</pre>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>CRM Hybrid Strategy (Corteza + Odoo)</h3>
        <pre>{JSON.stringify(crmRecommendation, null, 2)}</pre>
        <h4 style={{ marginTop: 12 }}>Connector Health</h4>
        <pre>{JSON.stringify(crmConnectorHealth, null, 2)}</pre>
        <div className="workspace-io-grid" style={{ marginTop: 12 }}>
          <div>
            <label htmlFor="crm-feature">Feature</label>
            <select id="crm-feature" value={crmFeature} onChange={(event) => setCrmFeature(event.target.value)}>
              <option value="multi_tenancy">multi_tenancy</option>
              <option value="low_code_objects">low_code_objects</option>
              <option value="sales_pipeline_and_erp_adjacent">sales_pipeline_and_erp_adjacent</option>
              <option value="cross_platform_workflow_orchestration">cross_platform_workflow_orchestration</option>
              <option value="ecosystem_modules">ecosystem_modules</option>
            </select>
          </div>
          <div>
            <label htmlFor="crm-owner">Owner</label>
            <select id="crm-owner" value={crmOwner} onChange={(event) => setCrmOwner(event.target.value)}>
              <option value="corteza">Corteza</option>
              <option value="odoo">Odoo</option>
            </select>
          </div>
          <div>
            <label htmlFor="crm-notes">Notes</label>
            <input id="crm-notes" value={crmNotes} onChange={(event) => setCrmNotes(event.target.value)} />
          </div>
        </div>
        <div className="workspace-actions">
          <button
            onClick={() => {
              void updateCrmGovernance();
            }}
            disabled={loading}
          >
            Update CRM Feature Governance
          </button>
        </div>
      </section>

      {error ? (
        <section className="card" style={{ marginTop: 18 }}>
          <p className="auth-errors">{error}</p>
        </section>
      ) : null}
    </main>
  );
}
