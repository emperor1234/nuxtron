'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, DataStatus, Field, FieldSelect, Page, PageHeader, Stat, StatGrid, TableWrap, tableClass } from '../_ui/kit';
import { isDisputesPreviewResponse, parseDisputesDashboard, type DisputeTicket, type DisputesDashboard } from './disputes-model';
import styles from './disputes.module.css';

type TicketFilter = 'all' | 'open' | 'queued' | 'resolved';

function formatDate(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function matchesFilter(ticket: DisputeTicket, filter: TicketFilter): boolean {
  const status = ticket.status.toLowerCase();
  if (filter === 'open') return status === 'open';
  if (filter === 'queued') return status === 'queued_for_human_validation';
  if (filter === 'resolved') return ['resolved', 'closed', 'complete'].includes(status);
  return true;
}

export default function DisputesDashboardPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [data, setData] = useState<DisputesDashboard | null>(null);
  const [loading, setLoading] = useState(Boolean(tenantId));
  const [hasLoaded, setHasLoaded] = useState(false);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState(tenantId ? '' : 'Workspace context is required. Sign in or select a workspace to review disputes.');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<TicketFilter>('all');

  const refresh = useCallback(async () => {
    if (!tenantId) {
      setLoading(false);
      setError('Workspace context is required. Sign in or select a workspace to review disputes.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await apiGet<unknown>('/ira/disputes/dashboard', tenantId);
      const parsed = parseDisputesDashboard(response);
      setData(parsed);
      setPreview(isDisputesPreviewResponse(response));
      setHasLoaded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load dispute data.');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;
    let active = true;
    window.queueMicrotask(() => {
      if (active) void refresh();
    });
    return () => {
      active = false;
    };
  }, [refresh, tenantId]);

  const visibleTickets = useMemo(() => {
    if (!data) return [];
    const normalizedQuery = query.trim().toLowerCase();
    return data.tickets.filter((ticket) => {
      const matchesText = !normalizedQuery || `${ticket.id} ${ticket.subject} ${ticket.status} ${ticket.priority} ${ticket.channel}`.toLowerCase().includes(normalizedQuery);
      return matchesFilter(ticket, filter) && matchesText;
    });
  }, [data, filter, query]);

  const summary = data?.summary;
  const showUnavailable = Boolean(error && !hasLoaded);
  const dataStatus = preview ? 'preview' : showUnavailable ? 'unavailable' : 'live';

  return (
    <Page>
      <PageHeader
        title="Disputes"
        subtitle="Prioritize cases awaiting human review and inspect the workspace event history."
        actions={<Button onClick={() => void refresh()} disabled={loading || !tenantId}>{loading ? 'Refreshing…' : 'Refresh'}</Button>}
      />

      {loading ? <p role="status" aria-live="polite">Loading dispute cases…</p> : null}
      {!loading && !(error && hasLoaded) ? <DataStatus state={dataStatus} provider="disputes dashboard" /> : null}
      {error ? (
        <div role="alert" style={{ color: 'var(--danger)' }}>
          <p>{error}</p>
          {hasLoaded ? <p>Previously loaded results remain visible; the latest refresh failed.</p> : null}
          <Button onClick={() => void refresh()} disabled={loading || !tenantId}>Retry</Button>
        </div>
      ) : null}

      {data ? (
        <>
          <section aria-label="Dispute summary" aria-busy={loading}>
            <StatGrid>
              <Stat label="Queued for human review" value={summary?.queuedForHumanReview ?? '—'} hint="Cases requiring human validation" />
              <Stat label="Open cases" value={summary?.openTickets ?? '—'} hint="Open and queued cases" />
              <Stat label="Dispute tickets" value={summary?.totalTickets ?? '—'} hint="Workspace dispute queue" />
              <Stat label="Dispute events" value={summary?.totalEvents ?? '—'} hint="Recorded event count" />
            </StatGrid>
          </section>

          <div className={styles.queueNote} role="note">
            {summary?.humanApprovalRequired === true
              ? 'Human review is required before dispute decisions. This dashboard is read-only; it does not resolve, refund, or submit a dispute response.'
              : summary?.humanApprovalRequired === false
                ? 'The API reports no human-approval requirement. Confirm your organization’s policy before acting; this dashboard itself is read-only.'
                : 'Human-review policy is unavailable. Treat case decisions as requiring human review until your policy is confirmed.'}
          </div>

          {data.guardrail ? <p>{data.guardrail}</p> : null}

          <section className={styles.section} aria-label="Human review queue">
            <Card>
              <CardTitle sub="The service returns up to 50 dispute tickets for this workspace.">Human review queue</CardTitle>
              <div className={styles.filters} style={{ marginTop: 14 }}>
                <Field id="dispute-search" label="Search cases" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Case, status, priority, or channel" />
                <FieldSelect id="dispute-filter" label="Case status" value={filter} onChange={(event) => setFilter(event.target.value as TicketFilter)}>
                  <option value="all">All cases</option>
                  <option value="open">Open</option>
                  <option value="queued">Queued for human review</option>
                  <option value="resolved">Resolved or closed</option>
                </FieldSelect>
              </div>
            </Card>
            {loading ? <p role="status">Refreshing case list…</p> : null}
            {!loading && data.tickets.length === 0 && !error ? <Card><p>No dispute tickets are recorded for this workspace.</p></Card> : null}
            {!loading && data.tickets.length > 0 && visibleTickets.length === 0 ? <Card><p>No cases match the selected search and filter.</p></Card> : null}
            {!loading && visibleTickets.length > 0 ? (
              <TableWrap>
                <table className={tableClass}>
                  <caption>Dispute cases returned for the current workspace</caption>
                  <thead>
                    <tr>
                      <th scope="col">Case</th>
                      <th scope="col">Status</th>
                      <th scope="col">Priority</th>
                      <th scope="col">Channel</th>
                      <th scope="col">Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleTickets.map((ticket) => (
                      <tr key={ticket.id}>
                        <th scope="row">{ticket.subject} <span className={styles.eventLabel}>({ticket.id})</span></th>
                        <td><Badge tone={ticket.status.toLowerCase() === 'queued_for_human_validation' ? 'brand' : ticket.status.toLowerCase() === 'open' ? 'danger' : 'neutral'}>{ticket.status.replaceAll('_', ' ')}</Badge></td>
                        <td>{ticket.priority}</td>
                        <td>{ticket.channel}</td>
                        <td>{formatDate(ticket.updatedAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            ) : null}
          </section>

          <section className={styles.section} aria-label="Recent dispute events">
            <Card>
              <CardTitle sub="Event records are listed as returned; no synthetic trend line is inferred.">Recent dispute events</CardTitle>
            </Card>
            {!loading && data.events.length === 0 && !error ? <Card><p>No dispute events are recorded for this workspace.</p></Card> : null}
            {!loading && data.events.length > 0 ? (
              <TableWrap>
                <table className={tableClass}>
                  <caption>Dispute event history returned for the current workspace</caption>
                  <thead><tr><th scope="col">Event</th><th scope="col">Recorded</th></tr></thead>
                  <tbody>
                    {data.events.map((event) => (
                      <tr key={event.id}><th scope="row" className={styles.eventLabel}>{event.eventType} <span>({event.id})</span></th><td>{formatDate(event.createdAt)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            ) : null}
          </section>
        </>
      ) : null}
    </Page>
  );
}
