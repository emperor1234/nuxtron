export type CrmTab =
  | 'overview'
  | 'contacts'
  | 'companies'
  | 'deals'
  | 'activities'
  | 'leads'
  | 'tasks'
  | 'tickets'
  | 'campaigns'
  | 'segments'
  | 'notes'
  | 'quotes'
  | 'invoices'
  | 'sequences'
  | 'projects'
  | 'reports';

export type CrmTabGroup = 'Core' | 'Service' | 'Growth' | 'Commercial' | 'Work';

export const CRM_TAB_GROUPS: ReadonlyArray<{ label: CrmTabGroup; tabs: readonly CrmTab[] }> = [
  { label: 'Core', tabs: ['overview', 'contacts', 'companies', 'deals', 'activities', 'leads', 'notes'] },
  { label: 'Service', tabs: ['tasks', 'tickets'] },
  { label: 'Growth', tabs: ['campaigns', 'segments', 'sequences'] },
  { label: 'Commercial', tabs: ['quotes', 'invoices'] },
  { label: 'Work', tabs: ['projects', 'reports'] },
];

export const CRM_TAB_LABELS: Readonly<Record<CrmTab, string>> = {
  overview: 'Overview',
  contacts: 'Contacts',
  companies: 'Companies',
  deals: 'Deals',
  activities: 'Activities',
  leads: 'Leads',
  tasks: 'Tasks',
  tickets: 'Support',
  campaigns: 'Campaigns',
  segments: 'Segments',
  notes: 'Notes',
  quotes: 'Quotes',
  invoices: 'Invoices',
  sequences: 'Sequences',
  projects: 'Projects',
  reports: 'Reports',
};

export function parseCrmTab(value: string | null): CrmTab | null {
  return value !== null && Object.prototype.hasOwnProperty.call(CRM_TAB_LABELS, value) ? (value as CrmTab) : null;
}

export function getCrmTabGroup(tab: CrmTab): CrmTabGroup {
  return CRM_TAB_GROUPS.find((group) => group.tabs.includes(tab))?.label ?? 'Core';
}
