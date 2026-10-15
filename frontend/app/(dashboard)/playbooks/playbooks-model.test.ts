import { describe, expect, it } from 'vitest';
import {
  filterPlaybooks,
  formatPlaybookDate,
  parsePlaybookCatalog,
  parsePlaybookRuns,
  playbookRunStatusLabel,
} from './playbooks-model';

const catalogItem = {
  id: 'pb-builtin-001',
  name: 'Welcome Sequence',
  vertical: 'all',
  description: 'A template definition for onboarding.',
  steps: ['Send welcome message', 'Review engagement'],
  integrations: ['email', 'crm'],
  built_in: true,
  time_to_value_days: 1,
};

describe('Playbooks model', () => {
  it('accepts a real empty catalog and normalizes a valid definition', () => {
    expect(parsePlaybookCatalog({ total: 0, playbooks: [] })).toEqual([]);
    expect(parsePlaybookCatalog({ total: 1, playbooks: [catalogItem] })).toEqual([{
      id: 'pb-builtin-001',
      name: 'Welcome Sequence',
      vertical: 'all',
      description: 'A template definition for onboarding.',
      steps: ['Send welcome message', 'Review engagement'],
      integrations: ['email', 'crm'],
      builtIn: true,
      timeToValueDays: 1,
    }]);
  });

  it('rejects incomplete catalog envelopes, malformed identifiers, duplicate IDs, and malformed steps', () => {
    expect(parsePlaybookCatalog({ playbooks: [] })).toBeNull();
    expect(parsePlaybookCatalog({ total: 1, playbooks: [{ ...catalogItem, id: '../bad' }] })).toBeNull();
    expect(parsePlaybookCatalog({ total: 2, playbooks: [catalogItem, catalogItem] })).toBeNull();
    expect(parsePlaybookCatalog({ total: 1, playbooks: [{ ...catalogItem, steps: ['ok', null] }] })).toBeNull();
  });

  it('keeps valid zero step counts distinct from missing metrics', () => {
    const parsed = parsePlaybookRuns({
      total: 2,
      runs: [
        { id: 'run-zero', playbook_id: 'pb-builtin-001', playbook_name: 'Welcome Sequence', dry_run: true, status: 'dry_run_preview', steps_total: 0, steps_completed: 0, created_at: '2026-10-12T10:00:00Z' },
        { id: 'run-unknown', playbook_id: 'pb-builtin-001', playbook_name: 'Welcome Sequence', dry_run: false, status: 'scheduled' },
      ],
    });
    expect(parsed?.[0].stepsTotal).toBe(0);
    expect(parsed?.[0].stepsCompleted).toBe(0);
    expect(parsed?.[1].stepsTotal).toBeNull();
    expect(parsed?.[1].stepsCompleted).toBeNull();
    expect(playbookRunStatusLabel(parsed![0])).toBe('Preview record — no steps executed');
    expect(playbookRunStatusLabel(parsed![1])).toBe('Scheduled — not executed');
  });

  it('rejects malformed run identifiers and negative or fractional step counts', () => {
    const base = { id: 'run-1', playbook_id: 'pb-builtin-001', playbook_name: 'Welcome Sequence', dry_run: false, status: 'scheduled' };
    expect(parsePlaybookRuns({ total: 1, runs: [{ ...base, id: '' }] })).toBeNull();
    expect(parsePlaybookRuns({ total: 1, runs: [{ ...base, steps_total: -1 }] })).toBeNull();
    expect(parsePlaybookRuns({ total: 1, runs: [{ ...base, steps_completed: 1.5 }] })).toBeNull();
  });

  it('filters by search and vertical and formats invalid run dates as unavailable', () => {
    const definitions = parsePlaybookCatalog({
      total: 2,
      playbooks: [catalogItem, { ...catalogItem, id: 'pb-saas', name: 'Lead Review', vertical: 'saas', integrations: ['crm'] }],
    })!;
    expect(filterPlaybooks(definitions, 'crm', 'saas').map((item) => item.id)).toEqual(['pb-saas']);
    expect(filterPlaybooks(definitions, 'nothing', 'all')).toEqual([]);
    expect(formatPlaybookDate('not-a-date')).toBeNull();
    expect(formatPlaybookDate(null)).toBeNull();
  });
});
