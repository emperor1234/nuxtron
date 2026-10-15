import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend, resolveSessionTenant } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiSend: vi.fn(),
  resolveSessionTenant: vi.fn(() => 'workspace-test'),
}));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import CompetitiveBenchmarkingPage from './page';

afterEach(() => cleanup());

const profile = { id: 7, name: 'Northwind', network: 'linkedin', handle: 'northwind', snapshot_count: 0 };
const emptyReport = { status: 'ok', own_brand: null, competitors: [] };
const emptyShare = { status: 'ok', total_estimated_mentions: 0, breakdown: [] };

function installEmptyData() {
  apiGet.mockImplementation((path: string) => Promise.resolve(
    path === '/competitive/profiles'
      ? { status: 'ok', count: 0, profiles: [] }
      : path === '/competitive/report'
        ? emptyReport
        : emptyShare,
  ));
}

beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
  resolveSessionTenant.mockReturnValue('workspace-test');
  installEmptyData();
});

describe('Competitive Benchmarking page', () => {
  it('uses blank forms, shows a true empty state, and removes unsupported scraping claims', async () => {
    render(<CompetitiveBenchmarkingPage />);

    expect(await screen.findByText('No competitor profiles have been added to this workspace.')).toBeTruthy();
    expect((screen.getByLabelText('Competitor or brand name') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Competitor social network') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Profile handle') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Competitor followers (count)') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Your brand followers (count)') as HTMLInputElement).value).toBe('');
    expect(screen.queryByText('Competitor A')).toBeNull();
    expect(screen.queryByRole('button', { name: /scraper/i })).toBeNull();
    expect(screen.getByText(/Automated social scraping is not available/i)).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith('/competitive/profiles', 'workspace-test');
  });

  it('records explicit zero values as real user-entered observations, not blank defaults', async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(
      path === '/competitive/profiles'
        ? { status: 'ok', count: 1, profiles: [profile] }
        : path === '/competitive/report'
          ? { status: 'ok', own_brand: null, competitors: [{ profile, latest_snapshot: null }] }
          : emptyShare,
    ));
    apiSend.mockResolvedValue({ status: 'ok', snapshot: {} });
    render(<CompetitiveBenchmarkingPage />);

    await screen.findByRole('option', { name: 'Northwind · linkedin' });
    fireEvent.change(await screen.findByLabelText('Competitor profile'), { target: { value: '7' } });
    fireEvent.change(screen.getByLabelText('Competitor followers (count)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Competitor engagement rate (%)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Competitor estimated mentions (count)'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record competitor observation' }));

    expect(await screen.findByText('Manual competitor observation recorded.')).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith(
      '/competitive/profiles/7/snapshots',
      'POST',
      { followers: 0, engagement_rate: 0, estimated_mentions: 0 },
      'workspace-test',
    );
  });

  it('adds a blank-start competitor profile through the current session workspace', async () => {
    const storedProfiles: typeof profile[] = [];
    apiGet.mockImplementation((path: string) => Promise.resolve(
      path === '/competitive/profiles'
        ? { status: 'ok', count: storedProfiles.length, profiles: storedProfiles }
        : path === '/competitive/report'
          ? { status: 'ok', own_brand: null, competitors: storedProfiles.map((item) => ({ profile: item, latest_snapshot: null })) }
          : emptyShare,
    ));
    apiSend.mockImplementation(async (path: string, method: string, payload: { name: string; network: string; handle: string }, workspace: string) => {
      if (path === '/competitive/profiles' && method === 'POST' && workspace === 'workspace-test') {
        const createdProfile = { ...profile, id: 11, name: payload.name, network: payload.network, handle: payload.handle };
        storedProfiles.push(createdProfile);
        return { status: 'ok', created: true, profile: createdProfile };
      }
      return { status: 'error' };
    });
    render(<CompetitiveBenchmarkingPage />);

    fireEvent.change(screen.getByLabelText('Competitor or brand name'), { target: { value: 'Northwind' } });
    fireEvent.change(screen.getByLabelText('Competitor social network'), { target: { value: 'linkedin' } });
    fireEvent.change(screen.getByLabelText('Profile handle'), { target: { value: '@northwind' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add competitor profile' }));

    expect(await screen.findByText('Competitor profile added.')).toBeTruthy();
    expect(screen.getAllByText('Northwind').length).toBeGreaterThan(0);
    expect(apiSend).toHaveBeenCalledWith('/competitive/profiles', 'POST', { name: 'Northwind', network: 'linkedin', handle: 'northwind' }, 'workspace-test');
  });

  it('does not show an empty state when the profile service fails', async () => {
    apiGet.mockImplementation((path: string) => path === '/competitive/profiles'
      ? Promise.reject(new Error('Profile service unavailable'))
      : Promise.resolve(path === '/competitive/report' ? emptyReport : emptyShare),
    );
    render(<CompetitiveBenchmarkingPage />);

    expect(await screen.findByText('Profile service unavailable')).toBeTruthy();
    expect(screen.queryByText('No competitor profiles have been added to this workspace.')).toBeNull();
  });

  it('fails closed when no workspace is available', async () => {
    resolveSessionTenant.mockReturnValue('');
    render(<CompetitiveBenchmarkingPage />);

    expect(await screen.findByText('Sign in to a workspace to load competitor profiles.')).toBeTruthy();
    expect(apiGet).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Add competitor profile' }) as HTMLButtonElement).disabled).toBe(true);
  });
});
