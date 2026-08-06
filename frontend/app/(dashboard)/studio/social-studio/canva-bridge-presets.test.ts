import { describe, expect, it } from 'vitest';

import { buildCanvaBridgePresetDraft } from './canva-bridge-presets';

describe('buildCanvaBridgePresetDraft', () => {
  it('builds a branded Canva preset draft from a full brand kit', () => {
    const draft = buildCanvaBridgePresetDraft({
      name: 'Launch Kit',
      colors: [{ hex: '#123456' }],
      fonts: [{ name: 'Sora' }],
    });

    expect(draft).toEqual({
      headline: 'Launch Kit',
      caption: 'Brand kit: Launch Kit · Primary color #123456 · Font Sora',
      activityMessage: 'Applied Launch Kit to Canva bridge.',
    });
  });

  it('falls back to defaults when the brand kit is incomplete', () => {
    const draft = buildCanvaBridgePresetDraft({
      name: 'Starter Kit',
      colors: [],
      fonts: [],
    });

    expect(draft).toEqual({
      headline: 'Starter Kit',
      caption: 'Brand kit: Starter Kit · Primary color #6366f1 · Font Inter',
      activityMessage: 'Applied Starter Kit to Canva bridge.',
    });
  });

  it('returns null when no brand kit is selected', () => {
    expect(buildCanvaBridgePresetDraft(null)).toBeNull();
    expect(buildCanvaBridgePresetDraft(undefined)).toBeNull();
  });
});
