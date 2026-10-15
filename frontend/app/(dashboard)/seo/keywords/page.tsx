'use client';

import { useState, type ChangeEvent, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, FieldSelect, Page, PageHeader } from '../../_ui/kit';
import styles from './keyword-data-review.module.css';
import {
  MAX_KEYWORD_IMPORT_CHARS,
  MAX_KEYWORD_ROWS,
  parseKeywordCsv,
  type KeywordCsvError,
  type KeywordCsvResult,
  type KeywordDataRow,
} from './keyword-data-model';

type SortKey = 'keyword' | 'volume' | 'difficulty' | 'intent';
type SortState = { key: SortKey; descending: boolean };

const ERROR_COPY: Record<KeywordCsvError, string> = {
  empty: 'Choose a CSV file or paste its contents before reviewing.',
  'too-large': `This import exceeds the ${MAX_KEYWORD_IMPORT_CHARS.toLocaleString()}-character limit. Split it into smaller files.`,
  'invalid-csv': 'The CSV quoting or row structure is invalid. Correct the file and try again.',
  'missing-keyword-column': 'The header row must include a Keyword column. No data was changed or uploaded.',
};

function compareNullable(a: number | null, b: number | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return a - b;
}

function formatMetric(value: number | null, state: KeywordDataRow['volumeState']): string {
  if (state === 'invalid') return 'Unrecognized';
  if (value === null) return 'Not provided';
  return value.toLocaleString();
}

function compareRows(a: KeywordDataRow, b: KeywordDataRow, key: SortKey): number {
  if (key === 'volume') return compareNullable(a.volume, b.volume);
  if (key === 'difficulty') return compareNullable(a.difficulty, b.difficulty);
  if (key === 'intent') return (a.intent ?? '').localeCompare(b.intent ?? '');
  return a.keyword.localeCompare(b.keyword, undefined, { sensitivity: 'base' });
}

function getSortLabel(state: SortState, key: SortKey): string {
  if (state.key !== key) return '';
  return state.descending ? 'descending' : 'ascending';
}

