'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Badge, Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader } from '../../_ui/kit';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import {
  describeSavedResult,
  formatModuleLabel,
  formatRedactedJson,
  parseSeoHistoryResponse,
  type SeoHistoryRecord,
} from './history-model';
import styles from './history.module.css';

function formatDate(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return 'Date unavailable';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(timestamp);
}

function describeHistoryError(cause: unknown): string {
  if (cause instanceof Error && /workspace context is required/i.test(cause.message)) {
    return 'A signed-in workspace is required. Sign in or select a workspace, then retry.';
  }
  return 'The history service could not complete this request. Retry; if the problem persists, contact your workspace owner.';
}

export default function SEOHistoryPage() {
  const requestSequence = useRef(0);
  const [moduleFilter, setModuleFilter] = useState('');
  const [search, setSearch] = useState('');
  const [records, setRecords] = useState<SeoHistoryRecord[]>([]);
  const recordsWorkspaceId = useRef('');
  const [total, setTotal] = useState(0);
  const [persistence, setPersistence] = useState<'postgres' | 'memory' | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState('');

  const loadAnalyses = useCallback(async (currentFilter: string) => {
    const currentRequest = ++requestSequence.current;
    setLoading(true);
    setError('');

    try {
      const workspaceId = resolveSessionTenant();
      if (!workspaceId) {
        recordsWorkspaceId.current = '';
        setRecords([]);
        setTotal(0);
        setPersistence(null);
        setSelectedId(null);
        throw new Error('Workspace context is required.');
      }

      // Never leave data from the prior workspace visible while switching scope.
      if (recordsWorkspaceId.current && recordsWorkspaceId.current !== workspaceId) {
        setRecords([]);
        setTotal(0);
        setPersistence(null);
        setSelectedId(null);
        recordsWorkspaceId.current = '';
      }

      const query = currentFilter
        ? `?module=${encodeURIComponent(currentFilter)}&limit=100`
        : '?limit=100';
      const response = await apiGet<unknown>(`/seo-platform/analyses${query}`, workspaceId, { cache: false });
      const parsed = parseSeoHistoryResponse(response);
      if (!parsed) throw new Error('The history service returned an invalid response.');
      if (currentRequest !== requestSequence.current) return;

      setRecords(parsed.analyses);
      recordsWorkspaceId.current = workspaceId;
      setTotal(parsed.total);
      setPersistence(parsed.persistence);
      setUpdatedAt(new Date().toISOString());
      setSelectedId((current) =>
        parsed.analyses.some((record) => record.id === current) ? current : parsed.analyses[0]?.id ?? null,
      );
    } catch (cause) {
      if (currentRequest === requestSequence.current) setError(describeHistoryError(cause));
    } finally {
      if (currentRequest === requestSequence.current) {
        setHasLoaded(true);
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let active = true;
    window.queueMicrotask(() => {
      if (active) void loadAnalyses(moduleFilter);
    });
    return () => {
      active = false;
      requestSequence.current += 1;
    };
  }, [loadAnalyses, moduleFilter]);

  const modules = useMemo(() => {
    const available = new Set(records.map((record) => record.module));
    if (moduleFilter) available.add(moduleFilter);
    return [...available].sort();
  }, [moduleFilter, records]);
  const visibleRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return records;
    return records.filter((record) => `${record.module} ${record.id}`.toLowerCase().includes(query));
  }, [records, search]);
  const selected = records.find((record) => record.id === selectedId) ?? null;

  return (
    <Page>
      <PageHeader
        title="SEO Analysis History"
        subtitle="Find and inspect saved SEO analysis inputs and outputs for this workspace."
        actions={
          <Button onClick={() => void loadAnalyses(moduleFilter)} disabled={loading} variant="primary">
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        }
      />

      {persistence === 'memory' ? (
        <div className={`${styles.notice} ${styles.noticeWarning}`} role="note">
          <strong>Temporary storage.</strong> These records are currently held in process memory and may be lost when the service restarts. They are not durable history.
        </div>
      ) : null}
      {persistence === 'postgres' ? (
        <div className={styles.notice} role="status">Saved history is stored in PostgreSQL for this workspace.</div>
      ) : null}

      <Card className={styles.toolbar}>
        <FieldSelect
          id="analysis-module-filter"
          label="Module"
          value={moduleFilter}
          onChange={(event) => setModuleFilter(event.target.value)}
          disabled={loading && !hasLoaded}
        >
          <option value="">All modules</option>
          {modules.map((module) => <option key={module} value={module}>{formatModuleLabel(module)}</option>)}
        </FieldSelect>
        <Field
          id="analysis-history-search"
          label="Search current results"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Module or record ID"
        />
        <span className={styles.count}>
          {loading && !hasLoaded ? 'Loading…' : `${total} records returned · request limit 100`}
        </span>
        <span className={styles.updated}>{updatedAt ? `Last refreshed ${formatDate(updatedAt)}` : 'Not refreshed yet'}</span>
      </Card>

      {error ? (
        <div className={`${styles.notice} ${styles.noticeWarning}`} role="alert">
          <strong>History could not be refreshed.</strong> {error}{records.length ? ' Previously loaded records remain visible and may not match the current filter.' : ''}
        </div>
      ) : null}
      {loading && hasLoaded ? <p className={styles.statusMessage} role="status">Refreshing history; previously loaded records remain available.</p> : null}

      <div className={styles.layout}>
        <Card className={styles.panel}>
          <div className={styles.panelHeader}>
            <CardTitle sub="Select a saved record to inspect its provenance and output.">Saved analyses</CardTitle>
            {persistence ? <Badge tone={persistence === 'postgres' ? 'success' : 'neutral'}>{persistence === 'postgres' ? 'Durable' : 'Temporary'}</Badge> : null}
          </div>
          {!hasLoaded && loading ? (
            <p className={styles.statusMessage} role="status">Loading saved analyses…</p>
          ) : records.length === 0 ? (
            <p className={styles.statusMessage} role="status">
              {error ? 'No history is available because the request failed.' : moduleFilter ? 'No saved analyses exist for this module.' : 'No saved SEO analyses yet in this workspace.'}
            </p>
          ) : visibleRecords.length === 0 ? (
            <p className={styles.statusMessage} role="status">No records match this search.</p>
          ) : (
            <ul className={styles.recordList} aria-label="Saved SEO analyses">
              {visibleRecords.map((record) => (
                <li key={record.id}>
                  <Button
                    className={styles.recordButton}
                    aria-pressed={selectedId === record.id}
                    onClick={() => setSelectedId(record.id)}
                  >
                    <strong>{formatModuleLabel(record.module)}</strong>
                    <span className={styles.recordMeta}><span>Record {record.id.slice(0, 8)}</span><span>{formatDate(record.createdAt)}</span></span>
                    <span className={styles.recordSummary}>{describeSavedResult(record)}</span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className={styles.panel}>
          <CardTitle sub="Historical outputs are records of earlier runs, not live provider measurements.">Analysis details</CardTitle>
          {!selected ? (
            <p className={styles.statusMessage}>Select a record from the history list to inspect its saved details.</p>
          ) : (
            <>
              <div className={styles.detailMeta}>
                <span><strong>Module:</strong> {formatModuleLabel(selected.module)}</span>
                <span><strong>Created:</strong> {formatDate(selected.createdAt)}</span>
                <span><strong>Record:</strong> {selected.id.slice(0, 8)}</span>
              </div>
              <p className={styles.resultSummary}>
                This archived record contains {describeSavedResult(selected)}. Review the redacted values below; historical outputs may reflect earlier heuristic or unavailable product behavior.
              </p>
              <details className={styles.disclosure}>
                <summary>Show redacted input and output JSON</summary>
                <p className={styles.sensitiveNote}>
                  Fields with keys resembling workspace identifiers, credentials, tokens, or contact details are redacted. Free-text values may still contain sensitive content; inspect before copying or sharing.
                </p>
                <div className={styles.rawGroup}>
                  <h3>Input</h3>
                  <pre className={styles.rawJson}>{formatRedactedJson(selected.payload)}</pre>
                </div>
                <div className={styles.rawGroup}>
                  <h3>Output</h3>
                  <pre className={styles.rawJson}>{formatRedactedJson(selected.result)}</pre>
                </div>
              </details>
            </>
          )}
        </Card>
      </div>
    </Page>
  );
}
