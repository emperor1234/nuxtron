'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type Dispatch,
  type DragEvent,
  type SetStateAction,
} from 'react';
import { DEFAULT_TENANT_ID, apiGet, apiSend, invalidateTenantGetCache } from '@/app/lib/platform-api';
import { CanvaBridgePanel } from './canva-bridge-panel';
import { buildCanvaBridgePresetDraft } from './canva-bridge-presets';

type MediaType = 'image' | 'video' | 'voice' | 'text';
type Complexity = 'auto' | 'simple' | 'standard' | 'advanced';
type BusyState = 'idle' | 'planning' | 'generating' | 'topup';

type StudioCategory = {
  id: string;
  title: string;
  summary: string;
  capability: string;
  mediaType: MediaType;
  deliveryMode: string;
  outputs: string[];
};

type SocialOpsModuleId =
  | 'accounts'
  | 'autonomous'
  | 'trends'
  | 'calendar'
  | 'kpi'
  | 'approvals'
  | 'inbox'
  | 'ugc'
  | 'browser_capture'
  | 'mobile'
  | 'optimization'
  | 'manychat';

type SocialOpsModule = {
  id: SocialOpsModuleId;
  title: string;
  summary: string;
  icon: string;
};

type ModuleVisualTheme = {
  heroBorder: string;
  heroBackground: string;
  glowOne: string;
  glowTwo: string;
  focusBorder: string;
  focusBackground: string;
};

type UploadZone = 'image' | 'video' | 'audio';
type UploadProgressState = Record<UploadZone, number>;
type UploadFileProgress = { id: string; name: string; progressPct: number };

type Toast = {
  id: string;
  message: string;
  tone: 'success' | 'error' | 'info' | 'warning';
};

const UPLOAD_ZONE_ORDER: UploadZone[] = ['image', 'video', 'audio'];

type SocialAccount = {
  id: number;
  network: string;
  account_name: string;
  handle: string;
  status?: string;
};

type ScheduledSocialPost = {
  id: string;
  platform: string;
  text: string;
  publish_at: string;
  status: string;
};

type ApprovalRequestItem = {
  id: number;
  status: string;
  scheduled_post_id: number;
  platform: string;
  content_preview: string;
  approval_levels?: string[];
};

type SavedReplyItem = {
  id: number;
  title: string;
  body: string;
  category: string;
  created_at: string;
};

type ContactViewItem = {
  handle: string;
  display_name: string;
  message_count: number;
  last_message_at: string;
  sentiment: string;
  networks: string[];
};

type InboxListItem = {
  id: string;
  network: string;
  source: string;
  content: string;
  sentiment: string;
  state: string;
  assignedTo?: string;
  responded?: boolean;
};

type ReplySuggestionItem = {
  action: 'rephrase' | 'shorten' | 'formal' | 'casual';
  label: string;
  result: string;
  provider: string;
};

type InboxTriageSuggestion = {
  action: 'claim' | 'complete' | 'review';
  label: string;
  reason: string;
};

type CanvaImportJob = {
  id: number;
  account_id: number;
  design_id?: string;
  design_url?: string;
  resolved_media_url: string;
  post_id: number;
  status: string;
  created_at: string;
};

type CanvaPublishMode = 'auto' | 'now' | 'draft';

function toDisplayText(value: unknown, fallback = ''): string {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function parseInboxMessageId(value: string): number | null {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildAvailableInboxMessageIdSet(items: InboxListItem[]): Set<number> {
  const ids = new Set<number>();
  for (const item of items) {
    const parsedId = parseInboxMessageId(item.id);
    if (parsedId !== null) {
      ids.add(parsedId);
    }
  }
  return ids;
}

function resolveInboxMessageId(previous: string, items: InboxListItem[]): string {
  if (previous && items.some((item) => item.id === previous)) {
    return previous;
  }
  return items[0]?.id || previous;
}

type ProviderHealth = { name: string; status: string };

type WorkspaceOverview = {
  creditBalance: number;
  pendingTopups: number;
  walletBalanceUsd: number;
  recentTransactions: number;
  providers: ProviderHealth[];
};

type ProviderPlan = {
  provider: string;
  quality: string;
  cost_rank: number;
  supports: string[];
};

type OrchestrationPlan = {
  capability: string;
  media_type: MediaType;
  complexity: string;
  estimated_credits: number;
  recommended_provider: ProviderPlan;
  provider_candidates: ProviderPlan[];
  workflow: string[];
  quality_policy: string;
  channel_targets: string[];
  edit_tools: string[];
  brand_rules: string[];
};

type GeneratedAsset = {
  id: string;
  type: MediaType;
  title: string;
  content: string;
  mediaUrl?: string;
  createdAt: string;
  provider: string;
  credits: number;
};

type ActivityItem = {
  id: string;
  label: string;
  tone: 'info' | 'success' | 'warning' | 'error';
  createdAt: string;
};

type QuoteResponse = {
  quote: { credits: number; total_usd: number; unit_price_usd: number };
};

type CheckoutResponse = {
  invoice: { id: number; amount: number; payment_reference: string; status: string };
};

type UsageResponse = {
  credit_balance: number;
  pending_credit_topups?: number;
};

type WalletResponse = {
  wallet?: { available_balance_usd?: number; recent_transactions?: unknown[] };
};

type HealthResponse = Record<string, { status?: string }>;

type GenerationResponse = {
  status: string;
  job_id?: string;
  error?: string;
  content?: string;
  media_url?: string;
  orchestration_plan?: OrchestrationPlan;
  estimated_credits?: number;
};

type ABVariant = {
  id: string;
  name: string;
  prompt_hook: string;
  copy: string;
  cta: string;
  predicted_ctr: number;
  predicted_roas: number;
};

type CopyVariation = {
  id: string;
  hook: string;
  headline: string;
  cta: string;
  estimated_ctr: number;
};

type HubspotFeature = {
  id: string;
  title: string;
  summary: string;
  href: string;
};

type ABTestingSession = {
  id: string;
  name: string;
  variants: ABVariant[];
  status: 'draft' | 'running' | 'completed';
  channel: string;
  created_at: string;
  results?: Record<string, { clicks: number; conversions: number; ctr: number; roas: number }>;
};

type CalendarEvent = {
  id: string;
  date: string;
  channel: string;
  asset_id: string;
  status: 'scheduled' | 'published' | 'failed';
  scheduled_time?: string;
  published_at?: string;
};

type ContentCalendarState = {
  events: CalendarEvent[];
  selected_date?: string;
  view_mode: 'month' | 'week' | 'day';
};

type BrandColor = {
  name: string;
  hex: string;
  usage: string;
};

type BrandFont = {
  name: string;
  category: string;
  weights?: string[];
  usage: string;
};

type BrandKit = {
  id: string;
  name: string;
  colors: BrandColor[];
  fonts: BrandFont[];
  logo_url?: string;
  brand_voice?: string;
  industry?: string;
  created_at: string;
};

type VoiceoverStyle = {
  name: string;
  gender: string;
  language: string;
  accent: string;
  tone: string;
};

type VoiceoverConfig = {
  enabled: boolean;
  style: VoiceoverStyle;
  speed: number;
  pitch: number;
  emotion?: string;
};

type PerformancePrediction = {
  estimated_ctr: number;
  estimated_roas: number;
  estimated_engagement_rate: number;
  confidence_score: number;
  top_hooks: string[];
  improvement_suggestions: string[];
};

type AnimationEffect = {
  id: string;
  name: string;
  category: string;
  duration: number;
  preview_url?: string;
  compatible_formats: string[];
};

type CompetitorAnalysis = {
  id: string;
  competitor_name: string;
  estimated_reach?: number;
  avg_engagement_rate: number;
  avg_comments?: number;
  top_ads: Array<{
    id: string;
    ctr: number;
    hook: string;
    visual_style: string;
  }>;
  trending_hooks: string[];
  gap_opportunities?: string[];
  average_ctr: number;
  common_styles: string[];
  analyzed_at: string;
};

type ParityContentListItem = {
  id: string;
  title?: string;
  caption?: string;
  platforms?: string[];
  status?: string;
  scheduled_for?: string | null;
};

function mapParityContentItemToScheduledPost(item: ParityContentListItem): ScheduledSocialPost | null {
  const scheduledFor = typeof item.scheduled_for === 'string' ? item.scheduled_for : '';
  if (!item.id || !scheduledFor) {
    return null;
  }

  const platforms = Array.isArray(item.platforms) ? item.platforms : [];
  const firstPlatform = platforms[0] || 'instagram';
  const title = typeof item.title === 'string' ? item.title : '';
  const caption = typeof item.caption === 'string' ? item.caption : '';

  return {
    id: item.id,
    platform: firstPlatform,
    text: caption || title || 'Untitled scheduled post',
    publish_at: scheduledFor,
    status: typeof item.status === 'string' ? item.status : 'scheduled',
  };
}
type BulkGenerationJob = {
  id: string;
  name: string;
  total_items: number;
  completed_items: number;
  total_count?: number;
  completed_count?: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  results?: GeneratedAsset[];
};

const STUDIO_CATEGORIES: StudioCategory[] = [
  {
    id: 'music',
    title: 'Music Generator',
    summary: 'Build hooks, beds, stems, and sonic branding.',
    capability: 'music',
    mediaType: 'voice',
    deliveryMode: 'music-stems',
    outputs: ['Theme stem', 'Hook loop', 'Voice bed'],
  },
  {
    id: 'sound-design',
    title: 'Sound Design',
    summary: 'Craft SFX, transitions, podcasts, and layered polish.',
    capability: 'sound',
    mediaType: 'voice',
    deliveryMode: 'audio-design',
    outputs: ['SFX pack', 'Podcast polish', 'Narration mix'],
  },
  {
    id: 'faceless-video',
    title: 'Faceless Video Engine',
    summary: 'Produce faceless explainers, motion narratives, and reels.',
    capability: 'faceless-video',
    mediaType: 'video',
    deliveryMode: 'faceless-video',
    outputs: ['Storyboard', 'Generated cut', 'Channel variants'],
  },
  {
    id: 'ar',
    title: 'AR Experience Studio',
    summary: 'Generate augmented overlays and product try-ons.',
    capability: 'ar',
    mediaType: 'video',
    deliveryMode: 'immersive-layer',
    outputs: ['AR concept', 'Interaction pass', 'Mobile export'],
  },
  {
    id: 'vr',
    title: 'VR World Builder',
    summary: 'Plan spatial stories and immersive launch worlds.',
    capability: 'vr',
    mediaType: 'video',
    deliveryMode: 'spatial-story',
    outputs: ['Environment concept', 'Scene sequence', 'Spatial notes'],
  },
  {
    id: 'hologram',
    title: 'Hologram Stage',
    summary: 'Create volumetric promo loops and keynote overlays.',
    capability: 'hologram',
    mediaType: 'video',
    deliveryMode: 'hologram-sequence',
    outputs: ['Stage loop', 'Projection guide', 'Backdrop package'],
  },
  {
    id: 'short-video',
    title: 'Short Video Lab',
    summary: 'Ship high-volume short-form production at speed.',
    capability: 'short-video',
    mediaType: 'video',
    deliveryMode: 'short-form',
    outputs: ['Primary cut', 'Hook variants', 'Caption pack'],
  },
  {
    id: 'reels',
    title: 'Reels Factory',
    summary: 'Build native reels for Meta, TikTok, and Shorts.',
    capability: 'reels',
    mediaType: 'video',
    deliveryMode: 'reel-campaign',
    outputs: ['Reel master', 'Loop endings', 'Thumbnail frames'],
  },
  {
    id: 'images',
    title: 'Image Direction',
    summary: 'Generate campaign stills, product shots, and hero art.',
    capability: 'image',
    mediaType: 'image',
    deliveryMode: 'campaign-still',
    outputs: ['Hero still', 'Alt crop set', 'Brand export'],
  },
  {
    id: 'slides',
    title: 'Image Slides',
    summary: 'Create carousel slides and swipe-ready sequences.',
    capability: 'slides',
    mediaType: 'image',
    deliveryMode: 'carousel',
    outputs: ['Slide series', 'Narrative order', 'Overlay frames'],
  },
  {
    id: 'blogs',
    title: 'Blog Studio',
    summary: 'Draft long-form blogs and channel-ready editorial packs.',
    capability: 'blog',
    mediaType: 'text',
    deliveryMode: 'editorial',
    outputs: ['Blog draft', 'Email excerpt', 'Caption pack'],
  },
  {
    id: 'avatars',
    title: 'Avatar Builder',
    summary: 'Design digital presenters and branded spokespeople.',
    capability: 'avatar',
    mediaType: 'image',
    deliveryMode: 'avatar-system',
    outputs: ['Avatar concept', 'Pose set', 'Style sheet'],
  },
  {
    id: 'templates',
    title: 'Template System',
    summary: 'Create reusable brand templates for evergreen campaigns.',
    capability: 'template',
    mediaType: 'image',
    deliveryMode: 'template-system',
    outputs: ['Master template', 'Editable variants', 'Brand constraints'],
  },
  {
    id: 'editing',
    title: 'Editing Suite',
    summary: 'Post-process, resize, caption, and refine existing media.',
    capability: 'edit',
    mediaType: 'video',
    deliveryMode: 'editing-pass',
    outputs: ['Edit timeline', 'Resize set', 'Publishing bundle'],
  },
];

const CHANNEL_OPTIONS = ['Instagram', 'TikTok', 'YouTube', 'X', 'LinkedIn', 'Pinterest', 'Blog', 'Email'];
const BRAND_RULE_OPTIONS = ['Brand-safe', 'Copyright-safe', 'Performance-first', 'Platform-native', 'Premium finish'];
const EDIT_TOOL_OPTIONS = [
  'Auto resize',
  'Caption sync',
  'Background cleanup',
  'Color grade',
  'Hook rewrite',
  'Slide sequencing',
  'Voice polish',
  'Thumbnail frame',
];
const HUBSPOT_FEATURES: HubspotFeature[] = [
  {
    id: 'crm',
    title: 'HubSpot CRM',
    summary: 'Sync leads and deal context for campaign personalization in social workflows.',
    href: '/hubspot-e2e#hubspot-product-completion',
  },
  {
    id: 'automation',
    title: 'Marketing Automation',
    summary: 'Connect campaign outcomes to automation flows and lifecycle stages.',
    href: '/hubspot-e2e#how-it-works',
  },
  {
    id: 'academy',
    title: 'HubSpot Knowledge Base',
    summary: 'Operational docs for campaign setup, contacts, and reporting best practices.',
    href: '/hubspot-e2e#validation-boundaries',
  },
  {
    id: 'api',
    title: 'HubSpot Developer Platform',
    summary: 'Use API docs to wire custom sync, attribution, and event ingestion.',
    href: '/hubspot-e2e',
  },
];
const CATEGORY_THEMES = [
  { icon: '🎵', color: '#4c8dff' },
  { icon: '🧾', color: '#2bd97f' },
  { icon: '📊', color: '#ffb41f' },
  { icon: '🗓️', color: '#64748b' },
  { icon: '📈', color: '#ff5f6d' },
  { icon: '🧠', color: '#14c4e6' },
  { icon: '🎬', color: '#7d8cff' },
  { icon: '📱', color: '#2dd4bf' },
  { icon: '🖼️', color: 'var(--brand)' },
  { icon: '📚', color: '#34d399' },
  { icon: '✍️', color: '#f59e0b' },
  { icon: '🧑', color: '#0ea5e9' },
  { icon: '🧩', color: '#fb7185' },
  { icon: '✂️', color: '#22d3ee' },
];
const MODULE_PRESETS: Record<string, ModulePreset> = {
  music: {
    complexity: 'standard',
    channels: ['YouTube', 'Instagram', 'TikTok'],
    brandRules: ['Brand-safe', 'Premium finish'],
    editTools: ['Voice polish', 'Hook rewrite'],
    prompt: 'Compose a premium launch hook, an ambient bed, and a branded sonic signature with cutdown variations.',
  },
  'sound-design': {
    complexity: 'standard',
    channels: ['YouTube', 'Instagram'],
    brandRules: ['Brand-safe', 'Copyright-safe'],
    editTools: ['Voice polish', 'Background cleanup'],
    prompt: 'Design cinematic SFX layers and transitions for social content intros, product reveals, and CTA moments.',
  },
  'faceless-video': {
    complexity: 'advanced',
    channels: ['TikTok', 'YouTube', 'Instagram'],
    brandRules: ['Performance-first', 'Platform-native'],
    editTools: ['Caption sync', 'Hook rewrite', 'Thumbnail frame'],
    prompt:
      'Create a faceless explainer sequence with a 3-second hook, visual pacing markers, and channel-specific edits.',
  },
  ar: {
    complexity: 'advanced',
    channels: ['Instagram', 'TikTok'],
    brandRules: ['Platform-native', 'Premium finish'],
    editTools: ['Color grade', 'Auto resize'],
    prompt: 'Generate an AR activation concept with overlays, interaction cues, and a mobile-first export strategy.',
  },
  vr: {
    complexity: 'advanced',
    channels: ['YouTube', 'Blog'],
    brandRules: ['Premium finish', 'Brand-safe'],
    editTools: ['Color grade', 'Background cleanup'],
    prompt: 'Build an immersive VR world storyboard with scene transitions, narrative beats, and launch teaser edits.',
  },
  hologram: {
    complexity: 'advanced',
    channels: ['YouTube', 'Instagram'],
    brandRules: ['Premium finish', 'Brand-safe'],
    editTools: ['Color grade', 'Caption sync'],
    prompt: 'Produce a hologram-style stage loop package including projection-safe layers and speaking overlays.',
  },
  'short-video': {
    complexity: 'standard',
    channels: ['TikTok', 'Instagram', 'YouTube'],
    brandRules: ['Performance-first', 'Platform-native'],
    editTools: ['Caption sync', 'Hook rewrite', 'Auto resize'],
    prompt: 'Generate short-form videos with high-retention hooks, rapid cuts, and CTA-driven endings.',
  },
  reels: {
    complexity: 'standard',
    channels: ['Instagram', 'TikTok', 'YouTube'],
    brandRules: ['Platform-native', 'Performance-first'],
    editTools: ['Thumbnail frame', 'Caption sync', 'Auto resize'],
    prompt: 'Create reel-native edits with trend-aware pacing, loop endings, and alternate hook variants.',
  },
  images: {
    complexity: 'standard',
    channels: ['Instagram', 'Pinterest', 'LinkedIn'],
    brandRules: ['Brand-safe', 'Premium finish'],
    editTools: ['Color grade', 'Background cleanup'],
    prompt: 'Generate premium campaign stills with product clarity, brand color consistency, and alternate crops.',
  },
  slides: {
    complexity: 'simple',
    channels: ['Instagram', 'LinkedIn', 'Blog'],
    brandRules: ['Brand-safe', 'Platform-native'],
    editTools: ['Slide sequencing', 'Caption sync'],
    prompt: 'Build a carousel slide sequence with narrative flow, strong opening frame, and concise panel copy.',
  },
  blogs: {
    complexity: 'standard',
    channels: ['Blog', 'Email', 'LinkedIn'],
    brandRules: ['Brand-safe', 'Copyright-safe'],
    editTools: ['Hook rewrite', 'Caption sync'],
    prompt: 'Draft a long-form blog with thought-leadership tone, data-backed sections, and repurposable snippets.',
  },
  avatars: {
    complexity: 'advanced',
    channels: ['YouTube', 'Instagram', 'LinkedIn'],
    brandRules: ['Brand-safe', 'Premium finish'],
    editTools: ['Color grade', 'Voice polish'],
    prompt: 'Design a branded avatar presenter kit with pose variants, expression set, and visual style guardrails.',
  },
  templates: {
    complexity: 'simple',
    channels: ['Instagram', 'LinkedIn', 'Email'],
    brandRules: ['Brand-safe', 'Performance-first'],
    editTools: ['Auto resize', 'Thumbnail frame'],
    prompt:
      'Create reusable template systems for recurring campaigns with locked brand zones and editable text blocks.',
  },
  editing: {
    complexity: 'standard',
    channels: ['Instagram', 'TikTok', 'YouTube'],
    brandRules: ['Platform-native', 'Premium finish'],
    editTools: ['Auto resize', 'Caption sync', 'Color grade', 'Background cleanup'],
    prompt:
      'Run an editing pass for social delivery: resize, caption, color-balance, and export platform-ready variants.',
  },
};
const SOCIAL_OPS_MODULES: SocialOpsModule[] = [
  {
    id: 'accounts',
    title: 'Account Connect',
    summary: 'Connect Instagram, TikTok, YouTube, X, and LinkedIn in one click.',
    icon: '🔗',
  },
  {
    id: 'autonomous',
    title: 'AI Post Manager',
    summary: 'Generate, preview, and publish autonomous social posts.',
    icon: '🤖',
  },
  {
    id: 'trends',
    title: 'Trends & Listening',
    summary: 'Track mentions, sentiment clusters, and competitor signals.',
    icon: '📡',
  },
  {
    id: 'calendar',
    title: 'Drag Calendar',
    summary: 'Schedule campaigns and drag-drop posts to any day/time.',
    icon: '🗓️',
  },
  {
    id: 'kpi',
    title: 'KPI + ROI Forecast',
    summary: 'Visualize growth metrics, engagement velocity, and ROI outlook.',
    icon: '📈',
  },
  { id: 'approvals', title: 'Approval Pipeline', summary: 'Run smart approval chains before publication.', icon: '✅' },
  { id: 'inbox', title: 'Smart Inbox', summary: 'Engage replies and comments with AI-assisted actions.', icon: '💬' },
  {
    id: 'ugc',
    title: 'UGC Management',
    summary: 'Review creator assets, manage rights approvals, and republish approved content.',
    icon: '🎞️',
  },
  {
    id: 'browser_capture',
    title: 'Browser Capture',
    summary: 'Capture web research, screenshots, and notes into queued posts.',
    icon: '🧭',
  },
  {
    id: 'mobile',
    title: 'Mobile Ops',
    summary: 'Register devices, draft from mobile, and sync offline actions.',
    icon: '📲',
  },
  {
    id: 'optimization',
    title: 'AI Optimization',
    summary: 'Predict top slots, score variants, and generate performance-driven captions.',
    icon: '🧠',
  },
  {
    id: 'manychat',
    title: 'Manychat Automations',
    summary: 'Build flows, keywords, broadcasts, and drip sequences with audience tags.',
    icon: '🧩',
  },
];
const SOCIAL_OPS_ACCENT_BY_ID: Record<SocialOpsModuleId, string> = {
  accounts: '#6366f1',
  autonomous: '#22c55e',
  trends: '#f59e0b',
  calendar: '#2563eb',
  kpi: '#ef4444',
  approvals: '#06b6d4',
  inbox: '#2dd4bf',
  ugc: '#f97316',
  browser_capture: '#78716c',
  mobile: '#22c55e',
  optimization: '#f59e0b',
  manychat: '#0ea5e9',
};

const SOCIAL_OPS_ROUTE_BY_MODULE_ID: Record<SocialOpsModuleId, string> = {
  accounts: 'social-accounts',
  autonomous: 'social-posts',
  trends: 'social-trends',
  calendar: 'social-calendar',
  kpi: 'social-analytics',
  approvals: 'social-approvals',
  inbox: 'social-inbox',
  ugc: 'social-ugc',
  browser_capture: 'social-studio/browser-capture',
  mobile: 'social-studio/mobile',
  optimization: 'social-studio/optimization',
  manychat: 'social-studio/manychat',
};

const SOCIAL_OPS_MODULE_ID_BY_ROUTE_SEGMENT: Partial<Record<string, SocialOpsModuleId>> = Object.fromEntries(
  Object.entries(SOCIAL_OPS_ROUTE_BY_MODULE_ID).map(([id, segment]) => [segment, id as SocialOpsModuleId])
);
const STUDIO_MODULE_ROUTE_BY_CATEGORY_ID: Record<string, string> = {
  music: 'music-generator',
  'sound-design': 'sound-design',
  'faceless-video': 'faceless-video-engine',
  ar: 'ar-experience-studio',
  vr: 'vr-world-builder',
  hologram: 'hologram-stage',
  'short-video': 'short-video-factory',
  reels: 'reels-factory',
  images: 'image-direction',
  slides: 'image-slider',
  blogs: 'blog-studio',
  avatars: 'avatar-builder',
  templates: 'template-system',
  editing: 'editing-suite',
};
const STUDIO_CATEGORY_ID_BY_ROUTE_SEGMENT: Record<string, string> = Object.fromEntries(
  Object.entries(STUDIO_MODULE_ROUTE_BY_CATEGORY_ID).map(([categoryId, routeSegment]) => [routeSegment, categoryId])
);
function hexToRgbChannels(hex: string): string {
  const normalized = hex.replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return '76, 141, 255';
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `${r}, ${g}, ${b}`;
}

function createModuleVisualFromHex(accentHex: string): ModuleVisualTheme {
  const rgb = hexToRgbChannels(accentHex);
  return {
    heroBorder: accentHex,
    heroBackground: `linear-gradient(135deg, color-mix(in oklab, ${accentHex} 24%, #eef0f4) 0%, color-mix(in oklab, ${accentHex} 16%, #eef0f4) 52%, color-mix(in oklab, ${accentHex} 56%, #6366f1) 130%)`,
    glowOne: `rgba(${rgb}, 0.28)`,
    glowTwo: `rgba(${rgb}, 0.18)`,
    focusBorder: `color-mix(in oklab, ${accentHex} 42%, var(--line))`,
    focusBackground: `linear-gradient(180deg, color-mix(in oklab, ${accentHex} 34%, #0f1f3f) 0%, color-mix(in oklab, ${accentHex} 20%, #0d1a34) 100%)`,
  };
}

const CATEGORY_ACCENT_BY_ID: Record<string, string> = Object.fromEntries(
  STUDIO_CATEGORIES.map((category, index) => [
    category.id,
    CATEGORY_THEMES[index % CATEGORY_THEMES.length]?.color ?? '#4c8dff',
  ])
);

const CATEGORY_SECONDARY_ACCENT_BY_ID: Record<string, string> = Object.fromEntries(
  STUDIO_CATEGORIES.map((category, index) => [
    category.id,
    CATEGORY_THEMES[(index + 1) % CATEGORY_THEMES.length]?.color ?? '#2bd97f',
  ])
);

const DEFAULT_STUDIO_MODULE_VISUAL: ModuleVisualTheme = createModuleVisualFromHex('#4c8dff');

const STUDIO_MODULE_VISUAL_BY_CATEGORY_ID: Record<string, ModuleVisualTheme> = Object.fromEntries(
  Object.entries(CATEGORY_ACCENT_BY_ID).map(([categoryId, accentHex]) => [
    categoryId,
    createModuleVisualFromHex(accentHex),
  ])
) as Record<string, ModuleVisualTheme>;
const DENSITY_STORAGE_KEY = 'nuxtron.socialStudio.density';
const CATEGORY_STORAGE_KEY = 'nuxtron.socialStudio.category';
const EXPECTED_GENERATION_SECONDS = 75;
const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type CommandAction = {
  id: string;
  title: string;
  shortcut: string;
  disabled: boolean;
  run: () => void;
};

type ModulePreset = {
  complexity: Complexity;
  channels: string[];
  brandRules: string[];
  editTools: string[];
  prompt: string;
};

type CommandShortcutsConfig = {
  isCommandPaletteOpen: boolean;
  filteredCommandActions: CommandAction[];
  closePalette: () => void;
  openPalette: () => void;
  triggerShortcutAction: (key: string) => boolean;
};

function useCommandShortcuts({
  isCommandPaletteOpen,
  filteredCommandActions,
  closePalette,
  openPalette,
  triggerShortcutAction,
}: CommandShortcutsConfig) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();
      if (target?.isContentEditable || tagName === 'input' || tagName === 'textarea' || tagName === 'select') return;

      const key = event.key.toLowerCase();
      if (isCommandPaletteOpen) {
        if (key === 'escape' || key === '/') {
          closePalette();
          event.preventDefault();
          return;
        }
        if (key === 'enter') {
          const action = filteredCommandActions.find((item) => !item.disabled);
          if (action) {
            closePalette();
            action.run();
            event.preventDefault();
          }
          return;
        }
      }

      if (key === '/') {
        openPalette();
        event.preventDefault();
        return;
      }

      if (!triggerShortcutAction(key)) return;
      event.preventDefault();
    }

    globalThis.addEventListener('keydown', onKeyDown);
    return () => {
      globalThis.removeEventListener('keydown', onKeyDown);
    };
  }, [closePalette, filteredCommandActions, isCommandPaletteOpen, openPalette, triggerShortcutAction]);
}

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--line)',
  background: 'rgba(255, 255, 255, 0.02)',
  color: 'var(--text)',
};

function toggleSelection(items: string[], value: string): string[] {
  return items.includes(value) ? items.filter((item) => item !== value) : [...items, value];
}

