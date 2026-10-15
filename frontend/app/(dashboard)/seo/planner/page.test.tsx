import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';
import SEOPlannerPage from './page';

vi.mock('@/app/lib/platform-api', () => ({ apiSend: vi.fn() }));
vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(resolveSessionTenant).mockReturnValue('workspace-test');
});

const draftResponse = {
  status: 'draft',
  goal: 'Increase qualified organic visits',
  domain: 'example.com',
  primary_keyword: 'workflow software',
  market: 'us',
  created_at: '2026-10-13T10:00:00Z',
  analysis_mode: 'heuristic',
  ai_available: false,
  planner_score: 99,
  tenant_id: 'never-render-this-tenant-id',
  workflow: [{
    phase: 'Validate search evidence',
    module: 'Keyword Data Review',
    action: 'Review a keyword export you provide.',
    path: '/seo/keywords',
  }],
  priorities: ['Check search intent'],
  risks: ['Current traffic data was not checked'],
  next_actions: ['Assign an owner'],
};

function submitGoal() {
  fireEvent.change(screen.getByLabelText(/goal/i), { target: { value: 'Increase qualified organic visits' } });
  fireEvent.click(screen.getByRole('button', { name: /create draft plan/i }));
}

describe('SEO Workflow Planner', () => {
  it('fails closed without an authenticated workspace and sends no request', async () => {
    vi.mocked(resolveSessionTenant).mockReturnValue('');
    render(<SEOPlannerPage />);
    submitGoal();

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/signed-in workspace is required/i)).toBeTruthy();
    expect(apiSend).not.toHaveBeenCalled();
  });

  it('creates an uncached, session-scoped review-only draft without scores or tenant IDs', async () => {
    vi.mocked(apiSend).mockResolvedValue(draftResponse);
    render(<SEOPlannerPage />);
    submitGoal();

    expect(await screen.findByRole('region', { name: 'Draft plan' })).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith(
      '/seo-platform/planner/draft',
      'POST',
      {
        goal: 'Increase qualified organic visits',
        domain: '',
        primary_keyword: '',
        market: '',
      },
      'workspace-test',
      { cache: false },
    );
    expect(screen.getByText('Template suggestions')).toBeTruthy();
    expect(screen.getByText(/no AI model or connected site data was used/i)).toBeTruthy();
    expect(screen.getByText(/nothing is executed from this page/i)).toBeTruthy();
    expect(screen.getByText(/created drafts are saved to this workspace/i)).toBeTruthy();
    expect(screen.getByRole('link', { name: /open analysis history/i }).getAttribute('href')).toBe('/seo/history');
    expect(screen.queryByText(/all modules orchestration/i)).toBeNull();
    expect(screen.queryByText(/planner score/i)).toBeNull();
    expect(document.body.textContent).not.toContain('never-render-this-tenant-id');
  });

  it('shows an explicit AI-only-from-brief label and does not leak server error details', async () => {
    vi.mocked(apiSend).mockRejectedValue(new Error('private provider trace')); 
    render(<SEOPlannerPage />);
    submitGoal();

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/did not trigger any SEO work/i)).toBeTruthy();
    expect(document.body.textContent).not.toContain('private provider trace');
  });

  it('does not expose controls for unsupported all-modules orchestration', () => {
    render(<SEOPlannerPage />);
    expect(screen.queryByText(/all modules orchestration/i)).toBeNull();
    expect(screen.queryByRole('checkbox')).toBeNull();
  });
});
