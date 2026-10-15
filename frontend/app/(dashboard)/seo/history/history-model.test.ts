import { describe, expect, it } from 'vitest';
import {
  describeSavedResult,
  formatModuleLabel,
  formatRedactedJson,
  parseSeoHistoryResponse,
} from './history-model';

const record = {
  id: 'analysis-123',
  tenant_id: 'workspace-private',
  module: 'seo_content_check',
  created_at: '2026-10-13T10:00:00Z',
  payload: { domain: 'example.com', api_key: 'secret-value' },
  result: { summary: 'Historical result', email: 'private@example.com', nested: { access_token: 'secret' } },
};

describe('SEO History model', () => {
  it('accepts a genuine empty history with explicit PostgreSQL persistence', () => {
    expect(parseSeoHistoryResponse({ analyses: [], total: 0, persistence: 'postgres' })).toEqual({
      analyses: [],
      total: 0,
      persistence: 'postgres',
    });
  });

  it('accepts a valid record but excludes backend tenant identifiers', () => {
    const parsed = parseSeoHistoryResponse({ analyses: [record], total: 1, persistence: 'memory' });
    expect(parsed?.analyses[0]).not.toHaveProperty('tenant_id');
    expect(parsed?.analyses[0]).toMatchObject({ id: 'analysis-123', module: 'seo_content_check' });
    expect(parsed?.persistence).toBe('memory');
  });

  it('rejects missing persistence, malformed records, invalid dates, and inconsistent counts', () => {
    expect(parseSeoHistoryResponse({ analyses: [], total: 0 })).toBeNull();
    expect(parseSeoHistoryResponse({ analyses: [{ ...record, created_at: 'not-a-date' }], total: 1, persistence: 'postgres' })).toBeNull();
    expect(parseSeoHistoryResponse({ analyses: [record], total: 0, persistence: 'postgres' })).toBeNull();
    expect(parseSeoHistoryResponse({ analyses: [{ ...record, result: null }], total: 1, persistence: 'memory' })).toBeNull();
  });

  it('redacts workspace identifiers, tokens, credentials, and contact fields from JSON detail', () => {
    const output = formatRedactedJson({
      tenant_id: 'workspace-private',
      api_key: 'secret-value',
      result: { email: 'private@example.com', access_token: 'secret', safe: 'visible' },
    });
    expect(output).not.toContain('workspace-private');
    expect(output).not.toContain('secret-value');
    expect(output).not.toContain('private@example.com');
    expect(output).toContain('[redacted]');
    expect(output).toContain('visible');
  });

  it('uses concise human-readable labels for module keys and archived output size', () => {
    const parsed = parseSeoHistoryResponse({ analyses: [record], total: 1, persistence: 'postgres' });
    expect(formatModuleLabel('seo_content-check')).toBe('Seo Content Check');
    expect(formatModuleLabel('keyword_research')).toBe('Keyword Data Review');
    expect(formatModuleLabel('keyword-research-engine')).toBe('Keyword Data Review');
    expect(formatModuleLabel('planner_workflow_draft')).toBe('SEO Workflow Planner');
    expect(formatModuleLabel('performance_audit')).toBe('Performance Audit (retired)');
    expect(formatModuleLabel('international_multilingual')).toBe('Hreflang & Locale Review');
    expect(formatModuleLabel('international-multilingual-seo')).toBe('Hreflang & Locale Review');
    expect(formatModuleLabel('rag_search')).toBe('Corpus Search Preview');
    expect(formatModuleLabel('programmatic')).toBe('Programmatic SEO Draft Preview');
    expect(formatModuleLabel('programmatic-seo-engine')).toBe('Programmatic SEO Draft Preview');
    expect(parsed && describeSavedResult(parsed.analyses[0])).toBe('2 saved output fields');
  });
});
