import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, resolveSessionTenant } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  resolveSessionTenant: vi.fn(() => 'workspace-test'),
}));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet }));

import PlaybooksPage from './page';

afterEach(() => cleanup());

const playbook = {
  id: 'pb-builtin-001',
  name: 'Welcome Sequence',
  vertical: 'all',
  description: 'A customer onboarding plan template.',
  steps: ['Send a welcome email', 'Review engagement'],
  integrations: ['email', 'crm'],
  roi_target: { metric: 'activation_rate_pct', value: 35 },
  time_to_value_days: 1,
  built_in: true,
};

beforeEach(() => {
  apiGet.mockReset();
  resolveSessionTenant.mockReturnValue('workspace-test');
  apiGet.mockImplementation((path: string) => Promise.resolve(
    path === '/playbooks'
      ? { total: 1, playbooks: [playbook] }
      : { total: 0, runs: [] },
  ));
});

describe('Playbooks page', () => {
  it('loads workspace definitions, presents review as informational, and exposes no activation action', async () => {
    render(<PlaybooksPage />);

    expect(await screen.findByRole('heading', { name: 'Welcome Sequence' })).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith('/playbooks', 'workspace-test');
    expect(apiGet).toHaveBeenCalledWith('/playbooks/runs/list', 'workspace-test');
    expect(screen.queryByText('workspace-test')).toBeNull();
    expect(screen.queryByText(/35/)).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Review plan' }));
    expect(screen.getByText('Send a welcome email')).toBeTruthy();
    expect(screen.getByText('This plan has not been validated against connected services and cannot be activated yet.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /activate/i })).toBeNull();
    expect(screen.getByText('No playbook run records are available for this workspace.')).toBeTruthy();
  });

  it('distinguishes a valid empty catalog from an old scheduled request that did not execute', async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(
      path === '/playbooks'
        ? { total: 0, playbooks: [] }
        : { total: 1, runs: [{ id: 'run-1', playbook_id: 'pb-builtin-001', playbook_name: 'Welcome Sequence', dry_run: false, status: 'scheduled', steps_total: 5, steps_completed: 0, created_at: '2026-10-12T10:00:00Z' }] },
    ));
    render(<PlaybooksPage />);

    expect(await screen.findByText('No playbook definitions are available for this workspace.')).toBeTruthy();
    expect(screen.getByText('Scheduled — not executed')).toBeTruthy();
    expect(screen.getByText('Activation request')).toBeTruthy();
  });

  it('keeps catalog and run-history failures independent', async () => {
    apiGet.mockImplementation((path: string) => path === '/playbooks'
      ? Promise.resolve({ total: 0, playbooks: [] })
      : Promise.reject(new Error('Run history unavailable')),
    );
    render(<PlaybooksPage />);

    expect(await screen.findByText('No playbook definitions are available for this workspace.')).toBeTruthy();
    expect(await screen.findByText('Run history unavailable')).toBeTruthy();
    expect(screen.queryByText('No playbook run records are available for this workspace.')).toBeNull();
  });

  it('fails closed without a session workspace', async () => {
    resolveSessionTenant.mockReturnValue('');
    render(<PlaybooksPage />);

    expect(await screen.findByText('Sign in to a workspace to load playbook definitions.')).toBeTruthy();
    expect(apiGet).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Refresh' }) as HTMLButtonElement).disabled).toBe(true);
  });
});
