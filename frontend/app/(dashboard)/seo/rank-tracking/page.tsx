'use client';

import { useMemo, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader } from '../../_ui/kit';
import styles from './rank-position-review.module.css';
import {
  MAX_RANK_IMPORT_CHARS,
  MAX_RANK_ROWS,
  parseRankCsv,
  type RankCsvError,
  type RankCsvResult,
  type RankPositionRow,
} from './rank-position-model';

type SortKey = 'keyword' | 'position' | 'checkedAt';
type SortState = { key: SortKey; descending: boolean };

const ERROR_COPY: Record<RankCsvError, string> = {
  empty: 'Choose a CSV file or paste its contents before reviewing.',
  'too-large': `This import exceeds the ${MAX_RANK_IMPORT_CHARS.toLocaleString()}-character limit. Split it into smaller files.`,
  'invalid-csv': 'The CSV quoting or row structure is invalid. Correct the file and try again.',
  'missing-keyword-column': 'The header row must include a Keyword column. No data was changed or uploaded.',
  'missing-position-column': 'The header row must include a Position or Rank column. No data was changed or uploaded.',
};

function compareNullableNumber(a: number | null, b: number | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return a - b;
}

function compareRows(a: RankPositionRow, b: RankPositionRow, key: SortKey): number {
  if (key === 'position') return compareNullableNumber(a.position, b.position);
  if (key === 'checkedAt') return (a.checkedAt ?? '').localeCompare(b.checkedAt ?? '');
  return a.keyword.localeCompare(b.keyword, undefined, { sensitivity: 'base' });
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

function getPositionLabel(row: RankPositionRow): string {
  if (row.positionState === 'invalid') return 'Unrecognized';
  if (row.position === null) return 'Not provided';
  return `#${row.position}`;
}

export default function RankPositionReviewPage() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [csvText, setCsvText] = useState('');
  const [fileName, setFileName] = useState('');
  const [source, setSource] = useState('');
  const [property, setProperty] = useState('');
  const [market, setMarket] = useState('');
  const [exportDate, setExportDate] = useState('');
  const [result, setResult] = useState<RankCsvResult | null>(null);
  const [searchText, setSearchText] = useState('');
  const [sort, setSort] = useState<SortState>({ key: 'keyword', descending: false });

  function updateCsv(value: string) {
    setCsvText(value);
    setFileName('');
    setResult(null);
    setSearchText('');
  }

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    setResult(null);
    setFileName(file.name.slice(0, 240));
    if (file.size > MAX_RANK_IMPORT_CHARS) {
      setCsvText('');
      setResult({ ok: false, reason: 'too-large' });
      return;
    }
    try {
      setCsvText(await file.text());
    } catch {
      setCsvText('');
      setResult({ ok: false, reason: 'invalid-csv' });
    }
  }

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult(parseRankCsv(csvText));
    setSearchText('');
  }

  function clearImport() {
    setCsvText('');
    setFileName('');
    setSource('');
    setProperty('');
    setMarket('');
    setExportDate('');
    setResult(null);
    setSearchText('');
    if (fileInput.current) fileInput.current.value = '';
  }

  function toggleSort(key: SortKey) {
    setSort((current) => ({ key, descending: current.key === key ? !current.descending : false }));
  }

  function sortHeader(key: SortKey, label: string) {
    const direction: 'ascending' | 'descending' | 'none' =
      sort.key === key ? (sort.descending ? 'descending' : 'ascending') : 'none';
    return (
      <th key={key} scope="col" aria-sort={direction}>
        <button type="button" className={styles.sortButton} onClick={() => toggleSort(key)}>
          {label}
          {direction !== 'none' ? (
            <span className={styles.sortMark} aria-hidden="true">{direction === 'descending' ? '↓' : '↑'}</span>
          ) : null}
        </button>
      </th>
    );
  }

  const parsed = result?.ok ? result : null;
  const filteredRows = useMemo(() => {
    if (!parsed) return [];
    const query = searchText.trim().toLocaleLowerCase();
    return parsed.rows
      .filter((row) => !query || row.keyword.toLocaleLowerCase().includes(query))
      .sort((a, b) => {
        const comparison = compareRows(a, b, sort.key);
        return sort.descending ? -comparison : comparison;
      });
  }, [parsed, searchText, sort]);
  const positions = parsed?.rows.flatMap((row) => (row.position === null ? [] : [row.position])) ?? [];
  const topTenCount = positions.filter((position) => position <= 10).length;
  const medianPosition = median(positions);

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Rank Position Review"
        subtitle="Review positions from an export you provide. No live tracking, provider connection, competitor surveillance, or forecast is performed."
        actions={<Badge tone="brand">Browser-local</Badge>}
      />

      <Card className={styles.localNotice}>
        <div className={styles.noticeRow}>
          <span className={styles.noticeIcon} aria-hidden="true">i</span>
          <p className={styles.noticeCopy}>
            <strong>Manual review only.</strong> Your CSV is parsed in this tab; it is not sent to a server, saved, or used to
            estimate missing positions. Imported values are not independently verified by Nuxtron.
          </p>
        </div>
      </Card>

      <Card>
        <CardTitle sub={`CSV only · UTF-8 text · up to 1 MB and ${MAX_RANK_ROWS.toLocaleString()} source rows. Keyword and Position/Rank headers are required.`}>
          Import an existing rank export
        </CardTitle>
        <form className={styles.form} onSubmit={handleReview}>
          <div className={styles.fileRow}>
            <div>
              <input
                ref={fileInput}
                id="rank-csv-file"
                className={styles.fileControl}
                type="file"
                accept=".csv,text/csv"
                aria-describedby="rank-file-help"
                onChange={(event) => void handleFile(event)}
              />
              <label className={styles.fileLabel} htmlFor="rank-csv-file">Choose CSV file</label>
            </div>
            <span className={styles.fileName} id="rank-file-help">
              {fileName || 'Or paste CSV text below. Nothing is uploaded.'}
            </span>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="rank-csv-text">Paste CSV contents</label>
            <textarea
              id="rank-csv-text"
              className={styles.textarea}
              value={csvText}
              maxLength={MAX_RANK_IMPORT_CHARS}
              onChange={(event) => updateCsv(event.target.value)}
              placeholder="keyword,position,checked_at,url,market"
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
            />
            <p className={styles.helper}>
              Supported position headers include position, rank, current position, and current rank. Date, URL, and market
              columns are optional and remain as provided.
            </p>
          </div>

          <fieldset className={styles.contextFieldset}>
            <legend className={styles.label}>Export context (optional)</legend>
            <div className={styles.contextGrid}>
              <Field id="rank-source" label="Source label" value={source} maxLength={120} onChange={(event) => setSource(event.target.value)} />
              <Field id="rank-property" label="Property / domain" value={property} maxLength={200} onChange={(event) => setProperty(event.target.value)} />
              <Field id="rank-market" label="Market / location" value={market} maxLength={120} onChange={(event) => setMarket(event.target.value)} />
              <Field id="rank-export-date" label="Export date" type="date" value={exportDate} onChange={(event) => setExportDate(event.target.value)} />
            </div>
          </fieldset>

          {result && !result.ok ? <p className={styles.error} role="alert">{ERROR_COPY[result.reason]}</p> : null}

          <div className={styles.actionRow}>
            <Button variant="primary" type="submit" disabled={!csvText.trim()}>Review imported positions</Button>
            <Button type="button" onClick={clearImport} disabled={!csvText && !fileName && !source && !property && !market && !exportDate}>
              Clear
            </Button>
            <span className={styles.helper} aria-live="polite">
              {csvText.length.toLocaleString()} / {MAX_RANK_IMPORT_CHARS.toLocaleString()} characters
            </span>
          </div>
        </form>
      </Card>

      {parsed ? (
        <Card>
          <div className={styles.resultsHeader}>
            <CardTitle sub="Positions and context are copied from your file. Summary counts are computed locally from numeric positions only.">
              Imported ranking rows
            </CardTitle>
            <Badge tone="neutral">Not provider-verified</Badge>
          </div>

          <p className={styles.resultStatus} role="status" aria-live="polite">
            {parsed.rows.length.toLocaleString()} source {parsed.rows.length === 1 ? 'row' : 'rows'} loaded locally.
          </p>
          <div className={styles.contextSummary}>
            <span>Source: {source.trim() || 'Not specified'}</span>
            <span>Property: {property.trim() || 'Not specified'}</span>
            <span>Market: {market.trim() || 'Not specified'}</span>
            <span>Export date: {exportDate || 'Not specified'}</span>
          </div>

          {parsed.rows.length === 0 ? (
            <p className={styles.emptyState} role="status">No rank rows were found in this export.</p>
          ) : (
            <>
              <div className={styles.metrics} aria-label="Local summary calculated from imported positions">
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Rows imported</span>
                  <span className={styles.metricValue}>{parsed.rows.length.toLocaleString()}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Positions provided</span>
                  <span className={styles.metricValue}>{positions.length.toLocaleString()} / {parsed.rows.length.toLocaleString()}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>In top 10</span>
                  <span className={styles.metricValue}>{positions.length ? topTenCount.toLocaleString() : 'Not provided'}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Median position</span>
                  <span className={styles.metricValue}>{medianPosition === null ? 'Not provided' : medianPosition.toFixed(1)}</span>
                </div>
              </div>

              {parsed.truncatedRows > 0 ? (
                <p className={styles.warning} role="status">
                  Only the first {MAX_RANK_ROWS.toLocaleString()} data rows were loaded. {parsed.truncatedRows.toLocaleString()} additional non-empty source rows were not read into the review.
                </p>
              ) : null}
              {parsed.skippedRows > 0 || parsed.invalidPositionCells > 0 ? (
                <p className={styles.warning}>
                  {parsed.skippedRows.toLocaleString()} loaded rows without a keyword were skipped; {parsed.invalidPositionCells.toLocaleString()} position cells were not recognized and remain unscored.
                </p>
              ) : null}

              <div className={styles.filterRow}>
                <Field
                  id="rank-filter"
                  label="Filter keywords"
                  className={styles.filterSearch}
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                />
              </div>

              {filteredRows.length > 0 ? (
                <div className={styles.tableScroller} role="region" aria-label="Imported rank-position table" tabIndex={0}>
                  <table className={styles.table}>
                    <caption className={styles.caption}>Source values only. Missing or unrecognized positions are never estimated.</caption>
                    <thead>
                      <tr>
                        {sortHeader('keyword', 'Keyword')}
                        {sortHeader('position', 'Position')}
                        {sortHeader('checkedAt', 'Checked date')}
                        <th scope="col">Market in file</th>
                        <th scope="col">URL in file</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.map((row) => (
                        <tr key={`${row.rowNumber}-${row.keyword}`}>
                          <td className={styles.keywordCell}>{row.keyword}</td>
                          <td className={styles.noWrap}>
                            <span className={row.positionState === 'present' ? undefined : styles.metricMissing}>{getPositionLabel(row)}</span>
                          </td>
                          <td className={styles.noWrap}>{row.checkedAt || <span className={styles.metricMissing}>Not provided</span>}</td>
                          <td>{row.market || market.trim() || <span className={styles.metricMissing}>Not provided</span>}</td>
                          <td className={styles.urlCell}>{row.url || <span className={styles.metricMissing}>Not provided</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className={styles.emptyState} role="status">No imported rows match this keyword filter.</p>
              )}
            </>
          )}
        </Card>
      ) : null}
    </Page>
  );
}
