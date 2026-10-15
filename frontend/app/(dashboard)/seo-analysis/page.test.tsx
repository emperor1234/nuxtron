import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiSend, resolveSessionTenant } = vi.hoisted(() => ({
  apiSend: vi.fn(),
  resolveSessionTenant: vi.fn(() => 'workspace-test'),
}));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant }));
vi.mock('@/app/lib/platform-api', () => ({ apiSend }));

import SeoAnalysisPage from './page';

afterEach(() => cleanup());

const response = {
  status: 'ok',
  tenant_id: 'internal-workspace-id',
  score: 90,
  word_count: 400,
  keyword_count: 4,
  keyword_density_percent: 1,
  checks: { has_url: true, keyword_present: true, good_length: true, balanced_density: true },
  recommendations: ['Review the page title against the target keyword.'],
};

beforeEach(() => {
  apiSend.mockReset();
  resolveSessionTenant.mockReturnValue('workspace-test');
});

describe('SEO Content Check page', () => {
  it('explains the rule-based limits and starts with a blank optional-URL brief', () => {
    render(<SeoAnalysisPage />);

    expect(screen.getByRole('heading', { name: 'SEO Content Check' })).toBeTruthy();
    expect(screen.getByText(/not an AI analysis, ranking prediction, or live page audit/i)).toBeTruthy();
    expect((screen.getByLabelText(/Reference page URL/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Target keyword') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Page copy') as HTMLTextAreaElement).value).toBe('');
    expect(apiSend).not.toHaveBeenCalled();
  });

  it('validates required keyword and copy fields without requiring a reference URL', () => {
    render(<SeoAnalysisPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Run content check' }));

    expect(screen.getByText('Enter a target keyword with at least 2 characters.')).toBeTruthy();
    expect(screen.getByText('Paste at least 20 characters of page copy.')).toBeTruthy();
    expect(apiSend).not.toHaveBeenCalled();
  });

  it('submits the real session-scoped payload and renders structured service checks', async () => {
    apiSend.mockResolvedValue(response);
    render(<SeoAnalysisPage />);

    fireEvent.change(screen.getByLabelText('Target keyword'), { target: { value: 'organic search' } });
    fireEvent.change(screen.getByLabelText('Page copy'), { target: { value: 'This is enough page copy for a first-pass check.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run content check' }));

    expect(await screen.findByText('90/100')).toBeTruthy();
    expect(screen.getByText('400')).toBeTruthy();
    expect(screen.getByText('Target keyword appears in the copy')).toBeTruthy();
    expect(screen.getByText('Review the page title against the target keyword.')).toBeTruthy();
    expect(screen.queryByText('internal-workspace-id')).toBeNull();
    expect(apiSend).toHaveBeenCalledWith(
      '/seo/analyze',
      'POST',
      { target_keyword: 'organic search', content: 'This is enough page copy for a first-pass check.' },
      'workspace-test',
    );
  });

  it('keeps the brief after an invalid service response and offers retry rather than false success', async () => {
    apiSend.mockResolvedValue({ status: 'ok', score: 'high' });
    render(<SeoAnalysisPage />);

    fireEvent.change(screen.getByLabelText('Target keyword'), { target: { value: 'organic search' } });
    fireEvent.change(screen.getByLabelText('Page copy'), { target: { value: 'This is enough page copy for a first-pass check.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run content check' }));

    expect(await screen.findByText('The analysis service returned an invalid result. Please retry.')).toBeTruthy();
    expect((screen.getByLabelText('Target keyword') as HTMLInputElement).value).toBe('organic search');
    expect((screen.getByLabelText('Page copy') as HTMLTextAreaElement).value).toBe('This is enough page copy for a first-pass check.');
    expect(screen.getByRole('button', { name: 'Retry content check' })).toBeTruthy();
    expect(screen.queryByText('90/100')).toBeNull();
  });

  it('fails closed when no authenticated workspace is present', () => {
    resolveSessionTenant.mockReturnValue('');
    render(<SeoAnalysisPage />);

    expect(screen.getByText('Sign in to a workspace before running a content check.')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Run content check' }) as HTMLButtonElement).disabled).toBe(true);
    expect(apiSend).not.toHaveBeenCalled();
  });
});
