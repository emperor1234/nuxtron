'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type SocialAccount, type SocialNetwork } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

// Monogram badges, not emoji: lucide-react 1.14 dropped brand/logo icons
// (Facebook, Instagram, etc. are all undefined), and approximating a
// trademarked logo with a generic icon is worse than a plain initial.
const SOCIAL_NETWORKS: { network: SocialNetwork; label: string; monogram: string; color: string }[] = [
  { network: 'facebook', label: 'Facebook', monogram: 'f', color: '#1877F2' },
  { network: 'instagram', label: 'Instagram', monogram: 'IG', color: '#E4405F' },
  { network: 'tiktok', label: 'TikTok', monogram: 'TT', color: '#000000' },
  { network: 'twitter', label: 'X (Twitter)', monogram: 'X', color: '#000000' },
  { network: 'linkedin', label: 'LinkedIn', monogram: 'in', color: '#0A66C2' },
  { network: 'youtube', label: 'YouTube', monogram: 'YT', color: '#FF0000' },
  { network: 'threads', label: 'Threads', monogram: '@', color: '#000000' },
];

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<SocialNetwork | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  async function loadAccounts() {
    try {
      setError(null);
      const result = await socialApi.listAccounts();
      setAccounts(result || []);
    } catch (err) {
      console.error('Failed to load accounts:', err);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Failed to load social accounts in strict no-mock mode.'
          : 'Failed to load social accounts in fail-closed mode.'
      );
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect(network: SocialNetwork) {
    setConnecting(network);
    setError(null);
    try {
      const { authorization_url: authorizationUrl } = await socialApi.startOAuth(network);
      // Full navigation, not a fetch — the provider's authorization page is
      // a real page the user must interact with, and it redirects back to
      // our own /oauth/[network]/callback route with ?code=&state=.
      globalThis.location.href = authorizationUrl;
    } catch (err) {
      console.error('Connect failed:', err);
      setError(err instanceof Error ? err.message : `Failed to connect ${network}. Please try again.`);
      setConnecting(null);
    }
  }

  async function handleDisconnect(accountId: string) {
    if (!confirm('Are you sure you want to disconnect this account?')) return;
    try {
      await socialApi.disconnectAccount(accountId);
      setAccounts(accounts.filter((a) => a.id !== accountId));
    } catch (err) {
      console.error('Disconnect failed:', err);
      alert('Failed to disconnect account. Please try again.');
    }
  }

  const connectedNetworks = new Set(accounts.map((a) => a.network));
  const availableNetworks = SOCIAL_NETWORKS.filter((n) => !connectedNetworks.has(n.network));

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Social Media Accounts</h1>
          <p style={styles.subtitle}>Connect and manage your social media accounts across all major platforms</p>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>⚠️ {error}</div>}

      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
        </div>
      ) : (
        <>
          {/* Connected Accounts Section */}
          {accounts.length > 0 && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>Connected Accounts ({accounts.length})</h2>
              <div style={styles.accountGrid}>
                {accounts.map((account) => {
                  const network = SOCIAL_NETWORKS.find((n) => n.network === account.network);
                  return (
                    <div key={account.id} style={styles.accountCard}>
                      <div style={{ ...styles.cardHeader, borderLeftColor: network?.color }}>
                        <span style={{ ...styles.networkIcon, background: network?.color }}>{network?.monogram}</span>
                        <div style={styles.accountInfo}>
                          <h3 style={styles.accountName}>{account.accountName}</h3>
                          <p style={styles.accountHandle}>{account.handle}</p>
                        </div>
                        <span style={styles.verifiedBadge}>{account.verified ? '✓' : ''}</span>
                      </div>

                      <div style={styles.cardStats}>
                        <div style={styles.stat}>
                          <span style={styles.statLabel}>Followers</span>
                          <span style={styles.statValue}>{account.followers.toLocaleString()}</span>
                        </div>
                        <div style={styles.stat}>
                          <span style={styles.statLabel}>Sync Status</span>
                          <span
                            style={{
                              ...styles.statusBadge,
                              backgroundColor:
                                account.syncStatus === 'synced'
                                  ? '#10B98126'
                                  : account.syncStatus === 'syncing'
                                    ? '#F5901426'
                                    : '#EF444426',
                              color:
                                account.syncStatus === 'synced'
                                  ? '#047857'
                                  : account.syncStatus === 'syncing'
                                    ? '#B45309'
                                    : '#DC2626',
                            }}
                          >
                            {account.syncStatus}
                          </span>
                        </div>
                        <div style={styles.stat}>
                          <span style={styles.statLabel}>Credits Balance</span>
                          <span style={styles.statValue}>{account.creditsBalance}</span>
                        </div>
                      </div>

                      <div style={styles.cardFooter}>
                        <small style={styles.syncedTime}>
                          Last sync: {new Date(account.last_sync).toLocaleString()}
                        </small>
                        <button onClick={() => handleDisconnect(account.id)} style={styles.disconnectBtn}>
                          Disconnect
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Available Networks Section */}
          {availableNetworks.length > 0 && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>Available Networks ({availableNetworks.length})</h2>
              <div style={styles.networkGrid}>
                {availableNetworks.map((network) => (
                  <button
                    key={network.network}
                    onClick={() => handleConnect(network.network)}
                    disabled={connecting === network.network}
                    style={{
                      ...styles.connectCard,
                      opacity: connecting === network.network ? 0.6 : 1,
                      cursor: connecting === network.network ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <span style={{ ...styles.connectIcon, background: network.color }}>{network.monogram}</span>
                    <span style={styles.connectLabel}>{network.label}</span>
                    {connecting === network.network && <span style={styles.connectingSpinner}>⟳</span>}
                  </button>
                ))}
              </div>
            </section>
          )}

          {accounts.length === 0 && availableNetworks.length === 0 && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>🔗</div>
              <h2>No Accounts Connected</h2>
              <p>Connect your social media accounts to get started</p>
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
    marginBottom: '48px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--muted)',
    textDecoration: 'none',
    fontSize: '14px',
    transition: 'color 0.2s',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: '0 0 8px',
    color: 'var(--text)',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--muted)',
    margin: 0,
  },
  errorBanner: {
    backgroundColor: '#ffedd526',
    border: '1px solid #DC266326',
    borderRadius: '8px',
    padding: '12px 16px',
    marginBottom: '24px',
    fontSize: '14px',
    color: '#dc2626',
  },
  section: {
    marginBottom: '40px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '16px',
    color: 'var(--text)',
  },
  accountGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
    gap: '16px',
  },
  accountCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    overflow: 'hidden',
    transition: 'all 0.2s',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px',
    borderLeft: '4px solid #6366f1',
    backgroundColor: 'var(--card)',
  },
  networkIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    fontSize: '13px',
    fontWeight: 700,
    color: '#fff',
    flexShrink: 0,
  },
  accountInfo: {
    flex: 1,
  },
  accountName: {
    margin: '0 0 4px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  accountHandle: {
    margin: 0,
    fontSize: '12px',
    color: 'var(--muted)',
  },
  verifiedBadge: {
    fontSize: '16px',
    color: '#6366f1',
  },
  cardStats: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
    gap: '12px',
    padding: '16px',
    borderTop: '1px solid var(--line)',
  },
  stat: {
    display: 'flex',
    flexDirection: 'column',
  },
  statLabel: {
    fontSize: '11px',
    color: 'var(--muted)',
    marginBottom: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  statValue: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
  },
  cardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderTop: '1px solid var(--line)',
    backgroundColor: 'var(--card)',
  },
  syncedTime: {
    color: 'var(--muted)',
    fontSize: '12px',
  },
  disconnectBtn: {
    padding: '6px 12px',
    backgroundColor: '#DC266326',
    color: '#dc2626',
    border: '1px solid #DC266326',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  networkGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))',
    gap: '12px',
  },
  connectCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '20px',
    backgroundColor: 'var(--card)',
    border: '2px dashed #e7e9ef',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text)',
  },
  connectIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '44px',
    height: '44px',
    borderRadius: '12px',
    fontSize: '15px',
    fontWeight: 700,
    color: '#fff',
  },
  connectLabel: {
    textAlign: 'center',
    fontSize: '13px',
  },
  connectingSpinner: {
    display: 'inline-block',
    animation: 'spin 1s linear infinite',
    fontSize: '16px',
  },
  skeleton: {
    display: 'grid',
    gap: '16px',
  },
  skeletonCard: {
    height: '200px',
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
