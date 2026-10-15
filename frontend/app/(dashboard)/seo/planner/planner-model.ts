export type PlannerWorkflowStep = {
  phase: string;
  module: string;
  action: string;
  path: string;
};

export type SeoPlannerDraft = {
  goal: string;
  domain: string;
  primaryKeyword: string;
  market: string;
  workflow: PlannerWorkflowStep[];
  priorities: string[];
  risks: string[];
  nextActions: string[];
  analysisMode: 'llm' | 'heuristic';
  aiAvailable: boolean;
  createdAt: string | null;
  cached: boolean;
};

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readText(value: unknown, maxLength = 1000): string {
  return typeof value === 'string' ? value.trim().slice(0, maxLength) : '';
}

function readTextList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim().slice(0, 1000))
    .filter(Boolean)
    .slice(0, 20);
}

function readWorkflow(value: unknown): PlannerWorkflowStep[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const phase = readText(item.phase, 80);
    const module = readText(item.module, 100);
    const action = readText(item.action, 1000);
    const candidatePath = readText(item.path, 300);
    const path = candidatePath.startsWith('/') && !candidatePath.startsWith('//') && !candidatePath.includes('\\')
      ? candidatePath
      : '';
    return phase && module && action ? [{ phase, module, action, path }] : [];
  }).slice(0, 20);
}

export function parseSeoPlannerDraft(value: unknown): SeoPlannerDraft | null {
  if (!isRecord(value) || value.status !== 'draft') return null;
  if (value.analysis_mode !== 'llm' && value.analysis_mode !== 'heuristic') return null;
  if (typeof value.ai_available !== 'boolean') return null;

  const goal = readText(value.goal, 1000);
  if (goal.length < 5) return null;

  const createdAt = readText(value.created_at, 80);
  return {
    goal,
    domain: readText(value.domain, 200),
    primaryKeyword: readText(value.primary_keyword, 200),
    market: readText(value.market, 200),
    workflow: readWorkflow(value.workflow),
    priorities: readTextList(value.priorities),
    risks: readTextList(value.risks),
    nextActions: readTextList(value.next_actions),
    analysisMode: value.analysis_mode,
    aiAvailable: value.ai_available,
    createdAt: createdAt && Number.isFinite(Date.parse(createdAt)) ? createdAt : null,
    cached: value.cached === true,
  };
}
