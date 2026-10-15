import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import CrawlBudgetPage from './page';

afterEach(() => cleanup());

function submit(form: HTMLFormElement) {
  fireEvent.submit(form);
}

describe('Crawl Budget Review page', () => {
  it('starts with blank evidence inputs and explains local, sample-only processing', () => {
    render(<CrawlBudgetPage />);

    expect(screen.getByRole('heading', { name: 'Crawl Budget Review', level: 1 })).toBeTruthy();
    expect((screen.getByLabelText(/Website origin/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Sample URLs/i) as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/analyzed in this browser and are not sent to the Nuxtron API/i)).toBeTruthy();
    expect(screen.queryByText(/Crawl Budget Score/i)).toBeNull();
  });

  it('reports only observed patterns and status codes from supplied samples', () => {
    const { container } = render(<CrawlBudgetPage />);
    fireEvent.change(screen.getByLabelText(/Website origin/i), { target: { value: 'example.com' } });
    fireEvent.change(screen.getByLabelText(/^Sample URLs/i), { target: { value: '/pricing\n/tag/news' } });
    fireEvent.change(screen.getByLabelText(/Access-log excerpt/i), {
      target: { value: '192.0.2.5 - - [12/Oct/2026:21:00:00 -0700] "GET /tag/news HTTP/1.1" 404 10 "-" "ExampleBot/1.0"' },
    });
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected Crawl Budget evidence form');
    submit(form);

    expect(screen.getByRole('heading', { name: 'Review summary' })).toBeTruthy();
    expect(screen.getByText('Tag archive path')).toBeTruthy();
    expect(screen.getByText(/Parsed requests: 1; response codes: 404 × 1/i)).toBeTruthy();
    expect(screen.getByText(/4xx \/ 5xx in sample/i)).toBeTruthy();
    expect(screen.queryByText('Crawl Budget Score')).toBeNull();
    expect((screen.getByRole('button', { name: 'Export candidate list' }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('rejects cross-origin samples and does not present them as measured findings', () => {
    const { container } = render(<CrawlBudgetPage />);
    fireEvent.change(screen.getByLabelText(/Website origin/i), { target: { value: 'example.com' } });
    fireEvent.change(screen.getByLabelText(/^Sample URLs/i), { target: { value: 'https://other.invalid/tag/' } });
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected Crawl Budget evidence form');
    submit(form);

    expect(screen.getByRole('alert').textContent).toMatch(/outside the selected website origin/i);
    expect(screen.queryByRole('heading', { name: 'Review summary' })).toBeNull();
  });

  it('reports a clear error when an access-log excerpt has no supported request rows', () => {
    const { container } = render(<CrawlBudgetPage />);
    fireEvent.change(screen.getByLabelText(/Website origin/i), { target: { value: 'example.com' } });
    fireEvent.change(screen.getByLabelText(/Access-log excerpt/i), { target: { value: 'unrecognized log text' } });
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected Crawl Budget evidence form');
    submit(form);

    expect(screen.getByRole('alert').textContent).toMatch(/no supported access-log request lines/i);
    expect(screen.queryByText('4xx / 5xx in sample')).toBeNull();
  });
});
