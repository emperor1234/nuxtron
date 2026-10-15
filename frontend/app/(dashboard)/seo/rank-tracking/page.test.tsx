import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import RankPositionReviewPage from './page';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('Rank Position Review page', () => {
  it('starts blank, discloses no live tracking, and makes no request', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<RankPositionReviewPage />);

    expect(screen.getByRole('heading', { name: 'Rank Position Review' })).toBeTruthy();
    expect((screen.getByLabelText('Paste CSV contents') as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/Manual review only/i)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('reviews supplied positions and only calculates summaries from imported numeric values', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<RankPositionReviewPage />);

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), {
      target: {
        value: 'keyword,position,checked_at,market,url\nseo software,3,2026-10-12,US,https://example.com/seo\nrank report,25,2026-10-12,UK,https://example.com/rank\nnot ranked,,2026-10-12,US,',
      },
    });
    fireEvent.change(screen.getByLabelText('Source label'), { target: { value: 'Imported provider export' } });
    fireEvent.change(screen.getByLabelText('Property / domain'), { target: { value: 'example.com' } });
    fireEvent.change(screen.getByLabelText('Export date'), { target: { value: '2026-10-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported positions' }));

    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByText('seo software')).toBeTruthy();
    expect(screen.getByText('rank report')).toBeTruthy();
    expect(screen.getByText('not ranked')).toBeTruthy();
    expect(screen.getByText('#3')).toBeTruthy();
    expect(screen.getAllByText('Not provided').length).toBeGreaterThan(0);
    expect(screen.getByText(/Source: Imported provider export/)).toBeTruthy();
    expect(screen.getByText(/Not provider-verified/i)).toBeTruthy();
    expect(screen.getByText('2 / 3')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.queryByText(/volatility score|estimated traffic|competitor movement detected/i)).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('distinguishes an empty export from a filtered-empty result and malformed input', () => {
    render(<RankPositionReviewPage />);

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), { target: { value: 'keyword,position' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported positions' }));
    expect(screen.getByText(/No rank rows were found in this export/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), {
      target: { value: 'keyword,position\nseo,4' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported positions' }));
    fireEvent.change(screen.getByLabelText('Filter keywords'), { target: { value: 'missing phrase' } });
    expect(screen.getByText(/No imported rows match this keyword filter/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), {
      target: { value: 'keyword,position\n"broken,2' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported positions' }));
    expect(screen.getByRole('alert').textContent).toMatch(/CSV quoting or row structure is invalid/i);
  });
});
