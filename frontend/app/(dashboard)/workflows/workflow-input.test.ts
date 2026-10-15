import { describe, expect, it } from 'vitest';

import { parseWorkflowSteps } from './workflow-input';

describe('parseWorkflowSteps', () => {
  it('rejects empty input', () => {
    expect(() => parseWorkflowSteps('  ')).toThrow('Add workflow steps');
  });

  it('rejects malformed JSON', () => {
    expect(() => parseWorkflowSteps('{')).toThrow('valid JSON');
  });

  it('requires a non-empty array with step identifiers and action types', () => {
    expect(() => parseWorkflowSteps('[]')).toThrow('non-empty JSON array');
    expect(() => parseWorkflowSteps('[{"step_id":"step-1"}]')).toThrow('step_id and an action_type');
  });

  it('accepts a user-provided workflow step array', () => {
    expect(parseWorkflowSteps('[{"step_id":"step-1","action_type":"send_email","config":{}}]')).toEqual([
      { step_id: 'step-1', action_type: 'send_email', config: {} },
    ]);
  });
});
