'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type AnalysisRecord = {
  id: string;
  module: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: string;
};

type AnalysesResponse = {
  analyses: AnalysisRecord[];
  total: number;
  persistence?: string;
};

export default function SEOHistoryPage() {
  const [moduleFilter, setModuleFilter] = useState('');
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [selected, setSelected] = useState<AnalysisRecord | null>(null);
  const [persistence, setPersistence] = useState('unknown');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const uniqueModules = useMemo(() => {
    return Array.from(new Set(analyses.map((a) => a.module))).sort((a, b) => a.localeCompare(b));
  }, [analyses]);

  async function loadAnalyses(currentFilter: string) {
    setLoading(true);
    setError('');
    try {
      const qs = currentFilter ? `?module=${encodeURIComponent(currentFilter)}&limit=100` : '?limit=100';
      const data = await apiGet<AnalysesResponse>(`/seo-platform/analyses${qs}`, DEFAULT_TENANT_ID);
      const items = Array.isArray(data.analyses) ? data.analyses : [];
      setAnalyses(items);
      setPersistence(typeof data.persistence === 'string' ? data.persistence : 'unknown');
      if (items.length === 0) {
        setSelected(null);
      } else if (!selected || !items.some((item) => item.id === selected.id)) {
        setSelected(items[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analyses');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadAnalyses(moduleFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleFilter]);

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800 }}>SEO Analysis History</h1>
          <p style={{ color: 'var(--muted)', marginTop: 6 }}>
            Production history viewer for all SEO modules. Persistence mode: <strong>{persistence}</strong>
          </p>
        </div>

        <section
          style={{ ...card, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}
        >
          <label style={{ fontSize: 12, fontWeight: 700 }} htmlFor="module-filter">
            Module
          </label>
          <select
            id="module-filter"
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
            style={{
              minWidth: 220,
              padding: '8px 10px',
              borderRadius: 8,
              border: '1px solid var(--line)',
              background: 'var(--bg)',
              color: 'var(--text)',
            }}
          >
            <option value="">All modules</option>
            {uniqueModules.map((moduleName) => (
              <option key={moduleName} value={moduleName}>
                {moduleName}
              </option>
            ))}
          </select>
          <button
            onClick={() => void loadAnalyses(moduleFilter)}
            disabled={loading}
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>{analyses.length} records</span>
        </section>

        {error && (
          <section style={{ ...card, borderColor: '#ef4444', color: '#fca5a5', marginBottom: 12 }}>{error}</section>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
          <section style={{ ...card, maxHeight: '70vh', overflowY: 'auto' }}>
            <h2 style={{ marginTop: 0, fontSize: 14 }}>Analyses</h2>
            {analyses.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: 12, margin: 0 }}>
                No analyses found for the selected filter.
              </p>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {analyses.map((item) => {
                  const active = selected?.id === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setSelected(item)}
                      style={{
                        textAlign: 'left',
                        padding: 10,
                        borderRadius: 8,
                        border: active ? '1px solid var(--brand)' : '1px solid var(--line)',
                        background: active ? 'rgba(27,199,255,0.08)' : 'var(--bg)',
                        color: 'var(--text)',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 3 }}>{item.module}</div>
                      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{item.id}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>

          <section style={{ ...card, maxHeight: '70vh', overflowY: 'auto' }}>
            <h2 style={{ marginTop: 0, fontSize: 14 }}>Analysis Details</h2>
            {!selected ? (
              <p style={{ color: 'var(--muted)', fontSize: 12, margin: 0 }}>
                Select an analysis record to inspect payload and result.
              </p>
            ) : (
              <>
                <div style={{ fontSize: 12, marginBottom: 8 }}>
                  <strong>Module:</strong> {selected.module}
                </div>
                <div style={{ fontSize: 12, marginBottom: 8 }}>
                  <strong>Created:</strong> {new Date(selected.created_at).toLocaleString()}
                </div>
                <div style={{ fontSize: 12, marginBottom: 8 }}>
                  <strong>ID:</strong> {selected.id}
                </div>
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Payload</div>
                  <pre
                    style={{
                      margin: 0,
                      fontSize: 11,
                      color: 'var(--muted)',
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: 10,
                      overflowX: 'auto',
                    }}
                  >
                    {JSON.stringify(selected.payload, null, 2)}
                  </pre>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Result</div>
                  <pre
                    style={{
                      margin: 0,
                      fontSize: 11,
                      color: 'var(--muted)',
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: 10,
                      overflowX: 'auto',
                    }}
                  >
                    {JSON.stringify(selected.result, null, 2)}
                  </pre>
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
