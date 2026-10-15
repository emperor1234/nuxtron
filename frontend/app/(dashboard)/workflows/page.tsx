'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, DataStatus, Field, FieldSelect, Page, PageHeader } from '../_ui/kit';
import { isWorkflowPreviewResponse, parseWorkflowList, type WorkflowDefinition, type WorkflowList } from './workflow-model';
import styles from './workflows.module.css';

type StatusFilter = 'all' | 'active' | 'paused';

function formatDate(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}

function matchesStatus(workflow: WorkflowDefinition, filter: StatusFilter): boolean {
  if (filter === 'all') return true;
  return workflow.status.toLowerCase() === filter;
}

export default function WorkflowsPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [data, setData] = useState<WorkflowList | null>(null);
  const [loading, setLoading] = useState(Boolean(tenantId));
  const [hasLoaded, setHasLoaded] = useState(false);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState(tenantId ? '' : 'Workspace context is required. Sign in or select a workspace to view workflow definitions.');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const refresh = useCallback(async () => {
    if (!tenantId) {
      setLoading(false);
      setError('Workspace context is required. Sign in or select a workspace to view workflow definitions.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await apiGet<unknown>('/workflows?limit=100', tenantId);
      setData(parseWorkflowList(response));
      setPreview(isWorkflowPreviewResponse(response));
      setHasLoaded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load workflow definitions.');
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

  const visibleWorkflows = useMemo(() => {
    if (!data) return [];
    const normalizedQuery = query.trim().toLowerCase();
    return data.workflows.filter((workflow) => {
      const matchesText = !normalizedQuery || `${workflow.name} ${workflow.description ?? ''} ${workflow.triggerType} ${workflow.status}`.toLowerCase().includes(normalizedQuery);
      return matchesText && matchesStatus(workflow, statusFilter);
    });
  }, [data, query, statusFilter]);

  const showUnavailable = Boolean(error && !hasLoaded);
  const definitionsStatus = preview ? 'preview' : showUnavailable ? 'unavailable' : 'live';

  return (
    <Page>
      <PageHeader
        title="Workflows"
        subtitle="Review automation definitions configured for this workspace."
        actions={<Button onClick={() => void refresh()} disabled={loading || !tenantId}>{loading ? 'Refreshing…' : 'Refresh definitions'}</Button>}
      />

      {loading ? <p role="status" aria-live="polite">Loading workflow definitions…</p> : null}
      {!loading && !(error && hasLoaded) ? <DataStatus state={definitionsStatus} provider="workflow definitions" /> : null}
      {error ? (
        <div role="alert" className={styles.error}>
          <p>{error}</p>
          {hasLoaded ? <p>Previously loaded definitions remain visible; the latest refresh failed.</p> : null}
          <Button onClick={() => void refresh()} disabled={loading || !tenantId}>Retry</Button>
        </div>
      ) : null}

      <section className={styles.notice} aria-label="Workflow execution availability" role="note">
        <h2>Execution is not available</h2>
        <p>The current workflow service records simulated “completed” steps; it does not perform configured actions such as sending email, updating contact properties, creating tickets, or calling external systems. To avoid implying work was done when it was not, workflow creation, activation, enrollment, and execution history are disabled here.</p>
        <p>Do not rely on an “active” status reported by the service to trigger customer-facing or operational actions.</p>
      </section>

      <section className={styles.section} aria-label="Workflow definitions">
        <Card>
          <CardTitle sub="Read-only until the service can execute and verify real actions.">Workspace definitions</CardTitle>
          <div className={styles.filters}>
            <Field id="workflow-search" label="Search definitions" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, description, trigger, status" />
            <FieldSelect id="workflow-status" label="Service-reported status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
              <option value="all">All statuses</option>
              <option value="active">Reported enabled</option>
              <option value="paused">Reported paused</option>
            </FieldSelect>
          </div>
        </Card>

        {loading ? <p role="status">Refreshing definitions…</p> : null}
        {!loading && data?.workflows.length === 0 && !error ? <Card><p>No workflow definitions were returned for this workspace.</p></Card> : null}
        {!loading && data && data.workflows.length > 0 && visibleWorkflows.length === 0 ? <Card><p>No definitions match the current search and status filter.</p></Card> : null}
        {!loading && visibleWorkflows.length > 0 ? (
          <div className={styles.list}>
            {visibleWorkflows.map((workflow) => (
              <article className={styles.item} key={workflow.id}>
                <div className={styles.itemHeader}>
                  <div className={styles.itemText}>
                    <h3>{workflow.name}</h3>
                    {workflow.description ? <p>{workflow.description}</p> : null}
                  </div>
                  <Badge tone="neutral">{workflow.status.toLowerCase() === 'active' ? 'Reported enabled' : workflow.status.toLowerCase() === 'paused' ? 'Reported paused' : workflow.status}</Badge>
                </div>
                <dl className={styles.metadata}>
                  <div><dt>Trigger</dt><dd>{workflow.triggerType.replaceAll('_', ' ')}</dd></div>
                  <div><dt>Steps configured</dt><dd>{workflow.stepCount ?? 'Unavailable'}</dd></div>
                  <div><dt>Updated</dt><dd>{formatDate(workflow.updatedAt)}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </Page>
  );
}
