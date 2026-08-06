import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  loadUgcTemplateProfile,
  normalizeUgcTemplateProfile,
  saveUgcTemplateProfile,
  trackUgcTemplateEvent,
  type UgcTemplateProfile,
} from './ugc-template-profile';

vi.mock('@/app/lib/api-client', () => ({
  DEFAULT_TENANT_ID: 'tenant-demo',
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiGet, apiPut, apiPost } from '@/app/lib/api-client';

const normalizeOptions = {
  categoryIds: ['no-discount-promo', 'travel'],
  templateIdsByCategory: {
    'no-discount-promo': ['tpl-value-story'],
    travel: ['tpl-destination-hook'],
  },
  templateDefaultsById: {
    'tpl-value-story': {
      categoryId: 'no-discount-promo',
      captionPackId: 'ugc-main-launch',
      platform: 'Instagram',
      objective: 'Sales',
      hookStyle: 'Announcement',
      scriptStyle: 'Storytelling',
      aspectRatio: '9:16',
      backgroundMedia: 'AI Videos',
      subtitlesAuto: true,
      subtitlesLanguage: 'Auto (detect)',
    },
    'tpl-destination-hook': {
      categoryId: 'travel',
      captionPackId: 'ugc-social-short',
      platform: 'TikTok',
      objective: 'Engagement',
      hookStyle: 'Announcement',
      scriptStyle: 'Exploratory',
      aspectRatio: '9:16',
      backgroundMedia: 'AI Videos',
      subtitlesAuto: true,
      subtitlesLanguage: 'Auto (detect)',
    },
  },
  allowedCaptionPackIds: ['ugc-main-launch', 'ugc-social-short'],
  allowedPlatforms: ['Instagram', 'TikTok'],
  allowedObjectives: ['Sales', 'Engagement'],
  allowedHookStyles: ['Announcement', 'Question'],
  allowedScriptStyles: ['Storytelling', 'Exploratory'],
  allowedAspectRatios: ['9:16', '16:9'],
  allowedBackgroundMedia: ['AI Videos', 'AI Images'],
  allowedSubtitleLanguages: ['Auto (detect)', 'English', 'Spanish'],
} as const;

describe('ugc-template-profile persistence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('normalizes invalid values to known defaults', () => {
    const normalized = normalizeUgcTemplateProfile(
      {
        style_category_id: 'invalid',
        preview_template_id: 'invalid-template',
        caption_pack_id: 'invalid-pack',
        platform: 'invalid-platform',
        objective: 'invalid-objective',
        hook_style: 'invalid-hook',
        script_style: 'invalid-script',
        aspect_ratio: 'invalid-ratio',
        auto_adjust_platforms: false,
        background_media: 'invalid-media',
        subtitles_auto: false,
        subtitles_language: 'invalid-language',
      },
      normalizeOptions
    );

    expect(normalized.style_category_id).toBe('no-discount-promo');
    expect(normalized.preview_template_id).toBe('tpl-value-story');
    expect(normalized.caption_pack_id).toBe('ugc-main-launch');
    expect(normalized.platform).toBe('Instagram');
    expect(normalized.objective).toBe('Sales');
    expect(normalized.hook_style).toBe('Announcement');
    expect(normalized.script_style).toBe('Storytelling');
    expect(normalized.aspect_ratio).toBe('9:16');
    expect(normalized.auto_adjust_platforms).toBe(false);
    expect(normalized.background_media).toBe('AI Videos');
    expect(normalized.subtitles_auto).toBe(false);
    expect(normalized.subtitles_language).toBe('Auto (detect)');
  });

  it('saves and reloads UGC template profile (reload persistence)', async () => {
    const profile: UgcTemplateProfile = {
      style_category_id: 'travel',
      preview_template_id: 'tpl-destination-hook',
      caption_pack_id: 'ugc-social-short',
      platform: 'TikTok',
      objective: 'Engagement',
      hook_style: 'Announcement',
      script_style: 'Exploratory',
      aspect_ratio: '9:16',
      auto_adjust_platforms: false,
      background_media: 'AI Videos',
      subtitles_auto: true,
      subtitles_language: 'Spanish',
    };

    vi.mocked(apiPut).mockResolvedValue({ status: 'ok' } as never);
    vi.mocked(apiGet).mockResolvedValue({
      status: 'ok',
      brand_profile: {
        ugc_template_profile: profile,
      },
    } as never);

    await saveUgcTemplateProfile(profile, 'tenant-42');
    const loaded = await loadUgcTemplateProfile('tenant-42');

    expect(apiPut).toHaveBeenCalledWith('/social/brand-profile/ugc-template', profile, 'tenant-42');
    expect(apiGet).toHaveBeenCalledWith('/social/brand-profile', 'tenant-42');
    expect(loaded).toEqual(profile);
  });

  it('emits telemetry capture payload', () => {
    vi.mocked(apiPost).mockResolvedValue({ status: 'ok' } as never);

    trackUgcTemplateEvent('ugc_template_applied', 'tenant-42', {
      template_id: 'tpl-value-story',
      category_id: 'no-discount-promo',
    });

    expect(apiPost).toHaveBeenCalledWith(
      '/analytics/posthog/capture',
      {
        event: 'ugc_template_applied',
        distinct_id: 'tenant-42',
        properties: {
          source: 'studio-editor-ugc-template',
          template_id: 'tpl-value-story',
          category_id: 'no-discount-promo',
        },
      },
      'tenant-42'
    );
  });
});
