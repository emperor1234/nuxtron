import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TrafficAnalyticsPage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Traffic Analytics page', () => {
  it('starts with blank source, period, and metric inputs and explains its local scope', () => {
    render(<TrafficAnalyticsPage />);
    expect((screen.getByLabelText('Data source') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Clicks — comparison period') as HTMLInputElement).value).toBe('');
    expect(screen.getByText(/not connected to an analytics provider/i)).toBeTruthy();
  });

  it('shows recorded zero separately from unsupplied KPIs and makes no network request', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<TrafficAnalyticsPage />);
    fireEvent.change(screen.getByLabelText('Data source'), { target: { value: 'Search export' } });
    fireEvent.change(screen.getByLabelText('Comparison period label'), { target: { value: 'August' } });
    fireEvent.change(screen.getByLabelText('Current period label'), { target: { value: 'September' } });
    fireEvent.change(screen.getByLabelText('Clicks — comparison period'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Clicks — current period'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Compare supplied values' }));

    const result = screen.getByRole('region', { name: 'Manual SEO comparison result' });
    expect(result.textContent).toContain('0 → 0');
    expect(result.textContent).toContain('Both periods are zero; percentage change is undefined.');
    expect(result.textContent).toContain('Not supplied');
    expect(result.textContent).not.toMatch(/score|recommendation|caused by/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('reports incomplete metric pairs without converting them into zeroes', () => {
    render(<TrafficAnalyticsPage />);
    fireEvent.change(screen.getByLabelText('Data source'), { target: { value: 'Export' } });
    fireEvent.change(screen.getByLabelText('Comparison period label'), { target: { value: 'Prior' } });
    fireEvent.change(screen.getByLabelText('Current period label'), { target: { value: 'Current' } });
    fireEvent.change(screen.getByLabelText('Clicks — current period'), { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Compare supplied values' }));
    expect(screen.getByRole('alert').textContent).toMatch(/both periods or leave both blank/i);
  });
});
