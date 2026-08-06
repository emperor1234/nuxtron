'use client';

import { useEffect, useMemo, useState } from 'react';

type ApiMarker = {
  name: string;
  durationMs: number;
};

type TelemetrySample = {
  recordedAt: number;
  ttfbMs: number | null;
  markers: ApiMarker[];
};

type Props = {
  routeName: string;
  apiMarkers: ApiMarker[];
};

const HISTORY_LIMIT = 20;

function storageKey(routeName: string) {
  return `nuxtron.routeTelemetry.${routeName}`;
}

function loadHistory(routeName: string): TelemetrySample[] {
  if (typeof window === 'undefined') return [];
  const raw = window.localStorage.getItem(storageKey(routeName));
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as TelemetrySample[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => typeof item?.recordedAt === 'number').slice(-HISTORY_LIMIT);
  } catch {
    return [];
  }
}

function saveHistory(routeName: string, samples: TelemetrySample[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(storageKey(routeName), JSON.stringify(samples.slice(-HISTORY_LIMIT)));
}

function formatDuration(durationMs: number) {
  if (!Number.isFinite(durationMs)) return 'n/a';
  return `${Math.max(0, Math.round(durationMs))} ms`;
}

function formatTime(unixMs: number) {
  const date = new Date(unixMs);
  if (Number.isNaN(date.getTime())) return 'n/a';
  return date.toLocaleTimeString();
}

function normalizeBaselineSamples(samples: unknown): TelemetrySample[] {
  if (!Array.isArray(samples)) return [];

  return samples
    .filter(
      (item) => typeof item === 'object' && item !== null && typeof (item as TelemetrySample).recordedAt === 'number'
    )
    .map((sample) => {
      const typedSample = sample as TelemetrySample;
      const markers = Array.isArray(typedSample.markers)
        ? typedSample.markers
            .filter((marker) => typeof marker?.name === 'string' && typeof marker?.durationMs === 'number')
            .map((marker) => ({ name: marker.name, durationMs: marker.durationMs }))
        : [];

      return {
        recordedAt: Number(typedSample.recordedAt),
        ttfbMs: typeof typedSample.ttfbMs === 'number' ? typedSample.ttfbMs : null,
        markers,
      };
    })
    .slice(-HISTORY_LIMIT);
}

export default function RoutePerformance({ routeName, apiMarkers }: Readonly<Props>) {
  const [ttfbMs, setTtfbMs] = useState<number | null>(null);
  const [history, setHistory] = useState<TelemetrySample[]>([]);
  const [baselineHistory, setBaselineHistory] = useState<TelemetrySample[] | null>(null);

  const markerSignature = useMemo(() => {
    return apiMarkers
      .map((marker) => `${marker.name}:${Math.round(marker.durationMs)}`)
      .sort((a, b) => a.localeCompare(b))
      .join('|');
  }, [apiMarkers]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('performance' in window)) return;

    const entries = performance.getEntriesByType('navigation');
    if (!entries.length) return;

    const nav = entries[0] as PerformanceNavigationTiming;
    if (!nav || !Number.isFinite(nav.responseStart) || !Number.isFinite(nav.requestStart)) return;

    const measured = nav.responseStart - nav.requestStart;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTtfbMs(measured >= 0 ? measured : null);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory(loadHistory(routeName));
  }, [routeName]);

  useEffect(() => {
    if (ttfbMs === null) return;
    const sample: TelemetrySample = {
      recordedAt: Date.now(),
      ttfbMs,
      markers: apiMarkers,
    };
    const current = loadHistory(routeName);
    const last = current[current.length - 1];
    const isDuplicate =
      !!last && last.ttfbMs === sample.ttfbMs && JSON.stringify(last.markers) === JSON.stringify(sample.markers);

    if (isDuplicate) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHistory(current);
      return;
    }

    const next = [...current, sample].slice(-HISTORY_LIMIT);
    saveHistory(routeName, next);
    setHistory(next);
  }, [routeName, markerSignature, ttfbMs, apiMarkers]);

  const slowestApi = useMemo(() => {
    if (!apiMarkers.length) return null;
    return [...apiMarkers].sort((a, b) => b.durationMs - a.durationMs)[0];
  }, [apiMarkers]);

  const avgTtfb = useMemo(() => {
    const values = history
      .map((sample) => sample.ttfbMs)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [history]);

  const baselineAvgTtfb = useMemo(() => {
    if (!baselineHistory?.length) return null;
    const values = baselineHistory
      .map((sample) => sample.ttfbMs)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [baselineHistory]);

  const avgSlowestApi = useMemo(() => {
    const values = history
      .map((sample) => sample.markers.reduce((max, marker) => Math.max(max, marker.durationMs), 0))
      .filter((value) => Number.isFinite(value) && value > 0);
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [history]);

  const baselineAvgSlowestApi = useMemo(() => {
    if (!baselineHistory?.length) return null;
    const values = baselineHistory
      .map((sample) => sample.markers.reduce((max, marker) => Math.max(max, marker.durationMs), 0))
      .filter((value) => Number.isFinite(value) && value > 0);
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [baselineHistory]);

  const ttfbDelta = useMemo(() => {
    if (avgTtfb === null || baselineAvgTtfb === null) return null;
    return avgTtfb - baselineAvgTtfb;
  }, [avgTtfb, baselineAvgTtfb]);

  const slowestApiDelta = useMemo(() => {
    if (avgSlowestApi === null || baselineAvgSlowestApi === null) return null;
    return avgSlowestApi - baselineAvgSlowestApi;
  }, [avgSlowestApi, baselineAvgSlowestApi]);

  const recentHistory = useMemo(() => [...history].reverse().slice(0, 8), [history]);

  const exportHistory = () => {
    if (!history.length) return;

    const payload = {
      route: routeName,
      exportedAt: new Date().toISOString(),
      retainedSamples: history.length,
      maxSamples: HISTORY_LIMIT,
      samples: history,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `nuxtron-telemetry-${routeName}-${Date.now()}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const importHistory = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || '{}')) as {
          route?: string;
          samples?: TelemetrySample[];
        };
        const normalized = normalizeBaselineSamples(parsed.samples);

        if (!normalized.length) return;
        setBaselineHistory(normalized);
      } catch {
        // no-op on malformed files
      }
    };
    reader.readAsText(file);
  };

  const clearBaseline = () => {
    setBaselineHistory(null);
  };

  const deltaColor = (delta: number | null) => {
    if (delta === null) return 'var(--text)';
    if (delta < 0) return '#22c55e';
    if (delta > 0) return '#ef4444';
    return 'var(--text)';
  };

  const deltaTrend = (delta: number | null) => {
    if (delta === null) return '';
    if (delta < 0) return 'faster';
    if (delta > 0) return 'slower';
    return 'no change';
  };

  const deltaArrow = (delta: number | null) => {
    if (delta === null) return '•';
    if (delta < 0) return '▼';
    if (delta > 0) return '▲';
    return '■';
  };

  const deltaLabel = (delta: number | null) => {
    if (delta === null) return 'n/a';
    const rounded = Math.round(delta);
    const sign = rounded > 0 ? '+' : '';
    return `${sign}${rounded} ms`;
  };

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <h3 style={{ marginBottom: 0 }}>Performance Telemetry</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <label
            style={{
              border: '1px solid var(--line)',
              borderRadius: 8,
              background: 'transparent',
              color: 'var(--text)',
              padding: '6px 10px',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Import JSON
            <input type="file" accept="application/json" onChange={importHistory} style={{ display: 'none' }} />
          </label>
          <button
            type="button"
            onClick={exportHistory}
            disabled={!history.length}
            style={{
              border: '1px solid var(--line)',
              borderRadius: 8,
              background: 'transparent',
              color: 'var(--text)',
              padding: '6px 10px',
              fontSize: 12,
              cursor: history.length ? 'pointer' : 'not-allowed',
              opacity: history.length ? 1 : 0.5,
            }}
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={clearBaseline}
            disabled={!baselineHistory?.length}
            style={{
              border: '1px solid var(--line)',
              borderRadius: 8,
              background: 'transparent',
              color: 'var(--text)',
              padding: '6px 10px',
              fontSize: 12,
              cursor: baselineHistory?.length ? 'pointer' : 'not-allowed',
              opacity: baselineHistory?.length ? 1 : 0.5,
            }}
          >
            Clear Baseline
          </button>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        Route: {routeName}
      </p>
      <div className="grid dashboard-kpis">
        <article className="card kpi-card">
          <p className="kpi-label">Route TTFB</p>
          <h3>{ttfbMs === null ? 'n/a' : formatDuration(ttfbMs)}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Slowest API Marker</p>
          <h3>{slowestApi ? `${slowestApi.name} (${formatDuration(slowestApi.durationMs)})` : 'n/a'}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Avg Route TTFB (history)</p>
          <h3>{avgTtfb === null ? 'n/a' : formatDuration(avgTtfb)}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Avg Slowest API (history)</p>
          <h3>{avgSlowestApi === null ? 'n/a' : formatDuration(avgSlowestApi)}</h3>
        </article>
      </div>
      {!!apiMarkers.length && (
        <div style={{ marginTop: 10 }}>
          {apiMarkers.map((marker) => (
            <div
              key={marker.name}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 10,
                borderBottom: '1px solid var(--line)',
                padding: '6px 0',
                fontSize: 12,
              }}
            >
              <span>{marker.name}</span>
              <strong>{formatDuration(marker.durationMs)}</strong>
            </div>
          ))}
        </div>
      )}

      {!!recentHistory.length && (
        <div style={{ marginTop: 14 }}>
          <p className="muted" style={{ marginBottom: 6 }}>
            Recent samples ({history.length}/{HISTORY_LIMIT})
          </p>
          {recentHistory.map((sample) => {
            const sampleSlowest = sample.markers.reduce((max, marker) => Math.max(max, marker.durationMs), 0);
            return (
              <div
                key={sample.recordedAt}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 10,
                  borderBottom: '1px solid var(--line)',
                  padding: '6px 0',
                  fontSize: 12,
                }}
              >
                <span>{formatTime(sample.recordedAt)}</span>
                <span>TTFB {sample.ttfbMs === null ? 'n/a' : formatDuration(sample.ttfbMs)}</span>
                <strong>Slowest API {sampleSlowest > 0 ? formatDuration(sampleSlowest) : 'n/a'}</strong>
              </div>
            );
          })}
        </div>
      )}

      {!!baselineHistory?.length && (
        <div style={{ marginTop: 14 }}>
          <p className="muted" style={{ marginBottom: 6 }}>
            Baseline comparison ({baselineHistory.length} imported samples)
          </p>
          <div className="grid dashboard-kpis">
            <article className="card kpi-card">
              <p className="kpi-label">Baseline Avg TTFB</p>
              <h3>{baselineAvgTtfb === null ? 'n/a' : formatDuration(baselineAvgTtfb)}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Current vs Baseline TTFB</p>
              <h3 style={{ color: deltaColor(ttfbDelta) }}>
                {deltaArrow(ttfbDelta)} {deltaLabel(ttfbDelta)} {deltaTrend(ttfbDelta)}
              </h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Baseline Avg Slowest API</p>
              <h3>{baselineAvgSlowestApi === null ? 'n/a' : formatDuration(baselineAvgSlowestApi)}</h3>
            </article>
            <article className="card kpi-card">
              <p className="kpi-label">Current vs Baseline Slowest API</p>
              <h3 style={{ color: deltaColor(slowestApiDelta) }}>
                {deltaArrow(slowestApiDelta)} {deltaLabel(slowestApiDelta)} {deltaTrend(slowestApiDelta)}
              </h3>
            </article>
          </div>
        </div>
      )}
    </section>
  );
}
