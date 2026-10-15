import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ get: vi.fn(), send: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({
  apiGet: api.get,
  resolveSessionTenant: () => 'workspace_test_42',
}));

vi.mock('@/app/lib/platform-api', () => ({
  apiSend: api.send,
}));

import BillingPage from './page';

function liveResponse(path: string) {
  if (path === '/billing/plans') return { plans: [
    { id: 'starter', display: 'Starter', price_monthly: 0, price_annual: 0, ai_credits: 100 },
    { id: 'pro', display: 'Pro', price_monthly: 79, price_annual: 63.2, ai_credits: 5000 },
  ] };
  if (path === '/billing/usage') return { current_plan: 'starter', plan_display: 'Starter', credit_balance: 0, pending_credit_topups: 0 };
  if (path === '/billing/invoices') return { invoices: [] };
  if (path === '/money-printers/nuxtron-bank/wallet') return { wallet: { available_balance_usd: 0, recent_transactions: [] } };
  throw new Error(`Unexpected API path: ${path}`);
}

describe('BillingPage', () => {
  beforeEach(() => {
    api.get.mockReset();
    api.send.mockReset();
    api.get.mockImplementation((path: string) => Promise.resolve(liveResponse(path)));
  });

  afterEach(cleanup);

  it('requires a deliberate plan choice before opening subscription checkout', async () => {
    render(<BillingPage />);
    const subscribe = await screen.findByRole('button', { name: 'Continue to secure checkout' }) as HTMLButtonElement;

    expect(subscribe.disabled).toBe(true);
    const plan = screen.getByRole('combobox', { name: 'Plan' }) as HTMLSelectElement;
    expect(plan.value).toBe('');
    fireEvent.change(screen.getByRole('combobox', { name: 'Plan' }), { target: { value: 'pro' } });
    await waitFor(() => expect(subscribe.disabled).toBe(false));
    expect(document.querySelector('.billing-price-review')?.textContent).toContain('Selected plan: Pro');
  });

  it('requires a fresh quote matching the entered credit amount before checkout', async () => {
    api.send.mockResolvedValue({ quote: { credits: 500, total_usd: 10, unit_price_usd: 0.02 } });
    render(<BillingPage />);

    const amount = await screen.findByLabelText('Credit amount') as HTMLInputElement;
    const buy = screen.getByRole('button', { name: 'Review a quote to continue' }) as HTMLButtonElement;
    expect(buy.disabled).toBe(true);

    fireEvent.change(amount, { target: { value: '500' } });
    fireEvent.click(screen.getByRole('button', { name: 'Get credit quote' }));
    await waitFor(() => expect((screen.getByRole('button', { name: 'Continue · $10.00' }) as HTMLButtonElement).disabled).toBe(false));
    expect(api.send).toHaveBeenCalledWith('/billing/credits/quote', 'POST', { amount: 500 }, 'workspace_test_42');

    fireEvent.change(amount, { target: { value: '600' } });
    expect((screen.getByRole('button', { name: 'Review a quote to continue' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows actual zero balances and a distinct empty invoice state', async () => {
    render(<BillingPage />);

    expect(await screen.findByText('No invoices are available for this account yet.')).toBeTruthy();
    expect(screen.getByText('Live data · plan and subscription')).toBeTruthy();
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
  });
});
