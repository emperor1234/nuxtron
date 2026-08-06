'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Project = { id: string; name: string; primary_domain: string };
type Run = { id: string; project_id: string; strict_probe_status: string; completed_at: string };

type ProjectsResponse = { status: string; projects: Project[] };
type RunsResponse = { status: string; runs: Run[] };

type GateResponse = {
  status: string;
  gate: { passed: boolean; blockers: string[] };
};

type FullAutomationResponse = {
  status: string;
  promptwatch_modules?: Record<string, string[]>;
  third_parties_and_vendors?: Array<{ vendor?: string }>;
  how_it_works?: string[];
  production_gate?: {
    passed?: boolean;
    blockers?: string[];
  };
};

export default function PromptwatchAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [automation, setAutomation] = useState<FullAutomationResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData, gateData] = await Promise.all([
        apiGet<ProjectsResponse>('/search-everywhere/promptwatch/projects', tenantId),
        apiGet<RunsResponse>('/search-everywhere/promptwatch/runs', tenantId),
        apiGet<GateResponse>('/search-everywhere/promptwatch/production-gate', tenantId),
      ]);
      setProjects(projectData.projects || []);
      setRuns(runData.runs || []);
      setGate(gateData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Promptwatch automation state');
    } finally {
      setLoading(false);
    }
  }

  async function createDemoProject() {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        '/search-everywhere/promptwatch/projects',
        'POST',
        {
          name: 'Promptwatch Automation Project',
          primary_domain: 'nuxtron.ai',
          crawl_urls: ['https://nuxtron.ai', 'https://nuxtron.ai/docs'],
          competitor_domains: ['promptwatch.com', 'langsmith.com'],
          max_urls: 10000,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
      setLoading(false);
    }
  }

  async function runLatestProject() {
    if (!projects.length) {
      setError('Create a Promptwatch project first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const projectId = projects[projects.length - 1]?.id;
      await apiSend(
        `/search-everywhere/promptwatch/projects/${projectId}/run`,
        'POST',
        {
          seed_keyword: 'llm prompt observability',
          competitor_domains: ['promptwatch.com', 'langsmith.com'],
          max_results: 12,
          require_live_providers: false,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run project');
      setLoading(false);
    }
  }

  async function runFullBlueprint() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<FullAutomationResponse>(
        '/search-everywhere/promptwatch/full-automation',
        'POST',
        {
          seed_keyword: 'llm prompt observability',
          your_domain: 'nuxtron.ai',
          competitor_domains: ['promptwatch.com', 'langsmith.com'],
          max_results: 12,
          require_live_providers: false,
        },
        tenantId
      );
      setAutomation(result);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Promptwatch automation blueprint');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Promptwatch Automation</p>
        <h1>Promptwatch Run And Product Control</h1>
        <p>
          Manage projects, execution runs, and product blueprints from the same API surface exposed by the backend
          Promptwatch automation suite.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshAll()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button onClick={() => void createDemoProject()} disabled={loading}>
            {loading ? 'Working...' : 'Create Demo Project'}
          </button>
          <button onClick={() => void runLatestProject()} disabled={loading}>
            {loading ? 'Running...' : 'Run Latest Project'}
          </button>
          <button onClick={() => void runFullBlueprint()} disabled={loading}>
            {loading ? 'Executing...' : 'Run Full Automation Blueprint'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Projects</h3>
          {!projects.length ? (
            <p style={{ opacity: 0.8 }}>No projects yet.</p>
          ) : (
            <ul className="bullet-list">
              {projects.slice(-8).map((p) => (
                <li key={p.id}>
                  <strong>{p.name}</strong> ({p.primary_domain})
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="card">
          <h3 style={{ marginTop: 0 }}>Runs</h3>
          {!runs.length ? (
            <p style={{ opacity: 0.8 }}>No runs yet.</p>
          ) : (
            <ul className="bullet-list">
              {runs.slice(-8).map((r) => (
                <li key={r.id}>
                  <strong>{r.id}</strong> - strict probe: {r.strict_probe_status}
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate Snapshot</h3>
          <p>
            Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          {!gate.gate.passed ? (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {automation ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Automation Blueprint</h3>
          <p>Vendors referenced: {automation.third_parties_and_vendors?.length ?? 0}</p>
          {automation.how_it_works?.length ? (
            <>
              <h4>How It Works</h4>
              <ul className="bullet-list">
                {automation.how_it_works.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}
          {automation.promptwatch_modules ? (
            <>
              <h4>Module Coverage</h4>
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
                {Object.entries(automation.promptwatch_modules).map(([name, items]) => (
                  <div key={name} className="card">
                    <h5 style={{ marginTop: 0, textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</h5>
                    <ul className="bullet-list">
                      {items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
