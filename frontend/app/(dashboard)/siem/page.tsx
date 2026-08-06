'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import AnalyticsExecutiveBoard from '@/app/components/analytics-executive-board';
import { PageHeader } from '../_ui/kit';

// Maps this page's legacy theme variables onto the shared dashboard tokens so
// its inline styles inherit the consistent palette without a per-node rewrite.
const siemThemeVars: React.CSSProperties = {
  ['--bg' as string]: 'var(--nx-bg)',
  ['--bg-soft' as string]: 'var(--nx-card)',
  ['--text' as string]: 'var(--nx-ink)',
  ['--muted' as string]: 'var(--nx-muted)',
  ['--line' as string]: 'var(--nx-border)',
  ['--brand' as string]: 'var(--nx-brand)',
  ['--brand-2' as string]: 'var(--nx-brand-2)',
  fontFamily: 'var(--nx-font)',
};

type DataCollectionPayload = {
  telemetry: {
    endpoints_servers_network_devices: {
      endpoint_count: number;
      server_events: number;
      network_events: number;
    };
    cloud_platforms: Record<string, boolean>;
    saas_apps: Record<string, number>;
    identity_systems: { auth_events: number; tenant_profiles: number };
    third_party_security_tools: Record<string, number>;
  };
  high_volume_ingestion: { ingested_events_total: number };
};

type DetectionPayload = {
  rule_based_correlation: {
    top_endpoints: Array<{ endpoint: string; events: number }>;
    triggered_rules: Array<{ ip: string; event_count: number; rule: string }>;
  };
  ml_anomaly_detection: {
    anomaly_score: number;
    state: string;
    recent_event_volume: number;
  };
  behavior_analytics_ueba: {
    top_actors: Array<{ actor: string; events: number }>;
    severity_distribution: Record<string, number>;
  };
  threat_intelligence_enrichment: {
    matches: Array<{ ip: string; events: number; threat: string; confidence: number }>;
  };
};

type CaseItem = {
  id: number;
  title: string;
  severity: string;
  status: string;
  assignee: string;
  updated_at: string;
};

type CasesPayload = { cases: CaseItem[] };

type InvestigationPayload = {
  results: Array<{ source: string; title: string; actor: string; ip: string; timestamp: string }>;
  attack_path_reconstruction: Array<{ step: number; source: string; title: string; timestamp: string }>;
  soar_automation: { run_count: number };
};

type CompliancePayload = {
  audit_logs: { count: number };
  prebuilt_compliance_reports: Array<{ framework: string; status: string; controls_mapped: number }>;
  retention_policies: { hot_days: number; warm_days: number; cold_days: number; immutable_audit: boolean };
};

type ArchitecturePayload = {
  scalability_architecture: {
    deployment_mode: string;
    data_lake_support: { enabled: boolean; exports: Array<{ sink: string; format: string; status: string }> };
    high_volume_ingestion: {
      events_ingested_total: number;
      estimated_eps_capacity: number;
      multi_region_ready: boolean;
    };
  };
};

type FlowNode = { id: string; total_bytes: number };
type FlowEdge = { source: string; target: string; bytes: number; packets: number; flow_count: number };
type FlowsPayload = {
  flow_count: number;
  graph: { nodes: FlowNode[]; edges: FlowEdge[] };
  analytics: {
    risk_distribution: Record<string, number>;
    action_distribution: Record<string, number>;
    events_timeline: Array<{ bucket: string; events: number }>;
    top_talkers: Array<{ id: string; total_bytes: number }>;
  };
};

type Control = {
  id: number;
  name: string;
  enabled: boolean;
  mode?: string;
  action?: string;
  threshold?: number;
  updated_at?: string;
};

type ControlsPayload = {
  posture_score: number;
  waf: Control[];
  firewall: Control[];
  ids: Control[];
  ips: Control[];
  summary: { controls_total: number; controls_enabled: number; controls_disabled: number };
};

type Vulnerability = {
  id: number;
  cve: string;
  asset: string;
  severity: string;
  cvss: number;
  status: string;
  source: string;
  updated_at: string;
};

