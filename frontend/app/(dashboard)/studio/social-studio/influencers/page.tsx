'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type InfluencerProfile = {
  id: string;
  name: string;
  handle: string;
  platform: string;
  followers: number;
  engagement_rate: number;
  category: string;
  fit_score: number;
  shortlisted?: boolean;
};

export default function SocialInfluencersPage() {
  const [items, setItems] = useState<InfluencerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('saas');
  const [platform, setPlatform] = useState('instagram');
  const [minFollowers, setMinFollowers] = useState('10000');
  const [campaign, setCampaign] = useState('Q3 Partner Amplification');
  const [title, setTitle] = useState('Influencer collaboration brief');
  const [messageAngle, setMessageAngle] = useState('Partnership opportunity');

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const response = await apiGet<{ items?: InfluencerProfile[] }>('/social/influencers', DEFAULT_TENANT_ID);
      setItems(response.items || []);
    } catch (err) {
      console.error('Failed to load influencers:', err);
      setItems([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Failed to load influencer CRM in strict no-mock mode.'
          : 'Failed to load influencer CRM in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch() {
    const min = Number.parseInt(minFollowers, 10);
    const response = await apiSend<{ items?: InfluencerProfile[] }>(
      '/social/influencers/search',
      'POST',
      {
        query,
        platform,
        min_followers: Number.isFinite(min) ? min : 0,
      },
      DEFAULT_TENANT_ID
    ).catch(() => null);
    if (response?.items) {
      setItems(response.items);
      return;
    }
    setError(
      IS_STRICT_NO_MOCK_MODE
        ? 'Influencer search backend unavailable in strict no-mock mode.'
        : 'Influencer search backend unavailable in fail-closed mode.'
    );
  }

  async function handleShortlist(id: string) {
    const response = await apiSend(
      '/social/influencers/shortlist',
      'POST',
      { influencer_id: id },
      DEFAULT_TENANT_ID
    ).catch(() => null);
    if (!response) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Unable to shortlist influencer in strict no-mock mode.'
          : 'Unable to shortlist influencer in fail-closed mode.'
      );
      return;
    }
    setItems((current) => current.map((item) => (item.id === id ? { ...item, shortlisted: true } : item)));
  }

  async function handleBridgeToAdvocacy(id: string) {
    const response = await apiSend<{ asset?: Record<string, unknown> }>(
      `/social/influencers/${id}/advocacy-asset`,
      'POST',
      {
        campaign,
        title,
        message_angle: messageAngle,
        network: platform,
      },
      DEFAULT_TENANT_ID
    ).catch(() => null);

    if (!response?.asset) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Unable to bridge influencer into advocacy in strict no-mock mode.'
          : 'Unable to bridge influencer into advocacy in fail-closed mode.'
      );
      return;
    }

    setItems((current) => current.map((item) => (item.id === id ? { ...item, shortlisted: true } : item)));
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Influencer CRM</h1>
          <p style={styles.subtitle}>Discover, score, and shortlist creators with operator-grade campaign readiness.</p>
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Discovery Filters</h2>
        <div style={styles.filterGrid}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={styles.input}
            placeholder="AI automation, b2b, creator economy"
          />
          <select value={platform} onChange={(e) => setPlatform(e.target.value)} style={styles.input}>
            <option value="instagram">Instagram</option>
            <option value="linkedin">LinkedIn</option>
            <option value="youtube">YouTube</option>
            <option value="x">X</option>
            <option value="tiktok">TikTok</option>
          </select>
          <input
            value={minFollowers}
            onChange={(e) => setMinFollowers(e.target.value)}
            style={styles.input}
            type="number"
            min={0}
          />
          <button onClick={() => void handleSearch()} style={styles.primaryBtn}>
            Search
          </button>
        </div>
        <div style={{ ...styles.filterGrid, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))' }}>
          <input
            value={campaign}
            onChange={(e) => setCampaign(e.target.value)}
            style={styles.input}
            placeholder="Campaign name"
          />
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={styles.input}
            placeholder="Brief title"
          />
          <input
            value={messageAngle}
            onChange={(e) => setMessageAngle(e.target.value)}
            style={styles.input}
            placeholder="Message angle"
          />
        </div>
      </section>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Creator Pipeline</h2>
        {loading ? (
          <p style={styles.muted}>Loading creators...</p>
        ) : (
          <div style={styles.list}>
            {items.map((item) => (
              <article key={item.id} style={styles.listItem}>
                <div>
                  <strong>
                    {item.name} ({item.handle})
                  </strong>
                  <div style={styles.muted}>
                    {item.platform} • {item.followers.toLocaleString()} followers • ER {item.engagement_rate.toFixed(1)}
                    %
                  </div>
                  <div style={styles.muted}>
                    Category: {item.category} • Fit score: {item.fit_score}
                  </div>
                </div>
                <div style={styles.actionStack}>
                  <button
                    onClick={() => void handleShortlist(item.id)}
                    style={item.shortlisted ? styles.successBtn : styles.secondaryBtn}
                  >
                    {item.shortlisted ? 'Shortlisted' : 'Add to Shortlist'}
                  </button>
                  <button onClick={() => void handleBridgeToAdvocacy(item.id)} style={styles.primaryBtn}>
                    Create Selling Asset
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', padding: '32px 24px 60px' },
  header: { marginBottom: 24 },
  backLink: { color: '#60a5fa', textDecoration: 'none', fontSize: 14, display: 'inline-block', marginBottom: 12 },
  title: { margin: 0, fontSize: 34, lineHeight: 1.1 },
  subtitle: { margin: '8px 0 0', color: '#9fb0d1', maxWidth: 780 },
  errorBanner: {
    background: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: 14,
    borderRadius: 16,
    marginBottom: 20,
  },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 16, padding: 20, marginBottom: 20 },
  sectionTitle: { margin: '0 0 16px', fontSize: 20 },
  filterGrid: { display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 12 },
  input: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 14px',
  },
  primaryBtn: {
    background: '#2563eb',
    color: '#fff',
    border: 0,
    borderRadius: 12,
    padding: '12px 18px',
    cursor: 'pointer',
  },
  secondaryBtn: {
    background: 'var(--card)',
    color: '#d7e6ff',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 16px',
    cursor: 'pointer',
  },
  successBtn: {
    background: '#1f6f43',
    color: '#eafff4',
    border: '1px solid #2ea56a',
    borderRadius: 12,
    padding: '12px 16px',
    cursor: 'pointer',
  },
  list: { display: 'grid', gap: 14 },
  listItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    padding: '16px 0',
    borderTop: '1px solid #1e2a48',
  },
  actionStack: { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' },
  muted: { color: '#8ea4ca', fontSize: 13 },
};
