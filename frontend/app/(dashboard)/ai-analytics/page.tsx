'use client';

import { useState } from 'react';

type Tab = 'images' | 'videos' | 'voice' | 'text';

const TABS: { key: Tab; label: string; emoji: string }[] = [
  { key: 'images', label: 'Images', emoji: '🖼' },
  { key: 'videos', label: 'Videos', emoji: '🎬' },
  { key: 'voice', label: 'Voice', emoji: '🎙' },
  { key: 'text', label: 'Text', emoji: '💬' },
];

type ModelStat = { name: string; pct: number; count: string; color: string };
type PerfStat = { name: string; ms: number };
type TabData = {
  color: string;
  totalToday: string;
  delta: string;
  successRate: string;
  avgLatency: string;
  activeModels: number;
  models: ModelStat[];
  themes: string[];
  timeSeries: number[];
  perf: PerfStat[];
  recentActivity: string[];
};

const DATA: Record<Tab, TabData> = {
  images: {
    color: '#1bc7ff',
    totalToday: '0',
    delta: '+0%',
    successRate: '—',
    avgLatency: '—',
    activeModels: 0,
    models: [],
    themes: [],
    timeSeries: [],
    perf: [],
    recentActivity: [],
  },
  videos: {
    color: '#ec4899',
    totalToday: '0',
    delta: '+0%',
    successRate: '—',
    avgLatency: '—',
    activeModels: 0,
    models: [],
    themes: [],
    timeSeries: [],
    perf: [],
    recentActivity: [],
  },
  voice: {
    color: '#26d78e',
    totalToday: '0',
    delta: '+0%',
    successRate: '—',
    avgLatency: '—',
    activeModels: 0,
    models: [],
    themes: [],
    timeSeries: [],
    perf: [],
    recentActivity: [],
  },
  text: {
    color: '#f59e0b',
    totalToday: '0',
    delta: '+0%',
    successRate: '—',
    avgLatency: '—',
    activeModels: 0,
    models: [],
    themes: [],
    timeSeries: [],
    perf: [],
    recentActivity: [],
  },
};

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// ─── SVG Donut Chart ───────────────────────────────────────────────────────
function DonutChart({ models }: { models: ModelStat[] }) {
  const R = 54;
  const C = 2 * Math.PI * R;
  const GAP = 2.5;
  let cumPct = 0;

  return (
    <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
      {/* Background ring */}
      <circle cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="18" />
      {models.map((m) => {
        const segLen = Math.max(0, (m.pct / 100) * C - GAP);
        const rotation = (cumPct / 100) * 360 - 90;
        // eslint-disable-next-line react-hooks/immutability
        cumPct += m.pct;
        return (
          <circle
            key={m.name}
            cx="70"
            cy="70"
            r={R}
            fill="none"
            stroke={m.color}
            strokeWidth="18"
            strokeDasharray={`${segLen} ${C}`}
            strokeLinecap="butt"
            style={{ transform: `rotate(${rotation}deg)`, transformOrigin: '70px 70px' }}
          />
        );
      })}
      {/* Center label */}
      <text x="70" y="63" textAnchor="middle" fill="var(--text)" fontSize="20" fontWeight="700">
        {models.length}
      </text>
      <text x="70" y="78" textAnchor="middle" fill="var(--muted)" fontSize="10">
        models
      </text>
    </svg>
  );
}

