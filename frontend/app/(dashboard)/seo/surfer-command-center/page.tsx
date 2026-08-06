'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type ParityModuleRow = { module: string; implemented: boolean; coverage_pct: number; evidence: string[] };
type VendorInventoryRow = { vendor: string; module: string; type: string; configured: boolean; evidence: string };
type ChecklistItem = {
  provider: string;
  kind: string;
  configured: boolean;
  required_missing: string[];
  remediation: string;
};

type ParityResponse = {
  status: string;
  surfer_parity_chart: ParityModuleRow[];
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

type WiringRow = {
  provider: string;
  kind: string;
  priority: 'P0' | 'P1' | 'P2';
  gate_impact_score: number;
  integration_pct_if_added: number;
  required_missing: string[];
  rationale: string;
};

type WiringPlanResponse = {
  status: string;
  wiring_plan: {
    configured: number;
    total: number;
    integration_configured_pct: number;
    stages: {
      stage_1_strict_live_foundation: { providers: string[] };
      stage_2_runtime_reliability: { providers: string[] };
      stage_3_full_automation_coverage: { providers: string[] };
    };
    prioritized_missing_providers: WiringRow[];
  };
};

type SetupPlaybookProvider = {
  provider: string;
  priority: 'P0' | 'P1' | 'P2';
  kind: string;
  gate_impact_score: number;
  integration_pct_if_added: number;
  required_missing: string[];
  setup_notes: string[];
  preflight_commands_powershell: string[];
  verify_with: string[];
};

type SetupPlaybookResponse = {
  status: string;
  setup_playbook: {
    summary: {
      configured: number;
      total: number;
      integration_configured_pct: number;
    };
    providers: SetupPlaybookProvider[];
    final_validation: string[];
  };
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
  steps: Array<{ provider: string; kind: string; required_missing: string[] }>;
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
    keyword_discovery?: {
      provider_selected?: string;
      fallback_used?: boolean;
      keywords_analyzed?: number;
      clusters_found?: number;
    };
    content_gap?: {
      provider_selected?: string;
      fallback_used?: boolean;
      total_opportunities?: number;
      high_coverage_gaps?: number;
    };
    backlink_audit?: { risk_level?: string; overall_risk_pct?: number; toxic_count?: number; suspicious_count?: number };
    backlink_gap?: { unique_opportunities?: number; competitors_analyzed?: number };
    parity_summary?: {
      modules_total?: number;
      modules_implemented?: number;
      implementation_pct?: number;
      integration_configured_units?: number;
      integration_total_units?: number;
      integration_configured_pct?: number;
    };
  };
  providers?: {
    keyword_discovery_attempts?: Array<{ provider: string; status?: string }>;
    content_gap_attempts?: Array<{ provider: string; status?: string }>;
    vendor_inventory?: VendorInventoryRow[];
  };
};

const DEFAULT_GATE_PAYLOAD = {
  seed_keyword: 'social media management',
  your_domain: 'nuxtron.ai',
  competitor_domains: ['semrush.com', 'ahrefs.com', 'moz.com'],
  max_results: 12,
};

const DEFAULT_AUTOMATION_PAYLOAD = {
  seed_keyword: 'social media management',
  your_domain: 'nuxtron.ai',
  competitor_domains: ['semrush.com', 'ahrefs.com', 'moz.com'],
  location: 'United States',
  language: 'en',
  include_questions: true,
  max_results: 12,
  require_live_providers: false,
};

const DEFAULT_BOOTSTRAP_PROVIDERS = ['DataForSEO', 'Serper.dev', 'Google Ads Keyword Planner', 'Google Search Console'];
const DEFAULT_PROBE_PROVIDERS = ['dataforseo', 'serper', 'google_keyword_planner', 'google_search_console'];

