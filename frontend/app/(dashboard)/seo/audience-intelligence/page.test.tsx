import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AudienceIntelligencePage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Audience Intelligence page', () => {
  it('discloses unavailable provider data instead of rendering domain-derived profiles', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<AudienceIntelligencePage />);
    expect(screen.getByText(/verified audience data yet/i)).toBeTruthy();
    expect(screen.getByText(/synthetic audience distributions .* disabled/i)).toBeTruthy();
    expect(screen.getByText(/demographics and interests: not available/i)).toBeTruthy();
    expect(screen.queryByRole('tablist')).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not link to an unrelated integrations analysis page as if it connected a provider', () => {
    render(<AudienceIntelligencePage />);
    expect(screen.getByText(/provider setup is not available in this dashboard yet/i)).toBeTruthy();
    expect(screen.queryByRole('link')).toBeNull();
  });
});
