'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type ParityModuleRow = { module: string; implemented: boolean; coverage_pct: number; evidence: string[] };
type AhrefsCoreToolRow = {
  tool_key: string;
  tool_name: string;
  route_path: string;
  parity_module_key: string;
  counterpart_module_key: string;
  coverage_pct: number;
  vendors: string[];
};
type VendorInventoryRow = { domain: string; vendor: string; capability: string; configured: boolean; evidence: string };
type ChecklistItem = { provider: string; kind: string; configured: boolean; required_missing: string[] };

type ParityResponse = {
  status: string;
  ahrefs_parity_chart: ParityModuleRow[];
  ahrefs_core_tools: AhrefsCoreToolRow[];
  completion_chart?: {
    core_tools?: { done: number; total: number; pct: number };
    automation_layers?: { done: number; total: number; pct: number };
    provider_wiring?: { done: number; total: number; pct: number };
  };
  summary: {
    modules_total: number;
    modules_implemented: number;
    implementation_pct: number;
    integration_configured_units: number;
    integration_total_units: number;
    integration_configured_pct: number;
    core_tools_total: number;
    core_tools_fully_covered: number;
    core_tools_average_coverage_pct: number;
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

type E2EVerificationResponse = {
  status: string;
  framework: string;
  automation_endpoints: string[];
  provider_wiring_summary: { configured: number; total: number; configured_pct: number };
};

type GateResponse = {
  status: string;
  gate: { passed: boolean; implementation_ok: boolean; integration_ok: boolean; strict_probe_ok: boolean; blockers: string[] };
  strict_live_probe?: { status: string; run_mode?: string; provider_selected?: string; fallback_used?: boolean; reason?: string };
  provider_checklist_summary?: { configured: number; total: number; missing_requirements: Array<{ provider: string; required_missing: string[] }> };
};

type ProviderBootstrapResponse = {
  status: string;
  requested_providers: string[];
  steps_total: number;
  steps: Array<{ step: number; provider: string; kind: string; status: string; required_missing: string[] }>;
  next?: { run_checklist: string; run_gate: string };
};

type ProviderProbeResponse = {
  status: string;
  summary: { providers_requested: number; passed: number; failed: number; skipped: number; strict_live_ready: boolean };
  probes: Array<{ provider: string; status: string; configured?: boolean; reason?: string; error_code?: string }>;
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
    keyword_discovery?: { provider_selected?: string; fallback_used?: boolean; keywords_analyzed?: number; clusters_found?: number };
    content_gap?: { provider_selected?: string; fallback_used?: boolean; total_opportunities?: number; high_coverage_gaps?: number };
    backlink_overview?: { authority_score?: number; referring_domains?: number; toxic_count?: number; suspicious_count?: number };
    backlink_audit?: { risk_level?: string; overall_risk_pct?: number; toxic_count?: number; suspicious_count?: number };
    backlink_gap?: { unique_opportunities?: number; competitors_analyzed?: number };
    rank_tracking?: {
      tracked_keywords?: number;
      improved_30d?: number;
      dropped_30d?: number;
      top_10?: number;
      top_3?: number;
      visibility_score?: number;
      estimated_monthly_traffic?: number;
      history_days?: number;
      gained_keywords?: number;
      lost_keywords?: number;
      forecast_buckets?: number;
      daily_improvements?: number;
    };
  };
  providers?: { vendor_inventory?: VendorInventoryRow[] };
  how_it_works?: Array<{ stage: number; name: string; description: string } | string>;
};

const DEFAULT_GATE_PAYLOAD = {
  seed_keyword: 'seo analytics',
  your_domain: 'nuxtron.ai',
  competitor_domains: ['semrush.com', 'moz.com', 'ahrefs.com'],
  max_results: 10,
};

const DEFAULT_AUTOMATION_PAYLOAD = {
  seed_keyword: 'seo analytics',
  your_domain: 'nuxtron.ai',
  competitor_domains: ['semrush.com', 'moz.com', 'ahrefs.com'],
  location: 'United States',
  language: 'en',
  include_questions: true,
  max_results: 12,
  require_live_providers: false,
};

const DEFAULT_BOOTSTRAP_PROVIDERS = ['DataForSEO', 'Serper.dev', 'Google Ads Keyword Planner', 'Google Search Console'];
const DEFAULT_PROBE_PROVIDERS = ['dataforseo', 'serper', 'google_keyword_planner', 'google_search_console'];

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
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

function SectionTitle({ title, summary }: Readonly<{ title: string; summary: string }>) {
  return (
    <div style={{ marginBottom: 12 }}>
      <h3 style={{ marginTop: 0, marginBottom: 6 }}>{title}</h3>
      <p style={{ margin: 0, opacity: 0.82 }}>{summary}</p>
    </div>
  );
}

function getGateStateLabel(gate: GateResponse | null): string {
  if (gate?.gate.passed === true) return 'PASSED';
  if (gate?.gate.passed === false) return 'FAILED';
  return 'Not run';
}

function ActionToolbar({
  loading,
  error,
  onRefresh,
  onGate,
  onBootstrap,
  onProbes,
  onEnvTemplate,
  onAutomation,
}: Readonly<{
  loading: boolean;
  error: string;
  onRefresh: () => void;
  onGate: () => void;
  onBootstrap: () => void;
  onProbes: () => void;
  onEnvTemplate: () => void;
  onAutomation: () => void;
}>) {
  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Control Actions" summary="These controls call live Ahrefs backend automation endpoints. Runtime UI does not inject mocked data." />
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button onClick={onRefresh} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
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
    { href: '/seo/site-explorer', title: 'Site Explorer', summary: 'Domain intelligence, backlink snapshots, and competitive reconnaissance.' },
    { href: '/seo/keywords-explorer', title: 'Keywords Explorer', summary: 'Keyword clustering, opportunity scores, and SERP surface analysis.' },
    { href: '/seo/site-audit', title: 'Site Audit', summary: 'Technical crawling, issue classes, and patch-ready remediation workflows.' },
    { href: '/seo/rank-tracker', title: 'Rank Tracker', summary: 'Position trends, volatility readouts, and forecast-aware monitoring.' },
    { href: '/seo/content-explorer', title: 'Content Explorer', summary: 'Topic expansion, content gap deltas, and editorial targeting insights.' },
    { href: '/seo/report-builder', title: 'Report Builder', summary: 'Executive reporting workflows and export-ready stakeholder outputs.' },
  ];

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Quick Navigation" summary="Ahrefs parity routes mapped to live Nuxtron capabilities." />
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
  verification,
  gate,
}: Readonly<{
  parity: ParityResponse | null;
  checklist: ChecklistResponse | null;
  verification: E2EVerificationResponse | null;
  gate: GateResponse | null;
}>) {
  const gateState = getGateStateLabel(gate);
  const done = parity?.completion_chart?.core_tools?.done ?? parity?.summary.core_tools_fully_covered ?? 0;
  const total = parity?.completion_chart?.core_tools?.total ?? parity?.summary.core_tools_total ?? 0;

  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <StatCard label="Core Tools" value={`${done}/${total}`} sub="Ahrefs tool parity" />
      <StatCard label="Automation Layers" value={parity ? `${parity.summary.modules_implemented}/${parity.summary.modules_total}` : '...'} sub="E2E logic layers" />
      <StatCard label="Provider Wiring" value={checklist ? `${checklist.configured_pct}%` : '...'} sub="Configured provider checklist" />
      <StatCard label="E2E Endpoints" value={String(verification?.automation_endpoints?.length ?? 0)} sub="Automation APIs discovered" />
      <StatCard label="Production Gate" value={gateState} sub="Strict live readiness" />
      <StatCard label="Vendors Tracked" value={String(parity?.vendor_inventory?.length ?? 0)} sub="Third-party inventory" />
    </section>
  );
}

