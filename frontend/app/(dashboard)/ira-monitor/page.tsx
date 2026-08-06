'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

// ─── Types ────────────────────────────────────────────────────────────────────

type IRAEvent = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type IRASession = {
  id: number;
  role: string;
  channel: string;
  user_message: string;
  created_at: string;
};

type IRAActionSnapshot = {
  id: number;
  target: string;
  command: string;
  confidence: number;
  rollback_enabled: boolean;
  created_at: string;
};

type MonitorData = {
  recent_events: IRAEvent[];
  recent_sessions: IRASession[];
  recent_snapshots: IRAActionSnapshot[];
  stats: {
    avg_confidence: number;
    total_chats: number;
    total_actions: number;
    failed_actions: number;
    total_cost_pence: number;
    total_cost_gbp: number;
  };
};

type PerformanceByType = {
  count: number;
  success_rate: number;
  failure_rate: number;
  avg_confidence: number;
  avg_latency_ms: number;
};

type PerformanceData = {
  total_data_points: number;
  overall_success_rate: number;
  overall_avg_confidence: number;
  by_action_type: Record<string, PerformanceByType>;
  recent: Array<{
    id: number;
    action_type: string;
    latency_ms: number;
    confidence: number;
    outcome: string;
    created_at: string;
  }>;
};

type ABVariantStats = {
  impressions: number;
  success_rate: number;
  avg_value: number;
};

type ABTest = {
  id: number;
  name: string;
  description: string;
  variants: string[];
  metric: string;
  status: string;
  created_at: string;
  analysis: {
    winner: string | null;
    confidence: number;
    by_variant: Record<string, ABVariantStats>;
  };
};

type ABTestsData = {
  total: number;
  tests: ABTest[];
};

type Tab = 'overview' | 'performance' | 'abtests' | 'events';
type Filter = 'all' | 'high' | 'low';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}

function confidenceBadge(c: number) {
  if (c >= 0.8) return 'bg-green-500/20 text-green-300';
  if (c >= 0.6) return 'bg-yellow-500/20 text-yellow-300';
  return 'bg-red-500/20 text-red-300';
}

