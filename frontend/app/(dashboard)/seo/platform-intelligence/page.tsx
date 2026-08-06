'use client';

import { useEffect, useRef, useState } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

// ── Types ──────────────────────────────────────────────────────────────────

interface SeoModule {
  key: string;
  display_name: string;
  group: string;
  description: string;
  route_path: string;
  badge?: string;
  implemented: boolean;
  backend_ready: boolean;
  frontend_ready: boolean;
  database_ready: boolean;
  integrations: string[];
}

interface ModulesResponse {
  total: number;
  implemented: number;
  modules: SeoModule[];
  groups: { group: string; items: SeoModule[] }[];
}

interface SlaData {
  compliance_pct: number;
  status: 'green' | 'amber' | 'red';
  uptime_seconds: number;
  breached_paths: string[];
}

interface IntelData {
  health_score: number;
  health_grade: string;
  sla_status: string;
  sla_compliance_pct: number;
  model_count: number;
  anomalies: { latency_spikes: unknown[]; high_retry_jobs: number; recovery_queue_depth: number };
  governance: { lineage_events: number; active_prompt_versions: number };
  ranked_actions: { priority: string; area: string; action: string }[];
  retrieved_at: string;
}

interface MetricsData {
  uptime_seconds: number;
  latency: { path_count: number; sample_count: number };
  sla: SlaData;
  models: { count: number; providers: string[] };
}

// ── Constants ──────────────────────────────────────────────────────────────

const GROUP_COLORS: Record<string, string> = {
  'Search Intelligence': '#6366f1',
  'Experience Optimization': '#8b5cf6',
  'Growth & Governance': '#06b6d4',
  'Core Foundations': '#22c55e',
  'Expansion Modules': '#f59e0b',
  'SaaS Platform': '#ec4899',
  'Monitoring & Observability': '#14b8a6',
  'Schema & Optimization': '#a78bfa',
  'Content & Distribution': '#fb923c',
  'Accessibility & Media': '#34d399',
  'Performance & Audits': '#f43f5e',
};

const C = {
  bg: 'var(--bg, #f5f6f9)',
  card: 'var(--card, #ffffff)',
  border: 'var(--line, #e7e9ef)',
  text: 'var(--text, #0e1525)',
  muted: 'var(--muted, #6b7385)',
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#6366f1',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
};

// ── Helpers ────────────────────────────────────────────────────────────────

function moduleScore(m: SeoModule): number {
  let s = 0;
  if (m.implemented) s += 40;
  if (m.backend_ready) s += 25;
  if (m.frontend_ready) s += 25;
  if (m.database_ready) s += 5;
  const intBonus = Math.min(5, m.integrations.length * 1);
  return Math.min(100, s + intBonus);
}

function gradeColor(g: string) {
  if (g === 'A+' || g === 'A') return C.green;
  if (g === 'B') return C.cyan;
  if (g === 'C') return C.amber;
  return C.red;
}

function statusColor(s: string) {
  if (s === 'green') return C.green;
  if (s === 'amber') return C.amber;
  return C.red;
}

function priorityColor(p: string) {
  if (p === 'high') return C.red;
  if (p === 'medium') return C.amber;
  return C.cyan;
}

function fmtUptime(sec: number) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return `${h}h ${m}m`;
}

// ── Components ─────────────────────────────────────────────────────────────

function BigRing({ score, grade, label }: { score: number; grade: string; label: string }) {
  const r = 58;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = gradeColor(grade);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <svg width={148} height={148} viewBox="0 0 148 148">
        <defs>
          <linearGradient id="big-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity={0.5} />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <circle cx={74} cy={74} r={r} fill="none" stroke={C.border} strokeWidth={11} />
        <circle
          cx={74}
          cy={74}
          r={r}
          fill="none"
          stroke="url(#big-grad)"
          strokeWidth={11}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 74 74)"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x={74} y={66} textAnchor="middle" fill={color} fontSize={36} fontWeight={900}>
          {score}
        </text>
        <text x={74} y={86} textAnchor="middle" fill={C.muted} fontSize={14}>
          /100
        </text>
      </svg>
      <div
        style={{
          background: color + '22',
          border: `2px solid ${color}`,
          borderRadius: 8,
          padding: '4px 20px',
          fontSize: 20,
          fontWeight: 800,
          color,
          letterSpacing: 3,
        }}
      >
        {grade}
      </div>
      <div style={{ fontSize: 12, color: C.muted }}>{label}</div>
    </div>
  );
}

