import { describe, expect, it } from 'vitest';
import { filterInboxMessages, isInboxPreviewResponse, parseInboxMessages, parseInboxStats } from './inbox-model';

const message = {
  id: 17,
  network: 'instagram',
  source_type: 'comment',
  author_handle: 'customer_17',
  text: 'Please help with my order',
  message_type: 'support',
  sentiment: 'negative',
  priority_score: 82,
  status: 'pending',
  read: false,
};

describe('Customer Inbox response model', () => {
  it('reads the backend total/unread fields and preserves legitimate zeros', () => {
    expect(parseInboxStats({ status: 'ok', total: 0, unread: 0 })).toEqual({ total: 0, unread: 0 });
  });

  it('parses a live message without inventing missing priority or read values', () => {
    const [parsed] = parseInboxMessages({ status: 'ok', messages: [{ ...message, priority_score: undefined, read: undefined }] });
    expect(parsed).toMatchObject({ id: 17, status: 'pending', priority_score: null, read: null });
  });

  it('rejects malformed list envelopes and invalid message identifiers', () => {
    expect(() => parseInboxMessages({ status: 'ok' })).toThrow(/malformed/);
    expect(() => parseInboxMessages({ status: 'ok', messages: [{ ...message, id: '17' }] })).toThrow(/identifier/);
  });

  it('does not turn missing counts into zero', () => {
    expect(() => parseInboxStats({ status: 'ok', total: 4 })).toThrow(/unread count/);
  });

  it('detects fallback data and filters by status and searchable content', () => {
    expect(isInboxPreviewResponse({ mode: 'fallback' })).toBe(true);
    expect(isInboxPreviewResponse({ status: 'ok' })).toBe(false);
    const messages = parseInboxMessages({ status: 'ok', messages: [message, { ...message, id: 18, status: 'complete' }] });
    expect(filterInboxMessages(messages, 'pending', 'order').map((entry) => entry.id)).toEqual([17]);
    expect(filterInboxMessages(messages, 'complete', '').map((entry) => entry.id)).toEqual([18]);
  });
});
