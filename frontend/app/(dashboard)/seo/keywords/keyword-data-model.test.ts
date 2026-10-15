import { describe, expect, it } from 'vitest';
import {
  MAX_KEYWORD_IMPORT_CHARS,
  MAX_KEYWORD_ROWS,
  parseKeywordCsv,
} from './keyword-data-model';

describe('parseKeywordCsv', () => {
  it('preserves only metrics supplied in a quoted CSV export', () => {
    const result = parseKeywordCsv(
      '\uFEFFKeyword,Search Volume,Keyword Difficulty,Search Intent\r\n"crm, enterprise","1,200",46%,commercial\r\ncrm guide,,,informational',
    );

    expect(result).toEqual({
      ok: true,
      rows: [
        {
          rowNumber: 2,
          keyword: 'crm, enterprise',
          volume: 1200,
          volumeState: 'present',
          difficulty: 46,
          difficultyState: 'present',
          intent: 'commercial',
        },
        {
          rowNumber: 3,
          keyword: 'crm guide',
          volume: null,
          volumeState: 'missing',
          difficulty: null,
          difficultyState: 'missing',
          intent: 'informational',
        },
      ],
      skippedRows: 0,
      truncatedRows: 0,
      invalidMetricCells: 0,
    });
  });

  it('distinguishes a true header-only export from malformed input', () => {
    expect(parseKeywordCsv('keyword,volume,difficulty')).toMatchObject({ ok: true, rows: [] });
    expect(parseKeywordCsv('')).toEqual({ ok: false, reason: 'empty' });
    expect(parseKeywordCsv('term,volume\ncrm,10')).toEqual({ ok: false, reason: 'missing-keyword-column' });
  });

  it('rejects malformed quoting rather than guessing row boundaries', () => {
    expect(parseKeywordCsv('keyword,volume\n"unfinished,10')).toEqual({ ok: false, reason: 'invalid-csv' });
    expect(parseKeywordCsv('keyword,volume\ncrm" plus,10')).toEqual({ ok: false, reason: 'invalid-csv' });
  });

  it('retains rows but marks absent or invalid numeric cells instead of inventing values', () => {
    const result = parseKeywordCsv('keyword,volume,kd\ncrm,1.2k,101\nseo,,unknown');
    expect(result).toMatchObject({ ok: true, invalidMetricCells: 3 });
    if (!result.ok) throw new Error('Expected valid CSV');
    expect(result.rows.map((row) => [row.volume, row.volumeState, row.difficulty, row.difficultyState])).toEqual([
      [null, 'invalid', null, 'invalid'],
      [null, 'missing', null, 'invalid'],
    ]);
  });

  it('caps input size and output rows explicitly', () => {
    expect(parseKeywordCsv(`keyword\n${'x'.repeat(MAX_KEYWORD_IMPORT_CHARS)}`)).toEqual({
      ok: false,
      reason: 'too-large',
    });

    const body = Array.from({ length: MAX_KEYWORD_ROWS + 3 }, (_, index) => `keyword ${index + 1}`).join('\n');
    const result = parseKeywordCsv(`keyword\n${body}`);
    expect(result).toMatchObject({ ok: true, rows: expect.any(Array), truncatedRows: 3 });
    if (!result.ok) throw new Error('Expected valid CSV');
    expect(result.rows).toHaveLength(MAX_KEYWORD_ROWS);
  });
});
