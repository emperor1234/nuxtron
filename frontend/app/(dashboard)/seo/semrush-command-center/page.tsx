'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Project = { id: string; name: string; primary_domain: string };
type Run = { id: string; project_id: string; strict_probe_status: string; completed_at: string };

type ProjectsResponse = { status: string; projects: Project[] };
type RunsResponse = { status: string; runs: Run[] };

type ParityRow = { module: string; implemented: boolean; coverage_pct: number; evidence: string[] };
type VendorInventoryRow = { domain: string; vendor: string; capability: string; configured: boolean; evidence: string };
type ChecklistItem = { provider: string; kind: string; configured: boolean; required_missing: string[] };

type ParityResponse = {
  status: string;
  semrush_parity_chart: ParityRow[];
  summary: {
    modules_total: number;
    modules_implemented: number;
    implementation_pct: number;
    integration_configured_units: number;
    integration_total_units: number;
    integration_configured_pct: number;
  };
  vendor_inventory: VendorInventoryRow[];
  validation_note?: string;
};

type ChecklistResponse = {
  status: string;
  configured: number;
  total: number;
  configured_pct: number;
  checklist: ChecklistItem[];
};

type GateResponse = {
  status: string;
  gate: { passed: boolean; implementation_ok: boolean; integration_ok: boolean; strict_probe_ok: boolean; blockers: string[] };
  provider_checklist_summary?: { configured: number; total: number; missing_requirements: Array<{ provider: string; required_missing: string[] }> };
};

type ProviderBootstrapResponse = {
  status: string;
  requested_providers: string[];
  steps_total: number;
  steps: Array<{ provider: string; kind: string; required_missing: string[] }>; 
  next?: { run_checklist: string; run_gate: string };
};

type ProviderProbeResponse = {
  status: string;
  summary: { providers_requested: number; passed: number; failed: number; skipped: number; strict_live_ready: boolean };
  probes: Array<{ provider: string; status: string }>;
};

type EnvTemplateResponse = {
  status: string;
  include_optional: boolean;
  include_configured: boolean;
  providers_included: string[];
  missing_keys: string[];
  filename: string;
  env_template: string;
};

type FullAutomationResponse = {
  status: string;
  run_mode?: string;
  results?: {
    keyword_discovery?: { provider_selected?: string; keywords_analyzed?: number; clusters_found?: number };
    content_gap?: { total_opportunities?: number; high_coverage_gaps?: number };
    backlink_audit?: { risk_level?: string; toxic_count?: number; suspicious_count?: number };
    backlink_gap?: { unique_opportunities?: number; competitors_analyzed?: number };
  };
  providers?: { vendor_inventory?: VendorInventoryRow[] };
  how_it_works?: string[];
  production_gate?: { passed?: boolean; blockers?: string[] };
};

const DEFAULT_PROJECT_PAYLOAD = {
  name: 'Semrush Command Center Project',
  primary_domain: 'nuxtron.ai',
  crawl_urls: ['https://nuxtron.ai', 'https://nuxtron.ai/seo'],
  competitor_domains: ['semrush.com', 'ahrefs.com', 'moz.com'],
  max_urls: 10000,
};

const DEFAULT_RUN_PAYLOAD = {
  seed_keyword: 'seo software platform',
  competitor_domains: ['semrush.com', 'ahrefs.com', 'moz.com'],
  max_results: 12,
  require_live_providers: false,
};

const DEFAULT_GATE_PAYLOAD = {
  seed_keyword: 'seo software platform',
  your_domain: 'nuxtron.ai',
  competitor_domains: ['semrush.com', 'ahrefs.com', 'moz.com'],
  max_results: 12,
};

const DEFAULT_BOOTSTRAP_PROVIDERS = ['DataForSEO', 'Serper.dev', 'Google Ads Keyword Planner', 'Google Search Console', 'Ahrefs API', 'Cloudflare'];
const DEFAULT_PROBE_PROVIDERS = ['dataforseo', 'serper', 'google_ads', 'gsc'];

