'use client';

import { useRef, useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader } from '@/app/(dashboard)/_ui/kit';
import { searchCorpus, type CorpusMatch, type CorpusSource } from './corpus-search-model';
import styles from './rag-search.module.css';

const MAX_SOURCES = 10;
const MAX_CONTENT_LENGTH = 12000;

function newSource(id: number): CorpusSource {
  return { id: `source-${id}`, label: '', url: '', content: '' };
}

export default function CorpusSearchPreviewPage() {
  const nextSourceId = useRef(2);
  const [query, setQuery] = useState('');
  const [sources, setSources] = useState<CorpusSource[]>([newSource(1)]);
  const [limit, setLimit] = useState(5);
  const [matches, setMatches] = useState<CorpusMatch[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  function updateQuery(value: string) {
    setQuery(value);
    setHasSearched(false);
    setMatches([]);
    setStatus('');
  }

  function updateSource(id: string, field: keyof Omit<CorpusSource, 'id'>, value: string) {
    setSources((current) => current.map((source) => (source.id === id ? { ...source, [field]: value } : source)));
    setHasSearched(false);
    setMatches([]);
    setStatus('');
  }

  function addSource() {
    if (sources.length >= MAX_SOURCES) return;
    setSources((current) => [...current, newSource(nextSourceId.current++)]);
    setHasSearched(false);
  }

  function removeSource(id: string) {
    setSources((current) => (current.length > 1 ? current.filter((source) => source.id !== id) : current));
    setHasSearched(false);
    setMatches([]);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const suppliedSources = sources.filter((source) => source.content.trim());
    if (suppliedSources.length === 0) {
      setHasSearched(false);
      setMatches([]);
      setError('Paste text into at least one source before searching.');
      return;
    }

    const result = searchCorpus(query, suppliedSources, limit);
    setMatches(result);
    setHasSearched(true);
    setStatus(
      result.length
        ? `Showing ${result.length} matching passage${result.length === 1 ? '' : 's'} from the text you supplied.`
        : 'No matching passages were found in the text you supplied.',
    );
  }

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Corpus Search Preview"
        subtitle="Preview keyword matches in text you provide. This local tool does not crawl a site, use a semantic index, or generate answers."
      />

      <Card className={styles.scopeCard}>
        <div className={styles.scopeHeader}>
          <Badge tone="brand">Browser-local</Badge>
          <h2>Search supplied sources</h2>
        </div>
        <p>
          Matching runs in this page using query-term overlap. Your query and pasted text are not sent to the Nuxtron search API or saved by this tool. Reloading the page clears them.
        </p>
        <p>A source URL is only shown as a link when it is a valid HTTP or HTTPS address.</p>
      </Card>

      <div className={styles.layout}>
        <Card className={styles.formCard}>
          <CardTitle sub="Results are exact passages from your supplied text, not live site search or semantic retrieval.">
            Preview matching passages
          </CardTitle>
          <form className={styles.form} onSubmit={handleSubmit}>
            <Field
              id="corpus-query"
              label="Search phrase"
              value={query}
              onChange={(event) => updateQuery(event.target.value)}
              maxLength={300}
              required
              placeholder="Enter a phrase to look for"
              autoComplete="off"
            />

            <div className={styles.limitField}>
              <label htmlFor="corpus-limit">Maximum passages</label>
              <select id="corpus-limit" value={limit} onChange={(event) => setLimit(Number(event.target.value))}>
                {[3, 5, 10, 20].map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </div>

            <div className={styles.sourcesHeader}>
              <div>
                <h3>Source text</h3>
                <p>Add up to {MAX_SOURCES} documents. Content stays in this browser page state.</p>
              </div>
              <Button type="button" variant="ghost" onClick={addSource} disabled={sources.length >= MAX_SOURCES}>
                Add source
              </Button>
            </div>

            <div className={styles.sources}>
              {sources.map((source, index) => (
                <fieldset className={styles.sourceCard} key={source.id}>
                  <legend>Source {index + 1}</legend>
                  <Field
                    id={`corpus-label-${source.id}`}
                    label="Source label (optional)"
                    value={source.label}
                    onChange={(event) => updateSource(source.id, 'label', event.target.value)}
                    maxLength={120}
                    placeholder="A short name for this source"
                  />
                  <Field
                    id={`corpus-url-${source.id}`}
                    label="Source URL (optional)"
                    value={source.url}
                    onChange={(event) => updateSource(source.id, 'url', event.target.value)}
                    maxLength={2000}
                    placeholder="https://…"
                    autoComplete="url"
                  />
                  <div className={styles.textareaField}>
                    <label htmlFor={`corpus-content-${source.id}`}>Pasted content</label>
                    <textarea
                      id={`corpus-content-${source.id}`}
                      value={source.content}
                      onChange={(event) => updateSource(source.id, 'content', event.target.value.slice(0, MAX_CONTENT_LENGTH))}
                      maxLength={MAX_CONTENT_LENGTH}
                      rows={6}
                      aria-describedby={`corpus-content-help-${source.id}`}
                      placeholder="Paste page text or an excerpt"
                    />
                    <p id={`corpus-content-help-${source.id}`} className={styles.hint}>
                      {source.content.length.toLocaleString()} / {MAX_CONTENT_LENGTH.toLocaleString()} characters. Blank lines separate passages.
                    </p>
                  </div>
                  {sources.length > 1 ? (
                    <Button type="button" variant="ghost" onClick={() => removeSource(source.id)}>
                      Remove source {index + 1}
                    </Button>
                  ) : null}
                </fieldset>
              ))}
            </div>

            <div className={styles.formFooter}>
              <p className={styles.hint}>No account data, site crawl, vector index, or external provider is queried.</p>
              <Button type="submit" variant="primary">Preview matches</Button>
            </div>
          </form>
        </Card>

        <Card className={styles.methodCard}>
          <CardTitle>What this preview does</CardTitle>
          <ul>
            <li>Splits supplied text at blank lines and compares query terms with each passage.</li>
            <li>Ranks passages by the number of distinct query terms they contain.</li>
            <li>Shows matched-term counts instead of confidence or relevance percentages.</li>
          </ul>
          <p>It does not fetch the URLs, verify that text is published, or infer site-wide coverage.</p>
        </Card>
      </div>

      <div className={styles.liveStatus} role="status" aria-live="polite" aria-atomic="true">{status}</div>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}

      {hasSearched ? (
        <section className={styles.results} aria-labelledby="corpus-results-title">
          <Card>
            <div className={styles.resultsHeader}>
              <div>
                <p className={styles.eyebrow}>Local keyword match</p>
                <h2 id="corpus-results-title">Matching passages</h2>
              </div>
              <Badge>{matches.length} shown · maximum {limit}</Badge>
            </div>
            {matches.length ? (
              <ol className={styles.matchList}>
                {matches.map((match) => (
                  <li key={match.id}>
                    <article className={styles.matchCard}>
                      <div className={styles.matchMeta}>
                        <strong>{match.sourceLabel}</strong>
                        <span>{match.matchedTerms.length} of {match.queryTermCount} query terms matched</span>
                      </div>
                      <blockquote>{match.excerpt}</blockquote>
                      {match.sourceUrl ? (
                        <a href={match.sourceUrl} target="_blank" rel="noreferrer" className={styles.sourceLink}>
                          Open supplied source
                        </a>
                      ) : (
                        <span className={styles.noSource}>No safe HTTP(S) source link supplied</span>
                      )}
                    </article>
                  </li>
                ))}
              </ol>
            ) : (
              <p className={styles.emptyResult}>No matching passages were found. Try another phrase or add text containing the terms you want to find.</p>
            )}
          </Card>
        </section>
      ) : null}
    </Page>
  );
}