// ─── SVG Line Chart ─────────────────────────────────────────────────────────
function LineChart({ data, color }: { data: number[]; color: string }) {
  const VW = 560;
  const H = 80;
  const padX = 6;
  const padY = 8;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const sx = (i: number) => padX + (i / (data.length - 1)) * (VW - padX * 2);
  const sy = (v: number) => padY + (1 - (v - min) / range) * (H - padY * 2);

  const points = data.map((v, i) => `${sx(i)},${sy(v)}`).join(' ');
  const areaPoints = `${sx(0)},${H} ${points} ${sx(data.length - 1)},${H}`;
  const gradId = `lg${color.replace('#', '')}`;
  const peakIdx = data.indexOf(Math.max(...data));

  return (
    <svg width="100%" height={H} viewBox={`0 0 ${VW} ${H}`} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map((t) => (
        <line
          key={t}
          x1={padX}
          y1={padY + (1 - t) * (H - padY * 2)}
          x2={VW - padX}
          y2={padY + (1 - t) * (H - padY * 2)}
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="1"
        />
      ))}
      <polygon points={areaPoints} fill={`url(#${gradId})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2.4"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Peak marker */}
      <circle cx={sx(peakIdx)} cy={sy(data[peakIdx])} r="5" fill={color} />
      <circle cx={sx(peakIdx)} cy={sy(data[peakIdx])} r="9" fill={color} fillOpacity="0.2" />
      {/* Latest dot */}
      <circle cx={sx(data.length - 1)} cy={sy(data[data.length - 1])} r="3.5" fill={color} />
    </svg>
  );
}

// ─── SVG Horizontal Bar Chart ───────────────────────────────────────────────
function BarChart({ data, color }: { data: PerfStat[]; color: string }) {
  const VW = 320;
  const barH = 14;
  const gap = 12;
  const labelW = 72;
  const valueW = 36;
  const maxMs = Math.max(...data.map((d) => d.ms));
  const totalH = data.length * (barH + gap) - gap;
  const fmtMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`);

  return (
    <svg width="100%" height={totalH} viewBox={`0 0 ${VW} ${totalH}`} aria-hidden="true">
      {data.map((d, i) => {
        const bw = Math.max(6, (d.ms / maxMs) * (VW - labelW - valueW - 8));
        const y = i * (barH + gap);
        return (
          <g key={d.name}>
            <text x="0" y={y + barH - 2} fill="var(--muted)" fontSize="11">
              {d.name}
            </text>
            {/* Track */}
            <rect x={labelW} y={y} width={VW - labelW - valueW} height={barH} rx="4" fill="rgba(255,255,255,0.05)" />
            {/* Fill */}
            <rect x={labelW} y={y} width={bw} height={barH} rx="4" fill={color} opacity="0.8" />
            <text x={VW} y={y + barH - 2} textAnchor="end" fill="var(--muted)" fontSize="10">
              {fmtMs(d.ms)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ─── Mini sparkline for stat cards ─────────────────────────────────────────
function Sparkline({ data, color }: { data: number[]; color: string }) {
  const W = 60;
  const H = 24;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const sx = (i: number) => (i / (data.length - 1)) * W;
  const sy = (v: number) => H - ((v - min) / range) * H * 0.8 - H * 0.1;
  const points = data.map((v, i) => `${sx(i)},${sy(v)}`).join(' ');

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.7"
      />
    </svg>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────
export default function AiAnalyticsPage() {
  const [tab, setTab] = useState<Tab>('images');
  const d = DATA[tab];

  const statCards = [
    {
      label: 'Generations Today',
      value: d.totalToday,
      sub: d.delta + ' vs yesterday',
      color: d.color,
    },
    {
      label: 'Success Rate',
      value: d.successRate,
      sub: 'last 24 hours',
      color: '#26d78e',
    },
    {
      label: 'Avg Latency',
      value: d.avgLatency,
      sub: 'per request',
      color: '#f59e0b',
    },
    {
      label: 'Active Models',
      value: String(d.activeModels),
      sub: 'all healthy',
      color: '#ec4899',
    },
  ];

  return (
    <main style={{ maxWidth: 1140, margin: '0 auto', padding: '32px 20px 80px' }}>
      {/* ── Header + Tabs ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--text)' }}>AI Analytics</h1>
          <p style={{ margin: '5px 0 0', fontSize: 13, color: 'var(--muted)' }}>
            Real-time performance across all AI models · April 24, 2026
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 6,
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 999,
            padding: '5px 6px',
          }}
        >
          {TABS.map((t) => {
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                style={{
                  border: 'none',
                  borderRadius: 999,
                  padding: '7px 18px',
                  background: active ? DATA[t.key].color : 'transparent',
                  color: active ? '#0a1120' : 'var(--muted)',
                  fontSize: 13,
                  fontWeight: active ? 700 : 400,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.15s',
                }}
              >
                <span aria-hidden="true">{t.emoji}</span>
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Stat Cards ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
          gap: 14,
          marginBottom: 20,
        }}
      >
        {statCards.map((c) => (
          <div
            key={c.label}
            style={{
              background: 'var(--bg-soft)',
              border: '1px solid var(--line)',
              borderRadius: 16,
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <p
                style={{
                  margin: 0,
                  fontSize: 11,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                {c.label}
              </p>
              <Sparkline data={d.timeSeries} color={c.color} />
            </div>
            <p style={{ margin: 0, fontSize: 30, fontWeight: 700, color: c.color, lineHeight: 1.1 }}>{c.value}</p>
            <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)' }}>{c.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Row 2: Distribution + Top Models + Themes ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
          gap: 14,
          marginBottom: 20,
        }}
      >
        {/* Donut chart */}
        <div
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: '20px',
          }}
        >
          <p style={{ margin: '0 0 16px', fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Model Distribution</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <DonutChart models={d.models} />
            <div style={{ flex: 1 }}>
              {d.models.map((m) => (
                <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: m.color,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--muted)',
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {m.name}
                  </span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)', flexShrink: 0 }}>{m.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Models list with progress bars */}
        <div
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: '20px',
          }}
        >
          <p style={{ margin: '0 0 16px', fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Top Models</p>
          {d.models.map((m) => (
            <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: `${m.color}20`,
                  border: `1px solid ${m.color}40`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 9,
                  fontWeight: 800,
                  color: m.color,
                  flexShrink: 0,
                  letterSpacing: '-0.02em',
                }}
              >
                {m.name.slice(0, 3).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{m.name}</span>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{m.count}</span>
                </div>
                <div
                  style={{
                    height: 5,
                    borderRadius: 3,
                    background: 'rgba(255,255,255,0.07)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${m.pct}%`,
                      height: '100%',
                      background: m.color,
                      borderRadius: 3,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Use Case Themes (like Hashtag Sets in screenshot) */}
        <div
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: '20px',
          }}
        >
          <p style={{ margin: '0 0 16px', fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Use Case Themes</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {d.themes.map((theme, i) => (
              <div
                key={theme}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 12px',
                  background: i === 0 ? `${d.color}16` : 'rgba(255,255,255,0.03)',
                  borderRadius: 9,
                  border: `1px solid ${i === 0 ? d.color + '35' : 'var(--line)'}`,
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    color: i === 0 ? d.color : 'var(--muted)',
                    width: 18,
                    textAlign: 'right',
                    flexShrink: 0,
                    fontWeight: 700,
                  }}
                >
                  #{i + 1}
                </span>
                <span
                  style={{ fontSize: 12, color: i === 0 ? d.color : 'var(--text)', fontWeight: i === 0 ? 600 : 400 }}
                >
                  {theme}
                </span>
                {i === 0 && (
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: 10,
                      color: d.color,
                      background: `${d.color}20`,
                      borderRadius: 999,
                      padding: '2px 7px',
                      fontWeight: 600,
                      flexShrink: 0,
                    }}
                  >
                    TOP
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Row 3: Requests Over Time (full width) ── */}
      <div
        style={{
          background: 'var(--bg-soft)',
          border: '1px solid var(--line)',
          borderRadius: 16,
          padding: '20px 24px',
          marginBottom: 20,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
          <div>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Requests Over Time</p>
            <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--muted)' }}>Last 14 days · daily totals</p>
          </div>
          <span
            style={{
              fontSize: 11,
              color: d.color,
              fontWeight: 600,
              background: `${d.color}18`,
              border: `1px solid ${d.color}40`,
              borderRadius: 999,
              padding: '4px 12px',
            }}
          >
            {d.delta} trend
          </span>
        </div>
        <div style={{ position: 'relative' }}>
          <LineChart data={d.timeSeries} color={d.color} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
            {DAYS.map((day, i) => (
              <span
                key={`item-${i}`}
                style={{
                  fontSize: 9,
                  color: 'var(--muted)',
                  width: `${100 / DAYS.length}%`,
                  textAlign: 'center',
                  display: 'block',
                }}
              >
                {day}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Row 4: Latency + Recent Activity ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 }}>
        {/* Avg Latency bar chart */}
        <div
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: '20px',
          }}
        >
          <p style={{ margin: '0 0 6px', fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Avg Latency by Model</p>
          <p style={{ margin: '0 0 18px', fontSize: 11, color: 'var(--muted)' }}>Average per-request processing time</p>
          <BarChart data={d.perf} color={d.color} />
        </div>

        {/* Recent Activity feed */}
        <div
          style={{
            background: 'var(--bg-soft)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Recent Activity</p>
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 10,
                color: '#26d78e',
                fontWeight: 600,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#26d78e',
                  display: 'inline-block',
                  animation: 'pulse 2s infinite',
                }}
              />
              LIVE
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {d.recentActivity.map((item, i) => (
              <div
                key={`item-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 0',
                  borderBottom: i < d.recentActivity.length - 1 ? '1px solid var(--line)' : 'none',
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: i === 0 ? d.color : 'var(--muted)',
                    flexShrink: 0,
                    opacity: Math.max(0.3, 1 - i * 0.13),
                  }}
                />
                <span
                  style={{
                    fontSize: 12,
                    color: 'var(--text)',
                    opacity: Math.max(0.4, 1 - i * 0.1),
                    lineHeight: 1.4,
                  }}
                >
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Footer note ── */}
      <p
        style={{
          marginTop: 28,
          fontSize: 11,
          color: 'var(--muted)',
          textAlign: 'center',
          opacity: 0.6,
        }}
      >
        Data refreshes every 30s · All models running on AMD Radeon 860M · ComfyUI DirectML
      </p>
    </main>
  );
}
