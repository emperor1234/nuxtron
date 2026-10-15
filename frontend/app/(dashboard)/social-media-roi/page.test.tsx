import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend, resolveSessionTenant } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiSend: vi.fn(),
  resolveSessionTenant: vi.fn(() => 'workspace-test'),
}));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import SocialMediaRoiPage from './page';

afterEach(() => {
  cleanup();
  window.history.replaceState({}, '', '/');
});

const noCurrencySummary = {
  status: 'ok',
  tenant_id: 'workspace-test',
  window_days: 90,
  persistence_mode: 'postgres',
  currency_status: 'none',
  currency_codes: [],
  invalid_currency_records: 0,
  totals: {
    revenue: null, spend: null, net_profit: null, roas: null, roi_pct: null,
    conversions: 0, tracked_conversions: 0, touchpoints: 0, spend_entries: 0, tracking_coverage_pct: 0,
  },
  channels: [],
  campaigns: [],
};
const emptySpendHistory = { status: 'ok', persistence_mode: 'postgres', count: 0, items: [] };

function singleCurrencySummary(persistenceMode = 'postgres') {
  return {
    status: 'ok', tenant_id: 'workspace-test', window_days: 90,
    persistence_mode: persistenceMode, currency_status: 'single', currency_codes: ['USD'], invalid_currency_records: 0,
    totals: {
      revenue: 0, spend: 0, net_profit: 0, roas: null, roi_pct: null,
      conversions: 0, tracked_conversions: 0, touchpoints: 0, spend_entries: 0, tracking_coverage_pct: 0,
    },
    channels: [], campaigns: [],
  };
}

function installEmptyData() {
  apiGet.mockImplementation((path: string) => Promise.resolve(
    path.startsWith('/analytics/social-roi/summary') ? noCurrencySummary : emptySpendHistory,
  ));
}

beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
  resolveSessionTenant.mockReturnValue('workspace-test');
  installEmptyData();
});

