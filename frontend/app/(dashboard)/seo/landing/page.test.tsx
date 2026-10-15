import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LandingPageBriefPage from './page';
import { apiSend } from '@/app/lib/platform-api';

vi.mock('@/app/lib/platform-api', () => ({ apiSend: vi.fn() }));
vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: vi.fn(() => 'workspace-session-1') }));

const apiSendMock = vi.mocked(apiSend);

const validResponse = {
  analysis_id: 'analysis-brief-1',
  analysis_mode: 'heuristic',
  cached: false,
  hero: { headline: 'Page headline', subheadline: 'Supporting copy', cta: 'Review plans' },
  sections: ['Problem', 'Approach', 'Evidence', 'Next step'],
  seo_meta: { title: 'Metadata title', description: 'Metadata description', canonical: '/draft-path' },
  faq_pairs: [{ question: 'What does this do?', answer: 'An unverified generated answer.' }],
  ab_test_variants: ['An alternate headline'],
  schema_markup: [{ type: 'Product', json_ld: { '@type': 'Product', name: 'User product' } }],
  conversion_signals: ['Add verified customer evidence'],
  landing_page_score: 99,
  recommended_tools: ['Unrequested third-party recommendation'],
};

beforeEach(() => vi.clearAllMocks());
afterEach(() => cleanup());

describe('Landing Page Brief page', () => {
  it('starts without prefilled product, keyword, audience, or schema assumptions', () => {
    render(<LandingPageBriefPage />);

    expect((screen.getByLabelText(/^Product or brand/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Target keyword/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Target audience/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Product') as HTMLInputElement).checked).toBe(false);
    expect(screen.getByText(/does not build, publish, or change a live page/i)).toBeTruthy();
  });

  it('requires explicit context/schema selection and submits against the session workspace', async () => {
    const { container } = render(<LandingPageBriefPage />);
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected landing brief form');
    fireEvent.submit(form);

    expect(screen.getByRole('alert').textContent).toMatch(/product or brand, target keyword, audience/i);
    expect(apiSendMock).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText(/^Product or brand/i), { target: { value: 'Product X' } });
    fireEvent.change(screen.getByLabelText(/^Target keyword/i), { target: { value: 'workflow software' } });
    fireEvent.change(screen.getByLabelText(/^Target audience/i), { target: { value: 'Operations teams' } });
    fireEvent.change(screen.getByLabelText(/^Context and differentiators/i), { target: { value: 'Approved claims only' } });
    fireEvent.click(screen.getByLabelText('Product'));
    fireEvent.click(screen.getByLabelText('FAQPage'));
    apiSendMock.mockResolvedValue(validResponse as never);
    fireEvent.click(screen.getByRole('button', { name: 'Generate Landing Page Brief' }));

    expect(await screen.findByRole('heading', { name: 'Landing page brief' })).toBeTruthy();
    expect(apiSendMock).toHaveBeenCalledWith(
      '/seo-platform/landing/generate',
      'POST',
      {
        product_name: 'Product X',
        target_keyword: 'workflow software',
        audience: 'Operations teams',
        schema_types: ['Product', 'FAQPage'],
        notes: 'Approved claims only',
      },
      'workspace-session-1',
    );
    expect(screen.getByText(/Heuristic\/template draft · not AI-generated/i)).toBeTruthy();
    expect(screen.getByText('Add verified customer evidence')).toBeTruthy();
    expect(screen.queryByText('99')).toBeNull();
    expect(screen.queryByText('Unrequested third-party recommendation')).toBeNull();
    expect(screen.getByText('Review plans').closest('button')).toBeNull();
  });

  it('keeps missing service fields distinct and rejects fallback output mislabeled as provider-generated', async () => {
    const { container } = render(<LandingPageBriefPage />);
    fireEvent.change(screen.getByLabelText(/^Product or brand/i), { target: { value: 'Product X' } });
    fireEvent.change(screen.getByLabelText(/^Target keyword/i), { target: { value: 'workflow software' } });
    fireEvent.change(screen.getByLabelText(/^Target audience/i), { target: { value: 'Operations teams' } });
    fireEvent.click(screen.getByLabelText('Product'));
    apiSendMock.mockResolvedValue({ ...validResponse, sections: undefined, fallback: true, analysis_mode: 'llm' } as never);
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected landing brief form');
    fireEvent.submit(form);

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toMatch(/fallback response was not identified/i);
    expect(screen.queryByRole('heading', { name: 'Landing page brief' })).toBeNull();
  });
});
