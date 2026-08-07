'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type StreamFeedItem = {
  id: string;
  author: string;
  network: string;
  text: string;
  engagement: number;
  sentiment: 'positive' | 'negative' | 'neutral';
  posted_at: string;
};

type MonitoringStream = {
  id: number;
  name: string;
  stream_type: string;
  query: string;
  networks: string[];
  column_index: number;
  feed: StreamFeedItem[];
  created_at: string;
};

function getStreamTypeColor(streamType: string): string {
  if (streamType === 'hashtag') {
    return '#ec4899';
  }
  if (streamType === 'account') {
    return '#6366f1';
  }
  return '#22c55e';
}

function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function normalizeStream(raw: Record<string, unknown>): MonitoringStream {
  const rawFeed = Array.isArray(raw.feed) ? raw.feed : [];
  return {
    id: Number(raw.id ?? 0),
    name: asString(raw.name),
    stream_type: asString(raw.stream_type, 'keyword'),
    query: asString(raw.query),
    networks: Array.isArray(raw.networks) ? raw.networks.map((item) => asString(item)).filter(Boolean) : [],
    column_index: Number(raw.column_index ?? 0),
    created_at: asString(raw.created_at, new Date().toISOString()),
    feed: rawFeed.map((item, index) => {
      const row = (item ?? {}) as Record<string, unknown>;
      const sentiment = asString(row.sentiment, 'neutral');
      return {
        id: asString(row.id, `feed-${index + 1}`),
        author: asString(row.author, 'Unknown'),
        network: asString(row.network, 'x'),
        text: asString(row.text),
        engagement: Number(row.engagement ?? 0),
        sentiment: sentiment === 'positive' || sentiment === 'negative' ? sentiment : 'neutral',
        posted_at: asString(row.posted_at, new Date().toISOString()),
      };
    }),
  };
}

const NETWORK_COLORS: Record<string, string> = {
  instagram: '#E1306C',
  x: '#1DA1F2',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  tiktok: '#69C9D0',
  reddit: '#FF4500',
  youtube: '#FF0000',
};

const SENTIMENT_COLOR: Record<string, string> = { positive: '#22c55e', negative: '#EF4444', neutral: 'var(--muted)' };

