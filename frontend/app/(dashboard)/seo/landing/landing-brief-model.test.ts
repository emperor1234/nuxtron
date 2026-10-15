import { describe, expect, it } from 'vitest';
import { landingBriefMarkdown, parseLandingBrief } from './landing-brief-model';

const response = {
  analysis_id: 'analysis-1',
  analysis_mode: 'heuristic',
  cached: false,
  hero: { headline: 'Headline', subheadline: 'Subheadline', cta: 'Request a demo' },
  sections: ['Problem', 'Approach', 'Proof'],
  seo_meta: { title: 'Page title', description: 'Description', canonical: '/draft' },
  faq_pairs: [{ question: 'Who is it for?', answer: 'The audience provided.' }],
  ab_test_variants: ['Alternative headline'],
  schema_markup: [{ type: 'Product', json_ld: { '@type': 'Product', name: 'Product' } }],
  conversion_signals: ['Trust evidence'],
};

describe('parseLandingBrief', () => {
  it('parses a truthful heuristic draft without using its unmeasured score', () => {
    const result = parseLandingBrief({ ...response, landing_page_score: 94, recommended_tools: ['External brand'] });
    expect(result.analysisMode).toBe('heuristic');
    expect(result.hero.cta).toBe('Request a demo');
    expect(result.sections).toEqual(['Problem', 'Approach', 'Proof']);
    expect(result.conversionSignals).toEqual(['Trust evidence']);
    expect('landingPageScore' in result).toBe(false);
  });

  it('distinguishes returned empty sections from fields omitted by the provider', () => {
    expect(parseLandingBrief({ ...response, sections: [], faq_pairs: [] }).sections).toEqual([]);
    const withoutSections = { ...response } as Record<string, unknown>;
    delete withoutSections.sections;
    expect(parseLandingBrief(withoutSections).sections).toBeNull();
  });

  it('rejects invalid fallback provenance and malformed required sections', () => {
    expect(() => parseLandingBrief({ ...response, fallback: true, analysis_mode: 'llm' })).toThrow(/not identified as a heuristic draft/i);
    expect(() => parseLandingBrief({ ...response, hero: null })).toThrow(/invalid hero section/i);
    expect(() => parseLandingBrief({ ...response, schema_markup: [{ type: 'Product', json_ld: [] }] })).toThrow(/invalid schema item/i);
  });

  it('exports every useful brief section with draft-only disclosure and no fake score', () => {
    const markdown = landingBriefMarkdown(parseLandingBrief(response), 'Product Name', 'target phrase');
    expect(markdown).toContain('## Page outline');
    expect(markdown).toContain('## Suggested conversion elements');
    expect(markdown).toContain('## Schema drafts');
    expect(markdown).toContain('Heuristic/template draft');
    expect(markdown).toContain('Draft only. Verify factual, legal, brand, SEO, and structured-data requirements before publishing.');
    expect(markdown).not.toContain('landing_page_score');
  });
});
