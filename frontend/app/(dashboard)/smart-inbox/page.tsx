'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, DataStatus, Field, FieldSelect, Page, PageHeader, Stat, StatGrid } from '../_ui/kit';
import { filterInboxMessages, isInboxPreviewResponse, parseInboxMessages, parseInboxStats, type InboxStatusFilter, type InboxMessage, type InboxStats } from './inbox-model';
import styles from './smart-inbox.module.css';

const STATUS_OPTIONS: Array<{ value: InboxStatusFilter; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'requires_approval', label: 'Requires approval' },
  { value: 'flagged', label: 'Flagged' },
  { value: 'complete', label: 'Complete' },
];

function formatStatus(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function SmartInboxPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [loading, setLoading] = useState(Boolean(tenantId));
  const [hasLoaded, setHasLoaded] = useState(false);
  const [preview, setPreview] = useState(false);
  const [loadError, setLoadError] = useState(tenantId ? '' : 'Workspace context is required. Sign in or select a workspace to open the inbox.');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<InboxStatusFilter>('all');
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [network, setNetwork] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [author, setAuthor] = useState('');
  const [text, setText] = useState('');
  const [writing, setWriting] = useState(false);
  const [pendingMessageId, setPendingMessageId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!tenantId) {
      setLoading(false);
      setLoadError('Workspace context is required. Sign in or select a workspace to open the inbox.');
      return;
    }

    setLoading(true);
    setLoadError('');
    try {
      const [statsResponse, messagesResponse] = await Promise.all([
        apiGet<unknown>('/inbox/stats', tenantId),
        apiGet<unknown>('/inbox/messages?limit=200', tenantId),
      ]);
      const nextStats = parseInboxStats(statsResponse);
      const nextMessages = parseInboxMessages(messagesResponse);
      setStats(nextStats);
      setMessages(nextMessages);
      setPreview(isInboxPreviewResponse(statsResponse) || isInboxPreviewResponse(messagesResponse));
      setHasLoaded(true);
    } catch (cause) {
      setLoadError(cause instanceof Error ? cause.message : 'Unable to load inbox data.');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;
    let active = true;
    window.queueMicrotask(() => {
      if (active) void load();
    });
    return () => {
      active = false;
    };
  }, [load, tenantId]);

  const visibleMessages = useMemo(
    () => filterInboxMessages(messages, statusFilter, query),
    [messages, query, statusFilter],
  );
  const canWrite = Boolean(tenantId) && hasLoaded && !preview && !loadError && !loading;

  async function updateStatus(message: InboxMessage, nextStatus: string) {
    if (!canWrite) return;
    setPendingMessageId(message.id);
    setActionError('');
    setNotice('');
    try {
      await apiSend(`/inbox/messages/${message.id}`, 'PATCH', { status: nextStatus }, tenantId);
      setMessages((current) => current.map((item) => item.id === message.id ? { ...item, status: nextStatus } : item));
      setNotice(`Status updated for ${message.author_handle}.`);
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : 'Unable to update message status.');
    } finally {
      setPendingMessageId(null);
    }
  }

  async function ingest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canWrite) return;
    setWriting(true);
    setActionError('');
    setNotice('');
    try {
      await apiSend('/inbox/messages', 'POST', {
        network: network.trim(),
        source_type: sourceType.trim(),
        author_handle: author.trim(),
        text: text.trim(),
      }, tenantId);
      setNotice('Message added to the workspace inbox.');
      setNetwork('');
      setSourceType('');
      setAuthor('');
      setText('');
      setIntakeOpen(false);
      await load();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : 'Unable to add this message.');
    } finally {
      setWriting(false);
    }
  }

  const liveState = preview ? 'preview' : loadError && !hasLoaded ? 'unavailable' : 'live';

  return (
    <Page>
      <PageHeader
        title="Customer Inbox"
        subtitle="Triage workspace messages by channel, urgency, and status."
        actions={
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <Button onClick={() => void load()} disabled={loading || !tenantId}>
              {loading ? 'Refreshing…' : 'Refresh inbox'}
            </Button>
            <Button variant="primary" aria-expanded={intakeOpen} onClick={() => setIntakeOpen((value) => !value)} disabled={!canWrite}>
              {intakeOpen ? 'Close intake' : 'Add existing message'}
            </Button>
          </div>
        }
      />

      <div>
        {loading ? <p role="status" aria-live="polite">Loading workspace messages…</p> : null}
        {!loading && !(loadError && hasLoaded) ? <DataStatus state={liveState} provider="Customer Inbox" /> : null}
        {loadError ? (
          <div role="alert" style={{ marginTop: 10, color: 'var(--danger)' }}>
            <p>{loadError}</p>
            {hasLoaded ? <p>Previously loaded messages are retained; the latest refresh did not complete.</p> : null}
            <Button onClick={() => void load()} disabled={loading || !tenantId}>Retry inbox load</Button>
          </div>
        ) : null}
      </div>

      {notice ? <p role="status" aria-live="polite">{notice}</p> : null}
      {actionError ? <p role="alert">{actionError}</p> : null}

      <section aria-label="Inbox summary" aria-busy={loading}>
        <StatGrid>
          <Stat label="Total messages" value={loading ? '…' : stats?.total ?? '—'} hint="Latest workspace snapshot" />
          <Stat label="Unread" value={loading ? '…' : stats?.unread ?? '—'} hint="Requires attention" />
          <Stat label="Messages shown" value={loading ? '…' : messages.length} hint="Up to 200 most recent" />
        </StatGrid>
      </section>

      <div className={styles.grid}>
        <section aria-label="Triage queue">
          <Card>
            <div className={styles.toolbar}>
              <div style={{ flex: '1 1 100%' }}>
                <CardTitle sub="Search the loaded workspace messages and narrow by current status.">Triage queue</CardTitle>
              </div>
              <div className={styles.filters}>
                <Field id="inbox-search" label="Search messages" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Author, channel, or message text" />
                <FieldSelect id="inbox-status-filter" label="Status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as InboxStatusFilter)}>
                  {STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </FieldSelect>
              </div>
              <Button onClick={() => void load()} disabled={loading || !tenantId}>Refresh</Button>
            </div>
          </Card>

          <div className={styles.queue} aria-busy={loading}>
            {loading ? <p role="status">Loading messages…</p> : null}
            {!loading && hasLoaded && messages.length === 0 && !loadError ? (
              <Card><p>No messages have been received for this workspace.</p><p className={styles.note}>To add an existing conversation, use the secondary intake action. This does not connect a social channel or send a reply.</p></Card>
            ) : null}
            {!loading && messages.length > 0 && visibleMessages.length === 0 ? (
              <Card><p>No messages match the selected search and status filters.</p></Card>
            ) : null}
            {!loading && visibleMessages.map((message) => (
              <article className={styles.message} key={message.id} aria-label={`Message from ${message.author_handle}`}>
                <div className={styles.messageHeader}>
                  <div className={styles.messageIdentity}>
                    <h2 style={{ margin: 0, fontSize: 15 }}>{message.author_handle}</h2>
                    <p className={styles.note}>{message.network} · {message.source_type}</p>
                  </div>
                  <div className={styles.messageMeta}>
                    <Badge tone={message.status === 'complete' ? 'success' : message.status === 'flagged' ? 'danger' : 'brand'}>{formatStatus(message.status)}</Badge>
                    <Badge>{message.read === null ? 'Read state unknown' : message.read ? 'Read' : 'Unread'}</Badge>
                  </div>
                </div>
                <p className={styles.messageText}>{message.text}</p>
                <div className={styles.messageMeta}>
                  <span>Type: {message.message_type}</span>
                  <span>Sentiment: {message.sentiment}</span>
                  <span>Priority: {message.priority_score ?? '—'}</span>
                </div>
                <div className={styles.messageActions}>
                  <FieldSelect
                    id={`inbox-status-${message.id}`}
                    label="Update status"
                    aria-label={`Update status for ${message.author_handle}`}
                    className={styles.statusField}
                    value={message.status}
                    onChange={(event) => void updateStatus(message, event.target.value)}
                    disabled={!canWrite || pendingMessageId === message.id}
                  >
                    {STATUS_OPTIONS.filter((option) => option.value !== 'all').map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </FieldSelect>
                  {pendingMessageId === message.id ? <span role="status">Saving status…</span> : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside>
          {intakeOpen ? (
            <Card>
              <CardTitle sub="Manually record a message received elsewhere. This form does not connect a channel or send a reply.">Add existing message</CardTitle>
              <form className={styles.intake} onSubmit={(event) => void ingest(event)} style={{ marginTop: 16 }}>
                <FieldSelect id="intake-network" label="Channel" value={network} onChange={(event) => setNetwork(event.target.value)} required>
                  <option value="">Choose a channel</option>
                  {['instagram', 'facebook', 'x', 'linkedin', 'youtube', 'tiktok', 'reddit', 'other'].map((value) => <option key={value} value={value}>{formatStatus(value)}</option>)}
                </FieldSelect>
                <FieldSelect id="intake-source" label="Message source" value={sourceType} onChange={(event) => setSourceType(event.target.value)} required>
                  <option value="">Choose a source type</option>
                  {['dm', 'comment', 'mention', 'review', 'story_reply'].map((value) => <option key={value} value={value}>{formatStatus(value)}</option>)}
                </FieldSelect>
                <Field id="intake-author" label="Author handle" value={author} onChange={(event) => setAuthor(event.target.value)} maxLength={120} required autoComplete="off" />
                <label className={styles.textareaLabel} htmlFor="intake-text">
                  Message text
                  <textarea id="intake-text" className={styles.textarea} value={text} onChange={(event) => setText(event.target.value)} maxLength={5000} rows={5} required />
                </label>
                <p className={styles.note}>The message will be stored in this workspace. No customer reply is sent.</p>
                <Button type="submit" variant="primary" disabled={!canWrite || writing || !network || !sourceType || !author.trim() || !text.trim()}>
                  {writing ? 'Adding message…' : 'Add to inbox'}
                </Button>
              </form>
            </Card>
          ) : (
            <Card>
              <CardTitle sub="Connect a social account to manage channel conversations from the publishing workspace.">Channel setup</CardTitle>
              <p className={styles.note} style={{ marginTop: 12 }}>This inbox shows workspace messages available to the inbox service. Connected social publishing accounts are managed separately.</p>
              <Link href="/studio/social-studio/accounts">Manage social accounts</Link>
            </Card>
          )}
        </aside>
      </div>
    </Page>
  );
}
