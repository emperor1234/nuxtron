import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ContentAuditorPage from './page';

afterEach(() => cleanup());

describe('Content Review page', () => {
  it('discloses the missing evidence pipeline and does not show generated scores or audit actions', () => {
    render(<ContentAuditorPage />);

    expect(screen.getByRole('heading', { name: 'Content Review', level: 1 })).toBeTruthy();
    expect(screen.getByText('Unavailable')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Claim-level evidence is not available' })).toBeTruthy();
    expect(screen.getByText(/does not fetch the submitted URL or retrieve primary sources/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /audit content/i })).toBeNull();
    expect(screen.queryByText('Hallucination Risk')).toBeNull();
    expect(screen.queryByText('Citation Coverage')).toBeNull();
  });

  it('links to content drafting and the SEO overview without implying either performs fact checking', () => {
    render(<ContentAuditorPage />);

    expect(screen.getByRole('link', { name: 'Open Content Generator' }).getAttribute('href')).toBe('/content-generation');
    expect(screen.getByRole('link', { name: 'Return to SEO Overview' }).getAttribute('href')).toBe('/seo');
  });
});