const STATIC_HOW_IT_WORKS = [
  'Keyword discovery starts with provider-backed research and clustering.',
  'Content gap analysis compares your domain against competitors to prioritize opportunities.',
  'Backlink audit and backlink gap workflows quantify authority risk and net-new links.',
  'Production gate enforces implementation parity, integration parity, and strict live probe success.',
];

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
      <SectionTitle
        title="Control Actions"
        summary="These controls call live Surfer backend automation endpoints. Runtime UI does not inject mocked data."
      />
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
        <button onClick={onGate} disabled={loading}>
          {loading ? 'Checking...' : 'Run Production Gate'}
        </button>
        <button onClick={onBootstrap} disabled={loading}>
          {loading ? 'Bootstrapping...' : 'Bootstrap Providers'}
        </button>
        <button onClick={onProbes} disabled={loading}>
          {loading ? 'Probing...' : 'Probe Providers'}
        </button>
        <button onClick={onEnvTemplate} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Env Template'}
        </button>
        <button onClick={onAutomation} disabled={loading}>
          {loading ? 'Executing...' : 'Run Full Automation Blueprint'}
        </button>
      </div>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
    </section>
  );
}

function QuickNavigation() {
  const links = [
    {
      href: '/seo/surfer-readiness',
      title: 'Surfer Readiness Hub',
      summary: 'Parity and production gate status in one summary view.',
    },
    {
      href: '/seo/surfer-wiring-plan',
      title: 'Surfer Wiring Plan',
      summary: 'Priority sequencing for strict-live provider readiness.',
    },
    {
      href: '/seo/surfer-setup-playbook',
      title: 'Surfer Setup Playbook',
      summary: 'Provider setup notes, PowerShell preflight, and verification endpoints.',
    },
    {
      href: '/seo/content-auditor',
      title: 'Content Auditor',
      summary: 'Content auditing and refresh workflows used in Surfer parity mapping.',
    },
  ];

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Quick Navigation" summary="Surfer command-center routes and adjacent SEO execution workspaces." />
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
  wiring,
  gate,
}: Readonly<{
  parity: ParityResponse | null;
  checklist: ChecklistResponse | null;
  wiring: WiringPlanResponse | null;
  gate: GateResponse | null;
}>) {
  const stageCount = wiring
    ? [
        wiring.wiring_plan.stages.stage_1_strict_live_foundation.providers.length,
        wiring.wiring_plan.stages.stage_2_runtime_reliability.providers.length,
        wiring.wiring_plan.stages.stage_3_full_automation_coverage.providers.length,
      ].filter((count) => count > 0).length
    : 0;

  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <StatCard
        label="Implementation"
        value={parity ? `${parity.summary.modules_implemented}/${parity.summary.modules_total}` : '...'}
        sub="Surfer parity modules"
      />
      <StatCard
        label="Integration Wiring"
        value={parity ? `${parity.summary.integration_configured_pct}%` : '...'}
        sub="Configured provider coverage"
      />
      <StatCard
        label="Provider Checklist"
        value={checklist ? `${checklist.configured_pct}%` : '...'}
        sub="Tenant provider readiness"
      />
      <StatCard label="Production Gate" value={getGateStateLabel(gate)} sub="Strict live readiness" />
      <StatCard label="Wiring Stages" value={String(stageCount)} sub="Active staged remediation groups" />
      <StatCard label="Vendors Tracked" value={String(parity?.vendor_inventory?.length ?? 0)} sub="Third-party inventory rows" />
    </section>
  );
}

