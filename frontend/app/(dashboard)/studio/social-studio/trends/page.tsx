'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type SocialTrend } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

export default function TrendsPage() {
  const [trends, setTrends] = useState<SocialTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTrends();
  }, []);

  async function loadTrends() {
    setError(null);
    try {
      const result = await socialApi.fetchTrends();
      setTrends(result || []);
    } catch (err) {
      console.error('Failed to load trends:', err);
      setTrends([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Trends backend unavailable in strict no-mock mode.'
          : 'Trends backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  const getMomentumColor = (momentum: string) => {
    switch (momentum) {
      case 'emerging':
        return '#8B5CF6';
      case 'uptrend':
        return '#10B981';
      case 'peak':
        return '#F59014';
      case 'downtrend':
        return '#EF4444';
      default:
        return 'var(--muted)';
    }
  };

  const getMomentumIcon = (momentum: string) => {
    switch (momentum) {
      case 'emerging':
        return '🌱';
      case 'uptrend':
        return '📈';
      case 'peak':
        return '🔝';
      case 'downtrend':
        return '📉';
      default:
        return '→';
    }
  };

  const categories = ['Technology', 'Lifestyle', 'Fashion', 'Marketing', 'Business'];
  const filtered =
    selectedCategory && selectedCategory !== 'All' ? trends.filter((t) => t.category === selectedCategory) : trends;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Social Trends & Intelligence</h1>
          <p style={styles.subtitle}>Real-time trending topics with ROI forecasting and competitive analysis</p>
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {/* Category Filter */}
      <div style={styles.filterBar}>
        <button
          onClick={() => setSelectedCategory(null)}
          style={{
            ...styles.filterBtn,
            backgroundColor: !selectedCategory ? '#6366f1' : '#eef0f4',
            color: 'var(--text)',
          }}
        >
          All Trends
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            style={{
              ...styles.filterBtn,
              backgroundColor: selectedCategory === cat ? '#6366f1' : '#eef0f4',
              color: 'var(--text)',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Trends Grid */}
      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
        </div>
      ) : (
        <>
          {filtered.length > 0 ? (
            <div style={styles.trendsGrid}>
              {filtered.map((trend) => (
                <div key={trend.id} style={styles.trendCard}>
                  <div style={styles.trendHeader}>
                    <div>
                      <h2 style={styles.trendTopic}>{trend.topic}</h2>
                      <p style={styles.trendCategory}>{trend.category}</p>
                    </div>
                    <div
                      style={{
                        ...styles.momentumBadge,
                        backgroundColor: getMomentumColor(trend.momentum) + '26',
                        borderColor: getMomentumColor(trend.momentum),
                      }}
                    >
                      <span style={{ fontSize: '20px' }}>{getMomentumIcon(trend.momentum)}</span>
                      <span style={{ color: getMomentumColor(trend.momentum), fontWeight: 600 }}>{trend.momentum}</span>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div style={styles.metricsGrid}>
                    <div style={styles.metricCard}>
                      <span style={styles.metricLabel}>Volume</span>
                      <span style={styles.metricValue}>{trend.volume.toLocaleString()}</span>
                    </div>
                    <div style={styles.metricCard}>
                      <span style={styles.metricLabel}>Growth Rate</span>
                      <span style={styles.metricValue}>
                        {trend.growthRate > 0 ? '↗️' : '↘️'} {Math.abs(trend.growthRate)}%
                      </span>
                    </div>
                    <div style={styles.metricCard}>
                      <span style={styles.metricLabel}>ROI Potential</span>
                      <span
                        style={{
                          ...styles.metricValue,
                          color: trend.roiPotential > 7 ? '#10B981' : '#F59014',
                        }}
                      >
                        {trend.roiPotential}/10
                      </span>
                    </div>
                  </div>

                  {/* ROI Forecast */}
                  <div
                    style={{
                      ...styles.forecastBox,
                      borderLeftColor: getMomentumColor(trend.momentum),
                    }}
                  >
                    <span style={styles.forecastLabel}>ROI Forecast:</span>
                    <p style={styles.forecastText}>{trend.roiForecast}</p>
                  </div>

                  {/* Related */}
                  <div style={styles.relatedSection}>
                    <div>
                      <span style={styles.relatedLabel}>Related Hashtags:</span>
                      <div style={styles.tagGrid}>
                        {trend.relatedHashtags.map((tag, idx) => (
                          <span key={idx} style={styles.tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span style={styles.relatedLabel}>Top Accounts:</span>
                      <div style={styles.tagGrid}>
                        {trend.relatedAccounts.map((acc, idx) => (
                          <span key={idx} style={styles.accountTag}>
                            {acc}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Action */}
                  <button
                    style={styles.actionBtn}
                    onClick={() => {
                      alert(`Creating post with trend: ${trend.topic}`);
                    }}
                  >
                    Create Post with This Trend
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>🔍</div>
              <h2>No Trends Found</h2>
              <p>Try selecting a different category</p>
            </div>
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
  errorBanner: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '12px 14px',
    borderRadius: '10px',
    marginBottom: '16px',
  },
  filterBar: {
    display: 'flex',
    gap: '12px',
    marginBottom: '32px',
    flexWrap: 'wrap',
  },
  filterBtn: {
    padding: '8px 16px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  trendsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 380px), 1fr))',
    gap: '20px',
  },
  trendCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '20px',
    transition: 'all 0.3s',
  },
  trendHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
    gap: '12px',
  },
  trendTopic: {
    fontSize: '18px',
    fontWeight: 700,
    margin: '0 0 4px',
    color: 'var(--text)',
  },
  trendCategory: {
    fontSize: '12px',
    color: 'var(--muted)',
    margin: 0,
  },
  momentumBadge: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
    padding: '12px',
    borderRadius: '8px',
    border: '2px solid',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
    gap: '12px',
    marginBottom: '16px',
  },
  metricCard: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'var(--card)',
    padding: '12px',
    borderRadius: '6px',
    textAlign: 'center',
  },
  metricLabel: {
    fontSize: '11px',
    color: 'var(--muted)',
    marginBottom: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  metricValue: {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--text)',
  },
  forecastBox: {
    borderLeft: '3px solid #6366f1',
    paddingLeft: '12px',
    marginBottom: '16px',
    paddingTop: '8px',
    paddingBottom: '8px',
  },
  forecastLabel: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--muted)',
  },
  forecastText: {
    margin: '4px 0 0',
    fontSize: '14px',
    color: 'var(--text)',
    lineHeight: '1.4',
  },
  relatedSection: {
    marginBottom: '16px',
  },
  relatedLabel: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--muted)',
    marginBottom: '8px',
    textTransform: 'uppercase',
  },
  tagGrid: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  tag: {
    display: 'inline-block',
    padding: '4px 10px',
    backgroundColor: '#8B5CF626',
    color: 'var(--brand)',
    borderRadius: '4px',
    fontSize: '12px',
  },
  accountTag: {
    display: 'inline-block',
    padding: '4px 10px',
    backgroundColor: '#6366f126',
    color: 'var(--brand)',
    borderRadius: '4px',
    fontSize: '12px',
  },
  actionBtn: {
    width: '100%',
    padding: '10px',
    backgroundColor: '#6366f1',
    color: 'var(--text)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  skeleton: {
    display: 'grid',
    gap: '20px',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 380px), 1fr))',
  },
  skeletonCard: {
    height: '400px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 24px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    border: '1px dashed #e7e9ef',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
};
