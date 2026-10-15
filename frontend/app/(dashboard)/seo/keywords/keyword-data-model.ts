export const MAX_KEYWORD_IMPORT_CHARS = 1_000_000;
export const MAX_KEYWORD_ROWS = 2_000;

export type KeywordMetricState = 'present' | 'missing' | 'invalid';

export type KeywordDataRow = {
  rowNumber: number;
  keyword: string;
  volume: number | null;
  volumeState: KeywordMetricState;
  difficulty: number | null;
  difficultyState: KeywordMetricState;
  intent: string | null;
};

export type KeywordCsvError = 'empty' | 'too-large' | 'invalid-csv' | 'missing-keyword-column';

export type KeywordCsvResult =
  | { ok: false; reason: KeywordCsvError }
  | {
      ok: true;
      rows: KeywordDataRow[];
      skippedRows: number;
      truncatedRows: number;
      invalidMetricCells: number;
    };

type CsvRow = { values: string[]; logicalRow: number };

function parseCsvMatrix(text: string): CsvRow[] | null {
  const input = text.replace(/^\uFEFF/, '');
  const rows: CsvRow[] = [];
  let cells: string[] = [];
  let field = '';
  let inQuotes = false;
  let afterQuote = false;
  let logicalRow = 1;

  const finishField = () => {
    cells.push(field.trim());
    field = '';
    afterQuote = false;
  };
  const finishRow = () => {
    finishField();
    if (cells.some((cell) => cell !== '')) rows.push({ values: cells, logicalRow });
    cells = [];
    logicalRow += 1;
  };

  for (let index = 0; index < input.length; index += 1) {
    const character = input[index];
    if (inQuotes) {
      if (character === '"' && input[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        inQuotes = false;
        afterQuote = true;
      } else {
        field += character;
      }
      continue;
    }

    if (afterQuote && character !== ',' && character !== '\n' && character !== '\r' && !/\s/.test(character)) {
      return null;
    }
    if (character === '"') {
      if (field.trim() !== '' || afterQuote) return null;
      field = '';
      inQuotes = true;
    } else if (character === ',') {
      finishField();
    } else if (character === '\n' || character === '\r') {
      if (character === '\r' && input[index + 1] === '\n') index += 1;
      finishRow();
    } else {
      field += character;
    }
  }

  if (inQuotes) return null;
  if (cells.length > 0 || field !== '' || afterQuote) finishRow();
  return rows;
}

function normalizeHeader(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function findColumn(headers: string[], aliases: string[]): number {
  return headers.findIndex((header) => aliases.includes(normalizeHeader(header)));
}

function parseMetric(value: string | undefined, kind: 'volume' | 'difficulty'):
  | { value: number; state: 'present' }
  | { value: null; state: 'missing' | 'invalid' } {
  if (value === undefined || value.trim() === '') return { value: null, state: 'missing' };
  const normalized = kind === 'difficulty' ? value.trim().replace(/%$/, '') : value.trim();
  if (!/^\d+(?:,\d{3})*(?:\.\d+)?$/.test(normalized)) return { value: null, state: 'invalid' };
  const number = Number(normalized.replace(/,/g, ''));
  if (!Number.isFinite(number) || (kind === 'difficulty' && number > 100)) {
    return { value: null, state: 'invalid' };
  }
  return { value: number, state: 'present' };
}

export function parseKeywordCsv(text: string): KeywordCsvResult {
  if (!text.trim()) return { ok: false, reason: 'empty' };
  if (text.length > MAX_KEYWORD_IMPORT_CHARS) return { ok: false, reason: 'too-large' };

  const parsedRows = parseCsvMatrix(text);
  if (!parsedRows || parsedRows.length === 0) return { ok: false, reason: 'invalid-csv' };

  const [headerRow, ...dataRows] = parsedRows;
  const keywordColumn = findColumn(headerRow.values, ['keyword', 'keywords', 'query', 'searchterm']);
  if (keywordColumn < 0) return { ok: false, reason: 'missing-keyword-column' };

  const volumeColumn = findColumn(headerRow.values, [
    'volume', 'searchvolume', 'monthlysearches', 'averagemonthlysearches',
  ]);
  const difficultyColumn = findColumn(headerRow.values, [
    'difficulty', 'keyworddifficulty', 'kd',
  ]);
  const intentColumn = findColumn(headerRow.values, ['intent', 'searchintent']);

  const rows: KeywordDataRow[] = [];
  let skippedRows = 0;
  let invalidMetricCells = 0;
  let validRowCount = 0;

  for (const sourceRow of dataRows) {
    const keyword = (sourceRow.values[keywordColumn] ?? '').trim();
    if (!keyword) {
      if (sourceRow.values.some((cell) => cell !== '')) skippedRows += 1;
      continue;
    }

    validRowCount += 1;
    const volume = parseMetric(volumeColumn < 0 ? undefined : sourceRow.values[volumeColumn], 'volume');
    const difficulty = parseMetric(
      difficultyColumn < 0 ? undefined : sourceRow.values[difficultyColumn],
      'difficulty',
    );
    if (volume.state === 'invalid') invalidMetricCells += 1;
    if (difficulty.state === 'invalid') invalidMetricCells += 1;
    if (rows.length < MAX_KEYWORD_ROWS) {
      const intentValue = intentColumn < 0 ? undefined : sourceRow.values[intentColumn];
      rows.push({
        rowNumber: sourceRow.logicalRow,
        keyword: keyword.slice(0, 500),
        volume: volume.value,
        volumeState: volume.state,
        difficulty: difficulty.value,
        difficultyState: difficulty.state,
        intent: intentValue?.trim() ? intentValue.trim().slice(0, 120) : null,
      });
    }
  }

  return {
    ok: true,
    rows,
    skippedRows,
    truncatedRows: Math.max(0, validRowCount - rows.length),
    invalidMetricCells,
  };
}
