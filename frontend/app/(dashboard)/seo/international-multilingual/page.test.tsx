import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import InternationalMultilingualPage from './page';

const MARKUP = [
  '<link rel="alternate" hreflang="en-US" href="https://example.com/en/">',
  '<link rel="alternate" hreflang="fr-FR" href="https://example.com/fr/">',
].join('\n');

describe('Hreflang & Locale Review page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('starts blank and does not advertise full-site crawling or a readiness score', () => {
    render(<InternationalMultilingualPage />);

    expect(screen.getByRole('heading', { name: 'Hreflang & Locale Review' })).toBeTruthy();
    expect((screen.getByLabelText('Hreflang link markup') as HTMLTextAreaElement).value).toBe('');
    expect((screen.getByLabelText('Expected locales (optional)') as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/does not fetch URLs/i)).toBeTruthy();
    expect(screen.queryByText(/readiness score|coverage score|estimated traffic/i)).toBeNull();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('checks only pasted tags and user-entered locale expectations without a network call', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(<InternationalMultilingualPage />);

    fireEvent.change(screen.getByLabelText('Current page locale (optional)'), { target: { value: 'en-us' } });
    fireEvent.change(screen.getByLabelText('Expected locales (optional)'), { target: { value: 'en-US, fr-FR' } });
    fireEvent.change(screen.getByLabelText('Hreflang link markup'), { target: { value: MARKUP } });
    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));

    expect(screen.getByRole('heading', { name: 'Results for supplied markup' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/2 alternate links found/i);
    expect(screen.getByText('en-US')).toBeTruthy();
    expect(screen.getByText('fr-FR')).toBeTruthy();
    expect(screen.queryByRole('link')).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('separates missing expected locales and duplicate alternates from valid links', () => {
    render(<InternationalMultilingualPage />);

    fireEvent.change(screen.getByLabelText('Expected locales (optional)'), { target: { value: 'en, fr' } });
    fireEvent.change(screen.getByLabelText('Hreflang link markup'), {
      target: {
        value: [
          '<link rel="alternate" hreflang="en" href="https://example.com/en/">',
          '<link rel="alternate" hreflang="en" href="https://example.com/english/">',
        ].join('\n'),
      },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));

    expect(screen.getByText(/More than one alternate is declared for en/i)).toBeTruthy();
    expect(screen.getByText(/No supplied alternate matches fr/i)).toBeTruthy();
    expect(screen.getAllByText('Duplicate locale')).toHaveLength(2);
  });

  it('requires user-provided markup and gives an accessible error without inventing empty results', () => {
    render(<InternationalMultilingualPage />);

    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));

    expect(screen.getByRole('alert').textContent).toMatch(/paste the alternate link markup/i);
    expect(screen.queryByRole('heading', { name: 'Results for supplied markup' })).toBeNull();
  });

  it('clears prior findings when the source markup changes', () => {
    render(<InternationalMultilingualPage />);

    const markupField = screen.getByLabelText('Hreflang link markup');
    fireEvent.change(markupField, { target: { value: MARKUP } });
    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));
    expect(screen.getByRole('heading', { name: 'Results for supplied markup' })).toBeTruthy();

    fireEvent.change(markupField, { target: { value: '' } });
    expect(screen.queryByRole('heading', { name: 'Results for supplied markup' })).toBeNull();
    expect(screen.getByText('Nothing reviewed yet')).toBeTruthy();
  });
});
