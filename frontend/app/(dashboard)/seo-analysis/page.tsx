'use client';

import Link from 'next/link';
import { useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader } from '../_ui/kit';
import {
  buildSeoAnalysisPayload,
  parseSeoAnalysisResult,
  type SeoAnalysisChecks,
  type SeoAnalysisDraft,
  type SeoAnalysisFieldErrors,
  type SeoAnalysisResult,
} from './seo-analysis-model';

type CheckKey = keyof SeoAnalysisChecks;

const CHECKS: Array<{ key: CheckKey; label: string }> = [
  { key: 'hasUrl', label: 'Reference URL supplied' },
  { key: 'keywordPresent', label: 'Target keyword appears in the copy' },
  { key: 'goodLength', label: 'Copy length is 300–2,000 words' },
  { key: 'balancedDensity', label: 'Keyword density is 0.5%–2.5%' },
];

const EMPTY_DRAFT: SeoAnalysisDraft = { url: '', targetKeyword: '', content: '' };

export default function SeoAnalysisPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [draft, setDraft] = useState<SeoAnalysisDraft>({ ...EMPTY_DRAFT });
  const [fieldErrors, setFieldErrors] = useState<SeoAnalysisFieldErrors>({});
  const [serviceError, setServiceError] = useState('');
  const [result, setResult] = useState<SeoAnalysisResult | null>(null);
  const [requestState, setRequestState] = useState<'idle' | 'loading' | 'error' | 'success'>('idle');
  const hasWorkspace = Boolean(tenantId);

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServiceError('');
    setResult(null);
    const validation = buildSeoAnalysisPayload(draft);
    setFieldErrors(validation.errors);
    if (!validation.payload) {
      setRequestState('idle');
      return;
    }
    if (!tenantId) {
      setServiceError('Sign in to a workspace before running a content check.');
      setRequestState('error');
      return;
    }

    setRequestState('loading');
    try {
      const response = await apiSend<unknown>('/seo/analyze', 'POST', validation.payload, tenantId);
      const parsed = parseSeoAnalysisResult(response);
      if (!parsed) throw new Error('The analysis service returned an invalid result. Please retry.');
      setResult(parsed);
      setRequestState('success');
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : 'The content check could not be completed.');
      setRequestState('error');
    }
  }

  function updateDraft(next: Partial<SeoAnalysisDraft>) {
    setDraft((current) => ({ ...current, ...next }));
    setFieldErrors((current) => {
      const updated = { ...current };
      for (const key of Object.keys(next) as Array<keyof SeoAnalysisDraft>) delete updated[key];
      return updated;
    });
  }

  return (
    <Page>
      <PageHeader
        title="SEO Content Check"
        subtitle="A fast, rule-based check of supplied copy against one target keyword."
      />

      <Card>
        <CardTitle>What this check does—and does not do</CardTitle>
        <div role="note" style={{ color: 'var(--muted)', marginTop: 12, lineHeight: 1.55 }}>
          This is a deterministic content check, not an AI analysis, ranking prediction, or live page audit. It counts case-insensitive keyword substrings, checks copy length and a simple keyword-density range, and records whether you supplied a reference URL. The URL is not fetched; canonical tags, search results, and technical page signals are not inspected.
          {' '}For a broader page audit, see <Link href="/seo/on-page">On-Page Optimizer</Link>.
        </div>
      </Card>

      <Card>
        <CardTitle sub="Your copy is sent only when you submit. The reference URL is optional and is used as a presence check only.">Analysis brief</CardTitle>
        <form noValidate onSubmit={(event) => void runAnalysis(event)} style={{ display: 'grid', gap: 14, marginTop: 16 }}>
          <div>
            <Field
              id="seo-analysis-url"
              type="url"
              label="Reference page URL (optional; not fetched)"
              value={draft.url}
              onChange={(event) => updateDraft({ url: event.target.value })}
              maxLength={2048}
              aria-invalid={Boolean(fieldErrors.url)}
              aria-describedby={fieldErrors.url ? 'seo-analysis-url-error' : 'seo-analysis-url-help'}
              disabled={!hasWorkspace || requestState === 'loading'}
            />
            <p id={fieldErrors.url ? 'seo-analysis-url-error' : 'seo-analysis-url-help'} style={{ color: fieldErrors.url ? 'var(--danger)' : 'var(--muted)', fontSize: 13, margin: '4px 0 0' }}>
              {fieldErrors.url ?? 'Optional context for the report; this service does not open or crawl it.'}
            </p>
          </div>
          <div>
            <Field
              id="seo-analysis-keyword"
              label="Target keyword"
              value={draft.targetKeyword}
              onChange={(event) => updateDraft({ targetKeyword: event.target.value })}
              required
              minLength={2}
              maxLength={120}
              aria-invalid={Boolean(fieldErrors.targetKeyword)}
              aria-describedby={fieldErrors.targetKeyword ? 'seo-analysis-keyword-error' : undefined}
              disabled={!hasWorkspace || requestState === 'loading'}
            />
            {fieldErrors.targetKeyword ? <p id="seo-analysis-keyword-error" style={{ color: 'var(--danger)', fontSize: 13, margin: '4px 0 0' }}>{fieldErrors.targetKeyword}</p> : null}
          </div>
          <div>
            <label htmlFor="seo-analysis-content" style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Page copy</label>
            <textarea
              id="seo-analysis-content"
              value={draft.content}
              onChange={(event) => updateDraft({ content: event.target.value })}
              minLength={20}
              maxLength={10000}
              required
              aria-invalid={Boolean(fieldErrors.content)}
              aria-describedby={fieldErrors.content ? 'seo-analysis-content-error seo-analysis-content-count' : 'seo-analysis-content-count'}
              disabled={!hasWorkspace || requestState === 'loading'}
              style={{ width: '100%', minHeight: 220, resize: 'vertical', border: '1px solid var(--line)', borderRadius: 10, padding: 12, background: 'var(--bg)', color: 'var(--text)', font: 'inherit', lineHeight: 1.5 }}
            />
            {fieldErrors.content ? <p id="seo-analysis-content-error" style={{ color: 'var(--danger)', fontSize: 13, margin: '4px 0 0' }}>{fieldErrors.content}</p> : null}
            <p id="seo-analysis-content-count" style={{ color: 'var(--muted)', fontSize: 13, margin: '4px 0 0' }}>{draft.content.length.toLocaleString()} / 10,000 characters · minimum 20</p>
          </div>
          {!hasWorkspace ? <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>Sign in to a workspace before running a content check.</p> : null}
          {serviceError ? <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{serviceError}</p> : null}
          {requestState === 'loading' ? <p role="status" style={{ margin: 0 }}>Checking the supplied copy…</p> : null}
          <div>
            <Button type="submit" variant="primary" disabled={!hasWorkspace || requestState === 'loading'}>
              {requestState === 'loading' ? 'Checking…' : requestState === 'error' ? 'Retry content check' : 'Run content check'}
            </Button>
          </div>
        </form>
      </Card>

      {result ? (
        <Card>
          <CardTitle sub="A simple rule score—not a search ranking, traffic forecast, or complete SEO health score.">Result</CardTitle>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
            <strong style={{ fontSize: 24 }}>{result.score}/100</strong>
            <span style={{ color: 'var(--muted)' }}>four-check heuristic score</span>
          </div>
          <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 165px), 1fr))', gap: 12, margin: '16px 0' }}>
            <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Words</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{result.wordCount.toLocaleString()}</dd></div>
            <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Keyword occurrences*</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{result.keywordCount.toLocaleString()}</dd></div>
            <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Keyword density</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{result.keywordDensityPercent.toLocaleString(undefined, { maximumFractionDigits: 2 })}%</dd></div>
          </dl>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>*Occurrences are case-insensitive substring matches, not whole-word or search-volume data.</p>
          <h3>Checks</h3>
          <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 8 }}>
            {CHECKS.map(({ key, label }) => (
              <li key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <span>{label}</span>
                <Badge tone={result.checks[key] ? 'success' : 'danger'}>{result.checks[key] ? 'Passed' : 'Needs attention'}</Badge>
              </li>
            ))}
          </ul>
          <h3>Recommendations</h3>
          {result.recommendations.length > 0 ? (
            <ul>{result.recommendations.map((recommendation, index) => <li key={`${index}-${recommendation}`}>{recommendation}</li>)}</ul>
          ) : <p>No recommendations were returned by this rule set.</p>}
          <details style={{ marginTop: 16 }}>
            <summary>Show normalized service response</summary>
            <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', padding: 12, borderRadius: 8, background: 'var(--bg-soft)', color: 'var(--muted)' }}>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </Card>
      ) : requestState === 'success' ? (
        <Card><CardTitle>Result</CardTitle><p>No result fields were returned.</p></Card>
      ) : requestState === 'idle' ? (
        <p role="status" style={{ color: 'var(--muted)' }}>Add a keyword and at least 20 characters of page copy to receive the rule-check report.</p>
      ) : null}
    </Page>
  );
}
