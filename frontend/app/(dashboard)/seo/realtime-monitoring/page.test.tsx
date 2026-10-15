import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SearchObservationLogPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function enterObservation(query: string, time: string, rank: string, aiStatus: string) {
  fireEvent.change(screen.getByLabelText(/^Search query/i), { target: { value: query } });
  fireEvent.change(screen.getByLabelText(/^Search source/i), { target: { value: 'Google' } });
  fireEvent.change(screen.getByLabelText(/^Observed at/i), { target: { value: time } });
  fireEvent.change(screen.getByLabelText(/^Rank position/i), { target: { value: rank } });
  fireEvent.change(screen.getByLabelText(/^AI answer observation/i), { target: { value: aiStatus } });
  fireEvent.click(screen.getByRole('button', { name: 'Record observation' }));
}

describe('Search Observation Log page', () => {
  it('starts blank and explains manual, session-only scope', () => {
    render(<SearchObservationLogPage />);
    expect((screen.getByLabelText(/^Search query/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Observed at/i) as HTMLInputElement).value).toBe('');
    expect(screen.getByText(/This is not live monitoring/i)).toBeTruthy();
    expect(screen.getByText(/not saved to your workspace/i)).toBeTruthy();
    expect(screen.getByText(/No observations yet/i)).toBeTruthy();
  });

  it('derives a source-specific trend only from two user-entered rank observations without network calls', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<SearchObservationLogPage />);
    enterObservation('workflow software', '2026-10-12T10:00', '10', 'none-observed');
    enterObservation('workflow software', '2026-10-13T10:00', '6', 'google-ai-overview');

    expect(screen.getByLabelText('Observations logged').textContent).toBe('2');
    expect(screen.getByText('Improved 4 positions')).toBeTruthy();
    expect(screen.getByText('Google AI Overview observed', { selector: 'span' })).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('keeps a single record trend unavailable and distinguishes a filtered-empty history', () => {
    render(<SearchObservationLogPage />);
    enterObservation('billing software', '2026-10-12T10:00', '', 'not-checked');
    expect(screen.getByText(/Trend unavailable/i)).toBeTruthy();
    expect(screen.getByText('Not checked', { selector: 'span' })).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/Filter by query or source/i), { target: { value: 'unmatched' } });
    expect(screen.getByText(/No observations match this filter/i)).toBeTruthy();
  });
});
