'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type PlanMode = 'standard' | 'all-modules';

type PlannerStep = {
  phase: string;
  module: string;
  action: string;
  path: string;
};

type AllModulesStep = {
  step: number;
  module_key: string;
  module_name: string;
  group: string;
  route_path: string;
  objective: string;
};

type PlannerResponse = {
  plan_id?: string;
  run_id?: string;
  status: string;
  planner_score?: number;
  workflow?: PlannerStep[] | AllModulesStep[];
  priorities?: string[];
  risks?: string[];
  next_actions?: string[];
  mission?: string;
  escalation_rules?: string[];
  selected_module_count?: number;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

type ModuleGroup = {
  group: string;
  items: Array<{ key?: string; display_name?: string }>;
};

function isAllModulesStep(step: PlannerStep | AllModulesStep): step is AllModulesStep {
  return 'module_key' in step;
}

function assertLiveAnalysis(response: PlannerResponse | null | undefined) {
  if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
    throw new Error(
      IS_STRICT_NO_MOCK_MODE
        ? 'Live LLM backend is unavailable in strict no-mock mode.'
        : 'Live LLM backend is unavailable in fail-closed mode.'
    );
  }
}

export default function SEOPlannerPage() {
  const [planMode, setPlanMode] = useState<PlanMode>('standard');
  const [goal, setGoal] = useState('');
  const [domain, setDomain] = useState('');
  const [primaryKeyword, setPrimaryKeyword] = useState('');
  const [market, setMarket] = useState('');
  const [moduleGroups, setModuleGroups] = useState<string[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [excludeKeys, setExcludeKeys] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<PlannerResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadGroups() {
      try {
        const response = await apiGet<{ groups?: ModuleGroup[] }>(
          '/seo-platform/modules',
          DEFAULT_TENANT_ID
        );
        if (cancelled) return;
        const names = (response?.groups ?? [])
          .map((group) => group.group.trim())
          .filter(Boolean);
        setModuleGroups(names);
      } catch {
        if (!cancelled) setModuleGroups([]);
      }
    }
    void loadGroups();
    return () => {
      cancelled = true;
    };
  }, []);

  async function executePlanner() {
    if (!goal.trim()) {
      setError('Please enter a goal before running the planner.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await apiSend<PlannerResponse>(
        '/seo-platform/planner/execute',
        'POST',
        {
          goal: goal.trim(),
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          market: market.trim(),
        },
        DEFAULT_TENANT_ID
      );
      assertLiveAnalysis(response);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Planner execution failed.');
    } finally {
      setLoading(false);
    }
  }

  async function executeAllModules() {
    if (!goal.trim()) {
      setError('Please enter a goal before planning all modules.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await apiSend<PlannerResponse>(
        '/seo-platform/planner/execute-all-modules',
        'POST',
        {
          goal: goal.trim(),
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          market: market.trim(),
          include_groups: selectedGroups,
          exclude_module_keys: excludeKeys
            .split(',')
            .map((key) => key.trim())
            .filter(Boolean),
        },
        DEFAULT_TENANT_ID
      );
      assertLiveAnalysis(response);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'All-modules planner failed.');
    } finally {
      setLoading(false);
    }
  }

  function toggleGroup(group: string) {
    setSelectedGroups((current) =>
      current.includes(group) ? current.filter((item) => item !== group) : [...current, group]
    );
  }

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

  const modeButton = (mode: PlanMode, label: string) => (
    <button
      type="button"
      onClick={() => {
        setPlanMode(mode);
        setResult(null);
        setError('');
      }}
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        border: planMode === mode ? '1px solid var(--brand)' : '1px solid var(--line)',
        background: planMode === mode ? 'rgba(27,199,255,0.12)' : 'var(--bg)',
        color: planMode === mode ? 'var(--brand)' : 'var(--text)',
        fontWeight: 700,
        fontSize: 12,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );

  const workflowSteps = result?.workflow ?? [];
  const standardSteps = workflowSteps.filter((step): step is PlannerStep => !isAllModulesStep(step));
  const allModuleSteps = workflowSteps.filter(isAllModulesStep);

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0, marginBottom: 6 }}>SEO Execution Planner</h1>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 18 }}>
          Build an end-to-end execution workflow or orchestrate the full SEO module registry with autonomy controls.
        </p>

        <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
          {modeButton('standard', 'Standard Workflow')}
          {modeButton('all-modules', 'All Modules Orchestration')}
        </div>

        <section style={{ ...card, marginBottom: 14, display: 'grid', gap: 10 }}>
          <label htmlFor="planner-goal" style={{ fontSize: 12, fontWeight: 700 }}>
            Goal
          </label>
          <textarea
            id="planner-goal"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="Example: Increase non-branded organic traffic by 35% over 90 days"
            style={{ ...input, minHeight: 90 }}
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
            <div>
              <label
                htmlFor="planner-domain"
                style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
              >
                Domain
              </label>
              <input
                id="planner-domain"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                placeholder="example.com"
                style={input}
              />
            </div>
            <div>
              <label
                htmlFor="planner-keyword"
                style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
              >
                Primary Keyword
              </label>
              <input
                id="planner-keyword"
                value={primaryKeyword}
                onChange={(event) => setPrimaryKeyword(event.target.value)}
                placeholder="best crm for startups"
                style={input}
              />
            </div>
            <div>
              <label
                htmlFor="planner-market"
                style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
              >
                Market
              </label>
              <input
                id="planner-market"
                value={market}
                onChange={(event) => setMarket(event.target.value)}
                placeholder="B2B SaaS"
                style={input}
              />
            </div>
          </div>

          {planMode === 'all-modules' && (
            <>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Include Groups (optional)</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {moduleGroups.map((group) => (
                    <label
                      key={group}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 12,
                        padding: '6px 10px',
                        borderRadius: 999,
                        border: '1px solid var(--line)',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedGroups.includes(group)}
                        onChange={() => toggleGroup(group)}
                      />
                      {group}
                    </label>
                  ))}
                  {moduleGroups.length === 0 && (
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>All registry groups will be included.</span>
                  )}
                </div>
              </div>
              <div>
                <label htmlFor="planner-exclude" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
                  Exclude Module Keys (comma-separated)
                </label>
                <input
                  id="planner-exclude"
                  value={excludeKeys}
                  onChange={(event) => setExcludeKeys(event.target.value)}
                  placeholder="legacy-module-key, optional-module-key"
                  style={input}
                />
              </div>
            </>
          )}

          <button
            type="button"
            onClick={planMode === 'all-modules' ? executeAllModules : executePlanner}
            disabled={loading}
            style={{
              marginTop: 2,
              width: 'fit-content',
              padding: '9px 14px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.75 : 1,
            }}
          >
            {loading
              ? planMode === 'all-modules'
                ? 'Planning all modules...'
                : 'Planning workflow...'
              : planMode === 'all-modules'
                ? 'Plan All Modules'
                : 'Create Execution Plan'}
          </button>

          {error && (
            <div style={{ color: '#fca5a5', border: '1px solid #ef4444', borderRadius: 8, padding: 10, fontSize: 12 }}>
              {error}
            </div>
          )}
        </section>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background:
                        result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: 'rgba(56,189,248,0.15)',
                      color: '#38bdf8',
                    }}
                  >
                    Cached result
                  </span>
                )}
              </div>
            )}
            <section style={{ ...card, marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                {result.run_id ? 'Run ID' : 'Plan ID'}
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{result.run_id ?? result.plan_id}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Status: {result.status}</div>
              {typeof result.selected_module_count === 'number' && (
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                  Modules selected: {result.selected_module_count}
                </div>
              )}
              {result.mission && (
                <div style={{ fontSize: 13, marginTop: 8, lineHeight: 1.5 }}>{result.mission}</div>
              )}
              {typeof result.planner_score === 'number' && (
                <div style={{ marginTop: 8, fontSize: 24, fontWeight: 800 }}>{result.planner_score}</div>
              )}
            </section>

            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, fontSize: 14 }}>
                {planMode === 'all-modules' ? 'Module Execution Graph' : 'Workflow'}
              </h2>
              <div style={{ display: 'grid', gap: 8 }}>
                {planMode === 'all-modules'
                  ? allModuleSteps.map((step) => (
                      <div
                        key={`${step.step}:${step.module_key}`}
                        style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
                      >
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                          Step {step.step} · {step.group}
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{step.module_name}</div>
                        <div style={{ fontSize: 12, marginBottom: 6 }}>{step.objective}</div>
                        {step.route_path && (
                          <a
                            href={step.route_path}
                            style={{ fontSize: 12, color: 'var(--brand)', textDecoration: 'none' }}
                          >
                            Open module
                          </a>
                        )}
                      </div>
                    ))
                  : standardSteps.map((step) => (
                      <div
                        key={`${step.phase}:${step.module}`}
                        style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
                      >
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>{step.phase}</div>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{step.module}</div>
                        <div style={{ fontSize: 12, marginBottom: 6 }}>{step.action}</div>
                        <a href={step.path} style={{ fontSize: 12, color: 'var(--brand)', textDecoration: 'none' }}>
                          Open module
                        </a>
                      </div>
                    ))}
              </div>
            </section>

            <section style={{ ...card, marginBottom: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
              <div>
                <h3 style={{ marginTop: 0, fontSize: 13 }}>Priorities</h3>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                  {(result.priorities ?? []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 style={{ marginTop: 0, fontSize: 13 }}>Risks</h3>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                  {(result.risks ?? []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </section>

            {(result.escalation_rules?.length ?? 0) > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h3 style={{ marginTop: 0, fontSize: 13 }}>Escalation Rules</h3>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                  {(result.escalation_rules ?? []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            )}

            <section style={card}>
              <h3 style={{ marginTop: 0, fontSize: 13 }}>Next Actions</h3>
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                {(result.next_actions ?? []).map((item) => (
                  <li key={item} style={{ marginBottom: 4 }}>
                    {item}
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
