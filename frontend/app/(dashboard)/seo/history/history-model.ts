export type SeoHistoryRecord = {
  id: string;
  module: string;
  createdAt: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type SeoHistoryResponse = {
  analyses: SeoHistoryRecord[];
  total: number;
  persistence: 'postgres' | 'memory';
};

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseRecord(value: unknown): SeoHistoryRecord | null {
  if (!isRecord(value)) return null;
  const { id, module, created_at: createdAt, payload, result } = value;
  if (
    typeof id !== 'string' || !id.trim() || id.length > 128 ||
    typeof module !== 'string' || !module.trim() || module.length > 200 ||
    typeof createdAt !== 'string' || !Number.isFinite(Date.parse(createdAt)) ||
    !isRecord(payload) || !isRecord(result)
  ) {
    return null;
  }

  // Deliberately map only customer-relevant fields; backend tenant_id is never
  // carried into the rendered history model.
  return { id: id.trim(), module: module.trim(), createdAt, payload, result };
}

export function parseSeoHistoryResponse(value: unknown): SeoHistoryResponse | null {
  if (!isRecord(value) || !Array.isArray(value.analyses)) return null;
  if (typeof value.total !== 'number' || !Number.isSafeInteger(value.total) || value.total < 0 || value.total > 100) {
    return null;
  }
  if (value.persistence !== 'postgres' && value.persistence !== 'memory') return null;

  const analyses = value.analyses.map(parseRecord);
  if (analyses.some((record) => record === null) || value.total !== analyses.length) return null;
  return { analyses: analyses as SeoHistoryRecord[], total: value.total, persistence: value.persistence };
}

function isSensitiveField(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, '');
  return [
    'tenant', 'tenantid', 'token', 'accesstoken', 'refreshtoken', 'secret', 'clientsecret',
    'password', 'credential', 'authorization', 'cookie', 'apikey', 'email', 'phone',
  ].some((fragment) => normalized.includes(fragment));
}

function redact(value: unknown, depth = 0): unknown {
  if (depth > 8) return '[maximum detail depth reached]';
  if (typeof value === 'string') {
    return value.length > 5000 ? `${value.slice(0, 5000)}… [value truncated]` : value;
  }
  if (Array.isArray(value)) {
    const limited = value.slice(0, 80).map((item) => redact(item, depth + 1));
    if (value.length > limited.length) limited.push(`[${value.length - limited.length} additional items omitted]`);
    return limited;
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).slice(0, 100).map(([key, child]) => [
        key,
        isSensitiveField(key) ? '[redacted]' : redact(child, depth + 1),
      ]),
    );
  }
  return value;
}

export function formatRedactedJson(value: Record<string, unknown>): string {
  const formatted = JSON.stringify(redact(value), null, 2) ?? '{}';
  return formatted.length > 24000 ? `${formatted.slice(0, 24000)}\n… [output truncated]` : formatted;
}

export function formatModuleLabel(module: string): string {
  if (module === 'planner_workflow_draft') return 'SEO Workflow Planner';
  if (module === 'performance_audit' || module === 'performance-audit') return 'Performance Audit (retired)';
  if (module === 'keyword_research' || module === 'keyword-research-engine') return 'Keyword Data Review';
  if (module === 'international_multilingual' || module === 'international-multilingual-seo') return 'Hreflang & Locale Review';
  if (module === 'rag_search' || module === 'rag-site-search-engine') return 'Corpus Search Preview';
  if (module === 'programmatic' || module === 'programmatic-seo-engine') return 'Programmatic SEO Draft Preview';
  return module
    .replace(/[_-]+/g, ' ')
    .replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
}

export function describeSavedResult(record: SeoHistoryRecord): string {
  const count = Object.keys(record.result).filter((key) => !isSensitiveField(key)).length;
  return count === 1 ? '1 saved output field' : `${count} saved output fields`;
}
