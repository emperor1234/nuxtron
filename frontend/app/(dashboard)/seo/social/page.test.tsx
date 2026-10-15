import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SocialSharePreviewPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Social Share Preview page', () => {
  it('starts with no sample metadata or channel preselected', () => {
    render(<SocialSharePreviewPage />);
    expect((screen.getByLabelText(/^Open Graph title/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Canonical URL/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('X (Twitter)') as HTMLInputElement).checked).toBe(false);
    expect(screen.getByText(/No page is fetched/i)).toBeTruthy();
  });

  it('shows per-selected-channel local previews and explicit canonical mismatch without a request', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<SocialSharePreviewPage />);
    fireEvent.change(screen.getByLabelText(/^Open Graph title/i), { target: { value: 'Product overview' } });
    fireEvent.change(screen.getByLabelText(/^Open Graph description/i), { target: { value: 'Product details for prospective customers.' } });
    fireEvent.change(screen.getByLabelText(/^Canonical URL/i), { target: { value: 'https://example.com/products' } });
    fireEvent.change(screen.getByLabelText(/^Open Graph URL/i), { target: { value: 'https://example.com/other' } });
    fireEvent.change(screen.getByLabelText(/^Open Graph image URL/i), { target: { value: 'https://example.com/share.png' } });
    fireEvent.click(screen.getByLabelText('LinkedIn'));
    fireEvent.click(screen.getByLabelText('X (Twitter)'));
    fireEvent.change(screen.getByLabelText(/^X \(Twitter\) card type/i), { target: { value: 'summary_large_image' } });
    fireEvent.click(screen.getByRole('button', { name: 'Build local preview' }));

    expect(screen.getByRole('region', { name: 'Social share previews' })).toBeTruthy();
    expect(screen.getByText('Open Graph URL differs from the supplied canonical URL; review both values.')).toBeTruthy();
    expect(screen.getAllByText('Product overview').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Image URL reference.*not fetched/i).length).toBeGreaterThan(0);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('requires at least one selected channel and announces a useful validation message', () => {
    render(<SocialSharePreviewPage />);
    fireEvent.change(screen.getByLabelText(/^Open Graph title/i), { target: { value: 'Title' } });
    fireEvent.change(screen.getByLabelText(/^Open Graph description/i), { target: { value: 'Description' } });
    fireEvent.change(screen.getByLabelText(/^Canonical URL/i), { target: { value: 'https://example.com/page' } });
    fireEvent.click(screen.getByRole('button', { name: 'Build local preview' }));
    expect(screen.getByRole('alert').textContent).toMatch(/select at least one channel/i);
  });
});
