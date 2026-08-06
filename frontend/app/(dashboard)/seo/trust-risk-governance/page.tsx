'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type RiskItem = {
  risk?: string;
  severity?: string;
  owner?: string;
  mitigation?: string;
};

type ControlGap = {
  control?: string;
  gap?: string;
  priority?: string;
};

type GovernanceResult = {
  governance_score?: number;
  policy_compliance_pct?: number;
  control_coverage_pct?: number;
  risk_register?: RiskItem[];
  control_gaps?: ControlGap[];
  audit_actions?: string[];
  incident_prevention_plan?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function TrustRiskGovernancePage() {
  const [domain, setDomain] = useState('');
  const [policyScope, setPolicyScope] = useState('seo-and-ai');
  const [controls, setControls] = useState('content_policy, prompt_review, rbac, audit_log');
  const [incidents, setIncidents] = useState(0);
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<GovernanceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!domain.trim()) {
      setError('Domain is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<GovernanceResult>(
        '/seo-platform/trust-risk-governance/analyze',
        'POST',
        {
          domain: domain.trim(),
          policy_scope: policyScope,
          controls: controls
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          incidents_last_90d: incidents,
          notes,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(IS_STRICT_NO_MOCK_MODE ? 'Live LLM backend is unavailable in strict no-mock mode.' : 'Live LLM backend is unavailable in fail-closed mode.');
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Trust and risk governance analysis failed');
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
        <h1 style={{ marginTop: 0 }}>Trust & Risk Governance</h1>
        <p style={{ color: 'var(--muted)' }}>Policy, governance, and risk controls for SEO and AI execution.</p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Policy Scope</label>
          <input
            style={input}
            value={policyScope}
            onChange={(e) => setPolicyScope(e.target.value)}
            placeholder="seo-and-ai"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Controls (comma-separated)
          </label>
          <input
            style={input}
            value={controls}
            onChange={(e) => setControls(e.target.value)}
            placeholder="content_policy, prompt_review, rbac"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Incidents Last 90 Days
          </label>
          <input
            style={input}
            type="number"
            min={0}
            max={1000}
            value={incidents}
            onChange={(e) => setIncidents(Number(e.target.value || 0))}
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Known risks, controls in place, audit constraints"
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
            {loading ? 'Analyzing governance...' : 'Analyze Trust & Risk'}
          </button>
        </section>

        {result && (
          <>
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Governance Score</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.governance_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Policy Compliance</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.policy_compliance_pct ?? '--'}%</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Control Coverage</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.control_coverage_pct ?? '--'}%</div>
              </div>
            </section>

            {(result.risk_register ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Risk Register</h3>
                {(result.risk_register ?? []).map((item, index) => (
                  <div
                    key={`risk-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.risk_register ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.risk ?? '--'} · {item.severity ?? 'unknown'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>Owner: {item.owner ?? 'unassigned'}</div>
                    <div style={{ fontSize: 12, color: 'var(--brand)' }}>{item.mitigation ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.control_gaps ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Control Gaps</h3>
                {(result.control_gaps ?? []).map((item, index) => (
                  <div
                    key={`gap-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.control_gaps ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.control ?? '--'} · {item.priority ?? 'medium'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.gap ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.audit_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Audit Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.audit_actions ?? []).map((item, index) => (
                    <li key={`audit-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.incident_prevention_plan ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Incident Prevention Plan</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.incident_prevention_plan ?? []).map((item, index) => (
                    <li key={`plan-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
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
