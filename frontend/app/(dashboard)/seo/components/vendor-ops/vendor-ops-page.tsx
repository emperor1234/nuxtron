'use client';

import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import {
  Badge,
  Button,
  Card,
  CardTitle,
  Page,
  PageHeader,
  Stat,
  StatGrid,
} from '@/app/(dashboard)/_ui/kit';

import type { VendorOpsView, VendorSpec } from './vendor-registry';
import styles from './vendor-ops.module.css';

type ChecklistItem = {
  provider: string;
  kind: string;
  configured: boolean;
  required_missing: string[];
};

type ChecklistResponse = {
  configured: number;
  total: number;
  configured_pct: number;
  checklist: ChecklistItem[];
};

type PreflightStep = {
  provider: string;
  priority: string;
  required_missing: string[];
};

type PreflightResponse = {
  configured_pct: number;
  missing_provider_steps: PreflightStep[];
};

type RemediationResponse = {
  remediation_steps: PreflightStep[];
};

type Project = { id: string; name: string; primary_domain: string };
type Run = { id: string; project_id: string; strict_probe_status: string; completed_at: string };
type ProjectsResponse = { projects: Project[] };
type RunsResponse = { runs: Run[] };

type AutomationResponse = {
  third_parties_and_vendors?: Array<{ vendor?: string }>;
  how_it_works?: string[];
};

type AssistResponse = {
  assist: {
    answer_summary: string;
    recommended_actions: string[];
    workflow_handoffs: string[];
  };
};

const VIEW_LABELS: Record<VendorOpsView, string> = {
  readiness: 'Overview',
  integrations: 'Connections',
  automation: 'Automation',
  assist: 'AI Assist',
};

function endpoint(vendor: VendorSpec, path: string) {
  return `/search-everywhere/${vendor.apiSlug}/${path}`;
}

function ViewNav({ vendor, view }: { vendor: VendorSpec; view: VendorOpsView }) {
  return (
    <nav className={styles.nav} aria-label={`${vendor.label} workspace`}>
      {vendor.views.map((item) => (
        <Link
          key={item}
          href={`/seo/${vendor.slug}-${item}`}
          className={`${styles.navLink} ${item === view ? styles.navLinkActive : ''}`}
          aria-current={item === view ? 'page' : undefined}
        >
          {VIEW_LABELS[item]}
        </Link>
      ))}
    </nav>
  );
}

