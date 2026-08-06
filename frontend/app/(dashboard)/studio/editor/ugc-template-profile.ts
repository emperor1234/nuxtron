import { apiGet, apiPost, apiPut, DEFAULT_TENANT_ID } from '@/app/lib/api-client';

export type UgcTemplateProfile = {
  style_category_id: string;
  preview_template_id: string;
  caption_pack_id: string;
  platform: string;
  objective: string;
  hook_style: string;
  script_style: string;
  aspect_ratio: string;
  auto_adjust_platforms: boolean;
  background_media: string;
  subtitles_auto: boolean;
  subtitles_language: string;
};

function asStringValue(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback;
  const trimmed = value.trim();
  return trimmed || fallback;
}

function hasValue<T extends string>(allowed: readonly T[], input: string): input is T {
  return allowed.includes(input as T);
}

export function normalizeUgcTemplateProfile(
  source: unknown,
  options: {
    categoryIds: readonly string[];
    templateIdsByCategory: Record<string, readonly string[]>;
    templateDefaultsById: Record<
      string,
      {
        categoryId: string;
        captionPackId: string;
        platform: string;
        objective: string;
        hookStyle: string;
        scriptStyle: string;
        aspectRatio: string;
        backgroundMedia: string;
        subtitlesAuto: boolean;
        subtitlesLanguage: string;
      }
    >;
    allowedCaptionPackIds: readonly string[];
    allowedPlatforms: readonly string[];
    allowedObjectives: readonly string[];
    allowedHookStyles: readonly string[];
    allowedScriptStyles: readonly string[];
    allowedAspectRatios: readonly string[];
    allowedBackgroundMedia: readonly string[];
    allowedSubtitleLanguages: readonly string[];
  }
): UgcTemplateProfile {
  const payload = source && typeof source === 'object' ? (source as Record<string, unknown>) : {};

  const fallbackCategoryId = options.categoryIds[0] ?? 'no-discount-promo';
  const categoryIdRaw = asStringValue(payload.style_category_id, fallbackCategoryId);
  const styleCategoryId = options.categoryIds.includes(categoryIdRaw) ? categoryIdRaw : fallbackCategoryId;

  const templateIds = options.templateIdsByCategory[styleCategoryId] ?? [];
  const firstTemplateId = templateIds[0] ?? Object.keys(options.templateDefaultsById)[0] ?? 'tpl-value-story';
  const previewTemplateRaw = asStringValue(payload.preview_template_id, firstTemplateId);
  const previewTemplateId = templateIds.includes(previewTemplateRaw) ? previewTemplateRaw : firstTemplateId;

  const templateDefaults = options.templateDefaultsById[previewTemplateId] ??
    options.templateDefaultsById[firstTemplateId] ?? {
      categoryId: styleCategoryId,
      captionPackId: options.allowedCaptionPackIds[0] ?? 'ugc-main-launch',
      platform: options.allowedPlatforms[0] ?? 'Instagram',
      objective: options.allowedObjectives[0] ?? 'Sales',
      hookStyle: options.allowedHookStyles[0] ?? 'Announcement',
      scriptStyle: options.allowedScriptStyles[0] ?? 'Storytelling',
      aspectRatio: options.allowedAspectRatios[0] ?? '9:16',
      backgroundMedia: options.allowedBackgroundMedia[0] ?? 'AI Videos',
      subtitlesAuto: true,
      subtitlesLanguage: options.allowedSubtitleLanguages[0] ?? 'Auto (detect)',
    };

  const captionPackRaw = asStringValue(payload.caption_pack_id, templateDefaults.captionPackId);
  const captionPackId = hasValue(options.allowedCaptionPackIds, captionPackRaw)
    ? captionPackRaw
    : templateDefaults.captionPackId;

  const platformRaw = asStringValue(payload.platform, templateDefaults.platform);
  const platform = hasValue(options.allowedPlatforms, platformRaw) ? platformRaw : templateDefaults.platform;

  const objectiveRaw = asStringValue(payload.objective, templateDefaults.objective);
  const objective = hasValue(options.allowedObjectives, objectiveRaw) ? objectiveRaw : templateDefaults.objective;

  const hookStyleRaw = asStringValue(payload.hook_style, templateDefaults.hookStyle);
  const hookStyle = hasValue(options.allowedHookStyles, hookStyleRaw) ? hookStyleRaw : templateDefaults.hookStyle;

  const scriptStyleRaw = asStringValue(payload.script_style, templateDefaults.scriptStyle);
  const scriptStyle = hasValue(options.allowedScriptStyles, scriptStyleRaw)
    ? scriptStyleRaw
    : templateDefaults.scriptStyle;

  const aspectRatioRaw = asStringValue(payload.aspect_ratio, templateDefaults.aspectRatio);
  const aspectRatio = hasValue(options.allowedAspectRatios, aspectRatioRaw)
    ? aspectRatioRaw
    : templateDefaults.aspectRatio;

  const backgroundMediaRaw = asStringValue(payload.background_media, templateDefaults.backgroundMedia);
  const backgroundMedia = hasValue(options.allowedBackgroundMedia, backgroundMediaRaw)
    ? backgroundMediaRaw
    : templateDefaults.backgroundMedia;

  const subtitlesLanguageRaw = asStringValue(payload.subtitles_language, templateDefaults.subtitlesLanguage);
  const subtitlesLanguage = hasValue(options.allowedSubtitleLanguages, subtitlesLanguageRaw)
    ? subtitlesLanguageRaw
    : templateDefaults.subtitlesLanguage;

  return {
    style_category_id: styleCategoryId,
    preview_template_id: previewTemplateId,
    caption_pack_id: captionPackId,
    platform,
    objective,
    hook_style: hookStyle,
    script_style: scriptStyle,
    aspect_ratio: aspectRatio,
    auto_adjust_platforms: Boolean(payload.auto_adjust_platforms ?? true),
    background_media: backgroundMedia,
    subtitles_auto: Boolean(payload.subtitles_auto ?? templateDefaults.subtitlesAuto),
    subtitles_language: subtitlesLanguage,
  };
}

export async function loadUgcTemplateProfile(tenantId = DEFAULT_TENANT_ID): Promise<unknown> {
  const response = await apiGet('/social/brand-profile', tenantId);
  const profile = (response.brand_profile as Record<string, unknown> | undefined) ?? {};
  return profile.ugc_template_profile ?? null;
}

export async function saveUgcTemplateProfile(payload: UgcTemplateProfile, tenantId = DEFAULT_TENANT_ID): Promise<void> {
  await apiPut('/social/brand-profile/ugc-template', payload as unknown as Record<string, unknown>, tenantId);
}

export function trackUgcTemplateEvent(
  eventName: string,
  tenantId = DEFAULT_TENANT_ID,
  properties: Record<string, unknown> = {}
): void {
  void apiPost(
    '/analytics/posthog/capture',
    {
      event: eventName,
      distinct_id: tenantId,
      properties: {
        source: 'studio-editor-ugc-template',
        ...properties,
      },
    },
    tenantId
  ).catch(() => undefined);
}
