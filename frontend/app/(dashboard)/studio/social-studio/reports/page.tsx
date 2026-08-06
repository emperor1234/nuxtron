'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type SocialGrowthIntegrationItem, type SocialGrowthMatrixResponse } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type Report = {
  id: number;
  name: string;
  report_type: string;
  networks: string[];
  date_range: string;
  metrics: string[];
  schedule: string;
  export_format: string;
  status: string;
  generated_at: string | null;
  export_url: string | null;
  created_at: string;
};

const NETWORK_COLORS: Record<string, string> = {
  instagram: '#E1306C',
  x: '#1DA1F2',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  tiktok: '#69C9D0',
  youtube: '#FF0000',
  all: '#6366f1',
};

const STATUS_STYLE: Record<string, { bg: string; color: string }> = {
  ready: { bg: '#dcfce722', color: '#22c55e' },
  generating: { bg: '#1e3a5f22', color: 'var(--brand)' },
  scheduled: { bg: '#fef3c722', color: '#F59E0B' },
  failed: { bg: '#fee2e222', color: '#EF4444' },
};

const ALL_METRICS = [
  'impressions',
  'reach',
  'engagement_rate',
  'followers_growth',
  'link_clicks',
  'profile_visits',
  'saves',
  'shares',
  'video_views',
  'story_views',
  'mentions',
  'hashtag_performance',
  'post_frequency',
  'best_posting_times',
];
const ALL_NETWORKS = ['all', 'instagram', 'x', 'facebook', 'linkedin', 'tiktok', 'youtube'];

