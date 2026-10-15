import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({
  apiGet: api.get,
  resolveSessionTenant: () => 'workspace_test_42',
}));

vi.mock('next/navigation', () => ({ usePathname: () => '/account/orders' }));

import AccountOrdersPage from './page';

describe('AccountOrdersPage', () => {
  beforeEach(() => api.get.mockReset());
  afterEach(cleanup);

  it('shows table context and safely renders invalid dates without exposing workspace IDs', async () => {
    api.get.mockResolvedValue({
      orders: [{ id: 'A-17', created_at: 'not-a-date', product_name: 'Pro plan', total_usd: 79, order_status: 'paid' }],
    });
    render(<AccountOrdersPage />);

    expect(await screen.findByText('ORD-A-17')).toBeTruthy();
    expect(screen.getByText('Date unavailable')).toBeTruthy();
    expect(screen.getByText('Up to 50 recent purchase records')).toBeTruthy();
    expect(screen.queryByText('workspace_test_42')).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Account sections' })).toBeTruthy();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/money-printers/commerce-pro/orders', 'workspace_test_42'));
  });

  it('distinguishes a successful empty response from loading', async () => {
    api.get.mockResolvedValue({ orders: [] });
    render(<AccountOrdersPage />);

    expect(await screen.findByText('No orders yet')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Review plans and billing' })).toBeTruthy();
  });
});
