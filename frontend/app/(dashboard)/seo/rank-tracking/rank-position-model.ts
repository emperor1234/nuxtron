export const MAX_RANK_IMPORT_CHARS = 1_000_000;
export const MAX_RANK_ROWS = 2_000;

export type RankPositionState = 'present' | 'missing' | 'invalid';

export type RankPositionRow = {
  rowNumber: number;
  keyword: string;
  position: number | null;
  positionState: RankPositionState;
  checkedAt: string | null;
  market: string | null;
  url: string | null;
};

export type RankCsvError =
  | 'empty'
  | 'too-large'
  | 'invalid-csv'
  | 'missing-keyword-column'
  | 'missing-position-column';

export type RankCsvResult =
  | { ok: false; reason: RankCsvError }
  | {
      ok: true;
      rows: RankPositionRow[];
      skippedRows: number;
      truncatedRows: number;
      invalidPositionCells: number;
    };

type CsvRow = { values: string[]; logicalRow: number };
type CsvMatrix = { rows: CsvRow[]; totalNonemptyRows: number };

function parseCsvMatrix(text: string): CsvMatrix | null {
  const input = text.replace(/^\uFEFF/, '');
  const rows: CsvRow[] = [];
  let cells: string[] = [];
  let field = '';
  let inQuotes = false;
  let afterQuote = false;
  let logicalRow = 1;
  let totalNonemptyRows = 0;

  const finishField = () => {
    cells.push(field.trim());
    field = '';
    afterQuote = false;
  };
  const finishRow = () => {
    finishField();
    if (cells.some((cell) => cell !== '')) {
      totalNonemptyRows += 1;
      if (rows.length < MAX_RANK_ROWS + 1) rows.push({ values: cells, logicalRow });
    }
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
  return { rows, totalNonemptyRows };
}

function normalizeHeader(value: string): string {
  return value.toLocaleLowerCase().replace(/[^a-z0-9]/g, '');
}

function findColumn(headers: string[], aliases: string[]): number {
  return headers.findIndex((header) => aliases.includes(normalizeHeader(header)));
}

function parsePosition(value: string | undefined): { value: number | null; state: RankPositionState } {
  if (value === undefined || value.trim() === '') return { value: null, state: 'missing' };
  if (!/^\d{1,4}$/.test(value.trim())) return { value: null, state: 'invalid' };
  const position = Number(value.trim());
  if (!Number.isInteger(position) || position < 1 || position > 1_000) {
    return { value: null, state: 'invalid' };
  }
  return { value: position, state: 'present' };
}

function optionalCell(row: CsvRow, index: number): string | null {
  const value = index < 0 ? '' : row.values[index] ?? '';
  return value.trim() ? value.trim().slice(0, 2_000) : null;
}

export function parseRankCsv(text: string): RankCsvResult {
  if (!text.trim()) return { ok: false, reason: 'empty' };
  if (text.length > MAX_RANK_IMPORT_CHARS) return { ok: false, reason: 'too-large' };

  const matrix = parseCsvMatrix(text);
  if (!matrix || matrix.rows.length === 0) return { ok: false, reason: 'invalid-csv' };

  const [headerRow, ...dataRows] = matrix.rows;
  const keywordColumn = findColumn(headerRow.values, ['keyword', 'keywords', 'query', 'searchterm']);
  if (keywordColumn < 0) return { ok: false, reason: 'missing-keyword-column' };

  const positionColumn = findColumn(headerRow.values, [
    'position',
    'rank',
    'currentposition',
    'currentrank',
    'rankingposition',
    'serpposition',
  ]);
  if (positionColumn < 0) return { ok: false, reason: 'missing-position-column' };

  const dateColumn = findColumn(headerRow.values, ['date', 'checkedat', 'observedat', 'snapshotdate', 'reportdate']);
  const marketColumn = findColumn(headerRow.values, ['market', 'location', 'country', 'region', 'locale']);
  const urlColumn = findColumn(headerRow.values, ['url', 'targeturl', 'rankingurl', 'landingpage', 'page']);

  const rows: RankPositionRow[] = [];
  let skippedRows = 0;
  let invalidPositionCells = 0;

  for (const sourceRow of dataRows) {
    const keyword = (sourceRow.values[keywordColumn] ?? '').trim();
    if (!keyword) {
      if (sourceRow.values.some((cell) => cell !== '')) skippedRows += 1;
      continue;
    }

    const position = parsePosition(sourceRow.values[positionColumn]);
    if (position.state === 'invalid') invalidPositionCells += 1;
    rows.push({
      rowNumber: sourceRow.logicalRow,
      keyword: keyword.slice(0, 500),
      position: position.value,
      positionState: position.state,
      checkedAt: optionalCell(sourceRow, dateColumn),
      market: optionalCell(sourceRow, marketColumn),
      url: optionalCell(sourceRow, urlColumn),
    });
  }

  return {
    ok: true,
    rows,
    skippedRows,
    truncatedRows: Math.max(0, matrix.totalNonemptyRows - 1 - MAX_RANK_ROWS),
    invalidPositionCells,
  };
}
