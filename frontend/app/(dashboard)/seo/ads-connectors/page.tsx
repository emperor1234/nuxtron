'use client';

import { useEffect, useState } from 'react';
import { adsApi, AdsConnector, AdsPlatform, PLATFORM_LABELS } from '@/app/lib/ads-api';

const STATUS_COLORS: Record<string, string> = {
  connected: '#22c55e',
  disconnected: '#6b7280',
  auth_pending: '#f59e0b',
};

const FALLBACK_PLATFORM_ACCENT: Record<AdsPlatform, string> = {
  google_ads: '#4285F4',
  microsoft_ads: '#00A4EF',
  amazon_ads: '#f59e0b',
  apple_search_ads: '#cbd5e1',
  youtube_ads: '#ef4444',
};

function PlatformLogo({ platform }: Readonly<{ platform: AdsPlatform }>) {
  if (platform === 'google_ads') {
    return (
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 999,
          background: 'conic-gradient(#4285F4 0 25%, #34A853 25% 50%, #FBBC05 50% 75%, #EA4335 75% 100%)',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
        }}
      >
        <div style={{ width: 12, height: 12, borderRadius: 999, background: 'var(--text)' }} />
      </div>
    );
  }
  if (platform === 'microsoft_ads') {
    return (
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          background: '#ffffff',
          border: '1px solid var(--line)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))',
          gap: 2,
          padding: 3,
          boxSizing: 'border-box',
          flexShrink: 0,
        }}
      >
        <div style={{ borderRadius: 2, background: '#F25022' }} />
        <div style={{ borderRadius: 2, background: '#7FBA00' }} />
        <div style={{ borderRadius: 2, background: '#00A4EF' }} />
        <div style={{ borderRadius: 2, background: '#FFB900' }} />
      </div>
    );
  }
  if (platform === 'amazon_ads') {
    return (
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 999,
          background: '#ffffff',
          border: '1px solid var(--line)',
          color: '#f59e0b',
          display: 'grid',
          placeItems: 'center',
          fontSize: 15,
          fontWeight: 900,
          flexShrink: 0,
        }}
      >
        a
      </div>
    );
  }
  if (platform === 'apple_search_ads') {
    return (
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 999,
          background: '#ffffff',
          border: '1px solid var(--line)',
          color: 'var(--text)',
          display: 'grid',
          placeItems: 'center',
          fontSize: 14,
          fontWeight: 900,
          flexShrink: 0,
        }}
      >
        A
      </div>
    );
  }
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: 8,
        background: '#991b1b',
        border: '1px solid #ef4444',
        color: '#ffffff',
        display: 'grid',
        placeItems: 'center',
        fontSize: 12,
        fontWeight: 900,
        flexShrink: 0,
      }}
    >
      ▶
    </div>
  );
}

