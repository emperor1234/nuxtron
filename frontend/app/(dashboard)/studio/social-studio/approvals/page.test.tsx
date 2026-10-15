import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend } = vi.hoisted(() => ({ apiGet: vi.fn(), apiSend: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'tenant-a' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import ApprovalsPage from './page';

afterEach(() => cleanup());

const pendingRequest = {
  id: 7,
  status: 'pending',
  scheduled_post_id: 3,
  platform: 'linkedin',
  content_preview: 'Quarterly launch post',
  requested_by: 'Ada',
  approval_levels: ['editor', 'legal'],
  approvals_received: [],
};

function mockLoad({
  requests = [] as unknown[],
  queue = [] as unknown[],
  config = null as unknown,
} = {}) {
  apiGet.mockImplementation((path: string) => {
    if (path === '/content/approval/requests') return Promise.resolve({ requests });
    if (path.startsWith('/social/queue')) return Promise.resolve({ queue });
    if (path === '/content/approval/config') return Promise.resolve({ config });
    return Promise.reject(new Error(`unexpected ${path}`));
  });
}

describe('Content approvals page', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiSend.mockReset();
  });

  it('reports an empty list only after a successful load and offers no sample posts', async () => {
    mockLoad();
    render(<ApprovalsPage />);
    expect(await screen.findByText('No approval requests yet')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Request approval' }));
    expect(screen.getByText(/No draft or scheduled posts are waiting for review/)).toBeTruthy();
    expect(screen.queryByText(/company\.com/)).toBeNull();
  });

  it('shows a load failure instead of an empty state', async () => {
    apiGet.mockRejectedValue(new Error('Service unavailable'));
    render(<ApprovalsPage />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/Service unavailable/)).toBeTruthy();
    expect(screen.queryByText('No approval requests yet')).toBeNull();
  });

  it('submits a real queued post to the shared approval contract', async () => {
    mockLoad({ queue: [{ id: 3, caption: 'Launch day thread', platform: 'x', status: 'scheduled' }] });
    apiSend.mockResolvedValue({ request: pendingRequest });
    render(<ApprovalsPage />);
    await screen.findByText('No approval requests yet');

    fireEvent.click(screen.getByRole('button', { name: 'Request approval' }));
    fireEvent.change(screen.getByLabelText('Post'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('Requested by'), { target: { value: 'Ada' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send for approval' }));

    await waitFor(() => expect(apiSend).toHaveBeenCalled());
    expect(apiSend).toHaveBeenCalledWith(
      '/content/approval/requests',
      'POST',
      { scheduled_post_id: 3, platform: 'x', content_preview: 'Launch day thread', requested_by: 'Ada' },
      'tenant-a'
    );
  });

  it('keeps a multi-level request pending when the server says other levels are outstanding', async () => {
    mockLoad({ requests: [pendingRequest] });
    apiSend.mockResolvedValue({
      request: { ...pendingRequest, approvals_received: ['editor'], status: 'pending' },
    });
    render(<ApprovalsPage />);
    await screen.findByText('Quarterly launch post');

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

    await waitFor(() => expect(screen.getByText(/Signed off: editor/)).toBeTruthy());
    expect(apiSend).toHaveBeenCalledWith(
      '/content/approval/requests/7/decision',
      'POST',
      { decision: 'approved', reviewer_role: 'editor', comment: null },
      'tenant-a'
    );
    expect(screen.getByText('Pending (1)')).toBeTruthy();
    expect(screen.queryByText(/Approved \(/)).toBeNull();
  });

  it('requires a reason before rejecting', async () => {
    mockLoad({ requests: [pendingRequest] });
    render(<ApprovalsPage />);
    await screen.findByText('Quarterly launch post');

    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    expect(await screen.findByText(/Add a reason/)).toBeTruthy();
    expect(apiSend).not.toHaveBeenCalled();
  });
});
