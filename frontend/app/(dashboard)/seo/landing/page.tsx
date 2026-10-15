'use client';

import { useState, type FormEvent } from 'react';
import { apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import { landingBriefMarkdown, parseLandingBrief, type LandingBrief } from './landing-brief-model';
import styles from './landing-brief.module.css';

const SCHEMA_OPTIONS = ['Product', 'FAQPage', 'Organization', 'Service', 'LocalBusiness'];

export default function LandingPageBriefPage() {
  const [productName, setProductName] = useState('');
  const [targetKeyword, setTargetKeyword] = useState('');
  const [audience, setAudience] = useState('');
  const [notes, setNotes] = useState('');
  const [schemaTypes, setSchemaTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [brief, setBrief] = useState<LandingBrief | null>(null);

  function toggleSchema(type: string) {
    setSchemaTypes((current) => current.includes(type) ? current.filter((item) => item !== type) : [...current, type]);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setBrief(null);
    if (!productName.trim() || !targetKeyword.trim() || !audience.trim() || schemaTypes.length === 0) {
      setError('Enter a product or brand, target keyword, audience, and at least one schema type.');
      return;
    }

    setLoading(true);
    try {
      const tenantId = resolveSessionTenant();
      if (!tenantId) throw new Error('Workspace context is required before generating a brief.');
      const response = await apiSend<unknown>(
        '/seo-platform/landing/generate',
        'POST',
        {
          product_name: productName.trim(),
          target_keyword: targetKeyword.trim(),
          audience: audience.trim(),
          schema_types: schemaTypes,
          notes: notes.trim(),
        },
        tenantId,
      );
      setBrief(parseLandingBrief(response));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Landing-page brief generation failed. Try again.');
    } finally {
      setLoading(false);
    }
  }

  function exportBrief() {
    if (!brief) return;
    const markdown = landingBriefMarkdown(brief, productName.trim(), targetKeyword.trim());
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'landing-page-brief.md';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  function listState(values: string[] | null, label: string) {
    if (values === null) return <p className={styles.missing}>{label} was not returned by the generation service.</p>;
    if (values.length === 0) return <p className={styles.missing}>The service returned no {label.toLowerCase()}.</p>;
    return <ul className={styles.contentList}>{values.map((value, index) => <li key={`${value}-${index}`}>{value}</li>)}</ul>;
  }

  const provenanceLabel = brief?.analysisMode === 'heuristic'
    ? 'Heuristic/template draft · not AI-generated'
    : brief?.analysisMode === 'llm'
      ? 'AI-generated draft · human review required'
      : 'Generation provenance unavailable · review cautiously';

  return (
    <Page>
      <PageHeader
        title="Landing Page Brief"
        subtitle="Generate a reviewable page outline and copy draft. This does not build, publish, or change a live page."
      />

      <Card className={styles.scopeNotice}>
        <Badge tone="brand">Draft workflow</Badge>
        <p>Review all generated claims and copy before use. Scores are not shown as performance evidence; this page does not crawl a website or measure conversions.</p>
      </Card>

      <Card>
        <CardTitle sub="Choose the brief context and schema types explicitly. Nothing is prefilled.">
          Describe the landing page
        </CardTitle>
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.inputGrid}>
            <label className={styles.field} htmlFor="landing-product">
              <span>Product or brand <b className={styles.required}>Required</b></span>
              <input id="landing-product" value={productName} maxLength={200} required onChange={(event) => setProductName(event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="landing-keyword">
              <span>Target keyword <b className={styles.required}>Required</b></span>
              <input id="landing-keyword" value={targetKeyword} maxLength={200} required onChange={(event) => setTargetKeyword(event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="landing-audience">
              <span>Target audience <b className={styles.required}>Required</b></span>
              <input id="landing-audience" value={audience} maxLength={200} required onChange={(event) => setAudience(event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="landing-notes">
              <span>Context and differentiators <em className={styles.optional}>Optional</em></span>
              <textarea id="landing-notes" rows={3} value={notes} maxLength={1000} onChange={(event) => setNotes(event.target.value)} />
              <small>Only include claims that are approved and supportable.</small>
            </label>
          </div>

          <fieldset className={styles.schemaOptions} aria-describedby="landing-schema-hint">
            <legend className={styles.legend}>Schema types <b className={styles.required}>Choose at least one</b></legend>
            <div className={styles.checks}>
              {SCHEMA_OPTIONS.map((type) => (
                <label className={styles.checkLabel} key={type}>
                  <input type="checkbox" checked={schemaTypes.includes(type)} onChange={() => toggleSchema(type)} />
                  <span>{type}</span>
                </label>
              ))}
            </div>
            <small id="landing-schema-hint">This creates a draft for review only. It is not validated or added to your website.</small>
          </fieldset>

          {error && <p className={styles.error} role="alert">{error}</p>}
          {loading && <p className={styles.loading} role="status">Generating a brief from the details you supplied…</p>}
          <Button type="submit" variant="primary" disabled={loading}>{loading ? 'Generating…' : 'Generate Landing Page Brief'}</Button>
        </form>
      </Card>

      {brief && (
        <section className={styles.results} aria-label="Generated landing page brief">
          <Card className={styles.resultHeader}>
            <div>
              <CardTitle sub={`${productName.trim()} · ${targetKeyword.trim()}`}>Landing page brief</CardTitle>
              <div className={styles.provenance}>
                <Badge tone={brief.analysisMode === 'llm' ? 'brand' : brief.analysisMode === 'heuristic' ? 'neutral' : 'danger'}>{provenanceLabel}</Badge>
                {brief.cached && <Badge tone="neutral">Cached response</Badge>}
              </div>
            </div>
            <Button type="button" onClick={exportBrief}>Export Markdown brief</Button>
          </Card>

          <Card>
            <CardTitle sub="Suggested copy only — this CTA does not navigate or submit a live form.">Hero draft</CardTitle>
            <h2 className={styles.heroHeadline}>{brief.hero.headline || 'No headline returned'}</h2>
            <p className={styles.heroSubheadline}>{brief.hero.subheadline || 'No supporting copy returned'}</p>
            <div className={styles.ctaCopy}>
              <small>Suggested CTA copy</small>
              <strong>{brief.hero.cta || 'No CTA copy returned'}</strong>
            </div>
          </Card>

          <Card>
            <CardTitle sub="Text returned by the generation service; canonical and metadata suggestions require review.">SEO metadata draft</CardTitle>
            <ul className={styles.metaList}>
              <li><span className={styles.metaLabel}>Title</span><span className={styles.metaValue}>{brief.seoMeta.title || 'Not returned'}</span></li>
              <li><span className={styles.metaLabel}>Description</span><span className={styles.metaValue}>{brief.seoMeta.description || 'Not returned'}</span></li>
              <li><span className={styles.metaLabel}>Canonical suggestion</span><code className={styles.metaValue}>{brief.seoMeta.canonical || 'Not returned'}</code></li>
            </ul>
          </Card>

          <Card>
            <CardTitle sub="The service can omit this field; omitted data is not represented as an empty list.">Page outline</CardTitle>
            {listState(brief.sections, 'Page outline')}
          </Card>

          <Card>
            <CardTitle sub="Questions and answers are drafts, not verified product facts.">FAQ draft</CardTitle>
            {brief.faqPairs === null ? <p className={styles.missing}>FAQ pairs were not returned by the generation service.</p> : brief.faqPairs.length === 0 ? <p className={styles.missing}>The service returned no FAQ pairs.</p> : (
              <div className={styles.faqList}>
                {brief.faqPairs.map((faq, index) => (
                  <article className={styles.faqItem} key={`${faq.question}-${index}`}>
                    <h3 className={styles.faqQuestion}>{faq.question}</h3>
                    <p className={styles.faqAnswer}>{faq.answer}</p>
                  </article>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <CardTitle sub="Alternative headline drafts; performance has not been tested.">Headline variants</CardTitle>
            {listState(brief.variants, 'Headline variants')}
          </Card>

          <Card>
            <CardTitle sub="These are suggested elements, not observed conversion signals or measured outcomes.">Suggested conversion elements</CardTitle>
            {listState(brief.conversionSignals, 'Suggested conversion elements')}
          </Card>

          <Card>
            <CardTitle sub="JSON-LD content is shown as escaped text and is not published or validated here.">Schema drafts</CardTitle>
            {brief.schemaMarkup === null ? <p className={styles.missing}>Schema markup was not returned by the generation service.</p> : brief.schemaMarkup.length === 0 ? <p className={styles.missing}>The service returned no schema drafts.</p> : (
              <div className={styles.schemaList}>
                {brief.schemaMarkup.map((schema, index) => (
                  <details className={styles.schemaItem} key={`${schema.type}-${index}`}>
                    <summary>{schema.type} JSON-LD draft</summary>
                    <pre>{JSON.stringify(schema.jsonLd, null, 2)}</pre>
                  </details>
                ))}
              </div>
            )}
          </Card>

          <p className={styles.limitNote}>Before publishing, verify factual, legal, brand, SEO, canonical, and structured-data requirements. No live page or website settings were changed.</p>
        </section>
      )}
    </Page>
  );
}