function splitCsv(value: string): string[] {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function StatCard({ label, value, sub }: Readonly<{ label: string; value: string; sub?: string }>) {
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>{label}</h3>
      <p style={{ fontSize: 28, fontWeight: 700, marginBottom: 6 }}>{value}</p>
      {sub ? <p style={{ margin: 0, opacity: 0.8 }}>{sub}</p> : null}
    </article>
  );
}

function getGateStateLabel(gate: GateResponse | null): string {
  if (gate?.gate.passed === true) return 'PASSED';
  if (gate?.gate.passed === false) return 'FAILED';
  return 'Not run';
}

function SectionTitle({ title, summary }: Readonly<{ title: string; summary: string }>) {
  return (
    <div style={{ marginBottom: 12 }}>
      <h3 style={{ marginTop: 0, marginBottom: 6 }}>{title}</h3>
      <p style={{ margin: 0, opacity: 0.82 }}>{summary}</p>
    </div>
  );
}

function ActionToolbar({
  loading,
  error,
  onRefresh,
  onCreateProject,
  onRunLatest,
  onGate,
  onBootstrap,
  onProbes,
  onEnvTemplate,
  onAutomation,
}: Readonly<{
  loading: boolean;
  error: string;
  onRefresh: () => void;
  onCreateProject: () => void;
  onRunLatest: () => void;
  onGate: () => void;
  onBootstrap: () => void;
  onProbes: () => void;
  onEnvTemplate: () => void;
  onAutomation: () => void;
}>) {
  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Control Actions" summary="These buttons call live backend endpoints. No mocked data is used by the runtime UI." />
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button onClick={onRefresh} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
        <button onClick={onCreateProject} disabled={loading}>{loading ? 'Working...' : 'Create Demo Project'}</button>
        <button onClick={onRunLatest} disabled={loading}>{loading ? 'Running...' : 'Run Latest Project'}</button>
        <button onClick={onGate} disabled={loading}>{loading ? 'Checking...' : 'Run Production Gate'}</button>
        <button onClick={onBootstrap} disabled={loading}>{loading ? 'Bootstrapping...' : 'Bootstrap Providers'}</button>
        <button onClick={onProbes} disabled={loading}>{loading ? 'Probing...' : 'Probe Providers'}</button>
        <button onClick={onEnvTemplate} disabled={loading}>{loading ? 'Generating...' : 'Generate Env Template'}</button>
        <button onClick={onAutomation} disabled={loading}>{loading ? 'Executing...' : 'Run Full Automation Blueprint'}</button>
      </div>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
    </section>
  );
}

