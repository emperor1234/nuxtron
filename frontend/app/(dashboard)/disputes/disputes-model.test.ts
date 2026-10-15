import { describe, expect, it } from 'vitest';
import { isDisputesPreviewResponse, parseDisputesDashboard } from './disputes-model';

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
  reputation_guardrail: 'Human review is required before a dispute decision.',
};

describe('Disputes dashboard response model', () => {
  it('preserves legitimate zero counts and the server review requirement', () => {
    expect(parseDisputesDashboard(emptyResponse).summary).toEqual({
      totalEvents: 0,
      totalTickets: 0,
      openTickets: 0,
      queuedForHumanReview: 0,
      humanApprovalRequired: true,
    });
  });

  it('represents missing metrics as unavailable instead of zero', () => {
    const parsed = parseDisputesDashboard({
      ...emptyResponse,
      summary: { ...emptyResponse.summary, open_dispute_tickets: null },
    });
    expect(parsed.summary.openTickets).toBeNull();
  });

  it('preserves ticket/event values and defensively labels missing text', () => {
    const parsed = parseDisputesDashboard({
      ...emptyResponse,
      tickets: [{ id: 32, status: 'open', subject: 'Charge disputed' }],
      recent_dispute_events: [{ id: 'evt-4', created_at: '2026-10-12T10:00:00Z' }],
    });
    expect(parsed.tickets[0]).toMatchObject({ id: 32, status: 'open', channel: 'Channel unavailable' });
    expect(parsed.events[0]).toMatchObject({ id: 'evt-4', eventType: 'Event unavailable' });
  });

  it('fails closed for malformed list envelopes and row identifiers', () => {
    expect(() => parseDisputesDashboard({ ...emptyResponse, tickets: null })).toThrow(/incomplete/);
    expect(() => parseDisputesDashboard({ ...emptyResponse, tickets: [{ subject: 'No id' }] })).toThrow(/identifier/);
  });

  it('detects preview-backed data', () => {
    expect(isDisputesPreviewResponse({ ...emptyResponse, data_source: 'fallback' })).toBe(true);
    expect(isDisputesPreviewResponse(emptyResponse)).toBe(false);
  });
});
