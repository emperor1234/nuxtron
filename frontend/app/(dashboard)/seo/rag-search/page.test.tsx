import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CorpusSearchPreviewPage from './page';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('Corpus Search Preview', () => {
  it('searches only pasted text locally and shows exact source passages', () => {
    render(<CorpusSearchPreviewPage />);
    expect(screen.getByRole('heading', { name: 'Corpus Search Preview' })).toBeTruthy();
    expect(screen.getByText(/not sent to the Nuxtron search API or saved/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Search phrase'), { target: { value: 'keyword research' } });
    fireEvent.change(screen.getByLabelText('Source label (optional)'), { target: { value: 'Editorial guide' } });
    fireEvent.change(screen.getByLabelText('Source URL (optional)'), { target: { value: 'https://content.example.org/guide' } });
    fireEvent.change(screen.getByLabelText('Pasted content'), {
      target: { value: 'Keyword research helps teams understand intent.\n\nUnrelated passage.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Preview matches' }));

    expect(screen.getByRole('heading', { name: 'Matching passages' })).toBeTruthy();
    expect(screen.getByText('Keyword research helps teams understand intent.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open supplied source' }).getAttribute('href')).toBe('https://content.example.org/guide');
    expect(screen.getByText(/2 of 2 query terms matched/i)).toBeTruthy();
    expect(screen.queryByText(/(?:confidence|relevance score)\s*[:=]?\s*\d+(?:\.\d+)?\s*%?/i)).toBeNull();
  });

  it('shows a real no-match state and never constructs results from a domain alone', () => {
    render(<CorpusSearchPreviewPage />);
    fireEvent.change(screen.getByLabelText('Search phrase'), { target: { value: 'missing concept' } });
    fireEvent.change(screen.getByLabelText('Pasted content'), { target: { value: 'Only customer-supplied content appears here.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview matches' }));

    expect(screen.getByRole('status').textContent).toMatch(/no matching passages were found/i);
    expect(screen.getByText(/try another phrase or add text/i)).toBeTruthy();
    expect(screen.queryByText(/example\.com/i)).toBeNull();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('requires supplied text and does not make a network request', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<CorpusSearchPreviewPage />);
    fireEvent.change(screen.getByLabelText('Search phrase'), { target: { value: 'keyword' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview matches' }));

    expect(screen.getByRole('alert').textContent).toMatch(/paste text into at least one source/i);
    expect(document.body.textContent).not.toContain('RAG Site Search Engine');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('omits an unsafe source URL as a clickable link', () => {
    render(<CorpusSearchPreviewPage />);
    fireEvent.change(screen.getByLabelText('Search phrase'), { target: { value: 'source phrase' } });
    fireEvent.change(screen.getByLabelText('Source URL (optional)'), { target: { value: 'javascript:alert(1)' } });
    fireEvent.change(screen.getByLabelText('Pasted content'), { target: { value: 'A source phrase in supplied text.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview matches' }));

    expect(screen.queryByRole('link', { name: 'Open supplied source' })).toBeNull();
    expect(screen.getByText(/no safe HTTP\(S\) source link supplied/i)).toBeTruthy();
  });
});
