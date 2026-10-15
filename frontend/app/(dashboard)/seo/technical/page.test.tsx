import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import TechnicalSEOPage from './page';

afterEach(() => cleanup());

describe('Technical SEO page', () => {
  it('discloses the missing crawler and does not show simulated audit metrics or a run action', () => {
    render(<TechnicalSEOPage />);

    expect(screen.getByRole('heading', { name: 'Technical SEO Audit', level: 1 })).toBeTruthy();
    expect(screen.getByText('Unavailable')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'A verified crawler is not connected' })).toBeTruthy();
    expect(screen.getByText(/does not crawl the submitted website or measure its Core Web Vitals/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /run technical audit/i })).toBeNull();
    expect(screen.queryByText('Overall')).toBeNull();
    expect(screen.queryByText('Crawlability')).toBeNull();
  });

  it('links only to the available local security-header review', () => {
    render(<TechnicalSEOPage />);

    expect(screen.getByRole('link', { name: 'Open Security & SEO Health' }).getAttribute('href')).toBe('/seo/security');
    expect(screen.queryByRole('link', { name: /SEO Performance/i })).toBeNull();
  });
});
