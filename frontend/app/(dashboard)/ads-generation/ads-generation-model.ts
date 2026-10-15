export type AdsGenerationResult = {
  status: 'ok';
  platform: string;
  objective: string;
  ai_status: 'generated' | 'fallback';
  provider_used: string;
  model_used: string;
  outputs: { text: string };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function optionalString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

export function parseAdsGenerationResult(value: unknown): AdsGenerationResult | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  if (typeof value.platform !== 'string' || typeof value.objective !== 'string') return null;
  if (value.ai_status !== 'generated' && value.ai_status !== 'fallback') return null;
  if (!isRecord(value.outputs)) return null;

  const text = optionalString(value.outputs.text);
  if (!text) return null;

  return {
    status: 'ok',
    platform: value.platform,
    objective: value.objective,
    ai_status: value.ai_status,
    provider_used: optionalString(value.provider_used),
    model_used: optionalString(value.model_used),
    outputs: { text },
  };
}
