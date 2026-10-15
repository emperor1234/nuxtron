'use client';

import { useMemo, useRef, useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import { aiSurfaceLabel, createSearchObservation, SEARCH_SOURCES, searchObservationsCsv, summarizeObservationTrends, AI_SURFACES, type SearchObservation } from './observation-log-model';
import styles from './observation-log.module.css';

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toLocaleString() : 'Invalid observation time';
}

function trendLabel(change: number | null): string {
  if (change === null) return 'Trend unavailable — two dated rank observations are needed';
  if (change > 0) return `Improved ${change} ${change === 1 ? 'position' : 'positions'}`;
  if (change < 0) return `Declined ${Math.abs(change)} ${Math.abs(change) === 1 ? 'position' : 'positions'}`;
  return 'No position change';
}

export default function SearchObservationLogPage() {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [observedAtLocal, setObservedAtLocal] = useState('');
  const [position, setPosition] = useState('');
  const [aiSurface, setAiSurface] = useState('');
  const [observations, setObservations] = useState<SearchObservation[]>([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const nextId = useRef(1);

  const trends = useMemo(() => summarizeObservationTrends(observations), [observations]);
  const visibleObservations = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return [...observations]
      .sort((left, right) => Date.parse(right.observedAt) - Date.parse(left.observedAt))
      .filter((observation) => !needle || observation.query.toLowerCase().includes(needle) || observation.source.toLowerCase().includes(needle));
  }, [observations, search]);
  const querySourceCount = trends.length;
  const rankedCount = observations.filter((observation) => observation.position !== null).length;
  const checkedAiCount = observations.filter((observation) => observation.aiSurface !== 'not-checked').length;

  function addObservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    try {
      const observation = createSearchObservation({ query, source, observedAtLocal, position, aiSurface }, `observation-${nextId.current++}`);
      setObservations((current) => [...current, observation]);
      setAnnouncement(`Recorded observation for ${observation.query}.`);
      setQuery('');
      setSource('');
      setObservedAtLocal('');
      setPosition('');
      setAiSurface('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not record this observation.');
    }
  }

  function removeObservation(observation: SearchObservation) {
    setObservations((current) => current.filter((item) => item.id !== observation.id));
    setAnnouncement(`Removed observation for ${observation.query}.`);
  }

  function exportCsv() {
    if (observations.length === 0) return;
    const href = URL.createObjectURL(new Blob([searchObservationsCsv(observations)], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'search-observation-log.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <Page>
      <PageHeader title="Search Observation Log" subtitle="Record manually verified search results and compare dated observations for the same query and source." />

      <Card>
        <Badge tone="neutral">Manual observations · session only</Badge>
        <p className={styles.scopeNotice}>This is not live monitoring. No search provider, AI answer engine, or website is queried, and this log is not saved to your workspace. Trend summaries use only the dated rank entries you provide. Export CSV to keep a copy.</p>
        <form className={styles.form} onSubmit={addObservation}>
          <div className={styles.fields}>
            <label className={styles.field} htmlFor="observation-query">
              <span>Search query <b className={styles.required}>Required</b></span>
              <input id="observation-query" value={query} maxLength={300} onChange={(event) => setQuery(event.target.value)} required />
            </label>
            <label className={styles.field} htmlFor="observation-source">
              <span>Search source <b className={styles.required}>Required</b></span>
              <select id="observation-source" value={source} onChange={(event) => setSource(event.target.value)} required>
                <option value="">Choose a source…</option>
                {SEARCH_SOURCES.map((item) => <option value={item} key={item}>{item}</option>)}
              </select>
            </label>
            <label className={styles.field} htmlFor="observation-time">
              <span>Observed at <b className={styles.required}>Required</b></span>
              <input id="observation-time" type="datetime-local" value={observedAtLocal} onChange={(event) => setObservedAtLocal(event.target.value)} required />
            </label>
            <label className={styles.field} htmlFor="observation-position">
              <span>Rank position <span>(optional)</span></span>
              <input id="observation-position" type="number" min={1} max={1000} step="any" value={position} onChange={(event) => setPosition(event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="observation-ai-surface">
              <span>AI answer observation <b className={styles.required}>Required</b></span>
              <select id="observation-ai-surface" value={aiSurface} onChange={(event) => setAiSurface(event.target.value)} required>
                <option value="">Choose a status…</option>
                {AI_SURFACES.map((surface) => <option value={surface} key={surface}>{aiSurfaceLabel(surface)}</option>)}
              </select>
            </label>
          </div>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Record observation</Button>
        </form>
      </Card>

      <p className={styles.status} role="status" aria-live="polite">{announcement}</p>

      <Card>
        <CardTitle sub="Counts apply only to this in-memory session log; empty counts do not describe live search coverage.">Observation summary</CardTitle>
        <div className={styles.metrics}>
          <div className={styles.metric}><span>Observations logged</span><output aria-label="Observations logged">{observations.length}</output></div>
          <div className={styles.metric}><span>Query/source pairs</span><output aria-label="Query and source pairs">{querySourceCount}</output></div>
          <div className={styles.metric}><span>Rank entries provided</span><output aria-label="Rank entries provided">{rankedCount}</output></div>
          <div className={styles.metric}><span>AI answer checks recorded</span><output aria-label="AI answer checks recorded">{checkedAiCount}</output></div>
        </div>
      </Card>

      <Card>
        <CardTitle sub="A positive change means the rank number moved closer to 1. A trend appears only when both latest and previous records include ranks.">Query/source trends</CardTitle>
        {trends.length === 0 ? <p className={styles.empty}>No observations yet. Add a dated record after you verify a search result.</p> : (
          <ul className={styles.trends}>
            {trends.map((trend) => (
              <li className={styles.trend} key={trend.key}>
                <div className={styles.trendHead}>
                  <h3 className={styles.query}>{trend.query}</h3>
                  <Badge tone="neutral">{trend.source} · {trend.observationCount} {trend.observationCount === 1 ? 'record' : 'records'}</Badge>
                </div>
                <div className={styles.facts}>
                  <span>Latest rank: {trend.latest.position === null ? 'not provided' : trend.latest.position}</span>
                  <span>{trendLabel(trend.positionsImprovedBy)}</span>
                  <span>Latest observation: {formatDate(trend.latest.observedAt)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <div className={styles.logHeader}>
          <CardTitle sub="Newest observations first. AI-surface state is the value selected by the reviewer, not an engine scan.">Observation history</CardTitle>
          <label className={styles.filter} htmlFor="observation-search">
            <span>Filter by query or source</span>
            <input id="observation-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
        </div>
        {observations.length === 0 ? <p className={styles.empty}>The session log is empty. Recorded observations will appear here.</p> : visibleObservations.length === 0 ? <p className={styles.empty}>No observations match this filter.</p> : (
          <ul className={styles.observationList}>
            {visibleObservations.map((observation) => (
              <li className={styles.observation} key={observation.id}>
                <div className={styles.observationHead}>
                  <h3 className={styles.query}>{observation.query}</h3>
                  <Button className={styles.removeButton} type="button" aria-label={`Remove observation for ${observation.query}`} onClick={() => removeObservation(observation)}>Remove</Button>
                </div>
                <div className={styles.facts}>
                  <span>{observation.source}</span>
                  <span>{formatDate(observation.observedAt)}</span>
                  <span>Rank: {observation.position === null ? 'not provided' : observation.position}</span>
                  <span>{aiSurfaceLabel(observation.aiSurface)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
        {observations.length > 0 && <div className={styles.exportRow}><p className={styles.scopeNotice}>CSV export is generated in your browser from these manually entered records.</p><Button type="button" onClick={exportCsv}>Export CSV</Button></div>}
      </Card>
    </Page>
  );
}
