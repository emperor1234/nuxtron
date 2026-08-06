'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AdCampaign = {
  id: number;
  name: string;
  objective: string;
  network: string;
  status: string;
  budget_daily: number;
  budget_total: number;
  spent: number;
  impressions: number;
  reach: number;
  clicks: number;
  conversions: number;
  ctr: number;
  cpc: number;
  roas: number;
  start_date: string;
  end_date: string;
  audience_targeting: Record<string, any>;
  created_at: string;
};

type AdSummary = {
  total_campaigns: number;
  active: number;
  total_spent: number;
  total_impressions: number;
  total_conversions: number;
  avg_roas: number;
};

type ByNetwork = Record<
  string,
  { impressions: number; clicks: number; conversions: number; spent: number; avg_roas: number }
>;

const NETWORK_COLORS: Record<string, string> = {
  facebook: '#1877F2',
  instagram: '#E1306C',
  linkedin: '#0A66C2',
  x: '#1DA1F2',
  tiktok: '#69C9D0',
  youtube: '#FF0000',
  snapchat: '#FFFC00',
};

const STATUS_STYLE: Record<string, { bg: string; color: string }> = {
  active: { bg: '#dcfce722', color: '#22c55e' },
  paused: { bg: '#fef3c722', color: '#F59E0B' },
  archived: { bg: '#eef0f4', color: 'var(--muted)' },
  pending_review: { bg: '#eef0f4', color: 'var(--brand)' },
};