function toDateTimeLocalValue(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function hoursFromNowIso(hours: number): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

function readString(value: unknown, fallback: string) {
  return typeof value === 'string' ? value : fallback;
}

function readNumber(value: unknown, fallback = 0) {
  return typeof value === 'number' ? value : fallback;
}

function buildSeoTileStyle(accent: string, isHovered: boolean, isActive = false): CSSProperties {
  const isEmphasized = isHovered || isActive;
  return {
    background: isEmphasized
      ? `linear-gradient(135deg, ${accent}1f 0%, rgba(148,163,184,0.10) 75%)`
      : 'var(--bg-soft, #eef0f4)',
    border: isEmphasized ? `1px solid ${accent}` : `1px solid ${accent}44`,
    borderRadius: 16,
    padding: 18,
    minHeight: 188,
    display: 'grid',
    gap: 8,
    alignContent: 'start',
    transform: isEmphasized ? 'translateY(-4px)' : 'translateY(0)',
    boxShadow: isEmphasized ? `0 14px 28px ${accent}33, 0 0 0 1px ${accent}22 inset` : '0 2px 8px rgba(148,163,184,0.10)',
    transition: 'transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.2s ease',
  };
}

function buildSeoIconStyle(isHovered: boolean, isActive = false): CSSProperties {
  return {
    fontSize: 28,
    lineHeight: 1,
    transform: isHovered || isActive ? 'scale(1.08)' : 'scale(1)',
    transition: 'transform 0.18s ease',
  };
}

function buildSeoSummaryStyle(isHovered: boolean, isActive = false): CSSProperties {
  return {
    color: isHovered || isActive ? 'var(--muted)' : 'var(--muted)',
    fontSize: 12,
    lineHeight: 1.55,
    transition: 'color 0.18s ease',
  };
}

function buildSeoArrowStyle(accent: string, isHovered: boolean, isActive = false): CSSProperties {
  return {
    color: accent,
    fontSize: 14,
    fontWeight: 900,
    opacity: isHovered || isActive ? 1 : 0,
    transform: isHovered || isActive ? 'translateX(0)' : 'translateX(-6px)',
    transition: 'opacity 0.18s ease, transform 0.18s ease',
  };
}

function downloadAsset(item: GeneratedAsset) {
  if (item.mediaUrl) {
    let extension = 'txt';
    if (item.type === 'image') extension = 'png';
    if (item.type === 'video') extension = 'mp4';
    if (item.type === 'voice') extension = 'wav';
    const link = document.createElement('a');
    link.href = item.mediaUrl;
    link.download = `${item.id}.${extension}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }

  const blob = new Blob([item.content], { type: 'text/plain;charset=utf-8' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `${item.id}.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoke after a short tick to allow the browser to initiate the download.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function previewPlanAction(args: {
  tenantId: string;
  buildRequestPayload: () => Record<string, unknown>;
  setBusy: (value: BusyState) => void;
  setStatusLabel: (value: string) => void;
  setLastError: (value: string) => void;
  setPlan: (value: OrchestrationPlan | null) => void;
  setGenerated: Dispatch<SetStateAction<GeneratedAsset[]>>;
  selectedCategory: StudioCategory;
  prompt: string;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
}) {
  const {
    tenantId,
    buildRequestPayload,
    setBusy,
    setStatusLabel,
    setLastError,
    setPlan,
    setGenerated,
    selectedCategory,
    prompt,
    addActivity,
  } = args;
  setBusy('planning');
  setStatusLabel('Planning provider route');
  setLastError('');
  try {
    const response = await apiSend<{ plan: OrchestrationPlan }>(
      '/ai/social-studio/plan',
      'POST',
      buildRequestPayload(),
      tenantId
    );
    setPlan(response.plan);
    setGenerated((previous) => [
      {
        id: `preview-${Date.now()}`,
        type: selectedCategory.mediaType,
        title: `${selectedCategory.title} preview`,
        content: `Preview ready for ${selectedCategory.title}.\n\nBrief:\n${prompt.trim() || 'No brief provided.'}\n\nSuggested workflow:\n${response.plan.workflow.slice(0, 4).join(' -> ')}`,
        createdAt: new Date().toLocaleString(),
        provider: response.plan.recommended_provider.provider,
        credits: response.plan.estimated_credits,
      },
      ...previous,
    ]);
    addActivity(`Plan ready: ${response.plan.recommended_provider.provider} for ${response.plan.capability}.`, 'info');
  } catch (error) {
    setLastError(error instanceof Error ? error.message : 'Plan request failed.');
  } finally {
    setBusy('idle');
    setStatusLabel('Ready');
  }
}

async function requestQuoteAction(args: {
  tenantId: string;
  topupCredits: string;
  setBusy: (value: BusyState) => void;
  setLastError: (value: string) => void;
  setQuote: (value: QuoteResponse['quote'] | null) => void;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
}) {
  const { tenantId, topupCredits, setBusy, setLastError, setQuote, addActivity } = args;
  setBusy('topup');
  setLastError('');
  try {
    const response = await apiSend<QuoteResponse>(
      '/billing/credits/quote',
      'POST',
      { amount: Number.parseInt(topupCredits, 10) || 0 },
      tenantId
    );
    setQuote(response.quote);
    addActivity(
      `Quote ready for ${response.quote.credits} credits at $${response.quote.total_usd.toFixed(2)}.`,
      'info'
    );
  } catch (error) {
    setLastError(error instanceof Error ? error.message : 'Could not quote credits.');
  } finally {
    setBusy('idle');
  }
}

async function checkoutCreditsAction(args: {
  tenantId: string;
  topupCredits: string;
  setBusy: (value: BusyState) => void;
  setLastError: (value: string) => void;
  setCheckout: (value: CheckoutResponse['invoice'] | null) => void;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
  loadWorkspace: () => Promise<void>;
}) {
  const { tenantId, topupCredits, setBusy, setLastError, setCheckout, addActivity, loadWorkspace } = args;
  setBusy('topup');
  setLastError('');
  try {
    const response = await apiSend<CheckoutResponse>(
      '/billing/credits/checkout',
      'POST',
      {
        amount: Number.parseInt(topupCredits, 10) || 0,
        payment_provider: 'manual',
        payment_method_id: 'studio-social-topup',
      },
      tenantId
    );
    setCheckout(response.invoice);
    addActivity(`Pending payment created: ${response.invoice.payment_reference}.`, 'warning');
    await loadWorkspace();
  } catch (error) {
    setLastError(error instanceof Error ? error.message : 'Could not create credit checkout.');
  } finally {
    setBusy('idle');
  }
}

async function confirmCreditsAction(args: {
  tenantId: string;
  checkout: CheckoutResponse['invoice'];
  setBusy: (value: BusyState) => void;
  setLastError: (value: string) => void;
  setCheckout: (value: CheckoutResponse['invoice'] | null) => void;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
  loadWorkspace: () => Promise<void>;
}) {
  const { tenantId, checkout, setBusy, setLastError, setCheckout, addActivity, loadWorkspace } = args;
  setBusy('topup');
  setLastError('');
  try {
    await apiSend(
      '/billing/credits/confirm',
      'POST',
      {
        invoice_id: checkout.id,
        payment_reference: checkout.payment_reference,
        provider_transaction_id: `manual-${checkout.id}`,
        amount_usd: checkout.amount,
      },
      tenantId
    );
    setCheckout(null);
    addActivity('Payment confirmed and credits applied.', 'success');
    await loadWorkspace();
  } catch (error) {
    setLastError(error instanceof Error ? error.message : 'Credit confirmation failed.');
  } finally {
    setBusy('idle');
  }
}

function stopPollingAction(args: {
  pollRef: { current: ReturnType<typeof setInterval> | null };
  setPollElapsedSeconds: (value: number) => void;
  setBusy: (value: BusyState) => void;
  setStatusLabel: (value: string) => void;
}) {
  const { pollRef, setPollElapsedSeconds, setBusy, setStatusLabel } = args;
  if (pollRef.current) {
    clearInterval(pollRef.current);
    pollRef.current = null;
  }
  setPollElapsedSeconds(0);
  setBusy('idle');
  setStatusLabel('Ready');
}

function handleGenerationSuccessAction(args: {
  result: GenerationResponse;
  plan: OrchestrationPlan | null;
  setPlan: (value: OrchestrationPlan | null) => void;
  setGenerated: Dispatch<SetStateAction<GeneratedAsset[]>>;
  selectedCategory: StudioCategory;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
  tenantId: string;
  loadWorkspace: () => Promise<void>;
}) {
  const { result, plan, setPlan, setGenerated, selectedCategory, addActivity, tenantId, loadWorkspace } = args;
  const resolvedPlan = result.orchestration_plan ?? plan;
  if (resolvedPlan) setPlan(resolvedPlan);
  setGenerated((previous) => [
    {
      id: `${Date.now()}`,
      type: selectedCategory.mediaType,
      title: `${selectedCategory.title} output`,
      content: result.content || `Generated ${selectedCategory.title.toLowerCase()} asset.`,
      mediaUrl: result.media_url,
      createdAt: new Date().toLocaleString(),
      provider: resolvedPlan?.recommended_provider.provider || 'auto',
      credits: result.estimated_credits || resolvedPlan?.estimated_credits || 0,
    },
    ...previous,
  ]);
  addActivity(`Generation completed via ${resolvedPlan?.recommended_provider.provider || 'auto route'}.`, 'success');
  invalidateTenantGetCache(tenantId);
  void loadWorkspace();
}

function startPollingAction(args: {
  jobId: string;
  tenantId: string;
  pollRef: { current: ReturnType<typeof setInterval> | null };
  setPollElapsedSeconds: (value: number) => void;
  setStatusLabel: (value: string) => void;
  stopPolling: () => void;
  handleGenerationSuccess: (result: GenerationResponse) => void;
  setLastError: (value: string) => void;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
  loadWorkspace: () => Promise<void>;
}) {
  const {
    jobId,
    tenantId,
    pollRef,
    setPollElapsedSeconds,
    setStatusLabel,
    stopPolling,
    handleGenerationSuccess,
    setLastError,
    addActivity,
    loadWorkspace,
  } = args;
  let attempts = 0;
  setPollElapsedSeconds(0);
  pollRef.current = setInterval(() => {
    attempts += 1;
    void (async () => {
      try {
        const response = await fetch(`/api/fastapi/ai/social-studio/job/${jobId}`, {
          headers: { 'X-Tenant-Id': tenantId },
        });
        const result = (await response.json()) as GenerationResponse;
        if (result.status === 'pending') {
          setPollElapsedSeconds(attempts * 5);
          setStatusLabel(`Generating (${attempts * 5}s)`);
          return;
        }
        stopPolling();
        if (result.status === 'success') {
          handleGenerationSuccess(result);
          return;
        }
        invalidateTenantGetCache(tenantId);
        void loadWorkspace();
        setLastError(result.error || 'Generation failed.');
        addActivity(result.error || 'Generation failed.', 'error');
      } catch (error) {
        stopPolling();
        setLastError(error instanceof Error ? error.message : 'Polling failed.');
      }
    })();
  }, 5000);
}

async function generateAction(args: {
  prompt: string;
  setPollElapsedSeconds: (value: number) => void;
  setBusy: (value: BusyState) => void;
  setStatusLabel: (value: string) => void;
  setLastError: (value: string) => void;
  tenantId: string;
  buildFormData: () => FormData;
  zoneUploadTotals: UploadProgressState;
  setUploadProgress: (value: UploadProgressState) => void;
  setUploadLoadedBytes: (value: UploadProgressState) => void;
  setPlan: (value: OrchestrationPlan | null) => void;
  addActivity: (label: string, tone: ActivityItem['tone']) => void;
  startPolling: (jobId: string) => void;
  handleGenerationSuccess: (result: GenerationResponse) => void;
  loadWorkspace: () => Promise<void>;
}) {
  const {
    prompt,
    setPollElapsedSeconds,
    setBusy,
    setStatusLabel,
    setLastError,
    tenantId,
    buildFormData,
    zoneUploadTotals,
    setUploadProgress,
    setUploadLoadedBytes,
    setPlan,
    addActivity,
    startPolling,
    handleGenerationSuccess,
    loadWorkspace,
  } = args;
  if (!prompt.trim()) return;
  setPollElapsedSeconds(0);
  setBusy('generating');
  setStatusLabel('Submitting workload');
  setLastError('');
  setUploadProgress({ image: 0, video: 0, audio: 0 });
  setUploadLoadedBytes({ image: 0, video: 0, audio: 0 });
  try {
    const formData = buildFormData();
    const result = await new Promise<{ statusCode: number; body: GenerationResponse }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/fastapi/ai/social-studio/generate');
      xhr.setRequestHeader('X-Tenant-Id', tenantId);
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        const maximum = totalUploadBytes(zoneUploadTotals);
        if (maximum <= 0) return;
        const loadedBytes = Math.min(maximum, event.loaded);
        setUploadLoadedBytes(calculateLoadedBytesByZone(loadedBytes, zoneUploadTotals));
        setUploadProgress(calculateUploadProgressByZone(loadedBytes, zoneUploadTotals));
      };
      xhr.onerror = () => reject(new Error('Network error while uploading request assets.'));
      xhr.onload = () => {
        try {
          const parsed = JSON.parse(xhr.responseText || '{}') as GenerationResponse;
          resolve({ statusCode: xhr.status, body: parsed });
        } catch {
          reject(new Error('Invalid response payload from generation API.'));
        }
      };
      xhr.send(formData);
    });

    const completedBytes = totalUploadBytes(zoneUploadTotals);
    setUploadLoadedBytes(calculateLoadedBytesByZone(completedBytes, zoneUploadTotals));
    setUploadProgress(calculateUploadProgressByZone(completedBytes, zoneUploadTotals));
    const responseStatus = result.statusCode;
    const responseBody = result.body;
    if (responseStatus >= 400 || responseBody.status === 'error') {
      setBusy('idle');
      setStatusLabel('Ready');
      invalidateTenantGetCache(tenantId);
      void loadWorkspace();
      const backendError = responseBody.error || `Generation backend unavailable (${responseStatus}).`;
      const strictMessage = IS_STRICT_NO_MOCK_MODE
        ? `${backendError} Strict no-mock mode blocked local fallback.`
        : `${backendError} Fail-closed mode blocked local fallback.`;
      setLastError(strictMessage);
      addActivity(strictMessage, 'error');
      return;
    }
    if (responseBody.orchestration_plan) setPlan(responseBody.orchestration_plan);
    if (responseBody.status === 'pending' && responseBody.job_id) {
      invalidateTenantGetCache(tenantId);
      void loadWorkspace();
      setStatusLabel('Rendering and packaging');
      addActivity(
        `Workload queued with ${responseBody.orchestration_plan?.recommended_provider.provider || 'auto route'}.`,
        'info'
      );
      startPolling(responseBody.job_id);
      return;
    }
    setBusy('idle');
    setStatusLabel('Ready');
    handleGenerationSuccess(responseBody);
  } catch (error) {
    setBusy('idle');
    setStatusLabel('Ready');
    const backendError = error instanceof Error ? error.message : 'Unable to reach the AI backend.';
    const strictMessage = IS_STRICT_NO_MOCK_MODE
      ? `${backendError} Strict no-mock mode blocked local fallback.`
      : `${backendError} Fail-closed mode blocked local fallback.`;
    setLastError(strictMessage);
    addActivity(strictMessage, 'error');
  }
}

