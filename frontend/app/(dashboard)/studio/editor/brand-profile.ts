import { apiGet, apiPost, apiPut, DEFAULT_TENANT_ID } from '@/app/lib/api-client';

export type SocialBrandProfile = {
  business_name: string;
  industry: string;
  website: string | null;
  description: string | null;
  tone: string;
  logo_url: string | null;
  logo_dark_url: string | null;
  keywords: string[];
  hashtags: string[];
  timezone: string;
  ethnicity: string | null;
  voiceover: string | null;
  avatar_profile: Record<string, unknown>;
  voiceover_engine: Record<string, unknown>;
  ugc_template_profile: Record<string, unknown>;
  brand_colors: string[];
  title_font_family: string;
  subtitle_font_family: string;
  title_font_weight: string;
  subtitle_font_weight: string;
  title_case_type: string;
  subtitle_case_type: string;
  use_custom_font_title: boolean;
  use_custom_font_subtitle: boolean;
  custom_font_title: string | null;
  custom_font_subtitle: string | null;
};

const DEFAULT_BRAND_PROFILE: SocialBrandProfile = {
  business_name: 'Nuxtron Brand Studio',
  industry: 'marketing',
  website: 'https://nuxtron.local',
  description: 'AI-assisted content operations for multi-channel growth teams.',
  tone: 'professional',
  logo_url: null,
  logo_dark_url: null,
  keywords: ['growth', 'content ops'],
  hashtags: ['#growth', '#socialmedia', '#nuxtron'],
  timezone: 'UTC',
  ethnicity: null,
  voiceover: null,
  avatar_profile: {},
  voiceover_engine: {},
  ugc_template_profile: {},
  brand_colors: ['#f8fafc', '#84cc16', '#93c5fd'],
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

function asText(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback;
  const trimmed = value.trim();
  return trimmed || fallback;
}

function asOptionalText(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function asStringArray(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) return fallback;
  const next = value.map((item) => (typeof item === 'string' ? item.trim() : '')).filter(Boolean);
  return next.length ? next : fallback;
}

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function normalizeBrandProfile(source: unknown): SocialBrandProfile {
  const payload = source && typeof source === 'object' ? (source as Record<string, unknown>) : {};
  return {
    business_name: asText(payload.business_name, DEFAULT_BRAND_PROFILE.business_name),
    industry: asText(payload.industry, DEFAULT_BRAND_PROFILE.industry),
    website: asOptionalText(payload.website) ?? DEFAULT_BRAND_PROFILE.website,
    description: asOptionalText(payload.description) ?? DEFAULT_BRAND_PROFILE.description,
    tone: asText(payload.tone, DEFAULT_BRAND_PROFILE.tone),
    logo_url: asOptionalText(payload.logo_url),
    logo_dark_url: asOptionalText(payload.logo_dark_url),
    keywords: asStringArray(payload.keywords, DEFAULT_BRAND_PROFILE.keywords),
    hashtags: asStringArray(payload.hashtags, DEFAULT_BRAND_PROFILE.hashtags),
    timezone: asText(payload.timezone, DEFAULT_BRAND_PROFILE.timezone),
    ethnicity: asOptionalText(payload.ethnicity),
    voiceover: asOptionalText(payload.voiceover),
    avatar_profile: asObject(payload.avatar_profile),
    voiceover_engine: asObject(payload.voiceover_engine),
    ugc_template_profile: asObject(payload.ugc_template_profile),
    brand_colors: asStringArray(payload.brand_colors, DEFAULT_BRAND_PROFILE.brand_colors),
    title_font_family: asText(payload.title_font_family, DEFAULT_BRAND_PROFILE.title_font_family),
    subtitle_font_family: asText(payload.subtitle_font_family, DEFAULT_BRAND_PROFILE.subtitle_font_family),
    title_font_weight: asText(payload.title_font_weight, DEFAULT_BRAND_PROFILE.title_font_weight),
    subtitle_font_weight: asText(payload.subtitle_font_weight, DEFAULT_BRAND_PROFILE.subtitle_font_weight),
    title_case_type: asText(payload.title_case_type, DEFAULT_BRAND_PROFILE.title_case_type),
    subtitle_case_type: asText(payload.subtitle_case_type, DEFAULT_BRAND_PROFILE.subtitle_case_type),
    use_custom_font_title: Boolean(payload.use_custom_font_title),
    use_custom_font_subtitle: Boolean(payload.use_custom_font_subtitle),
    custom_font_title: asOptionalText(payload.custom_font_title),
    custom_font_subtitle: asOptionalText(payload.custom_font_subtitle),
  };
}

export async function loadBrandProfile(tenantId = DEFAULT_TENANT_ID): Promise<SocialBrandProfile> {
  const response = await apiGet('/social/brand-profile', tenantId);
  return normalizeBrandProfile(response.brand_profile);
}

export async function saveBrandProfile(
  profile: SocialBrandProfile,
  tenantId = DEFAULT_TENANT_ID
): Promise<SocialBrandProfile> {
  const response = await apiPut('/social/brand-profile', profile, tenantId);
  return normalizeBrandProfile(response.brand_profile);
}

export async function fetchBrandProfileFromWebsite(
  websiteUrl: string,
  tenantId = DEFAULT_TENANT_ID
): Promise<SocialBrandProfile> {
  const response = await apiPost('/social/brand-profile/fetch-from-website', { website_url: websiteUrl }, tenantId);
  return normalizeBrandProfile(response.brand_profile);
}