export default function PaidSocialAdsPage() {
  const [campaigns, setCampaigns] = useState<AdCampaign[]>([]);
  const [summary, setSummary] = useState<AdSummary | null>(null);
  const [byNetwork, setByNetwork] = useState<ByNetwork>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'campaigns' | 'analytics' | 'boost'>('campaigns');
  const [showNewForm, setShowNewForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New campaign form state
  const [newName, setNewName] = useState('');
  const [newObjective, setNewObjective] = useState('awareness');
  const [newNetwork, setNewNetwork] = useState('facebook');
  const [newBudgetDaily, setNewBudgetDaily] = useState('50');
  const [newBudgetTotal, setNewBudgetTotal] = useState('500');
  const [newStartDate, setNewStartDate] = useState('');
  const [newEndDate, setNewEndDate] = useState('');

  // Boost form state
  const [boostPostId, setBoostPostId] = useState('');
  const [boostNetwork, setBoostNetwork] = useState('facebook');
  const [boostBudget, setBoostBudget] = useState('100');
  const [boostDays, setBoostDays] = useState('7');
  const [boosting, setBoosting] = useState(false);
  const [boostSuccess, setBoostSuccess] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet('/social/ads/analytics', DEFAULT_TENANT_ID);
      setCampaigns((data as any)?.campaigns ?? []);
      setSummary((data as any)?.paid_summary ?? null);
      setByNetwork((data as any)?.by_network ?? {});
    } catch {
      setCampaigns([]);
      setSummary(null);
      setByNetwork({});
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Paid ads backend unavailable in strict no-mock mode.'
          : 'Paid ads backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function createCampaign() {
    if (!newName.trim() || !newStartDate || !newEndDate) return;
    setCreating(true);
    try {
      const data = await apiSend(
        '/social/ads/campaigns',
        'POST',
        {
          name: newName.trim(),
          objective: newObjective,
          network: newNetwork,
          budget_daily: parseFloat(newBudgetDaily),
          budget_total: parseFloat(newBudgetTotal),
          start_date: newStartDate,
          end_date: newEndDate,
          audience_targeting: {},
          creative_ids: [],
        },
        DEFAULT_TENANT_ID
      );
      setCampaigns((prev) => [...prev, (data as any).campaign]);
      setShowNewForm(false);
      setNewName('');
    } catch {
      setError('Failed to create campaign');
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(campaign: AdCampaign) {
    const newStatus = campaign.status === 'active' ? 'paused' : 'active';
    try {
      await apiSend(`/social/ads/campaigns/${campaign.id}/status?status=${newStatus}`, 'PATCH', {}, DEFAULT_TENANT_ID);
      setCampaigns((prev) => prev.map((c) => (c.id === campaign.id ? { ...c, status: newStatus } : c)));
    } catch {
      setError('Failed to update campaign status');
    }
  }

  async function boostPost() {
    if (!boostPostId.trim()) return;
    setBoosting(true);
    try {
      await apiSend(
        '/social/ads/boost',
        'POST',
        {
          post_id: boostPostId.trim(),
          network: boostNetwork,
          budget_total: parseFloat(boostBudget),
          duration_days: Number.parseInt(boostDays, 10),
          objective: 'engagement',
        },
        DEFAULT_TENANT_ID
      );
      setBoostSuccess(true);
      setBoostPostId('');
      setTimeout(() => setBoostSuccess(false), 3000);
    } catch {
      setError('Failed to boost post');
    } finally {
      setBoosting(false);
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Paid Social Advertising</h1>
          <p style={styles.subtitle}>
            Manage ad campaigns, boost organic posts, and track paid vs organic ROI across all networks
          </p>
        </div>
        <button
          onClick={() => {
            setShowNewForm(!showNewForm);
            setActiveTab('campaigns');
          }}
          style={styles.primaryBtn}
        >
          + New Campaign
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

      {/* Summary KPIs */}
      {summary && (
        <div style={styles.kpiRow}>
          {[
            { label: 'Total Campaigns', value: summary.total_campaigns, icon: '📢' },
            { label: 'Active', value: summary.active, icon: '▶️', accent: '#22c55e' },
            { label: 'Total Spend', value: `$${summary.total_spent.toLocaleString()}`, icon: '💰' },
            { label: 'Impressions', value: `${(summary.total_impressions / 1000).toFixed(0)}K`, icon: '👁' },
            { label: 'Conversions', value: summary.total_conversions, icon: '✅' },
            { label: 'Avg ROAS', value: `${summary.avg_roas}×`, icon: '📈', accent: '#22c55e' },
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
        {(['campaigns', 'analytics', 'boost'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{ ...styles.tab, ...(activeTab === tab ? styles.tabActive : {}) }}
          >
            {tab === 'campaigns' ? '📢 Campaigns' : tab === 'analytics' ? '📊 Analytics' : '⚡ Boost Post'}
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
          {/* Campaigns Tab */}
          {activeTab === 'campaigns' && (
            <div>
              {showNewForm && (
                <div style={styles.formCard}>
                  <h3 style={styles.formTitle}>New Ad Campaign</h3>
                  <div style={styles.formGrid}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Campaign Name</label>
                      <input
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="e.g. Summer Brand Push"
                        style={styles.input}
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Objective</label>
                      <select
                        value={newObjective}
                        onChange={(e) => setNewObjective(e.target.value)}
                        style={styles.input}
                      >
                        {[
                          'awareness',
                          'reach',
                          'traffic',
                          'engagement',
                          'lead_generation',
                          'conversions',
                          'app_installs',
                        ].map((o) => (
                          <option key={o} value={o}>
                            {o.replace(/_/g, ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Network</label>
                      <select value={newNetwork} onChange={(e) => setNewNetwork(e.target.value)} style={styles.input}>
                        {Object.keys(NETWORK_COLORS).map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Daily Budget ($)</label>
                      <input
                        type="number"
                        value={newBudgetDaily}
                        onChange={(e) => setNewBudgetDaily(e.target.value)}
                        style={styles.input}
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Total Budget ($)</label>
                      <input
                        type="number"
                        value={newBudgetTotal}
                        onChange={(e) => setNewBudgetTotal(e.target.value)}
                        style={styles.input}
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Start Date</label>
                      <input
                        type="date"
                        value={newStartDate}
                        onChange={(e) => setNewStartDate(e.target.value)}
                        style={styles.input}
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>End Date</label>
                      <input
                        type="date"
                        value={newEndDate}
                        onChange={(e) => setNewEndDate(e.target.value)}
                        style={styles.input}
                      />
                    </div>
                  </div>
                  <div style={styles.formActions}>
                    <button onClick={() => setShowNewForm(false)} style={styles.cancelBtn}>
                      Cancel
                    </button>
                    <button onClick={createCampaign} disabled={creating} style={styles.primaryBtn}>
                      {creating ? 'Creating…' : 'Launch Campaign'}
                    </button>
                  </div>
                </div>
              )}
              <div style={styles.campaignList}>
                {campaigns.map((campaign) => {
                  const ss = STATUS_STYLE[campaign.status] ?? STATUS_STYLE.archived;
                  return (
                    <div key={campaign.id} style={styles.campaignCard}>
                      <div style={styles.campaignHeader}>
                        <div style={styles.campaignLeft}>
                          <div style={{ ...styles.netTag, background: NETWORK_COLORS[campaign.network] ?? '#e7e9ef' }}>
                            {campaign.network}
                          </div>
                          <div>
                            <div style={styles.campaignName}>{campaign.name}</div>
                            <div style={styles.campaignObjective}>
                              {campaign.objective.replace(/_/g, ' ')} · {campaign.start_date} → {campaign.end_date}
                            </div>
                          </div>
                        </div>
                        <div style={styles.campaignRight}>
                          <span style={{ ...styles.statusBadge, background: ss.bg, color: ss.color }}>
                            {campaign.status.replace(/_/g, ' ')}
                          </span>
                          <button onClick={() => toggleStatus(campaign)} style={styles.toggleBtn}>
                            {campaign.status === 'active' ? 'Pause' : 'Resume'}
                          </button>
                        </div>
                      </div>
                      <div style={styles.campaignMetrics}>
                        {[
                          {
                            label: 'Spent',
                            value: `$${campaign.spent.toLocaleString()}`,
                            sub: `of $${campaign.budget_total.toLocaleString()}`,
                          },
                          { label: 'Impressions', value: `${(campaign.impressions / 1000).toFixed(0)}K` },
                          { label: 'Clicks', value: campaign.clicks.toLocaleString() },
                          { label: 'CTR', value: `${campaign.ctr}%` },
                          { label: 'CPC', value: `$${campaign.cpc}` },
                          { label: 'Conversions', value: campaign.conversions },
                          {
                            label: 'ROAS',
                            value: `${campaign.roas}×`,
                            accent: campaign.roas >= 3 ? '#22c55e' : '#F59E0B',
                          },
                        ].map((m, i) => (
                          <div key={i} style={styles.metricCell}>
                            <span style={{ ...styles.metricValue, color: (m as any).accent ?? 'var(--text)' }}>
                              {m.value}
                            </span>
                            <span style={styles.metricLabel}>{m.label}</span>
                            {(m as any).sub && <span style={styles.muted}>{(m as any).sub}</span>}
                          </div>
                        ))}
                      </div>
                      <div style={styles.budgetBar}>
                        <div
                          style={{
                            ...styles.budgetFill,
                            width: `${Math.min((campaign.spent / campaign.budget_total) * 100, 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <div style={styles.analyticsGrid}>
              <div style={styles.analyticsCard}>
                <h3 style={styles.sectionTitle}>Performance by Network</h3>
                {Object.entries(byNetwork).map(([net, data]) => (
                  <div key={net} style={styles.networkRow}>
                    <div style={{ ...styles.netTag, background: NETWORK_COLORS[net] ?? '#e7e9ef', marginRight: 10 }}>
                      {net}
                    </div>
                    <div style={styles.networkStats}>
                      <span style={styles.netStat}>{(data.impressions / 1000).toFixed(0)}K impressions</span>
                      <span style={styles.netStat}>{data.clicks.toLocaleString()} clicks</span>
                      <span style={styles.netStat}>{data.conversions} conversions</span>
                      <span style={styles.netStat}>${data.spent.toLocaleString()} spent</span>
                      <span style={{ ...styles.netStat, color: '#22c55e' }}>{data.avg_roas}× ROAS</span>
                    </div>
                  </div>
                ))}
              </div>
              <div style={styles.analyticsCard}>
                <h3 style={styles.sectionTitle}>Paid vs Organic Comparison</h3>
                <div style={styles.comparisonTable}>
                  {[
                    {
                      metric: 'Reach',
                      paid: `${((summary?.total_impressions ?? 0) / 1000).toFixed(0)}K`,
                      organic: '620K',
                    },
                    { metric: 'Engagement Rate', paid: '3.8%', organic: '5.7%' },
                    { metric: 'Conversions', paid: summary?.total_conversions ?? 0, organic: '2,340' },
                    {
                      metric: 'Cost per Conversion',
                      paid: `$${summary ? (summary.total_spent / Math.max(summary.total_conversions, 1)).toFixed(2) : '—'}`,
                      organic: '$0 (organic)',
                    },
                    { metric: 'ROAS', paid: `${summary?.avg_roas ?? '—'}×`, organic: 'N/A' },
                  ].map((row, i) => (
                    <div key={i} style={styles.comparisonRow}>
                      <span style={styles.comparisonMetric}>{row.metric}</span>
                      <span style={{ ...styles.comparisonVal, color: 'var(--brand)' }}>📢 {row.paid}</span>
                      <span style={{ ...styles.comparisonVal, color: '#22c55e' }}>🌱 {row.organic}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Boost Tab */}
          {activeTab === 'boost' && (
            <div style={styles.boostSection}>
              <div style={styles.boostCard}>
                <h3 style={styles.sectionTitle}>⚡ Boost Organic Post</h3>
                <p style={styles.boostDesc}>
                  Convert your best organic posts into paid ads with one click. Set budget and duration — we handle the
                  rest.
                </p>
                {boostSuccess && (
                  <div style={styles.successBanner}>✅ Post boosted successfully! Campaign is now active.</div>
                )}
                <div style={styles.boostForm}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Post ID or URL</label>
                    <input
                      value={boostPostId}
                      onChange={(e) => setBoostPostId(e.target.value)}
                      placeholder="e.g. post_123 or https://instagram.com/p/..."
                      style={styles.input}
                    />
                  </div>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Network</label>
                    <select value={boostNetwork} onChange={(e) => setBoostNetwork(e.target.value)} style={styles.input}>
                      {Object.keys(NETWORK_COLORS).map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Total Budget ($)</label>
                    <input
                      type="number"
                      value={boostBudget}
                      onChange={(e) => setBoostBudget(e.target.value)}
                      style={styles.input}
                    />
                  </div>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Duration (days)</label>
                    <input
                      type="number"
                      value={boostDays}
                      onChange={(e) => setBoostDays(e.target.value)}
                      min="1"
                      max="90"
                      style={styles.input}
                    />
                  </div>
                </div>
                <button
                  onClick={boostPost}
                  disabled={boosting || !boostPostId.trim()}
                  style={{ ...styles.primaryBtn, width: '100%', marginTop: 16, padding: '12px 0', fontSize: 15 }}
                >
                  {boosting ? 'Boosting…' : '⚡ Boost This Post'}
                </button>
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
  iconBtn: { background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 16, padding: 4 },
  successBanner: {
    background: '#dcfce733',
    border: '1px solid #22c55e',
    borderRadius: 8,
    padding: '10px 16px',
    marginBottom: 16,
    fontSize: 14,
    color: '#22c55e',
  },
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
  skeletonBar: { height: 100, background: 'var(--card)', borderRadius: 10 },
  formCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 20 },
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
  campaignList: { display: 'flex', flexDirection: 'column', gap: 12 },
  campaignCard: { background: 'var(--card)', borderRadius: 12, padding: '16px 20px', border: '1px solid var(--line)' },
  campaignHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  campaignLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  netTag: {
    padding: '4px 10px',
    borderRadius: 6,
    color: '#fff',
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'capitalize',
    whiteSpace: 'nowrap',
  },
  campaignName: { fontWeight: 600, fontSize: 15 },
  campaignObjective: { fontSize: 12, color: 'var(--muted)', marginTop: 2, textTransform: 'capitalize' },
  campaignRight: { display: 'flex', alignItems: 'center', gap: 10 },
  statusBadge: { padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600, textTransform: 'capitalize' },
  toggleBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--text)',
    padding: '5px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
  },
  campaignMetrics: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: 8, marginBottom: 10 },
  metricCell: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    background: 'var(--card)',
    borderRadius: 6,
    padding: '8px 4px',
  },
  metricValue: { fontSize: 16, fontWeight: 700 },
  metricLabel: { fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.3px' },
  muted: { color: 'var(--muted)', fontSize: 10 },
  budgetBar: { height: 4, background: 'var(--card)', borderRadius: 2, overflow: 'hidden' },
  budgetFill: { height: '100%', background: '#6366f1', borderRadius: 2, transition: 'width 0.4s ease' },
  analyticsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 },
  analyticsCard: { background: 'var(--card)', borderRadius: 12, padding: 24, border: '1px solid var(--line)' },
  sectionTitle: { fontSize: 16, fontWeight: 600, marginBottom: 16, color: 'var(--text)' },
  networkRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0', borderBottom: '1px solid var(--line)' },
  networkStats: { display: 'flex', gap: 16, flex: 1, flexWrap: 'wrap' },
  netStat: { fontSize: 13, color: 'var(--text)' },
  comparisonTable: { display: 'flex', flexDirection: 'column', gap: 0 },
  comparisonRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
    gap: 10,
    padding: '10px 0',
    borderBottom: '1px solid var(--line)',
    alignItems: 'center',
  },
  comparisonMetric: { fontSize: 13, color: 'var(--muted)' },
  comparisonVal: { fontSize: 14, fontWeight: 600 },
  boostSection: { maxWidth: 560 },
  boostCard: { background: 'var(--card)', borderRadius: 12, padding: 28, border: '1px solid var(--line)' },
  boostDesc: { color: 'var(--muted)', fontSize: 14, lineHeight: 1.6, marginBottom: 20 },
  boostForm: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 },
};
