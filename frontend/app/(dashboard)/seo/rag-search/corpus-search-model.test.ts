import { describe, expect, it } from 'vitest';
import { searchCorpus, type CorpusSource } from './corpus-search-model';

const sources: CorpusSource[] = [
  {
    id: 'source-a',
    label: 'Guide',
    url: 'https://docs.example.org/guide',
    content: 'Keyword research helps teams identify search intent.\n\nA separate paragraph has no match.',
  },
  {
    id: 'source-b',
    label: 'Notes',
    url: 'javascript:alert(1)',
    content: 'Search intent and keyword research belong together.',
  },
];

describe('browser-local corpus search', () => {
  it('returns exact user-supplied passages ranked by matched query terms', () => {
    const matches = searchCorpus('keyword research intent', sources, 5);

    expect(matches).toHaveLength(2);
    expect(matches[0]).toMatchObject({
      sourceLabel: 'Guide',
      sourceUrl: 'https://docs.example.org/guide',
      excerpt: 'Keyword research helps teams identify search intent.',
      matchedTerms: ['keyword', 'research', 'intent'],
      queryTermCount: 3,
    });
    expect(matches[1]).toMatchObject({
      sourceLabel: 'Notes',
      sourceUrl: null,
      matchedTerms: ['keyword', 'research', 'intent'],
    });
    expect(matches.map((match) => match.excerpt)).toEqual([
      'Keyword research helps teams identify search intent.',
      'Search intent and keyword research belong together.',
    ]);
  });

  it('returns no result for absent terms or a query with no searchable tokens', () => {
    expect(searchCorpus('unrelated', sources, 5)).toEqual([]);
    expect(searchCorpus('!!!', sources, 5)).toEqual([]);
  });

  it('caps the result count and excerpt length without inventing URLs or answers', () => {
    const longContent = 'keyword '.repeat(100);
    const manySources = Array.from({ length: 4 }, (_, index) => ({
      id: `s-${index}`,
      label: '',
      url: '',
      content: `${index ? 'research' : 'keyword research'}\n\n${longContent}`,
    }));
    const matches = searchCorpus('keyword research', manySources, 1);

    expect(matches).toHaveLength(1);
    expect(matches[0].excerpt.length).toBeLessThanOrEqual(320);
    expect(matches[0].sourceUrl).toBeNull();
    expect('answer' in matches[0]).toBe(false);
    expect(matches[0].sourceLabel).toBe('Source 1');
  });
});
