'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';
import AnalyticsExecutiveBoard from '@/app/components/analytics-executive-board';

type Json = Record<string, unknown>;

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

export default function DisputesDashboardPage() {
  // Bound to the authenticated session; not user-editable (A01/IDOR).
  const [tenantId] = useState(resolveSessionTenant);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState<Json>({});

  const summary = useMemo(() => {
    const raw = payload.summary;
    return typeof raw === 'object' && raw ? (raw as Json) : {};
  }, [payload]);

  const tickets = useMemo(() => (Array.isArray(payload.tickets) ? (payload.tickets as Json[]) : []), [payload]);
  const events = useMemo(
    () => (Array.isArray(payload.recent_dispute_events) ? (payload.recent_dispute_events as Json[]) : []),
    [payload]
  );

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const data = (await apiGet('/ira/disputes/dashboard', tenantId)) as Json;
      setPayload(data);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to load disputes dashboard.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  const totalTickets = asNumber(summary.total_dispute_tickets, 0);
  const openTickets = asNumber(summary.open_dispute_tickets, 0);
  const queuedHuman = asNumber(summary.queued_for_human_validation, 0);
  const openPct = totalTickets > 0 ? Math.round((openTickets / totalTickets) * 100) : 0;
  const queuePct = totalTickets > 0 ? Math.round((queuedHuman / totalTickets) * 100) : 0;
  const ticketStatusBars = useMemo(() => {
    const counts = new Map<string, number>();
    for (const ticket of tickets) {
      const status = asString(ticket.status, 'unknown') || 'unknown';
      counts.set(status, (counts.get(status) || 0) + 1);
    }
    return Array.from(counts.entries()).map(([label, value]) => ({ label, value }));
  }, [tickets]);
  const eventTrend = useMemo(() => {
    const sample = events.slice(-8);
    return sample.map((_, idx) => idx + 1);
  }, [events]);

  return (
    <main>
      <section className="hero dashboard-hero">
        <p className="eyebrow">Risk Operations</p>
        <h1>Disputes Dashboard</h1>
        <p>
          Live dispute oversight with strict human-approval controls, queue visibility, and reputation-safe handling
          guidance.
        </p>
      </section>

      <AnalyticsExecutiveBoard
        title="Disputes Analytics"
        subtitle="Operational dispute telemetry aligned to human-review safeguards and risk reduction goals."
        kpis={[
          { label: 'Total Tickets', value: String(totalTickets), delta: 'All queues', trend: 'flat' },
          {
            label: 'Open Cases',
            value: String(openTickets),
            delta: `${openPct}% open ratio`,
            trend: openPct > 40 ? 'down' : 'up',
          },
          {
            label: 'Human Validation',
            value: String(queuedHuman),
            delta: `${queuePct}% queued`,
            trend: queuePct > 25 ? 'down' : 'flat',
          },
          { label: 'Recent Events', value: String(events.length), delta: 'Operational stream', trend: 'flat' },
          {
            label: 'Reputation Guardrail',
            value: asString(payload.reputation_guardrail ? 'On' : 'Off', 'On'),
            delta: 'Policy controlled',
            trend: 'up',
          },
          { label: 'Tenant', value: tenantId.slice(0, 8), delta: 'Scoped dashboard', trend: 'flat' },
        ]}
        bars={ticketStatusBars}
        line={eventTrend}
        ring={[
          { label: 'Open', value: openTickets, color: '#ef4444' },
          { label: 'Queued', value: queuedHuman, color: '#f59e0b' },
          { label: 'Resolved', value: Math.max(0, totalTickets - openTickets), color: '#22c55e' },
          { label: 'Events', value: events.length, color: '#6366f1' },
        ]}
      />

      <section className="grid dashboard-kpis" style={{ marginTop: 18 }}>
        <article className="card kpi-card">
          <p className="kpi-label">Tenant</p>
          <h3>{tenantId.slice(0, 8)}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Total Disputes</p>
          <h3>{asNumber(summary.total_dispute_events, 0)}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Open Tickets</p>
          <h3>{openTickets}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Queued Human Review</p>
          <h3>{queuedHuman}</h3>
        </article>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Dispute Queue Health</h3>
        <div className="risk-bar-wrap">
          <p className="kpi-label">Open ratio: {openPct}%</p>
          <div className="risk-bar-track">
            <span className="risk-bar-fill" style={{ width: `${openPct}%` }} />
          </div>
        </div>
        <div className="risk-bar-wrap" style={{ marginTop: 10 }}>
          <p className="kpi-label">Human queue ratio: {queuePct}%</p>
          <div className="risk-bar-track">
            <span className="risk-bar-fill danger" style={{ width: `${queuePct}%` }} />
          </div>
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          {asString(payload.reputation_guardrail, 'Use transparent, fair, non-coercive dispute handling policies.')}
        </p>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Dispute Tickets</h3>
        <div className="table-scroll">
          <table className="ops-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Channel</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {tickets.length === 0 ? (
                <tr>
                  <td colSpan={6}>No dispute tickets found.</td>
                </tr>
              ) : (
                tickets.map((ticket) => (
                  <tr key={`ticket-${asNumber(ticket.id, 0)}-${asString(ticket.updated_at, '')}`}>
                    <td>{asNumber(ticket.id, 0)}</td>
                    <td>{asString(ticket.subject, '-')}</td>
                    <td>{asString(ticket.status, '-')}</td>
                    <td>{asString(ticket.priority, '-')}</td>
                    <td>{asString(ticket.channel, '-')}</td>
                    <td>{asString(ticket.updated_at, '-')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h3>Recent Dispute Events</h3>
        <div className="table-scroll">
          <table className="ops-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Event</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={3}>No recent dispute events.</td>
                </tr>
              ) : (
                events.map((event) => (
                  <tr key={`event-${asNumber(event.id, 0)}-${asString(event.created_at, '')}`}>
                    <td>{asNumber(event.id, 0)}</td>
                    <td>{asString(event.event_type, '-')}</td>
                    <td>{asString(event.created_at, '-')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="workspace-actions" style={{ marginTop: 18 }}>
        <button
          onClick={() => {
            void refresh();
          }}
          disabled={loading}
        >
          Refresh Dashboard
        </button>
      </section>

      {error ? (
        <section className="card" style={{ marginTop: 18 }}>
          <p className="auth-errors">{error}</p>
        </section>
      ) : null}
    </main>
  );
}
