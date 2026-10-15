import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import KnowledgeGraphPage from './page';

afterEach(() => cleanup());

describe('Entity Graph Planner page', () => {
  it('starts blank and explains that no external graph or live site is queried', () => {
    render(<KnowledgeGraphPage />);

    expect(screen.getByRole('heading', { name: 'Entity Graph Planner', level: 1 })).toBeTruthy();
    expect((screen.getByLabelText(/^Entities/i) as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(/does not query Google, Wikidata, your site, or an external graph service/i)).toBeTruthy();
    expect(screen.queryByText('Graph Health')).toBeNull();
  });

  it('shows counts and relationship rows only from explicitly supplied outline entries', () => {
    const { container } = render(<KnowledgeGraphPage />);
    fireEvent.change(screen.getByLabelText(/^Entities/i), { target: { value: 'Organization\nProduct\nTopic' } });
    fireEvent.change(screen.getByLabelText(/^Relationships/i), { target: { value: 'Organization | offers | Product\nProduct | serves | Topic' } });
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected entity outline form');
    fireEvent.submit(form);

    expect(screen.getByRole('heading', { name: 'Outline summary' })).toBeTruthy();
    expect(screen.getByText('Explicit relationships')).toBeTruthy();
    expect(screen.getByText('Connected entities')).toBeTruthy();
    expect(screen.getAllByText(/Organization/).length).toBeGreaterThan(0);
    expect(screen.getByText('serves', { selector: 'b' })).toBeTruthy();
    expect(screen.queryByText('Graph Health')).toBeNull();
    expect(screen.getByText(/Local draft only\. No page crawling, knowledge-graph lookup, rank measurement, or schema publishing occurs/i)).toBeTruthy();
  });

  it('rejects a relationship endpoint not present in the entity list', () => {
    const { container } = render(<KnowledgeGraphPage />);
    fireEvent.change(screen.getByLabelText(/^Entities/i), { target: { value: 'Organization\nProduct' } });
    fireEvent.change(screen.getByLabelText(/^Relationships/i), { target: { value: 'Organization | offers | Unknown' } });
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected entity outline form');
    fireEvent.submit(form);

    expect(screen.getByRole('alert').textContent).toMatch(/endpoints must match entities/i);
    expect(screen.queryByRole('heading', { name: 'Outline summary' })).toBeNull();
  });
});
