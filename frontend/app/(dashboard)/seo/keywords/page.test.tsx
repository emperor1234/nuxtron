import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import KeywordsPage from './page';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('Keyword Data Review page', () => {
  it('starts blank, distinguishes unavailable provider discovery, and makes no request', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<KeywordsPage />);

    expect(screen.getByRole('heading', { name: 'Keyword Data Review' })).toBeTruthy();
    expect((screen.getByLabelText('Paste CSV contents') as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/No connected keyword data source/i)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('reviews only the values in pasted CSV and keeps provenance in the browser', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<KeywordsPage />);

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), {
      target: { value: 'keyword,search volume,difficulty,intent\ncrm software,1200,46,commercial\n"crm, enterprise",200,19,transactional' },
    });
    fireEvent.change(screen.getByLabelText('Source label'), { target: { value: 'Imported export' } });
    fireEvent.change(screen.getByLabelText('Market / location'), { target: { value: 'US' } });
    fireEvent.change(screen.getByLabelText('Export date'), { target: { value: '2026-10-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported data' }));

    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByText('crm software')).toBeTruthy();
    expect(screen.getByText('crm, enterprise')).toBeTruthy();
    expect(screen.getByText('1,200')).toBeTruthy();
    expect(screen.getByText('46')).toBeTruthy();
    expect(screen.getByText(/Source: Imported export/)).toBeTruthy();
    expect(screen.getByText(/Not provider-verified/i)).toBeTruthy();
    expect(screen.queryByText(/quick wins|clusters found|estimated traffic/i)).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps true empty exports separate from malformed CSV and filtered-empty results', () => {
    render(<KeywordsPage />);

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), { target: { value: 'keyword,volume,intent' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported data' }));
    expect(screen.getByText(/No keyword rows were found in this export/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), {
      target: { value: 'keyword,volume,intent\ncrm,100,commercial\nseo,0,informational' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported data' }));
    fireEvent.change(screen.getByLabelText('Filter keywords'), { target: { value: 'missing phrase' } });
    expect(screen.getByText(/No keyword rows match the current filters/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Paste CSV contents'), { target: { value: 'keyword,volume\n"broken,10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review imported data' }));
    expect(screen.getByRole('alert').textContent).toMatch(/CSV quoting or row structure is invalid/i);
  });
});
