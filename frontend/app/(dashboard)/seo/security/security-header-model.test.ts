import { describe, expect, it } from 'vitest';
import { parseSecurityHeaderSample, securityHeaderReviewCsv } from './security-header-model';

describe('parseSecurityHeaderSample', () => {
  it('reports exact, case-insensitive header evidence without certifying policy correctness', () => {
    const review = parseSecurityHeaderSample('HTTP/2 200\nStrict-Transport-Security: max-age=31536000\ncontent-security-policy: default-src \'self\'; frame-ancestors \'none\'\nX-Content-Type-Options: nosniff');
    expect(review.headerLinesCount).toBe(3);
    expect(review.frameAncestorsInSample).toBe(true);
    expect(review.observations.find((item) => item.name === 'Content-Security-Policy')?.value).toContain("default-src 'self'");
    expect(review.observations.find((item) => item.name === 'X-Frame-Options')?.foundInSample).toBe(false);
  });

  it('keeps malformed lines distinct from absent security headers and enforces the size limit', () => {
    const review = parseSecurityHeaderSample('Server: example\nnot a header');
    expect(review.ignoredLineCount).toBe(1);
    expect(review.observations.find((item) => item.name === 'Referrer-Policy')?.foundInSample).toBe(false);
    expect(() => parseSecurityHeaderSample('')).toThrow(/paste response headers/i);
    expect(() => parseSecurityHeaderSample('x'.repeat(128_001))).toThrow(/128 KB/i);
  });

  it('exports header values with spreadsheet formula mitigation', () => {
    const review = parseSecurityHeaderSample('X-Frame-Options: =SUM(A1:A2)');
    expect(securityHeaderReviewCsv(review)).toContain("'=SUM(A1:A2)");
  });
});
