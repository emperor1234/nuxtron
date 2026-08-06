'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { socialApi, type ContactView, type InboxItem, type SavedReply } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type InboxMessage = InboxItem & {
  assignedTo?: string;
  state?: 'open' | 'claimed' | 'complete';
};

export default function InboxPage() {
  const [items, setItems] = useState<InboxMessage[]>([]);
  const [savedReplies, setSavedReplies] = useState<SavedReply[]>([]);
  const [contacts, setContacts] = useState<ContactView[]>([]);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread' | 'responded'>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [respondingTo, setRespondingTo] = useState<string | null>(null);
  const [responseText, setResponseText] = useState('');
  const [agentName, setAgentName] = useState('Social Desk');
  const [draftReply, setDraftReply] = useState({ title: '', body: '', category: 'general' });
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    void loadInbox();
  }, [filter]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (filter === 'unread') return !item.responded;
      if (filter === 'responded') return item.responded;
      return true;
    });
  }, [filter, items]);

  const selectedItem = filtered.find((item) => item.id === selectedId) ?? filtered[0] ?? null;

  useEffect(() => {
    if (selectedItem && selectedItem.id !== selectedId) {
      setSelectedId(selectedItem.id);
    }
    if (selectedItem) {
      void loadHistory(selectedItem.id);
    }
  }, [selectedId, selectedItem]);

  async function loadInbox() {
    setLoading(true);
    setLoadError(null);
    try {
      const unreadOnly = filter === 'unread';
      const [nextItems, nextReplies, nextContacts] = await Promise.all([
        socialApi.listInboxItems(unreadOnly),
        socialApi.listSavedReplies(),
        socialApi.listContactViews(),
      ]);
      setItems((nextItems as InboxMessage[]) || []);
      setSavedReplies(nextReplies || []);
      setContacts(nextContacts || []);
      setSelectedId(String((nextItems[0] as InboxMessage | undefined)?.id ?? ''));
    } catch (err) {
      console.error('Failed to load inbox:', err);
      setItems([]);
      setSavedReplies([]);
      setContacts([]);
      setSelectedId(null);
      setLoadError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Inbox backend unavailable in strict no-mock mode.'
          : 'Inbox backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory(messageId: string) {
    try {
      const result = await socialApi.getMessageHistory(messageId);
      setHistory(result);
    } catch (err) {
      console.error('Failed to load history:', err);
      const message = items.find((item) => item.id === messageId);
      setHistory(
        message
          ? [
              {
                id: message.id,
                author_display_name: message.source,
                content: message.content,
                created_at: message.createdAt,
              },
            ]
          : []
      );
    }
  }

  async function handleRespond(itemId: string) {
    if (!responseText.trim()) return;
    try {
      await socialApi.respondToItem(itemId, responseText);
      setItems((current) =>
        current.map((item) => (item.id === itemId ? { ...item, responded: true, state: 'claimed' } : item))
      );
      setRespondingTo(null);
      setResponseText('');
      await loadHistory(itemId);
    } catch (err) {
      console.error('Response failed:', err);
      alert('Failed to send response');
    }
  }

  async function handleMarkAsRead(itemId: string) {
    try {
      await socialApi.markAsRead(itemId);
      setItems((current) => current.map((item) => (item.id === itemId ? { ...item } : item)));
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  }

  async function handleClaim(itemId: string) {
    try {
      await socialApi.claimMessage(itemId, agentName);
      setItems((current) =>
        current.map((item) => (item.id === itemId ? { ...item, assignedTo: agentName, state: 'claimed' } : item))
      );
    } catch (err) {
      console.error('Claim failed:', err);
      alert('Failed to claim message');
    }
  }

  async function handleComplete(itemId: string) {
    try {
      await socialApi.completeMessage(itemId);
      setItems((current) =>
        current.map((item) => (item.id === itemId ? { ...item, responded: true, state: 'complete' } : item))
      );
    } catch (err) {
      console.error('Complete failed:', err);
      alert('Failed to complete message');
    }
  }

  async function handleCreateSavedReply() {
    if (!draftReply.title.trim() || !draftReply.body.trim()) return;
    try {
      const created = await socialApi.createSavedReply(draftReply);
      setSavedReplies((current) => [created, ...current]);
      setDraftReply({ title: '', body: '', category: 'general' });
    } catch (err) {
      console.error('Failed to save reply:', err);
      alert('Saved reply could not be created');
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return '#22c55e';
      case 'negative':
        return '#ef4444';
      default:
        return 'var(--muted)';
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Smart Inbox</h1>
          <p style={styles.subtitle}>
            Run a collaborative inbox with saved replies, contact context, message claiming, and completion workflows.
          </p>
        </div>
        <div style={styles.headerControls}>
          <input
            value={agentName}
            onChange={(event) => setAgentName(event.target.value)}
            placeholder="Agent name"
            style={styles.inlineInput}
          />
        </div>
      </div>

      {loadError ? <div style={styles.errorBanner}>⚠ {loadError}</div> : null}

      <div style={styles.filterTabs}>
        {(['all', 'unread', 'responded'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            style={{
              ...styles.filterTab,
              background: filter === tab ? 'rgba(59, 130, 246, 0.16)' : 'transparent',
              borderColor: filter === tab ? '#6366f1' : 'rgba(148, 163, 184, 0.16)',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={styles.loadingCard}>Loading inbox…</div>
      ) : (
        <div style={styles.layout}>
          <section style={styles.messageList}>
            {filtered.map((item) => (
              <article
                key={item.id}
                onClick={() => setSelectedId(item.id)}
                style={{
                  ...styles.messageCard,
                  borderColor: item.id === selectedItem?.id ? '#6366f1' : 'rgba(148, 163, 184, 0.14)',
                }}
              >
                <div style={styles.messageTop}>
                  <div>
                    <strong style={styles.messageSource}>{item.source}</strong>
                    <p style={styles.messageMeta}>
                      {item.network} • {item.type} • {new Date(item.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <span style={{ ...styles.badge, color: getSentimentColor(item.sentiment) }}>{item.sentiment}</span>
                </div>
                <p style={styles.messageContent}>{item.content}</p>
                <div style={styles.messageActionsRow}>
                  <span style={styles.smallMeta}>Engagement {item.engagement}</span>
                  <span style={styles.smallMeta}>
                    {item.assignedTo ? `Claimed by ${item.assignedTo}` : 'Unclaimed'}
                  </span>
                  <span style={styles.smallMeta}>{item.state ?? (item.responded ? 'complete' : 'open')}</span>
                </div>
              </article>
            ))}
          </section>

          <section style={styles.detailPanel}>
            {selectedItem ? (
              <>
                <div style={styles.detailCard}>
                  <div style={styles.detailHeader}>
                    <div>
                      <p style={styles.eyebrow}>Active thread</p>
                      <h2 style={styles.detailTitle}>{selectedItem.source}</h2>
                    </div>
                    <div style={styles.detailActions}>
                      <button onClick={() => handleMarkAsRead(selectedItem.id)} style={styles.secondaryButton}>
                        Mark as read
                      </button>
                      <button onClick={() => handleClaim(selectedItem.id)} style={styles.secondaryButton}>
                        Claim
                      </button>
                      <button onClick={() => handleComplete(selectedItem.id)} style={styles.primaryButton}>
                        Complete
                      </button>
                    </div>
                  </div>
                  <p style={styles.detailCopy}>{selectedItem.content}</p>
                  <div style={styles.historyList}>
                    {history.map((entry, index) => (
                      <div key={`${selectedItem.id}-${index}`} style={styles.historyItem}>
                        <strong style={styles.historyAuthor}>
                          {String(entry.author_display_name || entry.author_handle || 'Conversation update')}
                        </strong>
                        <p style={styles.historyCopy}>{String(entry.content || entry.reply_text || '')}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={styles.composerCard}>
                  <div style={styles.panelTitleRow}>
                    <h3 style={styles.panelTitle}>Response composer</h3>
                    <button onClick={() => setRespondingTo(selectedItem.id)} style={styles.secondaryButton}>
                      Open composer
                    </button>
                  </div>
                  {respondingTo === selectedItem.id && (
                    <>
                      <textarea
                        value={responseText}
                        onChange={(event) => setResponseText(event.target.value)}
                        placeholder="Write a response or insert a saved reply."
                        style={styles.textarea}
                      />
                      <div style={styles.savedReplyRow}>
                        {savedReplies.map((reply) => (
                          <button key={reply.id} onClick={() => setResponseText(reply.body)} style={styles.replyChip}>
                            {reply.title}
                          </button>
                        ))}
                      </div>
                      <div style={styles.composeActions}>
                        <span style={styles.smallMeta}>{responseText.length} characters</span>
                        <button onClick={() => handleRespond(selectedItem.id)} style={styles.primaryButton}>
                          Send reply
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </>
            ) : (
              <div style={styles.emptyState}>No messages available for the selected filter.</div>
            )}
          </section>

          <aside style={styles.sideColumn}>
            <div style={styles.sideCard}>
              <div style={styles.panelTitleRow}>
                <h3 style={styles.panelTitle}>Saved replies</h3>
              </div>
              <div style={styles.sideForm}>
                <input
                  value={draftReply.title}
                  onChange={(event) => setDraftReply((current) => ({ ...current, title: event.target.value }))}
                  placeholder="Reply title"
                  style={styles.inlineInput}
                />
                <textarea
                  value={draftReply.body}
                  onChange={(event) => setDraftReply((current) => ({ ...current, body: event.target.value }))}
                  placeholder="Saved reply body"
                  style={styles.smallTextarea}
                />
                <button onClick={handleCreateSavedReply} style={styles.secondaryButton}>
                  Save reply
                </button>
              </div>
            </div>

            <div style={styles.sideCard}>
              <h3 style={styles.panelTitle}>Contact views</h3>
              <div style={styles.contactList}>
                {contacts.map((contact) => (
                  <div key={contact.handle} style={styles.contactItem}>
                    <strong style={styles.contactName}>{contact.display_name}</strong>
                    <p style={styles.contactMeta}>
                      {contact.handle} • {contact.message_count} messages • {contact.networks.join(', ')}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(180deg, #09111d 0%, #eef0f4 42%, #eef0f4 100%)',
    color: '#eceff4',
    padding: '32px 24px 64px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    marginBottom: '24px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--brand)',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '15px',
    color: 'var(--muted)',
    margin: 0,
    maxWidth: '760px',
    lineHeight: 1.6,
  },
  headerControls: {
    display: 'flex',
    gap: '12px',
  },
  errorBanner: {
    background: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '14px',
    borderRadius: '16px',
    marginBottom: '20px',
  },
  inlineInput: {
    minWidth: '220px',
    padding: '12px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: '#eceff4',
  },
  filterTabs: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px',
  },
  filterTab: {
    padding: '10px 14px',
    borderRadius: '999px',
    border: '1px solid var(--line)',
    color: 'var(--muted)',
    cursor: 'pointer',
  },
  loadingCard: {
    padding: '24px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: 'minmax(280px, 360px) repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
    gap: '18px',
  },
  messageList: {
    display: 'grid',
    gap: '12px',
  },
  messageCard: {
    padding: '16px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
    cursor: 'pointer',
  },
  messageTop: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    marginBottom: '10px',
  },
  messageSource: {
    fontSize: '15px',
  },
  messageMeta: {
    margin: '6px 0 0',
    color: 'var(--muted)',
    fontSize: '12px',
  },
  badge: {
    fontSize: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  messageContent: {
    margin: '0 0 12px',
    color: 'var(--text)',
    lineHeight: 1.5,
  },
  messageActionsRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  smallMeta: {
    color: 'var(--muted)',
    fontSize: '12px',
  },
  detailPanel: {
    display: 'grid',
    gap: '16px',
  },
  detailCard: {
    padding: '20px',
    borderRadius: '22px',
    background: 'var(--card)',
    border: '1px solid rgba(59, 130, 246, 0.18)',
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  eyebrow: {
    margin: '0 0 6px',
    color: 'var(--brand)',
    textTransform: 'uppercase',
    fontSize: '12px',
    letterSpacing: '0.08em',
  },
  detailTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: 700,
  },
  detailActions: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
  },
  primaryButton: {
    padding: '10px 14px',
    borderRadius: '12px',
    border: 'none',
    background: '#6366f1',
    color: '#eff6ff',
    cursor: 'pointer',
    fontWeight: 600,
  },
  secondaryButton: {
    padding: '10px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'transparent',
    color: 'var(--text)',
    cursor: 'pointer',
  },
  detailCopy: {
    margin: '0 0 16px',
    color: 'var(--text)',
    lineHeight: 1.6,
  },
  historyList: {
    display: 'grid',
    gap: '10px',
  },
  historyItem: {
    padding: '12px 14px',
    borderRadius: '16px',
    background: 'rgba(8, 15, 30, 0.72)',
    border: '1px solid var(--line)',
  },
  historyAuthor: {
    display: 'block',
    marginBottom: '6px',
  },
  historyCopy: {
    margin: 0,
    color: 'var(--muted)',
    lineHeight: 1.5,
  },
  composerCard: {
    padding: '20px',
    borderRadius: '22px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  panelTitleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '12px',
    alignItems: 'center',
    marginBottom: '12px',
  },
  panelTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 700,
  },
  textarea: {
    width: '100%',
    minHeight: '140px',
    padding: '14px',
    borderRadius: '16px',
    border: '1px solid var(--line)',
    background: 'rgba(8, 15, 30, 0.76)',
    color: '#eceff4',
    resize: 'vertical',
  },
  savedReplyRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    margin: '12px 0',
  },
  replyChip: {
    padding: '8px 12px',
    borderRadius: '999px',
    border: '1px solid rgba(96, 165, 250, 0.26)',
    background: 'rgba(37, 99, 235, 0.14)',
    color: '#dbeafe',
    cursor: 'pointer',
  },
  composeActions: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '12px',
    alignItems: 'center',
    marginTop: '10px',
  },
  sideColumn: {
    display: 'grid',
    gap: '16px',
  },
  sideCard: {
    padding: '18px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  sideForm: {
    display: 'grid',
    gap: '10px',
  },
  smallTextarea: {
    minHeight: '100px',
    padding: '12px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'rgba(8, 15, 30, 0.76)',
    color: '#eceff4',
    resize: 'vertical',
  },
  contactList: {
    display: 'grid',
    gap: '10px',
  },
  contactItem: {
    padding: '12px 14px',
    borderRadius: '16px',
    background: 'rgba(8, 15, 30, 0.7)',
    border: '1px solid var(--line)',
  },
  contactName: {
    display: 'block',
    marginBottom: '6px',
  },
  contactMeta: {
    margin: 0,
    color: 'var(--muted)',
    fontSize: '13px',
    lineHeight: 1.5,
  },
  emptyState: {
    padding: '24px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
    color: 'var(--muted)',
  },
};
