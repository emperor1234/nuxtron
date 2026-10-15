export type CrawlCandidate = {
  url: string;
  reasons: string[];
  sources: string[];
  requestCount: number;
  statusCounts: Record<string, number>;
};

export type CrawlReview = {
  origin: string;
  sampleUrlCount: number;
  duplicateSampleCount: number;
  logLineCount: number;
  parsedLogLineCount: number;
  unrecognizedLogLineCount: number;
  statusCounts: Record<string, number>;
  clientErrorCount: number;
  serverErrorCount: number;
  candidates: CrawlCandidate[];
};

export type CrawlReviewInput = {
  domain: string;
  sampleUrls: string;
  logSnippet: string;
};

const PATTERNS: Array<{ test: (url: URL) => boolean; label: string }> = [
  { test: (url) => /\/(?:tag|tags)\//i.test(url.pathname), label: 'Tag archive path' },
  { test: (url) => /\/(?:author|authors)\//i.test(url.pathname), label: 'Author archive path' },
  { test: (url) => /\/(?:search|find)(?:\/|$)/i.test(url.pathname), label: 'Search path' },
  { test: (url) => /\/(?:filter|facets?)(?:\/|$)/i.test(url.pathname), label: 'Filter/facet path' },
  { test: (url) => /\/page\/\d+\/?$/i.test(url.pathname) || url.searchParams.has('page'), label: 'Pagination path' },
  { test: (url) => [...url.searchParams.keys()].some((key) => /^(?:sort|filter|order|view)$/i.test(key)), label: 'Sorting or filter parameter' },
  { test: (url) => [...url.searchParams.keys()].some((key) => /^utm_/i.test(key)), label: 'Tracking parameter' },
];

function normalizeOrigin(value: string): string {
  const input = value.trim();
  if (!input) throw new Error('Enter the website origin you want to review.');
  let parsed: URL;
  try {
    parsed = new URL(input.includes('://') ? input : `https://${input}`);
  } catch {
    throw new Error('Enter a valid website origin, such as https://example.com.');
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('Use a credential-free HTTP or HTTPS website origin.');
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw new Error('Enter only the website origin, without a page path, query, or fragment.');
  }
  return parsed.origin;
}

function parseSampleUrl(value: string, origin: string): URL {
  let parsed: URL;
  try {
    if (/^https?:\/\//i.test(value)) parsed = new URL(value);
    else if (value.startsWith('/')) parsed = new URL(value, `${origin}/`);
    else throw new Error('Use an absolute URL or a path beginning with /.');
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('Use an absolute URL')) throw error;
    throw new Error(`Invalid sample URL: ${value}`);
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error(`Sample URLs must be credential-free HTTP(S) addresses: ${value}`);
  }
  if (parsed.origin !== origin) {
    throw new Error(`Sample URL is outside the selected website origin: ${value}`);
  }
  return parsed;
}

function candidateReasons(url: URL): string[] {
  return PATTERNS.filter((rule) => rule.test(url)).map((rule) => rule.label);
}

function addCandidate(
  candidates: Map<string, CrawlCandidate>,
  url: URL,
  source: string,
  status?: number,
): void {
  const reasons = candidateReasons(url);
  if (reasons.length === 0) return;
  const key = url.href;
  const candidate = candidates.get(key) ?? {
    url: `${url.origin}${url.pathname}${url.search}`,
    reasons,
    sources: [],
    requestCount: 0,
    statusCounts: {},
  };
  if (!candidate.sources.includes(source)) candidate.sources.push(source);
  if (status !== undefined) {
    candidate.requestCount += 1;
    const code = String(status);
    candidate.statusCounts[code] = (candidate.statusCounts[code] ?? 0) + 1;
  }
  candidates.set(key, candidate);
}

function parseAccessLogLine(line: string, origin: string): { url: URL; status: number } | null {
  const match = line.match(/"(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)\s+(\S+)\s+HTTP\/\d(?:\.\d)?"\s+(\d{3})(?:\s|$)/i);
  if (!match) return null;
  try {
    const url = new URL(match[1], `${origin}/`);
    if (url.origin !== origin || url.username || url.password || !['http:', 'https:'].includes(url.protocol)) return null;
    return { url, status: Number(match[2]) };
  } catch {
    return null;
  }
}

export function analyzeCrawlReview(input: CrawlReviewInput): CrawlReview {
  const origin = normalizeOrigin(input.domain);
  const candidates = new Map<string, CrawlCandidate>();
  const sampleLines = input.sampleUrls.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (sampleLines.length > 200) throw new Error('Review up to 200 sample URLs at a time.');

  const sampleSet = new Set<string>();
  let duplicateSampleCount = 0;
  for (const line of sampleLines) {
    const url = parseSampleUrl(line, origin);
    if (sampleSet.has(url.href)) duplicateSampleCount += 1;
    sampleSet.add(url.href);
    addCandidate(candidates, url, 'Sample URL list');
  }

  const logLines = input.logSnippet.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const statusCounts: Record<string, number> = {};
  let parsedLogLineCount = 0;
  let clientErrorCount = 0;
  let serverErrorCount = 0;
  for (const line of logLines) {
    const entry = parseAccessLogLine(line, origin);
    if (!entry) continue;
    parsedLogLineCount += 1;
    const code = String(entry.status);
    statusCounts[code] = (statusCounts[code] ?? 0) + 1;
    if (entry.status >= 400 && entry.status < 500) clientErrorCount += 1;
    if (entry.status >= 500) serverErrorCount += 1;
    addCandidate(candidates, entry.url, 'Parsed access-log sample', entry.status);
  }

  if (sampleLines.length === 0 && logLines.length === 0) {
    throw new Error('Add at least one sample URL or a supported access-log line.');
  }
  if (logLines.length > 0 && parsedLogLineCount === 0) {
    throw new Error('No supported access-log request lines were recognized. Paste Common or Combined Log Format entries.');
  }

  const sortedStatusCounts = Object.fromEntries(
    Object.entries(statusCounts).sort(([left], [right]) => Number(left) - Number(right)),
  );
  return {
    origin,
    sampleUrlCount: sampleSet.size,
    duplicateSampleCount,
    logLineCount: logLines.length,
    parsedLogLineCount,
    unrecognizedLogLineCount: logLines.length - parsedLogLineCount,
    statusCounts: sortedStatusCounts,
    clientErrorCount,
    serverErrorCount,
    candidates: [...candidates.values()].sort((left, right) => right.requestCount - left.requestCount || left.url.localeCompare(right.url)),
  };
}

function csvCell(value: string): string {
  const safeValue = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safeValue.replace(/"/g, '""')}"`;
}

export function crawlCandidatesCsv(candidates: CrawlCandidate[]): string {
  const header = ['URL', 'Review signals', 'Observed in', 'Parsed log requests', 'Response codes'];
  const rows = candidates.map((candidate) => [
    candidate.url,
    candidate.reasons.join('; '),
    candidate.sources.join('; '),
    String(candidate.requestCount),
    Object.entries(candidate.statusCounts).map(([code, count]) => `${code}=${count}`).join('; '),
  ]);
  return [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
}
