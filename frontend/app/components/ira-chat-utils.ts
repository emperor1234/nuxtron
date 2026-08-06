export type IraBackendMeta = {
  confidence?: number;
  intent?: string;
  domain?: string;
  riskLevel?: string;
  actionLabels: string[];
  knowledgeHits: string[];
  providerRequested?: string;
  providerUsed?: string;
  providerModel?: string;
  providerStatus?: string;
};

export type IraChatProviderPreference = 'auto' | 'internal' | 'openai' | 'anthropic' | 'custom';

export type IraChatProviderSettings = {
  providerPreference: IraChatProviderPreference;
  customProvider?: string;
};

type JsonRecord = Record<string, unknown>;

const IRA_EXTERNAL_PROVIDER_CANDIDATES = ['internal', 'openai', 'anthropic'];

function toRecord(value: unknown): JsonRecord | null {
  return typeof value === 'object' && value !== null ? (value as JsonRecord) : null;
}

function toLabelList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      const record = toRecord(item);
      const label = record && typeof record.label === 'string' ? record.label.trim() : '';
      return label;
    })
    .filter((label) => label.length > 0);
}

function toKnowledgeHits(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      const record = toRecord(item);
      if (!record) {
        return '';
      }

      const title = typeof record.title === 'string' ? record.title.trim() : '';
      const documentId =
        typeof record.document_id === 'string' || typeof record.document_id === 'number'
          ? String(record.document_id).trim()
          : '';

      return title || documentId;
    })
    .filter((entry) => entry.length > 0)
    .slice(0, 3);
}

export function getBackendErrorMessage(err: unknown): string {
  const message = typeof toRecord(err)?.message === 'string' ? toRecord(err)?.message : 'request failed';
  return `⚠️ **IRA backend unavailable.** I could not reach the autonomous service (${message}). Please retry in a few seconds.`;
}

export function extractIraBackendReply(data: unknown): string | null {
  const payload = toRecord(toRecord(data)?.ira);

  if (!payload) {
    return null;
  }

  const response = payload.response;
  return typeof response === 'string' && response.trim() ? response : null;
}

export function extractIraBackendMeta(data: unknown): IraBackendMeta | null {
  const payload = toRecord(data);
  const ira = toRecord(payload?.ira);
  if (!ira) {
    return null;
  }

  const actionPlan = toRecord(ira.action_plan);
  const riskAssessment = toRecord(ira.risk_assessment);
  const meta: IraBackendMeta = {
    confidence: typeof ira.confidence === 'number' ? ira.confidence : undefined,
    intent: typeof ira.intent === 'string' ? ira.intent : undefined,
    domain: typeof ira.domain === 'string' ? ira.domain : undefined,
    riskLevel: typeof riskAssessment?.risk_level === 'string' ? riskAssessment.risk_level : undefined,
    actionLabels: toLabelList(actionPlan?.recommended_actions),
    knowledgeHits: toKnowledgeHits(ira.knowledge_hits),
    providerRequested: typeof ira.provider_requested === 'string' ? ira.provider_requested : undefined,
    providerUsed: typeof ira.provider_used === 'string' ? ira.provider_used : undefined,
    providerModel: typeof ira.provider_model === 'string' ? ira.provider_model : undefined,
    providerStatus: typeof ira.provider_status === 'string' ? ira.provider_status : undefined,
  };

  if (
    meta.confidence === undefined &&
    !meta.intent &&
    !meta.domain &&
    !meta.riskLevel &&
    meta.actionLabels.length === 0 &&
    meta.knowledgeHits.length === 0 &&
    !meta.providerRequested &&
    !meta.providerUsed &&
    !meta.providerModel &&
    !meta.providerStatus
  ) {
    return null;
  }

  return meta;
}

export function resolveIraPreferredProvider(settings: IraChatProviderSettings): string {
  if (settings.providerPreference === 'custom') {
    return settings.customProvider?.trim() || 'custom';
  }

  return settings.providerPreference;
}

export function buildIraChatContext(
  context: JsonRecord,
  settings: IraChatProviderSettings
): JsonRecord {
  const preferredProvider = resolveIraPreferredProvider(settings);
  const requestedExternalProvider = preferredProvider !== 'auto' && preferredProvider !== 'internal';

  return {
    ...context,
    llm_routing: {
      preferred_provider: preferredProvider,
      requested_external_provider: requestedExternalProvider,
      candidate_providers: requestedExternalProvider ? [preferredProvider] : IRA_EXTERNAL_PROVIDER_CANDIDATES,
      custom_provider_label: settings.providerPreference === 'custom' ? settings.customProvider?.trim() || '' : '',
    },
  };
}
