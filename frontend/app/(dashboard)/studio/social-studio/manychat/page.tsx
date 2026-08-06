'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  socialApi,
  type ManychatBroadcast,
  type ManychatFlow,
  type ManychatKeyword,
  type ManychatOverview,
  type ManychatSegment,
  type ManychatSequence,
  type ManychatTag,
} from '@/app/lib/social-api';

type DraftState = {
  tagName: string;
  segmentName: string;
  flowName: string;
  flowTrigger: string;
  keyword: string;
  keywordReply: string;
  broadcastName: string;
  broadcastMessage: string;
  sequenceName: string;
  sequenceSteps: string;
  simulationHandle: string;
  simulationText: string;
};

const INITIAL_DRAFT: DraftState = {
  tagName: 'Prospect',
  segmentName: 'Comment Leads',
  flowName: 'IG Comment to DM',
  flowTrigger: 'demo',
  keyword: 'pricing',
  keywordReply: 'Great question. We sent pricing details in DM.',
  broadcastName: 'Weekly product update',
  broadcastMessage: 'New automation templates are live. Reply with DEMO to get walkthrough.',
  sequenceName: '3-day onboarding',
  sequenceSteps: 'Welcome message;Use-case question;Book call CTA',
  simulationHandle: '@growth_lead',
  simulationText: 'Can I get a demo and pricing?',
};

