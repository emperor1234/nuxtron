export type SeoAnalysisDraft = {
  url: string;
  targetKeyword: string;
  content: string;
};

export type SeoAnalysisPayload = {
  url?: string;
  target_keyword: string;
  content: string;
};

export type SeoAnalysisChecks = {
  hasUrl: boolean;
  keywordPresent: boolean;
  goodLength: boolean;
  balancedDensity: boolean;
};

export type SeoAnalysisResult = {
  score: number;
  wordCount: number;
  keywordCount: number;
  keywordDensityPercent: number;
  checks: SeoAnalysisChecks;
  recommendations: string[];
};

export type SeoAnalysisFieldErrors = Partial<Record<'url' | 'targetKeyword' | 'content', string>>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

export function buildSeoAnalysisPayload(draft: SeoAnalysisDraft): {
  payload: SeoAnalysisPayload | null;
  errors: SeoAnalysisFieldErrors;
} {
  const errors: SeoAnalysisFieldErrors = {};
  const urlText = draft.url.trim();
  const targetKeyword = draft.targetKeyword.trim();
  const content = draft.content.trim();

  if (urlText) {
    try {
      const url = new URL(urlText);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') errors.url = 'Use an http:// or https:// reference URL.';
    } catch {
      errors.url = 'Enter a valid http:// or https:// reference URL, or leave it blank.';
    }
  }
  if (targetKeyword.length < 2) errors.targetKeyword = 'Enter a target keyword with at least 2 characters.';
  else if (targetKeyword.length > 120) errors.targetKeyword = 'Keep the target keyword to 120 characters or fewer.';
  if (content.length < 20) errors.content = 'Paste at least 20 characters of page copy.';
  else if (content.length > 10000) errors.content = 'Keep page copy to 10,000 characters or fewer.';

  if (Object.keys(errors).length > 0) return { payload: null, errors };
  return {
    payload: {
      ...(urlText ? { url: new URL(urlText).toString() } : {}),
      target_keyword: targetKeyword,
      content,
    },
    errors: {},
  };
}

export function parseSeoAnalysisResult(value: unknown): SeoAnalysisResult | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  if (
    typeof value.score !== 'number' || !Number.isFinite(value.score) || value.score < 0 || value.score > 100 ||
    !nonNegativeInteger(value.word_count) || !nonNegativeInteger(value.keyword_count) ||
    typeof value.keyword_density_percent !== 'number' || !Number.isFinite(value.keyword_density_percent) || value.keyword_density_percent < 0 ||
    !isRecord(value.checks) || !Array.isArray(value.recommendations)
  ) return null;
  const checks = value.checks;
  if (
    typeof checks.has_url !== 'boolean' || typeof checks.keyword_present !== 'boolean' ||
    typeof checks.good_length !== 'boolean' || typeof checks.balanced_density !== 'boolean' ||
    value.recommendations.some((recommendation) => typeof recommendation !== 'string')
  ) return null;
  return {
    score: value.score,
    wordCount: value.word_count,
    keywordCount: value.keyword_count,
    keywordDensityPercent: value.keyword_density_percent,
    checks: {
      hasUrl: checks.has_url,
      keywordPresent: checks.keyword_present,
      goodLength: checks.good_length,
      balancedDensity: checks.balanced_density,
    },
    recommendations: (value.recommendations as string[]).map((item) => item.trim()).filter(Boolean),
  };
}
