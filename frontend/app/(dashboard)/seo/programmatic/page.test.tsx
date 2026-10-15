import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ProgrammaticPage from './page';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function fillValidDraft() {
  fireEvent.change(screen.getByLabelText('Relative URL path template'), {
    target: { value: '/areas/[city]/[service]' },
  });
  fireEvent.change(screen.getByLabelText('Page-title template'), {
    target: { value: '[service] in [city]' },
  });
  fireEvent.change(screen.getByLabelText('Meta-description template'), {
    target: { value: 'Explore [service] options in [city].' },
  });
  fireEvent.change(screen.getByLabelText('Token name 1'), { target: { value: 'city' } });
  fireEvent.change(screen.getByLabelText('Values for variable 1 (one per line)'), {
    target: { value: 'Austin\nBoston' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Add variable' }));
  fireEvent.change(screen.getByLabelText('Token name 2'), { target: { value: 'service' } });
  fireEvent.change(screen.getByLabelText('Values for variable 2 (one per line)'), {
    target: { value: 'Plumbing\nElectrical' },
  });
}

describe('Programmatic SEO Draft Preview page', () => {
  it('starts blank and discloses browser-only draft scope without example businesses', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<ProgrammaticPage />);

    expect(screen.getByRole('heading', { name: 'Programmatic SEO Draft Preview' })).toBeTruthy();
    expect((screen.getByLabelText('Relative URL path template') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Page-title template') as HTMLInputElement).value).toBe('');
    expect(screen.queryByText(/New York|OmniSEO|plumbers|electricians/i)).toBeNull();
    expect(screen.getByText(/Nothing leaves this page/i)).toBeTruthy();
    expect(screen.queryByText(/estimated traffic|cannibalization risk|template score/i)).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('expands only supplied values in-browser and requires explicit review before export', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<ProgrammaticPage />);
    fillValidDraft();

    fireEvent.click(screen.getByRole('button', { name: 'Preview variants' }));
    expect(screen.getByText('4 draft variants expanded locally from your matrix.')).toBeTruthy();
    expect(screen.getByText('/areas/austin/plumbing')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Export reviewed CSV' }) as HTMLButtonElement).disabled).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByLabelText(/I reviewed the complete draft set/i));
    expect((screen.getByRole('button', { name: 'Export reviewed CSV' }) as HTMLButtonElement).disabled).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows only a small sample first and requires opening the full set before review', () => {
    render(<ProgrammaticPage />);
    fireEvent.change(screen.getByLabelText('Relative URL path template'), { target: { value: '/[city]/[service]' } });
    fireEvent.change(screen.getByLabelText('Page-title template'), { target: { value: '[service] in [city]' } });
    fireEvent.change(screen.getByLabelText('Meta-description template'), { target: { value: 'Details for [service] in [city].' } });
    fireEvent.change(screen.getByLabelText('Token name 1'), { target: { value: 'city' } });
    fireEvent.change(screen.getByLabelText('Values for variable 1 (one per line)'), { target: { value: 'A\nB' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add variable' }));
    fireEvent.change(screen.getByLabelText('Token name 2'), { target: { value: 'service' } });
    fireEvent.change(screen.getByLabelText('Values for variable 2 (one per line)'), { target: { value: 'one\ntwo\nthree' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview variants' }));

    expect(screen.getByText(/Showing the first 5 of 6/i)).toBeTruthy();
    expect((screen.getByRole('checkbox') as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Show all 6 variants for review' }));
    expect(screen.getByText('All 6 local draft variants')).toBeTruthy();
    expect((screen.getByRole('checkbox') as HTMLInputElement).disabled).toBe(false);
  });

  it('blocks a matrix above the 100-variant cap with an announced validation error', () => {
    render(<ProgrammaticPage />);
    fireEvent.change(screen.getByLabelText('Relative URL path template'), { target: { value: '/[city]' } });
    fireEvent.change(screen.getByLabelText('Page-title template'), { target: { value: 'A guide to [city]' } });
    fireEvent.change(screen.getByLabelText('Meta-description template'), { target: { value: 'Read about [city].' } });
    fireEvent.change(screen.getByLabelText('Token name 1'), { target: { value: 'city' } });
    fireEvent.change(screen.getByLabelText('Values for variable 1 (one per line)'), {
      target: { value: Array.from({ length: 101 }, (_, index) => `City ${index}`).join('\n') },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Preview variants' }));

    expect(screen.getByRole('alert').textContent).toMatch(/more than 100 variants/i);
    expect(screen.queryByRole('heading', { name: 'Draft variants' })).toBeNull();
  });
});