export default function ManychatPage() {
  const [overview, setOverview] = useState<ManychatOverview | null>(null);
  const [tags, setTags] = useState<ManychatTag[]>([]);
  const [segments, setSegments] = useState<ManychatSegment[]>([]);
  const [flows, setFlows] = useState<ManychatFlow[]>([]);
  const [keywords, setKeywords] = useState<ManychatKeyword[]>([]);
  const [broadcasts, setBroadcasts] = useState<ManychatBroadcast[]>([]);
  const [sequences, setSequences] = useState<ManychatSequence[]>([]);
  const [draft, setDraft] = useState<DraftState>(INITIAL_DRAFT);
  const [lastRun, setLastRun] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completionPercent = useMemo(() => {
    if (!overview) return 0;
    const rows = overview.feature_matrix || [];
    if (rows.length === 0) return 0;
    const done = rows.filter((item) => item.status === 'implemented').length;
    return Math.round((done / rows.length) * 100);
  }, [overview]);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setError(null);
    try {
      const [nextOverview, nextTags, nextSegments, nextFlows, nextKeywords, nextBroadcasts, nextSequences] =
        await Promise.all([
          socialApi.getManychatOverview(),
          socialApi.listManychatTags(),
          socialApi.listManychatSegments(),
          socialApi.listManychatFlows(),
          socialApi.listManychatKeywords(),
          socialApi.listManychatBroadcasts(),
          socialApi.listManychatSequences(),
        ]);
      setOverview(nextOverview);
      setTags(nextTags);
      setSegments(nextSegments);
      setFlows(nextFlows);
      setKeywords(nextKeywords);
      setBroadcasts(nextBroadcasts);
      setSequences(nextSequences);
    } catch (loadError) {
      console.error(loadError);
      setError('Manychat automation APIs are unavailable.');
      setOverview(null);
      setTags([]);
      setSegments([]);
      setFlows([]);
      setKeywords([]);
      setBroadcasts([]);
      setSequences([]);
    }
  }

  async function createTag() {
    if (!draft.tagName.trim()) return;
    setBusy(true);
    try {
      await socialApi.createManychatTag({ name: draft.tagName.trim() });
      await loadAll();
      setDraft((current) => ({ ...current, tagName: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function createSegment() {
    if (!draft.segmentName.trim()) return;
    setBusy(true);
    try {
      await socialApi.createManychatSegment({
        name: draft.segmentName.trim(),
        description: 'Created from Manychat workspace UI',
        conditions: [{ field: 'tag', operator: 'contains', value: 'Lead' }],
      });
      await loadAll();
      setDraft((current) => ({ ...current, segmentName: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function createFlow() {
    if (!draft.flowName.trim() || !draft.flowTrigger.trim()) return;
    setBusy(true);
    try {
      await socialApi.createManychatFlow({
        name: draft.flowName.trim(),
        channel: 'instagram',
        trigger_type: 'keyword',
        trigger_value: draft.flowTrigger.trim(),
        steps: [
          { type: 'message', text: 'Thanks for your message. Here are next steps.' },
          { type: 'assign_tag', name: 'Lead' },
          { type: 'notify_team', target: 'sales' },
        ],
      });
      await loadAll();
      setDraft((current) => ({ ...current, flowName: '', flowTrigger: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function createKeyword() {
    if (!draft.keyword.trim() || !draft.keywordReply.trim()) return;
    setBusy(true);
    try {
      await socialApi.createManychatKeyword({
        keyword: draft.keyword.trim(),
        channel: 'instagram',
        reply_text: draft.keywordReply.trim(),
        assign_tag_ids: tags.slice(0, 1).map((item) => item.id),
      });
      await loadAll();
      setDraft((current) => ({ ...current, keyword: '', keywordReply: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function createBroadcast() {
    if (!draft.broadcastName.trim() || !draft.broadcastMessage.trim()) return;
    setBusy(true);
    try {
      await socialApi.createManychatBroadcast({
        name: draft.broadcastName.trim(),
        channel: 'instagram',
        target_segment_ids: segments.slice(0, 2).map((item) => item.id),
        message: draft.broadcastMessage.trim(),
      });
      await loadAll();
      setDraft((current) => ({ ...current, broadcastName: '', broadcastMessage: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function sendBroadcast(broadcastId: number) {
    setBusy(true);
    try {
      await socialApi.sendManychatBroadcast(broadcastId);
      await loadAll();
    } finally {
      setBusy(false);
    }
  }

  async function createSequence() {
    if (!draft.sequenceName.trim()) return;
    setBusy(true);
    try {
      const steps = draft.sequenceSteps
        .split(';')
        .map((value, index) => ({ day_offset: index, message: value.trim() }))
        .filter((item) => item.message.length > 0);

      await socialApi.createManychatSequence({
        name: draft.sequenceName.trim(),
        channel: 'instagram',
        steps,
        enrollment_trigger: 'tag_added',
      });
      await loadAll();
      setDraft((current) => ({ ...current, sequenceName: '', sequenceSteps: '' }));
    } finally {
      setBusy(false);
    }
  }

  async function simulate() {
    if (!draft.simulationHandle.trim() || !draft.simulationText.trim()) return;
    setBusy(true);
    try {
      const result = await socialApi.simulateManychatEvent({
        channel: 'instagram',
        contact_handle: draft.simulationHandle.trim(),
        message_text: draft.simulationText.trim(),
      });
      setLastRun(result.run || null);
      await loadAll();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Social Studio
          </Link>
          <h1 style={styles.title}>Manychat Automation Workspace</h1>
          <p style={styles.subtitle}>
            Manage audience tags, segments, keyword automations, flows, broadcasts, and drip sequences with live API
            wiring.
          </p>
        </div>
      </div>

      {error ? <div style={styles.error}>{error}</div> : null}

      <section style={styles.statsGrid}>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Completion</span>
          <strong style={styles.metricValue}>{completionPercent}%</strong>
        </div>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Tags</span>
          <strong style={styles.metricValue}>{overview?.counts.tags ?? 0}</strong>
        </div>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Flows</span>
          <strong style={styles.metricValue}>{overview?.counts.flows ?? 0}</strong>
        </div>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Broadcasts</span>
          <strong style={styles.metricValue}>{overview?.counts.broadcasts ?? 0}</strong>
        </div>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Sequences</span>
          <strong style={styles.metricValue}>{overview?.counts.sequences ?? 0}</strong>
        </div>
        <div style={styles.card}>
          <span style={styles.metricLabel}>Automation runs</span>
          <strong style={styles.metricValue}>{overview?.counts.automation_runs ?? 0}</strong>
        </div>
      </section>

      <section style={styles.layout}>
        <article style={styles.panel}>
          <h2 style={styles.panelTitle}>Audience</h2>
          <div style={styles.inlineRow}>
            <input
              value={draft.tagName}
              onChange={(event) => setDraft((s) => ({ ...s, tagName: event.target.value }))}
              placeholder="Tag name"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createTag()} disabled={busy}>
              Add tag
            </button>
          </div>
          <div style={styles.chipRow}>
            {tags.map((tag) => (
              <span key={tag.id} style={styles.chip}>
                {tag.name}
              </span>
            ))}
          </div>
          <div style={styles.inlineRow}>
            <input
              value={draft.segmentName}
              onChange={(event) => setDraft((s) => ({ ...s, segmentName: event.target.value }))}
              placeholder="Segment name"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createSegment()} disabled={busy}>
              Add segment
            </button>
          </div>
          <ul style={styles.list}>
            {segments.map((segment) => (
              <li key={segment.id}>{segment.name}</li>
            ))}
          </ul>
        </article>

        <article style={styles.panel}>
          <h2 style={styles.panelTitle}>Flow And Keywords</h2>
          <div style={styles.inlineRow}>
            <input
              value={draft.flowName}
              onChange={(event) => setDraft((s) => ({ ...s, flowName: event.target.value }))}
              placeholder="Flow name"
              style={styles.input}
            />
            <input
              value={draft.flowTrigger}
              onChange={(event) => setDraft((s) => ({ ...s, flowTrigger: event.target.value }))}
              placeholder="Trigger keyword"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createFlow()} disabled={busy}>
              Create flow
            </button>
          </div>
          <ul style={styles.list}>
            {flows.map((flow) => (
              <li key={flow.id}>
                {flow.name} ({flow.trigger_value})
              </li>
            ))}
          </ul>

          <div style={styles.inlineRow}>
            <input
              value={draft.keyword}
              onChange={(event) => setDraft((s) => ({ ...s, keyword: event.target.value }))}
              placeholder="Keyword"
              style={styles.input}
            />
            <input
              value={draft.keywordReply}
              onChange={(event) => setDraft((s) => ({ ...s, keywordReply: event.target.value }))}
              placeholder="Auto reply"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createKeyword()} disabled={busy}>
              Add keyword
            </button>
          </div>
          <ul style={styles.list}>
            {keywords.map((item) => (
              <li key={item.id}>
                {item.keyword} {'->'} {item.reply_text}
              </li>
            ))}
          </ul>
        </article>

        <article style={styles.panel}>
          <h2 style={styles.panelTitle}>Broadcasts And Sequences</h2>
          <div style={styles.inlineRow}>
            <input
              value={draft.broadcastName}
              onChange={(event) => setDraft((s) => ({ ...s, broadcastName: event.target.value }))}
              placeholder="Broadcast name"
              style={styles.input}
            />
            <input
              value={draft.broadcastMessage}
              onChange={(event) => setDraft((s) => ({ ...s, broadcastMessage: event.target.value }))}
              placeholder="Broadcast message"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createBroadcast()} disabled={busy}>
              Create broadcast
            </button>
          </div>
          <ul style={styles.list}>
            {broadcasts.map((item) => (
              <li key={item.id}>
                {item.name} ({item.status})
                {item.status === 'sent' ? null : (
                  <button style={styles.smallButton} onClick={() => void sendBroadcast(item.id)}>
                    Send now
                  </button>
                )}
              </li>
            ))}
          </ul>

          <div style={styles.inlineRow}>
            <input
              value={draft.sequenceName}
              onChange={(event) => setDraft((s) => ({ ...s, sequenceName: event.target.value }))}
              placeholder="Sequence name"
              style={styles.input}
            />
            <input
              value={draft.sequenceSteps}
              onChange={(event) => setDraft((s) => ({ ...s, sequenceSteps: event.target.value }))}
              placeholder="Step one;Step two;Step three"
              style={styles.input}
            />
            <button style={styles.button} onClick={() => void createSequence()} disabled={busy}>
              Create sequence
            </button>
          </div>
          <ul style={styles.list}>
            {sequences.map((item) => (
              <li key={item.id}>
                {item.name} ({item.steps.length} steps)
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section style={styles.panel}>
        <h2 style={styles.panelTitle}>Automation Simulation</h2>
        <div style={styles.inlineRow}>
          <input
            value={draft.simulationHandle}
            onChange={(event) => setDraft((s) => ({ ...s, simulationHandle: event.target.value }))}
            placeholder="@contact_handle"
            style={styles.input}
          />
          <input
            value={draft.simulationText}
            onChange={(event) => setDraft((s) => ({ ...s, simulationText: event.target.value }))}
            placeholder="Incoming message text"
            style={styles.input}
          />
          <button style={styles.button} onClick={() => void simulate()} disabled={busy}>
            Run simulation
          </button>
        </div>
        {lastRun ? <pre style={styles.pre}>{JSON.stringify(lastRun, null, 2)}</pre> : null}
      </section>

      <section style={styles.panel}>
        <h2 style={styles.panelTitle}>Vendor Map</h2>
        <ul style={styles.list}>
          {(overview?.vendors || []).map((vendor) => (
            <li key={vendor.vendor}>
              <strong>{vendor.vendor}</strong>: {vendor.products.join(', ')} - {vendor.use_case}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    padding: '28px 24px 56px',
    background: 'linear-gradient(160deg, #eef0f4 0%, #eef0f4 45%, #14213d 100%)',
    color: 'var(--text)',
  },
  header: { marginBottom: 20 },
  backLink: { color: 'var(--brand)', textDecoration: 'none', display: 'inline-block', marginBottom: 10 },
  title: { margin: '0 0 8px', fontSize: 30 },
  subtitle: { margin: 0, color: 'var(--muted)', maxWidth: 900 },
  error: { padding: 12, borderRadius: 10, background: '#fee2e2', marginBottom: 16 },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
    gap: 12,
    marginBottom: 18,
  },
  layout: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: 14, marginBottom: 14 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 12 },
  panel: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: 14,
    marginBottom: 14,
  },
  panelTitle: { margin: '0 0 12px', fontSize: 20 },
  metricLabel: { display: 'block', color: 'var(--muted)', fontSize: 12 },
  metricValue: { fontSize: 26 },
  inlineRow: { display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  input: {
    flex: 1,
    minWidth: 150,
    borderRadius: 10,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: 'var(--text)',
    padding: '10px 12px',
  },
  button: {
    borderRadius: 10,
    border: 0,
    background: '#6366f1',
    color: '#fff',
    padding: '10px 14px',
    cursor: 'pointer',
  },
  smallButton: {
    marginLeft: 8,
    borderRadius: 8,
    border: 0,
    background: '#0ea5e9',
    color: '#fff',
    padding: '5px 8px',
    cursor: 'pointer',
  },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  chip: {
    borderRadius: 999,
    background: 'rgba(30,64,175,0.35)',
    border: '1px solid rgba(96,165,250,0.7)',
    padding: '4px 10px',
    fontSize: 12,
  },
  list: { margin: 0, paddingLeft: 18, lineHeight: 1.7 },
  pre: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 10, overflowX: 'auto' },
};