function ParitySection({ parity }: Readonly<{ parity: ParityResponse | null }>) {
  if (!parity) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Surfer Parity Chart" summary="Feature implementation and evidence rows pulled from the live Surfer parity endpoint." />
      <p style={{ opacity: 0.82, marginTop: 0 }}>{parity.validation_note ?? 'Parity reflects live backend feature coverage and wiring state.'}</p>
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
            {parity.surfer_parity_chart.map((row) => (
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
      <SectionTitle title="Provider Checklist" summary="Provider readiness, missing requirements, and remediation guidance." />
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
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Remediation</th>
            </tr>
          </thead>
          <tbody>
            {checklist.checklist.map((item) => (
              <tr key={item.provider} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{item.provider}</td>
                <td style={{ padding: '8px 6px' }}>{item.kind}</td>
                <td style={{ padding: '8px 6px' }}>{item.configured ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{item.required_missing.length ? item.required_missing.join(', ') : 'None'}</td>
                <td style={{ padding: '8px 6px' }}>{item.remediation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function WiringPlanSection({ wiring }: Readonly<{ wiring: WiringPlanResponse | null }>) {
  if (!wiring) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Wiring Plan" summary="Priority staging from strict-live foundation to full automation coverage." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Configured providers: {wiring.wiring_plan.configured}/{wiring.wiring_plan.total} ({wiring.wiring_plan.integration_configured_pct}%)
      </p>
      <ul className="bullet-list">
        <li>
          <strong>Stage 1 (strict live foundation):</strong>{' '}
          {wiring.wiring_plan.stages.stage_1_strict_live_foundation.providers.join(', ') || 'none'}
        </li>
        <li>
          <strong>Stage 2 (runtime reliability):</strong>{' '}
          {wiring.wiring_plan.stages.stage_2_runtime_reliability.providers.join(', ') || 'none'}
        </li>
        <li>
          <strong>Stage 3 (full automation coverage):</strong>{' '}
          {wiring.wiring_plan.stages.stage_3_full_automation_coverage.providers.join(', ') || 'none'}
        </li>
      </ul>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Provider</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Priority</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Impact</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Next Integration %</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Missing</th>
            </tr>
          </thead>
          <tbody>
            {wiring.wiring_plan.prioritized_missing_providers.slice(0, 20).map((row) => (
              <tr key={row.provider} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{row.provider}</td>
                <td style={{ padding: '8px 6px' }}>{row.priority}</td>
                <td style={{ padding: '8px 6px' }}>{row.gate_impact_score}</td>
                <td style={{ padding: '8px 6px' }}>{row.integration_pct_if_added}%</td>
                <td style={{ padding: '8px 6px' }}>{row.required_missing.join(', ') || 'None'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SetupPlaybookSection({ playbook }: Readonly<{ playbook: SetupPlaybookResponse | null }>) {
  if (!playbook) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Setup Playbook" summary="Provider-by-provider setup notes, PowerShell preflight commands, and endpoint-level verification guidance." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Configured providers: {playbook.setup_playbook.summary.configured}/{playbook.setup_playbook.summary.total} ({playbook.setup_playbook.summary.integration_configured_pct}%)
      </p>
      {playbook.setup_playbook.providers.length ? (
        <>
          <h4>Top Priority Provider</h4>
          <p style={{ marginTop: 0, opacity: 0.82 }}>
            <strong>{playbook.setup_playbook.providers[0].provider}</strong> ({playbook.setup_playbook.providers[0].priority})
          </p>
          <ul className="bullet-list">
            {playbook.setup_playbook.providers[0].setup_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              overflowX: 'auto',
              margin: 0,
              padding: 16,
              borderRadius: 12,
              background: '#f6f7fa',
            }}
          >
            {playbook.setup_playbook.providers[0].preflight_commands_powershell.join('\n')}
          </pre>
        </>
      ) : (
        <p style={{ opacity: 0.82, marginBottom: 0 }}>No missing providers remain in the playbook.</p>
      )}

      {playbook.setup_playbook.final_validation.length ? (
        <>
          <h4 style={{ marginTop: 14 }}>Final Validation Endpoints</h4>
          <ul className="bullet-list">
            {playbook.setup_playbook.final_validation.map((endpoint) => (
              <li key={endpoint}>{endpoint}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function GateSection({ gate }: Readonly<{ gate: GateResponse | null }>) {
  if (!gate) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle title="Production Gate" summary="Gate requires implementation parity, integration parity, and strict live probe success." />
      <p style={{ marginTop: 0 }}>
        Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong> | Implementation: <strong>{gate.gate.implementation_ok ? 'Yes' : 'No'}</strong> | Integration:{' '}
        <strong>{gate.gate.integration_ok ? 'Yes' : 'No'}</strong> | Strict probe: <strong>{gate.gate.strict_probe_ok ? 'Yes' : 'No'}</strong>
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
      {gate.provider_checklist_summary ? (
        <p style={{ marginBottom: 0, opacity: 0.82 }}>
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
        {bootstrap.steps.slice(0, 20).map((step) => (
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
      <SectionTitle title="Provider Probes" summary="Live provider probe summary and strict readiness state." />
      <p style={{ marginTop: 0, opacity: 0.82 }}>
        Requested: {probes.summary.providers_requested} | Passed: {probes.summary.passed} | Failed: {probes.summary.failed} | Skipped: {probes.summary.skipped} | Strict live ready:{' '}
        {probes.summary.strict_live_ready ? 'Yes' : 'No'}
      </p>
      <ul className="bullet-list">
        {probes.probes.slice(0, 20).map((probe) => (
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

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <SectionTitle
        title="Automation Blueprint"
        summary="Full Surfer workflow across keyword discovery, content gap, backlink analysis, and parity verification."
      />
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
            Provider: {automation.results?.content_gap?.provider_selected ?? 'n/a'}
            <br />
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
          <h4 style={{ marginTop: 0 }}>Backlink Gap</h4>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Unique opportunities: {automation.results?.backlink_gap?.unique_opportunities ?? 0}
            <br />
            Competitors analyzed: {automation.results?.backlink_gap?.competitors_analyzed ?? 0}
          </p>
        </article>
      </div>

      <h4>How It Works</h4>
      <ul className="bullet-list">
        {STATIC_HOW_IT_WORKS.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      {automation.providers?.vendor_inventory?.length ? (
        <>
          <h4>Third Parties And Vendors</h4>
          <ul className="bullet-list">
            {automation.providers.vendor_inventory.map((vendor) => (
              <li key={`${vendor.vendor}-${vendor.module}-${vendor.type}`}>
                <strong>{vendor.vendor}</strong> - {vendor.module} ({vendor.configured ? 'configured' : 'not configured'})
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function useSurferCommandCenter() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [wiring, setWiring] = useState<WiringPlanResponse | null>(null);
  const [playbook, setPlaybook] = useState<SetupPlaybookResponse | null>(null);
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
      const [parityData, checklistData, wiringData, playbookData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/surfer/parity-audit', tenantId),
        apiGet<ChecklistResponse>('/search-everywhere/surfer/provider-checklist', tenantId),
        apiGet<WiringPlanResponse>('/search-everywhere/surfer/wiring-plan', tenantId),
        apiGet<SetupPlaybookResponse>('/search-everywhere/surfer/setup-playbook', tenantId),
      ]);
      setParity(parityData);
      setChecklist(checklistData);
      setWiring(wiringData);
      setPlaybook(playbookData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Surfer command center state');
    } finally {
      setLoading(false);
    }
  }

  async function runProductionGate() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<GateResponse>('/search-everywhere/surfer/production-gate', 'POST', DEFAULT_GATE_PAYLOAD, tenantId);
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
        '/search-everywhere/surfer/provider-bootstrap',
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
        '/search-everywhere/surfer/provider-probes',
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
        '/search-everywhere/surfer/env-template',
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
      const result = await apiSend<FullAutomationResponse>('/search-everywhere/surfer/full-automation', 'POST', DEFAULT_AUTOMATION_PAYLOAD, tenantId);
      setAutomation(result);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Surfer full automation');
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
    wiring,
    playbook,
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

export default function SurferCommandCenterPage() {
  const controller = useSurferCommandCenter();

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Surfer Command Center</p>
        <h1>Surfer End-to-End SEO Operations</h1>
        <p>
          End-to-end Surfer parity, provider readiness, strict production gate controls, setup playbook wiring, and full automation execution in one frontend workspace.
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
      <MetricsGrid parity={controller.parity} checklist={controller.checklist} wiring={controller.wiring} gate={controller.gate} />
      <ParitySection parity={controller.parity} />
      <ChecklistSection checklist={controller.checklist} />
      <WiringPlanSection wiring={controller.wiring} />
      <SetupPlaybookSection playbook={controller.playbook} />
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
