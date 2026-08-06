'use client';

import { useMemo } from 'react';

type ExecutiveKpi = {
  label: string;
  value: string;
  delta?: string;
  trend?: 'up' | 'down' | 'flat';
};

type ExecutiveBar = {
  label: string;
  value: number;
};

type ExecutiveRing = {
  label: string;
  value: number;
  color: string;
};

type Props = {
  title: string;
  subtitle: string;
  kpis: ExecutiveKpi[];
  bars: ExecutiveBar[];
  line: number[];
  ring: ExecutiveRing[];
};

function trendColor(trend: ExecutiveKpi['trend']): string {
  if (trend === 'up') return '#22c55e';
  if (trend === 'down') return '#ef4444';
  return 'var(--muted)';
}

function linePath(values: number[], width: number, height: number, pad: number): string {
  if (!values.length) return '';
  const max = Math.max(1, ...values);
  const min = Math.min(...values);
  const range = Math.max(1, max - min);
  const step = values.length > 1 ? (width - pad * 2) / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = pad + index * step;
      const y = height - pad - ((value - min) / range) * (height - pad * 2);
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

function barGradientByIndex(index: number): string {
  if (index % 3 === 0) return 'linear-gradient(90deg, #60a5fa, #2563eb)';
  if (index % 3 === 1) return 'linear-gradient(90deg, #34d399, #059669)';
  return 'linear-gradient(90deg, #fb7185, #e11d48)';
}

function ringArc(segments: ExecutiveRing[]): string[] {
  const total = Math.max(
    1,
    segments.reduce((sum, segment) => sum + Math.max(0, segment.value), 0)
  );
  let cursor = -Math.PI / 2;
  const result: string[] = [];
  const r = 66;
  const cx = 90;
  const cy = 90;

  for (const segment of segments) {
    const ratio = Math.max(0, segment.value) / total;
    const sweep = ratio * Math.PI * 2;
    const startX = (cx + r * Math.cos(cursor)).toFixed(4);
    const startY = (cy + r * Math.sin(cursor)).toFixed(4);
    const endX = (cx + r * Math.cos(cursor + sweep)).toFixed(4);
    const endY = (cy + r * Math.sin(cursor + sweep)).toFixed(4);
    const largeArc = sweep > Math.PI ? 1 : 0;
    result.push(`M ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${endX} ${endY}`);
    cursor += sweep;
  }

  return result;
}

export default function AnalyticsExecutiveBoard({ title, subtitle, kpis, bars, line, ring }: Readonly<Props>) {
  const normalizedBars = useMemo(() => {
    const clean = bars.filter((item) => Number.isFinite(item.value) && item.value >= 0).slice(0, 4);
    const max = Math.max(1, ...clean.map((item) => item.value));
    return clean.map((item) => ({ ...item, pct: Math.round((item.value / max) * 100) }));
  }, [bars]);

  const ringPaths = useMemo(() => ringArc(ring.filter((item) => item.value > 0)), [ring]);

  return (
    <section
      style={{
        marginTop: 18,
        marginBottom: 18,
        borderRadius: 20,
        border: '1px solid var(--line)',
        background: 'linear-gradient(160deg, #dbeafe 0%, #eff6ff 62%, #f8fafc 100%)',
        padding: 18,
        boxShadow: '0 14px 24px rgba(2, 6, 23, 0.08)',
      }}
    >
      <div style={{ marginBottom: 10 }}>
        <h2 style={{ margin: 0, fontSize: 22, color: '#0f172a' }}>{title}</h2>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#334155' }}>{subtitle}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <article
            style={{
              background: 'rgba(255,255,255,0.92)',
              borderRadius: 12,
              padding: 12,
              boxShadow: '0 8px 18px rgba(15, 23, 42, 0.12)',
            }}
          >
            <div style={{ fontSize: 12, color: '#334155', marginBottom: 8 }}>Content Distribution</div>
            <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 8, alignItems: 'center' }}>
              <svg viewBox="0 0 180 180" style={{ width: 170, height: 160 }} aria-label="Distribution ring chart">
                <circle cx="90" cy="90" r="66" stroke="#e2e8f0" strokeWidth="18" fill="none" />
                {ringPaths.map((path, index) => (
                  <path
                    key={`ring-${ring[index]?.label || index}`}
                    d={path}
                    stroke={ring[index]?.color || '#0ea5e9'}
                    strokeWidth="18"
                    fill="none"
                    strokeLinecap="round"
                  />
                ))}
                <circle cx="90" cy="90" r="44" fill="#ffffff" />
              </svg>
              <div style={{ display: 'grid', gap: 6 }}>
                {ring.slice(0, 4).map((segment) => (
                  <div
                    key={segment.label}
                    style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#0f172a' }}
                  >
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 2,
                        background: segment.color,
                        display: 'inline-block',
                      }}
                    />
                    <span>{segment.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </article>

          <article
            style={{
              background: 'rgba(255,255,255,0.92)',
              borderRadius: 12,
              padding: 12,
              boxShadow: '0 8px 18px rgba(15, 23, 42, 0.12)',
            }}
          >
            <div style={{ fontSize: 12, color: '#334155', marginBottom: 8 }}>Performance Breakdown</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {normalizedBars.map((item, index) => (
                <div key={item.label}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: 11,
                      color: '#334155',
                      marginBottom: 4,
                    }}
                  >
                    <span>{item.label}</span>
                    <span>{item.value}</span>
                  </div>
                  <div style={{ height: 9, borderRadius: 999, background: '#e2e8f0' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.max(6, item.pct)}%`,
                        borderRadius: 999,
                        background: barGradientByIndex(index),
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article
            style={{
              background: 'rgba(255,255,255,0.92)',
              borderRadius: 12,
              padding: 12,
              boxShadow: '0 8px 18px rgba(15, 23, 42, 0.12)',
              gridColumn: '1 / span 2',
            }}
          >
            <div style={{ fontSize: 12, color: '#334155', marginBottom: 8 }}>Post Performance</div>
            <svg viewBox="0 0 520 130" style={{ width: '100%', height: 120 }} aria-label="Trend line chart">
              <path
                d={linePath(line, 520, 130, 12)}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
              />
            </svg>
          </article>
        </div>

        <div style={{ display: 'grid', gap: 10 }}>
          {kpis.map((kpi) => (
            <article
              key={kpi.label}
              style={{
                background: 'rgba(255,255,255,0.92)',
                borderRadius: 12,
                padding: 12,
                boxShadow: '0 8px 18px rgba(15, 23, 42, 0.12)',
                display: 'grid',
                gap: 6,
              }}
            >
              <div style={{ fontSize: 12, color: '#475569' }}>{kpi.label}</div>
              <div style={{ fontSize: 30, fontWeight: 800, color: '#020617', lineHeight: 1 }}>{kpi.value}</div>
              {kpi.delta ? (
                <div style={{ fontSize: 12, color: trendColor(kpi.trend), fontWeight: 700 }}>{kpi.delta}</div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
