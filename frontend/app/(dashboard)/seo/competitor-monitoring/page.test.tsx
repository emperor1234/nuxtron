import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CompetitorActivityMonitorPage from './page';

describe('Competitor Activity Monitor page', () => {
  it('states the monitoring prerequisites without branded sample events or fake controls', () => {
    const { container } = render(<CompetitorActivityMonitorPage />);
    const text = container.textContent ?? '';

    expect(screen.getByRole('heading', { name: 'Competitor Activity Monitor' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/does not yet have durable monitor storage/i);
    expect(screen.getByRole('list').textContent).toMatch(/scheduled collection/i);
    expect(screen.getByRole('link', { name: 'Competitive Benchmarking' })).toBeTruthy();
    expect(container.querySelector('form, input, textarea, button')).toBeNull();
    expect(text).not.toMatch(/EyeOn|SEMrush|competitor1\.com|10 SEO Strategies|estimated_budget|\b\d+%/i);
  });
});
