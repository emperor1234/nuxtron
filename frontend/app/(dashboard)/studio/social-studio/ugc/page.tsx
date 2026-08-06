'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type UgcAsset = {
  id: number;
  creator_handle: string;
  creator_network: string;
  content_type: string;
  content_url: string;
  thumbnail_url: string;
  caption: string;
  hashtags: string[];
  mentions: string[];
  likes: number;
  comments: number;
  shares: number;
  reach: number;
  sentiment: string;
  rights_status: string;
  rights_requested_at: string | null;
  approved_at: string | null;
  created_at: string;
};

type UgcSummary = {
  total: number;
  pending_rights: number;
  approved: number;
  declined: number;
};

const NETWORK_COLORS: Record<string, string> = {
  instagram: '#E1306C',
  x: '#1DA1F2',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  tiktok: '#69C9D0',
  youtube: '#FF0000',
};

const RIGHTS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  pending: { bg: '#fef3c722', color: '#F59E0B', label: 'Pending Rights' },
  approved: { bg: '#dcfce722', color: '#22c55e', label: 'Rights Approved' },
  declined: { bg: '#fee2e222', color: '#EF4444', label: 'Declined' },
  not_requested: { bg: '#eef0f4', color: 'var(--muted)', label: 'Not Requested' },
};

const SENTIMENT_COLOR: Record<string, string> = { positive: '#22c55e', neutral: 'var(--muted)', negative: '#EF4444' };

