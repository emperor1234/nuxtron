import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-workflows-test' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet }));

import WorkflowsPage from './page';

afterEach(() => cleanup());

beforeEach(() => {
  apiGet.mockReset();
});

describe('Workflows page', () => {
  it('shows workspace definitions while disclosing that backend execution is simulated and disabling writes', async () => {
    apiGet.mockResolvedValue({
      status: 'ok',
      total: 1,
      workflows: [{ id: 19, name: 'Lifecycle follow-up', description: 'A configured workflow', trigger: { trigger_type: 'contact_created' }, status: 'active', step_count: 2, enrollment_count: 15, execution_count: 49, updated_at: '2026-10-12T10:00:00Z' }],
    });
    const { container } = render(<WorkflowsPage />);

    expect(await screen.findByText('Lifecycle follow-up')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Execution is not available' })).toBeTruthy();
    expect(screen.getByText(/records simulated “completed” steps/)).toBeTruthy();
    expect(within(screen.getByRole('article')).getByText('Reported enabled')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Create workflow' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Activate' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Enroll contact' })).toBeNull();
    expect(container.textContent).not.toContain('49');
    expect(container.textContent).not.toContain('15');
    expect(apiGet).toHaveBeenCalledWith('/workflows?limit=100', 'workspace-workflows-test');
  });

  it('does not show a false empty state when the first definitions request fails', async () => {
    apiGet.mockRejectedValue(new Error('Workflow service unavailable'));
    render(<WorkflowsPage />);

    expect(await screen.findByText('Workflow service unavailable')).toBeTruthy();
    expect(screen.queryByText('No workflow definitions were returned for this workspace.')).toBeNull();
  });
});
