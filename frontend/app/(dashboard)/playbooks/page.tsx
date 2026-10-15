'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader, TableWrap, tableClass } from '../_ui/kit';
import {
  filterPlaybooks,
  formatPlaybookDate,
  parsePlaybookCatalog,
  parsePlaybookRuns,
  playbookRunStatusLabel,
  type PlaybookDefinition,
  type PlaybookRun,
} from './playbooks-model';

type LoadState = 'loading' | 'ready' | 'error';

export default function PlaybooksPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [catalog, setCatalog] = useState<PlaybookDefinition[]>([]);
  const [runs, setRuns] = useState<PlaybookRun[]>([]);
  const [catalogState, setCatalogState] = useState<LoadState>('loading');
  const [runsState, setRunsState] = useState<LoadState>('loading');
  const [catalogError, setCatalogError] = useState('');
  const [runsError, setRunsError] = useState('');
  const [query, setQuery] = useState('');
  const [vertical, setVertical] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const hasWorkspace = Boolean(tenantId);

  const loadCatalog = useCallback(async () => {
    if (!tenantId) {
      setCatalogState('error');
      setCatalogError('Sign in to a workspace to load playbook definitions.');
      return;
    }
    setCatalogState('loading');
    setCatalogError('');
    try {
      const response = await apiGet<unknown>('/playbooks', tenantId);
      const parsed = parsePlaybookCatalog(response);
      if (!parsed) throw new Error('The playbook service returned an invalid catalog.');
      setCatalog(parsed);
      setCatalogState('ready');
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : 'Could not load playbook definitions.');
      setCatalogState('error');
    }
  }, [tenantId]);

  const loadRuns = useCallback(async () => {
    if (!tenantId) {
      setRunsState('error');
      setRunsError('Sign in to a workspace to load playbook history.');
      return;
    }
    setRunsState('loading');
    setRunsError('');
    try {
      const response = await apiGet<unknown>('/playbooks/runs/list', tenantId);
      const parsed = parsePlaybookRuns(response);
      if (!parsed) throw new Error('The playbook history service returned an invalid response.');
      setRuns(parsed);
      setRunsState('ready');
    } catch (error) {
      setRunsError(error instanceof Error ? error.message : 'Could not load playbook history.');
      setRunsState('error');
    }
  }, [tenantId]);

  useEffect(() => {
    const catalogTimer = window.setTimeout(() => void loadCatalog(), 0);
    const runsTimer = window.setTimeout(() => void loadRuns(), 0);
    return () => {
      window.clearTimeout(catalogTimer);
      window.clearTimeout(runsTimer);
    };
  }, [loadCatalog, loadRuns]);

  const verticals = useMemo(
    () => ['all', ...Array.from(new Set(catalog.map((item) => item.vertical.toLowerCase()).filter((value) => value !== 'all'))).sort()],
    [catalog],
  );
  const filtered = useMemo(() => filterPlaybooks(catalog, query, vertical), [catalog, query, vertical]);

  function refreshAll() {
    void loadCatalog();
    void loadRuns();
  }

  return (
    <Page>
      <PageHeader
        title="Integration Playbooks"
        subtitle="Browse plan templates and review their steps and integration requirements before adopting them."
        actions={<Button type="button" onClick={refreshAll} disabled={!hasWorkspace || catalogState === 'loading' || runsState === 'loading'}>Refresh</Button>}
      />

      <Card>
        <CardTitle>Execution status</CardTitle>
        <div role="note" style={{ marginTop: 12, border: '1px solid var(--line)', borderRadius: 10, padding: 14, color: 'var(--muted)' }}>
          This service currently stores playbook definitions and history records but has no step executor. Plan review below is informational only: it does not test integrations, schedule work, or activate automation. No ROI outcomes are measured here.
        </div>
      </Card>

      <Card>
        <CardTitle sub="Built-in entries are templates; workspace entries are saved definitions. These are plans, not measured performance.">Plan catalog</CardTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12, marginTop: 16 }}>
          <Field
            id="playbook-search"
            label="Search playbooks"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name, description, or integration"
            disabled={catalogState !== 'ready'}
          />
          <FieldSelect
            id="playbook-vertical"
            label="Category"
            value={vertical}
            onChange={(event) => setVertical(event.target.value)}
            disabled={catalogState !== 'ready'}
          >
            {verticals.map((value) => <option key={value} value={value}>{value === 'all' ? 'All categories' : value[0].toUpperCase() + value.slice(1)}</option>)}
          </FieldSelect>
        </div>
        {catalogState === 'loading' ? <p role="status">Loading playbook definitions…</p> : null}
        {catalogState === 'error' ? (
          <div role="alert" style={{ marginTop: 12, color: 'var(--danger)' }}>
            <p>{catalogError}</p>
            <Button type="button" onClick={() => void loadCatalog()} disabled={!hasWorkspace}>Retry catalog</Button>
          </div>
        ) : null}
        {catalogState === 'ready' ? (
          <>
            <p role="status" style={{ color: 'var(--muted)', marginTop: 14 }}>{filtered.length} matching {filtered.length === 1 ? 'plan' : 'plans'}</p>
            {catalog.length === 0 ? (
              <p style={{ color: 'var(--muted)' }}>No playbook definitions are available for this workspace.</p>
            ) : filtered.length === 0 ? (
              <p style={{ color: 'var(--muted)' }}>No playbooks match these search and category filters.</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 290px), 1fr))', gap: 14, marginTop: 14 }}>
                {filtered.map((playbook) => {
                  const isOpen = selectedId === playbook.id;
                  const detailId = `playbook-plan-${playbook.id.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
                  return (
                    <article key={playbook.id} style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 16, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                        <h3 style={{ margin: 0, fontSize: 17 }}>{playbook.name}</h3>
                        <Badge tone={playbook.builtIn ? 'brand' : 'neutral'}>{playbook.builtIn ? 'Built-in template' : 'Workspace plan'}</Badge>
                      </div>
                      <p style={{ color: 'var(--muted)', lineHeight: 1.5, margin: '10px 0' }}>{playbook.description || 'No description supplied.'}</p>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', color: 'var(--muted)', fontSize: 13 }}>
                        <span>Category: {playbook.vertical}</span>
                        {playbook.timeToValueDays !== null ? <span>Template setup estimate: {playbook.timeToValueDays} {playbook.timeToValueDays === 1 ? 'day' : 'days'}</span> : null}
                      </div>
                      <Button
                        type="button"
                        aria-expanded={isOpen}
                        aria-controls={detailId}
                        onClick={() => setSelectedId(isOpen ? null : playbook.id)}
                        style={{ marginTop: 14 }}
                      >
                        {isOpen ? 'Hide plan details' : 'Review plan'}
                      </Button>
                      {isOpen ? (
                        <section id={detailId} aria-label={`${playbook.name} plan details`} style={{ borderTop: '1px solid var(--line)', marginTop: 14, paddingTop: 14 }}>
                          <h4 style={{ margin: '0 0 8px' }}>Planned steps</h4>
                          {playbook.steps.length ? (
                            <ol style={{ paddingLeft: 22, margin: 0, display: 'grid', gap: 6 }}>
                              {playbook.steps.map((step, index) => <li key={`${playbook.id}-step-${index}`}>{step}</li>)}
                            </ol>
                          ) : <p style={{ color: 'var(--muted)' }}>No steps are defined.</p>}
                          <h4 style={{ margin: '14px 0 8px' }}>Integration requirements</h4>
                          {playbook.integrations.length ? (
                            <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: 0 }}>
                              {playbook.integrations.map((integration) => <li key={`${playbook.id}-${integration}`}><Badge>{integration}</Badge></li>)}
                            </ul>
                          ) : <p style={{ color: 'var(--muted)' }}>No integrations are specified.</p>}
                          <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 0 }}>This plan has not been validated against connected services and cannot be activated yet.</p>
                        </section>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            )}
          </>
        ) : null}
      </Card>

      <Card>
        <CardTitle sub="History may include preview records and older activation requests. A scheduled status does not mean steps ran.">Recent run records</CardTitle>
        {runsState === 'loading' ? <p role="status">Loading run history…</p> : null}
        {runsState === 'error' ? (
          <div role="alert" style={{ marginTop: 12, color: 'var(--danger)' }}>
            <p>{runsError}</p>
            <Button type="button" onClick={() => void loadRuns()} disabled={!hasWorkspace}>Retry history</Button>
          </div>
        ) : null}
        {runsState === 'ready' && runs.length === 0 ? <p style={{ color: 'var(--muted)', marginTop: 16 }}>No playbook run records are available for this workspace.</p> : null}
        {runsState === 'ready' && runs.length > 0 ? (
          <TableWrap>
            <table className={tableClass}>
              <caption className="sr-only">Playbook preview and activation request history</caption>
              <thead><tr><th scope="col">Playbook</th><th scope="col">Request type</th><th scope="col">Service status</th><th scope="col">Steps</th><th scope="col">Recorded</th></tr></thead>
              <tbody>
                {runs.slice(0, 100).map((run) => {
                  const progress = run.stepsCompleted === null || run.stepsTotal === null
                    ? 'Unavailable'
                    : `${run.stepsCompleted} of ${run.stepsTotal}`;
                  return (
                    <tr key={run.id}>
                      <th scope="row">{run.playbookName || 'Unnamed plan'}</th>
                      <td>{run.dryRun ? 'Preview record' : 'Activation request'}</td>
                      <td>{playbookRunStatusLabel(run)}</td>
                      <td>{progress}</td>
                      <td>{formatPlaybookDate(run.createdAt) ?? 'Date unavailable'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableWrap>
        ) : null}
      </Card>
    </Page>
  );
}
