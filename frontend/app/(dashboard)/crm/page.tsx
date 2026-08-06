'use client';

import { useEffect, useMemo, useState } from 'react';
import AnalyticsExecutiveBoard from '@/app/components/analytics-executive-board';

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
type WorkflowRule = {
  id: number;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
  run_count: number;
  last_triggered_at: string | null;
  created_at: string;
};
type SLARule = {
  id: number;
  name: string;
  priority: string;
  first_response_hours: number;
  resolution_hours: number;
  created_at: string;
};
type CRMWebhook = {
  id: number;
  event: string;
  target_url: string;
  status: string;
  last_delivery_status: string | null;
  last_delivery_at: string | null;
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
type ExecutiveAnalytics = {
  generated_at: string;
  overview: {
    total_contacts: number;
    total_deals: number;
    total_leads: number;
    lead_conversion_rate_pct: number;
    escalated_ticket_ratio_pct: number;
    overdue_tasks: number;
  };
  charts: {
    pipeline_funnel: Array<{ stage: string; display: string; count: number }>;
    monthly_closed_won: Array<{ month: string; value: number }>;
    lead_source_breakdown: Record<string, number>;
  };
  anomalies: Array<{ type: string; severity: string; detail: string }>;
};
type CRMBackupConfig = {
  incremental_minutes: number;
  full_backup_weekday: string;
  full_backup_hour_utc: number;
  retention_days: number;
  enabled: boolean;
};
type CRMBackupSnapshot = {
  id: number;
  mode: string;
  status: string;
  started_at: string;
  completed_at: string;
  checksum: string;
};
type CRMBackupOps = {
  config: CRMBackupConfig;
  latest_incremental: CRMBackupSnapshot | null;
  latest_full: CRMBackupSnapshot | null;
  snapshot_count: number;
  next_runs: { incremental_at: string; full_at: string };
  schedule_health: string;
};
type CRMLiveSync = {
  enabled: boolean;
  interval_seconds: number;
  last_sync_at: string | null;
  last_success_at: string | null;
  lag_seconds: number;
  events_processed_24h: number;
  conflict_queue: number;
  provider_status: Record<string, string>;
};
type Project = {
  id: number;
  name: string;
  description: string;
  owner: string;
  status: string;
  due_date: string | null;
  created_at: string;
};
type CustomEntityType = {
  id: number;
  key: string;
  name: string;
  description: string;
  fields: Record<string, unknown>[];
};
type CustomEntityRecord = {
  id: number;
  entity_key: string;
  values: Record<string, unknown>;
  created_at: string;
};
type AutomationRecipe = {
  id: number;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
  run_count: number;
  last_run_at: string | null;
};
type APIToken = {
  id: number;
  name: string;
  scopes: string[];
  token_prefix: string;
  status: string;
  created_at: string;
};

type CrmPageData = {
  summary: Summary | null;
  pipeline: PipelineRow[];
  contacts: Contact[];
  companies: Company[];
  deals: Deal[];
  activities: Activity[];
  webhooks: CRMWebhook[];
  leads: Lead[];
  tasks: Task[];
  tickets: Ticket[];
  campaigns: Campaign[];
  segments: Segment[];
  notes: Note[];
  quotes: Quote[];
  invoices: CRMInvoice[];
  sequences: EmailSequence[];
  workflowRules: WorkflowRule[];
  slaRules: SLARule[];
  kpis: KPIs | null;
  windowDays: number | null;
  forecast: Forecast | null;
  executiveAnalytics: ExecutiveAnalytics | null;
  backupOps: CRMBackupOps | null;
  liveSync: CRMLiveSync | null;
  projects: Project[];
  entityTypes: CustomEntityType[];
  entityRecords: CustomEntityRecord[];
  automationRecipes: AutomationRecipe[];
  apiTokens: APIToken[];
  activeEntityKey: string;
  failedSections: string[];
};

type Tab =
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
  | 'workflows'
  | 'projects'
  | 'extensions'
  | 'reports'
  | 'enterprise'
  | 'settings';

type CrmAutonomyModule = {
  id:
    | 'overview'
    | 'contacts'
    | 'companies'
    | 'deals'
    | 'activities'
    | 'leads'
    | 'tasks'
    | 'support'
    | 'campaigns'
    | 'segments'
    | 'notes'
    | 'quotes'
    | 'invoices'
    | 'sequences'
    | 'automation'
    | 'projects'
    | 'extensibility'
    | 'reports'
    | 'enterprise_ops'
    | 'settings_sla';
  label: string;
  tab: Tab;
  autonomy_tier: 'adaptive' | 'predictive' | 'self_optimizing' | 'autonomous';
  ops_signal: string;
  intelligence_detail: string;
  readiness_score: number;
  state: 'seeded' | 'active' | 'operational';
};

const MODULE_BLUEPRINTS: Array<Omit<CrmAutonomyModule, 'readiness_score' | 'state'> & { scoreHints: string[] }> = [
  {
    id: 'overview',
    label: 'Overview',
    tab: 'overview',
    autonomy_tier: 'autonomous',
    ops_signal: 'Unified command KPIs and runtime posture',
    intelligence_detail: 'Fuses pipeline, support, task, and revenue telemetry into one operator surface.',
    scoreHints: ['summary', 'kpis', 'forecast'],
  },
  {
    id: 'contacts',
    label: 'Contacts',
    tab: 'contacts',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Identity quality and dedupe intelligence',
    intelligence_detail: 'Lead scoring and dedupe orchestration keep the contact graph production-grade.',
    scoreHints: ['contacts'],
  },
  {
    id: 'companies',
    label: 'Companies',
    tab: 'companies',
    autonomy_tier: 'predictive',
    ops_signal: 'Account intelligence and enrichment',
    intelligence_detail: 'Company profiles drive account-level segmentation and revenue prioritization.',
    scoreHints: ['companies'],
  },
  {
    id: 'deals',
    label: 'Deals',
    tab: 'deals',
    autonomy_tier: 'autonomous',
    ops_signal: 'Pipeline probability + weighted forecast',
    intelligence_detail: 'Stage-based probability model enables proactive close-plan automation.',
    scoreHints: ['deals', 'pipeline', 'summary'],
  },
  {
    id: 'activities',
    label: 'Activities',
    tab: 'activities',
    autonomy_tier: 'predictive',
    ops_signal: 'Engagement timeline and execution rhythm',
    intelligence_detail: 'Activity stream powers next-best-action suggestions and SLA risk context.',
    scoreHints: ['activities'],
  },
  {
    id: 'leads',
    label: 'Leads',
    tab: 'leads',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Conversion intent + qualification automation',
    intelligence_detail: 'Score-based qualification and one-click conversion reduce response latency.',
    scoreHints: ['leads', 'kpis'],
  },
  {
    id: 'tasks',
    label: 'Tasks',
    tab: 'tasks',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Execution queue and overdue prevention',
    intelligence_detail: 'Kanban progression and overdue signals keep GTM execution deterministic.',
    scoreHints: ['tasks', 'kpis'],
  },
  {
    id: 'support',
    label: 'Support',
    tab: 'tickets',
    autonomy_tier: 'autonomous',
    ops_signal: 'Escalation + SLA breach control',
    intelligence_detail: 'Priority-aware routing and escalation handling preserve support reliability.',
    scoreHints: ['tickets', 'slaRules'],
  },
  {
    id: 'campaigns',
    label: 'Campaigns',
    tab: 'campaigns',
    autonomy_tier: 'predictive',
    ops_signal: 'Performance lift and A/B intelligence',
    intelligence_detail: 'Campaign run-states and opens/clicks support continuous optimization loops.',
    scoreHints: ['campaigns', 'segments'],
  },
  {
    id: 'segments',
    label: 'Segments',
    tab: 'segments',
    autonomy_tier: 'predictive',
    ops_signal: 'Audience topology and targeting precision',
    intelligence_detail: 'Dynamic filters convert lifecycle + score into high-intent targeting sets.',
    scoreHints: ['segments'],
  },
  {
    id: 'notes',
    label: 'Notes',
    tab: 'notes',
    autonomy_tier: 'adaptive',
    ops_signal: 'Context memory and pinned knowledge',
    intelligence_detail: 'Pinned notes preserve institutional memory for AI-assisted operators.',
    scoreHints: ['notes'],
  },
  {
    id: 'quotes',
    label: 'Quotes',
    tab: 'quotes',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Commercial proposal lifecycle',
    intelligence_detail: 'Quote acceptance path links directly into invoice automation.',
    scoreHints: ['quotes', 'invoices'],
  },
  {
    id: 'invoices',
    label: 'Invoices',
    tab: 'invoices',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Cashflow and collections telemetry',
    intelligence_detail: 'Invoice status transitions provide real-time finance operation visibility.',
    scoreHints: ['invoices', 'forecast'],
  },
  {
    id: 'sequences',
    label: 'Sequences',
    tab: 'sequences',
    autonomy_tier: 'predictive',
    ops_signal: 'Lifecycle orchestration cadence',
    intelligence_detail: 'Step orchestration enables automated nurturing by contact intent state.',
    scoreHints: ['sequences'],
  },
  {
    id: 'automation',
    label: 'Automation',
    tab: 'workflows',
    autonomy_tier: 'autonomous',
    ops_signal: 'Rule execution and self-healing flows',
    intelligence_detail: 'Workflow run telemetry and rule triggers power agentic orchestration.',
    scoreHints: ['workflowRules', 'automationRecipes'],
  },
  {
    id: 'projects',
    label: 'Projects',
    tab: 'projects',
    autonomy_tier: 'adaptive',
    ops_signal: 'Cross-functional delivery reliability',
    intelligence_detail: 'Project board state allows operations leaders to unblock execution quickly.',
    scoreHints: ['projects'],
  },
  {
    id: 'extensibility',
    label: 'Extensibility + API',
    tab: 'extensions',
    autonomy_tier: 'autonomous',
    ops_signal: 'Programmability and external integration control',
    intelligence_detail: 'Custom entities, recipes, and API tokens expose enterprise-grade extension paths.',
    scoreHints: ['entityTypes', 'automationRecipes', 'apiTokens', 'webhooks'],
  },
  {
    id: 'reports',
    label: 'Reports',
    tab: 'reports',
    autonomy_tier: 'predictive',
    ops_signal: 'Executive diagnostics and trend confidence',
    intelligence_detail: 'KPI and forecast surfaces provide strategic guidance for revenue operations.',
    scoreHints: ['kpis', 'forecast', 'executiveAnalytics'],
  },
  {
    id: 'enterprise_ops',
    label: 'Enterprise Ops',
    tab: 'enterprise',
    autonomy_tier: 'autonomous',
    ops_signal: 'Resilience controls and anomaly radar',
    intelligence_detail: 'Live sync + backup orchestration provide resilient, self-governing operations.',
    scoreHints: ['liveSync', 'backupOps', 'executiveAnalytics'],
  },
  {
    id: 'settings_sla',
    label: 'Settings / SLA',
    tab: 'settings',
    autonomy_tier: 'self_optimizing',
    ops_signal: 'Policy governance and support compliance',
    intelligence_detail: 'SLA rules and webhook contracts enforce enterprise governance controls.',
    scoreHints: ['slaRules', 'webhooks'],
  },
];

const API_BASE = '/api/fastapi';
const DEFAULT_TENANT = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? 'tenant-demo';

const STAGE_COLOR: Record<string, string> = {
  prospect: '#1bc7ff',
  qualified: '#26d78e',
  proposal: '#a78bfa',
  negotiation: '#f59e0b',
  closed_won: '#22c55e',
  closed_lost: '#ef4444',
};
const PRIORITY_COLOR: Record<string, string> = {
  low: '#6b7280',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#dc2626',
};

async function apiRequest(path: string, tenantId: string, init?: RequestInit) {
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

function getForecastWindow(range: AnalyticsRange): number {
  if (range === '7d') return 4;
  if (range === '30d') return 8;
  return 12;
}

function getStageColor(index: number): string {
  const colors = ['#0ea5e9', '#22c55e', '#f59e0b', '#f43f5e'];
  return colors[index] ?? '#f43f5e';
}

function getReadinessState(score: number): CrmAutonomyModule['state'] {
  if (score >= 92) return 'operational';
  if (score >= 74) return 'active';
  return 'seeded';
}

function getTierColor(tier: CrmAutonomyModule['autonomy_tier']): string {
  if (tier === 'autonomous') return '#22c55e';
  if (tier === 'self_optimizing') return '#0ea5e9';
  if (tier === 'predictive') return '#a78bfa';
  return '#f59e0b';
}

function getModuleStateColor(state: CrmAutonomyModule['state']): string {
  if (state === 'operational') return '#22c55e';
  if (state === 'active') return '#0ea5e9';
  return '#f59e0b';
}

function getReadinessColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 75) return '#0ea5e9';
  return '#f59e0b';
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
  selectedEntityKey: string;
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
    apiRequest('/crm/webhooks', params.tenantId),
    apiRequest('/crm/leads?limit=100', params.tenantId),
    apiRequest(`/crm/tasks?${tasksParams}&limit=100`, params.tenantId),
    apiRequest(`/crm/tickets?${ticketsParams}&limit=100`, params.tenantId),
    apiRequest('/crm/campaigns?limit=100', params.tenantId),
    apiRequest('/crm/segments', params.tenantId),
    apiRequest('/crm/notes?limit=100', params.tenantId),
    apiRequest('/crm/quotes?limit=100', params.tenantId),
    apiRequest('/crm/invoices?limit=100', params.tenantId),
    apiRequest('/crm/email-sequences', params.tenantId),
    apiRequest('/crm/workflow-rules', params.tenantId),
    apiRequest('/crm/sla-rules', params.tenantId),
    apiRequest(`/crm/reports/kpis?${reportsParams.toString()}`, params.tenantId),
    apiRequest(`/crm/reports/forecast?${reportsParams.toString()}`, params.tenantId),
    apiRequest(`/crm/reports/executive-analytics?${reportsParams.toString()}`, params.tenantId),
    apiRequest('/crm/ops/backup', params.tenantId),
    apiRequest('/crm/ops/live-sync', params.tenantId),
    apiRequest('/crm/projects', params.tenantId),
    apiRequest('/crm/custom-entities/types', params.tenantId),
    apiRequest('/crm/automation/recipes', params.tenantId),
    apiRequest('/crm/api-tokens', params.tenantId),
  ]);

  const failedSections: string[] = [];
  const markFailed = (label: string) => failedSections.push(label);

  const summaryRes = requests[0];
  const summary = summaryRes.status === 'fulfilled' ? (summaryRes.value.summary as Summary) : null;
  if (summaryRes.status !== 'fulfilled') markFailed('Overview');

  const contactsRes = requests[1];
  const contacts = contactsRes.status === 'fulfilled' ? ((contactsRes.value.contacts ?? []) as Contact[]) : [];
  if (contactsRes.status !== 'fulfilled') markFailed('Contacts');

  const companiesRes = requests[2];
  const companies = companiesRes.status === 'fulfilled' ? ((companiesRes.value.companies ?? []) as Company[]) : [];
  if (companiesRes.status !== 'fulfilled') markFailed('Companies');

  const dealsRes = requests[3];
  const deals = dealsRes.status === 'fulfilled' ? ((dealsRes.value.deals ?? []) as Deal[]) : [];
  if (dealsRes.status !== 'fulfilled') markFailed('Deals');

  const activitiesRes = requests[4];
  const activities = activitiesRes.status === 'fulfilled' ? ((activitiesRes.value.activities ?? []) as Activity[]) : [];
  if (activitiesRes.status !== 'fulfilled') markFailed('Activities');

  const pipelineRes = requests[5];
  const pipeline = pipelineRes.status === 'fulfilled' ? ((pipelineRes.value.pipeline ?? []) as PipelineRow[]) : [];
  if (pipelineRes.status !== 'fulfilled') markFailed('Pipeline');

  const webhooksRes = requests[6];
  const webhooks = webhooksRes.status === 'fulfilled' ? ((webhooksRes.value.webhooks ?? []) as CRMWebhook[]) : [];
  if (webhooksRes.status !== 'fulfilled') markFailed('Webhooks');

  const leadsRes = requests[7];
  const leads = leadsRes.status === 'fulfilled' ? ((leadsRes.value.leads ?? []) as Lead[]) : [];
  if (leadsRes.status !== 'fulfilled') markFailed('Leads');

  const tasksRes = requests[8];
  const tasks = tasksRes.status === 'fulfilled' ? ((tasksRes.value.tasks ?? []) as Task[]) : [];
  if (tasksRes.status !== 'fulfilled') markFailed('Tasks');

  const ticketsRes = requests[9];
  const tickets = ticketsRes.status === 'fulfilled' ? ((ticketsRes.value.tickets ?? []) as Ticket[]) : [];
  if (ticketsRes.status !== 'fulfilled') markFailed('Support');

  const campaignsRes = requests[10];
  const campaigns = campaignsRes.status === 'fulfilled' ? ((campaignsRes.value.campaigns ?? []) as Campaign[]) : [];
  if (campaignsRes.status !== 'fulfilled') markFailed('Campaigns');

  const segmentsRes = requests[11];
  const segments = segmentsRes.status === 'fulfilled' ? ((segmentsRes.value.segments ?? []) as Segment[]) : [];
  if (segmentsRes.status !== 'fulfilled') markFailed('Segments');

  const notesRes = requests[12];
  const notes = notesRes.status === 'fulfilled' ? ((notesRes.value.notes ?? []) as Note[]) : [];
  if (notesRes.status !== 'fulfilled') markFailed('Notes');

  const quotesRes = requests[13];
  const quotes = quotesRes.status === 'fulfilled' ? ((quotesRes.value.quotes ?? []) as Quote[]) : [];
  if (quotesRes.status !== 'fulfilled') markFailed('Quotes');

  const invoicesRes = requests[14];
  const invoices = invoicesRes.status === 'fulfilled' ? ((invoicesRes.value.invoices ?? []) as CRMInvoice[]) : [];
  if (invoicesRes.status !== 'fulfilled') markFailed('Invoices');

  const seqRes = requests[15];
  const sequences = seqRes.status === 'fulfilled' ? ((seqRes.value.sequences ?? []) as EmailSequence[]) : [];
  if (seqRes.status !== 'fulfilled') markFailed('Sequences');

  const wfRes = requests[16];
  const workflowRules = wfRes.status === 'fulfilled' ? ((wfRes.value.workflow_rules ?? []) as WorkflowRule[]) : [];
  if (wfRes.status !== 'fulfilled') markFailed('Automation');

  const slaRes = requests[17];
  const slaRules = slaRes.status === 'fulfilled' ? ((slaRes.value.sla_rules ?? []) as SLARule[]) : [];
  if (slaRes.status !== 'fulfilled') markFailed('Settings / SLA');

  const kpisRes = requests[18];
  const kpis = kpisRes.status === 'fulfilled' ? ((kpisRes.value.kpis ?? null) as KPIs | null) : null;
  const windowDays =
    kpisRes.status === 'fulfilled' && typeof kpisRes.value.window_days === 'number' ? kpisRes.value.window_days : null;
  if (kpisRes.status !== 'fulfilled') markFailed('Reports');

  const forecastRes = requests[19];
  const forecast = forecastRes.status === 'fulfilled' ? (forecastRes.value as Forecast) : null;
  if (forecastRes.status !== 'fulfilled') markFailed('Reports');

  const executiveRes = requests[20];
  const executiveAnalytics = executiveRes.status === 'fulfilled' ? (executiveRes.value as ExecutiveAnalytics) : null;
  if (executiveRes.status !== 'fulfilled') markFailed('Reports');

  const backupOpsRes = requests[21];
  const backupOps = backupOpsRes.status === 'fulfilled' ? (backupOpsRes.value as CRMBackupOps) : null;
  if (backupOpsRes.status !== 'fulfilled') markFailed('Enterprise Ops');

  const syncRes = requests[22];
  const liveSync = syncRes.status === 'fulfilled' ? ((syncRes.value.sync ?? null) as CRMLiveSync | null) : null;
  if (syncRes.status !== 'fulfilled') markFailed('Enterprise Ops');

  const projectsRes = requests[23];
  const projects = projectsRes.status === 'fulfilled' ? ((projectsRes.value.projects ?? []) as Project[]) : [];
  if (projectsRes.status !== 'fulfilled') markFailed('Projects');

  const entityTypesRes = requests[24];
  const entityTypes =
    entityTypesRes.status === 'fulfilled' ? ((entityTypesRes.value.entity_types ?? []) as CustomEntityType[]) : [];
  if (entityTypesRes.status !== 'fulfilled') markFailed('Extensibility + API');

  const recipesRes = requests[25];
  const automationRecipes =
    recipesRes.status === 'fulfilled' ? ((recipesRes.value.recipes ?? []) as AutomationRecipe[]) : [];
  if (recipesRes.status !== 'fulfilled') markFailed('Extensibility + API');

  const tokensRes = requests[26];
  const apiTokens = tokensRes.status === 'fulfilled' ? ((tokensRes.value.api_tokens ?? []) as APIToken[]) : [];
  if (tokensRes.status !== 'fulfilled') markFailed('Extensibility + API');

  const activeEntityKey = params.selectedEntityKey || entityTypes[0]?.key || '';
  let entityRecords: CustomEntityRecord[] = [];
  if (activeEntityKey) {
    try {
      const recordsRes = await apiRequest(`/crm/custom-entities/${activeEntityKey}/records?limit=100`, params.tenantId);
      entityRecords = (recordsRes.records ?? []) as CustomEntityRecord[];
    } catch {
      markFailed('Extensibility + API');
    }
  }

  return {
    summary,
    pipeline,
    contacts,
    companies,
    deals,
    activities,
    webhooks,
    leads,
    tasks,
    tickets,
    campaigns,
    segments,
    notes,
    quotes,
    invoices,
    sequences,
    workflowRules,
    slaRules,
    kpis,
    windowDays,
    forecast,
    executiveAnalytics,
    backupOps,
    liveSync,
    projects,
    entityTypes,
    entityRecords,
    automationRecipes,
    apiTokens,
    activeEntityKey,
    failedSections: Array.from(new Set(failedSections)),
  };
}

