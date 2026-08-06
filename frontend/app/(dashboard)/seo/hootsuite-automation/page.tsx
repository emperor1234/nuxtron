'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Project = { id: string; name: string; primary_domain: string };
type Run = { id: string; project_id: string; strict_probe_status: string; completed_at: string };
type Schedule = { id: string; project_id: string; cron: string; enabled: boolean };

type ProjectsResponse = { status: string; projects: Project[] };
type RunsResponse = { status: string; runs: Run[] };
type SchedulesResponse = { status: string; schedules: Schedule[] };

type GateResponse = {
  status: string;
  gate: { passed: boolean; blockers: string[] };
};

type FullAutomationResponse = {
  status: string;
  hootsuite_modules?: Record<string, string[]>;
  third_parties_and_vendors?: Array<{ vendor?: string; configured?: boolean }>;
  how_it_works?: string[];
  production_gate?: {
    passed?: boolean;
    blockers?: string[];
  };
};

export default function HootsuiteAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [automation, setAutomation] = useState<FullAutomationResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData, scheduleData, gateData] = await Promise.all([
        apiGet<ProjectsResponse>('/search-everywhere/hootsuite/projects', tenantId),
        apiGet<RunsResponse>('/search-everywhere/hootsuite/runs', tenantId),
        apiGet<SchedulesResponse>('/search-everywhere/hootsuite/schedules', tenantId),
        apiGet<GateResponse>('/search-everywhere/hootsuite/production-gate', tenantId),
      ]);
      setProjects(projectData.projects || []);
      setRuns(runData.runs || []);
      setSchedules(scheduleData.schedules || []);
      setGate(gateData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Hootsuite automation state');
    } finally {
      setLoading(false);
    }
  }

  async function createDemoProject() {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        '/search-everywhere/hootsuite/projects',
        'POST',
        {
          name: 'Hootsuite Automation Project',
          primary_domain: 'nuxtron.ai',
          crawl_urls: ['https://nuxtron.ai', 'https://nuxtron.ai/pricing'],
          competitor_domains: ['hootsuite.com', 'sproutsocial.com'],
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
      setError('Create a Hootsuite project first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const projectId = projects.at(-1)?.id;
      await apiSend(
        `/search-everywhere/hootsuite/projects/${projectId}/run`,
        'POST',
        {
          seed_keyword: 'social media management',
          competitor_domains: ['hootsuite.com', 'sproutsocial.com'],
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

  async function createWeeklySchedule() {
    if (!projects.length) {
      setError('Create a Hootsuite project before adding schedules.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const projectId = projects.at(-1)?.id;
      await apiSend(
        '/search-everywhere/hootsuite/schedules',
        'POST',
        {
          project_id: projectId,
          cron: '0 3 * * 1',
          enabled: true,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create schedule');
      setLoading(false);
    }
  }

  async function executeSchedules() {
    setLoading(true);
    setError('');
    try {
      await apiSend('/search-everywhere/hootsuite/schedules/execute', 'POST', { due_only: false }, tenantId);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to execute schedules');
      setLoading(false);
    }
  }

  async function runFullBlueprint() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<FullAutomationResponse>(
        '/search-everywhere/hootsuite/full-automation',
        'POST',
        {
          seed_keyword: 'social media management',
          your_domain: 'nuxtron.ai',
          competitor_domains: ['hootsuite.com', 'sproutsocial.com'],
          max_results: 12,
          require_live_providers: false,
        },
        tenantId
      );
      setAutomation(result);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Hootsuite automation blueprint');
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
        <p className="eyebrow">Hootsuite Automation</p>
        <h1>Hootsuite Run And Schedule Control</h1>
        <p>
          Manage projects and execution runs from the same API surface exposed by the backend Hootsuite automation
          suite.
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
          <button onClick={() => void createWeeklySchedule()} disabled={loading}>
            {loading ? 'Scheduling...' : 'Create Weekly Schedule'}
          </button>
          <button onClick={() => void executeSchedules()} disabled={loading}>
            {loading ? 'Executing...' : 'Execute Schedules'}
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
          {projects.length === 0 ? (
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
          {runs.length === 0 ? (
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

        <article className="card">
          <h3 style={{ marginTop: 0 }}>Schedules</h3>
          {schedules.length === 0 ? (
            <p style={{ opacity: 0.8 }}>No schedules yet.</p>
          ) : (
            <ul className="bullet-list">
              {schedules.slice(-8).map((schedule) => (
                <li key={schedule.id}>
                  <strong>{schedule.id}</strong> - {schedule.cron} ({schedule.enabled ? 'enabled' : 'disabled'})
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
          {gate.gate.passed ? null : (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
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
          {automation.hootsuite_modules ? (
            <>
              <h4>Module Coverage</h4>
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
                {Object.entries(automation.hootsuite_modules).map(([name, items]) => (
                  <div key={name} className="card">
                    <h5 style={{ marginTop: 0, textTransform: 'capitalize' }}>{name}</h5>
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
