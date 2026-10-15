import { describe, expect, it } from 'vitest';
import {
  contentProvenance,
  parseContentLibrary,
  parseContentResult,
  parseJobList,
} from './content-generation-model';

describe('content generation model', () => {
  it("accepts the backend library's actual summary shape and a genuine empty list", () => {
    expect(parseContentLibrary({ status: 'ok', count: 0, items: [] })).toEqual([]);
    expect(parseContentLibrary({
      status: 'ok',
      count: 1,
      items: [{ generation_id: 'cg-1', topic: 'User topic', channel: 'blog', headline: 'A headline', created_at: '2026-10-12T00:00:00Z' }],
    })?.[0]).toEqual({
      generationId: 'cg-1',
      topic: 'User topic',
      channel: 'blog',
      headline: 'A headline',
      createdAt: '2026-10-12T00:00:00Z',
    });
  });

  it('rejects missing library identity or mismatched counts rather than treating malformed data as empty', () => {
    expect(parseContentLibrary({ status: 'ok', count: 1, items: [] })).toBeNull();
    expect(parseContentLibrary({ status: 'ok', count: 1, items: [{ topic: 'x' }] })).toBeNull();
    expect(parseContentLibrary({ status: 'preview', count: 0, items: [] })).toBeNull();
  });

  it('unwraps raw, async-job, and saved-library results while requiring actual copy fields', () => {
    const generated = { status: 'ok', ai_status: 'generated', headline: 'Generated headline', body: 'Generated body' };
    expect(parseContentResult(generated)).toEqual(generated);
    expect(parseContentResult({ item: { response: generated } })).toEqual(generated);
    expect(parseContentResult({ headline: 'Only a title' })).toBeNull();
    expect(parseContentResult({ status: 'failed', headline: 'x', body: 'y' })).toBeNull();
  });

  it('distinguishes AI output, template fallback, and unknown provenance', () => {
    expect(contentProvenance({ ai_status: 'generated' })).toBe('ai-generated');
    expect(contentProvenance({ ai_status: 'fallback' })).toBe('template-fallback');
    expect(contentProvenance({})).toBe('unknown');
  });

  it('parses real job list envelopes without relying on an absent count field', () => {
    expect(parseJobList({ status: 'ok', items: [], retention: { terminal_seconds: 3600 } })).toEqual({
      items: [],
      terminalRetentionSeconds: 3600,
    });
    expect(parseJobList({ status: 'ok', items: [{ job_id: 'j-1', status: 'running', stage: 'generating', progress_pct: 50 }] })?.items[0]?.progress_pct).toBe(50);
    expect(parseJobList({ status: 'ok', items: [{ job_id: 'j-1', status: 'running', stage: 'generating', progress_pct: 101 }] })).toBeNull();
    expect(parseJobList({ status: 'ok', items: [{ status: 'running' }] })).toBeNull();
  });
});
