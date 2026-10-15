'use client';

import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader, Stat, StatGrid } from '../../_ui/kit';
import { analyzeCrawlReview, crawlCandidatesCsv, type CrawlReview } from './crawl-review-model';
import styles from './crawl-budget.module.css';

export default function CrawlBudgetPage() {
  const [domain, setDomain] = useState('');
  const [sampleUrls, setSampleUrls] = useState('');
  const [logSnippet, setLogSnippet] = useState('');
  const [error, setError] = useState('');
  const [review, setReview] = useState<CrawlReview | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setReview(null);
    try {
      setReview(analyzeCrawlReview({ domain, sampleUrls, logSnippet }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not review these samples.');
    }
  }

  function exportCandidates() {
    if (!review || review.candidates.length === 0) return;
    const blob = new Blob([crawlCandidatesCsv(review.candidates)], { type: 'text/csv;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'crawl-review-candidates.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <Page>
      <PageHeader
        title="Crawl Budget Review"
        subtitle="Inspect URL patterns and access-log samples you provide. This page does not connect to your site or search-engine data."
      />

      <Card className={styles.scopeNotice}>
        <Badge tone="brand">Local sample review</Badge>
        <p>
          Your inputs are analyzed in this browser and are not sent to the Nuxtron API. Pattern matches are review candidates, not crawl-budget measurements or instructions to change robots.txt.
        </p>
      </Card>

      <Card>
        <CardTitle sub="Provide a website origin and at least one same-origin sample URL or supported access-log line. Nothing is prefilled.">
          Choose the evidence to inspect
        </CardTitle>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field} htmlFor="crawl-domain">
            <span>Website origin</span>
            <input
              id="crawl-domain"
              autoComplete="url"
              inputMode="url"
              placeholder="https://example.com"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              required
            />
            <small>Enter the root origin only. The review will reject sample URLs from other hosts.</small>
          </label>
          <div className={styles.inputGrid}>
            <label className={styles.field} htmlFor="crawl-sample-urls">
              <span>Sample URLs <em>Optional</em></span>
              <textarea
                id="crawl-sample-urls"
                rows={7}
                value={sampleUrls}
                onChange={(event) => setSampleUrls(event.target.value)}
                placeholder={'/pricing\n/blog/article\n/tag/topic'}
              />
              <small>Use one same-origin path or full URL per line. Up to 200 entries.</small>
            </label>
            <label className={styles.field} htmlFor="crawl-log-snippet">
              <span>Access-log excerpt <em>Optional</em></span>
              <textarea
                id="crawl-log-snippet"
                rows={7}
                className={styles.mono}
                value={logSnippet}
                onChange={(event) => setLogSnippet(event.target.value)}
                placeholder={'192.0.2.1 - - [12/Oct/2026:21:00:00 -0700] "GET /tag/topic HTTP/1.1" 404 123 "-" "ExampleBot/1.0"'}
              />
              <small>Common/Combined Log Format is parsed locally. User-agent strings are not verified.</small>
            </label>
          </div>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Review samples</Button>
        </form>
      </Card>

      {review && (
        <section aria-label="Crawl sample review results" className={styles.results}>
          <Card className={styles.resultHeader}>
            <div>
              <CardTitle sub={`Origin: ${review.origin}. Results reflect only the supplied sample.`}>Review summary</CardTitle>
            </div>
            <Button type="button" onClick={exportCandidates} disabled={review.candidates.length === 0}>
              Export candidate list
            </Button>
          </Card>

          <StatGrid>
            <Stat label="Unique sample URLs" value={review.sampleUrlCount} hint={`${review.duplicateSampleCount} duplicate entries removed`} />
            <Stat label="Pattern candidates" value={review.candidates.length} hint="Human review required" />
            <Stat label="Parsed log rows" value={review.parsedLogLineCount} hint={review.logLineCount ? `${review.unrecognizedLogLineCount} unrecognized` : 'No log excerpt supplied'} />
            <Stat label="4xx / 5xx in sample" value={`${review.clientErrorCount} / ${review.serverErrorCount}`} hint="Observed log responses only" />
          </StatGrid>

          {Object.keys(review.statusCounts).length > 0 && (
            <Card className={styles.statusCodes}>
              <CardTitle sub="Counts from parsed log rows; crawler identity is not verified.">Observed response codes</CardTitle>
              <ul>
                {Object.entries(review.statusCounts).map(([code, count]) => <li key={code}><strong>{code}</strong><span>{count} requests</span></li>)}
              </ul>
            </Card>
          )}

          <Card>
            <CardTitle sub="Pattern matches identify URLs worth a human look. They do not prove that a path wastes crawl budget.">
              URL patterns to review
            </CardTitle>
            {review.candidates.length === 0 ? (
              <p className={styles.empty}>No review patterns were found in the provided sample. This is not evidence that the full site has no crawl issues.</p>
            ) : (
              <div className={styles.candidateList}>
                {review.candidates.map((candidate) => (
                  <article className={styles.candidate} key={candidate.url}>
                    <code className={styles.url}>{candidate.url}</code>
                    <div className={styles.tags}>
                      {candidate.reasons.map((reason) => <Badge key={reason} tone="neutral">{reason}</Badge>)}
                    </div>
                    <p className={styles.evidence}>Observed in: {candidate.sources.join(' · ')}</p>
                    {candidate.requestCount > 0 && (
                      <p className={styles.evidence}>
                        Parsed requests: {candidate.requestCount}; response codes: {Object.entries(candidate.statusCounts).map(([code, count]) => `${code} × ${count}`).join(', ')}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            )}
          </Card>

          <p className={styles.limitNote}>
            This review does not estimate total crawl waste, discover unlisted URLs, connect to Search Console, verify bots, or modify site settings.
          </p>
        </section>
      )}
    </Page>
  );
}
