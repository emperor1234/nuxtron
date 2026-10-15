'use client';

import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import { parseSecurityHeaderSample, securityHeaderReviewCsv, type SecurityHeaderReview } from './security-header-model';
import styles from './security-header.module.css';

export default function SecurityHeaderReviewPage() {
  const [sourceLabel, setSourceLabel] = useState('');
  const [sample, setSample] = useState('');
  const [review, setReview] = useState<SecurityHeaderReview | null>(null);
  const [error, setError] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setReview(null);
    try {
      setReview(parseSecurityHeaderSample(sample));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not review the supplied header block.');
    }
  }

  function exportCsv() {
    if (!review) return;
    const href = URL.createObjectURL(new Blob([securityHeaderReviewCsv(review)], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'security-header-review.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <Page>
      <PageHeader title="Security Header Review" subtitle="Inspect selected response-header values from a text sample you provide." />
      <Card>
        <Badge tone="neutral">Local review · no request sent</Badge>
        <p className={styles.scopeNotice}>Paste response headers copied from an authorized source. The sample is parsed in this browser; no URL is opened and no network request is made. A header marked “not found in sample” may simply be absent from the text you pasted. This is not a vulnerability scan, security certification, or full SEO audit.</p>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field} htmlFor="security-source-label">
            <span>Response source label or URL <em>(optional context only; it will not be fetched)</em></span>
            <input id="security-source-label" type="text" value={sourceLabel} maxLength={500} onChange={(event) => setSourceLabel(event.target.value)} />
          </label>
          <label className={styles.field} htmlFor="security-header-sample">
            <span>Response header block <b>Required</b></span>
            <textarea id="security-header-sample" value={sample} onChange={(event) => setSample(event.target.value)} rows={12} maxLength={128_000} required spellCheck={false} />
            <small>Paste lines in “Header-Name: value” form, up to 128 KB. HTTP status lines are ignored. Values are displayed as supplied and are not judged for policy suitability.</small>
          </label>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Review pasted headers</Button>
        </form>
      </Card>

      {review && (
        <section aria-label="Security header review results">
          <Card>
            <CardTitle sub={sourceLabel.trim() ? `Context label: ${sourceLabel.trim()}` : 'Evidence source: response-header text supplied by you'}>Observed header sample</CardTitle>
            <div className={styles.stats}>
              <div className={styles.stat}><span>Header lines parsed</span><output aria-label="Header lines parsed">{review.headerLinesCount}</output></div>
              <div className={styles.stat}><span>Unique header names</span><output aria-label="Unique header names">{review.uniqueHeaderNames}</output></div>
              <div className={styles.stat}><span>Unrecognized non-empty lines</span><output aria-label="Unrecognized lines">{review.ignoredLineCount}</output></div>
            </div>
            {review.headerLinesCount === 0 && <p className={styles.empty}>No valid header-name and value lines were found in the pasted block.</p>}
          </Card>
          <Card>
            <CardTitle sub="Presence is reported only in the submitted sample; a full-page result or security pass/fail is not inferred.">Header observations</CardTitle>
            <ul className={styles.checks}>
              {review.observations.map((item) => (
                <li className={styles.check} key={item.name}>
                  <div className={styles.checkTop}>
                    <h3 className={styles.checkName}>{item.name}</h3>
                    <Badge tone="neutral">{item.foundInSample ? 'Present in sample' : 'Not found in sample'}</Badge>
                  </div>
                  {item.value !== null && <code className={styles.value}>{item.value}</code>}
                </li>
              ))}
              <li className={styles.check}>
                <div className={styles.checkTop}>
                  <h3 className={styles.checkName}>CSP frame-ancestors directive</h3>
                  <Badge tone="neutral">{review.frameAncestorsInSample ? 'Found in sample' : 'Not found in sample'}</Badge>
                </div>
              </li>
            </ul>
            <p className={styles.empty}>HTTPS enforcement, HSTS effectiveness, policy correctness, mixed content, redirects, cloaking, spam, and application vulnerabilities are not assessed by this local text review.</p>
            <div className={styles.exportRow}>
              <p className={styles.scopeNotice}>CSV export contains only the parsed sample values and presence observations.</p>
              <Button type="button" onClick={exportCsv}>Export CSV</Button>
            </div>
          </Card>
        </section>
      )}
    </Page>
  );
}
