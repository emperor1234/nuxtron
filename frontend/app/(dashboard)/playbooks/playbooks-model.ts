export type PlaybookDefinition = {
  id: string;
  name: string;
  vertical: string;
  description: string;
  steps: string[];
  integrations: string[];
  builtIn: boolean;
  timeToValueDays: number | null;
};

export type PlaybookRun = {
  id: string;
  playbookId: string;
  playbookName: string;
  dryRun: boolean;
  status: string;
  stepsTotal: number | null;
  stepsCompleted: number | null;
  createdAt: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/.test(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

function optionalCount(value: unknown): number | null | undefined {
  if (value === undefined || value === null) return null;
  return isNonNegativeInteger(value) ? value : undefined;
}

function stringArray(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) return null;
  return value as string[];
}

export function parsePlaybookCatalog(value: unknown): PlaybookDefinition[] | null {
  if (!isRecord(value) || !Array.isArray(value.playbooks) || !isNonNegativeInteger(value.total)) return null;
  if (value.total !== value.playbooks.length) return null;

  const definitions: PlaybookDefinition[] = [];
  const seenIds = new Set<string>();
  for (const raw of value.playbooks) {
    if (!isRecord(raw) || !isIdentifier(raw.id) || seenIds.has(raw.id)) return null;
    if (
      typeof raw.name !== 'string' || !raw.name.trim() ||
      typeof raw.vertical !== 'string' || !raw.vertical.trim() ||
      typeof raw.description !== 'string' ||
      typeof raw.built_in !== 'boolean'
    ) return null;
    const steps = stringArray(raw.steps);
    const integrations = stringArray(raw.integrations);
    if (!steps || !integrations) return null;
    const timeToValueDays = raw.time_to_value_days === undefined || raw.time_to_value_days === null
      ? null
      : isNonNegativeInteger(raw.time_to_value_days) ? raw.time_to_value_days : undefined;
    if (timeToValueDays === undefined) return null;

    seenIds.add(raw.id);
    definitions.push({
      id: raw.id,
      name: raw.name.trim(),
      vertical: raw.vertical.trim(),
      description: raw.description.trim(),
      steps,
      integrations,
      builtIn: raw.built_in,
      timeToValueDays,
    });
  }
  return definitions;
}

export function parsePlaybookRuns(value: unknown): PlaybookRun[] | null {
  if (!isRecord(value) || !Array.isArray(value.runs) || !isNonNegativeInteger(value.total)) return null;
  if (value.total !== value.runs.length) return null;

  const runs: PlaybookRun[] = [];
  const seenIds = new Set<string>();
  for (const raw of value.runs) {
    if (!isRecord(raw) || !isIdentifier(raw.id) || !isIdentifier(raw.playbook_id) || seenIds.has(raw.id)) return null;
    if (typeof raw.playbook_name !== 'string' || typeof raw.dry_run !== 'boolean' || typeof raw.status !== 'string') return null;
    const stepsTotal = optionalCount(raw.steps_total);
    const stepsCompleted = optionalCount(raw.steps_completed);
    if (stepsTotal === undefined || stepsCompleted === undefined) return null;
    if (raw.created_at !== undefined && raw.created_at !== null && typeof raw.created_at !== 'string') return null;

    seenIds.add(raw.id);
    runs.push({
      id: raw.id,
      playbookId: raw.playbook_id,
      playbookName: raw.playbook_name.trim(),
      dryRun: raw.dry_run,
      status: raw.status.trim(),
      stepsTotal,
      stepsCompleted,
      createdAt: typeof raw.created_at === 'string' && raw.created_at.trim() ? raw.created_at : null,
    });
  }
  return runs;
}

export function filterPlaybooks(
  playbooks: PlaybookDefinition[],
  query: string,
  vertical: string,
): PlaybookDefinition[] {
  const normalizedQuery = query.trim().toLowerCase();
  return playbooks.filter((playbook) => {
    const matchesVertical = vertical === 'all' || playbook.vertical.toLowerCase() === vertical.toLowerCase();
    const matchesQuery = !normalizedQuery || [playbook.name, playbook.description, playbook.vertical, ...playbook.integrations]
      .some((value) => value.toLowerCase().includes(normalizedQuery));
    return matchesVertical && matchesQuery;
  });
}

export function playbookRunStatusLabel(run: PlaybookRun): string {
  if (run.dryRun) return 'Preview record — no steps executed';
  if (run.status.toLowerCase() === 'scheduled') return 'Scheduled — not executed';
  return run.status.replaceAll('_', ' ');
}

export function formatPlaybookDate(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString();
}
