'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type InboxMessage = {
  id: number;
  network: string;
  source_type: string;
  author_handle: string;
  text: string;
  message_type: string;
  sentiment: string;
  priority_score: number;
  status: string;
};
type InboxStats = {
  total_messages: number;
  unread_messages: number;
  by_status: Record<string, number>;
  by_sentiment: Record<string, number>;
};

export default function SmartInboxPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [network, setNetwork] = useState('linkedin');
  const [sourceType, setSourceType] = useState('dm');
  const [author, setAuthor] = useState('@prospect');
  const [text, setText] = useState('Can your platform automate ad + social workflows?');
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const [statsRes, messagesRes] = await Promise.all([
        apiGet<InboxStats & { status: string }>('/inbox/stats', tenantId),
        apiGet<{ messages: InboxMessage[] }>('/inbox/messages', tenantId),
      ]);
      setStats(statsRes);
      setMessages(messagesRes.messages ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load inbox');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ingestMessage() {
    try {
      await apiSend(
        '/inbox/messages',
        'POST',
        {
          network,
          source_type: sourceType,
          author_handle: author,
          text,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ingest failed');
    }
  }

  async function setStatus(messageId: number, status: string) {
    try {
      await apiSend(`/inbox/messages/${messageId}`, 'PATCH', { status }, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Smart Inbox</h1>
        <p style={{ color: 'var(--muted)' }}>
          Inbound messages with AI classification, sentiment, and team workflow status.
        </p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
            gap: 10,
            marginBottom: 10,
          }}
        >
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Total Messages</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{stats?.total_messages ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Unread</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{stats?.unread_messages ?? 0}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Ingest Message</h3>
            <select style={input} value={network} onChange={(e) => setNetwork(e.target.value)}>
              <option value="linkedin">linkedin</option>
              <option value="x">x</option>
              <option value="instagram">instagram</option>
              <option value="facebook">facebook</option>
              <option value="youtube">youtube</option>
              <option value="reddit">reddit</option>
            </select>
            <select style={input} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
              <option value="dm">dm</option>
              <option value="comment">comment</option>
              <option value="mention">mention</option>
              <option value="review">review</option>
            </select>
            <input
              style={input}
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="author handle"
            />
            <textarea style={{ ...input, minHeight: 90 }} value={text} onChange={(e) => setText(e.target.value)} />
            <button
              onClick={() => void ingestMessage()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Ingest
            </button>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Inbox Messages ({messages.length})</h3>
            {messages.map((m) => (
              <div key={m.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {m.author_handle} on {m.network}
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {m.source_type} · {m.message_type} · {m.sentiment} · priority {m.priority_score}
                    </div>
                    <div style={{ fontSize: 13 }}>{m.text}</div>
                  </div>
                  <div>
                    <select
                      value={m.status}
                      onChange={(e) => void setStatus(m.id, e.target.value)}
                      style={{ ...input, marginBottom: 0, width: 140 }}
                    >
                      <option value="pending">pending</option>
                      <option value="in_progress">in_progress</option>
                      <option value="complete">complete</option>
                      <option value="flagged">flagged</option>
                      <option value="requires_approval">requires_approval</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </section>
        </div>
      </div>
    </main>
  );
}
