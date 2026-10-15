import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SecurityHeaderReviewPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Security Header Review page', () => {
  it('starts blank and reviews supplied text locally without fetching the optional source label', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<SecurityHeaderReviewPage />);
    expect((screen.getByLabelText(/^Response header block/i) as HTMLTextAreaElement).value).toBe('');
    expect((screen.getByLabelText(/^Response source label/i) as HTMLInputElement).value).toBe('');
    expect(screen.getByText(/no network request is made/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/^Response source label/i), { target: { value: 'https://customer.example' } });
    fireEvent.change(screen.getByLabelText(/^Response header block/i), { target: { value: 'Content-Security-Policy: default-src \'self\'' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review pasted headers' }));

    expect(screen.getByRole('region', { name: 'Security header review results' })).toBeTruthy();
    expect(screen.getByLabelText('Header lines parsed').textContent).toBe('1');
    expect(screen.getByText('Present in sample')).toBeTruthy();
    expect(screen.getByText(/HTTPS enforcement.*are not assessed/i)).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
  });
});
