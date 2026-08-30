'use client';

import { useState, useMemo, useCallback } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader } from '../../_ui/kit';
import {
  AlertTriangle,
  CheckCircle,
  Info,
  RefreshCw,
  Download,
  Search,
  Zap,
  Globe,
  Clock,
  Shield,
  TrendingUp,
} from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type TechnicalIssue = {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  detail: string;
  fix: string;
  affected_urls?: string[];
  count?: number;
};

type CoreWebVitals = {
  lcp?: number;
  fid?: number;
  cls?: number;
  ttfb?: number;
  fcp?: number;
  inp?: number;
  lcp_rating?: 'good' | 'needs-improvement' | 'poor';
  cls_rating?: 'good' | 'needs-improvement' | 'poor';
  fid_rating?: 'good' | 'needs-improvement' | 'poor';
};

type TechnicalResult = {
  analysis_id: string;
  overall_score: number;
  crawlability_score: number;
  indexability_score: number;
  performance_score: number;
  issues: TechnicalIssue[];
  core_web_vitals?: CoreWebVitals;
  mobile_friendly?: boolean;
  https_secure?: boolean;
  sitemap_found?: boolean;
  robots_txt_found?: boolean;
  structured_data_types?: string[];
  page_speed_ms?: number;
  recommendations: string[];
  quick_wins: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

type ScoreGaugeProps = Readonly<{ score: number; label: string; size?: number }>;
type SeverityIconProps = Readonly<{ s: string }>;
type VitalBadgeProps = Readonly<{ value?: number; unit: string; rating?: string }>;

function getScoreColor(score: number): string {
  if (score >= 80) return '#26d78e';
  if (score >= 60) return '#ffb867';
  return '#dc2626';
}

function getVitalRatingColor(rating?: string): string {
  if (rating === 'good') return '#26d78e';
  if (rating === 'needs-improvement') return '#ffb867';
  return '#dc2626';
}

function getQuickSignalIcon(ok?: boolean): React.ReactNode {
  if (ok === true) return <CheckCircle size={16} color="#26d78e" />;
  if (ok === false) return <AlertTriangle size={16} color="#dc2626" />;
  return <Info size={16} color="var(--muted)" />;
}

function getPageSpeedColor(pageSpeedMs: number): string {
  if (pageSpeedMs < 1000) return '#26d78e';
  if (pageSpeedMs < 3000) return '#ffb867';
  return '#dc2626';
}

function ScoreGauge({ score, label, size = 90 }: ScoreGaugeProps) {
  const r = size * 0.36,
    s = size * 0.07,
    c = Math.PI * r;
  const color = getScoreColor(score);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={size} height={size * 0.62} viewBox={`0 0 ${size} ${size * 0.62}`}>
        <path
          d={`M ${s} ${size * 0.58} A ${r} ${r} 0 0 1 ${size - s} ${size * 0.58}`}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={s}
          strokeLinecap="round"
        />
        <path
          d={`M ${s} ${size * 0.58} A ${r} ${r} 0 0 1 ${size - s} ${size * 0.58}`}
          fill="none"
          stroke={color}
          strokeWidth={s}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text
          x={size / 2}
          y={size * 0.5}
          textAnchor="middle"
          fill={color}
          style={{ fontSize: size * 0.22, fontWeight: 800 }}
        >
          {score}
        </text>
      </svg>
      <span
        style={{
          fontSize: 10,
          color: 'var(--muted)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        {label}
      </span>
    </div>
  );
}

function SeverityIcon({ s }: SeverityIconProps) {
  if (s === 'critical') return <AlertTriangle size={13} color="#dc2626" />;
  if (s === 'warning') return <AlertTriangle size={13} color="#ffb867" />;
  return <Info size={13} color="#1bc7ff" />;
}

function VitalBadge({ value, unit, rating }: VitalBadgeProps) {
  if (value == null) return <span style={{ color: 'var(--muted)', fontSize: 13 }}>—</span>;
  const color = getVitalRatingColor(rating);
  return (
    <div>
      <span style={{ fontWeight: 800, fontSize: 16, color }}>
        {value}
        {unit}
      </span>
      {rating && (
        <span style={{ display: 'block', fontSize: 10, color, fontWeight: 700, textTransform: 'uppercase' }}>
          {rating}
        </span>
      )}
    </div>
  );
}

export default function TechnicalSEOPage() {
  const [url, setUrl] = useState('');
  const [sitemap, setSitemap] = useState('');
  const [crawlDepth, setCrawlDepth] = useState('3');
  const [checkMobile, setCheckMobile] = useState(true);
  const [checkCWV, setCheckCWV] = useState(true);
  const [result, setResult] = useState<TechnicalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'issues' | 'vitals' | 'actions'>('overview');
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all');
  const [search, setSearch] = useState('');

  async function runAudit() {
    if (!url) {
      setError('URL is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<TechnicalResult>(
        '/seo-platform/technical/audit',
        'POST',
        {
          url,
          sitemap_url: sitemap || undefined,
          crawl_depth: Number.parseInt(crawlDepth, 10),
          check_mobile_friendly: checkMobile,
          check_core_web_vitals: checkCWV,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(data);
      setActiveTab('overview');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Audit failed');
    } finally {
      setLoading(false);
    }
  }

  const filteredIssues = useMemo(() => {
    if (!result?.issues) return [];
    return result.issues.filter((i) => {
      if (filter !== 'all' && i.severity !== filter) return false;
      if (
        search &&
        !i.type.toLowerCase().includes(search.toLowerCase()) &&
        !i.detail.toLowerCase().includes(search.toLowerCase())
      )
        return false;
      return true;
    });
  }, [result, filter, search]);

  const exportCSV = useCallback(() => {
    if (!result?.issues) return;
    const rows = result.issues.map(
      (i) => `"${i.severity}","${i.type}","${i.detail.replaceAll('"', '""')}","${i.fix.replaceAll('"', '""')}"`
    );
    const blob = new Blob(['Severity,Type,Detail,Fix\n' + rows.join('\n')], { type: 'text/csv' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: 'technical-audit.csv',
    });
    a.click();
    URL.revokeObjectURL(a.href);
  }, [result]);

  const critical = result?.issues?.filter((i) => i.severity === 'critical').length ?? 0;
  const warnings = result?.issues?.filter((i) => i.severity === 'warning').length ?? 0;
  const infos = result?.issues?.filter((i) => i.severity === 'info').length ?? 0;

  const card: React.CSSProperties = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(45, 212, 191, 0.65)',
  };
  const input: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box',
    fontSize: 14,
  };
  const th: React.CSSProperties = {
    textAlign: 'left',
    padding: '8px 12px',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    color: 'var(--muted)',
    borderBottom: '1px solid var(--line)',
  };
  const td: React.CSSProperties = {
    padding: '10px 12px',
    fontSize: 13,
    borderBottom: '1px solid var(--line)',
    verticalAlign: 'top',
  };

  const tabs = [
    { key: 'overview' as const, label: 'Overview' },
    { key: 'issues' as const, label: `Issues (${result?.issues?.length ?? 0})` },
    { key: 'vitals' as const, label: 'Core Web Vitals' },
    { key: 'actions' as const, label: 'Quick Wins' },
  ];

  const SEVERITY_COLORS = { critical: '#dc2626', warning: '#ffb867', info: '#1bc7ff' };

  return (
    <Page className="seo-advanced-page">
        <PageHeader
          title="Technical SEO Audit"
          subtitle="Crawlability, indexability, Core Web Vitals, structured data, and mobile readiness."
          actions={
            result ? (
              <Button onClick={exportCSV}>
                <Download size={14} />
                Export CSV
              </Button>
            ) : null
          }
        />

        {error && (
          <div style={{ ...card, color: '#dc2626', borderColor: '#dc262644', background: '#dc262611' }}>{error}</div>
        )}

        <Card>
          <CardTitle sub="URL, crawl depth, and the checks to include.">Audit setup</CardTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 16, marginTop: 16 }}>
            <Field
              id="technical-url"
              label="Website URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
            />
            <Field
              id="technical-sitemap"
              label="Sitemap URL (optional)"
              value={sitemap}
              onChange={(e) => setSitemap(e.target.value)}
              placeholder="https://example.com/sitemap.xml"
            />
            <FieldSelect
              id="technical-crawl-depth"
              label="Crawl depth"
              value={crawlDepth}
              onChange={(e) => setCrawlDepth(e.target.value)}
            >
              {['1', '2', '3', '5', '10'].map((v) => (
                <option key={v} value={v}>
                  Depth {v}
                </option>
              ))}
            </FieldSelect>
          </div>
          <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={checkMobile} onChange={(e) => setCheckMobile(e.target.checked)} />
              <span>Check mobile friendly</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={checkCWV} onChange={(e) => setCheckCWV(e.target.checked)} />
              <span>Core Web Vitals</span>
            </label>
          </div>
          <div style={{ marginTop: 16 }}>
            <Button variant="primary" onClick={() => void runAudit()} disabled={loading}>
              {loading ? <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Shield size={15} />}
              {loading ? 'Auditing…' : 'Run technical audit'}
            </Button>
          </div>
        </Card>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)', color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)' }}>
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.15)', color: '#38bdf8' }}>
                    Cached result
                  </span>
                )}
              </div>
            )}
            {/* Score cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 12, marginBottom: 20 }}>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreGauge score={result.overall_score} label="Overall" />
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreGauge score={result.crawlability_score} label="Crawlability" />
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreGauge score={result.indexability_score} label="Indexability" />
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreGauge score={result.performance_score} label="Performance" />
              </div>
            </div>

            {/* Quick signals */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
                gap: 10,
                marginBottom: 20,
              }}
            >
              {[
                { label: 'HTTPS', ok: result.https_secure, icon: <Shield size={14} /> },
                { label: 'Mobile', ok: result.mobile_friendly, icon: <Globe size={14} /> },
                { label: 'Sitemap', ok: result.sitemap_found, icon: <Globe size={14} /> },
                { label: 'robots.txt', ok: result.robots_txt_found, icon: <Globe size={14} /> },
              ].map((s) => (
                <div key={s.label} style={{ ...card, marginBottom: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                  {getQuickSignalIcon(s.ok)}
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{s.label}</span>
                </div>
              ))}
              <div style={{ ...card, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Critical
                </span>
                <span style={{ fontSize: 22, fontWeight: 800, color: critical > 0 ? '#dc2626' : '#26d78e' }}>
                  {critical}
                </span>
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Warnings
                </span>
                <span style={{ fontSize: 22, fontWeight: 800, color: warnings > 0 ? '#ffb867' : '#26d78e' }}>
                  {warnings}
                </span>
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Info
                </span>
                <span style={{ fontSize: 22, fontWeight: 800, color: 'var(--muted)' }}>{infos}</span>
              </div>
            </div>

            {/* Severity bar chart */}
            {critical + warnings + infos > 0 && (
              <div style={{ ...card }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 12,
                  }}
                >
                  Issue Distribution
                </div>
                <div style={{ display: 'flex', gap: 3, height: 16, borderRadius: 8, overflow: 'hidden' }}>
                  {critical > 0 && (
                    <div style={{ flex: critical, background: '#dc2626' }} title={`${critical} critical`} />
                  )}
                  {warnings > 0 && (
                    <div style={{ flex: warnings, background: '#ffb867' }} title={`${warnings} warnings`} />
                  )}
                  {infos > 0 && <div style={{ flex: infos, background: '#1bc7ff33' }} title={`${infos} info`} />}
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                  {[
                    ['Critical', critical, '#dc2626'],
                    ['Warnings', warnings, '#ffb867'],
                    ['Info', infos, '#1bc7ff'],
                  ].map(([l, v, c]) => (
                    <div key={l as string} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                      <div style={{ width: 10, height: 10, borderRadius: 2, background: c as string }} />
                      <span style={{ color: 'var(--muted)' }}>{l}: </span>
                      <span style={{ fontWeight: 700 }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--line)' }}>
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '8px 8px 0 0',
                    background: activeTab === t.key ? 'var(--bg-soft)' : 'transparent',
                    color: activeTab === t.key ? 'var(--brand)' : 'var(--muted)',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: 'pointer',
                    borderBottom: activeTab === t.key ? '2px solid var(--brand)' : '2px solid transparent',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Site Analysis Summary</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
                  <div>
                    {result.structured_data_types && result.structured_data_types.length > 0 && (
                      <div style={{ marginBottom: 16 }}>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: 'var(--muted)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            marginBottom: 8,
                          }}
                        >
                          Structured Data Found
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {result.structured_data_types.map((t) => (
                            <span
                              key={t}
                              style={{
                                padding: '3px 10px',
                                borderRadius: 999,
                                background: 'rgba(38,215,142,0.12)',
                                color: '#26d78e',
                                fontSize: 11,
                                fontWeight: 700,
                                border: '1px solid rgba(38,215,142,0.3)',
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {result.page_speed_ms != null && (
                      <div>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: 'var(--muted)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            marginBottom: 8,
                          }}
                        >
                          Page Speed
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Clock size={14} color="var(--muted)" />
                          <span
                            style={{
                              fontSize: 20,
                              fontWeight: 800,
                              color: getPageSpeedColor(result.page_speed_ms),
                            }}
                          >
                            {result.page_speed_ms}ms
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 8,
                      }}
                    >
                      Top Recommendations
                    </div>
                    {result.recommendations?.slice(0, 5).map((r) => (
                      <div key={r} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <TrendingUp size={12} color="var(--brand)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{r}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'issues' && (
              <div style={card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                  <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
                    <Search
                      size={13}
                      style={{
                        position: 'absolute',
                        left: 10,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: 'var(--muted)',
                      }}
                    />
                    <input
                      style={{ ...input, paddingLeft: 32, marginBottom: 0 }}
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search issues..."
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {(['all', 'critical', 'warning', 'info'] as const).map((f) => (
                      <button
                        key={f}
                        onClick={() => setFilter(f)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 6,
                          border: '1px solid var(--line)',
                          background:
                            filter === f
                              ? (SEVERITY_COLORS[f as keyof typeof SEVERITY_COLORS] ?? 'var(--brand)') + '22'
                              : 'transparent',
                          color:
                            filter === f
                              ? (SEVERITY_COLORS[f as keyof typeof SEVERITY_COLORS] ?? 'var(--brand)')
                              : 'var(--muted)',
                          fontWeight: 700,
                          fontSize: 11,
                          cursor: 'pointer',
                          textTransform: 'capitalize',
                        }}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={th}>Severity</th>
                        <th style={th}>Issue Type</th>
                        <th style={th}>Detail</th>
                        <th style={th}>Fix</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIssues.map((issue) => (
                        <tr key={`${issue.type}-${issue.detail}`}>
                          <td style={td}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <SeverityIcon s={issue.severity} />
                              <span
                                style={{
                                  fontSize: 10,
                                  fontWeight: 700,
                                  textTransform: 'uppercase',
                                  padding: '2px 6px',
                                  borderRadius: 4,
                                  background: SEVERITY_COLORS[issue.severity] + '22',
                                  color: SEVERITY_COLORS[issue.severity],
                                }}
                              >
                                {issue.severity}
                              </span>
                            </div>
                          </td>
                          <td style={{ ...td, fontWeight: 600 }}>{issue.type}</td>
                          <td style={{ ...td, color: 'var(--muted)', maxWidth: 300 }}>{issue.detail}</td>
                          <td style={{ ...td, color: '#26d78e', maxWidth: 280 }}>
                            <Zap size={11} style={{ marginRight: 4 }} />
                            {issue.fix}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'vitals' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 20px', fontSize: 15, fontWeight: 700 }}>Core Web Vitals</h3>
                {result.core_web_vitals ? (
                  <div
                    style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: 16 }}
                  >
                    {[
                      {
                        label: 'LCP',
                        value: result.core_web_vitals.lcp,
                        unit: 's',
                        rating: result.core_web_vitals.lcp_rating,
                        desc: 'Largest Contentful Paint',
                      },
                      {
                        label: 'FID / INP',
                        value: result.core_web_vitals.inp ?? result.core_web_vitals.fid,
                        unit: 'ms',
                        rating: result.core_web_vitals.fid_rating,
                        desc: 'Interaction to Next Paint',
                      },
                      {
                        label: 'CLS',
                        value: result.core_web_vitals.cls,
                        unit: '',
                        rating: result.core_web_vitals.cls_rating,
                        desc: 'Cumulative Layout Shift',
                      },
                      {
                        label: 'TTFB',
                        value: result.core_web_vitals.ttfb,
                        unit: 'ms',
                        rating: undefined,
                        desc: 'Time to First Byte',
                      },
                      {
                        label: 'FCP',
                        value: result.core_web_vitals.fcp,
                        unit: 's',
                        rating: undefined,
                        desc: 'First Contentful Paint',
                      },
                    ].map((v) => (
                      <div
                        key={v.label}
                        style={{
                          background: 'var(--bg)',
                          borderRadius: 10,
                          padding: 16,
                          border: '1px solid var(--line)',
                        }}
                      >
                        <div
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: 'var(--muted)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            marginBottom: 8,
                          }}
                        >
                          {v.label}
                        </div>
                        <VitalBadge value={v.value} unit={v.unit} rating={v.rating} />
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>{v.desc}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                    Core Web Vitals data not available. Enable the option and re-run the audit.
                  </p>
                )}
              </div>
            )}

            {activeTab === 'actions' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Quick Wins</h3>
                <div style={{ display: 'grid', gap: 10 }}>
                  {result.quick_wins?.map((w, i) => (
                    <div
                      key={w}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 12,
                        background: 'var(--bg)',
                        borderRadius: 10,
                        padding: '12px 16px',
                        border: '1px solid rgba(38,215,142,0.2)',
                      }}
                    >
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: 6,
                          background: 'rgba(38,215,142,0.15)',
                          color: '#26d78e',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          fontSize: 11,
                          fontWeight: 800,
                        }}
                      >
                        {i + 1}
                      </div>
                      <span style={{ fontSize: 13, lineHeight: 1.5 }}>{w}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </Page>
  );
}
