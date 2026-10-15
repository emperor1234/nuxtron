export const PROGRAMMATIC_LIMITS = {
  variables: 5,
  valuesPerVariable: 20,
  variants: 100,
  sampleRows: 5,
  templateCharacters: 500,
  valueCharacters: 120,
} as const;

export type ProgrammaticVariable = {
  key: string;
  values: string[];
};

export type ProgrammaticDraftInput = {
  urlTemplate: string;
  titleTemplate: string;
  metaDescriptionTemplate: string;
  variables: ProgrammaticVariable[];
};

export type ProgrammaticPreviewRow = {
  path: string;
  title: string;
  metaDescription: string;
  values: Record<string, string>;
  duplicatePath: boolean;
};

export type ProgrammaticValidation = {
  errors: string[];
  pageCount: number;
};

export type ProgrammaticPreviewResult =
  | { ok: false; errors: string[]; pageCount: number }
  | {
      ok: true;
      rows: ProgrammaticPreviewRow[];
      pageCount: number;
      duplicatePathGroups: number;
    };

const PLACEHOLDER = /\[([a-z][a-z0-9_]*)\]/g;
const VARIABLE_KEY = /^[a-z][a-z0-9_]{0,39}$/;

export function validateProgrammaticDraft(input: ProgrammaticDraftInput): ProgrammaticValidation {
  const errors = new Set<string>();
  const urlTemplate = input.urlTemplate.trim();
  const titleTemplate = input.titleTemplate.trim();
  const metaTemplate = input.metaDescriptionTemplate.trim();

  if (!urlTemplate) errors.add('Enter a relative URL path template.');
  if (!titleTemplate) errors.add('Enter a page-title template.');
  if (!metaTemplate) errors.add('Enter a meta-description template.');

  if (
    urlTemplate &&
    (!urlTemplate.startsWith('/') ||
      urlTemplate.startsWith('//') ||
      /[?#\\]/.test(urlTemplate) ||
      [...urlTemplate].some((character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127) ||
      /(?:^|\/)\.\.(?:\/|$)/.test(urlTemplate) ||
      urlTemplate.includes('//'))
  ) {
    errors.add('Use a relative path beginning with one slash; query strings, fragments, backslashes, and parent-directory segments are not allowed.');
  }

  for (const [label, value] of [
    ['URL', urlTemplate],
    ['Title', titleTemplate],
    ['Meta description', metaTemplate],
  ] as const) {
    if (value.length > PROGRAMMATIC_LIMITS.templateCharacters) {
      errors.add(`${label} template must be ${PROGRAMMATIC_LIMITS.templateCharacters} characters or fewer.`);
    }
  }

  if (input.variables.length < 1 || input.variables.length > PROGRAMMATIC_LIMITS.variables) {
    errors.add(`Add between 1 and ${PROGRAMMATIC_LIMITS.variables} variables.`);
  }

  const seenKeys = new Set<string>();
  const validKeys = new Set<string>();
  let pageCount = input.variables.length > 0 ? 1 : 0;

  for (const variable of input.variables) {
    const key = variable.key.trim();
    if (!VARIABLE_KEY.test(key)) {
      errors.add('Variable names must start with a lowercase letter and contain only lowercase letters, numbers, or underscores.');
    } else if (seenKeys.has(key)) {
      errors.add(`Variable name “${key}” is repeated; each name must be unique.`);
    } else {
      seenKeys.add(key);
      validKeys.add(key);
    }

    const values = variable.values.map((value) => value.trim()).filter(Boolean);
    if (values.length === 0 || values.length > PROGRAMMATIC_LIMITS.valuesPerVariable) {
      errors.add(`Each variable needs 1–${PROGRAMMATIC_LIMITS.valuesPerVariable} non-empty values.`);
    }
    if (variable.values.some((value) => value.trim().length > PROGRAMMATIC_LIMITS.valueCharacters)) {
      errors.add(`Each value must be ${PROGRAMMATIC_LIMITS.valueCharacters} characters or fewer.`);
    }
    pageCount = values.length === 0
      ? 0
      : Math.min(PROGRAMMATIC_LIMITS.variants + 1, pageCount * values.length);
  }

  if (pageCount > PROGRAMMATIC_LIMITS.variants) {
    errors.add(`The matrix expands to more than ${PROGRAMMATIC_LIMITS.variants} variants. Narrow it before previewing.`);
  }

  const templates = [urlTemplate, titleTemplate, metaTemplate];
  for (const template of templates) {
    for (const [, key] of template.matchAll(PLACEHOLDER)) {
      if (!validKeys.has(key)) errors.add(`Template token [${key}] has no matching variable.`);
    }
  }

  const urlVariableKeys = new Set([...urlTemplate.matchAll(PLACEHOLDER)].map(([, key]) => key));
  for (const variable of input.variables) {
    if (
      urlVariableKeys.has(variable.key.trim()) &&
      variable.values.some((value) => value.trim() && !slugify(value.trim()))
    ) {
      errors.add(`Variable “${variable.key.trim()}” contains a value that cannot form a URL path segment.`);
    }
  }

  return { errors: [...errors], pageCount };
}

function slugify(value: string): string {
  return value
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '');
}

function expandTemplate(template: string, values: Record<string, string>, forPath: boolean): string {
  return template.replace(PLACEHOLDER, (_match, key: string) => {
    const value = values[key] ?? '';
    return forPath ? slugify(value) : value;
  });
}

export function buildProgrammaticPreview(input: ProgrammaticDraftInput): ProgrammaticPreviewResult {
  const validation = validateProgrammaticDraft(input);
  if (validation.errors.length > 0) {
    return { ok: false, errors: validation.errors, pageCount: validation.pageCount };
  }

  let combinations: Array<Record<string, string>> = [{}];
  for (const variable of input.variables) {
    const values = variable.values.map((value) => value.trim()).filter(Boolean);
    combinations = combinations.flatMap((combination) =>
      values.map((value) => ({ ...combination, [variable.key.trim()]: value })),
    );
  }

  const draftRows = combinations.map((values) => ({
    path: expandTemplate(input.urlTemplate.trim(), values, true),
    title: expandTemplate(input.titleTemplate.trim(), values, false),
    metaDescription: expandTemplate(input.metaDescriptionTemplate.trim(), values, false),
    values,
    duplicatePath: false,
  }));
  const pathCounts = new Map<string, number>();
  for (const row of draftRows) pathCounts.set(row.path, (pathCounts.get(row.path) ?? 0) + 1);
  const duplicatePathGroups = [...pathCounts.values()].filter((count) => count > 1).length;
  const rows = draftRows.map((row) => ({ ...row, duplicatePath: (pathCounts.get(row.path) ?? 0) > 1 }));

  return { ok: true, rows, pageCount: rows.length, duplicatePathGroups };
}

function csvCell(value: string): string {
  const guarded = /^[\t\r ]*[=+\-@]/.test(value) ? `'${value}` : value;
  return `"${guarded.replaceAll('"', '""')}"`;
}

export function serializeProgrammaticCsv(rows: ProgrammaticPreviewRow[], variableKeys: string[]): string {
  const headers = ['path', 'title', 'meta description', ...variableKeys];
  const records = rows.map((row) => [
    row.path,
    row.title,
    row.metaDescription,
    ...variableKeys.map((key) => row.values[key] ?? ''),
  ]);
  return [headers, ...records].map((record) => record.map(csvCell).join(',')).join('\r\n');
}
