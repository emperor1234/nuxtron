import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-test' }));

import CRMPage from './page';

const fetchMock = vi.fn();
let failSummary = false;
let failAnalyticsSources = false;
const summary = {
  contacts: 0,
  companies: 0,
  deals_total: 0,
  deals_open: 0,
  deals_won: 0,
  pipeline_value: 0,
  closed_won_value: 0,
  forecast_revenue: 0,
  avg_lead_score: 0,
  activities: 0,
  stage_counts: {},
};

const responses: Record<string, unknown> = {
  '/crm/summary': { summary },
  '/crm/contacts': { contacts: [] },
  '/crm/companies': { companies: [] },
  '/crm/deals': { deals: [] },
  '/crm/activities': { activities: [] },
  '/crm/pipeline': { pipeline: [] },
  '/crm/leads': { leads: [] },
  '/crm/tasks': { tasks: [] },
  '/crm/tickets': { tickets: [] },
  '/crm/campaigns': { campaigns: [] },
  '/crm/segments': { segments: [] },
  '/crm/notes': { notes: [] },
  '/crm/quotes': { quotes: [] },
  '/crm/invoices': { invoices: [] },
  '/crm/email-sequences': { sequences: [] },
  '/crm/reports/kpis': {
    kpis: {
      total_contacts: 0,
      total_leads: 0,
      lead_conversion_rate_pct: 0,
      total_deals: 0,
      win_rate_pct: 0,
      avg_deal_value: 0,
      closed_won_value: 0,
      open_tickets: 0,
      escalated_tickets: 0,
      open_tasks: 0,
      overdue_tasks: 0,
    },
    window_days: 30,
  },
  '/crm/reports/forecast': {
    weighted_pipeline: 0,
    closed_won_total: 0,
    outstanding_invoices: 0,
    paid_invoices: 0,
    monthly_forecast: {},
  },
  '/crm/reports/executive-analytics': { charts: { lead_source_breakdown: {} } },
  '/crm/projects': { projects: [] },
};

function response(body: unknown, ok = true) {
  return { ok, json: async () => body } as Response;
}

function endpoint(input: RequestInfo | URL) {
  return new URL(String(input), 'http://localhost').pathname.replace('/api/fastapi', '');
}

afterEach(() => {
  cleanup();
  window.history.replaceState({}, '', '/');
  vi.unstubAllGlobals();
});

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const path = endpoint(input);
    if (path === '/crm/summary' && failSummary) {
      return response({ detail: 'Summary service unavailable' }, false);
    }
    if (failAnalyticsSources && ['/crm/leads', '/crm/tasks', '/crm/tickets'].includes(path)) {
      return response({ detail: 'Analytics source unavailable' }, false);
    }
    const matchedPath = Object.keys(responses).find((candidate) => path.startsWith(candidate));
    return response(matchedPath ? responses[matchedPath] : {}, true);
  });
  failSummary = false;
  failAnalyticsSources = false;
});

describe('CRM page', () => {
  it('loads one customer data batch and distinguishes valid zeroes from a true empty pipeline/activity state', async () => {
    render(<CRMPage />);

    expect(await screen.findByText('No pipeline stages are recorded for this workspace.')).toBeTruthy();
    expect(screen.getByText('No activities are recorded for this workspace.')).toBeTruthy();
    expect(screen.getByRole('group', { name: 'Contacts: 0' })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(19);
    expect(fetchMock.mock.calls.map(([input]) => endpoint(input))).not.toContain('/crm/api-tokens');
    expect(fetchMock.mock.calls.map(([input]) => endpoint(input))).not.toContain('/crm/ops/backup');
  });

  it('does not turn a missing overview response into a zero contact count', async () => {
    failSummary = true;
    render(<CRMPage />);

    expect(await screen.findByRole('group', { name: 'Contacts: —' })).toBeTruthy();
    expect(screen.getByText(/temporarily unavailable: Overview/)).toBeTruthy();
    expect(screen.queryByRole('group', { name: 'Contacts: 0' })).toBeNull();
  });

  it('keeps empty-list copy hidden while the first customer data batch is still loading', async () => {
    let releaseSummary: ((value: Response) => void) | undefined;
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const path = endpoint(input);
      if (path === '/crm/summary') {
        return new Promise<Response>((resolve) => {
          releaseSummary = resolve;
        });
      }
      const matchedPath = Object.keys(responses).find((candidate) => path.startsWith(candidate));
      return response(matchedPath ? responses[matchedPath] : {}, true);
    });
    render(<CRMPage />);

    expect(screen.getByText('Loading CRM workspace data…')).toBeTruthy();
    expect(screen.queryByText('No activities are recorded for this workspace.')).toBeNull();
    expect(releaseSummary).toBeDefined();

    await act(async () => releaseSummary?.(response(responses['/crm/summary'])));
    expect(await screen.findByText('No activities are recorded for this workspace.')).toBeTruthy();
  });

  it('restores the selected section from the URL and persists subsequent navigation', async () => {
    window.history.replaceState({}, '', '/crm?tab=tickets');
    render(<CRMPage />);

    expect(await screen.findByText('New Support Ticket')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Support' }).getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(screen.getByRole('button', { name: 'Commercial' }));
    expect(window.location.search).toBe('?tab=quotes');
    expect(screen.getByRole('group', { name: 'Commercial CRM pages' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Quotes' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('reloads report data for the selected reporting window', async () => {
    render(<CRMPage />);
    expect(await screen.findByText('No pipeline stages are recorded for this workspace.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Work' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reports' }));

    fireEvent.change(screen.getByLabelText('CRM reporting period'), { target: { value: '7d' } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(38));
    const requests = fetchMock.mock.calls.map(([input]) => String(input));
    expect(requests.filter((url) => url.includes('/crm/reports/kpis')).at(-1)).toContain('days=7');
  });

  it('blocks analytics export when each underlying analytics source failed', async () => {
    failAnalyticsSources = true;
    render(<CRMPage />);
    expect(await screen.findByText(/Some CRM sections are temporarily unavailable/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Work' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reports' }));
    fireEvent.click(screen.getByRole('button', { name: 'Export analytics CSV' }));

    expect(await screen.findByText('Analytics data is unavailable. Refresh CRM before exporting.')).toBeTruthy();
  });
});
