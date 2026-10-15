import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'tenant-secret-77' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet }));

import DisputesDashboardPage from './page';

afterEach(() => cleanup());

const emptyResponse = {
  status: 'ok',
  summary: {
    total_dispute_events: 0,
    total_dispute_tickets: 0,
    open_dispute_tickets: 0,
    queued_for_human_validation: 0,
    human_approval_required_for_all_disputes: true,
  },
  tickets: [],
  recent_dispute_events: [],
};

const populatedResponse = {
  ...emptyResponse,
  summary: { ...emptyResponse.summary, total_dispute_tickets: 1, open_dispute_tickets: 1, queued_for_human_validation: 1 },
  tickets: [{ id: 'case-23', subject: 'Payment dispute', status: 'queued_for_human_validation', priority: 'high', channel: 'card', updated_at: '2026-10-12T10:00:00Z' }],
  recent_dispute_events: [{ id: 'event-4', event_type: 'customer_dispute_opened', created_at: '2026-10-12T10:00:00Z' }],
  reputation_guardrail: 'Review all submitted evidence before responding.',
};

describe('Disputes dashboard page', () => {
  beforeEach(() => {
    apiGet.mockReset();
  });

  it('shows a pending state first and only reports an empty queue after a successful response', async () => {
    let settle!: (value: unknown) => void;
    apiGet.mockImplementation(() => new Promise((resolve) => { settle = resolve; }));
    render(<DisputesDashboardPage />);

    expect(screen.getByText('Loading dispute cases…')).toBeTruthy();
    expect(screen.queryByText('No dispute tickets are recorded for this workspace.')).toBeNull();
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/ira/disputes/dashboard', 'tenant-secret-77'));

    await act(async () => settle(emptyResponse));
    expect(await screen.findByText('No dispute tickets are recorded for this workspace.')).toBeTruthy();
  });

  it('explains the human-review boundary and renders real case/event records without tenant identifiers or charts', async () => {
    apiGet.mockResolvedValue(populatedResponse);
    const { container } = render(<DisputesDashboardPage />);

    expect(await screen.findByText('Payment dispute')).toBeTruthy();
    expect(screen.getByText(/Human review is required before dispute decisions/)).toBeTruthy();
    expect(screen.getByText('Review all submitted evidence before responding.')).toBeTruthy();
    expect(screen.getByText(/customer_dispute_opened/)).toBeTruthy();
    expect(container.textContent).not.toContain('tenant-secret-77');
    expect(container.querySelector('svg')).toBeNull();
    expect(apiGet).toHaveBeenCalledTimes(1);
  });
});
