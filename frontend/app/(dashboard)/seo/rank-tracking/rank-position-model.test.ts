import { describe, expect, it } from 'vitest';
import { MAX_RANK_IMPORT_CHARS, MAX_RANK_ROWS, parseRankCsv } from './rank-position-model';

describe('parseRankCsv', () => {
  it('preserves source-provided rank, date, market, URL, and quoted keyword values', () => {
    const result = parseRankCsv(
      'keyword,position,checked_at,market,url\n"seo, software",7,2026-10-13,US,https://example.com/seo',
    );

    expect(result).toEqual({
      ok: true,
      rows: [
        {
          rowNumber: 2,
          keyword: 'seo, software',
          position: 7,
          positionState: 'present',
          checkedAt: '2026-10-13',
          market: 'US',
          url: 'https://example.com/seo',
        },
      ],
      skippedRows: 0,
      truncatedRows: 0,
      invalidPositionCells: 0,
    });
  });

  it('keeps missing and invalid positions explicit instead of substituting values', () => {
    const result = parseRankCsv('keyword,rank\nmissing,\ninvalid,0\nvalid,100');
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.rows.map((row) => [row.position, row.positionState])).toEqual([
      [null, 'missing'],
      [null, 'invalid'],
      [100, 'present'],
    ]);
    expect(result.invalidPositionCells).toBe(1);
  });

  it('requires keyword and rank columns and rejects malformed CSV quoting', () => {
    expect(parseRankCsv('position\n1')).toEqual({ ok: false, reason: 'missing-keyword-column' });
    expect(parseRankCsv('keyword\nseo')).toEqual({ ok: false, reason: 'missing-position-column' });
    expect(parseRankCsv('keyword,position\n"broken,2')).toEqual({ ok: false, reason: 'invalid-csv' });
  });

  it('bounds source text and retained rows while reporting additional source rows', () => {
    expect(parseRankCsv(`keyword,position\n${'x'.repeat(MAX_RANK_IMPORT_CHARS)}`)).toEqual({
      ok: false,
      reason: 'too-large',
    });

    const rows = Array.from({ length: MAX_RANK_ROWS + 3 }, (_, index) => `query-${index},${index + 1}`);
    const result = parseRankCsv(`keyword,position\n${rows.join('\n')}`);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.rows).toHaveLength(MAX_RANK_ROWS);
    expect(result.truncatedRows).toBe(3);
  });
});
