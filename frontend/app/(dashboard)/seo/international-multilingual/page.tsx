'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';

import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import {
  reviewHreflangMarkup,
  type HreflangReview,
  type HreflangSeverity,
} from './international-review-model';
import styles from './international-review.module.css';

export default function InternationalMultilingualPage() {
  const [currentPageLocale, setCurrentPageLocale] = useState('');
  const [expectedLocales, setExpectedLocales] = useState('');
  const [canonicalUrl, setCanonicalUrl] = useState('');
  const [markup, setMarkup] = useState('');
  const [result, setResult] = useState<HreflangReview | null>(null);
  const [formError, setFormError] = useState('');

  function clearResult() {
    setResult(null);
    setFormError('');
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!markup.trim()) {
      setResult(null);
      setFormError('Paste the alternate link markup you want to inspect. Nothing is fetched automatically.');
      return;
    }
    setFormError('');
    setResult(reviewHreflangMarkup({ currentPageLocale, expectedLocales, canonicalUrl, markup }));
  }

  const issueCounts = result
    ? {
        errors: result.findings.filter((finding) => finding.severity === 'error').length,
        warnings: result.findings.filter((finding) => finding.severity === 'warning').length,
      }
    : null;

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Hreflang & Locale Review"
        subtitle="Check language tags, alternate links, and an optional locale list using only the markup you provide."
        actions={<Badge tone="brand">Browser-only review</Badge>}
      />

      <p className={styles.notice} role="note">
        <strong>No live-site audit:</strong> this page does not fetch URLs, inspect other locale pages, check reciprocal tags,
        or verify canonical elements. Your entries are analyzed in this tab and are not saved or sent to Nuxtron.
      </p>

      <Card className={styles.formCard}>
        <CardTitle
          sub="Paste a source page's link tags. Optional locale and canonical fields add checks against the values you enter."
        >
          Review supplied markup
        </CardTitle>

        <form onSubmit={handleSubmit} noValidate>
          <div className={styles.fieldsGrid}>
            <label className={styles.field} htmlFor="current-page-locale">
              <span id="current-page-locale-label">Current page locale <span className={styles.optional}>(optional)</span></span>
              <input
                id="current-page-locale"
                name="currentPageLocale"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                maxLength={80}
                value={currentPageLocale}
                onChange={(event) => {
                  setCurrentPageLocale(event.target.value);
                  clearResult();
                }}
                placeholder=""
                aria-describedby="current-locale-help"
                aria-labelledby="current-page-locale-label"
              />
              <span className={styles.fieldHelp} id="current-locale-help">
                Used only to check whether this tag is present in the pasted alternates.
              </span>
            </label>

            <label className={styles.field} htmlFor="expected-locales">
              <span id="expected-locales-label">Expected locales <span className={styles.optional}>(optional)</span></span>
              <textarea
                id="expected-locales"
                name="expectedLocales"
                rows={3}
                maxLength={1000}
                value={expectedLocales}
                onChange={(event) => {
                  setExpectedLocales(event.target.value);
                  clearResult();
                }}
                placeholder=""
                aria-describedby="expected-locales-help"
                aria-labelledby="expected-locales-label"
              />
              <span className={styles.fieldHelp} id="expected-locales-help">
                Enter language tags separated by commas or new lines. No locale list is prefilled.
              </span>
            </label>

            <label className={styles.field} htmlFor="canonical-url">
              <span id="canonical-url-label">Canonical URL <span className={styles.optional}>(optional)</span></span>
              <input
                id="canonical-url"
                name="canonicalUrl"
                type="url"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                maxLength={2048}
                value={canonicalUrl}
                onChange={(event) => {
                  setCanonicalUrl(event.target.value);
                  clearResult();
                }}
                placeholder=""
                aria-describedby="canonical-url-help"
                aria-labelledby="canonical-url-label"
              />
              <span className={styles.fieldHelp} id="canonical-url-help">
                Only URL syntax is checked; no canonical tag is retrieved or compared.
              </span>
            </label>
          </div>

          <label className={`${styles.field} ${styles.markupField}`} htmlFor="hreflang-markup">
            <span id="hreflang-markup-label">Hreflang link markup</span>
            <textarea
              id="hreflang-markup"
              name="markup"
              rows={9}
              maxLength={30000}
              value={markup}
              onChange={(event) => {
                setMarkup(event.target.value);
                clearResult();
              }}
              placeholder=""
              spellCheck={false}
              aria-invalid={formError ? true : undefined}
              aria-labelledby="hreflang-markup-label"
              aria-describedby="markup-help"
            />
            <span className={styles.fieldHelp} id="markup-help">
              Paste the actual <code>&lt;link rel=&quot;alternate&quot; hreflang=&quot;…&quot; href=&quot;…&quot;&gt;</code> lines you want checked.
              Markup is parsed as text and never inserted into the page.
            </span>
          </label>

          {formError ? (
            <p className={styles.formError} role="alert">
              {formError}
            </p>
          ) : null}

          <div className={styles.formActions}>
            <Button variant="primary" type="submit">Review supplied markup</Button>
            <span className={styles.actionHint}>No fetch, score, persistence, or generated locale targets.</span>
          </div>
        </form>
      </Card>

      {result ? (
        <section className={styles.resultSection} aria-labelledby="review-results-title">
          <div className={styles.resultHeader}>
            <div>
              <p className={styles.eyebrow}>Local review</p>
              <h2 id="review-results-title">Results for supplied markup</h2>
              <p className={styles.resultSummary} role="status" aria-live="polite">
                {result.alternateTagsFound} alternate {result.alternateTagsFound === 1 ? 'link' : 'links'} found in the supplied text.
                {issueCounts ? ` ${issueCounts.errors} ${issueCounts.errors === 1 ? 'error' : 'errors'} and ${issueCounts.warnings} ${issueCounts.warnings === 1 ? 'warning' : 'warnings'}.` : ''}
              </p>
            </div>
            <Badge tone={issueCounts?.errors ? 'danger' : issueCounts?.warnings ? 'neutral' : 'success'}>
              {issueCounts?.errors ? 'Review needed' : issueCounts?.warnings ? 'Check warnings' : 'No structural issues found'}
            </Badge>
          </div>

          {result.findings.length > 0 ? (
            <ul className={styles.findingList} aria-label="Review findings">
              {result.findings.map((finding) => (
                <FindingItem key={finding.code} severity={finding.severity} title={finding.title} detail={finding.detail} />
              ))}
            </ul>
          ) : (
            <p className={styles.cleanNote}>The supplied tags and optional checks passed this limited syntax and coverage review.</p>
          )}

          {result.entries.length > 0 ? (
            <div className={styles.entriesSection}>
              <h3>Alternate links inspected</h3>
              <ul className={styles.entryList}>
                {result.entries.map((entry) => (
                  <li className={styles.entry} key={entry.index}>
                    <div className={styles.entryHeader}>
                      <code className={styles.localeCode}>{entry.locale ?? entry.rawLocale}</code>
                      <span className={`${styles.entryStatus} ${styles[entry.status]}`}>
                        {entry.status === 'valid' ? 'Syntax valid' : entry.status === 'duplicate' ? 'Duplicate locale' : entry.status === 'unexpected' ? 'Not in expected list' : 'Check markup'}
                      </span>
                    </div>
                    <code className={styles.href}>{entry.hrefPreview}</code>
                    {entry.details.length > 0 ? (
                      <ul className={styles.entryDetails}>
                        {entry.details.map((detail) => <li key={detail}>{detail}</li>)}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <p className={styles.limitNote}>
            This is a markup-format and user-supplied locale comparison only. It cannot establish that target pages exist,
            return matching reciprocal tags, use aligned canonicals, or contain suitable translations. Query strings and fragments are hidden from displayed targets.
          </p>
        </section>
      ) : (
        <Card className={styles.emptyCard}>
          <CardTitle sub="No example data is loaded. Add your own source snippet above to begin.">
            Nothing reviewed yet
          </CardTitle>
          <p>Paste the alternate links you want to inspect. The page stays blank until you submit your own markup.</p>
        </Card>
      )}
    </Page>
  );
}

function FindingItem({
  severity,
  title,
  detail,
}: {
  severity: HreflangSeverity;
  title: string;
  detail: string;
}) {
  return (
    <li className={`${styles.finding} ${styles[`finding${severity[0]?.toUpperCase()}${severity.slice(1)}`]}`}>
      <strong>{title}</strong>
      <span>{detail}</span>
    </li>
  );
}
