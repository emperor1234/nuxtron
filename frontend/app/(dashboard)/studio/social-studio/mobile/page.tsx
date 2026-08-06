'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { socialApi, type MobileDevice, type MobileSyncBatch, type SocialAccount } from '@/app/lib/social-api';

type MobileDeviceDraft = {
  device_id: string;
  platform: 'ios' | 'android' | 'web';
  push_provider: 'fcm' | 'onesignal' | 'apns' | 'none';
  push_token: string;
  app_version: string;
  locale: string;
  timezone: string;
};

const DEVICE_DEFAULT: MobileDeviceDraft = {
  device_id: 'mobile-device-001',
  platform: 'ios',
  push_provider: 'fcm',
  push_token: '',
  app_version: '1.0.0',
  locale: 'en-US',
  timezone: 'UTC',
};

export default function SocialMobilePage() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [devices, setDevices] = useState<MobileDevice[]>([]);
  const [batches, setBatches] = useState<MobileSyncBatch[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [deviceDraft, setDeviceDraft] = useState<MobileDeviceDraft>(DEVICE_DEFAULT);
  const [quickText, setQuickText] = useState('Mobile quick update from the field.');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setError(null);
    try {
      const [nextConfig, nextDevices, nextBatches, nextAccounts] = await Promise.all([
        socialApi.getMobileConfig(),
        socialApi.listMobileDevices(),
        socialApi.listMobileSyncBatches(20),
        socialApi.listAccounts(),
      ]);
      setConfig(nextConfig);
      setDevices(nextDevices);
      setBatches(nextBatches);
      setAccounts(nextAccounts);
    } catch (e) {
      console.error('Failed to load mobile workspace', e);
      setError('Mobile workspace unavailable right now.');
      setConfig(null);
      setDevices([]);
      setBatches([]);
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  async function registerDevice() {
    try {
      await socialApi.registerMobileDevice(deviceDraft);
      await loadAll();
    } catch (e) {
      console.error('Register device failed', e);
      setError('Device registration failed.');
    }
  }

  async function quickPost() {
    const firstAccount = accounts[0];
    if (!firstAccount) {
      setError('Connect one social account first.');
      return;
    }
    try {
      await socialApi.createMobileQuickPost({
        account_id: Number(firstAccount.id),
        text: quickText,
        network: 'instagram',
        publish_mode: 'draft',
      });
      await loadAll();
    } catch (e) {
      console.error('Mobile quick post failed', e);
      setError('Mobile quick post failed.');
    }
  }

  async function runOfflineSync() {
    try {
      await socialApi.syncMobileOfflineEvents({
        device_id: deviceDraft.device_id,
        events: [
          {
            id: `evt-${Date.now()}`,
            type: 'idea.create',
            payload: {
              title: 'Offline mobile idea',
              body: 'Captured while offline and synced when connectivity returned.',
              tags: ['mobile', 'offline'],
            },
          },
          {
            id: `evt-${Date.now() + 1}`,
            type: 'capture.create',
            payload: {
              source_url: 'https://example.com/mobile-capture',
              title: 'Offline capture',
              selected_text: 'Interesting point to repurpose',
              suggested_network: 'linkedin',
              tags: ['offline', 'capture'],
            },
          },
        ],
      });
      await loadAll();
    } catch (e) {
      console.error('Offline sync failed', e);
      setError('Offline sync failed. Make sure device is registered first.');
    }
  }

  return (
    <div style={styles.container}>
      <div>
        <Link href="/studio/social-studio" style={styles.backLink}>
          ← Back to Hub
        </Link>
        <h1 style={styles.title}>Mobile + PWA Ops</h1>
        <p style={styles.subtitle}>Manage mobile devices, quick-post flows, and offline sync processing.</p>
      </div>

      {error ? <div style={styles.error}>{error}</div> : null}
      {loading ? <div style={styles.card}>Loading…</div> : null}

      {loading ? null : (
        <>
          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Mobile Config</h2>
            <pre style={styles.pre}>{JSON.stringify(config, null, 2)}</pre>
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Register Device</h2>
            <div style={styles.grid}>
              <input
                style={styles.input}
                value={deviceDraft.device_id}
                onChange={(e) => setDeviceDraft((s) => ({ ...s, device_id: e.target.value }))}
                placeholder="device_id"
              />
              <select
                style={styles.input}
                value={deviceDraft.platform}
                onChange={(e) =>
                  setDeviceDraft((s) => ({ ...s, platform: e.target.value as 'ios' | 'android' | 'web' }))
                }
              >
                <option value="ios">iOS</option>
                <option value="android">Android</option>
                <option value="web">Web</option>
              </select>
              <select
                style={styles.input}
                value={deviceDraft.push_provider}
                onChange={(e) =>
                  setDeviceDraft((s) => ({
                    ...s,
                    push_provider: e.target.value as 'fcm' | 'onesignal' | 'apns' | 'none',
                  }))
                }
              >
                <option value="fcm">FCM</option>
                <option value="onesignal">OneSignal</option>
                <option value="apns">APNS</option>
                <option value="none">None</option>
              </select>
              <input
                style={styles.input}
                value={deviceDraft.push_token}
                onChange={(e) => setDeviceDraft((s) => ({ ...s, push_token: e.target.value }))}
                placeholder="push token"
              />
            </div>
            <button style={styles.button} onClick={registerDevice}>
              Register / Update Device
            </button>
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Quick Post</h2>
            <textarea style={styles.textarea} value={quickText} onChange={(e) => setQuickText(e.target.value)} />
            <button style={styles.button} onClick={quickPost}>
              Create Mobile Draft
            </button>
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Offline Sync</h2>
            <button style={styles.button} onClick={runOfflineSync}>
              Run Sample Offline Sync
            </button>
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Registered Devices ({devices.length})</h2>
            <pre style={styles.pre}>{JSON.stringify(devices, null, 2)}</pre>
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>Sync Batches ({batches.length})</h2>
            <pre style={styles.pre}>{JSON.stringify(batches, null, 2)}</pre>
          </section>
        </>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    minHeight: '100vh',
    padding: 24,
    display: 'grid',
    gap: 14,
    background: 'linear-gradient(180deg, var(--text) 0%, var(--text) 100%)',
  },
  backLink: { color: '#6366f1', textDecoration: 'none', fontWeight: 600 },
  title: { margin: '8px 0 4px', color: '#eef0f4', fontSize: 30 },
  subtitle: { margin: 0, color: '#e7e9ef' },
  card: { background: '#fff', border: '1px solid var(--muted)', borderRadius: 12, padding: 14, display: 'grid', gap: 10 },
  sectionTitle: { margin: 0, color: '#eef0f4' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 8 },
  input: { border: '1px solid var(--muted)', borderRadius: 8, padding: '8px 10px' },
  textarea: { border: '1px solid var(--muted)', borderRadius: 8, padding: '8px 10px', minHeight: 80, resize: 'vertical' },
  button: {
    border: 'none',
    borderRadius: 8,
    background: '#0f766e',
    color: '#fff',
    fontWeight: 700,
    padding: '9px 12px',
    cursor: 'pointer',
    width: 'fit-content',
  },
  pre: {
    margin: 0,
    background: 'var(--card)',
    color: 'var(--text)',
    borderRadius: 10,
    padding: 10,
    overflowX: 'auto',
    fontSize: 12,
  },
  error: {
    background: '#fee2e2',
    color: '#fee2e2',
    border: '1px solid #fecaca',
    borderRadius: 10,
    padding: '8px 10px',
  },
};
