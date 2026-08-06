'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type ListeningKeyword = {
  id: number;
  keyword: string;
  networks: string[];
  alert_threshold: number;
  alert_on_crisis: boolean;
  created_at: string;
};

type ListeningMention = {
  id: number;
  keyword_id: number;
  network: string;
  author: string;
  text: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  reach: number;
  engagement: number;
  is_crisis: boolean;
  alert_dismissed: boolean;
  created_at: string;
};

type SentimentData = {
  sentiment_score: number;
  label: string;
  breakdown: { positive: number; neutral: number; negative: number; total: number };
  network_breakdown: Record<string, { positive: number; negative: number }>;
};

type MentionSummary = {
  total: number;
  crisis: number;
  positive: number;
  negative: number;
  neutral: number;
  total_reach: number;
};

const NETWORK_COLORS: Record<string, string> = {
  instagram: '#E1306C',
  x: '#000000',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  tiktok: '#69C9D0',
  reddit: '#FF4500',
  youtube: '#FF0000',
};

export default function SocialListeningPage() {
  const [keywords, setKeywords] = useState<ListeningKeyword[]>([]);
  const [mentions, setMentions] = useState<ListeningMention[]>([]);
  const [summary, setSummary] = useState<MentionSummary | null>(null);
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'mentions' | 'keywords' | 'sentiment'>('mentions');
  const [crisisOnly, setCrisisOnly] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [addingKeyword, setAddingKeyword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, [crisisOnly]);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      const [kData, mData, sData] = await Promise.all([
        apiGet(`/social/listening/keywords`, DEFAULT_TENANT_ID),
        apiGet(`/social/listening/mentions${crisisOnly ? '?crisis_only=true' : ''}`, DEFAULT_TENANT_ID),
        apiGet(`/social/listening/sentiment`, DEFAULT_TENANT_ID),
      ]);
      setKeywords((kData as any)?.keywords ?? []);
      setMentions((mData as any)?.mentions ?? []);
      setSummary((mData as any)?.summary ?? null);
      setSentiment(sData as SentimentData);
    } catch {
      setKeywords([]);
      setMentions([]);
      setSummary(null);
      setSentiment(null);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Social listening backend unavailable in strict no-mock mode.'
          : 'Social listening backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function addKeyword() {
    if (!newKeyword.trim()) return;
    setAddingKeyword(true);
    try {
      await apiSend(
        `/social/listening/keywords`,
        'POST',
        {
          keyword: newKeyword.trim(),
          networks: ['instagram', 'x', 'facebook', 'linkedin'],
          alert_threshold: 200,
          alert_on_crisis: true,
        },
        DEFAULT_TENANT_ID
      );
      setNewKeyword('');
      loadAll();
    } catch {
      setError('Failed to add keyword');
    } finally {
      setAddingKeyword(false);
    }
  }

  async function dismissAlert(mentionId: number) {
    try {
      await apiSend(`/social/listening/mentions/${mentionId}/dismiss`, 'PATCH', { dismissed: true }, DEFAULT_TENANT_ID);
      setMentions((prev) => prev.map((m) => (m.id === mentionId ? { ...m, alert_dismissed: true } : m)));
    } catch {
      setError('Failed to dismiss alert');
    }
  }

  async function deleteKeyword(id: number) {
    try {
      await apiSend(`/social/listening/keywords/${id}`, 'DELETE', {}, DEFAULT_TENANT_ID);
      setKeywords((prev) => prev.filter((k) => k.id !== id));
    } catch {
      setError('Failed to delete keyword');
    }
  }

  const getSentimentColor = (s: string) => (s === 'positive' ? '#22c55e' : s === 'negative' ? '#EF4444' : 'var(--muted)');
  const getSentimentBg = (s: string) => (s === 'positive' ? '#dcfce722' : s === 'negative' ? '#fee2e222' : '#eef0f4');

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Social Listening</h1>
          <p style={styles.subtitle}>
            Monitor brand mentions across 30+ networks · Track sentiment · Get crisis alerts in real time
          </p>
        </div>
        <div style={styles.headerStats}>
          {summary && (
            <>
              <div style={{ ...styles.statBadge, background: '#fee2e222', borderColor: '#EF4444' }}>
                🚨 {summary.crisis} Crisis Alerts
              </div>
              <div style={{ ...styles.statBadge, background: '#dcfce722', borderColor: '#22c55e' }}>
                📡 {(summary.total_reach / 1000).toFixed(1)}K Reach
              </div>
            </>
          )}
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          {error}{' '}
          <button onClick={() => setError(null)} style={styles.dismissBtn}>
            ✕
          </button>
        </div>
      )}

      {/* KPI Row */}
      {summary && (
        <div style={styles.kpiRow}>
          {[
            { label: 'Total Mentions', value: summary.total, icon: '🔔' },
            { label: 'Crisis Alerts', value: summary.crisis, icon: '🚨', accent: '#EF4444' },
            { label: 'Positive', value: summary.positive, icon: '✅', accent: '#22c55e' },
            { label: 'Negative', value: summary.negative, icon: '⚠️', accent: '#EF4444' },
            { label: 'Total Reach', value: `${(summary.total_reach / 1000).toFixed(1)}K`, icon: '📡' },
            {
              label: 'Sentiment Score',
              value: sentiment ? `${sentiment.sentiment_score > 0 ? '+' : ''}${sentiment.sentiment_score}` : '—',
              icon: sentiment?.label === 'positive' ? '😊' : '😐',
              accent: sentiment ? getSentimentColor(sentiment.label) : undefined,
            },
          ].map((kpi, i) => (
            <div key={i} style={{ ...styles.kpiCard, borderColor: kpi.accent ?? '#e7e9ef' }}>
              <span style={styles.kpiIcon}>{kpi.icon}</span>
              <span style={{ ...styles.kpiValue, color: kpi.accent ?? 'var(--text)' }}>{kpi.value}</span>
              <span style={styles.kpiLabel}>{kpi.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={styles.tabBar}>
        {(['mentions', 'keywords', 'sentiment'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{ ...styles.tab, ...(activeTab === tab ? styles.tabActive : {}) }}
          >
            {tab === 'mentions' ? '🔔 Mentions' : tab === 'keywords' ? '🔑 Keywords' : '📊 Sentiment'}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={styles.skeleton}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={styles.skeletonBar} />
          ))}
        </div>
      ) : (
        <>
          {/* Mentions Tab */}
          {activeTab === 'mentions' && (
            <div>
              <div style={styles.filterRow}>
                <label style={styles.filterLabel}>
                  <input
                    type="checkbox"
                    checked={crisisOnly}
                    onChange={(e) => setCrisisOnly(e.target.checked)}
                    style={{ marginRight: 6 }}
                  />
                  Show crisis alerts only
                </label>
                <span style={styles.muted}>{mentions.length} mentions</span>
              </div>
              <div style={styles.mentionList}>
                {mentions.map((mention) => (
                  <div
                    key={mention.id}
                    style={{
                      ...styles.mentionCard,
                      opacity: mention.alert_dismissed ? 0.5 : 1,
                      borderLeft: `3px solid ${mention.is_crisis ? '#EF4444' : getSentimentColor(mention.sentiment)}`,
                    }}
                  >
                    <div style={styles.mentionHeader}>
                      <div style={styles.mentionMeta}>
                        <span
                          style={{ ...styles.networkBadge, background: NETWORK_COLORS[mention.network] ?? '#e7e9ef' }}
                        >
                          {mention.network}
                        </span>
                        <span style={styles.mentionAuthor}>{mention.author}</span>
                        {mention.is_crisis && <span style={styles.crisisBadge}>🚨 CRISIS</span>}
                      </div>
                      <div style={styles.mentionActions}>
                        <span
                          style={{
                            ...styles.sentimentChip,
                            background: getSentimentBg(mention.sentiment),
                            color: getSentimentColor(mention.sentiment),
                          }}
                        >
                          {mention.sentiment}
                        </span>
                        {!mention.alert_dismissed && (
                          <button onClick={() => dismissAlert(mention.id)} style={styles.dismissBtn2}>
                            Dismiss
                          </button>
                        )}
                      </div>
                    </div>
                    <p style={styles.mentionText}>{mention.text}</p>
                    <div style={styles.mentionFooter}>
                      <span style={styles.muted}>👁 {mention.reach.toLocaleString()} reach</span>
                      <span style={styles.muted}>💬 {mention.engagement} engagements</span>
                    </div>
                  </div>
                ))}
                {mentions.length === 0 && (
                  <div style={styles.empty}>No mentions found{crisisOnly ? ' matching crisis filter' : ''}.</div>
                )}
              </div>
            </div>
          )}

          {/* Keywords Tab */}
          {activeTab === 'keywords' && (
            <div>
              <div style={styles.addKeywordRow}>
                <input
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  placeholder="Add keyword, hashtag, or phrase..."
                  style={styles.input}
                  onKeyDown={(e) => e.key === 'Enter' && addKeyword()}
                />
                <button onClick={addKeyword} disabled={addingKeyword || !newKeyword.trim()} style={styles.primaryBtn}>
                  {addingKeyword ? 'Adding…' : '+ Add Keyword'}
                </button>
              </div>
              <div style={styles.keywordList}>
                {keywords.map((kw) => (
                  <div key={kw.id} style={styles.keywordCard}>
                    <div style={styles.keywordHeader}>
                      <span style={styles.keywordText}>{kw.keyword}</span>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {kw.alert_on_crisis && <span style={styles.crisisBadge}>Crisis Alert ON</span>}
                        <button onClick={() => deleteKeyword(kw.id)} style={styles.deleteBtn}>
                          Remove
                        </button>
                      </div>
                    </div>
                    <div style={styles.keywordMeta}>
                      <span style={styles.muted}>Alert at {kw.alert_threshold.toLocaleString()}+ mentions</span>
                      <span style={styles.muted}>{kw.networks.join(' · ')}</span>
                    </div>
                  </div>
                ))}
                {keywords.length === 0 && (
                  <div style={styles.empty}>No keywords configured. Add your first keyword above.</div>
                )}
              </div>
            </div>
          )}

          {/* Sentiment Tab */}
          {activeTab === 'sentiment' && sentiment && (
            <div style={styles.sentimentView}>
              <div style={styles.sentimentScore}>
                <div style={{ ...styles.scoreCircle, borderColor: getSentimentColor(sentiment.label) }}>
                  <span style={{ ...styles.scoreNumber, color: getSentimentColor(sentiment.label) }}>
                    {sentiment.sentiment_score > 0 ? '+' : ''}
                    {sentiment.sentiment_score}
                  </span>
                  <span style={styles.scoreLabel}>{sentiment.label.toUpperCase()}</span>
                </div>
                <div style={styles.sentimentBreakdown}>
                  <div style={styles.breakdownRow}>
                    <span style={styles.breakdownLabel}>😊 Positive</span>
                    <div style={styles.progressBar}>
                      <div
                        style={{
                          ...styles.progressFill,
                          width: `${(sentiment.breakdown.positive / sentiment.breakdown.total) * 100}%`,
                          background: '#22c55e',
                        }}
                      />
                    </div>
                    <span style={styles.breakdownCount}>{sentiment.breakdown.positive}</span>
                  </div>
                  <div style={styles.breakdownRow}>
                    <span style={styles.breakdownLabel}>😐 Neutral</span>
                    <div style={styles.progressBar}>
                      <div
                        style={{
                          ...styles.progressFill,
                          width: `${(sentiment.breakdown.neutral / sentiment.breakdown.total) * 100}%`,
                          background: 'var(--muted)',
                        }}
                      />
                    </div>
                    <span style={styles.breakdownCount}>{sentiment.breakdown.neutral}</span>
                  </div>
                  <div style={styles.breakdownRow}>
                    <span style={styles.breakdownLabel}>😡 Negative</span>
                    <div style={styles.progressBar}>
                      <div
                        style={{
                          ...styles.progressFill,
                          width: `${(sentiment.breakdown.negative / sentiment.breakdown.total) * 100}%`,
                          background: '#EF4444',
                        }}
                      />
                    </div>
                    <span style={styles.breakdownCount}>{sentiment.breakdown.negative}</span>
                  </div>
                </div>
              </div>
              <div style={styles.networkSentiment}>
                <h3 style={styles.sectionTitle}>Sentiment by Network</h3>
                <div style={styles.networkGrid}>
                  {Object.entries(sentiment.network_breakdown).map(([net, data]) => (
                    <div key={net} style={styles.networkSentCard}>
                      <div style={{ ...styles.networkDot, background: NETWORK_COLORS[net] ?? '#e7e9ef' }} />
                      <span style={styles.networkName}>{net}</span>
                      <span style={{ ...styles.netSent, color: '#22c55e' }}>+{data.positive}</span>
                      <span style={{ ...styles.netSent, color: '#EF4444' }}>-{data.negative}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
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
  headerStats: { display: 'flex', gap: 10 },
  statBadge: { padding: '6px 14px', borderRadius: 8, border: '1px solid', fontSize: 13, fontWeight: 600 },
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
  dismissBtn: { background: 'none', border: 'none', color: 'var(--text)', cursor: 'pointer', fontSize: 16 },
  kpiRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))', gap: 12, marginBottom: 24 },
  kpiCard: {
    background: 'var(--card)',
    borderRadius: 10,
    padding: '14px 16px',
    border: '1px solid',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    alignItems: 'center',
    textAlign: 'center',
  },
  kpiIcon: { fontSize: 22 },
  kpiValue: { fontSize: 22, fontWeight: 700 },
  kpiLabel: { fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  tabBar: {
    display: 'flex',
    gap: 4,
    marginBottom: 20,
    background: 'var(--card)',
    borderRadius: 10,
    padding: 4,
    width: 'fit-content',
  },
  tab: {
    padding: '8px 20px',
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: 'var(--muted)',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 500,
  },
  tabActive: { background: 'var(--card)', color: 'var(--text)' },
  skeleton: { display: 'flex', flexDirection: 'column', gap: 12 },
  skeletonBar: { height: 72, background: 'var(--card)', borderRadius: 10, animation: 'pulse 1.5s infinite' },
  filterRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  filterLabel: { display: 'flex', alignItems: 'center', color: 'var(--text)', fontSize: 14, cursor: 'pointer' },
  muted: { color: 'var(--muted)', fontSize: 13 },
  mentionList: { display: 'flex', flexDirection: 'column', gap: 10 },
  mentionCard: {
    background: 'var(--card)',
    borderRadius: 10,
    padding: '14px 16px',
    border: '1px solid var(--line)',
    transition: 'opacity 0.2s',
  },
  mentionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  mentionMeta: { display: 'flex', alignItems: 'center', gap: 8 },
  networkBadge: {
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    color: '#fff',
    textTransform: 'capitalize',
  },
  mentionAuthor: { fontWeight: 600, fontSize: 14 },
  crisisBadge: {
    background: '#fee2e2',
    color: '#dc2626',
    fontSize: 11,
    padding: '2px 8px',
    borderRadius: 4,
    fontWeight: 700,
    border: '1px solid #EF444466',
  },
  mentionActions: { display: 'flex', gap: 8, alignItems: 'center' },
  sentimentChip: { padding: '3px 10px', borderRadius: 16, fontSize: 11, fontWeight: 600, textTransform: 'capitalize' },
  dismissBtn2: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--text)',
    padding: '3px 10px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
  },
  mentionText: { color: 'var(--text)', fontSize: 14, lineHeight: 1.6, margin: '0 0 10px' },
  mentionFooter: { display: 'flex', gap: 16 },
  empty: { color: 'var(--muted)', textAlign: 'center', padding: '40px 0', fontSize: 15 },
  addKeywordRow: { display: 'flex', gap: 10, marginBottom: 16 },
  input: {
    flex: 1,
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '9px 14px',
    color: 'var(--text)',
    fontSize: 14,
  },
  primaryBtn: {
    background: '#6366f1',
    border: 'none',
    color: '#fff',
    padding: '9px 18px',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
    opacity: 1,
  },
  keywordList: { display: 'flex', flexDirection: 'column', gap: 10 },
  keywordCard: { background: 'var(--card)', borderRadius: 10, padding: '14px 16px', border: '1px solid var(--line)' },
  keywordHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  keywordText: { fontWeight: 600, fontSize: 15, fontFamily: 'monospace', color: 'var(--brand)' },
  deleteBtn: {
    background: '#fee2e233',
    border: '1px solid #EF444466',
    color: '#dc2626',
    padding: '4px 10px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
  },
  keywordMeta: { display: 'flex', gap: 16 },
  sentimentView: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 24 },
  sentimentScore: {
    background: 'var(--card)',
    borderRadius: 12,
    padding: 24,
    border: '1px solid var(--line)',
    display: 'flex',
    flexDirection: 'column',
    gap: 24,
    alignItems: 'center',
  },
  scoreCircle: {
    width: 140,
    height: 140,
    borderRadius: '50%',
    border: '4px solid',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreNumber: { fontSize: 36, fontWeight: 800 },
  scoreLabel: { fontSize: 11, color: 'var(--muted)', letterSpacing: '1px' },
  sentimentBreakdown: { width: '100%', display: 'flex', flexDirection: 'column', gap: 12 },
  breakdownRow: { display: 'flex', alignItems: 'center', gap: 10 },
  breakdownLabel: { width: 90, fontSize: 13, color: 'var(--text)' },
  progressBar: { flex: 1, height: 8, background: 'var(--card)', borderRadius: 4, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 4, transition: 'width 0.6s ease' },
  breakdownCount: { fontSize: 13, fontWeight: 600, width: 30, textAlign: 'right' },
  networkSentiment: { background: 'var(--card)', borderRadius: 12, padding: 24, border: '1px solid var(--line)' },
  sectionTitle: { fontSize: 16, fontWeight: 600, marginBottom: 16, color: 'var(--text)' },
  networkGrid: { display: 'flex', flexDirection: 'column', gap: 10 },
  networkSentCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 12px',
    background: 'var(--card)',
    borderRadius: 8,
    border: '1px solid var(--line)',
  },
  networkDot: { width: 10, height: 10, borderRadius: '50%' },
  networkName: { flex: 1, fontSize: 13, textTransform: 'capitalize', fontWeight: 500 },
  netSent: { fontSize: 14, fontWeight: 700, width: 36, textAlign: 'center' },
};
