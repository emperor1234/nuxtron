import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CompetitorPage from './page';

describe('SEO Competitor Research page', () => {
  it('requires verifiable evidence and does not generate sample competitor metrics', () => {
    const { container } = render(<CompetitorPage />);
    const text = container.textContent ?? '';

    expect(screen.getByRole('heading', { name: 'SEO Competitor Research' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/no authorized SERP or competitor-data source/i);
    expect(screen.getByRole('list').textContent).toMatch(/collection date/i);
    expect(screen.getByRole('link', { name: 'Competitive Benchmarking' })).toBeTruthy();
    expect(container.querySelector('form, input, textarea, button')).toBeNull();
    expect(text).not.toMatch(/competitor1\.com|competitor2\.com|\b\d{2,}(?:\.\d+)?%?\b/i);
  });
});