function QuickNavigation() {
  const links = [
    { href: '/seo/rank-tracking', title: 'Rank Tracking', summary: 'Keyword movement, volatility, and rank visibility controls.' },
    { href: '/seo/backlink-intelligence', title: 'Backlink Intelligence', summary: 'Toxicity, gap analysis, and authority signal workflows.' },
    { href: '/seo/domain-overview', title: 'Domain Overview', summary: 'Competitive domain intelligence and visibility snapshots.' },
    { href: '/seo/writesonic-readiness', title: 'Writesonic Readiness', summary: 'A parallel production-grade vendor command center slice.' },
  ];

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Quick Navigation" summary="Semrush-focused routes and the neighboring SEO workspaces used for comparison and handoff." />
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
        {links.map((item) => (
          <Link key={item.href} className="card" href={item.href} style={{ textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>{item.title}</h3>
            <p style={{ opacity: 0.82, marginBottom: 0 }}>{item.summary}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

function MetricsGrid({
  parity,
  checklist,
  gate,
  projects,
  runs,
}: Readonly<{
  parity: ParityResponse | null;
  checklist: ChecklistResponse | null;
  gate: GateResponse | null;
  projects: Project[];
  runs: Run[];
}>) {
  const productionGateState = getGateStateLabel(gate);

  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <StatCard label="Implementation" value={parity ? `${parity.summary.modules_implemented}/${parity.summary.modules_total}` : '...'} sub="Semrush parity modules" />
      <StatCard label="Integration Wiring" value={parity ? `${parity.summary.integration_configured_pct}%` : '...'} sub="Configured provider coverage" />
      <StatCard label="Provider Checklist" value={checklist ? `${checklist.configured_pct}%` : '...'} sub="Wiring readiness" />
      <StatCard label="Production Gate" value={productionGateState} sub="Strict live readiness" />
      <StatCard label="Vendors Tracked" value={String(parity?.vendor_inventory?.length ?? 0)} sub="Third-party inventory rows" />
      <StatCard label="Projects / Runs" value={`${projects.length}/${runs.length}`} sub="Project orchestration" />
    </section>
  );
}

function ParitySection({ parity }: Readonly<{ parity: ParityResponse | null }>) {
  if (!parity) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Semrush Parity Chart" summary="Feature implementation and evidence rows pulled from the live search-everywhere Semrush parity endpoint." />
      <p style={{ opacity: 0.82, marginTop: 0 }}>{parity.validation_note ?? 'Parity reflects live backend feature coverage.'}</p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Module</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Implemented</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Coverage</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {parity.semrush_parity_chart.map((row) => (
              <tr key={row.module} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{row.module}</td>
                <td style={{ padding: '8px 6px' }}>{row.implemented ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{row.coverage_pct}%</td>
                <td style={{ padding: '8px 6px' }}>{row.evidence.join('; ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ChecklistSection({ checklist }: Readonly<{ checklist: ChecklistResponse | null }>) {
  if (!checklist) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Provider Checklist" summary="Configured providers, required environment variables, and missing wiring are surfaced here." />
      <p style={{ opacity: 0.82, marginTop: 0 }}>{checklist.configured}/{checklist.total} configured ({checklist.configured_pct}%)</p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Provider</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Kind</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Configured</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Missing</th>
            </tr>
          </thead>
          <tbody>
            {checklist.checklist.map((item) => (
              <tr key={item.provider} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{item.provider}</td>
                <td style={{ padding: '8px 6px' }}>{item.kind}</td>
                <td style={{ padding: '8px 6px' }}>{item.configured ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{item.required_missing.length ? item.required_missing.join(', ') : 'None'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function GateSection({ gate }: Readonly<{ gate: GateResponse | null }>) {
  if (!gate) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Production Gate" summary="Semrush production-grade readiness is determined by implementation, wiring, and strict live probe state." />
      <p style={{ marginTop: 0 }}>
        Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong> | Implementation: <strong>{gate.gate.implementation_ok ? 'Yes' : 'No'}</strong> | Integration:{' '}
        <strong>{gate.gate.integration_ok ? 'Yes' : 'No'}</strong> | Strict probe: <strong>{gate.gate.strict_probe_ok ? 'Yes' : 'No'}</strong>
      </p>
      {gate.gate.blockers.length ? (
        <ul className="bullet-list">
          {gate.gate.blockers.map((blocker) => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}
      {gate.provider_checklist_summary ? (
        <p style={{ opacity: 0.82, marginBottom: 0 }}>
          Provider checklist: {gate.provider_checklist_summary.configured}/{gate.provider_checklist_summary.total} configured.
        </p>
      ) : null}
    </section>
  );
}

function InputPanels({
  bootstrapProviders,
  onBootstrapProvidersChange,
  probeProviders,
  onProbeProvidersChange,
}: Readonly<{
  bootstrapProviders: string;
  onBootstrapProvidersChange: (value: string) => void;
  probeProviders: string;
  onProbeProvidersChange: (value: string) => void;
}>) {
  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <article className="card">
        <SectionTitle title="Provider Bootstrap Inputs" summary="Tune the provider list before generating the bootstrap plan." />
        <input
          value={bootstrapProviders}
          onChange={(event) => onBootstrapProvidersChange(event.target.value)}
          style={{ width: '100%', padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,0.25)' }}
        />
      </article>
      <article className="card">
        <SectionTitle title="Provider Probe Inputs" summary="Tune the provider list before running live readiness probes." />
        <input
          value={probeProviders}
          onChange={(event) => onProbeProvidersChange(event.target.value)}
          style={{ width: '100%', padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,0.25)' }}
        />
      </article>
    </section>
  );
}

function BootstrapSection({ bootstrap }: Readonly<{ bootstrap: ProviderBootstrapResponse | null }>) {
  if (!bootstrap) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Provider Bootstrap" summary="Steps to wire the required providers are generated from the live backend contract." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        {bootstrap.steps_total} steps prepared for {bootstrap.requested_providers.length} requested providers.
      </p>
      {bootstrap.next ? <p style={{ opacity: 0.82 }}>Next: {bootstrap.next.run_checklist} then {bootstrap.next.run_gate}</p> : null}
      <ul className="bullet-list">
        {bootstrap.steps.slice(0, 12).map((step) => (
          <li key={`${step.provider}-${step.kind}`}>
            <strong>{step.provider}</strong> ({step.kind}) - {step.required_missing.length ? step.required_missing.join(', ') : 'no missing env'}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProbeSection({ probes }: Readonly<{ probes: ProviderProbeResponse | null }>) {
  if (!probes) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Provider Probes" summary="The probe runner exercises requested providers and reports live readiness status." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Requested: {probes.summary.providers_requested} | Passed: {probes.summary.passed} | Failed: {probes.summary.failed} | Skipped: {probes.summary.skipped} |
        Strict live ready: {probes.summary.strict_live_ready ? 'Yes' : 'No'}
      </p>
      <ul className="bullet-list">
        {probes.probes.slice(0, 12).map((probe) => (
          <li key={`${probe.provider}-${probe.status}`}>
            <strong>{probe.provider}</strong> - {probe.status}
          </li>
        ))}
      </ul>
    </section>
  );
}

function EnvTemplateSection({ envTemplate }: Readonly<{ envTemplate: EnvTemplateResponse | null }>) {
  if (!envTemplate) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Environment Template" summary="A ready-to-export env template is generated by the live backend for the current tenant." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        File: <strong>{envTemplate.filename}</strong> | Optional keys: {envTemplate.include_optional ? 'included' : 'excluded'} | Configured keys:{' '}
        {envTemplate.include_configured ? 'included' : 'excluded'}
      </p>
      <p style={{ opacity: 0.82 }}>Providers included: {envTemplate.providers_included.join(', ')}</p>
      <p style={{ opacity: 0.82 }}>Missing keys: {envTemplate.missing_keys.length ? envTemplate.missing_keys.join(', ') : 'None'}</p>
      <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto', margin: 0, padding: 16, borderRadius: 12, background: '#f6f7fa' }}>
        {envTemplate.env_template}
      </pre>
    </section>
  );
}

function AutomationSection({ automation }: Readonly<{ automation: FullAutomationResponse | null }>) {
  if (!automation) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Automation Blueprint" summary="Full Semrush automation stitches keyword discovery, content gap analysis, backlink audit, and parity evidence together." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Run mode: <strong>{automation.run_mode ?? 'n/a'}</strong> | Vendor inventory: <strong>{automation.providers?.vendor_inventory?.length ?? 0}</strong>
      </p>
      {automation.results ? (
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
          <article className="card">
            <h4 style={{ marginTop: 0 }}>Keyword Discovery</h4>
            <p style={{ marginBottom: 0, opacity: 0.82 }}>
              Provider: {automation.results.keyword_discovery?.provider_selected ?? 'n/a'}
              <br />
              Keywords analyzed: {automation.results.keyword_discovery?.keywords_analyzed ?? 0}
              <br />
              Clusters found: {automation.results.keyword_discovery?.clusters_found ?? 0}
            </p>
          </article>
          <article className="card">
            <h4 style={{ marginTop: 0 }}>Content Gap</h4>
            <p style={{ marginBottom: 0, opacity: 0.82 }}>
              Opportunities: {automation.results.content_gap?.total_opportunities ?? 0}
              <br />
              High coverage gaps: {automation.results.content_gap?.high_coverage_gaps ?? 0}
            </p>
          </article>
          <article className="card">
            <h4 style={{ marginTop: 0 }}>Backlink Audit</h4>
            <p style={{ marginBottom: 0, opacity: 0.82 }}>
              Risk: {automation.results.backlink_audit?.risk_level ?? 'n/a'}
              <br />
              Toxic links: {automation.results.backlink_audit?.toxic_count ?? 0}
              <br />
              Suspicious links: {automation.results.backlink_audit?.suspicious_count ?? 0}
            </p>
          </article>
          <article className="card">
            <h4 style={{ marginTop: 0 }}>Backlink Gap</h4>
            <p style={{ marginBottom: 0, opacity: 0.82 }}>
              Unique opportunities: {automation.results.backlink_gap?.unique_opportunities ?? 0}
              <br />
              Competitors analyzed: {automation.results.backlink_gap?.competitors_analyzed ?? 0}
            </p>
          </article>
        </div>
      ) : null}

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

      {automation.providers?.vendor_inventory?.length ? (
        <>
          <h4>Third Parties And Vendors</h4>
          <ul className="bullet-list">
            {automation.providers.vendor_inventory.map((vendor) => (
              <li key={`${vendor.vendor}-${vendor.domain}`}>
                <strong>{vendor.vendor}</strong> - {vendor.capability} ({vendor.configured ? 'configured' : 'not configured'})
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function ProjectsRunsSection({ projects, runs }: Readonly<{ projects: Project[]; runs: Run[] }>) {
  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Projects And Runs" summary="The command center keeps project orchestration and execution history visible alongside the readiness controls." />
      <div className="grid">
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Projects</h4>
          {projects.length ? (
            <ul className="bullet-list">
              {projects.slice(-8).map((project) => (
                <li key={project.id}>
                  <strong>{project.name}</strong> ({project.primary_domain})
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ opacity: 0.8 }}>No projects yet.</p>
          )}
        </article>

        <article className="card">
          <h4 style={{ marginTop: 0 }}>Runs</h4>
          {runs.length ? (
            <ul className="bullet-list">
              {runs.slice(-8).map((run) => (
                <li key={run.id}>
                  <strong>{run.id}</strong> - strict probe: {run.strict_probe_status}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ opacity: 0.8 }}>No runs yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}

function useSemrushCommandCenter() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [bootstrap, setBootstrap] = useState<ProviderBootstrapResponse | null>(null);
  const [probes, setProbes] = useState<ProviderProbeResponse | null>(null);
  const [envTemplate, setEnvTemplate] = useState<EnvTemplateResponse | null>(null);
  const [automation, setAutomation] = useState<FullAutomationResponse | null>(null);
  const [bootstrapProviders, setBootstrapProviders] = useState(DEFAULT_BOOTSTRAP_PROVIDERS.join(', '));
  const [probeProviders, setProbeProviders] = useState(DEFAULT_PROBE_PROVIDERS.join(', '));

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData, parityData, checklistData] = await Promise.all([
        apiGet<ProjectsResponse>('/search-everywhere/semrush/projects', tenantId),
        apiGet<RunsResponse>('/search-everywhere/semrush/runs', tenantId),
        apiGet<ParityResponse>('/search-everywhere/semrush/parity-audit', tenantId),
        apiGet<ChecklistResponse>('/search-everywhere/semrush/provider-checklist', tenantId),
      ]);
      setProjects(projectData.projects || []);
      setRuns(runData.runs || []);
      setParity(parityData);
      setChecklist(checklistData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Semrush command center state');
    } finally {
      setLoading(false);
    }
  }

  async function createDemoProject() {
    setLoading(true);
    setError('');
    try {
      await apiSend('/search-everywhere/semrush/projects', 'POST', DEFAULT_PROJECT_PAYLOAD, tenantId);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
      setLoading(false);
    }
  }

  async function runLatestProject() {
    if (!projects.length) {
      setError('Create a Semrush project first.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const projectId = projects.at(-1)?.id;
      await apiSend(`/search-everywhere/semrush/projects/${projectId}/run`, 'POST', DEFAULT_RUN_PAYLOAD, tenantId);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run project');
      setLoading(false);
    }
  }

  async function runProductionGate() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<GateResponse>('/search-everywhere/semrush/production-gate', 'POST', DEFAULT_GATE_PAYLOAD, tenantId);
      setGate(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run production gate');
    } finally {
      setLoading(false);
    }
  }

  async function runProviderBootstrap() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<ProviderBootstrapResponse>(
        '/search-everywhere/semrush/provider-bootstrap',
        'POST',
        { providers: splitCsv(bootstrapProviders), include_configured: true },
        tenantId
      );
      setBootstrap(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to bootstrap providers');
    } finally {
      setLoading(false);
    }
  }

  async function runProviderProbes() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<ProviderProbeResponse>(
        '/search-everywhere/semrush/provider-probes',
        'POST',
        { providers: splitCsv(probeProviders), include_unconfigured: true, max_results: 5 },
        tenantId
      );
      setProbes(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run provider probes');
    } finally {
      setLoading(false);
    }
  }

  async function generateEnvTemplate() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<EnvTemplateResponse>(
        '/search-everywhere/semrush/env-template',
        'POST',
        { include_optional: true, include_configured: false },
        tenantId
      );
      setEnvTemplate(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate env template');
    } finally {
      setLoading(false);
    }
  }

  async function runFullAutomation() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<FullAutomationResponse>(
        '/search-everywhere/semrush/full-automation',
        'POST',
        {
          seed_keyword: DEFAULT_RUN_PAYLOAD.seed_keyword,
          your_domain: DEFAULT_GATE_PAYLOAD.your_domain,
          competitor_domains: DEFAULT_GATE_PAYLOAD.competitor_domains,
          max_results: DEFAULT_RUN_PAYLOAD.max_results,
          require_live_providers: false,
        },
        tenantId
      );
      setAutomation(result);
      if (result.production_gate) {
        setGate({
          status: result.status,
          gate: {
            passed: Boolean(result.production_gate.passed),
            implementation_ok: Boolean(result.production_gate.passed),
            integration_ok: Boolean(result.production_gate.passed),
            strict_probe_ok: Boolean(result.production_gate.passed),
            blockers: result.production_gate.blockers ?? [],
          },
        });
      }
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Semrush full automation');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return {
    loading,
    error,
    projects,
    runs,
    parity,
    checklist,
    gate,
    bootstrap,
    probes,
    envTemplate,
    automation,
    bootstrapProviders,
    setBootstrapProviders,
    probeProviders,
    setProbeProviders,
    refreshAll,
    createDemoProject,
    runLatestProject,
    runProductionGate,
    runProviderBootstrap,
    runProviderProbes,
    generateEnvTemplate,
    runFullAutomation,
  };
}

export default function SemrushCommandCenterPage() {
  const controller = useSemrushCommandCenter();

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Semrush Command Center</p>
        <h1>Semrush End-to-End SEO Operations</h1>
        <p>
          Live Semrush parity, provider readiness, production gate controls, provider bootstrap, provider probes, env template generation, and full automation execution in one frontend surface.
        </p>
      </section>

      <ActionToolbar
        loading={controller.loading}
        error={controller.error}
        onRefresh={() => void controller.refreshAll()}
        onCreateProject={() => void controller.createDemoProject()}
        onRunLatest={() => void controller.runLatestProject()}
        onGate={() => void controller.runProductionGate()}
        onBootstrap={() => void controller.runProviderBootstrap()}
        onProbes={() => void controller.runProviderProbes()}
        onEnvTemplate={() => void controller.generateEnvTemplate()}
        onAutomation={() => void controller.runFullAutomation()}
      />

      <QuickNavigation />

      <MetricsGrid parity={controller.parity} checklist={controller.checklist} gate={controller.gate} projects={controller.projects} runs={controller.runs} />
      <ParitySection parity={controller.parity} />
      <ChecklistSection checklist={controller.checklist} />
      <GateSection gate={controller.gate} />
      <InputPanels
        bootstrapProviders={controller.bootstrapProviders}
        onBootstrapProvidersChange={controller.setBootstrapProviders}
        probeProviders={controller.probeProviders}
        onProbeProvidersChange={controller.setProbeProviders}
      />
      <BootstrapSection bootstrap={controller.bootstrap} />
      <ProbeSection probes={controller.probes} />
      <EnvTemplateSection envTemplate={controller.envTemplate} />
      <AutomationSection automation={controller.automation} />
      <ProjectsRunsSection projects={controller.projects} runs={controller.runs} />
    </main>
  );
}