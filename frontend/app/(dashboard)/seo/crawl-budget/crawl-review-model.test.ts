import { describe, expect, it } from 'vitest';
import { analyzeCrawlReview, crawlCandidatesCsv } from './crawl-review-model';

const logLine = '192.0.2.4 - - [12/Oct/2026:21:00:00 -0700] "GET /tag/seo HTTP/1.1" 404 123 "-" "ExampleBot/1.0"';

describe('analyzeCrawlReview', () => {
  it('derives only observable URL patterns and status counts from the supplied sample', () => {
    const result = analyzeCrawlReview({
      domain: 'example.com',
      sampleUrls: '/pricing\n/tag/seo\n/tag/seo\n/page/2/?utm_source=email',
      logSnippet: `${logLine}\n192.0.2.4 - - [12/Oct/2026:21:01:00 -0700] "GET /tag/seo HTTP/1.1" 404 122 "-" "ExampleBot/1.0"`,
    });

    expect(result.origin).toBe('https://example.com');
    expect(result.sampleUrlCount).toBe(3);
    expect(result.duplicateSampleCount).toBe(1);
    expect(result.parsedLogLineCount).toBe(2);
    expect(result.statusCounts).toEqual({ '404': 2 });
    expect(result.clientErrorCount).toBe(2);
    expect(result.serverErrorCount).toBe(0);
    expect(result.candidates.some((candidate) => candidate.reasons.includes('Tag archive path'))).toBe(true);
    expect(result.candidates.find((candidate) => candidate.url === 'https://example.com/tag/seo')?.requestCount).toBe(2);
    expect('crawlBudgetScore' in result).toBe(false);
    expect('wastePercent' in result).toBe(false);
  });

  it('distinguishes a genuinely empty sample from unavailable or invented site metrics', () => {
    const result = analyzeCrawlReview({ domain: 'https://example.com', sampleUrls: '/pricing', logSnippet: '' });
    expect(result.sampleUrlCount).toBe(1);
    expect(result.logLineCount).toBe(0);
    expect(result.statusCounts).toEqual({});
    expect(result.candidates).toEqual([]);
  });

  it('rejects a URL outside the selected origin and domains containing paths or credentials', () => {
    expect(() => analyzeCrawlReview({ domain: 'example.com', sampleUrls: 'https://other.example/tag/', logSnippet: '' })).toThrow(/outside the selected website origin/i);
    expect(() => analyzeCrawlReview({ domain: 'https://example.com/blog', sampleUrls: '/tag/', logSnippet: '' })).toThrow(/only the website origin/i);
    expect(() => analyzeCrawlReview({ domain: 'https://user:secret@example.com', sampleUrls: '/tag/', logSnippet: '' })).toThrow(/credential-free/i);
  });

  it('rejects unrecognized-only access log snippets rather than reporting a false zero', () => {
    expect(() => analyzeCrawlReview({ domain: 'example.com', sampleUrls: '', logSnippet: 'not a supported access log' })).toThrow(/no supported access-log request lines/i);
  });

  it('escapes formula-like cells in an exportable candidate list', () => {
    const csv = crawlCandidatesCsv([{
      url: '=HYPERLINK("https://untrusted.invalid")',
      reasons: ['Test signal'],
      sources: ['Sample URL list'],
      requestCount: 0,
      statusCounts: {},
    }]);
    expect(csv).toContain("'=HYPERLINK");
    expect(csv.startsWith('"URL","Review signals"')).toBe(true);
  });
});
