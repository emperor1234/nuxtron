import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import AccessibilityOptimizerPage from './page';

afterEach(() => cleanup());

describe('Accessibility Audit page', () => {
  it('discloses the missing scanner and suppresses generated compliance metrics and audit controls', () => {
    render(<AccessibilityOptimizerPage />);

    expect(screen.getByRole('heading', { name: 'Accessibility Audit', level: 1 })).toBeTruthy();
    expect(screen.getByText('Unavailable')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'A verified accessibility scanner is not connected' })).toBeTruthy();
    expect(screen.getByText(/does not load the submitted page, inspect its rendered DOM, or run an accessibility rule engine/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /run accessibility audit/i })).toBeNull();
    expect(screen.queryByText('Accessibility Score')).toBeNull();
    expect(screen.queryByText('Screen Reader')).toBeNull();
  });

  it('offers a direct return to the SEO overview', () => {
    render(<AccessibilityOptimizerPage />);

    expect(screen.getByRole('link', { name: 'Return to SEO Overview' }).getAttribute('href')).toBe('/seo');
  });
});
