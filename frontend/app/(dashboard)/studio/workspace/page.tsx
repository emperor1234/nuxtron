'use client';

import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type Dispatch,
  type DragEvent,
  type KeyboardEvent,
  type SetStateAction,
} from 'react';

import { resolveSessionTenant, apiDelete, apiGet, apiPatch, apiPost, apiPut } from '@/app/lib/api-client';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type WorkspaceTab = 'manager' | 'social' | 'brand' | 'engagement' | 'competitors' | 'autopost' | 'notifications';

function isWorkspaceTab(value: string | null): value is WorkspaceTab {
  return (
    value === 'manager' ||
    value === 'social' ||
    value === 'brand' ||
    value === 'engagement' ||
    value === 'competitors' ||
    value === 'autopost' ||
    value === 'notifications'
  );
}

type Provider = {
  network: string;
  label: string;
  supported_formats: string[];
};

type SocialAccount = {
  id: number;
  network: string;
  network_label: string;
  account_name: string;
  handle: string;
  account_type: string;
  website?: string;
  description: string;
  oauth_status: string;
  capabilities: string[];
  followers: number;
  likes: number;
  shares: number;
  comments: number;
  mentions: number;
  connected_at: string;
};

type BrandProfile = {
  business_name: string;
  industry: string;
  website?: string;
  logo_url?: string;
  logo_dark_url?: string;
  description?: string;
  tone: string;
  keywords: string[];
  hashtags: string[];
  timezone: string;
  ethnicity?: string;
  voiceover?: string;
  avatar_profile?: AvatarProfile;
  voiceover_engine?: VoiceoverEngine;
  brand_colors: string[];
  title_font_family: string;
  subtitle_font_family: string;
  title_font_weight: string;
  subtitle_font_weight: string;
  title_case_type: string;
  subtitle_case_type: string;
  use_custom_font_title: boolean;
  use_custom_font_subtitle: boolean;
  custom_font_title?: string;
  custom_font_subtitle?: string;
};

type AvatarProfile = {
  mode: 'catalog' | 'custom' | 'scratch';
  preset_id?: string;
  name: string;
  location?: string;
  ethnicity?: string;
  gender?: string;
  age_range?: string;
  style?: string;
  face_type?: string;
  eye_style?: string;
  body_shape?: string;
  body_proportions?: string;
};

type VoiceoverEngine = {
  language: string;
  voice_name?: string;
  style: string;
  tone: string;
  accent: string;
  use_case: string;
};

const TONALITY_OPTIONS = [
  'professional',
  'informal',
  'friendly',
  'enthusiastic',
  'humorous',
  'inspirational',
  'persuasive',
  'bold',
];
const ETHNICITY_OPTIONS = [
  'Global / Generic',
  'South Asian',
  'East Asian',
  'African',
  'Middle Eastern',
  'European',
  'Latin American',
];
const FONT_FAMILY_OPTIONS = ['Hanken Grotesk', 'Sora', 'Manrope', 'Space Grotesk', 'Abeezee', 'Abel', 'Ar One Sans'];
const FONT_WEIGHT_OPTIONS = ['Light', 'Regular', 'Medium', 'Semi Bold', 'Bold'];
const CASE_TYPE_OPTIONS = ['Auto', 'Sentence', 'Title', 'Uppercase', 'Lowercase'];

type VoiceoverOption = {
  name: string;
  gender: 'male' | 'female';
  language: string;
  accent: string;
  style: string;
  tone: string;
  premium: boolean;
};

type AvatarPreset = {
  id: string;
  name: string;
  ethnicity: string;
  gender: string;
  age_range: string;
  style: string;
  face_type: string;
  eye_style: string;
  body_shape: string;
  body_proportions: string;
  location: string;
};

const AVATAR_PRESET_CATALOG: AvatarPreset[] = [
  {
    id: 'ava-creator-01',
    name: 'Mila Harper',
    ethnicity: 'European',
    gender: 'female',
    age_range: '25-34',
    style: 'Modern Casual',
    face_type: 'Oval',
    eye_style: 'Almond',
    body_shape: 'Athletic',
    body_proportions: 'Balanced',
    location: 'New York, US',
  },
  {
    id: 'ava-creator-02',
    name: 'Arjun Mehta',
    ethnicity: 'Indian',
    gender: 'male',
    age_range: '25-34',
    style: 'Business Casual',
    face_type: 'Square',
    eye_style: 'Deep Set',
    body_shape: 'Lean',
    body_proportions: 'Balanced',
    location: 'Mumbai, IN',
  },
  {
    id: 'ava-creator-03',
    name: 'Aiko Tanaka',
    ethnicity: 'East Asian',
    gender: 'female',
    age_range: '18-24',
    style: 'Streetwear',
    face_type: 'Heart',
    eye_style: 'Monolid',
    body_shape: 'Slim',
    body_proportions: 'Long Torso',
    location: 'Tokyo, JP',
  },
  {
    id: 'ava-creator-04',
    name: 'Kwame Nkrumah',
    ethnicity: 'African',
    gender: 'male',
    age_range: '35-44',
    style: 'Minimal Premium',
    face_type: 'Round',
    eye_style: 'Hooded',
    body_shape: 'Muscular',
    body_proportions: 'Broad Shoulders',
    location: 'Accra, GH',
  },
  {
    id: 'ava-creator-05',
    name: 'Lina Haddad',
    ethnicity: 'Middle Eastern',
    gender: 'female',
    age_range: '25-34',
    style: 'Editorial',
    face_type: 'Diamond',
    eye_style: 'Round',
    body_shape: 'Curvy',
    body_proportions: 'Balanced',
    location: 'Dubai, AE',
  },
  {
    id: 'ava-creator-06',
    name: 'Sofia Reyes',
    ethnicity: 'Latin American',
    gender: 'female',
    age_range: '25-34',
    style: 'Creator Chic',
    face_type: 'Oval',
    eye_style: 'Almond',
    body_shape: 'Petite',
    body_proportions: 'Long Legs',
    location: 'Mexico City, MX',
  },
];

const VOICEOVER_CATALOG: VoiceoverOption[] = [
  {
    name: 'Liam',
    gender: 'male',
    language: 'English',
    accent: 'US',
    style: 'Narration',
    tone: 'Confident',
    premium: true,
  },
  {
    name: 'Layla',
    gender: 'female',
    language: 'English',
    accent: 'US',
    style: 'Presentation',
    tone: 'Warm',
    premium: true,
  },
  {
    name: 'Ethan',
    gender: 'male',
    language: 'English',
    accent: 'US',
    style: 'Tutorial',
    tone: 'Professional',
    premium: true,
  },
  {
    name: 'Adrian',
    gender: 'male',
    language: 'English',
    accent: 'UK',
    style: 'Narration',
    tone: 'Neutral',
    premium: false,
  },
  {
    name: 'Maya',
    gender: 'female',
    language: 'English',
    accent: 'AU',
    style: 'Character',
    tone: 'Playful',
    premium: false,
  },
  {
    name: 'Aarav',
    gender: 'male',
    language: 'English',
    accent: 'IN',
    style: 'Narration',
    tone: 'Calm',
    premium: false,
  },
  {
    name: 'Isabella',
    gender: 'female',
    language: 'Spanish',
    accent: 'MX',
    style: 'Presentation',
    tone: 'Energetic',
    premium: true,
  },
  { name: 'Noah', gender: 'male', language: 'French', accent: 'FR', style: 'Tutorial', tone: 'Neutral', premium: true },
  {
    name: 'Yuki',
    gender: 'female',
    language: 'Japanese',
    accent: 'JP',
    style: 'Narration',
    tone: 'Soft',
    premium: true,
  },
];

const AVATAR_MODE_OPTIONS: AvatarProfile['mode'][] = ['catalog', 'custom', 'scratch'];
const AVATAR_GENDER_OPTIONS = ['female', 'male', 'non-binary'];
const AVATAR_AGE_OPTIONS = ['18-24', '25-34', '35-44', '45-54', '55+'];
const VOICE_STYLE_OPTIONS = ['Narration', 'Presentation', 'Tutorial', 'Character'];
const VOICE_TONE_OPTIONS = ['Professional', 'Confident', 'Warm', 'Energetic', 'Calm', 'Playful'];
const VOICE_USE_CASE_OPTIONS = ['Narration', 'Presentation', 'Tutorial', 'Character Dialogue'];

function defaultAvatarProfile(): AvatarProfile {
  const firstPreset = AVATAR_PRESET_CATALOG[0];
  return {
    mode: 'catalog',
    preset_id: firstPreset.id,
    name: firstPreset.name,
    location: firstPreset.location,
    ethnicity: firstPreset.ethnicity,
    gender: firstPreset.gender,
    age_range: firstPreset.age_range,
    style: firstPreset.style,
    face_type: firstPreset.face_type,
    eye_style: firstPreset.eye_style,
    body_shape: firstPreset.body_shape,
    body_proportions: firstPreset.body_proportions,
  };
}

function defaultVoiceoverEngine(): VoiceoverEngine {
  const firstVoice = VOICEOVER_CATALOG[0];
  return {
    language: firstVoice.language,
    voice_name: firstVoice.name,
    style: firstVoice.style,
    tone: firstVoice.tone,
    accent: firstVoice.accent,
    use_case: 'Narration',
  };
}

type Overview = {
  connected_accounts: number;
  networks_connected: number;
  inbox_open: number;
  notifications_unread: number;
  competitors_tracked: number;
  competitor_snapshots: number;
  scheduled_posts: number;
  engagement_total: number;
};

type InboxStats = {
  total: number;
  unread: number;
  replied: number;
  replyRate: number;
  avgPriorityScore: number;
  byNetwork: Record<string, number>;
  bySentiment: Record<string, number>;
};

type InboxMessage = {
  id: number;
  network: string;
  source_type: string;
  author_handle: string;
  text: string;
  sentiment: string;
  priority_score: number;
  status: string;
  suggested_replies: string[];
  replied: boolean;
};

type CompetitorEntry = {
  profile: {
    id: number;
    name: string;
    network: string;
    handle: string;
  };
  latest_snapshot?: {
    followers: number;
    engagement_rate: number;
    estimated_mentions: number;
  };
  vs_own?: {
    followers_delta: number;
    engagement_rate_delta: number;
    ahead: boolean;
  };
};

type CompetitorReport = {
  own_brand?: {
    followers: number;
    engagement_rate: number;
    estimated_mentions: number;
  };
  competitors: CompetitorEntry[];
  competitor_count: number;
};

type ShareOfVoice = {
  total_estimated_mentions: number;
  breakdown: Array<{
    brand: string;
    estimated_mentions: number;
    share_pct: number;
  }>;
};

type NotificationItem = {
  id: number;
  title: string;
  message: string;
  category: string;
  priority: string;
  read: boolean;
  created_at: string;
};

type AutopostPreview = {
  account_id: number;
  network: string;
  aspect_ratio: string;
  headline: string;
  caption: string;
  description: string;
  hashtags: string[];
  keywords: string[];
  recommended_publish_at: string;
  supported_formats: string[];
};

type ListeningSummary = {
  total_mentions: number;
  avg_engagement: number;
  alerts_open: number;
  top_queries: Array<{ query: string; mentions: number }>;
  crisis: {
    triggered: boolean;
    level: string;
    negative_ratio: number;
  };
};

type ListeningAlert = {
  id: number;
  title?: string;
  message?: string;
  status?: string;
  created_at?: string;
};

type TrendForecast = {
  trend_id: string;
  topic: string;
  phase: string;
  roi_score: number;
  trend_strength: number;
  best_platform?: string;
};

type TrendRecommendation = {
  trend_id: string;
  topic: string;
  phase: string;
  priority: string;
  roi_score: number;
  recommendations: string[];
};

type TrendDashboard = {
  summary?: {
    tracked_trends?: number;
    tracked_posts_ads?: number;
    totals?: {
      revenue?: number;
      spend?: number;
    };
  };
  kpi?: {
    trend_strength_kpi?: number;
    roi_kpi?: number;
    conversion_efficiency_kpi?: number;
  };
  graphs?: {
    achievable_projection?: {
      target_revenue?: number;
    };
  };
};

type ScheduledPost = {
  id: number;
  platform: string;
  text: string;
  publish_at: string;
  status: string;
  headline?: string;
};

type CreativeStep = 1 | 2 | 3;
type CreativePostType = 'ad' | 'highlights' | 'before_after' | 'review';
type LibraryFilter = 'all' | 'image' | 'video' | 'carousel';

type ContentLibraryItem = {
  id: string;
  title: string;
  subtitle: string;
  cta: string;
  caption: string;
  imageUrl: string;
  postType: CreativePostType;
  aspectRatio: string;
  status: 'generating' | 'ready';
  createdAt: string;
};