function MiniGauge({ value, label, color }: { value: number; label: string; color: string }) {
  const pct = Math.min(100, Math.max(0, value));
  const r = 26;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
      <svg width={64} height={64} viewBox="0 0 64 64">
        <circle cx={32} cy={32} r={r} fill="none" stroke={C.border} strokeWidth={6} />
        <circle
          cx={32}
          cy={32}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 32 32)"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x={32} y={36} textAnchor="middle" fill={C.text} fontSize={12} fontWeight={700}>
          {Math.round(pct)}
        </text>
      </svg>
      <span style={{ fontSize: 10, color: C.muted, textAlign: 'center', maxWidth: 64 }}>{label}</span>
    </div>
  );
}

function StatPill({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        padding: '12px 16px',
        textAlign: 'center',
        minWidth: 110,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 800, color: color ?? C.text }}>{value}</div>
      <div style={{ fontSize: 10, color: C.muted, marginTop: 3, textTransform: 'uppercase', letterSpacing: 0.8 }}>
        {label}
      </div>
    </div>
  );
}

function ProgressBar({ value, color, label }: { value: number; color: string; label?: string }) {
  return (
    <div>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: C.muted }}>{label}</span>
          <span style={{ fontSize: 11, fontWeight: 700, color }}>{value}%</span>
        </div>
      )}
      <div style={{ background: C.border, borderRadius: 8, height: 8, overflow: 'hidden' }}>
        <div
          style={{
            width: `${value}%`,
            height: '100%',
            background: color,
            borderRadius: 8,
            transition: 'width 1s ease',
          }}
        />
      </div>
    </div>
  );
}

