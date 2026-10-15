'use client';

import { useEffect, useMemo, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { CRM_TAB_GROUPS, CRM_TAB_LABELS, getCrmTabGroup, parseCrmTab, type CrmTab, type CrmTabGroup } from './crm-nav';

// ── Types ─────────────────────────────────────────────────────────────────────

type Stage = 'prospect' | 'qualified' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost';

type Contact = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  phone: string;
  lifecycle_stage: string;
  lead_score: number;
  tags: string[];
  created_at: string;
};
type Company = {
  id: number;
  name: string;
  domain: string;
  industry: string;
  employee_count: number;
  annual_revenue: number;
  created_at: string;
};
type Deal = {
  id: number;
  title: string;
  value: number;
  currency: string;
  stage: Stage;
  probability: number;
  contact_id: number | null;
  company_id: number | null;
  close_date: string | null;
  created_at: string;
};
type Activity = {
  id: number;
  type: string;
  subject: string;
  body: string;
  contact_id: number | null;
  deal_id: number | null;
  created_at: string;
};
type Lead = {
  id: number;
  title: string;
  contact_id: number | null;
  company_id: number | null;
  source: string;
  estimated_value: number;
  status: string;
  score: number;
  assigned_to: string;
  created_at: string;
};
type Task = {
  id: number;
  title: string;
  description: string;
  contact_id: number | null;
  deal_id: number | null;
  due_date: string | null;
  priority: string;
  assigned_to: string;
  type: string;
  status: string;
  created_at: string;
};
type Ticket = {
  id: number;
  ticket_number: string;
  subject: string;
  description: string;
  contact_id: number | null;
  priority: string;
  channel: string;
  status: string;
  escalated: boolean;
  assigned_to: string | null;
  resolution: string | null;
  first_response_deadline: string | null;
  resolution_deadline: string | null;
  created_at: string;
};
type Campaign = {
  id: number;
  name: string;
  type: string;
  subject: string;
  segment_id: number | null;
  status: string;
  sent_count: number;
  open_count: number;
  click_count: number;
  ab_test: boolean;
  created_at: string;
};
type Segment = {
  id: number;
  name: string;
  description: string;
  filters: Record<string, unknown>;
  member_count: number;
  created_at: string;
};
type Note = {
  id: number;
  body: string;
  contact_id: number | null;
  deal_id: number | null;
  company_id: number | null;
  pinned: boolean;
  created_at: string;
};
type Quote = {
  id: number;
  quote_number: string;
  title: string;
  contact_id: number | null;
  deal_id: number | null;
  subtotal: number;
  currency: string;
  status: string;
  valid_until: string | null;
  created_at: string;
};
type CRMInvoice = {
  id: number;
  invoice_number: string;
  title: string;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  created_at: string;
};
type EmailSequence = {
  id: number;
  name: string;
  description: string;
  step_count: number;
  enrollments: number;
  status: string;
  created_at: string;
};
type PipelineRow = { stage: Stage; display: string; probability: number; count: number; total_value: number };
type Summary = {
  contacts: number;
  companies: number;
  deals_total: number;
  deals_open: number;
  deals_won: number;
  pipeline_value: number;
  closed_won_value: number;
  forecast_revenue: number;
  avg_lead_score: number;
  activities: number;
  stage_counts: Record<string, number>;
};
type KPIs = {
  total_contacts: number;
  total_leads: number;
  lead_conversion_rate_pct: number;
  total_deals: number;
  win_rate_pct: number;
  avg_deal_value: number;
  closed_won_value: number;
  open_tickets: number;
  escalated_tickets: number;
  open_tasks: number;
  overdue_tasks: number;
};
type Forecast = {
  weighted_pipeline: number;
  closed_won_total: number;
  outstanding_invoices: number;
  paid_invoices: number;
  monthly_forecast: Record<string, number>;
};
type ExecutiveAnalytics = { charts: { lead_source_breakdown: Record<string, number> } };
type Project = {
  id: number;
  name: string;
  description: string;
  owner: string;
  status: string;
  due_date: string | null;
  created_at: string;
};
type CrmPageData = {
  summary: Summary | null;
  pipeline: PipelineRow[];
  contacts: Contact[];
  companies: Company[];
  deals: Deal[];
  activities: Activity[];
  leads: Lead[];
  tasks: Task[];
  tickets: Ticket[];
  campaigns: Campaign[];
  segments: Segment[];
  notes: Note[];
  quotes: Quote[];
  invoices: CRMInvoice[];
  sequences: EmailSequence[];
  kpis: KPIs | null;
  forecast: Forecast | null;
  executiveAnalytics: ExecutiveAnalytics | null;
  projects: Project[];
  failedSections: string[];
};
const API_BASE = '/api/fastapi';

// Pipeline stages are categories, so they use the categorical series. Only the
// two closed outcomes carry a success/danger meaning.
const STAGE_COLOR: Record<string, string> = {
  prospect: 'var(--series-6)',
  qualified: 'var(--series-2)',
  proposal: 'var(--series-4)',
  negotiation: 'var(--series-1)',
  closed_won: 'var(--success)',
  closed_lost: 'var(--danger)',
};
const PRIORITY_COLOR: Record<string, string> = {
  low: 'var(--neutral)',
  medium: 'var(--warning)',
  high: 'var(--danger)',
  critical: 'var(--danger-ink)',
};

async function apiRequest(path: string, tenantId: string, init?: RequestInit) {
  if (!tenantId.trim()) {
    throw new Error('Workspace context is required. Sign in or select a workspace before loading CRM data.');
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      ...(init?.headers ? Object.fromEntries(new Headers(init.headers).entries()) : {}),
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail ?? `Request failed: ${res.status}`);
  return data;
}

function fmt(value: number, currency = 'USD') {
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value);
  } catch {
    return `$${value.toLocaleString()}`;
  }
}

function fmtCount(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat().format(value) : '—';
}

function fmtOptionalCurrency(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? fmt(value) : '—';
}