function ConnectorCard({
  connector,
  onConnect,
  onDisconnect,
  busy,
}: Readonly<{
  connector: AdsConnector;
  onConnect: (platform: AdsPlatform) => void;
  onDisconnect: (platform: AdsPlatform) => void;
  busy: boolean;
}>) {
  const color = STATUS_COLORS[connector.status] ?? '#6b7280';
  const accent = connector.platform_accent ?? FALLBACK_PLATFORM_ACCENT[connector.platform] ?? '#6366f1';

  return (
    <>
      <div
        className="connector-card"
        style={{
          background: 'var(--bg-soft, #111)',
          border: '1px solid var(--line, #333)',
          borderRadius: 16,
          padding: 18,
          boxShadow: '0 2px 8px rgba(2, 6, 23, 0.2)',
          transition: 'transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.2s ease',
          ['--accent' as string]: accent,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div className="connector-logo" style={{ transform: 'scale(1)', transition: 'transform 0.18s ease' }}>
              <PlatformLogo platform={connector.platform} />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 15 }}>
                {PLATFORM_LABELS[connector.platform] ?? connector.platform}
              </div>
              <div
                className="connector-description"
                style={{
                  fontSize: 12,
                  color: '#64748b',
                  marginTop: 4,
                  lineHeight: 1.45,
                  transition: 'color 0.18s ease',
                }}
              >
                {connector.platform_description ?? 'Connect this platform to enable campaigns and reporting.'}
              </div>
              {connector.connected && (
                <div
                  className="connector-account"
                  style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4, transition: 'color 0.18s ease' }}
                >
                  {connector.account_name} · {connector.account_id}
                </div>
              )}
            </div>
          </div>
          <span
            style={{
              borderRadius: 999,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 800,
              background: `${color}22`,
              color,
              border: `1px solid ${color}55`,
            }}
          >
            {connector.status.replace('_', ' ')}
          </span>
        </div>

        {connector.connected && (
          <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
            <Stat label="Credits Total" value={`$${connector.credit_total.toFixed(0)}`} />
            <Stat label="Credits Left" value={`$${connector.credit_remaining.toFixed(0)}`} />
            <Stat label="Currency" value={connector.credit_currency} />
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
          {connector.connected ? (
            <button
              disabled={busy}
              onClick={() => onDisconnect(connector.platform)}
              style={{
                padding: '7px 16px',
                borderRadius: 8,
                border: '1px solid #ef4444',
                color: '#ef4444',
                background: 'transparent',
                cursor: busy ? 'not-allowed' : 'pointer',
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              Disconnect
            </button>
          ) : (
            <button
              disabled={busy}
              onClick={() => onConnect(connector.platform)}
              style={{
                padding: '7px 16px',
                borderRadius: 8,
                border: '1px solid #6366f1',
                color: '#93c5fd',
                background: '#6366f122',
                cursor: busy ? 'not-allowed' : 'pointer',
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              Connect via OAuth
            </button>
          )}
        </div>
      </div>
      <style jsx>{`
        .connector-card:hover,
        .connector-card:focus-within {
          background: linear-gradient(
            135deg,
            color-mix(in srgb, var(--accent) 16%, transparent) 0%,
            var(--card) 75%
          );
          border-color: var(--accent);
          transform: translateY(-4px);
          box-shadow:
            0 12px 26px color-mix(in srgb, var(--accent) 28%, transparent),
            0 0 0 1px color-mix(in srgb, var(--accent) 14%, transparent) inset;
        }

        .connector-card:hover .connector-logo,
        .connector-card:focus-within .connector-logo {
          transform: scale(1.08);
        }

        .connector-card:hover .connector-description,
        .connector-card:focus-within .connector-description {
          color: #cbd5e1;
        }

        .connector-card:hover .connector-account,
        .connector-card:focus-within .connector-account {
          color: #e2e8f0;
        }
      `}</style>
    </>
  );
}

function Stat({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div>
      <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontWeight: 800, fontSize: 15, marginTop: 2 }}>{value}</div>
    </div>
  );
}

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<AdsConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<AdsPlatform | null>(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  async function refresh() {
    setLoading(true);
    try {
      const res = await adsApi.listConnectors();
      setConnectors(res.connectors);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load connectors.');
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    void refresh();
  }, []);

  async function handleConnect(platform: AdsPlatform) {
    setBusy(platform);
    setError('');
    try {
      const { state, authorization_url } = await adsApi.oauthStart(platform);
      // Simulate OAuth callback in dev: code=demo, account derived from platform
      const demoCode = `demo-code-${Date.now()}`;
      const res = await adsApi.oauthCallback(platform, {
        state,
        code: demoCode,
        account_name: `${PLATFORM_LABELS[platform]} — Demo Account`,
        account_id: `${platform}-demo-001`,
        scopes: ['ads.read', 'ads.write', 'reports.read'],
        credit_total: 1000,
        credit_remaining: 760,
        credit_currency: 'USD',
      });
      setInfo(`Connected ${PLATFORM_LABELS[platform]}! Auth URL: ${authorization_url.slice(0, 80)}…`);
      setConnectors((prev) => prev.map((c) => (c.platform === platform ? res.connector : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OAuth failed.');
    } finally {
      setBusy(null);
    }
  }

  async function handleDisconnect(platform: AdsPlatform) {
    setBusy(platform);
    setError('');
    try {
      const res = await adsApi.disconnectConnector(platform);
      setConnectors((prev) => prev.map((c) => (c.platform === platform ? res.connector : c)));
      setInfo(`${PLATFORM_LABELS[platform]} disconnected.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed.');
    } finally {
      setBusy(null);
    }
  }

  const connected = connectors.filter((c) => c.connected).length;

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg, #0a0a0a)', color: 'var(--text, #f1f5f9)' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 26 }}>Ad Network Connectors</h1>
            <p style={{ color: '#64748b', marginTop: 6, marginBottom: 0, fontSize: 14 }}>
              Connect ad platforms via OAuth to enable campaign management and reporting.
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 28, fontWeight: 900, color: '#22c55e' }}>{connected}</div>
            <div style={{ fontSize: 12, color: '#64748b' }}>of {connectors.length} connected</div>
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: 14,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ef4444',
              color: '#dc2626',
              background: '#7f1d1d22',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}
        {info && (
          <div
            style={{
              marginTop: 14,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #22c55e',
              color: '#86efac',
              background: '#14532d22',
              fontSize: 13,
            }}
          >
            {info}
          </div>
        )}

        {loading ? (
          <div style={{ marginTop: 40, textAlign: 'center', color: '#64748b' }}>Loading connectors…</div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))',
              gap: 14,
              marginTop: 20,
            }}
          >
            {connectors.map((c) => (
              <ConnectorCard
                key={c.platform}
                connector={c}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
                busy={busy === c.platform}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
