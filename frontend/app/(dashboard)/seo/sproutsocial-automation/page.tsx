'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  type BestStackReportRecord,
  type SocialAuditLogEntry,
  type SocialGrowthMatrixResponse,
  type SocialProductionRemediationPlan,
  type SocialProductionReadiness,
  socialApi,
} from '@/app/lib/social-api';

type ProbeResult = {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
};

type ProbeCheck = {
  key: string;
  label: string;
  run: () => Promise<string>;
};

type IntegrationSummary = {
  providers_total: number;
  configured_total: number;
  coverage_percent: number;
};

type BestStackProbeResult = {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
};

type BestStackCoverageRow = {
  key: string;
  label: string;
  completion: number;
  status: 'done' | 'partial' | 'missing';
  howItWorks: string;
  vendors: string;
};

type VerificationScoreRow = {
  key: string;
  label: string;
  percent: number;
  status: 'pass' | 'partial' | 'pending';
  detail: string;
};

type BestStackProbeSectionProps = {
  results: BestStackProbeResult[];
  latestReport: BestStackReportRecord | null;
  reports: BestStackReportRecord[];
  exporting: boolean;
  running: boolean;
  onExportJson: () => void;
  onExportMarkdown: () => void;
};

async function runStackCheck(
  results: BestStackProbeResult[],
  key: string,
  label: string,
  probe: () => Promise<{ ok: boolean; detail: string }>
) {
  try {
    const out = await probe();
    results.push({ key, label, ok: out.ok, detail: out.detail });
  } catch (e) {
    results.push({
      key,
      label,
      ok: false,
      detail: e instanceof Error ? e.message : 'Probe failed',
    });
  }
}

function downloadTextFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function CapabilityMatrixSection({ readiness }: Readonly<{ readiness: SocialProductionReadiness | null }>) {
  if (!readiness?.capability_matrix?.length) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Sprout-Style Feature Completion Chart</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Capability</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Completion</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Automation</th>
            </tr>
          </thead>
          <tbody>
            {readiness.capability_matrix.map((item) => (
              <tr key={item.capability_key} style={{ borderTop: '1px solid rgba(148, 163, 184, 0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{item.capability}</td>
                <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{item.status}</td>
                <td style={{ padding: '8px 6px' }}>{item.completion_percent}%</td>
                <td style={{ padding: '8px 6px' }}>{item.automation_level_percent}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VendorsSection({ readiness }: Readonly<{ readiness: SocialProductionReadiness | null }>) {
  if (!readiness?.vendors.registry?.length) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Third-Parties and Vendors</h3>
      <ul className="bullet-list">
        {readiness.vendors.registry.map((vendor) => (
          <li key={vendor.vendor_key}>
            <strong>{vendor.vendor}</strong> ({vendor.configured ? 'configured' : 'not configured'}):{' '}
            {vendor.capabilities.join(', ')}
          </li>
        ))}
      </ul>
      <p style={{ marginTop: 12, opacity: 0.85 }}>
        How this works: each capability in the matrix maps required routes and vendor keys. A capability is fully wired
        only when its API routes are available and required vendors are configured.
      </p>
    </section>
  );
}

function BestStackCoverageSection({ rows }: Readonly<{ rows: BestStackCoverageRow[] }>) {
  if (!rows.length) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Best-of Stack Coverage Chart</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Stack</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Completion</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>How It Works</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Vendors</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.key} style={{ borderTop: '1px solid rgba(148, 163, 184, 0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{item.label}</td>
                <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{item.status}</td>
                <td style={{ padding: '8px 6px' }}>{item.completion}%</td>
                <td style={{ padding: '8px 6px' }}>{item.howItWorks}</td>
                <td style={{ padding: '8px 6px' }}>{item.vendors}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProductionVerificationSection({ rows }: Readonly<{ rows: VerificationScoreRow[] }>) {
  if (!rows.length) {
    return null;
  }

  const overall = Math.round(rows.reduce((sum, row) => sum + row.percent, 0) / rows.length);

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Production Verification Scorecard</h3>
      <p style={{ opacity: 0.85 }}>Overall verified completion: {overall}%</p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Area</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Verified</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} style={{ borderTop: '1px solid rgba(148, 163, 184, 0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{row.label}</td>
                <td style={{ padding: '8px 6px' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <div
                      aria-label={`${row.label} completion bar`}
                      style={{
                        width: 140,
                        height: 8,
                        borderRadius: 999,
                        overflow: 'hidden',
                        background: 'rgba(148, 163, 184, 0.25)',
                      }}
                    >
                      <div
                        style={{
                          width: `${row.percent}%`,
                          height: '100%',
                          background:
                            row.status === 'pass'
                              ? '#22c55e'
                              : row.status === 'partial'
                                ? '#f59e0b'
                                : '#64748b',
                        }}
                      />
                    </div>
                    <span>{row.percent}%</span>
                  </div>
                </td>
                <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{row.status}</td>
                <td style={{ padding: '8px 6px' }}>{row.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function BestStackProbeSection({
  results,
  latestReport,
  reports,
  exporting,
  running,
  onExportJson,
  onExportMarkdown,
}: Readonly<BestStackProbeSectionProps>) {
  if (!results.length) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Best-of Stack Probe Results</h3>
      {latestReport ? (
        <p style={{ opacity: 0.85 }}>
          Latest auditable report: {latestReport.name} ({latestReport.generated_at})
        </p>
      ) : null}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
        <button onClick={onExportJson} disabled={!latestReport || exporting || running}>
          {exporting ? 'Exporting...' : 'Export Latest Report (JSON)'}
        </button>
        <button onClick={onExportMarkdown} disabled={!latestReport || exporting || running}>
          {exporting ? 'Exporting...' : 'Export Latest Report (Markdown)'}
        </button>
      </div>
      <ul className="bullet-list">
        {results.map((item) => (
          <li key={item.key}>
            <strong>{item.label}</strong>: {item.ok ? 'PASS' : 'FAIL'} ({item.detail})
          </li>
        ))}
      </ul>
      {reports.length ? (
        <>
          <h4 style={{ marginBottom: 8 }}>Recent Best-Stack Reports</h4>
          <ul className="bullet-list">
            {reports.slice(0, 5).map((report) => (
              <li key={report.id}>
                #{report.id} {report.name} ({report.generated_at})
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function E2EProbeSection({ results }: Readonly<{ results: ProbeResult[] }>) {
  if (!results.length) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>E2E Probe Results</h3>
      <ul className="bullet-list">
        {results.map((item) => (
          <li key={item.key}>
            <strong>{item.label}</strong>: {item.ok ? 'PASS' : 'FAIL'} ({item.detail})
          </li>
        ))}
      </ul>
    </section>
  );
}

function RemediationSection({ remediation }: Readonly<{ remediation: SocialProductionRemediationPlan | null }>) {
  if (!remediation) {
    return null;
  }

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>100% Remediation Plan</h3>
      <p style={{ opacity: 0.85 }}>
        Remaining blockers: {remediation.blocking_items.length}. Missing env keys: {remediation.missing_env_keys.length}.
      </p>

      {remediation.global_requirements.length ? (
        <>
          <h4>Global Requirements</h4>
          <ul className="bullet-list">
            {remediation.global_requirements.map((item) => (
              <li key={item.key}>
                <strong>{item.key}</strong> - {item.configured ? 'configured' : 'missing'} ({item.expected})
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {remediation.integration_requirements.length ? (
        <>
          <h4>Integration Credentials Remaining</h4>
          <ul className="bullet-list">
            {remediation.integration_requirements.map((item) => (
              <li key={item.integration_key}>
                <strong>{item.integration}</strong> ({item.integration_key}) - {item.missing_env_keys.join(', ')}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {remediation.next_actions.length ? (
        <>
          <h4>Next Actions</h4>
          <ol>
            {remediation.next_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
        </>
      ) : null}
    </section>
  );
}

function AuditTrailSection({ entries }: Readonly<{ entries: SocialAuditLogEntry[] }>) {
  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Social Audit Trail</h3>
      {entries.length ? (
        <ul className="bullet-list">
          {entries.slice(0, 12).map((entry) => (
            <li key={entry.id}>
              <strong>{entry.action}</strong> (ref: {entry.ref_id ?? 'n/a'}) at {entry.created_at}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ opacity: 0.85, marginBottom: 0 }}>No audit entries available yet for this tenant.</p>
      )}
    </section>
  );
}

export default function SproutSocialAutomationPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [readiness, setReadiness] = useState<SocialProductionReadiness | null>(null);
  const [growthMatrix, setGrowthMatrix] = useState<SocialGrowthMatrixResponse | null>(null);
  const [remediation, setRemediation] = useState<SocialProductionRemediationPlan | null>(null);
  const [integrationSummary, setIntegrationSummary] = useState<IntegrationSummary | null>(null);
  const [automationRulesCount, setAutomationRulesCount] = useState(0);
  const [automationFeedsCount, setAutomationFeedsCount] = useState(0);
  const [inboxTotal, setInboxTotal] = useState(0);
  const [listeningMentions, setListeningMentions] = useState(0);
  const [reportsCount, setReportsCount] = useState(0);
  const [aiTemplatesCount, setAiTemplatesCount] = useState(0);

  const [probeRunning, setProbeRunning] = useState(false);
  const [probeResults, setProbeResults] = useState<ProbeResult[]>([]);
  const [bestStackProbeRunning, setBestStackProbeRunning] = useState(false);
  const [bestStackProbeResults, setBestStackProbeResults] = useState<BestStackProbeResult[]>([]);
  const [bestStackReports, setBestStackReports] = useState<BestStackReportRecord[]>([]);
  const [latestBestStackReport, setLatestBestStackReport] = useState<BestStackReportRecord | null>(null);
  const [bestStackExporting, setBestStackExporting] = useState(false);
  const [auditLogEntries, setAuditLogEntries] = useState<SocialAuditLogEntry[]>([]);

  const checks: ProbeCheck[] = useMemo(
    () => [
      {
        key: 'readiness',
        label: 'Production readiness contract',
        run: async () => {
          const r = await socialApi.getProductionReadiness();
          return `score=${r.readiness_score}, ready=${r.production_ready}`;
        },
      },
      {
        key: 'growth',
        label: 'Growth integration matrix',
        run: async () => {
          const r = await socialApi.getGrowthIntegrationMatrix();
          return `done=${r.summary.done}, partial=${r.summary.partial}, missing=${r.summary.missing}`;
        },
      },
      {
        key: 'automation-rules',
        label: 'Automation rules engine',
        run: async () => {
          const rules = await socialApi.listAutomationRules();
          return `rules=${rules.length}`;
        },
      },
      {
        key: 'automation-feeds',
        label: 'Automation feeds scheduler',
        run: async () => {
          const feeds = await socialApi.listAutomationFeeds();
          return `feeds=${feeds.length}`;
        },
      },
      {
        key: 'listening',
        label: 'Social listening and sentiment',
        run: async () => {
          const mentions = await socialApi.listListeningMentions(false);
          const sentiment = await socialApi.getListeningSentiment();
          return `mentions=${mentions.mentions.length}, negative=${sentiment.breakdown.negative}`;
        },
      },
      {
        key: 'inbox',
        label: 'Unified smart inbox',
        run: async () => {
          const stats = await socialApi.getInboxStats();
          return `total=${stats.total}, unread=${stats.unread}`;
        },
      },
      {
        key: 'reports',
        label: 'Analytics and reporting',
        run: async () => {
          const reports = await socialApi.listReports();
          return `reports=${reports.length}`;
        },
      },
      {
        key: 'ai-workflow',
        label: 'AI automation workflow execution',
        run: async () => {
          const response = await socialApi.executeAIAgentWorkflow({
            template_key: 'social_poster',
            trigger_type: 'manual',
            payload: {
              topic: 'Product launch',
              objective: 'engagement',
              platform: 'linkedin',
            },
          });
          const raw = response.status ?? response.result ?? 'ok';
          const status = typeof raw === 'string' || typeof raw === 'number' || typeof raw === 'boolean' ? raw : 'ok';
          return `status=${status}`;
        },
      },
    ],
    []
  );

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [
        readinessData,
        growthData,
        rules,
        feeds,
        inboxStats,
        mentions,
        reports,
        templates,
        integrationCatalog,
        bestStackReportItems,
      ] = await Promise.all([
        socialApi.getProductionReadiness(),
        socialApi.getGrowthIntegrationMatrix(),
        socialApi.listAutomationRules(),
        socialApi.listAutomationFeeds(),
        socialApi.getInboxStats(),
        socialApi.listListeningMentions(false),
        socialApi.listReports(),
        socialApi.listAIAgentTemplates(),
        socialApi.listIntegrationCatalog(),
        socialApi.listBestStackReports(),
      ]);

      try {
        const remediationPlan = await socialApi.getProductionRemediationPlan();
        setRemediation(remediationPlan);
      } catch {
        setRemediation(null);
      }

      try {
        const auditRows = await socialApi.listSocialAuditLog(120);
        setAuditLogEntries(auditRows);
      } catch {
        setAuditLogEntries([]);
      }

      setReadiness(readinessData);
      setGrowthMatrix(growthData);
      setAutomationRulesCount(rules.length);
      setAutomationFeedsCount(feeds.length);
      setInboxTotal(inboxStats.total);
      setListeningMentions(mentions.mentions.length);
      setReportsCount(reports.length);
      setAiTemplatesCount(templates.length);
      setIntegrationSummary(integrationCatalog.summary);
      setBestStackReports(bestStackReportItems);
      setLatestBestStackReport(bestStackReportItems[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Sprout Social automation status');
    } finally {
      setLoading(false);
    }
  }

  async function runE2EProbe() {
    setProbeRunning(true);
    setError('');
    try {
      const results: ProbeResult[] = [];
      for (const check of checks) {
        try {
          const detail = await check.run();
          results.push({ key: check.key, label: check.label, ok: true, detail });
        } catch (e) {
          results.push({
            key: check.key,
            label: check.label,
            ok: false,
            detail: e instanceof Error ? e.message : 'Probe failed',
          });
        }
      }
      setProbeResults(results);
      await refreshAll();
    } finally {
      setProbeRunning(false);
    }
  }

  const bestStackCoverage = useMemo<BestStackCoverageRow[]>(() => {
    const capabilityByKey = new Map((readiness?.capability_matrix ?? []).map((item) => [item.capability_key, item]));
    const vendorByKey = new Map((readiness?.vendors.registry ?? []).map((item) => [item.vendor_key, item]));

    const scheduling = capabilityByKey.get('ai_scheduling');
    const repurpose = capabilityByKey.get('ai_repurposing');
    const content = capabilityByKey.get('ai_content_engines');
    const listening = capabilityByKey.get('ai_social_listening');

    const brandwatch = vendorByKey.get('brandwatch_meltwater');
    const openai = vendorByKey.get('openai');
    const canva = vendorByKey.get('canva');

    const rows: BestStackCoverageRow[] = [
      {
        key: 'sprout_ops',
        label: 'Sprout Social (ops)',
        completion: readiness?.capability_summary.average_completion_percent ?? 0,
        status: readiness?.production_ready ? 'done' : 'partial',
        howItWorks:
          'Uses publishing, inbox, listening, automation queue, analytics, and approval routes with capability-level readiness scoring.',
        vendors: 'OAuth providers, OpenAI, optional shorteners, optional Canva',
      },
      {
        key: 'lately_repurpose',
        label: 'Lately (AI repurposing)',
        completion: repurpose?.completion_percent ?? 0,
        status: repurpose?.status ?? 'missing',
        howItWorks:
          'Longform assets are transformed into multi-variant social drafts via repurpose endpoints and can be auto-queued.',
        vendors: 'OpenAI',
      },
      {
        key: 'jasper_copy',
        label: 'Jasper (AI copy)',
        completion: content?.completion_percent ?? 0,
        status: content?.status ?? 'missing',
        howItWorks:
          'AI assistant and content engines generate and rewrite social copy variants with tone/platform controls.',
        vendors: [openai?.configured ? 'OpenAI' : 'OpenAI (missing)', canva?.configured ? 'Canva' : 'Canva (optional)'].join(', '),
      },
      {
        key: 'brandwatch_listening',
        label: 'Brandwatch (listening intelligence)',
        completion: listening?.completion_percent ?? 0,
        status: listening?.status ?? 'missing',
        howItWorks:
          'Listening keywords, mentions, sentiment, and competitor insight routes run natively with optional Brandwatch/Meltwater enrichment.',
        vendors: brandwatch?.configured ? 'Brandwatch/Meltwater configured' : 'Brandwatch/Meltwater optional (not configured)',
      },
      {
        key: 'buffer_later_scheduling',
        label: 'Buffer/Later (visual scheduling)',
        completion: scheduling?.completion_percent ?? 0,
        status: scheduling?.status ?? 'missing',
        howItWorks:
          'Calendar, queue, posting schedules, and best-time routes drive visual planning and publish-time orchestration.',
        vendors: 'OAuth providers, optional shorteners',
      },
    ];

    return rows;
  }, [readiness]);

  const verificationRows = useMemo<VerificationScoreRow[]>(() => {
    const e2eTotal = checks.length;
    const e2ePass = probeResults.filter((item) => item.ok).length;
    const e2ePercent = e2eTotal ? Math.round((e2ePass / e2eTotal) * 100) : 0;

    const stackTotal = bestStackProbeResults.length;
    const stackPass = bestStackProbeResults.filter((item) => item.ok).length;
    const stackPercent = stackTotal ? Math.round((stackPass / stackTotal) * 100) : 0;

    const capabilityPercent = readiness?.capability_summary.average_completion_percent ?? 0;
    const wiringPercent = integrationSummary?.coverage_percent ?? 0;
    const blockers = remediation?.blocking_items.length ?? 0;

    return [
      {
        key: 'e2e-probes',
        label: 'Core E2E probes',
        percent: e2ePercent,
        status: e2eTotal === 0 ? 'pending' : e2ePercent === 100 ? 'pass' : 'partial',
        detail: e2eTotal === 0 ? 'Run E2E Probe to verify all checks.' : `${e2ePass}/${e2eTotal} checks passed`,
      },
      {
        key: 'best-stack-probes',
        label: 'Best stack probes',
        percent: stackPercent,
        status: stackTotal === 0 ? 'pending' : stackPercent === 100 ? 'pass' : 'partial',
        detail: stackTotal === 0 ? 'Run Best-Stack Probe to verify all stack providers.' : `${stackPass}/${stackTotal} checks passed`,
      },
      {
        key: 'capability-coverage',
        label: 'Capability coverage',
        percent: capabilityPercent,
        status: capabilityPercent >= 95 ? 'pass' : capabilityPercent > 0 ? 'partial' : 'pending',
        detail: `${readiness?.capability_summary.fully_wired_capabilities ?? 0}/${readiness?.capability_summary.total_capabilities ?? 0} fully wired`,
      },
      {
        key: 'vendor-wiring',
        label: 'Vendor wiring',
        percent: wiringPercent,
        status: wiringPercent >= 95 ? 'pass' : wiringPercent > 0 ? 'partial' : 'pending',
        detail: `${integrationSummary?.configured_total ?? 0}/${integrationSummary?.providers_total ?? 0} providers configured`,
      },
      {
        key: 'remediation-blockers',
        label: 'Remediation blockers',
        percent: blockers === 0 ? 100 : 0,
        status: blockers === 0 ? 'pass' : 'partial',
        detail: `${blockers} blockers remaining`,
      },
    ];
  }, [bestStackProbeResults, checks.length, integrationSummary, probeResults, readiness, remediation]);

  async function exportLatestBestStackReport(format: 'json' | 'markdown') {
    if (!latestBestStackReport) {
      return;
    }
    setBestStackExporting(true);
    setError('');
    try {
      const report = await socialApi.exportBestStackReport(latestBestStackReport.id);
      const stamp = String(report.report.generated_at || new Date().toISOString()).replace(/[:.]/g, '-');
      if (format === 'markdown') {
        downloadTextFile(`best-stack-report-${report.report.id}-${stamp}.md`, report.artifact_markdown, 'text/markdown;charset=utf-8');
      } else {
        downloadTextFile(
          `best-stack-report-${report.report.id}-${stamp}.json`,
          JSON.stringify(report.artifact, null, 2),
          'application/json;charset=utf-8'
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to export best-stack report');
    } finally {
      setBestStackExporting(false);
    }
  }

  async function runBestStackProbe() {
    setBestStackProbeRunning(true);
    setError('');
    try {
      const results: BestStackProbeResult[] = [];

      await runStackCheck(results, 'sprout', 'Sprout Social (ops)', async () => {
        const r = await socialApi.getProductionReadiness();
        return {
          ok: (r.capability_summary.average_completion_percent ?? 0) > 0,
          detail: `score=${r.readiness_score}, ready=${r.production_ready}`,
        };
      });

      await runStackCheck(results, 'lately', 'Lately (AI repurposing)', async () => {
        const r = await socialApi.repurposeLongform({
          source_title: 'Q2 Growth Brief',
          source_text:
            'Revenue attribution and social automation are now connected, enabling teams to repurpose one strategic asset across channels with measurable pipeline impact.',
          target_platform: 'linkedin',
          tone: 'professional',
          variant_count: 3,
          queue_first_variant: false,
        });
        return {
          ok: (r.variant_count ?? 0) > 0,
          detail: `variants=${r.variant_count}, provider=${r.provider}`,
        };
      });

      await runStackCheck(results, 'jasper', 'Jasper (AI copy)', async () => {
        const r = await socialApi.aiAssistant({
          text: 'Turn launch updates into high-converting social copy for product teams.',
          action: 'generate',
          target_platform: 'linkedin',
          tone: 'professional',
        });
        return {
          ok: Boolean(r.result?.trim()),
          detail: `provider=${r.provider}, chars=${r.result?.length ?? 0}`,
        };
      });

      await runStackCheck(results, 'brandwatch', 'Brandwatch (listening intelligence)', async () => {
        const [mentions, r] = await Promise.all([
          socialApi.listListeningMentions(false),
          socialApi.getProductionReadiness(),
        ]);
        const brandwatchVendor = r.vendors.registry.find((item) => item.vendor_key === 'brandwatch_meltwater');
        return {
          ok: Array.isArray(mentions.mentions),
          detail: `mentions=${mentions.mentions.length}, vendor=${brandwatchVendor?.configured ? 'configured' : 'optional'}`,
        };
      });

      await runStackCheck(results, 'buffer-later', 'Buffer/Later (visual scheduling)', async () => {
        const today = new Date().toISOString();
        const [calendar, queue] = await Promise.all([
          socialApi.listCalendarEvents(today, today),
          socialApi.getPublishingQueue(),
        ]);
        return {
          ok: Array.isArray(calendar) && Array.isArray(queue.items),
          detail: `calendar_items=${calendar.length}, queue_items=${queue.items.length}`,
        };
      });

      setBestStackProbeResults(results);
      try {
        const created = await socialApi.createBestStackReport({
          probe_results: results,
          generated_by: 'sproutsocial-automation-page',
        });
        setLatestBestStackReport(created.report);
        setBestStackReports((prev) => {
          const next = [created.report, ...prev.filter((item) => item.id !== created.report.id)];
          return next.slice(0, 20);
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Best-stack report generation failed; probe results are still available.');
      }
      await refreshAll();
    } finally {
      setBestStackProbeRunning(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Sprout Social Automation</p>
        <h1>Sprout Social End-to-End Production Console</h1>
        <p>
          Live wiring for publishing, inbox, listening, analytics, automation, and AI workflow execution using the
          social workspace backend routes.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshAll()} disabled={loading || probeRunning}>
            {loading ? 'Refreshing...' : 'Refresh Live State'}
          </button>
          <button onClick={() => void runE2EProbe()} disabled={loading || probeRunning}>
            {probeRunning ? 'Running...' : 'Run E2E Probe'}
          </button>
          <button onClick={() => void runBestStackProbe()} disabled={loading || probeRunning || bestStackProbeRunning}>
            {bestStackProbeRunning ? 'Running Best-Stack Probe...' : 'Run Best-Stack Probe'}
          </button>
          <a href="/studio/social-studio" className="button" style={{ textDecoration: 'none' }}>
            Open Social Studio
          </a>
          <a href="/vendor-inventory-report" className="button" style={{ textDecoration: 'none' }}>
            Open Vendor Inventory
          </a>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Readiness Score</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{readiness?.readiness_score ?? 0}%</p>
          <p style={{ opacity: 0.8, marginBottom: 0 }}>
            Production ready: {readiness?.production_ready ? 'Yes' : 'No'}
          </p>
        </article>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Capability Completion</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>
            {readiness?.capability_summary.fully_wired_capabilities ?? 0}/
            {readiness?.capability_summary.total_capabilities ?? 0}
          </p>
          <p style={{ opacity: 0.8, marginBottom: 0 }}>
            Avg completion: {readiness?.capability_summary.average_completion_percent ?? 0}%
          </p>
        </article>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Growth Matrix</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{growthMatrix?.summary.average_completion_percent ?? 0}%</p>
          <p style={{ opacity: 0.8, marginBottom: 0 }}>
            done {growthMatrix?.summary.done ?? 0}, partial {growthMatrix?.summary.partial ?? 0}, missing{' '}
            {growthMatrix?.summary.missing ?? 0}
          </p>
        </article>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Integration Wiring</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{integrationSummary?.coverage_percent ?? 0}%</p>
          <p style={{ opacity: 0.8, marginBottom: 0 }}>
            configured {integrationSummary?.configured_total ?? 0}/{integrationSummary?.providers_total ?? 0}
          </p>
        </article>
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Smart Inbox</h4>
          <p style={{ marginBottom: 0 }}>Messages available: {inboxTotal}</p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Listening</h4>
          <p style={{ marginBottom: 0 }}>Mentions tracked: {listeningMentions}</p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>Automation</h4>
          <p style={{ marginBottom: 0 }}>
            Rules {automationRulesCount}, Feeds {automationFeedsCount}
          </p>
        </article>
        <article className="card">
          <h4 style={{ marginTop: 0 }}>AI and Reporting</h4>
          <p style={{ marginBottom: 0 }}>
            Templates {aiTemplatesCount}, Reports {reportsCount}
          </p>
        </article>
      </section>

      <CapabilityMatrixSection readiness={readiness} />
      <ProductionVerificationSection rows={verificationRows} />
      <VendorsSection readiness={readiness} />
      <BestStackCoverageSection rows={bestStackCoverage} />
      <BestStackProbeSection
        results={bestStackProbeResults}
        latestReport={latestBestStackReport}
        reports={bestStackReports}
        exporting={bestStackExporting}
        running={bestStackProbeRunning}
        onExportJson={() => void exportLatestBestStackReport('json')}
        onExportMarkdown={() => void exportLatestBestStackReport('markdown')}
      />
      <AuditTrailSection entries={auditLogEntries} />
      <E2EProbeSection results={probeResults} />
      <RemediationSection remediation={remediation} />
    </main>
  );
}