export default function MonitoringStreamsPage() {
  const [streams, setStreams] = useState<MonitoringStream[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newQuery, setNewQuery] = useState('');
  const [newType, setNewType] = useState('keyword');
  const [newNetworks, setNewNetworks] = useState(['instagram', 'x', 'facebook']);
  const [creating, setCreating] = useState(false);
  const [movingId, setMovingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStreams();
  }, []);

  async function loadStreams() {
    setLoading(true);
    setError(null);
    try {
      const items = await socialApi.listMonitoringStreams();
      setStreams(items.map((item) => normalizeStream(item as unknown as Record<string, unknown>)));
    } catch {
      setStreams([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Monitoring streams backend unavailable in strict no-mock mode.'
          : 'Monitoring streams backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function moveStream(streamId: number, direction: 'left' | 'right') {
    const sortedStreams = [...streams].sort((a, b) => (a.column_index ?? 0) - (b.column_index ?? 0));
    const currentIndex = sortedStreams.findIndex((stream) => stream.id === streamId);
    if (currentIndex < 0) {
      return;
    }
    const targetIndex = direction === 'left' ? currentIndex - 1 : currentIndex + 1;
    if (targetIndex < 0 || targetIndex >= sortedStreams.length) {
      return;
    }

    const current = sortedStreams[currentIndex];
    const target = sortedStreams[targetIndex];
    setMovingId(streamId);
    try {
      await Promise.all([
        socialApi.updateMonitoringStream(current.id, { column_index: target.column_index }),
        socialApi.updateMonitoringStream(target.id, { column_index: current.column_index }),
      ]);
      await loadStreams();
    } catch {
      setError('Failed to reorder streams');
    } finally {
      setMovingId(null);
    }
  }

  async function createStream() {
    if (!newName.trim() || !newQuery.trim()) return;
    setCreating(true);
    try {
      const stream = await socialApi.createMonitoringStream({
        name: newName.trim(),
        stream_type: newType,
        query: newQuery.trim(),
        networks: newNetworks,
        column_index: streams.length,
      });
      setStreams((prev) => [...prev, normalizeStream(stream as unknown as Record<string, unknown>)]);
      setNewName('');
      setNewQuery('');
      setShowNewForm(false);
    } catch {
      setError('Failed to create stream');
    } finally {
      setCreating(false);
    }
  }

  async function deleteStream(id: number) {
    setDeletingId(id);
    try {
      await socialApi.deleteMonitoringStream(id);
      setStreams((prev) => prev.filter((s) => s.id !== id));
    } catch {
      setError('Failed to delete stream');
    } finally {
      setDeletingId(null);
    }
  }

  const toggleNetwork = (net: string) =>
    setNewNetworks((prev) => (prev.includes(net) ? prev.filter((n) => n !== net) : [...prev, net]));
  const allNetworks = ['instagram', 'x', 'facebook', 'linkedin', 'tiktok', 'reddit', 'youtube'];

  const sorted = [...streams].sort((a, b) => (a.column_index ?? 0) - (b.column_index ?? 0));

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Monitoring Streams</h1>
          <p style={styles.subtitle}>
            Real-time multi-column feed view · Monitor keywords, hashtags, mentions, and competitors simultaneously
          </p>
        </div>
        <button onClick={() => setShowNewForm(!showNewForm)} style={styles.primaryBtn}>
          + Add Stream
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

      {/* New Stream Form */}
      {showNewForm && (
        <div style={styles.newStreamForm}>
          <h3 style={styles.formTitle}>New Monitoring Stream</h3>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label htmlFor="stream-name" style={styles.label}>
                Stream Name
              </label>
              <input
                id="stream-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Brand Mentions"
                style={styles.input}
              />
            </div>
            <div style={styles.formGroup}>
              <label htmlFor="stream-type" style={styles.label}>
                Type
              </label>
              <select
                id="stream-type"
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                style={styles.input}
              >
                <option value="keyword">Keyword / Phrase</option>
                <option value="hashtag">Hashtag</option>
                <option value="account">Account Mentions</option>
                <option value="list">Social List</option>
              </select>
            </div>
            <div style={{ ...styles.formGroup, gridColumn: '1 / -1' }}>
              <label htmlFor="stream-query" style={styles.label}>
                Query
              </label>
              <input
                id="stream-query"
                value={newQuery}
                onChange={(e) => setNewQuery(e.target.value)}
                placeholder="e.g. @YourBrand OR #YourHashtag"
                style={styles.input}
              />
            </div>
            <div style={{ ...styles.formGroup, gridColumn: '1 / -1' }}>
              <span style={styles.label}>Networks</span>
              <div style={styles.networkPicker}>
                {allNetworks.map((net) => (
                  <button
                    key={net}
                    onClick={() => toggleNetwork(net)}
                    style={{
                      ...styles.netBtn,
                      ...(newNetworks.includes(net)
                        ? { background: NETWORK_COLORS[net], color: '#fff', border: `1px solid ${NETWORK_COLORS[net]}` }
                        : {}),
                    }}
                  >
                    {net}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div style={styles.formActions}>
            <button onClick={() => setShowNewForm(false)} style={styles.cancelBtn}>
              Cancel
            </button>
            <button
              onClick={createStream}
              disabled={creating || !newName.trim() || !newQuery.trim()}
              style={styles.primaryBtn}
            >
              {creating ? 'Creating…' : 'Create Stream'}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={styles.streamsGrid}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={{ ...styles.streamColumn, opacity: 0.4 }}>
              <div style={styles.columnHeader} />
              {[1, 2, 3].map((j) => (
                <div key={j} style={styles.skeletonCard} />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            ...styles.streamsGrid,
            gridTemplateColumns: `repeat(${Math.max(sorted.length, 1)}, minmax(min(100%, 280px), 1fr))`,
          }}
        >
          {sorted.map((stream, index) => (
            <div key={stream.id} style={styles.streamColumn}>
              <div style={styles.columnHeader}>
                <div style={styles.columnHeaderLeft}>
                  <div
                    style={{
                      ...styles.streamTypeDot,
                      background: getStreamTypeColor(stream.stream_type),
                    }}
                  />
                  <span style={styles.columnName}>{stream.name}</span>
                </div>
                <div style={styles.columnActions}>
                  <button
                    onClick={() => moveStream(stream.id, 'left')}
                    disabled={index === 0 || movingId === stream.id}
                    style={styles.iconBtn}
                    title="Move left"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => moveStream(stream.id, 'right')}
                    disabled={index === sorted.length - 1 || movingId === stream.id}
                    style={styles.iconBtn}
                    title="Move right"
                  >
                    →
                  </button>
                  <button
                    onClick={() => deleteStream(stream.id)}
                    disabled={deletingId === stream.id}
                    style={styles.iconBtn}
                    title="Delete stream"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div style={styles.queryTag}>{stream.query}</div>
              <div style={styles.networkRow}>
                {stream.networks.map((net) => (
                  <span
                    key={net}
                    style={{ ...styles.netDot, background: NETWORK_COLORS[net] ?? '#e7e9ef' }}
                    title={net}
                  />
                ))}
              </div>
              <div style={styles.feedList}>
                {stream.feed.map((item) => (
                  <div
                    key={item.id}
                    style={{ ...styles.feedCard, borderLeft: `3px solid ${SENTIMENT_COLOR[item.sentiment]}` }}
                  >
                    <div style={styles.feedMeta}>
                      <span style={{ ...styles.networkBadge, background: NETWORK_COLORS[item.network] ?? '#e7e9ef' }}>
                        {item.network}
                      </span>
                      <span style={styles.feedAuthor}>{item.author}</span>
                    </div>
                    <p style={styles.feedText}>{item.text}</p>
                    <div style={styles.feedFooter}>
                      <span style={styles.muted}>💬 {item.engagement}</span>
                      <span style={{ color: SENTIMENT_COLOR[item.sentiment], fontSize: 11 }}>{item.sentiment}</span>
                    </div>
                  </div>
                ))}
                {stream.feed.length === 0 && <div style={styles.emptyFeed}>No posts yet. Stream is monitoring...</div>}
              </div>
            </div>
          ))}
          {sorted.length === 0 && (
            <div style={styles.emptyState}>
              <p style={styles.emptyText}>No streams yet. Add your first monitoring stream.</p>
            </div>
          )}
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
  iconBtn: { background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 16, padding: 4 },
  newStreamForm: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 24,
    marginBottom: 24,
  },
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
  networkPicker: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  netBtn: {
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
  streamsGrid: { display: 'grid', gap: 16, overflowX: 'auto' },
  streamColumn: {
    background: 'var(--card)',
    borderRadius: 12,
    border: '1px solid var(--line)',
    overflow: 'hidden',
    minWidth: 280,
  },
  columnHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 14px',
    borderBottom: '1px solid var(--line)',
  },
  columnHeaderLeft: { display: 'flex', alignItems: 'center', gap: 8 },
  columnActions: { display: 'flex', alignItems: 'center', gap: 6 },
  streamTypeDot: { width: 8, height: 8, borderRadius: '50%' },
  columnName: { fontWeight: 600, fontSize: 14 },
  queryTag: { padding: '6px 14px', fontSize: 12, color: 'var(--brand)', fontFamily: 'monospace', background: '#0D111799' },
  networkRow: { display: 'flex', gap: 6, padding: '6px 14px', borderBottom: '1px solid var(--line)' },
  netDot: { width: 8, height: 8, borderRadius: '50%' },
  feedList: { display: 'flex', flexDirection: 'column', gap: 8, padding: 10, maxHeight: 420, overflowY: 'auto' },
  feedCard: { background: 'var(--card)', borderRadius: 8, padding: '10px 12px' },
  feedMeta: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 },
  networkBadge: {
    padding: '1px 6px',
    borderRadius: 3,
    fontSize: 10,
    fontWeight: 600,
    color: '#fff',
    textTransform: 'capitalize',
  },
  feedAuthor: { fontSize: 12, fontWeight: 600, color: 'var(--text)' },
  feedText: { fontSize: 13, color: 'var(--muted)', lineHeight: 1.5, margin: '0 0 6px' },
  feedFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  muted: { fontSize: 11, color: 'var(--muted)' },
  emptyFeed: { color: 'var(--muted)', textAlign: 'center', padding: '20px 0', fontSize: 13 },
  emptyState: { gridColumn: '1 / -1', textAlign: 'center', padding: '80px 0' },
  emptyText: { color: 'var(--muted)', fontSize: 15 },
  skeletonCard: { height: 80, background: 'var(--card)', borderRadius: 8, marginBottom: 8 },
};
