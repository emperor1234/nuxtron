export type ContentLibrarySummary = {
  generationId: string;
  topic: string;
  channel: string;
  headline: string;
  createdAt: string | null;
};

export type ContentGenerationJob = {
  job_id: string;
  status: string;
  progress_pct: number;
  stage: string;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
  is_terminal?: boolean;
  expires_at?: string | null;
};

export type JobList = {
  items: ContentGenerationJob[];
  terminalRetentionSeconds: number | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validOptionalText(value: unknown): value is string | null | undefined {
  return value === undefined || value === null || typeof value === 'string';
}

export function parseContentLibrary(value: unknown): ContentLibrarySummary[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !Number.isInteger(value.count) || !Array.isArray(value.items)) return null;
  if (value.count !== value.items.length || (value.count as number) < 0) return null;

  const items: ContentLibrarySummary[] = [];
  for (const raw of value.items) {
    if (
      !isRecord(raw) || typeof raw.generation_id !== 'string' || !raw.generation_id.trim() ||
      typeof raw.topic !== 'string' || typeof raw.channel !== 'string' || typeof raw.headline !== 'string' ||
      !validOptionalText(raw.created_at)
    ) return null;
    const date = typeof raw.created_at === 'string' && Number.isFinite(Date.parse(raw.created_at)) ? raw.created_at : null;
    items.push({ generationId: raw.generation_id, topic: raw.topic, channel: raw.channel, headline: raw.headline, createdAt: date });
  }
  return items;
}

export function parseContentResult(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) return null;
  let candidate: Record<string, unknown> = value;
  if (isRecord(candidate.item)) {
    const item = candidate.item;
    candidate = isRecord(item.response) ? item.response : item;
  }
  if (isRecord(candidate.response)) candidate = candidate.response;
  if (typeof candidate.headline !== 'string' || typeof candidate.body !== 'string') return null;
  if (candidate.status !== undefined && candidate.status !== 'ok') return null;
  return candidate;
}

export type ContentProvenance = 'ai-generated' | 'template-fallback' | 'unknown';

export function contentProvenance(result: Record<string, unknown>): ContentProvenance {
  if (result.ai_status === 'generated') return 'ai-generated';
  if (result.ai_status === 'fallback') return 'template-fallback';
  return 'unknown';
}

function parseJob(value: unknown): ContentGenerationJob | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.job_id !== 'string' || !value.job_id.trim() ||
    typeof value.status !== 'string' || !value.status.trim() ||
    typeof value.stage !== 'string' || !value.stage.trim() ||
    typeof value.progress_pct !== 'number' || !Number.isFinite(value.progress_pct) ||
    value.progress_pct < 0 || value.progress_pct > 100 ||
    !validOptionalText(value.updated_at) || !validOptionalText(value.started_at) ||
    !validOptionalText(value.completed_at) || !validOptionalText(value.error) ||
    !validOptionalText(value.expires_at) ||
    (value.is_terminal !== undefined && typeof value.is_terminal !== 'boolean') ||
    (value.result !== undefined && value.result !== null && !isRecord(value.result))
  ) return null;
  return {
    job_id: value.job_id,
    status: value.status,
    progress_pct: value.progress_pct,
    stage: value.stage,
    ...(value.updated_at !== undefined ? { updated_at: value.updated_at as string | null } : {}),
    ...(value.started_at !== undefined ? { started_at: value.started_at as string | null } : {}),
    ...(value.completed_at !== undefined ? { completed_at: value.completed_at as string | null } : {}),
    ...(value.error !== undefined ? { error: value.error as string | null } : {}),
    ...(value.is_terminal !== undefined ? { is_terminal: value.is_terminal } : {}),
    ...(value.expires_at !== undefined ? { expires_at: value.expires_at as string | null } : {}),
    ...(value.result !== undefined ? { result: value.result as Record<string, unknown> | null } : {}),
  };
}

export function parseJobList(value: unknown): JobList | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.items)) return null;
  const items = value.items.map(parseJob);
  if (items.some((item) => item === null)) return null;
  const retention = isRecord(value.retention) ? value.retention.terminal_seconds : undefined;
  if (retention !== undefined && (!Number.isInteger(retention) || (retention as number) < 0)) return null;
  return {
    items: items as ContentGenerationJob[],
    terminalRetentionSeconds: typeof retention === 'number' ? retention : null,
  };
}
