import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiSend } = vi.hoisted(() => ({ apiSend: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-test' }));
vi.mock('@/app/lib/platform-api', () => ({ apiSend }));

import AdsGenerationPage from './page';

afterEach(() => cleanup());

beforeEach(() => apiSend.mockReset());

function completeBrief() {
  fireEvent.change(screen.getByLabelText('Product or offer'), { target: { value: 'Analytics platform' } });
  fireEvent.change(screen.getByLabelText('Target audience'), { target: { value: 'Small business marketers' } });
  fireEvent.change(screen.getByLabelText('Advertising platform'), { target: { value: 'linkedin' } });
  fireEvent.change(screen.getByLabelText('Campaign objective'), { target: { value: 'leads' } });
}

describe('AI Ads Generation page', () => {
  it('starts with a blank brief and disables generation until all required inputs are provided', () => {
    render(<AdsGenerationPage />);

    expect((screen.getByLabelText('Product or offer') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Target audience') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Advertising platform') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Campaign objective') as HTMLSelectElement).value).toBe('');
    expect((screen.getByRole('button', { name: 'Generate ad copy' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('sends a session-workspace-scoped brief and renders only the provider-generated text', async () => {
    apiSend.mockResolvedValue({
      status: 'ok',
      platform: 'linkedin',
      objective: 'leads',
      ai_status: 'generated',
      provider_used: 'openai',
      model_used: 'model-x',
      outputs: { text: 'An authentic provider-generated campaign draft.' },
      headlines: ['A deterministic backend template that is not the AI output.'],
      descriptions: ['Another deterministic backend template.'],
    });
    render(<AdsGenerationPage />);
    completeBrief();
    fireEvent.click(screen.getByRole('button', { name: 'Generate ad copy' }));

    expect(await screen.findByText('An authentic provider-generated campaign draft.')).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith(
      '/ads/generate',
      'POST',
      { product: 'Analytics platform', audience: 'Small business marketers', platform: 'linkedin', objective: 'leads' },
      'workspace-test'
    );
    expect(screen.queryByText('A deterministic backend template that is not the AI output.')).toBeNull();
    expect(screen.getByText('openai · model-x')).toBeTruthy();
  });

  it('hides deterministic fallback text and explains that no AI copy was returned', async () => {
    apiSend.mockResolvedValue({
      status: 'ok',
      platform: 'linkedin',
      objective: 'leads',
      ai_status: 'fallback',
      provider_used: 'unconfigured',
      model_used: '',
      outputs: { text: 'Template fallback must not be shown.' },
    });
    render(<AdsGenerationPage />);
    completeBrief();
    fireEvent.click(screen.getByRole('button', { name: 'Generate ad copy' }));

    expect(await screen.findByText(/template fallback is hidden/i)).toBeTruthy();
    expect(screen.queryByText('Template fallback must not be shown.')).toBeNull();
    expect(screen.queryByText('Generated ad copy')).toBeNull();
  });

  it('announces an incomplete service response and preserves the entered brief for retry', async () => {
    apiSend.mockResolvedValue({ status: 'ok', outputs: {} });
    render(<AdsGenerationPage />);
    completeBrief();
    fireEvent.click(screen.getByRole('button', { name: 'Generate ad copy' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText('The ad-generation service returned an incomplete response. Please retry.')).toBeTruthy();
    expect((screen.getByLabelText('Product or offer') as HTMLInputElement).value).toBe('Analytics platform');
    await waitFor(() => expect((screen.getByRole('button', { name: 'Generate ad copy' }) as HTMLButtonElement).disabled).toBe(false));
  });
});