function fmtTime(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

type AnalyticsRange = '7d' | '30d' | '90d';

function buildCrmLoadParams(filters: {
  contactsQuery: string;
  contactsStage: string;
  dealsQuery: string;
  dealsStage: string;
  activityTypeFilter: string;
  ticketsStatusFilter: string;
  taskStatusFilter: string;
  analyticsRange: AnalyticsRange;
}) {
  const reportDays = getReportDays(filters.analyticsRange);
  const contactsParams = new URLSearchParams({ limit: '100', offset: '0' });
  if (filters.contactsQuery.trim()) contactsParams.set('q', filters.contactsQuery.trim());
  if (filters.contactsStage.trim()) contactsParams.set('lifecycle_stage', filters.contactsStage.trim());
  const dealsParams = new URLSearchParams({ limit: '100', offset: '0' });
  if (filters.dealsQuery.trim()) dealsParams.set('q', filters.dealsQuery.trim());
  if (filters.dealsStage.trim()) dealsParams.set('stage', filters.dealsStage.trim());
  const activitiesParams = new URLSearchParams({ limit: '100', offset: '0' });
  if (filters.activityTypeFilter.trim()) activitiesParams.set('type', filters.activityTypeFilter.trim());
  const ticketsParams = new URLSearchParams({ limit: '100', offset: '0' });
  if (filters.ticketsStatusFilter.trim()) ticketsParams.set('status', filters.ticketsStatusFilter.trim());
  const tasksParams = new URLSearchParams({ limit: '100', offset: '0' });
  if (filters.taskStatusFilter.trim()) tasksParams.set('status', filters.taskStatusFilter.trim());
  const reportsParams = new URLSearchParams({ days: String(reportDays) });
  return { contactsParams, dealsParams, activitiesParams, ticketsParams, tasksParams, reportsParams };
}

function getReportDays(range: AnalyticsRange): number {
  if (range === '7d') return 7;
  if (range === '30d') return 30;
  return 90;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readCrmArray<T>(
  result: PromiseSettledResult<unknown>,
  field: string,
  label: string,
  markFailed: (label: string) => void
): T[] {
  if (result.status !== 'fulfilled' || !isRecord(result.value) || !Array.isArray(result.value[field])) {
    markFailed(label);
    return [];
  }
  return result.value[field] as T[];
}

function readCrmObject<T extends object>(
  result: PromiseSettledResult<unknown>,
  label: string,
  markFailed: (label: string) => void,
  field?: string
): T | null {
  const payload = result.status === 'fulfilled' && isRecord(result.value) ? result.value : null;
  const value = payload ? (field ? payload[field] : payload) : null;
  if (!isRecord(value)) {
    markFailed(label);
    return null;
  }
  return value as T;
}

async function fetchCrmPageData(params: {
  tenantId: string;
  contactsQuery: string;
  contactsStage: string;
  dealsQuery: string;
  dealsStage: string;
  activityTypeFilter: string;
  ticketsStatusFilter: string;
  taskStatusFilter: string;
  analyticsRange: AnalyticsRange;
}): Promise<CrmPageData> {
  const { contactsParams, dealsParams, activitiesParams, ticketsParams, tasksParams, reportsParams } =
    buildCrmLoadParams(params);

  const requests = await Promise.allSettled([
    apiRequest('/crm/summary', params.tenantId),
    apiRequest(`/crm/contacts?${contactsParams}`, params.tenantId),
    apiRequest('/crm/companies', params.tenantId),
    apiRequest(`/crm/deals?${dealsParams}`, params.tenantId),
    apiRequest(`/crm/activities?${activitiesParams}`, params.tenantId),
    apiRequest('/crm/pipeline', params.tenantId),
    apiRequest('/crm/leads?limit=100', params.tenantId),
    apiRequest(`/crm/tasks?${tasksParams}&limit=100`, params.tenantId),
    apiRequest(`/crm/tickets?${ticketsParams}&limit=100`, params.tenantId),
    apiRequest('/crm/campaigns?limit=100', params.tenantId),
    apiRequest('/crm/segments', params.tenantId),
    apiRequest('/crm/notes?limit=100', params.tenantId),
    apiRequest('/crm/quotes?limit=100', params.tenantId),
    apiRequest('/crm/invoices?limit=100', params.tenantId),
    apiRequest('/crm/email-sequences', params.tenantId),
    apiRequest(`/crm/reports/kpis?${reportsParams.toString()}`, params.tenantId),
    apiRequest(`/crm/reports/forecast?${reportsParams.toString()}`, params.tenantId),
    apiRequest(`/crm/reports/executive-analytics?${reportsParams.toString()}`, params.tenantId),
    apiRequest('/crm/projects', params.tenantId),
  ]);

  const failedSections: string[] = [];
  const markFailed = (label: string) => failedSections.push(label);
  const summary = readCrmObject<Summary>(requests[0], 'Overview', markFailed, 'summary');
  const contacts = readCrmArray<Contact>(requests[1], 'contacts', 'Contacts', markFailed);
  const companies = readCrmArray<Company>(requests[2], 'companies', 'Companies', markFailed);
  const deals = readCrmArray<Deal>(requests[3], 'deals', 'Deals', markFailed);
  const activities = readCrmArray<Activity>(requests[4], 'activities', 'Activities', markFailed);
  const pipeline = readCrmArray<PipelineRow>(requests[5], 'pipeline', 'Pipeline', markFailed);
  const leads = readCrmArray<Lead>(requests[6], 'leads', 'Leads', markFailed);
  const tasks = readCrmArray<Task>(requests[7], 'tasks', 'Tasks', markFailed);
  const tickets = readCrmArray<Ticket>(requests[8], 'tickets', 'Support', markFailed);
  const campaigns = readCrmArray<Campaign>(requests[9], 'campaigns', 'Campaigns', markFailed);
  const segments = readCrmArray<Segment>(requests[10], 'segments', 'Segments', markFailed);
  const notes = readCrmArray<Note>(requests[11], 'notes', 'Notes', markFailed);
  const quotes = readCrmArray<Quote>(requests[12], 'quotes', 'Quotes', markFailed);
  const invoices = readCrmArray<CRMInvoice>(requests[13], 'invoices', 'Invoices', markFailed);
  const sequences = readCrmArray<EmailSequence>(requests[14], 'sequences', 'Sequences', markFailed);
  const kpiResponse = requests[15];
  const kpis = readCrmObject<KPIs>(kpiResponse, 'Reports', markFailed, 'kpis');
  const forecast = readCrmObject<Forecast>(requests[16], 'Reports', markFailed);
  const executiveAnalytics = readCrmObject<ExecutiveAnalytics>(requests[17], 'Reports', markFailed);
  const projects = readCrmArray<Project>(requests[18], 'projects', 'Projects', markFailed);

  return {
    summary,
    pipeline,
    contacts,
    companies,
    deals,
    activities,
    leads,
    tasks,
    tickets,
    campaigns,
    segments,
    notes,
    quotes,
    invoices,
    sequences,
    kpis,
    forecast,
    executiveAnalytics,
    projects,
    failedSections: Array.from(new Set(failedSections)),
  };
}

export default function CRMPage() {
  // NOSONAR
  const [tenantId] = useState(resolveSessionTenant);
  const [tab, setTabState] = useState<CrmTab>('overview');
  const [tabGroup, setTabGroup] = useState<CrmTabGroup>('Core');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loadWarning, setLoadWarning] = useState('');
  const [failedSections, setFailedSections] = useState<string[]>([]);
  const [success, setSuccess] = useState('');
  const [analyticsRange, setAnalyticsRange] = useState<AnalyticsRange>('30d');

  function setTab(nextTab: CrmTab) {
    setTabState(nextTab);
    setTabGroup(getCrmTabGroup(nextTab));
    if (typeof window === 'undefined') return;
    const nextUrl = new URL(window.location.href);
    if (nextUrl.searchParams.get('tab') === nextTab) return;
    nextUrl.searchParams.set('tab', nextTab);
    window.history.pushState(window.history.state, '', `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
  }

  // Core CRM
  const [summary, setSummary] = useState<Summary | null>(null);
  const [pipeline, setPipeline] = useState<PipelineRow[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);

  // New modules
  const [leads, setLeads] = useState<Lead[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [invoices, setInvoices] = useState<CRMInvoice[]>([]);
  const [sequences, setSequences] = useState<EmailSequence[]>([]);
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [executiveAnalytics, setExecutiveAnalytics] = useState<ExecutiveAnalytics | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  // Filters
  const [contactsQuery, setContactsQuery] = useState('');
  const [contactsStage, setContactsStage] = useState('');
  const [dealsQuery, setDealsQuery] = useState('');
  const [dealsStage, setDealsStage] = useState('');
  const [activityTypeFilter, setActivityTypeFilter] = useState('');
  const [ticketsStatusFilter, setTicketsStatusFilter] = useState('');
  const [taskStatusFilter, setTaskStatusFilter] = useState('');

  // Forms
  const [contactForm, setContactForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    company: '',
    phone: '',
    lifecycle_stage: 'lead',
  });
  const [companyForm, setCompanyForm] = useState({
    name: '',
    domain: '',
    industry: '',
    employee_count: '0',
    annual_revenue: '0',
  });
  const [dealForm, setDealForm] = useState({
    title: '',
    value: '0',
    currency: 'USD',
    stage: 'prospect' as Stage,
    contact_id: '',
    company_id: '',
    close_date: '',
  });
  const [activityForm, setActivityForm] = useState({
    type: 'note',
    subject: '',
    body: '',
    contact_id: '',
    deal_id: '',
  });
  const [leadForm, setLeadForm] = useState({
    title: '',
    source: 'website',
    estimated_value: '0',
    status: 'new',
    score: '0',
    assigned_to: '',
  });
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    type: 'task',
    assigned_to: '',
    due_date: '',
    contact_id: '',
    deal_id: '',
  });
  const [ticketForm, setTicketForm] = useState({
    subject: '',
    description: '',
    priority: 'medium',
    channel: 'email',
    contact_id: '',
  });
  const [campaignForm, setCampaignForm] = useState({
    name: '',
    type: 'email',
    subject: '',
    body: '',
    ab_test: false,
    variant_b_subject: '',
  });
  const [segmentForm, setSegmentForm] = useState({
    name: '',
    description: '',
    lifecycle_stage: '',
    min_lead_score: '',
  });
  const [noteForm, setNoteForm] = useState({ body: '', contact_id: '', deal_id: '', company_id: '', pinned: false });
  const [quoteForm, setQuoteForm] = useState({
    title: '',
    contact_id: '',
    deal_id: '',
    currency: 'USD',
    valid_until: '',
    notes: '',
    item_desc: '',
    item_qty: '1',
    item_price: '0',
  });
  const [invoiceForm, setInvoiceForm] = useState({
    title: '',
    amount: '0',
    currency: 'USD',
    due_date: '',
    contact_id: '',
  });
  const [sequenceForm, setSequenceForm] = useState({
    name: '',
    description: '',
    step1_subject: '',
    step1_body: '',
    step1_day: '0',
  });
  const [projectForm, setProjectForm] = useState({
    name: '',
    description: '',
    owner: '',
    status: 'planning',
    due_date: '',
  });
  const openDeals = useMemo(() => deals.filter((d) => d.stage !== 'closed_won' && d.stage !== 'closed_lost'), [deals]);


  function sectionState(section: string, count: number, emptyMessage: string) {
    if (loading) return null;
    if (failedSections.includes(section)) {
      return (
        <div role="status" style={{ color: 'var(--muted)' }}>
          {section} data is unavailable. Use Refresh to try again.
        </div>
      );
    }
    if (count === 0) return <div style={{ color: 'var(--muted)' }}>{emptyMessage}</div>;
    return null;
  }

  async function loadData() {
    setLoading(true);
    setError('');
    setLoadWarning('');
    try {
      const data = await fetchCrmPageData({
        tenantId,
        contactsQuery,
        contactsStage,
        dealsQuery,
        dealsStage,
        activityTypeFilter,
        ticketsStatusFilter,
        taskStatusFilter,
        analyticsRange,
      });

      setFailedSections(data.failedSections);
      setSummary(data.summary);
      setPipeline(data.pipeline);
      setContacts(data.contacts);
      setCompanies(data.companies);
      setDeals(data.deals);
      setActivities(data.activities);
      setLeads(data.leads);
      setTasks(data.tasks);
      setTickets(data.tickets);
      setCampaigns(data.campaigns);
      setSegments(data.segments);
      setNotes(data.notes);
      setQuotes(data.quotes);
      setInvoices(data.invoices);
      setSequences(data.sequences);
      setKpis(data.kpis);
      setForecast(data.forecast);
      setExecutiveAnalytics(data.executiveAnalytics);
      setProjects(data.projects);

      if (data.failedSections.length === 0) {
        setLoadWarning('');
      } else if (data.failedSections.length >= 17) {
        setError('Unable to load CRM data right now. Check the FastAPI service and retry.');
      } else {
        setError('');
        setLoadWarning(`Some CRM sections are temporarily unavailable: ${data.failedSections.join(', ')}.`);
      }
    } catch (e) {
      setFailedSections([
        'Overview',
        'Contacts',
        'Companies',
        'Deals',
        'Activities',
        'Pipeline',
        'Leads',
        'Tasks',
        'Support',
        'Campaigns',
        'Segments',
        'Notes',
        'Quotes',
        'Invoices',
        'Sequences',
        'Reports',
        'Projects',
      ]);
      setError(e instanceof Error ? e.message : 'Failed to load CRM data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const syncTabFromUrl = () => {
      const requestedTab = parseCrmTab(new URLSearchParams(window.location.search).get('tab'));
      if (!requestedTab) return;
      setTabState(requestedTab);
      setTabGroup(getCrmTabGroup(requestedTab));
    };

    syncTabFromUrl();
    window.addEventListener('popstate', syncTabFromUrl);
    return () => window.removeEventListener('popstate', syncTabFromUrl);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analyticsRange]);

  function showSuccess(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 2500);
  }

  async function req(path: string, method: string, body?: unknown) {
    setError('');
    try {
      await apiRequest(path, tenantId, { method, body: body ? JSON.stringify(body) : undefined });
      showSuccess('Done');
      await loadData();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
      return false;
    }
  }

  function exportAnalyticsCsv() {
    const quote = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;
    const rows = [
      ...(failedSections.includes('Leads')
        ? []
        : leadSourceBreakdown.map((row) => ['lead_source', row.source, row.count].map(quote).join(','))),
      ...(failedSections.includes('Tasks')
        ? []
        : taskStatusGraph.map((row) => ['task_status', row.label, row.value].map(quote).join(','))),
      ...(failedSections.includes('Support')
        ? []
        : ticketStatusGraph.map((row) => ['ticket_status', row.label, row.value].map(quote).join(','))),
    ];
    if (rows.length === 0) {
      setError('Analytics data is unavailable. Refresh CRM before exporting.');
      return;
    }
    const lines = [['section', 'label', 'value'].map(quote).join(','), ...rows];

    downloadFile(
      `crm-analytics-${analyticsRange}-${new Date().toISOString().slice(0, 10)}.csv`,
      `${lines.join('\n')}\n`,
      'text/csv;charset=utf-8'
    );
    showSuccess('Analytics CSV exported');
  }

  const ps = { minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: '28px 20px 48px' } as const;
  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  } as const;
  const inp = {
    width: '100%',
    padding: '7px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
    boxSizing: 'border-box' as const,
  } as const;
  const btn = {
    border: 'none',
    background: 'var(--brand)',
    color: 'var(--on-brand)',
    borderRadius: 8,
    fontWeight: 700,
    padding: '8px 12px',
    cursor: 'pointer',
  } as const;
  const ghostBtn = {
    ...btn,
    background: 'transparent',
    color: 'var(--text)',
    border: '1px solid var(--line)',
  } as const;
  const dangerBtn = { ...btn, background: 'var(--danger)', color: 'var(--on-status)' } as const;

  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const leadSourceBreakdown = useMemo<Array<{ source: string; count: number }>>(() => {
    const fromAnalytics = executiveAnalytics?.charts.lead_source_breakdown ?? {};
    const analyticsRows = Object.entries(fromAnalytics).map(([source, value]) => ({
      source,
      count: typeof value === 'number' ? value : 0,
    }));
    if (analyticsRows.length) {
      const sortedAnalyticsRows = [...analyticsRows].sort((a, b) => b.count - a.count);
      return sortedAnalyticsRows.slice(0, 8);
    }

    const derived = leads.reduce<Record<string, number>>((acc, lead) => {
      const key = lead.source || 'unknown';
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});

    return Object.entries(derived)
      .map(([source, count]) => ({ source, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [executiveAnalytics, leads]);
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const taskStatusGraph = useMemo(
    () => [
      { label: 'Open', value: tasks.filter((task) => task.status === 'open').length, color: 'var(--info)' },
      {
        label: 'In Progress',
        value: tasks.filter((task) => task.status === 'in_progress').length,
        color: 'var(--info)',
      },
      { label: 'Completed', value: tasks.filter((task) => task.status === 'completed').length, color: 'var(--success)' },
      { label: 'Cancelled', value: tasks.filter((task) => task.status === 'cancelled').length, color: 'var(--warning)' },
    ],
    [tasks]
  );
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const ticketStatusGraph = useMemo(
    () => [
      { label: 'Open', value: tickets.filter((ticket) => ticket.status === 'open').length, color: 'var(--danger)' },
      {
        label: 'In Progress',
        value: tickets.filter((ticket) => ticket.status === 'in_progress').length,
        color: 'var(--warning)',
      },
      { label: 'Resolved', value: tickets.filter((ticket) => ticket.status === 'resolved').length, color: 'var(--success)' },
      { label: 'Closed', value: tickets.filter((ticket) => ticket.status === 'closed').length, color: 'var(--neutral)' },
    ],
    [tickets]
  );
  const activeTabGroup = CRM_TAB_GROUPS.find((group) => group.label === tabGroup) ?? CRM_TAB_GROUPS[0];

  return (
    <div style={ps} aria-busy={loading}>
      <div style={{ maxWidth: 1240, margin: '0 auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 26 }}>CRM</h1>
            <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
              Customer records, pipeline, support, and work tracking for this workspace.
            </p>
          </div>
          <button style={btn} onClick={() => void loadData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </header>

        {loading ? <p role="status" aria-live="polite">Loading CRM workspace data…</p> : null}
        {error ? (
          <div
            role="alert"
            style={{ border: '1px solid var(--danger)', color: 'var(--danger)', borderRadius: 12, padding: 12, marginBottom: 14 }}
          >
            {error}
          </div>
        ) : null}
        {loadWarning ? (
          <div
            role="status"
            style={{ border: '1px solid var(--warning)', color: 'var(--warning)', borderRadius: 12, padding: 12, marginBottom: 14 }}
          >
            {loadWarning}
          </div>
        ) : null}

        {success && (
          <div
            role="status"
            style={{
              ...card,
              marginBottom: 12,
              borderColor: 'color-mix(in oklab, var(--success) 53%, transparent)',
              color: 'var(--success)',
            }}
          >
            {success}
          </div>
        )}

        <nav aria-label="CRM navigation" style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
          <div role="group" aria-label="CRM categories" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {CRM_TAB_GROUPS.map((group) => (
              <button
                key={group.label}
                type="button"
                aria-pressed={group.label === tabGroup}
                style={{
                  ...btn,
                  background: group.label === tabGroup ? 'var(--brand)' : 'transparent',
                  color: group.label === tabGroup ? 'var(--on-brand)' : 'var(--text)',
                  border: group.label === tabGroup ? 'none' : '1px solid var(--line)',
                  fontSize: 12,
                  padding: '6px 10px',
                }}
                onClick={() => {
                  setTabGroup(group.label);
                  setTab(group.tabs[0]);
                }}
              >
                {group.label}
              </button>
            ))}
          </div>
          <div role="group" aria-label={`${activeTabGroup.label} CRM pages`} style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {activeTabGroup.tabs.map((t) => (
              <button
                key={t}
                type="button"
                aria-pressed={t === tab}
                style={{
                  ...btn,
                  background: t === tab ? 'var(--bg-soft)' : 'transparent',
                  color: t === tab ? 'var(--brand)' : 'var(--text)',
                  border: t === tab ? '1px solid var(--brand)' : '1px solid var(--line)',
                  fontSize: 12,
                  padding: '6px 10px',
                }}
                onClick={() => setTab(t)}
              >
                {CRM_TAB_LABELS[t]}
              </button>
            ))}
          </div>
        </nav>

        {/* OVERVIEW */}
        {tab === 'overview' && (
          <section>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
                gap: 10,
                marginBottom: 12,
              }}
            >
              {[
                { label: 'Contacts', val: failedSections.includes('Overview') ? '—' : fmtCount(summary?.contacts) },
                { label: 'Companies', val: failedSections.includes('Overview') ? '—' : fmtCount(summary?.companies) },
                { label: 'Open Deals', val: failedSections.includes('Overview') ? '—' : fmtCount(summary?.deals_open) },
                { label: 'Pipeline', val: failedSections.includes('Overview') ? '—' : fmtOptionalCurrency(summary?.pipeline_value) },
                { label: 'Forecast', val: failedSections.includes('Overview') ? '—' : fmtOptionalCurrency(summary?.forecast_revenue) },
                { label: 'Avg Score', val: failedSections.includes('Overview') ? '—' : fmtCount(summary?.avg_lead_score) },
                { label: 'Leads', val: failedSections.includes('Leads') ? '—' : fmtCount(leads.length) },
                { label: 'Open Tasks', val: failedSections.includes('Tasks') ? '—' : fmtCount(tasks.filter((t) => t.status === 'open').length) },
                { label: 'Open Tickets', val: failedSections.includes('Support') ? '—' : fmtCount(tickets.filter((t) => t.status === 'open').length) },
              ].map(({ label, val }) => (
                <div key={label} role="group" aria-label={`${label}: ${val}`} style={card}>
                  <div style={{ color: 'var(--muted)', fontSize: 11 }}>{label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{val}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Pipeline Stages</h3>
                {sectionState('Pipeline', pipeline.length, 'No pipeline stages are recorded for this workspace.')}
                {pipeline.map((row) => (
                  <div key={row.stage} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                      <span>
                        {row.display} ({row.count})
                      </span>
                      <span>{fmt(row.total_value)}</span>
                    </div>
                    <div style={{ height: 7, borderRadius: 999, background: 'var(--line)', overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.min(100, row.probability)}%`,
                          background: STAGE_COLOR[row.stage] ?? 'var(--brand)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Recent Activities</h3>
                {activities.slice(0, 8).map((a) => (
                  <div key={a.id} style={{ borderBottom: '1px solid var(--line)', padding: '5px 0' }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {a.type.toUpperCase()} - {fmtTime(a.created_at)}
                    </div>
                    <div style={{ fontSize: 13 }}>{a.subject}</div>
                  </div>
                ))}
                {sectionState('Activities', activities.length, 'No activities are recorded for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* CONTACTS */}
        {tab === 'contacts' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Contact</h3>
              {(['first_name', 'last_name', 'email', 'company', 'phone'] as const).map((f) => (
                <input
                  key={f}
                  style={inp}
                  aria-label={f.replace('_', ' ')}
                  placeholder={f.replace('_', ' ')}
                  value={contactForm[f]}
                  onChange={(e) => setContactForm((s) => ({ ...s, [f]: e.target.value }))}
                />
              ))}
              <select
                style={inp}
                aria-label="Lifecycle stage"
                value={contactForm.lifecycle_stage}
                onChange={(e) => setContactForm((s) => ({ ...s, lifecycle_stage: e.target.value }))}
              >
                {['lead', 'subscriber', 'mql', 'sql', 'opportunity', 'customer'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/contacts', 'POST', contactForm).then(
                    (ok) =>
                      ok &&
                      setContactForm({
                        email: '',
                        first_name: '',
                        last_name: '',
                        company: '',
                        phone: '',
                        lifecycle_stage: 'lead',
                      })
                  )
                }
              >
                Create Contact
              </button>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button style={ghostBtn} onClick={() => void req('/crm/contacts/dedupe', 'POST', { dry_run: true })}>
                  Dedupe Preview
                </button>
                <button style={dangerBtn} onClick={() => void req('/crm/contacts/dedupe', 'POST', { dry_run: false })}>
                  Run Dedupe
                </button>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {(['contacts', 'companies', 'deals', 'activities'] as const).map((r) => (
                  <button
                    key={r}
                    style={ghostBtn}
                    onClick={async () => {
                      const res = await apiRequest(`/crm/export?resource=${r}&format=csv`, tenantId).catch(() => null);
                      if (res?.csv) {
                        await navigator.clipboard.writeText(res.csv as string);
                        showSuccess(`${r} CSV copied`);
                      }
                    }}
                  >
                    Export {r}
                  </button>
                ))}
              </div>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Contacts ({contacts.length})</h3>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input
                  style={inp}
                  placeholder="Search name/email"
                  value={contactsQuery}
                  onChange={(e) => setContactsQuery(e.target.value)}
                />
                <input
                  style={inp}
                  placeholder="Stage filter"
                  value={contactsStage}
                  onChange={(e) => setContactsStage(e.target.value)}
                />
                <button style={btn} onClick={() => void loadData()}>
                  Apply
                </button>
              </div>
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {contacts.map((c) => (
                  <div key={c.id} style={{ borderBottom: '1px solid var(--line)', padding: '7px 0' }}>
                    <div style={{ fontWeight: 700 }}>
                      {c.first_name} {c.last_name} <span style={{ fontSize: 11, color: 'var(--muted)' }}>#{c.id}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {c.email} - score {c.lead_score} - {c.lifecycle_stage}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {c.company} - {fmtTime(c.created_at)}
                    </div>
                  </div>
                ))}
                {sectionState('Contacts', contacts.length, contactsQuery.trim() || contactsStage ? 'No contacts match the current filters.' : 'No contacts have been added to this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* COMPANIES */}
        {tab === 'companies' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Company</h3>
              {(['name', 'domain', 'industry'] as const).map((f) => (
                <input
                  key={f}
                  style={inp}
                  placeholder={f}
                  value={companyForm[f]}
                  onChange={(e) => setCompanyForm((s) => ({ ...s, [f]: e.target.value }))}
                />
              ))}
              <input
                style={inp}
                type="number"
                placeholder="Employees"
                value={companyForm.employee_count}
                onChange={(e) => setCompanyForm((s) => ({ ...s, employee_count: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                placeholder="Annual Revenue"
                value={companyForm.annual_revenue}
                onChange={(e) => setCompanyForm((s) => ({ ...s, annual_revenue: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/companies', 'POST', {
                    ...companyForm,
                    employee_count: Number.parseInt(companyForm.employee_count) || 0,
                    annual_revenue: Number.parseFloat(companyForm.annual_revenue) || 0,
                  }).then(
                    (ok) =>
                      ok &&
                      setCompanyForm({ name: '', domain: '', industry: '', employee_count: '0', annual_revenue: '0' })
                  )
                }
              >
                Create Company
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Companies ({companies.length})</h3>
              <div style={{ maxHeight: 420, overflow: 'auto' }}>
                {companies.map((c) => (
                  <div key={c.id} style={{ borderBottom: '1px solid var(--line)', padding: '7px 0' }}>
                    <div style={{ fontWeight: 700 }}>{c.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {c.domain} - {c.industry} - {c.employee_count} emp - {fmt(c.annual_revenue)}/yr
                    </div>
                  </div>
                ))}
                {sectionState('Companies', companies.length, 'No companies have been added to this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* DEALS */}
        {tab === 'deals' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Deal</h3>
              <input
                style={inp}
                placeholder="Deal Title"
                value={dealForm.title}
                onChange={(e) => setDealForm((s) => ({ ...s, title: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                placeholder="Value"
                value={dealForm.value}
                onChange={(e) => setDealForm((s) => ({ ...s, value: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Currency"
                value={dealForm.currency}
                onChange={(e) => setDealForm((s) => ({ ...s, currency: e.target.value }))}
              />
              <select
                style={inp}
                value={dealForm.stage}
                onChange={(e) => setDealForm((s) => ({ ...s, stage: e.target.value as Stage }))}
              >
                {['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={dealForm.contact_id}
                onChange={(e) => setDealForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                type="date"
                value={dealForm.close_date}
                onChange={(e) => setDealForm((s) => ({ ...s, close_date: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/deals', 'POST', {
                    title: dealForm.title,
                    value: Number.parseFloat(dealForm.value) || 0,
                    currency: dealForm.currency,
                    stage: dealForm.stage,
                    contact_id: dealForm.contact_id ? Number.parseInt(dealForm.contact_id) : null,
                    close_date: dealForm.close_date || null,
                  }).then(
                    (ok) =>
                      ok &&
                      setDealForm({
                        title: '',
                        value: '0',
                        currency: 'USD',
                        stage: 'prospect',
                        contact_id: '',
                        company_id: '',
                        close_date: '',
                      })
                  )
                }
              >
                Create Deal
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Deals ({deals.length})</h3>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input
                  style={inp}
                  placeholder="Search"
                  value={dealsQuery}
                  onChange={(e) => setDealsQuery(e.target.value)}
                />
                <select style={inp} value={dealsStage} onChange={(e) => setDealsStage(e.target.value)}>
                  <option value="">All stages</option>
                  {['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <button style={btn} onClick={() => void loadData()}>
                  Apply
                </button>
              </div>
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {deals.map((d) => (
                  <div key={d.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700 }}>{d.title}</span>
                      <span style={{ fontWeight: 700 }}>{fmt(d.value, d.currency)}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 6 }}>
                      <span style={{ color: STAGE_COLOR[d.stage] }}>{d.stage}</span> - {d.probability}% - close{' '}
                      {d.close_date ?? 'TBD'}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {(
                        ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'] as Stage[]
                      ).map((s) => (
                        <button
                          key={s}
                          style={{
                            ...btn,
                            background: s === d.stage ? STAGE_COLOR[s] : 'transparent',
                            color: s === d.stage ? 'var(--on-status)' : 'var(--text)',
                            border: s === d.stage ? 'none' : '1px solid var(--line)',
                            padding: '3px 7px',
                            fontSize: 11,
                          }}
                          onClick={() => void req(`/crm/deals/${d.id}`, 'PATCH', { stage: s })}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                {sectionState('Deals', deals.length, dealsQuery.trim() || dealsStage ? 'No deals match the current filters.' : 'No deals have been added to this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* ACTIVITIES */}
        {tab === 'activities' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Log Activity</h3>
              <select
                style={inp}
                value={activityForm.type}
                onChange={(e) => setActivityForm((s) => ({ ...s, type: e.target.value }))}
              >
                {['note', 'call', 'email', 'meeting', 'task'].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                placeholder="Subject"
                value={activityForm.subject}
                onChange={(e) => setActivityForm((s) => ({ ...s, subject: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 80 }}
                placeholder="Body"
                value={activityForm.body}
                onChange={(e) => setActivityForm((s) => ({ ...s, body: e.target.value }))}
              />
              <select
                style={inp}
                value={activityForm.contact_id}
                onChange={(e) => setActivityForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact link</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={activityForm.deal_id}
                onChange={(e) => setActivityForm((s) => ({ ...s, deal_id: e.target.value }))}
              >
                <option value="">No deal link</option>
                {openDeals.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} #{d.id}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/activities', 'POST', {
                    type: activityForm.type,
                    subject: activityForm.subject,
                    body: activityForm.body,
                    contact_id: activityForm.contact_id ? Number.parseInt(activityForm.contact_id) : null,
                    deal_id: activityForm.deal_id ? Number.parseInt(activityForm.deal_id) : null,
                  }).then(
                    (ok) => ok && setActivityForm({ type: 'note', subject: '', body: '', contact_id: '', deal_id: '' })
                  )
                }
              >
                Log Activity
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Timeline ({activities.length})</h3>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <select style={inp} value={activityTypeFilter} onChange={(e) => setActivityTypeFilter(e.target.value)}>
                  <option value="">All types</option>
                  {['note', 'call', 'email', 'meeting', 'task'].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button style={btn} onClick={() => void loadData()}>
                  Apply
                </button>
              </div>
              <div style={{ maxHeight: 420, overflow: 'auto' }}>
                {activities.map((a) => (
                  <div key={a.id} style={{ borderBottom: '1px solid var(--line)', padding: '7px 0' }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {a.type.toUpperCase()} - {fmtTime(a.created_at)}
                    </div>
                    <div style={{ fontWeight: 700 }}>{a.subject}</div>
                    {a.body && <div style={{ fontSize: 13 }}>{a.body}</div>}
                  </div>
                ))}
                {sectionState('Activities', activities.length, activityTypeFilter ? 'No activities match the current filter.' : 'No activities are recorded for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* LEADS */}
        {tab === 'leads' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Lead</h3>
              <input
                style={inp}
                placeholder="Lead Title"
                value={leadForm.title}
                onChange={(e) => setLeadForm((s) => ({ ...s, title: e.target.value }))}
              />
              <select
                style={inp}
                value={leadForm.source}
                onChange={(e) => setLeadForm((s) => ({ ...s, source: e.target.value }))}
              >
                {['website', 'inbound', 'referral', 'social', 'paid_ads', 'cold_outreach', 'api'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                type="number"
                placeholder="Estimated Value"
                value={leadForm.estimated_value}
                onChange={(e) => setLeadForm((s) => ({ ...s, estimated_value: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                min="0"
                max="100"
                placeholder="Score (0-100)"
                value={leadForm.score}
                onChange={(e) => setLeadForm((s) => ({ ...s, score: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Assigned To"
                value={leadForm.assigned_to}
                onChange={(e) => setLeadForm((s) => ({ ...s, assigned_to: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/leads', 'POST', {
                    title: leadForm.title,
                    source: leadForm.source,
                    estimated_value: Number.parseFloat(leadForm.estimated_value) || 0,
                    score: Number.parseInt(leadForm.score) || 0,
                    assigned_to: leadForm.assigned_to,
                  }).then(
                    (ok) =>
                      ok &&
                      setLeadForm({
                        title: '',
                        source: 'website',
                        estimated_value: '0',
                        status: 'new',
                        score: '0',
                        assigned_to: '',
                      })
                  )
                }
              >
                Create Lead
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Leads ({leads.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {leads.map((l) => (
                  <div
                    key={l.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '8px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700 }}>{l.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {l.source} - score {l.score} - {l.status} - {fmt(l.estimated_value)}
                      </div>
                      {l.assigned_to && (
                        <div style={{ fontSize: 12, color: 'var(--muted)' }}>assigned to {l.assigned_to}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button
                        style={{ ...ghostBtn, fontSize: 11, padding: '4px 8px' }}
                        onClick={() => void req(`/crm/leads/${l.id}`, 'PATCH', { status: 'qualified' })}
                      >
                        Qualify
                      </button>
                      <button
                        style={{ ...btn, fontSize: 11, padding: '4px 8px' }}
                        onClick={() => void req(`/crm/leads/${l.id}/convert`, 'POST')}
                      >
                        Convert
                      </button>
                    </div>
                  </div>
                ))}
                {sectionState('Leads', leads.length, 'No leads have been added to this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* TASKS */}
        {tab === 'tasks' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Task</h3>
              <input
                style={inp}
                placeholder="Title"
                value={taskForm.title}
                onChange={(e) => setTaskForm((s) => ({ ...s, title: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 60 }}
                placeholder="Description"
                value={taskForm.description}
                onChange={(e) => setTaskForm((s) => ({ ...s, description: e.target.value }))}
              />
              <select
                style={inp}
                value={taskForm.priority}
                onChange={(e) => setTaskForm((s) => ({ ...s, priority: e.target.value }))}
              >
                {['low', 'medium', 'high', 'critical'].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={taskForm.type}
                onChange={(e) => setTaskForm((s) => ({ ...s, type: e.target.value }))}
              >
                {['task', 'call', 'email', 'follow_up', 'demo', 'proposal'].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                placeholder="Assigned To"
                value={taskForm.assigned_to}
                onChange={(e) => setTaskForm((s) => ({ ...s, assigned_to: e.target.value }))}
              />
              <input
                style={inp}
                type="date"
                value={taskForm.due_date}
                onChange={(e) => setTaskForm((s) => ({ ...s, due_date: e.target.value }))}
              />
              <select
                style={inp}
                value={taskForm.contact_id}
                onChange={(e) => setTaskForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/tasks', 'POST', {
                    title: taskForm.title,
                    description: taskForm.description,
                    priority: taskForm.priority,
                    type: taskForm.type,
                    assigned_to: taskForm.assigned_to,
                    due_date: taskForm.due_date || null,
                    contact_id: taskForm.contact_id ? Number.parseInt(taskForm.contact_id) : null,
                  }).then(
                    (ok) =>
                      ok &&
                      setTaskForm({
                        title: '',
                        description: '',
                        priority: 'medium',
                        type: 'task',
                        assigned_to: '',
                        due_date: '',
                        contact_id: '',
                        deal_id: '',
                      })
                  )
                }
              >
                Create Task
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Tasks Kanban</h3>
              {sectionState(
                'Tasks',
                tasks.length,
                taskStatusFilter ? 'No tasks match the current filter.' : 'No tasks have been recorded for this workspace.'
              )}
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <select style={inp} value={taskStatusFilter} onChange={(e) => setTaskStatusFilter(e.target.value)}>
                  <option value="">All statuses</option>
                  {['open', 'in_progress', 'completed', 'cancelled'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <button style={btn} onClick={() => void loadData()}>
                  Apply
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 8 }}>
                {['open', 'in_progress', 'completed'].map((col) => (
                  <div key={col} style={{ ...card, background: 'var(--bg)' }}>
                    <div
                      style={{
                        fontWeight: 700,
                        marginBottom: 8,
                        textTransform: 'uppercase',
                        fontSize: 11,
                        color: 'var(--muted)',
                      }}
                    >
                      {col.replace('_', ' ')}
                    </div>
                    {tasks
                      .filter((t) => t.status === col)
                      .map((t) => (
                        <div
                          key={t.id}
                          style={{
                            background: 'var(--bg-soft)',
                            border: '1px solid var(--line)',
                            borderRadius: 8,
                            padding: '6px 8px',
                            marginBottom: 6,
                          }}
                        >
                          <div style={{ fontWeight: 700, fontSize: 13 }}>{t.title}</div>
                          <div style={{ fontSize: 11, color: PRIORITY_COLOR[t.priority] ?? 'var(--muted)' }}>
                            {t.priority} - {t.due_date ?? 'no due date'}
                          </div>
                          {col === 'open' && (
                            <button
                              style={{ ...btn, fontSize: 11, padding: '3px 6px', marginTop: 4 }}
                              onClick={() => void req(`/crm/tasks/${t.id}`, 'PATCH', { status: 'in_progress' })}
                            >
                              Start
                            </button>
                          )}
                          {col === 'in_progress' && (
                            <button
                              style={{ ...btn, fontSize: 11, padding: '3px 6px', marginTop: 4, background: 'var(--success)' }}
                              onClick={() => void req(`/crm/tasks/${t.id}`, 'PATCH', { status: 'completed' })}
                            >
                              Done
                            </button>
                          )}
                        </div>
                      ))}
                    {!loading && !failedSections.includes('Tasks') && tasks.length > 0 && !tasks.some((task) => task.status === col) ? (
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>No tasks in this stage.</div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* TICKETS */}
        {tab === 'tickets' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Support Ticket</h3>
              <input
                style={inp}
                placeholder="Subject"
                value={ticketForm.subject}
                onChange={(e) => setTicketForm((s) => ({ ...s, subject: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 80 }}
                placeholder="Description"
                value={ticketForm.description}
                onChange={(e) => setTicketForm((s) => ({ ...s, description: e.target.value }))}
              />
              <select
                style={inp}
                value={ticketForm.priority}
                onChange={(e) => setTicketForm((s) => ({ ...s, priority: e.target.value }))}
              >
                {['low', 'medium', 'high', 'critical'].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={ticketForm.channel}
                onChange={(e) => setTicketForm((s) => ({ ...s, channel: e.target.value }))}
              >
                {['email', 'chat', 'phone', 'portal', 'twitter', 'whatsapp'].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={ticketForm.contact_id}
                onChange={(e) => setTicketForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact link</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/tickets', 'POST', {
                    subject: ticketForm.subject,
                    description: ticketForm.description,
                    priority: ticketForm.priority,
                    channel: ticketForm.channel,
                    contact_id: ticketForm.contact_id ? Number.parseInt(ticketForm.contact_id) : null,
                  }).then(
                    (ok) =>
                      ok &&
                      setTicketForm({
                        subject: '',
                        description: '',
                        priority: 'medium',
                        channel: 'email',
                        contact_id: '',
                      })
                  )
                }
              >
                Open Ticket
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Tickets ({tickets.length})</h3>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <select
                  style={inp}
                  value={ticketsStatusFilter}
                  onChange={(e) => setTicketsStatusFilter(e.target.value)}
                >
                  <option value="">All</option>
                  {['open', 'in_progress', 'resolved', 'closed'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <button style={btn} onClick={() => void loadData()}>
                  Apply
                </button>
              </div>
              <div style={{ maxHeight: 420, overflow: 'auto' }}>
                {tickets.map((t) => (
                  <div key={t.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 700 }}>
                          {t.ticket_number} - {t.subject}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                          <span style={{ color: PRIORITY_COLOR[t.priority] ?? 'var(--muted)' }}>{t.priority}</span> -{' '}
                          {t.channel} - {t.status}
                          {t.escalated && <span style={{ color: 'var(--danger)', marginLeft: 6 }}>ESCALATED</span>}
                        </div>
                        {t.first_response_deadline && (
                          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                            SLA by {fmtTime(t.first_response_deadline)}
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                        <button
                          style={{ ...ghostBtn, fontSize: 11, padding: '3px 7px' }}
                          onClick={() => void req(`/crm/tickets/${t.id}`, 'PATCH', { status: 'resolved' })}
                        >
                          Resolve
                        </button>
                        {!t.escalated && (
                          <button
                            style={{ ...dangerBtn, fontSize: 11, padding: '3px 7px' }}
                            onClick={() => void req(`/crm/tickets/${t.id}/escalate`, 'POST')}
                          >
                            Escalate
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {sectionState('Support', tickets.length, ticketsStatusFilter ? 'No tickets match the current filter.' : 'No support tickets have been recorded for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* CAMPAIGNS */}
        {tab === 'campaigns' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Campaign</h3>
              <input
                style={inp}
                placeholder="Campaign Name"
                value={campaignForm.name}
                onChange={(e) => setCampaignForm((s) => ({ ...s, name: e.target.value }))}
              />
              <select
                style={inp}
                value={campaignForm.type}
                onChange={(e) => setCampaignForm((s) => ({ ...s, type: e.target.value }))}
              >
                {['email', 'sms', 'push', 'in_app', 'drip'].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                placeholder="Subject Line"
                value={campaignForm.subject}
                onChange={(e) => setCampaignForm((s) => ({ ...s, subject: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 80 }}
                placeholder="Body / Content"
                value={campaignForm.body}
                onChange={(e) => setCampaignForm((s) => ({ ...s, body: e.target.value }))}
              />
              <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <input
                  type="checkbox"
                  checked={campaignForm.ab_test}
                  onChange={(e) => setCampaignForm((s) => ({ ...s, ab_test: e.target.checked }))}
                />
                <span>A/B Test</span>
              </label>
              {campaignForm.ab_test && (
                <input
                  style={inp}
                  placeholder="Variant B Subject"
                  value={campaignForm.variant_b_subject}
                  onChange={(e) => setCampaignForm((s) => ({ ...s, variant_b_subject: e.target.value }))}
                />
              )}
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/campaigns', 'POST', campaignForm).then(
                    (ok) =>
                      ok &&
                      setCampaignForm({
                        name: '',
                        type: 'email',
                        subject: '',
                        body: '',
                        ab_test: false,
                        variant_b_subject: '',
                      })
                  )
                }
              >
                Create Campaign
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Campaigns ({campaigns.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {campaigns.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '8px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700 }}>
                        {c.name} <span style={{ fontSize: 11, color: 'var(--muted)' }}>{c.type}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        Status: {c.status} - Sent: {c.sent_count} - Opens: {c.open_count}
                        {c.ab_test ? ' - A/B' : ''}
                      </div>
                    </div>
                    {c.status === 'draft' && (
                      <button
                        style={{ ...btn, fontSize: 11, padding: '4px 8px' }}
                        onClick={() => void req(`/crm/campaigns/${c.id}/send`, 'POST')}
                      >
                        Send
                      </button>
                    )}
                  </div>
                ))}
                {sectionState('Campaigns', campaigns.length, 'No campaigns have been created for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* SEGMENTS */}
        {tab === 'segments' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Segment</h3>
              <input
                style={inp}
                placeholder="Segment Name"
                value={segmentForm.name}
                onChange={(e) => setSegmentForm((s) => ({ ...s, name: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Description"
                value={segmentForm.description}
                onChange={(e) => setSegmentForm((s) => ({ ...s, description: e.target.value }))}
              />
              <p style={{ fontSize: 12, color: 'var(--muted)', margin: '0 0 6px' }}>Filters (optional)</p>
              <select
                style={inp}
                value={segmentForm.lifecycle_stage}
                onChange={(e) => setSegmentForm((s) => ({ ...s, lifecycle_stage: e.target.value }))}
              >
                <option value="">Any lifecycle stage</option>
                {['lead', 'subscriber', 'mql', 'sql', 'opportunity', 'customer'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                type="number"
                placeholder="Min Lead Score"
                value={segmentForm.min_lead_score}
                onChange={(e) => setSegmentForm((s) => ({ ...s, min_lead_score: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() => {
                  const filters: Record<string, unknown> = {};
                  if (segmentForm.lifecycle_stage) filters['lifecycle_stage'] = segmentForm.lifecycle_stage;
                  if (segmentForm.min_lead_score)
                    filters['min_lead_score'] = Number.parseInt(segmentForm.min_lead_score);
                  void req('/crm/segments', 'POST', {
                    name: segmentForm.name,
                    description: segmentForm.description,
                    filters,
                  }).then(
                    (ok) => ok && setSegmentForm({ name: '', description: '', lifecycle_stage: '', min_lead_score: '' })
                  );
                }}
              >
                Create Segment
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Segments ({segments.length})</h3>
              {segments.map((s) => (
                <div key={s.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                  <div style={{ fontWeight: 700 }}>
                    {s.name}{' '}
                    <span style={{ fontSize: 12, color: 'var(--brand)', marginLeft: 6 }}>{s.member_count} members</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{s.description || 'no description'}</div>
                </div>
              ))}
              {sectionState('Segments', segments.length, 'No segments have been created for this workspace.')}
            </div>
          </section>
        )}

        {/* NOTES */}
        {tab === 'notes' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Note</h3>
              <textarea
                style={{ ...inp, minHeight: 120 }}
                placeholder="Note body"
                value={noteForm.body}
                onChange={(e) => setNoteForm((s) => ({ ...s, body: e.target.value }))}
              />
              <select
                style={inp}
                value={noteForm.contact_id}
                onChange={(e) => setNoteForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact link</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={noteForm.deal_id}
                onChange={(e) => setNoteForm((s) => ({ ...s, deal_id: e.target.value }))}
              >
                <option value="">No deal link</option>
                {openDeals.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} #{d.id}
                  </option>
                ))}
              </select>
              <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <input
                  type="checkbox"
                  checked={noteForm.pinned}
                  onChange={(e) => setNoteForm((s) => ({ ...s, pinned: e.target.checked }))}
                />
                <span>Pin note</span>
              </label>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/notes', 'POST', {
                    body: noteForm.body,
                    contact_id: noteForm.contact_id ? Number.parseInt(noteForm.contact_id) : null,
                    deal_id: noteForm.deal_id ? Number.parseInt(noteForm.deal_id) : null,
                    pinned: noteForm.pinned,
                  }).then(
                    (ok) => ok && setNoteForm({ body: '', contact_id: '', deal_id: '', company_id: '', pinned: false })
                  )
                }
              >
                Save Note
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Notes ({notes.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {notes.map((n) => (
                  <div key={n.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                    {n.pinned && <div style={{ fontSize: 11, color: 'var(--brand)', fontWeight: 700 }}>PINNED</div>}
                    <div style={{ fontSize: 14 }}>{n.body}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                      contact #{n.contact_id ?? '-'} - deal #{n.deal_id ?? '-'} - {fmtTime(n.created_at)}
                    </div>
                  </div>
                ))}
                {sectionState('Notes', notes.length, 'No notes have been recorded for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* QUOTES */}
        {tab === 'quotes' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Quote</h3>
              <input
                style={inp}
                placeholder="Quote Title"
                value={quoteForm.title}
                onChange={(e) => setQuoteForm((s) => ({ ...s, title: e.target.value }))}
              />
              <select
                style={inp}
                value={quoteForm.contact_id}
                onChange={(e) => setQuoteForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                placeholder="Currency"
                value={quoteForm.currency}
                onChange={(e) => setQuoteForm((s) => ({ ...s, currency: e.target.value }))}
              />
              <input
                style={inp}
                type="date"
                placeholder="Valid Until"
                value={quoteForm.valid_until}
                onChange={(e) => setQuoteForm((s) => ({ ...s, valid_until: e.target.value }))}
              />
              <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0' }}>Line Item</p>
              <input
                style={inp}
                placeholder="Item description"
                value={quoteForm.item_desc}
                onChange={(e) => setQuoteForm((s) => ({ ...s, item_desc: e.target.value }))}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  style={inp}
                  type="number"
                  placeholder="Qty"
                  value={quoteForm.item_qty}
                  onChange={(e) => setQuoteForm((s) => ({ ...s, item_qty: e.target.value }))}
                />
                <input
                  style={inp}
                  type="number"
                  placeholder="Unit price"
                  value={quoteForm.item_price}
                  onChange={(e) => setQuoteForm((s) => ({ ...s, item_price: e.target.value }))}
                />
              </div>
              <textarea
                style={{ ...inp, minHeight: 60 }}
                placeholder="Notes"
                value={quoteForm.notes}
                onChange={(e) => setQuoteForm((s) => ({ ...s, notes: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/quotes', 'POST', {
                    title: quoteForm.title,
                    contact_id: quoteForm.contact_id ? Number.parseInt(quoteForm.contact_id) : null,
                    currency: quoteForm.currency,
                    valid_until: quoteForm.valid_until || null,
                    notes: quoteForm.notes,
                    line_items: quoteForm.item_desc
                      ? [
                          {
                            description: quoteForm.item_desc,
                            quantity: Number.parseFloat(quoteForm.item_qty) || 1,
                            unit_price: Number.parseFloat(quoteForm.item_price) || 0,
                            discount_pct: 0,
                          },
                        ]
                      : [],
                  }).then(
                    (ok) =>
                      ok &&
                      setQuoteForm({
                        title: '',
                        contact_id: '',
                        deal_id: '',
                        currency: 'USD',
                        valid_until: '',
                        notes: '',
                        item_desc: '',
                        item_qty: '1',
                        item_price: '0',
                      })
                  )
                }
              >
                Create Quote
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Quotes ({quotes.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {quotes.map((q) => (
                  <div
                    key={q.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '8px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700 }}>
                        {q.quote_number} - {q.title}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {fmt(q.subtotal, q.currency)} - {q.status} - valid until {q.valid_until ?? '-'}
                      </div>
                    </div>
                    {q.status === 'draft' && (
                      <button
                        style={{ ...btn, fontSize: 11, padding: '4px 8px' }}
                        onClick={() => void req(`/crm/quotes/${q.id}/accept`, 'POST')}
                      >
                        Accept + Invoice
                      </button>
                    )}
                  </div>
                ))}
                {sectionState('Quotes', quotes.length, 'No quotes have been created for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* INVOICES */}
        {tab === 'invoices' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Invoice</h3>
              <input
                style={inp}
                placeholder="Invoice Title"
                value={invoiceForm.title}
                onChange={(e) => setInvoiceForm((s) => ({ ...s, title: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                placeholder="Amount"
                value={invoiceForm.amount}
                onChange={(e) => setInvoiceForm((s) => ({ ...s, amount: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Currency"
                value={invoiceForm.currency}
                onChange={(e) => setInvoiceForm((s) => ({ ...s, currency: e.target.value }))}
              />
              <input
                style={inp}
                type="date"
                placeholder="Due Date"
                value={invoiceForm.due_date}
                onChange={(e) => setInvoiceForm((s) => ({ ...s, due_date: e.target.value }))}
              />
              <select
                style={inp}
                value={invoiceForm.contact_id}
                onChange={(e) => setInvoiceForm((s) => ({ ...s, contact_id: e.target.value }))}
              >
                <option value="">No contact</option>
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} #{c.id}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/invoices', 'POST', {
                    title: invoiceForm.title,
                    amount: Number.parseFloat(invoiceForm.amount) || 0,
                    currency: invoiceForm.currency,
                    due_date: invoiceForm.due_date || null,
                    contact_id: invoiceForm.contact_id ? Number.parseInt(invoiceForm.contact_id) : null,
                  }).then(
                    (ok) =>
                      ok && setInvoiceForm({ title: '', amount: '0', currency: 'USD', due_date: '', contact_id: '' })
                  )
                }
              >
                Create Invoice
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Invoices ({invoices.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {invoices.map((inv) => (
                  <div
                    key={inv.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '8px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700 }}>
                        {inv.invoice_number} - {inv.title}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {fmt(inv.amount, inv.currency)} -{' '}
                        <span style={{ color: inv.status === 'paid' ? 'var(--success)' : 'var(--warning)' }}>{inv.status}</span> - due{' '}
                        {inv.due_date ?? '-'}
                      </div>
                    </div>
                    {inv.status === 'pending' && (
                      <button
                        style={{ ...btn, fontSize: 11, padding: '4px 8px', background: 'var(--success)' }}
                        onClick={() =>
                          void req(`/crm/invoices/${inv.id}`, 'PATCH', {
                            status: 'paid',
                            paid_at: new Date().toISOString(),
                          })
                        }
                      >
                        Mark Paid
                      </button>
                    )}
                  </div>
                ))}
                {sectionState('Invoices', invoices.length, 'No invoices have been created for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* EMAIL SEQUENCES */}
        {tab === 'sequences' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Email Sequence</h3>
              <input
                style={inp}
                placeholder="Sequence Name"
                value={sequenceForm.name}
                onChange={(e) => setSequenceForm((s) => ({ ...s, name: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Description"
                value={sequenceForm.description}
                onChange={(e) => setSequenceForm((s) => ({ ...s, description: e.target.value }))}
              />
              <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0' }}>Step 1</p>
              <input
                style={inp}
                placeholder="Subject"
                value={sequenceForm.step1_subject}
                onChange={(e) => setSequenceForm((s) => ({ ...s, step1_subject: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 80 }}
                placeholder="Body"
                value={sequenceForm.step1_body}
                onChange={(e) => setSequenceForm((s) => ({ ...s, step1_body: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                placeholder="Day offset"
                value={sequenceForm.step1_day}
                onChange={(e) => setSequenceForm((s) => ({ ...s, step1_day: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/email-sequences', 'POST', {
                    name: sequenceForm.name,
                    description: sequenceForm.description,
                    steps: sequenceForm.step1_subject
                      ? [
                          {
                            subject: sequenceForm.step1_subject,
                            body: sequenceForm.step1_body,
                            day_offset: Number.parseInt(sequenceForm.step1_day) || 0,
                            type: 'email',
                          },
                        ]
                      : [],
                  }).then(
                    (ok) =>
                      ok &&
                      setSequenceForm({ name: '', description: '', step1_subject: '', step1_body: '', step1_day: '0' })
                  )
                }
              >
                Create Sequence
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Email Sequences ({sequences.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {sequences.map((s) => (
                  <div key={s.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                    <div style={{ fontWeight: 700 }}>{s.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {s.step_count} steps - {s.enrollments} enrolled - {s.status}
                    </div>
                    {s.description && <div style={{ fontSize: 13 }}>{s.description}</div>}
                    <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                      {contacts.slice(0, 1).map((c) => (
                        <button
                          key={c.id}
                          style={{ ...btn, fontSize: 11, padding: '3px 7px' }}
                          onClick={() => void req(`/crm/email-sequences/${s.id}/enroll?contact_id=${c.id}`, 'POST')}
                        >
                          Enroll Contact #{c.id}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                {sectionState('Sequences', sequences.length, 'No email sequences have been created for this workspace.')}
              </div>
            </div>
          </section>
        )}

        {/* PROJECTS */}
        {tab === 'projects' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Project</h3>
              <input
                style={inp}
                placeholder="Project Name"
                value={projectForm.name}
                onChange={(e) => setProjectForm((s) => ({ ...s, name: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 70 }}
                placeholder="Description"
                value={projectForm.description}
                onChange={(e) => setProjectForm((s) => ({ ...s, description: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Owner"
                value={projectForm.owner}
                onChange={(e) => setProjectForm((s) => ({ ...s, owner: e.target.value }))}
              />
              <select
                style={inp}
                value={projectForm.status}
                onChange={(e) => setProjectForm((s) => ({ ...s, status: e.target.value }))}
              >
                {['planning', 'active', 'blocked', 'done'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                type="date"
                value={projectForm.due_date}
                onChange={(e) => setProjectForm((s) => ({ ...s, due_date: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/projects', 'POST', { ...projectForm, due_date: projectForm.due_date || null }).then(
                    (ok) =>
                      ok && setProjectForm({ name: '', description: '', owner: '', status: 'planning', due_date: '' })
                  )
                }
              >
                Create Project
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Project Board</h3>
              {sectionState('Projects', projects.length, 'No projects have been added for this workspace.')}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 8 }}>
                {['planning', 'active', 'blocked', 'done'].map((col) => (
                  <div key={col} style={{ ...card, background: 'var(--bg)' }}>
                    <div
                      style={{
                        fontWeight: 700,
                        marginBottom: 8,
                        textTransform: 'uppercase',
                        fontSize: 11,
                        color: 'var(--muted)',
                      }}
                    >
                      {col}
                    </div>
                    {projects
                      .filter((p) => p.status === col)
                      .map((p) => (
                        <div
                          key={p.id}
                          style={{
                            border: '1px solid var(--line)',
                            borderRadius: 8,
                            padding: '6px 8px',
                            marginBottom: 6,
                          }}
                        >
                          <div style={{ fontWeight: 700, fontSize: 13 }}>{p.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--muted)' }}>owner: {p.owner || 'unassigned'}</div>
                          <div style={{ fontSize: 11, color: 'var(--muted)' }}>due: {p.due_date || '-'}</div>
                          <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                            {['planning', 'active', 'blocked', 'done'].map((s) => (
                              <button
                                key={s}
                                style={{ ...ghostBtn, fontSize: 10, padding: '2px 5px' }}
                                onClick={() => void req(`/crm/projects/${p.id}`, 'PATCH', { status: s })} // NOSONAR
                              >
                                {s}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    {!loading && !failedSections.includes('Projects') && projects.length > 0 && !projects.some((project) => project.status === col) ? (
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>No projects in this status.</div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* REPORTS */}
        {tab === 'reports' && (
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 20 }}>CRM reports</h2>
                <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
                  Workspace data for the last {getReportDays(analyticsRange)} days.
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'end', gap: 8, flexWrap: 'wrap' }}>
                <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted)' }}>
                  Reporting period
                  <select
                    aria-label="CRM reporting period"
                    style={inp}
                    value={analyticsRange}
                    onChange={(event) => setAnalyticsRange(event.target.value as AnalyticsRange)}
                  >
                    <option value="7d">Last 7 days</option>
                    <option value="30d">Last 30 days</option>
                    <option value="90d">Last 90 days</option>
                  </select>
                </label>
                <button type="button" style={ghostBtn} onClick={exportAnalyticsCsv}>
                  Export analytics CSV
                </button>
              </div>
            </div>
            {!loading && failedSections.includes('Reports') ? (
              <p role="status">Some report sources are unavailable. Available metrics remain visible; unavailable data is not shown as zero.</p>
            ) : null}
            {!loading && !failedSections.includes('Reports') && !kpis && !forecast && !executiveAnalytics ? (
              <p>No report data is available for this workspace yet.</p>
            ) : null}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
                gap: 10,
                marginBottom: 12,
              }}
            >
              {kpis &&
                [
                  { label: 'Total Contacts', val: kpis.total_contacts },
                  { label: 'Total Leads', val: kpis.total_leads },
                  { label: 'Lead Conv. Rate', val: `${kpis.lead_conversion_rate_pct}%` },
                  { label: 'Win Rate', val: `${kpis.win_rate_pct}%` },
                  { label: 'Avg Deal Value', val: fmt(kpis.avg_deal_value) },
                  { label: 'Closed Won', val: fmt(kpis.closed_won_value) },
                  { label: 'Open Tickets', val: kpis.open_tickets },
                  { label: 'Escalated', val: kpis.escalated_tickets },
                  { label: 'Open Tasks', val: kpis.open_tasks },
                  { label: 'Overdue Tasks', val: kpis.overdue_tasks },
                ].map(({ label, val }) => (
                  <div key={label} style={card}>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>{label}</div>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>{val}</div>
                  </div>
                ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Revenue Forecast</h3>
                {forecast && (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8, marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Weighted Pipeline</div>
                        <div style={{ fontSize: 20, fontWeight: 700 }}>{fmt(forecast.weighted_pipeline)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Closed Won Total</div>
                        <div style={{ fontSize: 20, fontWeight: 700 }}>{fmt(forecast.closed_won_total)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Outstanding Invoices</div>
                        <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--warning)' }}>
                          {fmt(forecast.outstanding_invoices)}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Paid Invoices</div>
                        <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--success)' }}>
                          {fmt(forecast.paid_invoices)}
                        </div>
                      </div>
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>Monthly Forecast</div>
                      {Object.entries(forecast.monthly_forecast ?? {}).map(([month, val]) => (
                        <div
                          key={month}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            fontSize: 13,
                            padding: '4px 0',
                            borderBottom: '1px solid var(--line)',
                          }}
                        >
                          <span>{month}</span>
                          <span style={{ fontWeight: 700 }}>{fmt(val)}</span>
                        </div>
                      ))}
                      {!Object.keys(forecast.monthly_forecast ?? {}).length && (
                        <div style={{ color: 'var(--muted)' }}>No pipeline deals with close dates.</div>
                      )}
                    </div>
                  </>
                )}
              </div>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Stage Breakdown</h3>
                {pipeline.map((row) => (
                  <div key={row.stage} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                      <span style={{ color: STAGE_COLOR[row.stage] }}>{row.display}</span>
                      <span>
                        {row.count} deals - {fmt(row.total_value)}
                      </span>
                    </div>
                    <div style={{ height: 6, borderRadius: 999, background: 'var(--line)', overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${row.count ? Math.min(100, row.probability) : 0}%`,
                          background: STAGE_COLOR[row.stage] ?? 'var(--brand)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

      </div>
    </div>
  );
}