function ParitySection({ parity }: Readonly<{ parity: ParityResponse | null }>) {
  if (!parity) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Ahrefs Parity Chart" summary="Coverage status for the core automation layers." />
      <p style={{ opacity: 0.82, marginTop: 0 }}>{parity.validation_note ?? 'Parity reflects backend feature and wiring status.'}</p>
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
            {parity.ahrefs_parity_chart.map((row) => (
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

function CoreToolsSection({ parity }: Readonly<{ parity: ParityResponse | null }>) {
  if (!parity) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Core Tool Coverage" summary="Tool-by-tool route coverage and counterpart mapping." />
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Tool</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Route</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Coverage</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Vendors</th>
            </tr>
          </thead>
          <tbody>
            {parity.ahrefs_core_tools.map((row) => (
              <tr key={row.tool_key} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{row.tool_name}</td>
                <td style={{ padding: '8px 6px' }}>{row.route_path}</td>
                <td style={{ padding: '8px 6px' }}>{row.coverage_pct}%</td>
                <td style={{ padding: '8px 6px' }}>{row.vendors.join(', ') || 'n/a'}</td>
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
      <SectionTitle title="Provider Checklist" summary="Provider readiness, missing environment variables, and wiring gaps." />
      <p style={{ opacity: 0.82, marginTop: 0 }}>
        {checklist.configured}/{checklist.total} configured ({checklist.configured_pct}%)
      </p>
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

function VerificationSection({ verification }: Readonly<{ verification: E2EVerificationResponse | null }>) {
  if (!verification) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="E2E Verification Surface" summary="Automation endpoints and provider wiring status published by the backend." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Framework: {verification.framework} | Provider wiring: {verification.provider_wiring_summary.configured}/{verification.provider_wiring_summary.total} ({verification.provider_wiring_summary.configured_pct}%)
      </p>
      <ul className="bullet-list">
        {verification.automation_endpoints.map((endpoint) => (
          <li key={endpoint}>{endpoint}</li>
        ))}
      </ul>
    </section>
  );
}

function GateSection({ gate }: Readonly<{ gate: GateResponse | null }>) {
  if (!gate) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Production Gate" summary="Gate requires implementation parity, wiring parity, and strict live probe success." />
      <p style={{ marginTop: 0 }}>
        Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong> | Implementation: <strong>{gate.gate.implementation_ok ? 'Yes' : 'No'}</strong> | Integration: <strong>{gate.gate.integration_ok ? 'Yes' : 'No'}</strong> | Strict probe:{' '}
        <strong>{gate.gate.strict_probe_ok ? 'Yes' : 'No'}</strong>
      </p>
      {gate.strict_live_probe ? (
        <p style={{ opacity: 0.82 }}>
          Strict probe status: {gate.strict_live_probe.status}
          {gate.strict_live_probe.provider_selected ? ` | provider: ${gate.strict_live_probe.provider_selected}` : ''}
          {gate.strict_live_probe.reason ? ` | reason: ${gate.strict_live_probe.reason}` : ''}
        </p>
      ) : null}
      {gate.gate.blockers.length ? (
        <ul className="bullet-list">
          {gate.gate.blockers.map((blocker) => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
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
        <SectionTitle title="Provider Bootstrap Inputs" summary="Providers to include while generating the bootstrap plan." />
        <input
          value={bootstrapProviders}
          onChange={(event) => onBootstrapProvidersChange(event.target.value)}
          style={{ width: '100%', padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,0.25)' }}
        />
      </article>
      <article className="card">
        <SectionTitle title="Provider Probe Inputs" summary="Providers to probe for strict live readiness." />
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
      <SectionTitle title="Provider Bootstrap" summary="Actionable provider bootstrap steps generated by backend contracts." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        {bootstrap.steps_total} steps for {bootstrap.requested_providers.length} requested providers.
      </p>
      {bootstrap.next ? <p style={{ opacity: 0.82 }}>Next: {bootstrap.next.run_checklist} then {bootstrap.next.run_gate}</p> : null}
      <ul className="bullet-list">
        {bootstrap.steps.slice(0, 12).map((step) => (
          <li key={`${step.provider}-${step.kind}-${step.step}`}>
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
      <SectionTitle title="Provider Probes" summary="Live provider probe summary and strict readiness state." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Requested: {probes.summary.providers_requested} | Passed: {probes.summary.passed} | Failed: {probes.summary.failed} | Skipped: {probes.summary.skipped} | Strict live ready:{' '}
        {probes.summary.strict_live_ready ? 'Yes' : 'No'}
      </p>
      <ul className="bullet-list">
        {probes.probes.slice(0, 12).map((probe) => (
          <li key={`${probe.provider}-${probe.status}`}>
            <strong>{probe.provider}</strong> - {probe.status}
            {probe.reason ? ` (${probe.reason})` : ''}
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
      <SectionTitle title="Environment Template" summary="Backend-generated env template for provider wiring and production readiness." />
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

  const rank = automation.results?.rank_tracking;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Automation Blueprint" summary="Full Ahrefs workflow: discovery, content gap, backlink intelligence, rank visibility, and readiness checks." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Run mode: <strong>{automation.run_mode ?? 'n/a'}</strong> | Vendor inventory: <strong>{automation.providers?.vendor_inventory?.length ?? 0}</strong>
      </p>

      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Keyword Discovery</h4>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Provider: {automation.results?.keyword_discovery?.provider_selected ?? 'n/a'}
            <br />
            Keywords analyzed: {automation.results?.keyword_discovery?.keywords_analyzed ?? 0}
            <br />
            Clusters found: {automation.results?.keyword_discovery?.clusters_found ?? 0}
          </p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Content Gap</h4>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Opportunities: {automation.results?.content_gap?.total_opportunities ?? 0}
            <br />
            High coverage gaps: {automation.results?.content_gap?.high_coverage_gaps ?? 0}
          </p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Backlink Audit</h4>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Risk: {automation.results?.backlink_audit?.risk_level ?? 'n/a'}
            <br />
            Toxic links: {automation.results?.backlink_audit?.toxic_count ?? 0}
            <br />
            Suspicious links: {automation.results?.backlink_audit?.suspicious_count ?? 0}
          </p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Rank Tracking</h4>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Tracked keywords: {rank?.tracked_keywords ?? 0}
            <br />
            Visibility score: {rank?.visibility_score ?? 0}
            <br />
            Top 10 keywords: {rank?.top_10 ?? 0}
          </p>
        </article>
      </div>

      {automation.how_it_works?.length ? (
        <>
          <h4>How It Works</h4>
          <ul className="bullet-list">
            {automation.how_it_works.map((item) => {
              if (typeof item === 'string') {
                return <li key={item}>{item}</li>;
              }
              return (
                <li key={`${item.stage}-${item.name}`}>
                  <strong>Stage {item.stage}: {item.name}</strong> - {item.description}
                </li>
              );
            })}
          </ul>
        </>
      ) : null}

      {automation.providers?.vendor_inventory?.length ? (
        <>
          <h4>Third Parties And Vendors</h4>
          <ul className="bullet-list">
            {automation.providers.vendor_inventory.map((vendor) => (
              <li key={`${vendor.vendor}-${vendor.domain}-${vendor.capability}`}>
                <strong>{vendor.vendor}</strong> - {vendor.capability} ({vendor.configured ? 'configured' : 'not configured'})
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function useAhrefsCommandCenter() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [verification, setVerification] = useState<E2EVerificationResponse | null>(null);
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
      const [parityData, checklistData, verificationData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/ahrefs/parity-audit', tenantId),
        apiGet<ChecklistResponse>('/search-everywhere/ahrefs/provider-checklist', tenantId),
        apiGet<E2EVerificationResponse>('/search-everywhere/ahrefs/e2e-verification', tenantId),
      ]);
      setParity(parityData);
      setChecklist(checklistData);
      setVerification(verificationData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Ahrefs command center state');
    } finally {
      setLoading(false);
    }
  }

  async function runProductionGate() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<GateResponse>('/search-everywhere/ahrefs/production-gate', 'POST', DEFAULT_GATE_PAYLOAD, tenantId);
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
        '/search-everywhere/ahrefs/provider-bootstrap',
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
        '/search-everywhere/ahrefs/provider-probes',
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
        '/search-everywhere/ahrefs/env-template',
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
      const result = await apiSend<FullAutomationResponse>('/search-everywhere/ahrefs/full-automation', 'POST', DEFAULT_AUTOMATION_PAYLOAD, tenantId);
      setAutomation(result);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Ahrefs full automation');
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return {
    loading,
    error,
    parity,
    checklist,
    verification,
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
    runProductionGate,
    runProviderBootstrap,
    runProviderProbes,
    generateEnvTemplate,
    runFullAutomation,
  };
}

export default function AhrefsCommandCenterPage() {
  const controller = useAhrefsCommandCenter();

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Ahrefs Command Center</p>
        <h1>Ahrefs End-to-End SEO Operations</h1>
        <p>
          End-to-end Ahrefs parity, provider readiness, strict production gate controls, full automation wiring, and vendor visibility in one frontend workspace.
        </p>
      </section>

      <ActionToolbar
        loading={controller.loading}
        error={controller.error}
        onRefresh={() => void controller.refreshAll()}
        onGate={() => void controller.runProductionGate()}
        onBootstrap={() => void controller.runProviderBootstrap()}
        onProbes={() => void controller.runProviderProbes()}
        onEnvTemplate={() => void controller.generateEnvTemplate()}
        onAutomation={() => void controller.runFullAutomation()}
      />

      <QuickNavigation />
      <MetricsGrid parity={controller.parity} checklist={controller.checklist} verification={controller.verification} gate={controller.gate} />
      <ParitySection parity={controller.parity} />
      <CoreToolsSection parity={controller.parity} />
      <ChecklistSection checklist={controller.checklist} />
      <VerificationSection verification={controller.verification} />
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
    </main>
  );
}