export default function KeywordsPage() {
  const [csvText, setCsvText] = useState('');
  const [fileName, setFileName] = useState('');
  const [source, setSource] = useState('');
  const [market, setMarket] = useState('');
  const [exportDate, setExportDate] = useState('');
  const [result, setResult] = useState<KeywordCsvResult | null>(null);
  const [searchText, setSearchText] = useState('');
  const [intentFilter, setIntentFilter] = useState('');
  const [sort, setSort] = useState<SortState>({ key: 'keyword', descending: false });

  function updateCsv(value: string) {
    setCsvText(value);
    setFileName('');
    setResult(null);
    setSearchText('');
    setIntentFilter('');
  }

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    setResult(null);
    setFileName(file.name.slice(0, 240));
    if (file.size > MAX_KEYWORD_IMPORT_CHARS) {
      setCsvText('');
      setResult({ ok: false, reason: 'too-large' });
      return;
    }
    try {
      updateCsv(await file.text());
      setFileName(file.name.slice(0, 240));
    } catch {
      setCsvText('');
      setResult({ ok: false, reason: 'invalid-csv' });
    }
  }

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = parseKeywordCsv(csvText);
    setResult(parsed);
    setSearchText('');
    setIntentFilter('');
  }

  function clearImport() {
    setCsvText('');
    setFileName('');
    setSource('');
    setMarket('');
    setExportDate('');
    setResult(null);
    setSearchText('');
    setIntentFilter('');
  }

  function toggleSort(key: SortKey) {
    setSort((current) => ({
      key,
      descending: current.key === key ? !current.descending : false,
    }));
  }

  const parsed = result?.ok ? result : null;
  const intentOptions = parsed
    ? Array.from(new Set(parsed.rows.map((row) => row.intent).filter((intent): intent is string => Boolean(intent))))
        .sort((a, b) => a.localeCompare(b))
        .slice(0, 50)
    : [];
  const filteredRows = parsed
    ? parsed.rows
        .filter((row) => row.keyword.toLocaleLowerCase().includes(searchText.trim().toLocaleLowerCase()))
        .filter((row) => !intentFilter || row.intent === intentFilter)
        .sort((a, b) => {
          const comparison = compareRows(a, b, sort.key);
          return sort.descending ? -comparison : comparison;
        })
    : [];
  const volumeCount = parsed?.rows.filter((row) => row.volumeState === 'present').length ?? 0;
  const difficultyCount = parsed?.rows.filter((row) => row.difficultyState === 'present').length ?? 0;

  function header(key: SortKey, label: string) {
    const direction = getSortLabel(sort, key);
    const ariaSort = direction ? (sort.descending ? 'descending' : 'ascending') : 'none';
    return (
      <th key={key} scope="col" aria-sort={ariaSort}>
        <button type="button" className={styles.sortButton} onClick={() => toggleSort(key)}>
          {label}
          {direction ? <span className={styles.sortMark} aria-hidden="true">{sort.descending ? '↓' : '↑'}</span> : null}
        </button>
      </th>
    );
  }

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Keyword Data Review"
        subtitle="Review a keyword export you provide. Search volume, difficulty and intent are shown only when they exist in your file."
        actions={<Badge tone="brand">Browser-local</Badge>}
      />

      <Card className={styles.localNotice}>
        <div className={styles.noticeRow}>
          <span className={styles.noticeIcon} aria-hidden="true">i</span>
          <p className={styles.noticeCopy}>
            <strong>No connected keyword data source.</strong> Nuxtron does not fetch or estimate search volume, rankings,
            intent, competitor gaps or opportunity scores here. Your import is parsed in this tab only; it is not sent to a
            server, saved, or used to generate new keywords.
          </p>
        </div>
      </Card>

      <Card>
        <CardTitle
          sub="CSV only · UTF-8 text · up to 1 MB and 2,000 keyword rows. A Keyword column is required."
        >
          Import an existing export
        </CardTitle>
        <form className={styles.form} onSubmit={handleReview}>
          <div className={styles.fileRow}>
            <div>
              <input
                id="keyword-csv-file"
                className={styles.fileControl}
                type="file"
                accept=".csv,text/csv"
                aria-describedby="keyword-file-help"
                onChange={(event) => void handleFile(event)}
              />
              <label className={styles.fileLabel} htmlFor="keyword-csv-file">Choose CSV file</label>
            </div>
            <span className={styles.fileName} id="keyword-file-help">
              {fileName || 'Or paste CSV text below. Nothing is uploaded.'}
            </span>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="keyword-csv-text">Paste CSV contents</label>
            <textarea
              id="keyword-csv-text"
              className={styles.textarea}
              value={csvText}
              maxLength={MAX_KEYWORD_IMPORT_CHARS}
              onChange={(event) => updateCsv(event.target.value)}
              placeholder="keyword,search volume,difficulty,intent"
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
            />
            <p className={styles.helper}>
              Supported optional headers: search volume/monthly searches, keyword difficulty/KD, and intent. Unrecognized
              metric cells stay unscored; no zero is substituted.
            </p>
          </div>

          <fieldset className={styles.contextFieldset}>
            <legend className={styles.label}>Export context (optional)</legend>
            <div className={styles.contextGrid}>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="keyword-source">Source label</label>
                <input id="keyword-source" className={styles.input} value={source} maxLength={120} onChange={(event) => setSource(event.target.value)} />
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="keyword-market">Market / location</label>
                <input id="keyword-market" className={styles.input} value={market} maxLength={120} onChange={(event) => setMarket(event.target.value)} />
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="keyword-export-date">Export date</label>
                <input id="keyword-export-date" className={styles.input} type="date" value={exportDate} onChange={(event) => setExportDate(event.target.value)} />
              </div>
            </div>
          </fieldset>

          {result && !result.ok ? <p className={styles.error} role="alert">{ERROR_COPY[result.reason]}</p> : null}

          <div className={styles.actionRow}>
            <Button variant="primary" type="submit" disabled={!csvText.trim()}>
              Review imported data
            </Button>
            <Button type="button" onClick={clearImport} disabled={!csvText && !fileName && !source && !market && !exportDate}>
              Clear
            </Button>
            <span className={styles.helper} aria-live="polite">
              {csvText.length.toLocaleString()} / {MAX_KEYWORD_IMPORT_CHARS.toLocaleString()} characters
            </span>
          </div>
        </form>
      </Card>

      {parsed ? (
        <Card>
          <div className={styles.resultsHeader}>
            <div>
              <CardTitle sub="Values are copied from the imported file; Nuxtron has not independently verified them.">
                Imported keyword rows
              </CardTitle>
            </div>
            <Badge tone="neutral">Not provider-verified</Badge>
          </div>

          <p className={styles.resultStatus} role="status" aria-live="polite">
            {parsed.rows.length.toLocaleString()} keyword {parsed.rows.length === 1 ? 'row' : 'rows'} available locally.
          </p>
          <div className={styles.contextSummary}>
            <span>Source: {source.trim() || 'Not specified'}</span>
            <span>Market: {market.trim() || 'Not specified'}</span>
            <span>Export date: {exportDate || 'Not specified'}</span>
          </div>

          {parsed.rows.length > 0 ? (
            <>
              <div className={styles.metrics} aria-label="Imported data completeness">
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Keyword rows</span>
                  <span className={styles.metricValue}>{parsed.rows.length.toLocaleString()}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Rows with volume</span>
                  <span className={styles.metricValue}>{volumeCount.toLocaleString()} / {parsed.rows.length.toLocaleString()}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Rows with difficulty</span>
                  <span className={styles.metricValue}>{difficultyCount.toLocaleString()} / {parsed.rows.length.toLocaleString()}</span>
                </div>
              </div>

              {parsed.truncatedRows > 0 ? (
                <p className={styles.warning} role="status">
                  Showing the first {MAX_KEYWORD_ROWS.toLocaleString()} keyword rows. {parsed.truncatedRows.toLocaleString()} additional rows were not loaded.
                </p>
              ) : null}
              {parsed.skippedRows > 0 || parsed.invalidMetricCells > 0 ? (
                <p className={styles.warning}>
                  {parsed.skippedRows.toLocaleString()} rows without a keyword were skipped; {parsed.invalidMetricCells.toLocaleString()} numeric cells were not recognized and remain blank.
                </p>
              ) : null}

              <div className={styles.filterRow}>
                <div className={`${styles.field} ${styles.filterSearch}`}>
                  <label className={styles.label} htmlFor="keyword-filter">Filter keywords</label>
                  <input id="keyword-filter" className={styles.input} value={searchText} onChange={(event) => setSearchText(event.target.value)} />
                </div>
                <FieldSelect
                  id="keyword-intent-filter"
                  label="Filter by imported intent"
                  className={styles.input}
                  value={intentFilter}
                  onChange={(event) => setIntentFilter(event.target.value)}
                >
                  <option value="">All imported intents</option>
                  {intentOptions.map((intent) => <option key={intent} value={intent}>{intent}</option>)}
                </FieldSelect>
              </div>

              {filteredRows.length > 0 ? (
                <div className={styles.tableScroller} role="region" aria-label="Imported keyword data table" tabIndex={0}>
                  <table className={styles.table}>
                    <caption className={styles.caption}>Source values only. “Not provided” and “Unrecognized” are not estimated.</caption>
                    <thead>
                      <tr>
                        {header('keyword', 'Keyword')}
                        {header('volume', 'Search volume')}
                        {header('difficulty', 'Difficulty')}
                        {header('intent', 'Intent')}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.map((row) => (
                        <tr key={`${row.rowNumber}-${row.keyword}`}>
                          <td className={styles.keywordCell}>{row.keyword}</td>
                          <td className={styles.noWrap}>
                            <span className={row.volumeState === 'present' ? undefined : styles.metricMissing}>
                              {formatMetric(row.volume, row.volumeState)}
                            </span>
                          </td>
                          <td className={styles.noWrap}>
                            <span className={row.difficultyState === 'present' ? undefined : styles.metricMissing}>
                              {formatMetric(row.difficulty, row.difficultyState)}
                            </span>
                          </td>
                          <td>{row.intent || <span className={styles.metricMissing}>Not provided</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className={styles.emptyState} role="status">No keyword rows match the current filters.</p>
              )}
            </>
          ) : (
            <p className={styles.emptyState} role="status">
              No keyword rows were found in this export. Add rows beneath the Keyword header and review again.
            </p>
          )}
        </Card>
      ) : null}
    </Page>
  );
}
