export type LandingFaq = { question: string; answer: string };
export type LandingSchema = { type: string; jsonLd: Record<string, unknown> };

export type LandingBrief = {
  analysisId: string | null;
  analysisMode: 'llm' | 'heuristic' | null;
  cached: boolean;
  hero: { headline: string; subheadline: string; cta: string };
  sections: string[] | null;
  seoMeta: { title: string; description: string; canonical: string };
  faqPairs: LandingFaq[] | null;
  variants: string[] | null;
  schemaMarkup: LandingSchema[] | null;
  conversionSignals: string[] | null;
  generatedAt: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requiredRecord(value: unknown, name: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`The generation service returned an invalid ${name} section.`);
  return value;
}

function requiredText(record: Record<string, unknown>, field: string, section: string): string {
  const value = record[field];
  if (typeof value !== 'string') throw new Error(`The generation service returned an invalid ${section}.${field} field.`);
  return value;
}

function optionalStringArray(record: Record<string, unknown>, field: string): string[] | null {
  if (!Object.hasOwn(record, field)) return null;
  const value = record[field];
  if (!Array.isArray(value) || !value.every((item) => typeof item === 'string')) {
    throw new Error(`The generation service returned an invalid ${field} list.`);
  }
  return value;
}

function optionalFaqArray(record: Record<string, unknown>): LandingFaq[] | null {
  if (!Object.hasOwn(record, 'faq_pairs')) return null;
  const value = record.faq_pairs;
  if (!Array.isArray(value)) throw new Error('The generation service returned an invalid FAQ list.');
  return value.map((item, index) => {
    if (!isRecord(item) || typeof item.question !== 'string' || typeof item.answer !== 'string') {
      throw new Error(`The generation service returned an invalid FAQ item at position ${index + 1}.`);
    }
    return { question: item.question, answer: item.answer };
  });
}

function optionalSchemaArray(record: Record<string, unknown>): LandingSchema[] | null {
  if (!Object.hasOwn(record, 'schema_markup')) return null;
  const value = record.schema_markup;
  if (!Array.isArray(value)) throw new Error('The generation service returned an invalid schema list.');
  return value.map((item, index) => {
    if (!isRecord(item) || typeof item.type !== 'string' || !isRecord(item.json_ld)) {
      throw new Error(`The generation service returned an invalid schema item at position ${index + 1}.`);
    }
    return { type: item.type, jsonLd: item.json_ld };
  });
}

export function parseLandingBrief(value: unknown): LandingBrief {
  const response = requiredRecord(value, 'response');
  const hero = requiredRecord(response.hero, 'hero');
  const seo = requiredRecord(response.seo_meta, 'SEO metadata');
  const mode = response.analysis_mode === 'llm' || response.analysis_mode === 'heuristic'
    ? response.analysis_mode
    : null;
  if (response.fallback === true && mode !== 'heuristic') {
    throw new Error('A fallback response was not identified as a heuristic draft. It was not shown as provider-generated content.');
  }
  if (response.cached !== undefined && typeof response.cached !== 'boolean') {
    throw new Error('The generation service returned an invalid cache status.');
  }
  const analysisId = typeof response.analysis_id === 'string' && response.analysis_id.trim()
    ? response.analysis_id
    : null;
  const generatedAt = typeof response.generated_at === 'string' && response.generated_at.trim()
    ? response.generated_at
    : null;

  return {
    analysisId,
    analysisMode: mode,
    cached: response.cached === true,
    hero: {
      headline: requiredText(hero, 'headline', 'hero'),
      subheadline: requiredText(hero, 'subheadline', 'hero'),
      cta: requiredText(hero, 'cta', 'hero'),
    },
    sections: optionalStringArray(response, 'sections'),
    seoMeta: {
      title: requiredText(seo, 'title', 'seo_meta'),
      description: requiredText(seo, 'description', 'seo_meta'),
      canonical: requiredText(seo, 'canonical', 'seo_meta'),
    },
    faqPairs: optionalFaqArray(response),
    variants: optionalStringArray(response, 'ab_test_variants'),
    schemaMarkup: optionalSchemaArray(response),
    conversionSignals: optionalStringArray(response, 'conversion_signals'),
    generatedAt,
  };
}

function markdownList(values: string[] | null, missingLabel: string): string {
  if (values === null) return `Not returned by the generation service (${missingLabel}).`;
  if (values.length === 0) return 'None returned.';
  return values.map((value) => `- ${value}`).join('\n');
}

export function landingBriefMarkdown(brief: LandingBrief, productName: string, keyword: string): string {
  const faq = brief.faqPairs === null
    ? 'Not returned by the generation service.'
    : brief.faqPairs.length === 0
      ? 'None returned.'
      : brief.faqPairs.map(({ question, answer }) => `### ${question}\n\n${answer}`).join('\n\n');
  const schemas = brief.schemaMarkup === null
    ? 'Not returned by the generation service.'
    : brief.schemaMarkup.length === 0
      ? 'None returned.'
      : brief.schemaMarkup.map((item) => `### ${item.type}\n\n\`\`\`json\n${JSON.stringify(item.jsonLd, null, 2)}\n\`\`\``).join('\n\n');
  return [
    `# Landing Page Brief: ${productName}`,
    `Target keyword: ${keyword}`,
    `Output type: ${brief.analysisMode === 'heuristic' ? 'Heuristic/template draft' : brief.analysisMode === 'llm' ? 'Provider-generated draft' : 'Provenance unavailable'}`,
    '',
    '## Hero',
    `**Headline:** ${brief.hero.headline}`,
    `**Subheadline:** ${brief.hero.subheadline}`,
    `**Suggested CTA copy:** ${brief.hero.cta}`,
    '',
    '## Page outline',
    markdownList(brief.sections, 'page outline'),
    '',
    '## SEO metadata',
    `**Title:** ${brief.seoMeta.title}`,
    `**Description:** ${brief.seoMeta.description}`,
    `**Canonical suggestion:** ${brief.seoMeta.canonical}`,
    '',
    '## FAQs', faq,
    '',
    '## Headline variants', markdownList(brief.variants, 'headline variants'),
    '',
    '## Suggested conversion elements', markdownList(brief.conversionSignals, 'conversion elements'),
    '',
    '## Schema drafts', schemas,
    '',
    '> Draft only. Verify factual, legal, brand, SEO, and structured-data requirements before publishing.',
  ].join('\n');
}
