import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import RevenueAttributionPage from './page';

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: vi.fn() }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet: vi.fn() }));

function report(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ok',
    tenant_id: 'internal-workspace-id',
    window_days: 30,
    persistence_mode: 'postgres',
    currency_status: 'none',
    currency_codes: [],
    currency_totals: [],
    totals: {
      conversions: 0,
      tracked_conversions: 0,
      currency: null,
      revenue: 0,
      attributed_revenue: 0,
      unattributed_revenue: 0,
    },
    channels: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(resolveSessionTenant).mockReturnValue('workspace-1');
  vi.mocked(apiGet).mockResolvedValue(report());
});

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe('Revenue Attribution page', () => {
  it('shows loading before a true empty state and requests the current workspace without caching', async () => {
    let resolveRequest!: (value: unknown) => void;
    vi.mocked(apiGet).mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
    render(<RevenueAttributionPage />);

    expect(screen.getByRole('status').textContent).toMatch(/loading recorded conversion activity/i);
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith(
      '/analytics/revenue-attribution/report?window_days=30',
      'workspace-1',
      { cache: false }
    ));
    await act(async () => resolveRequest(report()));
    expect(await screen.findByRole('heading', { name: 'No recorded conversion activity' })).toBeTruthy();
    expect(screen.queryByText(/0\.00/)).toBeNull();
    expect(screen.queryByText('internal-workspace-id')).toBeNull();
  });

  it('renders multi-currency totals in separate buckets without a combined monetary figure', async () => {
    vi.mocked(apiGet).mockResolvedValue(report({
      currency_status: 'mixed',
      currency_codes: ['EUR', 'USD'],
      persistence_mode: 'process-memory',
      currency_totals: [
        { currency: 'EUR', currency_supported: true, conversions: 1, tracked_conversions: 1, revenue: 200, attributed_revenue: 200, unattributed_revenue: 0 },
        { currency: 'USD', currency_supported: true, conversions: 1, tracked_conversions: 0, revenue: 100, attributed_revenue: 0, unattributed_revenue: 100 },
      ],
      totals: { conversions: 2, tracked_conversions: 1, currency: null, revenue: null, attributed_revenue: null, unattributed_revenue: null },
      channels: [
        { channel: 'organic_search', currency: 'EUR', currency_supported: true, attributed_revenue: 200 },
      ],
    }));
    render(<RevenueAttributionPage />);

    expect(await screen.findByText('Temporary process-memory data')).toBeTruthy();
    expect(screen.getByText(/may be lost when the service restarts/i)).toBeTruthy();
    expect(screen.getAllByText('200.00 EUR').length).toBeGreaterThan(0);
    expect(screen.getAllByText('100.00 USD').length).toBeGreaterThan(0);
    expect(screen.getByText(/no exchange-rate conversion or cross-currency total is applied/i)).toBeTruthy();
    expect(screen.getByText(/does not establish incremental lift/i)).toBeTruthy();
    expect(screen.queryByText('internal-workspace-id')).toBeNull();
  });

  it('fails closed when workspace context is missing and does not send a report request', async () => {
    vi.mocked(resolveSessionTenant).mockReturnValue('');
    render(<RevenueAttributionPage />);
    expect((await screen.findByRole('alert')).textContent).toMatch(/workspace context is required/i);
    expect(apiGet).not.toHaveBeenCalled();
  });

  it('keeps request failures distinct from an empty report', async () => {
    vi.mocked(apiGet).mockRejectedValue(new Error('private upstream details'));
    render(<RevenueAttributionPage />);
    expect((await screen.findByRole('alert')).textContent).toMatch(/could not load the recorded revenue report/i);
    expect(screen.queryByRole('heading', { name: 'No recorded conversion activity' })).toBeNull();
    expect(screen.queryByText(/private upstream details/i)).toBeNull();
  });
});
