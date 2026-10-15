import { describe, expect, it } from 'vitest';
import {
  buildProgrammaticPreview,
  PROGRAMMATIC_LIMITS,
  serializeProgrammaticCsv,
  validateProgrammaticDraft,
  type ProgrammaticDraftInput,
} from './programmatic-model';

const validDraft: ProgrammaticDraftInput = {
  urlTemplate: '/areas/[city]/[service]',
  titleTemplate: '[service] in [city]',
  metaDescriptionTemplate: 'Compare [service] options in [city].',
  variables: [
    { key: 'city', values: ['New York', 'Austin'] },
    { key: 'service', values: ['Plumbing', 'Electrical'] },
  ],
};

describe('Programmatic SEO local draft preview', () => {
  it('expands only the supplied matrix and produces relative paths without business estimates', () => {
    const result = buildProgrammaticPreview(validDraft);
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    expect(result.pageCount).toBe(4);
    expect(result.rows[0]).toMatchObject({
      path: '/areas/new-york/plumbing',
      title: 'Plumbing in New York',
      metaDescription: 'Compare Plumbing options in New York.',
      values: { city: 'New York', service: 'Plumbing' },
      duplicatePath: false,
    });
    expect(result.rows[0]).not.toHaveProperty('estimatedTraffic');
    expect(result.rows[0]).not.toHaveProperty('score');
  });

  it('starts invalid when templates or real user-supplied values are missing', () => {
    const validation = validateProgrammaticDraft({
      urlTemplate: '',
      titleTemplate: '',
      metaDescriptionTemplate: '',
      variables: [{ key: '', values: [] }],
    });
    expect(validation.errors.length).toBeGreaterThan(0);
    expect(validation.pageCount).toBe(0);
  });

  it('rejects unknown template tokens, duplicate keys, and unsafe relative paths', () => {
    const validation = validateProgrammaticDraft({
      ...validDraft,
      urlTemplate: '/../[unknown]',
      variables: [
        { key: 'city', values: ['Austin'] },
        { key: 'city', values: ['Boston'] },
      ],
    });
    expect(validation.errors.some((error) => /relative path/i.test(error))).toBe(true);
    expect(validation.errors.some((error) => /no matching variable/i.test(error))).toBe(true);
    expect(validation.errors.some((error) => /repeated/i.test(error))).toBe(true);
  });

  it('caps the cartesian product before allocating an oversized preview', () => {
    const validation = validateProgrammaticDraft({
      ...validDraft,
      variables: [
        { key: 'city', values: Array.from({ length: 11 }, (_, index) => `City ${index}`) },
        { key: 'service', values: Array.from({ length: 10 }, (_, index) => `Service ${index}`) },
      ],
    });
    expect(validation.pageCount).toBe(PROGRAMMATIC_LIMITS.variants + 1);
    expect(validation.errors.some((error) => /more than 100 variants/i.test(error))).toBe(true);
  });

  it('flags URL collisions rather than silently deduplicating or inventing metrics', () => {
    const result = buildProgrammaticPreview({
      ...validDraft,
      urlTemplate: '/services',
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.duplicatePathGroups).toBe(1);
    expect(result.rows.every((row) => row.duplicatePath)).toBe(true);
  });

  it('quotes CSV cells and neutralizes spreadsheet formula prefixes', () => {
    const result = buildProgrammaticPreview({
      ...validDraft,
      titleTemplate: '=HYPERLINK("https://bad.example") [city]',
      variables: [{ key: 'city', values: ['Austin'] }],
      urlTemplate: '/[city]',
      metaDescriptionTemplate: 'A safe draft for [city].',
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const csv = serializeProgrammaticCsv(result.rows, ['city']);
    expect(csv).toContain("'=HYPERLINK(\"\"https://bad.example\"\") Austin");
    expect(csv.split('\r\n')).toHaveLength(2);
  });
});