export default function ReportBuilderPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewForm, setShowNewForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [exportingId, setExportingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [growthMatrix, setGrowthMatrix] = useState<SocialGrowthIntegrationItem[]>([]);
  const [growthSummary, setGrowthSummary] = useState<SocialGrowthMatrixResponse['summary'] | null>(null);

  // New report form
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('engagement');
  const [newNetworks, setNewNetworks] = useState<string[]>(['all']);
  const [newDateRange, setNewDateRange] = useState('last_30_days');
  const [newMetrics, setNewMetrics] = useState<string[]>([
    'impressions',
    'reach',
    'engagement_rate',
    'followers_growth',
  ]);
  const [newSchedule, setNewSchedule] = useState('manual');
  const [newFormat, setNewFormat] = useState('pdf');

  useEffect(() => {
    void loadReports();
    void loadGrowthMatrix();
  }, []);

  async function loadReports() {
    setLoading(true);
    setError(null);
    try {
      const data = await socialApi.listReports();
      setReports(data as Report[]);
    } catch {
      setReports([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Social reports backend unavailable in strict no-mock mode.'
          : 'Social reports backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadGrowthMatrix() {
    try {
      const response = await socialApi.getGrowthIntegrationMatrix();
      setGrowthMatrix(Array.isArray(response.matrix) ? response.matrix : []);
      setGrowthSummary(response.summary ?? null);
    } catch {
      setGrowthMatrix([]);
      setGrowthSummary(null);
    }
  }

  async function createReport() {
    if (!newName.trim() || newNetworks.length === 0 || newMetrics.length === 0) return;
    setCreating(true);
    try {
      const report = await socialApi.createReport({
        name: newName.trim(),
        report_type: newType,
        networks: newNetworks,
        date_range: newDateRange,
        metrics: newMetrics,
        schedule: newSchedule,
        export_format: newFormat,
      });
      setReports((prev) => [...prev, report as Report]);
      setShowNewForm(false);
      setNewName('');
      setSuccessMsg('Report created and is now generating...');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch {
      setError('Failed to create report');
    } finally {
      setCreating(false);
    }
  }

  async function exportReport(report: Report) {
    setExportingId(report.id);
    try {
      const data = await socialApi.exportReport(report.id);
      const url = (data as any)?.export_url;
      if (url) {
        setSuccessMsg(`Report exported: ${url}`);
      } else {
        setSuccessMsg('Export queued. Download link will appear shortly.');
      }
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch {
      setError('Failed to export report');
    } finally {
      setExportingId(null);
    }
  }

  async function deleteReport(id: number) {
    setDeletingId(id);
    try {
      await socialApi.deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError('Failed to delete report');
    } finally {
      setDeletingId(null);
    }
  }

  const toggleMetric = (m: string) =>
    setNewMetrics((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));
  const toggleNetwork = (n: string) =>
    setNewNetworks((prev) => (prev.includes(n) ? prev.filter((x) => x !== n) : [...prev, n]));

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Report Builder</h1>
          <p style={styles.subtitle}>
            Build custom analytics reports · Export as PDF, Excel, or CSV · Schedule recurring delivery
          </p>
        </div>
        <button onClick={() => setShowNewForm(!showNewForm)} style={styles.primaryBtn}>
          + New Report
        </button>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          {error}{' '}
          <button onClick={() => setError(null)} style={styles.iconBtn}>
            ✕
          </button>
        </div>
      )}
      {successMsg && <div style={styles.successBanner}>✅ {successMsg}</div>}

      {growthSummary && (
        <section style={styles.growthCard}>
          <div style={styles.growthHeader}>
            <div>
              <h3 style={styles.growthTitle}>Integration ROI & Completion Matrix</h3>
              <p style={styles.growthSubtitle}>Live production-grade progress for acquisition and revenue integrations.</p>
            </div>
            <div style={styles.growthStatsRow}>
              <span style={{ ...styles.growthStatChip, borderColor: '#6366f133' }}>
                Required Done: {growthSummary.required_done}/{growthSummary.required_integrations}
              </span>
              <span style={{ ...styles.growthStatChip, borderColor: '#22C55E33' }}>Done: {growthSummary.done}</span>
              <span style={{ ...styles.growthStatChip, borderColor: '#F59E0B33' }}>Partial: {growthSummary.partial}</span>
              <span style={{ ...styles.growthStatChip, borderColor: '#EF444433' }}>Missing: {growthSummary.missing}</span>
              <span style={styles.growthStatChip}>Avg: {growthSummary.average_completion_percent}%</span>
            </div>
          </div>
          <div style={styles.growthTableWrap}>
            <table style={styles.growthTable}>
              <thead>
                <tr>
                  <th style={styles.growthTh}>Integration</th>
                  <th style={styles.growthTh}>Phase</th>
                  <th style={styles.growthTh}>ROI</th>
                  <th style={styles.growthTh}>Status</th>
                  <th style={styles.growthTh}>Done</th>
                  <th style={styles.growthTh}>Vendors</th>
                  <th style={styles.growthTh}>Left</th>
                </tr>
              </thead>
              <tbody>
                {growthMatrix.map((item) => {
                  const statusColor =
                    item.implementation_status === 'done'
                      ? '#22c55e'
                      : item.implementation_status === 'missing'
                        ? '#EF4444'
                        : '#F59E0B';
                  return (
                    <tr key={item.integration_key}>
                      <td style={styles.growthTd}>{item.integration}</td>
                      <td style={styles.growthTd}>{item.phase.replace(/_/g, ' ')}</td>
                      <td style={styles.growthTd}>#{item.roi_priority} · {'★'.repeat(Math.max(1, item.impact_stars))}</td>
                      <td style={styles.growthTd}>
                        <span style={{ ...styles.statusDot, background: statusColor }} />
                        {item.implementation_status}
                      </td>
                      <td style={styles.growthTd}>
                        <div style={styles.progressWrap}>
                          <div style={{ ...styles.progressFill, width: `${item.completion_percent}%` }} />
                        </div>
                        <span>{item.completion_percent}%</span>
                      </td>
                      <td style={styles.growthTd}>{item.vendors.slice(0, 2).join(', ')}</td>
                      <td style={styles.growthTd}>{item.left_to_complete[0] || 'Fully wired'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* New Report Form */}
      {showNewForm && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>Configure New Report</h3>
          <div style={styles.formGrid}>
            <div style={{ ...styles.formGroup, gridColumn: '1 / -1' }}>
              <label style={styles.label}>Report Name</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Q3 Cross-Platform Performance"
                style={styles.input}
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Report Type</label>
              <select value={newType} onChange={(e) => setNewType(e.target.value)} style={styles.input}>
                {[
                  'engagement',
                  'performance',
                  'growth',
                  'content',
                  'audience',
                  'paid_vs_organic',
                  'competitive',
                  'executive_summary',
                ].map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Date Range</label>
              <select value={newDateRange} onChange={(e) => setNewDateRange(e.target.value)} style={styles.input}>
                {[
                  'last_7_days',
                  'last_14_days',
                  'last_30_days',
                  'last_90_days',
                  'last_12_months',
                  'year_to_date',
                  'custom',
                ].map((r) => (
                  <option key={r} value={r}>
                    {r.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Schedule</label>
              <select value={newSchedule} onChange={(e) => setNewSchedule(e.target.value)} style={styles.input}>
                {['manual', 'weekly', 'monthly', 'quarterly'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Export Format</label>
              <select value={newFormat} onChange={(e) => setNewFormat(e.target.value)} style={styles.input}>
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel (XLSX)</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </div>
            <div style={{ ...styles.formGroup, gridColumn: '1 / -1' }}>
              <label style={styles.label}>Networks</label>
              <div style={styles.chipRow}>
                {ALL_NETWORKS.map((n) => (
                  <button
                    key={n}
                    onClick={() => toggleNetwork(n)}
                    style={{
                      ...styles.chip,
                      ...(newNetworks.includes(n)
                        ? { background: NETWORK_COLORS[n], color: '#fff', borderColor: NETWORK_COLORS[n] }
                        : {}),
                    }}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ ...styles.formGroup, gridColumn: '1 / -1' }}>
              <label style={styles.label}>Metrics to Include ({newMetrics.length} selected)</label>
              <div style={styles.chipRow}>
                {ALL_METRICS.map((m) => (
                  <button
                    key={m}
                    onClick={() => toggleMetric(m)}
                    style={{
                      ...styles.chip,
                      ...(newMetrics.includes(m)
                        ? { background: '#6366f1', color: '#fff', borderColor: '#6366f1' }
                        : {}),
                    }}
                  >
                    {m.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div style={styles.formActions}>
            <button onClick={() => setShowNewForm(false)} style={styles.cancelBtn}>
              Cancel
            </button>
            <button onClick={createReport} disabled={creating || !newName.trim()} style={styles.primaryBtn}>
              {creating ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
        </div>
      )}

      {/* Report List */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2].map((i) => (
            <div key={i} style={{ height: 140, background: 'var(--card)', borderRadius: 12 }} />
          ))}
        </div>
      ) : (
        <div style={styles.reportList}>
          {reports.length === 0 && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📊</div>
              <p style={styles.emptyTitle}>No reports yet</p>
              <p style={styles.emptyDesc}>Create your first custom report to analyze your social performance.</p>
            </div>
          )}
          {reports.map((report) => {
            const ss = STATUS_STYLE[report.status] ?? STATUS_STYLE.scheduled;
            return (
              <div key={report.id} style={styles.reportCard}>
                <div style={styles.reportHeader}>
                  <div style={styles.reportLeft}>
                    <div style={styles.reportIcon}>📊</div>
                    <div>
                      <div style={styles.reportName}>{report.name}</div>
                      <div style={styles.reportMeta}>
                        {report.report_type.replace(/_/g, ' ')} · {report.date_range.replace(/_/g, ' ')} ·{' '}
                        {report.schedule}
                      </div>
                    </div>
                  </div>
                  <div style={styles.reportRight}>
                    <span style={{ ...styles.statusBadge, ...ss }}>{report.status}</span>
                    {report.status === 'ready' && (
                      <button
                        onClick={() => exportReport(report)}
                        disabled={exportingId === report.id}
                        style={styles.exportBtn}
                      >
                        {exportingId === report.id ? 'Exporting…' : `⬇ Export ${report.export_format.toUpperCase()}`}
                      </button>
                    )}
                    <button
                      onClick={() => deleteReport(report.id)}
                      disabled={deletingId === report.id}
                      style={styles.deleteBtn}
                    >
                      🗑
                    </button>
                  </div>
                </div>
                <div style={styles.reportBody}>
                  <div style={styles.networksRow}>
                    {report.networks.map((n) => (
                      <span key={n} style={{ ...styles.netTag, background: NETWORK_COLORS[n] ?? '#e7e9ef' }}>
                        {n}
                      </span>
                    ))}
                  </div>
                  <div style={styles.metricsRow}>
                    {report.metrics.map((m) => (
                      <span key={m} style={styles.metricTag}>
                        {m.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>
                {report.generated_at && (
                  <div style={styles.reportFooter}>Generated: {new Date(report.generated_at).toLocaleString()}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'var(--card)',
    minHeight: '100vh',
    padding: '32px 40px',
    color: 'var(--text)',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 13, display: 'block', marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: '-0.5px' },
  subtitle: { color: 'var(--muted)', fontSize: 14, marginTop: 6, lineHeight: 1.5 },
  primaryBtn: {
    background: '#6366f1',
    border: 'none',
    color: '#fff',
    padding: '9px 18px',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
  },
  errorBanner: {
    background: '#fee2e2',
    border: '1px solid #EF4444',
    borderRadius: 8,
    padding: '10px 16px',
    marginBottom: 16,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 14,
  },
  successBanner: {
    background: '#dcfce733',
    border: '1px solid #22c55e',
    borderRadius: 8,
    padding: '10px 16px',
    marginBottom: 16,
    fontSize: 14,
    color: '#22c55e',
  },
  iconBtn: { background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 16, padding: 4 },
  formCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 24 },
  formTitle: { fontSize: 17, fontWeight: 600, marginBottom: 18, color: 'var(--text)' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 },
  formGroup: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 12, color: 'var(--muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' },
  input: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '9px 14px',
    color: 'var(--text)',
    fontSize: 14,
  },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  chip: {
    padding: '5px 12px',
    borderRadius: 6,
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--muted)',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 500,
    textTransform: 'capitalize',
  },
  formActions: { display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' },
  cancelBtn: {
    background: 'transparent',
    border: '1px solid var(--line)',
    color: 'var(--muted)',
    padding: '9px 18px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 14,
  },
  reportList: { display: 'flex', flexDirection: 'column', gap: 14 },
  reportCard: { background: 'var(--card)', borderRadius: 12, border: '1px solid var(--line)', overflow: 'hidden' },
  reportHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid var(--line)',
  },
  reportLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  reportIcon: { fontSize: 28, lineHeight: 1 },
  reportName: { fontWeight: 600, fontSize: 16 },
  reportMeta: { fontSize: 12, color: 'var(--muted)', marginTop: 3, textTransform: 'capitalize' },
  reportRight: { display: 'flex', alignItems: 'center', gap: 10 },
  statusBadge: { padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600, textTransform: 'capitalize' },
  exportBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--text)',
    padding: '6px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: 18,
    color: '#EF4444',
    padding: '4px 6px',
  },
  reportBody: { padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 8 },
  networksRow: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  netTag: {
    padding: '3px 8px',
    borderRadius: 4,
    color: '#fff',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'capitalize',
  },
  metricsRow: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  metricTag: {
    padding: '3px 8px',
    borderRadius: 4,
    background: 'var(--card)',
    color: 'var(--muted)',
    fontSize: 11,
    textTransform: 'capitalize',
  },
  reportFooter: { padding: '8px 20px', borderTop: '1px solid var(--line)', fontSize: 11, color: 'var(--muted)' },
  emptyState: { textAlign: 'center', padding: '80px 0' },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: 600, marginBottom: 8 },
  emptyDesc: { color: 'var(--muted)', fontSize: 14 },
  growthCard: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
  },
  growthHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 12,
  },
  growthTitle: { fontSize: 18, margin: 0, fontWeight: 700 },
  growthSubtitle: { fontSize: 13, color: 'var(--muted)', margin: '6px 0 0' },
  growthStatsRow: { display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-end' },
  growthStatChip: {
    fontSize: 12,
    borderRadius: 999,
    border: '1px solid var(--line)',
    padding: '4px 10px',
    color: '#D5D9E2',
    background: 'var(--card)',
  },
  growthTableWrap: { overflowX: 'auto' },
  growthTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 12,
    minWidth: 960,
  },
  growthTh: {
    textAlign: 'left',
    color: 'var(--muted)',
    borderBottom: '1px solid var(--line)',
    padding: '10px 8px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    fontWeight: 600,
  },
  growthTd: {
    borderBottom: '1px solid var(--line)',
    padding: '10px 8px',
    verticalAlign: 'top',
    color: 'var(--text)',
  },
  statusDot: {
    display: 'inline-block',
    width: 8,
    height: 8,
    borderRadius: '50%',
    marginRight: 6,
  },
  progressWrap: {
    width: 120,
    height: 6,
    borderRadius: 999,
    background: 'var(--card)',
    overflow: 'hidden',
    marginBottom: 4,
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #22c55e 0%, #6366f1 100%)',
  },
};
