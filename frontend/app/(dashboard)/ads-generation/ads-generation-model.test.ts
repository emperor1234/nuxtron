import { describe, expect, it } from 'vitest';
import { parseAdsGenerationResult } from './ads-generation-model';

const generated = {
  status: 'ok',
  platform: 'linkedin',
  objective: 'leads',
  ai_status: 'generated',
  provider_used: 'openai',
  model_used: 'model-x',
  outputs: { text: 'A provider-generated draft.' },
  headlines: ['A backend template headline that the customer UI must not label as AI output.'],
};

describe('parseAdsGenerationResult', () => {
  it("accepts the backend's explicit provider-generated text contract", () => {
    expect(parseAdsGenerationResult(generated)).toEqual({
      status: 'ok',
      platform: 'linkedin',
      objective: 'leads',
      ai_status: 'generated',
      provider_used: 'openai',
      model_used: 'model-x',
      outputs: { text: 'A provider-generated draft.' },
    });
  });

  it('preserves fallback status so template text can be hidden instead of reported as generated', () => {
    expect(parseAdsGenerationResult({
      ...generated,
      ai_status: 'fallback',
      outputs: { text: 'Deterministic fallback template.' },
    })?.ai_status).toBe('fallback');
  });

  it.each([
    null,
    {},
    { ...generated, status: 'preview' },
    { ...generated, ai_status: 'unknown' },
    { ...generated, outputs: { text: '   ' } },
    { ...generated, outputs: null },
  ])('rejects incomplete or malformed generation responses', (value) => {
    expect(parseAdsGenerationResult(value)).toBeNull();
  });
});
