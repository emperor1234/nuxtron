type JsonObject = Record<string, unknown>;

export type WorkflowDefinition = {
  id: number;
  name: string;
  description: string | null;
  triggerType: string;
  status: string;
  stepCount: number | null;
  updatedAt: string | null;
};

export type WorkflowList = {
  workflows: WorkflowDefinition[];
  total: number | null;
};

function object(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : null;
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function nonNegativeInteger(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

export function isWorkflowPreviewResponse(value: unknown): boolean {
  const payload = object(value);
  if (!payload) return false;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

export function parseWorkflowList(value: unknown): WorkflowList {
  const payload = object(value);
  if (!payload || payload.status !== 'ok' || !Array.isArray(payload.workflows)) {
    throw new Error('Workflow service returned an incomplete definitions list.');
  }

  const workflows = payload.workflows.map((entry, index): WorkflowDefinition => {
    const workflow = object(entry);
    const trigger = object(workflow?.trigger);
    if (!workflow || typeof workflow.id !== 'number' || !Number.isSafeInteger(workflow.id) || workflow.id <= 0) {
      throw new Error(`Workflow definition ${index + 1} has an invalid identifier.`);
    }
    const name = text(workflow.name);
    if (!name) throw new Error(`Workflow definition ${index + 1} has no name.`);
    return {
      id: workflow.id,
      name,
      description: text(workflow.description),
      triggerType: text(trigger?.trigger_type) ?? 'Trigger unavailable',
      status: text(workflow.status) ?? 'Status unavailable',
      stepCount: nonNegativeInteger(workflow.step_count),
      updatedAt: text(workflow.updated_at),
    };
  });

  return { workflows, total: nonNegativeInteger(payload.total) };
}
