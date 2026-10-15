import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MediaMarkupReviewPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => vi.clearAllMocks());

describe('Media Markup Review page', () => {
  it('starts blank and makes clear that the supplied sample stays local', () => {
    render(<MediaMarkupReviewPage />);
    expect((screen.getByLabelText(/^Page URL or source label/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^HTML markup sample/i) as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/nothing is sent to Nuxtron and no website or asset is fetched/i)).toBeTruthy();
    expect(screen.queryByText(/SEO Score|Average Size|Optimisable/i)).toBeNull();
  });

  it('reviews only pasted attributes, shows asset-level findings, and makes no network request', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<MediaMarkupReviewPage />);
    fireEvent.change(screen.getByLabelText(/^Page URL or source label/i), { target: { value: 'https://customer.example/page' } });
    fireEvent.change(screen.getByLabelText(/^HTML markup sample/i), {
      target: { value: '<img src="/hero.webp"><video src="/demo.mp4" title="Demo"><track kind="captions" src="/captions.vtt"></video>' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));

    expect(screen.getByRole('region', { name: 'Media markup review results' })).toBeTruthy();
    expect(screen.getByLabelText('Images in supplied markup').textContent).toBe('1');
    expect(screen.getByLabelText('Videos in supplied markup').textContent).toBe('1');
    expect(screen.getByLabelText('Images missing alt').textContent).toBe('1');
    expect(screen.getByLabelText('Videos without captions').textContent).toBe('0');
    expect(screen.getByText(/Alt attribute is missing from the supplied markup/i)).toBeTruthy();
    expect(screen.getByText(/Video sitemap and transcript coverage: not assessed/i)).toBeTruthy();
    expect(screen.queryByText(/Media SEO Score|Images Detected|Avg Size/i)).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('distinguishes a valid sample with no media elements from blank input', () => {
    render(<MediaMarkupReviewPage />);
    fireEvent.change(screen.getByLabelText(/^HTML markup sample/i), { target: { value: '<main><p>Text only.</p></main>' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review supplied markup' }));

    expect(screen.getByLabelText('Images in supplied markup').textContent).toBe('0');
    expect(screen.getByLabelText('Videos in supplied markup').textContent).toBe('0');
    expect(screen.getByText(/No image or video elements were found in this supplied markup sample/i)).toBeTruthy();
  });
});
