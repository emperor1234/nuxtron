import { describe, expect, it } from 'vitest';
import { buildEntityGraphDraft, entityGraphDraftCsv } from './entity-graph-model';

describe('buildEntityGraphDraft', () => {
  it('counts only distinct user-provided entities and explicit relationship rows', () => {
    const draft = buildEntityGraphDraft(
      'Brand\nCore Product\nIndustry\nbrand',
      'Brand | offers | Core Product\nCore Product | serves | Industry',
    );

    expect(draft.entities.map((entity) => entity.name)).toEqual(['Brand', 'Core Product', 'Industry']);
    expect(draft.duplicateEntityCount).toBe(1);
    expect(draft.relationships).toHaveLength(2);
    expect(draft.linkedEntityCount).toBe(3);
    expect(draft.connectionCoveragePct).toBe(100);
    expect(draft.unlinkedEntities).toEqual([]);
  });

  it('reports unlinked entities only within the manually entered outline', () => {
    const draft = buildEntityGraphDraft('Brand\nProduct\nUnrelated Topic', 'Brand | offers | Product');

    expect(draft.relationships).toEqual([{ from: 'Brand', type: 'offers', to: 'Product' }]);
    expect(draft.unlinkedEntities).toEqual(['Unrelated Topic']);
    expect(draft.connectionCoveragePct).toBe(67);
  });

  it('counts duplicate relationship rows without adding them twice', () => {
    const draft = buildEntityGraphDraft('A\nB', 'A | related to | B\nA | related to | B');

    expect(draft.relationships).toHaveLength(1);
    expect(draft.duplicateRelationshipCount).toBe(1);
  });

  it('rejects empty entities, malformed rows, unknown endpoints, and self-relationships', () => {
    expect(() => buildEntityGraphDraft('  \n', '')).toThrow(/add at least one entity/i);
    expect(() => buildEntityGraphDraft('A\nB', 'A relates B')).toThrow(/source entity \| relationship \| target entity/i);
    expect(() => buildEntityGraphDraft('A\nB', 'A | relates to | Missing')).toThrow(/must match entities/i);
    expect(() => buildEntityGraphDraft('A', 'A | relates to | A')).toThrow(/cannot relate to itself/i);
  });

  it('escapes spreadsheet formula-like values in CSV export', () => {
    const draft = buildEntityGraphDraft('=HYPERLINK("https://x.invalid")\nTarget', '=HYPERLINK("https://x.invalid") | points to | Target');
    expect(entityGraphDraftCsv(draft)).toContain("'=HYPERLINK");
  });
});
