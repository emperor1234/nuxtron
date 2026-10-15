import { describe, expect, it } from 'vitest';
import { CRM_TAB_GROUPS, CRM_TAB_LABELS, getCrmTabGroup, parseCrmTab, type CrmTab } from './crm-nav';

describe('CRM navigation', () => {
  it('keeps every retained customer destination in exactly one task-oriented group', () => {
    const tabs = CRM_TAB_GROUPS.flatMap((group) => group.tabs);
    const expected: CrmTab[] = [
      'overview',
      'contacts',
      'companies',
      'deals',
      'activities',
      'leads',
      'tasks',
      'tickets',
      'campaigns',
      'segments',
      'notes',
      'quotes',
      'invoices',
      'sequences',
      'projects',
      'reports',
    ];

    expect(tabs).toHaveLength(expected.length);
    expect(new Set(tabs).size).toBe(expected.length);
    expect([...tabs].sort()).toEqual([...expected].sort());
  });

  it('keeps the navigation customer-facing and labels every page', () => {
    const tabs = CRM_TAB_GROUPS.flatMap((group) => group.tabs);

    expect(CRM_TAB_GROUPS.map((group) => group.label)).toEqual([
      'Core',
      'Service',
      'Growth',
      'Commercial',
      'Work',
    ]);
    expect(tabs).not.toContain('workflows');
    expect(tabs).not.toContain('extensions');
    expect(tabs).not.toContain('enterprise');
    expect(tabs).not.toContain('settings');
    expect(tabs.every((tab) => CRM_TAB_LABELS[tab].trim().length > 0)).toBe(true);
  });

  it('parses only known customer tabs and resolves their group', () => {
    expect(parseCrmTab('tickets')).toBe('tickets');
    expect(parseCrmTab('enterprise')).toBeNull();
    expect(parseCrmTab('__proto__')).toBeNull();
    expect(parseCrmTab(null)).toBeNull();
    expect(getCrmTabGroup('tickets')).toBe('Service');
    expect(getCrmTabGroup('reports')).toBe('Work');
  });
});