// eslint-disable-next-line sonarjs/cognitive-complexity
export default function SocialStudioPage() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewButtonRef = useRef<HTMLButtonElement | null>(null);
  const generateButtonRef = useRef<HTMLButtonElement | null>(null);
  const quoteButtonRef = useRef<HTMLButtonElement | null>(null);
  const checkoutButtonRef = useRef<HTMLButtonElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [selectedCategoryId, setSelectedCategoryId] = useState(STUDIO_CATEGORIES[0].id);
  const [prompt, setPrompt] = useState(
    'Build a flagship launch sequence with crisp hooks, premium visuals, and reusable outputs.'
  );
  const [complexity, setComplexity] = useState<Complexity>('auto');
  const [targetChannels, setTargetChannels] = useState<string[]>(['Instagram', 'TikTok', 'YouTube']);
  const [brandRules, setBrandRules] = useState<string[]>(['Brand-safe', 'Performance-first']);
  const [editTools, setEditTools] = useState<string[]>(['Auto resize', 'Caption sync', 'Thumbnail frame']);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [videoFiles, setVideoFiles] = useState<File[]>([]);
  const [audioFiles, setAudioFiles] = useState<File[]>([]);
  const [uploadDragZone, setUploadDragZone] = useState<UploadZone | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState>({ image: 0, video: 0, audio: 0 });
  const [uploadLoadedBytes, setUploadLoadedBytes] = useState<UploadProgressState>({ image: 0, video: 0, audio: 0 });
  const [overview, setOverview] = useState<WorkspaceOverview>({
    creditBalance: 0,
    pendingTopups: 0,
    walletBalanceUsd: 0,
    recentTransactions: 0,
    providers: [],
  });
  const [plan, setPlan] = useState<OrchestrationPlan | null>(null);
  const [generated, setGenerated] = useState<GeneratedAsset[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [busy, setBusy] = useState<BusyState>('idle');
  const [statusLabel, setStatusLabel] = useState('Ready');
  const [lastError, setLastError] = useState('');
  const [topupCredits, setTopupCredits] = useState('500');
  const [quote, setQuote] = useState<QuoteResponse['quote'] | null>(null);
  const [checkout, setCheckout] = useState<CheckoutResponse['invoice'] | null>(null);
  const [density, setDensity] = useState<'comfortable' | 'compact'>('comfortable');
  const [isPageReady, setIsPageReady] = useState(false);
  const [hoveredModuleId, setHoveredModuleId] = useState<string | null>(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState('');
  const [pollElapsedSeconds, setPollElapsedSeconds] = useState(0);
  const [activeOpsModuleId, setActiveOpsModuleId] = useState<SocialOpsModuleId>('accounts');
  const [opsLoading, setOpsLoading] = useState(false);
  const [opsMessage, setOpsMessage] = useState('');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [calendarDragOverDay, setCalendarDragOverDay] = useState<string | null>(null);
  const [socialCatalog, setSocialCatalog] = useState<Array<{ network: string; label: string }>>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [canvaAccountId, setCanvaAccountId] = useState('');
  const [canvaDesignId, setCanvaDesignId] = useState('');
  const [canvaDesignUrl, setCanvaDesignUrl] = useState('');
  const [canvaHeadline, setCanvaHeadline] = useState('Canva design');
  const [canvaCaption, setCanvaCaption] = useState('Imported from Canva');
  const [canvaPublishMode, setCanvaPublishMode] = useState<CanvaPublishMode>('draft');
  const [canvaPublishAt, setCanvaPublishAt] = useState(toDateTimeLocalValue(hoursFromNowIso(2)));
  const [canvaImportBusy, setCanvaImportBusy] = useState(false);
  const [canvaImportMessage, setCanvaImportMessage] = useState('');
  const [canvaImports, setCanvaImports] = useState<CanvaImportJob[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledSocialPost[]>([]);
  const [listeningSummary, setListeningSummary] = useState<Record<string, unknown> | null>(null);
  const [listeningMentions, setListeningMentions] = useState<Array<Record<string, unknown>>>([]);
  const [listeningClusters, setListeningClusters] = useState<Array<Record<string, unknown>>>([]);
  const [approvalRequests, setApprovalRequests] = useState<ApprovalRequestItem[]>([]);
  const [approvalLevels, setApprovalLevels] = useState('manager,legal');
  const [workspaceOpsOverview, setWorkspaceOpsOverview] = useState<Record<string, number>>({});
  const [autopilotResult, setAutopilotResult] = useState<Record<string, unknown> | null>(null);
  const [draggedPostId, setDraggedPostId] = useState<string | null>(null);
  const [connectNetwork, setConnectNetwork] = useState('instagram');
  const [connectAccountName, setConnectAccountName] = useState('Nuxtron Social Account');
  const [connectHandle, setConnectHandle] = useState('nuxtron_official');
  const [postHeadline, setPostHeadline] = useState('AI-driven launch update');
  const [postCaption, setPostCaption] = useState('Rolling out new autonomous social workflows with measurable ROI.');
  const [postMode, setPostMode] = useState<CanvaPublishMode>('auto');
  const [postPublishAt, setPostPublishAt] = useState(toDateTimeLocalValue(hoursFromNowIso(4)));
  const [postMediaUrl, setPostMediaUrl] = useState('');
  const [schedulePlatform, setSchedulePlatform] = useState('linkedin');
  const [scheduleText, setScheduleText] = useState('Campaign teaser: premium social growth is now live.');
  const [schedulePublishAt, setSchedulePublishAt] = useState(toDateTimeLocalValue(hoursFromNowIso(6)));
  const [scheduleMediaUrl, setScheduleMediaUrl] = useState('');
  const [movePostId, setMovePostId] = useState('');
  const [movePublishAt, setMovePublishAt] = useState(toDateTimeLocalValue(hoursFromNowIso(12)));
  const [approvalPostId, setApprovalPostId] = useState('');
  const [approvalPlatform, setApprovalPlatform] = useState('linkedin');
  const [approvalPreview, setApprovalPreview] = useState('Approval request: finalize cross-platform launch post.');
  const [approvalRequestedBy, setApprovalRequestedBy] = useState('social-manager');
  const [inboxMessageId, setInboxMessageId] = useState('1');
  const [inboxReplyText, setInboxReplyText] = useState(
    'Thanks for reaching out. We will share a detailed follow-up shortly.'
  );
  const [savedReplies, setSavedReplies] = useState<SavedReplyItem[]>([]);
  const [savedReplyEditingId, setSavedReplyEditingId] = useState<number | null>(null);
  const [savedReplyTitle, setSavedReplyTitle] = useState('VIP follow-up');
  const [savedReplyCategory, setSavedReplyCategory] = useState('vip');
  const [savedReplyBody, setSavedReplyBody] = useState(
    'Thanks for the note. We have routed this to the partnership team.'
  );
  const [contactViews, setContactViews] = useState<ContactViewItem[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxListItem[]>([]);
  const [selectedInboxMessageIds, setSelectedInboxMessageIds] = useState<number[]>([]);
  const [bulkInboxActionLoading, setBulkInboxActionLoading] = useState(false);
  const [selectedContactHandle, setSelectedContactHandle] = useState('');
  const [inboxContactQuery, setInboxContactQuery] = useState('');
  const [inboxSentimentFilter, setInboxSentimentFilter] = useState('all');
  const [messageHistory, setMessageHistory] = useState<Array<Record<string, unknown>>>([]);
  const [inboxClaimAgentName, setInboxClaimAgentName] = useState('Social Desk');
  const [replySuggestions, setReplySuggestions] = useState<ReplySuggestionItem[]>([]);
  const [replySuggestionsLoading, setReplySuggestionsLoading] = useState(false);
  const [dmChatbotLoading, setDmChatbotLoading] = useState(false);
  const [lastInboxSyncAt, setLastInboxSyncAt] = useState('');
  const [previewAssetIndex, setPreviewAssetIndex] = useState(0);
  const [bulkGenerationCount, setBulkGenerationCount] = useState('5');
  const [copyGenerationTone, setCopyGenerationTone] = useState('casual');
  const [abTestingVariants, setAbTestingVariants] = useState<ABVariant[]>([]);
  const [copyVariations, setCopyVariations] = useState<CopyVariation[]>([]);

  // ── NEW PREDIS.AI FEATURE STATES ───────────────────────────────────────
  const [activeAbTest] = useState<ABTestingSession | null>(null);
  const [brandKits, setBrandKits] = useState<BrandKit[]>([]);
  const [activeBrandKit, setActiveBrandKit] = useState<BrandKit | null>(null);
  const [contentCalendar, setContentCalendar] = useState<ContentCalendarState>({ events: [], view_mode: 'month' });
  const [performancePredictions, setPerformancePredictions] = useState<PerformancePrediction | null>(null);
  const [animationEffects, setAnimationEffects] = useState<AnimationEffect[]>([]);
  const [selectedAnimationEffect, setSelectedAnimationEffect] = useState<AnimationEffect | null>(null);
  const [competitorAnalysis, setCompetitorAnalysis] = useState<CompetitorAnalysis | null>(null);
  const [bulkGenerationJobs, setBulkGenerationJobs] = useState<BulkGenerationJob[]>([]);
  const [activeBulkJob, setActiveBulkJob] = useState<BulkGenerationJob | null>(null);

  // ── PANEL TOGGLE BOOLEANS ─────────────────────────────────────────────
  const [showAbTestPanel, setShowAbTestPanel] = useState(false);
  const [showCopyGeneratorPanel, setShowCopyGeneratorPanel] = useState(false);
  const [showBrandKitPanel, setShowBrandKitPanel] = useState(false);
  const [showContentCalendarPanel, setShowContentCalendarPanel] = useState(false);
  const [showVoiceoverPanel, setShowVoiceoverPanel] = useState(false);
  const [showPerformanceAnalysisPanel, setShowPerformanceAnalysisPanel] = useState(false);
  const [showAnimationEffectsPanel, setShowAnimationEffectsPanel] = useState(false);
  const [showCompetitorAnalysisPanel, setShowCompetitorAnalysisPanel] = useState(false);
  const [showBulkGenerationPanel, setShowBulkGenerationPanel] = useState(false);
  const [showMemeGeneratorPanel, setShowMemeGeneratorPanel] = useState(false);
  const [showQuoteToPostPanel, setShowQuoteToPostPanel] = useState(false);
  const [showHolidayPostPanel, setShowHolidayPostPanel] = useState(false);
  const [showEcommercePostPanel, setShowEcommercePostPanel] = useState(false);
  const [showAssetLibraryPanel, setShowAssetLibraryPanel] = useState(false);
  const [showChatIdeationPanel, setShowChatIdeationPanel] = useState(false);
  const hasAnyPredisPanelOpen =
    showMemeGeneratorPanel ||
    showQuoteToPostPanel ||
    showHolidayPostPanel ||
    showEcommercePostPanel ||
    showAssetLibraryPanel ||
    showChatIdeationPanel ||
    showBrandKitPanel ||
    showVoiceoverPanel ||
    showPerformanceAnalysisPanel ||
    showAnimationEffectsPanel ||
    showCompetitorAnalysisPanel ||
    showBulkGenerationPanel ||
    showAbTestPanel ||
    showCopyGeneratorPanel ||
    showContentCalendarPanel;

  // ── MEME GENERATOR ────────────────────────────────────────────────────
  const [memeTemplate, setMemeTemplate] = useState('distracted-boyfriend');
  const [memeTopText, setMemeTopText] = useState('');
  const [memeBottomText, setMemeBottomText] = useState('');
  const [memeCaption, setMemeCaption] = useState('');
  const [generatedMeme, setGeneratedMeme] = useState<{
    id: string;
    image_url: string;
    caption: string;
    hashtags: string[];
  } | null>(null);

  // ── QUOTE TO POST ────────────────────────────────────────────────────
  const [quoteText, setQuoteText] = useState('');
  const [quoteAuthor, setQuoteAuthor] = useState('');
  const [quoteStyle, setQuoteStyle] = useState('modern-card');
  const [generatedQuotePost, setGeneratedQuotePost] = useState<{
    id: string;
    caption: string;
    visual_suggestion: string;
    hashtags: string[];
    image_url: string;
  } | null>(null);

  // ── HOLIDAY POST ─────────────────────────────────────────────────────
  const [holidayName, setHolidayName] = useState('');
  const [holidayTheme, setHolidayTheme] = useState('celebration');
  const [generatedHolidayPost, setGeneratedHolidayPost] = useState<{
    id: string;
    caption: string;
    visual_style: string;
    cta: string;
    hashtags: string[];
    image_url: string;
  } | null>(null);

  // ── ECOMMERCE POST ───────────────────────────────────────────────────
  const [ecomProductUrl, setEcomProductUrl] = useState('');
  const [ecomProductName, setEcomProductName] = useState('');
  const [ecomProductPrice, setEcomProductPrice] = useState('');
  const [ecomDiscount, setEcomDiscount] = useState('');
  const [generatedEcomPost, setGeneratedEcomPost] = useState<{
    id: string;
    caption: string;
    headline: string;
    cta: string;
    hashtags: string[];
    image_url: string;
  } | null>(null);

  // ── ASSET LIBRARY ────────────────────────────────────────────────────
  const [assetLibraryQuery, setAssetLibraryQuery] = useState('');
  const [assetLibraryCategory, setAssetLibraryCategory] = useState('all');
  const [assetLibraryResults, setAssetLibraryResults] = useState<
    { id: string; url: string; thumb_url: string; title: string; type: string; tags: string[] }[]
  >([]);
  const [assetLibraryPage, setAssetLibraryPage] = useState(1);
  const [assetLibraryTotal, setAssetLibraryTotal] = useState(0);

  // ── AI CHAT IDEATION ─────────────────────────────────────────────────
  const [chatMessages, setChatMessages] = useState<
    { role: 'user' | 'assistant'; content: string; timestamp: string }[]
  >([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSessionId] = useState(() => `chat-${Date.now()}`);

  // ── VOICEOVER LAB ────────────────────────────────────────────────────
  const [voiceoverText, setVoiceoverText] = useState('');
  const [voiceoverSpeed, setVoiceoverSpeed] = useState(1);
  const [voiceoverPitch, setVoiceoverPitch] = useState(1);
  const [voiceoverEmotion, setVoiceoverEmotion] = useState('neutral');
  const [voiceoverVoiceName, setVoiceoverVoiceName] = useState('Liam');
  const [voiceoverResult, setVoiceoverResult] = useState<{
    voiceover_url: string;
    duration_ms: number;
    word_count: number;
  } | null>(null);

  // ── PERFORMANCE AI ───────────────────────────────────────────────────
  const [perfChannel, setPerfChannel] = useState('instagram');
  const [perfMediaType, setPerfMediaType] = useState('image');

  // ── ANIMATION FX ─────────────────────────────────────────────────────
  const [animationTarget, setAnimationTarget] = useState('');

  // ── BULK GENERATOR ───────────────────────────────────────────────────
  const [bulkPrompt, setBulkPrompt] = useState('');
  const [bulkMediaType, setBulkMediaType] = useState('image');
  const [bulkCount, setBulkCount] = useState('5');

  // ── COPY GENERATOR ───────────────────────────────────────────────────
  const [copyGenerationCategory, setCopyGenerationCategory] = useState('ecommerce');
  const [copyGenerationProduct, setCopyGenerationProduct] = useState('');

  // ── BRAND KIT ────────────────────────────────────────────────────────
  const [brandKitName, setBrandKitName] = useState('');
  const [brandKitColors] = useState<BrandColor[]>([{ name: 'Primary', hex: '#6366f1', usage: 'CTA buttons' }]);
  const [brandKitFonts] = useState<BrandFont[]>([{ name: 'Inter', category: 'sans-serif', usage: 'Body text' }]);

  // ── CONTENT CALENDAR ─────────────────────────────────────────────────
  const [calendarSelectedDate, setCalendarSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  // ── COMPETITOR INTEL ─────────────────────────────────────────────────
  const [competitorUrl, setCompetitorUrl] = useState('');

  const activeRouteSegment = useMemo(() => {
    const segments = pathname.split('/');
    for (let i = segments.length - 1; i >= 0; i -= 1) {
      if (segments[i]) return segments[i];
    }
    return '';
  }, [pathname]);
  const routeSelectedCategoryId = useMemo(
    () => STUDIO_CATEGORY_ID_BY_ROUTE_SEGMENT[activeRouteSegment] ?? null,
    [activeRouteSegment]
  );
  const routeOpsModuleId = useMemo(
    () => SOCIAL_OPS_MODULE_ID_BY_ROUTE_SEGMENT[activeRouteSegment] ?? null,
    [activeRouteSegment]
  );
  const selectedPredisPanel = useMemo(() => (searchParams.get('panel') || '').trim().toLowerCase(), [searchParams]);
  const effectiveOpsModuleId: SocialOpsModuleId = routeOpsModuleId ?? activeOpsModuleId;
  const isStudioModulePage = routeSelectedCategoryId !== null;
  const activeVisualCategoryId = routeSelectedCategoryId ?? selectedCategoryId;
  const activeAccent = CATEGORY_ACCENT_BY_ID[activeVisualCategoryId] ?? '#4c8dff';
  const activeAccentSecondary = CATEGORY_SECONDARY_ACCENT_BY_ID[activeVisualCategoryId] ?? '#2bd97f';
  const activeAccentRgb = hexToRgbChannels(activeAccent);
  const activeAccentSecondaryRgb = hexToRgbChannels(activeAccentSecondary);
  const moduleVisual = useMemo(
    () =>
      isStudioModulePage
        ? (STUDIO_MODULE_VISUAL_BY_CATEGORY_ID[activeVisualCategoryId] ?? DEFAULT_STUDIO_MODULE_VISUAL)
        : DEFAULT_STUDIO_MODULE_VISUAL,
    [activeVisualCategoryId, isStudioModulePage]
  );
  const moduleVisualStyle = useMemo(
    () =>
      ({
        '--module-accent': activeAccent,
        '--module-accent-2': activeAccentSecondary,
        '--module-accent-rgb': activeAccentRgb,
        '--module-accent-2-rgb': activeAccentSecondaryRgb,
        '--module-hero-border': moduleVisual.heroBorder,
        '--module-hero-bg': moduleVisual.heroBackground,
        '--module-glow-one': moduleVisual.glowOne,
        '--module-glow-two': moduleVisual.glowTwo,
        '--module-focus-border': moduleVisual.focusBorder,
        '--module-focus-bg': moduleVisual.focusBackground,
      }) as CSSProperties,
    [activeAccent, activeAccentRgb, activeAccentSecondary, activeAccentSecondaryRgb, moduleVisual]
  );

  const selectedCategory = useMemo(
    () => STUDIO_CATEGORIES.find((category) => category.id === selectedCategoryId) ?? STUDIO_CATEGORIES[0],
    [selectedCategoryId]
  );
  const hasPlan = plan !== null;
  const totalReferenceFiles = imageFiles.length + videoFiles.length + audioFiles.length;
  const imageReadiness = useMemo(() => calculateUploadReadiness(imageFiles), [imageFiles]);
  const videoReadiness = useMemo(() => calculateUploadReadiness(videoFiles), [videoFiles]);
  const audioReadiness = useMemo(() => calculateUploadReadiness(audioFiles), [audioFiles]);
  const zoneUploadTotals = useMemo<UploadProgressState>(
    () => ({
      image: imageFiles.reduce((sum, file) => sum + file.size, 0),
      video: videoFiles.reduce((sum, file) => sum + file.size, 0),
      audio: audioFiles.reduce((sum, file) => sum + file.size, 0),
    }),
    [audioFiles, imageFiles, videoFiles]
  );
  const imageProgressValue =
    busy === 'generating' && zoneUploadTotals.image > 0 ? uploadProgress.image : imageReadiness;
  const videoProgressValue =
    busy === 'generating' && zoneUploadTotals.video > 0 ? uploadProgress.video : videoReadiness;
  const audioProgressValue =
    busy === 'generating' && zoneUploadTotals.audio > 0 ? uploadProgress.audio : audioReadiness;
  const imageProgressLabel =
    busy === 'generating' && zoneUploadTotals.image > 0
      ? `${uploadProgress.image}% uploaded`
      : `${imageReadiness}% ready`;
  const videoProgressLabel =
    busy === 'generating' && zoneUploadTotals.video > 0
      ? `${uploadProgress.video}% uploaded`
      : `${videoReadiness}% ready`;
  const audioProgressLabel =
    busy === 'generating' && zoneUploadTotals.audio > 0
      ? `${uploadProgress.audio}% uploaded`
      : `${audioReadiness}% ready`;
  const imageFileUploadRows = useMemo(
    () => buildFileUploadRows(imageFiles, uploadLoadedBytes.image),
    [imageFiles, uploadLoadedBytes.image]
  );
  const videoFileUploadRows = useMemo(
    () => buildFileUploadRows(videoFiles, uploadLoadedBytes.video),
    [videoFiles, uploadLoadedBytes.video]
  );
  const audioFileUploadRows = useMemo(
    () => buildFileUploadRows(audioFiles, uploadLoadedBytes.audio),
    [audioFiles, uploadLoadedBytes.audio]
  );
  const totalGeneratedCredits = generated.reduce((sum, item) => sum + item.credits, 0);
  const shouldShowOutputSkeleton = generated.length === 0 && busy === 'generating';
  const currentPreviewAsset = generated[previewAssetIndex] ?? null;
  const hasMultipleGenerated = generated.length > 1;
  let previewStatusLabel = 'Live preview';
  if (hasMultipleGenerated) previewStatusLabel = `${previewAssetIndex + 1} of ${generated.length}`;
  else if (generated.length === 1) previewStatusLabel = '1 generated';
  const generationProgressPct = Math.min(95, Math.round((pollElapsedSeconds / EXPECTED_GENERATION_SECONDS) * 100));
  const generationEtaSeconds = Math.max(0, EXPECTED_GENERATION_SECONDS - pollElapsedSeconds);

  const addToast = useCallback((message: string, tone: Toast['tone']) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const remove = (prev: Toast[]) => prev.filter((t) => t.id !== id);
    setToasts((previous) => [...previous, { id, message, tone }]);
    setTimeout(() => setToasts(remove), 4000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  const triggerShortcutAction = useCallback((key: string) => {
    switch (key) {
      case 'p':
        previewButtonRef.current?.click();
        return true;
      case 'g':
        generateButtonRef.current?.click();
        return true;
      case 'q':
        quoteButtonRef.current?.click();
        return true;
      case 'k':
        checkoutButtonRef.current?.click();
        return true;
      case 'c':
        confirmButtonRef.current?.click();
        return true;
      case 'd':
        setDensity((previous) => (previous === 'comfortable' ? 'compact' : 'comfortable'));
        return true;
      default:
        return false;
    }
  }, []);

  function addActivity(label: string, tone: ActivityItem['tone']) {
    setActivity((previous) =>
      [
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          label,
          tone,
          createdAt: new Date().toLocaleTimeString(),
        },
        ...previous,
      ].slice(0, 8)
    );
  }

  const loadInboxOpsData = useCallback(async () => {
    const [accountsRes, overviewRes, repliesRes, contactsRes, inboxRes] = await Promise.all([
      apiGet<{ accounts?: SocialAccount[] }>('/social/accounts', tenantId),
      apiGet<{ overview?: Record<string, number> }>('/social/workspace/overview', tenantId),
      apiGet<{ items?: SavedReplyItem[] }>('/social/inbox/saved-replies', tenantId),
      apiGet<{ items?: ContactViewItem[] }>('/social/inbox/contact-views', tenantId),
      apiGet<{ items?: InboxListItem[] }>('/social/inbox', tenantId),
    ]);
    setSocialAccounts(accountsRes.accounts || []);
    setWorkspaceOpsOverview(overviewRes.overview || {});
    setSavedReplies(repliesRes.items || []);

    const nextContactViews = contactsRes.items || [];
    const nextInboxItems = inboxRes.items || [];
    const availableMessageIds = buildAvailableInboxMessageIdSet(nextInboxItems);

    setContactViews(nextContactViews);
    setInboxItems(nextInboxItems);
    setSelectedInboxMessageIds((previous) => previous.filter((messageId) => availableMessageIds.has(messageId)));
    setSelectedContactHandle((prev) => prev || nextContactViews[0]?.handle || '');
    setInboxMessageId((previous) => resolveInboxMessageId(previous, nextInboxItems));
    setLastInboxSyncAt(new Date().toLocaleTimeString());
  }, [tenantId]);

  const loadCanvaImports = useCallback(async () => {
    try {
      const response = await apiGet<{ jobs?: CanvaImportJob[] }>('/social/integrations/canva/imports', tenantId);
      setCanvaImports(response.jobs || []);
    } catch (error) {
      setCanvaImportMessage(error instanceof Error ? error.message : 'Unable to load Canva imports.');
    }
  }, [tenantId]);

  const submitCanvaImport = useCallback(async () => {
    const selectedAccount =
      socialAccounts.find((account) => String(account.id) === canvaAccountId) ?? socialAccounts[0] ?? null;
    if (!selectedAccount) {
      setCanvaImportMessage('Connect a social account before importing from Canva.');
      return;
    }

    if (!canvaDesignId.trim() && !canvaDesignUrl.trim()) {
      setCanvaImportMessage('Provide a Canva design ID or design URL.');
      return;
    }

    setCanvaImportBusy(true);
    setCanvaImportMessage('');
    try {
      const response = await apiSend<{ job: CanvaImportJob; post: Record<string, unknown> }>(
        '/social/integrations/canva/import',
        'POST',
        {
          account_id: selectedAccount.id,
          design_id: canvaDesignId.trim() || undefined,
          design_url: canvaDesignUrl.trim() || undefined,
          caption: canvaCaption.trim(),
          headline: canvaHeadline.trim(),
          target_network: selectedAccount.network,
          publish_mode: canvaPublishMode,
          publish_at: canvaPublishMode === 'draft' ? undefined : canvaPublishAt,
        }
      );
      setCanvaImports((previous) => [response.job, ...previous.filter((item) => item.id !== response.job.id)]);
      setCanvaImportMessage(`Imported Canva asset into scheduled post ${response.job.post_id}.`);
      addToast('Canva import completed', 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Canva import failed.';
      setCanvaImportMessage(message);
      addToast(message, 'error');
    } finally {
      setCanvaImportBusy(false);
    }
  }, [
    addToast,
    canvaAccountId,
    canvaCaption,
    canvaDesignId,
    canvaDesignUrl,
    canvaHeadline,
    canvaPublishAt,
    canvaPublishMode,
    socialAccounts,
  ]);

  const loadSocialOpsData = useCallback(
    async (moduleId: SocialOpsModuleId) => {
      setOpsLoading(true);
      setOpsMessage('');
      try {
        if (moduleId === 'accounts') {
          const [catalogRes, accountsRes] = await Promise.all([
            apiGet<{ providers?: Array<{ network?: string; label?: string }> }>('/social/accounts/catalog', tenantId),
            apiGet<{ accounts?: SocialAccount[] }>('/social/accounts', tenantId),
          ]);
          setSocialCatalog(
            (catalogRes.providers || []).map((provider) => ({
              network: String(provider.network || ''),
              label: String(provider.label || provider.network || ''),
            }))
          );
          setSocialAccounts(accountsRes.accounts || []);
          if ((catalogRes.providers || []).length > 0) {
            setConnectNetwork(String(catalogRes.providers?.[0]?.network || 'instagram'));
          }
          return;
        }

        if (moduleId === 'autonomous') {
          const accountsRes = await apiGet<{ accounts?: SocialAccount[] }>('/social/accounts', tenantId);
          setSocialAccounts(accountsRes.accounts || []);
          return;
        }

        if (moduleId === 'trends') {
          const [summaryRes, mentionsRes, clustersRes, overviewRes] = await Promise.all([
            apiGet<{ summary?: Record<string, unknown> }>('/social/listening/summary', tenantId),
            apiGet<{ mentions?: Array<Record<string, unknown>> }>('/social/listening/mentions', tenantId),
            apiGet<{ clusters?: Array<Record<string, unknown>> }>('/social/listening/clusters', tenantId),
            apiGet<{ overview?: Record<string, number> }>('/social/workspace/overview', tenantId),
          ]);
          setListeningSummary(summaryRes.summary || null);
          setListeningMentions(mentionsRes.mentions || []);
          setListeningClusters(clustersRes.clusters || []);
          setWorkspaceOpsOverview(overviewRes.overview || {});
          return;
        }

        if (moduleId === 'calendar') {
          const postsRes = await apiGet<{ items?: ParityContentListItem[] }>(
            '/api/v1/social/content/list?status=scheduled',
            tenantId
          );
          const items = Array.isArray(postsRes.items)
            ? postsRes.items
                .map((item) => mapParityContentItemToScheduledPost(item))
                .filter((item): item is ScheduledSocialPost => Boolean(item))
            : [];
          setScheduledPosts(items);
          return;
        }

        if (moduleId === 'kpi') {
          const [overviewRes, summaryRes] = await Promise.all([
            apiGet<{ overview?: Record<string, number> }>('/social/workspace/overview', tenantId),
            apiGet<{ summary?: Record<string, unknown> }>('/social/listening/summary', tenantId),
          ]);
          setWorkspaceOpsOverview(overviewRes.overview || {});
          setListeningSummary(summaryRes.summary || null);
          return;
        }

        if (moduleId === 'approvals') {
          const requestsRes = await apiGet<{ requests?: ApprovalRequestItem[] }>(
            '/content/approval/requests',
            tenantId
          );
          setApprovalRequests(requestsRes.requests || []);
          return;
        }

        if (moduleId === 'inbox') {
          await loadInboxOpsData();
          return;
        }
      } catch (error) {
        setOpsMessage(error instanceof Error ? error.message : 'Unable to load social operations data.');
      } finally {
        setOpsLoading(false);
      }
    },
    [loadInboxOpsData, tenantId]
  );

  async function loadWorkspace() {
    const [usageResult, walletResult, healthResult] = await Promise.allSettled([
      apiGet<UsageResponse>('/billing/usage', tenantId),
      apiGet<WalletResponse>('/money-printers/nuxtron-bank/wallet', tenantId),
      apiGet<HealthResponse>('/ai/health', tenantId),
    ]);

    const nextOverview: WorkspaceOverview = {
      creditBalance: 0,
      pendingTopups: 0,
      walletBalanceUsd: 0,
      recentTransactions: 0,
      providers: [],
    };

    if (usageResult.status === 'fulfilled') {
      nextOverview.creditBalance = Number(usageResult.value.credit_balance || 0);
      nextOverview.pendingTopups = Number(usageResult.value.pending_credit_topups || 0);
    }

    if (walletResult.status === 'fulfilled') {
      nextOverview.walletBalanceUsd = Number(walletResult.value.wallet?.available_balance_usd || 0);
      nextOverview.recentTransactions = (walletResult.value.wallet?.recent_transactions || []).length;
    }

    if (healthResult.status === 'fulfilled') {
      nextOverview.providers = Object.entries(healthResult.value).map(([name, providerStatus]) => ({
        name,
        status: typeof providerStatus?.status === 'string' ? providerStatus.status : 'unknown',
      }));
    }

    setOverview(nextOverview);
  }

  useEffect(() => {
    void loadWorkspace().catch((error) => {
      setLastError(error instanceof Error ? error.message : 'Failed to load studio status.');
    });
  }, [tenantId]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setIsPageReady(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    setPrompt((previous) =>
      previous.trim() ? previous : `Create ${selectedCategory.title.toLowerCase()} assets for our next campaign.`
    );
  }, [selectedCategory]);

  // Restore persisted density + category once on mount. Runs a single time
  // (empty deps) rather than re-syncing on every route change — the
  // route-driven adjustment is handled inline below via a prev-prop guard.
  useEffect(() => {
    try {
      const storedDensity = globalThis.localStorage.getItem(DENSITY_STORAGE_KEY);
      const storedCategory = globalThis.localStorage.getItem(CATEGORY_STORAGE_KEY);
      if (storedDensity === 'comfortable' || storedDensity === 'compact') {
        setDensity(storedDensity);
      }
      if (
        storedCategory &&
        STUDIO_CATEGORIES.some((category) => category.id === storedCategory)
      ) {
        setSelectedCategoryId(storedCategory);
      }
    } catch {
      // Ignore local storage read failures.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When the route-derived category changes, apply its preset inline during
  // render (prev-prop comparison pattern) instead of inside an effect — this
  // avoids the extra render with stale UI that react-doctor flags. The guard
  // ensures we only apply the preset when the value actually changes.
  // prevRouteCategoryIdRef mirrors routeSelectedCategoryId so we can detect
  // transitions without touching state in an effect.
  const prevRouteCategoryIdRef = useRef<string | null>(routeSelectedCategoryId);
  if (prevRouteCategoryIdRef.current !== routeSelectedCategoryId) {
    prevRouteCategoryIdRef.current = routeSelectedCategoryId;
    if (routeSelectedCategoryId && routeSelectedCategoryId !== selectedCategoryId) {
      const category = STUDIO_CATEGORIES.find((item) => item.id === routeSelectedCategoryId);
      const preset = category ? MODULE_PRESETS[category.id] : undefined;
      // setState during render is the React-endorsed way to adjust state on a
      // prop change (see https://react.dev/learn/you-might-not-need-an-effect).
      setSelectedCategoryId(routeSelectedCategoryId);
      if (preset) {
        setComplexity(preset.complexity);
        setTargetChannels(preset.channels);
        setBrandRules(preset.brandRules);
        setEditTools(preset.editTools);
        setPrompt(preset.prompt);
      }
    }
  }

  useEffect(() => {
    try {
      globalThis.localStorage.setItem(DENSITY_STORAGE_KEY, density);
    } catch {
      // Ignore local storage write failures.
    }
  }, [density]);

  useEffect(() => {
    try {
      globalThis.localStorage.setItem(CATEGORY_STORAGE_KEY, selectedCategoryId);
    } catch {
      // Ignore local storage write failures.
    }
  }, [selectedCategoryId]);

  useEffect(() => {
    void loadSocialOpsData(effectiveOpsModuleId);
  }, [loadSocialOpsData, effectiveOpsModuleId]);

  useEffect(() => {
    void loadCanvaImports();
  }, [loadCanvaImports]);

  useEffect(() => {
    if (socialAccounts.length === 0) {
      return;
    }
    const selectedAccount =
      socialAccounts.find((account) => String(account.id) === canvaAccountId) ?? socialAccounts[0];
    if (!selectedAccount) {
      return;
    }
    if (!canvaAccountId) {
      setCanvaAccountId(String(selectedAccount.id));
    }
  }, [canvaAccountId, socialAccounts]);

  useEffect(() => {
    if (effectiveOpsModuleId !== 'inbox') {
      return;
    }
    const interval = globalThis.setInterval(() => {
      void loadSocialOpsData('inbox');
    }, 60000);
    return () => globalThis.clearInterval(interval);
  }, [effectiveOpsModuleId, loadSocialOpsData]);

  useEffect(() => {
    setPreviewAssetIndex((current) => {
      if (generated.length === 0) return 0;
      return Math.min(current, generated.length - 1);
    });
  }, [generated.length]);

  // Sync route-driven ops module into local state so manual tile clicks persist until next navigation.
  useEffect(() => {
    if (routeOpsModuleId && routeOpsModuleId !== activeOpsModuleId) {
      setActiveOpsModuleId(routeOpsModuleId);
    }
  }, [routeOpsModuleId, activeOpsModuleId]);

  // Open a specific Predis panel when linked with ?panel=<name>.
  useEffect(() => {
    if (!selectedPredisPanel) return;

    setShowAbTestPanel(selectedPredisPanel === 'ab-testing');
    setShowCopyGeneratorPanel(selectedPredisPanel === 'copy-generator');
    setShowContentCalendarPanel(selectedPredisPanel === 'content-calendar');
    setShowBrandKitPanel(selectedPredisPanel === 'brand-kit');
    setShowVoiceoverPanel(selectedPredisPanel === 'voiceover-lab');
    setShowPerformanceAnalysisPanel(selectedPredisPanel === 'performance-ai');
    setShowAnimationEffectsPanel(selectedPredisPanel === 'animation-fx');
    setShowCompetitorAnalysisPanel(selectedPredisPanel === 'competitor-intel');
    setShowBulkGenerationPanel(selectedPredisPanel === 'bulk-generator');
    setShowMemeGeneratorPanel(selectedPredisPanel === 'meme-factory');
    setShowQuoteToPostPanel(selectedPredisPanel === 'quote-studio');
    setShowHolidayPostPanel(selectedPredisPanel === 'holiday-posts');
    setShowEcommercePostPanel(selectedPredisPanel === 'ecom-posts');
    setShowAssetLibraryPanel(selectedPredisPanel === 'asset-library');
    setShowChatIdeationPanel(selectedPredisPanel === 'ai-ideation-chat');

    if (selectedPredisPanel === 'brand-kit') {
      void loadBrandKits();
    }
    if (selectedPredisPanel === 'animation-fx') {
      void loadAnimationEffects();
    }
    if (selectedPredisPanel === 'asset-library') {
      void searchAssetLibrary(1);
    }
  }, [selectedPredisPanel]);

  async function connectSocialAccount() {
    if (!connectNetwork.trim() || !connectAccountName.trim() || !connectHandle.trim()) return;
    setOpsMessage('');
    try {
      await apiSend(
        '/social/accounts/connect',
        'POST',
        {
          network: connectNetwork,
          account_name: connectAccountName,
          handle: connectHandle,
          account_type: 'business',
        },
        tenantId
      );
      addActivity(`Connected ${connectNetwork} account ${connectHandle}.`, 'success');
      await loadSocialOpsData('accounts');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to connect account.');
    }
  }

  async function connectAllSocialNetworks() {
    setOpsMessage('');
    try {
      let providers = socialCatalog;
      if (providers.length === 0) {
        const catalogRes = await apiGet<{ providers?: Array<{ network?: string; label?: string }> }>(
          '/social/accounts/catalog',
          tenantId
        );
        providers = (catalogRes.providers || []).map((provider) => ({
          network: String(provider.network || ''),
          label: String(provider.label || provider.network || ''),
        }));
      }

      const existingNetworks = new Set(socialAccounts.map((account) => account.network.toLowerCase()));
      const targets = providers.filter(
        (provider) => provider.network && !existingNetworks.has(provider.network.toLowerCase())
      );

      let connectedCount = 0;
      if (targets.length > 0) {
        const connectResults = await Promise.allSettled(
          targets.map((provider, index) =>
            apiSend(
              '/social/accounts/connect',
              'POST',
              {
                network: provider.network,
                account_name: `Nuxtron ${provider.label || provider.network}`,
                handle: `nuxtron_${provider.network}_${index + 1}`,
                account_type: 'business',
              },
              tenantId
            )
          )
        );
        connectedCount = connectResults.filter((result) => result.status === 'fulfilled').length;
      }

      if (connectedCount === 0 && providers.length === 0) {
        await apiSend(
          '/social/oauth/connect-all',
          'POST',
          {
            account_name_prefix: 'Nuxtron',
            handle_prefix: 'nuxtron',
            account_type: 'business',
          },
          tenantId
        );
        connectedCount = 1;
      }

      let connectMessage = 'All supported social networks are already connected.';
      if (connectedCount > 0) {
        const suffix = connectedCount === 1 ? '' : 's';
        connectMessage = `Connected ${connectedCount} social network${suffix}.`;
      }
      addActivity(connectMessage, 'success');
      await loadSocialOpsData('accounts');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to connect all networks.');
    }
  }

  async function disconnectAllSocialNetworks() {
    if (socialAccounts.length === 0) {
      setOpsMessage('No connected accounts to disconnect.');
      return;
    }
    setOpsMessage('');
    try {
      const results = await Promise.allSettled(
        socialAccounts.map((account) => apiSend(`/social/accounts/${account.id}`, 'DELETE', {}, tenantId))
      );
      const disconnectedCount = results.filter((result) => result.status === 'fulfilled').length;
      const disconnectMessage = `Disconnected ${disconnectedCount} account${disconnectedCount === 1 ? '' : 's'}.`;
      addActivity(disconnectMessage, 'warning');
      await loadSocialOpsData('accounts');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to disconnect accounts.');
    }
  }

  async function runAutonomousPost(mode: 'preview' | 'publish') {
    const accountId = socialAccounts[0]?.id;
    if (!accountId) {
      setOpsMessage('Connect at least one account before running autonomous posting.');
      return;
    }
    setOpsMessage('');
    try {
      const response = await apiSend<Record<string, unknown>>(
        `/social/autopilot/${mode}`,
        'POST',
        {
          account_id: accountId,
          content_type: 'image',
          headline: postHeadline,
          caption: postCaption,
          media_urls: postMediaUrl.trim() ? [postMediaUrl.trim()] : [],
          publish_mode: postMode,
          publish_at: postPublishAt ? new Date(postPublishAt).toISOString() : null,
        },
        tenantId
      );
      setAutopilotResult(response);
      addActivity(mode === 'preview' ? 'Autonomous preview generated.' : 'Autonomous publish request sent.', 'info');
      await loadSocialOpsData('autonomous');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Autonomous manager request failed.');
    }
  }

  async function scheduleSocialPostAction() {
    setOpsMessage('');
    try {
      await apiSend(
        '/api/v1/social/content/create',
        'POST',
        {
          title: scheduleText.slice(0, 80) || 'Scheduled social post',
          caption: scheduleText,
          media_assets: scheduleMediaUrl.trim() ? [{ type: 'image', url: scheduleMediaUrl.trim() }] : [],
          platforms: [schedulePlatform],
          requires_approval: false,
          scheduled_for: new Date(schedulePublishAt).toISOString(),
        },
        tenantId
      );
      addActivity(`Scheduled ${schedulePlatform} post.`, 'success');
      await loadSocialOpsData('calendar');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to schedule social post.');
    }
  }

  async function moveScheduledPostAction(postId: string, publishAtIso: string) {
    setOpsMessage('');
    try {
      await apiSend(
        `/api/v1/social/content/${postId}/reschedule`,
        'POST',
        { new_scheduled_time: publishAtIso },
        tenantId
      );
      addActivity(`Moved scheduled post #${postId}.`, 'info');
      await loadSocialOpsData('calendar');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to move scheduled post.');
    }
  }

  async function moveScheduledPostByForm() {
    const id = movePostId.trim();
    if (!id) return;
    await moveScheduledPostAction(id, new Date(movePublishAt).toISOString());
  }

  async function configureApprovals() {
    const levels = approvalLevels
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 5);
    if (!levels.length) return;
    setOpsMessage('');
    try {
      await apiSend(
        '/content/approval/config',
        'PUT',
        { levels, require_all_levels: true, expiry_hours: 72 },
        tenantId
      );
      addActivity('Approval chain updated.', 'success');
      await loadSocialOpsData('approvals');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to configure approvals.');
    }
  }

  async function submitApprovalRequest() {
    const scheduledPostId = Number.parseInt(approvalPostId, 10);
    if (!Number.isFinite(scheduledPostId)) return;
    setOpsMessage('');
    try {
      await apiSend(
        '/content/approval/requests',
        'POST',
        {
          scheduled_post_id: scheduledPostId,
          platform: approvalPlatform,
          content_preview: approvalPreview,
          requested_by: approvalRequestedBy,
        },
        tenantId
      );
      addActivity(`Submitted approval request for post #${scheduledPostId}.`, 'warning');
      await loadSocialOpsData('approvals');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to submit approval request.');
    }
  }

  async function decideApproval(requestId: number, decision: 'approved' | 'rejected') {
    setOpsMessage('');
    try {
      await apiSend(
        `/content/approval/requests/${requestId}/decision`,
        'POST',
        {
          decision,
          reviewer_role: 'manager',
          comment: decision === 'approved' ? 'Approved for publishing.' : 'Needs revisions before publish.',
        },
        tenantId
      );
      addActivity(
        `Approval request #${requestId} marked ${decision}.`,
        decision === 'approved' ? 'success' : 'warning'
      );
      await loadSocialOpsData('approvals');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to update approval decision.');
    }
  }

  async function engageInboxMessage() {
    const messageId = Number.parseInt(inboxMessageId, 10);
    const accountId = socialAccounts[0]?.id;
    if (!Number.isFinite(messageId) || !accountId) {
      setOpsMessage('Connect at least one account and provide a valid message ID.');
      return;
    }
    setOpsMessage('');
    try {
      await apiSend(
        `/social/inbox/messages/${messageId}/engage`,
        'POST',
        {
          account_id: accountId,
          reply_text: inboxReplyText,
          action: 'reply',
        },
        tenantId
      );
      addActivity(`Engaged inbox message #${messageId}.`, 'success');
      await loadSocialOpsData('inbox');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to engage inbox message.');
    }
  }

  async function createSavedReplyTemplate() {
    if (!savedReplyTitle.trim() || !savedReplyBody.trim()) {
      setOpsMessage('Provide a title and body for the saved reply template.');
      return;
    }
    setOpsMessage('');
    try {
      const method = savedReplyEditingId ? 'PATCH' : 'POST';
      const path = savedReplyEditingId
        ? `/social/inbox/saved-replies/${savedReplyEditingId}`
        : '/social/inbox/saved-replies';
      await apiSend(
        path,
        method,
        {
          title: savedReplyTitle,
          body: savedReplyBody,
          category: savedReplyCategory,
        },
        tenantId
      );
      addActivity(
        `Saved reply template "${savedReplyTitle}" ${savedReplyEditingId ? 'updated' : 'created'}.`,
        'success'
      );
      setSavedReplyEditingId(null);
      await loadSocialOpsData('inbox');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to create saved reply template.');
    }
  }

  async function deleteSavedReplyTemplate(replyId: number) {
    setOpsMessage('');
    try {
      await apiSend(`/social/inbox/saved-replies/${replyId}`, 'DELETE', {}, tenantId);
      addActivity(`Saved reply template #${replyId} deleted.`, 'success');
      if (savedReplyEditingId === replyId) {
        setSavedReplyEditingId(null);
        setSavedReplyTitle('VIP follow-up');
        setSavedReplyCategory('vip');
        setSavedReplyBody('Thanks for the note. We have routed this to the partnership team.');
      }
      await loadSocialOpsData('inbox');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to delete saved reply template.');
    }
  }

  function applySavedReplyTemplate(reply: SavedReplyItem) {
    setInboxReplyText(reply.body);
    setSavedReplyTitle(reply.title);
    setSavedReplyCategory(reply.category);
    setSavedReplyBody(reply.body);
    setSavedReplyEditingId(reply.id);
  }

  function clearSavedReplyTemplateForm() {
    setSavedReplyEditingId(null);
    setSavedReplyTitle('VIP follow-up');
    setSavedReplyCategory('vip');
    setSavedReplyBody('Thanks for the note. We have routed this to the partnership team.');
  }

  const latestInboxMessageText = useMemo(() => {
    const latestMessage = messageHistory.at(-1);
    if (!latestMessage) {
      return '';
    }
    return (
      toDisplayText(latestMessage.text) || toDisplayText(latestMessage.body) || toDisplayText(latestMessage.content)
    );
  }, [messageHistory]);

  const selectedContact = useMemo(
    () => contactViews.find((contact) => contact.handle === selectedContactHandle) || null,
    [contactViews, selectedContactHandle]
  );

  const inboxTriageSuggestion = useMemo<InboxTriageSuggestion>(() => {
    const sentiment = (selectedContact?.sentiment || '').toLowerCase();
    const text = `${latestInboxMessageText} ${inboxReplyText}`.toLowerCase();
    const urgentSignals = ['urgent', 'asap', 'help', 'issue', 'broken', 'refund', 'complaint', 'angry', 'escalate'];
    const positiveSignals = ['thanks', 'thank you', 'resolved', 'appreciate', 'great', 'awesome', 'perfect'];
    const hasUrgentSignals = urgentSignals.some((word) => text.includes(word));
    const hasPositiveSignals = positiveSignals.some((word) => text.includes(word));

    if (sentiment === 'negative' || hasUrgentSignals) {
      return {
        action: 'claim',
        label: 'Claim and investigate',
        reason: hasUrgentSignals
          ? 'The latest message contains urgent support language, so a human should own it now.'
          : 'The contact sentiment is negative, so this thread should be claimed for follow-up.',
      };
    }

    if (sentiment === 'positive' || hasPositiveSignals) {
      return {
        action: 'complete',
        label: 'Complete after reply',
        reason: hasPositiveSignals
          ? 'The thread reads as resolved or appreciative, so completion is likely appropriate after a reply.'
          : 'The contact sentiment is positive, so this thread can likely be closed after confirmation.',
      };
    }

    return {
      action: 'review',
      label: 'Review and reply',
      reason: 'The thread is neutral or ambiguous, so generate a reply and inspect the history before closing.',
    };
  }, [inboxReplyText, latestInboxMessageText, selectedContact?.sentiment]);

  async function generateReplySuggestions() {
    const promptText = latestInboxMessageText || inboxReplyText.trim();
    if (!promptText) {
      setOpsMessage('Load message history or enter a reply draft before generating suggestions.');
      return;
    }
    setReplySuggestionsLoading(true);
    setOpsMessage('');
    try {
      const [rephrase, formal, casual] = await Promise.all([
        apiSend<{ result?: string; provider?: string }>(
          '/social/ai-assistant',
          'POST',
          {
            text: promptText,
            action: 'rephrase',
            target_platform: selectedContactHandle || 'inbox',
            tone: selectedContact?.sentiment || 'neutral',
          },
          tenantId
        ),
        apiSend<{ result?: string; provider?: string }>(
          '/social/ai-assistant',
          'POST',
          {
            text: promptText,
            action: 'formal',
            target_platform: selectedContactHandle || 'inbox',
            tone: 'professional',
          },
          tenantId
        ),
        apiSend<{ result?: string; provider?: string }>(
          '/social/ai-assistant',
          'POST',
          { text: promptText, action: 'casual', target_platform: selectedContactHandle || 'inbox', tone: 'friendly' },
          tenantId
        ),
      ]);
      setReplySuggestions([
        {
          action: 'rephrase',
          label: 'Rephrase',
          result: rephrase.result || promptText,
          provider: rephrase.provider || 'openai/gpt-4o',
        },
        {
          action: 'formal',
          label: 'Formal',
          result: formal.result || promptText,
          provider: formal.provider || 'openai/gpt-4o',
        },
        {
          action: 'casual',
          label: 'Casual',
          result: casual.result || promptText,
          provider: casual.provider || 'openai/gpt-4o',
        },
      ]);
      addActivity('Generated inbox reply suggestions.', 'success');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to generate reply suggestions.');
    } finally {
      setReplySuggestionsLoading(false);
    }
  }

  function applyReplySuggestion(suggestion: ReplySuggestionItem) {
    setInboxReplyText(suggestion.result);
  }

  async function runInboxDmChatbot() {
    const messageId = Number.parseInt(inboxMessageId, 10);
    if (!Number.isFinite(messageId)) {
      setOpsMessage('Provide a valid message ID before running the AI chatbot.');
      return;
    }

    setDmChatbotLoading(true);
    setOpsMessage('');
    try {
      const inferredIntent = inboxTriageSuggestion.action === 'claim' ? 'support' : 'sales';
      const buyerStage = selectedContact?.sentiment?.toLowerCase() === 'positive' ? 'decision' : 'consideration';
      const response = await apiSend<{
        message?: Record<string, unknown>;
        provider?: string;
        escalation_recommended?: boolean;
        escalation_reason?: string;
      }>(
        '/social/inbox/agents/dm-chatbot/respond',
        'POST',
        {
          message_id: messageId,
          intent: inferredIntent,
          response_tone: 'friendly',
          context: {
            buyer_stage: buyerStage,
            selected_contact: selectedContactHandle || null,
            selected_contact_sentiment: selectedContact?.sentiment || 'neutral',
            selected_contact_message_count: Number(selectedContact?.message_count || 0),
          },
        },
        tenantId
      );

      const chatbotReply = toDisplayText(response.message?.reply_text);
      if (chatbotReply) {
        setInboxReplyText(chatbotReply);
      }

      const provider = toDisplayText(response.provider, 'dm-chatbot');
      const escalationRecommended = Boolean(response.escalation_recommended);
      const escalationReason = toDisplayText(response.escalation_reason);

      if (escalationRecommended && escalationReason) {
        setOpsMessage(`AI chatbot flagged escalation: ${escalationReason}`);
      }
      addActivity(
        `AI chatbot replied for message #${messageId} (${provider}).`,
        escalationRecommended ? 'warning' : 'success'
      );
      await Promise.all([loadInboxMessageHistory(), loadSocialOpsData('inbox')]);
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to run AI chatbot response.');
    } finally {
      setDmChatbotLoading(false);
    }
  }

  async function loadInboxMessageHistory() {
    const messageId = Number.parseInt(inboxMessageId, 10);
    if (!Number.isFinite(messageId)) {
      setOpsMessage('Provide a valid message ID to load history.');
      return;
    }
    setOpsMessage('');
    try {
      const response = await apiGet<{ history?: Array<Record<string, unknown>> }>(
        `/social/inbox/messages/${messageId}/history`,
        tenantId
      );
      setMessageHistory(response.history || []);
      const authorHandle =
        toDisplayText(response.history?.[0]?.author_handle) || toDisplayText(response.history?.[0]?.author);
      if (authorHandle) {
        setSelectedContactHandle(authorHandle);
      }
      addActivity(`Loaded inbox history for message #${messageId}.`, 'info');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to load message history.');
    }
  }

  async function claimInboxMessage() {
    const messageId = Number.parseInt(inboxMessageId, 10);
    if (!Number.isFinite(messageId) || !inboxClaimAgentName.trim()) {
      setOpsMessage('Provide a valid message ID and agent name to claim the message.');
      return;
    }
    setOpsMessage('');
    try {
      await apiSend(`/social/inbox/messages/${messageId}/claim`, 'POST', { agent_name: inboxClaimAgentName }, tenantId);
      addActivity(`Claimed inbox message #${messageId} for ${inboxClaimAgentName}.`, 'success');
      await Promise.all([loadInboxMessageHistory(), loadSocialOpsData('inbox')]);
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to claim inbox message.');
    }
  }

  async function completeInboxMessage() {
    const messageId = Number.parseInt(inboxMessageId, 10);
    if (!Number.isFinite(messageId)) {
      setOpsMessage('Provide a valid message ID to complete the message.');
      return;
    }
    setOpsMessage('');
    try {
      await apiSend(`/social/inbox/messages/${messageId}/complete`, 'POST', {}, tenantId);
      addActivity(`Completed inbox message #${messageId}.`, 'success');
      await Promise.all([loadInboxMessageHistory(), loadSocialOpsData('inbox')]);
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to complete inbox message.');
    }
  }

  function toggleInboxMessageSelection(messageId: number) {
    setSelectedInboxMessageIds((current) => {
      if (current.includes(messageId)) {
        return current.filter((id) => id !== messageId);
      }
      return [...current, messageId];
    });
  }

  async function runBulkInboxAction(action: 'claim' | 'complete') {
    const uniqueMessageIds = Array.from(new Set(selectedInboxMessageIds)).filter((id) => Number.isFinite(id));
    if (uniqueMessageIds.length === 0) {
      setOpsMessage('Select at least one inbox message for a bulk action.');
      return;
    }
    if (action === 'claim' && !inboxClaimAgentName.trim()) {
      setOpsMessage('Provide an agent name before running bulk claim.');
      return;
    }

    setBulkInboxActionLoading(true);
    setOpsMessage('');
    try {
      const response = await apiSend<{
        updated_count?: number;
        missing_ids?: number[];
        summary?: Record<string, number>;
      }>(
        '/social/inbox/bulk-action',
        'POST',
        {
          message_ids: uniqueMessageIds,
          action,
          agent_name: inboxClaimAgentName,
        },
        tenantId
      );
      const updatedCount = Number(response.updated_count || uniqueMessageIds.length);
      const missingIds = (response.missing_ids || []).map(Number).filter((value) => Number.isFinite(value));
      let suffix = 's';
      if (updatedCount === 1) {
        suffix = '';
      }
      let actionLabel = `Completed ${updatedCount} message${suffix}.`;
      if (action === 'claim') {
        actionLabel = `Claimed ${updatedCount} message${suffix} for ${inboxClaimAgentName}.`;
      }
      addActivity(actionLabel, 'success');
      if (response.summary) {
        setWorkspaceOpsOverview((current) => ({
          ...current,
          inbox_open: Number(response.summary?.open ?? current.inbox_open ?? 0),
        }));
      }
      if (missingIds.length > 0) {
        setOpsMessage(`Some messages were not found: ${missingIds.join(', ')}`);
      }
      setSelectedInboxMessageIds([]);
      await loadSocialOpsData('inbox');
    } catch (error) {
      setOpsMessage(error instanceof Error ? error.message : 'Failed to run bulk inbox action.');
    } finally {
      setBulkInboxActionLoading(false);
    }
  }

  const filteredContactViews = useMemo(() => {
    const query = inboxContactQuery.trim().toLowerCase();
    return contactViews
      .filter((contact) => {
        if (inboxSentimentFilter !== 'all' && contact.sentiment.toLowerCase() !== inboxSentimentFilter) {
          return false;
        }
        if (!query) {
          return true;
        }
        const haystack = [contact.handle, contact.display_name, contact.sentiment, contact.networks.join(' ')]
          .join(' ')
          .toLowerCase();
        return haystack.includes(query);
      })
      .sort((left, right) => {
        const rightCount = Number(right.message_count || 0);
        const leftCount = Number(left.message_count || 0);
        if (rightCount !== leftCount) {
          return rightCount - leftCount;
        }
        return right.last_message_at.localeCompare(left.last_message_at);
      });
  }, [contactViews, inboxContactQuery, inboxSentimentFilter]);

  const inboxSelectionSummary = useMemo(() => {
    const selected = inboxItems.filter((item) => {
      const id = Number.parseInt(item.id, 10);
      return Number.isFinite(id) && selectedInboxMessageIds.includes(id);
    });
    return {
      selectedCount: selected.length,
      openCount: selected.filter((item) => item.state !== 'complete' && !item.responded).length,
      completeCount: selected.filter((item) => item.state === 'complete').length,
    };
  }, [inboxItems, selectedInboxMessageIds]);

  function selectInboxMessagesBy(predicate: (item: InboxListItem) => boolean) {
    const nextIds = inboxItems
      .filter(predicate)
      .map((item) => Number.parseInt(item.id, 10))
      .filter((id) => Number.isFinite(id));
    setSelectedInboxMessageIds(Array.from(new Set(nextIds)));
  }

  function clearInboxSelection() {
    setSelectedInboxMessageIds([]);
  }

  const calendarDays = useMemo(() => {
    return Array.from({ length: 7 }).map((_, index) => {
      const date = new Date();
      date.setHours(12, 0, 0, 0);
      date.setDate(date.getDate() + index);
      return {
        id: date.toISOString().slice(0, 10),
        label: date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }),
      };
    });
  }, []);

  function handleCalendarLaneDrop(dayId: string) {
    if (draggedPostId === null) return;
    const nextDate = new Date(`${dayId}T10:00:00`);
    void moveScheduledPostAction(draggedPostId, nextDate.toISOString());
    setDraggedPostId(null);
  }

  const commandActions = useMemo<CommandAction[]>(
    () => [
      {
        id: 'preview',
        title: 'Preview orchestration plan',
        shortcut: 'P',
        disabled: busy !== 'idle',
        run: () => previewButtonRef.current?.click(),
      },
      {
        id: 'generate',
        title: 'Launch generation',
        shortcut: 'G',
        disabled: busy !== 'idle' || !prompt.trim(),
        run: () => generateButtonRef.current?.click(),
      },
      {
        id: 'quote',
        title: 'Request credits quote',
        shortcut: 'Q',
        disabled: busy !== 'idle',
        run: () => quoteButtonRef.current?.click(),
      },
      {
        id: 'checkout',
        title: 'Create credit checkout',
        shortcut: 'K',
        disabled: busy !== 'idle',
        run: () => checkoutButtonRef.current?.click(),
      },
      {
        id: 'confirm',
        title: 'Confirm payment',
        shortcut: 'C',
        disabled: busy !== 'idle' || !checkout,
        run: () => confirmButtonRef.current?.click(),
      },
      {
        id: 'density',
        title: density === 'comfortable' ? 'Switch to compact density' : 'Switch to comfortable density',
        shortcut: 'D',
        disabled: false,
        run: () => setDensity((previous) => (previous === 'comfortable' ? 'compact' : 'comfortable')),
      },
    ],
    [busy, checkout, density, prompt]
  );

  const filteredCommandActions = useMemo(() => {
    const q = commandQuery.trim().toLowerCase();
    if (!q) return commandActions;
    return commandActions.filter(
      (action) => action.title.toLowerCase().includes(q) || action.shortcut.toLowerCase() === q
    );
  }, [commandActions, commandQuery]);

  const closeCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(false);
    setCommandQuery('');
  }, []);

  const openCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(true);
  }, []);

  useCommandShortcuts({
    isCommandPaletteOpen,
    filteredCommandActions,
    closePalette: closeCommandPalette,
    openPalette: openCommandPalette,
    triggerShortcutAction,
  });

  function buildRequestPayload() {
    return {
      prompt,
      media_type: selectedCategory.mediaType,
      capability: selectedCategory.capability,
      use_case: selectedCategory.id,
      creative_mode: selectedCategory.id,
      delivery_mode: selectedCategory.deliveryMode,
      orchestration_goal: `Deliver ${selectedCategory.outputs.join(', ')}`,
      complexity,
      target_channels: targetChannels,
      edit_tools: editTools,
      brand_rules: brandRules,
      auto_route: true,
      prompt_description: `${selectedCategory.summary} Outputs: ${selectedCategory.outputs.join(', ')}.`,
      aspect_ratio: selectedCategory.mediaType === 'image' ? '4:5' : '9:16',
      resolution: selectedCategory.mediaType === 'video' ? '4K' : '1080p',
      contains_real_people: selectedCategory.id === 'avatars',
      return_last_frame: selectedCategory.mediaType === 'video',
    };
  }

  function activateModule(category: StudioCategory) {
    const preset = MODULE_PRESETS[category.id];
    setSelectedCategoryId(category.id);
    if (preset) {
      setComplexity(preset.complexity);
      setTargetChannels(preset.channels);
      setBrandRules(preset.brandRules);
      setEditTools(preset.editTools);
      setPrompt(preset.prompt);
    } else {
      setPrompt(`Create ${category.title.toLowerCase()} assets for our next campaign.`);
    }
    setLastError('');
    addActivity(`${category.title} module activated and configured.`, 'info');
  }

  function buildFormData() {
    const payload = buildRequestPayload();
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => formData.append(key, item));
      } else {
        formData.append(key, String(value));
      }
    });
    imageFiles.forEach((file) => formData.append('reference_images', file));
    videoFiles.forEach((file) => formData.append('reference_videos', file));
    audioFiles.forEach((file) => formData.append('reference_audios', file));
    formData.append('portrait_library', JSON.stringify({ focus: selectedCategory.capability }));
    return formData;
  }

  function appendFilesToZone(zone: UploadZone, files: File[]) {
    if (files.length === 0) return;
    if (zone === 'image') {
      setImageFiles((current) => mergeFiles(current, files));
      return;
    }
    if (zone === 'video') {
      setVideoFiles((current) => mergeFiles(current, files));
      return;
    }
    setAudioFiles((current) => mergeFiles(current, files));
  }

  function handleUploadInput(zone: UploadZone, fileList: FileList | null) {
    appendFilesToZone(zone, Array.from(fileList || []));
  }

  function handleUploadDrop(zone: UploadZone, event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setUploadDragZone(null);
    appendFilesToZone(zone, Array.from(event.dataTransfer.files || []));
  }

  function removeUploadFile(zone: UploadZone, fileToRemove: File) {
    if (zone === 'image') {
      setImageFiles((current) => current.filter((file) => file !== fileToRemove));
      return;
    }
    if (zone === 'video') {
      setVideoFiles((current) => current.filter((file) => file !== fileToRemove));
      return;
    }
    setAudioFiles((current) => current.filter((file) => file !== fileToRemove));
  }

  function previewPlan() {
    void previewPlanAction({
      tenantId,
      buildRequestPayload,
      setBusy,
      setStatusLabel,
      setLastError,
      setPlan,
      setGenerated,
      selectedCategory,
      prompt,
      addActivity,
    });
  }

  function stopPolling() {
    stopPollingAction({ pollRef, setPollElapsedSeconds, setBusy, setStatusLabel });
  }

  function handleGenerationSuccess(result: GenerationResponse) {
    handleGenerationSuccessAction({
      result,
      plan,
      setPlan,
      setGenerated,
      selectedCategory,
      addActivity,
      tenantId,
      loadWorkspace,
    });
  }

  function startPolling(jobId: string) {
    startPollingAction({
      jobId,
      tenantId,
      pollRef,
      setPollElapsedSeconds,
      setStatusLabel,
      stopPolling,
      handleGenerationSuccess,
      setLastError,
      addActivity,
      loadWorkspace,
    });
  }

  function generate() {
    const resetUploadProgress = () => {
      setUploadProgress({ image: 0, video: 0, audio: 0 });
      setUploadLoadedBytes({ image: 0, video: 0, audio: 0 });
    };
    void generateAction({
      prompt,
      setPollElapsedSeconds,
      setBusy,
      setStatusLabel,
      setLastError,
      tenantId,
      buildFormData,
      zoneUploadTotals,
      setUploadProgress,
      setUploadLoadedBytes,
      setPlan,
      addActivity,
      startPolling,
      handleGenerationSuccess,
      loadWorkspace,
    }).finally(resetUploadProgress);
  }

  function requestQuote() {
    void requestQuoteAction({ tenantId, topupCredits, setBusy, setLastError, setQuote, addActivity });
  }

  function checkoutCredits() {
    void checkoutCreditsAction({
      tenantId,
      topupCredits,
      setBusy,
      setLastError,
      setCheckout,
      addActivity,
      loadWorkspace,
    });
  }

  function confirmCredits() {
    if (!checkout) return;
    void confirmCreditsAction({ tenantId, checkout, setBusy, setLastError, setCheckout, addActivity, loadWorkspace });
  }

  async function disconnectSocialAccount(account: SocialAccount) {
    const accountId = account.id;
    const accountName = account.account_name;
    try {
      await apiSend(`/social/accounts/${accountId}`, 'DELETE', {}, tenantId);
      setSocialAccounts((previous) => previous.filter((item) => item.id !== accountId));
      addToast(`Disconnected ${accountName}`, 'success');
    } catch (error) {
      addToast(error instanceof Error ? error.message : 'Failed to disconnect account.', 'error');
    }
  }

  function getActivityBorderColor(tone: ActivityItem['tone']): string {
    if (tone === 'error') return '#ff6b6b';
    if (tone === 'success') return '#22c55e';
    return 'var(--line)';
  }

  function dismissActivity(id: string) {
    setActivity((previous) => previous.filter((item) => item.id !== id));
  }

  async function generateAbTestingVariants() {
    const requested = Number.parseInt(bulkGenerationCount, 10);
    const variantCount = Number.isFinite(requested) ? Math.min(10, Math.max(3, requested)) : 5;
    const basePrompt = prompt.trim() || postCaption.trim() || 'Launch campaign creative';

    try {
      const response = await apiSend<{ variants: ABVariant[] }>(
        '/ai/social-studio/ab-variants',
        'POST',
        {
          prompt: basePrompt,
          num_variants: variantCount,
          media_type: selectedCategory.mediaType,
        },
        tenantId
      );

      const variants = Array.isArray(response.variants) ? response.variants : [];
      setAbTestingVariants(variants);
      addActivity(`Generated ${variants.length} A/B variants from live backend.`, 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'A/B variant generation failed.';
      setLastError(message);
      addActivity(message, 'error');
    }
  }

  async function generateCopyHooks() {
    const tone = copyGenerationTone.trim() || 'casual';
    const product = copyGenerationProduct.trim() || selectedCategory.title;

    try {
      const response = await apiSend<{ variations: CopyVariation[] }>(
        '/ai/social-studio/copy-generator',
        'POST',
        {
          category: copyGenerationCategory,
          product,
          tone,
          num_variations: 5,
        },
        tenantId
      );

      const variations = Array.isArray(response.variations) ? response.variations : [];
      setCopyVariations(variations);
      addActivity(`Generated ${variations.length} copy/hook variants (${tone}) from live backend.`, 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Copy generator failed.';
      setLastError(message);
      addActivity(message, 'error');
    }
  }

  // ── PREDIS PANEL API FUNCTIONS ────────────────────────────────────────

  async function runMemeGenerator() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/meme-generator', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: memeTemplate,
          slots: {
            top_text: memeTopText,
            bottom_text: memeBottomText,
            label_a: memeTopText,
            approve_text: memeBottomText,
          },
          caption: memeCaption,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { meme: typeof generatedMeme };
      setGeneratedMeme(d.meme);
      addActivity('Meme generated.', 'success');
    } catch {
      addActivity('Meme generation failed.', 'error');
    }
  }

  async function runQuoteToPost() {
    const quote = quoteText.trim() || prompt.trim();
    if (!quote) {
      addActivity('Enter a quote before generating.', 'error');
      return;
    }
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/quote-to-post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote,
          author: quoteAuthor,
          style: quoteStyle,
          platform: targetChannels[0] || 'instagram',
          add_cta: true,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { post: typeof generatedQuotePost };
      setGeneratedQuotePost(d.post);
      addActivity('Quote post generated.', 'success');
    } catch {
      addActivity('Quote-to-post failed.', 'error');
    }
  }

  async function runHolidayPost() {
    const holiday = holidayName.trim();
    if (!holiday) {
      addActivity('Enter a holiday name before generating.', 'error');
      return;
    }
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/holiday-post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          holiday_name: holiday,
          theme: holidayTheme,
          platform: targetChannels[0] || 'instagram',
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { post: typeof generatedHolidayPost };
      setGeneratedHolidayPost(d.post);
      addActivity('Holiday post generated.', 'success');
    } catch {
      addActivity('Holiday post generation failed.', 'error');
    }
  }

  async function runEcommercePost() {
    const productName = ecomProductName.trim();
    if (!productName) {
      addActivity('Enter a product name before generating.', 'error');
      return;
    }
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/ecommerce-product-post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_name: productName,
          product_url: ecomProductUrl,
          price: ecomProductPrice,
          discount: ecomDiscount,
          platform: targetChannels[0] || 'instagram',
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { post: typeof generatedEcomPost };
      setGeneratedEcomPost(d.post);
      addActivity('Ecommerce post generated.', 'success');
    } catch {
      addActivity('Ecommerce post generation failed.', 'error');
    }
  }

  async function searchAssetLibrary(page = 1) {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: '24' });
      if (assetLibraryQuery) params.set('q', assetLibraryQuery);
      if (assetLibraryCategory !== 'all') params.set('category', assetLibraryCategory);
      const res = await fetch('/api/fastapi/ai/social-studio/asset-library?' + params.toString());
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { assets: typeof assetLibraryResults; total: number };
      setAssetLibraryResults(d.assets);
      setAssetLibraryTotal(d.total);
      setAssetLibraryPage(page);
    } catch {
      addActivity('Asset library search failed.', 'error');
    }
  }

  async function sendChatMessage() {
    const msg = chatInput.trim();
    if (!msg) {
      addActivity('Type a message before sending.', 'error');
      return;
    }
    const ts = new Date().toISOString();
    setChatMessages((prev) => [...prev, { role: 'user', content: msg, timestamp: ts }]);
    setChatInput('');
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/chat-ideation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: chatSessionId }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { reply: string };
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: d.reply, timestamp: new Date().toISOString() },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Unable to reach AI. Check connection.', timestamp: new Date().toISOString() },
      ]);
    }
  }

  async function runVoiceover() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/voiceover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: voiceoverText || prompt,
          voice_style: {
            name: voiceoverVoiceName,
            gender: 'neutral',
            language: 'en',
            accent: 'US',
            tone: voiceoverEmotion,
          },
          speed: voiceoverSpeed,
          pitch: voiceoverPitch,
          emotion: voiceoverEmotion,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { voiceover_url: string; duration_ms: number; word_count: number };
      setVoiceoverResult(d);
      addActivity('Voiceover generated.', 'success');
    } catch {
      addActivity('Voiceover generation failed.', 'error');
    }
  }

  async function runPerformancePrediction() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/performance-prediction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt || postCaption,
          media_type: perfMediaType,
          channel: perfChannel,
          tone: copyGenerationTone,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { prediction: PerformancePrediction };
      setPerformancePredictions(d.prediction);
      addActivity('Performance prediction complete.', 'success');
    } catch {
      addActivity('Performance prediction failed.', 'error');
    }
  }

  async function loadAnimationEffects() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/animation-effects');
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { effects: AnimationEffect[] };
      setAnimationEffects(d.effects);
      addActivity('Animation effects loaded.', 'success');
    } catch {
      addActivity('Failed to load animation effects.', 'error');
    }
  }

  async function runCompetitorAnalysis() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/competitor-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: competitorUrl }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { analysis: CompetitorAnalysis };
      setCompetitorAnalysis(d.analysis);
      addActivity('Competitor analysis complete.', 'success');
    } catch {
      addActivity('Competitor analysis failed.', 'error');
    }
  }

  async function startBulkGeneration() {
    try {
      const platforms = targetChannels.length > 0 ? targetChannels : ['instagram'];
      const res = await fetch('/api/fastapi/ai/social-studio/bulk-generate-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: bulkPrompt || prompt,
          num_variations: Number.parseInt(bulkCount, 10) || 5,
          media_type: bulkMediaType,
          platforms,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { job: BulkGenerationJob };
      setActiveBulkJob(d.job);
      setBulkGenerationJobs((prev) => [d.job, ...prev].slice(0, 20));
      addActivity('Bulk generation job started.', 'success');
    } catch {
      addActivity('Bulk generation failed.', 'error');
    }
  }

  async function loadBrandKits() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/brand-kits');
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { brand_kits: BrandKit[] };
      setBrandKits(d.brand_kits);
      if (d.brand_kits.length > 0 && !activeBrandKit) setActiveBrandKit(d.brand_kits[0]);
    } catch {
      addActivity('Failed to load brand kits.', 'error');
    }
  }

  async function saveBrandKit() {
    try {
      const res = await fetch('/api/fastapi/ai/social-studio/brand-kit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: brandKitName, colors: brandKitColors, fonts: brandKitFonts }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const d = (await res.json()) as { brand_kit: BrandKit };
      setBrandKits((prev) => [d.brand_kit, ...prev]);
      setActiveBrandKit(d.brand_kit);
      addActivity('Brand kit saved.', 'success');
    } catch {
      addActivity('Failed to save brand kit.', 'error');
    }
  }

  function applyActiveBrandKitToCanvaBridge() {
    const presetDraft = buildCanvaBridgePresetDraft(activeBrandKit);
    if (!presetDraft) {
      addActivity('No active brand kit selected.', 'error');
      return;
    }

    setCanvaHeadline(presetDraft.headline);
    setCanvaCaption(presetDraft.caption);
    addActivity(presetDraft.activityMessage, 'success');
  }

  return (
    <main
      className={`social-studio-page density-${density} ${isPageReady ? '' : 'page-loading'}`}
      style={moduleVisualStyle}
    >
      <div className="tower-wrap">
        <section className="hero-shell tower-hero">
          <div className="hero-copy tower-copy">
            <p className="eyebrow">Advanced Social Studio Control Tower</p>
            <h1>Unified Social Studio Frontier Stack</h1>
            <p>
              Centralized operating plane for multimodal campaign production, provider orchestration, credit-safe
              execution, and cross-channel publishing.
            </p>
            <p className="hero-lately-link">
              <Link href="/studio/lately">Launch Lately AI Hub →</Link>
            </p>
            {lastError ? (
              <div className="hero-inline-error">{lastError} — some features may be unavailable.</div>
            ) : null}
          </div>
          <div className="hero-metrics">
            <article className="metric-card">
              <p>{overview.creditBalance} paid credits</p>
            </article>
            <article className="metric-card">
              <p>{overview.pendingTopups} top-ups pending</p>
            </article>
            <article className="metric-card">
              <p>${overview.walletBalanceUsd.toFixed(2)} wallet balance</p>
            </article>
            <article className="metric-card">
              <p>{generated.length} generated outputs</p>
            </article>
          </div>
        </section>

        {isStudioModulePage ? (
          <section className="modules-shell card module-focus-shell">
            <div className="modules-head">
              <Link href="/studio/social-studio" className="module-back-link">
                ← Back to Studio Modules
              </Link>
              <h3>{selectedCategory.title}</h3>
              <span className="small-text">{selectedCategory.summary}</span>
            </div>
          </section>
        ) : (
          <section className="modules-shell card">
            <div className="modules-head">
              <h3>Studio Modules</h3>
              <span className="small-text">Click a module to open its dedicated page</span>
            </div>
            <div className="category-grid tower-grid">
              {STUDIO_CATEGORIES.map((category, index) => {
                const theme = CATEGORY_THEMES[index % CATEGORY_THEMES.length];
                const isHovered = hoveredModuleId === category.id;
                const isActive = category.id === selectedCategory.id;
                const moduleRouteSegment = STUDIO_MODULE_ROUTE_BY_CATEGORY_ID[category.id] ?? 'social-studio';
                return (
                  <Link
                    key={category.id}
                    href={`/studio/${moduleRouteSegment}`}
                    onMouseEnter={() => setHoveredModuleId(category.id)}
                    onMouseLeave={() => setHoveredModuleId(null)}
                    onFocus={() => setHoveredModuleId(category.id)}
                    onBlur={() => setHoveredModuleId(null)}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <div style={buildSeoTileStyle(theme.color, isHovered, isActive)}>
                      <span aria-hidden="true" style={buildSeoIconStyle(isHovered, isActive)}>
                        {theme.icon}
                      </span>
                      <strong
                        style={{ margin: 0, fontSize: 14, lineHeight: 1.35, fontWeight: 800, color: theme.color }}
                      >
                        {category.title}
                      </strong>
                      <span style={buildSeoSummaryStyle(isHovered, isActive)}>{category.summary}</span>
                      <div
                        style={{
                          marginTop: 'auto',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: 10,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 11,
                            letterSpacing: '0.08em',
                            textTransform: 'uppercase',
                            color: theme.color,
                          }}
                        >
                          {isActive ? 'Active module' : 'Open module page'}
                        </span>
                        <span aria-hidden="true" style={buildSeoArrowStyle(theme.color, isHovered, isActive)}>
                          →
                        </span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        <section className="card social-ops-hub">
          <div className="widget-head">
            <div>
              <h3>Autonomous Social Operations</h3>
              <p className="muted">
                Click each module to connect accounts, generate posts, monitor trends, schedule campaigns, track KPIs,
                and run approvals.
              </p>
            </div>
            <span className="suggestion-chip">Process-by-click workflow</span>
          </div>

          <div className="ops-module-grid">
            {SOCIAL_OPS_MODULES.map((module) => {
              const accent = SOCIAL_OPS_ACCENT_BY_ID[module.id];
              const hoverKey = `ops-${module.id}`;
              const isHovered = hoveredModuleId === hoverKey;
              return (
                <Link
                  key={module.id}
                  href={`/studio/${SOCIAL_OPS_ROUTE_BY_MODULE_ID[module.id]}`}
                  onMouseEnter={() => setHoveredModuleId(hoverKey)}
                  onMouseLeave={() => setHoveredModuleId(null)}
                  onFocus={() => setHoveredModuleId(hoverKey)}
                  onBlur={() => setHoveredModuleId(null)}
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  <div style={buildSeoTileStyle(accent, isHovered)}>
                    <span style={buildSeoIconStyle(isHovered)} aria-hidden="true">
                      {module.icon}
                    </span>
                    <strong style={{ margin: 0, fontSize: 14, lineHeight: 1.35, fontWeight: 800, color: accent }}>
                      {module.title}
                    </strong>
                    <small style={{ margin: 0, ...buildSeoSummaryStyle(isHovered) }}>{module.summary}</small>
                    <div
                      style={{
                        marginTop: 'auto',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 10,
                      }}
                    >
                      <span
                        style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: accent }}
                      >
                        Open module page
                      </span>
                      <span style={buildSeoArrowStyle(accent, isHovered)} aria-hidden="true">
                        →
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="card" style={{ marginTop: 18 }}>
            <div className="widget-head">
              <div>
                <h3>Advanced Creative Surfaces</h3>
                <p className="muted">Direct launchers for all newly added Predis production features.</p>
              </div>
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
                gap: 12,
              }}
            >
              {[
                { href: '/studio/reels-factory', title: 'Reels Factory', desc: 'Generate template-driven reels.' },
                {
                  href: '/studio/short-video-factory',
                  title: 'Short Video Factory',
                  desc: 'Create vertical short-form videos.',
                },
                {
                  href: '/studio/faceless-video-engine',
                  title: 'Faceless Video Engine',
                  desc: 'Produce avatar-led UGC videos.',
                },
                { href: '/studio/avatar-builder', title: 'Avatar Builder', desc: 'Browse and select AI avatars.' },
                {
                  href: '/studio/template-system',
                  title: 'Template System',
                  desc: 'Import templates from Canva/Figma/Adobe.',
                },
                {
                  href: '/studio/image-direction',
                  title: 'AI Product Photoshoot',
                  desc: 'Generate style-based ecommerce photos.',
                },
                {
                  href: '/studio/multilingual-ads',
                  title: 'Multilingual Ads',
                  desc: 'Translate and adapt ads across languages.',
                },
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    textDecoration: 'none',
                    color: 'inherit',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    background: 'var(--surface-raised)',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <strong style={{ fontSize: 13, lineHeight: 1.35 }}>{item.title}</strong>
                  <small className="muted" style={{ lineHeight: 1.45 }}>
                    {item.desc}
                  </small>
                </Link>
              ))}
            </div>
          </div>

          <CanvaBridgePanel
            socialAccounts={socialAccounts}
            canvaAccountId={canvaAccountId}
            setCanvaAccountId={setCanvaAccountId}
            canvaDesignId={canvaDesignId}
            setCanvaDesignId={setCanvaDesignId}
            canvaDesignUrl={canvaDesignUrl}
            setCanvaDesignUrl={setCanvaDesignUrl}
            canvaHeadline={canvaHeadline}
            setCanvaHeadline={setCanvaHeadline}
            canvaCaption={canvaCaption}
            setCanvaCaption={setCanvaCaption}
            canvaPublishMode={canvaPublishMode}
            setCanvaPublishMode={setCanvaPublishMode}
            canvaPublishAt={canvaPublishAt}
            setCanvaPublishAt={setCanvaPublishAt}
            canvaImportBusy={canvaImportBusy}
            canvaImportMessage={canvaImportMessage}
            canvaImports={canvaImports}
            inputStyle={inputStyle}
            activeBrandKitName={activeBrandKit?.name}
            activeBrandKitColorsCount={activeBrandKit?.colors?.length}
            activeBrandKitFontsCount={activeBrandKit?.fonts?.length}
            onSubmitImport={() => void submitCanvaImport()}
            onApplyActiveBrandKit={applyActiveBrandKitToCanvaBridge}
            onRefreshImports={() => void loadCanvaImports()}
          />

          {opsLoading ? <p className="small-text">Loading module data...</p> : null}
          {opsMessage ? <p className="ops-inline-error">{opsMessage}</p> : null}

          {effectiveOpsModuleId === 'accounts' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>Connect social account</h4>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-connect-network">Network</label>
                    <select
                      id="social-connect-network"
                      value={connectNetwork}
                      onChange={(event) => setConnectNetwork(event.target.value)}
                      style={inputStyle}
                    >
                      {(socialCatalog.length ? socialCatalog : [{ network: 'instagram', label: 'Instagram' }]).map(
                        (provider) => (
                          <option key={provider.network} value={provider.network}>
                            {provider.label}
                          </option>
                        )
                      )}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="social-connect-handle">Handle</label>
                    <input
                      id="social-connect-handle"
                      value={connectHandle}
                      onChange={(event) => setConnectHandle(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-connect-name">Account name</label>
                  <input
                    id="social-connect-name"
                    value={connectAccountName}
                    onChange={(event) => setConnectAccountName(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div className="command-grid compact-grid">
                  <button type="button" className="command-btn command-btn-primary" onClick={connectSocialAccount}>
                    Connect account
                  </button>
                  <button type="button" className="command-btn command-btn-muted" onClick={connectAllSocialNetworks}>
                    Connect all supported networks
                  </button>
                  <button type="button" className="command-btn command-btn-muted" onClick={disconnectAllSocialNetworks}>
                    Disconnect all accounts
                  </button>
                </div>
              </section>
              <section className="ops-panel">
                <h4>Connected accounts</h4>
                {socialAccounts.length === 0 ? (
                  <p className="small-text">No connected accounts yet.</p>
                ) : (
                  <div className="ops-list">
                    {socialAccounts.map((account) => {
                      let statusColor = '#ef4444';
                      if (account.status === 'connected') statusColor = '#22c55e';
                      else if (account.status === 'pending') statusColor = '#f59e0b';
                      let statusLabel = account.status ?? 'Unknown';
                      if (account.status === 'connected') statusLabel = 'Connected';
                      else if (account.status === 'pending') statusLabel = 'Pending';
                      return (
                        <article key={account.id} className="ops-list-item ops-account-item">
                          <span
                            className={`ops-account-status-dot${account.status === 'connected' ? ' pulse' : ''}`}
                            style={{ background: statusColor, color: statusColor }}
                            title={statusLabel}
                            aria-label={statusLabel}
                          />
                          <div className="ops-account-info">
                            <strong>{account.account_name}</strong>
                            <span>
                              {account.network} • @{account.handle}
                            </span>
                          </div>
                          <span className="ops-account-status-label" style={{ color: statusColor }}>
                            {statusLabel}
                          </span>
                          <button
                            type="button"
                            className="command-btn command-btn-danger-sm"
                            aria-label={`Disconnect ${account.account_name}`}
                            onClick={() => {
                              void disconnectSocialAccount(account);
                            }}
                          >
                            Disconnect
                          </button>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'autonomous' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>AI autonomous manager</h4>
                <div className="field">
                  <label htmlFor="social-autopilot-headline">Headline</label>
                  <input
                    id="social-autopilot-headline"
                    value={postHeadline}
                    onChange={(event) => setPostHeadline(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div className="field">
                  <label htmlFor="social-autopilot-caption">Caption</label>
                  <textarea
                    id="social-autopilot-caption"
                    value={postCaption}
                    onChange={(event) => setPostCaption(event.target.value)}
                    rows={4}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </div>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-autopilot-mode">Publish mode</label>
                    <select
                      id="social-autopilot-mode"
                      value={postMode}
                      onChange={(event) => setPostMode(event.target.value as CanvaPublishMode)}
                      style={inputStyle}
                    >
                      <option value="auto">auto</option>
                      <option value="now">now</option>
                      <option value="draft">draft</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="social-autopilot-time">Preferred publish time</label>
                    <input
                      id="social-autopilot-time"
                      type="datetime-local"
                      value={postPublishAt}
                      onChange={(event) => setPostPublishAt(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-autopilot-media">Media URL (optional)</label>
                  <input
                    id="social-autopilot-media"
                    value={postMediaUrl}
                    onChange={(event) => setPostMediaUrl(event.target.value)}
                    style={inputStyle}
                    placeholder="https://..."
                  />
                </div>
                <div className="command-grid compact-grid">
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() => void runAutonomousPost('preview')}
                  >
                    Preview autonomous post
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-success"
                    onClick={() => void runAutonomousPost('publish')}
                  >
                    Publish autonomous post
                  </button>
                </div>
              </section>
              <section className="ops-panel">
                <h4>Autopilot output</h4>
                {autopilotResult ? (
                  <div className="autopilot-result">
                    {Object.entries(autopilotResult).map(([key, value]) => (
                      <dl key={key} className="autopilot-row">
                        <dt className="autopilot-key">{key.replaceAll('_', ' ')}</dt>
                        <dd className="autopilot-val">{formatAutopilotValue(value)}</dd>
                      </dl>
                    ))}
                  </div>
                ) : (
                  <p className="small-text">Run preview or publish to see AI manager output.</p>
                )}
              </section>

              <section className="ops-panel">
                <div className="section-header-row">
                  <h4>A/B Testing Lab</h4>
                  <span className="suggestion-chip">Predis</span>
                </div>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="ab-variant-count-ops">Variant count (3-10)</label>
                    <input
                      id="ab-variant-count-ops"
                      type="number"
                      min={3}
                      max={10}
                      value={bulkGenerationCount}
                      onChange={(event) => setBulkGenerationCount(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="ab-copy-tone-ops">Copy tone</label>
                    <select
                      id="ab-copy-tone-ops"
                      value={copyGenerationTone}
                      onChange={(event) => setCopyGenerationTone(event.target.value)}
                      style={inputStyle}
                    >
                      <option value="casual">Casual</option>
                      <option value="professional">Professional</option>
                      <option value="urgent">Urgent</option>
                      <option value="playful">Playful</option>
                      <option value="educational">Educational</option>
                    </select>
                  </div>
                </div>
                <div className="command-grid compact-grid" style={{ marginTop: 8 }}>
                  <button type="button" className="command-btn command-btn-success" onClick={generateAbTestingVariants}>
                    Generate A/B variants
                  </button>
                  <button type="button" className="command-btn command-btn-muted" onClick={generateCopyHooks}>
                    Generate copy/hooks
                  </button>
                </div>
                {abTestingVariants.length > 0 ? (
                  <ul className="widget-list" style={{ marginTop: 10 }}>
                    {abTestingVariants.slice(0, 5).map((variant) => (
                      <li key={variant.id}>
                        <strong>{variant.name}</strong>
                        <div className="small-text">{variant.copy}</div>
                        <div className="small-text">
                          CTR {(variant.predicted_ctr * 100).toFixed(2)}% • ROAS {variant.predicted_roas.toFixed(2)}x
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {copyVariations.length > 0 ? (
                  <ul className="widget-list" style={{ marginTop: 10 }}>
                    {copyVariations.slice(0, 3).map((variation) => (
                      <li key={variation.id}>
                        <strong>{variation.hook}</strong>
                        <div className="small-text">{variation.headline}</div>
                        <div className="small-text">
                          {variation.cta} • Est. CTR {(variation.estimated_ctr * 100).toFixed(2)}%
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'trends' ? (
            <div className="ops-panel-grid trends-grid">
              <section className="ops-panel">
                <h4>Trend intelligence</h4>
                <div className="ops-kpi-grid">
                  <article className="metric-card">
                    <p>{Number(listeningSummary?.['total_mentions'] || 0)} mentions</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(listeningSummary?.['alerts_open'] || 0)} open alerts</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.competitors_tracked || 0)} competitors tracked</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.competitor_snapshots || 0)} competitor snapshots</p>
                  </article>
                </div>
                <div className="ops-subhead">Top queries</div>
                <div className="ops-list">
                  {(Array.isArray(listeningSummary?.['top_queries'])
                    ? (listeningSummary?.['top_queries'] as Array<Record<string, unknown>>)
                    : []
                  )
                    .slice(0, 5)
                    .map((queryItem, index) => {
                      const query =
                        typeof queryItem === 'object' && queryItem
                          ? String((queryItem as { query?: string }).query || 'unknown')
                          : 'unknown';
                      const mentions =
                        typeof queryItem === 'object' && queryItem
                          ? Number((queryItem as { mentions?: number }).mentions || 0)
                          : 0;
                      return (
                        <article key={`${query}-${index}`} className="ops-list-item">
                          <strong>{query}</strong>
                          <span>{mentions} mentions</span>
                        </article>
                      );
                    })}
                </div>
              </section>
              <section className="ops-panel">
                <h4>Sentiment + cluster feed</h4>
                <div className="small-text">
                  Negative:{' '}
                  {Number((listeningSummary?.['sentiment'] as Record<string, number> | undefined)?.negative || 0)} •
                  Neutral:{' '}
                  {Number((listeningSummary?.['sentiment'] as Record<string, number> | undefined)?.neutral || 0)} •
                  Positive:{' '}
                  {Number((listeningSummary?.['sentiment'] as Record<string, number> | undefined)?.positive || 0)}
                </div>
                <div className="ops-list">
                  {listeningClusters.slice(0, 6).map((cluster, index) => (
                    <article key={`${readString(cluster.query, 'cluster')}-${index}`} className="ops-list-item">
                      <strong>
                        {readString(cluster.query, 'query')} on {readString(cluster.platform, 'platform')}
                      </strong>
                      <span>
                        {readNumber(cluster.mentions)} mentions • {readString(cluster.sentiment, 'neutral')}
                      </span>
                    </article>
                  ))}
                </div>
                <div className="ops-subhead">Latest listening mentions</div>
                <div className="ops-list">
                  {listeningMentions.slice(0, 4).map((mention, index) => (
                    <article key={`${readString(mention.id, String(index))}`} className="ops-list-item">
                      <strong>@{readString(mention.author_handle, 'unknown')}</strong>
                      <span>
                        {readString(mention.platform, 'platform')} • {readString(mention.sentiment, 'neutral')} •{' '}
                        {readNumber(mention.engagement_count)} engagement
                      </span>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'calendar' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>Schedule campaigns</h4>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-schedule-platform">Platform</label>
                    <select
                      id="social-schedule-platform"
                      value={schedulePlatform}
                      onChange={(event) => setSchedulePlatform(event.target.value)}
                      style={inputStyle}
                    >
                      <option value="linkedin">LinkedIn</option>
                      <option value="instagram">Instagram</option>
                      <option value="tiktok">TikTok</option>
                      <option value="x">X</option>
                      <option value="youtube">YouTube</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="social-schedule-time">Publish at</label>
                    <input
                      id="social-schedule-time"
                      type="datetime-local"
                      value={schedulePublishAt}
                      onChange={(event) => setSchedulePublishAt(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-schedule-text">Post text</label>
                  <textarea
                    id="social-schedule-text"
                    rows={4}
                    value={scheduleText}
                    onChange={(event) => setScheduleText(event.target.value)}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="social-schedule-media">Media URL (optional)</label>
                  <input
                    id="social-schedule-media"
                    value={scheduleMediaUrl}
                    onChange={(event) => setScheduleMediaUrl(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <button
                  type="button"
                  className="command-btn command-btn-primary"
                  onClick={() => void scheduleSocialPostAction()}
                >
                  Schedule post
                </button>
              </section>

              <section className="ops-panel">
                <h4>Drag-drop calendar</h4>
                <p className="small-text">
                  Drag a scheduled post card and drop it on a day lane to reschedule automatically.
                </p>
                <div className="calendar-lane-grid">
                  {calendarDays.map((day) => (
                    <button
                      key={day.id}
                      type="button"
                      className="calendar-lane"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={() => {
                        setCalendarDragOverDay(null);
                        handleCalendarLaneDrop(day.id);
                      }}
                      onDragEnter={(event) => {
                        event.preventDefault();
                        setCalendarDragOverDay(day.id);
                      }}
                      onDragLeave={() => setCalendarDragOverDay((prev) => (prev === day.id ? null : prev))}
                      data-drag-active={calendarDragOverDay === day.id ? 'true' : undefined}
                      style={
                        calendarDragOverDay === day.id
                          ? {
                              borderColor: '#2563eb',
                              background: 'rgba(37,99,235,0.12)',
                              boxShadow: '0 0 0 2px rgba(37,99,235,0.35)',
                            }
                          : undefined
                      }
                    >
                      <strong>{day.label}</strong>
                      {scheduledPosts
                        .filter((item) => item.publish_at.slice(0, 10) === day.id)
                        .map((item) => (
                          <article
                            key={item.id}
                            className="calendar-post"
                            draggable
                            onDragStart={() => setDraggedPostId(item.id)}
                          >
                            <span>
                              #{item.id} {item.platform}
                            </span>
                            <small>
                              {new Date(item.publish_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </small>
                          </article>
                        ))}
                    </button>
                  ))}
                </div>

                <div className="dual-grid compact" style={{ marginTop: 12 }}>
                  <div className="field">
                    <label htmlFor="social-move-id">Move post ID</label>
                    <input
                      id="social-move-id"
                      value={movePostId}
                      onChange={(event) => setMovePostId(event.target.value)}
                      style={inputStyle}
                      placeholder="Post ID"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-move-time">New publish time</label>
                    <input
                      id="social-move-time"
                      type="datetime-local"
                      value={movePublishAt}
                      onChange={(event) => setMovePublishAt(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  className="command-btn command-btn-muted"
                  onClick={() => void moveScheduledPostByForm()}
                >
                  Move by ID
                </button>
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'kpi' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>KPI dashboard</h4>
                <div className="ops-kpi-grid">
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.connected_accounts || 0)} connected accounts</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.scheduled_posts || 0)} scheduled posts</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.inbox_open || 0)} open inbox items</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.engagement_total || 0)} total engagement</p>
                  </article>
                </div>
              </section>
              <section className="ops-panel">
                <h4>ROI forecast</h4>
                <div className="ops-list">
                  {Array.from({ length: 4 }).map((_, index) => {
                    const week = index + 1;
                    const baseEngagement = Number(workspaceOpsOverview.engagement_total || 0);
                    const projected = Math.round(baseEngagement * (1 + week * 0.12));
                    const roi =
                      Math.round((projected / Math.max(1, Number(workspaceOpsOverview.connected_accounts || 1))) * 10) /
                      10;
                    return (
                      <article key={`roi-${week}`} className="ops-list-item">
                        <strong>Week {week}</strong>
                        <span>
                          Projected engagement {projected} • ROI index {roi}
                        </span>
                      </article>
                    );
                  })}
                </div>
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'approvals' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>Smart approval settings</h4>
                <div className="field">
                  <label htmlFor="social-approval-levels">Approval levels (comma separated)</label>
                  <input
                    id="social-approval-levels"
                    value={approvalLevels}
                    onChange={(event) => setApprovalLevels(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <button
                  type="button"
                  className="command-btn command-btn-muted"
                  onClick={() => void configureApprovals()}
                >
                  Save approval chain
                </button>

                <div className="ops-subhead">Submit post for approval</div>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-approval-post-id">Scheduled post ID</label>
                    <input
                      id="social-approval-post-id"
                      value={approvalPostId}
                      onChange={(event) => setApprovalPostId(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-approval-platform">Platform</label>
                    <input
                      id="social-approval-platform"
                      value={approvalPlatform}
                      onChange={(event) => setApprovalPlatform(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-approval-preview">Content preview</label>
                  <textarea
                    id="social-approval-preview"
                    rows={3}
                    value={approvalPreview}
                    onChange={(event) => setApprovalPreview(event.target.value)}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="social-approval-requester">Requested by</label>
                  <input
                    id="social-approval-requester"
                    value={approvalRequestedBy}
                    onChange={(event) => setApprovalRequestedBy(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <button
                  type="button"
                  className="command-btn command-btn-primary"
                  onClick={() => void submitApprovalRequest()}
                >
                  Submit approval request
                </button>
              </section>

              <section className="ops-panel">
                <h4>Approval queue</h4>
                {approvalRequests.length === 0 ? (
                  <p className="small-text">No approval requests yet.</p>
                ) : (
                  <div className="ops-list">
                    {approvalRequests.map((request) => (
                      <article key={request.id} className="ops-list-item">
                        <strong>
                          #{request.id} • {request.platform} • {request.status}
                        </strong>
                        <span>
                          Post #{request.scheduled_post_id} • {request.content_preview}
                        </span>
                        {request.status === 'pending' ? (
                          <div className="inline-actions">
                            <button
                              type="button"
                              className="command-btn command-btn-success"
                              onClick={() => void decideApproval(request.id, 'approved')}
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className="command-btn command-btn-muted"
                              onClick={() => void decideApproval(request.id, 'rejected')}
                            >
                              Reject
                            </button>
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          ) : null}

          {effectiveOpsModuleId === 'inbox' ? (
            <div className="ops-panel-grid">
              <section className="ops-panel">
                <h4>Smart inbox overview</h4>
                <div className="inline-actions" style={{ marginBottom: 12 }}>
                  <span className="suggestion-chip">Last sync {lastInboxSyncAt || 'pending'}</span>
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() => void loadSocialOpsData('inbox')}
                  >
                    Refresh inbox
                  </button>
                </div>
                <div className="ops-kpi-grid">
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.inbox_open || 0)} open threads</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.notifications_unread || 0)} unread notifications</p>
                  </article>
                  <article className="metric-card">
                    <p>{Number(workspaceOpsOverview.connected_accounts || 0)} response accounts</p>
                  </article>
                </div>
                <p className="small-text">
                  Use message ID + AI-assisted reply to engage, escalate, or resolve interactions.
                </p>
              </section>
              <section className="ops-panel">
                <h4>Engage message</h4>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-inbox-message-id">Message ID</label>
                    <input
                      id="social-inbox-message-id"
                      value={inboxMessageId}
                      onChange={(event) => setInboxMessageId(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-inbox-account">Account</label>
                    <input
                      id="social-inbox-account"
                      value={
                        socialAccounts[0]
                          ? `${socialAccounts[0].network} @${socialAccounts[0].handle}`
                          : 'No account connected'
                      }
                      readOnly
                      style={{ ...inputStyle, opacity: 0.8 }}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-inbox-reply">Reply text</label>
                  <textarea
                    id="social-inbox-reply"
                    rows={4}
                    value={inboxReplyText}
                    onChange={(event) => setInboxReplyText(event.target.value)}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </div>
                <button
                  type="button"
                  className="command-btn command-btn-primary"
                  onClick={() => void engageInboxMessage()}
                >
                  Send smart reply
                </button>
              </section>
              <section className="ops-panel">
                <h4>Saved reply templates</h4>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-saved-reply-title">Template title</label>
                    <input
                      id="social-saved-reply-title"
                      value={savedReplyTitle}
                      onChange={(event) => setSavedReplyTitle(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-saved-reply-category">Category</label>
                    <input
                      id="social-saved-reply-category"
                      value={savedReplyCategory}
                      onChange={(event) => setSavedReplyCategory(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-saved-reply-body">Template body</label>
                  <textarea
                    id="social-saved-reply-body"
                    rows={4}
                    value={savedReplyBody}
                    onChange={(event) => setSavedReplyBody(event.target.value)}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </div>
                <div className="inline-actions">
                  <button
                    type="button"
                    className="command-btn command-btn-secondary"
                    onClick={() => void createSavedReplyTemplate()}
                  >
                    {savedReplyEditingId ? 'Update template' : 'Save template'}
                  </button>
                  {savedReplyEditingId ? (
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={clearSavedReplyTemplateForm}
                    >
                      Cancel edit
                    </button>
                  ) : null}
                </div>
                <div className="stack-list" style={{ marginTop: 16 }}>
                  {savedReplies.length > 0 ? (
                    savedReplies.map((reply) => (
                      <article key={reply.id} className="mini-card">
                        <div className="mini-card-head">
                          <strong>{reply.title}</strong>
                          <span className="suggestion-chip">{reply.category}</span>
                        </div>
                        <p className="small-text">{reply.body}</p>
                        <div className="inline-actions">
                          <button
                            type="button"
                            className="command-btn command-btn-muted"
                            onClick={() => applySavedReplyTemplate(reply)}
                          >
                            Use in reply
                          </button>
                          <button
                            type="button"
                            className="command-btn command-btn-secondary"
                            onClick={() => applySavedReplyTemplate(reply)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="command-btn command-btn-danger"
                            onClick={() => void deleteSavedReplyTemplate(reply.id)}
                          >
                            Delete
                          </button>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="small-text">No saved replies yet. Create one above to speed up inbox responses.</p>
                  )}
                </div>
              </section>
              <section className="ops-panel">
                <h4>Inbox intelligence</h4>
                <div className="metric-card" style={{ marginBottom: 16 }}>
                  <strong>Suggested next step</strong>
                  <p className="small-text" style={{ marginTop: 8 }}>
                    {inboxTriageSuggestion.label}
                  </p>
                  <p className="small-text">{inboxTriageSuggestion.reason}</p>
                  <div className="inline-actions" style={{ marginTop: 12 }}>
                    {inboxTriageSuggestion.action === 'claim' ? (
                      <button
                        type="button"
                        className="command-btn command-btn-secondary"
                        onClick={() => void claimInboxMessage()}
                      >
                        Claim now
                      </button>
                    ) : null}
                    {inboxTriageSuggestion.action === 'complete' ? (
                      <button
                        type="button"
                        className="command-btn command-btn-muted"
                        onClick={() => void completeInboxMessage()}
                      >
                        Mark complete
                      </button>
                    ) : null}
                    {inboxTriageSuggestion.action === 'review' ? (
                      <button
                        type="button"
                        className="command-btn command-btn-secondary"
                        onClick={() => void loadInboxMessageHistory()}
                      >
                        Review history
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="command-btn command-btn-primary"
                      onClick={() => void runInboxDmChatbot()}
                      disabled={dmChatbotLoading}
                    >
                      {dmChatbotLoading ? 'Running AI chatbot...' : 'Run AI chatbot'}
                    </button>
                    <button
                      type="button"
                      className="command-btn command-btn-primary"
                      onClick={() => void generateReplySuggestions()}
                    >
                      Generate reply options
                    </button>
                  </div>
                </div>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-inbox-contact-search">Search contacts</label>
                    <input
                      id="social-inbox-contact-search"
                      value={inboxContactQuery}
                      onChange={(event) => setInboxContactQuery(event.target.value)}
                      placeholder="name, handle, sentiment, network"
                      style={inputStyle}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-inbox-sentiment-filter">Sentiment</label>
                    <select
                      id="social-inbox-sentiment-filter"
                      value={inboxSentimentFilter}
                      onChange={(event) => setInboxSentimentFilter(event.target.value)}
                      style={inputStyle}
                    >
                      <option value="all">All</option>
                      <option value="positive">Positive</option>
                      <option value="neutral">Neutral</option>
                      <option value="negative">Negative</option>
                    </select>
                  </div>
                </div>
                <div className="dual-grid compact">
                  <div className="field">
                    <label htmlFor="social-inbox-selected-contact">Selected contact</label>
                    <input
                      id="social-inbox-selected-contact"
                      value={selectedContact?.display_name || selectedContact?.handle || 'Pick a contact below'}
                      readOnly
                      style={{ ...inputStyle, opacity: 0.8 }}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="social-inbox-history-message">History message ID</label>
                    <input
                      id="social-inbox-history-message"
                      value={inboxMessageId}
                      onChange={(event) => setInboxMessageId(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="social-inbox-agent-name">Claim as</label>
                  <input
                    id="social-inbox-agent-name"
                    value={inboxClaimAgentName}
                    onChange={(event) => setInboxClaimAgentName(event.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div className="inline-actions">
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    onClick={() => void loadInboxMessageHistory()}
                  >
                    Load message history
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-secondary"
                    onClick={() => void claimInboxMessage()}
                  >
                    Claim message
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() => void completeInboxMessage()}
                  >
                    Mark complete
                  </button>
                </div>
                <div className="inline-actions" style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() => selectInboxMessagesBy((item) => item.state !== 'complete' && !item.responded)}
                  >
                    Select open
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() =>
                      selectInboxMessagesBy((item) => item.state === 'complete' || Boolean(item.responded))
                    }
                  >
                    Select completed
                  </button>
                  <button type="button" className="command-btn command-btn-muted" onClick={clearInboxSelection}>
                    Clear selection
                  </button>
                </div>
                <p className="small-text" style={{ marginTop: 8 }}>
                  Selected {inboxSelectionSummary.selectedCount} messages ({inboxSelectionSummary.openCount} open,{' '}
                  {inboxSelectionSummary.completeCount} complete)
                </p>
                <div className="inline-actions" style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    className="command-btn command-btn-secondary"
                    onClick={() => void runBulkInboxAction('claim')}
                    disabled={bulkInboxActionLoading || selectedInboxMessageIds.length === 0}
                  >
                    {bulkInboxActionLoading ? 'Running...' : `Bulk claim (${selectedInboxMessageIds.length})`}
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-muted"
                    onClick={() => void runBulkInboxAction('complete')}
                    disabled={bulkInboxActionLoading || selectedInboxMessageIds.length === 0}
                  >
                    {bulkInboxActionLoading ? 'Running...' : `Bulk complete (${selectedInboxMessageIds.length})`}
                  </button>
                </div>
                <div className="inline-actions" style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    onClick={() => void runInboxDmChatbot()}
                    disabled={dmChatbotLoading}
                  >
                    {dmChatbotLoading ? 'Running AI chatbot...' : 'Run AI chatbot'}
                  </button>
                  <button
                    type="button"
                    className="command-btn command-btn-secondary"
                    onClick={() => void generateReplySuggestions()}
                    disabled={replySuggestionsLoading}
                  >
                    {replySuggestionsLoading ? 'Generating...' : 'Generate reply suggestions'}
                  </button>
                </div>
                <div className="stack-list" style={{ marginTop: 16 }}>
                  {inboxItems.length > 0 ? (
                    inboxItems.map((item) => {
                      const numericId = Number.parseInt(item.id, 10);
                      const isSelected = Number.isFinite(numericId) && selectedInboxMessageIds.includes(numericId);
                      return (
                        <article key={item.id} className="mini-card">
                          <div className="mini-card-head">
                            <strong>{item.source}</strong>
                            <span className="suggestion-chip">{item.sentiment}</span>
                          </div>
                          <p className="small-text">
                            #{item.id} • {item.network} • {item.state}
                          </p>
                          <p className="small-text">{item.content}</p>
                          <div className="inline-actions">
                            <button
                              type="button"
                              className="command-btn command-btn-muted"
                              onClick={() => {
                                setInboxMessageId(item.id);
                                if (Number.isFinite(numericId)) {
                                  toggleInboxMessageSelection(numericId);
                                }
                              }}
                            >
                              {isSelected ? 'Deselect' : 'Select'}
                            </button>
                            <button
                              type="button"
                              className="command-btn command-btn-secondary"
                              onClick={() => {
                                setInboxMessageId(item.id);
                                void loadInboxMessageHistory();
                              }}
                            >
                              Inspect
                            </button>
                          </div>
                        </article>
                      );
                    })
                  ) : (
                    <p className="small-text">No inbox messages loaded yet for selection.</p>
                  )}
                </div>
                <div className="stack-list" style={{ marginTop: 16 }}>
                  {filteredContactViews.length > 0 ? (
                    filteredContactViews.map((contact) => (
                      <article key={contact.handle} className="mini-card">
                        <div className="mini-card-head">
                          <strong>{contact.display_name}</strong>
                          <span className="suggestion-chip">{contact.sentiment}</span>
                        </div>
                        <p className="small-text">
                          @{contact.handle} • {contact.message_count} messages •{' '}
                          {contact.networks.join(', ') || 'unknown network'}
                        </p>
                        <p className="small-text">Last message: {contact.last_message_at}</p>
                        <div className="inline-actions">
                          <button
                            type="button"
                            className="command-btn command-btn-muted"
                            onClick={() => setSelectedContactHandle(contact.handle)}
                          >
                            Inspect
                          </button>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="small-text">No matching contacts. Try clearing the search or sentiment filter.</p>
                  )}
                </div>
                <div className="stack-list" style={{ marginTop: 16 }}>
                  {messageHistory.length > 0 ? (
                    messageHistory.map((message, index) => (
                      <article key={`${toDisplayText(message.id, String(index))}-${index}`} className="mini-card">
                        <div className="mini-card-head">
                          <strong>
                            {toDisplayText(message.author_display_name) ||
                              toDisplayText(message.author_handle) ||
                              toDisplayText(message.author) ||
                              'Message'}
                          </strong>
                          <span className="suggestion-chip">{toDisplayText(message.network, 'unknown')}</span>
                        </div>
                        <p className="small-text">
                          {toDisplayText(message.text) || toDisplayText(message.body) || toDisplayText(message.content)}
                        </p>
                        <p className="small-text">{toDisplayText(message.created_at)}</p>
                      </article>
                    ))
                  ) : (
                    <p className="small-text">Load a message history to see the conversation trail for that contact.</p>
                  )}
                </div>
                <div className="stack-list" style={{ marginTop: 16 }}>
                  {replySuggestions.length > 0 ? (
                    replySuggestions.map((suggestion) => (
                      <article key={suggestion.action} className="mini-card">
                        <div className="mini-card-head">
                          <strong>{suggestion.label}</strong>
                          <span className="suggestion-chip">{suggestion.provider}</span>
                        </div>
                        <p className="small-text">{suggestion.result}</p>
                        <div className="inline-actions">
                          <button
                            type="button"
                            className="command-btn command-btn-muted"
                            onClick={() => applyReplySuggestion(suggestion)}
                          >
                            Use suggestion
                          </button>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="small-text">Generate reply suggestions from the latest message or current draft.</p>
                  )}
                </div>
              </section>
            </div>
          ) : null}
        </section>

        <section className="card hubspot-hub">
          <div className="widget-head">
            <div>
              <h3>HubSpot features</h3>
              <p className="muted">
                Open each HubSpot capability to wire CRM, automation, and attribution into Social Studio.
              </p>
            </div>
            <span className="suggestion-chip">HubSpot stack</span>
          </div>
          <div className="hubspot-grid">
            {HUBSPOT_FEATURES.map((feature) => (
              <a key={feature.id} href={feature.href} target="_blank" rel="noreferrer" className="hubspot-link-card">
                <strong>{feature.title}</strong>
                <span>{feature.summary}</span>
                <em>Open link ↗</em>
              </a>
            ))}
          </div>
        </section>

        {lastError ? (
          <section className="card alert-card">
            <strong>Studio alert</strong>
            <p>{lastError}</p>
          </section>
        ) : null}

        <section className="main-layout">
          <section className="builder-stack">
            <section className="card block">
              <div className="widget-head">
                <div>
                  <h3>Workload builder</h3>
                  <p className="muted">Configure briefs, channels, brand constraints, and inputs in one place.</p>
                </div>
                <span className="suggestion-chip">{selectedCategory.deliveryMode}</span>
              </div>

              <div className="field">
                <label htmlFor="social-studio-brief">Creative brief</label>
                <textarea
                  id="social-studio-brief"
                  rows={7}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </div>

              <div className="dual-grid">
                <div className="field">
                  <label htmlFor="social-studio-complexity">Complexity</label>
                  <select
                    id="social-studio-complexity"
                    value={complexity}
                    onChange={(event) => setComplexity(event.target.value as Complexity)}
                    style={inputStyle}
                  >
                    <option value="auto">Auto route</option>
                    <option value="simple">Simple</option>
                    <option value="standard">Standard</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="social-studio-tenant">Tenant</label>
                  <input id="social-studio-tenant" value={tenantId} readOnly style={{ ...inputStyle, opacity: 0.8 }} />
                </div>
              </div>

              <div className="field">
                <div className="field-title">Target channels</div>
                <div className="chip-wrap">
                  {CHANNEL_OPTIONS.map((channel) => (
                    <button
                      key={channel}
                      type="button"
                      onClick={() => setTargetChannels((current) => toggleSelection(current, channel))}
                      className={`toggle-chip ${targetChannels.includes(channel) ? 'active-brand' : ''}`}
                    >
                      {channel}
                    </button>
                  ))}
                </div>
              </div>

              <div className="dual-grid">
                <div className="field">
                  <div className="field-title">Brand rules</div>
                  <div className="chip-wrap">
                    {BRAND_RULE_OPTIONS.map((rule) => (
                      <button
                        key={rule}
                        type="button"
                        onClick={() => setBrandRules((current) => toggleSelection(current, rule))}
                        className={`toggle-chip ${brandRules.includes(rule) ? 'active-success' : ''}`}
                      >
                        {rule}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="field">
                  <div className="field-title">Editing tools</div>
                  <div className="chip-wrap">
                    {EDIT_TOOL_OPTIONS.map((tool) => (
                      <button
                        key={tool}
                        type="button"
                        onClick={() => setEditTools((current) => toggleSelection(current, tool))}
                        className={`toggle-chip ${editTools.includes(tool) ? 'active-brand' : ''}`}
                      >
                        {tool}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="upload-grid">
                <label
                  className={`upload-box upload-box-image ${uploadDragZone === 'image' ? 'is-dragging' : ''}`}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setUploadDragZone('image');
                  }}
                  onDragLeave={() => setUploadDragZone((previous) => (previous === 'image' ? null : previous))}
                  onDrop={(event) => handleUploadDrop('image', event)}
                >
                  <div className="upload-head">
                    <span className="upload-icon" aria-hidden="true">
                      🖼️
                    </span>
                    <div>
                      <span>Reference images</span>
                      <small>PNG, JPG, WEBP for style and composition control</small>
                    </div>
                  </div>
                  <input
                    className="upload-input"
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={(event) => handleUploadInput('image', event.target.files)}
                  />
                  <div className="upload-meta">
                    <em>{imageFiles.length} selected</em>
                    <strong>Choose files</strong>
                  </div>
                  <div className="upload-progress-wrap">
                    <div className="upload-progress-track">
                      <div
                        className={`upload-progress-fill${busy === 'generating' && imageProgressValue > 0 && imageProgressValue < 100 ? ' is-active' : ''}`}
                        style={{ width: `${imageProgressValue}%` }}
                      />
                    </div>
                    <small className="upload-progress-label">{imageProgressLabel}</small>
                  </div>
                  {imageFiles.length > 0 ? (
                    <div className="upload-file-list">
                      {imageFiles.slice(0, 3).map((file) => (
                        <span key={`${file.name}-${file.lastModified}`} className="upload-file-chip">
                          <span className="upload-file-chip-name">{file.name}</span>
                          <span className="upload-file-size">{formatFileSize(file.size)}</span>
                          <button
                            type="button"
                            className="upload-file-remove"
                            aria-label={`Remove ${file.name}`}
                            onClick={(event) => {
                              event.preventDefault();
                              removeUploadFile('image', file);
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                      {imageFiles.length > 3 ? <span>+{imageFiles.length - 3} more</span> : null}
                    </div>
                  ) : null}
                  {busy === 'generating' && imageFileUploadRows.length > 0 ? (
                    <div className="upload-file-progress-list">
                      {imageFileUploadRows.slice(0, 3).map((row) => (
                        <div key={row.id} className="upload-file-progress-row">
                          <div className="upload-file-progress-meta">
                            <span>{row.name}</span>
                            <em>{row.progressPct}%</em>
                          </div>
                          <div className="upload-file-progress-track">
                            <div className="upload-file-progress-fill" style={{ width: `${row.progressPct}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </label>
                <label
                  className={`upload-box upload-box-video ${uploadDragZone === 'video' ? 'is-dragging' : ''}`}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setUploadDragZone('video');
                  }}
                  onDragLeave={() => setUploadDragZone((previous) => (previous === 'video' ? null : previous))}
                  onDrop={(event) => handleUploadDrop('video', event)}
                >
                  <div className="upload-head">
                    <span className="upload-icon" aria-hidden="true">
                      🎬
                    </span>
                    <div>
                      <span>Reference videos</span>
                      <small>MP4, MOV clips for pacing and motion cues</small>
                    </div>
                  </div>
                  <input
                    className="upload-input"
                    type="file"
                    accept="video/*"
                    multiple
                    onChange={(event) => handleUploadInput('video', event.target.files)}
                  />
                  <div className="upload-meta">
                    <em>{videoFiles.length} selected</em>
                    <strong>Choose files</strong>
                  </div>
                  <div className="upload-progress-wrap">
                    <div className="upload-progress-track">
                      <div
                        className={`upload-progress-fill${busy === 'generating' && videoProgressValue > 0 && videoProgressValue < 100 ? ' is-active' : ''}`}
                        style={{ width: `${videoProgressValue}%` }}
                      />
                    </div>
                    <small className="upload-progress-label">{videoProgressLabel}</small>
                  </div>
                  {videoFiles.length > 0 ? (
                    <div className="upload-file-list">
                      {videoFiles.slice(0, 3).map((file) => (
                        <span key={`${file.name}-${file.lastModified}`} className="upload-file-chip">
                          <span className="upload-file-chip-name">{file.name}</span>
                          <span className="upload-file-size">{formatFileSize(file.size)}</span>
                          <button
                            type="button"
                            className="upload-file-remove"
                            aria-label={`Remove ${file.name}`}
                            onClick={(event) => {
                              event.preventDefault();
                              removeUploadFile('video', file);
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                      {videoFiles.length > 3 ? <span>+{videoFiles.length - 3} more</span> : null}
                    </div>
                  ) : null}
                  {busy === 'generating' && videoFileUploadRows.length > 0 ? (
                    <div className="upload-file-progress-list">
                      {videoFileUploadRows.slice(0, 3).map((row) => (
                        <div key={row.id} className="upload-file-progress-row">
                          <div className="upload-file-progress-meta">
                            <span>{row.name}</span>
                            <em>{row.progressPct}%</em>
                          </div>
                          <div className="upload-file-progress-track">
                            <div className="upload-file-progress-fill" style={{ width: `${row.progressPct}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </label>
                <label
                  className={`upload-box upload-box-audio ${uploadDragZone === 'audio' ? 'is-dragging' : ''}`}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setUploadDragZone('audio');
                  }}
                  onDragLeave={() => setUploadDragZone((previous) => (previous === 'audio' ? null : previous))}
                  onDrop={(event) => handleUploadDrop('audio', event)}
                >
                  <div className="upload-head">
                    <span className="upload-icon" aria-hidden="true">
                      🎧
                    </span>
                    <div>
                      <span>Reference audio</span>
                      <small>WAV, MP3, M4A for voice and sonic direction</small>
                    </div>
                  </div>
                  <input
                    className="upload-input"
                    type="file"
                    accept="audio/*"
                    multiple
                    onChange={(event) => handleUploadInput('audio', event.target.files)}
                  />
                  <div className="upload-meta">
                    <em>{audioFiles.length} selected</em>
                    <strong>Choose files</strong>
                  </div>
                  <div className="upload-progress-wrap">
                    <div className="upload-progress-track">
                      <div
                        className={`upload-progress-fill${busy === 'generating' && audioProgressValue > 0 && audioProgressValue < 100 ? ' is-active' : ''}`}
                        style={{ width: `${audioProgressValue}%` }}
                      />
                    </div>
                    <small className="upload-progress-label">{audioProgressLabel}</small>
                  </div>
                  {audioFiles.length > 0 ? (
                    <div className="upload-file-list">
                      {audioFiles.slice(0, 3).map((file) => (
                        <span key={`${file.name}-${file.lastModified}`} className="upload-file-chip">
                          <span className="upload-file-chip-name">{file.name}</span>
                          <span className="upload-file-size">{formatFileSize(file.size)}</span>
                          <button
                            type="button"
                            className="upload-file-remove"
                            aria-label={`Remove ${file.name}`}
                            onClick={(event) => {
                              event.preventDefault();
                              removeUploadFile('audio', file);
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                      {audioFiles.length > 3 ? <span>+{audioFiles.length - 3} more</span> : null}
                    </div>
                  ) : null}
                  {busy === 'generating' && audioFileUploadRows.length > 0 ? (
                    <div className="upload-file-progress-list">
                      {audioFileUploadRows.slice(0, 3).map((row) => (
                        <div key={row.id} className="upload-file-progress-row">
                          <div className="upload-file-progress-meta">
                            <span>{row.name}</span>
                            <em>{row.progressPct}%</em>
                          </div>
                          <div className="upload-file-progress-track">
                            <div className="upload-file-progress-fill" style={{ width: `${row.progressPct}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </label>
              </div>
            </section>

            <section className="card block preview-stage-card">
              <div className="section-header-row">
                <h3>Generated outcome preview</h3>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {hasMultipleGenerated ? (
                    <>
                      <button
                        type="button"
                        className="command-btn command-btn-muted"
                        onClick={() => setPreviewAssetIndex((index) => (index > 0 ? index - 1 : generated.length - 1))}
                        style={{ padding: '4px 8px', fontSize: '12px' }}
                      >
                        ← Prev
                      </button>
                      <span className="suggestion-chip">
                        {previewAssetIndex + 1} of {generated.length}
                      </span>
                      <button
                        type="button"
                        className="command-btn command-btn-muted"
                        onClick={() => setPreviewAssetIndex((index) => (index < generated.length - 1 ? index + 1 : 0))}
                        style={{ padding: '4px 8px', fontSize: '12px' }}
                      >
                        Next →
                      </button>
                    </>
                  ) : null}
                  <span className="suggestion-chip">{previewStatusLabel}</span>
                </div>
              </div>

              {busy === 'generating' && !currentPreviewAsset ? (
                <div className="preview-stage-shell">
                  <div className="output-item output-preview-item">
                    <div className="skeleton-line" />
                    <div className="skeleton-line short" />
                    <div className="skeleton-media preview-stage-skeleton" />
                  </div>
                </div>
              ) : null}

              {!currentPreviewAsset && busy !== 'generating' ? (
                <div className="preview-stage-shell preview-stage-empty">
                  <div className="preview-stage-copy">
                    <strong>{selectedCategory.title}</strong>
                    <p className="muted">
                      Your generated content, image, voice, or video preview will appear here immediately after a
                      successful preview or generation.
                    </p>
                    <div className="preview-stage-meta">
                      <span>{selectedCategory.mediaType}</span>
                      <span>{selectedCategory.deliveryMode}</span>
                      <span>{selectedCategory.outputs.join(' • ')}</span>
                    </div>
                  </div>
                </div>
              ) : null}

              {currentPreviewAsset ? (
                <article className="output-item output-preview-item preview-stage-shell">
                  <div className="widget-head">
                    <div>
                      <strong>{currentPreviewAsset.title}</strong>
                      <div className="small-text">
                        {currentPreviewAsset.provider} • {currentPreviewAsset.credits} credits •{' '}
                        {currentPreviewAsset.createdAt}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => downloadAsset(currentPreviewAsset)}
                      className="command-btn command-btn-muted"
                    >
                      Download
                    </button>
                  </div>
                  <p>{currentPreviewAsset.content}</p>
                  {currentPreviewAsset.type === 'image' && currentPreviewAsset.mediaUrl ? (
                    <img
                      src={currentPreviewAsset.mediaUrl}
                      alt={currentPreviewAsset.title}
                      className="media-frame output-preview-frame"
                    />
                  ) : null}
                  {currentPreviewAsset.type === 'video' && currentPreviewAsset.mediaUrl ? (
                    <video controls className="media-frame output-preview-frame">
                      <source src={currentPreviewAsset.mediaUrl} />
                      <track kind="captions" srcLang="en" label="Generated captions unavailable" />
                    </video>
                  ) : null}
                  {currentPreviewAsset.type === 'voice' && currentPreviewAsset.mediaUrl ? (
                    <audio controls style={{ width: '100%' }}>
                      <source src={currentPreviewAsset.mediaUrl} />
                      <track kind="captions" srcLang="en" label="Generated transcript unavailable" />
                    </audio>
                  ) : null}
                </article>
              ) : null}
            </section>

            <section className="command-rail card">
              <div className="command-head">
                <h3>Global controls</h3>
                <div className="rail-meta">
                  <span className="suggestion-chip">Status: {statusLabel}</span>
                  <fieldset className="density-toggle" aria-label="Density mode">
                    <button
                      type="button"
                      className={`density-btn ${density === 'comfortable' ? 'active' : ''}`}
                      onClick={() => setDensity('comfortable')}
                    >
                      Comfortable
                    </button>
                    <button
                      type="button"
                      className={`density-btn ${density === 'compact' ? 'active' : ''}`}
                      onClick={() => setDensity('compact')}
                    >
                      Compact
                    </button>
                  </fieldset>
                </div>
              </div>
              <div className="command-grid">
                <button
                  ref={previewButtonRef}
                  type="button"
                  onClick={previewPlan}
                  disabled={busy !== 'idle'}
                  className="command-btn command-btn-muted"
                  aria-keyshortcuts="P"
                >
                  Preview orchestration (P)
                </button>
                <button
                  ref={generateButtonRef}
                  type="button"
                  onClick={generate}
                  disabled={busy !== 'idle' || !prompt.trim()}
                  className="command-btn command-btn-primary"
                  aria-keyshortcuts="G"
                >
                  Launch generation (G)
                </button>
                <button
                  ref={quoteButtonRef}
                  type="button"
                  onClick={requestQuote}
                  disabled={busy !== 'idle'}
                  className="command-btn command-btn-muted"
                  aria-keyshortcuts="Q"
                >
                  Quote credits (Q)
                </button>
                <button
                  ref={checkoutButtonRef}
                  type="button"
                  onClick={checkoutCredits}
                  disabled={busy !== 'idle'}
                  className="command-btn command-btn-muted"
                  aria-keyshortcuts="K"
                >
                  Create checkout (K)
                </button>
                <button
                  ref={confirmButtonRef}
                  type="button"
                  onClick={confirmCredits}
                  disabled={busy !== 'idle' || !checkout}
                  className="command-btn command-btn-success"
                  aria-keyshortcuts="C"
                >
                  Confirm payment (C)
                </button>
              </div>
              <div className="predis-toggle-groups">
                <section className="predis-toggle-group" aria-label="Core Predis tools">
                  <p className="predis-toggle-label">Core Predis Tools</p>
                  <div className="predis-toggle-grid">
                    <button
                      type="button"
                      aria-pressed={showAbTestPanel}
                      className={`predis-toggle-btn ${showAbTestPanel ? 'active' : ''}`}
                      onClick={() => setShowAbTestPanel((p) => !p)}
                    >
                      Predis A/B Lab
                    </button>
                    <button
                      type="button"
                      aria-pressed={showCopyGeneratorPanel}
                      className={`predis-toggle-btn ${showCopyGeneratorPanel ? 'active' : ''}`}
                      onClick={() => setShowCopyGeneratorPanel((p) => !p)}
                    >
                      Copy Generator
                    </button>
                    <button
                      type="button"
                      aria-pressed={showContentCalendarPanel}
                      className={`predis-toggle-btn ${showContentCalendarPanel ? 'active' : ''}`}
                      onClick={() => setShowContentCalendarPanel((p) => !p)}
                    >
                      Content Calendar
                    </button>
                    <button
                      type="button"
                      aria-pressed={showBrandKitPanel}
                      className={`predis-toggle-btn ${showBrandKitPanel ? 'active' : ''}`}
                      onClick={() => {
                        setShowBrandKitPanel((p) => !p);
                        if (!showBrandKitPanel) void loadBrandKits();
                      }}
                    >
                      Brand Kit Studio
                    </button>
                    <button
                      type="button"
                      aria-pressed={showVoiceoverPanel}
                      className={`predis-toggle-btn ${showVoiceoverPanel ? 'active' : ''}`}
                      onClick={() => setShowVoiceoverPanel((p) => !p)}
                    >
                      Voiceover Lab
                    </button>
                    <button
                      type="button"
                      aria-pressed={showPerformanceAnalysisPanel}
                      className={`predis-toggle-btn ${showPerformanceAnalysisPanel ? 'active' : ''}`}
                      onClick={() => setShowPerformanceAnalysisPanel((p) => !p)}
                    >
                      Performance AI
                    </button>
                    <button
                      type="button"
                      aria-pressed={showAnimationEffectsPanel}
                      className={`predis-toggle-btn ${showAnimationEffectsPanel ? 'active' : ''}`}
                      onClick={() => {
                        setShowAnimationEffectsPanel((p) => !p);
                        if (!showAnimationEffectsPanel) void loadAnimationEffects();
                      }}
                    >
                      Animation FX
                    </button>
                    <button
                      type="button"
                      aria-pressed={showCompetitorAnalysisPanel}
                      className={`predis-toggle-btn ${showCompetitorAnalysisPanel ? 'active' : ''}`}
                      onClick={() => setShowCompetitorAnalysisPanel((p) => !p)}
                    >
                      Competitor Intel
                    </button>
                    <button
                      type="button"
                      aria-pressed={showBulkGenerationPanel}
                      className={`predis-toggle-btn ${showBulkGenerationPanel ? 'active' : ''}`}
                      onClick={() => setShowBulkGenerationPanel((p) => !p)}
                    >
                      Bulk Generator
                    </button>
                  </div>
                </section>
                <section className="predis-toggle-group" aria-label="Creative Predis tools">
                  <p className="predis-toggle-label">Creative Boosters</p>
                  <div className="predis-toggle-grid">
                    <button
                      type="button"
                      aria-pressed={showMemeGeneratorPanel}
                      className={`predis-toggle-btn ${showMemeGeneratorPanel ? 'active' : ''}`}
                      onClick={() => setShowMemeGeneratorPanel((p) => !p)}
                    >
                      Meme Factory
                    </button>
                    <button
                      type="button"
                      aria-pressed={showQuoteToPostPanel}
                      className={`predis-toggle-btn ${showQuoteToPostPanel ? 'active' : ''}`}
                      onClick={() => setShowQuoteToPostPanel((p) => !p)}
                    >
                      Quote Studio
                    </button>
                    <button
                      type="button"
                      aria-pressed={showHolidayPostPanel}
                      className={`predis-toggle-btn ${showHolidayPostPanel ? 'active' : ''}`}
                      onClick={() => setShowHolidayPostPanel((p) => !p)}
                    >
                      Holiday Posts
                    </button>
                    <button
                      type="button"
                      aria-pressed={showEcommercePostPanel}
                      className={`predis-toggle-btn ${showEcommercePostPanel ? 'active' : ''}`}
                      onClick={() => setShowEcommercePostPanel((p) => !p)}
                    >
                      Ecom Posts
                    </button>
                    <button
                      type="button"
                      aria-pressed={showAssetLibraryPanel}
                      className={`predis-toggle-btn ${showAssetLibraryPanel ? 'active' : ''}`}
                      onClick={() => {
                        setShowAssetLibraryPanel((p) => !p);
                        if (!showAssetLibraryPanel) void searchAssetLibrary(1);
                      }}
                    >
                      Asset Library
                    </button>
                    <button
                      type="button"
                      aria-pressed={showChatIdeationPanel}
                      className={`predis-toggle-btn ${showChatIdeationPanel ? 'active' : ''}`}
                      onClick={() => setShowChatIdeationPanel((p) => !p)}
                    >
                      AI Ideation Chat
                    </button>
                  </div>
                </section>
              </div>
              <p className="shortcut-hint">
                Shortcuts: P preview, G generate, Q quote, K checkout, C confirm, D density toggle.
              </p>
              {busy === 'generating' ? (
                <div className="progress-wrap" role="status" aria-live="polite">
                  <div className="progress-meta">
                    <span>Rendering in progress</span>
                    <span>{generationEtaSeconds}s ETA</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${generationProgressPct}%` }} />
                  </div>
                </div>
              ) : null}
              <div className="quick-grid">
                <div className="metric-card">
                  <p>{hasPlan ? 'Plan ready' : 'No plan yet'}</p>
                </div>
                <div className="metric-card">
                  <p>{totalReferenceFiles} files attached</p>
                </div>
                <div className="metric-card">
                  <p>{totalGeneratedCredits} credits consumed</p>
                </div>
              </div>
            </section>
          </section>

          <aside className="ops-stack">
            <section className="card block">
              <h3>Provider orchestration</h3>
              {busy === 'planning' || busy === 'generating' ? (
                <div className="stack">
                  <div className="skeleton-line" />
                  <div className="skeleton-line short" />
                  <div className="skeleton-list">
                    <div className="skeleton-line" />
                    <div className="skeleton-line" />
                    <div className="skeleton-line" />
                  </div>
                </div>
              ) : null}
              {plan ? (
                <div className="stack">
                  <div className="dual-grid compact">
                    <div className="metric-card">
                      <p>{plan.recommended_provider.provider}</p>
                    </div>
                    <div className="metric-card">
                      <p>{plan.estimated_credits} credits</p>
                    </div>
                  </div>
                  <p className="muted" style={{ margin: 0 }}>
                    {plan.quality_policy}
                  </p>
                  <ul className="widget-list">
                    {plan.workflow.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                  <div className="stack">
                    {plan.provider_candidates.map((candidate) => (
                      <div key={candidate.provider} className="candidate-row">
                        <strong>{candidate.provider}</strong>
                        <span>
                          {candidate.quality} quality • rank {candidate.cost_rank} • {candidate.supports.join(', ')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="muted">
                  Preview orchestration to inspect provider routing, quality policy, and credit estimates.
                </p>
              )}
            </section>

            <section className="card block">
              <h3>Credit command center</h3>
              <p className="muted">Quote, checkout, and confirm are required before credits are applied.</p>
              <input
                value={topupCredits}
                onChange={(event) => setTopupCredits(event.target.value)}
                type="number"
                min={1}
                style={inputStyle}
              />
              <div className="command-grid compact-grid">
                <button
                  type="button"
                  onClick={requestQuote}
                  disabled={busy !== 'idle'}
                  className="command-btn command-btn-muted"
                >
                  Quote
                </button>
                <button
                  type="button"
                  onClick={checkoutCredits}
                  disabled={busy !== 'idle'}
                  className="command-btn command-btn-muted"
                >
                  Create checkout
                </button>
                <button
                  type="button"
                  onClick={confirmCredits}
                  disabled={busy !== 'idle' || !checkout}
                  className="command-btn command-btn-success"
                >
                  Confirm payment
                </button>
              </div>
              {quote ? (
                <p className="small-text">
                  Quote: {quote.credits} credits for ${quote.total_usd.toFixed(2)} at ${quote.unit_price_usd.toFixed(2)}
                  /credit.
                </p>
              ) : null}
              {checkout ? (
                <p className="small-text">
                  Pending invoice #{checkout.id} • {checkout.payment_reference} • ${checkout.amount.toFixed(2)}
                </p>
              ) : null}
            </section>

            <section className="card block">
              <h3>Provider health</h3>
              {overview.providers.length === 0 ? (
                <p className="muted">Provider health has not been reported yet.</p>
              ) : (
                <div className="stack">
                  {overview.providers.map((provider) => (
                    <div key={provider.name} className="health-row">
                      <span>{provider.name}</span>
                      <strong className={provider.status === 'ok' ? 'ok' : 'warn'}>{provider.status}</strong>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </aside>
        </section>

        {hasAnyPredisPanelOpen ? null : (
          <section className="card block">
            <div className="section-header-row">
              <h3>A/B Testing Lab</h3>
              <span className="suggestion-chip">Predis</span>
            </div>
            <div className="dual-grid compact" style={{ marginBottom: 10 }}>
              <div className="field">
                <label htmlFor="ab-variant-count">Variant count (3-10)</label>
                <input
                  id="ab-variant-count"
                  type="number"
                  min={3}
                  max={10}
                  value={bulkGenerationCount}
                  onChange={(event) => setBulkGenerationCount(event.target.value)}
                  style={inputStyle}
                />
              </div>
              <div className="field">
                <label htmlFor="ab-channel">Primary channel</label>
                <input
                  id="ab-channel"
                  value={targetChannels[0] || 'instagram'}
                  readOnly
                  style={{ ...inputStyle, opacity: 0.85 }}
                />
              </div>
            </div>
            <button type="button" className="command-btn command-btn-success" onClick={generateAbTestingVariants}>
              Generate variants
            </button>
            {abTestingVariants.length > 0 ? (
              <ul className="widget-list" style={{ marginTop: 10 }}>
                {abTestingVariants.map((variant) => (
                  <li key={variant.id}>
                    <strong>{variant.name}</strong>
                    <div className="small-text">{variant.copy}</div>
                    <div className="small-text">Hook: {variant.prompt_hook}</div>
                    <div className="small-text">
                      CTA: {variant.cta} • CTR {(variant.predicted_ctr * 100).toFixed(2)}% • ROAS{' '}
                      {variant.predicted_roas.toFixed(2)}x
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        )}

        <section className="bottom-layout">
          {/* ── PREDIS FEATURE PANELS ─────────────────────────────────────────────────── */}
          {hasAnyPredisPanelOpen && (
            <section className="predis-panels-section">
              {showAbTestPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Predis A/B Testing Lab</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowAbTestPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div className="dual-grid compact" style={{ marginBottom: 10 }}>
                    <div className="field">
                      <label htmlFor="ab-variant-count">Variant count (3-10)</label>
                      <input
                        id="ab-variant-count"
                        type="number"
                        min={3}
                        max={10}
                        value={bulkGenerationCount}
                        onChange={(event) => setBulkGenerationCount(event.target.value)}
                        style={inputStyle}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="ab-channel">Primary channel</label>
                      <input
                        id="ab-channel"
                        value={targetChannels[0] || 'instagram'}
                        readOnly
                        style={{ ...inputStyle, opacity: 0.85 }}
                      />
                    </div>
                  </div>
                  <button type="button" className="command-btn command-btn-success" onClick={generateAbTestingVariants}>
                    Generate variants
                  </button>
                  {abTestingVariants.length > 0 ? (
                    <ul className="widget-list" style={{ marginTop: 10 }}>
                      {abTestingVariants.map((variant) => (
                        <li key={variant.id}>
                          <strong>{variant.name}</strong>
                          <div className="small-text">{variant.copy}</div>
                          <div className="small-text">Hook: {variant.prompt_hook}</div>
                          <div className="small-text">
                            CTA: {variant.cta} • CTR {(variant.predicted_ctr * 100).toFixed(2)}% • ROAS{' '}
                            {variant.predicted_roas.toFixed(2)}x
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {activeAbTest ? (
                    <p className="small-text" style={{ marginTop: 8 }}>
                      Session: {activeAbTest.name} ({activeAbTest.status})
                    </p>
                  ) : null}
                </section>
              ) : null}

              {showCopyGeneratorPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Predis Copy &amp; Hook Generator</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowCopyGeneratorPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div className="dual-grid compact">
                    <div className="field">
                      <label htmlFor="copy-category">Category</label>
                      <select
                        id="copy-category"
                        value={copyGenerationCategory}
                        onChange={(event) => setCopyGenerationCategory(event.target.value)}
                        style={inputStyle}
                      >
                        <option value="ecommerce">E-Commerce</option>
                        <option value="b2b">B2B</option>
                        <option value="wellness">Wellness</option>
                        <option value="tech">Tech</option>
                        <option value="travel">Travel</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="copy-tone">Tone</label>
                      <select
                        id="copy-tone"
                        value={copyGenerationTone}
                        onChange={(event) => setCopyGenerationTone(event.target.value)}
                        style={inputStyle}
                      >
                        <option value="casual">Casual</option>
                        <option value="professional">Professional</option>
                        <option value="urgent">Urgent</option>
                        <option value="playful">Playful</option>
                        <option value="educational">Educational</option>
                      </select>
                    </div>
                  </div>
                  <div className="field" style={{ marginTop: 10 }}>
                    <label htmlFor="copy-product">Product/Service</label>
                    <input
                      id="copy-product"
                      value={copyGenerationProduct}
                      onChange={(event) => setCopyGenerationProduct(event.target.value)}
                      style={inputStyle}
                      placeholder="Premium social automation suite"
                    />
                  </div>
                  <button type="button" className="command-btn command-btn-success" onClick={generateCopyHooks}>
                    Generate copy variants
                  </button>
                  {copyVariations.length > 0 ? (
                    <ul className="widget-list" style={{ marginTop: 10 }}>
                      {copyVariations.map((variation) => (
                        <li key={variation.id}>
                          <strong>{variation.hook}</strong>
                          <div className="small-text">
                            <strong>Headline:</strong> {variation.headline}
                          </div>
                          <div className="small-text">
                            <strong>CTA:</strong> {variation.cta} • Est. CTR{' '}
                            {(Number(variation.estimated_ctr || 0) * 100).toFixed(2)}%
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ) : null}

              {showContentCalendarPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Predis Content Calendar</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowContentCalendarPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div className="command-grid compact-grid" style={{ marginBottom: 10 }}>
                    <button
                      type="button"
                      className={`density-btn ${contentCalendar.view_mode === 'month' ? 'active' : ''}`}
                      onClick={() => setContentCalendar((previous) => ({ ...previous, view_mode: 'month' }))}
                    >
                      Month
                    </button>
                    <button
                      type="button"
                      className={`density-btn ${contentCalendar.view_mode === 'week' ? 'active' : ''}`}
                      onClick={() => setContentCalendar((previous) => ({ ...previous, view_mode: 'week' }))}
                    >
                      Week
                    </button>
                    <button
                      type="button"
                      className={`density-btn ${contentCalendar.view_mode === 'day' ? 'active' : ''}`}
                      onClick={() => setContentCalendar((previous) => ({ ...previous, view_mode: 'day' }))}
                    >
                      Day
                    </button>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => void loadSocialOpsData('calendar')}
                    >
                      Refresh
                    </button>
                  </div>
                  <div className="field" style={{ marginBottom: 10 }}>
                    <label htmlFor="calendar-selected-date">Selected date</label>
                    <input
                      id="calendar-selected-date"
                      type="date"
                      value={calendarSelectedDate}
                      onChange={(event) => setCalendarSelectedDate(event.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  {scheduledPosts.length === 0 ? (
                    <p className="muted">No scheduled posts yet.</p>
                  ) : (
                    <ul className="widget-list">
                      {scheduledPosts
                        .filter(
                          (post) =>
                            contentCalendar.view_mode === 'day' ||
                            String(post.publish_at || '').slice(0, 10) === calendarSelectedDate
                        )
                        .slice(0, contentCalendar.view_mode === 'day' ? 20 : 8)
                        .map((post) => (
                          <li key={post.id}>
                            <strong>{post.platform}</strong>
                            <div className="small-text">{post.text}</div>
                            <div className="small-text">
                              Publish: {post.publish_at} • Status: {post.status}
                            </div>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
              ) : null}

              {showCompetitorAnalysisPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Competitor Intel</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowCompetitorAnalysisPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    <div className="field-label">Competitor URL</div>
                    <input
                      className="form-input"
                      value={competitorUrl}
                      onChange={(e) => setCompetitorUrl(e.target.value)}
                      placeholder="https://competitor-brand.com"
                    />
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    onClick={() => void runCompetitorAnalysis()}
                  >
                    Analyze Competitor
                  </button>
                  {competitorAnalysis ? (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                        <div>
                          <p style={{ fontSize: 12, fontWeight: 600 }}>
                            Competitor: {competitorAnalysis.competitor_name}
                          </p>
                          <p style={{ fontSize: 11, marginTop: 4 }}>
                            Est. Monthly Reach: {competitorAnalysis.estimated_reach?.toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <p style={{ fontSize: 12, fontWeight: 600 }}>Avg Post Engagement</p>
                          <p style={{ fontSize: 11, marginTop: 4 }}>
                            {(competitorAnalysis.avg_engagement_rate * 100).toFixed(2)}% ·{' '}
                            {competitorAnalysis.avg_comments ?? '0'} comments
                          </p>
                        </div>
                      </div>
                      {(competitorAnalysis.top_ads?.length ?? 0) > 0 ? (
                        <div style={{ marginTop: 10 }}>
                          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Top Performing Ads</p>
                          <ul style={{ fontSize: 11, paddingLeft: 16 }}>
                            {competitorAnalysis.top_ads.map((ad) => (
                              <li key={ad.id}>
                                {ad.hook} (CTR: {(ad.ctr * 100).toFixed(1)}%)
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {(competitorAnalysis.gap_opportunities?.length ?? 0) > 0 ? (
                        <div style={{ marginTop: 10 }}>
                          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Market Gaps</p>
                          <ul style={{ fontSize: 11, paddingLeft: 16 }}>
                            {competitorAnalysis.gap_opportunities?.map((gap) => (
                              <li key={gap}>{gap}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showBulkGenerationPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Bulk Generator</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowBulkGenerationPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Media Type</div>
                      <select
                        className="form-input"
                        value={bulkMediaType}
                        onChange={(e) => setBulkMediaType(e.target.value)}
                      >
                        {['image', 'video', 'carousel'].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <div className="field-label">Count</div>
                      <input
                        className="form-input"
                        type="number"
                        min="1"
                        max="50"
                        value={bulkCount}
                        onChange={(e) => setBulkCount(e.target.value)}
                      />
                    </div>
                    <div>
                      <div className="field-label">&nbsp;</div>
                      <button
                        type="button"
                        className="command-btn command-btn-primary"
                        onClick={() => void startBulkGeneration()}
                      >
                        Start Job
                      </button>
                    </div>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <div className="field-label">Prompt (optional)</div>
                    <textarea
                      className="form-input"
                      rows={2}
                      value={bulkPrompt}
                      onChange={(e) => setBulkPrompt(e.target.value)}
                      placeholder="Describe what you want to generate..."
                    />
                  </div>
                  {activeBulkJob ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Job {activeBulkJob.id}</strong> · {activeBulkJob.status} ·{' '}
                        {activeBulkJob.completed_count ?? activeBulkJob.completed_items}/
                        {activeBulkJob.total_count ?? activeBulkJob.total_items} items
                      </p>
                    </div>
                  ) : null}
                  {bulkGenerationJobs.length > 0 ? (
                    <div style={{ marginTop: 12 }}>
                      <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Recent Jobs</p>
                      <ul className="ops-list">
                        {bulkGenerationJobs.map((job) => (
                          <li key={job.id} className="ops-list-item">
                            <strong>Job {job.id}</strong>
                            <span>
                              {job.status} · {job.completed_count ?? job.completed_items}/
                              {job.total_count ?? job.total_items}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showMemeGeneratorPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Meme Factory</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowMemeGeneratorPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Template</div>
                      <select
                        className="form-input"
                        value={memeTemplate}
                        onChange={(e) => setMemeTemplate(e.target.value)}
                      >
                        {[
                          'distracted-boyfriend',
                          'drake',
                          'woman-yelling-cat',
                          'two-buttons',
                          'this-is-fine',
                          'expanding-brain',
                          'loss',
                          'one-does-not-simply',
                          'success-kid',
                          'bad-luck-brian',
                        ].map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                      <button type="button" className="command-btn command-btn-muted" style={{ fontSize: 11 }}>
                        Template preview
                      </button>
                    </div>
                  </div>
                  <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Top Text</div>
                      <input
                        className="form-input"
                        value={memeTopText}
                        onChange={(e) => setMemeTopText(e.target.value)}
                        placeholder="Top caption"
                      />
                    </div>
                    <div>
                      <div className="field-label">Bottom Text</div>
                      <input
                        className="form-input"
                        value={memeBottomText}
                        onChange={(e) => setMemeBottomText(e.target.value)}
                        placeholder="Bottom caption"
                      />
                    </div>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <div className="field-label">Brand Caption</div>
                    <input
                      className="form-input"
                      value={memeCaption}
                      onChange={(e) => setMemeCaption(e.target.value)}
                      placeholder="Add brand mention or call-to-action"
                    />
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runMemeGenerator()}
                  >
                    Generate Meme
                  </button>
                  {generatedMeme ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Meme ready</strong> · ID: {generatedMeme.id}
                      </p>
                      {generatedMeme.image_url ? (
                        <img
                          src={generatedMeme.image_url}
                          alt="Generated meme"
                          style={{ maxWidth: '100%', maxHeight: 300, marginTop: 8 }}
                        />
                      ) : null}
                      {generatedMeme.hashtags?.length > 0 ? (
                        <p style={{ fontSize: 11, marginTop: 6 }}>
                          Suggested tags: {generatedMeme.hashtags.join(', ')}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showQuoteToPostPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Quote Studio</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowQuoteToPostPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    <div className="field-label">Quote Text</div>
                    <textarea
                      className="form-input"
                      rows={2}
                      value={quoteText}
                      onChange={(e) => setQuoteText(e.target.value)}
                      placeholder="Enter inspirational or witty quote"
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Author</div>
                      <input
                        className="form-input"
                        value={quoteAuthor}
                        onChange={(e) => setQuoteAuthor(e.target.value)}
                        placeholder="Attribution"
                      />
                    </div>
                    <div>
                      <div className="field-label">Visual Style</div>
                      <select className="form-input" value={quoteStyle} onChange={(e) => setQuoteStyle(e.target.value)}>
                        {['modern-card', 'neon', 'minimal', 'script', 'bold-sans', 'elegant', 'chalkboard'].map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runQuoteToPost()}
                  >
                    Generate Quote Post
                  </button>
                  {generatedQuotePost ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Quote post ready</strong>
                      </p>
                      <p style={{ fontSize: 12, fontStyle: 'italic', marginTop: 6 }}>
                        &ldquo;{generatedQuotePost.caption}&rdquo;
                      </p>
                      {generatedQuotePost.image_url ? (
                        <img
                          src={generatedQuotePost.image_url}
                          alt="Quote visual"
                          style={{ maxWidth: '100%', maxHeight: 280, marginTop: 8 }}
                        />
                      ) : null}
                      {generatedQuotePost.hashtags?.length > 0 ? (
                        <p style={{ fontSize: 11, marginTop: 6 }}>Tags: {generatedQuotePost.hashtags.join(', ')}</p>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showHolidayPostPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Holiday Posts</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowHolidayPostPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Holiday</div>
                      <select
                        className="form-input"
                        value={holidayName}
                        onChange={(e) => setHolidayName(e.target.value)}
                      >
                        {[
                          `New Year`,
                          `Easter`,
                          `Mother's Day`,
                          `Father's Day`,
                          `July 4th`,
                          `Halloween`,
                          `Thanksgiving`,
                          `Christmas`,
                          `Black Friday`,
                        ].map((h) => (
                          <option key={h} value={h}>
                            {h}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <div className="field-label">Theme</div>
                      <select
                        className="form-input"
                        value={holidayTheme}
                        onChange={(e) => setHolidayTheme(e.target.value)}
                      >
                        {['celebration', 'deal', 'gratitude', 'reflection', 'giving'].map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runHolidayPost()}
                  >
                    Generate Holiday Post
                  </button>
                  {generatedHolidayPost ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>{generatedHolidayPost.visual_style}</strong> post generated
                      </p>
                      <p style={{ fontSize: 12, marginTop: 6 }}>{generatedHolidayPost.caption}</p>
                      <p style={{ fontSize: 11, marginTop: 4, fontWeight: 600 }}>CTA: {generatedHolidayPost.cta}</p>
                      {generatedHolidayPost.image_url ? (
                        <img
                          src={generatedHolidayPost.image_url}
                          alt="Holiday post"
                          style={{ maxWidth: '100%', maxHeight: 280, marginTop: 8 }}
                        />
                      ) : null}
                      {generatedHolidayPost.hashtags?.length > 0 ? (
                        <p style={{ fontSize: 11, marginTop: 6 }}>Tags: {generatedHolidayPost.hashtags.join(', ')}</p>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showEcommercePostPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Ecom Posts</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowEcommercePostPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Product Name</div>
                      <input
                        className="form-input"
                        value={ecomProductName}
                        onChange={(e) => setEcomProductName(e.target.value)}
                        placeholder="e.g., Premium Wireless Headphones"
                      />
                    </div>
                    <div>
                      <div className="field-label">Product URL</div>
                      <input
                        className="form-input"
                        value={ecomProductUrl}
                        onChange={(e) => setEcomProductUrl(e.target.value)}
                        placeholder="https://shop.example.com/product/123"
                      />
                    </div>
                  </div>
                  <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Price</div>
                      <input
                        className="form-input"
                        value={ecomProductPrice}
                        onChange={(e) => setEcomProductPrice(e.target.value)}
                        placeholder="$99.99"
                      />
                    </div>
                    <div>
                      <div className="field-label">Discount %</div>
                      <input
                        className="form-input"
                        value={ecomDiscount}
                        onChange={(e) => setEcomDiscount(e.target.value)}
                        placeholder="20"
                      />
                    </div>
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runEcommercePost()}
                  >
                    Generate Product Post
                  </button>
                  {generatedEcomPost ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>{generatedEcomPost.headline}</strong>
                      </p>
                      <p style={{ fontSize: 12, marginTop: 6 }}>{generatedEcomPost.caption}</p>
                      <p style={{ fontSize: 11, marginTop: 4, fontWeight: 600 }}>CTA: {generatedEcomPost.cta}</p>
                      {generatedEcomPost.image_url ? (
                        <img
                          src={generatedEcomPost.image_url}
                          alt="Product post"
                          style={{ maxWidth: '100%', maxHeight: 280, marginTop: 8 }}
                        />
                      ) : null}
                      {generatedEcomPost.hashtags?.length > 0 ? (
                        <p style={{ fontSize: 11, marginTop: 6 }}>Tags: {generatedEcomPost.hashtags.join(', ')}</p>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showAssetLibraryPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Asset Library</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowAssetLibraryPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10, marginBottom: 10 }}>
                    <div>
                      <div className="field-label">Search</div>
                      <input
                        className="form-input"
                        value={assetLibraryQuery}
                        onChange={(e) => setAssetLibraryQuery(e.target.value)}
                        placeholder="Search by name or tag"
                      />
                    </div>
                    <div>
                      <div className="field-label">Category</div>
                      <select
                        className="form-input"
                        value={assetLibraryCategory}
                        onChange={(e) => setAssetLibraryCategory(e.target.value)}
                      >
                        {['all', 'photos', 'illustrations', 'icons', 'graphics', 'video-clips'].map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                      <button
                        type="button"
                        className="command-btn command-btn-primary"
                        onClick={() => void searchAssetLibrary(1)}
                      >
                        Search
                      </button>
                    </div>
                  </div>
                  {assetLibraryResults.length > 0 ? (
                    <div>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))',
                          gap: 8,
                          marginBottom: 10,
                        }}
                      >
                        {assetLibraryResults.map((asset) => (
                          <article
                            key={asset.id}
                            style={{
                              cursor: 'pointer',
                              border: '1px solid var(--line)',
                              borderRadius: 8,
                              overflow: 'hidden',
                              padding: 8,
                            }}
                          >
                            {asset.thumb_url ? (
                              <img
                                src={asset.thumb_url}
                                alt={asset.title}
                                style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 4 }}
                              />
                            ) : null}
                            <p style={{ fontSize: 11, fontWeight: 600, marginTop: 6 }}>{asset.title}</p>
                            <p style={{ fontSize: 10, color: 'var(--muted-fg)' }}>{asset.type}</p>
                          </article>
                        ))}
                      </div>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                        <button
                          type="button"
                          className="command-btn command-btn-muted"
                          disabled={assetLibraryPage === 1}
                          onClick={() => void searchAssetLibrary(assetLibraryPage - 1)}
                        >
                          Prev
                        </button>
                        <span style={{ fontSize: 12, display: 'flex', alignItems: 'center' }}>
                          Page {assetLibraryPage} of {Math.ceil(assetLibraryTotal / 24)}
                        </span>
                        <button
                          type="button"
                          className="command-btn command-btn-muted"
                          disabled={assetLibraryPage >= Math.ceil(assetLibraryTotal / 24)}
                          onClick={() => void searchAssetLibrary(assetLibraryPage + 1)}
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showChatIdeationPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>AI Ideation Chat</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowChatIdeationPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: 'max(300px, 60vh)' }}>
                    <div
                      style={{
                        flex: 1,
                        overflowY: 'auto',
                        border: '1px solid var(--line)',
                        borderRadius: 8,
                        padding: 12,
                        backgroundColor: 'var(--slightly-muted-bg, rgba(0,0,0,0.02))',
                      }}
                    >
                      {chatMessages.length === 0 ? (
                        <p style={{ fontSize: 12, color: 'var(--muted-fg)' }}>
                          Start a conversation about your content strategy. Ask about trends, hooks, or scheduling
                          advice.
                        </p>
                      ) : (
                        chatMessages.map((msg) => (
                          <div
                            key={`${msg.timestamp}-${msg.role}`}
                            style={{
                              marginBottom: 12,
                              display: 'flex',
                              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            }}
                          >
                            <div
                              style={{
                                maxWidth: '70%',
                                padding: '8px 12px',
                                borderRadius: 8,
                                backgroundColor: msg.role === 'user' ? 'var(--brand, #6366f1)' : 'var(--line)',
                                color: msg.role === 'user' ? 'white' : 'inherit',
                                fontSize: 12,
                              }}
                            >
                              {msg.content}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <textarea
                        className="form-input"
                        rows={2}
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && e.ctrlKey) void sendChatMessage();
                        }}
                        placeholder="Type your question... (Ctrl+Enter to send)"
                        style={{ flex: 1, resize: 'none' }}
                      />
                      <button
                        type="button"
                        className="command-btn command-btn-primary"
                        style={{ alignSelf: 'flex-end' }}
                        onClick={() => void sendChatMessage()}
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </section>
              ) : null}

              {showBrandKitPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Brand Kit Studio</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowBrandKitPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Kit Name</div>
                      <input
                        className="form-input"
                        value={brandKitName}
                        onChange={(e) => setBrandKitName(e.target.value)}
                        placeholder="My Holiday Campaign Kit"
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                      <button
                        type="button"
                        className="command-btn command-btn-primary"
                        onClick={() => void saveBrandKit()}
                      >
                        Save Brand Kit
                      </button>
                    </div>
                  </div>
                  {activeBrandKit ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Active:</strong> {activeBrandKit.name}
                      </p>
                      <p style={{ fontSize: 11, marginTop: 4 }}>
                        Colors: {activeBrandKit.colors?.length ?? 0} · Fonts: {activeBrandKit.fonts?.length ?? 0}
                      </p>
                    </div>
                  ) : null}
                  {brandKits.length > 0 ? (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Saved Kits</p>
                      <ul className="ops-list">
                        {brandKits.slice(0, 8).map((kit) => (
                          <li key={kit.id} className="ops-list-item" style={{ padding: 0 }}>
                            <button
                              type="button"
                              onClick={() => setActiveBrandKit(kit)}
                              style={{
                                width: '100%',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                gap: 10,
                                background: 'transparent',
                                border: 'none',
                                color: 'inherit',
                                padding: '10px 12px',
                                textAlign: 'left',
                                cursor: 'pointer',
                              }}
                            >
                              <strong>{kit.name}</strong>
                              <span>
                                {kit.colors?.length ?? 0} colors · {kit.fonts?.length ?? 0} fonts
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showVoiceoverPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Voiceover Lab</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowVoiceoverPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div>
                    <div className="field-label">Script</div>
                    <textarea
                      className="form-input"
                      rows={3}
                      value={voiceoverText}
                      onChange={(e) => setVoiceoverText(e.target.value)}
                      placeholder="Type your script text..."
                    />
                  </div>
                  <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Voice</div>
                      <input
                        className="form-input"
                        value={voiceoverVoiceName}
                        onChange={(e) => setVoiceoverVoiceName(e.target.value)}
                        placeholder="Liam"
                      />
                    </div>
                    <div>
                      <div className="field-label">Emotion</div>
                      <select
                        className="form-input"
                        value={voiceoverEmotion}
                        onChange={(e) => setVoiceoverEmotion(e.target.value)}
                      >
                        {['neutral', 'energetic', 'calm', 'confident'].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
                      <div>
                        <div className="field-label">Speed</div>
                        <input
                          className="form-input"
                          type="number"
                          step="0.1"
                          min="0.5"
                          max="2"
                          value={voiceoverSpeed}
                          onChange={(e) => setVoiceoverSpeed(Number(e.target.value) || 1)}
                        />
                      </div>
                      <div>
                        <div className="field-label">Pitch</div>
                        <input
                          className="form-input"
                          type="number"
                          step="0.1"
                          min="0.5"
                          max="2"
                          value={voiceoverPitch}
                          onChange={(e) => setVoiceoverPitch(Number(e.target.value) || 1)}
                        />
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runVoiceover()}
                  >
                    Generate Voiceover
                  </button>
                  {voiceoverResult ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Voiceover ready</strong>
                      </p>
                      <p style={{ fontSize: 11, marginTop: 4 }}>Duration: {voiceoverResult.duration_ms} ms</p>
                      {voiceoverResult.voiceover_url ? (
                        <a
                          href={voiceoverResult.voiceover_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: 12 }}
                        >
                          Open audio
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showPerformanceAnalysisPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Performance AI</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowPerformanceAnalysisPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Channel</div>
                      <select
                        className="form-input"
                        value={perfChannel}
                        onChange={(e) => setPerfChannel(e.target.value)}
                      >
                        {['instagram', 'facebook', 'tiktok', 'linkedin', 'youtube'].map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <div className="field-label">Media Type</div>
                      <select
                        className="form-input"
                        value={perfMediaType}
                        onChange={(e) => setPerfMediaType(e.target.value)}
                      >
                        {['image', 'video', 'carousel', 'text'].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="command-btn command-btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={() => void runPerformancePrediction()}
                  >
                    Predict Performance
                  </button>
                  {performancePredictions ? (
                    <div className="result-card" style={{ marginTop: 10 }}>
                      <p>
                        <strong>Estimated CTR:</strong> {(performancePredictions.estimated_ctr * 100).toFixed(2)}%
                      </p>
                      <p style={{ fontSize: 11 }}>
                        <strong>ROAS:</strong> {performancePredictions.estimated_roas.toFixed(2)} ·{' '}
                        <strong>Confidence:</strong> {(performancePredictions.confidence_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  ) : null}
                </section>
              ) : null}

              {showAnimationEffectsPanel ? (
                <section className="card block">
                  <div className="section-header-row">
                    <h3>Animation FX</h3>
                    <button
                      type="button"
                      className="command-btn command-btn-muted"
                      onClick={() => setShowAnimationEffectsPanel(false)}
                    >
                      Close
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
                    <div>
                      <div className="field-label">Target</div>
                      <input
                        className="form-input"
                        value={animationTarget}
                        onChange={(e) => setAnimationTarget(e.target.value)}
                        placeholder="Post ID or asset URL"
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                      <button
                        type="button"
                        className="command-btn command-btn-primary"
                        onClick={() => void loadAnimationEffects()}
                      >
                        Load Effects
                      </button>
                    </div>
                  </div>
                  {animationEffects.length > 0 ? (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Available Effects</p>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))',
                          gap: 8,
                        }}
                      >
                        {animationEffects.map((fx) => (
                          <button
                            key={fx.id}
                            type="button"
                            className="command-btn command-btn-muted"
                            style={{ textAlign: 'left' }}
                            onClick={() => setSelectedAnimationEffect(fx)}
                          >
                            <strong>{fx.name}</strong>
                            <div style={{ fontSize: 11, marginTop: 4 }}>
                              {fx.category} · {fx.duration}ms
                            </div>
                          </button>
                        ))}
                      </div>
                      {selectedAnimationEffect ? (
                        <p style={{ fontSize: 11, marginTop: 8 }}>Selected: {selectedAnimationEffect.name}</p>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              ) : null}
            </section>
          )}

          <section className="card block">
            <div className="section-header-row">
              <h3>Ops timeline</h3>
              {activity.length > 0 && (
                <button
                  type="button"
                  className="command-btn command-btn-muted"
                  style={{ fontSize: 11, padding: '2px 8px' }}
                  onClick={() => setActivity([])}
                >
                  Clear all
                </button>
              )}
            </div>
            {activity.length === 0 ? (
              <p className="muted">No activity yet. Plan a workload or run a credit operation.</p>
            ) : (
              <ul className="widget-list">
                {activity.map((item) => (
                  <li key={item.id} style={{ borderColor: getActivityBorderColor(item.tone) }}>
                    <div className="activity-row">
                      <div>
                        <strong>{item.label}</strong>
                        <div className="small-text">{item.createdAt}</div>
                      </div>
                      <button
                        type="button"
                        className="activity-dismiss-btn"
                        aria-label={`Dismiss: ${item.label}`}
                        onClick={() => dismissActivity(item.id)}
                      >
                        ✕
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card block">
            <h3>Output wall</h3>
            {shouldShowOutputSkeleton ? (
              <div className="stack">
                <div className="output-item">
                  <div className="skeleton-line" />
                  <div className="skeleton-line short" />
                  <div className="skeleton-media" />
                </div>
                <div className="output-item">
                  <div className="skeleton-line" />
                  <div className="skeleton-line short" />
                  <div className="skeleton-media" />
                </div>
              </div>
            ) : null}
            {!shouldShowOutputSkeleton && generated.length === 0 ? (
              <p className="muted">
                No outputs yet. Successful generation jobs will appear here with provider and credit metadata.
              </p>
            ) : null}
            {generated.length > 0 ? (
              <div className="stack">
                {generated.map((item) => (
                  <article key={item.id} className="output-item">
                    <div className="widget-head">
                      <div>
                        <strong>{item.title}</strong>
                        <div className="small-text">
                          {item.provider} • {item.credits} credits • {item.createdAt}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => downloadAsset(item)}
                        className="command-btn command-btn-muted"
                      >
                        Download
                      </button>
                    </div>
                    <p>{item.content}</p>
                    {item.type === 'image' && item.mediaUrl ? (
                      <img src={item.mediaUrl} alt={item.title} className="media-frame" />
                    ) : null}
                    {item.type === 'video' && item.mediaUrl ? (
                      <video controls className="media-frame">
                        <source src={item.mediaUrl} />
                        <track kind="captions" srcLang="en" label="Generated captions unavailable" />
                      </video>
                    ) : null}
                    {item.type === 'voice' && item.mediaUrl ? (
                      <audio controls style={{ width: '100%' }}>
                        <source src={item.mediaUrl} />
                        <track kind="captions" srcLang="en" label="Generated transcript unavailable" />
                      </audio>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}
          </section>
        </section>

        {isCommandPaletteOpen ? (
          <dialog open className="palette-backdrop" aria-label="Command palette">
            <section className="palette">
              <button
                type="button"
                className="palette-close"
                onClick={closeCommandPalette}
                aria-label="Close command palette"
              >
                Close
              </button>
              <input
                autoFocus
                value={commandQuery}
                onChange={(event) => setCommandQuery(event.target.value)}
                placeholder="Search actions or press a shortcut key..."
                className="palette-input"
              />
              <div className="palette-list">
                {filteredCommandActions.length === 0 ? (
                  <div className="palette-empty">No matching actions.</div>
                ) : (
                  filteredCommandActions.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      disabled={action.disabled}
                      className="palette-item"
                      onClick={() => {
                        closeCommandPalette();
                        action.run();
                      }}
                    >
                      <span>{action.title}</span>
                      <kbd>{action.shortcut}</kbd>
                    </button>
                  ))
                )}
              </div>
            </section>
          </dialog>
        ) : null}

        {toasts.length > 0 && (
          <div className="toast-container" role="status" aria-live="polite" aria-atomic="false">
            {toasts.map((toast) => (
              <div key={toast.id} className={`toast toast-${toast.tone}`}>
                <span className="toast-message">{toast.message}</span>
                <button
                  type="button"
                  className="toast-dismiss"
                  aria-label="Dismiss notification"
                  onClick={() => dismissToast(toast.id)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .social-studio-page {
          display: grid;
          gap: 16px;
          padding-bottom: 20px;
          background:
            radial-gradient(circle at 0% -15%, rgba(57, 176, 255, 0.12), transparent 42%),
            radial-gradient(circle at 100% -10%, rgba(72, 252, 196, 0.12), transparent 44%),
            linear-gradient(180deg, rgba(5, 16, 28, 0.9), rgba(6, 17, 31, 0.95));
          transition:
            opacity 180ms ease,
            transform 220ms ease;
          will-change: opacity, transform;
        }

        .social-studio-page.page-loading {
          opacity: 0.975;
          transform: translateY(2px);
        }

        .social-studio-page.page-loading .preview-stage-card,
        .social-studio-page.page-loading .command-rail,
        .social-studio-page.page-loading .social-ops-hub,
        .social-studio-page.page-loading .hubspot-hub,
        .social-studio-page.page-loading .predis-panels-section {
          transition:
            opacity 180ms ease,
            transform 220ms ease;
          opacity: 0.94;
          transform: translateY(2px);
        }

        .tower-wrap {
          width: min(1220px, 100%);
          margin: 0 auto;
          display: grid;
          gap: 16px;
          font-family:
            Manrope,
            Segoe UI,
            ui-sans-serif,
            sans-serif;
        }

        .tower-hero {
          border-radius: 20px;
          border: 1px solid var(--module-hero-border, #1e3a8a);
          background: var(--module-hero-bg, linear-gradient(135deg, #eef0f4 0%, #eef0f4 52%, #6366f1 130%));
        }

        .tower-copy p {
          max-width: 760px;
        }

        .hero-inline-error {
          margin-top: 14px;
          font-size: 13px;
          color: #dc2626;
        }

        .modules-shell {
          padding: 0;
          border: none;
          background: transparent;
        }

        .modules-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
          margin-bottom: 12px;
        }

        .modules-head h3 {
          margin: 0;
        }

        .tower-grid {
          margin-top: 0;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
          gap: 14px;
        }

        .hero-shell {
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 24%, var(--line));
          border-radius: 18px;
          padding: 24px;
          background:
            radial-gradient(circle at 0% 10%, var(--module-glow-one, rgba(27, 199, 255, 0.2)), transparent 38%),
            radial-gradient(circle at 100% 0%, var(--module-glow-two, rgba(38, 215, 142, 0.18)), transparent 32%),
            linear-gradient(165deg, rgba(5, 18, 32, 0.95), rgba(10, 30, 46, 0.85));
          display: grid;
          gap: 18px;
        }

        .hero-copy h1 {
          margin: 0;
          font-size: clamp(1.8rem, 2.8vw, 3rem);
          letter-spacing: -0.03em;
        }

        .hero-copy p {
          margin: 10px 0 0;
          color: var(--muted);
          max-width: 760px;
        }

        .hero-lately-link a {
          color: var(--brand);
          text-decoration: none;
          font-weight: 600;
          border-bottom: 1px solid rgba(165, 180, 252, 0.3);
        }

        .hero-lately-link a:hover {
          color: #c7d2fe;
          border-bottom-color: rgba(199, 210, 254, 0.8);
        }

        .hero-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
          gap: 10px;
        }

        .command-rail {
          position: relative;
          z-index: 4;
          backdrop-filter: blur(10px);
          background:
            radial-gradient(circle at 8% 0%, rgba(var(--module-accent-rgb, 76, 141, 255), 0.18), transparent 32%),
            radial-gradient(circle at 100% 0%, rgba(var(--module-accent-2-rgb, 43, 217, 127), 0.15), transparent 34%),
            linear-gradient(140deg, rgba(8, 24, 38, 0.88), rgba(8, 27, 35, 0.82));
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 18%, var(--line));
          padding: 16px;
          box-shadow: 0 18px 36px rgba(3, 8, 18, 0.35);
        }

        .command-head {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: center;
          margin-bottom: 10px;
        }

        .rail-meta {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .density-toggle {
          display: inline-flex;
          border: 1px solid var(--line);
          border-radius: 999px;
          overflow: hidden;
          background: rgba(255, 255, 255, 0.03);
          margin: 0;
          padding: 0;
        }

        .density-btn {
          border: none;
          background: transparent;
          color: var(--muted);
          padding: 6px 10px;
          font-size: 12px;
          cursor: pointer;
        }

        .density-btn.active {
          color: var(--text);
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.16);
        }

        .shortcut-hint {
          margin: 10px 0 0;
          font-size: 12px;
          color: var(--muted);
        }

        .predis-toggle-groups {
          margin-top: 10px;
          display: grid;
          gap: 10px;
        }

        .predis-toggle-group {
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 22%, var(--line));
          border-radius: 14px;
          padding: 10px;
          background: linear-gradient(150deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
        }

        .predis-toggle-label {
          margin: 0 0 8px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: color-mix(in oklab, var(--module-accent, #4c8dff) 70%, #d8e9ff);
        }

        .predis-toggle-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 144px), 1fr));
          gap: 8px;
        }

        .predis-toggle-btn {
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 20%, var(--line));
          background: rgba(255, 255, 255, 0.02);
          color: #c8d6ea;
          border-radius: 10px;
          padding: 8px 10px;
          font-size: 12px;
          font-weight: 700;
          text-align: left;
          transition:
            transform 130ms ease,
            box-shadow 180ms ease,
            border-color 180ms ease,
            color 180ms ease,
            background 180ms ease;
          cursor: pointer;
        }

        .predis-toggle-btn:hover {
          transform: translateY(-1px);
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 48%, #87deff);
          color: #eef5ff;
        }

        .predis-toggle-btn.active {
          color: #07162c;
          border-color: transparent;
          background: linear-gradient(
            125deg,
            color-mix(in oklab, var(--module-accent, #4c8dff) 86%, #bff3ff),
            color-mix(in oklab, var(--module-accent-2, #2bd97f) 76%, #d2ffd8)
          );
          box-shadow: 0 10px 24px rgba(7, 20, 40, 0.28);
        }

        .progress-wrap {
          margin-top: 10px;
          display: grid;
          gap: 6px;
        }

        .progress-meta {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          font-size: 12px;
          color: var(--muted);
        }

        .progress-track {
          height: 8px;
          border-radius: 999px;
          border: 1px solid var(--line);
          overflow: hidden;
          background: rgba(255, 255, 255, 0.04);
        }

        .progress-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--module-accent, #4c8dff), var(--module-accent-2, #2bd97f));
          transition: width 250ms ease;
        }

        .suggestion-chip {
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 40%, var(--line));
          background: color-mix(in oklab, var(--module-accent, #4c8dff) 14%, transparent);
          color: color-mix(in oklab, var(--module-accent, #4c8dff) 82%, #e7f0ff);
          border-radius: 999px;
          padding: 5px 10px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }

        .command-head h3 {
          margin: 0;
        }

        .command-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr));
          gap: 10px;
        }

        .quick-grid {
          margin-top: 10px;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr));
          gap: 10px;
        }

        .alert-card {
          border-color: #ff6b6b;
          color: #ffd5d5;
        }

        .alert-card p {
          margin-bottom: 0;
        }

        .social-ops-hub {
          display: grid;
          gap: 12px;
          border: 1px solid color-mix(in oklab, var(--module-accent-2, #2bd97f) 26%, var(--line));
          background: linear-gradient(135deg, rgba(7, 24, 33, 0.9), rgba(8, 25, 41, 0.86));
        }

        .hubspot-hub {
          display: grid;
          gap: 12px;
          border: 1px solid color-mix(in oklab, #f59e0b 24%, var(--line));
          background: linear-gradient(135deg, rgba(30, 20, 4, 0.42), rgba(8, 20, 34, 0.86));
        }

        .hubspot-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
          gap: 12px;
        }

        .hubspot-link-card {
          border: 1px solid color-mix(in oklab, #f59e0b 35%, var(--line));
          border-radius: 12px;
          padding: 12px;
          display: grid;
          gap: 8px;
          text-decoration: none;
          color: inherit;
          background: rgba(255, 255, 255, 0.02);
          transition:
            border-color 160ms ease,
            transform 160ms ease,
            box-shadow 180ms ease;
        }

        .hubspot-link-card:hover,
        .hubspot-link-card:focus-visible {
          transform: translateY(-2px);
          border-color: #f59e0b;
          box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
        }

        .hubspot-link-card strong {
          font-size: 13px;
          color: #f9c770;
        }

        .hubspot-link-card span {
          font-size: 12px;
          color: var(--muted);
          line-height: 1.45;
        }

        .hubspot-link-card em {
          font-style: normal;
          font-size: 11px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: #ffd28a;
        }

        .ops-inline-error {
          margin: 0;
          color: #dc2626;
          font-size: 13px;
        }

        .ops-module-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
          gap: 14px;
        }

        .ops-module-link {
          text-decoration: none;
          color: inherit;
          border: 1px solid color-mix(in oklab, var(--ops-accent) 28%, #e7e9ef);
          border-radius: 14px;
          background: var(--bg-soft, #eef0f4);
          padding: 18px;
          min-height: 188px;
          display: grid;
          gap: 8px;
          align-content: start;
          transition:
            transform 180ms ease,
            border-color 180ms ease,
            box-shadow 180ms ease,
            background 200ms ease;
          box-shadow: 0 2px 8px rgba(148,163,184,0.10);
        }

        .ops-module-link:hover,
        .ops-module-link:focus-visible {
          transform: translateY(-4px);
          border-color: var(--ops-accent);
          background: linear-gradient(
            135deg,
            color-mix(in oklab, var(--ops-accent) 18%, transparent) 0%,
            rgba(148,163,184,0.10) 75%
          );
          box-shadow:
            0 14px 28px color-mix(in oklab, var(--ops-accent) 24%, transparent),
            0 0 0 1px color-mix(in oklab, var(--ops-accent) 14%, transparent) inset;
        }

        .ops-module-icon {
          font-size: 28px;
          line-height: 1;
          transition: transform 0.18s ease;
        }

        .ops-module-link:hover .ops-module-icon,
        .ops-module-link:focus-visible .ops-module-icon {
          transform: scale(1.08);
        }

        .ops-module-title {
          margin: 0;
          font-size: 14px;
          line-height: 1.35;
          font-weight: 800;
          color: var(--ops-accent);
        }

        .ops-module-summary {
          margin: 0;
          color: var(--muted);
          font-size: 12px;
          line-height: 1.55;
          transition: color 0.18s ease;
        }

        .ops-module-link:hover .ops-module-summary,
        .ops-module-link:focus-visible .ops-module-summary {
          color: var(--muted);
        }

        .ops-module-foot {
          margin-top: auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .ops-module-state {
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: color-mix(in oklab, var(--ops-accent) 72%, #cfdaf0);
        }

        .ops-module-arrow {
          color: var(--ops-accent);
          font-size: 14px;
          font-weight: 900;
          opacity: 0;
          transform: translateX(-6px);
          transition:
            opacity 0.18s ease,
            transform 0.18s ease;
        }

        .ops-module-link:hover .ops-module-arrow,
        .ops-module-link:focus-visible .ops-module-arrow {
          opacity: 1;
          transform: translateX(0);
        }

        .ops-module-btn {
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.02);
          color: var(--text);
          padding: 10px;
          display: grid;
          gap: 5px;
          text-align: left;
          cursor: pointer;
          transition:
            border-color 140ms ease,
            transform 120ms ease,
            box-shadow 160ms ease;
        }

        .ops-module-btn:hover {
          transform: translateY(-1px);
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 44%, var(--line));
          box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }

        .ops-module-btn.active {
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 72%, #ffffff);
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.16);
        }

        .ops-module-btn strong {
          font-size: 13px;
        }

        .ops-module-btn small {
          font-size: 11px;
          color: var(--muted);
        }

        .ops-panel-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .ops-panel {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 12px;
          background: rgba(255, 255, 255, 0.02);
          display: grid;
          gap: 10px;
        }

        .ops-panel h4 {
          margin: 0;
          font-size: 14px;
        }

        .ops-subhead {
          font-size: 12px;
          color: var(--muted);
          margin-top: 4px;
        }

        .ops-list {
          display: grid;
          gap: 8px;
        }

        .ops-list-item {
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 8px;
          display: grid;
          gap: 4px;
          background: rgba(255, 255, 255, 0.015);
        }

        .ops-list-item {
          transition:
            border-color 150ms ease,
            transform 150ms ease,
            box-shadow 160ms ease;
        }

        .ops-list-item:hover {
          transform: translateY(-1px);
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 36%, var(--line));
          box-shadow: 0 6px 18px rgba(0, 0, 0, 0.22);
        }

        .ops-list-item strong {
          font-size: 13px;
        }

        .ops-list-item span {
          color: var(--muted);
          font-size: 12px;
        }

        /* --- Ops panel hover --- */
        .ops-panel {
          transition:
            border-color 180ms ease,
            box-shadow 180ms ease;
        }

        .ops-panel:hover {
          border-color: color-mix(in oklab, var(--module-accent-2, #2bd97f) 24%, var(--line));
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
        }

        /* --- Account item layout --- */
        .ops-account-item {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: nowrap;
        }

        .ops-account-status-dot {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          flex-shrink: 0;
          transition: box-shadow 300ms ease;
        }

        .ops-account-status-dot.pulse {
          animation: status-pulse 2s ease-in-out infinite;
        }

        @keyframes status-pulse {
          0%,
          100% {
            box-shadow: 0 0 0 0 currentColor;
            opacity: 1;
          }
          50% {
            box-shadow: 0 0 0 4px transparent;
            opacity: 0.82;
          }
        }

        .ops-account-info {
          flex: 1;
          min-width: 0;
          display: grid;
          gap: 2px;
        }

        .ops-account-status-label {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.03em;
          white-space: nowrap;
        }

        .command-btn-danger-sm {
          background: rgba(239, 68, 68, 0.12);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #dc2626;
          border-radius: 6px;
          padding: 3px 10px;
          font-size: 11px;
          cursor: pointer;
          transition:
            background 150ms ease,
            border-color 150ms ease;
          white-space: nowrap;
        }

        .command-btn-danger-sm:hover {
          background: rgba(239, 68, 68, 0.22);
          border-color: rgba(239, 68, 68, 0.55);
        }

        /* --- Autopilot structured result --- */
        .autopilot-result {
          display: grid;
          gap: 6px;
          max-height: 320px;
          overflow-y: auto;
          padding-right: 4px;
        }

        .autopilot-row {
          display: flex;
          gap: 8px;
          margin: 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          padding: 5px 0;
          align-items: baseline;
        }

        .autopilot-key {
          flex: 0 0 140px;
          font-size: 11px;
          color: var(--muted);
          text-transform: capitalize;
          letter-spacing: 0.03em;
        }

        .autopilot-val {
          flex: 1;
          font-size: 12px;
          color: #d8e6ff;
          word-break: break-all;
        }

        /* --- KPI bar chart --- */
        .kpi-bar-list {
          display: grid;
          gap: 10px;
        }

        .kpi-bar-row {
          display: grid;
          grid-template-columns: 60px 1fr 140px;
          align-items: center;
          gap: 8px;
        }

        .kpi-bar-label {
          font-size: 12px;
          color: var(--muted);
          white-space: nowrap;
        }

        .kpi-bar-track {
          height: 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.08);
          overflow: hidden;
        }

        .kpi-bar-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(
            90deg,
            var(--module-accent, #4c8dff),
            color-mix(in oklab, var(--module-accent, #4c8dff) 60%, var(--module-accent-2, #2bd97f))
          );
          transition: width 600ms cubic-bezier(0.22, 1, 0.36, 1);
        }

        .kpi-bar-meta {
          font-size: 11px;
          color: var(--muted);
          text-align: right;
          white-space: nowrap;
        }

        /* --- Section header row --- */
        .section-header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          margin-bottom: 8px;
        }

        .section-header-row h3 {
          margin: 0;
        }

        /* --- Activity row --- */
        .activity-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
        }

        .activity-dismiss-btn {
          background: transparent;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 0 2px;
          font-size: 12px;
          line-height: 1;
          flex-shrink: 0;
          transition: color 150ms ease;
        }

        .activity-dismiss-btn:hover {
          color: #ff6b6b;
        }

        /* --- Metric card hover (if used) --- */
        .metric-card {
          transition:
            border-color 150ms ease,
            transform 150ms ease,
            box-shadow 160ms ease;
        }

        .metric-card:hover {
          transform: translateY(-2px);
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 40%, var(--line));
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }

        /* --- Toast notification system --- */
        .toast-container {
          position: fixed;
          bottom: 24px;
          right: 24px;
          z-index: 9999;
          display: grid;
          gap: 8px;
          max-width: 360px;
          pointer-events: none;
        }

        .toast {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid;
          backdrop-filter: blur(12px);
          font-size: 13px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
          pointer-events: all;
          animation: toast-in 220ms cubic-bezier(0.22, 1, 0.36, 1);
        }

        @keyframes toast-in {
          from {
            opacity: 0;
            transform: translateX(24px) scale(0.97);
          }
          to {
            opacity: 1;
            transform: translateX(0) scale(1);
          }
        }

        .toast-success {
          background: rgba(34, 197, 94, 0.14);
          border-color: rgba(34, 197, 94, 0.35);
          color: #15803d;
        }

        .toast-error {
          background: rgba(239, 68, 68, 0.14);
          border-color: rgba(239, 68, 68, 0.35);
          color: #dc2626;
        }

        .toast-info {
          background: rgba(59, 130, 246, 0.14);
          border-color: rgba(59, 130, 246, 0.35);
          color: var(--brand);
        }

        .toast-warning {
          background: rgba(245, 158, 11, 0.14);
          border-color: rgba(245, 158, 11, 0.35);
          color: #b45309;
        }

        .toast-message {
          flex: 1;
          line-height: 1.4;
        }

        .toast-dismiss {
          background: transparent;
          border: none;
          cursor: pointer;
          color: inherit;
          opacity: 0.7;
          font-size: 13px;
          padding: 0;
          line-height: 1;
          transition: opacity 120ms ease;
          flex-shrink: 0;
        }

        .toast-dismiss:hover {
          opacity: 1;
        }

        /* --- Upload chip name + size --- */
        .upload-file-chip-name {
          max-width: 120px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .upload-file-size {
          font-size: 10px;
          color: var(--muted);
          white-space: nowrap;
          opacity: 0.75;
        }

        /* --- Progress shimmer during generation --- */
        @keyframes progress-shimmer {
          0% {
            background-position: -200px 0;
          }
          100% {
            background-position: 200px 0;
          }
        }

        .upload-progress-fill.is-active,
        .kpi-bar-fill.is-active {
          background-image: linear-gradient(
            90deg,
            var(--module-accent, #4c8dff) 0%,
            color-mix(in oklab, var(--module-accent, #4c8dff) 55%, #fff) 40%,
            var(--module-accent, #4c8dff) 80%
          );
          background-size: 200px 100%;
          animation: progress-shimmer 1.6s linear infinite;
        }

        /* --- Density compact overrides --- */
        .density-compact .card {
          padding: 10px 12px;
        }

        .density-compact .ops-panel {
          padding: 10px 12px;
        }

        .density-compact .ops-panel h4 {
          margin-bottom: 6px;
          font-size: 13px;
        }

        .density-compact .widget-list li {
          padding: 6px 8px;
        }

        .density-compact .metric-card {
          padding: 8px 10px;
        }

        .density-compact .kpi-bar-row {
          grid-template-columns: 50px 1fr 120px;
          gap: 6px;
        }

        .density-compact .ops-list-item {
          padding: 6px;
        }

        .density-compact .activity-row {
          padding: 4px 0;
        }

        .density-compact .autopilot-row {
          padding: 3px 0;
        }

        .ops-json {
          margin: 0;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 10px;
          background: rgba(4, 13, 22, 0.8);
          color: #9ae6ff;
          font-size: 12px;
          max-height: 300px;
          overflow: auto;
        }

        .calendar-lane-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 120px), 1fr));
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 2px;
        }

        .calendar-lane {
          border: 1px dashed color-mix(in oklab, var(--module-accent, #4c8dff) 34%, var(--line));
          border-radius: 10px;
          min-height: 124px;
          padding: 8px;
          display: grid;
          gap: 8px;
          align-content: start;
          background: rgba(255, 255, 255, 0.015);
          transition:
            border-color 180ms ease,
            background 200ms ease,
            box-shadow 200ms ease;
        }

        .calendar-lane:hover {
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 52%, var(--line));
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.04);
        }

        .calendar-lane strong {
          font-size: 11px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .calendar-post {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: rgba(27, 199, 255, 0.08);
          padding: 6px;
          display: grid;
          gap: 2px;
          cursor: grab;
          transition:
            border-color 140ms ease,
            transform 140ms ease,
            box-shadow 160ms ease,
            background 140ms ease;
        }

        .calendar-post:hover {
          transform: translateY(-2px) scale(1.01);
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 55%, var(--line));
          background: rgba(27, 199, 255, 0.14);
          box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
        }

        .calendar-post span {
          font-size: 11px;
          font-weight: 700;
        }

        .calendar-post small {
          font-size: 11px;
          color: var(--muted);
        }

        .inline-actions {
          display: flex;
          gap: 8px;
          margin-top: 2px;
        }

        .main-layout {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
          gap: 16px;
          align-items: start;
          contain: layout paint;
        }

        .builder-stack,
        .ops-stack,
        .stack {
          display: grid;
          gap: 16px;
        }

        .ops-stack {
          position: sticky;
          top: 174px;
          align-content: start;
        }

        .builder-stack {
          align-content: start;
        }

        .block {
          padding: 18px;
        }

        .muted {
          color: var(--muted);
          margin: 6px 0 0;
        }

        .category-grid {
          margin-top: 12px;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
          gap: 14px;
        }

        .category-tile {
          text-align: left;
          border: 1px solid color-mix(in oklab, var(--tile-accent) 60%, #27385c);
          border-radius: 22px;
          background: linear-gradient(180deg, #112346 0%, #0f1f3f 100%);
          color: var(--text);
          text-decoration: none;
          padding: 20px 20px 18px;
          cursor: pointer;
          transition:
            transform 140ms ease,
            box-shadow 180ms ease,
            border-color 140ms ease;
          display: grid;
          gap: 10px;
          min-height: 210px;
          align-content: start;
        }

        .module-focus-shell {
          border-color: var(--module-focus-border, color-mix(in oklab, #4c8dff 32%, var(--line)));
          background: var(--module-focus-bg, linear-gradient(180deg, #0f1f3f 0%, #0d1a34 100%));
        }

        .module-back-link {
          display: inline-block;
          margin-bottom: 8px;
          color: #94b5ff;
          text-decoration: none;
          font-size: 13px;
          font-weight: 700;
        }

        .module-back-link:hover {
          color: #c7d8ff;
          text-decoration: underline;
        }

        .category-tile strong {
          margin-top: 2px;
          font-size: 20px;
          line-height: 1.25;
          color: var(--tile-accent);
        }

        .category-summary {
          color: #7486a6;
          font-size: 18px;
          line-height: 1.45;
          font-weight: 500;
        }

        .module-state {
          margin-top: auto;
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: color-mix(in oklab, var(--tile-accent) 74%, #cfdaf0);
        }

        .category-tile:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 30px rgba(3, 8, 20, 0.45);
        }

        .category-tile.active {
          border-color: color-mix(in oklab, var(--tile-accent) 85%, #ffffff);
          box-shadow:
            0 0 0 1px color-mix(in oklab, var(--tile-accent) 45%, transparent),
            0 18px 36px rgba(4, 10, 26, 0.46);
        }

        .category-tile.is-hovered {
          transform: translateY(-4px);
          box-shadow: 0 16px 30px rgba(3, 8, 20, 0.45);
        }

        .category-tile.active .module-state {
          color: color-mix(in oklab, var(--tile-accent) 90%, #ffffff);
        }

        .category-icon {
          display: block;
          font-size: 34px;
          line-height: 1;
        }

        .module-foot {
          margin-top: auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .module-arrow {
          color: var(--tile-accent);
          font-size: 15px;
          font-weight: 800;
          opacity: 0;
          transform: translateX(-6px);
          transition:
            opacity 0.18s ease,
            transform 0.18s ease;
        }

        .category-tile.is-hovered .module-arrow,
        .category-tile.active .module-arrow {
          opacity: 1;
          transform: translateX(0);
        }

        .field {
          display: grid;
          gap: 8px;
        }

        .field label {
          font-size: 12px;
          font-weight: 700;
        }

        .field-title {
          font-size: 12px;
          font-weight: 700;
        }

        .dual-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .dual-grid.compact {
          gap: 8px;
        }

        .chip-wrap {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .toggle-chip {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.02);
          color: var(--text);
          padding: 7px 10px;
          font-size: 12px;
          cursor: pointer;
          transition:
            border-color 120ms ease,
            background 120ms ease;
        }

        .toggle-chip.active-brand {
          border-color: var(--module-accent, #4c8dff);
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.16);
        }

        .toggle-chip.active-success {
          border-color: var(--module-accent-2, #2bd97f);
          background: rgba(var(--module-accent-2-rgb, 43, 217, 127), 0.16);
        }

        .upload-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
          gap: 10px;
        }

        .upload-box {
          border: 1px dashed var(--line);
          border-radius: 12px;
          padding: 14px;
          display: grid;
          gap: 10px;
          background: linear-gradient(155deg, rgba(15, 26, 46, 0.88), rgba(12, 20, 36, 0.84));
          min-height: 178px;
          transition:
            border-color 180ms ease,
            transform 180ms ease,
            box-shadow 180ms ease;
        }

        .upload-box:hover {
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 50%, var(--line));
          transform: translateY(-2px);
          box-shadow: 0 14px 28px rgba(148,163,184,0.10);
        }

        .upload-box.is-dragging {
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 78%, #ffffff);
          box-shadow:
            0 0 0 1px color-mix(in oklab, var(--module-accent, #4c8dff) 36%, transparent),
            0 14px 28px rgba(148,163,184,0.10);
          transform: translateY(-3px);
        }

        .upload-head {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }

        .upload-icon {
          width: 34px;
          height: 34px;
          border-radius: 10px;
          display: grid;
          place-items: center;
          font-size: 18px;
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.14);
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 42%, var(--line));
          flex-shrink: 0;
        }

        .upload-head span {
          font-size: 12px;
          font-weight: 700;
          display: block;
          color: #d8e6ff;
        }

        .upload-head small {
          display: block;
          margin-top: 3px;
          font-size: 11px;
          color: var(--muted);
          line-height: 1.4;
        }

        .upload-input {
          width: 100%;
          border: 1px dashed color-mix(in oklab, var(--module-accent, #4c8dff) 35%, var(--line));
          border-radius: 10px;
          padding: 8px;
          background: rgba(255, 255, 255, 0.02);
          color: var(--muted);
        }

        .upload-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .upload-box em {
          font-style: normal;
          font-size: 12px;
          color: var(--muted);
        }

        .upload-meta strong {
          font-size: 11px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: color-mix(in oklab, var(--module-accent, #4c8dff) 82%, #e8f1ff);
        }

        .upload-file-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .upload-file-list span {
          font-size: 11px;
          color: var(--muted);
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 30%, var(--line));
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.12);
          border-radius: 999px;
          padding: 4px 8px;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .upload-file-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition:
            border-color 120ms ease,
            background 120ms ease,
            transform 120ms ease;
        }

        .upload-file-chip:hover {
          border-color: color-mix(in oklab, var(--module-accent, #4c8dff) 55%, var(--line));
          background: rgba(var(--module-accent-rgb, 76, 141, 255), 0.2);
          transform: translateY(-1px);
        }

        .upload-file-remove {
          border: none;
          background: transparent;
          color: #d8e6ff;
          font-size: 14px;
          line-height: 1;
          cursor: pointer;
          padding: 0;
        }

        .upload-progress-wrap {
          display: grid;
          gap: 6px;
        }

        .upload-progress-track {
          height: 7px;
          border-radius: 999px;
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 25%, var(--line));
          background: rgba(255, 255, 255, 0.03);
          overflow: hidden;
        }

        .upload-progress-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(
            90deg,
            var(--module-accent, #4c8dff),
            color-mix(in oklab, var(--module-accent, #4c8dff) 70%, #9bd7ff)
          );
          transition: width 180ms ease;
        }

        .upload-progress-label {
          font-size: 11px;
          color: color-mix(in oklab, var(--module-accent, #4c8dff) 72%, #dbe8ff);
        }

        .upload-file-progress-list {
          display: grid;
          gap: 6px;
        }

        .upload-file-progress-row {
          display: grid;
          gap: 4px;
        }

        .upload-file-progress-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .upload-file-progress-meta span {
          font-size: 10px;
          color: #d7e6ff;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .upload-file-progress-meta em {
          font-size: 10px;
          color: var(--muted);
          font-style: normal;
          flex-shrink: 0;
        }

        .upload-file-progress-track {
          height: 5px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          overflow: hidden;
        }

        .upload-file-progress-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(
            90deg,
            color-mix(in oklab, var(--module-accent, #4c8dff) 80%, #ffffff),
            var(--module-accent, #4c8dff)
          );
          transition: width 120ms linear;
        }

        .upload-box-image .upload-icon {
          background: rgba(96, 165, 250, 0.18);
        }

        .upload-box-video .upload-icon {
          background: rgba(244, 114, 182, 0.18);
        }

        .upload-box-audio .upload-icon {
          background: rgba(34, 211, 238, 0.18);
        }

        .preview-stage-card {
          display: grid;
          gap: 12px;
          min-height: 420px;
          content-visibility: auto;
          contain-intrinsic-size: 420px;
        }

        .preview-stage-shell {
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 26%, var(--line));
          border-radius: 12px;
          background: linear-gradient(160deg, rgba(7, 20, 34, 0.92), rgba(6, 17, 30, 0.86));
          padding: 14px;
          min-height: 320px;
        }

        .preview-stage-empty {
          display: grid;
          align-items: center;
        }

        .preview-stage-copy {
          display: grid;
          gap: 10px;
          max-width: 620px;
        }

        .preview-stage-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .preview-stage-meta span {
          border: 1px solid var(--line);
          border-radius: 999px;
          padding: 4px 8px;
          font-size: 11px;
          color: var(--muted);
          background: rgba(255, 255, 255, 0.02);
        }

        .output-preview-item {
          min-height: 0;
          margin: 0;
        }

        .output-preview-frame {
          max-height: 420px;
          object-fit: contain;
          background: rgba(148,163,184,0.10);
        }

        .preview-stage-skeleton {
          min-height: 260px;
        }

        .candidate-row {
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 10px;
          display: grid;
          gap: 4px;
        }

        .candidate-row span {
          font-size: 12px;
          color: var(--muted);
        }

        .health-row {
          display: flex;
          justify-content: space-between;
          gap: 10px;
        }

        .health-row .ok {
          color: #15803d;
        }

        .health-row .warn {
          color: #fbbf24;
        }

        .bottom-layout {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
          gap: 16px;
          align-items: start;
        }

        .output-item {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 12px;
          background: rgba(255, 255, 255, 0.02);
        }

        .output-item p {
          margin: 10px 0;
        }

        .media-frame {
          width: 100%;
          border-radius: 10px;
          border: 1px solid var(--line);
        }

        .small-text {
          font-size: 12px;
          color: var(--muted);
        }

        .skeleton-line {
          height: 12px;
          border-radius: 999px;
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.08),
            rgba(255, 255, 255, 0.17),
            rgba(255, 255, 255, 0.08)
          );
          background-size: 200% 100%;
          animation: shimmer 1.2s linear infinite;
        }

        .skeleton-line.short {
          width: 62%;
        }

        .skeleton-list {
          display: grid;
          gap: 8px;
        }

        .skeleton-media {
          height: 180px;
          border-radius: 10px;
          margin-top: 8px;
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.08),
            rgba(255, 255, 255, 0.17),
            rgba(255, 255, 255, 0.08)
          );
          background-size: 200% 100%;
          animation: shimmer 1.2s linear infinite;
        }

        .command-btn {
          border-radius: 12px;
          padding: 10px 12px;
          font-weight: 700;
          transition:
            transform 130ms ease,
            box-shadow 160ms ease;
          cursor: pointer;
        }

        .command-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 10px 22px rgba(0, 0, 0, 0.2);
        }

        .command-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .command-btn-muted {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.02);
          color: var(--text);
        }

        .command-btn-primary {
          border: none;
          background: linear-gradient(
            130deg,
            var(--module-accent, #4c8dff),
            color-mix(in oklab, var(--module-accent, #4c8dff) 72%, #92f4ff)
          );
          color: #001528;
        }

        .command-btn-success {
          border: none;
          background: linear-gradient(
            130deg,
            var(--module-accent-2, #2bd97f),
            color-mix(in oklab, var(--module-accent-2, #2bd97f) 72%, #93f7c4)
          );
          color: #03130c;
        }

        .compact-grid {
          margin-top: 10px;
          grid-template-columns: 1fr;
        }

        .predis-panels-section {
          display: flex;
          flex-direction: column;
          gap: 16px;
          margin: 0 0 24px;
          content-visibility: auto;
          contain-intrinsic-size: 1200px;
        }

        .social-ops-hub,
        .hubspot-hub,
        .command-rail {
          content-visibility: auto;
          contain-intrinsic-size: 780px;
        }

        .palette-backdrop {
          position: fixed;
          inset: 0;
          z-index: 30;
          display: grid;
          place-items: start center;
          padding: 12vh 16px 16px;
          background: rgba(2, 8, 14, 0.62);
          backdrop-filter: blur(6px);
        }

        .palette {
          position: relative;
          width: min(720px, 100%);
          border: 1px solid color-mix(in oklab, var(--module-accent, #4c8dff) 20%, var(--line));
          border-radius: 14px;
          background: linear-gradient(165deg, rgba(8, 21, 34, 0.96), rgba(8, 24, 35, 0.92));
          box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
          overflow: hidden;
        }

        .palette-close {
          position: absolute;
          top: 10px;
          right: 10px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.02);
          color: var(--muted);
          border-radius: 8px;
          font-size: 11px;
          padding: 4px 8px;
          cursor: pointer;
        }

        .palette-input {
          width: 100%;
          border: none;
          border-bottom: 1px solid var(--line);
          background: transparent;
          color: var(--text);
          padding: 14px 16px;
          font-size: 14px;
          outline: none;
        }

        .palette-list {
          display: grid;
          max-height: min(380px, 60vh);
          overflow: auto;
        }

        .palette-item {
          border: none;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          background: transparent;
          color: var(--text);
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          text-align: left;
          cursor: pointer;
        }

        .palette-item:hover:not(:disabled) {
          background: rgba(27, 199, 255, 0.1);
        }

        .palette-item:disabled {
          color: var(--muted);
          opacity: 0.55;
          cursor: not-allowed;
        }

        .palette-item kbd {
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 3px 7px;
          font-size: 11px;
          color: var(--muted);
          background: rgba(255, 255, 255, 0.03);
        }

        .palette-empty {
          padding: 14px 16px;
          color: var(--muted);
          font-size: 13px;
        }

        .density-compact .block {
          padding: 14px;
        }

        .social-studio-page.density-compact {
          gap: 12px;
        }

        .density-compact .hero-shell {
          padding: 18px;
          gap: 12px;
        }

        .density-compact .category-grid {
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
        }

        .density-compact .category-tile {
          min-height: 176px;
          padding: 16px;
        }

        .density-compact .category-tile strong {
          font-size: 18px;
        }

        .density-compact .category-tile > strong + span {
          font-size: 16px;
        }

        .density-compact .category-summary {
          font-size: 16px;
        }

        .density-compact .module-state {
          font-size: 10px;
        }

        @media (min-width: 1680px) {
          .tower-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
        }

        .density-compact .command-btn {
          padding: 8px 10px;
        }

        .density-compact .upload-box {
          padding: 10px;
        }

        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }

        @media (max-width: 1180px) {
          .main-layout {
            grid-template-columns: 1fr;
          }

          .ops-panel-grid {
            grid-template-columns: 1fr;
          }

          .ops-stack {
            position: static;
          }

          .bottom-layout {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 760px) {
          .hero-shell {
            padding: 18px;
          }

          .block {
            padding: 14px;
          }

          .dual-grid {
            grid-template-columns: 1fr;
          }

          .command-head {
            flex-direction: column;
            align-items: flex-start;
          }

          .predis-toggle-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
      `}</style>
    </main>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

function formatAutopilotValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return `${value}`;
  return Object.prototype.toString.call(value);
}

function mergeFiles(existing: File[], incoming: File[]): File[] {
  const fingerprints = new Set(existing.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
  const next = [...existing];
  incoming.forEach((file) => {
    const fingerprint = `${file.name}:${file.size}:${file.lastModified}`;
    if (fingerprints.has(fingerprint)) return;
    fingerprints.add(fingerprint);
    next.push(file);
  });
  return next;
}

function calculateUploadReadiness(files: File[]): number {
  if (files.length === 0) return 0;
  return Math.min(100, 35 + files.length * 16);
}

function totalUploadBytes(zoneUploadTotals: UploadProgressState): number {
  return zoneUploadTotals.image + zoneUploadTotals.video + zoneUploadTotals.audio;
}

function calculateUploadProgressByZone(
  loadedBytes: number,
  zoneUploadTotals: UploadProgressState
): UploadProgressState {
  let remaining = loadedBytes;
  const progress: UploadProgressState = { image: 0, video: 0, audio: 0 };

  UPLOAD_ZONE_ORDER.forEach((zone) => {
    const zoneBytes = zoneUploadTotals[zone];
    if (zoneBytes <= 0) {
      progress[zone] = 0;
      return;
    }
    const consumed = Math.max(0, Math.min(zoneBytes, remaining));
    progress[zone] = Math.round((consumed / zoneBytes) * 100);
    remaining -= consumed;
  });

  return progress;
}

function calculateLoadedBytesByZone(loadedBytes: number, zoneUploadTotals: UploadProgressState): UploadProgressState {
  let remaining = loadedBytes;
  const loadedByZone: UploadProgressState = { image: 0, video: 0, audio: 0 };

  UPLOAD_ZONE_ORDER.forEach((zone) => {
    const zoneBytes = zoneUploadTotals[zone];
    const consumed = Math.max(0, Math.min(zoneBytes, remaining));
    loadedByZone[zone] = consumed;
    remaining -= consumed;
  });

  return loadedByZone;
}

function buildFileUploadRows(files: File[], loadedZoneBytes: number): UploadFileProgress[] {
  let remaining = loadedZoneBytes;
  return files.map((file) => {
    const consumed = Math.max(0, Math.min(file.size, remaining));
    const progressPct = file.size > 0 ? Math.round((consumed / file.size) * 100) : 0;
    remaining -= consumed;
    return {
      id: `${file.name}-${file.lastModified}-${file.size}`,
      name: file.name,
      progressPct,
    };
  });
}
