'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type PlaybookItem = {
  name?: string;
  goal?: string;
  owner?: string;
  cadence?: string;
  status?: string;
  expected_lift_pct?: number;
};

type TimelineItem = {
  week?: number;
  focus?: string;
  deliverables?: string[];
};

type GrowthPlaybooksResult = {
  automation_readiness_score?: number;
  playbooks?: PlaybookItem[];
  execution_timeline?: TimelineItem[];
  blocked_dependencies?: string[];
  next_best_actions?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function GrowthPlaybooksPage() {
  const [objective, setObjective] = useState('Increase qualified pipeline from organic and AI-assisted demand');
  const [domain, setDomain] = useState('');
  const [targetChannels, setTargetChannels] = useState('search, social, email');
  const [weeklyCapacityHours, setWeeklyCapacityHours] = useState(20);
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<GrowthPlaybooksResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!objective.trim()) {
      setError('Objective is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<GrowthPlaybooksResult>(
        '/seo-platform/growth-playbooks/analyze',
        'POST',
        {
          objective: objective.trim(),
          domain: domain.trim(),
          target_channels: targetChannels
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          weekly_capacity_hours: weeklyCapacityHours,
          notes,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(IS_STRICT_NO_MOCK_MODE ? 'Live LLM backend is unavailable in strict no-mock mode.' : 'Live LLM backend is unavailable in fail-closed mode.');
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Growth playbooks analysis failed');
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
        <h1 style={{ marginTop: 0 }}>Growth Playbooks Automation</h1>
        <p style={{ color: 'var(--muted)' }}>Automated growth playbook execution and measurement.</p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Objective</label>
          <input
            style={input}
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Primary growth objective"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Domain (optional)</label>
          <input style={input} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Target Channels</label>
          <input
            style={input}
            value={targetChannels}
            onChange={(e) => setTargetChannels(e.target.value)}
            placeholder="search, social, email"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Weekly Capacity (hours)
          </label>
          <input
            style={input}
            type="number"
            min={1}
            max={200}
            value={weeklyCapacityHours}
            onChange={(e) => setWeeklyCapacityHours(Number(e.target.value || 20))}
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Constraints, owners, operating model"
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
            {loading ? 'Building playbooks...' : 'Generate Growth Playbooks'}
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Automation Readiness</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.automation_readiness_score ?? '--'}</div>
              </div>
            </section>

            {(result.playbooks ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Playbooks</h3>
                {(result.playbooks ?? []).map((item, index) => (
                  <div
                    key={`playbook-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.playbooks ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.name ?? '--'} · {item.status ?? 'planned'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.goal ?? ''}</div>
                    <div style={{ fontSize: 12 }}>
                      Owner: {item.owner ?? 'unassigned'} · Cadence: {item.cadence ?? 'weekly'} · Lift:{' '}
                      {item.expected_lift_pct ?? 0}%
                    </div>
                  </div>
                ))}
              </section>
            )}

            {(result.execution_timeline ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Execution Timeline</h3>
                {(result.execution_timeline ?? []).map((item, index) => (
                  <div
                    key={`timeline-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.execution_timeline ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>Week {item.week ?? index + 1}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.focus ?? ''}</div>
                    <div style={{ fontSize: 12 }}>{(item.deliverables ?? []).join(' • ')}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.blocked_dependencies ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Blocked Dependencies</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.blocked_dependencies ?? []).map((item, index) => (
                    <li key={`dep-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.next_best_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Next Best Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.next_best_actions ?? []).map((item, index) => (
                    <li key={`next-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
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