export default function CRMPage() {
  // NOSONAR
  const [tenantId] = useState(DEFAULT_TENANT);
  const [tab, setTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loadWarning, setLoadWarning] = useState('');
  const [success, setSuccess] = useState('');
  const [analyticsRange, setAnalyticsRange] = useState<AnalyticsRange>('30d');
  const [windowDays, setWindowDays] = useState<number>(30);

  // Core CRM
  const [summary, setSummary] = useState<Summary | null>(null);
  const [pipeline, setPipeline] = useState<PipelineRow[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [webhooks, setWebhooks] = useState<CRMWebhook[]>([]);

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
  const [workflowRules, setWorkflowRules] = useState<WorkflowRule[]>([]);
  const [slaRules, setSlaRules] = useState<SLARule[]>([]);
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [executiveAnalytics, setExecutiveAnalytics] = useState<ExecutiveAnalytics | null>(null);
  const [backupOps, setBackupOps] = useState<CRMBackupOps | null>(null);
  const [liveSync, setLiveSync] = useState<CRMLiveSync | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [entityTypes, setEntityTypes] = useState<CustomEntityType[]>([]);
  const [entityRecords, setEntityRecords] = useState<CustomEntityRecord[]>([]);
  const [automationRecipes, setAutomationRecipes] = useState<AutomationRecipe[]>([]);
  const [apiTokens, setApiTokens] = useState<APIToken[]>([]);

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
  const [workflowForm, setWorkflowForm] = useState({
    name: '',
    trigger: 'contact.created',
    action: 'assign_contact',
    enabled: true,
  });
  const [slaForm, setSlaForm] = useState({
    name: '',
    priority: 'medium',
    first_response_hours: '4',
    resolution_hours: '24',
  });
  const [webhookForm, setWebhookForm] = useState({ event: 'contact.created', target_url: '', secret: '' });
  const [projectForm, setProjectForm] = useState({
    name: '',
    description: '',
    owner: '',
    status: 'planning',
    due_date: '',
  });
  const [entityTypeForm, setEntityTypeForm] = useState({
    key: '',
    name: '',
    description: '',
    fields_json: '{"label":"","type":"text"}',
  });
  const [selectedEntityKey, setSelectedEntityKey] = useState('');
  const [entityRecordForm, setEntityRecordForm] = useState({ values_json: '{"name":""}' });
  const [recipeForm, setRecipeForm] = useState({ name: '', trigger: 'deal.created', action: 'create_task' });
  const [apiTokenForm, setApiTokenForm] = useState({ name: '', scopes: 'crm.read,crm.write' });
  const [backupConfigForm, setBackupConfigForm] = useState<CRMBackupConfig>({
    incremental_minutes: 5,
    full_backup_weekday: 'sunday',
    full_backup_hour_utc: 3,
    retention_days: 30,
    enabled: true,
  });
  const recipeTemplates = [
    {
      label: 'Deal Won -> Create Invoice',
      payload: {
        name: 'Deal Won Invoice Automation',
        trigger: 'deal.stage_changed',
        action: 'create_invoice',
        config: { when_stage: 'closed_won' },
        enabled: true,
      },
    },
    {
      label: 'Ticket Escalated -> Slack',
      payload: {
        name: 'Escalation Slack Alert',
        trigger: 'ticket.escalated',
        action: 'call_webhook',
        config: { channel: 'slack', severity: 'high' },
        enabled: true,
      },
    },
    {
      label: 'Lead Converted -> Enroll Sequence',
      payload: {
        name: 'Converted Lead Nurture',
        trigger: 'lead.converted',
        action: 'add_to_sequence',
        config: { sequence: 'welcome' },
        enabled: true,
      },
    },
  ] as const;
  const templateAlreadyExists = (payload: (typeof recipeTemplates)[number]['payload']) => {
    const name = payload.name.trim().toLowerCase();
    const trigger = payload.trigger.trim().toLowerCase();
    const action = payload.action.trim().toLowerCase();
    return automationRecipes.some(
      (recipe) =>
        recipe.name.trim().toLowerCase() === name &&
        recipe.trigger.trim().toLowerCase() === trigger &&
        recipe.action.trim().toLowerCase() === action
    );
  };

  const openDeals = useMemo(() => deals.filter((d) => d.stage !== 'closed_won' && d.stage !== 'closed_lost'), [deals]);

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
        selectedEntityKey,
      });

      setSummary(data.summary);
      setPipeline(data.pipeline);
      setContacts(data.contacts);
      setCompanies(data.companies);
      setDeals(data.deals);
      setActivities(data.activities);
      setWebhooks(data.webhooks);
      setLeads(data.leads);
      setTasks(data.tasks);
      setTickets(data.tickets);
      setCampaigns(data.campaigns);
      setSegments(data.segments);
      setNotes(data.notes);
      setQuotes(data.quotes);
      setInvoices(data.invoices);
      setSequences(data.sequences);
      setWorkflowRules(data.workflowRules);
      setSlaRules(data.slaRules);
      setKpis(data.kpis);
      if (data.windowDays !== null) setWindowDays(data.windowDays);
      setForecast(data.forecast);
      setExecutiveAnalytics(data.executiveAnalytics);
      setBackupOps(data.backupOps);
      setLiveSync(data.liveSync);
      setProjects(data.projects);
      setEntityTypes(data.entityTypes);
      setEntityRecords(data.entityRecords);
      setAutomationRecipes(data.automationRecipes);
      setApiTokens(data.apiTokens);
      if (!selectedEntityKey && data.activeEntityKey) setSelectedEntityKey(data.activeEntityKey);

      if (data.failedSections.length === 0) {
        setLoadWarning('');
      } else if (data.failedSections.length === 27) {
        setError('Unable to load CRM data right now. Check the FastAPI service and retry.');
      } else {
        setError('');
        setLoadWarning(`Some CRM sections are temporarily unavailable: ${data.failedSections.join(', ')}.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load CRM data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const requestedTab = new URLSearchParams(globalThis.location.search).get('tab');
    if (requestedTab === 'enterprise') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTab('enterprise');
    }
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analyticsRange]);

  useEffect(() => {
    if (!backupOps?.config) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBackupConfigForm({
      incremental_minutes: Number(backupOps.config.incremental_minutes) || 5,
      full_backup_weekday: backupOps.config.full_backup_weekday || 'sunday',
      full_backup_hour_utc: Number(backupOps.config.full_backup_hour_utc) || 3,
      retention_days: Number(backupOps.config.retention_days) || 30,
      enabled: Boolean(backupOps.config.enabled),
    });
  }, [backupOps]);

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

  async function saveBackupConfig() {
    await req('/crm/ops/backup/config', 'POST', backupConfigForm);
  }

  async function runBackup(mode: 'incremental' | 'full') {
    await req(`/crm/ops/backup/run?mode=${mode}&source=crm-ui`, 'POST', {});
  }

  async function toggleLiveSync(enabled: boolean) {
    await req('/crm/ops/live-sync/toggle', 'POST', {
      enabled,
      interval_seconds: liveSync?.interval_seconds ?? 30,
    });
  }

  async function runLiveSyncNow() {
    await req('/crm/ops/live-sync/run', 'POST', {});
  }

  async function drillToTaskStatus(status: string) {
    setTaskStatusFilter(status === 'all' ? '' : status);
    setTab('tasks');
    await loadData();
  }

  async function drillToTicketStatus(status: string) {
    setTicketsStatusFilter(status === 'all' ? '' : status);
    setTab('tickets');
    await loadData();
  }

  function exportAnalyticsCsv() {
    const quote = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;
    const lines = [
      ['section', 'label', 'value'].map(quote).join(','),
      ...leadSourceBreakdown.map((row) => ['lead_source', row.source, row.count].map(quote).join(',')),
      ...taskStatusGraph.map((row) => ['task_status', row.label, row.value].map(quote).join(',')),
      ...ticketStatusGraph.map((row) => ['ticket_status', row.label, row.value].map(quote).join(',')),
      ...topReadinessModules.map((row) => ['module_readiness', row.label, row.readiness_score].map(quote).join(',')),
    ];

    downloadFile(
      `crm-analytics-${analyticsRange}-${new Date().toISOString().slice(0, 10)}.csv`,
      `${lines.join('\n')}\n`,
      'text/csv;charset=utf-8'
    );
    showSuccess('Analytics CSV exported');
  }

  function exportForecastPng() {
    const width = 720;
    const height = 260;
    const paddingX = 44;
    const paddingY = 26;
    const innerWidth = width - paddingX * 2;
    const innerHeight = height - paddingY * 2;
    const series = forecastSeriesWindow.length ? forecastSeriesWindow : [1];
    const max = Math.max(1, ...series);
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i += 1) {
      const y = paddingY + (i / 4) * innerHeight;
      ctx.beginPath();
      ctx.moveTo(paddingX, y);
      ctx.lineTo(width - paddingX, y);
      ctx.stroke();
    }

    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 3;
    ctx.beginPath();
    series.forEach((value, index) => {
      const x = paddingX + (index / Math.max(1, series.length - 1)) * innerWidth;
      const y = paddingY + innerHeight - (value / max) * innerHeight;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = '#e2e8f0';
    ctx.font = '600 14px Segoe UI';
    ctx.fillText(`Forecast Momentum (${analyticsRange})`, paddingX, 18);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crm-forecast-${analyticsRange}-${new Date().toISOString().slice(0, 10)}.png`;
      a.click();
      URL.revokeObjectURL(url);
      showSuccess('Forecast PNG exported');
    }, 'image/png');
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
    color: '#00101e',
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
  const dangerBtn = { ...btn, background: '#ef4444', color: '#fff' } as const;

  const ALL_TABS: Tab[] = [
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
    'workflows',
    'projects',
    'extensions',
    'reports',
    'enterprise',
    'settings',
  ];
  const TAB_LABELS: Record<Tab, string> = {
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
    workflows: 'Automation',
    projects: 'Projects',
    extensions: 'Extensibility + API',
    reports: 'Reports',
    enterprise: 'Enterprise Ops',
    settings: 'Settings / SLA',
  };
  const crmBars = pipeline.slice(0, 4).map((row) => ({ label: row.display, value: row.count }));
  const monthlyForecastLine = Object.values(forecast?.monthly_forecast ?? {}).map((value) =>
    typeof value === 'number' ? value : 0
  );
  const forecastSparkSeries = monthlyForecastLine.length ? monthlyForecastLine : [12, 18, 17, 24, 29, 33, 31, 38];
  const rangeWindow = getForecastWindow(analyticsRange);
  const forecastSeriesWindow = forecastSparkSeries.slice(-rangeWindow);
  const stageRing = Object.entries(summary?.stage_counts ?? {})
    .slice(0, 4)
    .map(([label, value], index) => ({
      label,
      value: typeof value === 'number' ? value : 0,
      color: getStageColor(index),
    }));
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
      { label: 'Open', value: tasks.filter((task) => task.status === 'open').length, color: '#0ea5e9' },
      {
        label: 'In Progress',
        value: tasks.filter((task) => task.status === 'in_progress').length,
        color: '#a78bfa',
      },
      { label: 'Completed', value: tasks.filter((task) => task.status === 'completed').length, color: '#22c55e' },
      { label: 'Cancelled', value: tasks.filter((task) => task.status === 'cancelled').length, color: '#f97316' },
    ],
    [tasks]
  );
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const ticketStatusGraph = useMemo(
    () => [
      { label: 'Open', value: tickets.filter((ticket) => ticket.status === 'open').length, color: '#ef4444' },
      {
        label: 'In Progress',
        value: tickets.filter((ticket) => ticket.status === 'in_progress').length,
        color: '#f59e0b',
      },
      { label: 'Resolved', value: tickets.filter((ticket) => ticket.status === 'resolved').length, color: '#22c55e' },
      { label: 'Closed', value: tickets.filter((ticket) => ticket.status === 'closed').length, color: '#94a3b8' },
    ],
    [tickets]
  );
  const forecastLinePoints = useMemo(() => {
    const width = 320;
    const height = 84;
    const max = Math.max(1, ...forecastSeriesWindow);
    const lastIndex = Math.max(1, forecastSeriesWindow.length - 1);

    return forecastSeriesWindow
      .map((value, index) => {
        const x = (index / lastIndex) * width;
        const y = height - (value / max) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }, [forecastSeriesWindow]);
  const autonomyModules = useMemo<CrmAutonomyModule[]>(() => {
    const signalCounts: Record<string, number> = {
      summary: summary ? 1 : 0,
      contacts: contacts.length,
      companies: companies.length,
      deals: deals.length,
      activities: activities.length,
      pipeline: pipeline.length,
      leads: leads.length,
      tasks: tasks.length,
      tickets: tickets.length,
      campaigns: campaigns.length,
      segments: segments.length,
      notes: notes.length,
      quotes: quotes.length,
      invoices: invoices.length,
      sequences: sequences.length,
      workflowRules: workflowRules.length,
      projects: projects.length,
      entityTypes: entityTypes.length,
      automationRecipes: automationRecipes.length,
      apiTokens: apiTokens.length,
      webhooks: webhooks.length,
      kpis: kpis ? 1 : 0,
      forecast: forecast ? 1 : 0,
      executiveAnalytics: executiveAnalytics ? 1 : 0,
      backupOps: backupOps ? 1 : 0,
      liveSync: liveSync ? 1 : 0,
      slaRules: slaRules.length,
    };

    return MODULE_BLUEPRINTS.map((moduleDef) => {
      const matchedSignals = moduleDef.scoreHints.reduce((count, key) => {
        const value = signalCounts[key] ?? 0;
        return count + (value > 0 ? 1 : 0);
      }, 0);

      const hintTotal = Math.max(1, moduleDef.scoreHints.length);
      const score = Math.round(54 + (matchedSignals / hintTotal) * 46);
      const state: CrmAutonomyModule['state'] = getReadinessState(score);

      return {
        id: moduleDef.id,
        label: moduleDef.label,
        tab: moduleDef.tab,
        autonomy_tier: moduleDef.autonomy_tier,
        ops_signal: moduleDef.ops_signal,
        intelligence_detail: moduleDef.intelligence_detail,
        readiness_score: score,
        state,
      };
    });
  }, [
    summary,
    contacts,
    companies,
    deals,
    activities,
    pipeline,
    leads,
    tasks,
    tickets,
    campaigns,
    segments,
    notes,
    quotes,
    invoices,
    sequences,
    workflowRules,
    projects,
    entityTypes,
    automationRecipes,
    apiTokens,
    webhooks,
    kpis,
    forecast,
    executiveAnalytics,
    backupOps,
    liveSync,
    slaRules,
  ]);
  const autonomyAverageScore =
    autonomyModules.length > 0
      ? Math.round(autonomyModules.reduce((acc, item) => acc + item.readiness_score, 0) / autonomyModules.length)
      : 0;
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const topReadinessModules = useMemo(
    () => [...autonomyModules].sort((a, b) => b.readiness_score - a.readiness_score).slice(0, 10),
    [autonomyModules]
  );

  return (
    <main style={ps}>
      <div style={{ maxWidth: 1240, margin: '0 auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 26 }}>CRM Command Center</h1>
            <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
              Full-stack SaaS CRM — contacts, deals, leads, support, automation, billing.
            </p>
          </div>
          <button style={btn} onClick={() => void loadData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </header>

        {error ? (
          <div
            style={{ border: '1px solid #ef4444', color: '#ef4444', borderRadius: 12, padding: 12, marginBottom: 14 }}
          >
            {error}
          </div>
        ) : null}
        {loadWarning ? (
          <div
            style={{ border: '1px solid #f59e0b', color: '#f59e0b', borderRadius: 12, padding: 12, marginBottom: 14 }}
          >
            {loadWarning}
          </div>
        ) : null}

        <AnalyticsExecutiveBoard
          title="CRM Enterprise Ops Analytics"
          subtitle="Revenue, pipeline, service operations, and enterprise governance signals in one command surface."
          kpis={[
            {
              label: 'Contacts',
              value: String(kpis?.total_contacts ?? summary?.contacts ?? 0),
              delta: `${kpis?.total_leads ?? leads.length} leads`,
              trend: 'up',
            },
            {
              label: 'Open Deals',
              value: String(summary?.deals_open ?? 0),
              delta: `${summary?.deals_total ?? 0} total deals`,
              trend: (summary?.deals_open ?? 0) > 0 ? 'up' : 'flat',
            },
            {
              label: 'Win Rate',
              value: `${Math.round(kpis?.win_rate_pct ?? 0)}%`,
              delta: 'Revenue conversion',
              trend: (kpis?.win_rate_pct ?? 0) >= 30 ? 'up' : 'down',
            },
            {
              label: 'Forecast',
              value: fmt(summary?.forecast_revenue ?? 0),
              delta: 'Weighted pipeline',
              trend: (summary?.forecast_revenue ?? 0) >= 0 ? 'up' : 'flat',
            },
            {
              label: 'Open Tickets',
              value: String(kpis?.open_tickets ?? tickets.filter((ticket) => ticket.status === 'open').length),
              delta: `${kpis?.escalated_tickets ?? 0} escalated`,
              trend: (kpis?.escalated_tickets ?? 0) <= 3 ? 'up' : 'down',
            },
            {
              label: 'Overdue Tasks',
              value: String(kpis?.overdue_tasks ?? 0),
              delta: `${kpis?.open_tasks ?? tasks.filter((task) => task.status === 'open').length} open tasks`,
              trend: (kpis?.overdue_tasks ?? 0) === 0 ? 'up' : 'down',
            },
          ]}
          bars={crmBars}
          line={monthlyForecastLine.length ? monthlyForecastLine : [12, 18, 17, 24, 29, 33, 31, 38]}
          ring={
            stageRing.length
              ? stageRing
              : [
                  { label: 'Prospect', value: 8, color: '#0ea5e9' },
                  { label: 'Qualified', value: 6, color: '#22c55e' },
                  { label: 'Proposal', value: 4, color: '#f59e0b' },
                  { label: 'Closed Won', value: 2, color: '#f43f5e' },
                ]
          }
        />

        <section style={{ ...card, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <h3 style={{ margin: 0 }}>Autonomous CRM Module Matrix</h3>

              <section style={{ ...card, marginBottom: 12 }}>
                <div style={{ marginBottom: 8 }}>
                  <h3 style={{ margin: 0 }}>Advanced Analytics Graphs</h3>
                  <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 12 }}>
                    Live conversion, workload, and forecast momentum visuals for enterprise operations.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                  <select
                    style={{ ...inp, width: 170, marginBottom: 0 }}
                    value={analyticsRange}
                    onChange={(e) => setAnalyticsRange(e.target.value as AnalyticsRange)}
                  >
                    <option value="7d">Range: 7 Days</option>
                    <option value="30d">Range: 30 Days</option>
                    <option value="90d">Range: 90 Days</option>
                  </select>
                  <button style={ghostBtn} onClick={exportAnalyticsCsv}>
                    Export Analytics CSV
                  </button>
                  <button style={ghostBtn} onClick={exportForecastPng}>
                    Export Forecast PNG
                  </button>
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--muted)',
                      border: '1px solid var(--line)',
                      borderRadius: 6,
                      padding: '2px 8px',
                      alignSelf: 'center',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    Server window: {windowDays}d
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
                  <div style={{ ...card, background: 'var(--bg)', padding: 12 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6 }}>Lead Source Distribution</div>
                    {leadSourceBreakdown.map((row) => {
                      const max = Math.max(1, ...leadSourceBreakdown.map((item) => item.count));
                      const width = Math.round((row.count / max) * 100);
                      return (
                        <button
                          key={row.source}
                          style={{
                            ...ghostBtn,
                            width: '100%',
                            textAlign: 'left',
                            padding: 0,
                            marginBottom: 8,
                            border: 'none',
                          }}
                          onClick={() => {
                            setTab('leads');
                            showSuccess(`Focused on lead source: ${row.source}`);
                          }}
                        >
                          <div
                            style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}
                          >
                            <span>{row.source}</span>
                            <span>{row.count}</span>
                          </div>
                          <div style={{ height: 8, borderRadius: 999, background: 'var(--line)', overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${width}%`,
                                height: '100%',
                                background: 'linear-gradient(90deg, #22c55e, #0ea5e9)',
                              }}
                            />
                          </div>
                        </button>
                      );
                    })}
                    {!leadSourceBreakdown.length && (
                      <div style={{ color: 'var(--muted)', fontSize: 12 }}>No lead source data.</div>
                    )}
                  </div>

                  <div style={{ ...card, background: 'var(--bg)', padding: 12 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6 }}>Execution Throughput Graph</div>
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Tasks</div>
                      {taskStatusGraph.map((row) => {
                        const max = Math.max(1, ...taskStatusGraph.map((item) => item.value));
                        return (
                          <button
                            key={row.label}
                            style={{
                              ...ghostBtn,
                              width: '100%',
                              textAlign: 'left',
                              padding: 0,
                              marginBottom: 4,
                              border: 'none',
                            }}
                            onClick={() => void drillToTaskStatus(row.label.toLowerCase().replace(' ', '_'))}
                          >
                            <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr 26px', gap: 6 }}>
                              <span style={{ fontSize: 11, color: 'var(--muted)' }}>{row.label}</span>
                              <div
                                style={{ height: 8, background: 'var(--line)', borderRadius: 999, overflow: 'hidden' }}
                              >
                                <div
                                  style={{
                                    height: '100%',
                                    width: `${Math.round((row.value / max) * 100)}%`,
                                    background: row.color,
                                  }}
                                />
                              </div>
                              <span style={{ fontSize: 11, textAlign: 'right' }}>{row.value}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Support</div>
                      {ticketStatusGraph.map((row) => {
                        const max = Math.max(1, ...ticketStatusGraph.map((item) => item.value));
                        return (
                          <button
                            key={row.label}
                            style={{
                              ...ghostBtn,
                              width: '100%',
                              textAlign: 'left',
                              padding: 0,
                              marginBottom: 4,
                              border: 'none',
                            }}
                            onClick={() => void drillToTicketStatus(row.label.toLowerCase().replace(' ', '_'))}
                          >
                            <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr 26px', gap: 6 }}>
                              <span style={{ fontSize: 11, color: 'var(--muted)' }}>{row.label}</span>
                              <div
                                style={{ height: 8, background: 'var(--line)', borderRadius: 999, overflow: 'hidden' }}
                              >
                                <div
                                  style={{
                                    height: '100%',
                                    width: `${Math.round((row.value / max) * 100)}%`,
                                    background: row.color,
                                  }}
                                />
                              </div>
                              <span style={{ fontSize: 11, textAlign: 'right' }}>{row.value}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div style={{ ...card, background: 'var(--bg)', padding: 12 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6 }}>Forecast Momentum (Sparkline)</div>
                    <svg
                      viewBox="0 0 320 88"
                      style={{ width: '100%', height: 96, marginBottom: 8 }}
                      aria-label="Forecast trend line"
                    >
                      <polyline
                        fill="none"
                        stroke="#22c55e"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={forecastLinePoints}
                      />
                    </svg>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>
                      Latest point: {fmt(forecastSeriesWindow.at(-1) ?? 0)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Top readiness modules</div>
                    {topReadinessModules.slice(0, 5).map((module) => (
                      <div
                        key={module.id}
                        style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' }}
                      >
                        <span>{module.label}</span>
                        <strong>{module.readiness_score}%</strong>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
              <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 12 }}>
                Enterprise-grade readiness model across all CRM Command Center modules.
              </p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Average Readiness</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: autonomyAverageScore >= 85 ? '#22c55e' : '#f59e0b' }}>
                {autonomyAverageScore}%
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 250px), 1fr))',
              gap: 8,
            }}
          >
            {autonomyModules.map((module) => {
              const tierColor = getTierColor(module.autonomy_tier);
              const stateColor = getModuleStateColor(module.state);

              return (
                <div key={module.id} style={{ ...card, background: 'var(--bg)', padding: 12 }}>
                  <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}
                  >
                    <strong style={{ fontSize: 14 }}>{module.label}</strong>
                    <span style={{ fontSize: 11, color: stateColor, fontWeight: 700, textTransform: 'uppercase' }}>
                      {module.state}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: tierColor,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      marginBottom: 6,
                    }}
                  >
                    {module.autonomy_tier.replace('_', ' ')}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>{module.ops_signal}</div>
                  <div style={{ fontSize: 12, marginBottom: 8 }}>{module.intelligence_detail}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>Readiness {module.readiness_score}%</span>
                    <button
                      style={{ ...ghostBtn, padding: '4px 8px', fontSize: 11 }}
                      onClick={() => setTab(module.tab)}
                    >
                      Open module
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {(error || success) && (
          <div
            style={{
              ...card,
              marginBottom: 12,
              borderColor: error ? '#ef444488' : '#26d78e88',
              color: error ? '#f87171' : '#34d399',
            }}
          >
            {error || success}
          </div>
        )}

        {/* Tab bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
          {ALL_TABS.map((t) => (
            <button
              key={t}
              style={{
                ...btn,
                background: t === tab ? 'var(--brand)' : 'transparent',
                color: t === tab ? '#00101e' : 'var(--text)',
                border: t === tab ? 'none' : '1px solid var(--line)',
                fontSize: 12,
                padding: '6px 10px',
              }}
              onClick={() => setTab(t)}
            >
              {TAB_LABELS[t]}
            </button>
          ))}
        </div>

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
                { label: 'Contacts', val: summary?.contacts ?? 0 },
                { label: 'Companies', val: summary?.companies ?? 0 },
                { label: 'Open Deals', val: summary?.deals_open ?? 0 },
                { label: 'Pipeline', val: fmt(summary?.pipeline_value ?? 0) },
                { label: 'Forecast', val: fmt(summary?.forecast_revenue ?? 0) },
                { label: 'Avg Score', val: summary?.avg_lead_score ?? 0 },
                { label: 'Leads', val: leads.length },
                { label: 'Open Tasks', val: tasks.filter((t) => t.status === 'open').length },
                { label: 'Open Tickets', val: tickets.filter((t) => t.status === 'open').length },
              ].map(({ label, val }) => (
                <div key={label} style={card}>
                  <div style={{ color: 'var(--muted)', fontSize: 11 }}>{label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{val}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Pipeline Stages</h3>
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
                {!activities.length && <div style={{ color: 'var(--muted)' }}>No activities yet.</div>}
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
                  placeholder={f.replace('_', ' ')}
                  value={contactForm[f]}
                  onChange={(e) => setContactForm((s) => ({ ...s, [f]: e.target.value }))}
                />
              ))}
              <select
                style={inp}
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
                {!contacts.length && <div style={{ color: 'var(--muted)' }}>No contacts yet.</div>}
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
                {!companies.length && <div style={{ color: 'var(--muted)' }}>No companies yet.</div>}
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
                            color: s === d.stage ? '#fff' : 'var(--text)',
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
                {!deals.length && <div style={{ color: 'var(--muted)' }}>No deals yet.</div>}
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
                {!activities.length && <div style={{ color: 'var(--muted)' }}>No activities yet.</div>}
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
                {!leads.length && <div style={{ color: 'var(--muted)' }}>No leads yet.</div>}
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
                              style={{ ...btn, fontSize: 11, padding: '3px 6px', marginTop: 4, background: '#22c55e' }}
                              onClick={() => void req(`/crm/tasks/${t.id}`, 'PATCH', { status: 'completed' })}
                            >
                              Done
                            </button>
                          )}
                        </div>
                      ))}
                    {!tasks.filter((t) => t.status === col).length && (
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>Empty</div>
                    )}
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
                          {t.escalated && <span style={{ color: '#ef4444', marginLeft: 6 }}>ESCALATED</span>}
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
                {!tickets.length && <div style={{ color: 'var(--muted)' }}>No tickets yet.</div>}
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
                {!campaigns.length && <div style={{ color: 'var(--muted)' }}>No campaigns yet.</div>}
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
              {!segments.length && <div style={{ color: 'var(--muted)' }}>No segments yet.</div>}
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
                {!notes.length && <div style={{ color: 'var(--muted)' }}>No notes yet.</div>}
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
                {!quotes.length && <div style={{ color: 'var(--muted)' }}>No quotes yet.</div>}
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
                        <span style={{ color: inv.status === 'paid' ? '#22c55e' : '#f59e0b' }}>{inv.status}</span> - due{' '}
                        {inv.due_date ?? '-'}
                      </div>
                    </div>
                    {inv.status === 'pending' && (
                      <button
                        style={{ ...btn, fontSize: 11, padding: '4px 8px', background: '#22c55e' }}
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
                {!invoices.length && <div style={{ color: 'var(--muted)' }}>No invoices yet.</div>}
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
                {!sequences.length && <div style={{ color: 'var(--muted)' }}>No sequences yet.</div>}
              </div>
            </div>
          </section>
        )}

        {/* WORKFLOWS */}
        {tab === 'workflows' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>New Workflow Rule</h3>
              <input
                style={inp}
                placeholder="Rule Name"
                value={workflowForm.name}
                onChange={(e) => setWorkflowForm((s) => ({ ...s, name: e.target.value }))}
              />
              <select
                style={inp}
                value={workflowForm.trigger}
                onChange={(e) => setWorkflowForm((s) => ({ ...s, trigger: e.target.value }))}
              >
                {[
                  'contact.created',
                  'deal.created',
                  'deal.stage_changed',
                  'lead.created',
                  'ticket.created',
                  'ticket.escalated',
                  'task.completed',
                ].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select
                style={inp}
                value={workflowForm.action}
                onChange={(e) => setWorkflowForm((s) => ({ ...s, action: e.target.value }))}
              >
                {[
                  'assign_contact',
                  'send_email',
                  'create_task',
                  'update_lead_score',
                  'send_slack_notification',
                  'add_to_sequence',
                  'create_ticket',
                ].map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
              <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <input
                  type="checkbox"
                  checked={workflowForm.enabled}
                  onChange={(e) => setWorkflowForm((s) => ({ ...s, enabled: e.target.checked }))}
                />
                <span>Enabled</span>
              </label>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/workflow-rules', 'POST', {
                    name: workflowForm.name,
                    trigger: workflowForm.trigger,
                    action: workflowForm.action,
                    conditions: {},
                    action_params: {},
                    enabled: workflowForm.enabled,
                  }).then(
                    (ok) =>
                      ok &&
                      setWorkflowForm({ name: '', trigger: 'contact.created', action: 'assign_contact', enabled: true })
                  )
                }
              >
                Create Rule
              </button>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Workflow Rules ({workflowRules.length})</h3>
              <div style={{ maxHeight: 440, overflow: 'auto' }}>
                {workflowRules.map((r) => (
                  <div
                    key={r.id}
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
                        {r.name}{' '}
                        <span style={{ fontSize: 11, color: r.enabled ? '#22c55e' : 'var(--muted)' }}>
                          {r.enabled ? 'ACTIVE' : 'PAUSED'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        Trigger: {r.trigger} - Action: {r.action}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        Runs: {r.run_count} - Last: {r.last_triggered_at ? fmtTime(r.last_triggered_at) : 'never'}
                      </div>
                    </div>
                    <button
                      style={{ ...btn, fontSize: 11, padding: '4px 8px' }}
                      onClick={() => void req(`/crm/workflow-rules/${r.id}/trigger`, 'POST')}
                    >
                      Run
                    </button>
                  </div>
                ))}
                {!workflowRules.length && <div style={{ color: 'var(--muted)' }}>No workflow rules yet.</div>}
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
              <h3 style={{ marginTop: 0 }}>Project Board ({projects.length})</h3>
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
                    {!projects.filter((p) => p.status === col).length && (
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>Empty</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* EXTENSIBILITY + API */}
        {tab === 'extensions' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Custom Entity Types</h3>
              <input
                style={inp}
                placeholder="entity key (e.g. assets)"
                value={entityTypeForm.key}
                onChange={(e) =>
                  setEntityTypeForm((s) => ({ ...s, key: e.target.value.toLowerCase().replaceAll(/[^a-z0-9_]/g, '') }))
                }
              />
              <input
                style={inp}
                placeholder="Display Name"
                value={entityTypeForm.name}
                onChange={(e) => setEntityTypeForm((s) => ({ ...s, name: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Description"
                value={entityTypeForm.description}
                onChange={(e) => setEntityTypeForm((s) => ({ ...s, description: e.target.value }))}
              />
              <textarea
                style={{ ...inp, minHeight: 70 }}
                placeholder="Fields JSON array (optional)"
                value={entityTypeForm.fields_json}
                onChange={(e) => setEntityTypeForm((s) => ({ ...s, fields_json: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() => {
                  let fields: Record<string, unknown>[] = [];
                  try {
                    const parsed = JSON.parse(entityTypeForm.fields_json);
                    if (Array.isArray(parsed)) fields = parsed as Record<string, unknown>[];
                  } catch {
                    /* ignore parse error */
                  }
                  void req('/crm/custom-entities/types', 'POST', {
                    key: entityTypeForm.key,
                    name: entityTypeForm.name,
                    description: entityTypeForm.description,
                    fields,
                  }).then(
                    (ok) =>
                      ok &&
                      setEntityTypeForm({
                        key: '',
                        name: '',
                        description: '',
                        fields_json: '[{"label":"Name","type":"text"}]',
                      })
                  );
                }}
              >
                Create Entity Type
              </button>

              <div style={{ marginTop: 12 }}>
                <select style={inp} value={selectedEntityKey} onChange={(e) => setSelectedEntityKey(e.target.value)}>
                  <option value="">Select entity type</option>
                  {entityTypes.map((et) => (
                    <option key={et.id} value={et.key}>
                      {et.name} ({et.key})
                    </option>
                  ))}
                </select>
                <textarea
                  style={{ ...inp, minHeight: 70 }}
                  placeholder="Record values JSON"
                  value={entityRecordForm.values_json}
                  onChange={(e) => setEntityRecordForm((s) => ({ ...s, values_json: e.target.value }))}
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    style={btn}
                    disabled={!selectedEntityKey}
                    onClick={() => {
                      if (!selectedEntityKey) return;
                      let values: Record<string, unknown> = {};
                      try {
                        values = JSON.parse(entityRecordForm.values_json) as Record<string, unknown>;
                      } catch {
                        /* ignore parse error */
                      }
                      void req(`/crm/custom-entities/${selectedEntityKey}/records`, 'POST', { values });
                    }}
                  >
                    Add Record
                  </button>
                  <button
                    style={ghostBtn}
                    disabled={!selectedEntityKey}
                    onClick={async () => {
                      if (!selectedEntityKey) return;
                      const res = await apiRequest(
                        `/crm/custom-entities/${selectedEntityKey}/records?limit=100`,
                        tenantId
                      ).catch(() => null);
                      if (res?.records) setEntityRecords(res.records as CustomEntityRecord[]);
                    }}
                  >
                    Load Records
                  </button>
                </div>
                <div style={{ marginTop: 8, maxHeight: 180, overflow: 'auto' }}>
                  {entityRecords.map((r) => (
                    <div key={r.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0' }}>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        #{r.id} - {r.entity_key}
                      </div>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 11 }}>{JSON.stringify(r.values)}</pre>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Automation Recipes</h3>
              <div style={{ display: 'grid', gap: 6, marginBottom: 10 }}>
                {recipeTemplates.map((template) => {
                  const exists = templateAlreadyExists(template.payload);
                  return (
                    <button
                      key={template.label}
                      style={{ ...ghostBtn, textAlign: 'left' as const, fontSize: 12, padding: '6px 10px' }}
                      onClick={() => {
                        if (exists) {
                          showSuccess(`Reusing existing template: ${template.payload.name}`);
                          return;
                        }
                        void req('/crm/automation/recipes', 'POST', template.payload);
                      }}
                    >
                      {exists ? 'Reuse existing: ' : '+ '}
                      {template.label}
                    </button>
                  );
                })}
              </div>
              <input
                style={inp}
                placeholder="Recipe Name"
                value={recipeForm.name}
                onChange={(e) => setRecipeForm((s) => ({ ...s, name: e.target.value }))}
              />
              <select
                style={inp}
                value={recipeForm.trigger}
                onChange={(e) => setRecipeForm((s) => ({ ...s, trigger: e.target.value }))}
              >
                {['contact.created', 'deal.created', 'deal.stage_changed', 'ticket.created', 'project.updated'].map(
                  (t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  )
                )}
              </select>
              <select
                style={inp}
                value={recipeForm.action}
                onChange={(e) => setRecipeForm((s) => ({ ...s, action: e.target.value }))}
              >
                {['create_task', 'send_email', 'create_ticket', 'call_webhook', 'update_entity'].map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/automation/recipes', 'POST', { ...recipeForm, config: {}, enabled: true }).then(
                    (ok) => ok && setRecipeForm({ name: '', trigger: 'deal.created', action: 'create_task' })
                  )
                }
              >
                Create Recipe
              </button>

              <div style={{ marginTop: 10, maxHeight: 180, overflow: 'auto' }}>
                {automationRecipes.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '6px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 13 }}>{r.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                        {r.trigger}
                        {' -> '}
                        {r.action} ({r.run_count} runs)
                      </div>
                    </div>
                    <button
                      style={{ ...btn, fontSize: 11, padding: '3px 7px' }}
                      onClick={() => void req(`/crm/automation/recipes/${r.id}/run`, 'POST')}
                    >
                      Run
                    </button>
                  </div>
                ))}
              </div>

              <h3 style={{ marginTop: 14 }}>API Tokens</h3>
              <input
                style={inp}
                placeholder="Token Name"
                value={apiTokenForm.name}
                onChange={(e) => setApiTokenForm((s) => ({ ...s, name: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Scopes (comma-separated)"
                value={apiTokenForm.scopes}
                onChange={(e) => setApiTokenForm((s) => ({ ...s, scopes: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/api-tokens', 'POST', {
                    name: apiTokenForm.name,
                    scopes: apiTokenForm.scopes
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }).then((ok) => ok && setApiTokenForm({ name: '', scopes: 'crm.read,crm.write' }))
                }
              >
                Create API Token
              </button>
              <div style={{ marginTop: 10, maxHeight: 180, overflow: 'auto' }}>
                {apiTokens.map((t) => (
                  <div key={t.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0' }}>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>
                      {t.name} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>({t.status})</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                      prefix: {t.token_prefix} - scopes: {(t.scopes ?? []).join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* REPORTS */}
        {tab === 'reports' && (
          <section>
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
                        <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>
                          {fmt(forecast.outstanding_invoices)}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Paid Invoices</div>
                        <div style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>
                          {fmt(forecast.paid_invoices)}
                        </div>
                      </div>
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>Monthly Forecast</div>
                      {Object.entries(forecast.monthly_forecast).map(([month, val]) => (
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
                      {!Object.keys(forecast.monthly_forecast).length && (
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
            <div style={{ ...card, marginTop: 10 }}>
              <h3 style={{ marginTop: 0 }}>Module Readiness Graph</h3>
              <div style={{ display: 'grid', gap: 6 }}>
                {topReadinessModules.map((module) => (
                  <div key={module.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                      <span>{module.label}</span>
                      <span>{module.readiness_score}%</span>
                    </div>
                    <div style={{ height: 8, background: 'var(--line)', borderRadius: 999, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${module.readiness_score}%`,
                          height: '100%',
                          background: getReadinessColor(module.readiness_score),
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* ENTERPRISE OPS */}
        {tab === 'enterprise' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Executive Analytics</h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))',
                  gap: 8,
                  marginBottom: 12,
                }}
              >
                <div style={{ ...card, padding: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Lead Conversion</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>
                    {executiveAnalytics?.overview.lead_conversion_rate_pct ?? 0}%
                  </div>
                </div>
                <div style={{ ...card, padding: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Escalation Ratio</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>
                    {executiveAnalytics?.overview.escalated_ticket_ratio_pct ?? 0}%
                  </div>
                </div>
                <div style={{ ...card, padding: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Overdue Tasks</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{executiveAnalytics?.overview.overdue_tasks ?? 0}</div>
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Pipeline Funnel</div>
                {(executiveAnalytics?.charts.pipeline_funnel ?? []).map((bucket) => {
                  const maxCount = Math.max(
                    1,
                    ...(executiveAnalytics?.charts.pipeline_funnel ?? []).map((item) => item.count)
                  );
                  const width = Math.round((bucket.count / maxCount) * 100);
                  return (
                    <div key={bucket.stage} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                        <span>{bucket.display}</span>
                        <span>{bucket.count}</span>
                      </div>
                      <div style={{ height: 7, borderRadius: 999, background: 'var(--line)', overflow: 'hidden' }}>
                        <div style={{ width: `${width}%`, height: '100%', background: 'var(--brand)' }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Closed-Won Trend (6 Months)</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 80px), 1fr))', gap: 8 }}>
                  {(executiveAnalytics?.charts.monthly_closed_won ?? []).map((row) => {
                    const maxValue = Math.max(
                      1,
                      ...(executiveAnalytics?.charts.monthly_closed_won ?? []).map((item) => item.value)
                    );
                    const barHeight = Math.max(6, Math.round((row.value / maxValue) * 68));
                    return (
                      <div key={row.month} style={{ textAlign: 'center' }}>
                        <div style={{ height: 74, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                          <div style={{ width: 24, height: barHeight, borderRadius: 6, background: '#22c55e' }} />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>{row.month.slice(5)}</div>
                        <div style={{ fontSize: 11 }}>{fmt(row.value)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Live Sync Control</h3>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
                  Status: {liveSync?.enabled ? 'enabled' : 'paused'} | Lag: {liveSync?.lag_seconds ?? 0}s | Events/24h:{' '}
                  {liveSync?.events_processed_24h ?? 0}
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                  <button style={btn} onClick={() => void runLiveSyncNow()}>
                    Run Sync Now
                  </button>
                  <button style={ghostBtn} onClick={() => void toggleLiveSync(!(liveSync?.enabled ?? true))}>
                    {liveSync?.enabled ? 'Pause Sync' : 'Resume Sync'}
                  </button>
                </div>
                <div style={{ fontSize: 12 }}>
                  Last success: {liveSync?.last_success_at ? fmtTime(liveSync.last_success_at) : 'never'}
                </div>
              </div>

              <div style={card}>
                <h3 style={{ marginTop: 0 }}>AI Backup Orchestration</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
                  <label style={{ fontSize: 12 }}>
                    <span>Incremental (minutes)</span>
                    <input
                      style={inp}
                      type="number"
                      min={5}
                      step={1}
                      value={backupConfigForm.incremental_minutes}
                      onChange={(e) =>
                        setBackupConfigForm((s) => ({ ...s, incremental_minutes: Number(e.target.value) || 5 }))
                      }
                    />
                  </label>
                  <label style={{ fontSize: 12 }}>
                    <span>Full Backup Hour (UTC)</span>
                    <input
                      style={inp}
                      type="number"
                      min={0}
                      max={23}
                      step={1}
                      value={backupConfigForm.full_backup_hour_utc}
                      onChange={(e) =>
                        setBackupConfigForm((s) => ({ ...s, full_backup_hour_utc: Number(e.target.value) || 3 }))
                      }
                    />
                  </label>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
                  <select
                    style={inp}
                    value={backupConfigForm.full_backup_weekday}
                    onChange={(e) => setBackupConfigForm((s) => ({ ...s, full_backup_weekday: e.target.value }))}
                  >
                    {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map((day) => (
                      <option key={day} value={day}>
                        {day}
                      </option>
                    ))}
                  </select>
                  <input
                    style={inp}
                    type="number"
                    min={7}
                    max={365}
                    step={1}
                    value={backupConfigForm.retention_days}
                    onChange={(e) =>
                      setBackupConfigForm((s) => ({ ...s, retention_days: Number(e.target.value) || 30 }))
                    }
                    placeholder="Retention days"
                  />
                </div>
                <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <input
                    type="checkbox"
                    checked={backupConfigForm.enabled}
                    onChange={(e) => setBackupConfigForm((s) => ({ ...s, enabled: e.target.checked }))}
                  />
                  <span>Backup scheduler enabled</span>
                </label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button style={btn} onClick={() => void saveBackupConfig()}>
                    Save Cadence
                  </button>
                  <button style={ghostBtn} onClick={() => void runBackup('incremental')}>
                    Run Incremental Now
                  </button>
                  <button style={ghostBtn} onClick={() => void runBackup('full')}>
                    Run Full Backup
                  </button>
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
                  Next incremental:{' '}
                  {backupOps?.next_runs?.incremental_at ? fmtTime(backupOps.next_runs.incremental_at) : '-'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                  Next full backup: {backupOps?.next_runs?.full_at ? fmtTime(backupOps.next_runs.full_at) : '-'}
                </div>
              </div>

              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Anomaly Radar</h3>
                {(executiveAnalytics?.anomalies ?? []).map((item) => (
                  <div
                    key={`${item.type}-${item.detail}`}
                    style={{ fontSize: 12, borderBottom: '1px solid var(--line)', padding: '4px 0' }}
                  >
                    <strong style={{ color: item.severity === 'high' ? '#ef4444' : '#f59e0b' }}>
                      {item.severity.toUpperCase()}
                    </strong>{' '}
                    {item.detail}
                  </div>
                ))}
                {!executiveAnalytics?.anomalies?.length && (
                  <div style={{ fontSize: 12, color: '#22c55e' }}>No active anomalies detected.</div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* SETTINGS / SLA */}
        {tab === 'settings' && (
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>SLA Rules</h3>
              <input
                style={inp}
                placeholder="SLA Name"
                value={slaForm.name}
                onChange={(e) => setSlaForm((s) => ({ ...s, name: e.target.value }))}
              />
              <select
                style={inp}
                value={slaForm.priority}
                onChange={(e) => setSlaForm((s) => ({ ...s, priority: e.target.value }))}
              >
                {['low', 'medium', 'high', 'critical'].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                type="number"
                placeholder="First Response (hours)"
                value={slaForm.first_response_hours}
                onChange={(e) => setSlaForm((s) => ({ ...s, first_response_hours: e.target.value }))}
              />
              <input
                style={inp}
                type="number"
                placeholder="Resolution (hours)"
                value={slaForm.resolution_hours}
                onChange={(e) => setSlaForm((s) => ({ ...s, resolution_hours: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/sla-rules', 'POST', {
                    name: slaForm.name,
                    priority: slaForm.priority,
                    first_response_hours: Number.parseInt(slaForm.first_response_hours) || 4,
                    resolution_hours: Number.parseInt(slaForm.resolution_hours) || 24,
                  }).then(
                    (ok) =>
                      ok &&
                      setSlaForm({ name: '', priority: 'medium', first_response_hours: '4', resolution_hours: '24' })
                  )
                }
              >
                Add SLA Rule
              </button>
              <div style={{ marginTop: 12 }}>
                {slaRules.map((r) => (
                  <div key={r.id} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0' }}>
                    <div style={{ fontWeight: 700 }}>
                      {r.name} <span style={{ color: PRIORITY_COLOR[r.priority] }}>[{r.priority}]</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Response: {r.first_response_hours}h - Resolution: {r.resolution_hours}h
                    </div>
                  </div>
                ))}
                {!slaRules.length && (
                  <div style={{ color: 'var(--muted)', marginTop: 8 }}>No SLA rules configured.</div>
                )}
              </div>
            </div>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>CRM Webhooks</h3>
              <select
                style={inp}
                value={webhookForm.event}
                onChange={(e) => setWebhookForm((s) => ({ ...s, event: e.target.value }))}
              >
                {[
                  'contact.created',
                  'contact.updated',
                  'deal.created',
                  'deal.updated',
                  'activity.created',
                  'lead.created',
                  'ticket.created',
                  'ticket.updated',
                  'task.completed',
                ].map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
              <input
                style={inp}
                placeholder="Target URL"
                value={webhookForm.target_url}
                onChange={(e) => setWebhookForm((s) => ({ ...s, target_url: e.target.value }))}
              />
              <input
                style={inp}
                placeholder="Secret (optional)"
                value={webhookForm.secret}
                onChange={(e) => setWebhookForm((s) => ({ ...s, secret: e.target.value }))}
              />
              <button
                style={btn}
                onClick={() =>
                  void req('/crm/webhooks', 'POST', webhookForm).then(
                    (ok) => ok && setWebhookForm((s) => ({ ...s, target_url: '', secret: '' }))
                  )
                }
              >
                Register Webhook
              </button>
              <div style={{ marginTop: 12 }}>
                {webhooks.map((w) => (
                  <div
                    key={w.id}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      padding: '6px 0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700 }}>{w.event}</div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{w.target_url}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                        last: {w.last_delivery_status ?? 'none'}
                      </div>
                    </div>
                    <button
                      style={{ ...ghostBtn, fontSize: 11, padding: '3px 7px' }}
                      onClick={() => void req(`/crm/webhooks/${w.id}/test`, 'POST')}
                    >
                      Test
                    </button>
                  </div>
                ))}
                {!webhooks.length && <div style={{ color: 'var(--muted)', marginTop: 8 }}>No webhooks configured.</div>}
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