export default function UgcManagementPage() {
  const [assets, setAssets] = useState<UgcAsset[]>([]);
  const [summary, setSummary] = useState<UgcSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [filterRights, setFilterRights] = useState<string>('all');
  const [filterSentiment, setFilterSentiment] = useState<string>('all');
  const [filterNetwork, setFilterNetwork] = useState<string>('all');
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [requestingRightsId, setRequestingRightsId] = useState<number | null>(null);
  const [republishingId, setRepublishingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<UgcAsset | null>(null);
  const [republishTime, setRepublishTime] = useState('');

  useEffect(() => {
    loadAssets();
  }, []);

  async function loadAssets() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet('/social/ugc', DEFAULT_TENANT_ID);
      const normalized = (((data as any)?.assets ?? []) as Array<Record<string, unknown>>).map(normalizeAsset);
      setAssets(normalized);
      setSummary(normalizeSummary((data as any)?.summary, normalized));
    } catch {
      setAssets([]);
      setSummary(null);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'UGC backend unavailable in strict no-mock mode.'
          : 'UGC backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function discoverAssets() {
    setDiscovering(true);
    setError(null);
    try {
      await apiSend(
        '/social/ugc/discover',
        'POST',
        { brand_domain: `${DEFAULT_TENANT_ID}.example.com`, limit: 20 },
        DEFAULT_TENANT_ID
      );
      await loadAssets();
      setSuccessMsg('UGC discovery completed.');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {
      setError('Failed to discover UGC assets');
    } finally {
      setDiscovering(false);
    }
  }

  async function requestRights(asset: UgcAsset) {
    setRequestingRightsId(asset.id);
    setError(null);
    try {
      await apiSend(
        `/social/ugc/${asset.id}/request-rights`,
        'POST',
        { message: `Hi ${asset.creator_handle}, we would love to republish your content and credit you.` },
        DEFAULT_TENANT_ID
      );
      setAssets((prev) =>
        prev.map((a) =>
          a.id === asset.id ? { ...a, rights_status: 'pending', rights_requested_at: new Date().toISOString() } : a
        )
      );
      setSummary((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          pending_rights: prev.pending_rights + 1,
        };
      });
      setSuccessMsg(`Rights request sent to ${asset.creator_handle}`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {
      setError('Failed to request creator rights');
    } finally {
      setRequestingRightsId(null);
    }
  }

  async function approveRights(asset: UgcAsset, approve: boolean) {
    setApprovingId(asset.id);
    try {
      await apiSend(
        `/social/ugc/${asset.id}/approve`,
        'PATCH',
        { approved: approve, note: approve ? 'Approved for republishing' : 'Declined' },
        DEFAULT_TENANT_ID
      );
      const newStatus = approve ? 'approved' : 'declined';
      setAssets((prev) =>
        prev.map((a) =>
          a.id === asset.id
            ? { ...a, rights_status: newStatus, approved_at: approve ? new Date().toISOString() : null }
            : a
        )
      );
      setSummary((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          pending_rights: prev.pending_rights - 1,
          approved: approve ? prev.approved + 1 : prev.approved,
          declined: approve ? prev.declined : prev.declined + 1,
        };
      });
      setSuccessMsg(`Rights ${approve ? 'approved' : 'declined'} for ${asset.creator_handle}`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {
      setError('Failed to update rights status');
    } finally {
      setApprovingId(null);
    }
  }

  async function republishAsset(asset: UgcAsset) {
    if (!republishTime) {
      setError('Please set a scheduled time');
      return;
    }
    setRepublishingId(asset.id);
    try {
      await apiSend(
        `/social/ugc/${asset.id}/republish`,
        'POST',
        {
          scheduled_time: republishTime,
          target_networks: [asset.creator_network],
          add_credit: true,
        },
        DEFAULT_TENANT_ID
      );
      setSuccessMsg(`${asset.creator_handle}'s content scheduled for republishing!`);
      setSelectedAsset(null);
      setRepublishTime('');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch {
      setError('Failed to schedule republish');
    } finally {
      setRepublishingId(null);
    }
  }

  const filtered = assets.filter((a) => {
    if (filterRights !== 'all' && a.rights_status !== filterRights) return false;
    if (filterSentiment !== 'all' && a.sentiment !== filterSentiment) return false;
    if (filterNetwork !== 'all' && a.creator_network !== filterNetwork) return false;
    return true;
  });

  const networks = [...new Set(assets.map((a) => a.creator_network))];
  const assetCountLabel = filtered.length === 1 ? 'asset' : 'assets';

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>UGC Management</h1>
          <p style={styles.subtitle}>
            Discover, approve, and republish user-generated content · Manage rights requests · Track performance of
            curated UGC
          </p>
        </div>
        <button
          type="button"
          onClick={() => void discoverAssets()}
          disabled={discovering || loading}
          style={styles.discoverBtn}
        >
          {discovering ? 'Discovering…' : 'Discover UGC'}
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

      {/* Summary Bar */}
      {summary && (
        <div style={styles.summaryBar}>
          {[
            { label: 'Total UGC', value: summary.total, icon: '🎨' },
            { label: 'Pending Rights', value: summary.pending_rights, icon: '⏳', accent: '#F59E0B' },
            { label: 'Approved', value: summary.approved, icon: '✅', accent: '#22c55e' },
            { label: 'Declined', value: summary.declined, icon: '❌', accent: '#EF4444' },
          ].map((item) => (
            <div key={item.label} style={styles.summaryCard}>
              <span style={styles.summaryIcon}>{item.icon}</span>
              <span style={{ ...styles.summaryValue, color: item.accent ?? 'var(--text)' }}>{item.value}</span>
              <span style={styles.summaryLabel}>{item.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div style={styles.filterRow}>
        <div style={styles.filterGroup}>
          <label htmlFor="ugc-rights-filter" style={styles.filterLabel}>
            Rights Status
          </label>
          <select
            id="ugc-rights-filter"
            value={filterRights}
            onChange={(e) => setFilterRights(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="declined">Declined</option>
            <option value="not_requested">Not Requested</option>
          </select>
        </div>
        <div style={styles.filterGroup}>
          <label htmlFor="ugc-sentiment-filter" style={styles.filterLabel}>
            Sentiment
          </label>
          <select
            id="ugc-sentiment-filter"
            value={filterSentiment}
            onChange={(e) => setFilterSentiment(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="all">All</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
        </div>
        <div style={styles.filterGroup}>
          <label htmlFor="ugc-network-filter" style={styles.filterLabel}>
            Network
          </label>
          <select
            id="ugc-network-filter"
            value={filterNetwork}
            onChange={(e) => setFilterNetwork(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="all">All</option>
            {networks.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <span style={styles.resultCount}>
          {filtered.length} {assetCountLabel}
        </span>
      </div>

      {/* Asset Grid */}
      {loading ? (
        <div style={styles.assetGrid}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={styles.skeletonCard} />
          ))}
        </div>
      ) : (
        <div style={styles.assetGrid}>
          {filtered.map((asset) => {
            const rs = RIGHTS_STYLE[asset.rights_status] ?? RIGHTS_STYLE.not_requested;
            return (
              <div key={asset.id} style={styles.assetCard}>
                {/* Thumbnail */}
                <div style={styles.thumbnailWrap}>
                  <img
                    src={asset.thumbnail_url}
                    alt={asset.caption}
                    style={styles.thumbnail}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <div
                    style={{
                      ...styles.contentTypeBadge,
                      background: asset.content_type === 'video' ? '#6366f1' : '#eef0f4',
                    }}
                  >
                    {asset.content_type === 'video' ? '▶ Video' : '🖼 Image'}
                  </div>
                  <div
                    style={{
                      ...styles.networkBadgeOverlay,
                      background: NETWORK_COLORS[asset.creator_network] ?? '#e7e9ef',
                    }}
                  >
                    {asset.creator_network}
                  </div>
                </div>

                {/* Content */}
                <div style={styles.assetContent}>
                  <div style={styles.creatorRow}>
                    <span style={styles.creatorHandle}>{asset.creator_handle}</span>
                    <span
                      style={{ ...styles.sentimentDot, background: SENTIMENT_COLOR[asset.sentiment] }}
                      title={asset.sentiment}
                    />
                  </div>
                  <p style={styles.caption}>
                    {asset.caption.length > 100 ? asset.caption.slice(0, 100) + '…' : asset.caption}
                  </p>

                  {/* Engagement */}
                  <div style={styles.engagementRow}>
                    <span style={styles.engageStat}>❤ {asset.likes.toLocaleString()}</span>
                    <span style={styles.engageStat}>💬 {asset.comments.toLocaleString()}</span>
                    <span style={styles.engageStat}>🔁 {asset.shares.toLocaleString()}</span>
                    <span style={styles.engageStat}>👁 {(asset.reach / 1000).toFixed(0)}K</span>
                  </div>

                  {/* Rights Status */}
                  <div style={{ ...styles.rightsBadge, background: rs.bg, color: rs.color }}>{rs.label}</div>

                  {/* Hashtags */}
                  {asset.hashtags.length > 0 && (
                    <div style={styles.hashtagRow}>
                      {asset.hashtags.slice(0, 3).map((h) => (
                        <span key={h} style={styles.hashtag}>
                          {h}
                        </span>
                      ))}
                      {asset.hashtags.length > 3 && <span style={styles.hashtag}>+{asset.hashtags.length - 3}</span>}
                    </div>
                  )}

                  {/* Actions */}
                  <div style={styles.actionRow}>
                    {asset.rights_status === 'pending' && (
                      <>
                        <button
                          onClick={() => approveRights(asset, true)}
                          disabled={approvingId === asset.id}
                          style={styles.approveBtn}
                        >
                          ✓ Approve
                        </button>
                        <button
                          onClick={() => approveRights(asset, false)}
                          disabled={approvingId === asset.id}
                          style={styles.declineBtn}
                        >
                          ✕ Decline
                        </button>
                      </>
                    )}
                    {asset.rights_status === 'not_requested' && (
                      <button
                        onClick={() => requestRights(asset)}
                        disabled={requestingRightsId === asset.id}
                        style={styles.requestBtn}
                      >
                        {requestingRightsId === asset.id ? 'Requesting…' : 'Request Rights'}
                      </button>
                    )}
                    {asset.rights_status === 'approved' && (
                      <button
                        onClick={() => {
                          setSelectedAsset(asset);
                          setRepublishTime('');
                        }}
                        style={styles.republishBtn}
                      >
                        🔁 Republish
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div style={styles.emptyState}>
              <p style={styles.emptyText}>No UGC assets match the current filters.</p>
            </div>
          )}
        </div>
      )}

      {/* Republish Modal */}
      {selectedAsset && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <h3 style={styles.modalTitle}>Republish UGC</h3>
            <p style={styles.modalDesc}>
              Republishing <strong>{selectedAsset.creator_handle}</strong>'s content. Creator will be credited
              automatically.
            </p>
            <div style={styles.formGroup}>
              <label htmlFor="ugc-republish-time" style={styles.label}>
                Scheduled Time
              </label>
              <input
                id="ugc-republish-time"
                type="datetime-local"
                value={republishTime}
                onChange={(e) => setRepublishTime(e.target.value)}
                style={styles.input}
              />
            </div>
            <div style={styles.modalActions}>
              <button onClick={() => setSelectedAsset(null)} style={styles.cancelBtn}>
                Cancel
              </button>
              <button
                onClick={() => republishAsset(selectedAsset)}
                disabled={republishingId === selectedAsset.id || !republishTime}
                style={styles.primaryBtn}
              >
                {republishingId === selectedAsset.id ? 'Scheduling…' : '🔁 Schedule Republish'}
              </button>
            </div>
          </div>
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
  discoverBtn: {
    alignSelf: 'center',
    background: '#6366f1',
    border: 'none',
    color: '#FFFFFF',
    borderRadius: 8,
    padding: '10px 14px',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
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
  summaryBar: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
    gap: 12,
    marginBottom: 24,
  },
  summaryCard: {
    background: 'var(--card)',
    borderRadius: 10,
    padding: '14px 16px',
    border: '1px solid var(--line)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    textAlign: 'center',
  },
  summaryIcon: { fontSize: 24 },
  summaryValue: { fontSize: 28, fontWeight: 700 },
  summaryLabel: { fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  filterRow: { display: 'flex', gap: 16, alignItems: 'flex-end', marginBottom: 20, flexWrap: 'wrap' },
  filterGroup: { display: 'flex', flexDirection: 'column', gap: 6 },
  filterLabel: { fontSize: 11, color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' },
  filterSelect: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '7px 12px',
    color: 'var(--text)',
    fontSize: 14,
  },
  resultCount: { fontSize: 13, color: 'var(--muted)', alignSelf: 'center', marginLeft: 'auto' },
  assetGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 16 },
  assetCard: { background: 'var(--card)', borderRadius: 12, border: '1px solid var(--line)', overflow: 'hidden' },
  thumbnailWrap: { position: 'relative', height: 200, background: 'var(--card)', overflow: 'hidden' },
  thumbnail: { width: '100%', height: '100%', objectFit: 'cover' },
  contentTypeBadge: {
    position: 'absolute',
    top: 8,
    left: 8,
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: 10,
    fontWeight: 600,
    color: '#fff',
  },
  networkBadgeOverlay: {
    position: 'absolute',
    top: 8,
    right: 8,
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: 10,
    fontWeight: 600,
    color: '#fff',
    textTransform: 'capitalize',
  },
  assetContent: { padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 },
  creatorRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  creatorHandle: { fontWeight: 600, fontSize: 14 },
  sentimentDot: { width: 8, height: 8, borderRadius: '50%' },
  caption: { fontSize: 13, color: 'var(--muted)', lineHeight: 1.5, margin: 0 },
  engagementRow: { display: 'flex', gap: 10, flexWrap: 'wrap' },
  engageStat: { fontSize: 12, color: 'var(--muted)' },
  rightsBadge: { padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, width: 'fit-content' },
  hashtagRow: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  hashtag: { background: 'var(--card)', color: 'var(--brand)', padding: '2px 8px', borderRadius: 4, fontSize: 11 },
  actionRow: { display: 'flex', gap: 8, marginTop: 4 },
  approveBtn: {
    flex: 1,
    background: '#dcfce722',
    border: '1px solid #22c55e',
    color: '#22c55e',
    padding: '6px 0',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  },
  declineBtn: {
    flex: 1,
    background: '#fee2e222',
    border: '1px solid #EF4444',
    color: '#EF4444',
    padding: '6px 0',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  },
  requestBtn: {
    flex: 1,
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--text)',
    padding: '6px 0',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
  },
  republishBtn: {
    flex: 1,
    background: 'var(--card)',
    border: '1px solid #6366f1',
    color: 'var(--brand)',
    padding: '6px 0',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  },
  skeletonCard: { height: 340, background: 'var(--card)', borderRadius: 12 },
  emptyState: { gridColumn: '1 / -1', textAlign: 'center', padding: '80px 0' },
  emptyText: { color: 'var(--muted)', fontSize: 15 },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: 32,
    maxWidth: 480,
    width: '90%',
  },
  modalTitle: { fontSize: 20, fontWeight: 700, marginBottom: 10 },
  modalDesc: { color: 'var(--muted)', fontSize: 14, lineHeight: 1.6, marginBottom: 20 },
  modalActions: { display: 'flex', gap: 10, marginTop: 20, justifyContent: 'flex-end' },
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
  cancelBtn: {
    background: 'transparent',
    border: '1px solid var(--line)',
    color: 'var(--muted)',
    padding: '9px 18px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 14,
  },
  primaryBtn: {
    background: '#6366f1',
    border: 'none',
    color: '#fff',
    padding: '9px 24px',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
  },
};

function normalizeAsset(raw: Record<string, unknown>): UgcAsset {
  const likes = Number(raw.likes ?? raw.engagement ?? 0);
  let hashtags: string[] = [];
  if (Array.isArray(raw.hashtags)) {
    hashtags = raw.hashtags.map((value) => toSafeString(value, ''));
  } else if (Array.isArray(raw.tags)) {
    hashtags = raw.tags.map((value) => toSafeString(value, ''));
  }

  return {
    id: Number(raw.id ?? 0),
    creator_handle: toSafeString(raw.creator_handle ?? raw.author, '@unknown'),
    creator_network: toSafeString(raw.creator_network ?? raw.network, 'instagram'),
    content_type: toSafeString(raw.content_type ?? raw.media_type, 'image'),
    content_url: toSafeString(raw.content_url ?? raw.media_url, ''),
    thumbnail_url: toSafeString(raw.thumbnail_url ?? raw.media_url, ''),
    caption: toSafeString(raw.caption, ''),
    hashtags,
    mentions: Array.isArray(raw.mentions) ? raw.mentions.map((value) => toSafeString(value, '')) : [],
    likes,
    comments: Number(raw.comments ?? 0),
    shares: Number(raw.shares ?? 0),
    reach: Number(raw.reach ?? 0),
    sentiment: toSafeString(raw.sentiment, 'neutral'),
    rights_status: toSafeString(raw.rights_status, 'not_requested'),
    rights_requested_at: (raw.rights_requested_at ?? raw.rights_request_sent_at ?? null) as string | null,
    approved_at: (raw.approved_at ?? null) as string | null,
    created_at: toSafeString(raw.created_at, new Date().toISOString()),
  };
}

function toSafeString(value: unknown, fallback: string): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
}

function normalizeSummary(rawSummary: unknown, normalizedAssets: UgcAsset[]): UgcSummary {
  if (rawSummary && typeof rawSummary === 'object') {
    const src = rawSummary as Record<string, unknown>;
    return {
      total: Number(src.total ?? normalizedAssets.length),
      pending_rights: Number(
        src.pending_rights ?? normalizedAssets.filter((a) => a.rights_status === 'pending').length
      ),
      approved: Number(src.approved ?? normalizedAssets.filter((a) => a.rights_status === 'approved').length),
      declined: Number(src.declined ?? normalizedAssets.filter((a) => a.rights_status === 'declined').length),
    };
  }
  return {
    total: normalizedAssets.length,
    pending_rights: normalizedAssets.filter((a) => a.rights_status === 'pending').length,
    approved: normalizedAssets.filter((a) => a.rights_status === 'approved').length,
    declined: normalizedAssets.filter((a) => a.rights_status === 'declined').length,
  };
}
