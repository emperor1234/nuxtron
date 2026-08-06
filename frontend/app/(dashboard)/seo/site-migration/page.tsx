'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type CriticalIssue = {
  type?: string;
  severity?: string;
  detail?: string;
  fix?: string;
};

type MappingRow = {
  legacy_url?: string;
  target_url?: string;
  status?: string;
};

type MigrationResult = {
  migration_readiness_score?: number;
  redirect_coverage_pct?: number;
  critical_issues?: CriticalIssue[];
  url_mapping_preview?: MappingRow[];
  monitoring_plan?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function SiteMigrationPage() {
  const [sourceDomain, setSourceDomain] = useState('');
  const [targetDomain, setTargetDomain] = useState('');
  const [sampleUrls, setSampleUrls] = useState('/, /pricing, /blog/seo-checklist, /features');
  const [launchWindow, setLaunchWindow] = useState('Q3 2026');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<MigrationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!sourceDomain.trim() || !targetDomain.trim()) {
      setError('Source and target domains are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<MigrationResult>(
        '/seo-platform/site-migration/analyze',
        'POST',
        {
          source_domain: sourceDomain.trim(),
          target_domain: targetDomain.trim(),
          sample_urls: sampleUrls
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          launch_window: launchWindow,
          notes,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Site migration analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Site Migration SEO Manager</h1>
        <p style={{ color: 'var(--muted)' }}>
          SEO-safe migration planning, redirect validation, and post-launch risk monitoring.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Source Domain</label>
              <input
                style={input}
                value={sourceDomain}
                onChange={(e) => setSourceDomain(e.target.value)}
                placeholder="old-domain.com"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Target Domain</label>
              <input
                style={input}
                value={targetDomain}
                onChange={(e) => setTargetDomain(e.target.value)}
                placeholder="new-domain.com"
              />
            </div>
          </div>

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Sample URLs (comma-separated)
          </label>
          <input
            style={input}
            value={sampleUrls}
            onChange={(e) => setSampleUrls(e.target.value)}
            placeholder="/, /pricing, /blog/seo-checklist"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Launch Window</label>
          <input
            style={input}
            value={launchWindow}
            onChange={(e) => setLaunchWindow(e.target.value)}
            placeholder="Q3 2026"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Constraints, migration sequence, rollback requirements"
          />

          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Analyzing migration...' : 'Analyze Site Migration'}
          </button>
        </section>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)', color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)' }}>
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.12)', color: '#38bdf8' }}>Cached result</span>
                )}
              </div>
            )}
            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Migration Readiness</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.migration_readiness_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Redirect Coverage</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.redirect_coverage_pct ?? '--'}%</div>
              </div>
            </section>

            {(result.critical_issues ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Critical Issues</h3>
                {(result.critical_issues ?? []).map((issue, index) => (
                  <div
                    key={`issue-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.critical_issues ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {issue.type ?? 'issue'} · {issue.severity ?? 'info'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{issue.detail ?? ''}</div>
                    <div style={{ fontSize: 12, color: 'var(--brand)' }}>{issue.fix ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.url_mapping_preview ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>URL Mapping Preview</h3>
                {(result.url_mapping_preview ?? []).map((row, index) => (
                  <div
                    key={`map-${index}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr auto',
                      gap: 8,
                      fontSize: 12,
                      padding: '6px 0',
                      borderBottom:
                        index < (result.url_mapping_preview ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <span style={{ color: 'var(--muted)' }}>{row.legacy_url ?? ''}</span>
                    <span>{row.target_url ?? ''}</span>
                    <span style={{ color: 'var(--brand)' }}>{row.status ?? 'mapped'}</span>
                  </div>
                ))}
              </section>
            )}

            {(result.monitoring_plan ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Post-Launch Monitoring Plan</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.monitoring_plan ?? []).map((step, index) => (
                    <li key={`step-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {step}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
