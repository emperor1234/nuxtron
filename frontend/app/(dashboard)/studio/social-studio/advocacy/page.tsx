'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AdvocacyAsset = {
  id: string;
  title: string;
  message: string;
  network: string;
  campaign: string;
  status: 'draft' | 'ready' | 'published';
  created_at: string;
};

export default function SocialAdvocacyPage() {
  const [assets, setAssets] = useState<AdvocacyAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaign, setCampaign] = useState('Q3 Product Launch');
  const [title, setTitle] = useState('Launch update: autonomous workflows now live');
  const [message, setMessage] = useState(
    'Proud to share our latest release for social teams. Faster orchestration, clearer ROI, stronger collaboration.'
  );
  const [network, setNetwork] = useState('linkedin');

  useEffect(() => {
    void loadAssets();
  }, []);

  async function loadAssets() {
    try {
      setLoading(true);
      setError(null);
      const response = await apiGet<{ items?: AdvocacyAsset[] }>('/social/advocacy/assets', DEFAULT_TENANT_ID);
      setAssets(response.items || []);
    } catch (err) {
      console.error('Failed to load advocacy assets:', err);
      setAssets([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Failed to load advocacy queue in strict no-mock mode.'
          : 'Failed to load advocacy queue in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateAsset() {
    const response = await apiSend<{ asset?: AdvocacyAsset }>(
      '/social/advocacy/assets',
      'POST',
      {
        campaign,
        title,
        message,
        network,
      },
      DEFAULT_TENANT_ID
    ).catch(() => null);

    if (response?.asset) {
      setAssets((current) => [response.asset as AdvocacyAsset, ...current]);
      return;
    }

    setError(
      IS_STRICT_NO_MOCK_MODE
        ? 'Unable to create advocacy asset in strict no-mock mode.'
        : 'Unable to create advocacy asset in fail-closed mode.'
    );
  }

  async function handlePublishAsset(assetId: string) {
    const response = await apiSend(`/social/advocacy/assets/${assetId}/publish`, 'POST', {}, DEFAULT_TENANT_ID).catch(
      () => null
    );
    if (!response) {
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? `Unable to publish advocacy asset ${assetId} in strict no-mock mode.`
          : `Unable to publish advocacy asset ${assetId} in fail-closed mode.`
      );
      return;
    }
    setAssets((current) => current.map((asset) => (asset.id === assetId ? { ...asset, status: 'published' } : asset)));
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Employee Advocacy</h1>
          <p style={styles.subtitle}>
            Prepare share-ready employee content with campaign governance and publish controls.
          </p>
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      <div style={styles.grid}>
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Create Advocacy Asset</h2>
          <div style={styles.field}>
            <label style={styles.label}>Campaign</label>
            <input value={campaign} onChange={(e) => setCampaign(e.target.value)} style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Message</label>
            <textarea rows={5} value={message} onChange={(e) => setMessage(e.target.value)} style={styles.textarea} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Network</label>
            <select value={network} onChange={(e) => setNetwork(e.target.value)} style={styles.input}>
              <option value="linkedin">LinkedIn</option>
              <option value="x">X</option>
              <option value="facebook">Facebook</option>
            </select>
          </div>
          <button onClick={() => void handleCreateAsset()} style={styles.primaryBtn}>
            Create Asset
          </button>
        </section>

        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Distribution Queue</h2>
          {loading ? (
            <p style={styles.muted}>Loading advocacy queue...</p>
          ) : assets.length === 0 ? (
            <p style={styles.muted}>No assets yet.</p>
          ) : (
            assets.map((asset) => (
              <article key={asset.id} style={styles.listItem}>
                <strong>{asset.title}</strong>
                <div style={styles.muted}>
                  {asset.campaign} • {asset.network} • {asset.status}
                </div>
                <p style={styles.copy}>{asset.message}</p>
                {asset.status !== 'published' ? (
                  <button onClick={() => void handlePublishAsset(asset.id)} style={styles.secondaryBtn}>
                    Publish to Employee Feed
                  </button>
                ) : null}
              </article>
            ))
          )}
        </section>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', padding: '32px 24px 60px' },
  header: { marginBottom: 24 },
  backLink: { color: '#69db7c', textDecoration: 'none', fontSize: 14, display: 'inline-block', marginBottom: 12 },
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
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 16, padding: 20 },
  sectionTitle: { margin: '0 0 16px', fontSize: 20 },
  field: { display: 'grid', gap: 8, marginBottom: 14 },
  label: { fontSize: 13, color: '#9fb0d1' },
  input: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 14px',
  },
  textarea: {
    background: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid #2a3b63',
    borderRadius: 12,
    padding: '12px 14px',
    resize: 'vertical',
  },
  primaryBtn: {
    background: '#16a34a',
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
    marginTop: 8,
  },
  listItem: { display: 'grid', gap: 6, padding: '16px 0', borderTop: '1px solid #1e2a48' },
  muted: { color: '#8ea4ca', fontSize: 13 },
  copy: { margin: 0, color: '#d7e6ff' },
};
