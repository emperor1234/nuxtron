export type HeaderObservation = {
  name: string;
  value: string | null;
  foundInSample: boolean;
};

export type SecurityHeaderReview = {
  headerLinesCount: number;
  uniqueHeaderNames: number;
  ignoredLineCount: number;
  frameAncestorsInSample: boolean;
  observations: HeaderObservation[];
};

const MAX_HEADER_SAMPLE_LENGTH = 128_000;
const HEADER_NAME = /^[!#$%&'*+.^_`|~0-9a-z-]+$/i;
const REVIEW_HEADERS = [
  ['Strict-Transport-Security', 'strict-transport-security'],
  ['Content-Security-Policy', 'content-security-policy'],
  ['X-Frame-Options', 'x-frame-options'],
  ['X-Content-Type-Options', 'x-content-type-options'],
  ['Referrer-Policy', 'referrer-policy'],
  ['Permissions-Policy', 'permissions-policy'],
] as const;

export function parseSecurityHeaderSample(sample: string): SecurityHeaderReview {
  if (!sample.trim()) throw new Error('Paste response headers before starting the review.');
  if (sample.length > MAX_HEADER_SAMPLE_LENGTH) throw new Error('Header sample is too large. Limit it to 128 KB.');

  const headers = new Map<string, string[]>();
  let headerLinesCount = 0;
  let ignoredLineCount = 0;
  for (const rawLine of sample.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || /^HTTP\/\d(?:\.\d)?\s+\d{3}\b/i.test(line)) continue;
    const colon = line.indexOf(':');
    if (colon <= 0) {
      ignoredLineCount += 1;
      continue;
    }
    const name = line.slice(0, colon).trim();
    if (!HEADER_NAME.test(name)) {
      ignoredLineCount += 1;
      continue;
    }
    const key = name.toLowerCase();
    const values = headers.get(key) ?? [];
    values.push(line.slice(colon + 1).trim());
    headers.set(key, values);
    headerLinesCount += 1;
  }

  const csp = (headers.get('content-security-policy') ?? []).join('\n');
  return {
    headerLinesCount,
    uniqueHeaderNames: headers.size,
    ignoredLineCount,
    frameAncestorsInSample: /(?:^|;)\s*frame-ancestors(?:\s|;|$)/i.test(csp),
    observations: REVIEW_HEADERS.map(([name, key]) => ({
      name,
      value: headers.has(key) ? (headers.get(key) ?? []).join('\n') : null,
      foundInSample: headers.has(key),
    })),
  };
}

function csvCell(value: string): string {
  const safe = /^[\s]*[=+@-]/.test(value) ? `'${value}` : value;
  return `"${safe.replaceAll('"', '""')}"`;
}

export function securityHeaderReviewCsv(review: SecurityHeaderReview): string {
  const rows = [
    ['Header', 'Found in pasted sample', 'Observed value'],
    ...review.observations.map((item) => [item.name, item.foundInSample ? 'yes' : 'not found in sample', item.value ?? '']),
    ['Content-Security-Policy frame-ancestors directive', review.frameAncestorsInSample ? 'found in sample' : 'not found in sample', ''],
  ];
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}
