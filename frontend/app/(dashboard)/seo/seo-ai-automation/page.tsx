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

export default function SeoAiAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [gate, setGate] = useState<GateResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData, gateData] = await Promise.all([
        apiGet<ProjectsResponse>('/search-everywhere/seoai/projects', tenantId),
        apiGet<RunsResponse>('/search-everywhere/seoai/runs', tenantId),
        apiGet<GateResponse>('/search-everywhere/seoai/production-gate', tenantId),
      ]);
      setProjects(projectData.projects || []);
      setRuns(runData.runs || []);
      setGate(gateData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load SEO.AI automation state');
    } finally {
      setLoading(false);
    }
  }

  async function createDemoProject() {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        '/search-everywhere/seoai/projects',
        'POST',
        {
          name: 'SEO.AI Automation Project',
          primary_domain: 'nuxtron.ai',
          content_sources: ['blog', 'docs', 'landing_pages'],
          competitor_domains: ['semrush.com', 'ahrefs.com'],
          target_markets: ['us-en'],
          publish_targets: ['wordpress', 'shopify'],
          enable_programmatic_refresh: true,
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
      setError('Create a SEO.AI project first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const projectId = projects[projects.length - 1]?.id;
      await apiSend(
        `/search-everywhere/seoai/projects/${projectId}/run`,
        'POST',
        {
          seed_keyword: 'social media management',
          max_results: 12,
          require_live_providers: false,
          include_assist_summary: true,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run project');
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">SEO.AI Automation</p>
        <h1>SEO.AI Run And Schedule Control</h1>
        <p>
          Manage projects and execution runs from the same API surface exposed by the backend SEO.AI automation suite.
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
    </main>
  );
}
