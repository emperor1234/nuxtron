import { describe, expect, it } from 'vitest';
import { createSearchObservation, searchObservationsCsv, summarizeObservationTrends, type SearchObservation } from './observation-log-model';

const base = {
  query: 'workflow software',
  source: 'Google',
  observedAtLocal: '2026-10-12T10:00',
  position: '10',
  aiSurface: 'not-checked',
};

function observation(id: string, observedAt: string, position: number | null, source: SearchObservation['source'] = 'Google'): SearchObservation {
  return { id, query: 'workflow software', source, observedAt, position, aiSurface: 'not-checked' };
}

describe('manual search observation model', () => {
  it('requires actual user-entered query/source/time and distinguishes unknown AI coverage', () => {
    expect(createSearchObservation(base, 'entry-1')).toMatchObject({
      id: 'entry-1', query: 'workflow software', source: 'Google', position: 10, aiSurface: 'not-checked',
    });
    expect(() => createSearchObservation({ ...base, query: ' ' }, 'entry-2')).toThrow(/enter the search query/i);
    expect(() => createSearchObservation({ ...base, source: '' }, 'entry-2')).toThrow(/choose the search source/i);
    expect(() => createSearchObservation({ ...base, position: '0' }, 'entry-2')).toThrow(/from 1 to 1000/i);
  });

  it('computes an improvement only from two dated ranks for the same query and source', () => {
    const trends = summarizeObservationTrends([
      observation('older', '2026-10-12T10:00:00.000Z', 10),
      observation('newer', '2026-10-13T10:00:00.000Z', 6),
      observation('other-source', '2026-10-13T11:00:00.000Z', 2, 'Bing'),
    ]);
    const google = trends.find((trend) => trend.source === 'Google');
    const bing = trends.find((trend) => trend.source === 'Bing');
    expect(google?.positionsImprovedBy).toBe(4);
    expect(google?.observationCount).toBe(2);
    expect(bing?.positionsImprovedBy).toBeNull();
  });

  it('keeps missing rank data from creating a false trend and exports formula-safe CSV', () => {
    const observations = [observation('older', '2026-10-12T10:00:00.000Z', null), observation('newer', '2026-10-13T10:00:00.000Z', 8)];
    expect(summarizeObservationTrends(observations)[0].positionsImprovedBy).toBeNull();
    const malicious = [{ ...observations[0], query: '=HYPERLINK("https://example.test")' }];
    expect(searchObservationsCsv(malicious)).toContain("'=HYPERLINK(");
  });
});
