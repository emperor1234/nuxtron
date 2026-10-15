import { describe, expect, it } from 'vitest';
import { buildSeoAnalysisPayload, parseSeoAnalysisResult, type SeoAnalysisDraft } from './seo-analysis-model';

const draft: SeoAnalysisDraft = {
  url: '',
  targetKeyword: 'organic search',
  content: 'This is enough page copy for a first-pass check.',
};

const response = {
  status: 'ok',
  tenant_id: 'internal-workspace-id',
  score: 90,
  word_count: 400,
  keyword_count: 4,
  keyword_density_percent: 1,
  checks: { has_url: true, keyword_present: true, good_length: true, balanced_density: true },
  recommendations: [],
};

describe('SEO Content Check model', () => {
  it('allows an optional URL and submits only the real endpoint fields', () => {
    expect(buildSeoAnalysisPayload(draft)).toEqual({
      payload: { target_keyword: 'organic search', content: draft.content },
      errors: {},
    });
    expect(buildSeoAnalysisPayload({ ...draft, url: 'https://example.com/page' }).payload).toEqual({
      url: 'https://example.com/page',
      target_keyword: 'organic search',
      content: draft.content,
    });
  });

  it('validates HTTP(S) URLs and backend field length limits', () => {
    expect(buildSeoAnalysisPayload({ ...draft, url: 'ftp://example.com/page' }).errors.url).toContain('http:// or https://');
    expect(buildSeoAnalysisPayload({ ...draft, targetKeyword: 'x' }).errors.targetKeyword).toBeTruthy();
    expect(buildSeoAnalysisPayload({ ...draft, content: 'too short' }).errors.content).toBeTruthy();
    expect(buildSeoAnalysisPayload({ ...draft, content: 'x'.repeat(10001) }).errors.content).toContain('10,000');
  });

  it('normalizes the exact supported response and ignores internal workspace identifiers', () => {
    expect(parseSeoAnalysisResult(response)).toEqual({
      score: 90,
      wordCount: 400,
      keywordCount: 4,
      keywordDensityPercent: 1,
      checks: { hasUrl: true, keywordPresent: true, goodLength: true, balancedDensity: true },
      recommendations: [],
    });
  });

  it('preserves genuine zero values rather than replacing them with unavailable data', () => {
    const parsed = parseSeoAnalysisResult({
      ...response,
      score: 60,
      word_count: 0,
      keyword_count: 0,
      keyword_density_percent: 0,
      checks: { has_url: false, keyword_present: false, good_length: false, balanced_density: false },
      recommendations: ['Add the target keyword.'],
    });
    expect(parsed?.wordCount).toBe(0);
    expect(parsed?.keywordCount).toBe(0);
    expect(parsed?.keywordDensityPercent).toBe(0);
  });

  it('rejects incomplete or malformed result records', () => {
    expect(parseSeoAnalysisResult({ ...response, checks: { has_url: true } })).toBeNull();
    expect(parseSeoAnalysisResult({ ...response, word_count: '400' })).toBeNull();
    expect(parseSeoAnalysisResult({ ...response, recommendations: ['ok', 3] })).toBeNull();
    expect(parseSeoAnalysisResult({ ...response, status: 'fallback' })).toBeNull();
  });
});
