'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SecurityIssue = {
  severity: string;
  category: string;
  description: string;
  fix: string;
};

type SecuritySeoAuditResponse = {
  analysis_id: string;
  url: string;
  security_seo_score: number;
  https: { enabled: boolean; hsts: boolean; mixed_content_issues: number };
  security_headers: { csp_present: boolean; x_frame_options: string; x_content_type: string };
  cloaking_signals: { user_agent_cloaking: boolean; ip_cloaking: boolean; js_cloaking: boolean };
  spam_signals: { hidden_text: boolean; keyword_stuffing: boolean; doorway_pages: boolean };
  redirect_health: { chains_detected: number; chain_details: string[] };
  issues: SecurityIssue[];
  quick_wins: string[];
  recommended_tools: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: ok ? '#22c55e' : '#ef4444',
        marginRight: 5,
      }}
    />
  );
}

export default function SecuritySeoPage() {
  const [url, setUrl] = useState('https://example.com');
  const [checkCloaking, setCheckCloaking] = useState(true);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<SecuritySeoAuditResponse | null>(null);

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box' as const,
  };

  async function runAudit() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<SecuritySeoAuditResponse>(
        '/seo-platform/security/audit',
        'POST',
        { url: url.trim(), check_cloaking: checkCloaking, notes: notes.trim() },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Security SEO audit failed.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <Link href={'/seo' as Route} style={{ color: 'var(--brand)', textDecoration: 'none', fontSize: 13 }}>
          ← Back to SEO Platform
        </Link>
        <h1 style={{ marginTop: 12, marginBottom: 6 }}>Security & SEO Health Monitor</h1>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 18 }}>
          Audit security posture, spam signals, cloaking detection, and SEO integrity.
        </p>

        <section style={{ ...card, marginBottom: 14, display: 'grid', gap: 10 }}>
          <div>
            <label htmlFor="sec-url" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              URL
            </label>
            <input id="sec-url" value={url} onChange={(e) => setUrl(e.target.value)} style={input} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              id="sec-cloaking"
              type="checkbox"
              checked={checkCloaking}
              onChange={(e) => setCheckCloaking(e.target.checked)}
            />
            <label htmlFor="sec-cloaking" style={{ fontSize: 13 }}>
              Include cloaking detection
            </label>
          </div>
          <div>
            <label htmlFor="sec-notes" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Notes (optional)
            </label>
            <input
              id="sec-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={input}
              placeholder="Known issues or focus areas..."
            />
          </div>
          <button
            onClick={runAudit}
            disabled={loading}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Running Audit…' : 'Run Security & SEO Audit'}
          </button>
          {error && <div style={{ color: '#fca5a5', fontSize: 13 }}>{error}</div>}
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
            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 15 }}>
                Security SEO Score: {result.security_seo_score}/100
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
                <div style={card}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>HTTPS</div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.https.enabled} />
                    HTTPS Enabled
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.https.hsts} />
                    HSTS
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.https.mixed_content_issues === 0} />
                    Mixed Content ({result.https.mixed_content_issues} issues)
                  </div>
                </div>
                <div style={card}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Security Headers</div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.security_headers.csp_present} />
                    Content-Security-Policy
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.security_headers.x_frame_options !== 'Missing'} />
                    X-Frame-Options: {result.security_headers.x_frame_options}
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={result.security_headers.x_content_type === 'nosniff'} />
                    X-Content-Type: {result.security_headers.x_content_type}
                  </div>
                </div>
                <div style={card}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Cloaking Signals</div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.cloaking_signals.user_agent_cloaking} />
                    User-Agent Cloaking
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.cloaking_signals.ip_cloaking} />
                    IP Cloaking
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.cloaking_signals.js_cloaking} />
                    JS Cloaking
                  </div>
                </div>
                <div style={card}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Spam Signals</div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.spam_signals.hidden_text} />
                    Hidden Text
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.spam_signals.keyword_stuffing} />
                    Keyword Stuffing
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <StatusDot ok={!result.spam_signals.doorway_pages} />
                    Doorway Pages
                  </div>
                </div>
              </div>
            </section>

            {result.redirect_health.chains_detected > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>
                  Redirect Chains ({result.redirect_health.chains_detected})
                </h2>
                {result.redirect_health.chain_details.map((chain, i) => (
                  <div key={`item-${i}`} style={{ fontSize: 13, marginBottom: 4, color: '#fca5a5' }}>
                    {chain}
                  </div>
                ))}
              </section>
            )}

            {result.issues.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 15 }}>Issues ({result.issues.length})</h2>
                <div style={{ display: 'grid', gap: 8 }}>
                  {result.issues.map((issue, i) => (
                    <div
                      key={`item-${i}`}
                      style={{ ...card, borderLeft: `4px solid ${SEVERITY_COLORS[issue.severity] ?? '#6366f1'}` }}
                    >
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <span
                          style={{ fontSize: 10, fontWeight: 700, color: SEVERITY_COLORS[issue.severity] ?? '#6366f1' }}
                        >
                          {issue.severity.toUpperCase()}
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            background: '#eef0f4',
                            color: 'var(--muted)',
                            borderRadius: 4,
                            padding: '1px 5px',
                          }}
                        >
                          {issue.category}
                        </span>
                      </div>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{issue.description}</div>
                      <div style={{ fontSize: 12, color: '#86efac' }}>Fix: {issue.fix}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {result.quick_wins.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>Quick Wins</h2>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {result.quick_wins.map((w, i) => (
                    <li key={`item-${i}`} style={{ fontSize: 13, marginBottom: 4 }}>
                      {w}
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
