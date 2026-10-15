export type WorkflowStepInput = Record<string, unknown>;

export function parseWorkflowSteps(input: string): WorkflowStepInput[] {
  if (!input.trim()) {
    throw new Error('Add workflow steps before creating the automation.');
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(input);
  } catch {
    throw new Error('Workflow steps must be valid JSON.');
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('Workflow steps must be a non-empty JSON array.');
  }

  if (
    parsed.some(
      (step) =>
        !step ||
        typeof step !== 'object' ||
        Array.isArray(step) ||
        typeof (step as Record<string, unknown>).step_id !== 'string' ||
        !(step as Record<string, unknown>).step_id ||
        typeof (step as Record<string, unknown>).action_type !== 'string' ||
        !(step as Record<string, unknown>).action_type
    )
  ) {
    throw new Error('Each workflow step needs a step_id and an action_type.');
  }

  return parsed as WorkflowStepInput[];
}
