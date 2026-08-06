'use client';
/* eslint-disable react/no-array-index-key, sonarjs/no-nested-conditional */

import { useEffect, useRef, useState } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

// ── Types ──────────────────────────────────────────────────────────────────

interface AgentTool {
  key: string;
  display_name: string;
  group_name: string;
  description: string;
  fn_signature: string;
  risk_level: 'low' | 'medium' | 'high';
  requires_confirmation: boolean;
  backend_endpoint: string;
  is_active: boolean;
}

interface ToolGroup {
  group: string;
  count: number;
  tools: AgentTool[];
}

interface AgentConfig {
  current_phase: string;
  enabled_models: string[];
  enabled_agent_roles: string[];
  tool_count_limit: number;
  max_auto_actions: number;
  allow_high_risk_tools: boolean;
  mcp_endpoint: string | null;
}

interface AgentConfigResponse {
  status: string;
  tenant_id: string;
  agent_stack: {
    llm: string[];
    framework: string[];
    tool_protocol: string;
    backend: string;
    context_store: string[];
    auth: string[];
    observability: string[];
    audit: string[];
  };
  config: AgentConfig;
  phase_info: Record<string, { label: string; status: string; description: string }>;
  tool_stats: {
    total: number;
    active: number;
    by_group: Record<string, number>;
    by_risk: { low: number; medium: number; high: number };
    requiring_confirmation: number;
  };
  session_stats: {
    total: number;
    active: number;
    total_tool_calls: number;
    successful_calls: number;
    failed_calls: number;
    pending_confirmations: number;
  };
  health: {
    agent_ready: boolean;
    llm_available: boolean;
    db_available: boolean;
    mcp_endpoint: string | null;
    audit_enabled: boolean;
  };
  retrieved_at: string;
}

interface AgentToolsResponse {
  status: string;
  total: number;
  tools: AgentTool[];
  by_group: ToolGroup[];
}

interface AgentAuditResponse {
  status: string;
  total_calls: number;
  success_count: number;
  error_count: number;
  calls: {
    tool_key: string;
    status: string;
    risk_level: string;
    agent_role: string;
    created_at: string;
    duration_ms?: number;
  }[];
}

// ── Design tokens ──────────────────────────────────────────────────────────

const C = {
  bg: 'var(--bg)',
  card: 'var(--card)',
  card2: '#f6f7fa',
  border: 'var(--line)',
  text: 'var(--text)',
  muted: 'var(--muted)',
  green: '#16a34a',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#6366f1',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
  pink: '#ec4899',
  indigo: '#6366f1',
};

const STACK_LAYERS = [
  { label: 'LLM', color: C.purple, icon: '🧠', purposeKey: 'llm' as const },
  { label: 'Agent Framework', color: C.blue, icon: '🤖', purposeKey: 'framework' as const },
  { label: 'Tool Protocol', color: C.cyan, icon: '🔌', purposeKey: null },
  { label: 'Backend', color: C.green, icon: '⚙️', purposeKey: 'backend' as const },
  { label: 'Context Store', color: C.amber, icon: '🗃️', purposeKey: 'context_store' as const },
  { label: 'Auth', color: C.indigo, icon: '🔐', purposeKey: 'auth' as const },
  { label: 'Observability', color: '#f97316', icon: '📊', purposeKey: 'observability' as const },
  { label: 'Audit', color: C.red, icon: '📋', purposeKey: 'audit' as const },
] as const;

const AGENT_ROLES = [
  { name: 'User Proxy Agent', model: 'Any LLM', role: 'Talks to user, clarifies intent', color: C.blue, icon: '👤' },
  {
    name: 'Planner Agent',
    model: 'DeepSeek R1',
    role: 'Breaks request into steps, chooses tools',
    color: C.purple,
    icon: '🗺️',
  },
  {
    name: 'Executor Agent',
    model: 'Llama-3 8B',
    role: 'Calls tools via FastAPI/MCP, handles retries',
    color: C.cyan,
    icon: '⚡',
  },
  {
    name: 'Critic Agent',
    model: 'Llama-3 8B',
    role: 'Validates results, checks side effects',
    color: C.amber,
    icon: '🔍',
  },
  {
    name: 'Supervisor Agent',
    model: 'DeepSeek R1',
    role: 'Enforces safety rules, stops risky actions',
    color: C.red,
    icon: '🛡️',
  },
];

