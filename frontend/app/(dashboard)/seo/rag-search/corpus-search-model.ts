export type CorpusSource = {
  id: string;
  label: string;
  url: string;
  content: string;
};

export type CorpusMatch = {
  id: string;
  sourceId: string;
  sourceLabel: string;
  sourceUrl: string | null;
  excerpt: string;
  matchedTerms: string[];
  queryTermCount: number;
};

const TOKEN_PATTERN = /[\p{L}\p{N}]{2,}/gu;
const MAX_EXCERPT_LENGTH = 320;

function tokenize(value: string): string[] {
  return Array.from(new Set(value.normalize('NFKC').toLocaleLowerCase().match(TOKEN_PATTERN) ?? []));
}

function safeHttpUrl(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null;
  } catch {
    return null;
  }
}

function excerptFor(value: string): string {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= MAX_EXCERPT_LENGTH) return normalized;
  return `${normalized.slice(0, MAX_EXCERPT_LENGTH - 1).trimEnd()}…`;
}

export function searchCorpus(query: string, sources: readonly CorpusSource[], limit: number): CorpusMatch[] {
  const queryTerms = tokenize(query);
  if (queryTerms.length === 0) return [];

  const matches: Array<CorpusMatch & { order: number; score: number }> = [];
  let order = 0;

  sources.forEach((source, sourceIndex) => {
    const paragraphs = source.content.split(/\n\s*\n+/).map((paragraph) => paragraph.trim()).filter(Boolean);
    paragraphs.forEach((paragraph, paragraphIndex) => {
      const availableTerms = new Set(tokenize(paragraph));
      const matchedTerms = queryTerms.filter((term) => availableTerms.has(term));
      if (matchedTerms.length > 0) {
        matches.push({
          id: `${source.id}:${paragraphIndex}`,
          sourceId: source.id,
          sourceLabel: source.label.trim() || `Source ${sourceIndex + 1}`,
          sourceUrl: safeHttpUrl(source.url),
          excerpt: excerptFor(paragraph),
          matchedTerms,
          queryTermCount: queryTerms.length,
          order,
          score: matchedTerms.length,
        });
      }
      order += 1;
    });
  });

  const safeLimit = Math.max(1, Math.min(20, Math.floor(limit) || 1));
  return matches
    .sort((left, right) => right.score - left.score || left.order - right.order)
    .slice(0, safeLimit)
    .map(({ order: _order, score: _score, ...match }) => match);
}
