import { describe, expect, it } from 'vitest';
import { parseSeoPlannerDraft } from './planner-model';

const validDraft = {
  status: 'draft',
  goal: 'Increase qualified organic visits',
  domain: 'example.com',
  primary_keyword: 'workflow software',
  market: 'us',
  created_at: '2026-10-13T10:00:00Z',
  analysis_mode: 'llm',
  ai_available: true,
  planner_score: 99,
  tenant_id: 'must-not-reach-the-view-model',
  workflow: [
    { phase: 'Validate search evidence', module: 'Keyword Data Review', action: 'Inspect a keyword export you provide.', path: '/seo/keywords' },
    { phase: 'Prepare content', module: 'Content Generation', action: 'Prepare a draft.', path: '//outside.example' },
    { phase: 'Invalid row', module: 'Missing action', path: '/seo/history' },
  ],
  priorities: ['Check search intent'],
  risks: ['The brief does not include current traffic evidence'],
  next_actions: ['Assign an owner'],
};

describe('SEO Planner response model', () => {
  it('accepts a draft while omitting tenant identifiers and ungrounded scores', () => {
    const parsed = parseSeoPlannerDraft(validDraft);
    expect(parsed).toEqual({
      goal: 'Increase qualified organic visits',
      domain: 'example.com',
      primaryKeyword: 'workflow software',
      market: 'us',
      workflow: [
        { phase: 'Validate search evidence', module: 'Keyword Data Review', action: 'Inspect a keyword export you provide.', path: '/seo/keywords' },
        { phase: 'Prepare content', module: 'Content Generation', action: 'Prepare a draft.', path: '' },
      ],
      priorities: ['Check search intent'],
      risks: ['The brief does not include current traffic evidence'],
      nextActions: ['Assign an owner'],
      analysisMode: 'llm',
      aiAvailable: true,
      createdAt: '2026-10-13T10:00:00Z',
      cached: false,
    });
    expect(parsed && 'planner_score' in parsed).toBe(false);
    expect(JSON.stringify(parsed)).not.toContain('must-not-reach-the-view-model');
  });

  it('rejects non-draft or missing-provenance responses', () => {
    expect(parseSeoPlannerDraft({ ...validDraft, status: 'planned' })).toBeNull();
    expect(parseSeoPlannerDraft({ ...validDraft, analysis_mode: 'unknown' })).toBeNull();
    expect(parseSeoPlannerDraft({ ...validDraft, ai_available: undefined })).toBeNull();
    expect(parseSeoPlannerDraft({ ...validDraft, goal: 'bad' })).toBeNull();
  });

  it('bounds generated text lists and accepts only internal route paths', () => {
    const parsed = parseSeoPlannerDraft({
      ...validDraft,
      workflow: [{ phase: 'Review', module: 'History', action: 'Check the record.', path: 'javascript:alert(1)' }],
      priorities: Array.from({ length: 30 }, (_, index) => `priority ${index}`),
    });
    expect(parsed?.workflow[0]?.path).toBe('');
    expect(parsed?.priorities).toHaveLength(20);
  });
});