const SECURITY_RULES = [
  'Every tool has required scopes/roles — agent can only call allowed tools',
  'All tool calls are audited: who · what · when · params · result',
  'High-risk tools require explicit "Yes, proceed" confirmation',
  'Two-step flow for destructive ops: plan → preview → confirm',
  'OPA available for policy-as-code enforcement',
];

const RISK_COLOR: Record<string, string> = { low: C.green, medium: C.amber, high: C.red };
const RISK_LABEL: Record<string, string> = { low: 'Low', medium: 'Med', high: 'High' };

// ── Components ─────────────────────────────────────────────────────────────

function StatusDot({ ok, label }: Readonly<{ ok: boolean; label: string }>) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: ok ? C.green : C.muted,
          boxShadow: ok ? `0 0 6px ${C.green}` : 'none',
        }}
      />
      <span style={{ fontSize: 12, color: ok ? C.text : C.muted }}>{label}</span>
    </div>
  );
}

function StatBox({ label, value, color }: Readonly<{ label: string; value: string | number; color?: string }>) {
  return (
    <div
      style={{
        background: C.card2,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        padding: '12px 16px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 800, color: color ?? C.text }}>{value}</div>
      <div style={{ fontSize: 10, color: C.muted, marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.8 }}>
        {label}
      </div>
    </div>
  );
}

function Badge({ label, color }: Readonly<{ label: string; color: string }>) {
  return (
    <span
      style={{
        background: color + '20',
        color,
        border: `1px solid ${color}44`,
        borderRadius: 6,
        padding: '2px 8px',
        fontSize: 10,
        fontWeight: 700,
      }}
    >
      {label}
    </span>
  );
}

function Card({ children, style }: Readonly<{ children: React.ReactNode; style?: React.CSSProperties }>) {
  return (
    <div
      style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 16, padding: '20px 24px', ...style }}
    >
      {children}
    </div>
  );
}

