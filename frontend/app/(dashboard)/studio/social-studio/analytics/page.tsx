'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type AnalyticsMetrics, type CompetitorInsight } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('month');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  async function loadAnalytics() {
    setError(null);
    try {
      const [metricsData, competitorsData] = await Promise.all([
        socialApi.getAnalytics(period),
        socialApi.getCompetitorInsights(),
      ]);

      setMetrics(metricsData);
      setCompetitors(competitorsData || []);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setMetrics(null);
      setCompetitors([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Analytics backend unavailable in strict no-mock mode.'
          : 'Analytics backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  const kpis = metrics
    ? [
        { label: 'Impressions', value: metrics.impressions, icon: '👁️' },
        { label: 'Reach', value: metrics.reach, icon: '📡' },
        { label: 'Engagement', value: metrics.engagement, icon: '💬' },
        { label: 'Clicks', value: metrics.clicks, icon: '🔗' },
        { label: 'Conversions', value: metrics.conversions, icon: '✅' },
        { label: 'ROI', value: `${metrics.roiPercentage}%`, icon: '📊' },
      ]
    : [];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Analytics & KPIs</h1>
          <p style={styles.subtitle}>Track performance across all networks and compare with competitors</p>
          <Link href="/studio/social-studio/optimization" style={styles.optimizeLink}>
            Open AI Optimization Workspace
          </Link>
        </div>
        <div style={styles.periodSelector}>
          {(['day', 'week', 'month'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                ...styles.periodBtn,
                backgroundColor: period === p ? '#6366f1' : '#eef0f4',
                borderColor: period === p ? '#6366f1' : '#e7e9ef',
              }}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonBar} />
          <div style={styles.skeletonBar} />
          <div style={styles.skeletonBar} />
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          {metrics && (
            <div style={styles.kpiGrid}>
              {kpis.map((kpi, idx) => (
                <div key={kpi.label} style={styles.kpiCard}>
                  <div style={styles.kpiIcon}>{kpi.icon}</div>
                  <div>
                    <p style={styles.kpiLabel}>{kpi.label}</p>
                    <p style={styles.kpiValue}>
                      {typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Performance Overview */}
          {metrics && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>Performance Breakdown</h2>
              <div style={styles.breakdownGrid}>
                <div style={styles.breakdownCard}>
                  <h3 style={styles.breakdownTitle}>Engagement Rate</h3>
                  <div style={styles.breakdownBar}>
                    <div
                      style={{
                        ...styles.breakdownFill,
                        width: `${(metrics.engagement / metrics.reach) * 100}%`,
                      }}
                    />
                  </div>
                  <p style={styles.breakdownPercent}>{((metrics.engagement / metrics.reach) * 100).toFixed(1)}%</p>
                </div>

                <div style={styles.breakdownCard}>
                  <h3 style={styles.breakdownTitle}>Click-Through Rate</h3>
                  <div style={styles.breakdownBar}>
                    <div
                      style={{
                        ...styles.breakdownFill,
                        width: `${(metrics.clicks / metrics.reach) * 100}%`,
                      }}
                    />
                  </div>
                  <p style={styles.breakdownPercent}>{((metrics.clicks / metrics.reach) * 100).toFixed(1)}%</p>
                </div>

                <div style={styles.breakdownCard}>
                  <h3 style={styles.breakdownTitle}>Conversion Rate</h3>
                  <div style={styles.breakdownBar}>
                    <div
                      style={{
                        ...styles.breakdownFill,
                        width: `${(metrics.conversions / metrics.clicks) * 100}%`,
                      }}
                    />
                  </div>
                  <p style={styles.breakdownPercent}>{((metrics.conversions / metrics.clicks) * 100).toFixed(1)}%</p>
                </div>
              </div>
            </section>
          )}

          {/* Competitor Insights */}
          {competitors.length > 0 && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>Competitor Analysis</h2>
              <div style={styles.competitorGrid}>
                {competitors.map((comp, idx) => (
                  <div key={comp.competitor} style={styles.competitorCard}>
                    <div style={styles.competitorHeader}>
                      <h3 style={styles.competitorName}>{comp.competitor}</h3>
                      <span style={styles.networkBadge}>{comp.network}</span>
                    </div>

                    <div style={styles.competitorMetrics}>
                      <div style={styles.compMetric}>
                        <span style={styles.compLabel}>Followers</span>
                        <span style={styles.compValue}>{(comp.followers / 1000).toFixed(0)}K</span>
                      </div>
                      <div style={styles.compMetric}>
                        <span style={styles.compLabel}>Engagement</span>
                        <span style={styles.compValue}>{comp.engagement_rate}%</span>
                      </div>
                      <div style={styles.compMetric}>
                        <span style={styles.compLabel}>Avg Likes</span>
                        <span style={styles.compValue}>{comp.average_likes}</span>
                      </div>
                      <div style={styles.compMetric}>
                        <span style={styles.compLabel}>Avg Comments</span>
                        <span style={styles.compValue}>{comp.average_comments}</span>
                      </div>
                    </div>

                    <div style={styles.competitorStrategy}>
                      <div style={styles.strategyItem}>
                        <span style={styles.strategyLabel}>Posting Frequency:</span>
                        <span>{comp.posting_frequency}</span>
                      </div>
                      <div style={styles.strategyItem}>
                        <span style={styles.strategyLabel}>Best Time:</span>
                        <span>{comp.best_posting_time}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Insights */}
          {metrics && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>AI-Powered Insights</h2>
              <div style={styles.insightsList}>
                <div style={styles.insightItem}>
                  <span style={styles.insightIcon}>💡</span>
                  <div>
                    <p style={styles.insightTitle}>Peak Engagement Times</p>
                    <p style={styles.insightText}>
                      Your audience is most active between 2-4 PM UTC. Consider scheduling posts around these times for
                      maximum reach.
                    </p>
                  </div>
                </div>

                <div style={styles.insightItem}>
                  <span style={styles.insightIcon}>📈</span>
                  <div>
                    <p style={styles.insightTitle}>ROI Opportunity</p>
                    <p style={styles.insightText}>
                      Your ROI of {metrics.roiPercentage}% is above industry average. Increase posting frequency by 20%
                      to maximize returns.
                    </p>
                  </div>
                </div>

                <div style={styles.insightItem}>
                  <span style={styles.insightIcon}>🎯</span>
                  <div>
                    <p style={styles.insightTitle}>Competitor Gap</p>
                    <p style={styles.insightText}>
                      Competitors average{' '}
                      {(competitors.reduce((a, c) => a + c.engagement_rate, 0) / competitors.length).toFixed(1)}%
                      engagement. You're{' '}
                      {(competitors[0].engagement_rate - (metrics.engagement / metrics.reach) * 100).toFixed(1)}%
                      behind.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    padding: '32px 24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--muted)',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--muted)',
    margin: 0,
  },
  optimizeLink: {
    display: 'inline-block',
    marginTop: '12px',
    color: 'var(--brand)',
    textDecoration: 'none',
    fontWeight: 700,
  },
  periodSelector: {
    display: 'flex',
    gap: '8px',
  },
  errorBanner: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '12px 14px',
    borderRadius: '10px',
    marginBottom: '16px',
  },
  periodBtn: {
    padding: '8px 16px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
    gap: '16px',
    marginBottom: '32px',
  },
  kpiCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '20px',
  },
  kpiIcon: {
    fontSize: '32px',
  },
  kpiLabel: {
    margin: '0 0 4px',
    fontSize: '12px',
    color: 'var(--muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  kpiValue: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 700,
    color: 'var(--text)',
  },
  section: {
    marginBottom: '32px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '16px',
    color: 'var(--text)',
  },
  breakdownGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))',
    gap: '16px',
  },
  breakdownCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '16px',
  },
  breakdownTitle: {
    margin: '0 0 12px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  breakdownBar: {
    height: '8px',
    backgroundColor: 'var(--card)',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  breakdownFill: {
    height: '100%',
    backgroundColor: '#6366f1',
    transition: 'width 0.3s',
  },
  breakdownPercent: {
    margin: 0,
    fontSize: '12px',
    color: 'var(--muted)',
  },
  competitorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
    gap: '16px',
  },
  competitorCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '16px',
  },
  competitorHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  competitorName: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  networkBadge: {
    display: 'inline-block',
    padding: '4px 8px',
    backgroundColor: '#6366f126',
    color: 'var(--brand)',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
  },
  competitorMetrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))',
    gap: '12px',
    marginBottom: '12px',
    paddingBottom: '12px',
    borderBottom: '1px solid var(--line)',
  },
  compMetric: {
    display: 'flex',
    flexDirection: 'column',
  },
  compLabel: {
    fontSize: '11px',
    color: 'var(--muted)',
    marginBottom: '3px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  compValue: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  competitorStrategy: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  strategyItem: {
    display: 'flex',
    flexDirection: 'column',
    fontSize: '12px',
  },
  strategyLabel: {
    color: 'var(--muted)',
    marginBottom: '2px',
    fontWeight: 500,
  },
  insightsList: {
    display: 'grid',
    gap: '12px',
  },
  insightItem: {
    display: 'flex',
    gap: '16px',
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '8px',
    padding: '16px',
  },
  insightIcon: {
    fontSize: '24px',
    minWidth: '24px',
  },
  insightTitle: {
    margin: '0 0 4px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  insightText: {
    margin: 0,
    fontSize: '13px',
    color: 'var(--muted)',
    lineHeight: '1.4',
  },
  skeleton: {
    display: 'grid',
    gap: '16px',
    marginBottom: '32px',
  },
  skeletonBar: {
    height: '150px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
};