describe('Social Media ROI page', () => {
  it('distinguishes the first summary load from a confirmed period with no currency-coded records', async () => {
    let resolveSummary!: (value: unknown) => void;
    apiGet.mockImplementation((path: string) => path.startsWith('/analytics/social-roi/summary')
      ? new Promise((resolve) => { resolveSummary = resolve; })
      : Promise.resolve(emptySpendHistory),
    );
    render(<SocialMediaRoiPage />);

    expect(await screen.findByText('Loading ROI summary…')).toBeTruthy();
    expect(screen.queryByText(/No currency-coded conversions or spend entries/i)).toBeNull();
    resolveSummary(noCurrencySummary);
    expect(await screen.findByText(/No currency-coded conversions or spend entries/i)).toBeTruthy();
  });

  it('starts with blank shared campaign fields and explicit blank currency choices', async () => {
    render(<SocialMediaRoiPage />);
    expect(await screen.findByText(/No currency-coded conversions or spend entries/i)).toBeTruthy();

    expect((screen.getByLabelText('Campaign name') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Social channel') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Spend currency') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Scenario currency') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Post ID or internal reference') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Destination URL') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Attributed revenue') as HTMLInputElement).value).toBe('');
    expect(apiGet).toHaveBeenCalledWith('/analytics/social-roi/summary?window_days=90', 'workspace-test');
    expect(apiGet).toHaveBeenCalledWith('/analytics/social-roi/spend?limit=20&offset=0', 'workspace-test');
  });

  it('uses one shared campaign context, validates receipts, and never renders an untrusted tracked URL as a link', async () => {
    const trackedUrl = 'https://example.com/pricing?utm_source=linkedin&nux_touchpoint=tp_abcdefghijk';
    apiSend.mockImplementation((path: string) => Promise.resolve(path.includes('touchpoints')
      ? { status: 'ok', persistence_mode: 'process-memory', touchpoint: { tracked_url: trackedUrl } }
      : { status: 'ok', persistence_mode: 'process-memory', spend: { id: 5, channel: 'linkedin', campaign: 'Launch', currency: 'USD', amount: 12.5, spent_at: '2026-10-12T12:00:00Z' } },
    ));
    render(<SocialMediaRoiPage />);
    await screen.findByText(/No currency-coded conversions or spend entries/i);

    fireEvent.change(screen.getByLabelText('Campaign name'), { target: { value: 'Launch' } });
    fireEvent.change(screen.getByLabelText('Social channel'), { target: { value: 'LinkedIn' } });
    fireEvent.change(screen.getByLabelText('Post ID or internal reference'), { target: { value: 'post-4' } });
    fireEvent.change(screen.getByLabelText('Destination URL'), { target: { value: 'https://example.com/pricing' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create tracked URL' }));

    expect(await screen.findByText(/Tracked URL created in temporary process memory/i)).toBeTruthy();
    const displayedUrl = screen.getByText(trackedUrl);
    expect(displayedUrl.tagName.toLowerCase()).toBe('code');
    expect(displayedUrl.closest('a')).toBeNull();
    expect(apiSend).toHaveBeenCalledWith('/analytics/revenue-attribution/touchpoints', 'POST', {
      post_id: 'post-4', platform: 'linkedin', campaign: 'Launch', destination_url: 'https://example.com/pricing',
    }, 'workspace-test');

    fireEvent.change(screen.getByLabelText('Spend amount'), { target: { value: '12.50' } });
    fireEvent.change(screen.getByLabelText('Spend currency'), { target: { value: 'USD' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record spend' }));
    expect(await screen.findByText(/Spend entry recorded in temporary process memory/i)).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/analytics/social-roi/spend', 'POST', {
      channel: 'linkedin', campaign: 'Launch', amount: 12.5, currency: 'USD',
    }, 'workspace-test');
  });

  it('associates destination URL policy errors with the field and blocks the write', async () => {
    render(<SocialMediaRoiPage />);
    await screen.findByText(/No currency-coded conversions or spend entries/i);
    fireEvent.change(screen.getByLabelText('Campaign name'), { target: { value: 'Launch' } });
    fireEvent.change(screen.getByLabelText('Social channel'), { target: { value: 'LinkedIn' } });
    fireEvent.change(screen.getByLabelText('Post ID or internal reference'), { target: { value: 'post-4' } });
    fireEvent.change(screen.getByLabelText('Destination URL'), { target: { value: 'https://user:secret@example.com/path' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create tracked URL' }));

    const destination = screen.getByLabelText('Destination URL');
    expect(destination.getAttribute('aria-invalid')).toBe('true');
    const errorId = destination.getAttribute('aria-describedby')?.split(' ').find((id) => id.endsWith('-error'));
    expect(errorId).toBeTruthy();
    expect(document.getElementById(errorId ?? '')?.textContent).toMatch(/embedded credentials/i);
    expect(apiSend).not.toHaveBeenCalled();
  });

  it('warns when the backend reports process-memory storage', async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(
      path.startsWith('/analytics/social-roi/summary') ? singleCurrencySummary('process-memory') : { ...emptySpendHistory, persistence_mode: 'process-memory' },
    ));
    render(<SocialMediaRoiPage />);

    expect(await screen.findByText(/Temporary storage is active/i)).toBeTruthy();
    expect(screen.getByText(/may be lost when the service restarts/i)).toBeTruthy();
    expect(screen.getAllByText('$0.00').length).toBe(3);
    expect(screen.getAllByText('Requires recorded spend').length).toBe(2);
  });

  it('withholds combined money metrics and comparisons for mixed currencies', async () => {
    const mixed = {
      status: 'ok', tenant_id: 'workspace-test', window_days: 90, persistence_mode: 'postgres',
      currency_status: 'mixed', currency_codes: ['EUR', 'USD'], invalid_currency_records: 0,
      totals: {
        revenue: null, spend: null, net_profit: null, roas: null, roi_pct: null,
        conversions: 2, tracked_conversions: 1, touchpoints: 2, spend_entries: 1, tracking_coverage_pct: 50,
      },
      channels: [{ channel: 'linkedin', revenue: null, spend: null, net_profit: null, roas: null, roi_pct: null }],
      campaigns: [{ campaign: 'Launch', revenue: null, spend: null, net_profit: null, roas: null, roi_pct: null }],
    };
    apiGet.mockImplementation((path: string) => Promise.resolve(path.startsWith('/analytics/social-roi/summary') ? mixed : emptySpendHistory));
    render(<SocialMediaRoiPage />);

    expect(await screen.findByText(/Mixed currencies are not normalized/i)).toBeTruthy();
    expect(screen.getByText(/Reported currencies: EUR, USD/i)).toBeTruthy();
    expect(screen.queryByRole('table', { name: /Campaign performance/i })).toBeNull();
    expect(screen.queryByRole('table', { name: /Channel performance/i })).toBeNull();
  });

  it('calculates a blank-start what-if scenario using explicit zero inputs and selected currency', async () => {
    apiSend.mockResolvedValue({ status: 'ok', totals: { revenue: 100, spend: 0, net_profit: 100, roas: null, roi_pct: null } });
    render(<SocialMediaRoiPage />);
    await screen.findByText(/No currency-coded conversions or spend entries/i);

    fireEvent.change(screen.getByLabelText('Scenario currency'), { target: { value: 'EUR' } });
    for (const label of ['Attributed revenue', 'Paid social spend', 'Team cost', 'Tools cost', 'Agency cost']) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: label === 'Attributed revenue' ? '100' : '0' } });
    }
    fireEvent.click(screen.getByRole('button', { name: 'Calculate scenario' }));

    expect(await screen.findByText(/Scenario result · EUR/i)).toBeTruthy();
    expect(screen.getByText('ROAS', { selector: 'dt' })).toBeTruthy();
    expect(screen.getByText(/ROAS and ROI are undefined with zero total cost/i)).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/analytics/social-roi/calculator', 'POST', {
      attributed_revenue: 100, paid_social_spend: 0, team_cost: 0, tools_cost: 0, agency_cost: 0,
    }, 'workspace-test');
  });

  it('shows failed summary reads as errors rather than zero or an empty period', async () => {
    apiGet.mockImplementation((path: string) => path.startsWith('/analytics/social-roi/summary')
      ? Promise.reject(new Error('ROI service unavailable'))
      : Promise.resolve(emptySpendHistory),
    );
    render(<SocialMediaRoiPage />);

    expect(await screen.findByText('ROI service unavailable')).toBeTruthy();
    expect(screen.queryByText(/No currency-coded conversions or spend entries/i)).toBeNull();
  });

  it('fails closed if no workspace session can be resolved', async () => {
    resolveSessionTenant.mockReturnValue('');
    render(<SocialMediaRoiPage />);

    expect(screen.getByText('Sign in to a workspace before using Social Media ROI.')).toBeTruthy();
    await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 5)); });
    expect(apiGet).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Create tracked URL' }) as HTMLButtonElement).disabled).toBe(true);
  });
});
