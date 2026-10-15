import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import IntegrationsAutomationPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Integrations & Automation page', () => {
  it('discloses that no authorized connector inventory is available', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<IntegrationsAutomationPage />);
    expect(screen.getByRole('heading', { name: 'No verified connector inventory' })).toBeTruthy();
    expect(screen.getByText(/cannot verify which connectors are connected/i)).toBeTruthy();
    expect(screen.getByText(/coverage scores, connector-health results, and generated backlog items are disabled/i)).toBeTruthy();
    expect(screen.queryByRole('form')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});
