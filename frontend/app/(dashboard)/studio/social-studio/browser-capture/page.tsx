'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { socialApi, type BrowserCapture, type SocialAccount } from '@/app/lib/social-api';

const CAPTURE_DEFAULT = {
  source_url: 'https://example.com/article',
  title: 'Captured insight',
  selected_text: '',
  note: '',
  suggested_network: 'linkedin',
  screenshot_url: '',
  tags: 'research;insight',
};

export default function BrowserCapturePage() {
  const [captures, setCaptures] = useState<BrowserCapture[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [draft, setDraft] = useState(CAPTURE_DEFAULT);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [queueingId, setQueueingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    setError(null);
    try {
      const [nextCaptures, nextAccounts] = await Promise.all([
        socialApi.listBrowserCaptures(),
        socialApi.listAccounts(),
      ]);
      setCaptures(nextCaptures);
      setAccounts(nextAccounts);
    } catch (e) {
      console.error('Failed to load browser capture workspace', e);
      setError('Browser capture workspace unavailable right now.');
      setCaptures([]);
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  async function createCapture() {
    if (!draft.source_url.trim() || !draft.title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await socialApi.createBrowserCapture({
        source_url: draft.source_url.trim(),
        title: draft.title.trim(),
        selected_text: draft.selected_text.trim() || undefined,
        note: draft.note.trim() || undefined,
        suggested_network: draft.suggested_network.trim() || 'linkedin',
        screenshot_url: draft.screenshot_url.trim() || undefined,
        tags: draft.tags
          .split(';')
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setCaptures((current) => [created, ...current]);
      setDraft(CAPTURE_DEFAULT);
    } catch (e) {
      console.error('Failed to create capture', e);
      setError('Capture creation failed. Check URL and API availability.');
    } finally {
      setSaving(false);
    }
  }

  async function queueCapture(capture: BrowserCapture) {
    const firstAccount = accounts[0];
    if (!firstAccount) {
      setError('Connect at least one social account before queueing captured content.');
      return;
    }
    setQueueingId(capture.id);
    setError(null);
    try {
      await socialApi.queueBrowserCapture(capture.id, {
        account_id: Number(firstAccount.id),
        publish_mode: 'draft',
        target_network: capture.suggested_network || 'linkedin',
      });
      await loadData();
    } catch (e) {
      console.error('Failed to queue capture', e);
      setError('Queue action failed for this capture.');
    } finally {
      setQueueingId(null);
    }
  }

  function queueLabel(capture: BrowserCapture): string {
    if (capture.status === 'queued') {
      return 'Queued';
    }
    if (queueingId === capture.id) {
      return 'Queueing…';
    }
    return 'Queue as Draft';
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Browser Capture Pipeline</h1>
          <p style={styles.subtitle}>
            Capture web content from extension events and queue it into Social Studio posts.
          </p>
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>{error}</div> : null}

      <section style={styles.card}>
        <h2 style={styles.cardTitle}>Create Capture</h2>
        <div style={styles.formGrid}>
          <label style={styles.label}>
            Source URL
            <input
              style={styles.input}
              value={draft.source_url}
              onChange={(e) => setDraft((c) => ({ ...c, source_url: e.target.value }))}
            />
          </label>
          <label style={styles.label}>
            Title
            <input
              style={styles.input}
              value={draft.title}
              onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value }))}
            />
          </label>
          <label style={styles.label}>
            Suggested Network
            <input
              style={styles.input}
              value={draft.suggested_network}
              onChange={(e) => setDraft((c) => ({ ...c, suggested_network: e.target.value }))}
            />
          </label>
          <label style={styles.label}>
            Screenshot URL
            <input
              style={styles.input}
              value={draft.screenshot_url}
              onChange={(e) => setDraft((c) => ({ ...c, screenshot_url: e.target.value }))}
            />
          </label>
          <label style={styles.label}>
            Tags ; separated
            <input
              style={styles.input}
              value={draft.tags}
              onChange={(e) => setDraft((c) => ({ ...c, tags: e.target.value }))}
            />
          </label>
        </div>
        <label style={styles.label}>
          Selected Text
          <textarea
            style={styles.textarea}
            value={draft.selected_text}
            onChange={(e) => setDraft((c) => ({ ...c, selected_text: e.target.value }))}
          />
        </label>
        <label style={styles.label}>
          Note
          <textarea
            style={styles.textarea}
            value={draft.note}
            onChange={(e) => setDraft((c) => ({ ...c, note: e.target.value }))}
          />
        </label>
        <button style={styles.primaryButton} onClick={createCapture} disabled={saving}>
          {saving ? 'Saving…' : 'Create Capture'}
        </button>
      </section>

      <section style={styles.card}>
        <h2 style={styles.cardTitle}>Captured Items</h2>
        {loading ? <div style={styles.empty}>Loading captures…</div> : null}
        {!loading && captures.length === 0 ? <div style={styles.empty}>No captures yet.</div> : null}
        <div style={styles.list}>
          {captures.map((capture) => (
            <article key={capture.id} style={styles.captureCard}>
              <div style={styles.captureTop}>
                <h3 style={styles.captureTitle}>{capture.title}</h3>
                <span style={styles.statusPill}>{capture.status}</span>
              </div>
              <p style={styles.meta}>{capture.source_url}</p>
              <p style={styles.meta}>
                network: {capture.suggested_network} · tags: {(capture.tags || []).join(', ') || 'none'}
              </p>
              {capture.note ? <p style={styles.note}>{capture.note}</p> : null}
              <button
                style={styles.secondaryButton}
                onClick={() => void queueCapture(capture)}
                disabled={queueingId === capture.id || capture.status === 'queued'}
              >
                {queueLabel(capture)}
              </button>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    padding: 24,
    display: 'grid',
    gap: 16,
    background: 'linear-gradient(180deg, var(--text) 0%, var(--text) 100%)',
    minHeight: '100vh',
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  backLink: { color: '#6366f1', textDecoration: 'none', fontWeight: 600 },
  title: { margin: '8px 0 4px', fontSize: 30, color: '#eef0f4' },
  subtitle: { margin: 0, color: '#e7e9ef' },
  errorBanner: {
    background: '#fee2e2',
    color: '#fee2e2',
    border: '1px solid #fecaca',
    borderRadius: 12,
    padding: '10px 12px',
  },
  card: { background: '#ffffff', border: '1px solid var(--text)', borderRadius: 16, padding: 16, display: 'grid', gap: 10 },
  cardTitle: { margin: 0, color: '#eef0f4' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 10 },
  label: { display: 'grid', gap: 6, color: '#eef0f4', fontSize: 13, fontWeight: 600 },
  input: { border: '1px solid var(--muted)', borderRadius: 10, padding: '8px 10px', fontSize: 14 },
  textarea: {
    border: '1px solid var(--muted)',
    borderRadius: 10,
    padding: '8px 10px',
    minHeight: 80,
    fontSize: 14,
    resize: 'vertical',
  },
  primaryButton: {
    border: 'none',
    borderRadius: 10,
    background: '#6366f1',
    color: '#fff',
    fontWeight: 700,
    padding: '10px 14px',
    cursor: 'pointer',
    width: 'fit-content',
  },
  secondaryButton: {
    border: '1px solid #6366f1',
    borderRadius: 10,
    background: '#eff6ff',
    color: '#6366f1',
    fontWeight: 700,
    padding: '8px 12px',
    cursor: 'pointer',
    width: 'fit-content',
  },
  empty: { color: 'var(--muted)', padding: 10 },
  list: { display: 'grid', gap: 10 },
  captureCard: {
    border: '1px solid var(--text)',
    borderRadius: 12,
    padding: 12,
    background: 'var(--text)',
    display: 'grid',
    gap: 6,
  },
  captureTop: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' },
  captureTitle: { margin: 0, color: '#eef0f4', fontSize: 17 },
  statusPill: {
    background: '#dbeafe',
    color: '#6366f1',
    borderRadius: 999,
    padding: '3px 10px',
    fontSize: 12,
    fontWeight: 700,
  },
  meta: { margin: 0, color: '#e7e9ef', fontSize: 13 },
  note: { margin: 0, color: '#eef0f4', fontSize: 14 },
};
