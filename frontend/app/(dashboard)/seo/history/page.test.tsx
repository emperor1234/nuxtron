import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiGet } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';
import SEOHistoryPage from './page';

vi.mock('@/app/lib/platform-api', () => ({ apiGet: vi.fn() }));
vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(resolveSessionTenant).mockReturnValue('workspace-test');
});

const emptyHistory = { analyses: [], total: 0, persistence: 'postgres' as const };
const historyWithRecord = {
  analyses: [{
    id: 'analysis-12345678',
    tenant_id: 'tenant-secret-not-for-display',
    module: 'seo_content_check',
    created_at: '2026-10-13T10:00:00Z',
    payload: { domain: 'example.com', api_key: 'do-not-show' },
    result: { summary: 'Archived result', email: 'private@example.com', score: 42 },
  }],
  total: 1,
  persistence: 'memory' as const,
};

describe('SEO Analysis History page', () => {
  it('shows loading before a valid empty response and then a genuine empty state', async () => {
    let resolveResponse!: (value: typeof emptyHistory) => void;
    vi.mocked(apiGet).mockReturnValueOnce(new Promise((resolve) => { resolveResponse = resolve; }));
    render(<SEOHistoryPage />);
    expect(screen.getByText(/loading saved analyses/i)).toBeTruthy();
    expect(screen.queryByText(/no saved seo analyses yet/i)).toBeNull();
    await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(1));
    await act(async () => { resolveResponse(emptyHistory); });
    expect(await screen.findByText(/no saved seo analyses yet/i)).toBeTruthy();
  });

  it('discloses temporary persistence, omits tenant IDs, redacts sensitive detail, and refreshes uncached', async () => {
    vi.mocked(apiGet).mockResolvedValue(historyWithRecord);
    render(<SEOHistoryPage />);
    await screen.findByRole('button', { name: /seo content check/i });
    expect(screen.getByText(/held in process memory/i)).toBeTruthy();
    expect(document.body.textContent).not.toContain('tenant-secret-not-for-display');
    fireEvent.click(screen.getByText(/show redacted input and output json/i));
    expect(document.body.textContent).not.toContain('do-not-show');
    expect(document.body.textContent).not.toContain('private@example.com');
    expect(document.body.textContent).toContain('[redacted]');

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2));
    expect(apiGet).toHaveBeenLastCalledWith('/seo-platform/analyses?limit=100', 'workspace-test', { cache: false });
  });

  it('keeps a failed request distinct from a successful empty history', async () => {
    vi.mocked(apiGet).mockRejectedValue(new Error('Service unavailable'));
    render(<SEOHistoryPage />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.queryByText(/no saved seo analyses yet/i)).toBeNull();
    expect(screen.getByText(/no history is available because the request failed/i)).toBeTruthy();
  });

  it('filters by module with a server-scoped query', async () => {
    vi.mocked(apiGet).mockResolvedValue(historyWithRecord);
    render(<SEOHistoryPage />);
    await screen.findByRole('button', { name: /seo content check/i });
    fireEvent.change(screen.getByLabelText('Module'), { target: { value: 'seo_content_check' } });
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith(
      '/seo-platform/analyses?module=seo_content_check&limit=100', 'workspace-test', { cache: false },
    ));
  });
});


describe('SEO Analysis History workspace access', () => {
  it('fails closed without a workspace and does not call the history API', async () => {
    vi.mocked(resolveSessionTenant).mockReturnValue('');
    render(<SEOHistoryPage />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/a signed-in workspace is required/i)).toBeTruthy();
    expect(apiGet).not.toHaveBeenCalled();
  });
});