type VulnerabilitiesPayload = {
  count: number;
  total: number;
  severity_distribution: Record<string, number>;
  items: Vulnerability[];
};

type UpdateItem = {
  id: number;
  component: string;
  version: string;
  risk_level: string;
  status: string;
  window: string;
  updated_at: string;
};

type UpdatesPayload = { count: number; items: UpdateItem[] };

function TinyBars({ data, emptyLabel }: { data: Record<string, number>; emptyLabel: string }) {
  const entries = Object.entries(data);
  const max = entries.reduce((acc, [, value]) => Math.max(acc, value), 1);
  if (!entries.length) return <div style={{ fontSize: 12, color: 'var(--muted)' }}>{emptyLabel}</div>;
  return (
    <div style={{ display: 'grid', gap: 6 }}>
      {entries.map(([label, value]) => (
        <div
          key={label}
          style={{ display: 'grid', gridTemplateColumns: '120px 1fr 48px', alignItems: 'center', gap: 8 }}
        >
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>{label}</span>
          <div style={{ height: 8, background: 'var(--line)', borderRadius: 999 }}>
            <div
              style={{
                width: `${Math.max(4, (value / max) * 100)}%`,
                height: '100%',
                background: 'var(--brand)',
                borderRadius: 999,
              }}
            />
          </div>
          <span style={{ fontSize: 11, textAlign: 'right' }}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function TinyLine({ points }: { points: Array<{ bucket: string; events: number }> }) {
  if (!points.length) return <div style={{ fontSize: 12, color: 'var(--muted)' }}>No timeline points yet.</div>;
  const width = 540;
  const height = 120;
  const maxY = Math.max(1, ...points.map((p) => p.events));
  const stepX = points.length > 1 ? width / (points.length - 1) : width;
  const path = points
    .map((p, idx) => {
      const x = idx * stepX;
      const y = height - (p.events / maxY) * height;
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: '100%', maxWidth: width, height: 120, overflow: 'visible' }}
    >
      <path d={path} fill="none" stroke="var(--brand)" strokeWidth="2" />
      {points.map((p, idx) => {
        const x = idx * stepX;
        const y = height - (p.events / maxY) * height;
        return <circle key={`${p.bucket}-${idx}`} cx={x} cy={y} r={2.5} fill="var(--brand)" />;
      })}
    </svg>
  );
}

export default function SiemPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [collection, setCollection] = useState<DataCollectionPayload | null>(null);
  const [detection, setDetection] = useState<DetectionPayload | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationPayload | null>(null);
  const [compliance, setCompliance] = useState<CompliancePayload | null>(null);
  const [architecture, setArchitecture] = useState<ArchitecturePayload | null>(null);
  const [flows, setFlows] = useState<FlowsPayload | null>(null);
  const [controls, setControls] = useState<ControlsPayload | null>(null);
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilitiesPayload | null>(null);
  const [updates, setUpdates] = useState<UpdatesPayload | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [query, setQuery] = useState('auth');
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseSeverity, setNewCaseSeverity] = useState('medium');
  const [zapTarget, setZapTarget] = useState('https://example.local');
  const [zapProfile, setZapProfile] = useState('full-active');
  const [controlType, setControlType] = useState<'waf' | 'firewall' | 'ids' | 'ips'>('waf');
  const [controlId, setControlId] = useState<number>(1);
  const [controlEnabled, setControlEnabled] = useState(true);
  const [controlMode, setControlMode] = useState('block');
  const [controlAction, setControlAction] = useState('deny');
  const [controlThreshold, setControlThreshold] = useState(120);
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const [
        collectionRes,
        detectionRes,
        investigationRes,
        complianceRes,
        architectureRes,
        casesRes,
        flowsRes,
        controlsRes,
        vulnerabilitiesRes,
        updatesRes,
      ] = await Promise.all([
        apiGet<DataCollectionPayload>('/ops/siem/data-collection?limit=200', tenantId),
        apiGet<DetectionPayload>('/ops/siem/detection?limit=200', tenantId),
        apiGet<InvestigationPayload>(`/ops/siem/investigation?query=${encodeURIComponent(query)}&limit=100`, tenantId),
        apiGet<CompliancePayload>('/ops/siem/compliance', tenantId),
        apiGet<ArchitecturePayload>('/ops/siem/architecture', tenantId),
        apiGet<CasesPayload>('/ops/siem/cases?limit=50', tenantId),
        apiGet<FlowsPayload>('/ops/siem/flows?minutes=180&limit=1000', tenantId),
        apiGet<ControlsPayload>('/ops/siem/controls', tenantId),
        apiGet<VulnerabilitiesPayload>('/ops/siem/vulnerabilities?limit=200', tenantId),
        apiGet<UpdatesPayload>('/ops/siem/updates', tenantId),
      ]);
      setCollection(collectionRes);
      setDetection(detectionRes);
      setInvestigation(investigationRes);
      setCompliance(complianceRes);
      setArchitecture(architectureRes);
      setCases(casesRes.cases ?? []);
      setFlows(flowsRes);
      setControls(controlsRes);
      setVulnerabilities(vulnerabilitiesRes);
      setUpdates(updatesRes);
      const firstControl = controlsRes[controlType][0];
      if (firstControl) {
        setControlId(firstControl.id);
        setControlEnabled(firstControl.enabled);
        setControlMode(firstControl.mode ?? 'block');
        setControlAction(firstControl.action ?? 'deny');
        setControlThreshold(firstControl.threshold ?? 120);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load SIEM data');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cloudPlatforms = useMemo(() => Object.entries(collection?.telemetry.cloud_platforms ?? {}), [collection]);
  const saasApps = useMemo(() => Object.entries(collection?.telemetry.saas_apps ?? {}), [collection]);

  async function runInvestigation() {
    try {
      const result = await apiGet<InvestigationPayload>(
        `/ops/siem/investigation?query=${encodeURIComponent(query)}&limit=100`,
        tenantId
      );
      setInvestigation(result);
      setStatusMessage('Investigation query refreshed.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Investigation query failed');
    }
  }

  async function createCase() {
    if (!newCaseTitle.trim()) {
      setError('Case title is required.');
      return;
    }
    try {
      await apiSend(
        '/ops/siem/cases',
        'POST',
        {
          title: newCaseTitle,
          severity: newCaseSeverity,
          description: `Created from SIEM console query '${query}'`,
          evidence_ids: investigation?.results?.slice(0, 3).map((_, idx) => `query-hit-${idx + 1}`) ?? [],
        },
        tenantId
      );
      setStatusMessage('Case created.');
      setNewCaseTitle('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create case');
    }
  }

  async function runSoar(caseId?: number) {
    try {
      await apiSend(
        '/ops/siem/soar/run',
        'POST',
        {
          playbook: 'contain-compromised-endpoint',
          case_id: caseId ?? null,
          parameters: { source: 'siem-console' },
        },
        tenantId
      );
      setStatusMessage('SOAR playbook executed.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'SOAR execution failed');
    }
  }

  async function updateRetention() {
    try {
      await apiSend(
        '/ops/siem/compliance/retention',
        'POST',
        {
          hot_days: 30,
          warm_days: 120,
          cold_days: 365,
          immutable_audit: true,
        },
        tenantId
      );
      setStatusMessage('Retention policy updated.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update retention policy');
    }
  }

  async function runZapScan() {
    try {
      await apiSend(
        '/ops/siem/zap/scan',
        'POST',
        {
          target_url: zapTarget,
          scan_profile: zapProfile,
          authenticated: false,
        },
        tenantId
      );
      setStatusMessage('ZAP scan completed and vulnerability register updated.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run ZAP scan');
    }
  }

  async function applyControlChange() {
    try {
      await apiSend(
        `/ops/siem/controls/${controlType}/${controlId}`,
        'PATCH',
        {
          enabled: controlEnabled,
          mode: controlMode,
          action: controlAction,
          threshold: controlThreshold,
          notes: 'Updated from SIEM advanced control console',
        },
        tenantId
      );
      setStatusMessage('Security control updated.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update security control');
    }
  }

  async function applyUpdate(updateId: number) {
    try {
      await apiSend(`/ops/siem/updates/${updateId}/apply`, 'POST', { strategy: 'rolling' }, tenantId);
      setStatusMessage(`Applied update ${updateId}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply update');
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  } as const;
  const openCases = cases.filter((item) => item.status !== 'closed').length;
  const openVulnerabilities = (vulnerabilities?.items ?? []).filter((item) => item.status === 'open').length;
  const siemBars = [
    { label: 'Ingested Events', value: collection?.high_volume_ingestion.ingested_events_total ?? 0 },
    { label: 'Open Cases', value: openCases },
    { label: 'Open CVEs', value: openVulnerabilities },
    { label: 'Pending Updates', value: (updates?.items ?? []).filter((item) => item.status !== 'applied').length },
  ];
  const siemLine = (flows?.analytics.events_timeline ?? []).slice(-8).map((item) => item.events);
  const severityRing = Object.entries(vulnerabilities?.severity_distribution ?? {})
    .slice(0, 4)
    .map(([label, value], index) => ({
      label,
      value,
      color: index === 0 ? '#ef4444' : index === 1 ? '#f59e0b' : index === 2 ? '#6366f1' : '#22c55e',
    }));

  return (
    <div style={siemThemeVars}>
      <div style={{ maxWidth: 1280, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--nx-gap)' }}>
        <PageHeader
          title="SIEM & Security Operations"
          subtitle="SIEM control plane with flow analytics, vulnerability intelligence, and operations for WAF, firewall, IDS/IPS, CVE posture, ZAP scanning, and secure update orchestration."
        />

        <AnalyticsExecutiveBoard
          title="SIEM + SOAR Executive Analytics"
          subtitle="Unified telemetry for ingestion, anomaly detection, incident response, vulnerability posture, and automation actions."
          kpis={[
            {
              label: 'Ingested Events',
              value: String(collection?.high_volume_ingestion.ingested_events_total ?? 0),
              delta: 'High-volume pipeline',
              trend: 'up',
            },
            {
              label: 'Anomaly Score',
              value: String(detection?.ml_anomaly_detection.anomaly_score ?? 0),
              delta: String(detection?.ml_anomaly_detection.state ?? 'model'),
              trend: (detection?.ml_anomaly_detection.anomaly_score ?? 0) <= 45 ? 'up' : 'down',
            },
            {
              label: 'Open Cases',
              value: String(openCases),
              delta: `${cases.length} total`,
              trend: openCases <= 5 ? 'up' : 'down',
            },
            {
              label: 'Flow Count',
              value: String(flows?.flow_count ?? 0),
              delta: '3-hour graph',
              trend: 'flat',
            },
            {
              label: 'Posture Score',
              value: String(controls?.posture_score ?? 0),
              delta: `${controls?.summary.controls_enabled ?? 0}/${controls?.summary.controls_total ?? 0} enabled`,
              trend: (controls?.posture_score ?? 0) >= 75 ? 'up' : 'down',
            },
            {
              label: 'Open CVEs',
              value: String(openVulnerabilities),
              delta: `${vulnerabilities?.count ?? 0} tracked`,
              trend: openVulnerabilities <= 3 ? 'up' : 'down',
            },
          ]}
          bars={siemBars}
          line={siemLine.length ? siemLine : [12, 17, 15, 20, 26, 19, 24, 28]}
          ring={
            severityRing.length
              ? severityRing
              : [
                  { label: 'Critical', value: 4, color: '#ef4444' },
                  { label: 'High', value: 6, color: '#f59e0b' },
                  { label: 'Medium', value: 8, color: '#6366f1' },
                  { label: 'Low', value: 10, color: '#22c55e' },
                ]
          }
        />

        {(error || statusMessage) && (
          <div
            style={{
              ...card,
              marginBottom: 12,
              borderColor: error ? '#ef444488' : '#22c55e88',
              color: error ? '#f87171' : '#4ade80',
            }}
          >
            {error || statusMessage}
          </div>
        )}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: 10,
            marginBottom: 10,
          }}
        >
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Ingested Events</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>
              {collection?.high_volume_ingestion.ingested_events_total ?? 0}
            </div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Anomaly Score</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{detection?.ml_anomaly_detection.anomaly_score ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Open Cases</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{cases.filter((c) => c.status !== 'closed').length}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Audit Log Records</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{compliance?.audit_logs.count ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>EPS Capacity</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>
              {architecture?.scalability_architecture.high_volume_ingestion.estimated_eps_capacity ?? 0}
            </div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Flow Count (3h)</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{flows?.flow_count ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Security Posture</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{controls?.posture_score ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Open CVEs</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>
              {(vulnerabilities?.items ?? []).filter((item) => item.status === 'open').length}
            </div>
          </div>
        </div>

        <section style={{ ...card, marginBottom: 10 }}>
          <h3 style={{ marginTop: 0 }}>Flow Analytics Graph And Attack Path Telemetry</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Event timeline (last buckets)</div>
              <TinyLine points={flows?.analytics.events_timeline ?? []} />
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
                Nodes: {flows?.graph.nodes.length ?? 0} · Edges: {flows?.graph.edges.length ?? 0}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Risk distribution</div>
              <TinyBars data={flows?.analytics.risk_distribution ?? {}} emptyLabel="No risk data" />
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Action distribution</div>
              <TinyBars data={flows?.analytics.action_distribution ?? {}} emptyLabel="No action data" />
            </div>
          </div>
          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>Top talkers</div>
              {(flows?.analytics.top_talkers ?? []).slice(0, 8).map((item) => (
                <div key={item.id} style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}>
                  {item.id} · {item.total_bytes} bytes
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>Highest-volume edges</div>
              {(flows?.graph.edges ?? []).slice(0, 8).map((item, idx) => (
                <div
                  key={`${item.source}-${item.target}-${idx}`}
                  style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
                >
                  {item.source} → {item.target} · {item.bytes} bytes · {item.flow_count} flows
                </div>
              ))}
            </div>
          </div>
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginBottom: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>1) Data Collection & Telemetry</h3>
            <div style={{ fontSize: 13, marginBottom: 6 }}>
              Endpoints: {collection?.telemetry.endpoints_servers_network_devices.endpoint_count ?? 0} · Servers:{' '}
              {collection?.telemetry.endpoints_servers_network_devices.server_events ?? 0} · Network devices:{' '}
              {collection?.telemetry.endpoints_servers_network_devices.network_events ?? 0}
            </div>
            <div style={{ fontSize: 13, marginBottom: 6 }}>
              Identity systems: auth events {collection?.telemetry.identity_systems.auth_events ?? 0}, tenant profiles{' '}
              {collection?.telemetry.identity_systems.tenant_profiles ?? 0}
            </div>
            <h4 style={{ marginBottom: 6 }}>Cloud platforms</h4>
            {cloudPlatforms.map(([name, enabled]) => (
              <div key={name} style={{ fontSize: 12 }}>
                {name}: {enabled ? 'configured' : 'not configured'}
              </div>
            ))}
            <h4 style={{ marginBottom: 6 }}>SaaS apps</h4>
            {saasApps.map(([name, count]) => (
              <div key={name} style={{ fontSize: 12 }}>
                {name}: {count} events
              </div>
            ))}
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>2) Correlation & Detection</h3>
            <div style={{ fontSize: 13, marginBottom: 8 }}>Rule-based correlation hits:</div>
            {(detection?.rule_based_correlation.triggered_rules ?? []).slice(0, 6).map((r) => (
              <div
                key={`${r.ip}-${r.rule}`}
                style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
              >
                {r.ip} · {r.event_count} events · {r.rule}
              </div>
            ))}
            <div style={{ marginTop: 8, fontSize: 13 }}>UEBA top actors:</div>
            {(detection?.behavior_analytics_ueba.top_actors ?? []).slice(0, 6).map((a) => (
              <div key={a.actor} style={{ fontSize: 12 }}>
                {a.actor}: {a.events}
              </div>
            ))}
            <div style={{ marginTop: 8, fontSize: 13 }}>Threat intel enrichment:</div>
            {(detection?.threat_intelligence_enrichment.matches ?? []).slice(0, 4).map((m) => (
              <div key={m.ip} style={{ fontSize: 12 }}>
                {m.ip} · {m.threat} · confidence {m.confidence}
              </div>
            ))}
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginBottom: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>3) Investigation & Response</h3>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search indicators, users, paths"
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <button
                onClick={() => void runInvestigation()}
                style={{
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 12px',
                  background: 'var(--brand)',
                  color: '#00101e',
                  fontWeight: 700,
                }}
              >
                Search & Pivot
              </button>
            </div>
            {(investigation?.results ?? []).slice(0, 8).map((r, idx) => (
              <div
                key={`${r.source}-${idx}`}
                style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
              >
                {r.source} · {r.title} · actor {r.actor || 'n/a'} · ip {r.ip || 'n/a'}
              </div>
            ))}
            <div style={{ marginTop: 10, fontSize: 13 }}>
              Attack path reconstruction: {(investigation?.attack_path_reconstruction ?? []).length} steps
            </div>
            <button
              onClick={() => void runSoar()}
              style={{
                marginTop: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '7px 11px',
                background: 'transparent',
                color: 'var(--text)',
              }}
            >
              Run SOAR Playbook
            </button>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Case Management</h3>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input
                value={newCaseTitle}
                onChange={(e) => setNewCaseTitle(e.target.value)}
                placeholder="Case title"
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <select
                value={newCaseSeverity}
                onChange={(e) => setNewCaseSeverity(e.target.value)}
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
              <button
                onClick={() => void createCase()}
                style={{
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 12px',
                  background: 'var(--brand)',
                  color: '#00101e',
                  fontWeight: 700,
                }}
              >
                Create
              </button>
            </div>
            {cases.slice(0, 10).map((c) => (
              <div key={c.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0', fontSize: 12 }}>
                #{c.id} · {c.title} · {c.severity} · {c.status}
              </div>
            ))}
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>4) Compliance</h3>
            <div style={{ fontSize: 12, marginBottom: 8 }}>
              Audit logs retained: {compliance?.audit_logs.count ?? 0}
            </div>
            {(compliance?.prebuilt_compliance_reports ?? []).map((report) => (
              <div
                key={report.framework}
                style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
              >
                {report.framework}: {report.status} ({report.controls_mapped} controls)
              </div>
            ))}
            <div style={{ fontSize: 12, marginTop: 8 }}>
              Retention: hot {compliance?.retention_policies.hot_days ?? 0}d · warm{' '}
              {compliance?.retention_policies.warm_days ?? 0}d · cold {compliance?.retention_policies.cold_days ?? 0}d
            </div>
            <button
              onClick={() => void updateRetention()}
              style={{
                marginTop: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '7px 11px',
                background: 'transparent',
                color: 'var(--text)',
              }}
            >
              Apply Production Retention Policy
            </button>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>5) Scalability & Architecture</h3>
            <div style={{ fontSize: 12 }}>
              Mode: {architecture?.scalability_architecture.deployment_mode ?? 'hybrid'}
            </div>
            <div style={{ fontSize: 12 }}>
              Data lake support:{' '}
              {architecture?.scalability_architecture.data_lake_support.enabled ? 'enabled' : 'disabled'}
            </div>
            {(architecture?.scalability_architecture.data_lake_support.exports ?? []).map((exp, idx) => (
              <div
                key={`${exp.sink}-${idx}`}
                style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
              >
                {exp.sink} · {exp.format} · {exp.status}
              </div>
            ))}
            <div style={{ fontSize: 12, marginTop: 8 }}>
              High-volume ingestion:{' '}
              {architecture?.scalability_architecture.high_volume_ingestion.events_ingested_total ?? 0} events ·
              capacity {architecture?.scalability_architecture.high_volume_ingestion.estimated_eps_capacity ?? 0} eps
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginTop: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Security Control Plane (WAF, Firewall, IDS, IPS)</h3>
            <div style={{ fontSize: 12, marginBottom: 8 }}>
              Controls: {controls?.summary.controls_total ?? 0} · Enabled: {controls?.summary.controls_enabled ?? 0} ·
              Disabled: {controls?.summary.controls_disabled ?? 0}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8, marginBottom: 8 }}>
              <select
                value={controlType}
                onChange={(e) => setControlType(e.target.value as 'waf' | 'firewall' | 'ids' | 'ips')}
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              >
                <option value="waf">waf</option>
                <option value="firewall">firewall</option>
                <option value="ids">ids</option>
                <option value="ips">ips</option>
              </select>
              <input
                value={controlId}
                onChange={(e) => setControlId(Number(e.target.value || '0'))}
                type="number"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <input
                value={controlMode}
                onChange={(e) => setControlMode(e.target.value)}
                placeholder="mode"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <input
                value={controlAction}
                onChange={(e) => setControlAction(e.target.value)}
                placeholder="action"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <input
                value={controlThreshold}
                onChange={(e) => setControlThreshold(Number(e.target.value || '0'))}
                type="number"
                placeholder="threshold"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <input checked={controlEnabled} onChange={(e) => setControlEnabled(e.target.checked)} type="checkbox" />
                Enabled
              </label>
            </div>
            <button
              onClick={() => void applyControlChange()}
              style={{
                border: 'none',
                borderRadius: 8,
                padding: '8px 12px',
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Apply Security Control Change
            </button>
            <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
              {[
                ...(controls?.waf ?? []),
                ...(controls?.firewall ?? []),
                ...(controls?.ids ?? []),
                ...(controls?.ips ?? []),
              ]
                .slice(0, 12)
                .map((item) => (
                  <div
                    key={`${item.name}-${item.id}`}
                    style={{ fontSize: 12, border: '1px solid var(--line)', borderRadius: 10, padding: 8 }}
                  >
                    #{item.id} {item.name} · {item.enabled ? 'enabled' : 'disabled'} ·{' '}
                    {item.mode || item.action || 'n/a'}
                  </div>
                ))}
            </div>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Vulnerability Intelligence, ZAP Scanning, and Updates</h3>
            <div style={{ fontSize: 12, marginBottom: 8 }}>Vulnerability severity distribution</div>
            <TinyBars data={vulnerabilities?.severity_distribution ?? {}} emptyLabel="No vulnerability data" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8, marginTop: 10 }}>
              <input
                value={zapTarget}
                onChange={(e) => setZapTarget(e.target.value)}
                placeholder="https://target.local"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
              <input
                value={zapProfile}
                onChange={(e) => setZapProfile(e.target.value)}
                placeholder="scan profile"
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
            </div>
            <button
              onClick={() => void runZapScan()}
              style={{
                marginTop: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '7px 11px',
                background: 'transparent',
                color: 'var(--text)',
              }}
            >
              Run ZAP Scan
            </button>
            <div style={{ marginTop: 10, maxHeight: 180, overflow: 'auto' }}>
              {(vulnerabilities?.items ?? []).slice(0, 12).map((item) => (
                <div key={item.id} style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '5px 0' }}>
                  {item.cve} · {item.asset} · {item.severity} · CVSS {item.cvss} · {item.status}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, fontWeight: 700, fontSize: 13 }}>Patch updates</div>
            {(updates?.items ?? []).slice(0, 8).map((item) => (
              <div
                key={item.id}
                style={{ fontSize: 12, border: '1px solid var(--line)', borderRadius: 10, padding: 8, marginTop: 6 }}
              >
                #{item.id} {item.component} {item.version} · {item.risk_level} · {item.status}
                <div>
                  <button
                    onClick={() => void applyUpdate(item.id)}
                    style={{
                      marginTop: 6,
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: '6px 10px',
                      background: 'transparent',
                      color: 'var(--text)',
                    }}
                  >
                    Apply Update
                  </button>
                </div>
              </div>
            ))}
          </section>
        </div>
      </div>
    </div>
  );
}