function SectionTitle({ children, sub }: Readonly<{ children: React.ReactNode; sub?: string }>) {
  return (
    <div style={{ marginBottom: 16 }}>
      <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: C.text }}>{children}</h2>
      {sub && <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function KodeeAgentPage() {
  const [configData, setConfigData] = useState<AgentConfigResponse | null>(null);
  const [toolsData, setToolsData] = useState<AgentToolsResponse | null>(null);
  const [auditData, setAuditData] = useState<AgentAuditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState('');
  const [activePhase, setActivePhase] = useState(0);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [view, setView] = useState<'overview' | 'tools' | 'audit'>('overview');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [cfg, tools, audit] = await Promise.all([
        apiGet<AgentConfigResponse>('/platform/agent-config', DEFAULT_TENANT_ID),
        apiGet<AgentToolsResponse>('/platform/agent-tools', DEFAULT_TENANT_ID),
        apiGet<AgentAuditResponse>('/platform/agent-audit', DEFAULT_TENANT_ID),
      ]);
      setConfigData(cfg);
      setToolsData(tools);
      setAuditData(audit);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load agent telemetry.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    intervalRef.current = setInterval(load, 60_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const phaseKeys = ['phase1', 'phase2', 'phase3'];
  const phases = configData?.phase_info
    ? phaseKeys.map((k) => ({ key: k, ...configData.phase_info[k] }))
    : [
        {
          key: 'phase1',
          label: 'Internal Admin Agent',
          status: 'current',
          description: 'Read-only + reporting, 5–10 safe tools, local LLM',
        },
        {
          key: 'phase2',
          label: 'Controlled Actions',
          status: 'planned',
          description: 'Write tools with confirmation UX + full audit logging',
        },
        {
          key: 'phase3',
          label: 'Full Kodee-Class',
          status: 'planned',
          description: 'MCP tool registry, multi-agent orchestration, 350+ actions',
        },
      ];

  const phaseIcons = ['🌱', '⚙️', '🚀'];

  return (
    <div
      style={{
        minHeight: '100vh',
        background: C.bg,
        color: C.text,
        fontFamily: 'system-ui, sans-serif',
        padding: '28px 20px',
        maxWidth: 1200,
        margin: '0 auto',
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 6 }}>
            Platform · AI Infrastructure
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 40 }}>🤖</div>
            <div>
              <h1 style={{ margin: 0, fontSize: 26, fontWeight: 900 }}>Kodee-Class AI Agent</h1>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: C.muted, maxWidth: 500 }}>
                Self-hosted, open-source agent that <strong style={{ color: C.text }}>takes real actions</strong> via
                MCP tools — with full context, security, and multi-agent orchestration.
              </p>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {lastRefresh && <span style={{ fontSize: 10, color: C.muted }}>Last: {lastRefresh}</span>}
          {(['overview', 'tools', 'audit'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: '6px 14px',
                borderRadius: 7,
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                border: `1px solid ${view === v ? C.blue : C.border}`,
                background: view === v ? C.blue + '22' : 'transparent',
                color: view === v ? C.blue : C.muted,
                textTransform: 'capitalize',
              }}
            >
              {v}
            </button>
          ))}
          <button
            onClick={load}
            disabled={loading}
            style={{
              padding: '6px 14px',
              borderRadius: 7,
              fontSize: 12,
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              border: `1px solid ${C.border}`,
              background: 'transparent',
              color: loading ? C.muted : C.text,
            }}
          >
            {loading ? '…' : '⟳'}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: C.red + '15',
            border: `1px solid ${C.red}44`,
            borderRadius: 10,
            padding: '10px 14px',
            marginBottom: 20,
            color: C.red,
            fontSize: 12,
          }}
        >
          ⚠ {error} — showing static architecture data below.
        </div>
      )}

      {/* ── Live health strip (always visible) ── */}
      {configData && (
        <Card style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <StatusDot ok={configData.health.agent_ready} label="Agent Ready" />
              <StatusDot ok={configData.health.llm_available} label="LLM Online" />
              <StatusDot ok={configData.health.audit_enabled} label="Audit Active" />
              <StatusDot ok={!!configData.health.mcp_endpoint} label="MCP Connected" />
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginLeft: 'auto' }}>
              <Badge label={`Phase: ${configData.config.current_phase}`} color={C.green} />
              <Badge label={`${configData.tool_stats.total} Tools`} color={C.blue} />
              <Badge label={`${configData.config.enabled_models.length} Models`} color={C.purple} />
              <Badge label={`${configData.session_stats.total_tool_calls} Calls`} color={C.cyan} />
            </div>
          </div>
        </Card>
      )}

      {/* ── OVERVIEW TAB ── */}
      {view === 'overview' && (
        <>
          {/* Stats row */}
          {configData && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 120px), 1fr))',
                gap: 10,
                marginBottom: 24,
              }}
            >
              <StatBox label="Total Tools" value={configData.tool_stats.total} color={C.blue} />
              <StatBox label="Active" value={configData.tool_stats.active} color={C.green} />
              <StatBox label="Sessions" value={configData.session_stats.total} color={C.purple} />
              <StatBox label="Tool Calls" value={configData.session_stats.total_tool_calls} color={C.cyan} />
              <StatBox label="Successful" value={configData.session_stats.successful_calls} color={C.green} />
              <StatBox
                label="Errors"
                value={configData.session_stats.failed_calls}
                color={configData.session_stats.failed_calls > 0 ? C.red : C.muted}
              />
              <StatBox
                label="Pending Confirm"
                value={configData.session_stats.pending_confirmations}
                color={configData.session_stats.pending_confirmations > 0 ? C.amber : C.muted}
              />
              <StatBox label="AI Models" value={configData.config.enabled_models.length} color={C.purple} />
            </div>
          )}

          {/* Core Agent Loop */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="The fundamental loop — replicated with open tools">Core Agent Loop</SectionTitle>
            <div style={{ display: 'flex', gap: 0, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
              {['💬 Chat', '🧠 Understand', '🔧 Call Tools', '⚡ Execute', '✅ Confirm'].map((step, i, arr) => (
                <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                  <div
                    style={{
                      background: C.blue + '20',
                      border: `1.5px solid ${C.blue}55`,
                      borderRadius: 10,
                      padding: '12px 18px',
                      textAlign: 'center',
                      minWidth: 90,
                    }}
                  >
                    <div style={{ fontSize: 18 }}>{step.split(' ')[0]}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: C.blue, marginTop: 3 }}>
                      {step.split(' ').slice(1).join(' ')}
                    </div>
                  </div>
                  {i < arr.length - 1 && <div style={{ color: C.muted, fontSize: 18, margin: '0 4px' }}>→</div>}
                </div>
              ))}
            </div>
          </Card>

          {/* Stack layers — live data if available */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="All free / open-source — 100% self-hostable">Hybrid Stack</SectionTitle>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 12 }}>
              {STACK_LAYERS.map((layer) => {
                const tools: string[] = configData?.agent_stack
                  ? layer.purposeKey && layer.purposeKey in configData.agent_stack
                    ? Array.isArray((configData.agent_stack as Record<string, unknown>)[layer.purposeKey])
                      ? ((configData.agent_stack as Record<string, unknown>)[layer.purposeKey] as string[])
                      : [JSON.stringify((configData.agent_stack as Record<string, unknown>)[layer.purposeKey])]
                    : layer.purposeKey === null
                      ? [configData.agent_stack.tool_protocol]
                      : []
                  : [];
                const fallbackTools: Record<string, string[]> = {
                  LLM: ['Llama-3 8B/70B', 'DeepSeek R1'],
                  'Agent Framework': ['AutoGen', 'LangChain'],
                  'Tool Protocol': ['MCP (Model Context Protocol)', 'Custom Tool Registry'],
                  Backend: ['FastAPI'],
                  'Context Store': ['PostgreSQL + pgvector', 'OpenSearch'],
                  Auth: ['Keycloak', 'Supabase Auth'],
                  Observability: ['Prometheus', 'Grafana', 'Loki'],
                  Audit: ['PostgreSQL', 'OpenSearch'],
                };
                const displayTools = tools.length ? tools : (fallbackTools[layer.label] ?? []);
                return (
                  <div
                    key={layer.label}
                    style={{
                      background: C.card2,
                      border: `1px solid ${layer.color}44`,
                      borderRadius: 12,
                      padding: '14px 16px',
                      borderLeft: `4px solid ${layer.color}`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ fontSize: 20 }}>{layer.icon}</span>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 800,
                          color: layer.color,
                          textTransform: 'uppercase',
                          letterSpacing: 0.5,
                        }}
                      >
                        {layer.label}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {displayTools.map((t: string) => (
                        <span
                          key={t}
                          style={{
                            fontSize: 11,
                            background: layer.color + '18',
                            color: layer.color,
                            border: `1px solid ${layer.color}33`,
                            borderRadius: 5,
                            padding: '2px 7px',
                            fontWeight: 600,
                          }}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Agent roles */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="AutoGen-style multi-agent pattern running in FastAPI">Agent Roles</SectionTitle>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {AGENT_ROLES.map((a) => {
                const isEnabled =
                  configData?.config.enabled_agent_roles.some((r) =>
                    a.name.toLowerCase().includes(r.replace('_agent', ''))
                  ) ?? true;
                return (
                  <div
                    key={a.name}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '32px 180px 120px 1fr auto',
                      gap: 14,
                      alignItems: 'center',
                      background: C.card2,
                      border: `1px solid ${a.color}33`,
                      borderRadius: 10,
                      padding: '12px 16px',
                      opacity: isEnabled ? 1 : 0.5,
                    }}
                  >
                    <span style={{ fontSize: 20 }}>{a.icon}</span>
                    <div style={{ fontSize: 13, fontWeight: 700, color: a.color }}>{a.name}</div>
                    <span
                      style={{
                        fontSize: 10,
                        background: a.color + '18',
                        color: a.color,
                        border: `1px solid ${a.color}33`,
                        borderRadius: 5,
                        padding: '3px 8px',
                        fontWeight: 600,
                      }}
                    >
                      {a.model}
                    </span>
                    <div style={{ fontSize: 12, color: C.muted }}>{a.role}</div>
                    <Badge label={isEnabled ? 'Active' : 'Inactive'} color={isEnabled ? C.green : C.muted} />
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Context & memory */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="At conversation start, backend loads all context and injects into system prompt">
              Context & Memory
            </SectionTitle>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))',
                gap: 10,
                marginBottom: 14,
              }}
            >
              {[
                {
                  icon: '👤',
                  label: 'User Identity',
                  store: 'PostgreSQL',
                  color: C.blue,
                  detail: 'Role, org, permissions, plan',
                },
                {
                  icon: '🌐',
                  label: 'Owned Resources',
                  store: 'PostgreSQL',
                  color: C.cyan,
                  detail: 'Sites, domains, projects',
                },
                {
                  icon: '📜',
                  label: 'Recent Activity',
                  store: 'OpenSearch',
                  color: C.green,
                  detail: 'Last actions, errors, tickets',
                },
                {
                  icon: '🧬',
                  label: 'Semantic Memory',
                  store: 'pgvector',
                  color: C.purple,
                  detail: 'Past conversations, embeddings',
                },
                {
                  icon: '📚',
                  label: 'Docs & Knowledge',
                  store: 'OpenSearch',
                  color: C.amber,
                  detail: 'Help articles, FAQs, SEO docs',
                },
              ].map((ctx) => (
                <div
                  key={ctx.label}
                  style={{
                    background: C.card2,
                    border: `1px solid ${ctx.color}33`,
                    borderRadius: 10,
                    padding: '14px 16px',
                  }}
                >
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 20 }}>{ctx.icon}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: ctx.color }}>{ctx.label}</span>
                  </div>
                  <Badge label={ctx.store} color={ctx.color} />
                  <div style={{ fontSize: 11, color: C.muted, marginTop: 6 }}>{ctx.detail}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Security rules */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="Enforced at every tool call">Security & Safety</SectionTitle>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
              {SECURITY_RULES.map((r, i) => (
                <div
                  key={`item-${i}`}
                  style={{
                    display: 'flex',
                    gap: 12,
                    padding: '10px 14px',
                    background: C.red + '08',
                    border: `1px solid ${C.red}22`,
                    borderRadius: 10,
                  }}
                >
                  <span style={{ color: C.red, fontWeight: 900, flexShrink: 0 }}>🔒</span>
                  <span style={{ fontSize: 12, color: C.text }}>{r}</span>
                </div>
              ))}
            </div>
            {configData && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Badge
                  label={configData.config.allow_high_risk_tools ? '⚠ High-Risk Tools ON' : '✓ High-Risk Tools OFF'}
                  color={configData.config.allow_high_risk_tools ? C.red : C.green}
                />
                <Badge
                  label={`Max Auto-Actions: ${configData.config.max_auto_actions}`}
                  color={configData.config.max_auto_actions > 0 ? C.amber : C.green}
                />
                <Badge
                  label={`Audit: ${configData.health.audit_enabled ? 'Enabled' : 'Disabled'}`}
                  color={configData.health.audit_enabled ? C.green : C.red}
                />
              </div>
            )}
          </Card>

          {/* MVP Phases */}
          <Card style={{ marginBottom: 24 }}>
            <SectionTitle sub="Phased rollout — from internal agent to full Kodee-class">MVP Roadmap</SectionTitle>
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
              {phases.map((p, i) => {
                const isCurrent = p.status === 'current';
                const phaseColors = [C.green, C.amber, C.blue];
                const color = phaseColors[i];
                return (
                  <button
                    key={p.key}
                    onClick={() => setActivePhase(i)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 8,
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: `1px solid ${activePhase === i ? color : C.border}`,
                      background: activePhase === i ? color + '20' : 'transparent',
                      color: activePhase === i ? color : C.muted,
                    }}
                  >
                    {phaseIcons[i]} {p.label}
                    {isCurrent && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: 9,
                          background: C.green + '30',
                          color: C.green,
                          borderRadius: 4,
                          padding: '1px 5px',
                        }}
                      >
                        LIVE
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            <div
              style={{
                background: C.card2,
                border: `1px solid ${[C.green, C.amber, C.blue][activePhase]}44`,
                borderRadius: 12,
                padding: '18px 22px',
              }}
            >
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 800,
                  color: [C.green, C.amber, C.blue][activePhase],
                  marginBottom: 12,
                }}
              >
                {phaseIcons[activePhase]} {phases[activePhase]?.label}
              </div>
              <div style={{ fontSize: 13, color: C.muted }}>{phases[activePhase]?.description}</div>
            </div>
          </Card>
        </>
      )}

      {/* ── TOOLS TAB ── */}
      {view === 'tools' && (
        <div>
          {toolsData && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 120px), 1fr))',
                gap: 10,
                marginBottom: 20,
              }}
            >
              <StatBox label="Total Tools" value={toolsData.total} color={C.blue} />
              <StatBox label="Low Risk" value={configData?.tool_stats.by_risk.low ?? 0} color={C.green} />
              <StatBox label="Medium Risk" value={configData?.tool_stats.by_risk.medium ?? 0} color={C.amber} />
              <StatBox label="High Risk" value={configData?.tool_stats.by_risk.high ?? 0} color={C.red} />
              <StatBox
                label="Confirm Req."
                value={configData?.tool_stats.requiring_confirmation ?? 0}
                color={C.amber}
              />
              <StatBox label="Groups" value={toolsData.by_group.length} color={C.purple} />
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {(toolsData?.by_group ?? []).map((g) => {
              const groupColors: Record<string, string> = {
                'SEO Tools': C.blue,
                'Platform Tools': C.green,
                'Content Tools': C.purple,
              };
              const color = groupColors[g.group] ?? C.cyan;
              const open = expandedGroup === g.group;
              return (
                <div
                  key={g.group}
                  style={{ background: C.card, border: `1px solid ${color}44`, borderRadius: 12, overflow: 'hidden' }}
                >
                  <button
                    onClick={() => setExpandedGroup(open ? null : g.group)}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '14px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      textAlign: 'left',
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 700, color, flex: 1 }}>{g.group}</span>
                    <span style={{ fontSize: 11, color: C.muted }}>{g.count} tools</span>
                    <span style={{ color: C.muted }}>{open ? '▲' : '▼'}</span>
                  </button>
                  {open && (
                    <div
                      style={{
                        borderTop: `1px solid ${C.border}`,
                        padding: '12px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 10,
                      }}
                    >
                      {g.tools.map((t) => (
                        <div
                          key={t.key}
                          style={{
                            background: C.card2,
                            border: `1px solid ${C.border}`,
                            borderRadius: 10,
                            padding: '12px 14px',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: 12,
                              justifyContent: 'space-between',
                              flexWrap: 'wrap',
                            }}
                          >
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginBottom: 2 }}>
                                {t.display_name}
                              </div>
                              <code style={{ fontSize: 10, color, fontFamily: 'monospace' }}>{t.fn_signature}</code>
                              {t.description && (
                                <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>{t.description}</div>
                              )}
                              {t.backend_endpoint && (
                                <div style={{ fontSize: 10, color: C.muted, marginTop: 3 }}>
                                  → <code style={{ color: C.cyan }}>{t.backend_endpoint}</code>
                                </div>
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                              <span
                                style={{
                                  fontSize: 9,
                                  fontWeight: 800,
                                  padding: '3px 8px',
                                  borderRadius: 5,
                                  background: RISK_COLOR[t.risk_level] + '18',
                                  color: RISK_COLOR[t.risk_level],
                                  border: `1px solid ${RISK_COLOR[t.risk_level]}33`,
                                }}
                              >
                                RISK: {RISK_LABEL[t.risk_level]}
                              </span>
                              {t.requires_confirmation && (
                                <span
                                  style={{
                                    fontSize: 9,
                                    color: C.amber,
                                    border: `1px solid ${C.amber}33`,
                                    borderRadius: 5,
                                    padding: '3px 8px',
                                    background: C.amber + '10',
                                  }}
                                >
                                  ⚠ Confirm
                                </span>
                              )}
                              <span style={{ fontSize: 9, color: t.is_active ? C.green : C.red }}>
                                {t.is_active ? '✓ Active' : '✗ Off'}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── AUDIT TAB ── */}
      {view === 'audit' && (
        <div>
          {auditData && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 130px), 1fr))',
                gap: 10,
                marginBottom: 20,
              }}
            >
              <StatBox label="Total Calls" value={auditData.total_calls} color={C.blue} />
              <StatBox label="Successful" value={auditData.success_count} color={C.green} />
              <StatBox
                label="Errors"
                value={auditData.error_count}
                color={auditData.error_count > 0 ? C.red : C.muted}
              />
            </div>
          )}

          <Card>
            <SectionTitle sub="Every tool invocation — who, what, when">Tool Call Audit Log</SectionTitle>
            {(auditData?.calls?.length ?? 0) === 0 ? (
              <div style={{ textAlign: 'center', color: C.muted, padding: 40, fontSize: 13 }}>
                No tool calls recorded yet. Start an agent session to generate audit entries.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(auditData?.calls ?? []).map((call, i) => {
                  const statusColor =
                    call.status === 'success'
                      ? C.green
                      : call.status === 'error'
                        ? C.red
                        : call.status === 'pending'
                          ? C.amber
                          : C.muted;
                  return (
                    <div
                      key={`item-${i}`}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '160px 100px 80px 80px 1fr',
                        gap: 12,
                        alignItems: 'center',
                        padding: '10px 14px',
                        background: C.card2,
                        border: `1px solid ${C.border}`,
                        borderRadius: 8,
                      }}
                    >
                      <code style={{ fontSize: 11, color: C.cyan }}>{call.tool_key}</code>
                      <span style={{ fontSize: 10, fontWeight: 700, color: statusColor, textTransform: 'uppercase' }}>
                        {call.status}
                      </span>
                      <span style={{ fontSize: 10, color: RISK_COLOR[call.risk_level] ?? C.muted }}>
                        {RISK_LABEL[call.risk_level] ?? '-'} risk
                      </span>
                      <span style={{ fontSize: 10, color: C.muted }}>{call.agent_role ?? '-'}</span>
                      <span style={{ fontSize: 10, color: C.muted }}>
                        {call.created_at ? new Date(call.created_at).toLocaleTimeString() : '-'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ── Footer ── */}
      <div
        style={{
          borderTop: `1px solid ${C.border}`,
          paddingTop: 16,
          marginTop: 28,
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div style={{ fontSize: 10, color: C.muted }}>
          Kodee-Class AI Agent · MCP + AutoGen + LangChain + DeepSeek R1 + FastAPI + Next.js · 100% Open Source
        </div>
        {lastRefresh && <div style={{ fontSize: 10, color: C.muted }}>Refreshed {lastRefresh} · auto 60s</div>}
      </div>
    </div>
  );
}
