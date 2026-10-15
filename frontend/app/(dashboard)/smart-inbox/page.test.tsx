import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend } = vi.hoisted(() => ({ apiGet: vi.fn(), apiSend: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-test' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import SmartInboxPage from './page';

afterEach(() => cleanup());

function successfulInbox() {
  apiGet.mockImplementation((path: string) => Promise.resolve(
    path === '/inbox/stats'
      ? { status: 'ok', total: 1, unread: 1 }
      : { status: 'ok', messages: [{ id: 17, network: 'instagram', source_type: 'comment', author_handle: 'customer_17', text: 'Please help with my order', message_type: 'support', sentiment: 'negative', priority_score: 82, status: 'pending', read: false }] },
  ));
}

describe('Customer Inbox page', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiSend.mockReset();
  });

  it('shows live workspace messages and starts manual intake with blank values', async () => {
    successfulInbox();
    render(<SmartInboxPage />);
    expect(await screen.findByText('customer_17')).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith('/inbox/stats', 'workspace-test');
    expect(apiGet).toHaveBeenCalledWith('/inbox/messages?limit=200', 'workspace-test');

    fireEvent.click(screen.getByRole('button', { name: 'Add existing message' }));
    expect((screen.getByLabelText('Channel') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Message source') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Author handle') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Message text') as HTMLTextAreaElement).value).toBe('');
    expect(screen.queryByText('@prospect')).toBeNull();
  });

  it('does not present a failed first load as an empty inbox', async () => {
    apiGet.mockRejectedValue(new Error('Inbox service unavailable'));
    render(<SmartInboxPage />);
    expect(await screen.findByText('Inbox service unavailable')).toBeTruthy();
    expect(screen.queryByText('No messages have been received for this workspace.')).toBeNull();
    expect(screen.getByRole('button', { name: 'Retry inbox load' })).toBeTruthy();
  });

  it('updates one message only after the live API accepts the status change', async () => {
    successfulInbox();
    apiSend.mockResolvedValue({ status: 'ok' });
    render(<SmartInboxPage />);
    const status = await screen.findByRole('combobox', { name: 'Update status for customer_17' });
    fireEvent.change(status, { target: { value: 'complete' } });
    await waitFor(() => expect(apiSend).toHaveBeenCalledWith('/inbox/messages/17', 'PATCH', { status: 'complete' }, 'workspace-test'));
    expect(await screen.findByText('Status updated for customer_17.')).toBeTruthy();
  });
});