function ProviderList({ items }: { items: ChecklistItem[] }) {
  if (!items.length) return <p className={styles.notice}>No provider connections are required.</p>;
  return (
    <ul className={styles.list}>
      {items.map((item) => (
        <li key={`${item.provider}-${item.kind}`} className={styles.row}>
          <span className={styles.rowMain}>
            <span className={styles.rowTitle}>{item.provider}</span>
            <span className={styles.muted}>{item.kind}</span>
            {!item.configured && item.required_missing.length ? (
              <span className={styles.muted}>Needs: {item.required_missing.join(', ')}</span>
            ) : null}
          </span>
          <Badge tone={item.configured ? 'success' : 'neutral'}>
            {item.configured ? 'Connected' : 'Action needed'}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

function ReadinessView({ vendor, tenantId }: { vendor: VendorSpec; tenantId: string }) {
  const [data, setData] = useState<ChecklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await apiGet<ChecklistResponse>(endpoint(vendor, 'provider-checklist'), tenantId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load connection health.');
    } finally {
      setLoading(false);
    }
  }, [tenantId, vendor]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className={styles.stack}>
      <StatGrid>
        <Stat label="Connections ready" value={data ? `${data.configured}/${data.total}` : '—'} />
        <Stat label="Setup complete" value={data ? `${data.configured_pct}%` : '—'} />
        <Stat label="Needs attention" value={data ? data.total - data.configured : '—'} />
      </StatGrid>
      <Card>
        <div className={styles.toolbar}>
          <CardTitle sub="Only your workspace connections are shown here.">Connection health</CardTitle>
          <Button onClick={() => void load()} disabled={loading}>
            {loading ? 'Checking…' : 'Refresh'}
          </Button>
        </div>
        {error ? <p className={styles.error}>{error}</p> : null}
        {!error && loading && !data ? <p className={styles.notice}>Checking connections…</p> : null}
        {data ? <ProviderList items={data.checklist} /> : null}
      </Card>
    </div>
  );
}

function IntegrationsView({ vendor, tenantId }: { vendor: VendorSpec; tenantId: string }) {
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [remediation, setRemediation] = useState<RemediationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [connections, nextSteps] = await Promise.all([
        apiGet<ChecklistResponse>(endpoint(vendor, 'provider-checklist'), tenantId),
        apiGet<PreflightResponse>(endpoint(vendor, 'preflight'), tenantId),
      ]);
      setChecklist(connections);
      setPreflight(nextSteps);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load connections.');
    } finally {
      setLoading(false);
    }
  }, [tenantId, vendor]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function buildRemediation() {
    setLoading(true);
    setError('');
    try {
      setRemediation(
        await apiSend<RemediationResponse>(
          endpoint(vendor, 'remediation-bundle'),
          'POST',
          { include_optional: false, include_configured: false, top_steps: 12 },
          tenantId
        )
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not build setup steps.');
    } finally {
      setLoading(false);
    }
  }

  async function applyWiring() {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        endpoint(vendor, 'wiring/apply'),
        'POST',
        { providers: [], include_all_missing: true, include_optional_auth: true },
        tenantId
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not apply connection settings.');
      setLoading(false);
    }
  }

  const nextSteps = remediation?.remediation_steps ?? preflight?.missing_provider_steps ?? [];

  return (
    <div className={styles.stack}>
      <Card>
        <div className={styles.toolbar}>
          <Button onClick={() => void refresh()} disabled={loading}>
            Refresh
          </Button>
          <Button onClick={() => void buildRemediation()} disabled={loading}>
            Build setup plan
          </Button>
          {vendor.supportsWiring ? (
            <Button variant="primary" onClick={() => void applyWiring()} disabled={loading}>
              Apply available settings
            </Button>
          ) : null}
        </div>
        {error ? <p className={styles.error}>{error}</p> : null}
      </Card>
      <div className={styles.split}>
        <Card>
          <CardTitle sub={checklist ? `${checklist.configured_pct}% complete` : undefined}>
            Provider connections
          </CardTitle>
          {loading && !checklist ? <p className={styles.notice}>Loading connections…</p> : null}
          {checklist ? <ProviderList items={checklist.checklist} /> : null}
        </Card>
        <Card>
          <CardTitle sub="Ordered by what blocks useful work first.">Next setup steps</CardTitle>
          {!nextSteps.length ? (
            <p className={styles.notice}>No blocking setup steps found.</p>
          ) : (
            <ul className={styles.list}>
              {nextSteps.map((step) => (
                <li key={`${step.provider}-${step.priority}`} className={styles.row}>
                  <span className={styles.rowMain}>
                    <span className={styles.rowTitle}>{step.provider}</span>
                    <span className={styles.muted}>
                      {step.required_missing.join(', ') || 'Connect provider account'}
                    </span>
                  </span>
                  <Badge tone={step.priority === 'high' ? 'danger' : 'neutral'}>{step.priority}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function AutomationView({ vendor, tenantId }: { vendor: VendorSpec; tenantId: string }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [name, setName] = useState(`${vendor.label} workspace`);
  const [domain, setDomain] = useState('');
  const [keyword, setKeyword] = useState(vendor.defaultKeyword);
  const [automation, setAutomation] = useState<AutomationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData] = await Promise.all([
        apiGet<ProjectsResponse>(endpoint(vendor, 'projects'), tenantId),
        apiGet<RunsResponse>(endpoint(vendor, 'runs'), tenantId),
      ]);
      setProjects(projectData.projects ?? []);
      setRuns(runData.runs ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load automation workspace.');
    } finally {
      setLoading(false);
    }
  }, [tenantId, vendor]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await apiSend(
        endpoint(vendor, 'projects'),
        'POST',
        {
          name: name.trim(),
          primary_domain: domain.trim(),
          crawl_urls: [`https://${domain.trim()}`],
          competitor_domains: [...vendor.defaultCompetitors],
          max_urls: 10000,
        },
        tenantId
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create project.');
      setLoading(false);
    }
  }

  async function runProject(projectId: string) {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        endpoint(vendor, `projects/${projectId}/run`),
        'POST',
        {
          seed_keyword: keyword.trim(),
          competitor_domains: [...vendor.defaultCompetitors],
          max_results: 12,
          require_live_providers: true,
        },
        tenantId
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not run project.');
      setLoading(false);
    }
  }

  async function runBlueprint() {
    if (!domain.trim()) {
      setError('Enter your domain before running the automation.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      setAutomation(
        await apiSend<AutomationResponse>(
          endpoint(vendor, 'full-automation'),
          'POST',
          {
            seed_keyword: keyword.trim(),
            your_domain: domain.trim(),
            competitor_domains: [...vendor.defaultCompetitors],
            max_results: 12,
            require_live_providers: true,
          },
          tenantId
        )
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not run automation.');
    } finally {
      setLoading(false);
    }
  }

  if (!vendor.supportsProjects) {
    return <ReadinessView vendor={vendor} tenantId={tenantId} />;
  }

  return (
    <div className={styles.stack}>
      <Card>
        <CardTitle sub="Use your own domain. No demo projects or fabricated runs are created.">
          New project
        </CardTitle>
        <form className={styles.stack} onSubmit={(event) => void createProject(event)}>
          <div className={styles.formGrid}>
            <label className={styles.field}>
              Project name
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
            <label className={styles.field}>
              Domain
              <input
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                placeholder="example.com"
                inputMode="url"
                required
              />
            </label>
            <label className={styles.field}>
              Starting keyword
              <input value={keyword} onChange={(event) => setKeyword(event.target.value)} required />
            </label>
          </div>
          <div className={styles.toolbar}>
            <Button type="submit" variant="primary" disabled={loading}>
              Create project
            </Button>
            {vendor.supportsFullAutomation ? (
              <Button type="button" onClick={() => void runBlueprint()} disabled={loading}>
                Run full automation
              </Button>
            ) : null}
            <Button type="button" onClick={() => void refresh()} disabled={loading}>
              Refresh
            </Button>
          </div>
        </form>
        {error ? <p className={styles.error}>{error}</p> : null}
      </Card>
      <div className={styles.split}>
        <Card>
          <CardTitle>Projects</CardTitle>
          {!projects.length ? (
            <p className={styles.notice}>Create your first project to start automating.</p>
          ) : (
            <ul className={styles.list}>
              {projects.slice(-12).reverse().map((project) => (
                <li key={project.id} className={styles.row}>
                  <span className={styles.rowMain}>
                    <span className={styles.rowTitle}>{project.name}</span>
                    <span className={styles.muted}>{project.primary_domain}</span>
                  </span>
                  <Button onClick={() => void runProject(project.id)} disabled={loading}>
                    Run
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardTitle>Recent runs</CardTitle>
          {!runs.length ? (
            <p className={styles.notice}>Completed and running jobs will appear here.</p>
          ) : (
            <ul className={styles.list}>
              {runs.slice(-12).reverse().map((run) => (
                <li key={run.id} className={styles.row}>
                  <span className={styles.rowMain}>
                    <span className={styles.rowTitle}>{run.id}</span>
                    <span className={styles.muted}>{run.completed_at || 'In progress'}</span>
                  </span>
                  <Badge tone={run.strict_probe_status === 'passed' ? 'success' : 'neutral'}>
                    {run.strict_probe_status || 'running'}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      {automation ? (
        <Card>
          <CardTitle>Latest automation</CardTitle>
          <p className={styles.notice}>
            {automation.third_parties_and_vendors?.length ?? 0} provider connections participated.
          </p>
          {automation.how_it_works?.length ? (
            <ol className={styles.actions}>
              {automation.how_it_works.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}

function AssistView({ vendor, tenantId }: { vendor: VendorSpec; tenantId: string }) {
  const [prompt, setPrompt] = useState(
    `Review my ${vendor.label} workspace and recommend the next best actions.`
  );
  const [result, setResult] = useState<AssistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      setResult(
        await apiSend<AssistResponse>(
          endpoint(vendor, 'assist/chat'),
          'POST',
          { prompt, include_vendor_context: true },
          tenantId
        )
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not run AI Assist.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.stack}>
      <Card>
        <CardTitle sub={`Ask about your ${vendor.label} setup, data, and workflows.`}>AI Assist</CardTitle>
        <form className={styles.stack} onSubmit={(event) => void submit(event)}>
          <label className={styles.field}>
            What would you like help with?
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} required />
          </label>
          <div>
            <Button type="submit" variant="primary" disabled={loading || !prompt.trim()}>
              {loading ? 'Working…' : 'Get recommendations'}
            </Button>
          </div>
        </form>
        {error ? <p className={styles.error}>{error}</p> : null}
      </Card>
      {result ? (
        <Card>
          <CardTitle>Recommendations</CardTitle>
          <p className={styles.summary}>{result.assist.answer_summary}</p>
          <ol className={styles.actions}>
            {result.assist.recommended_actions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
          {result.assist.workflow_handoffs.length ? (
            <>
              <CardTitle>Suggested workflows</CardTitle>
              <ul className={styles.actions}>
                {result.assist.workflow_handoffs.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}

export function VendorOpsPage({ vendor, view }: { vendor: VendorSpec; view: VendorOpsView }) {
  const tenantId = useMemo(resolveSessionTenant, []);
  const subtitle = {
    readiness: `See what is connected and what needs attention in your ${vendor.label} workspace.`,
    integrations: `Connect providers and complete the setup required by ${vendor.label}.`,
    automation: `Create projects and run real ${vendor.label} workflows for your domain.`,
    assist: `Get recommendations grounded in your ${vendor.label} workspace.`,
  }[view];

  return (
    <Page>
      <PageHeader title={`${vendor.label} ${VIEW_LABELS[view]}`} subtitle={subtitle} />
      <ViewNav vendor={vendor} view={view} />
      {view === 'readiness' ? <ReadinessView vendor={vendor} tenantId={tenantId} /> : null}
      {view === 'integrations' ? <IntegrationsView vendor={vendor} tenantId={tenantId} /> : null}
      {view === 'automation' ? <AutomationView vendor={vendor} tenantId={tenantId} /> : null}
      {view === 'assist' ? <AssistView vendor={vendor} tenantId={tenantId} /> : null}
    </Page>
  );
}
