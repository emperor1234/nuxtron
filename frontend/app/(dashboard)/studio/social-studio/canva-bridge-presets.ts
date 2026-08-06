type BrandKitLike = {
  name: string;
  colors?: Array<{ hex?: string }>;
  fonts?: Array<{ name?: string }>;
};

export type CanvaBridgePresetDraft = {
  headline: string;
  caption: string;
  activityMessage: string;
};

export function buildCanvaBridgePresetDraft(
  activeBrandKit: BrandKitLike | null | undefined
): CanvaBridgePresetDraft | null {
  if (!activeBrandKit) {
    return null;
  }

  const primaryColor = activeBrandKit.colors?.[0]?.hex || '#6366f1';
  const primaryFont = activeBrandKit.fonts?.[0]?.name || 'Inter';

  return {
    headline: activeBrandKit.name,
    caption: `Brand kit: ${activeBrandKit.name} · Primary color ${primaryColor} · Font ${primaryFont}`,
    activityMessage: `Applied ${activeBrandKit.name} to Canva bridge.`,
  };
}