const DISPLAY_LOCALE = 'en-US';
const DISPLAY_TIME_ZONE = 'UTC';
const COMPACT_NUMBER_FORMATTER = new Intl.NumberFormat(DISPLAY_LOCALE, {
  notation: 'compact',
  maximumFractionDigits: 1,
});
const USD_CURRENCY_FORMATTER = new Intl.NumberFormat(DISPLAY_LOCALE, {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

function formatCompactNumber(value: number) {
  return COMPACT_NUMBER_FORMATTER.format(value);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatAge(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return 'just now';
  const minutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatMoney(value: number) {
  return USD_CURRENCY_FORMATTER.format(value);
}

function toDatetimeLocalValue(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '';
  const date = new Date(timestamp);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function formatClock(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '--:--';
  return new Date(timestamp).toLocaleTimeString(DISPLAY_LOCALE, {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: DISPLAY_TIME_ZONE,
  });
}

function scheduleDayKey(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '';
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatScheduleDayLabel(dayKey: string) {
  const date = new Date(`${dayKey}T12:00:00`);
  return date.toLocaleDateString(DISPLAY_LOCALE, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: DISPLAY_TIME_ZONE,
  });
}

function formatDateTime(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '--';
  return new Date(timestamp).toLocaleString(DISPLAY_LOCALE, { timeZone: DISPLAY_TIME_ZONE });
}

function mergeScheduleDayAndTime(dayKey: string, timeValue: string) {
  if (!dayKey || !timeValue) return '';
  const next = new Date(`${dayKey}T${timeValue}:00`);
  if (Number.isNaN(next.getTime())) return '';
  return next.toISOString();
}

function formatTimeValue(hours: number, minutes: number) {
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

function timeInputValue(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '09:06';
  const date = new Date(timestamp);
  return formatTimeValue(date.getHours(), date.getMinutes());
}

function buildHumanizedTimeChoices(baseValue: string) {
  const timestamp = Date.parse(baseValue);
  if (Number.isNaN(timestamp)) return [] as Array<{ label: string; value: string }>;
  const base = new Date(timestamp);
  return [6, 12, 18, 27, 34, 41, 48, 57]
    .map((minute) => {
      const option = new Date(base);
      option.setMinutes(minute, 0, 0);
      const value = toDatetimeLocalValue(option.toISOString());
      return { label: formatClock(option.toISOString()), value };
    })
    .filter((item, index, array) => array.findIndex((candidate) => candidate.value === item.value) === index)
    .slice(0, 5);
}

function scheduleMinuteChoices(value: string) {
  const timestamp = Date.parse(value);
  const date = Number.isNaN(timestamp) ? new Date() : new Date(timestamp);
  return [6, 18, 27, 41, 57].map((minute) => formatTimeValue(date.getHours(), minute));
}

function businessSetupScore(profile: BrandProfile, connectedChannels: number) {
  const checks = [
    Boolean(profile.business_name.trim()),
    Boolean(profile.website?.trim()),
    Boolean(profile.description?.trim()),
    profile.keywords.length > 0,
    profile.hashtags.length > 0,
    Boolean(profile.avatar_profile?.name?.trim()),
    Boolean(profile.voiceover_engine?.voice_name?.trim()),
    connectedChannels > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function settledData<T>(
  result: PromiseSettledResult<Record<string, unknown>>,
  selector: (value: Record<string, unknown>) => T,
  fallback: T
): T {
  if (result.status !== 'fulfilled') return fallback;
  try {
    return selector(result.value);
  } catch {
    return fallback;
  }
}

function providerHint(network: string) {
  if (network === 'instagram') return 'Business or Creator accounts';
  if (network === 'facebook') return 'Pages';
  if (network === 'linkedin') return 'Personal and Company profiles';
  if (network === 'youtube') return 'Channels and Brand accounts';
  return 'Business accounts';
}

function makeCreativePreview(title: string, subtitle: string, cta: string) {
  const safeTitle = title.slice(0, 44) || 'Campaign Creative';
  const safeSubtitle = subtitle.slice(0, 48) || 'Limited Time Offer';
  const safeCta = cta.slice(0, 18) || 'Shop Now';
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1080 1080'>
    <defs>
      <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
        <stop offset='0%' stop-color='#eef0f4' />
        <stop offset='55%' stop-color='#eef0f4' />
        <stop offset='100%' stop-color='#eef0f4' />
      </linearGradient>
      <radialGradient id='glowA' cx='0.2' cy='0.2' r='0.45'>
        <stop offset='0%' stop-color='#f59e0b' stop-opacity='0.75' />
        <stop offset='100%' stop-color='#f59e0b' stop-opacity='0' />
      </radialGradient>
      <radialGradient id='glowB' cx='0.82' cy='0.78' r='0.45'>
        <stop offset='0%' stop-color='#ec4899' stop-opacity='0.72' />
        <stop offset='100%' stop-color='#ec4899' stop-opacity='0' />
      </radialGradient>
    </defs>
    <rect width='1080' height='1080' fill='url(#bg)' />
    <rect width='1080' height='1080' fill='url(#glowA)' />
    <rect width='1080' height='1080' fill='url(#glowB)' />
    <text x='84' y='178' fill='var(--text)' font-size='106' font-family='Arial, Helvetica, sans-serif' font-weight='800'>${safeTitle}</text>
    <text x='84' y='250' fill='var(--text)' font-size='56' font-family='Arial, Helvetica, sans-serif'>${safeSubtitle}</text>
    <rect x='740' y='938' width='250' height='82' rx='40' fill='#e11d48' />
    <text x='820' y='994' text-anchor='middle' fill='#ffffff' font-size='42' font-family='Arial, Helvetica, sans-serif' font-weight='700'>${safeCta}</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function initials(value: string) {
  const chunks = value.replaceAll('_', ' ').replaceAll('-', ' ').split(/\s+/).filter(Boolean).slice(0, 2);
  if (!chunks.length) return 'NA';
  return chunks.map((chunk) => chunk[0]?.toUpperCase() ?? '').join('');
}

function creativeStepLabel(step: CreativeStep) {
  if (step === 1) return 'Create Image';
  if (step === 2) return 'Configure your Image';
  return 'Review details';
}

function avatarCreatorDisplay(profile: BrandProfile['avatar_profile']) {
  const name = profile?.name || 'Creator';
  const location = profile?.location ? ` (${profile.location})` : '';
  return `${name}${location}`;
}

function markGeneratedCreativeReady(item: ContentLibraryItem, cardId: string): ContentLibraryItem {
  if (item.id !== cardId) return item;
  return {
    ...item,
    status: 'ready',
    caption: `${item.caption} Publish to start distribution across connected channels.`,
  };
}

function applySuggestedReplyDraft(
  setReplyDrafts: Dispatch<SetStateAction<Record<string, string>>>,
  messageId: number,
  reply: string
) {
  setReplyDrafts((current) => ({ ...current, [messageId]: reply }));
}

function finalizeGeneratedCreative(setContentLibrary: Dispatch<SetStateAction<ContentLibraryItem[]>>, cardId: string) {
  setContentLibrary((current) => current.map((item) => markGeneratedCreativeReady(item, cardId)));
}

async function fileToDataUrl(file: File): Promise<string> {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      resolve(result);
    };
    reader.onerror = () => reject(new Error('Unable to read selected file.'));
    reader.readAsDataURL(file);
  });
}

export default function StudioWorkspacePage() {
  // NOSONAR
  const [tenantId] = useState(resolveSessionTenant);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('manager');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [brandProfile, setBrandProfile] = useState<BrandProfile>({
    business_name: '',
    industry: 'marketing',
    website: '',
    logo_url: '',
    logo_dark_url: '',
    description: '',
    tone: 'professional',
    keywords: [],
    hashtags: [],
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    ethnicity: 'Global / Generic',
    voiceover: '',
    avatar_profile: defaultAvatarProfile(),
    voiceover_engine: defaultVoiceoverEngine(),
    brand_colors: ['var(--text)', '#84cc16', 'var(--brand)'],
    title_font_family: 'Hanken Grotesk',
    subtitle_font_family: 'Hanken Grotesk',
    title_font_weight: 'Regular',
    subtitle_font_weight: 'Regular',
    title_case_type: 'Auto',
    subtitle_case_type: 'Auto',
    use_custom_font_title: false,
    use_custom_font_subtitle: false,
    custom_font_title: '',
    custom_font_subtitle: '',
  });
  const [overview, setOverview] = useState<Overview | null>(null);
  const [inboxStats, setInboxStats] = useState<InboxStats | null>(null);
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [competitorReport, setCompetitorReport] = useState<CompetitorReport | null>(null);
  const [shareOfVoice, setShareOfVoice] = useState<ShareOfVoice | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [preview, setPreview] = useState<AutopostPreview | null>(null);
  const [listeningSummary, setListeningSummary] = useState<ListeningSummary | null>(null);
  const [listeningAlerts, setListeningAlerts] = useState<ListeningAlert[]>([]);
  const [trendDashboard, setTrendDashboard] = useState<TrendDashboard | null>(null);
  const [trendForecasts, setTrendForecasts] = useState<TrendForecast[]>([]);
  const [trendRecommendations, setTrendRecommendations] = useState<TrendRecommendation[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [lastPublished, setLastPublished] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({});
  const [competitorForm, setCompetitorForm] = useState({ name: '', network: 'instagram', handle: '', profile_url: '' });
  const [autopostForm, setAutopostForm] = useState({
    account_id: 0,
    content_type: 'image',
    headline: '',
    caption: '',
    media_urls: '',
    publish_at: '',
  });
  const [isFetchWebsiteModalOpen, setIsFetchWebsiteModalOpen] = useState(false);
  const [websiteDraft, setWebsiteDraft] = useState('');
  const [isFetchingWebsite, setIsFetchingWebsite] = useState(false);
  const [isSavingBrand, setIsSavingBrand] = useState(false);
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  const [avatarSearch, setAvatarSearch] = useState('');
  const [avatarEthnicityFilter, setAvatarEthnicityFilter] = useState('All');
  const [isVoiceoverModalOpen, setIsVoiceoverModalOpen] = useState(false);
  const [voiceoverSearch, setVoiceoverSearch] = useState('');
  const [voiceoverGender, setVoiceoverGender] = useState<'all' | 'male' | 'female'>('all');
  const [voiceoverLanguage, setVoiceoverLanguage] = useState('All');
  const [voiceoverStyle, setVoiceoverStyle] = useState('All');
  const [voiceoverTone, setVoiceoverTone] = useState('All');
  const [voiceoverAccent, setVoiceoverAccent] = useState('All');
  const [showPremiumVoiceovers, setShowPremiumVoiceovers] = useState(true);
  const [creativeStep, setCreativeStep] = useState<CreativeStep>(1);
  const [creativeIdea, setCreativeIdea] = useState('');
  const [creativeReferenceImage, setCreativeReferenceImage] = useState('');
  const [creativeReferenceName, setCreativeReferenceName] = useState('');
  const [creativePostType, setCreativePostType] = useState<CreativePostType>('ad');
  const [creativeAspectRatio, setCreativeAspectRatio] = useState('1:1');
  const [creativeLibraryFilter, setCreativeLibraryFilter] = useState<LibraryFilter>('all');
  const [isCreativeGenerating, setIsCreativeGenerating] = useState(false);
  const [contentLibrary, setContentLibrary] = useState<ContentLibraryItem[]>([]);
  const [selectedLibraryId, setSelectedLibraryId] = useState('');
  const [draggingScheduledId, setDraggingScheduledId] = useState<number | null>(null);

  const accountsByNetwork = useMemo(() => {
    const byNetwork: Record<string, SocialAccount[]> = {};
    for (const account of accounts) {
      if (!byNetwork[account.network]) byNetwork[account.network] = [];
      byNetwork[account.network].push(account);
    }
    return byNetwork;
  }, [accounts]);
  const connectedChannelCount = useMemo(
    () => providers.filter((provider) => (accountsByNetwork[provider.network] ?? []).length > 0).length,
    [providers, accountsByNetwork]
  );
  const totalReach = useMemo(
    () =>
      accounts.reduce((sum, account) => sum + account.followers + account.likes + account.shares + account.comments, 0),
    [accounts]
  );
  const setupScore = useMemo(
    () => businessSetupScore(brandProfile, connectedChannelCount),
    [brandProfile, connectedChannelCount]
  );
  const scheduleBoardDays = useMemo(() => {
    return Array.from({ length: 5 }, (_, index) => {
      const date = new Date();
      date.setHours(12, 0, 0, 0);
      date.setDate(date.getDate() + index);
      const dayKey = scheduleDayKey(date.toISOString());
      return {
        dayKey,
        label: formatScheduleDayLabel(dayKey),
        items: scheduledPosts.filter((item) => scheduleDayKey(item.publish_at) === dayKey),
      };
    });
  }, [scheduledPosts]);
  const humanizedScheduleChoices = useMemo(
    () => buildHumanizedTimeChoices(autopostForm.publish_at || preview?.recommended_publish_at || ''),
    [autopostForm.publish_at, preview?.recommended_publish_at]
  );

  useEffect(() => {
    if (!globalThis.window) return;
    const tabParam = new URLSearchParams(globalThis.window.location.search).get('tab');
    if (isWorkspaceTab(tabParam)) {
      setActiveTab(tabParam);
    }
  }, []);

  function updateBrandColor(colorIndex: number, value: string) {
    setBrandProfile((current) => ({
      ...current,
      brand_colors: current.brand_colors.map((item, index) => (index === colorIndex ? value : item)),
    }));
  }

  function addBrandPaletteColor() {
    setBrandProfile((current) => ({
      ...current,
      brand_colors: current.brand_colors.length >= 12 ? current.brand_colors : [...current.brand_colors, '#6366f1'],
    }));
  }

  const filteredAvatars = useMemo(() => {
    const keyword = avatarSearch.trim().toLowerCase();
    return AVATAR_PRESET_CATALOG.filter((avatar) => {
      if (avatarEthnicityFilter !== 'All' && avatar.ethnicity !== avatarEthnicityFilter) return false;
      if (
        keyword &&
        !`${avatar.name} ${avatar.ethnicity} ${avatar.style} ${avatar.location}`.toLowerCase().includes(keyword)
      ) {
        return false;
      }
      return true;
    });
  }, [avatarEthnicityFilter, avatarSearch]);

  const filteredVoiceovers = useMemo(() => {
    const keyword = voiceoverSearch.trim().toLowerCase();
    return VOICEOVER_CATALOG.filter((voice) => {
      if (voiceoverGender !== 'all' && voice.gender !== voiceoverGender) return false;
      if (voiceoverLanguage !== 'All' && voice.language !== voiceoverLanguage) return false;
      if (voiceoverStyle !== 'All' && voice.style !== voiceoverStyle) return false;
      if (voiceoverTone !== 'All' && voice.tone !== voiceoverTone) return false;
      if (voiceoverAccent !== 'All' && voice.accent !== voiceoverAccent) return false;
      if (!showPremiumVoiceovers && voice.premium) return false;
      if (
        keyword &&
        !`${voice.name} ${voice.language} ${voice.accent} ${voice.style} ${voice.tone}`.toLowerCase().includes(keyword)
      ) {
        return false;
      }
      return true;
    });
  }, [
    showPremiumVoiceovers,
    voiceoverAccent,
    voiceoverGender,
    voiceoverLanguage,
    voiceoverSearch,
    voiceoverStyle,
    voiceoverTone,
  ]);

  function applyAvatarPreset(preset: AvatarPreset) {
    setBrandProfile((current) => ({
      ...current,
      ethnicity: preset.ethnicity,
      avatar_profile: {
        mode: 'catalog',
        preset_id: preset.id,
        name: preset.name,
        location: preset.location,
        ethnicity: preset.ethnicity,
        gender: preset.gender,
        age_range: preset.age_range,
        style: preset.style,
        face_type: preset.face_type,
        eye_style: preset.eye_style,
        body_shape: preset.body_shape,
        body_proportions: preset.body_proportions,
      },
    }));
  }

  function selectVoiceover(voice: VoiceoverOption) {
    setBrandProfile((current) => ({
      ...current,
      voiceover: voice.name,
      voiceover_engine: {
        language: voice.language,
        voice_name: voice.name,
        style: voice.style,
        tone: voice.tone,
        accent: voice.accent,
        use_case: current.voiceover_engine?.use_case ?? 'Narration',
      },
    }));
  }

  const creativeIdeas = useMemo(
    () => [
      'Design a bold Black Friday hoodie sale visual with urgency-led CTA.',
      'Create a clean product-first post announcing the launch of a new ecommerce store.',
      'Build an ad visual highlighting limited-time discounts and fast shipping.',
      'Generate a modern sale announcement with headline, subheading, and shop-now button.',
    ],
    []
  );

  const selectedLibraryItem = useMemo(
    () => contentLibrary.find((item) => item.id === selectedLibraryId) ?? null,
    [contentLibrary, selectedLibraryId]
  );

  const visibleLibraryItems = useMemo(() => {
    if (creativeLibraryFilter === 'all') return contentLibrary;
    if (creativeLibraryFilter === 'image') return contentLibrary.filter((item) => item.aspectRatio !== '16:9');
    if (creativeLibraryFilter === 'video') return [];
    return [];
  }, [contentLibrary, creativeLibraryFilter]);

  async function handleLogoUpload(file: File | null, variant: 'light' | 'dark') {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file for logo.');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('Logo file is too large. Use a file under 2MB.');
      return;
    }
    try {
      const dataUrl = await fileToDataUrl(file);
      setBrandProfile((current) =>
        variant === 'light' ? { ...current, logo_url: dataUrl } : { ...current, logo_dark_url: dataUrl }
      );
      setSuccessMessage(`${variant === 'light' ? 'Light' : 'Dark'} logo uploaded. Click Save Changes to persist.`);
      setTimeout(() => setSuccessMessage(''), 2600);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to upload logo image.');
    }
  }

  function previewVoiceover(voiceName: string) {
    if (!globalThis.window?.speechSynthesis) {
      setError('Voice preview is not supported in this browser.');
      return;
    }
    const utterance = new SpeechSynthesisUtterance(`Hello, this is ${voiceName}. I will narrate your brand content.`);
    const matchingVoice = globalThis.window.speechSynthesis
      .getVoices()
      .find(
        (voice) =>
          voice.name.toLowerCase().includes(voiceName.toLowerCase()) || voice.lang.toLowerCase().startsWith('en')
      );
    if (matchingVoice) {
      utterance.voice = matchingVoice;
      utterance.lang = matchingVoice.lang;
    }
    globalThis.window.speechSynthesis.cancel();
    globalThis.window.speechSynthesis.speak(utterance);
  }

  function hydrateBrandProfile(nextBrand: BrandProfile, fallbackWebsite = ''): BrandProfile {
    const fallbackAvatar = defaultAvatarProfile();
    const fallbackVoiceEngine = defaultVoiceoverEngine();
    const avatar = nextBrand.avatar_profile ?? fallbackAvatar;
    const voiceEngine = nextBrand.voiceover_engine ?? fallbackVoiceEngine;
    const selectedVoice = nextBrand.voiceover ?? voiceEngine.voice_name ?? '';

    return {
      business_name: nextBrand.business_name ?? '',
      industry: nextBrand.industry ?? 'marketing',
      website: nextBrand.website ?? fallbackWebsite,
      logo_url: nextBrand.logo_url ?? '',
      logo_dark_url: nextBrand.logo_dark_url ?? '',
      description: nextBrand.description ?? '',
      tone: nextBrand.tone ?? 'professional',
      keywords: Array.isArray(nextBrand.keywords) ? nextBrand.keywords : [],
      hashtags: Array.isArray(nextBrand.hashtags) ? nextBrand.hashtags : [],
      timezone: nextBrand.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC',
      ethnicity: nextBrand.ethnicity ?? avatar.ethnicity ?? 'Global / Generic',
      voiceover: selectedVoice,
      avatar_profile: {
        mode: AVATAR_MODE_OPTIONS.includes(avatar.mode ?? 'catalog') ? (avatar.mode ?? 'catalog') : 'catalog',
        preset_id: avatar.preset_id ?? fallbackAvatar.preset_id,
        name: avatar.name ?? fallbackAvatar.name,
        location: avatar.location ?? fallbackAvatar.location,
        ethnicity: avatar.ethnicity ?? nextBrand.ethnicity ?? fallbackAvatar.ethnicity,
        gender: avatar.gender ?? fallbackAvatar.gender,
        age_range: avatar.age_range ?? fallbackAvatar.age_range,
        style: avatar.style ?? fallbackAvatar.style,
        face_type: avatar.face_type ?? fallbackAvatar.face_type,
        eye_style: avatar.eye_style ?? fallbackAvatar.eye_style,
        body_shape: avatar.body_shape ?? fallbackAvatar.body_shape,
        body_proportions: avatar.body_proportions ?? fallbackAvatar.body_proportions,
      },
      voiceover_engine: {
        language: voiceEngine.language ?? 'English',
        voice_name: voiceEngine.voice_name ?? selectedVoice,
        style: voiceEngine.style ?? 'Narration',
        tone: voiceEngine.tone ?? 'Professional',
        accent: voiceEngine.accent ?? 'US',
        use_case: voiceEngine.use_case ?? 'Narration',
      },
      brand_colors:
        Array.isArray(nextBrand.brand_colors) && nextBrand.brand_colors.length
          ? nextBrand.brand_colors.slice(0, 12)
          : ['var(--text)', '#84cc16', 'var(--brand)'],
      title_font_family: nextBrand.title_font_family ?? 'Hanken Grotesk',
      subtitle_font_family: nextBrand.subtitle_font_family ?? 'Hanken Grotesk',
      title_font_weight: nextBrand.title_font_weight ?? 'Regular',
      subtitle_font_weight: nextBrand.subtitle_font_weight ?? 'Regular',
      title_case_type: nextBrand.title_case_type ?? 'Auto',
      subtitle_case_type: nextBrand.subtitle_case_type ?? 'Auto',
      use_custom_font_title: Boolean(nextBrand.use_custom_font_title),
      use_custom_font_subtitle: Boolean(nextBrand.use_custom_font_subtitle),
      custom_font_title: nextBrand.custom_font_title ?? '',
      custom_font_subtitle: nextBrand.custom_font_subtitle ?? '',
    };
  }

  async function loadWorkspace() {
    setIsLoading(true);
    setError('');
    try {
      const [
        catalogRaw,
        accountsRaw,
        brandRaw,
        overviewRaw,
        inboxStatsRaw,
        messagesRaw,
        reportRaw,
        sovRaw,
        notificationsRaw,
      ] = await Promise.all([
        apiGet('/social/accounts/catalog', tenantId),
        apiGet('/social/accounts', tenantId),
        apiGet('/social/brand-profile', tenantId),
        apiGet('/social/workspace/overview', tenantId),
        apiGet('/inbox/stats', tenantId),
        apiGet('/inbox/messages?limit=8', tenantId),
        apiGet('/competitive/report', tenantId),
        apiGet('/competitive/share-of-voice', tenantId),
        apiGet('/notifications?limit=8', tenantId),
      ]);

      const optionalResults = await Promise.allSettled([
        apiGet('/social/listening/summary', tenantId),
        apiGet('/social/listening/alerts', tenantId),
        apiGet('/trends/analytics/dashboard', tenantId),
        apiGet('/trends/forecast', tenantId),
        apiGet('/trends/recommendations', tenantId),
        apiGet('/social/scheduled', tenantId),
      ]);

      const catalogProviders = ((catalogRaw.providers ?? []) as Provider[]).slice();
      setProviders(catalogProviders);
      const nextAccounts = ((accountsRaw.accounts ?? []) as SocialAccount[]).slice();
      setAccounts(nextAccounts);
      const nextBrand = (brandRaw.brand_profile ?? {}) as BrandProfile;
      setBrandProfile(hydrateBrandProfile(nextBrand));
      setWebsiteDraft(nextBrand.website ?? '');
      setOverview((overviewRaw.overview ?? null) as Overview | null);
      setInboxStats((inboxStatsRaw ?? null) as InboxStats | null);
      setMessages(((messagesRaw.messages ?? []) as InboxMessage[]).slice());
      setCompetitorReport((reportRaw ?? null) as CompetitorReport | null);
      setShareOfVoice((sovRaw ?? null) as ShareOfVoice | null);
      setNotifications(((notificationsRaw.notifications ?? []) as NotificationItem[]).slice());
      setListeningSummary(
        settledData(optionalResults[0], (value) => (value.summary ?? null) as ListeningSummary | null, null)
      );
      setListeningAlerts(
        settledData(optionalResults[1], (value) => ((value.alerts ?? []) as ListeningAlert[]).slice(0, 5), [])
      );
      setTrendDashboard(settledData(optionalResults[2], (value) => value as TrendDashboard, null));
      setTrendForecasts(
        settledData(optionalResults[3], (value) => ((value.forecasts ?? []) as TrendForecast[]).slice(0, 6), [])
      );
      setTrendRecommendations(
        settledData(optionalResults[4], (value) => ((value.items ?? []) as TrendRecommendation[]).slice(0, 4), [])
      );
      setScheduledPosts(
        settledData(optionalResults[5], (value) => ((value.items ?? []) as ScheduledPost[]).slice(0, 24), [])
      );

      setAutopostForm((current) => ({
        ...current,
        account_id: current.account_id || nextAccounts[0]?.id || 0,
      }));
    } catch (nextError) {
      setProviders([]);
      const baseMessage = nextError instanceof Error ? nextError.message : 'Failed to load social workspace.';
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? `${baseMessage} Provider catalog is unavailable in strict no-mock mode.`
          : `${baseMessage} Provider catalog is unavailable in fail-closed mode.`
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, [tenantId]);

  async function connectProvider(provider: Provider) {
    setError('');
    try {
      const accountName = `${brandProfile.business_name || 'Nuxtron'} ${provider.label}`;
      const handle = `${(brandProfile.business_name || 'nuxtron').toLowerCase().replaceAll(/\s+/g, '_')}_${provider.network}`;
      const start = (await apiPost(
        `/social/oauth/${provider.network}/start`,
        {
          account_name: accountName,
          handle,
          account_type: 'business',
          website: brandProfile.website || 'https://nuxtron.local',
          description: brandProfile.description || `Connected ${provider.label} publishing workspace.`,
        },
        tenantId
      )) as { state?: string; mode?: string; configured?: boolean; provider_label?: string };

      if (!start.state) {
        throw new Error('Failed to initialize OAuth login state.');
      }
      if (start.mode === 'live' && start.configured === false) {
        throw new Error(`OAuth credentials are not configured for ${start.provider_label || provider.label}.`);
      }

      await apiPost(
        `/social/oauth/${provider.network}/callback`,
        {
          state: start.state,
          code: `local-dev-code-${provider.network}`,
        },
        tenantId
      );
      setActiveTab('social');
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to connect account.');
    }
  }

  async function connectAllProviders() {
    setError('');
    try {
      await apiPost(
        '/social/oauth/connect-all',
        {
          account_name_prefix: brandProfile.business_name || 'Nuxtron',
          handle_prefix: (brandProfile.business_name || 'nuxtron').toLowerCase().replaceAll(/\s+/g, '_'),
          account_type: 'business',
          website: brandProfile.website || 'https://nuxtron.local',
          description:
            brandProfile.description || 'Connected social workspace for publishing, engagement, and analytics.',
        },
        tenantId
      );
      setActiveTab('social');
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to connect all providers.');
    }
  }

  async function disconnectAccount(accountId: number) {
    setError('');
    try {
      await apiDelete(`/social/accounts/${accountId}`, tenantId);
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to disconnect account.');
    }
  }

  async function saveBrandProfile() {
    setError('');
    setIsSavingBrand(true);
    try {
      await apiPut(
        '/social/brand-profile',
        {
          ...brandProfile,
          keywords: brandProfile.keywords,
          hashtags: brandProfile.hashtags,
        },
        tenantId
      );
      await loadWorkspace();
      setSuccessMessage('Brand settings saved successfully.');
      setTimeout(() => setSuccessMessage(''), 2600);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to save brand details.');
    } finally {
      setIsSavingBrand(false);
    }
  }

  async function fetchBrandDetailsFromWebsite() {
    const websiteUrl = websiteDraft.trim();
    if (!websiteUrl) return;
    setError('');
    setIsFetchingWebsite(true);
    try {
      const response = (await apiPost(
        '/social/brand-profile/fetch-from-website',
        {
          website_url: websiteUrl,
        },
        tenantId
      )) as { brand_profile?: BrandProfile };
      const nextBrand = (response.brand_profile ?? {}) as BrandProfile;
      setBrandProfile(hydrateBrandProfile(nextBrand, websiteUrl));
      setWebsiteDraft(nextBrand.website ?? websiteUrl);
      setSuccessMessage('Success: website details fetched and applied.');
      setIsFetchWebsiteModalOpen(false);
      setTimeout(() => setSuccessMessage(''), 3200);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to fetch details from website.');
    } finally {
      setIsFetchingWebsite(false);
    }
  }

  async function engageMessage(messageId: number) {
    const replyText = replyDrafts[messageId]?.trim();
    if (!replyText || !accounts[0]) return;
    setError('');
    try {
      await apiPost(
        `/social/inbox/messages/${messageId}/engage`,
        {
          account_id: accounts[0].id,
          reply_text: replyText,
          action: 'reply',
          agent_name: 'Workspace Desk',
        },
        tenantId
      );
      setReplyDrafts((current) => ({ ...current, [messageId]: '' }));
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to engage message.');
    }
  }

  async function addCompetitor() {
    setError('');
    try {
      const created = (await apiPost('/competitive/profiles', competitorForm, tenantId)) as {
        profile?: { id: number };
      };
      const profileId = created.profile?.id;
      if (profileId) {
        await apiPost(
          `/competitive/profiles/${profileId}/snapshots`,
          {
            followers: 6500,
            following: 280,
            posts_last_30d: 18,
            avg_likes_last_30d: 320,
            avg_comments_last_30d: 34,
            avg_shares_last_30d: 29,
            avg_views_last_30d: 910,
            engagement_rate: 4.2,
            estimated_reach: 48000,
            estimated_mentions: 120,
          },
          tenantId
        );
      }
      setCompetitorForm({ name: '', network: 'instagram', handle: '', profile_url: '' });
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to add competitor.');
    }
  }

  async function syncOwnBrandMetrics() {
    setError('');
    const followers = accounts.reduce((sum, account) => sum + account.followers, 0);
    const likes = accounts.reduce((sum, account) => sum + account.likes, 0);
    const comments = accounts.reduce((sum, account) => sum + account.comments, 0);
    const shares = accounts.reduce((sum, account) => sum + account.shares, 0);
    try {
      await apiPost(
        '/competitive/own-profile',
        {
          network: accounts[0]?.network || 'instagram',
          followers,
          following: Math.max(30, Math.round(followers * 0.03)),
          posts_last_30d: overview?.scheduled_posts ?? 12,
          avg_likes_last_30d: Math.round(likes / Math.max(accounts.length, 1)),
          avg_comments_last_30d: Math.round(comments / Math.max(accounts.length, 1)),
          avg_shares_last_30d: Math.round(shares / Math.max(accounts.length, 1)),
          avg_views_last_30d: 1400,
          engagement_rate: followers > 0 ? Number((((likes + comments + shares) / followers) * 100).toFixed(2)) : 3.6,
          estimated_reach: followers * 4,
          estimated_mentions: Math.max(80, Math.round(totalReach / 500)),
        },
        tenantId
      );
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to sync own brand metrics.');
    }
  }

  async function previewAutopost() {
    setError('');
    try {
      const response = (await apiPost(
        '/social/autopilot/preview',
        {
          ...autopostForm,
          publish_at: autopostForm.publish_at ? new Date(autopostForm.publish_at).toISOString() : undefined,
          media_urls: autopostForm.media_urls
            .split(/\r?\n/)
            .map((item) => item.trim())
            .filter(Boolean),
        },
        tenantId
      )) as { preview?: AutopostPreview };
      setPreview(response.preview ?? null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to preview autopost.');
    }
  }

  async function handleCreativeReferenceUpload(file: File | null) {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Reference image must be an image file.');
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      setError('Reference image is too large. Please use a file under 4MB.');
      return;
    }
    try {
      const dataUrl = await fileToDataUrl(file);
      setCreativeReferenceImage(dataUrl);
      setCreativeReferenceName(file.name);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to load reference image.');
    }
  }

  function creativeSummary() {
    const idea = creativeIdea.trim();
    const lower = idea.toLowerCase();
    const heading = lower.includes('black friday') ? 'Black Friday Hoodie Deals' : 'Limited-Time Product Campaign';
    const subtitle = lower.includes('newsletter') ? 'Launch Your New Store Update' : 'Limited Time Sale Event';
    const cta = lower.includes('newsletter') ? 'Sign Up' : 'Shop Now';
    return {
      heading,
      subtitle,
      cta,
      visualIdea:
        idea ||
        'A high-contrast product-focused ad visual with bold headline hierarchy and a conversion-first CTA button.',
    };
  }

  function generateCreativeCard() {
    if (isCreativeGenerating) return;
    const summary = creativeSummary();
    const cardId = `creative-${Date.now()}`;
    const pendingItem: ContentLibraryItem = {
      id: cardId,
      title: summary.heading,
      subtitle: summary.subtitle,
      cta: summary.cta,
      caption: `${summary.heading} is now live with a high-impact visual angle tailored to your audience.`,
      imageUrl: creativeReferenceImage || makeCreativePreview(summary.heading, summary.subtitle, summary.cta),
      postType: creativePostType,
      aspectRatio: creativeAspectRatio,
      status: 'generating',
      createdAt: new Date().toISOString(),
    };

    setIsCreativeGenerating(true);
    setContentLibrary((current) => [pendingItem, ...current]);

    globalThis.setTimeout(() => {
      finalizeGeneratedCreative(setContentLibrary, cardId); // NOSONAR
      setIsCreativeGenerating(false);
      setSuccessMessage('Creative generated and added to Content Library.');
      setTimeout(() => setSuccessMessage(''), 2600);
    }, 2000);
  }

  async function copyShareLink(itemId: string) {
    const shareUrl = `${globalThis.location.origin}/studio/editor?asset=${encodeURIComponent(itemId)}`;
    try {
      await globalThis.navigator.clipboard.writeText(shareUrl);
      setSuccessMessage('Share link copied to clipboard.');
      setTimeout(() => setSuccessMessage(''), 2200);
    } catch {
      setError('Unable to copy link. Please copy manually from browser address bar.');
    }
  }

  function triggerDownload(item: ContentLibraryItem) {
    const anchor = document.createElement('a');
    anchor.href = item.imageUrl;
    anchor.download = `${item.title.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-') || 'creative'}.png`;
    anchor.click();
  }

  async function publishAutopost(mode: 'auto' | 'now') {
    setError('');
    try {
      const response = (await apiPost(
        '/social/autopilot/publish',
        {
          ...autopostForm,
          publish_mode: mode,
          publish_at:
            mode === 'now' || !autopostForm.publish_at ? undefined : new Date(autopostForm.publish_at).toISOString(),
          media_urls: autopostForm.media_urls
            .split(/\r?\n/)
            .map((item) => item.trim())
            .filter(Boolean),
        },
        tenantId
      )) as Record<string, unknown>;
      setLastPublished(response);
      await loadWorkspace();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to publish autopost.');
    }
  }

  async function moveScheduledPost(postId: number, publishAt: string) {
    if (!publishAt) return;
    setError('');
    try {
      await apiPatch(`/social/scheduled/${postId}/move`, { publish_at: publishAt }, tenantId);
      await loadWorkspace();
      setSuccessMessage('Scheduled time updated.');
      setTimeout(() => setSuccessMessage(''), 2200);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to move scheduled post.');
    }
  }

  async function deleteScheduledPost(postId: number) {
    setError('');
    try {
      await apiDelete(`/social/scheduled/${postId}`, tenantId);
      await loadWorkspace();
      setSuccessMessage('Scheduled post removed.');
      setTimeout(() => setSuccessMessage(''), 2200);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Failed to delete scheduled post.');
    }
  }

  function scheduleDropTarget(dayKey: string, item: ScheduledPost | undefined) {
    if (!item) return '';
    return mergeScheduleDayAndTime(dayKey, timeInputValue(item.publish_at));
  }

  function handleCalendarDrop(dayKey: string, event: DragEvent<HTMLElement>) {
    event.preventDefault();
    const postId = Number(event.dataTransfer.getData('text/plain') || draggingScheduledId || 0);
    const item = scheduledPosts.find((post) => post.id === postId);
    const nextPublishAt = scheduleDropTarget(dayKey, item);
    if (!item || !nextPublishAt) return;
    void moveScheduledPost(postId, nextPublishAt);
    setDraggingScheduledId(null);
  }

  function triggerCalendarDrop(dayKey: string) {
    const item = scheduledPosts.find((post) => post.id === draggingScheduledId);
    const nextPublishAt = scheduleDropTarget(dayKey, item);
    if (!item || !nextPublishAt) return;
    void moveScheduledPost(item.id, nextPublishAt);
    setDraggingScheduledId(null);
  }

  function handleCalendarKeyDown(dayKey: string, event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    triggerCalendarDrop(dayKey);
  }

  function renderScheduleMinuteButtons(postId: number, dayKey: string, publishAt: string) {
    return scheduleMinuteChoices(publishAt).map((choice) => (
      <button
        key={`${postId}-${choice}`}
        type="button"
        className="chip-btn"
        onClick={() => void moveScheduledPost(postId, mergeScheduleDayAndTime(dayKey, choice))}
      >
        {choice}
      </button>
    ));
  }

  const tabs: Array<{ id: WorkspaceTab; label: string }> = [
    { id: 'manager', label: 'AI Manager' },
    { id: 'social', label: 'Social Platforms' },
    { id: 'brand', label: 'Brand Details' },
    { id: 'engagement', label: 'Engagement Desk' },
    { id: 'competitors', label: 'Competitors' },
    { id: 'autopost', label: 'Auto Posting' },
    { id: 'notifications', label: 'Notifications' },
  ];

  const workspaceStyle = {
    '--brand-accent': brandProfile.brand_colors[1] || '#6366f1',
    '--brand-secondary': brandProfile.brand_colors[2] || 'var(--brand)',
    '--brand-font-title': brandProfile.title_font_family || 'inherit',
    '--brand-font-subtitle': brandProfile.subtitle_font_family || 'inherit',
  } as CSSProperties;

  return (
    <main className="workspace-shell" style={workspaceStyle}>
      <section className="workspace-hero">
        <div>
          <p className="eyebrow">Social Workspace</p>
          <h1>Run your AI social media manager from one place.</h1>
          <p className="hero-copy">
            Business setup, avatars, smart inbox, social listening, trend radar, competitor tracking, and humanized
            scheduling are grouped into a single operator workspace.
          </p>
        </div>
        <div className="hero-actions">
          <label>
            <span>Tenant</span>
            <input value={tenantId} readOnly />
          </label>
          <a href="/studio/editor" className="ghost-link">
            Open Editor
          </a>
        </div>
      </section>

      {successMessage ? <p className="success-banner">{successMessage}</p> : null}
      {error ? <p className="error-banner">{error}</p> : null}

      <section className="kpi-grid">
        <article className="kpi-card">
          <span>Connected</span>
          <strong>{overview?.connected_accounts ?? 0}</strong>
          <small>accounts live</small>
        </article>
        <article className="kpi-card">
          <span>Reach</span>
          <strong>{formatCompactNumber(totalReach)}</strong>
          <small>likes, shares, comments, followers</small>
        </article>
        <article className="kpi-card">
          <span>Inbox</span>
          <strong>{overview?.inbox_open ?? 0}</strong>
          <small>open conversations</small>
        </article>
        <article className="kpi-card">
          <span>Inbox triage</span>
          <strong>{Number(overview?.inbox_open ?? 0) + Number(overview?.notifications_unread ?? 0)}</strong>
          <small>{overview?.notifications_unread ?? 0} unread alerts</small>
          <a
            href="/studio/social-studio?panel=inbox"
            className="ghost-link"
            style={{ marginTop: 10, display: 'inline-flex' }}
          >
            Open inbox triage
          </a>
        </article>
        <article className="kpi-card">
          <span>Notifications</span>
          <strong>{overview?.notifications_unread ?? 0}</strong>
          <small>unread alerts</small>
        </article>
        <article className="kpi-card">
          <span>Scheduled</span>
          <strong>{scheduledPosts.length}</strong>
          <small>calendar items</small>
        </article>
      </section>

      <section className="tabs-row" aria-label="Workspace tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? 'tab-btn active' : 'tab-btn'}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </section>

      {activeTab === 'manager' ? (
        <section className="manager-stack">
          <section className="panel-grid two-col">
            <article className="workspace-card manager-focus-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">AI manager status</p>
                  <h2>{setupScore}% of your operator setup is ready</h2>
                </div>
                <button type="button" className="ghost-btn" onClick={() => setActiveTab('brand')}>
                  Complete setup
                </button>
              </div>
              <div className="manager-highlight-grid">
                <div className="mini-stat">
                  <span>Business</span>
                  <strong>{brandProfile.business_name || 'Add brand name'}</strong>
                </div>
                <div className="mini-stat">
                  <span>Website</span>
                  <strong>{brandProfile.website || 'Fetch domain data'}</strong>
                </div>
                <div className="mini-stat">
                  <span>Avatar</span>
                  <strong>{avatarCreatorDisplay(brandProfile.avatar_profile)}</strong>
                </div>
                <div className="mini-stat">
                  <span>Voice</span>
                  <strong>{brandProfile.voiceover || 'Choose voiceover'}</strong>
                </div>
              </div>
              <div className="tag-row">
                {brandProfile.hashtags.slice(0, 5).map((tag) => (
                  <span key={tag} className="capability-pill">
                    {tag}
                  </span>
                ))}
                {brandProfile.hashtags.length === 0 ? (
                  <span className="empty-state inline">No hashtags saved yet.</span>
                ) : null}
              </div>
              <div className="manager-link-row">
                <a href="/smart-inbox" className="ghost-link">
                  Open Smart Inbox
                </a>
                <a href="/social-listening" className="ghost-link">
                  Open Social Listening
                </a>
                <a href="/competitive-benchmarking" className="ghost-link">
                  Open Competitors
                </a>
              </div>
            </article>

            <article className="workspace-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">Trend and ROI radar</p>
                  <h2>Emerging plays and forecasted return</h2>
                </div>
                <button type="button" className="ghost-btn" onClick={() => setActiveTab('autopost')}>
                  Schedule from trends
                </button>
              </div>
              <div className="stats-grid">
                <div className="mini-stat">
                  <span>Tracked trends</span>
                  <strong>{trendDashboard?.summary?.tracked_trends ?? trendForecasts.length}</strong>
                </div>
                <div className="mini-stat">
                  <span>ROI score</span>
                  <strong>{Math.round((trendDashboard?.kpi?.roi_kpi ?? 0) * 100)}%</strong>
                </div>
                <div className="mini-stat">
                  <span>Trend strength</span>
                  <strong>{Math.round((trendDashboard?.kpi?.trend_strength_kpi ?? 0) * 100)}%</strong>
                </div>
                <div className="mini-stat">
                  <span>Target revenue</span>
                  <strong>{formatMoney(trendDashboard?.graphs?.achievable_projection?.target_revenue ?? 0)}</strong>
                </div>
              </div>
              <div className="insight-list compact-list">
                {trendRecommendations.map((item) => (
                  <article key={item.trend_id} className="insight-row">
                    <div>
                      <strong>{item.topic}</strong>
                      <p>
                        {item.phase.replaceAll('_', ' ')} · {Math.round(item.roi_score * 100)}% ROI score
                      </p>
                    </div>
                    <span>{item.recommendations[0] || 'Generate content for this trend.'}</span>
                  </article>
                ))}
                {trendRecommendations.length === 0 ? (
                  <p className="empty-state">
                    No trend forecast yet. Feed signals or open the trend stack to generate one.
                  </p>
                ) : null}
              </div>
            </article>
          </section>

          <section className="panel-grid two-col">
            <article className="workspace-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">Smart inbox</p>
                  <h2>Priority conversations and reply velocity</h2>
                </div>
                <button type="button" className="ghost-btn" onClick={() => setActiveTab('engagement')}>
                  Open desk
                </button>
              </div>
              <div className="stats-grid">
                <div className="mini-stat">
                  <span>Unread</span>
                  <strong>{inboxStats?.unread ?? 0}</strong>
                </div>
                <div className="mini-stat">
                  <span>Reply rate</span>
                  <strong>{formatPercent(inboxStats?.replyRate ?? 0)}</strong>
                </div>
                <div className="mini-stat">
                  <span>Priority score</span>
                  <strong>{Math.round(inboxStats?.avgPriorityScore ?? 0)}</strong>
                </div>
              </div>
              <div className="insight-list compact-list">
                {messages.slice(0, 3).map((message) => (
                  <article key={message.id} className="insight-row">
                    <div>
                      <strong>@{message.author_handle}</strong>
                      <p>
                        {message.network} · {message.sentiment}
                      </p>
                    </div>
                    <span>{message.text}</span>
                  </article>
                ))}
                {messages.length === 0 ? (
                  <p className="empty-state">Connect a channel to populate the inbox desk.</p>
                ) : null}
              </div>
            </article>

            <article className="workspace-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">Social listening</p>
                  <h2>Mentions, alerts, and crisis watch</h2>
                </div>
                <a href="/social-listening" className="ghost-link">
                  Deep dive
                </a>
              </div>
              <div className="stats-grid">
                <div className="mini-stat">
                  <span>Mentions</span>
                  <strong>{listeningSummary?.total_mentions ?? 0}</strong>
                </div>
                <div className="mini-stat">
                  <span>Alerts open</span>
                  <strong>{listeningSummary?.alerts_open ?? 0}</strong>
                </div>
                <div className="mini-stat">
                  <span>Avg engagement</span>
                  <strong>{Math.round(listeningSummary?.avg_engagement ?? 0)}</strong>
                </div>
                <div className="mini-stat">
                  <span>Crisis</span>
                  <strong>{listeningSummary?.crisis?.level ?? 'none'}</strong>
                </div>
              </div>
              <div className="tag-row">
                {(listeningSummary?.top_queries ?? []).map((item) => (
                  <span key={item.query} className="capability-pill subtle">
                    {item.query} · {item.mentions}
                  </span>
                ))}
              </div>
              <div className="insight-list compact-list">
                {listeningAlerts.map((alert) => (
                  <article key={alert.id} className="insight-row">
                    <div>
                      <strong>{alert.title || 'Alert'}</strong>
                      <p>{alert.status || 'open'}</p>
                    </div>
                    <span>{alert.message || 'Listening alert triggered.'}</span>
                  </article>
                ))}
                {listeningAlerts.length === 0 ? <p className="empty-state">No listening alerts right now.</p> : null}
              </div>
            </article>
          </section>

          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Humanized schedule calendar</p>
                <h2>Drag scheduled posts across upcoming days, then tune the exact minute</h2>
              </div>
              <button type="button" className="ghost-btn" onClick={() => setActiveTab('autopost')}>
                Open autopost planner
              </button>
            </div>
            <div className="calendar-board">
              {scheduleBoardDays.map((column) => (
                <section key={column.dayKey} className="calendar-column">
                  <header>
                    <strong>{column.label}</strong>
                    <span>{column.items.length} queued</span>
                  </header>
                  <button
                    type="button"
                    className="calendar-drop-target"
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => handleCalendarDrop(column.dayKey, event)}
                    onKeyDown={(event) => handleCalendarKeyDown(column.dayKey, event)}
                  >
                    Drop here to move the selected post
                  </button>
                  <div className="calendar-column-body">
                    {column.items.map((item) => (
                      <article
                        key={item.id}
                        className="schedule-card"
                        draggable
                        onDragStart={(event) => {
                          setDraggingScheduledId(item.id);
                          event.dataTransfer.setData('text/plain', `${item.id}`);
                        }}
                        onDragEnd={() => setDraggingScheduledId(null)}
                      >
                        <strong>{item.headline || item.platform}</strong>
                        <p>{item.text.slice(0, 88)}</p>
                        <div className="schedule-card-meta">
                          <span>{item.platform}</span>
                          <span>{formatClock(item.publish_at)}</span>
                        </div>
                      </article>
                    ))}
                    {column.items.length === 0 ? <p className="empty-state">Drop scheduled posts here.</p> : null}
                  </div>
                </section>
              ))}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'social' ? (
        <section className="workspace-card social-platforms-board">
          <div className="social-board-head">
            <div>
              <p className="card-kicker">Social Platforms</p>
              <h2>
                {connectedChannelCount}/{providers.length} channels connected
              </h2>
              <p className="board-copy">Connect channels, view linked profiles, and unlink accounts from one place.</p>
            </div>
            <div className="inline-actions">
              <a href="/studio/social-studio?panel=inbox" className="ghost-btn">
                Open inbox triage
              </a>
              <button type="button" className="ghost-btn" onClick={() => void connectAllProviders()}>
                Connect all
              </button>
            </div>
          </div>

          <div className="provider-section-list">
            {providers.map((provider) => {
              const networkAccounts = accountsByNetwork[provider.network] ?? [];
              const isConnected = networkAccounts.length > 0;
              return (
                <article key={provider.network} className="provider-section">
                  <div className="provider-section-head">
                    <div>
                      <h3>{provider.label}</h3>
                      <p>{providerHint(provider.network)}</p>
                    </div>
                    <div className="provider-actions">
                      <button
                        type="button"
                        className={isConnected ? 'ghost-btn connected' : 'ghost-btn'}
                        onClick={() => void connectProvider(provider)}
                      >
                        {isConnected ? 'Add another' : 'Add'}
                      </button>
                      <span>FAQ</span>
                      <span>Watch Videos</span>
                    </div>
                  </div>

                  <div className="provider-account-tiles">
                    {networkAccounts.map((account) => (
                      <article key={account.id} className="linked-account-tile">
                        <div className="linked-avatar">{initials(account.account_name || account.handle)}</div>
                        <strong>{account.account_name}</strong>
                        <p>@{account.handle}</p>
                        <button type="button" className="unlink-btn" onClick={() => void disconnectAccount(account.id)}>
                          Unlink
                        </button>
                      </article>
                    ))}
                    {networkAccounts.length === 0 ? (
                      <p className="empty-state">No accounts linked yet. Click Add to connect.</p>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeTab === 'brand' ? (
        <section className="brand-tab-layout">
          <div className="brand-warning-banner">
            Any changes to your Brand Settings can affect auto-posting content generation.
          </div>

          <article className="workspace-card brand-card">
            <div className="card-head">
              <div>
                <h2>Business Details</h2>
              </div>
              <button type="button" className="ghost-btn" onClick={() => setIsFetchWebsiteModalOpen(true)}>
                Fetch details from website
              </button>
            </div>
            <div className="form-grid">
              <label className="full">
                <span>Brand/Business Name</span>
                <input
                  value={brandProfile.business_name}
                  onChange={(event) =>
                    setBrandProfile((current) => ({ ...current, business_name: event.target.value }))
                  }
                />
              </label>
              <label className="full">
                <span>Business Description</span>
                <textarea
                  value={brandProfile.description ?? ''}
                  onChange={(event) => setBrandProfile((current) => ({ ...current, description: event.target.value }))}
                />
              </label>
            </div>
          </article>

          <article className="workspace-card brand-card">
            <div className="card-head">
              <div>
                <h2>Brand Details</h2>
                <p className="board-copy">Adding brand and business details helps create stronger posts.</p>
              </div>
            </div>
            <div className="brand-sub-warning">
              Your brand colours can be used for auto posting when at least 3 colours are set.
            </div>

            <div className="brand-colors-row">
              {brandProfile.brand_colors.slice(0, 4).map((color, index) => (
                <div key={`${color}-${index}`} className="color-picker-item" title={`Brand color ${index + 1}`}>
                  <input
                    type="color"
                    aria-label={`Brand color ${index + 1}`}
                    value={color}
                    onChange={(event) => updateBrandColor(index, event.target.value)}
                  />
                  <span className="color-dot" style={{ background: color }}></span>
                </div>
              ))}
              <button
                type="button"
                className="ghost-btn"
                onClick={() => addBrandPaletteColor()}
                disabled={brandProfile.brand_colors.length >= 12}
              >
                Add new palette
              </button>
            </div>

            <div className="form-grid">
              <label>
                <span>Tonality of Communication</span>
                <select
                  value={brandProfile.tone}
                  onChange={(event) => setBrandProfile((current) => ({ ...current, tone: event.target.value }))}
                >
                  {TONALITY_OPTIONS.map((tone) => (
                    <option key={tone} value={tone}>
                      {tone[0].toUpperCase() + tone.slice(1)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Select Timezone</span>
                <select
                  value={brandProfile.timezone}
                  onChange={(event) => setBrandProfile((current) => ({ ...current, timezone: event.target.value }))}
                >
                  {Array.from(
                    new Set([
                      Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
                      'UTC',
                      'Asia/Kolkata',
                      'Europe/London',
                      'America/New_York',
                      'America/Los_Angeles',
                      'Asia/Singapore',
                    ])
                  ).map((zone) => (
                    <option key={zone} value={zone}>
                      {zone}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Brand Ethnicity</span>
                <select
                  value={brandProfile.ethnicity ?? 'Global / Generic'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      ethnicity: event.target.value,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        ethnicity: event.target.value,
                      },
                    }))
                  }
                >
                  {ETHNICITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Avatar Creator</span>
                <div className="inline-control">
                  <input
                    value={avatarCreatorDisplay(brandProfile.avatar_profile)}
                    readOnly
                    placeholder="Select avatar"
                  />
                  <button type="button" className="ghost-btn" onClick={() => setIsAvatarModalOpen(true)}>
                    Open creator
                  </button>
                </div>
              </label>
              <label>
                <span>Brand Voiceover</span>
                <div className="inline-control">
                  <input value={brandProfile.voiceover ?? ''} readOnly placeholder="Select a voiceover" />
                  <button type="button" className="ghost-btn" onClick={() => setIsVoiceoverModalOpen(true)}>
                    Select voiceover
                  </button>
                </div>
              </label>
              <label>
                <span>Voice Language</span>
                <select
                  value={brandProfile.voiceover_engine?.language ?? 'English'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      voiceover_engine: {
                        ...(current.voiceover_engine ?? defaultVoiceoverEngine()),
                        language: event.target.value,
                      },
                    }))
                  }
                >
                  {Array.from(new Set(VOICEOVER_CATALOG.map((voice) => voice.language))).map((language) => (
                    <option key={language} value={language}>
                      {language}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Voice Style</span>
                <select
                  value={brandProfile.voiceover_engine?.style ?? 'Narration'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      voiceover_engine: {
                        ...(current.voiceover_engine ?? defaultVoiceoverEngine()),
                        style: event.target.value,
                      },
                    }))
                  }
                >
                  {VOICE_STYLE_OPTIONS.map((style) => (
                    <option key={style} value={style}>
                      {style}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Voice Tone</span>
                <select
                  value={brandProfile.voiceover_engine?.tone ?? 'Professional'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      voiceover_engine: {
                        ...(current.voiceover_engine ?? defaultVoiceoverEngine()),
                        tone: event.target.value,
                      },
                    }))
                  }
                >
                  {VOICE_TONE_OPTIONS.map((toneOption) => (
                    <option key={toneOption} value={toneOption}>
                      {toneOption}
                    </option>
                  ))}
                </select>
              </label>
              <label className="full">
                <span>Brand website</span>
                <input
                  value={brandProfile.website ?? ''}
                  onChange={(event) => {
                    const nextWebsite = event.target.value;
                    setBrandProfile((current) => ({ ...current, website: nextWebsite }));
                    setWebsiteDraft(nextWebsite);
                  }}
                />
              </label>
              <label className="full">
                <span>Logo for light background (URL)</span>
                <input
                  value={brandProfile.logo_url ?? ''}
                  onChange={(event) => setBrandProfile((current) => ({ ...current, logo_url: event.target.value }))}
                  placeholder="https://example.com/logo.png"
                />
              </label>
              <label className="full">
                <span>Upload logo for light background</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => void handleLogoUpload(event.target.files?.[0] ?? null, 'light')}
                />
              </label>
              <label className="full">
                <span>Logo for dark background (URL)</span>
                <input
                  value={brandProfile.logo_dark_url ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({ ...current, logo_dark_url: event.target.value }))
                  }
                  placeholder="https://example.com/logo-dark.png"
                />
              </label>
              <label className="full">
                <span>Upload logo for dark background</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => void handleLogoUpload(event.target.files?.[0] ?? null, 'dark')}
                />
              </label>
              <label className="full">
                <span>Brand hashtags</span>
                <textarea
                  value={brandProfile.hashtags.join(', ')}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      hashtags: event.target.value
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }))
                  }
                />
              </label>
              <label className="full">
                <span>Keywords</span>
                <input
                  value={brandProfile.keywords.join(', ')}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      keywords: event.target.value
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }))
                  }
                />
              </label>
            </div>

            <div className="font-settings-wrap">
              <h3>Manage Font & Typecase</h3>
              <div className="form-grid">
                <label>
                  <span>Title Font</span>
                  <select
                    value={brandProfile.title_font_family}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, title_font_family: event.target.value }))
                    }
                  >
                    {FONT_FAMILY_OPTIONS.map((font) => (
                      <option key={font} value={font}>
                        {font}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Title Font Weight</span>
                  <select
                    value={brandProfile.title_font_weight}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, title_font_weight: event.target.value }))
                    }
                  >
                    {FONT_WEIGHT_OPTIONS.map((weight) => (
                      <option key={weight} value={weight}>
                        {weight}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Title Case Type</span>
                  <select
                    value={brandProfile.title_case_type}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, title_case_type: event.target.value }))
                    }
                  >
                    {CASE_TYPE_OPTIONS.map((caseType) => (
                      <option key={caseType} value={caseType}>
                        {caseType}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Subtitle Font</span>
                  <select
                    value={brandProfile.subtitle_font_family}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, subtitle_font_family: event.target.value }))
                    }
                  >
                    {FONT_FAMILY_OPTIONS.map((font) => (
                      <option key={font} value={font}>
                        {font}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Subtitle Font Weight</span>
                  <select
                    value={brandProfile.subtitle_font_weight}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, subtitle_font_weight: event.target.value }))
                    }
                  >
                    {FONT_WEIGHT_OPTIONS.map((weight) => (
                      <option key={weight} value={weight}>
                        {weight}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Subtitle Case Type</span>
                  <select
                    value={brandProfile.subtitle_case_type}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, subtitle_case_type: event.target.value }))
                    }
                  >
                    {CASE_TYPE_OPTIONS.map((caseType) => (
                      <option key={caseType} value={caseType}>
                        {caseType}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Use custom title font</span>
                  <input
                    type="checkbox"
                    checked={brandProfile.use_custom_font_title}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, use_custom_font_title: event.target.checked }))
                    }
                  />
                </label>
                <label>
                  <span>Title custom font URL</span>
                  <input
                    value={brandProfile.custom_font_title ?? ''}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, custom_font_title: event.target.value }))
                    }
                    placeholder="https://.../title-font.woff2"
                    disabled={!brandProfile.use_custom_font_title}
                  />
                </label>
                <label>
                  <span>Use custom subtitle font</span>
                  <input
                    type="checkbox"
                    checked={brandProfile.use_custom_font_subtitle}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, use_custom_font_subtitle: event.target.checked }))
                    }
                  />
                </label>
                <label>
                  <span>Subtitle custom font URL</span>
                  <input
                    value={brandProfile.custom_font_subtitle ?? ''}
                    onChange={(event) =>
                      setBrandProfile((current) => ({ ...current, custom_font_subtitle: event.target.value }))
                    }
                    placeholder="https://.../subtitle-font.woff2"
                    disabled={!brandProfile.use_custom_font_subtitle}
                  />
                </label>
              </div>
            </div>

            <div className="logo-preview-wrap">
              <p className="card-kicker">Logo Preview</p>
              <div className="logo-preview-grid">
                <div className="logo-preview-card">
                  {brandProfile.logo_url ? (
                    <img src={brandProfile.logo_url} alt="Brand logo preview light" loading="lazy" />
                  ) : (
                    <p className="empty-state">No light logo yet.</p>
                  )}
                </div>
                <div className="logo-preview-card dark">
                  {brandProfile.logo_dark_url ? (
                    <img src={brandProfile.logo_dark_url} alt="Brand logo preview dark" loading="lazy" />
                  ) : (
                    <p className="empty-state">No dark logo yet.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="action-row">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => void saveBrandProfile()}
                disabled={isSavingBrand}
              >
                {isSavingBrand ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'engagement' ? (
        <section className="panel-grid two-col">
          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Traction</p>
                <h2>Likes, shares, comments, and inbox stats</h2>
              </div>
            </div>
            <div className="stats-grid">
              <div className="mini-stat">
                <span>Unread</span>
                <strong>{inboxStats?.unread ?? 0}</strong>
              </div>
              <div className="mini-stat">
                <span>Reply rate</span>
                <strong>{formatPercent(inboxStats?.replyRate ?? 0)}</strong>
              </div>
              <div className="mini-stat">
                <span>Priority</span>
                <strong>{Math.round(inboxStats?.avgPriorityScore ?? 0)}</strong>
              </div>
              <div className="mini-stat">
                <span>Networks</span>
                <strong>{Object.keys(inboxStats?.byNetwork ?? {}).length}</strong>
              </div>
            </div>
          </article>
          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Single-point engagement</p>
                <h2>Unified inbox</h2>
              </div>
            </div>
            <div className="message-list">
              {messages.map((message) => (
                <article key={message.id} className="message-card">
                  <div className="message-meta">
                    <strong>{message.network}</strong>
                    <span>@{message.author_handle}</span>
                    <span>{message.sentiment}</span>
                  </div>
                  <p>{message.text}</p>
                  <div className="suggestion-row">
                    {message.suggested_replies.slice(0, 2).map((reply) => (
                      <button
                        key={reply}
                        type="button"
                        className="chip-btn"
                        onClick={() => applySuggestedReplyDraft(setReplyDrafts, message.id, reply)} // NOSONAR
                      >
                        {reply}
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={replyDrafts[message.id] ?? ''}
                    onChange={(event) =>
                      setReplyDrafts((current) => ({ ...current, [message.id]: event.target.value }))
                    }
                    placeholder="Reply from a single desk"
                  />
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => void engageMessage(message.id)}
                    disabled={!accounts.length}
                  >
                    Send engagement
                  </button>
                </article>
              ))}
              {messages.length === 0 ? (
                <p className="empty-state">Connect an account to seed the unified inbox.</p>
              ) : null}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'competitors' ? (
        <section className="panel-grid two-col">
          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Competitor tracking</p>
                <h2>Monitor social media, websites, and blogs</h2>
              </div>
              <button type="button" className="ghost-btn" onClick={() => void syncOwnBrandMetrics()}>
                Sync own brand
              </button>
            </div>
            <div className="form-grid compact">
              <label>
                <span>Name</span>
                <input
                  value={competitorForm.name}
                  onChange={(event) => setCompetitorForm((current) => ({ ...current, name: event.target.value }))}
                />
              </label>
              <label>
                <span>Network</span>
                <select
                  value={competitorForm.network}
                  onChange={(event) => setCompetitorForm((current) => ({ ...current, network: event.target.value }))}
                >
                  <option value="instagram">Instagram</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="facebook">Facebook</option>
                  <option value="x">X</option>
                  <option value="youtube">YouTube</option>
                </select>
              </label>
              <label>
                <span>Handle</span>
                <input
                  value={competitorForm.handle}
                  onChange={(event) => setCompetitorForm((current) => ({ ...current, handle: event.target.value }))}
                />
              </label>
              <label>
                <span>Profile URL</span>
                <input
                  value={competitorForm.profile_url}
                  onChange={(event) =>
                    setCompetitorForm((current) => ({ ...current, profile_url: event.target.value }))
                  }
                />
              </label>
            </div>
            <button type="button" className="ghost-btn" onClick={() => void addCompetitor()}>
              Track competitor
            </button>
          </article>
          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Comparison report</p>
                <h2>Share of voice and latest benchmark</h2>
              </div>
            </div>
            <div className="sov-grid">
              {shareOfVoice?.breakdown?.map((item) => (
                <div key={item.brand} className="sov-card">
                  <span>{item.brand}</span>
                  <strong>{item.share_pct}%</strong>
                  <small>{formatCompactNumber(item.estimated_mentions)} mentions</small>
                </div>
              ))}
            </div>
            <div className="competitor-table">
              {competitorReport?.competitors?.map((item) => (
                <div key={item.profile.id} className="competitor-row">
                  <strong>{item.profile.name}</strong>
                  <span>@{item.profile.handle}</span>
                  <span>{formatCompactNumber(item.latest_snapshot?.followers ?? 0)} followers</span>
                  <span>{item.latest_snapshot?.engagement_rate ?? 0}% ER</span>
                  <span>{item.vs_own?.ahead ? 'Ahead of you' : 'Behind you'}</span>
                </div>
              ))}
              {(competitorReport?.competitors?.length ?? 0) === 0 ? (
                <p className="empty-state">Add a competitor and sync your own brand to start tracking.</p>
              ) : null}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'autopost' ? (
        <section className="autopost-stack">
          <article className="workspace-card creative-flow-card">
            <div className="creative-stepper" aria-label="Creative flow steps">
              {[1, 2, 3].map((step) => (
                <button
                  key={step}
                  type="button"
                  className={creativeStep === step ? 'step-btn active' : 'step-btn'}
                  onClick={() => setCreativeStep(step as CreativeStep)}
                >
                  <span className="step-index">{step}</span>
                  <span>{creativeStepLabel(step as CreativeStep)}</span>
                </button>
              ))}
            </div>

            {creativeStep === 1 ? (
              <div className="creative-stage">
                <h2>Create Image</h2>
                <p className="board-copy">Describe the image you want to create.</p>
                <label className="full">
                  <span>Write Your Idea</span>
                  <textarea
                    value={creativeIdea}
                    onChange={(event) => setCreativeIdea(event.target.value)}
                    placeholder="I want a poster for my campaign that promotes my product launch..."
                  />
                </label>

                <div className="reference-row">
                  <label className="reference-upload" aria-label="Reference image upload">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(event) => void handleCreativeReferenceUpload(event.target.files?.[0] ?? null)}
                    />
                    <span>{creativeReferenceName || 'Reference Image'}</span>
                    <small>Upload style/layout reference</small>
                  </label>
                  {creativeReferenceImage ? (
                    <img src={creativeReferenceImage} alt="Reference preview" className="reference-preview" />
                  ) : null}
                </div>

                <div className="idea-suggestions">
                  {creativeIdeas.map((idea) => (
                    <button key={idea} type="button" className="chip-btn" onClick={() => setCreativeIdea(idea)}>
                      {idea}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {creativeStep === 2 ? (
              <div className="creative-stage">
                <h2>Configure your Image</h2>
                <p className="board-copy">Customize your image settings to match your brand style.</p>

                <div className="post-type-grid" role="tablist" aria-label="Post type">
                  {(
                    [
                      ['ad', 'Ad'],
                      ['highlights', 'Highlights'],
                      ['before_after', 'Before-After'],
                      ['review', 'Review'],
                    ] as Array<[CreativePostType, string]>
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      className={creativePostType === value ? 'post-type-btn active' : 'post-type-btn'}
                      onClick={() => setCreativePostType(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="aspect-ratio-row" aria-label="Aspect ratio choices">
                  {['1:1', '9:16', '4:5', '2:3', '3:4', '3:2', '16:9', '5:4', '4:3'].map((ratio) => (
                    <button
                      key={ratio}
                      type="button"
                      className={creativeAspectRatio === ratio ? 'ratio-pill active' : 'ratio-pill'}
                      onClick={() => setCreativeAspectRatio(ratio)}
                    >
                      {ratio}
                    </button>
                  ))}
                </div>

                <div className="brand-sub-warning">
                  Brand details linked. Your brand identity will be applied to this image.{' '}
                  <a href="/studio/workspace?tab=brand" className="ghost-link">
                    Go to Brand Settings
                  </a>
                </div>
              </div>
            ) : null}

            {creativeStep === 3 ? (
              <div className="creative-stage">
                <h2>Review and confirm your details</h2>
                <p className="board-copy">Make sure everything looks right before generating your image.</p>
                <div className="review-box">
                  <p>
                    <strong>Visual Idea:</strong> {creativeSummary().visualIdea}
                  </p>
                  <p>
                    <strong>Heading:</strong> {creativeSummary().heading}
                  </p>
                  <p>
                    <strong>Subheading:</strong> {creativeSummary().subtitle}
                  </p>
                  <p>
                    <strong>CTA:</strong> {creativeSummary().cta}
                  </p>
                </div>
                <div className="summary-row">
                  <span>Post Type: {creativePostType.replace('_', ' ')}</span>
                  <span>Aspect Ratio: {creativeAspectRatio}</span>
                  <span>Estimated credit usage: 15</span>
                </div>
              </div>
            ) : null}

            <div className="action-row">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setCreativeStep((current) => (current > 1 ? ((current - 1) as CreativeStep) : current))}
              >
                Back
              </button>
              {creativeStep < 3 ? (
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() =>
                    setCreativeStep((current) => (current < 3 ? ((current + 1) as CreativeStep) : current))
                  }
                >
                  Continue
                </button>
              ) : (
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => generateCreativeCard()}
                  disabled={isCreativeGenerating}
                >
                  {isCreativeGenerating ? 'Generating...' : 'Generate Image'}
                </button>
              )}
            </div>
          </article>

          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Content Library</p>
                <h2>Generated assets</h2>
              </div>
              <div className="tag-row">
                {(['all', 'image', 'video', 'carousel'] as LibraryFilter[]).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    className={creativeLibraryFilter === filter ? 'tab-btn active' : 'tab-btn'}
                    onClick={() => setCreativeLibraryFilter(filter)}
                  >
                    {filter[0].toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="library-grid">
              {visibleLibraryItems.map((item) => (
                <article key={item.id} className="library-card">
                  <div className="library-thumb-wrap">
                    <img src={item.imageUrl} alt={item.title} className="library-thumb" />
                    <span className="library-ratio-tag">{item.aspectRatio}</span>
                  </div>
                  <button type="button" className="ghost-btn" onClick={() => setSelectedLibraryId(item.id)}>
                    Open preview
                  </button>
                  {item.status === 'generating' ? (
                    <div className="library-generating-state">
                      <div className="loading-spinner" />
                      <p>Creating your post...</p>
                      <small>Great things take time. Your content is cooking.</small>
                    </div>
                  ) : (
                    <>
                      <strong>{item.title}</strong>
                      <p>{item.subtitle}</p>
                    </>
                  )}
                  <div className="library-actions">
                    <button
                      type="button"
                      className="ghost-btn"
                      disabled={item.status !== 'ready'}
                      onClick={(event) => {
                        event.stopPropagation();
                        triggerDownload(item);
                      }}
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      className="ghost-btn"
                      disabled={item.status !== 'ready'}
                      onClick={(event) => {
                        event.stopPropagation();
                        setSuccessMessage('Publish queued from content library.');
                        setTimeout(() => setSuccessMessage(''), 2200);
                      }}
                    >
                      Publish
                    </button>
                    <button
                      type="button"
                      className="ghost-btn"
                      disabled={item.status !== 'ready'}
                      onClick={(event) => {
                        event.stopPropagation();
                        void copyShareLink(item.id);
                      }}
                    >
                      Share Link
                    </button>
                  </div>
                </article>
              ))}

              {visibleLibraryItems.length === 0 ? (
                <p className="empty-state">
                  No generated assets yet. Complete the 3-step flow and click Generate Image.
                </p>
              ) : null}
            </div>
          </article>

          <section className="panel-grid two-col">
            <article className="workspace-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">One-click autopost</p>
                  <h2>Auto-adjust size, text, hashtags, keywords, headings, and descriptions</h2>
                </div>
              </div>
              {accounts.length > 0 ? null : (
                <p className="empty-state">
                  Connect a social account in Social Platforms before using autopost content generation.
                </p>
              )}
              <div className="form-grid">
                <label>
                  <span>Account</span>
                  <select
                    value={autopostForm.account_id}
                    onChange={(event) =>
                      setAutopostForm((current) => ({ ...current, account_id: Number(event.target.value) }))
                    }
                  >
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.network_label} @{account.handle}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Content type</span>
                  <select
                    value={autopostForm.content_type}
                    onChange={(event) =>
                      setAutopostForm((current) => ({ ...current, content_type: event.target.value }))
                    }
                  >
                    <option value="image">Image</option>
                    <option value="video">Video</option>
                    <option value="voice">Voice</option>
                    <option value="text">Text</option>
                    <option value="story">Story</option>
                  </select>
                </label>
                <label className="full">
                  <span>Headline</span>
                  <input
                    value={autopostForm.headline}
                    onChange={(event) => setAutopostForm((current) => ({ ...current, headline: event.target.value }))}
                  />
                </label>
                <label className="full">
                  <span>Caption</span>
                  <textarea
                    value={autopostForm.caption}
                    onChange={(event) => setAutopostForm((current) => ({ ...current, caption: event.target.value }))}
                  />
                </label>
                <label className="full">
                  <span>Media URLs</span>
                  <textarea
                    value={autopostForm.media_urls}
                    onChange={(event) => setAutopostForm((current) => ({ ...current, media_urls: event.target.value }))}
                    placeholder="One URL per line"
                  />
                </label>
                <label>
                  <span>Publish at</span>
                  <input
                    type="datetime-local"
                    value={autopostForm.publish_at}
                    onChange={(event) => setAutopostForm((current) => ({ ...current, publish_at: event.target.value }))}
                  />
                </label>
                <div className="human-time-wrap">
                  <span>Human touch</span>
                  <div className="tag-row">
                    {humanizedScheduleChoices.map((choice) => (
                      <button
                        key={choice.value}
                        type="button"
                        className={autopostForm.publish_at === choice.value ? 'tab-btn active' : 'tab-btn'}
                        onClick={() => setAutopostForm((current) => ({ ...current, publish_at: choice.value }))}
                      >
                        {choice.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      className="ghost-btn"
                      onClick={() => setAutopostForm((current) => ({ ...current, publish_at: '' }))}
                    >
                      Use AI timing
                    </button>
                  </div>
                </div>
              </div>
              <div className="action-row">
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => void previewAutopost()}
                  disabled={!autopostForm.account_id}
                >
                  Preview adjustments
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => void publishAutopost('auto')}
                  disabled={!autopostForm.account_id}
                >
                  Queue autopost
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => void publishAutopost('now')}
                  disabled={!autopostForm.account_id}
                >
                  Publish now
                </button>
              </div>
            </article>
            <article className="workspace-card">
              <div className="card-head">
                <div>
                  <p className="card-kicker">Autopost preview</p>
                  <h2>Channel-specific optimization</h2>
                </div>
              </div>
              {preview ? (
                <div className="preview-stack brand-preview-stack">
                  <div className="preview-row">
                    <span>Aspect ratio</span>
                    <strong>{preview.aspect_ratio}</strong>
                  </div>
                  <div className="preview-row">
                    <span>Recommended publish</span>
                    <strong>{formatDateTime(preview.recommended_publish_at)}</strong>
                  </div>
                  <div className="preview-row">
                    <span>Description</span>
                    <strong>{preview.description}</strong>
                  </div>
                  <div className="tag-row">
                    {preview.hashtags.map((tag) => (
                      <span key={tag} className="capability-pill">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="tag-row">
                    {preview.keywords.map((keyword) => (
                      <span key={keyword} className="capability-pill subtle">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="empty-state">
                  Run a preview to see resized format guidance, optimized copy, hashtags, and timing.
                </p>
              )}
              {lastPublished ? <pre className="result-box">{JSON.stringify(lastPublished, null, 2)}</pre> : null}
            </article>
          </section>

          <article className="workspace-card">
            <div className="card-head">
              <div>
                <p className="card-kicker">Schedule planner</p>
                <h2>Move posts across days, then fine-tune the exact time</h2>
              </div>
              <button type="button" className="ghost-btn" onClick={() => void loadWorkspace()}>
                Refresh queue
              </button>
            </div>
            <div className="calendar-board">
              {scheduleBoardDays.map((column) => (
                <section key={column.dayKey} className="calendar-column">
                  <header>
                    <strong>{column.label}</strong>
                    <span>{column.items.length} posts</span>
                  </header>
                  <button
                    type="button"
                    className="calendar-drop-target"
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => handleCalendarDrop(column.dayKey, event)}
                    onKeyDown={(event) => handleCalendarKeyDown(column.dayKey, event)}
                  >
                    Drop here to move the selected post
                  </button>
                  <div className="calendar-column-body">
                    {column.items.map((item) => (
                      <article
                        key={item.id}
                        className="schedule-card detailed"
                        draggable
                        onDragStart={(event) => {
                          setDraggingScheduledId(item.id);
                          event.dataTransfer.setData('text/plain', `${item.id}`);
                        }}
                        onDragEnd={() => setDraggingScheduledId(null)}
                      >
                        <strong>{item.headline || item.platform}</strong>
                        <p>{item.text.slice(0, 96)}</p>
                        <div className="schedule-card-meta">
                          <span>{item.platform}</span>
                          <span>{item.status}</span>
                        </div>
                        <div className="schedule-card-actions">
                          <input
                            type="time"
                            value={timeInputValue(item.publish_at)}
                            onChange={(event) =>
                              void moveScheduledPost(
                                item.id,
                                mergeScheduleDayAndTime(column.dayKey, event.target.value)
                              )
                            }
                          />
                          {renderScheduleMinuteButtons(item.id, column.dayKey, item.publish_at)}
                          <button
                            type="button"
                            className="ghost-btn danger"
                            onClick={() => void deleteScheduledPost(item.id)}
                          >
                            Remove
                          </button>
                        </div>
                      </article>
                    ))}
                    {column.items.length === 0 ? (
                      <p className="empty-state">Drop a post here to reschedule it.</p>
                    ) : null}
                  </div>
                </section>
              ))}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'notifications' ? (
        <section className="workspace-card notifications-card">
          <div className="card-head">
            <div>
              <p className="card-kicker">Connected account alerts</p>
              <h2>Notifications from social channels</h2>
            </div>
            <button type="button" className="ghost-btn" onClick={() => void loadWorkspace()}>
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <div className="notification-list">
            {notifications.map((notification) => (
              <article key={notification.id} className="notification-row">
                <div>
                  <strong>{notification.title}</strong>
                  <p>{notification.message}</p>
                </div>
                <div className="notification-meta">
                  <span>{notification.priority}</span>
                  <span>{formatAge(notification.created_at)}</span>
                </div>
              </article>
            ))}
            {notifications.length === 0 ? <p className="empty-state">No notifications yet.</p> : null}
          </div>
        </section>
      ) : null}

      {isFetchWebsiteModalOpen ? (
        <dialog className="fetch-modal-overlay" open aria-label="Fetch details from website">
          <div className="fetch-modal-card">
            <div className="fetch-modal-head">
              <h3>Fetch details from website</h3>
              <button type="button" className="modal-close" onClick={() => setIsFetchWebsiteModalOpen(false)}>
                x
              </button>
            </div>
            <p>Your details are secure. We only fetch public information to make setup faster.</p>
            <label>
              <span>Step 1: Enter website URL</span>
              <input
                value={websiteDraft}
                onChange={(event) => setWebsiteDraft(event.target.value)}
                placeholder="https://yourwebsite.com"
              />
            </label>
            <div className="brand-sub-warning">
              Step 2: Existing brand details may be replaced by fetched website information.
            </div>
            <div className="action-row">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => void fetchBrandDetailsFromWebsite()}
                disabled={!websiteDraft.trim() || isFetchingWebsite}
              >
                {isFetchingWebsite ? 'Fetching...' : 'Step 3: Fetch Details'}
              </button>
            </div>
          </div>
        </dialog>
      ) : null}

      {isAvatarModalOpen ? (
        <dialog className="fetch-modal-overlay" open aria-label="Avatar creator">
          <div className="fetch-modal-card voiceover-modal-card">
            <div className="fetch-modal-head">
              <h3>Avatar creator</h3>
              <button type="button" className="modal-close" onClick={() => setIsAvatarModalOpen(false)}>
                x
              </button>
            </div>

            <div className="voiceover-filters avatar-filters">
              <input
                value={avatarSearch}
                onChange={(event) => setAvatarSearch(event.target.value)}
                placeholder="Search avatar"
              />
              <select value={avatarEthnicityFilter} onChange={(event) => setAvatarEthnicityFilter(event.target.value)}>
                <option value="All">Ethnicity: All</option>
                {Array.from(new Set(AVATAR_PRESET_CATALOG.map((avatar) => avatar.ethnicity))).map((ethnicity) => (
                  <option key={ethnicity} value={ethnicity}>
                    {ethnicity}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="ghost-btn"
                onClick={() =>
                  setBrandProfile((current) => ({
                    ...current,
                    avatar_profile: {
                      ...(current.avatar_profile ?? defaultAvatarProfile()),
                      mode: 'scratch',
                      preset_id: '',
                    },
                  }))
                }
              >
                Start from scratch
              </button>
            </div>

            <div className="voiceover-list">
              {filteredAvatars.map((avatar) => (
                <label key={avatar.id} className="voiceover-row avatar-row">
                  <input
                    type="radio"
                    name="avatar-profile"
                    checked={brandProfile.avatar_profile?.preset_id === avatar.id}
                    onChange={() => applyAvatarPreset(avatar)}
                  />
                  <div>
                    <strong>{avatar.name}</strong>
                    <p>
                      {avatar.ethnicity} • {avatar.style} • {avatar.location}
                    </p>
                  </div>
                  <button type="button" className="ghost-btn" onClick={() => applyAvatarPreset(avatar)}>
                    Use
                  </button>
                </label>
              ))}
              {filteredAvatars.length === 0 ? <p className="empty-state">No avatars match your filters.</p> : null}
            </div>

            <div className="form-grid compact avatar-custom-grid">
              <label>
                <span>Mode</span>
                <select
                  value={brandProfile.avatar_profile?.mode ?? 'catalog'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: event.target.value as AvatarProfile['mode'],
                      },
                    }))
                  }
                >
                  {AVATAR_MODE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Name</span>
                <input
                  value={brandProfile.avatar_profile?.name ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        name: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Location</span>
                <input
                  value={brandProfile.avatar_profile?.location ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        location: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Gender</span>
                <select
                  value={brandProfile.avatar_profile?.gender ?? 'female'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        gender: event.target.value,
                      },
                    }))
                  }
                >
                  {AVATAR_GENDER_OPTIONS.map((gender) => (
                    <option key={gender} value={gender}>
                      {gender}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Age range</span>
                <select
                  value={brandProfile.avatar_profile?.age_range ?? '25-34'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        age_range: event.target.value,
                      },
                    }))
                  }
                >
                  {AVATAR_AGE_OPTIONS.map((ageRange) => (
                    <option key={ageRange} value={ageRange}>
                      {ageRange}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Style</span>
                <input
                  value={brandProfile.avatar_profile?.style ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        style: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Face type</span>
                <input
                  value={brandProfile.avatar_profile?.face_type ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        face_type: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Eye style</span>
                <input
                  value={brandProfile.avatar_profile?.eye_style ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        eye_style: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Body shape</span>
                <input
                  value={brandProfile.avatar_profile?.body_shape ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        body_shape: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                <span>Body proportions</span>
                <input
                  value={brandProfile.avatar_profile?.body_proportions ?? ''}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      avatar_profile: {
                        ...(current.avatar_profile ?? defaultAvatarProfile()),
                        mode: 'custom',
                        body_proportions: event.target.value,
                      },
                    }))
                  }
                />
              </label>
            </div>

            <div className="voiceover-footer">
              <div className="action-row">
                <button type="button" className="ghost-btn" onClick={() => setIsAvatarModalOpen(false)}>
                  Cancel
                </button>
                <button type="button" className="ghost-btn" onClick={() => setIsAvatarModalOpen(false)}>
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </dialog>
      ) : null}

      {isVoiceoverModalOpen ? (
        <dialog className="fetch-modal-overlay" open aria-label="Select a voiceover">
          <div className="fetch-modal-card voiceover-modal-card">
            <div className="fetch-modal-head">
              <h3>Select a voiceover</h3>
              <button type="button" className="modal-close" onClick={() => setIsVoiceoverModalOpen(false)}>
                x
              </button>
            </div>

            <div className="voiceover-filters">
              <input
                value={voiceoverSearch}
                onChange={(event) => setVoiceoverSearch(event.target.value)}
                placeholder="Search voiceover"
              />
              <select
                value={voiceoverGender}
                onChange={(event) => setVoiceoverGender(event.target.value as 'all' | 'male' | 'female')}
              >
                <option value="all">Gender: both</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
              <select value={voiceoverLanguage} onChange={(event) => setVoiceoverLanguage(event.target.value)}>
                <option value="All">Language: All</option>
                {Array.from(new Set(VOICEOVER_CATALOG.map((voice) => voice.language))).map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
              <select value={voiceoverStyle} onChange={(event) => setVoiceoverStyle(event.target.value)}>
                <option value="All">Style: All</option>
                {VOICE_STYLE_OPTIONS.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
              <select value={voiceoverTone} onChange={(event) => setVoiceoverTone(event.target.value)}>
                <option value="All">Tone: All</option>
                {VOICE_TONE_OPTIONS.map((toneOption) => (
                  <option key={toneOption} value={toneOption}>
                    {toneOption}
                  </option>
                ))}
              </select>
              <select value={voiceoverAccent} onChange={(event) => setVoiceoverAccent(event.target.value)}>
                <option value="All">Accent: All</option>
                {Array.from(new Set(VOICEOVER_CATALOG.map((voice) => voice.accent))).map((accent) => (
                  <option key={accent} value={accent}>
                    {accent}
                  </option>
                ))}
              </select>
            </div>

            <div className="voiceover-list">
              {filteredVoiceovers.map((voice) => (
                <label key={voice.name} className="voiceover-row">
                  <input
                    type="radio"
                    name="voiceover"
                    checked={brandProfile.voiceover === voice.name}
                    onChange={() => selectVoiceover(voice)}
                  />
                  <div>
                    <strong>{voice.name}</strong>
                    <p>
                      {voice.language} ({voice.accent}) • {voice.style} • {voice.tone}{' '}
                      {voice.premium ? 'Premium' : 'Standard'}
                    </p>
                  </div>
                  <button type="button" className="ghost-btn" onClick={() => previewVoiceover(voice.name)}>
                    Preview
                  </button>
                </label>
              ))}
              {filteredVoiceovers.length === 0 ? (
                <p className="empty-state">No voiceovers match your filters.</p>
              ) : null}
            </div>

            <div className="voiceover-footer">
              <label>
                <span>Use case</span>
                <select
                  value={brandProfile.voiceover_engine?.use_case ?? 'Narration'}
                  onChange={(event) =>
                    setBrandProfile((current) => ({
                      ...current,
                      voiceover_engine: {
                        ...(current.voiceover_engine ?? defaultVoiceoverEngine()),
                        use_case: event.target.value,
                      },
                    }))
                  }
                >
                  {VOICE_USE_CASE_OPTIONS.map((useCase) => (
                    <option key={useCase} value={useCase}>
                      {useCase}
                    </option>
                  ))}
                </select>
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={showPremiumVoiceovers}
                  onChange={(event) => setShowPremiumVoiceovers(event.target.checked)}
                />
                <span>Show Premium</span>
              </label>
              <div className="action-row">
                <button type="button" className="ghost-btn" onClick={() => setIsVoiceoverModalOpen(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => setIsVoiceoverModalOpen(false)}
                  disabled={!brandProfile.voiceover}
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </dialog>
      ) : null}

      {selectedLibraryItem ? (
        <dialog className="fetch-modal-overlay" open aria-label="Creative preview">
          <div className="creative-preview-modal">
            <div className="creative-preview-media">
              <img src={selectedLibraryItem.imageUrl} alt={selectedLibraryItem.title} />
            </div>
            <div className="creative-preview-body">
              <div className="fetch-modal-head">
                <h3>{selectedLibraryItem.title}</h3>
                <button type="button" className="modal-close" onClick={() => setSelectedLibraryId('')}>
                  x
                </button>
              </div>
              <p>{selectedLibraryItem.caption}</p>
              <div className="summary-row">
                <span>Aspect ratio: {selectedLibraryItem.aspectRatio}</span>
                <span>Post type: {selectedLibraryItem.postType.replace('_', ' ')}</span>
              </div>
              <div className="action-row">
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => {
                    setSuccessMessage('Creative publish queued from preview.');
                    setTimeout(() => setSuccessMessage(''), 2200);
                  }}
                >
                  Publish
                </button>
                <a href="/studio/editor" className="ghost-link">
                  Edit
                </a>
                <button type="button" className="ghost-btn" onClick={() => triggerDownload(selectedLibraryItem)}>
                  Download
                </button>
              </div>
            </div>
          </div>
        </dialog>
      ) : null}

      <style jsx>{`
        .workspace-shell {
          max-width: 1500px;
          margin: 0 auto;
          padding: 24px 16px 48px;
          display: grid;
          gap: 16px;
        }

        .workspace-hero,
        .workspace-card,
        .kpi-card {
          border: 1px solid var(--line);
          border-radius: 18px;
          background: color-mix(in oklab, var(--bg-soft) 97%, white 3%);
          box-shadow: 0 16px 42px rgba(0, 0, 0, 0.14);
        }

        .workspace-hero {
          padding: 22px;
          display: grid;
          grid-template-columns: 1.5fr auto;
          gap: 16px;
          background:
            radial-gradient(circle at top right, rgba(56, 189, 248, 0.18), transparent 34%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 246, 255, 0.98));
          color: #eef0f4;
        }

        .eyebrow,
        .card-kicker {
          margin: 0 0 6px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: #6366f1;
        }

        .workspace-hero h1,
        .workspace-card h2 {
          margin: 0;
          font-family: var(--brand-font-title, inherit);
        }

        .hero-copy {
          margin: 12px 0 0;
          max-width: 760px;
          color: #e7e9ef;
          line-height: 1.6;
          font-family: var(--brand-font-subtitle, inherit);
        }

        .hero-actions {
          display: grid;
          align-content: start;
          gap: 12px;
          min-width: 220px;
        }

        .hero-actions label,
        .form-grid label {
          display: grid;
          gap: 6px;
          font-size: 12px;
          color: var(--muted);
          font-weight: 700;
        }

        input,
        textarea,
        select {
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(0, 0, 0, 0.08);
          color: var(--fg);
          padding: 10px 12px;
          font: inherit;
        }

        input[type='checkbox'] {
          width: 18px;
          height: 18px;
          padding: 0;
          border-radius: 6px;
          justify-self: start;
          accent-color: #6366f1;
        }

        textarea {
          min-height: 110px;
          resize: vertical;
        }

        .ghost-link,
        .ghost-btn,
        .tab-btn,
        .chip-btn {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px 12px;
          background: transparent;
          color: var(--fg);
          font-weight: 700;
          text-decoration: none;
          cursor: pointer;
        }

        .ghost-btn.connected {
          background: rgba(16, 185, 129, 0.12);
          color: #059669;
        }

        .ghost-btn.danger {
          color: #ef4444;
          border-color: rgba(239, 68, 68, 0.45);
        }

        .error-banner {
          margin: 0;
          padding: 12px 14px;
          border-radius: 12px;
          background: rgba(239, 68, 68, 0.12);
          color: #ef4444;
          font-weight: 700;
        }

        .success-banner {
          margin: 0;
          padding: 12px 14px;
          border-radius: 12px;
          background: rgba(16, 185, 129, 0.16);
          color: #047857;
          font-weight: 700;
        }

        .brand-tab-layout {
          display: grid;
          gap: 14px;
        }

        .brand-warning-banner,
        .brand-sub-warning {
          border: 1px solid rgba(245, 158, 11, 0.55);
          background: rgba(245, 158, 11, 0.15);
          color: #fef3c7;
          border-radius: 12px;
          padding: 10px 12px;
          font-weight: 700;
        }

        .brand-card {
          gap: 14px;
        }

        .brand-colors-row {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }

        .color-picker-item {
          position: relative;
          display: inline-grid;
          place-items: center;
          width: 34px;
          height: 34px;
        }

        .color-picker-item input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }

        .font-settings-wrap {
          display: grid;
          gap: 10px;
          border-top: 1px solid var(--line);
          padding-top: 10px;
        }

        .inline-control {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 8px;
        }

        .font-settings-wrap h3 {
          margin: 0;
        }

        .logo-preview-wrap {
          display: grid;
          gap: 8px;
        }

        .logo-preview-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          max-width: 560px;
        }

        .logo-preview-card {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.04);
          width: min(260px, 100%);
          min-height: 120px;
          display: grid;
          place-items: center;
        }

        .logo-preview-card.dark {
          background: #eef0f4;
        }

        .logo-preview-card img {
          max-width: 100%;
          max-height: 92px;
          object-fit: contain;
          border-radius: 8px;
        }

        .color-dot {
          width: 34px;
          height: 34px;
          border-radius: 999px;
          border: 1px solid var(--line);
          display: inline-block;
        }

        .fetch-modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(148,163,184,0.10);
          z-index: 90;
          display: grid;
          place-items: center;
          padding: 16px;
        }

        .fetch-modal-card {
          width: min(100%, 620px);
          border-radius: 16px;
          border: 1px solid var(--line);
          background: color-mix(in oklab, var(--bg-soft) 99%, white 1%);
          box-shadow: 0 24px 48px rgba(148,163,184,0.10);
          padding: 18px;
          display: grid;
          gap: 12px;
        }

        .fetch-modal-card h3,
        .fetch-modal-card p {
          margin: 0;
        }

        .fetch-modal-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .modal-close {
          border: 1px solid var(--line);
          background: transparent;
          color: var(--fg);
          border-radius: 10px;
          padding: 6px 9px;
          cursor: pointer;
          font-weight: 700;
        }

        .voiceover-modal-card {
          max-height: 80vh;
          overflow: auto;
        }

        .voiceover-filters {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }

        .avatar-filters {
          grid-template-columns: 1.3fr 1fr auto;
        }

        .voiceover-list {
          display: grid;
          gap: 8px;
          max-height: 320px;
          overflow: auto;
        }

        .voiceover-row {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 10px;
          background: rgba(255, 255, 255, 0.03);
        }

        .voiceover-row p {
          margin: 2px 0 0;
          color: var(--muted);
          font-size: 12px;
        }

        .avatar-row {
          align-items: start;
        }

        .avatar-custom-grid {
          margin-top: 8px;
        }

        .voiceover-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .autopost-stack {
          display: grid;
          gap: 16px;
        }

        .manager-stack {
          display: grid;
          gap: 16px;
        }

        .manager-focus-card {
          background:
            radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 38%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(236, 253, 245, 0.98));
          color: #eef0f4;
        }

        .manager-highlight-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }

        .manager-link-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .compact-list {
          margin-top: 12px;
        }

        .insight-list {
          display: grid;
          gap: 10px;
        }

        .insight-row {
          display: grid;
          grid-template-columns: minmax(0, 220px) 1fr;
          gap: 12px;
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px 12px;
          background: rgba(255, 255, 255, 0.04);
        }

        .insight-row p {
          margin: 4px 0 0;
          color: var(--muted);
          font-size: 12px;
        }

        .empty-state.inline {
          display: inline-flex;
          margin: 0;
        }

        .calendar-board {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 10px;
        }

        .calendar-column {
          border: 1px dashed rgba(148, 163, 184, 0.55);
          border-radius: 14px;
          padding: 10px;
          background: rgba(255, 255, 255, 0.03);
          min-height: 220px;
          display: grid;
          gap: 10px;
        }

        .calendar-column header {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          font-size: 12px;
          color: var(--muted);
        }

        .calendar-drop-target {
          border: 1px dashed rgba(37, 99, 235, 0.45);
          border-radius: 10px;
          background: rgba(37, 99, 235, 0.08);
          color: #6366f1;
          padding: 8px 10px;
          font-size: 12px;
          font-weight: 700;
          text-align: left;
          cursor: pointer;
        }

        .calendar-column-body {
          display: grid;
          gap: 8px;
          align-content: start;
        }

        .schedule-card {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          background: rgba(148,163,184,0.10);
          display: grid;
          gap: 8px;
          cursor: grab;
        }

        .schedule-card p {
          margin: 0;
          color: var(--muted);
          font-size: 12px;
          line-height: 1.5;
        }

        .schedule-card-meta {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          font-size: 11px;
          color: var(--muted);
          text-transform: capitalize;
        }

        .schedule-card-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .schedule-card-actions input {
          max-width: 110px;
        }

        .human-time-wrap {
          display: grid;
          gap: 8px;
          align-content: start;
        }

        .human-time-wrap > span {
          font-size: 12px;
          color: var(--muted);
          font-weight: 700;
        }

        .creative-flow-card {
          gap: 14px;
          background:
            radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 40%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(241, 245, 249, 0.98));
          color: #eef0f4;
        }

        .creative-stepper {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }

        .step-btn {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.8);
          border-radius: 12px;
          padding: 10px;
          color: #e7e9ef;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-weight: 700;
          cursor: pointer;
        }

        .step-btn.active {
          border-color: #6366f1;
          color: #eef0f4;
          box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.18);
        }

        .step-index {
          width: 22px;
          height: 22px;
          border-radius: 999px;
          display: inline-grid;
          place-items: center;
          background: rgba(37, 99, 235, 0.18);
          color: #6366f1;
          font-size: 11px;
          font-weight: 800;
        }

        .creative-stage {
          display: grid;
          gap: 12px;
        }

        .creative-stage h2 {
          margin: 0;
          font-size: 34px;
          color: #6366f1;
        }

        .reference-row {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .reference-upload {
          border: 1px dashed rgba(148, 163, 184, 0.8);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.78);
          padding: 12px;
          min-width: 220px;
          position: relative;
          overflow: hidden;
          display: grid !important;
          gap: 4px;
          color: #e7e9ef !important;
        }

        .reference-upload input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }

        .reference-upload small {
          color: var(--muted);
          font-weight: 600;
        }

        .reference-preview {
          width: 84px;
          height: 84px;
          border-radius: 12px;
          border: 1px solid var(--line);
          object-fit: cover;
        }

        .idea-suggestions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .post-type-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
        }

        .post-type-btn {
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.86);
          color: #e7e9ef;
          padding: 12px;
          font-weight: 700;
          cursor: pointer;
        }

        .post-type-btn.active {
          border-color: #6366f1;
          box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.16);
        }

        .aspect-ratio-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .ratio-pill {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.85);
          color: #e7e9ef;
          padding: 6px 12px;
          font-weight: 700;
          font-size: 12px;
          cursor: pointer;
        }

        .ratio-pill.active {
          border-color: #6366f1;
          color: #1e3a8a;
          background: rgba(191, 219, 254, 0.5);
        }

        .review-box {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.78);
          padding: 14px;
          display: grid;
          gap: 8px;
        }

        .review-box p,
        .summary-row {
          margin: 0;
          color: #e7e9ef;
        }

        .summary-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          font-size: 12px;
          font-weight: 700;
          color: #e7e9ef;
        }

        .library-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
          gap: 12px;
        }

        .library-card {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.04);
          padding: 10px;
          display: grid;
          gap: 8px;
          cursor: pointer;
        }

        .library-card strong,
        .library-card p {
          margin: 0;
        }

        .library-card p {
          color: var(--muted);
          font-size: 13px;
        }

        .library-thumb-wrap {
          position: relative;
          border-radius: 12px;
          overflow: hidden;
          border: 1px solid var(--line);
        }

        .library-thumb {
          width: 100%;
          aspect-ratio: 1 / 1;
          object-fit: cover;
          display: block;
        }

        .library-ratio-tag {
          position: absolute;
          left: 8px;
          top: 8px;
          border-radius: 999px;
          background: rgba(148,163,184,0.10);
          color: var(--text);
          padding: 4px 8px;
          font-size: 11px;
          font-weight: 700;
        }

        .library-actions {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }

        .library-generating-state {
          border: 1px dashed rgba(148, 163, 184, 0.65);
          border-radius: 12px;
          padding: 10px;
          display: grid;
          justify-items: center;
          gap: 4px;
          text-align: center;
        }

        .library-generating-state p,
        .library-generating-state small {
          margin: 0;
        }

        .loading-spinner {
          width: 28px;
          height: 28px;
          border-radius: 999px;
          border: 3px solid var(--line);
          border-top-color: #6366f1;
          animation: spin 1s linear infinite;
        }

        .creative-preview-modal {
          width: min(100%, 980px);
          border-radius: 18px;
          border: 1px solid var(--line);
          background: color-mix(in oklab, var(--bg-soft) 99%, white 1%);
          box-shadow: 0 24px 48px rgba(148,163,184,0.10);
          overflow: hidden;
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
        }

        .creative-preview-media {
          background: rgba(148,163,184,0.10);
          padding: 12px;
        }

        .creative-preview-media img {
          width: 100%;
          aspect-ratio: 1 / 1;
          object-fit: cover;
          border-radius: 14px;
          display: block;
        }

        .creative-preview-body {
          padding: 16px;
          display: grid;
          gap: 12px;
          align-content: start;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .toggle-row {
          display: inline-flex !important;
          align-items: center;
          gap: 8px;
          color: var(--muted);
          font-weight: 700;
        }

        .kpi-grid,
        .tabs-row,
        .stats-grid,
        .sov-grid,
        .tag-row,
        .action-row,
        .capability-row,
        .message-meta,
        .suggestion-row,
        .notification-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .kpi-card {
          padding: 16px;
          display: grid;
          gap: 8px;
        }

        .kpi-card span,
        .mini-stat span,
        .preview-row span,
        .sov-card span {
          color: var(--muted);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          font-weight: 700;
        }

        .kpi-card strong,
        .mini-stat strong,
        .sov-card strong {
          font-size: 28px;
        }

        .tabs-row {
          gap: 8px;
        }

        .tab-btn.active {
          background: color-mix(in oklab, var(--brand-accent) 18%, transparent);
          border-color: color-mix(in oklab, var(--brand-accent) 68%, var(--line));
        }

        .panel-grid {
          display: grid;
          gap: 16px;
        }

        .panel-grid.two-col,
        .panel-grid.social-grid {
          grid-template-columns: 0.92fr 1.08fr;
        }

        .workspace-card {
          padding: 18px;
          display: grid;
          gap: 16px;
        }

        .card-head {
          display: flex;
          justify-content: space-between;
          align-items: start;
          gap: 12px;
        }

        .head-actions {
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }

        .pill,
        .capability-pill {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 7px 10px;
          background: color-mix(in oklab, var(--brand-accent) 20%, transparent);
          color: var(--fg);
          font-size: 11px;
          font-weight: 700;
        }

        .capability-pill.subtle {
          background: rgba(255, 255, 255, 0.05);
          color: var(--muted);
        }

        .provider-list,
        .notification-list,
        .message-list,
        .competitor-table,
        .account-grid {
          display: grid;
          gap: 12px;
        }

        .provider-row,
        .notification-row,
        .competitor-row,
        .account-card,
        .message-card,
        .sov-card,
        .mini-stat {
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.03);
        }

        .provider-row,
        .notification-row,
        .competitor-row,
        .account-card-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .provider-row p,
        .account-card p,
        .notification-row p,
        .message-card p,
        .empty-state,
        .preview-row,
        .account-description {
          margin: 0;
          color: var(--muted);
          line-height: 1.5;
          font-family: var(--brand-font-subtitle, inherit);
        }

        .account-card {
          display: grid;
          gap: 10px;
        }

        .account-metrics,
        .preview-stack {
          display: grid;
          gap: 8px;
        }

        .brand-preview-stack {
          border: 1px solid color-mix(in oklab, var(--brand-accent) 44%, var(--line));
          border-radius: 14px;
          padding: 12px;
          background: linear-gradient(
            135deg,
            color-mix(in oklab, var(--brand-secondary) 24%, transparent),
            rgba(255, 255, 255, 0.02)
          );
        }

        .social-platforms-board {
          gap: 18px;
        }

        .social-board-head {
          display: flex;
          justify-content: space-between;
          align-items: start;
          gap: 12px;
          padding-bottom: 14px;
          border-bottom: 1px solid var(--line);
        }

        .board-copy {
          margin: 8px 0 0;
          color: var(--muted);
        }

        .provider-section-list {
          display: grid;
          gap: 14px;
          max-height: 860px;
          overflow: auto;
          padding-right: 6px;
        }

        .provider-section {
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 14px;
          display: grid;
          gap: 12px;
          background: rgba(255, 255, 255, 0.03);
        }

        .provider-section-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .provider-section-head h3,
        .provider-section-head p {
          margin: 0;
        }

        .provider-section-head p {
          color: var(--muted);
          margin-top: 4px;
        }

        .provider-actions {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
        }

        .provider-account-tiles {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(min(100%, 180px), 1fr));
          gap: 10px;
        }

        .linked-account-tile {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 12px;
          display: grid;
          justify-items: center;
          gap: 6px;
          background: rgba(255, 255, 255, 0.03);
          text-align: center;
        }

        .linked-account-tile strong,
        .linked-account-tile p {
          margin: 0;
        }

        .linked-account-tile p {
          color: var(--muted);
          font-size: 12px;
        }

        .linked-avatar {
          width: 48px;
          height: 48px;
          border-radius: 999px;
          display: grid;
          place-items: center;
          font-weight: 800;
          color: #eef0f4;
          background: linear-gradient(135deg, #b45309, #dc2626);
        }

        .unlink-btn {
          background: transparent;
          border: none;
          color: #ef4444;
          cursor: pointer;
          font-weight: 700;
          padding: 0;
        }

        .form-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .form-grid.compact {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .form-grid .full {
          grid-column: 1 / -1;
        }

        .feature-list {
          margin: 0;
          padding-left: 18px;
          display: grid;
          gap: 10px;
          color: var(--muted);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .message-card,
        .notification-row,
        .competitor-row {
          display: grid;
          gap: 10px;
        }

        .result-box {
          margin: 0;
          padding: 12px;
          border-radius: 14px;
          background: rgba(0, 0, 0, 0.12);
          color: var(--muted);
          font-size: 12px;
          white-space: pre-wrap;
          overflow: auto;
        }

        @media (max-width: 1180px) {
          .calendar-board,
          .manager-highlight-grid,
          .kpi-grid,
          .stats-grid,
          .panel-grid.two-col,
          .panel-grid.social-grid,
          .form-grid.compact {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 820px) {
          .workspace-hero,
          .kpi-grid,
          .stats-grid,
          .calendar-board,
          .manager-highlight-grid,
          .panel-grid.two-col,
          .panel-grid.social-grid,
          .form-grid,
          .form-grid.compact {
            grid-template-columns: 1fr;
          }

          .insight-row {
            grid-template-columns: 1fr;
          }

          .provider-row,
          .notification-row,
          .competitor-row,
          .card-head,
          .account-card-head,
          .provider-section-head,
          .social-board-head {
            align-items: start;
            flex-direction: column;
          }

          .logo-preview-grid {
            grid-template-columns: 1fr;
          }

          .voiceover-filters {
            grid-template-columns: 1fr;
          }

          .avatar-filters {
            grid-template-columns: 1fr;
          }

          .voiceover-footer {
            flex-direction: column;
            align-items: start;
          }

          .creative-stepper,
          .post-type-grid,
          .library-actions,
          .creative-preview-modal {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </main>
  );
}