function outcomeBadge(o: string) {
  if (o === 'success') return 'bg-green-500/20 text-green-300';
  if (o === 'failure') return 'bg-red-500/20 text-red-300';
  return 'bg-slate-600 text-[var(--muted)]';
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function filterButtonClass(filter: Filter, isActive: boolean): string {
  if (!isActive) return 'bg-slate-600 text-[var(--muted)] hover:bg-slate-500';
  if (filter === 'all') return 'bg-[var(--brand)] text-white';
  if (filter === 'high') return 'bg-green-600 text-white';
  return 'bg-red-600 text-white';
}

function filterButtonLabel(filter: Filter): string {
  if (filter === 'all') return 'All';
  if (filter === 'high') return '>=75%';
  return '<50%';
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function IRAMonitor() {
  const [monitor, setMonitor] = useState<MonitorData | null>(null);
  const [perf, setPerf] = useState<PerformanceData | null>(null);
  const [abTests, setAbTests] = useState<ABTestsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [filter, setFilter] = useState<Filter>('all');
  const [lastRefreshLabel, setLastRefreshLabel] = useState('pending');

  const fetchAll = async () => {
    try {
      const [monitorData, performanceData, abTestsData] = await Promise.all([
        apiGet<MonitorData>('/ira/monitor', DEFAULT_TENANT_ID),
        apiGet<PerformanceData>('/ira/performance', DEFAULT_TENANT_ID),
        apiGet<ABTestsData>('/ira/ab-tests', DEFAULT_TENANT_ID),
      ]);

      setMonitor(monitorData);
      setPerf(performanceData);
      setAbTests(abTestsData);
      setError(null);
      setLastRefreshLabel(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredSnapshots = (monitor?.recent_snapshots ?? []).filter((s) => {
    if (filter === 'high') return s.confidence >= 0.75;
    if (filter === 'low') return s.confidence < 0.5;
    return true;
  });

  const abTestsLabel = abTests ? ` (${abTests.total})` : '';

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'performance', label: 'Performance' },
    { id: 'abtests', label: `A/B Tests${abTestsLabel}` },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-[#f1f5f9] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-[var(--text)]">IRA Monitor</h1>
            <p className="text-[var(--muted)] text-sm mt-1">Real-time autonomous agent · refreshed {lastRefreshLabel}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setLoading(true);
                void fetchAll();
              }}
              className="px-3 py-1.5 bg-[var(--brand)] hover:bg-slate-600 text-[var(--muted)] text-sm rounded-lg transition"
            >
              ↻ Refresh
            </button>
            <Link
              href="/dashboard"
              className="px-4 py-2 bg-[var(--brand)] hover:bg-[var(--brand)] text-white text-sm rounded-lg transition"
            >
              ← Dashboard
            </Link>
          </div>
        </div>

        {/* Stat Cards */}
        {monitor && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            {(
              [
                { label: 'Avg Confidence', value: pct(monitor.stats.avg_confidence), color: 'text-[var(--text)]' },
                { label: 'Chat Sessions', value: monitor.stats.total_chats, color: 'text-[var(--text)]' },
                { label: 'Actions Run', value: monitor.stats.total_actions, color: 'text-[var(--text)]' },
                { label: 'Failed', value: monitor.stats.failed_actions, color: 'text-red-400' },
                {
                  label: 'Total Cost',
                  value: `\u00a3${monitor.stats.total_cost_gbp.toFixed(4)}`,
                  sub: `${monitor.stats.total_cost_pence.toFixed(2)}p`,
                  color: 'text-emerald-400',
                },
                perf
                  ? { label: 'Overall Success', value: pct(perf.overall_success_rate), color: 'text-[var(--brand)]' }
                  : { label: 'Success Rate', value: '\u2014', color: 'text-[var(--muted)]' },
              ] as Array<{ label: string; value: string | number; sub?: string; color: string }>
            ).map((s) => (
              <div key={s.label} className="bg-[var(--brand)]/50 backdrop-blur border border-[var(--line)] rounded-lg p-4">
                <p className="text-[var(--muted)] text-xs mb-1">{s.label}</p>
                <p className={`text-xl font-bold ${s.color}`}>{String(s.value)}</p>
                {s.sub && <p className="text-[var(--text)]0 text-xs mt-0.5">{s.sub}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg p-10 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-3" />
            <p className="text-[var(--muted)]">Loading IRA activity…</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-400 text-sm">⚠ {error}</p>
          </div>
        )}

        {/* Tabs */}
        {monitor && !loading && (
          <>
            <div className="flex gap-1 mb-5 bg-[#f1f5f9] rounded-lg p-1 w-fit">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                    tab === t.id
                      ? 'bg-[var(--brand)] text-white shadow'
                      : 'text-[var(--muted)] hover:text-white hover:bg-[var(--brand)]'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* OVERVIEW */}
            {tab === 'overview' && (
              <div className="space-y-5">
                <section className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden">
                  <div className="px-6 py-4 border-b border-[var(--line)] flex justify-between items-center">
                    <h2 className="font-bold text-[var(--text)]">Action Snapshots</h2>
                    <div className="flex gap-2">
                      {(['all', 'high', 'low'] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setFilter(f)}
                          className={`px-3 py-1 rounded text-xs transition ${filterButtonClass(f, filter === f)}`}
                        >
                          {filterButtonLabel(f)}
                        </button>
                      ))}
                    </div>
                  </div>
                  {filteredSnapshots.length === 0 ? (
                    <p className="p-6 text-[var(--muted)] text-sm text-center">No snapshots yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#f1f5f9] text-[var(--muted)] text-xs uppercase">
                          <tr>
                            <th className="px-5 py-3 text-left">Target</th>
                            <th className="px-5 py-3 text-left">Command</th>
                            <th className="px-5 py-3 text-center">Confidence</th>
                            <th className="px-5 py-3 text-center">Rollback</th>
                            <th className="px-5 py-3 text-left">Time</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {filteredSnapshots.slice(0, 12).map((s) => (
                            <tr key={s.id} className="hover:bg-[var(--brand)]/60 transition">
                              <td className="px-5 py-3">
                                <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-purple-300 rounded text-xs font-mono">
                                  {s.target}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-[var(--muted)] font-mono text-xs">{s.command}</td>
                              <td className="px-5 py-3 text-center">
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-bold ${confidenceBadge(s.confidence)}`}
                                >
                                  {pct(s.confidence)}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center">
                                {s.rollback_enabled ? (
                                  <span className="px-2 py-0.5 bg-green-500/20 text-green-300 rounded text-xs">
                                    Yes
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 bg-slate-600 text-[var(--muted)] rounded text-xs">No</span>
                                )}
                              </td>
                              <td className="px-5 py-3 text-[var(--muted)] text-xs">{formatTime(s.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                <section className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden">
                  <div className="px-6 py-4 border-b border-[var(--line)]">
                    <h2 className="font-bold text-[var(--text)]">Recent Chat Sessions</h2>
                  </div>
                  {monitor.recent_sessions.length === 0 ? (
                    <p className="p-6 text-[var(--muted)] text-sm text-center">No sessions yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#f1f5f9] text-[var(--muted)] text-xs uppercase">
                          <tr>
                            <th className="px-5 py-3 text-left">Role</th>
                            <th className="px-5 py-3 text-left">Channel</th>
                            <th className="px-5 py-3 text-left">Message</th>
                            <th className="px-5 py-3 text-left">Time</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {monitor.recent_sessions.slice(0, 10).map((s) => (
                            <tr key={s.id} className="hover:bg-[var(--brand)]/60 transition">
                              <td className="px-5 py-3">
                                <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-indigo-300 rounded text-xs font-mono">
                                  {s.role}
                                </span>
                              </td>
                              <td className="px-5 py-3">
                                <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-cyan-300 rounded text-xs">
                                  {s.channel}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-[var(--muted)] text-xs max-w-xs truncate">
                                {s.user_message.substring(0, 80)}
                              </td>
                              <td className="px-5 py-3 text-[var(--muted)] text-xs">{formatTime(s.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              </div>
            )}

            {/* PERFORMANCE */}
            {tab === 'performance' && (
              <div className="space-y-5">
                {perf && (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg p-5">
                      <p className="text-[var(--muted)] text-xs mb-1">Data Points</p>
                      <p className="text-3xl font-bold text-[var(--text)]">{perf.total_data_points}</p>
                    </div>
                    <div className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg p-5">
                      <p className="text-[var(--muted)] text-xs mb-1">Overall Success Rate</p>
                      <p className="text-3xl font-bold text-green-400">{pct(perf.overall_success_rate)}</p>
                    </div>
                    <div className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg p-5">
                      <p className="text-[var(--muted)] text-xs mb-1">Avg Confidence</p>
                      <p className="text-3xl font-bold text-[var(--brand)]">{pct(perf.overall_avg_confidence)}</p>
                    </div>
                  </div>
                )}

                <section className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden">
                  <div className="px-6 py-4 border-b border-[var(--line)]">
                    <h2 className="font-bold text-[var(--text)]">By Action Type</h2>
                  </div>
                  {!perf || Object.keys(perf.by_action_type).length === 0 ? (
                    <p className="p-6 text-[var(--muted)] text-sm text-center">No performance data yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#f1f5f9] text-[var(--muted)] text-xs uppercase">
                          <tr>
                            <th className="px-5 py-3 text-left">Action Type</th>
                            <th className="px-5 py-3 text-center">Count</th>
                            <th className="px-5 py-3 text-center">Success Rate</th>
                            <th className="px-5 py-3 text-center">Failure Rate</th>
                            <th className="px-5 py-3 text-center">Avg Confidence</th>
                            <th className="px-5 py-3 text-center">Avg Latency</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {Object.entries(perf.by_action_type).map(([atype, stats]) => (
                            <tr key={atype} className="hover:bg-[var(--brand)]/60 transition">
                              <td className="px-5 py-3">
                                <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-blue-300 rounded text-xs font-mono">
                                  {atype}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center text-[var(--muted)]">{stats.count}</td>
                              <td className="px-5 py-3 text-center">
                                <div className="flex items-center justify-center gap-2">
                                  <div className="w-16 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-green-400 rounded-full"
                                      style={{ width: `${stats.success_rate * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-green-400 text-xs">{pct(stats.success_rate)}</span>
                                </div>
                              </td>
                              <td className="px-5 py-3 text-center text-red-400 text-xs">{pct(stats.failure_rate)}</td>
                              <td className="px-5 py-3 text-center">
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-bold ${confidenceBadge(stats.avg_confidence)}`}
                                >
                                  {pct(stats.avg_confidence)}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center text-[var(--muted)] text-xs">
                                {stats.avg_latency_ms > 0 ? `${stats.avg_latency_ms.toFixed(0)}ms` : '\u2014'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                <section className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden">
                  <div className="px-6 py-4 border-b border-[var(--line)]">
                    <h2 className="font-bold text-[var(--text)]">Recent Data Points</h2>
                  </div>
                  {!perf || perf.recent.length === 0 ? (
                    <p className="p-6 text-[var(--muted)] text-sm text-center">No data yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#f1f5f9] text-[var(--muted)] text-xs uppercase">
                          <tr>
                            <th className="px-5 py-3 text-left">Action Type</th>
                            <th className="px-5 py-3 text-center">Outcome</th>
                            <th className="px-5 py-3 text-center">Confidence</th>
                            <th className="px-5 py-3 text-center">Latency</th>
                            <th className="px-5 py-3 text-left">Time</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {perf.recent.map((p) => (
                            <tr key={p.id} className="hover:bg-[var(--brand)]/60 transition">
                              <td className="px-5 py-3">
                                <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-blue-300 rounded text-xs font-mono">
                                  {p.action_type}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center">
                                <span className={`px-2 py-0.5 rounded text-xs ${outcomeBadge(p.outcome)}`}>
                                  {p.outcome}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center">
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-bold ${confidenceBadge(p.confidence)}`}
                                >
                                  {pct(p.confidence)}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center text-[var(--muted)] text-xs">
                                {p.latency_ms > 0 ? `${p.latency_ms.toFixed(0)}ms` : '\u2014'}
                              </td>
                              <td className="px-5 py-3 text-[var(--muted)] text-xs">{formatTime(p.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              </div>
            )}

            {/* A/B TESTS */}
            {tab === 'abtests' && (
              <div className="space-y-5">
                {!abTests || abTests.total === 0 ? (
                  <div className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg p-10 text-center">
                    <p className="text-[var(--muted)] text-sm mb-2">No A/B tests created yet.</p>
                    <p className="text-[var(--text)]0 text-xs">
                      Use <code className="text-[var(--brand)]">POST /ira/ab-tests</code> to start your first test.
                    </p>
                  </div>
                ) : (
                  abTests.tests.map((test) => (
                    <section
                      key={test.id}
                      className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden"
                    >
                      <div className="px-6 py-4 border-b border-[var(--line)] flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-3 mb-1">
                            <h2 className="font-bold text-[var(--text)]">{test.name}</h2>
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-medium ${test.status === 'running' ? 'bg-green-500/20 text-green-300' : 'bg-slate-600 text-[var(--muted)]'}`}
                            >
                              {test.status}
                            </span>
                          </div>
                          {test.description && <p className="text-[var(--muted)] text-sm">{test.description}</p>}
                          <p className="text-[var(--text)]0 text-xs mt-1">
                            Metric: <span className="text-[var(--muted)]">{test.metric}</span> · Created:{' '}
                            {formatTime(test.created_at)}
                          </p>
                        </div>
                        {test.analysis.winner && (
                          <div className="text-right">
                            <p className="text-[var(--muted)] text-xs mb-1">Current Leader</p>
                            <span className="px-3 py-1 bg-yellow-500/20 text-yellow-300 rounded-lg text-sm font-bold">
                              &#127942; {test.analysis.winner}
                            </span>
                            <p className="text-[var(--text)]0 text-xs mt-1">Confidence: {pct(test.analysis.confidence)}</p>
                          </div>
                        )}
                      </div>
                      <div className="p-6 grid gap-4">
                        {Object.entries(test.analysis.by_variant).map(([variant, stats]) => {
                          const isWinner = variant === test.analysis.winner;
                          return (
                            <div
                              key={variant}
                              className={`rounded-lg p-4 border ${isWinner ? 'border-yellow-500/40 bg-yellow-500/5' : 'border-[var(--line)] bg-[#f1f5f9]'}`}
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                  {isWinner && <span className="text-yellow-400">&#127942;</span>}
                                  <span className="text-[var(--text)] font-medium text-sm">{variant}</span>
                                </div>
                                <div className="flex gap-4 text-xs text-[var(--muted)]">
                                  <span>{stats.impressions} impressions</span>
                                  <span className="text-green-400">{pct(stats.success_rate)} success</span>
                                  <span className="text-[var(--brand)]">avg value {stats.avg_value.toFixed(2)}</span>
                                </div>
                              </div>
                              <div className="w-full h-2 bg-[var(--brand)] rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all ${isWinner ? 'bg-yellow-400' : 'bg-[var(--brand)]'}`}
                                  style={{ width: `${Math.min(stats.success_rate * 100, 100)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  ))
                )}
              </div>
            )}

            {/* EVENTS */}
            {tab === 'events' && (
              <section className="bg-[var(--brand)]/50 border border-[var(--line)] rounded-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-[var(--line)]">
                  <h2 className="font-bold text-[var(--text)]">Recent IRA Events</h2>
                </div>
                {monitor.recent_events.length === 0 ? (
                  <p className="p-6 text-[var(--muted)] text-sm text-center">No events yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-[#f1f5f9] text-[var(--muted)] text-xs uppercase">
                        <tr>
                          <th className="px-5 py-3 text-left">Type</th>
                          <th className="px-5 py-3 text-left">Payload</th>
                          <th className="px-5 py-3 text-left">Time</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-700">
                        {monitor.recent_events.slice(0, 20).map((e) => (
                          <tr key={e.id} className="hover:bg-[var(--brand)]/60 transition">
                            <td className="px-5 py-3">
                              <span className="px-2 py-0.5 bg-[var(--brand)]/20 text-blue-300 rounded text-xs font-mono whitespace-nowrap">
                                {e.event_type}
                              </span>
                            </td>
                            <td className="px-5 py-3 text-[var(--muted)] text-xs max-w-md truncate">
                              {JSON.stringify(e.payload).substring(0, 120)}
                            </td>
                            <td className="px-5 py-3 text-[var(--muted)] text-xs whitespace-nowrap">
                              {formatTime(e.created_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
