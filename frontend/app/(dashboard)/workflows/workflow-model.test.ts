import { describe, expect, it } from 'vitest';
import { isWorkflowPreviewResponse, parseWorkflowList } from './workflow-model';

const response = {
  status: 'ok',
  total: 1,
  workflows: [{ id: 8, name: 'Lifecycle follow-up', description: 'Contact follow-up', trigger: { trigger_type: 'contact_created' }, status: 'active', step_count: 0, updated_at: '2026-10-12T10:00:00Z', enrollment_count: 44, execution_count: 128 }],
};

describe('workflow definition model', () => {
  it('extracts only definition metadata, not simulated execution or enrollment counters', () => {
    expect(parseWorkflowList(response)).toEqual({
      total: 1,
      workflows: [{ id: 8, name: 'Lifecycle follow-up', description: 'Contact follow-up', triggerType: 'contact_created', status: 'active', stepCount: 0, updatedAt: '2026-10-12T10:00:00Z' }],
    });
  });

  it('preserves a real zero and represents missing step counts as unavailable', () => {
    expect(parseWorkflowList(response).workflows[0].stepCount).toBe(0);
    expect(parseWorkflowList({ ...response, workflows: [{ id: 8, name: 'Workflow' }] }).workflows[0].stepCount).toBeNull();
  });

  it('fails closed when the response or a record is malformed', () => {
    expect(() => parseWorkflowList({ workflows: [] })).toThrow(/incomplete/);
    expect(() => parseWorkflowList({ ...response, workflows: [{ name: 'Missing ID' }] })).toThrow(/identifier/);
    expect(() => parseWorkflowList({ ...response, workflows: [{ id: 8 }] })).toThrow(/no name/);
  });

  it('detects explicit mock, fallback, and preview sources', () => {
    expect(isWorkflowPreviewResponse({ ...response, data_source: 'fallback' })).toBe(true);
    expect(isWorkflowPreviewResponse({ ...response, is_demo: true })).toBe(true);
    expect(isWorkflowPreviewResponse(response)).toBe(false);
  });
});