function ModuleCard({ m, globalIdx }: { m: SeoModule; globalIdx: number }) {
  const score = moduleScore(m);
  const color = GROUP_COLORS[m.group] ?? C.blue;
  const r = 22;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <a href={m.route_path} style={{ textDecoration: 'none' }}>
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 12,
          padding: '14px 16px',
          display: 'flex',
          gap: 12,
          alignItems: 'flex-start',
          cursor: 'pointer',
          transition: 'border-color 0.2s',
          position: 'relative',
          overflow: 'hidden',
          height: '100%',
          boxSizing: 'border-box',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = color;
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = C.border;
        }}
      >
        <div style={{ position: 'absolute', top: 8, right: 10, fontSize: 10, color: C.muted, fontWeight: 600 }}>
          #{globalIdx + 1}
        </div>

        <div style={{ flexShrink: 0 }}>
          <svg width={56} height={56} viewBox="0 0 56 56">
            <circle cx={28} cy={28} r={r} fill="none" stroke={C.border} strokeWidth={5} />
            <circle
              cx={28}
              cy={28}
              r={r}
              fill="none"
              stroke={color}
              strokeWidth={5}
              strokeDasharray={`${dash} ${circ}`}
              strokeLinecap="round"
              transform="rotate(-90 28 28)"
            />
            <text x={28} y={32} textAnchor="middle" fill={color} fontSize={12} fontWeight={800}>
              {score}
            </text>
          </svg>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.text, lineHeight: 1.3 }}>{m.display_name}</div>
            {m.badge && (
              <span
                style={{
                  background: color + '22',
                  color,
                  border: `1px solid ${color}44`,
                  borderRadius: 4,
                  padding: '1px 6px',
                  fontSize: 9,
                  fontWeight: 700,
                }}
              >
                {m.badge}
              </span>
            )}
          </div>
          <div
            style={{
              fontSize: 11,
              color: C.muted,
              lineHeight: 1.4,
              marginBottom: 8,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {m.description}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {(
              [
                { label: 'Backend', ok: m.backend_ready },
                { label: 'Frontend', ok: m.frontend_ready },
                { label: 'DB', ok: m.database_ready },
                { label: 'AI', ok: m.implemented },
              ] as { label: string; ok: boolean }[]
            ).map(({ label, ok }) => (
              <span
                key={label}
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: ok ? C.green + '18' : C.red + '18',
                  color: ok ? C.green : C.red,
                  border: `1px solid ${ok ? C.green : C.red}33`,
                }}
              >
                {ok ? '✓' : '✗'} {label}
              </span>
            ))}
          </div>
          {m.integrations.length > 0 && (
            <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {m.integrations.slice(0, 4).map((i) => (
                <span
                  key={`item-${i}`}
                  style={{
                    fontSize: 9,
                    color: C.muted,
                    background: C.border + '55',
                    borderRadius: 4,
                    padding: '1px 5px',
                  }}
                >
                  {i}
                </span>
              ))}
              {m.integrations.length > 4 && (
                <span style={{ fontSize: 9, color: C.muted }}>+{m.integrations.length - 4}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </a>
  );
}

function computePlatformScore(modules: SeoModule[]): { score: number; grade: string } {
  if (!modules.length) return { score: 0, grade: 'D' };
  const avg = Math.round(modules.reduce((s, m) => s + moduleScore(m), 0) / modules.length);
  const grade = avg >= 95 ? 'A+' : avg >= 90 ? 'A' : avg >= 80 ? 'B' : avg >= 70 ? 'C' : 'D';
  return { score: avg, grade };
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function PlatformMatrixPage() {
  const [mods, setMods] = useState<SeoModule[]>([]);
  const [groups, setGroups] = useState<{ group: string; items: SeoModule[] }[]>([]);
  const [intel, setIntel] = useState<IntelData | null>(null);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState('');
  const [view, setView] = useState<'matrix' | 'groups'>('matrix');
  const [searchQ, setSearchQ] = useState('');
  const [filterGroup, setFilterGroup] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [modRes, iRes, mRes] = await Promise.all([
        apiGet('/seo-platform/modules', DEFAULT_TENANT_ID) as Promise<ModulesResponse>,
        apiGet('/platform/intelligence', DEFAULT_TENANT_ID) as Promise<IntelData>,
        apiGet('/platform/metrics', DEFAULT_TENANT_ID) as Promise<MetricsData>,
      ]);
      setMods(modRes.modules ?? []);
      setGroups(modRes.groups ?? []);
      setIntel(iRes);
      setMetrics(mRes);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
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

  const { score: platformScore, grade: platformGrade } = computePlatformScore(mods);
  const allGroupNames = Array.from(new Set(mods.map((m) => m.group)));

  const filtered = mods.filter((m) => {
    const q = searchQ.toLowerCase();
    const matchQ =
      !q ||
      m.display_name.toLowerCase().includes(q) ||
      m.description.toLowerCase().includes(q) ||
      m.key.toLowerCase().includes(q);
    const matchG = !filterGroup || m.group === filterGroup;
    return matchQ && matchG;
  });

  const implementedCount = mods.filter((m) => m.implemented).length;
  const backendCount = mods.filter((m) => m.backend_ready).length;
  const frontendCount = mods.filter((m) => m.frontend_ready).length;
  const totalModules = mods.length;

  return (
    <div
      style={{
        minHeight: '100vh',
        background: C.bg,
        color: C.text,
        fontFamily: 'system-ui, sans-serif',
        padding: '28px 20px',
      }}
    >
      {/* Header */}
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
          <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 4 }}>
            Platform Intelligence · Module 50
          </div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 900, letterSpacing: -0.5 }}>
            🏆 SEO Platform Matrix Score
          </h1>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>
            {loading ? 'Loading…' : `${totalModules} modules · ${allGroupNames.length} groups · Production-grade`}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {lastRefresh && <span style={{ fontSize: 10, color: C.muted }}>Last: {lastRefresh}</span>}
          {(['matrix', 'groups'] as const).map((v) => (
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
              }}
            >
              {v === 'matrix' ? 'Matrix' : 'By Group'}
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
          {error}
        </div>
      )}

      {/* Hero Score Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 20, marginBottom: 24, alignItems: 'start' }}>
        <div
          style={{
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 16,
            padding: '24px 32px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 16,
          }}
        >
          <BigRing score={platformScore} grade={platformGrade} label="Platform Score" />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12, textAlign: 'center' }}>
            {[
              { v: `${implementedCount}/${totalModules}`, l: 'IMPLEMENTED', c: C.green },
              { v: `${backendCount}/${totalModules}`, l: 'BACKEND', c: C.cyan },
              { v: `${frontendCount}/${totalModules}`, l: 'FRONTEND', c: C.purple },
            ].map(({ v, l, c }) => (
              <div key={l}>
                <div style={{ fontSize: 18, fontWeight: 800, color: c }}>{v}</div>
                <div style={{ fontSize: 9, color: C.muted }}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <StatPill label="Total Modules" value={totalModules} color={C.blue} />
            <StatPill label="Groups" value={allGroupNames.length} color={C.purple} />
            <StatPill label="Platform Score" value={`${platformScore}/100`} color={gradeColor(platformGrade)} />
            {intel && (
              <StatPill
                label="Health Score"
                value={`${intel.health_score}/100`}
                color={gradeColor(intel.health_grade)}
              />
            )}
            {metrics && (
              <StatPill label="SLA" value={`${metrics.sla.compliance_pct}%`} color={statusColor(metrics.sla.status)} />
            )}
            {metrics && <StatPill label="Uptime" value={fmtUptime(metrics.uptime_seconds)} color={C.green} />}
            {metrics && <StatPill label="AI Providers" value={metrics.models.count} color={C.cyan} />}
          </div>

          <div
            style={{
              background: C.card,
              border: `1px solid ${C.border}`,
              borderRadius: 12,
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            <ProgressBar
              value={Math.round((implementedCount / Math.max(totalModules, 1)) * 100)}
              color={C.green}
              label="AI Implementation"
            />
            <ProgressBar
              value={Math.round((backendCount / Math.max(totalModules, 1)) * 100)}
              color={C.cyan}
              label="Backend Coverage"
            />
            <ProgressBar
              value={Math.round((frontendCount / Math.max(totalModules, 1)) * 100)}
              color={C.purple}
              label="Frontend Coverage"
            />
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {groups.map((g) => {
              const color = GROUP_COLORS[g.group] ?? C.blue;
              const avg = Math.round(g.items.reduce((s, m) => s + moduleScore(m), 0) / g.items.length);
              const active = filterGroup === g.group;
              return (
                <button
                  key={g.group}
                  onClick={() => setFilterGroup(active ? '' : g.group)}
                  style={{
                    background: active ? color + '22' : C.card,
                    border: `1px solid ${active ? color : C.border}`,
                    borderRadius: 8,
                    padding: '5px 10px',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontSize: 10, fontWeight: 700, color }}>{avg}/100</div>
                  <div
                    style={{
                      fontSize: 9,
                      color: C.muted,
                      maxWidth: 80,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {g.group}
                  </div>
                  <div style={{ fontSize: 9, color: C.muted }}>{g.items.length}m</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mini gauges */}
      {intel && metrics && (
        <div
          style={{
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: '16px 20px',
            marginBottom: 24,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: C.muted,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 14,
            }}
          >
            Live Platform Gauges
          </div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            <MiniGauge value={platformScore} label="Platform" color={gradeColor(platformGrade)} />
            <MiniGauge value={intel.health_score} label="Health" color={gradeColor(intel.health_grade)} />
            <MiniGauge value={intel.sla_compliance_pct} label="SLA %" color={statusColor(intel.sla_status)} />
            <MiniGauge
              value={Math.round((implementedCount / Math.max(totalModules, 1)) * 100)}
              label="AI Impl"
              color={C.green}
            />
            <MiniGauge
              value={Math.round((backendCount / Math.max(totalModules, 1)) * 100)}
              label="Backend"
              color={C.cyan}
            />
            <MiniGauge
              value={Math.round((frontendCount / Math.max(totalModules, 1)) * 100)}
              label="Frontend"
              color={C.purple}
            />
            <MiniGauge
              value={Math.max(0, 100 - (intel.anomalies.latency_spikes as unknown[]).length * 20)}
              label="Latency"
              color={C.amber}
            />
            <MiniGauge
              value={Math.max(0, 100 - intel.anomalies.recovery_queue_depth * 10)}
              label="Queue"
              color={C.blue}
            />
            <MiniGauge value={Math.min(100, intel.governance.lineage_events * 5)} label="Lineage" color={C.purple} />
            <MiniGauge value={Math.min(100, metrics.models.count * 33)} label="Models" color={C.green} />
          </div>
        </div>
      )}

      {/* Search + filter bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          placeholder="Search modules…"
          style={{
            flex: 1,
            minWidth: 200,
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: '8px 14px',
            color: C.text,
            fontSize: 13,
            outline: 'none',
          }}
        />
        <select
          value={filterGroup}
          onChange={(e) => setFilterGroup(e.target.value)}
          style={{
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: '8px 12px',
            color: C.text,
            fontSize: 12,
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          <option value="">All Groups ({totalModules})</option>
          {allGroupNames.map((g) => (
            <option key={g} value={g}>
              {g} ({mods.filter((m) => m.group === g).length})
            </option>
          ))}
        </select>
        {(searchQ || filterGroup) && (
          <button
            onClick={() => {
              setSearchQ('');
              setFilterGroup('');
            }}
            style={{
              background: C.red + '22',
              border: `1px solid ${C.red}44`,
              color: C.red,
              borderRadius: 8,
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
        <span style={{ fontSize: 12, color: C.muted }}>{filtered.length} shown</span>
      </div>

      {/* Matrix View */}
      {view === 'matrix' && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 340px), 1fr))',
            gap: 14,
            marginBottom: 28,
          }}
        >
          {filtered.map((m) => (
            <ModuleCard key={m.key} m={m} globalIdx={mods.indexOf(m)} />
          ))}
          {filtered.length === 0 && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: C.muted, padding: 48, fontSize: 14 }}>
              No modules match your search.
            </div>
          )}
        </div>
      )}

      {/* Groups View */}
      {view === 'groups' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 32, marginBottom: 28 }}>
          {groups
            .filter((g) => !filterGroup || g.group === filterGroup)
            .map((g) => {
              const color = GROUP_COLORS[g.group] ?? C.blue;
              const items = g.items.filter((m) => {
                const q = searchQ.toLowerCase();
                return !q || m.display_name.toLowerCase().includes(q) || m.key.toLowerCase().includes(q);
              });
              if (!items.length) return null;
              const avg = Math.round(items.reduce((s, m) => s + moduleScore(m), 0) / items.length);
              return (
                <div key={g.group}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                    <div style={{ width: 4, height: 32, background: color, borderRadius: 4 }} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color }}>{g.group}</div>
                      <div style={{ fontSize: 11, color: C.muted }}>
                        {items.length} modules · avg {avg}/100
                      </div>
                    </div>
                    <div
                      style={{
                        marginLeft: 'auto',
                        background: color + '20',
                        border: `1px solid ${color}44`,
                        borderRadius: 16,
                        padding: '3px 12px',
                        fontSize: 12,
                        fontWeight: 700,
                        color,
                      }}
                    >
                      {avg}/100
                    </div>
                  </div>
                  <div
                    style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))', gap: 12 }}
                  >
                    {items.map((m) => (
                      <ModuleCard key={m.key} m={m} globalIdx={g.items.indexOf(m)} />
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      )}

      {/* Group scorecard table */}
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 16,
          padding: '20px 24px',
          marginBottom: 24,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: C.muted,
            textTransform: 'uppercase',
            letterSpacing: 1,
            marginBottom: 16,
          }}
        >
          Group Scorecard
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {groups.map((g) => {
            const color = GROUP_COLORS[g.group] ?? C.blue;
            const avg = Math.round(g.items.reduce((s, m) => s + moduleScore(m), 0) / g.items.length);
            const implCount = g.items.filter((m) => m.implemented).length;
            return (
              <div
                key={g.group}
                style={{ display: 'grid', gridTemplateColumns: '180px 50px 1fr 100px', gap: 12, alignItems: 'center' }}
              >
                <div style={{ fontSize: 12, color: C.text, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.group}</span>
                </div>
                <div style={{ fontSize: 12, color: C.muted, textAlign: 'right' }}>{g.items.length}m</div>
                <div style={{ background: C.border, borderRadius: 6, height: 8, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${avg}%`,
                      height: '100%',
                      background: color,
                      borderRadius: 6,
                      transition: 'width 1s ease',
                    }}
                  />
                </div>
                <div style={{ fontSize: 12, fontWeight: 700, color, textAlign: 'right' }}>
                  {avg}/100 ({implCount}/{g.items.length})
                </div>
              </div>
            );
          })}
          <div
            style={{
              borderTop: `1px solid ${C.border}`,
              paddingTop: 10,
              display: 'grid',
              gridTemplateColumns: '180px 50px 1fr 100px',
              gap: 12,
              alignItems: 'center',
              marginTop: 4,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 800, color: gradeColor(platformGrade) }}>TOTAL</div>
            <div style={{ fontSize: 12, color: C.muted, textAlign: 'right' }}>{totalModules}m</div>
            <div style={{ background: C.border, borderRadius: 6, height: 10, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${platformScore}%`,
                  height: '100%',
                  background: gradeColor(platformGrade),
                  borderRadius: 6,
                  transition: 'width 1s ease',
                }}
              />
            </div>
            <div style={{ fontSize: 14, fontWeight: 900, color: gradeColor(platformGrade), textAlign: 'right' }}>
              {platformScore}/100
            </div>
          </div>
        </div>
      </div>

      {/* Ranked actions */}
      {intel && intel.ranked_actions.length > 0 && (
        <div
          style={{
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 16,
            padding: '20px 24px',
            marginBottom: 24,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: C.muted,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 16,
            }}
          >
            Ranked Action Items
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {intel.ranked_actions.map((a, i) => (
              <div
                key={`item-${i}`}
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: '10px 14px',
                  background: priorityColor(a.priority) + '10',
                  border: `1px solid ${priorityColor(a.priority)}33`,
                  borderRadius: 10,
                }}
              >
                <div
                  style={{
                    minWidth: 54,
                    fontSize: 9,
                    fontWeight: 800,
                    color: priorityColor(a.priority),
                    textTransform: 'uppercase',
                    paddingTop: 1,
                  }}
                >
                  {a.priority}
                </div>
                <div style={{ fontSize: 12, color: C.text }}>{a.action}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div
        style={{
          borderTop: `1px solid ${C.border}`,
          paddingTop: 16,
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div style={{ fontSize: 10, color: C.muted }}>
          SEO Platform Matrix · {totalModules} modules · Grade {platformGrade} · {platformScore}/100 · DeepSeek R1 +
          FastAPI + Next.js + PostgreSQL + OpenSearch
        </div>
        {lastRefresh && <div style={{ fontSize: 10, color: C.muted }}>Refreshed {lastRefresh} · auto 60s</div>}
      </div>
    </div>
  );
}
