import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchBrandProfileFromWebsite,
  loadBrandProfile,
  normalizeBrandProfile,
  saveBrandProfile,
  type SocialBrandProfile,
} from './brand-profile';

vi.mock('@/app/lib/api-client', () => ({
  DEFAULT_TENANT_ID: 'tenant-demo',
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiGet, apiPut, apiPost } from '@/app/lib/api-client';

describe('brand-profile API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('normalizes sparse payloads with safe defaults', () => {
    const normalized = normalizeBrandProfile({
      business_name: '  ',
      tone: 'bold',
      keywords: [' product ', '', 'launch'],
      hashtags: ['#demo'],
      brand_colors: [],
      timezone: '',
      avatar_profile: null,
    });

    expect(normalized.business_name).toBe('Nuxtron Brand Studio');
    expect(normalized.tone).toBe('bold');
    expect(normalized.keywords).toEqual(['product', 'launch']);
    expect(normalized.hashtags).toEqual(['#demo']);
    expect(normalized.brand_colors).toEqual(['#f8fafc', '#84cc16', '#93c5fd']);
    expect(normalized.timezone).toBe('UTC');
    expect(normalized.avatar_profile).toEqual({});
  });

  it('loads and saves profile through live endpoints', async () => {
    const profile: SocialBrandProfile = {
      business_name: 'Acme Studio',
      industry: 'saas',
      website: 'https://acme.example',
      description: 'Acme brand profile',
      tone: 'confident',
      logo_url: null,
      logo_dark_url: null,
      keywords: ['acme', 'ai'],
      hashtags: ['#acme'],
      timezone: 'UTC',
      ethnicity: null,
      voiceover: null,
      avatar_profile: {},
      voiceover_engine: {},
      ugc_template_profile: {},
      brand_colors: ['#ffffff'],
      title_font_family: 'Hanken Grotesk',
      subtitle_font_family: 'Hanken Grotesk',
      title_font_weight: 'Regular',
      subtitle_font_weight: 'Regular',
      title_case_type: 'Auto',
      subtitle_case_type: 'Auto',
      use_custom_font_title: false,
      use_custom_font_subtitle: false,
      custom_font_title: null,
      custom_font_subtitle: null,
    };

    vi.mocked(apiGet).mockResolvedValue({ status: 'ok', brand_profile: profile });
    vi.mocked(apiPut).mockResolvedValue({ status: 'ok', brand_profile: profile });

    const loaded = await loadBrandProfile('tenant-42');
    const saved = await saveBrandProfile(profile, 'tenant-42');

    expect(apiGet).toHaveBeenCalledWith('/social/brand-profile', 'tenant-42');
    expect(apiPut).toHaveBeenCalledWith('/social/brand-profile', profile, 'tenant-42');
    expect(loaded).toEqual(profile);
    expect(saved).toEqual(profile);
  });

  it('fetches profile from website endpoint', async () => {
    vi.mocked(apiPost).mockResolvedValue({
      status: 'ok',
      brand_profile: {
        business_name: 'Website Brand',
        industry: 'ecommerce',
        website: 'https://shop.example',
        description: 'Fetched from website',
        tone: 'professional',
      },
    });

    const profile = await fetchBrandProfileFromWebsite('https://shop.example', 'tenant-77');

    expect(apiPost).toHaveBeenCalledWith(
      '/social/brand-profile/fetch-from-website',
      { website_url: 'https://shop.example' },
      'tenant-77'
    );
    expect(profile.business_name).toBe('Website Brand');
    expect(profile.website).toBe('https://shop.example');
  });
});
