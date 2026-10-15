export type InboxMessage = {
  id: number;
  network: string;
  source_type: string;
  author_handle: string;
  text: string;
  message_type: string;
  sentiment: string;
  priority_score: number | null;
  status: string;
  read: boolean | null;
};

export type InboxStats = {
  total: number;
  unread: number;
};

export type InboxStatusFilter = 'all' | 'pending' | 'in_progress' | 'requires_approval' | 'flagged' | 'complete';

type JsonObject = Record<string, unknown>;

function object(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : null;
}

function requiredText(value: unknown, field: string): string {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`Inbox response is missing ${field}.`);
  }
  return value.trim();
}

function count(value: unknown, field: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`Inbox response has an invalid ${field} count.`);
  }
  return value;
}

export function isInboxPreviewResponse(value: unknown): boolean {
  const payload = object(value);
  if (!payload) return false;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

export function parseInboxStats(value: unknown): InboxStats {
  const payload = object(value);
  if (!payload || payload.status !== 'ok') {
    throw new Error('Inbox statistics are unavailable or malformed.');
  }
  return {
    total: count(payload.total, 'total'),
    unread: count(payload.unread, 'unread'),
  };
}

export function parseInboxMessages(value: unknown): InboxMessage[] {
  const payload = object(value);
  if (!payload || payload.status !== 'ok' || !Array.isArray(payload.messages)) {
    throw new Error('Inbox messages are unavailable or malformed.');
  }

  return payload.messages.map((entry, index) => {
    const message = object(entry);
    if (!message || typeof message.id !== 'number' || !Number.isSafeInteger(message.id) || message.id < 1) {
      throw new Error(`Inbox message ${index + 1} has an invalid identifier.`);
    }
    const priority = message.priority_score;
    const read = message.read;
    return {
      id: message.id,
      network: requiredText(message.network, 'message channel'),
      source_type: requiredText(message.source_type, 'message source type'),
      author_handle: requiredText(message.author_handle, 'message author'),
      text: requiredText(message.text, 'message text'),
      message_type: typeof message.message_type === 'string' && message.message_type.trim() ? message.message_type.trim() : 'Unclassified',
      sentiment: typeof message.sentiment === 'string' && message.sentiment.trim() ? message.sentiment.trim() : 'Unknown',
      priority_score: typeof priority === 'number' && Number.isFinite(priority) ? priority : null,
      status: requiredText(message.status, 'message status'),
      read: typeof read === 'boolean' ? read : null,
    };
  });
}

export function filterInboxMessages(
  messages: InboxMessage[],
  status: InboxStatusFilter,
  query: string,
): InboxMessage[] {
  const normalizedQuery = query.trim().toLowerCase();
  return messages.filter((message) => {
    const matchesStatus = status === 'all' || message.status === status;
    const searchable = `${message.author_handle} ${message.network} ${message.source_type} ${message.text}`.toLowerCase();
    return matchesStatus && (!normalizedQuery || searchable.includes(normalizedQuery));
  });
}
