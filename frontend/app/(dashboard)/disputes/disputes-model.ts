type JsonObject = Record<string, unknown>;

export type DisputeSummary = {
  totalEvents: number | null;
  totalTickets: number | null;
  openTickets: number | null;
  queuedForHumanReview: number | null;
  humanApprovalRequired: boolean | null;
};

export type DisputeTicket = {
  id: string | number;
  subject: string;
  status: string;
  priority: string;
  channel: string;
  updatedAt: string | null;
};

export type DisputeEvent = {
  id: string | number;
  eventType: string;
  createdAt: string | null;
};

export type DisputesDashboard = {
  summary: DisputeSummary;
  tickets: DisputeTicket[];
  events: DisputeEvent[];
  guardrail: string | null;
};

function object(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : null;
}

function count(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

function stableId(value: unknown, label: string): string | number {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value;
  if (typeof value === 'string' && value.trim()) return value.trim();
  throw new Error(`Disputes response has an invalid ${label} identifier.`);
}

function text(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function optionalText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export function isDisputesPreviewResponse(value: unknown): boolean {
  const payload = object(value);
  if (!payload) return false;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

export function parseDisputesDashboard(value: unknown): DisputesDashboard {
  const payload = object(value);
  const rawSummary = object(payload?.summary);
  if (!payload || payload.status !== 'ok' || !rawSummary || !Array.isArray(payload.tickets) || !Array.isArray(payload.recent_dispute_events)) {
    throw new Error('Disputes dashboard returned an incomplete response.');
  }

  const tickets = payload.tickets.map((entry, index): DisputeTicket => {
    const ticket = object(entry);
    if (!ticket) throw new Error(`Dispute ticket ${index + 1} is malformed.`);
    return {
      id: stableId(ticket.id, `ticket ${index + 1}`),
      subject: text(ticket.subject, 'Subject unavailable'),
      status: text(ticket.status, 'Status unavailable'),
      priority: text(ticket.priority, 'Priority unavailable'),
      channel: text(ticket.channel, 'Channel unavailable'),
      updatedAt: optionalText(ticket.updated_at),
    };
  });

  const events = payload.recent_dispute_events.map((entry, index): DisputeEvent => {
    const event = object(entry);
    if (!event) throw new Error(`Dispute event ${index + 1} is malformed.`);
    return {
      id: stableId(event.id, `event ${index + 1}`),
      eventType: text(event.event_type, 'Event unavailable'),
      createdAt: optionalText(event.created_at),
    };
  });

  return {
    summary: {
      totalEvents: count(rawSummary.total_dispute_events),
      totalTickets: count(rawSummary.total_dispute_tickets),
      openTickets: count(rawSummary.open_dispute_tickets),
      queuedForHumanReview: count(rawSummary.queued_for_human_validation),
      humanApprovalRequired: typeof rawSummary.human_approval_required_for_all_disputes === 'boolean'
        ? rawSummary.human_approval_required_for_all_disputes
        : null,
    },
    tickets,
    events,
    guardrail: optionalText(payload.reputation_guardrail),
  };
}
