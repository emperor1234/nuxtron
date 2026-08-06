'use client';
/* eslint-disable react/jsx-child-element-spacing, sonarjs/no-nested-conditional, sonarjs/cognitive-complexity, sonarjs/no-nested-functions, sonarjs/no-redundant-jump, unicorn/no-negated-condition, unicorn/prefer-at, jsx-a11y/prefer-tag-over-role */

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type MouseEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiDelete, apiGet, apiPost, resolveSessionTenant, PROXY_BASE_URL } from '@/app/lib/api-client';
import {
  fetchBrandProfileFromWebsite,
  loadBrandProfile,
  saveBrandProfile,
  type SocialBrandProfile,
} from './brand-profile';
import {
  loadUgcTemplateProfile,
  normalizeUgcTemplateProfile,
  saveUgcTemplateProfile,
  trackUgcTemplateEvent,
} from './ugc-template-profile';

type EditorMode =
  | 'creatives'
  | 'captions'
  | 'hashtags'
  | 'suggestions'
  | 'timeline'
  | 'color'
  | 'effects'
  | 'audio'
  | 'transitions'
  | 'motion'
  | 'media';

type TimelineTrack = {
  id: string;
  label: string;
  type: 'video' | 'audio' | 'text' | 'effect';
  locked: boolean;
  grouped: boolean;
  muted: boolean;
  color: string;
};

type KeyframeType = 'opacity' | 'position' | 'scale';

type Keyframe = {
  id: string;
  trackId: string;
  time: number;
  type: KeyframeType;
  value: number;
};

type SubtitleItem = {
  id: string;
  start: number;
  end: number;
  text: string;
};
type AssetType = 'image_ad' | 'carousel' | 'story_ad';
type Tool = 'design' | 'text' | 'media' | 'voiceover' | 'shapes' | 'layers' | 'uploads' | 'resize';
type Panel = 'edit' | 'animate';
type PublishMode = 'draft' | 'now';
type CreativeView = 'library' | 'editor';
type CreativeLibraryTab = 'all' | 'image' | 'video' | 'carousel';
type EditorSidebarView = 'insert' | 'layers' | 'history';
type InsertPanelView = 'root' | 'text';
type EditorLayerId = 'background' | 'headline' | 'subtitle' | 'brand' | 'cta';

type TemplateItem = {
  id: string;
  title: string;
  category: AssetType;
  subtitle: string;
  colorA: string;
  colorB: string;
  aspectRatio: string;
  channel: string;
  hook: string;
};

type Slide = {
  id: string;
  headline: string;
  subheadline: string;
  cta: string;
  imageUrl?: string;
};

type SlideSnapshot = {
  headline: string;
  subheadline: string;
  cta: string;
  imageUrl?: string;
};

type EditorVersionItem = {
  id: string;
  label: string;
  ts: string;
  selectedSlideIndex: number;
  slide: SlideSnapshot;
};

type PublishTarget = {
  path: string;
  payload: Record<string, unknown>;
};

type PublishHistoryItem = {
  id: string;
  endpoint: string;
  tenantId: string;
  publishedAt: string;
  publishMode: PublishMode;
  response: Record<string, unknown>;
  request: Record<string, unknown>;
};

type ScheduledPost = {
  id: string;
  tenant_id: string;
  platform: string;
  text: string;
  publish_at: string;
  media_urls: string[];
  status: string;
  created_at: string;
};

type ParityContentItem = {
  id: string;
  title?: string;
  caption?: string;
  platforms?: string[];
  status?: string;
  created_at?: string;
  scheduled_for?: string | null;
};

type SocialCatalogProvider = {
  network: string;
  label: string;
  supported_formats: string[];
};

type CreativeLibraryItem = {
  id: string;
  title: string;
  subtitle: string;
  caption: string;
  format: 'image' | 'video' | 'carousel';
  aspectRatio: string;
  brand: string;
  cta: string;
  badge?: string;
};

type EditorLayer = {
  id: EditorLayerId;
  label: string;
  visible: boolean;
};

type DragPayload = { type: 'draft'; slideIndex: number } | { type: 'scheduled'; postId: string };
type CaptionItem = { id: string; text: string };
type CaptionPack = { id: string; title: string; description: string; body: string };
type HashtagItem = { tag: string; count: string };
type HashtagsBy = 'caption' | 'creative' | 'keyword';
type HashtagsSortBy = 'relevancy' | 'reach';
type EditorSuggestionItem = {
  id: string;
  platform: string;
  caption: string;
  hashtags: string[];
  score: number;
};

type TrendPoint = {
  period_index: number;
  value: number;
};

type PostInsights = {
  projectedEngagement: number;
  projectedClicks: number;
  projectedConversions: number;
  projectedRevenue: number;
  roiLift: number;
  confidence: number;
  recommendedSlot: string;
  scheduledPosts: number;
  listeningMentions: number;
  crmContacts: number;
  trendDirection: string;
  trendPoints: TrendPoint[];
};

const HASHTAGS_CAPTION: HashtagItem[] = [
  { tag: '#shoppingdeals', count: '22.6K' },
  { tag: '#onlineshopping', count: '68.5M' },
  { tag: '#clothingstore', count: '1.7M' },
  { tag: '#shoponline', count: '19.5M' },
  { tag: '#blackfridayhairsales', count: '917' },
  { tag: '#clothingbrand', count: '11.0M' },
  { tag: '#christmasshopping', count: '2.5M' },
  { tag: '#shopping', count: '142.9M' },
  { tag: '#clothingdesign', count: '529.9K' },
  { tag: '#clothingbrands', count: '729.5K' },
  { tag: '#shopnow', count: '7.8M' },
  { tag: '#mensfashion', count: '61.5M' },
  { tag: '#bestgifts', count: '290.4K' },
  { tag: '#clothingline', count: '4.9M' },
  { tag: '#falldeals', count: '5.8K' },
  { tag: '#clothingcompany', count: '781.3K' },
  { tag: '#discountapp', count: '3.3K' },
  { tag: '#highfashion', count: '9.5M' },
  { tag: '#wheretoshop', count: '26.1K' },
  { tag: '#discount', count: '10.8M' },
  { tag: '#customerreviews', count: '192.5K' },
  { tag: '#apparelbrand', count: '532.7K' },
  { tag: '#clothingdesigner', count: '359.1K' },
  { tag: '#customerlove', count: '243.7K' },
  { tag: '#shop', count: '59.4M' },
  { tag: '#clothing', count: '40.6M' },
  { tag: '#discountcode', count: '1.2M' },
  { tag: '#fashion', count: '971.9M' },
  { tag: '#discounts', count: '2.5M' },
  { tag: '#shopsmall', count: '42.6M' },
  { tag: '#fashiondesign', count: '11.5M' },
  { tag: '#clothingboutique', count: '1.3M' },
  { tag: '#homeaccessories', count: '2.0M' },
  { tag: '#fashionstyle', count: '72.7M' },
  { tag: '#januarydeals', count: '13.6K' },
  { tag: '#streetfashion', count: '30.8M' },
  { tag: '#customerreview', count: '555.4K' },
  { tag: '#limitedtimeoffer', count: '199.1K' },
  { tag: '#blackbusiness', count: '4.9M' },
  { tag: '#happycustomer', count: '3.5M' },
  { tag: '#customapparel', count: '773.3K' },
  { tag: '#weddingmakeup', count: '11.2M' },
];
const HASHTAGS_CREATIVE: HashtagItem[] = [
  { tag: '#logobrand', count: '672.6K' },
  { tag: '#advertising', count: '12.7M' },
  { tag: '#creativeadvertising', count: '96.1K' },
  { tag: '#brand', count: '35.3M' },
  { tag: '#companylogo', count: '218.6K' },
  { tag: '#brandidentity', count: '3.6M' },
  { tag: '#contentmarketing', count: '4.8M' },
  { tag: '#brandingdesign', count: '2.3M' },
  { tag: '#advertisingagency', count: '1.0M' },
  { tag: '#clothingbrand', count: '11.0M' },
  { tag: '#marketing', count: '55.7M' },
  { tag: '#digitalads', count: '48.6K' },
  { tag: '#apparelbrand', count: '532.7K' },
  { tag: '#branding', count: '29.9M' },
  { tag: '#font', count: '2.9M' },
  { tag: '#advertisement', count: '2.1M' },
  { tag: '#fontpack', count: '39.2K' },
  { tag: '#digitalmarketingagency', count: '1.7M' },
  { tag: '#onlinemarketing', count: '6.4M' },
  { tag: '#digitalmarketing', count: '17.6M' },
  { tag: '#typefacedesign', count: '131.0K' },
  { tag: '#logodesigner', count: '5.8M' },
  { tag: '#logomaker', count: '1.8M' },
  { tag: '#logoinspiration', count: '1.8M' },
  { tag: '#logodesigns', count: '3.3M' },
  { tag: '#brandingagency', count: '712.3K' },
  { tag: '#socialmediamarketing', count: '15.2M' },
  { tag: '#logo', count: '26.1M' },
  { tag: '#ad', count: '15.4M' },
  { tag: '#marketingstrategy', count: '4.2M' },
  { tag: '#graphicdesign', count: '52.9M' },
  { tag: '#webdesign', count: '9.3M' },
  { tag: '#ads', count: '2.4M' },
  { tag: '#logos', count: '5.1M' },
  { tag: '#fonts', count: '919.8K' },
  { tag: '#clothingcompany', count: '781.3K' },
  { tag: '#graphicdesigner', count: '13.0M' },
  { tag: '#creativedesign', count: '1.3M' },
  { tag: '#marketingtips', count: '4.5M' },
];
const HASHTAGS_KEYWORD: HashtagItem[] = [
  { tag: '#pink', count: '153.7M Posts' },
  { tag: '#sale', count: '87.8M Posts' },
  { tag: '#friday', count: '78.5M Posts' },
  { tag: '#mensfashion', count: '61.5M Posts' },
  { tag: '#clothes', count: '51.7M Posts' },
  { tag: '#tshirt', count: '45.4M Posts' },
  { tag: '#clothing', count: '40.6M Posts' },
  { tag: '#forsale', count: '27.1M Posts' },
  { tag: '#ladies', count: '16.3M Posts' },
  { tag: '#hoodie', count: '14.2M Posts' },
  { tag: '#tshirts', count: '11.7M Posts' },
  { tag: '#clothingbrand', count: '11.0M Posts' },
  { tag: '#internationalwomensday', count: '8.8M Posts' },
  { tag: '#artforsale', count: '8.4M Posts' },
  { tag: '#shirts', count: '7.1M Posts' },
  { tag: '#tshirtdesign', count: '5.6M Posts' },
  { tag: '#hoodies', count: '5.5M Posts' },
  { tag: '#clothingline', count: '4.9M Posts' },
  { tag: '#customshirts', count: '1.0M Posts' },
  { tag: '#clothingstore', count: '1.7M Posts' },
  { tag: '#sweatshirts', count: '1.1M Posts' },
  { tag: '#shirtdesign', count: '979.4K Posts' },
  { tag: '#customapparel', count: '773.3K Posts' },
  { tag: '#shirtshop', count: '268.0K Posts' },
  { tag: '#toddlerclothing', count: '193.7K Posts' },
  { tag: '#funnytshirt', count: '155.6K Posts' },
  { tag: '#printedshirt', count: '118.6K Posts' },
  { tag: '#moccsforsale', count: '14.4K Posts' },
  { tag: '#toddlerboots', count: '8.1K Posts' },
];

const SUGGESTION_PLATFORM_OPTIONS = ['instagram', 'tiktok', 'youtube', 'linkedin', 'x', 'threads'] as const;

const BASE_LIBRARY_ITEMS: CreativeLibraryItem[] = [
  {
    id: 'lib-black-friday-hoodie',
    title: 'Black Friday Hoodie Deals',
    subtitle: 'Limited Time Sale Event',
    caption:
      "Black Friday is the perfect opportunity to score amazing deals on your favorite hoodies! Black Friday is a great time to update your wardrobe. Look for quality fabrics and unique designs that reflect your style. Don't forget to check sizing guides and customer reviews to ensure the best fit! Plan ahead by making a list of what you want, so you can snag those limited-time offers before they're gone. Happy shopping!",
    format: 'image',
    aspectRatio: '1:1',
    brand: 'shopify',
    cta: 'Shop Now',
    badge: '1:1',
  },
];

const TEXT_STYLE_PRESETS = [
  'NEW ARRIVAL',
  'NEW COLLECTION',
  'SALE',
  'END OF summer SALE',
  'FLASH SALE',
  'COMING SOON',
  'Stay Tuned',
  'Explore the World',
  'Innovation. Implement. Impact.',
  'Where TECH Meets Insight',
  'Luxury Elegance',
  'Empower',
] as const;

const TEXT_STYLE_VARIANTS = [
  'text-style-hero',
  'text-style-condensed',
  'text-style-script',
  'text-style-stamp',
  'text-style-modern',
  'text-style-serif',
] as const;

const UGC_CAPTION_PACKS: CaptionPack[] = [
  {
    id: 'ugc-main-launch',
    title: 'UGC 2.0 Launch (Full)',
    description: 'Long-form product update for email and landing pages',
    body: 'UGC 2.0 just changed the game.\n\nHi,\n\nUGC videos were not where they needed to be. Lip sync felt off. You had to download every video just to check the output. Quality was not where performance brands need it.\n\nWe heard you and went back to the drawing board.\n\nIntroducing UGC 2.0, rebuilt with state-of-the-art AI models that deliver 10X better output quality.\n\nWhat changed:\n- Lip sync fixed for good: natural, accurate, seamless\n- Real-time preview: see the video instantly, no download checks\n- 10X better video quality: sharper visuals and smoother motion\n- Stronger product focus: your product stays front and center\n- Built for ecommerce: optimized for ads, demos, and social-first creatives\n\nThe result: product videos that look professional, feel authentic, and actually convert.\n\nIf you use UGC to sell products, run ads, or grow your brand, you will notice the difference the moment you hit Generate.',
  },
  {
    id: 'ugc-social-short',
    title: 'Social Short Version',
    description: 'Fast-scrolling version for Instagram, X, and TikTok captions',
    body: 'UGC 2.0 is live.\n\nBetter lip sync. Real-time preview. Sharper output.\n\nNo more download-and-check loops. No more soft quality.\n\nBuilt for ecommerce teams that need product-first videos that convert.\n\nHit Generate and feel the difference.',
  },
  {
    id: 'ugc-ad-punch',
    title: 'Ad Punch Version',
    description: 'High-intent paid-media framing with strong CTA angle',
    body: 'Still shipping UGC with weak lip sync and slow review cycles?\n\nUGC 2.0 fixes both.\n\nReal-time preview, 10X better quality, and product-first framing that keeps attention where it matters.\n\nBuilt for ecommerce ads that need performance, not just pretty visuals.\n\nGenerate your next product video now.',
  },
  {
    id: 'ugc-premium-brand',
    title: 'Premium Brand Tone',
    description: 'Clean, elevated language for premium ecommerce brands',
    body: 'Introducing UGC 2.0.\n\nA complete rebuild powered by state-of-the-art AI video models.\n\nThe experience is faster. The output is cleaner. The product remains the hero in every frame.\n\nFrom natural lip sync to real-time preview and materially stronger visual quality, every layer was upgraded for modern commerce teams.\n\nThe result is simple: social-ready product videos with premium polish and measurable conversion impact.',
  },
  {
    id: 'ugc-founder-note',
    title: 'Founder Note',
    description: 'Human, transparent update style for loyal customers',
    body: 'Quick founder update:\n\nWe were not satisfied with UGC quality, so we rebuilt it.\n\nUGC 2.0 now delivers natural lip sync, live preview, better visual fidelity, and stronger product focus.\n\nIf you trusted us before, thank you. If you paused because quality was not there yet, now is the best time to try again.',
  },
  {
    id: 'ugc-performance-proof',
    title: 'Performance Proof',
    description: 'Data-forward copy for growth teams and agencies',
    body: 'UGC 2.0 is built for outcomes:\n\n- 10X better output quality\n- Real-time preview feedback loops\n- Product-first framing for ad clarity\n- Natural lip sync for credibility\n\nFor ecommerce growth teams, this means faster iteration, cleaner creatives, and higher-conviction product storytelling.',
  },
];

const UGC_SCRIPT_STYLES = [
  'Storytelling',
  'Professional',
  'Promotional',
  'Exploratory',
  'Problem-Solution',
  'Testimonial',
  'Product Demo',
] as const;

const UGC_CANVAS_RATIOS = ['9:16', '1:1', '16:9', '4:5', '3:4'] as const;

const UGC_PLATFORM_CANVAS_MAP: Record<string, string> = {
  Instagram: '9:16',
  LinkedIn: '1:1',
  TikTok: '9:16',
  X: '16:9',
  Facebook: '4:5',
  YouTube: '16:9',
};

const UGC_PLATFORM_LABEL = ['Instagram', 'LinkedIn', 'TikTok', 'X', 'Facebook', 'YouTube'] as const;

const UGC_BG_MEDIA_SOURCES = ['AI Videos', 'AI Images'] as const;
const UGC_SUBTITLE_LANGUAGES = [
  'Auto (detect)',
  'English',
  'Spanish',
  'Portuguese',
  'French',
  'German',
  'Italian',
  'Dutch',
  'Polish',
  'Turkish',
  'Russian',
  'Arabic',
  'Hindi',
  'Bengali',
  'Urdu',
  'Tamil',
  'Telugu',
  'Japanese',
  'Korean',
  'Indonesian',
  'Thai',
  'Vietnamese',
  'Chinese (Simplified)',
  'Chinese (Traditional)',
] as const;

const UGC_PLATFORM_PRESETS = [
  {
    id: 'reels',
    label: 'Reels Pack',
    platform: 'Instagram',
    aspectRatio: '9:16',
    scriptStyle: 'Storytelling',
    packId: 'ugc-social-short',
    mediaSource: 'AI Videos',
  },
  {
    id: 'tiktok',
    label: 'TikTok Pack',
    platform: 'TikTok',
    aspectRatio: '9:16',
    scriptStyle: 'Promotional',
    packId: 'ugc-ad-punch',
    mediaSource: 'AI Videos',
  },
  {
    id: 'shorts',
    label: 'Shorts Pack',
    platform: 'YouTube',
    aspectRatio: '9:16',
    scriptStyle: 'Product Demo',
    packId: 'ugc-performance-proof',
    mediaSource: 'AI Videos',
  },
  {
    id: 'linkedin-feed',
    label: 'LinkedIn Feed',
    platform: 'LinkedIn',
    aspectRatio: '1:1',
    scriptStyle: 'Professional',
    packId: 'ugc-premium-brand',
    mediaSource: 'AI Images',
  },
  {
    id: 'x-feed',
    label: 'X Feed',
    platform: 'X',
    aspectRatio: '16:9',
    scriptStyle: 'Exploratory',
    packId: 'ugc-social-short',
    mediaSource: 'AI Images',
  },
] as const;

type UgcStyleCategory = {
  id: string;
  label: string;
  description: string;
};

type UgcPreviewTemplate = {
  id: string;
  title: string;
  categoryId: string;
  description: string;
  packId: (typeof UGC_CAPTION_PACKS)[number]['id'];
  platform: (typeof UGC_PLATFORM_LABEL)[number];
  aspectRatio: (typeof UGC_CANVAS_RATIOS)[number];
  scriptStyle: (typeof UGC_SCRIPT_STYLES)[number];
  mediaSource: (typeof UGC_BG_MEDIA_SOURCES)[number];
  hookStyle: string;
  objective: string;
};

const UGC_OBJECTIVES = ['Sales', 'Awareness', 'Engagement', 'Lead Gen'] as const;
const UGC_HOOK_STYLES = ['Announcement', 'Question', 'Proof', 'Pattern Break'] as const;

const UGC_STYLE_CATEGORIES: UgcStyleCategory[] = [
  {
    id: 'no-discount-promo',
    label: 'No-discount promotional layout',
    description: 'Conversion-focused value messaging without discount framing.',
  },
  {
    id: 'business-services',
    label: 'Business & services',
    description: 'Trust-first service positioning and authority tone.',
  },
  {
    id: 'features-benefits',
    label: 'Features & benefits',
    description: 'Feature callouts that map directly to customer outcomes.',
  },
  {
    id: 'real-estate',
    label: 'Real estate',
    description: 'Property-centric storytelling and listing highlight sequences.',
  },
  {
    id: 'travel',
    label: 'Travel',
    description: 'Destination-led narrative with experience-focused visuals.',
  },
  {
    id: 'tech-consultancy',
    label: 'Tech / consultancy',
    description: 'Solution-led messaging with proof and thought-leadership cues.',
  },
];

const UGC_PREVIEW_TEMPLATES: UgcPreviewTemplate[] = [
  {
    id: 'tpl-value-story',
    title: 'Value Story Promo',
    categoryId: 'no-discount-promo',
    description: 'Build urgency through product value, not price cuts.',
    packId: 'ugc-main-launch',
    platform: 'Instagram',
    aspectRatio: '9:16',
    scriptStyle: 'Storytelling',
    mediaSource: 'AI Videos',
    hookStyle: 'Announcement',
    objective: 'Sales',
  },
  {
    id: 'tpl-service-authority',
    title: 'Service Authority',
    categoryId: 'business-services',
    description: 'Position your service as the premium trusted option.',
    packId: 'ugc-premium-brand',
    platform: 'LinkedIn',
    aspectRatio: '1:1',
    scriptStyle: 'Professional',
    mediaSource: 'AI Images',
    hookStyle: 'Proof',
    objective: 'Lead Gen',
  },
  {
    id: 'tpl-feature-breakdown',
    title: 'Feature Breakdown',
    categoryId: 'features-benefits',
    description: 'Walk through top features and outcome-driven benefits.',
    packId: 'ugc-performance-proof',
    platform: 'YouTube',
    aspectRatio: '16:9',
    scriptStyle: 'Product Demo',
    mediaSource: 'AI Videos',
    hookStyle: 'Pattern Break',
    objective: 'Awareness',
  },
  {
    id: 'tpl-listing-tour',
    title: 'Listing Tour Teaser',
    categoryId: 'real-estate',
    description: 'Showcase property highlights and next-step CTA.',
    packId: 'ugc-ad-punch',
    platform: 'Facebook',
    aspectRatio: '4:5',
    scriptStyle: 'Problem-Solution',
    mediaSource: 'AI Videos',
    hookStyle: 'Question',
    objective: 'Lead Gen',
  },
  {
    id: 'tpl-destination-hook',
    title: 'Destination Hook',
    categoryId: 'travel',
    description: 'Inspire action with location-first visual hooks.',
    packId: 'ugc-social-short',
    platform: 'TikTok',
    aspectRatio: '9:16',
    scriptStyle: 'Exploratory',
    mediaSource: 'AI Videos',
    hookStyle: 'Announcement',
    objective: 'Engagement',
  },
  {
    id: 'tpl-consulting-proof',
    title: 'Consulting Proof Stack',
    categoryId: 'tech-consultancy',
    description: 'Use proof points and clear business outcomes.',
    packId: 'ugc-performance-proof',
    platform: 'X',
    aspectRatio: '16:9',
    scriptStyle: 'Professional',
    mediaSource: 'AI Images',
    hookStyle: 'Proof',
    objective: 'Awareness',
  },
];

const UGC_TEMPLATE_NORMALIZE_OPTIONS = {
  categoryIds: UGC_STYLE_CATEGORIES.map((item) => item.id),
  templateIdsByCategory: UGC_STYLE_CATEGORIES.reduce<Record<string, string[]>>((acc, category) => {
    acc[category.id] = UGC_PREVIEW_TEMPLATES.filter((template) => template.categoryId === category.id).map(
      (template) => template.id
    );
    return acc;
  }, {}),
  templateDefaultsById: UGC_PREVIEW_TEMPLATES.reduce<
    Record<
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
    >
  >((acc, template) => {
    acc[template.id] = {
      categoryId: template.categoryId,
      captionPackId: template.packId,
      platform: template.platform,
      objective: template.objective,
      hookStyle: template.hookStyle,
      scriptStyle: template.scriptStyle,
      aspectRatio: template.aspectRatio,
      backgroundMedia: template.mediaSource,
      subtitlesAuto: true,
      subtitlesLanguage: 'Auto (detect)',
    };
    return acc;
  }, {}),
  allowedCaptionPackIds: UGC_CAPTION_PACKS.map((item) => item.id),
  allowedPlatforms: [...UGC_PLATFORM_LABEL],
  allowedObjectives: [...UGC_OBJECTIVES],
  allowedHookStyles: [...UGC_HOOK_STYLES],
  allowedScriptStyles: [...UGC_SCRIPT_STYLES],
  allowedAspectRatios: [...UGC_CANVAS_RATIOS],
  allowedBackgroundMedia: [...UGC_BG_MEDIA_SOURCES],
  allowedSubtitleLanguages: [...UGC_SUBTITLE_LANGUAGES],
} as const;

const PUBLISH_HISTORY_STORAGE_KEY = 'nuxtron.studioEditor.publishHistory';

const TEMPLATES: TemplateItem[] = [
  {
    id: 'tpl-webinar',
    title: 'Live Webinar Promo',
    category: 'image_ad',
    subtitle: 'Conversion-focused social ad',
    colorA: '#0ea5e9',
    colorB: '#6366f1',
    aspectRatio: '1:1',
    channel: 'LinkedIn',
    hook: 'High-intent lead gen',
  },
  {
    id: 'tpl-zero-stress',
    title: 'Zero Stress Exchange',
    category: 'image_ad',
    subtitle: 'Crypto + gifting campaign',
    colorA: '#6366f1',
    colorB: '#6366f1',
    aspectRatio: '1:1',
    channel: 'Instagram',
    hook: 'Fast conversion angle',
  },
  {
    id: 'tpl-sale-stack',
    title: 'End Of Season Sale',
    category: 'story_ad',
    subtitle: 'Story ad with urgency',
    colorA: '#0f766e',
    colorB: '#06b6d4',
    aspectRatio: '9:16',
    channel: 'Stories',
    hook: 'Urgency-driven offer',
  },
  {
    id: 'tpl-product-grid',
    title: 'Carousel Product Grid',
    category: 'carousel',
    subtitle: 'Multi-slide ecommerce set',
    colorA: '#ef4444',
    colorB: '#f59e0b',
    aspectRatio: '4:5',
    channel: 'Instagram',
    hook: 'Swipeable product reveal',
  },
  {
    id: 'tpl-agency-case',
    title: 'Agency Case Study',
    category: 'carousel',
    subtitle: 'B2B proof sequence',
    colorA: '#6366f1',
    colorB: '#6366f1',
    aspectRatio: '4:5',
    channel: 'LinkedIn',
    hook: 'Proof and credibility',
  },
  {
    id: 'tpl-fashion-drop',
    title: 'New Collection Drop',
    category: 'story_ad',
    subtitle: 'Visual-first conversion story',
    colorA: '#ec4899',
    colorB: '#db2777',
    aspectRatio: '9:16',
    channel: 'Instagram',
    hook: 'Visual product launch',
  },
];

function nextSlideId(currentCount: number) {
  return `slide-${currentCount + 1}`;
}

function toolLabel(tool: Tool) {
  return tool.replaceAll('_', ' ').replaceAll(/\b\w/g, (letter) => letter.toUpperCase());
}

function assetTypeLabel(assetType: AssetType) {
  return assetType.replaceAll('_', ' ').replaceAll(/\b\w/g, (letter) => letter.toUpperCase());
}

function startOfWeek(baseDate: Date) {
  const date = new Date(baseDate);
  date.setHours(0, 0, 0, 0);
  const day = date.getDay();
  date.setDate(date.getDate() - day);
  return date;
}

function addDays(baseDate: Date, days: number) {
  const date = new Date(baseDate);
  date.setDate(date.getDate() + days);
  return date;
}

function withHour(baseDate: Date, hour: number) {
  const date = new Date(baseDate);
  date.setHours(hour, 0, 0, 0);
  return date;
}

function toLocalDateKey(value: Date | string) {
  const date = new Date(value);
  const yyyy = String(date.getFullYear());
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function clampToFuture(date: Date) {
  const minLeadMs = 2 * 60 * 1000;
  const now = Date.now();
  const candidate = date.getTime();
  if (candidate > now + minLeadMs) {
    return date;
  }
  return new Date(now + 15 * 60 * 1000);
}

function buildCellPublishTime(day: Date, hour: number) {
  return clampToFuture(withHour(day, hour));
}

function parseDragPayload(value: string): DragPayload | null {
  try {
    const parsed = JSON.parse(value) as DragPayload;
    if (!parsed || typeof parsed !== 'object' || typeof parsed.type !== 'string') {
      return null;
    }
    if (parsed.type === 'draft' && typeof parsed.slideIndex === 'number') {
      return parsed;
    }
    if (parsed.type === 'scheduled' && typeof parsed.postId === 'string' && parsed.postId.trim()) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

function coerceNumber(value: unknown, fallback = 0) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function coerceText(value: unknown, fallback: string) {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed || fallback;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function formatCompactNumber(value: number) {
  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: value < 10 ? 1 : 0,
  }).format(value);
}

function formatCalendarDate(date: Date, options: Intl.DateTimeFormatOptions) {
  // NOSONAR
  return new Intl.DateTimeFormat('en-US', options).format(date);
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function mapParityContentItemToScheduledPost(item: ParityContentItem, tenantId: string): ScheduledPost | null {
  const scheduledFor = typeof item.scheduled_for === 'string' ? item.scheduled_for : '';
  if (!item.id || !scheduledFor) {
    return null;
  }

  const platforms = Array.isArray(item.platforms) ? item.platforms : [];
  const firstPlatform = platforms[0] ?? 'instagram';
  const title = typeof item.title === 'string' ? item.title : '';
  const caption = typeof item.caption === 'string' ? item.caption : '';

  return {
    id: item.id,
    tenant_id: tenantId,
    platform: firstPlatform,
    text: caption || title || 'Untitled scheduled post',
    publish_at: scheduledFor,
    media_urls: [],
    status: typeof item.status === 'string' ? item.status : 'scheduled',
    created_at: typeof item.created_at === 'string' ? item.created_at : new Date().toISOString(),
  };
}

export default function StudioEditorPage() {
  // NOSONAR
  const searchParams = useSearchParams();
  const initialCreativeView: CreativeView = searchParams.get('view') === 'editor' ? 'editor' : 'library';
  const initialCreativeTemplate = searchParams.get('template');
  const [activeMode, setActiveMode] = useState<EditorMode>('creatives');
  const [activeAssetType, setActiveAssetType] = useState<AssetType>('image_ad');
  const [activeTool] = useState<Tool>('design');
  const activePanel: Panel = 'edit';
  const keepEdits = true;
  const [selectedTemplateId, setSelectedTemplateId] = useState('tpl-zero-stress');
  const [selectedSlideIndex, setSelectedSlideIndex] = useState(0);
  const tone: string = 'casual';
  const fontName = 'Sora';
  const fontColor = '#12b76a';
  const [tenantId] = useState(resolveSessionTenant);
  const ugcTemplateHydratedRef = useRef(false);
  const ugcTemplateSavingRef = useRef(false);
  const [ugcTemplateSyncError, setUgcTemplateSyncError] = useState('');
  const [publishAt, setPublishAt] = useState('');
  const [publishMode, setPublishMode] = useState<PublishMode>('draft');
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishError, setPublishError] = useState('');
  const [generationPrompt, setGenerationPrompt] = useState(
    'Generate text, image prompt, video script, voiceover, reel script, and short-video script optimized for conversion.'
  );
  const [generationContext, setGenerationContext] = useState('');
  const [brandProfile, setBrandProfile] = useState<SocialBrandProfile | null>(null);
  const [brandWebsiteDraft, setBrandWebsiteDraft] = useState('');
  const [brandProfileError, setBrandProfileError] = useState('');
  const [brandProfileStatus, setBrandProfileStatus] = useState('');
  const [isBrandProfileLoading, setIsBrandProfileLoading] = useState(false);
  const [isBrandProfileSaving, setIsBrandProfileSaving] = useState(false);
  const [isBrandWebsiteSyncing, setIsBrandWebsiteSyncing] = useState(false);
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null);
  const [publishHistory, setPublishHistory] = useState<PublishHistoryItem[]>([]);
  const [published, setPublished] = useState(false);
  const [socialCatalogProviders, setSocialCatalogProviders] = useState<SocialCatalogProvider[]>([]);
  const [isSocialCatalogLoading, setIsSocialCatalogLoading] = useState(false);
  const [socialCatalogError, setSocialCatalogError] = useState('');
  const [calendarWeekStart, setCalendarWeekStart] = useState(() => startOfWeek(new Date()));
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [isScheduleLoading, setIsScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState('');
  const [activeDropCell, setActiveDropCell] = useState('');
  const [isInsightsLoading, setIsInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState('');
  const [postInsights, setPostInsights] = useState<PostInsights | null>(null);
  const [creativeView, setCreativeView] = useState<CreativeView>(initialCreativeView);
  const [libraryTab, setLibraryTab] = useState<CreativeLibraryTab>('all');
  const [librarySearch, setLibrarySearch] = useState('');
  const [selectedLibraryId, setSelectedLibraryId] = useState('');
  const [editorSidebarView, setEditorSidebarView] = useState<EditorSidebarView>('insert');
  const [insertPanelView, setInsertPanelView] = useState<InsertPanelView>('root');
  const [insertSearch, setInsertSearch] = useState('');
  const [selectedEditorLayer, setSelectedEditorLayer] = useState<EditorLayerId>('headline');
  const [editorLayers, setEditorLayers] = useState<EditorLayer[]>([
    { id: 'background', label: 'Background image', visible: true },
    { id: 'headline', label: 'Headline text', visible: true },
    { id: 'subtitle', label: 'Subtitle text', visible: true },
    { id: 'brand', label: 'Brand logo', visible: true },
    { id: 'cta', label: 'CTA button', visible: true },
  ]);
  const [editorHistory, setEditorHistory] = useState<string[]>(['Created canvas']);
  const [editorBrandLabel, setEditorBrandLabel] = useState('shopify');
  const [editorBadge, setEditorBadge] = useState('1:1');

  // 3D + lighting + shadow state
  const [fx3dRotateX, setFx3dRotateX] = useState(0);
  const [fx3dRotateY, setFx3dRotateY] = useState(0);
  const [fx3dRotateZ, setFx3dRotateZ] = useState(0);
  const [fx3dScale, setFx3dScale] = useState(100);
  const [fxPerspective, setFxPerspective] = useState(800);
  const [fxLightAngle, setFxLightAngle] = useState(135);
  const [fxLightIntensity, setFxLightIntensity] = useState(0);
  const [fxShadowEnabled, setFxShadowEnabled] = useState(false);
  const [fxShadowX, setFxShadowX] = useState(8);
  const [fxShadowY, setFxShadowY] = useState(16);
  const [fxShadowBlur, setFxShadowBlur] = useState(40);
  const [fxShadowSpread, setFxShadowSpread] = useState(0);
  const [fxShadowColor, setFxShadowColor] = useState('#000000');
  const [fxShadowOpacity, setFxShadowOpacity] = useState(50);
  const [fxGlow, setFxGlow] = useState(0);
  const [fxGlowColor, setFxGlowColor] = useState('#6366f1');
  const [fxBlur, setFxBlur] = useState(0);
  const [fxBrightness, setFxBrightness] = useState(100);
  const [fxContrast, setFxContrast] = useState(100);
  const [fxSaturation, setFxSaturation] = useState(100);
  const [fxOpacity, setFxOpacity] = useState(100);
  const [fxBgOverlay, setFxBgOverlay] = useState(false);
  const [fxBgOverlayColor, setFxBgOverlayColor] = useState('#000000');
  const [fxBgOverlayOpacity, setFxBgOverlayOpacity] = useState(30);

  // ── Timeline ──────────────────────────────────────────────────────────────
  const [timelineTracks, setTimelineTracks] = useState<TimelineTrack[]>([
    { id: 'trk-video', label: 'Video', type: 'video', locked: false, grouped: false, muted: false, color: '#6366f1' },
    { id: 'trk-audio', label: 'Audio', type: 'audio', locked: false, grouped: false, muted: false, color: '#10b981' },
    { id: 'trk-text', label: 'Text', type: 'text', locked: false, grouped: false, muted: false, color: '#f59e0b' },
    { id: 'trk-fx', label: 'Effects', type: 'effect', locked: false, grouped: false, muted: false, color: '#8b5cf6' },
  ]);
  const [keyframes, setKeyframes] = useState<Keyframe[]>([
    { id: 'kf-1', trackId: 'trk-video', time: 0, type: 'opacity', value: 0 },
    { id: 'kf-2', trackId: 'trk-video', time: 30, type: 'opacity', value: 100 },
    { id: 'kf-3', trackId: 'trk-video', time: 0, type: 'scale', value: 80 },
    { id: 'kf-4', trackId: 'trk-video', time: 30, type: 'scale', value: 100 },
  ]);
  const [timelinePlayhead, setTimelinePlayhead] = useState(0);
  const [timelineSnap, setTimelineSnap] = useState(true);
  const [timelineDuration, setTimelineDuration] = useState(300);
  const [selectedTrackId, setSelectedTrackId] = useState('trk-video');
  const [selectedKfType, setSelectedKfType] = useState<KeyframeType>('opacity');

  // ── Color & Grading ───────────────────────────────────────────────────────
  const [gradeExposure, setGradeExposure] = useState(0);
  const [gradeHighlights, setGradeHighlights] = useState(0);
  const [gradeShadows, setGradeShadows] = useState(0);
  const [gradeTemperature, setGradeTemperature] = useState(0);
  const [gradeTint, setGradeTint] = useState(0);
  const [gradeLutId, setGradeLutId] = useState('none');
  const [gradeLutStrength, setGradeLutStrength] = useState(100);
  const [gradeCurveR, setGradeCurveR] = useState(50);
  const [gradeCurveG, setGradeCurveG] = useState(50);
  const [gradeCurveB, setGradeCurveB] = useState(50);
  const [gradeLift, setGradeLift] = useState(0);
  const [gradeGamma, setGradeGamma] = useState(0);
  const [gradeGain, setGradeGain] = useState(0);

  // ── Effects & Filters ─────────────────────────────────────────────────────
  const [fxSharpen, setFxSharpen] = useState(0);
  const [fxVignette, setFxVignette] = useState(0);
  const [fxChromaKey, setFxChromaKey] = useState(false);
  const [fxChromaColor, setFxChromaColor] = useState('#00ff00');
  const [fxChromaThreshold, setFxChromaThreshold] = useState(40);
  const [fxMotionBlur, setFxMotionBlur] = useState(0);
  const [fxNoiseReduction, setFxNoiseReduction] = useState(0);

  // ── Audio ─────────────────────────────────────────────────────────────────
  const [audioNoiseReduction, setAudioNoiseReduction] = useState(0);
  const [audioCompressor, setAudioCompressor] = useState(false);
  const [audioCompThreshold, setAudioCompThreshold] = useState(-24);
  const [audioCompRatio, setAudioCompRatio] = useState(4);
  const [audioLimiter, setAudioLimiter] = useState(false);
  const [audioLimiterCeiling, setAudioLimiterCeiling] = useState(-1);
  const [audioAutoLoudness, setAudioAutoLoudness] = useState(false);
  const [audioSyncOffset, setAudioSyncOffset] = useState(0);
  const [audioMasterVolume, setAudioMasterVolume] = useState(100);

  // ── Transitions ───────────────────────────────────────────────────────────
  const [transitionType, setTransitionType] = useState('none');
  const [transitionDuration, setTransitionDuration] = useState(500);
  const [transitionEasing, setTransitionEasing] = useState('ease-in-out');

  // ── Text & Motion Graphics ────────────────────────────────────────────────
  const [titlePreset, setTitlePreset] = useState('none');
  const [titleText, setTitleText] = useState('Your Title Here');
  const [titleAnimIn, setTitleAnimIn] = useState('fade');
  const [titleAnimOut, setTitleAnimOut] = useState('fade');
  const [titleDuration, setTitleDuration] = useState(3000);
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([
    { id: 'sub-1', start: 0, end: 3, text: 'Welcome to UGC 2.0' },
    { id: 'sub-2', start: 3, end: 7, text: '10X better video quality' },
    { id: 'sub-3', start: 7, end: 11, text: 'Real-time preview — no download loops' },
  ]);
  const [subtitleFormat, setSubtitleFormat] = useState<'srt' | 'vtt'>('srt');

  // ── Media Management ──────────────────────────────────────────────────────
  const [autosaveEnabled, setAutosaveEnabled] = useState(true);
  const versionHistory: EditorVersionItem[] = [
    {
      id: 'v3',
      label: 'Version 3 — current',
      ts: 'Today 14:22',
      selectedSlideIndex: 0,
      slide: {
        headline: 'ZERO STRESS',
        subheadline: 'Trade your cryptocurrency and giftcards with us today!',
        cta: 'Start now',
      },
    },
    {
      id: 'v2',
      label: 'Version 2',
      ts: 'Today 12:04',
      selectedSlideIndex: 1,
      slide: {
        headline: 'SMARTER',
        subheadline: 'Launch premium social creatives in a single workflow.',
        cta: 'See demo',
      },
    },
    {
      id: 'v1',
      label: 'Version 1',
      ts: 'Yesterday 18:31',
      selectedSlideIndex: 2,
      slide: { headline: 'FAST', subheadline: 'Build conversion-first assets with fewer steps.', cta: 'Get started' },
    },
  ];
  const [saveStatus, setSaveStatus] = useState('Unsaved changes');

  useEffect(() => {
    if (initialCreativeView === 'editor' && initialCreativeTemplate === 'blank') {
      openBlankCreativeEditor();
    }
  }, [initialCreativeTemplate, initialCreativeView]);
  const [activeVersionId, setActiveVersionId] = useState('v3');

  // Captions state
  const [captionTone, setCaptionTone] = useState('Witty');
  const [captionLength, setCaptionLength] = useState('Small');
  const [captionPackId, setCaptionPackId] = useState('ugc-main-launch');
  const [captionPlatform, setCaptionPlatform] = useState('Instagram');
  const [captionObjective, setCaptionObjective] = useState('Sales');
  const [captionHookStyle, setCaptionHookStyle] = useState('Announcement');
  const [captionCtaStrength, setCaptionCtaStrength] = useState('Balanced');
  const [captionEmojiDensity, setCaptionEmojiDensity] = useState('Low');
  const [captionVariantCount, setCaptionVariantCount] = useState('3');
  const [captionAutoHashtags, setCaptionAutoHashtags] = useState(true);
  const [ugcStyleCategoryId, setUgcStyleCategoryId] = useState(UGC_STYLE_CATEGORIES[0].id);
  const [ugcPreviewTemplateId, setUgcPreviewTemplateId] = useState(UGC_PREVIEW_TEMPLATES[0].id);
  const [videoScriptStyle, setVideoScriptStyle] = useState<(typeof UGC_SCRIPT_STYLES)[number]>('Storytelling');
  const [videoCanvasAspectRatio, setVideoCanvasAspectRatio] = useState<(typeof UGC_CANVAS_RATIOS)[number] | ''>('9:16');
  const [videoAutoAdjustPlatforms, setVideoAutoAdjustPlatforms] = useState(true);
  const [videoBackgroundMedia, setVideoBackgroundMedia] = useState<(typeof UGC_BG_MEDIA_SOURCES)[number]>('AI Videos');
  const [videoSubtitlesAuto, setVideoSubtitlesAuto] = useState(true);
  const [videoSubtitlesLanguage, setVideoSubtitlesLanguage] =
    useState<(typeof UGC_SUBTITLE_LANGUAGES)[number]>('Auto (detect)');
  const [selectedCaptionId, setSelectedCaptionId] = useState('caption-1');
  const [isGeneratingCaptions, setIsGeneratingCaptions] = useState(false);
  const [captions, setCaptions] = useState<CaptionItem[]>([
    {
      id: 'caption-1',
      text: "Black Friday is the perfect opportunity to score amazing deals on your favorite hoodies! \u2665\n\nMany brands offer significant discounts, making it an ideal time to update your wardrobe. Look for quality fabrics and unique designs that reflect your style.\n\nDon't forget to check sizing guides and customer reviews to ensure the best fit!\n\nPlan ahead by making a list of what you want, so you can snag those limited-time offers before they're gone. Happy shopping!",
    },
    {
      id: 'caption-2',
      text: "Discover amazing deals on cozy hoodies this Black Friday! \u2665 \uD83D\uDECD\uFE0F Don't miss out!",
    },
  ]);

  // Hashtags state
  const [hashtagsBy, setHashtagsBy] = useState<HashtagsBy>('caption');
  const [hashtagsSortBy, setHashtagsSortBy] = useState<HashtagsSortBy>('relevancy');
  const [addedHashtags, setAddedHashtags] = useState<string[]>([]);
  const [hashtagKeyword, setHashtagKeyword] = useState('');
  const [hashtagEditText, setHashtagEditText] = useState('');
  const [isGeneratingHashtags, setIsGeneratingHashtags] = useState(false);
  const [generatedKeywordHashtags, setGeneratedKeywordHashtags] = useState<HashtagItem[]>([]);
  const [suggestionTopic, setSuggestionTopic] = useState('');
  const [suggestionGoal, setSuggestionGoal] = useState('engagement');
  const [suggestionStyle, setSuggestionStyle] = useState('professional');
  const [suggestionAudience, setSuggestionAudience] = useState('social audience');
  const [suggestionPlatforms, setSuggestionPlatforms] = useState<string[]>(['instagram', 'tiktok', 'youtube']);
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState('');
  const [suggestionsActionMessage, setSuggestionsActionMessage] = useState('');
  const [suggestions, setSuggestions] = useState<EditorSuggestionItem[]>([]);
  const [timerSeconds, setTimerSeconds] = useState(611);

  useEffect(() => {
    if (!globalThis.window) return;

    try {
      const raw = globalThis.localStorage.getItem(PUBLISH_HISTORY_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as PublishHistoryItem[];
      if (!Array.isArray(parsed)) return;
      setPublishHistory(parsed.slice(0, 10));
    } catch {
      // Ignore malformed storage values and keep an empty history.
    }
  }, []);

  useEffect(() => {
    if (!globalThis.window) return;
    globalThis.localStorage.setItem(PUBLISH_HISTORY_STORAGE_KEY, JSON.stringify(publishHistory));
  }, [publishHistory]);

  const [slides, setSlides] = useState<Slide[]>([
    {
      id: 'slide-1',
      headline: 'ZERO STRESS',
      subheadline: 'Trade your cryptocurrency and giftcards with us today!',
      cta: 'Start now',
      imageUrl: '',
    },
    {
      id: 'slide-2',
      headline: 'FAST PAYOUTS',
      subheadline: 'Instant valuation, secure transfer, and same-day settlement.',
      cta: 'Get quote',
      imageUrl: '',
    },
  ]);

  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, index) => addDays(calendarWeekStart, index));
  }, [calendarWeekStart]);

  const weekDayKeys = useMemo(() => weekDays.map((date) => toLocalDateKey(date)), [weekDays]);

  const timeSlots = useMemo(() => Array.from({ length: 16 }, (_, index) => index + 7), []);

  const selectedSlide = slides[selectedSlideIndex] ?? slides[0];

  const restoreEditorSnapshot = useCallback(
    (version: EditorVersionItem) => {
      setSlides((current) => {
        const next = [...current];
        if (version.selectedSlideIndex >= 0 && version.selectedSlideIndex < next.length) {
          next[version.selectedSlideIndex] = {
            ...next[version.selectedSlideIndex],
            headline: version.slide.headline,
            subheadline: version.slide.subheadline,
            cta: version.slide.cta,
            imageUrl: version.slide.imageUrl,
          };
        }
        return next;
      });
      setSelectedSlideIndex(Math.max(0, Math.min(version.selectedSlideIndex, slides.length - 1)));
      setActiveVersionId(version.id);
      setSaveStatus(`Restored ${version.label}`);
    },
    [slides.length]
  );

  useEffect(() => {
    const interval = setInterval(() => {
      setTimerSeconds((s) => (s > 0 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!videoAutoAdjustPlatforms) return;
    const mappedRatio = UGC_PLATFORM_CANVAS_MAP[captionPlatform] as (typeof UGC_CANVAS_RATIOS)[number] | undefined;
    if (!mappedRatio) return;
    setVideoCanvasAspectRatio(mappedRatio);
  }, [captionPlatform, videoAutoAdjustPlatforms]);

  useEffect(() => {
    let active = true;
    ugcTemplateHydratedRef.current = false;

    async function loadPersistedUgcTemplateProfile() {
      try {
        const persisted = await loadUgcTemplateProfile(tenantId);
        if (!active) return;
        const profile = normalizeUgcTemplateProfile(persisted, UGC_TEMPLATE_NORMALIZE_OPTIONS);
        setUgcStyleCategoryId(profile.style_category_id);
        setUgcPreviewTemplateId(profile.preview_template_id);
        setCaptionPackId(profile.caption_pack_id);
        setCaptionPlatform(profile.platform);
        setCaptionObjective(profile.objective);
        setCaptionHookStyle(profile.hook_style);
        setVideoScriptStyle(profile.script_style as (typeof UGC_SCRIPT_STYLES)[number]);
        setVideoCanvasAspectRatio(profile.aspect_ratio as (typeof UGC_CANVAS_RATIOS)[number]);
        setVideoAutoAdjustPlatforms(profile.auto_adjust_platforms);
        setVideoBackgroundMedia(profile.background_media as (typeof UGC_BG_MEDIA_SOURCES)[number]);
        setVideoSubtitlesAuto(profile.subtitles_auto);
        setVideoSubtitlesLanguage(profile.subtitles_language as (typeof UGC_SUBTITLE_LANGUAGES)[number]);
        setUgcTemplateSyncError('');
      } catch (error) {
        if (!active) return;
        trackUgcTemplateEvent('ugc_template_load_failed', tenantId, {
          message: error instanceof Error ? error.message : 'unknown-load-error',
        });
        setUgcTemplateSyncError(error instanceof Error ? error.message : 'Failed to load UGC template preferences.');
      } finally {
        if (active) {
          ugcTemplateHydratedRef.current = true;
        }
      }
    }

    void loadPersistedUgcTemplateProfile();
    return () => {
      active = false;
    };
  }, [tenantId]);

  function formatTimer(seconds: number) {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function getCaptionHookLine() {
    if (captionHookStyle === 'Question') return 'Still fixing lip sync in post before you can publish?';
    if (captionHookStyle === 'Proof')
      return '10X better output quality with instant preview and stronger product framing.';
    if (captionHookStyle === 'Pattern Break')
      return 'Most UGC tools optimize for speed. UGC 2.0 optimizes for quality and conversion.';
    return 'UGC 2.0 just changed the game.';
  }

  function getVideoScriptLine() {
    if (videoScriptStyle === 'Professional') return 'Script style: professional and conversion-focused messaging.';
    if (videoScriptStyle === 'Promotional') return 'Script style: promotional copy with strong offer and urgency.';
    if (videoScriptStyle === 'Exploratory')
      return 'Script style: exploratory narrative to test fresh hooks and angles.';
    if (videoScriptStyle === 'Problem-Solution') return 'Script style: start with pain, then show UGC 2.0 as the fix.';
    if (videoScriptStyle === 'Testimonial') return 'Script style: customer voice with social-proof framing.';
    if (videoScriptStyle === 'Product Demo') return 'Script style: product-demo structure with clear feature callouts.';
    return 'Script style: storytelling flow with a clear beginning, middle, and conversion CTA.';
  }

  function applyUgcPlatformPreset(presetId: (typeof UGC_PLATFORM_PRESETS)[number]['id']) {
    const preset = UGC_PLATFORM_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    setCaptionPlatform(preset.platform);
    setVideoCanvasAspectRatio(preset.aspectRatio);
    setVideoScriptStyle(preset.scriptStyle);
    setCaptionPackId(preset.packId);
    setVideoBackgroundMedia(preset.mediaSource);
    setVideoAutoAdjustPlatforms(false);
  }

  function getCaptionHashtags() {
    if (captionPlatform === 'LinkedIn') return '#ecommerce #paidmedia #digitalmarketing #creativestrategy';
    if (captionPlatform === 'TikTok') return '#ugccreator #ecomtips #tiktokads #productvideo';
    if (captionPlatform === 'X') return '#UGC #Ecommerce #PerformanceMarketing #AIvideo';
    return '#ecommerce #ugcvideo #productads #socialcommerce #digitalmarketing';
  }

  function getCtaLine() {
    if (captionCtaStrength === 'Soft') return 'Try UGC 2.0 when you are ready and compare the output side by side.';
    if (captionCtaStrength === 'Hard') return 'Generate your next product video now and ship better creatives today.';
    return 'Open UGC 2.0, hit Generate, and see the quality jump instantly.';
  }

  function withEmojiDensity(text: string) {
    if (captionEmojiDensity === 'None') return text;
    if (captionEmojiDensity === 'High') return `${text} 🔥🚀`;
    return `${text} 🔥`;
  }

  function buildAdvancedCaption(seed: string, variantIndex: number) {
    // NOSONAR
    const sections = seed
      .split('\n\n')
      .map((section) => section.trim())
      .filter(Boolean);

    let sectionCount = sections.length;
    if (captionLength === 'Small') sectionCount = 2;
    if (captionLength === 'Medium') sectionCount = 4;
    const compactSeed = sections.slice(0, Math.max(1, sectionCount)).join('\n\n');

    let objectiveLine = 'Built to generate leads with product clarity and trust.';
    if (captionObjective === 'Sales') objectiveLine = 'Built to move shoppers from attention to checkout.';
    if (captionObjective === 'Awareness') objectiveLine = 'Built to make your brand and product memorable in-feed.';
    if (captionObjective === 'Engagement') objectiveLine = 'Built to earn watch time, comments, and saves.';

    let tonePrefix = 'Hot take:';
    if (captionTone === 'Professional') tonePrefix = 'Professional brief:';
    if (captionTone === 'Funny') tonePrefix = 'Real talk:';
    if (captionTone === 'Inspirational') tonePrefix = 'Growth update:';
    if (captionTone === 'Bold') tonePrefix = 'Big upgrade:';
    if (captionTone === 'Casual') tonePrefix = 'Quick update:';

    const variantMod = variantIndex % 3;
    let variantLine = 'Ideal for performance teams that iterate fast.';
    if (variantMod === 0) variantLine = 'Use this for product demos and launch creatives.';
    if (variantMod === 1) variantLine = 'Great fit for paid social testing across new audiences.';

    const base = [
      `${tonePrefix} ${withEmojiDensity(getCaptionHookLine())}`,
      getVideoScriptLine(),
      compactSeed,
      objectiveLine,
      `Background media: ${videoBackgroundMedia}`,
      variantLine,
      getCtaLine(),
    ]
      .filter(Boolean)
      .join('\n\n');

    return captionAutoHashtags ? `${base}\n\n${getCaptionHashtags()}` : base;
  }

  const selectedCaptionPack = useMemo(
    () => UGC_CAPTION_PACKS.find((pack) => pack.id === captionPackId) ?? UGC_CAPTION_PACKS[0],
    [captionPackId]
  );

  const visibleUgcPreviewTemplates = useMemo(
    () => UGC_PREVIEW_TEMPLATES.filter((template) => template.categoryId === ugcStyleCategoryId),
    [ugcStyleCategoryId]
  );

  const selectedUgcPreviewTemplate = useMemo(
    () => UGC_PREVIEW_TEMPLATES.find((template) => template.id === ugcPreviewTemplateId) ?? UGC_PREVIEW_TEMPLATES[0],
    [ugcPreviewTemplateId]
  );

  function applyUgcPreviewTemplate(templateId: string) {
    const template = UGC_PREVIEW_TEMPLATES.find((item) => item.id === templateId);
    if (!template) return;
    trackUgcTemplateEvent('ugc_template_applied', tenantId, {
      template_id: template.id,
      category_id: template.categoryId,
      platform: template.platform,
      objective: template.objective,
    });
    setUgcPreviewTemplateId(template.id);
    setCaptionPackId(template.packId);
    setCaptionPlatform(template.platform);
    setVideoCanvasAspectRatio(template.aspectRatio);
    setVideoScriptStyle(template.scriptStyle);
    setVideoBackgroundMedia(template.mediaSource);
    setVideoSubtitlesAuto(true);
    setVideoSubtitlesLanguage('Auto (detect)');
    setCaptionHookStyle(template.hookStyle);
    setCaptionObjective(template.objective);
    setVideoAutoAdjustPlatforms(false);
  }

  function selectUgcStyleCategory(categoryId: string) {
    setUgcStyleCategoryId(categoryId);
    const firstTemplate = UGC_PREVIEW_TEMPLATES.find((template) => template.categoryId === categoryId);
    if (firstTemplate) setUgcPreviewTemplateId(firstTemplate.id);
  }

  const adjustedCanvas = UGC_PLATFORM_CANVAS_MAP[captionPlatform] ?? videoCanvasAspectRatio;
  const captionsVideoConfigNote = videoCanvasAspectRatio
    ? [
        `Template: ${selectedUgcPreviewTemplate.title}`,
        `Canvas ${videoCanvasAspectRatio}`,
        videoAutoAdjustPlatforms ? `Auto-adjust: ${captionPlatform} -> ${adjustedCanvas}` : '',
        `Source: ${videoBackgroundMedia}`,
        videoSubtitlesAuto ? `Subtitles: ${videoSubtitlesLanguage}` : 'Subtitles: Off',
      ]
        .filter(Boolean)
        .join(' • ')
    : 'Select a canvas size to proceed.';

  useEffect(() => {
    if (!ugcTemplateHydratedRef.current || ugcTemplateSavingRef.current) return;

    const timer = setTimeout(async () => {
      const payload = normalizeUgcTemplateProfile(
        {
          style_category_id: ugcStyleCategoryId,
          preview_template_id: ugcPreviewTemplateId,
          caption_pack_id: captionPackId,
          platform: captionPlatform,
          objective: captionObjective,
          hook_style: captionHookStyle,
          script_style: videoScriptStyle,
          aspect_ratio: videoCanvasAspectRatio,
          auto_adjust_platforms: videoAutoAdjustPlatforms,
          background_media: videoBackgroundMedia,
          subtitles_auto: videoSubtitlesAuto,
          subtitles_language: videoSubtitlesLanguage,
        },
        UGC_TEMPLATE_NORMALIZE_OPTIONS
      );

      ugcTemplateSavingRef.current = true;
      try {
        await saveUgcTemplateProfile(payload, tenantId);
        trackUgcTemplateEvent('ugc_template_saved', tenantId, {
          template_id: payload.preview_template_id,
          category_id: payload.style_category_id,
          platform: payload.platform,
        });
        setUgcTemplateSyncError('');
      } catch (error) {
        trackUgcTemplateEvent('ugc_template_save_failed', tenantId, {
          message: error instanceof Error ? error.message : 'unknown-save-error',
        });
        setUgcTemplateSyncError(error instanceof Error ? error.message : 'Failed to save UGC template preferences.');
      } finally {
        ugcTemplateSavingRef.current = false;
      }
    }, 700);

    return () => clearTimeout(timer);
  }, [
    captionHookStyle,
    captionObjective,
    captionPackId,
    captionPlatform,
    tenantId,
    ugcPreviewTemplateId,
    ugcStyleCategoryId,
    videoAutoAdjustPlatforms,
    videoBackgroundMedia,
    videoCanvasAspectRatio,
    videoSubtitlesAuto,
    videoSubtitlesLanguage,
    videoScriptStyle,
  ]);

  async function generateCaptionVariants(multiplier = 1) {
    const parsed = Number.parseInt(captionVariantCount, 10);
    const count = Number.isFinite(parsed) ? Math.min(Math.max(parsed, 1), 6) : 3;
    const total = Math.min(8, count * Math.max(1, multiplier));

    setIsGeneratingCaptions(true);
    try {
      const response = await apiPost(
        '/social/ai/owly-writer/generate',
        {
          topic: selectedCaptionPack.body.slice(0, 800),
          style: getApiToneValue(),
          platforms: [captionPlatform.toLowerCase()],
          goal: captionObjective.toLowerCase(),
          audience: 'social audience',
          include_hashtags: captionAutoHashtags,
          include_emoji: captionEmojiDensity !== 'None',
          include_cta: true,
          variations_per_platform: Math.max(1, Math.min(6, total)),
        },
        tenantId
      );

      const generation = (response as { generation?: { items?: Array<Record<string, unknown>> } }).generation;
      const items = Array.isArray(generation?.items) ? generation.items : [];
      const createdFromApi = items
        .slice(0, total)
        .map((item, index) => {
          const caption = coerceText(item.caption, '').trim();
          if (!caption) return null;
          const hashtags = Array.isArray(item.hashtags)
            ? item.hashtags
                .map((tag) => coerceText(tag, '').trim())
                .filter(Boolean)
                .map((tag) => (tag.startsWith('#') ? tag : `#${tag}`))
            : [];
          return {
            id: `caption-${Date.now()}-${index}`,
            text: hashtags.length > 0 && captionAutoHashtags ? `${caption}\n\n${hashtags.join(' ')}` : caption,
          };
        })
        .filter((item): item is { id: string; text: string } => Boolean(item));

      if (createdFromApi.length > 0) {
        setCaptions((current) => [...createdFromApi, ...current].slice(0, 16));
        setSelectedCaptionId(createdFromApi[0]?.id ?? selectedCaptionId);
        return;
      }

      const fallback = Array.from({ length: total }, (_, index) => ({
        id: `caption-${Date.now()}-${index}`,
        text: buildAdvancedCaption(selectedCaptionPack.body, index),
      }));
      setCaptions((current) => [...fallback, ...current].slice(0, 16));
      setSelectedCaptionId(fallback[0]?.id ?? selectedCaptionId);
    } finally {
      setIsGeneratingCaptions(false);
    }
  }

  function toggleSuggestionPlatform(platform: string) {
    setSuggestionPlatforms((current) => {
      if (current.includes(platform)) {
        return current.length === 1 ? current : current.filter((item) => item !== platform);
      }
      return [...current, platform];
    });
  }

  async function generateKeywordHashtags() {
    if (!hashtagKeyword.trim()) return;
    setIsGeneratingHashtags(true);

    try {
      const response = await apiPost(
        '/social/ai/owly-writer/generate',
        {
          topic: hashtagKeyword.trim(),
          style: getApiToneValue(),
          platforms: ['instagram', 'tiktok', 'youtube'],
          goal: 'engagement',
          audience: 'social audience',
          include_hashtags: true,
          include_emoji: false,
          include_cta: false,
          variations_per_platform: 2,
        },
        tenantId
      );

      const generation = (response as { generation?: { items?: Array<{ hashtags?: string[] }> } }).generation;
      const items = Array.isArray(generation?.items) ? generation.items : [];
      const hashtagCounts = new Map<string, number>();

      for (const item of items) {
        const hashtags = Array.isArray(item.hashtags) ? item.hashtags : [];
        for (const hashtag of hashtags) {
          const normalized = hashtag.startsWith('#') ? hashtag : `#${hashtag}`;
          hashtagCounts.set(normalized, (hashtagCounts.get(normalized) ?? 0) + 1);
        }
      }

      const generated = [...hashtagCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30)
        .map(([tag, count]) => ({ tag, count: `${count}x` }));

      if (generated.length > 0) {
        setGeneratedKeywordHashtags(generated);
        setAddedHashtags(generated.slice(0, 12).map((item) => item.tag));
        setHashtagEditText(
          generated
            .slice(0, 20)
            .map((item) => item.tag)
            .join(' ')
        );
        return;
      }

      const fallback = hashtagKeyword
        .split(/[\s,]+/)
        .map((item) => item.trim().replace(/[^a-zA-Z0-9]/g, ''))
        .filter(Boolean)
        .slice(0, 8)
        .map((item, index) => ({ tag: `#${item.toLowerCase()}`, count: `${Math.max(1, 8 - index)}x` }));
      setGeneratedKeywordHashtags(fallback);
      setAddedHashtags(fallback.map((item) => item.tag));
      setHashtagEditText(fallback.map((item) => item.tag).join(' '));
    } finally {
      setIsGeneratingHashtags(false);
    }
  }

  async function generatePostSuggestions() {
    setSuggestionsError('');
    setSuggestionsActionMessage('');
    setIsGeneratingSuggestions(true);

    try {
      const topic = suggestionTopic.trim() || generationPrompt.trim() || slides[0]?.headline || 'Social video clip';
      const response = await apiPost(
        '/social/ai/owly-writer/generate',
        {
          topic,
          style: suggestionStyle,
          platforms: suggestionPlatforms,
          goal: suggestionGoal,
          audience: suggestionAudience.trim() || 'social audience',
          include_hashtags: true,
          include_emoji: true,
          include_cta: true,
          variations_per_platform: 2,
        },
        tenantId
      );

      const generation = (response as { generation?: { items?: Array<Record<string, unknown>> } }).generation;
      const items = Array.isArray(generation?.items) ? generation.items : [];
      const mapped: EditorSuggestionItem[] = items.map((item, index) => {
        const rawHashtags = Array.isArray(item.hashtags) ? item.hashtags : [];
        const hashtags = rawHashtags
          .map((tag) => coerceText(tag, '').trim())
          .filter(Boolean)
          .map((tag) => (tag.startsWith('#') ? tag : `#${tag}`));
        const quality =
          item.quality && typeof item.quality === 'object' ? (item.quality as { overall?: number }) : undefined;

        return {
          id: coerceText(item.id, `suggestion-${Date.now()}-${index}`),
          platform: coerceText(item.platform, 'social'),
          caption: coerceText(item.caption, '').trim(),
          hashtags,
          score: Number(quality?.overall ?? 0),
        };
      });

      setSuggestions(mapped.filter((item) => item.caption.length > 0));
    } catch (error) {
      setSuggestionsError(error instanceof Error ? error.message : 'Failed to generate AI suggestions.');
    } finally {
      setIsGeneratingSuggestions(false);
    }
  }

  async function sendSuggestionToIdeas(item: EditorSuggestionItem) {
    setSuggestionsActionMessage('');
    await apiPost(
      '/social/ideas',
      {
        title: `${item.platform.toUpperCase()} clip suggestion`,
        body: `${item.caption}\n\n${item.hashtags.join(' ')}`.trim(),
        source: 'editor-suggestions',
        tags: item.hashtags.map((tag) => tag.replace(/^#/, '')),
      },
      tenantId
    );
    setSuggestionsActionMessage('Suggestion sent to Social Ideas queue.');
  }

  const hashtagList = useMemo<HashtagItem[]>(() => {
    if (hashtagsBy === 'creative') return HASHTAGS_CREATIVE;
    if (hashtagsBy === 'keyword') {
      return generatedKeywordHashtags.length > 0 ? generatedKeywordHashtags : HASHTAGS_KEYWORD;
    }
    return HASHTAGS_CAPTION;
  }, [generatedKeywordHashtags, hashtagsBy]);

  const insightTrendBars = useMemo(() => {
    if (!postInsights?.trendPoints.length) return [];
    const max = Math.max(1, ...postInsights.trendPoints.map((point) => point.value));
    return postInsights.trendPoints.map((point) => ({
      label: `P${point.period_index}`,
      value: point.value,
      height: Math.max(16, Math.round((point.value / max) * 84)),
    }));
  }, [postInsights]);

  const libraryItems = useMemo<CreativeLibraryItem[]>(() => {
    const historyItems: CreativeLibraryItem[] = publishHistory.map((item) => ({
      id: `history-${item.id}`,
      title: coerceText(item.request.topic ?? item.request.product ?? slides[0]?.headline, 'Published Creative').slice(
        0,
        48
      ),
      subtitle: coerceText(item.request.audience ?? slides[0]?.subheadline, 'Campaign asset').slice(0, 48),
      caption:
        coerceText(item.request.topic ?? item.request.product ?? slides[0]?.headline, 'Published Creative') +
        ' was published successfully for this tenant.',
      format: item.endpoint.includes('schedule') ? 'carousel' : 'image',
      aspectRatio: item.endpoint.includes('schedule') ? '4:5' : '1:1',
      brand: 'nuxtron',
      cta: item.publishMode === 'draft' ? 'Draft' : 'Published',
      badge: item.endpoint.includes('schedule') ? 'carousel' : '1:1',
    }));

    return [...BASE_LIBRARY_ITEMS, ...historyItems].filter((libraryItem) => {
      const matchesTab =
        libraryTab === 'all' ||
        (libraryTab === 'image' && libraryItem.format === 'image') ||
        (libraryTab === 'video' && libraryItem.format === 'video') ||
        (libraryTab === 'carousel' && libraryItem.format === 'carousel');
      if (!matchesTab) return false;
      const q = librarySearch.trim().toLowerCase();
      if (!q) return true;
      return `${libraryItem.title} ${libraryItem.subtitle} ${libraryItem.caption}`.toLowerCase().includes(q);
    });
  }, [librarySearch, libraryTab, publishHistory, slides]);

  const selectedLibraryItem = useMemo(
    () => libraryItems.find((item) => item.id === selectedLibraryId) ?? null,
    [libraryItems, selectedLibraryId]
  );

  const visibleEditorLayers = useMemo(
    () => new Set(editorLayers.filter((layer) => layer.visible).map((layer) => layer.id)),
    [editorLayers]
  );

  const insertOptions = useMemo(
    () => [
      'Upload Media',
      'Text',
      'Shapes',
      'Buttons',
      'Stock photos',
      'My uploads',
      'AI images',
      'Illustrations',
      'Icons & Logos',
    ],
    []
  );

  function recordEditorAction(action: string) {
    setEditorHistory((current) => [action, ...current.filter((item) => item !== action)].slice(0, 8));
  }

  async function loadPostInsights() {
    setIsInsightsLoading(true);
    setInsightsError('');

    const historyRevenue = [320, 410, 515].map(
      (base, index) => base + publishHistory.length * 18 + scheduledPosts.length * 24 + index * 12
    );
    const historyEngagement = [0.041, 0.052, 0.048].map((base, index) =>
      Number((base + scheduledPosts.length * 0.0015 + publishHistory.length * 0.0008 + index * 0.0004).toFixed(3))
    );

    try {
      const [dashboardRaw, kpiRaw, trendRaw, roiRaw] = await Promise.all([
        apiGet('/analytics/dashboard', tenantId),
        apiGet('/analytics/insights/kpi', tenantId),
        apiPost(
          '/analytics/insights/trend',
          {
            metric: 'social_scheduled',
            period: 'last_30_days',
            granularity: 'daily',
          },
          tenantId
        ),
        apiPost(
          '/forecast/roi',
          {
            content_title: selectedSlide.headline,
            platform: 'instagram',
            expected_impressions: 12000 + scheduledPosts.length * 1200 + publishHistory.length * 400,
            historical_revenue: historyRevenue,
            historical_engagement_rate: historyEngagement,
          },
          tenantId
        ),
      ]);

      const dashboard = (dashboardRaw.dashboard ?? {}) as Record<string, unknown>;
      const kpi = (kpiRaw.kpi ?? {}) as Record<string, unknown>;
      const growth = (kpi.growth ?? {}) as Record<string, unknown>;
      const trend = (trendRaw.trend ?? {}) as Record<string, unknown>;
      const forecast = (roiRaw.forecast ?? {}) as Record<string, unknown>;
      const baselineRevenue = historyRevenue.reduce((sum, value) => sum + value, 0) / historyRevenue.length;

      setPostInsights({
        projectedEngagement: coerceNumber(forecast.projected_engagement),
        projectedClicks: coerceNumber(forecast.projected_clicks),
        projectedConversions: coerceNumber(forecast.projected_conversions),
        projectedRevenue: coerceNumber(forecast.projected_revenue),
        roiLift:
          baselineRevenue > 0 ? (coerceNumber(forecast.projected_revenue) - baselineRevenue) / baselineRevenue : 0,
        confidence: coerceNumber(forecast.confidence),
        recommendedSlot: coerceText(forecast.recommended_slot, 'Tue 09:30'),
        scheduledPosts: coerceNumber(dashboard.social_posts_scheduled, coerceNumber(growth.social_posts)),
        listeningMentions: coerceNumber(dashboard.listening_mentions),
        crmContacts: coerceNumber(growth.crm_contacts),
        trendDirection: coerceText(trend.trend_direction, 'flat'),
        trendPoints: Array.isArray(trend.datapoints)
          ? (trend.datapoints as TrendPoint[])
              .map((point) => ({
                period_index: coerceNumber(point.period_index),
                value: coerceNumber(point.value),
              }))
              .slice(-8)
          : [],
      });
    } catch (error) {
      setInsightsError(error instanceof Error ? error.message : 'Failed to load post insights.');
    } finally {
      setIsInsightsLoading(false);
    }
  }

  async function loadScheduledPosts() {
    setIsScheduleLoading(true);
    setScheduleError('');
    try {
      const response = await apiGet('/api/v1/social/content/list?status=scheduled', tenantId);
      const itemsRaw = Array.isArray(response.items) ? (response.items as ParityContentItem[]) : [];
      const items = itemsRaw
        .map((item) => mapParityContentItemToScheduledPost(item, tenantId))
        .filter((item): item is ScheduledPost => Boolean(item))
        .sort((a, b) => a.publish_at.localeCompare(b.publish_at));
      setScheduledPosts(items);
    } catch (error) {
      setScheduleError(error instanceof Error ? error.message : 'Failed to load scheduled posts.');
    } finally {
      setIsScheduleLoading(false);
    }
  }

  async function loadSocialCatalog() {
    setIsSocialCatalogLoading(true);
    setSocialCatalogError('');
    try {
      const response = await apiGet('/social/accounts/catalog', tenantId);
      const providers = Array.isArray(response.providers) ? (response.providers as SocialCatalogProvider[]) : [];
      setSocialCatalogProviders(providers);
    } catch (error) {
      setSocialCatalogError(error instanceof Error ? error.message : 'Failed to load social platform requirements.');
    } finally {
      setIsSocialCatalogLoading(false);
    }
  }

  async function loadBrandProfileSettings() {
    setIsBrandProfileLoading(true);
    setBrandProfileError('');
    setBrandProfileStatus('');
    try {
      const profile = await loadBrandProfile(tenantId);
      setBrandProfile(profile);
      setBrandWebsiteDraft(profile.website ?? '');
    } catch (error) {
      setBrandProfileError(error instanceof Error ? error.message : 'Failed to load brand profile settings.');
      setBrandProfile(null);
    } finally {
      setIsBrandProfileLoading(false);
    }
  }

  async function handleSaveBrandProfile() {
    if (!brandProfile) return;
    setIsBrandProfileSaving(true);
    setBrandProfileError('');
    setBrandProfileStatus('');
    try {
      const saved = await saveBrandProfile(brandProfile, tenantId);
      setBrandProfile(saved);
      setBrandWebsiteDraft(saved.website ?? '');
      setBrandProfileStatus('Brand profile saved.');
    } catch (error) {
      setBrandProfileError(error instanceof Error ? error.message : 'Failed to save brand profile.');
    } finally {
      setIsBrandProfileSaving(false);
    }
  }

  async function handleSyncBrandFromWebsite() {
    const websiteUrl = brandWebsiteDraft.trim();
    if (!websiteUrl) return;
    setIsBrandWebsiteSyncing(true);
    setBrandProfileError('');
    setBrandProfileStatus('');
    try {
      const synced = await fetchBrandProfileFromWebsite(websiteUrl, tenantId);
      setBrandProfile(synced);
      setBrandWebsiteDraft(synced.website ?? websiteUrl);
      setBrandProfileStatus('Brand profile synced from website.');
    } catch (error) {
      setBrandProfileError(error instanceof Error ? error.message : 'Failed to sync brand profile from website.');
    } finally {
      setIsBrandWebsiteSyncing(false);
    }
  }

  useEffect(() => {
    void loadScheduledPosts();
    void loadSocialCatalog();
    void loadBrandProfileSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  useEffect(() => {
    void loadPostInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedSlideIndex, scheduledPosts.length, publishHistory.length]);

  const scheduledPostsByCell = useMemo(() => {
    const map = new Map<string, ScheduledPost[]>();
    for (const post of scheduledPosts) {
      const date = new Date(post.publish_at);
      const dayKey = toLocalDateKey(date);
      const hour = date.getHours();
      const key = `${dayKey}::${hour}`;
      const existing = map.get(key) ?? [];
      map.set(key, [...existing, post]);
    }
    return map;
  }, [scheduledPosts]);

  function updateSlideText(field: keyof Slide, value: string) {
    setSlides((current) => {
      const next = [...current];
      next[selectedSlideIndex] = { ...next[selectedSlideIndex], [field]: value };
      return next;
    });
  }

  function applyLibraryItemToEditor(item: CreativeLibraryItem) {
    setSlides((current) => {
      const next = [...current];
      next[0] = {
        ...next[0],
        headline: item.title,
        subheadline: item.subtitle,
        cta: item.cta,
      };
      return next;
    });
    setSelectedSlideIndex(0);
    setActiveAssetType(item.format === 'carousel' ? 'carousel' : 'image_ad');
    setEditorBrandLabel(item.brand);
    setEditorBadge(item.badge ?? '1:1');
    setInsertPanelView('root');
    setInsertSearch('');
    setSelectedEditorLayer('headline');
    setEditorLayers((current) => current.map((layer) => ({ ...layer, visible: true })));
    setEditorHistory(['Opened preview', `Loaded ${item.title}`, 'Created canvas']);
    setCreativeView('editor');
    setSelectedLibraryId('');
  }

  function openBlankCreativeEditor() {
    setSlides((current) => {
      const next = [...current];
      next[0] = {
        ...next[0],
        headline: 'BLACK FRIDAY',
        subheadline: 'Build a studio-ready campaign in minutes.',
        cta: 'Launch Offer',
        imageUrl: '',
      };
      return next;
    });
    setSelectedSlideIndex(0);
    setActiveAssetType('image_ad');
    setEditorBrandLabel('nuxtron');
    setEditorBadge('1:1');
    setInsertPanelView('root');
    setInsertSearch('');
    setSelectedEditorLayer('headline');
    setEditorLayers((current) => current.map((layer) => ({ ...layer, visible: true })));
    setEditorHistory(['Created blank creative', 'Created canvas']);
    setCreativeView('editor');
  }

  function setLayerVisibility(layerId: EditorLayerId, visible: boolean) {
    const layer = editorLayers.find((item) => item.id === layerId);
    if (!layer) return;
    setEditorLayers((current) => current.map((item) => (item.id === layerId ? { ...item, visible } : item)));
    recordEditorAction(`${visible ? 'Showed' : 'Hidden'} ${layer.label}`);
  }

  function applyTextQuickAction(mode: 'header' | 'subheader' | 'body') {
    if (mode === 'header') {
      setLayerVisibility('headline', true);
      setSelectedEditorLayer('headline');
      updateSlideText('headline', 'Create Header');
      recordEditorAction('Created headline text');
      return;
    }

    if (mode === 'subheader') {
      setLayerVisibility('subtitle', true);
      setSelectedEditorLayer('subtitle');
      updateSlideText('subheadline', 'Create sub header');
      recordEditorAction('Created sub header text');
      return;
    }

    setLayerVisibility('subtitle', true);
    setSelectedEditorLayer('subtitle');
    const next = selectedSlide.subheadline?.trim()
      ? `${selectedSlide.subheadline} Create body text.`
      : 'Create body text';
    updateSlideText('subheadline', next);
    recordEditorAction('Created body text');
  }

  function applyTextStylePreset(preset: string) {
    setLayerVisibility('headline', true);
    setSelectedEditorLayer('headline');
    updateSlideText('headline', preset);
    recordEditorAction(`Applied text style: ${preset}`);
  }

  function handleInsertAction(option: string) {
    if (option === 'Text') {
      setInsertPanelView('text');
      recordEditorAction('Opened text insert panel');
      return;
    }

    if (option === 'Buttons') {
      updateSlideText('cta', selectedSlide.cta === 'Shop Now' ? 'Grab Deal' : 'Shop Now');
      setLayerVisibility('cta', true);
      setSelectedEditorLayer('cta');
      recordEditorAction('Added CTA button');
      return;
    }

    if (option === 'Shapes') {
      setEditorBadge((current) => (current === 'LIMITED' ? '1:1' : 'LIMITED'));
      setSelectedEditorLayer('background');
      recordEditorAction('Added promo badge');
      return;
    }

    if (option === 'Icons & Logos') {
      setEditorBrandLabel((current) => (current === 'nuxtron' ? 'shopify' : 'nuxtron'));
      setLayerVisibility('brand', true);
      setSelectedEditorLayer('brand');
      recordEditorAction('Updated brand logo');
      return;
    }

    if (option === 'Upload Media' || option === 'Stock photos' || option === 'My uploads' || option === 'AI images') {
      setLayerVisibility('background', true);
      setSelectedEditorLayer('background');
      recordEditorAction(`Prepared ${option.toLowerCase()}`);
      return;
    }

    if (option === 'Illustrations') {
      setSelectedEditorLayer('subtitle');
      updateSlideText('subheadline', 'Fresh illustration-ready layout for social campaigns.');
      recordEditorAction('Added illustration prompt');
    }
  }

  function addSlide() {
    setSlides((current) => {
      const next = [
        ...current,
        {
          id: nextSlideId(current.length),
          headline: 'NEW HEADLINE',
          subheadline: 'Write your carousel message here.',
          cta: 'Learn more',
          imageUrl: '',
        },
      ];
      return next;
    });
    setSelectedSlideIndex(slides.length);
    setActiveAssetType('carousel');
  }

  function duplicateSlide() {
    setSlides((current) => {
      const source = current[selectedSlideIndex];
      if (!source) return current;
      const clone: Slide = {
        ...source,
        id: nextSlideId(current.length),
      };
      const next = [...current.slice(0, selectedSlideIndex + 1), clone, ...current.slice(selectedSlideIndex + 1)];
      return next;
    });
    setSelectedSlideIndex((index) => index + 1);
  }

  function deleteSlide() {
    setSlides((current) => {
      if (current.length <= 1) return current;
      const next = [...current.slice(0, selectedSlideIndex), ...current.slice(selectedSlideIndex + 1)];
      return next;
    });
    setSelectedSlideIndex((index) => Math.max(0, index - 1));
  }

  function uploadSlideImage(file?: File) {
    if (!file) return;
    const objectUrl = URL.createObjectURL(file);
    setSlides((current) => {
      const next = [...current];
      const target = { ...next[selectedSlideIndex], imageUrl: objectUrl };
      next[selectedSlideIndex] = target;
      return next;
    });
  }

  function applyTemplate(templateId: string) {
    setSelectedTemplateId(templateId);
    const template = TEMPLATES.find((item) => item.id === templateId);
    if (!template) return;

    setSlides((current) => {
      const next = [...current];
      const active = {
        ...next[selectedSlideIndex],
        headline: template.title.toUpperCase().slice(0, 22),
        subheadline: template.subtitle,
      };
      next[selectedSlideIndex] = active;
      return next;
    });
  }

  function addSlideFromTemplate(templateId: string) {
    const template = TEMPLATES.find((item) => item.id === templateId);
    if (!template) return;

    setSelectedTemplateId(templateId);
    setSlides((current) => {
      const next = [
        ...current,
        {
          id: nextSlideId(current.length),
          headline: template.title.toUpperCase().slice(0, 22),
          subheadline: template.subtitle,
          cta: 'Learn more',
          imageUrl: '',
        },
      ];
      return next;
    });
    setSelectedSlideIndex(slides.length);
    setActiveAssetType(template.category);
  }

  const exportPayload = {
    mode: activeMode,
    assetType: activeAssetType,
    templateId: selectedTemplateId,
    keepEdits,
    slides,
    style: {
      tone,
      fontName,
      fontColor,
      panel: activePanel,
      tool: activeTool,
    },
  };

  const publishAssetLinks = useMemo(() => {
    if (!publishResult) return [] as Array<{ label: string; href: string }>;
    const response = publishResult.response;
    if (!response || typeof response !== 'object') return [] as Array<{ label: string; href: string }>;

    const outputs = (response as Record<string, unknown>).outputs;
    if (!outputs || typeof outputs !== 'object') return [] as Array<{ label: string; href: string }>;

    const outputMap = outputs as Record<string, unknown>;
    const candidates: Array<{ key: string; label: string }> = [
      { key: 'image_url', label: 'Image' },
      { key: 'video_url', label: 'Video' },
      { key: 'voice_url', label: 'Voice' },
    ];

    return candidates
      .map((candidate) => {
        const value = outputMap[candidate.key];
        if (typeof value !== 'string' || !value.trim()) return null;
        const href = value.startsWith('/') ? `${PROXY_BASE_URL}${value}` : value;
        return { label: candidate.label, href };
      })
      .filter((item): item is { label: string; href: string } => Boolean(item));
  }, [publishResult]);

  function getApiToneValue() {
    if (tone === 'informal') {
      return 'casual';
    }

    return tone;
  }

  function buildPublishTarget(): PublishTarget {
    const textBundle = slides
      .map((slide, index) => `${index + 1}. ${slide.headline} - ${slide.subheadline}`)
      .join('\n');
    const mediaUrls = slides.map((slide) => slide.imageUrl).filter(Boolean);
    const firstSlide = slides[0] ?? {
      headline: 'Creative concept',
      subheadline: 'Campaign concept generated from Studio editor',
      cta: 'Learn more',
    };
    const requirementsSummary = socialCatalogProviders
      .map((provider) => `${provider.label}: ${provider.supported_formats.join(', ')}`)
      .join('; ');
    const contextBundle = [
      generationContext.trim(),
      requirementsSummary ? `Platform requirements -> ${requirementsSummary}` : '',
    ]
      .filter(Boolean)
      .join('\n');
    const basePrompt = generationPrompt.trim() || `Generate campaign assets for ${firstSlide.headline}.`;
    let publishAtIso = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    if (publishMode === 'now') {
      publishAtIso = new Date().toISOString();
    }
    if (publishAt) {
      publishAtIso = new Date(publishAt).toISOString();
    }

    if (activeMode === 'creatives') {
      if (activeAssetType === 'carousel') {
        return {
          path: '/api/v1/social/content/create',
          payload: {
            title: firstSlide.headline,
            caption: textBundle,
            media_assets: mediaUrls.map((url) => ({ type: 'image', url })),
            platforms: ['instagram'],
            requires_approval: publishMode === 'draft',
            scheduled_for: publishAtIso,
          },
        };
      }

      return {
        path: '/ads/generate',
        payload: {
          product: firstSlide.headline,
          audience: 'growth operators',
          platform: activeAssetType === 'story_ad' ? 'meta' : 'google',
          objective: 'sales',
          provider: 'google_vertex',
          prompt: `${basePrompt}\n\nPrimary asset: ${firstSlide.headline}.`,
          system_prompt: contextBundle || undefined,
          target_formats: ['text', 'image', 'video', 'voice', 'reel', 'short'],
        },
      };
    }

    return {
      path: '/content/generate',
      payload: {
        topic: firstSlide.headline,
        audience: 'digital marketing teams',
        channel: activeAssetType === 'story_ad' ? 'instagram' : 'linkedin',
        tone: getApiToneValue(),
        include_seo: activeMode !== 'hashtags',
        provider: 'google_vertex',
        prompt: `${basePrompt}\n\nCampaign summary:\n${textBundle}`,
        system_prompt: contextBundle || undefined,
        target_formats: ['text', 'image', 'video', 'voice', 'reel', 'short'],
      },
    };
  }

  async function publishCreative() {
    setPublishError('');
    setPublishResult(null);
    setIsPublishing(true);

    try {
      const target = buildPublishTarget();
      const response = await apiPost(target.path, target.payload, tenantId);

      const nextResult = {
        endpoint: target.path,
        tenantId,
        publishMode,
        request: target.payload,
        response,
      };

      setPublishResult({
        ...nextResult,
      });
      setPublishHistory((current) => {
        const entry: PublishHistoryItem = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          endpoint: target.path,
          tenantId,
          publishedAt: new Date().toISOString(),
          publishMode,
          request: target.payload,
          response,
        };
        return [entry, ...current].slice(0, 10);
      });
      setPublished(true);
    } catch (error) {
      setPublishError(error instanceof Error ? error.message : 'Publish failed.');
      setPublished(true);
    } finally {
      setIsPublishing(false);
    }
  }

  async function scheduleDraftAt(slideIndex: number, day: Date, hour: number) {
    const source = slides[slideIndex];
    if (!source) return;

    const publishDate = buildCellPublishTime(day, hour);
    const payload = {
      title: source.headline || 'Scheduled post',
      caption: `${source.headline}\n${source.subheadline}`.trim(),
      media_assets: source.imageUrl ? [{ type: 'image', url: source.imageUrl }] : [],
      platforms: ['instagram'],
      requires_approval: false,
      scheduled_for: publishDate.toISOString(),
    };

    await apiPost('/api/v1/social/content/create', payload, tenantId);
    await loadScheduledPosts();
  }

  async function moveScheduledPostTo(postId: string, day: Date, hour: number) {
    const publishDate = buildCellPublishTime(day, hour);
    const nextPublishAt = publishDate.toISOString();
    const previous = scheduledPosts;
    setScheduledPosts((current) =>
      current.map((item) =>
        item.id === postId
          ? {
              ...item,
              publish_at: nextPublishAt,
            }
          : item
      )
    );

    try {
      await apiPost(`/api/v1/social/content/${postId}/reschedule`, { new_scheduled_time: nextPublishAt }, tenantId);
    } catch (error) {
      setScheduledPosts(previous);
      throw error;
    }
  }

  async function handleCalendarDrop(day: Date, hour: number, transferData: string) {
    const payload = parseDragPayload(transferData);
    if (!payload) return;

    setScheduleError('');
    if (payload.type === 'draft') {
      await scheduleDraftAt(payload.slideIndex, day, hour);
      return;
    }

    await moveScheduledPostTo(payload.postId, day, hour);
  }

  async function removeScheduledPost(postId: string) {
    const before = scheduledPosts;
    setScheduledPosts((current) => current.filter((item) => item.id !== postId));
    try {
      await apiDelete(`/api/v1/social/content/${postId}`, tenantId);
    } catch (error) {
      setScheduledPosts(before);
      setScheduleError(error instanceof Error ? error.message : 'Failed to delete scheduled post.');
    }
  }

  function onDraftCardDragStart(event: DragEvent<HTMLElement>) {
    const value = event.currentTarget.dataset.slideIndex;
    const slideIndex = Number.parseInt(value ?? '', 10);
    if (Number.isNaN(slideIndex)) return;
    event.dataTransfer.setData(
      'application/x-nuxtron-calendar-item',
      JSON.stringify({ type: 'draft', slideIndex } satisfies DragPayload)
    );
    event.dataTransfer.effectAllowed = 'copy';
  }

  function onScheduledCardDragStart(event: DragEvent<HTMLElement>) {
    const postId = event.currentTarget.dataset.postId?.trim() || '';
    if (!postId) return;
    event.dataTransfer.setData(
      'application/x-nuxtron-calendar-item',
      JSON.stringify({ type: 'scheduled', postId } satisfies DragPayload)
    );
    event.dataTransfer.effectAllowed = 'move';
  }

  function onDeleteScheduledPostClick(event: MouseEvent<HTMLButtonElement>) {
    const postId = event.currentTarget.dataset.postId?.trim() || '';
    if (!postId) return;
    void removeScheduledPost(postId);
  }

  function onCellDragOver(event: DragEvent<HTMLElement>, cellKey: string) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setActiveDropCell(cellKey);
  }

  function onCellDragLeave(cellKey: string) {
    setActiveDropCell((current) => (current === cellKey ? '' : current));
  }

  async function onCellDrop(event: DragEvent<HTMLElement>, day: Date, hour: number) {
    event.preventDefault();
    setActiveDropCell('');
    const payload = event.dataTransfer.getData('application/x-nuxtron-calendar-item');
    if (!payload) return;
    try {
      await handleCalendarDrop(day, hour, payload);
    } catch (error) {
      setScheduleError(error instanceof Error ? error.message : 'Failed to schedule post.');
    }
  }

  function buildArtboardStyle(editable: boolean): React.CSSProperties {
    if (!editable) return {};

    const aspect = videoCanvasAspectRatio || '1:1';
    const aspectCss = aspect.replace(':', ' / ');
    let canvasWidth = 'min(560px, 100%)';
    if (aspect === '9:16') canvasWidth = 'min(360px, 100%)';
    if (aspect === '16:9') canvasWidth = 'min(660px, 100%)';

    const shadowHex = fxShadowColor;
    const shadowAlpha = Math.round((fxShadowOpacity / 100) * 255)
      .toString(16)
      .padStart(2, '0');
    const glowAlpha = Math.round((fxGlow / 100) * 255)
      .toString(16)
      .padStart(2, '0');

    const shadows: string[] = [];
    if (fxShadowEnabled) {
      shadows.push(`${fxShadowX}px ${fxShadowY}px ${fxShadowBlur}px ${fxShadowSpread}px ${shadowHex}${shadowAlpha}`);
    }
    if (fxGlow > 0) {
      shadows.push(`0 0 ${fxGlow * 2}px ${fxGlow}px ${fxGlowColor}${glowAlpha}`);
    }

    const lightRad = (fxLightAngle * Math.PI) / 180;
    const lightX = Math.round(50 + 40 * Math.cos(lightRad));
    const lightY = Math.round(50 + 40 * Math.sin(lightRad));
    const lightAlpha = fxLightIntensity / 100;
    const sourceBackground =
      videoBackgroundMedia === 'AI Videos'
        ? 'linear-gradient(140deg, #eef0f4 4%, #eef0f4 36%, #0ea5a4 100%)'
        : 'linear-gradient(130deg, #eef0f4 0%, #eef0f4 45%, #e7e9ef 100%)';

    return {
      width: canvasWidth,
      aspectRatio: aspectCss,
      perspective: `${fxPerspective}px`,
      transform: `rotateX(${fx3dRotateX}deg) rotateY(${fx3dRotateY}deg) rotateZ(${fx3dRotateZ}deg) scale(${fx3dScale / 100})`,
      boxShadow: shadows.join(', ') || undefined,
      filter:
        [
          fxBlur > 0 ? `blur(${fxBlur}px)` : '',
          fxBrightness === 100 ? '' : `brightness(${fxBrightness}%)`,
          fxContrast === 100 ? '' : `contrast(${fxContrast}%)`,
          fxSaturation === 100 ? '' : `saturate(${fxSaturation}%)`,
        ]
          .filter(Boolean)
          .join(' ') || undefined,
      opacity: fxOpacity / 100,
      backgroundImage:
        fxLightIntensity > 0
          ? `radial-gradient(circle at ${lightX}% ${lightY}%, rgba(255,255,255,${lightAlpha}) 0%, transparent 65%), ${sourceBackground}`
          : sourceBackground,
    };
  }

  function renderCreativeArtboard(
    item: Pick<CreativeLibraryItem, 'title' | 'subtitle' | 'brand' | 'cta' | 'badge'>,
    options?: { compact?: boolean; editable?: boolean }
  ) {
    const compact = options?.compact ?? false;
    const editable = options?.editable ?? false;
    const artboardStyle = buildArtboardStyle(editable);
    let artboardClass = 'creative-artboard';
    if (compact) artboardClass = 'creative-artboard compact';
    if (!compact && editable) artboardClass = 'creative-artboard editable';

    return (
      <div className={artboardClass} style={artboardStyle}>
        <div className="creative-artboard-badge">
          {editable ? videoCanvasAspectRatio || 'Select ratio' : (item.badge ?? '1:1')}
        </div>
        {editable && fxBgOverlay && (
          <div
            className="artboard-overlay"
            style={{
              background: fxBgOverlayColor,
              opacity: fxBgOverlayOpacity / 100,
            }}
          />
        )}
        {(!editable || visibleEditorLayers.has('brand')) && <div className="creative-artboard-logo">Predis.ai</div>}
        <div className="creative-artboard-copy">
          {(!editable || visibleEditorLayers.has('headline')) && <h3>{item.title}</h3>}
          {(!editable || visibleEditorLayers.has('subtitle')) && <p>{item.subtitle}</p>}
        </div>
        {(!editable || visibleEditorLayers.has('background')) && (
          <div className="creative-artboard-hoodies">
            <div className="hoodie hoodie-gold" />
            <div className="hoodie hoodie-green" />
            <div className="hoodie hoodie-red" />
            <div className="hoodie hoodie-blue" />
          </div>
        )}
        <div className="creative-artboard-footer">
          {(!editable || visibleEditorLayers.has('brand')) && (
            <span className="creative-artboard-brand">{item.brand}</span>
          )}
          {(!editable || visibleEditorLayers.has('cta')) && <span className="creative-artboard-cta">{item.cta}</span>}
        </div>
      </div>
    );
  }

  return (
    <main className="editor-shell">
      <div className="editor-halo left" />
      <div className="editor-halo right" />

      <header className="editor-topbar">
        <div className="topbar-left">
          <a href="/studio/workspace" className="topbar-back-btn">
            ← Save &amp; Exit
          </a>
          <button type="button" className="ghost-btn topbar-save-btn">
            Save
          </button>
        </div>

        <nav className="mode-tabs" aria-label="Editor mode">
          <button
            type="button"
            className={activeMode === 'creatives' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('creatives')}
          >
            ✦ Creatives
          </button>
          <button
            type="button"
            className={activeMode === 'captions' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('captions')}
          >
            ☰ Captions
          </button>
          <button
            type="button"
            className={activeMode === 'hashtags' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('hashtags')}
          >
            # Hashtags
          </button>
          <button
            type="button"
            className={activeMode === 'suggestions' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('suggestions')}
          >
            💡 Suggestions
          </button>
          <button
            type="button"
            className={activeMode === 'timeline' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('timeline')}
          >
            ⏱ Timeline
          </button>
          <button
            type="button"
            className={activeMode === 'color' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('color')}
          >
            🎨 Color
          </button>
          <button
            type="button"
            className={activeMode === 'effects' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('effects')}
          >
            ✨ Effects
          </button>
          <button
            type="button"
            className={activeMode === 'audio' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('audio')}
          >
            🎚 Audio
          </button>
          <button
            type="button"
            className={activeMode === 'transitions' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('transitions')}
          >
            ↔ Transitions
          </button>
          <button
            type="button"
            className={activeMode === 'motion' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('motion')}
          >
            ✦ Motion
          </button>
          <button
            type="button"
            className={activeMode === 'media' ? 'mode-tab active' : 'mode-tab'}
            onClick={() => setActiveMode('media')}
          >
            📁 Media
          </button>
        </nav>

        <div className="topbar-right">
          <button type="button" className="ghost-btn topbar-icon-btn" title="Download">
            ⬇
          </button>
          <button
            type="button"
            className="topbar-send-btn"
            onClick={() => void publishCreative()}
            disabled={isPublishing}
            title="Send"
          >
            ➤
          </button>
          <button type="button" className="topbar-promo-btn">
            Claim Up To 50% Off &nbsp;<span className="topbar-promo-timer">🔴 {formatTimer(timerSeconds)}</span>
          </button>
        </div>
      </header>

      <section className="publish-toolbar">
        <label>
          <span>Tenant</span>
          <input value={tenantId} readOnly placeholder="tenant-demo" />
        </label>
        <label>
          <span>Prompt</span>
          <input
            value={generationPrompt}
            onChange={(event) => setGenerationPrompt(event.target.value)}
            placeholder="Tell AI what to generate"
          />
        </label>
        <label>
          <span>Context</span>
          <input
            value={generationContext}
            onChange={(event) => setGenerationContext(event.target.value)}
            placeholder="Brand voice, offer details, constraints"
          />
        </label>
        <label>
          <span>Brand</span>
          <input
            value={brandProfile?.business_name ?? ''}
            onChange={(event) =>
              setBrandProfile((current) =>
                current
                  ? {
                      ...current,
                      business_name: event.target.value,
                    }
                  : current
              )
            }
            placeholder="Brand name"
          />
        </label>
        <label>
          <span>Brand tone</span>
          <input
            value={brandProfile?.tone ?? ''}
            onChange={(event) =>
              setBrandProfile((current) =>
                current
                  ? {
                      ...current,
                      tone: event.target.value,
                    }
                  : current
              )
            }
            placeholder="professional"
          />
        </label>
        <label>
          <span>Brand website</span>
          <input
            value={brandWebsiteDraft}
            onChange={(event) => {
              const value = event.target.value;
              setBrandWebsiteDraft(value);
              setBrandProfile((current) =>
                current
                  ? {
                      ...current,
                      website: value.trim() || null,
                    }
                  : current
              );
            }}
            placeholder="https://example.com"
          />
        </label>
        <label>
          <span>Publish at</span>
          <input type="datetime-local" value={publishAt} onChange={(event) => setPublishAt(event.target.value)} />
        </label>
        <div className="publish-mode-switch" role="tablist" aria-label="Publish mode">
          <button
            type="button"
            className={publishMode === 'draft' ? 'chip active' : 'chip'}
            onClick={() => setPublishMode('draft')}
          >
            Publish As Draft
          </button>
          <button
            type="button"
            className={publishMode === 'now' ? 'chip active' : 'chip'}
            onClick={() => setPublishMode('now')}
          >
            Publish Now
          </button>
        </div>
        <button
          type="button"
          className="ghost-btn"
          onClick={() => void loadSocialCatalog()}
          disabled={isSocialCatalogLoading}
        >
          {isSocialCatalogLoading ? 'Loading requirements...' : 'Refresh Platform Requirements'}
        </button>
        <button
          type="button"
          className="ghost-btn"
          onClick={() => void handleSyncBrandFromWebsite()}
          disabled={isBrandWebsiteSyncing || !brandWebsiteDraft.trim()}
        >
          {isBrandWebsiteSyncing ? 'Syncing brand...' : 'Sync Brand DNA From Website'}
        </button>
        <button
          type="button"
          className="ghost-btn"
          onClick={() => void handleSaveBrandProfile()}
          disabled={isBrandProfileSaving || !brandProfile}
        >
          {isBrandProfileSaving ? 'Saving brand...' : 'Save Brand Profile'}
        </button>
        <button type="button" className="publish-btn" onClick={() => void publishCreative()} disabled={isPublishing}>
          {isPublishing ? 'Publishing...' : 'Publish To Backend'}
        </button>
      </section>

      {isBrandProfileLoading ? <p className="adv-info-text">Loading brand profile...</p> : null}
      {brandProfileError ? <p className="publish-error">{brandProfileError}</p> : null}
      {brandProfileStatus ? <p className="adv-info-text">{brandProfileStatus}</p> : null}
      {socialCatalogError ? <p className="publish-error">{socialCatalogError}</p> : null}
      {socialCatalogProviders.length ? (
        <section className="publish-toolbar" aria-label="Social platform requirements">
          <strong>All social media account requirements</strong>
          <p className="adv-info-text">Includes reels and short-video compatibility where supported.</p>
          {socialCatalogProviders.slice(0, 12).map((provider) => (
            <span key={provider.network} className="chip active">
              {provider.label}: {provider.supported_formats.join(', ')}
            </span>
          ))}
        </section>
      ) : null}

      <section className="insights-shell" aria-label="Current post traction and ROI">
        <div className="insights-head">
          <div>
            <p className="insights-eyebrow">Live Performance</p>
            <h2>Current post traction, results and ROI</h2>
            <p className="insights-copy">
              Tracking <strong>{selectedSlide.headline}</strong> with live tenant activity, scheduling momentum, and
              revenue forecast.
            </p>
          </div>
          <button
            type="button"
            className="ghost-btn"
            onClick={() => void loadPostInsights()}
            disabled={isInsightsLoading}
          >
            {isInsightsLoading ? 'Refreshing...' : 'Refresh insights'}
          </button>
        </div>

        {insightsError ? <p className="publish-error">{insightsError}</p> : null}

        <div className="insights-grid">
          <article className="insight-card insight-card-traction">
            <p className="insight-label">Current traction</p>
            <h3 className="insight-value">
              {postInsights ? formatCompactNumber(postInsights.projectedEngagement) : '--'}
            </h3>
            <p className="insight-subtle">
              {postInsights?.trendDirection === 'up' ? 'Momentum is climbing' : 'Momentum is steady'} with{' '}
              {formatCompactNumber(postInsights?.listeningMentions ?? 0)} live mentions.
            </p>
            <div className="trend-bars" aria-hidden="true">
              {insightTrendBars.length ? (
                insightTrendBars.map((bar) => (
                  <div key={bar.label} className="trend-bar-wrap">
                    <div className="trend-bar" style={{ height: `${bar.height}px` }} />
                    <span>{bar.label}</span>
                  </div>
                ))
              ) : (
                <p className="insight-empty">No traction trend yet.</p>
              )}
            </div>
          </article>

          <article className="insight-card">
            <p className="insight-label">Results snapshot</p>
            <h3 className="insight-value">{postInsights ? formatCompactNumber(postInsights.projectedClicks) : '--'}</h3>
            <p className="insight-subtle">Projected clicks for the current post based on live queue volume.</p>
            <div className="metric-pair-grid">
              <div className="metric-pair">
                <span>Scheduled posts</span>
                <strong>{formatCompactNumber(postInsights?.scheduledPosts ?? 0)}</strong>
              </div>
              <div className="metric-pair">
                <span>CRM contacts</span>
                <strong>{formatCompactNumber(postInsights?.crmContacts ?? 0)}</strong>
              </div>
              <div className="metric-pair">
                <span>Conversions</span>
                <strong>{formatCompactNumber(postInsights?.projectedConversions ?? 0)}</strong>
              </div>
              <div className="metric-pair">
                <span>Best slot</span>
                <strong>{postInsights?.recommendedSlot ?? '--'}</strong>
              </div>
            </div>
          </article>

          <article className="insight-card insight-card-roi">
            <p className="insight-label">Projected ROI</p>
            <h3 className="insight-value">{postInsights ? formatCurrency(postInsights.projectedRevenue) : '--'}</h3>
            <p className="insight-subtle">Forecasted revenue contribution from the current post creative.</p>
            <div className="insight-pill-row">
              <span className="insight-pill positive">
                {postInsights
                  ? `${postInsights.roiLift >= 0 ? '+' : ''}${Math.round(postInsights.roiLift * 100)}% uplift`
                  : '--'}
              </span>
              <span className="insight-pill">
                {postInsights ? `${Math.round(postInsights.confidence * 100)}% confidence` : '--'}
              </span>
            </div>
          </article>

          <article className="insight-card insight-card-post">
            <p className="insight-label">Current post</p>
            <h3 className="insight-title">{selectedSlide.headline}</h3>
            <p className="insight-copy-card">{selectedSlide.subheadline}</p>
            <div className="insight-post-meta">
              <span>{selectedSlide.cta}</span>
              <span>{publishMode === 'draft' ? 'Draft mode' : 'Publish now'}</span>
            </div>
          </article>
        </div>
      </section>

      {activeMode === 'creatives' ? (
        <>
          {creativeView === 'library' ? (
            <section className="creative-library-shell">
              <div className="creative-library-header">
                <div>
                  <h2>Content Library</h2>
                  <div className="creative-library-tabs" role="tablist" aria-label="Library asset type">
                    {(['all', 'image', 'video', 'carousel'] as CreativeLibraryTab[]).map((tab) => (
                      <button
                        key={tab}
                        type="button"
                        className={libraryTab === tab ? 'library-tab active' : 'library-tab'}
                        onClick={() => setLibraryTab(tab)}
                      >
                        {tab === 'all' ? 'All' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="creative-library-actions">
                  <button type="button" className="library-create-btn" onClick={openBlankCreativeEditor}>
                    Create New
                  </button>
                  <label className="creative-library-search">
                    <span className="sr-only">Search in your posts</span>
                    <input
                      value={librarySearch}
                      onChange={(event) => setLibrarySearch(event.target.value)}
                      placeholder="Search in your Posts"
                    />
                  </label>
                  <button type="button" className="ghost-btn">
                    Filter
                  </button>
                </div>
              </div>

              <div className="creative-library-grid">
                {libraryItems.map((item) => (
                  <article key={item.id} className="library-card">
                    <button
                      type="button"
                      className="library-card-preview"
                      onClick={() => setSelectedLibraryId(item.id)}
                    >
                      {renderCreativeArtboard(item, { compact: true })}
                    </button>
                    <div className="library-card-actions">
                      <button type="button" className="library-card-action ghost-btn">
                        Download
                      </button>
                      <button
                        type="button"
                        className="library-card-action ghost-btn"
                        onClick={() => {
                          setSelectedLibraryId(item.id);
                        }}
                      >
                        Publish
                      </button>
                      <button type="button" className="library-card-action ghost-btn">
                        Share Link
                      </button>
                      <button type="button" className="library-card-action ghost-btn">
                        More
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : (
            <section className="editor-workspace editor-workspace-modern">
              <aside className="editor-sidebar-rail">
                <button
                  type="button"
                  className={editorSidebarView === 'insert' ? 'editor-sidebar-btn active' : 'editor-sidebar-btn'}
                  onClick={() => setEditorSidebarView('insert')}
                >
                  <span className="editor-sidebar-icon">＋</span>
                  <span>Insert</span>
                </button>
                <button
                  type="button"
                  className={editorSidebarView === 'layers' ? 'editor-sidebar-btn active' : 'editor-sidebar-btn'}
                  onClick={() => {
                    setEditorSidebarView('layers');
                    setInsertPanelView('root');
                  }}
                >
                  <span className="editor-sidebar-icon">▤</span>
                  <span>Layers</span>
                </button>
                <button
                  type="button"
                  className={editorSidebarView === 'history' ? 'editor-sidebar-btn active' : 'editor-sidebar-btn'}
                  onClick={() => {
                    setEditorSidebarView('history');
                    setInsertPanelView('root');
                  }}
                >
                  <span className="editor-sidebar-icon">↺</span>
                  <span>History</span>
                </button>
              </aside>

              <aside className="editor-insert-panel">
                <div className="editor-insert-head">
                  {editorSidebarView === 'insert' && insertPanelView === 'text' ? (
                    <div className="insert-subpanel-head">
                      <button type="button" className="insert-back-btn" onClick={() => setInsertPanelView('root')}>
                        ←
                      </button>
                      <h3>Text</h3>
                    </div>
                  ) : (
                    <h3>
                      {editorSidebarView === 'insert' && 'Insert'}
                      {editorSidebarView === 'layers' && 'Layers'}
                      {editorSidebarView === 'history' && 'History'}
                    </h3>
                  )}
                </div>
                {editorSidebarView === 'insert' && insertPanelView === 'root' ? (
                  <>
                    <label className="editor-insert-search">
                      <span className="sr-only">Search insert options</span>
                      <input
                        value={insertSearch}
                        onChange={(event) => setInsertSearch(event.target.value)}
                        placeholder="Search"
                      />
                    </label>
                    <div className="editor-insert-groups">
                      {insertOptions
                        .filter((item) => item.toLowerCase().includes(insertSearch.trim().toLowerCase()))
                        .map((item) => (
                          <button
                            key={item}
                            type="button"
                            className="insert-item-btn"
                            onClick={() => handleInsertAction(item)}
                          >
                            <span className="insert-item-icon">◌</span>
                            <span>{item}</span>
                          </button>
                        ))}
                    </div>
                  </>
                ) : null}
                {editorSidebarView === 'insert' && insertPanelView === 'text' ? (
                  <div className="text-insert-shell">
                    <div className="text-quick-actions">
                      <button
                        type="button"
                        className="text-quick-btn text-quick-btn-primary"
                        onClick={() => applyTextQuickAction('header')}
                      >
                        Create Header
                      </button>
                      <button
                        type="button"
                        className="text-quick-btn"
                        onClick={() => applyTextQuickAction('subheader')}
                      >
                        Create sub header
                      </button>
                      <button type="button" className="text-quick-btn" onClick={() => applyTextQuickAction('body')}>
                        Create body text
                      </button>
                    </div>
                    <div className="text-style-grid">
                      {TEXT_STYLE_PRESETS.map((preset, index) => (
                        <button
                          key={preset}
                          type="button"
                          className={`text-style-chip ${TEXT_STYLE_VARIANTS[index % TEXT_STYLE_VARIANTS.length]}`}
                          onClick={() => applyTextStylePreset(preset)}
                        >
                          <span className="text-style-line text-style-line-primary">
                            {preset.split(' ').slice(0, 2).join(' ')}
                          </span>
                          {preset.split(' ').length > 2 ? (
                            <span className="text-style-line text-style-line-secondary">
                              {preset.split(' ').slice(2).join(' ')}
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
                {editorSidebarView === 'layers' ? (
                  <div className="editor-stack-list">
                    {editorLayers.map((layer) => (
                      <div
                        key={layer.id}
                        className={selectedEditorLayer === layer.id ? 'editor-stack-item active' : 'editor-stack-item'}
                      >
                        <button
                          type="button"
                          className="editor-stack-main"
                          onClick={() => {
                            setSelectedEditorLayer(layer.id);
                            recordEditorAction(`Selected ${layer.label}`);
                          }}
                        >
                          {layer.label}
                        </button>
                        <button
                          type="button"
                          className={layer.visible ? 'layer-visibility-pill visible' : 'layer-visibility-pill hidden'}
                          onClick={(event) => {
                            event.stopPropagation();
                            setLayerVisibility(layer.id, !layer.visible);
                          }}
                        >
                          {layer.visible ? 'Visible' : 'Hidden'}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : null}
                {editorSidebarView === 'history' ? (
                  <div className="editor-stack-list">
                    {editorHistory.map((item) => (
                      <div key={item} className="editor-stack-item history-item">
                        {item}
                      </div>
                    ))}
                  </div>
                ) : null}
              </aside>

              <section className="canvas-zone canvas-zone-modern">
                <div className="editor-canvas-topbar">
                  <button type="button" className="ghost-btn" onClick={() => setCreativeView('library')}>
                    Back to Library
                  </button>
                  <div className="editor-zoom-cluster">
                    <button type="button" className="ghost-btn">
                      －
                    </button>
                    <input type="range" min="50" max="150" value="90" readOnly />
                    <button type="button" className="ghost-btn">
                      ＋
                    </button>
                  </div>
                </div>

                <div className="canvas-stage">
                  {renderCreativeArtboard(
                    {
                      title: selectedSlide.headline,
                      subtitle: selectedSlide.subheadline,
                      brand: editorBrandLabel,
                      cta: selectedSlide.cta,
                      badge: editorBadge,
                    },
                    { editable: true }
                  )}
                </div>
              </section>

              <aside className="property-panel property-panel-modern">
                <div className="editor-properties-head">
                  <div>
                    <strong>4.0 Edits</strong>
                  </div>
                  <span>⌃</span>
                </div>

                <div className="editor-primary-actions">
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => {
                      const nextHeadline =
                        selectedEditorLayer === 'subtitle'
                          ? selectedSlide.subheadline
                          : `${selectedSlide.headline} PRO`;
                      if (selectedEditorLayer === 'subtitle') {
                        updateSlideText('subheadline', `${nextHeadline}`);
                        recordEditorAction('Adjusted subtitle');
                      } else if (selectedEditorLayer === 'cta') {
                        updateSlideText('cta', selectedSlide.cta === 'Shop Now' ? 'Claim Offer' : 'Shop Now');
                        recordEditorAction('Adjusted CTA');
                      } else {
                        updateSlideText('headline', `${nextHeadline}`);
                        recordEditorAction('Adjusted headline');
                      }
                    }}
                  >
                    Change Text
                  </button>
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => {
                      setLayerVisibility('background', true);
                      setEditorBadge((current) => (current === 'LIMITED' ? 'FLASH' : 'LIMITED'));
                      recordEditorAction('Changed background');
                    }}
                  >
                    Change Background
                  </button>
                </div>

                <details className="editor-accordion" open>
                  <summary>Position</summary>
                  <div className="editor-accordion-body">
                    <div className="align-row">
                      <button type="button" className="ghost-btn">
                        Left
                      </button>
                      <button type="button" className="ghost-btn">
                        Center
                      </button>
                      <button type="button" className="ghost-btn">
                        Right
                      </button>
                      <button type="button" className="ghost-btn">
                        Justify
                      </button>
                    </div>
                  </div>
                </details>

                <details className="editor-accordion" open>
                  <summary>Image</summary>
                  <div className="editor-accordion-body">
                    <label>
                      <span>Upload image</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(event) => uploadSlideImage(event.target.files?.[0])}
                      />
                    </label>
                  </div>
                </details>

                <details className="editor-accordion" open>
                  <summary>3D Transform</summary>
                  <div className="editor-accordion-body fx-grid">
                    <label className="fx-label">
                      Rotate X <span>{fx3dRotateX}°</span>
                      <input
                        type="range"
                        min="-60"
                        max="60"
                        value={fx3dRotateX}
                        onChange={(e) => {
                          setFx3dRotateX(Number(e.target.value));
                          recordEditorAction('3D Rotate X');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Rotate Y <span>{fx3dRotateY}°</span>
                      <input
                        type="range"
                        min="-60"
                        max="60"
                        value={fx3dRotateY}
                        onChange={(e) => {
                          setFx3dRotateY(Number(e.target.value));
                          recordEditorAction('3D Rotate Y');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Rotate Z <span>{fx3dRotateZ}°</span>
                      <input
                        type="range"
                        min="-180"
                        max="180"
                        value={fx3dRotateZ}
                        onChange={(e) => {
                          setFx3dRotateZ(Number(e.target.value));
                          recordEditorAction('3D Rotate Z');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Scale <span>{fx3dScale}%</span>
                      <input
                        type="range"
                        min="50"
                        max="150"
                        value={fx3dScale}
                        onChange={(e) => {
                          setFx3dScale(Number(e.target.value));
                          recordEditorAction('3D Scale');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Perspective <span>{fxPerspective}px</span>
                      <input
                        type="range"
                        min="200"
                        max="2000"
                        step="50"
                        value={fxPerspective}
                        onChange={(e) => setFxPerspective(Number(e.target.value))}
                      />
                    </label>
                    <button
                      type="button"
                      className="fx-reset-btn"
                      onClick={() => {
                        setFx3dRotateX(0);
                        setFx3dRotateY(0);
                        setFx3dRotateZ(0);
                        setFx3dScale(100);
                        setFxPerspective(800);
                        recordEditorAction('Reset 3D');
                      }}
                    >
                      Reset 3D
                    </button>
                  </div>
                </details>

                <details className="editor-accordion" open>
                  <summary>Lighting</summary>
                  <div className="editor-accordion-body fx-grid">
                    <label className="fx-label">
                      Light Angle <span>{fxLightAngle}°</span>
                      <input
                        type="range"
                        min="0"
                        max="360"
                        value={fxLightAngle}
                        onChange={(e) => {
                          setFxLightAngle(Number(e.target.value));
                          recordEditorAction('Light angle');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Intensity <span>{fxLightIntensity}%</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={fxLightIntensity}
                        onChange={(e) => {
                          setFxLightIntensity(Number(e.target.value));
                          recordEditorAction('Light intensity');
                        }}
                      />
                    </label>
                    <label className="fx-label">
                      Brightness <span>{fxBrightness}%</span>
                      <input
                        type="range"
                        min="50"
                        max="200"
                        value={fxBrightness}
                        onChange={(e) => setFxBrightness(Number(e.target.value))}
                      />
                    </label>
                    <label className="fx-label">
                      Contrast <span>{fxContrast}%</span>
                      <input
                        type="range"
                        min="50"
                        max="200"
                        value={fxContrast}
                        onChange={(e) => setFxContrast(Number(e.target.value))}
                      />
                    </label>
                    <label className="fx-label">
                      Saturation <span>{fxSaturation}%</span>
                      <input
                        type="range"
                        min="0"
                        max="200"
                        value={fxSaturation}
                        onChange={(e) => setFxSaturation(Number(e.target.value))}
                      />
                    </label>
                    <label className="fx-label">
                      Opacity <span>{fxOpacity}%</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={fxOpacity}
                        onChange={(e) => setFxOpacity(Number(e.target.value))}
                      />
                    </label>
                    <label className="fx-label">
                      Blur <span>{fxBlur}px</span>
                      <input
                        type="range"
                        min="0"
                        max="20"
                        value={fxBlur}
                        onChange={(e) => setFxBlur(Number(e.target.value))}
                      />
                    </label>
                  </div>
                </details>

                <details className="editor-accordion" open>
                  <summary>Shadow</summary>
                  <div className="editor-accordion-body fx-grid">
                    <div className="editor-toggle-row">
                      <span>Drop shadow</span>
                      <input
                        type="checkbox"
                        checked={fxShadowEnabled}
                        onChange={(e) => {
                          setFxShadowEnabled(e.target.checked);
                          recordEditorAction('Toggle shadow');
                        }}
                      />
                    </div>
                    {fxShadowEnabled && (
                      <>
                        <label className="fx-label">
                          Offset X <span>{fxShadowX}px</span>
                          <input
                            type="range"
                            min="-60"
                            max="60"
                            value={fxShadowX}
                            onChange={(e) => setFxShadowX(Number(e.target.value))}
                          />
                        </label>
                        <label className="fx-label">
                          Offset Y <span>{fxShadowY}px</span>
                          <input
                            type="range"
                            min="-60"
                            max="60"
                            value={fxShadowY}
                            onChange={(e) => setFxShadowY(Number(e.target.value))}
                          />
                        </label>
                        <label className="fx-label">
                          Blur <span>{fxShadowBlur}px</span>
                          <input
                            type="range"
                            min="0"
                            max="120"
                            value={fxShadowBlur}
                            onChange={(e) => setFxShadowBlur(Number(e.target.value))}
                          />
                        </label>
                        <label className="fx-label">
                          Spread <span>{fxShadowSpread}px</span>
                          <input
                            type="range"
                            min="-30"
                            max="60"
                            value={fxShadowSpread}
                            onChange={(e) => setFxShadowSpread(Number(e.target.value))}
                          />
                        </label>
                        <label className="fx-label">
                          Opacity <span>{fxShadowOpacity}%</span>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={fxShadowOpacity}
                            onChange={(e) => setFxShadowOpacity(Number(e.target.value))}
                          />
                        </label>
                        <div className="fx-color-row">
                          <span>Color</span>
                          <input
                            type="color"
                            value={fxShadowColor}
                            onChange={(e) => setFxShadowColor(e.target.value)}
                            className="fx-color-input"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </details>

                <details className="editor-accordion">
                  <summary>Glow</summary>
                  <div className="editor-accordion-body fx-grid">
                    <label className="fx-label">
                      Glow Size <span>{fxGlow}px</span>
                      <input
                        type="range"
                        min="0"
                        max="80"
                        value={fxGlow}
                        onChange={(e) => {
                          setFxGlow(Number(e.target.value));
                          recordEditorAction('Glow');
                        }}
                      />
                    </label>
                    <div className="fx-color-row">
                      <span>Glow Color</span>
                      <input
                        type="color"
                        value={fxGlowColor}
                        onChange={(e) => setFxGlowColor(e.target.value)}
                        className="fx-color-input"
                      />
                    </div>
                  </div>
                </details>

                <details className="editor-accordion">
                  <summary>Background</summary>
                  <div className="editor-accordion-body fx-grid">
                    <div className="editor-toggle-row">
                      <span>Background overlay</span>
                      <input
                        type="checkbox"
                        checked={fxBgOverlay}
                        onChange={(e) => {
                          setFxBgOverlay(e.target.checked);
                          recordEditorAction('Background overlay');
                        }}
                      />
                    </div>
                    {fxBgOverlay && (
                      <>
                        <div className="fx-color-row">
                          <span>Overlay Color</span>
                          <input
                            type="color"
                            value={fxBgOverlayColor}
                            onChange={(e) => setFxBgOverlayColor(e.target.value)}
                            className="fx-color-input"
                          />
                        </div>
                        <label className="fx-label">
                          Opacity <span>{fxBgOverlayOpacity}%</span>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={fxBgOverlayOpacity}
                            onChange={(e) => setFxBgOverlayOpacity(Number(e.target.value))}
                          />
                        </label>
                      </>
                    )}
                  </div>
                </details>
              </aside>
            </section>
          )}
        </>
      ) : null}

      {selectedLibraryItem ? (
        <dialog className="fetch-modal-overlay" open aria-label="Creative preview">
          <div className="creative-preview-modal creative-preview-modal-editor">
            <div className="creative-preview-media creative-preview-media-editor">
              {renderCreativeArtboard(selectedLibraryItem)}
            </div>
            <div className="creative-preview-body creative-preview-body-editor">
              <div className="creative-preview-meta-row">
                <span className="creative-preview-pill">from your idea</span>
                <div className="creative-preview-meta-actions">
                  <span className="creative-preview-credits">15 credits used</span>
                  <button type="button" className="modal-close" onClick={() => setSelectedLibraryId('')}>
                    ×
                  </button>
                </div>
              </div>
              <div className="creative-preview-copy-block">
                <strong>Caption</strong>
                <p>{selectedLibraryItem.caption}</p>
              </div>
              <div className="action-row creative-preview-action-row">
                <button
                  type="button"
                  className="publish-btn"
                  onClick={() => {
                    setPublishMode('now');
                    void publishCreative();
                    setSelectedLibraryId('');
                  }}
                >
                  Publish
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => applyLibraryItemToEditor(selectedLibraryItem)}
                >
                  Edit
                </button>
                <button type="button" className="ghost-btn">
                  Download
                </button>
                <button type="button" className="ghost-btn">
                  •••
                </button>
              </div>
            </div>
          </div>
        </dialog>
      ) : null}

      {activeMode === 'captions' ? (
        <section className="captions-shell" aria-label="Caption generator">
          <div className="captions-style-shell">
            <div className="captions-style-header">
              <p className="captions-style-kicker">Style Selection</p>
              <h3>Choose the perfect style for your UGC 2.0 video.</h3>
              <p>
                Pick a Template. Select a layout style that matches your content and click a pre-built preview template
                to apply it instantly.
              </p>
            </div>

            <div className="captions-style-categories" aria-label="UGC style categories">
              {UGC_STYLE_CATEGORIES.map((category) => (
                <button
                  key={category.id}
                  type="button"
                  className={ugcStyleCategoryId === category.id ? 'ugc-style-chip active' : 'ugc-style-chip'}
                  onClick={() => selectUgcStyleCategory(category.id)}
                  title={category.description}
                >
                  {category.label}
                </button>
              ))}
              <button type="button" className="ugc-style-chip explore-chip">
                Click to explore more categories
              </button>
            </div>

            <div className="ugc-preview-head">
              <strong>Pre-built Preview Templates</strong>
              <span>Browse professionally designed, ready-to-use preview templates.</span>
              {ugcTemplateSyncError ? (
                <span className="captions-sync-error">Sync error: {ugcTemplateSyncError}</span>
              ) : null}
            </div>

            <div className="ugc-preview-grid">
              {visibleUgcPreviewTemplates.map((template) => (
                <article
                  key={template.id}
                  className={ugcPreviewTemplateId === template.id ? 'ugc-preview-card active' : 'ugc-preview-card'}
                >
                  <div className="ugc-preview-meta">
                    <span>{template.platform}</span>
                    <span>{template.aspectRatio}</span>
                  </div>
                  <strong>{template.title}</strong>
                  <p>{template.description}</p>
                  <div className="ugc-preview-footer">
                    <span>{template.scriptStyle}</span>
                    <button
                      type="button"
                      className="captions-preset-btn"
                      onClick={() => applyUgcPreviewTemplate(template.id)}
                    >
                      Use template
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="captions-topbar">
            <label className="captions-control-label">
              Select Caption Tone
              <select className="captions-select" value={captionTone} onChange={(e) => setCaptionTone(e.target.value)}>
                {['Witty', 'Professional', 'Casual', 'Bold', 'Funny', 'Inspirational'].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Select Caption Length
              <select
                className="captions-select"
                value={captionLength}
                onChange={(e) => setCaptionLength(e.target.value)}
              >
                {['Small', 'Medium', 'Large'].map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              UGC Pack
              <select
                className="captions-select"
                value={captionPackId}
                onChange={(e) => setCaptionPackId(e.target.value)}
              >
                {UGC_CAPTION_PACKS.map((pack) => (
                  <option key={pack.id} value={pack.id}>
                    {pack.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Platform
              <select
                className="captions-select"
                value={captionPlatform}
                onChange={(e) => setCaptionPlatform(e.target.value)}
              >
                {UGC_PLATFORM_LABEL.map((platform) => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Script Style
              <select
                className="captions-select"
                value={videoScriptStyle}
                onChange={(e) => setVideoScriptStyle(e.target.value as (typeof UGC_SCRIPT_STYLES)[number])}
              >
                {UGC_SCRIPT_STYLES.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Aspect Ratio (Canvas)
              <select
                className="captions-select"
                value={videoCanvasAspectRatio}
                onChange={(e) => setVideoCanvasAspectRatio(e.target.value as (typeof UGC_CANVAS_RATIOS)[number] | '')}
              >
                <option value="">Select a canvas size to proceed</option>
                {UGC_CANVAS_RATIOS.map((ratio) => (
                  <option key={ratio} value={ratio}>
                    {ratio}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label captions-toggle-label">
              <span>Auto adjust by platform</span>
              <input
                type="checkbox"
                checked={videoAutoAdjustPlatforms}
                onChange={(e) => setVideoAutoAdjustPlatforms(e.target.checked)}
              />
            </label>
            <label className="captions-control-label">
              Background Media
              <select
                className="captions-select"
                value={videoBackgroundMedia}
                onChange={(e) => setVideoBackgroundMedia(e.target.value as (typeof UGC_BG_MEDIA_SOURCES)[number])}
              >
                {UGC_BG_MEDIA_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label captions-toggle-label">
              <span>Auto subtitles</span>
              <input
                type="checkbox"
                checked={videoSubtitlesAuto}
                onChange={(e) => setVideoSubtitlesAuto(e.target.checked)}
              />
            </label>
            <label className="captions-control-label">
              Subtitle language
              <select
                className="captions-select"
                value={videoSubtitlesLanguage}
                onChange={(e) => setVideoSubtitlesLanguage(e.target.value as (typeof UGC_SUBTITLE_LANGUAGES)[number])}
                disabled={!videoSubtitlesAuto}
              >
                {UGC_SUBTITLE_LANGUAGES.map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="captions-preset-row" aria-label="Subtitle toggle actions">
              <legend className="captions-sr-only">Subtitle toggle actions</legend>
              <button type="button" className="captions-preset-btn" onClick={() => setVideoSubtitlesAuto(false)}>
                Subtitles Off
              </button>
              <button type="button" className="captions-preset-btn" onClick={() => setVideoSubtitlesAuto(true)}>
                Subtitles On
              </button>
            </fieldset>
            <div className="captions-pack-description">
              Subtitles: Add subtitles automatically, available in all major languages worldwide for maximum
              accessibility and global reach.
            </div>
            <label className="captions-control-label">
              Objective
              <select
                className="captions-select"
                value={captionObjective}
                onChange={(e) => setCaptionObjective(e.target.value)}
              >
                {UGC_OBJECTIVES.map((objective) => (
                  <option key={objective} value={objective}>
                    {objective}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Hook Style
              <select
                className="captions-select"
                value={captionHookStyle}
                onChange={(e) => setCaptionHookStyle(e.target.value)}
              >
                {UGC_HOOK_STYLES.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              CTA Strength
              <select
                className="captions-select"
                value={captionCtaStrength}
                onChange={(e) => setCaptionCtaStrength(e.target.value)}
              >
                {['Soft', 'Balanced', 'Hard'].map((strength) => (
                  <option key={strength} value={strength}>
                    {strength}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Emoji Density
              <select
                className="captions-select"
                value={captionEmojiDensity}
                onChange={(e) => setCaptionEmojiDensity(e.target.value)}
              >
                {['None', 'Low', 'High'].map((density) => (
                  <option key={density} value={density}>
                    {density}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label">
              Variants
              <select
                className="captions-select"
                value={captionVariantCount}
                onChange={(e) => setCaptionVariantCount(e.target.value)}
              >
                {['1', '2', '3', '4', '5', '6'].map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </label>
            <label className="captions-control-label captions-toggle-label">
              <span>Auto hashtags</span>
              <input
                type="checkbox"
                checked={captionAutoHashtags}
                onChange={(e) => setCaptionAutoHashtags(e.target.checked)}
              />
            </label>
            <div className="captions-pack-description">{selectedCaptionPack.description}</div>
            <fieldset className="captions-preset-row" aria-label="Quick caption presets">
              <legend className="captions-sr-only">Quick caption presets</legend>
              <button
                type="button"
                className="captions-preset-btn"
                onClick={() => setCaptionPackId('ugc-social-short')}
              >
                Social
              </button>
              <button type="button" className="captions-preset-btn" onClick={() => setCaptionPackId('ugc-ad-punch')}>
                Ad
              </button>
              <button
                type="button"
                className="captions-preset-btn"
                onClick={() => setCaptionPackId('ugc-premium-brand')}
              >
                Premium
              </button>
            </fieldset>
            <div className="captions-platform-preset-row" aria-label="Platform preset bundles">
              {UGC_PLATFORM_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className="captions-preset-btn captions-preset-btn-platform"
                  onClick={() => applyUgcPlatformPreset(preset.id)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="captions-generate-btn"
              disabled={isGeneratingCaptions || !videoCanvasAspectRatio}
              onClick={() => {
                if (!videoCanvasAspectRatio) return;
                void generateCaptionVariants(1);
              }}
            >
              {isGeneratingCaptions ? 'Generating...' : 'Generate More'}
            </button>
            <button
              type="button"
              className="captions-generate-btn captions-generate-btn-strong"
              disabled={isGeneratingCaptions || !videoCanvasAspectRatio}
              onClick={() => {
                if (!videoCanvasAspectRatio) return;
                void generateCaptionVariants(2);
              }}
            >
              {isGeneratingCaptions ? 'Generating...' : 'Generate Advanced Batch'}
            </button>
            <div className="captions-video-config-note">{captionsVideoConfigNote}</div>
          </div>

          <div className="captions-list">
            {captions.map((caption) => (
              <div
                key={caption.id}
                className={selectedCaptionId === caption.id ? 'captions-item selected' : 'captions-item'}
              >
                <button
                  type="button"
                  className="captions-check"
                  aria-label="Select caption"
                  onClick={() => setSelectedCaptionId(caption.id)}
                >
                  {selectedCaptionId === caption.id ? '\u2713' : ''}
                </button>
                <div className="captions-textarea-wrap">
                  <textarea
                    className="captions-textarea"
                    value={caption.text}
                    rows={caption.text.split('\n').length + 2}
                    onChange={(e) => {
                      const val = e.target.value;
                      setCaptions((current) => current.map((c) => (c.id === caption.id ? { ...c, text: val } : c)));
                    }}
                  />
                  <div className="captions-footer">
                    <span className="captions-char-count">{caption.text.length} Characters</span>
                    <button type="button" className="captions-emoji-btn" title="Add emoji">
                      \uD83D\uDE42
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {activeMode === 'hashtags' ? (
        <section className="hashtags-shell" aria-label="Hashtag generator">
          <div className="hashtags-topbar">
            <div className="hashtags-by-group">
              <span className="hashtags-group-label">Hashtags by</span>
              {(['caption', 'creative', 'keyword'] as HashtagsBy[]).map((by) => (
                <label key={by} className="hashtags-radio-label">
                  <input
                    type="radio"
                    name="hashtagsBy"
                    value={by}
                    checked={hashtagsBy === by}
                    onChange={() => setHashtagsBy(by)}
                  />
                  {by.charAt(0).toUpperCase() + by.slice(1)}
                </label>
              ))}
            </div>

            <div className="hashtags-sort-group">
              <span className="hashtags-group-label">Sort by</span>
              {(['relevancy', 'reach'] as HashtagsSortBy[]).map((sort) => (
                <label key={sort} className="hashtags-radio-label">
                  <input
                    type="radio"
                    name="hashtagsSortBy"
                    value={sort}
                    checked={hashtagsSortBy === sort}
                    onChange={() => setHashtagsSortBy(sort)}
                  />
                  {sort.charAt(0).toUpperCase() + sort.slice(1)}
                </label>
              ))}
            </div>

            <div className="hashtags-reload-group">
              <button type="button" className="hashtags-reload-btn" onClick={() => setAddedHashtags([])}>
                \u21BB Reload Hashtags
              </button>
              <span className="hashtags-added-count">{addedHashtags.length} added</span>
            </div>
          </div>

          <div className="hashtags-body">
            <div className="hashtags-main">
              {hashtagsBy === 'keyword' ? (
                <div className="hashtags-keyword-row">
                  <input
                    type="text"
                    className="hashtags-keyword-input"
                    placeholder="Enter keywords or phrases. Eg. Herbal Medicine, Mountaineering"
                    value={hashtagKeyword}
                    onChange={(e) => setHashtagKeyword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="hashtags-generate-btn"
                    disabled={isGeneratingHashtags || !hashtagKeyword.trim()}
                    onClick={() => void generateKeywordHashtags()}
                  >
                    {isGeneratingHashtags ? 'Generating...' : 'Generate Hashtags'}
                  </button>
                </div>
              ) : null}

              <div className="hashtags-chips-grid">
                {hashtagList.map((item) => {
                  const isAdded = addedHashtags.includes(item.tag);
                  return (
                    <button
                      key={item.tag}
                      type="button"
                      className={isAdded ? 'hashtag-chip added' : 'hashtag-chip'}
                      onClick={() => {
                        setAddedHashtags((current) =>
                          isAdded ? current.filter((t) => t !== item.tag) : [...current, item.tag]
                        );
                        if (!isAdded) {
                          setHashtagEditText((current) => (current ? `${current} ${item.tag}` : item.tag));
                        }
                      }}
                    >
                      {item.tag} <span className="hashtag-count">{item.count}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="hashtags-edit-panel">
              <span className="hashtags-edit-label">Edit</span>
              <textarea
                className="hashtags-edit-textarea"
                value={hashtagEditText}
                onChange={(e) => setHashtagEditText(e.target.value)}
                placeholder="Selected hashtags appear here\u2026"
              />
              <button type="button" className="captions-emoji-btn" title="Add emoji">
                \uD83D\uDE42
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {activeMode === 'suggestions' ? (
        <section className="suggestions-shell" aria-label="Post suggestions">
          <div className="suggestions-layout">
            <div className="suggestions-controls">
              <label className="captions-control-label">
                Topic
                <input
                  className="captions-select"
                  value={suggestionTopic}
                  onChange={(event) => setSuggestionTopic(event.target.value)}
                  placeholder="Longform idea, webinar, podcast, or launch theme"
                />
              </label>
              <label className="captions-control-label">
                Goal
                <select
                  className="captions-select"
                  value={suggestionGoal}
                  onChange={(event) => setSuggestionGoal(event.target.value)}
                >
                  <option value="engagement">Engagement</option>
                  <option value="awareness">Awareness</option>
                  <option value="conversion">Conversion</option>
                  <option value="community">Community</option>
                </select>
              </label>
              <label className="captions-control-label">
                Style
                <select
                  className="captions-select"
                  value={suggestionStyle}
                  onChange={(event) => setSuggestionStyle(event.target.value)}
                >
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                  <option value="witty">Witty</option>
                  <option value="informative">Informative</option>
                </select>
              </label>
              <label className="captions-control-label">
                Audience
                <input
                  className="captions-select"
                  value={suggestionAudience}
                  onChange={(event) => setSuggestionAudience(event.target.value)}
                />
              </label>
              <div className="suggestions-platforms" role="group" aria-label="Suggestion platforms">
                {SUGGESTION_PLATFORM_OPTIONS.map((platform) => (
                  <button
                    key={platform}
                    type="button"
                    className={suggestionPlatforms.includes(platform) ? 'hashtag-chip added' : 'hashtag-chip'}
                    onClick={() => toggleSuggestionPlatform(platform)}
                  >
                    {platform}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="captions-generate-btn captions-generate-btn-strong"
                disabled={isGeneratingSuggestions || suggestionPlatforms.length === 0}
                onClick={() => void generatePostSuggestions()}
              >
                {isGeneratingSuggestions ? 'Generating...' : 'Generate Suggestions'}
              </button>
              {suggestionsError ? <p className="suggestions-placeholder">{suggestionsError}</p> : null}
              {suggestionsActionMessage ? <p className="suggestions-success">{suggestionsActionMessage}</p> : null}
            </div>
            <div className="suggestions-results">
              {suggestions.length === 0 ? (
                <p className="suggestions-placeholder">
                  Generate AI suggestions to get publish-ready clip captions and hashtag packs.
                </p>
              ) : (
                suggestions.map((item) => (
                  <article key={item.id} className="suggestion-card">
                    <header>
                      <p className="suggestion-platform">{item.platform}</p>
                      <p className="suggestion-score">Score {Math.round(item.score)}/100</p>
                    </header>
                    <p className="suggestion-caption">{item.caption}</p>
                    <p className="suggestion-hashtags">{item.hashtags.join(' ')}</p>
                    <div className="suggestion-actions">
                      <button
                        type="button"
                        className="captions-preset-btn"
                        onClick={() => {
                          const next = {
                            id: `caption-${Date.now()}`,
                            text: `${item.caption}\n\n${item.hashtags.join(' ')}`.trim(),
                          };
                          setCaptions((current) => [next, ...current].slice(0, 16));
                          setSelectedCaptionId(next.id);
                          setActiveMode('captions');
                        }}
                      >
                        Use in Captions
                      </button>
                      <button
                        type="button"
                        className="captions-preset-btn"
                        onClick={() => void sendSuggestionToIdeas(item)}
                      >
                        Send to Ideas
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </section>
      ) : null}

      {/* ── Timeline ───────────────────────────────────────────────────── */}
      {activeMode === 'timeline' ? (
        <section className="advanced-panel" aria-label="Timeline editor">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Advanced Timeline</h2>
            <div className="adv-panel-actions">
              <label className="fx-label adv-snap-label">
                Snap
                <input type="checkbox" checked={timelineSnap} onChange={(e) => setTimelineSnap(e.target.checked)} />
              </label>
              <label className="fx-label">
                Duration <span>{timelineDuration}f</span>
                <input
                  type="range"
                  min="60"
                  max="900"
                  step="30"
                  value={timelineDuration}
                  onChange={(e) => setTimelineDuration(Number(e.target.value))}
                />
              </label>
            </div>
          </div>

          <div className="timeline-shell">
            <div className="timeline-ruler">
              {Array.from({ length: 11 }, (_, i) => (
                <span key={i} className="timeline-ruler-mark" style={{ left: `${(i / 10) * 100}%` }}>
                  {Math.round((i / 10) * timelineDuration)}f
                </span>
              ))}
              <div className="timeline-playhead" style={{ left: `${(timelinePlayhead / timelineDuration) * 100}%` }} />
            </div>

            <div className="timeline-tracks">
              {timelineTracks.map((track) => (
                <div key={track.id} className={`timeline-track${selectedTrackId === track.id ? ' selected' : ''}`}>
                  <div className="timeline-track-header" style={{ borderLeftColor: track.color }}>
                    <button type="button" className="timeline-track-name" onClick={() => setSelectedTrackId(track.id)}>
                      {track.label}
                    </button>
                    <div className="timeline-track-controls">
                      <button
                        type="button"
                        className={`tl-ctrl-btn${track.locked ? ' active' : ''}`}
                        title="Lock track"
                        onClick={() =>
                          setTimelineTracks((ts) =>
                            ts.map((t) => (t.id === track.id ? { ...t, locked: !t.locked } : t))
                          )
                        }
                      >
                        {track.locked ? '🔒' : '🔓'}
                      </button>
                      <button
                        type="button"
                        className={`tl-ctrl-btn${track.muted ? ' active' : ''}`}
                        title="Mute track"
                        onClick={() =>
                          setTimelineTracks((ts) => ts.map((t) => (t.id === track.id ? { ...t, muted: !t.muted } : t)))
                        }
                      >
                        {track.muted ? '🔇' : '🔊'}
                      </button>
                      <button
                        type="button"
                        className={`tl-ctrl-btn${track.grouped ? ' active' : ''}`}
                        title="Group track"
                        onClick={() =>
                          setTimelineTracks((ts) =>
                            ts.map((t) => (t.id === track.id ? { ...t, grouped: !t.grouped } : t))
                          )
                        }
                      >
                        ⊞
                      </button>
                    </div>
                  </div>
                  <div className="timeline-lane">
                    <div className="timeline-clip" style={{ background: track.color, left: '2%', width: '86%' }} />
                    {keyframes
                      .filter((kf) => kf.trackId === track.id)
                      .map((kf) => (
                        <div
                          key={kf.id}
                          className="timeline-keyframe"
                          style={{ left: `${(kf.time / timelineDuration) * 100}%`, background: track.color }}
                          title={`${kf.type}: ${kf.value} @ ${kf.time}f`}
                        />
                      ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="timeline-kf-panel">
              <h4>Add Keyframe on selected track</h4>
              <div className="timeline-kf-row">
                <label className="fx-label">
                  At frame <span>{timelinePlayhead}f</span>
                  <input
                    type="range"
                    min="0"
                    max={timelineDuration}
                    value={timelinePlayhead}
                    onChange={(e) => setTimelinePlayhead(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Type
                  <select
                    className="captions-select"
                    value={selectedKfType}
                    onChange={(e) => setSelectedKfType(e.target.value as KeyframeType)}
                  >
                    <option value="opacity">Opacity</option>
                    <option value="position">Position</option>
                    <option value="scale">Scale</option>
                  </select>
                </label>
                <button
                  type="button"
                  className="captions-generate-btn"
                  onClick={() => {
                    let initialValue = 0;
                    if (selectedKfType === 'opacity' || selectedKfType === 'scale') initialValue = 100;
                    const newKf: Keyframe = {
                      id: `kf-${Date.now()}`,
                      trackId: selectedTrackId,
                      time: timelinePlayhead,
                      type: selectedKfType,
                      value: initialValue,
                    };
                    setKeyframes((ks) => [...ks, newKf]);
                  }}
                >
                  + Keyframe
                </button>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* ── Color & Grading ────────────────────────────────────────────── */}
      {activeMode === 'color' ? (
        <section className="advanced-panel" aria-label="Color grading">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Color &amp; Grading</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>LUT</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  3D LUT Preset
                  <select
                    className="captions-select"
                    value={gradeLutId}
                    onChange={(e) => setGradeLutId(e.target.value)}
                  >
                    {[
                      'none',
                      'Cinematic',
                      'Warm Sunset',
                      'Cool Teal',
                      'Desaturated Film',
                      'High Contrast',
                      'Vintage',
                      'Day for Night',
                    ].map((lut) => (
                      <option key={lut} value={lut}>
                        {lut === 'none' ? 'None' : lut}
                      </option>
                    ))}
                  </select>
                </label>
                {gradeLutId !== 'none' && (
                  <label className="fx-label">
                    LUT Strength <span>{gradeLutStrength}%</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={gradeLutStrength}
                      onChange={(e) => setGradeLutStrength(Number(e.target.value))}
                    />
                  </label>
                )}
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Exposure</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Exposure{' '}
                  <span>
                    {gradeExposure > 0 ? '+' : ''}
                    {gradeExposure}
                  </span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    value={gradeExposure}
                    onChange={(e) => setGradeExposure(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Highlights{' '}
                  <span>
                    {gradeHighlights > 0 ? '+' : ''}
                    {gradeHighlights}
                  </span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    value={gradeHighlights}
                    onChange={(e) => setGradeHighlights(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Shadows{' '}
                  <span>
                    {gradeShadows > 0 ? '+' : ''}
                    {gradeShadows}
                  </span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    value={gradeShadows}
                    onChange={(e) => setGradeShadows(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Color Balance</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Temperature{' '}
                  <span>
                    {gradeTemperature > 0 ? '+' : ''}
                    {gradeTemperature}K
                  </span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    value={gradeTemperature}
                    onChange={(e) => setGradeTemperature(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Tint{' '}
                  <span>
                    {gradeTint > 0 ? '+' : ''}
                    {gradeTint}
                  </span>
                  <input
                    type="range"
                    min="-100"
                    max="100"
                    value={gradeTint}
                    onChange={(e) => setGradeTint(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion">
              <summary>RGB Curves</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="curve-preview">
                  <svg viewBox="0 0 100 100" className="curve-svg">
                    <path
                      d={`M0,100 Q${gradeCurveR},${100 - gradeCurveR} 100,0`}
                      fill="none"
                      stroke="#ef4444"
                      strokeWidth="2"
                    />
                    <path
                      d={`M0,100 Q${gradeCurveG},${100 - gradeCurveG} 100,0`}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                    />
                    <path
                      d={`M0,100 Q${gradeCurveB},${100 - gradeCurveB} 100,0`}
                      fill="none"
                      stroke="#6366f1"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
                <label className="fx-label">
                  Red <span>{gradeCurveR}</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={gradeCurveR}
                    onChange={(e) => setGradeCurveR(Number(e.target.value))}
                    className="range-red"
                  />
                </label>
                <label className="fx-label">
                  Green <span>{gradeCurveG}</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={gradeCurveG}
                    onChange={(e) => setGradeCurveG(Number(e.target.value))}
                    className="range-green"
                  />
                </label>
                <label className="fx-label">
                  Blue <span>{gradeCurveB}</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={gradeCurveB}
                    onChange={(e) => setGradeCurveB(Number(e.target.value))}
                    className="range-blue"
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Color Wheels (Lift / Gamma / Gain)</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="color-wheels-row">
                  {[
                    ['Lift', gradeLift, setGradeLift],
                    ['Gamma', gradeGamma, setGradeGamma],
                    ['Gain', gradeGain, setGradeGain],
                  ].map(([label, val, setter]) => (
                    <div key={String(label)} className="color-wheel-item">
                      <div className="color-wheel-ring">
                        <span className="color-wheel-val">
                          {Number(val) > 0 ? '+' : ''}
                          {Number(val)}
                        </span>
                      </div>
                      <span className="color-wheel-label">{String(label)}</span>
                      <input
                        type="range"
                        min="-50"
                        max="50"
                        value={Number(val)}
                        onChange={(e) => (setter as (n: number) => void)(Number(e.target.value))}
                        className="color-wheel-range"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </div>
        </section>
      ) : null}

      {/* ── Effects & Filters ──────────────────────────────────────────── */}
      {activeMode === 'effects' ? (
        <section className="advanced-panel" aria-label="Effects and filters">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Effects &amp; Filters</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>Blur &amp; Sharpen</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Blur <span>{fxBlur}px</span>
                  <input
                    type="range"
                    min="0"
                    max="20"
                    value={fxBlur}
                    onChange={(e) => setFxBlur(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Sharpen <span>{fxSharpen}%</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={fxSharpen}
                    onChange={(e) => setFxSharpen(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Glow &amp; Vignette</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Glow <span>{fxGlow}px</span>
                  <input
                    type="range"
                    min="0"
                    max="80"
                    value={fxGlow}
                    onChange={(e) => setFxGlow(Number(e.target.value))}
                  />
                </label>
                <div className="fx-color-row">
                  <span>Glow Color</span>
                  <input
                    type="color"
                    value={fxGlowColor}
                    onChange={(e) => setFxGlowColor(e.target.value)}
                    className="fx-color-input"
                  />
                </div>
                <label className="fx-label">
                  Vignette <span>{fxVignette}%</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={fxVignette}
                    onChange={(e) => setFxVignette(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Chroma Key (Green Screen)</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="editor-toggle-row">
                  <span>Enable chroma key</span>
                  <input type="checkbox" checked={fxChromaKey} onChange={(e) => setFxChromaKey(e.target.checked)} />
                </div>
                {fxChromaKey && (
                  <>
                    <div className="fx-color-row">
                      <span>Key Color</span>
                      <input
                        type="color"
                        value={fxChromaColor}
                        onChange={(e) => setFxChromaColor(e.target.value)}
                        className="fx-color-input"
                      />
                    </div>
                    <label className="fx-label">
                      Threshold <span>{fxChromaThreshold}%</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={fxChromaThreshold}
                        onChange={(e) => setFxChromaThreshold(Number(e.target.value))}
                      />
                    </label>
                  </>
                )}
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Motion Blur</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Strength <span>{fxMotionBlur}px</span>
                  <input
                    type="range"
                    min="0"
                    max="30"
                    value={fxMotionBlur}
                    onChange={(e) => setFxMotionBlur(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Noise Reduction</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Strength <span>{fxNoiseReduction}%</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={fxNoiseReduction}
                    onChange={(e) => setFxNoiseReduction(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>
          </div>
        </section>
      ) : null}

      {/* ── Audio ──────────────────────────────────────────────────────── */}
      {activeMode === 'audio' ? (
        <section className="advanced-panel" aria-label="Audio enhancements">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Audio Enhancements</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>Master</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Volume <span>{audioMasterVolume}%</span>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={audioMasterVolume}
                    onChange={(e) => setAudioMasterVolume(Number(e.target.value))}
                  />
                </label>
                <div className="editor-toggle-row">
                  <span>Auto loudness normalization</span>
                  <input
                    type="checkbox"
                    checked={audioAutoLoudness}
                    onChange={(e) => setAudioAutoLoudness(e.target.checked)}
                  />
                </div>
                <label className="fx-label">
                  Sync offset <span>{audioSyncOffset}ms</span>
                  <input
                    type="range"
                    min="-500"
                    max="500"
                    value={audioSyncOffset}
                    onChange={(e) => setAudioSyncOffset(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Noise Reduction</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Strength <span>{audioNoiseReduction}%</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={audioNoiseReduction}
                    onChange={(e) => setAudioNoiseReduction(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Compressor</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="editor-toggle-row">
                  <span>Enable compressor</span>
                  <input
                    type="checkbox"
                    checked={audioCompressor}
                    onChange={(e) => setAudioCompressor(e.target.checked)}
                  />
                </div>
                {audioCompressor && (
                  <>
                    <label className="fx-label">
                      Threshold <span>{audioCompThreshold}dB</span>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        value={audioCompThreshold}
                        onChange={(e) => setAudioCompThreshold(Number(e.target.value))}
                      />
                    </label>
                    <label className="fx-label">
                      Ratio <span>{audioCompRatio}:1</span>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        value={audioCompRatio}
                        onChange={(e) => setAudioCompRatio(Number(e.target.value))}
                      />
                    </label>
                  </>
                )}
              </div>
            </details>

            <details className="editor-accordion">
              <summary>Limiter</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="editor-toggle-row">
                  <span>Enable limiter</span>
                  <input type="checkbox" checked={audioLimiter} onChange={(e) => setAudioLimiter(e.target.checked)} />
                </div>
                {audioLimiter && (
                  <label className="fx-label">
                    Ceiling <span>{audioLimiterCeiling}dB</span>
                    <input
                      type="range"
                      min="-12"
                      max="0"
                      step="0.5"
                      value={audioLimiterCeiling}
                      onChange={(e) => setAudioLimiterCeiling(Number(e.target.value))}
                    />
                  </label>
                )}
              </div>
            </details>
          </div>
        </section>
      ) : null}

      {/* ── Transitions ────────────────────────────────────────────────── */}
      {activeMode === 'transitions' ? (
        <section className="advanced-panel" aria-label="Advanced transitions">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Advanced Transitions</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>Transition Type</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="transition-grid">
                  {[
                    'none',
                    'Zoom In',
                    'Zoom Out',
                    'Spin CW',
                    'Spin CCW',
                    'Luma Fade',
                    'Slide Left',
                    'Slide Right',
                    'Motion Push',
                    'Whip Pan',
                    'Glitch',
                    'Cross Dissolve',
                  ].map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`transition-chip${transitionType === t ? ' active' : ''}`}
                      onClick={() => setTransitionType(t)}
                    >
                      {t === 'none' ? 'None' : t}
                    </button>
                  ))}
                </div>
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Settings</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Duration <span>{transitionDuration}ms</span>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="50"
                    value={transitionDuration}
                    onChange={(e) => setTransitionDuration(Number(e.target.value))}
                  />
                </label>
                <label className="fx-label">
                  Easing
                  <select
                    className="captions-select"
                    value={transitionEasing}
                    onChange={(e) => setTransitionEasing(e.target.value)}
                  >
                    {['ease-in-out', 'linear', 'ease-in', 'ease-out', 'spring', 'bounce'].map((e) => (
                      <option key={e} value={e}>
                        {e}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </details>
          </div>
        </section>
      ) : null}

      {/* ── Text & Motion Graphics ─────────────────────────────────────── */}
      {activeMode === 'motion' ? (
        <section className="advanced-panel" aria-label="Text and motion graphics">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Text &amp; Motion Graphics</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>Animated Titles</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="transition-grid">
                  {[
                    'none',
                    'Typewriter',
                    'Slide Up',
                    'Fade In',
                    'Scale Pop',
                    'Glitch Reveal',
                    'Word by Word',
                    'Kinetic',
                  ].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className={`transition-chip${titlePreset === preset ? ' active' : ''}`}
                      onClick={() => setTitlePreset(preset)}
                    >
                      {preset === 'none' ? 'None' : preset}
                    </button>
                  ))}
                </div>
                <label className="fx-label">
                  Title Text
                  <input
                    type="text"
                    className="captions-select"
                    value={titleText}
                    onChange={(e) => setTitleText(e.target.value)}
                    style={{ borderRadius: 10, padding: '8px 10px' }}
                  />
                </label>
                <label className="fx-label">
                  Animate In
                  <select
                    className="captions-select"
                    value={titleAnimIn}
                    onChange={(e) => setTitleAnimIn(e.target.value)}
                  >
                    {['fade', 'slide', 'scale', 'bounce', 'typewriter'].map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="fx-label">
                  Animate Out
                  <select
                    className="captions-select"
                    value={titleAnimOut}
                    onChange={(e) => setTitleAnimOut(e.target.value)}
                  >
                    {['fade', 'slide', 'scale', 'shrink'].map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="fx-label">
                  Duration <span>{titleDuration}ms</span>
                  <input
                    type="range"
                    min="500"
                    max="10000"
                    step="250"
                    value={titleDuration}
                    onChange={(e) => setTitleDuration(Number(e.target.value))}
                  />
                </label>
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Subtitles / Captions</summary>
              <div className="editor-accordion-body fx-grid">
                <label className="fx-label">
                  Export format
                  <select
                    className="captions-select"
                    value={subtitleFormat}
                    onChange={(e) => setSubtitleFormat(e.target.value as 'srt' | 'vtt')}
                  >
                    <option value="srt">SRT</option>
                    <option value="vtt">VTT</option>
                  </select>
                </label>
                <div className="subtitle-list">
                  {subtitles.map((sub) => (
                    <div key={sub.id} className="subtitle-row">
                      <span className="subtitle-time">
                        {sub.start}s – {sub.end}s
                      </span>
                      <input
                        type="text"
                        className="subtitle-input"
                        value={sub.text}
                        onChange={(e) => {
                          const val = e.target.value;
                          setSubtitles((ss) => ss.map((s) => (s.id === sub.id ? { ...s, text: val } : s)));
                        }}
                      />
                      <button
                        type="button"
                        className="fx-reset-btn"
                        onClick={() => setSubtitles((ss) => ss.filter((s) => s.id !== sub.id))}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="captions-generate-btn"
                    onClick={() => {
                      const last = subtitles[subtitles.length - 1];
                      const newStart = last ? last.end : 0;
                      setSubtitles((ss) => [
                        ...ss,
                        { id: `sub-${Date.now()}`, start: newStart, end: newStart + 4, text: 'New subtitle line' },
                      ]);
                    }}
                  >
                    + Add subtitle
                  </button>
                  <button
                    type="button"
                    className="captions-generate-btn captions-generate-btn-strong"
                    onClick={() => {
                      const content =
                        subtitleFormat === 'srt'
                          ? subtitles
                              .map((s, i) => `${i + 1}\n00:00:0${s.start},000 --> 00:00:0${s.end},000\n${s.text}`)
                              .join('\n\n')
                          : `WEBVTT\n\n${subtitles
                              .map((s) => `00:00:0${s.start}.000 --> 00:00:0${s.end}.000\n${s.text}`)
                              .join('\n\n')}`;
                      const blob = new Blob([content], { type: 'text/plain' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `subtitles.${subtitleFormat}`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Export {subtitleFormat.toUpperCase()}
                  </button>
                </div>
              </div>
            </details>
          </div>
        </section>
      ) : null}

      {/* ── Media Management ───────────────────────────────────────────── */}
      {activeMode === 'media' ? (
        <section className="advanced-panel" aria-label="Media management">
          <div className="adv-panel-head">
            <h2 className="adv-panel-title">Media Management</h2>
          </div>
          <div className="adv-panel-body">
            <details className="editor-accordion" open>
              <summary>Autosave</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="editor-toggle-row">
                  <span>Project autosave</span>
                  <input
                    type="checkbox"
                    checked={autosaveEnabled}
                    onChange={(e) => setAutosaveEnabled(e.target.checked)}
                  />
                </div>
                {autosaveEnabled && <p className="adv-info-text">Autosave is active. Project saved every 2 minutes.</p>}
              </div>
            </details>

            <details className="editor-accordion" open>
              <summary>Version History</summary>
              <div className="editor-accordion-body fx-grid">
                <div className="version-list">
                  {versionHistory.map((v) => (
                    <div key={v.id} className={`version-row${activeVersionId === v.id ? ' active' : ''}`}>
                      <div className="version-meta">
                        <strong>{v.label}</strong>
                        <span>{v.ts}</span>
                      </div>
                      <button type="button" className="fx-reset-btn" onClick={() => restoreEditorSnapshot(v)}>
                        {activeVersionId === v.id ? 'Current' : 'Restore'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
              <div className="adv-info-text">{saveStatus}</div>
            </details>
          </div>
        </section>
      ) : null}

      {activeMode === 'creatives' ? (
        <section className="schedule-shell" aria-label="Content scheduling calendar">
          <div className="schedule-topbar">
            <div className="schedule-nav">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setCalendarWeekStart((current) => addDays(current, -7))}
              >
                Prev
              </button>
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setCalendarWeekStart((current) => addDays(current, 7))}
              >
                Next
              </button>
              <button type="button" className="ghost-btn" onClick={() => setCalendarWeekStart(startOfWeek(new Date()))}>
                Today
              </button>
            </div>
            <h3>
              {weekDays[0] ? formatCalendarDate(weekDays[0], { month: 'short', day: 'numeric', year: 'numeric' }) : ''}{' '}
              -{' '}
              {weekDays[6] ? formatCalendarDate(weekDays[6], { month: 'short', day: 'numeric', year: 'numeric' }) : ''}
            </h3>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => void loadScheduledPosts()}
              disabled={isScheduleLoading}
            >
              {isScheduleLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {scheduleError ? <p className="publish-error">{scheduleError}</p> : null}

          <div className="schedule-body">
            <aside className="draft-lane">
              <h4>Post Queue</h4>
              <p>Drag a post into a day/time slot to schedule it.</p>
              <div className="draft-cards">
                {slides.map((slide, index) => (
                  <article
                    key={slide.id}
                    className="draft-card"
                    data-slide-index={index}
                    draggable
                    onDragStart={onDraftCardDragStart}
                  >
                    <strong>{slide.headline}</strong>
                    <span>{slide.subheadline}</span>
                  </article>
                ))}
              </div>
            </aside>

            <div className="calendar-wrap">
              <table className="calendar-table">
                <thead>
                  <tr className="calendar-header-row">
                    <th className="calendar-time-head">Time</th>
                    {weekDays.map((day) => (
                      <th key={day.toISOString()} className="calendar-day-head">
                        <strong>{formatCalendarDate(day, { weekday: 'short' })}</strong>
                        <span>{formatCalendarDate(day, { month: 'numeric', day: 'numeric' })}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="calendar-grid">
                  {timeSlots.map((hour) => (
                    <tr key={hour} className="calendar-row">
                      <th className="calendar-time-cell">
                        {formatCalendarDate(new Date(2000, 0, 1, hour), { hour: 'numeric' })}
                      </th>
                      {weekDays.map((day, dayIndex) => {
                        const dayKey = weekDayKeys[dayIndex] ?? toLocalDateKey(day);
                        const cellKey = `${dayKey}::${hour}`;
                        const posts = scheduledPostsByCell.get(cellKey) ?? [];
                        const isActive = activeDropCell === cellKey;

                        return (
                          <td
                            key={cellKey}
                            className={isActive ? 'calendar-drop-cell active' : 'calendar-drop-cell'}
                            onDragOver={(event) => onCellDragOver(event, cellKey)}
                            onDragLeave={() => onCellDragLeave(cellKey)}
                            onDrop={(event) => {
                              void onCellDrop(event, day, hour);
                            }}
                          >
                            {posts.map((post) => (
                              <article
                                key={post.id}
                                className="scheduled-post"
                                data-post-id={post.id}
                                draggable
                                onDragStart={onScheduledCardDragStart}
                              >
                                <strong>{post.platform.toUpperCase()}</strong>
                                <span>{post.text.slice(0, 52)}</span>
                                <button
                                  type="button"
                                  className="ghost-btn danger"
                                  data-post-id={post.id}
                                  onClick={onDeleteScheduledPostClick}
                                >
                                  Delete
                                </button>
                              </article>
                            ))}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {published && (
        <section className="publish-preview">
          <h3>Publish payload</h3>
          {publishError ? <p className="publish-error">{publishError}</p> : null}
          {publishAssetLinks.length > 0 ? (
            <div className="publish-asset-links" aria-label="Generated asset downloads">
              {publishAssetLinks.map((asset) => (
                <a key={asset.label} href={asset.href} target="_blank" rel="noreferrer" className="chip active">
                  Download {asset.label}
                </a>
              ))}
            </div>
          ) : null}
          <pre>{JSON.stringify(publishResult ?? exportPayload, null, 2)}</pre>
        </section>
      )}

      {publishHistory.length > 0 && (
        <section className="publish-history">
          <div className="publish-history-head">
            <h3>Recent Successful Publishes</h3>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => {
                if (globalThis.window && !globalThis.window.confirm('Clear all saved publish history?')) {
                  return;
                }
                setPublishHistory([]);
              }}
            >
              Clear History
            </button>
          </div>
          <div className="publish-history-list">
            {publishHistory.map((item) => (
              <article key={item.id} className="history-card">
                <p>
                  <strong>{item.publishMode === 'draft' ? 'Draft' : 'Live'}</strong> to {item.endpoint}
                </p>
                <p className="muted-line">Tenant: {item.tenantId}</p>
                <p className="muted-line">{new Date(item.publishedAt).toLocaleString()}</p>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => {
                    setPublishResult(item);
                    setPublished(true);
                    setPublishError('');
                  }}
                >
                  View Result
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      <style jsx>{`
        .editor-shell {
          max-width: 1500px;
          margin: 0 auto;
          padding: 20px 16px 48px;
          position: relative;
        }

        .editor-halo {
          position: absolute;
          width: 320px;
          height: 320px;
          border: 2px solid color-mix(in oklab, var(--brand) 70%, transparent);
          border-radius: 50%;
          pointer-events: none;
          opacity: 0.6;
        }

        .editor-halo.left {
          left: -180px;
          top: 150px;
        }

        .editor-halo.right {
          right: -160px;
          top: 8px;
          border-color: color-mix(in oklab, var(--brand-2) 70%, transparent);
        }

        .editor-topbar {
          display: grid;
          grid-template-columns: auto 1fr auto;
          gap: 10px;
          align-items: center;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 10px;
          margin-bottom: 10px;
          position: sticky;
          top: 12px;
          z-index: 30;
          backdrop-filter: blur(10px);
        }

        .mode-tabs {
          display: inline-flex;
          justify-self: center;
          border: 1px solid var(--line);
          border-radius: 10px;
          overflow: hidden;
        }

        .mode-tab {
          border: 0;
          padding: 8px 14px;
          background: transparent;
          color: var(--muted);
          font-weight: 700;
          cursor: pointer;
        }

        .mode-tab.active {
          background: color-mix(in oklab, var(--brand) 20%, transparent);
          color: var(--fg);
        }

        .editor-workspace {
          display: grid;
          grid-template-columns: 86px 360px minmax(0, 1fr) 310px;
          gap: 10px;
          align-items: start;
        }

        .creative-library-shell,
        .fetch-modal-overlay,
        .creative-preview-modal-editor,
        .editor-workspace-modern,
        .creative-artboard,
        .creative-artboard.editable,
        .creative-artboard.compact {
          --creative-surface: color-mix(in oklab, var(--bg-soft) 97%, white 3%);
        }

        .creative-library-shell {
          border: 1px solid var(--line);
          border-radius: 18px;
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
          box-shadow: 0 18px 44px rgba(0, 0, 0, 0.18);
          padding: 18px;
          display: grid;
          gap: 18px;
        }

        .creative-library-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }

        .creative-library-header h2 {
          margin: 0 0 12px;
          font-size: 28px;
        }

        .creative-library-tabs {
          display: inline-flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .library-tab,
        .editor-sidebar-btn,
        .insert-item-btn,
        .editor-stack-item {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.02);
          color: var(--muted);
          transition: 160ms ease;
        }

        .library-tab {
          border-radius: 999px;
          padding: 8px 14px;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
        }

        .library-tab.active {
          color: var(--fg);
          background: color-mix(in oklab, var(--brand) 18%, rgba(255, 255, 255, 0.03));
          border-color: color-mix(in oklab, var(--brand) 44%, var(--line));
        }

        .creative-library-actions {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
          justify-content: flex-end;
        }

        .library-create-btn {
          border: 0;
          border-radius: 12px;
          padding: 10px 16px;
          background: linear-gradient(135deg, var(--brand), color-mix(in oklab, var(--brand) 72%, white 28%));
          color: white;
          font-weight: 800;
          cursor: pointer;
          box-shadow: 0 12px 28px color-mix(in oklab, var(--brand) 30%, transparent);
        }

        .creative-library-search {
          min-width: 240px;
        }

        .creative-library-search input,
        .editor-insert-search input {
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 11px 14px;
          background: rgba(255, 255, 255, 0.03);
          color: var(--fg);
          font: inherit;
        }

        .creative-library-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 320px));
          gap: 18px;
        }

        .library-card {
          border: 1px solid var(--line);
          border-radius: 18px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          overflow: hidden;
          display: grid;
          gap: 0;
        }

        .library-card-preview {
          border: 0;
          padding: 18px;
          background: transparent;
          cursor: pointer;
          text-align: left;
        }

        .library-card-actions {
          padding: 12px;
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
          border-top: 1px solid var(--line);
        }

        .library-card-action {
          width: 100%;
          justify-content: center;
        }

        .fetch-modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(6, 10, 21, 0.72);
          display: grid;
          place-items: center;
          padding: 24px;
          z-index: 60;
          backdrop-filter: blur(10px);
        }

        .creative-preview-modal-editor {
          width: min(1060px, calc(100vw - 48px));
          border: 1px solid var(--line);
          border-radius: 24px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          box-shadow: 0 30px 80px rgba(0, 0, 0, 0.3);
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(320px, 1.15fr) minmax(320px, 0.85fr);
        }

        .creative-preview-media-editor {
          padding: 28px;
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01));
        }

        .creative-preview-body-editor {
          padding: 24px;
          display: grid;
          gap: 18px;
          align-content: start;
        }

        .creative-preview-meta-row,
        .creative-preview-meta-actions,
        .creative-preview-action-row,
        .editor-properties-head,
        .editor-primary-actions,
        .editor-canvas-topbar,
        .editor-zoom-cluster {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
        }

        .creative-preview-pill {
          border: 1px solid color-mix(in oklab, var(--brand) 40%, var(--line));
          border-radius: 999px;
          padding: 7px 12px;
          font-size: 12px;
          color: var(--fg);
          background: color-mix(in oklab, var(--brand) 12%, transparent);
        }

        .creative-preview-credits {
          color: var(--muted);
          font-size: 12px;
        }

        .creative-preview-copy-block {
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.02);
          display: grid;
          gap: 10px;
        }

        .creative-preview-copy-block strong,
        .editor-insert-head h3 {
          margin: 0;
          font-size: 14px;
        }

        .creative-preview-copy-block p {
          margin: 0;
          color: var(--muted);
          line-height: 1.7;
          font-size: 14px;
        }

        .action-row {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .modal-close {
          border: 1px solid var(--line);
          border-radius: 12px;
          width: 36px;
          height: 36px;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          font-size: 22px;
          line-height: 1;
        }

        .editor-workspace-modern {
          grid-template-columns: 88px 280px minmax(0, 1fr) 320px;
        }

        .editor-sidebar-rail,
        .editor-insert-panel,
        .canvas-zone-modern,
        .property-panel-modern {
          border: 1px solid var(--line);
          border-radius: 18px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          box-shadow: 0 18px 44px rgba(0, 0, 0, 0.18);
        }

        .editor-sidebar-rail {
          padding: 12px 10px;
          display: grid;
          gap: 10px;
        }

        .editor-sidebar-btn {
          border-radius: 14px;
          padding: 14px 8px;
          display: grid;
          gap: 8px;
          justify-items: center;
          cursor: pointer;
          font-size: 12px;
          font-weight: 700;
        }

        .editor-sidebar-btn.active,
        .insert-item-btn:hover,
        .editor-stack-item:hover {
          color: var(--fg);
          background: color-mix(in oklab, var(--brand) 14%, rgba(255, 255, 255, 0.05));
          border-color: color-mix(in oklab, var(--brand) 42%, var(--line));
        }

        .editor-stack-item.active {
          color: var(--fg);
          background: color-mix(in oklab, var(--brand) 18%, rgba(255, 255, 255, 0.05));
          border-color: color-mix(in oklab, var(--brand) 46%, var(--line));
        }

        .editor-sidebar-icon {
          width: 34px;
          height: 34px;
          border-radius: 10px;
          display: grid;
          place-items: center;
          background: rgba(255, 255, 255, 0.05);
          font-size: 18px;
        }

        .editor-insert-panel,
        .property-panel-modern {
          padding: 16px;
          display: grid;
          gap: 14px;
          align-content: start;
        }

        .insert-subpanel-head {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .insert-back-btn {
          border: 1px solid var(--line);
          border-radius: 9px;
          width: 32px;
          height: 32px;
          display: grid;
          place-items: center;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          font-size: 16px;
          line-height: 1;
        }

        .text-insert-shell {
          display: grid;
          gap: 14px;
        }

        .text-quick-actions {
          display: grid;
          gap: 8px;
        }

        .text-quick-btn {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px 12px;
          background: rgba(255, 255, 255, 0.02);
          color: var(--fg);
          text-align: left;
          cursor: pointer;
          font-weight: 600;
        }

        .text-quick-btn-primary {
          font-size: 31px;
          font-weight: 800;
          letter-spacing: -0.03em;
          line-height: 1.06;
          padding-top: 14px;
          padding-bottom: 14px;
        }

        .text-style-grid {
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 10px;
          background: rgba(255, 255, 255, 0.02);
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
          max-height: 560px;
          overflow: auto;
        }

        .text-style-chip {
          border: 1px dashed color-mix(in oklab, var(--line) 80%, white 20%);
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.03);
          color: var(--fg);
          padding: 9px 10px;
          min-height: 62px;
          text-align: left;
          cursor: pointer;
          font-weight: 700;
          line-height: 1.1;
          display: grid;
          align-content: center;
          gap: 2px;
        }

        .text-style-line {
          display: block;
        }

        .text-style-line-primary {
          font-size: 18px;
        }

        .text-style-line-secondary {
          font-size: 13px;
          opacity: 0.92;
          letter-spacing: 0.02em;
        }

        .text-style-hero {
          color: var(--text);
          background: linear-gradient(120deg, rgba(190, 24, 93, 0.24), rgba(255, 255, 255, 0.03));
        }

        .text-style-hero .text-style-line-primary {
          font-size: 22px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: -0.03em;
        }

        .text-style-condensed {
          color: var(--brand);
          text-transform: uppercase;
        }

        .text-style-condensed .text-style-line-primary {
          font-family: 'Arial Black', 'Segoe UI', sans-serif;
          font-size: 16px;
          letter-spacing: 0.05em;
        }

        .text-style-script {
          color: #fda4af;
        }

        .text-style-script .text-style-line-primary {
          font-family: 'Times New Roman', serif;
          font-style: italic;
          font-weight: 700;
          font-size: 21px;
          text-transform: none;
        }

        .text-style-stamp {
          color: #fef08a;
          background: linear-gradient(120deg, rgba(217, 119, 6, 0.2), rgba(255, 255, 255, 0.02));
        }

        .text-style-stamp .text-style-line-primary {
          font-size: 17px;
          font-weight: 900;
          letter-spacing: 0.03em;
          text-transform: uppercase;
        }

        .text-style-modern {
          color: #15803d;
        }

        .text-style-modern .text-style-line-primary {
          font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
          font-size: 18px;
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .text-style-serif {
          color: #f5d0fe;
        }

        .text-style-serif .text-style-line-primary {
          font-family: 'Georgia', serif;
          font-size: 20px;
          font-weight: 700;
        }

        .editor-insert-groups,
        .editor-stack-list {
          display: grid;
          gap: 10px;
        }

        .insert-item-btn,
        .editor-stack-item {
          border-radius: 14px;
          padding: 12px 14px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          cursor: pointer;
        }

        .editor-stack-main {
          border: 0;
          background: transparent;
          color: inherit;
          font: inherit;
          text-align: left;
          cursor: pointer;
          flex: 1 1 auto;
          padding: 0;
        }

        .layer-visibility-pill {
          border: 1px solid var(--line);
          border-radius: 999px;
          padding: 6px 10px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          background: rgba(255, 255, 255, 0.04);
          color: var(--muted);
          flex: 0 0 auto;
        }

        .layer-visibility-pill.visible {
          color: var(--fg);
          border-color: color-mix(in oklab, var(--brand) 44%, var(--line));
          background: color-mix(in oklab, var(--brand) 16%, rgba(255, 255, 255, 0.04));
        }

        .layer-visibility-pill.hidden {
          opacity: 0.82;
        }

        .insert-item-icon {
          width: 28px;
          height: 28px;
          border-radius: 9px;
          display: grid;
          place-items: center;
          background: rgba(255, 255, 255, 0.05);
          color: var(--fg);
          flex: 0 0 auto;
        }

        .canvas-zone-modern {
          padding: 18px;
          min-height: 720px;
          display: grid;
          gap: 16px;
        }

        .editor-zoom-cluster input {
          width: 180px;
        }

        .canvas-stage {
          min-height: 620px;
          border-radius: 20px;
          background: radial-gradient(circle at top, rgba(255, 255, 255, 0.08), transparent 48%), #eef0f4;
          display: grid;
          place-items: center;
          padding: 18px;
        }

        .creative-artboard {
          width: 100%;
          min-height: 100%;
          border-radius: 26px;
          background: linear-gradient(180deg, #eef0f4, #eef0f4 48%, #eef0f4);
          color: white;
          padding: 26px;
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-rows: auto auto 1fr auto;
          gap: 16px;
          box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
        }

        .creative-artboard.compact {
          min-height: 360px;
          padding: 18px;
          border-radius: 22px;
        }

        .creative-artboard.editable {
          width: min(560px, 100%);
          aspect-ratio: 1 / 1;
        }

        .creative-artboard::before,
        .creative-artboard::after {
          content: '';
          position: absolute;
          inset: auto;
          border-radius: 999px;
          filter: blur(0px);
          opacity: 0.8;
        }

        .creative-artboard::before {
          width: 220px;
          height: 220px;
          top: -80px;
          right: -40px;
          background: radial-gradient(circle, rgba(234, 179, 8, 0.25), transparent 72%);
        }

        .creative-artboard::after {
          width: 200px;
          height: 200px;
          left: -70px;
          bottom: -60px;
          background: radial-gradient(circle, rgba(96, 165, 250, 0.22), transparent 72%);
        }

        .creative-artboard-badge,
        .creative-artboard-logo,
        .creative-artboard-cta {
          justify-self: start;
          border-radius: 999px;
          padding: 7px 12px;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 0.04em;
        }

        .creative-artboard-badge {
          background: rgba(255, 255, 255, 0.08);
        }

        .creative-artboard-logo {
          background: linear-gradient(135deg, rgba(248, 250, 252, 0.16), rgba(255, 255, 255, 0.05));
          margin-top: -6px;
        }

        .creative-artboard-copy {
          position: relative;
          z-index: 1;
        }

        .creative-artboard-copy h3 {
          margin: 0;
          font-size: clamp(32px, 4vw, 56px);
          line-height: 0.96;
          text-transform: uppercase;
          letter-spacing: -0.04em;
          max-width: 8ch;
        }

        .creative-artboard-copy p {
          margin: 10px 0 0;
          max-width: 28ch;
          color: rgba(255, 255, 255, 0.72);
          font-size: 15px;
        }

        .creative-artboard-hoodies {
          display: flex;
          align-items: end;
          justify-content: center;
          gap: 10px;
          padding: 6px 0 10px;
          z-index: 1;
        }

        .hoodie {
          width: 82px;
          height: 118px;
          border-radius: 24px 24px 32px 32px;
          position: relative;
          box-shadow:
            inset 0 -10px 20px rgba(0, 0, 0, 0.18),
            0 18px 24px rgba(0, 0, 0, 0.22);
        }

        .hoodie::before {
          content: '';
          position: absolute;
          width: 46px;
          height: 34px;
          left: 50%;
          top: -12px;
          transform: translateX(-50%);
          border-radius: 999px 999px 18px 18px;
          background: inherit;
          box-shadow: inset 0 -6px 10px rgba(0, 0, 0, 0.14);
        }

        .hoodie-gold {
          background: linear-gradient(180deg, #fbbf24, #d97706);
        }

        .hoodie-green {
          background: linear-gradient(180deg, #15803d, #16a34a);
        }

        .hoodie-red {
          background: linear-gradient(180deg, #dc2626, #dc2626);
        }

        .hoodie-blue {
          background: linear-gradient(180deg, var(--brand), #6366f1);
        }

        .creative-artboard-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          z-index: 1;
        }

        .creative-artboard-brand {
          text-transform: uppercase;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.68);
          letter-spacing: 0.16em;
        }

        .creative-artboard-cta {
          background: white;
          color: #eef0f4;
        }

        .editor-primary-actions {
          justify-content: stretch;
        }

        .editor-primary-actions .ghost-btn {
          flex: 1 1 0;
        }

        .editor-accordion {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.02);
          overflow: hidden;
        }

        .editor-accordion summary {
          list-style: none;
          cursor: pointer;
          padding: 14px 16px;
          font-weight: 700;
        }

        .editor-accordion summary::-webkit-details-marker {
          display: none;
        }

        .editor-accordion-body {
          padding: 0 16px 16px;
          display: grid;
          gap: 12px;
        }

        /* FX Controls */
        .fx-grid {
          gap: 10px;
        }

        .fx-label {
          display: grid;
          grid-template-columns: 1fr auto;
          grid-template-rows: auto auto;
          gap: 4px 8px;
          font-size: 12px;
          font-weight: 600;
          color: var(--muted);
        }

        .fx-label span {
          font-size: 11px;
          color: var(--fg);
          font-variant-numeric: tabular-nums;
          justify-self: end;
        }

        .fx-label input[type='range'] {
          grid-column: 1 / -1;
          width: 100%;
          accent-color: var(--brand);
          cursor: pointer;
          height: 4px;
        }

        .fx-color-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 600;
          color: var(--muted);
        }

        .fx-color-input {
          width: 36px;
          height: 28px;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 2px;
          background: transparent;
          cursor: pointer;
        }

        .fx-reset-btn {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: transparent;
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
          padding: 6px 12px;
          cursor: pointer;
          justify-self: start;
        }

        .fx-reset-btn:hover {
          border-color: color-mix(in oklab, var(--brand) 55%, var(--line));
          color: var(--fg);
        }

        .artboard-overlay {
          position: absolute;
          inset: 0;
          border-radius: inherit;
          pointer-events: none;
          z-index: 1;
        }

        /* ── Advanced Panels ───────────────────────────────────────────── */
        .advanced-panel {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 16px;
          overflow: hidden;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
        }

        .adv-panel-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          flex-wrap: wrap;
          padding: 16px 20px 12px;
          border-bottom: 1px solid var(--line);
        }

        .adv-panel-title {
          font-size: 15px;
          font-weight: 800;
          margin: 0;
          letter-spacing: -0.01em;
        }

        .adv-panel-actions {
          display: flex;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
        }

        .adv-snap-label {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          flex-direction: row;
          font-size: 12px;
          font-weight: 700;
          color: var(--muted);
        }

        .adv-panel-body {
          padding: 4px 0 0;
        }

        .adv-info-text {
          font-size: 12px;
          color: var(--muted);
          margin: 0;
        }

        /* Timeline */
        .timeline-shell {
          display: grid;
          gap: 0;
        }

        .timeline-ruler {
          position: relative;
          height: 28px;
          background: color-mix(in oklab, var(--bg-soft) 94%, black 6%);
          border-bottom: 1px solid var(--line);
          margin: 0 0 0 140px;
        }

        .timeline-ruler-mark {
          position: absolute;
          top: 6px;
          transform: translateX(-50%);
          font-size: 10px;
          color: var(--muted);
          font-variant-numeric: tabular-nums;
          pointer-events: none;
        }

        .timeline-playhead {
          position: absolute;
          top: 0;
          bottom: 0;
          width: 2px;
          background: #ef4444;
          transform: translateX(-50%);
          z-index: 2;
        }

        .timeline-tracks {
          display: grid;
          gap: 0;
        }

        .timeline-track {
          display: grid;
          grid-template-columns: 140px minmax(0, 1fr);
          border-bottom: 1px solid var(--line);
          min-height: 44px;
        }

        .timeline-track.selected .timeline-track-header {
          background: color-mix(in oklab, var(--brand) 12%, transparent);
        }

        .timeline-track-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 6px 10px;
          border-right: 1px solid var(--line);
          border-left: 3px solid transparent;
          gap: 6px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
        }

        .timeline-track-name {
          font-size: 12px;
          font-weight: 700;
          background: transparent;
          border: 0;
          color: var(--fg);
          cursor: pointer;
          text-align: left;
          padding: 0;
        }

        .timeline-track-controls {
          display: flex;
          gap: 4px;
        }

        .tl-ctrl-btn {
          border: 0;
          background: transparent;
          font-size: 13px;
          cursor: pointer;
          padding: 2px;
          border-radius: 4px;
          opacity: 0.5;
          line-height: 1;
        }

        .tl-ctrl-btn.active,
        .tl-ctrl-btn:hover {
          opacity: 1;
          background: color-mix(in oklab, var(--brand) 14%, transparent);
        }

        .timeline-lane {
          position: relative;
          overflow: hidden;
          background: color-mix(in oklab, var(--bg-soft) 96%, transparent);
        }

        .timeline-clip {
          position: absolute;
          top: 8px;
          bottom: 8px;
          border-radius: 6px;
          opacity: 0.5;
        }

        .timeline-keyframe {
          position: absolute;
          top: 50%;
          transform: translate(-50%, -50%) rotate(45deg);
          width: 10px;
          height: 10px;
          border-radius: 2px;
          z-index: 2;
          cursor: pointer;
        }

        .timeline-kf-panel {
          padding: 14px 16px;
          border-top: 1px solid var(--line);
          display: grid;
          gap: 12px;
        }

        .timeline-kf-panel h4 {
          font-size: 12px;
          font-weight: 700;
          color: var(--muted);
          margin: 0;
        }

        .timeline-kf-row {
          display: flex;
          align-items: flex-end;
          gap: 14px;
          flex-wrap: wrap;
        }

        /* RGB Curves */
        .curve-preview {
          background: rgba(0, 0, 0, 0.3);
          border-radius: 10px;
          padding: 8px;
        }

        .curve-svg {
          width: 100%;
          height: 80px;
          display: block;
        }

        .range-red {
          accent-color: #ef4444;
        }
        .range-green {
          accent-color: #10b981;
        }
        .range-blue {
          accent-color: #6366f1;
        }

        /* Color Wheels */
        .color-wheels-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }

        .color-wheel-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }

        .color-wheel-ring {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: conic-gradient(#ef4444, #f59e0b, #10b981, #6366f1, #8b5cf6, #ef4444);
          display: grid;
          place-items: center;
          box-shadow: inset 0 0 0 6px color-mix(in oklab, var(--bg-soft) 96%, transparent);
        }

        .color-wheel-val {
          font-size: 11px;
          font-weight: 800;
          font-variant-numeric: tabular-nums;
          color: var(--fg);
          background: color-mix(in oklab, var(--bg-soft) 90%, transparent);
          border-radius: 999px;
          padding: 1px 5px;
        }

        .color-wheel-label {
          font-size: 11px;
          font-weight: 700;
          color: var(--muted);
        }

        .color-wheel-range {
          width: 100%;
        }

        /* Transitions */
        .transition-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .transition-chip {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          color: var(--fg);
          font-size: 12px;
          font-weight: 600;
          padding: 6px 12px;
          cursor: pointer;
          white-space: nowrap;
        }

        .transition-chip.active {
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 16%, transparent);
          color: var(--fg);
        }

        .transition-chip:hover {
          border-color: color-mix(in oklab, var(--brand) 50%, var(--line));
        }

        /* Subtitle editor */
        .subtitle-list {
          display: grid;
          gap: 8px;
        }

        .subtitle-row {
          display: grid;
          grid-template-columns: 90px minmax(0, 1fr) auto;
          align-items: center;
          gap: 8px;
        }

        .subtitle-time {
          font-size: 11px;
          font-weight: 700;
          color: var(--muted);
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }

        .subtitle-input {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          color: var(--fg);
          font: inherit;
          font-size: 13px;
          padding: 6px 10px;
        }

        /* Version history */
        .version-list {
          display: grid;
          gap: 8px;
        }

        .version-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 10px 12px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
        }

        .version-row.active {
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 10%, transparent);
        }

        .version-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .version-meta strong {
          font-size: 13px;
          font-weight: 700;
        }

        .version-meta span {
          font-size: 11px;
          color: var(--muted);
        }

        .editor-toggle-row {
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: center;
        }

        .publish-toolbar {
          margin: 0 0 10px;
          border: 1px solid var(--line);
          border-radius: 14px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          box-shadow: 0 12px 34px rgba(0, 0, 0, 0.17);
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) auto;
          align-items: end;
          gap: 10px;
          padding: 10px;
        }

        .publish-mode-switch {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 6px;
        }

        .publish-toolbar label {
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
        }

        .publish-toolbar input {
          margin-top: 6px;
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 10px;
          background: rgba(0, 0, 0, 0.1);
          color: var(--fg);
          padding: 9px 10px;
          font: inherit;
        }

        .tool-rail,
        .template-panel,
        .canvas-zone,
        .property-panel {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          box-shadow: 0 12px 34px rgba(0, 0, 0, 0.17);
        }

        .tool-rail {
          padding: 10px 8px;
          display: grid;
          gap: 8px;
        }

        .rail-btn {
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 8px 6px;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          display: grid;
          justify-items: center;
          gap: 4px;
          font-size: 11px;
          font-weight: 700;
          text-transform: capitalize;
        }

        .rail-btn .dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: color-mix(in oklab, var(--brand) 40%, transparent);
        }

        .rail-btn.active {
          border-color: color-mix(in oklab, var(--brand) 65%, var(--line));
          color: var(--fg);
          background: color-mix(in oklab, var(--brand) 15%, transparent);
        }

        .template-panel {
          padding: 12px;
          display: grid;
          gap: 10px;
          max-height: 78vh;
          overflow: auto;
        }

        .panel-head h2 {
          margin: 0;
          font-size: 20px;
        }

        .panel-copy {
          margin: 6px 0 0;
          color: var(--muted);
          font-size: 12px;
          line-height: 1.5;
        }

        .asset-switch,
        .panel-tabs {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 6px;
        }

        .panel-tabs {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .chip {
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 7px 8px;
          background: transparent;
          color: var(--muted);
          font-weight: 700;
          cursor: pointer;
          font-size: 12px;
        }

        .chip.active {
          color: var(--fg);
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 20%, transparent);
        }

        .search-wrap input,
        .property-group input,
        .property-group select,
        .property-group textarea {
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 10px;
          background: rgba(0, 0, 0, 0.1);
          color: var(--fg);
          padding: 9px 10px;
          font: inherit;
          margin-top: 6px;
        }

        .checkbox-row {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: var(--muted);
        }

        .library-stats-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .library-stat-chip {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 6px 10px;
          background: color-mix(in oklab, var(--brand) 16%, transparent);
          color: var(--fg);
          font-size: 11px;
          font-weight: 700;
        }

        .library-stat-chip.muted {
          background: rgba(255, 255, 255, 0.04);
          color: var(--muted);
        }

        .template-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
        }

        .template-card {
          border: 1px solid var(--line);
          border-radius: 18px;
          overflow: hidden;
          background: rgba(255, 255, 255, 0.03);
          display: grid;
          gap: 0;
        }

        .template-preview {
          min-height: 164px;
          padding: 14px;
          display: grid;
          align-content: space-between;
          color: white;
        }

        .template-preview-head {
          display: flex;
          justify-content: space-between;
          gap: 8px;
        }

        .template-preview-body {
          display: grid;
          gap: 6px;
        }

        .template-preview-body strong,
        .template-card-copy strong {
          font-size: 14px;
          line-height: 1.1;
        }

        .template-preview-body span,
        .template-card-copy span {
          font-size: 12px;
          line-height: 1.5;
        }

        .template-badge {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 5px 8px;
          background: rgba(148,163,184,0.10);
          color: white;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .template-badge.subtle {
          background: rgba(255, 255, 255, 0.16);
        }

        .template-card-body {
          padding: 12px;
          display: grid;
          gap: 12px;
        }

        .template-card-copy {
          display: grid;
          gap: 6px;
          color: var(--fg);
        }

        .template-card-copy span {
          color: var(--muted);
        }

        .template-card-actions {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        .template-card.active {
          border-color: color-mix(in oklab, var(--brand) 68%, var(--line));
          box-shadow: 0 0 0 2px color-mix(in oklab, var(--brand) 28%, transparent);
        }

        .template-customizer {
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 12px;
          display: grid;
          gap: 10px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
        }

        .template-customizer-head {
          display: flex;
          justify-content: space-between;
          align-items: start;
          gap: 10px;
        }

        .template-customizer-head h3 {
          margin: 4px 0 0;
          font-size: 16px;
        }

        .template-customizer-kicker {
          margin: 0;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--muted);
        }

        .template-customizer-tag {
          border-radius: 999px;
          padding: 6px 10px;
          background: color-mix(in oklab, var(--brand) 14%, transparent);
          color: var(--fg);
          font-size: 11px;
          font-weight: 700;
        }

        .template-customizer-row {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }

        .empty {
          grid-column: 1 / -1;
          color: var(--muted);
          margin: 0;
          font-size: 13px;
        }

        .canvas-zone {
          padding: 10px;
          display: grid;
          gap: 10px;
        }

        .canvas-toolbar {
          display: inline-flex;
          gap: 8px;
          flex-wrap: wrap;
          align-items: center;
        }

        .spacer {
          flex: 1;
        }

        .canvas-board {
          min-height: 620px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background-color: #eef5ff;
          position: relative;
          overflow: hidden;
          padding: 30px 28px;
          display: grid;
          grid-template-rows: auto auto auto auto 1fr;
          align-content: start;
        }

        .brand {
          color: #6366f1;
          font-weight: 800;
          letter-spacing: 0.01em;
          font-size: 28px;
        }

        .headline {
          margin-top: 24px;
          font-size: clamp(44px, 7vw, 86px);
          line-height: 0.92;
          font-weight: 900;
          max-width: 62%;
          text-transform: uppercase;
        }

        .subheadline {
          margin: 10px 0 0;
          color: #eef0f4;
          font-weight: 600;
          font-size: 21px;
          max-width: 58%;
        }

        .cta {
          margin-top: 14px;
          border: 0;
          background: #6366f1;
          color: white;
          border-radius: 999px;
          padding: 11px 18px;
          font-weight: 700;
          width: fit-content;
        }

        .uploaded-image,
        .image-placeholder {
          position: absolute;
          right: 20px;
          bottom: 20px;
          width: 42%;
          height: 66%;
          border-radius: 14px;
          border: 2px solid rgba(29, 78, 216, 0.2);
          object-fit: cover;
          background: rgba(255, 255, 255, 0.5);
          display: grid;
          place-items: center;
          color: #e7e9ef;
          font-weight: 700;
        }

        .coin {
          position: absolute;
          width: 74px;
          height: 74px;
          border-radius: 50%;
          background: radial-gradient(circle at 30% 25%, #fef3c7, #f59e0b 70%);
          box-shadow: 0 12px 18px rgba(245, 158, 11, 0.28);
        }

        .coin-a {
          right: 34%;
          top: 44%;
        }

        .coin-b {
          right: 9%;
          top: 27%;
        }

        .carousel-strip {
          display: flex;
          gap: 8px;
          overflow: auto;
          padding-bottom: 2px;
        }

        .slide-chip {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: transparent;
          color: var(--muted);
          font-weight: 700;
          padding: 7px 11px;
          white-space: nowrap;
          cursor: pointer;
        }

        .slide-chip.active {
          color: var(--fg);
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 20%, transparent);
        }

        .property-panel {
          padding: 12px;
          display: grid;
          gap: 10px;
          max-height: 78vh;
          overflow: auto;
        }

        .property-group {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          display: grid;
          gap: 8px;
        }

        .property-group h3 {
          margin: 0;
          font-size: 14px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .property-group label {
          font-size: 12px;
          color: var(--muted);
        }

        .align-row {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 6px;
        }

        .ghost-btn {
          border: 1px solid var(--line);
          border-radius: 10px;
          background: transparent;
          color: var(--fg);
          padding: 8px 10px;
          font-weight: 700;
          cursor: pointer;
        }

        .ghost-btn.danger {
          border-color: rgba(239, 68, 68, 0.55);
          color: #ef4444;
        }

        .publish-btn {
          border: 0;
          border-radius: 10px;
          background: linear-gradient(120deg, #6366f1, #6366f1);
          color: white;
          font-weight: 800;
          padding: 10px 16px;
          cursor: pointer;
        }

        .insights-shell {
          margin: 0 0 12px;
          border: 1px solid color-mix(in oklab, var(--brand) 25%, var(--line));
          border-radius: 18px;
          padding: 16px;
          background:
            radial-gradient(circle at top left, rgba(96, 165, 250, 0.26), transparent 34%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(236, 245, 255, 0.98));
          box-shadow: 0 20px 45px rgba(30, 41, 59, 0.12);
          color: #eef0f4;
          display: grid;
          gap: 14px;
        }

        .insights-head {
          display: flex;
          align-items: start;
          justify-content: space-between;
          gap: 12px;
        }

        .insights-eyebrow {
          margin: 0 0 6px;
          color: #6366f1;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }

        .insights-head h2 {
          margin: 0;
          font-size: 28px;
          line-height: 1.05;
        }

        .insights-copy {
          margin: 8px 0 0;
          color: #e7e9ef;
          max-width: 720px;
        }

        .insights-grid {
          display: grid;
          grid-template-columns: 1.15fr 1fr 0.9fr 0.9fr;
          gap: 12px;
        }

        .insight-card {
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.92);
          box-shadow: 0 12px 26px rgba(37, 99, 235, 0.08);
          display: grid;
          gap: 10px;
          min-height: 188px;
        }

        .insight-card-traction {
          background: linear-gradient(180deg, rgba(238, 248, 255, 0.98), rgba(255, 255, 255, 0.94));
        }

        .insight-card-roi {
          background: linear-gradient(180deg, rgba(236, 253, 245, 0.98), rgba(255, 255, 255, 0.94));
        }

        .insight-card-post {
          background: linear-gradient(180deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.94));
          align-content: start;
        }

        .insight-label {
          margin: 0;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--muted);
        }

        .insight-value,
        .insight-title {
          margin: 0;
          font-size: clamp(24px, 3vw, 38px);
          line-height: 1;
          color: #eef0f4;
        }

        .insight-title {
          font-size: 24px;
        }

        .insight-subtle,
        .insight-copy-card {
          margin: 0;
          color: #e7e9ef;
          font-size: 13px;
          line-height: 1.5;
        }

        .trend-bars {
          display: grid;
          grid-template-columns: repeat(8, minmax(0, 1fr));
          align-items: end;
          gap: 8px;
          min-height: 104px;
          margin-top: auto;
        }

        .trend-bar-wrap {
          display: grid;
          justify-items: center;
          gap: 6px;
        }

        .trend-bar {
          width: 100%;
          border-radius: 999px 999px 10px 10px;
          background: linear-gradient(180deg, #6366f1, var(--brand));
          min-height: 12px;
        }

        .trend-bar-wrap span {
          font-size: 10px;
          font-weight: 700;
          color: var(--muted);
        }

        .metric-pair-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          margin-top: auto;
        }

        .metric-pair {
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 10px;
          background: rgba(248, 250, 252, 0.92);
          display: grid;
          gap: 4px;
        }

        .metric-pair span {
          font-size: 11px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          font-weight: 700;
        }

        .metric-pair strong {
          font-size: 18px;
          color: #eef0f4;
        }

        .insight-pill-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: auto;
        }

        .insight-pill {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 8px 12px;
          background: rgba(148,163,184,0.10);
          color: #eef0f4;
          font-size: 12px;
          font-weight: 800;
        }

        .insight-pill.positive {
          background: rgba(16, 185, 129, 0.16);
          color: #047857;
        }

        .insight-post-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: auto;
        }

        .insight-post-meta span {
          border-radius: 999px;
          padding: 7px 10px;
          background: rgba(37, 99, 235, 0.08);
          color: #6366f1;
          font-size: 12px;
          font-weight: 700;
        }

        .insight-empty {
          margin: auto 0;
          grid-column: 1 / -1;
          color: var(--muted);
          font-size: 12px;
        }

        /* Topbar enhancements */
        .topbar-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .topbar-right {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .topbar-back-btn {
          border: 1px solid var(--line);
          border-radius: 10px;
          background: transparent;
          color: var(--fg);
          padding: 8px 12px;
          font-weight: 700;
          cursor: pointer;
          text-decoration: none;
          font-size: 13px;
          display: inline-flex;
          align-items: center;
        }

        .topbar-save-btn {
          font-size: 13px;
        }

        .topbar-icon-btn {
          padding: 8px 12px;
          font-size: 16px;
        }

        .topbar-send-btn {
          border: 0;
          border-radius: 10px;
          background: linear-gradient(120deg, #6366f1, #6366f1);
          color: white;
          font-weight: 800;
          padding: 9px 14px;
          cursor: pointer;
          font-size: 15px;
        }

        .topbar-send-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .topbar-promo-btn {
          border: 0;
          border-radius: 10px;
          background: linear-gradient(120deg, #1e3a8a, #6366f1);
          color: white;
          font-weight: 800;
          padding: 9px 14px;
          cursor: pointer;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .topbar-promo-timer {
          font-variant-numeric: tabular-nums;
          letter-spacing: 0.02em;
        }

        /* Captions */
        .captions-shell {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 20px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          display: grid;
          gap: 16px;
        }

        .captions-topbar {
          display: flex;
          align-items: flex-end;
          justify-content: flex-start;
          gap: 14px;
          flex-wrap: wrap;
        }

        .captions-style-shell {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 14px;
          background: color-mix(in oklab, var(--bg-soft) 97%, white 3%);
          display: grid;
          gap: 12px;
        }

        .captions-style-header {
          display: grid;
          gap: 4px;
        }

        .captions-style-header h3,
        .captions-style-header p {
          margin: 0;
        }

        .captions-style-kicker {
          margin: 0;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
          font-weight: 700;
        }

        .captions-style-categories {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .ugc-style-chip {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: color-mix(in oklab, var(--bg-soft) 95%, white 5%);
          color: var(--fg);
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 700;
          cursor: pointer;
        }

        .ugc-style-chip.active {
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 20%, transparent);
        }

        .explore-chip {
          border-style: dashed;
        }

        .ugc-preview-head {
          display: grid;
          gap: 2px;
        }

        .ugc-preview-head strong {
          font-size: 13px;
        }

        .ugc-preview-head span {
          font-size: 12px;
          color: var(--muted);
        }

        .captions-sync-error {
          color: #ef4444;
          font-weight: 700;
        }

        .ugc-preview-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr));
          gap: 10px;
        }

        .ugc-preview-card {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          display: grid;
          gap: 8px;
          background: color-mix(in oklab, var(--bg-soft) 95%, white 5%);
        }

        .ugc-preview-card.active {
          border-color: color-mix(in oklab, var(--brand) 72%, var(--line));
          background: color-mix(in oklab, var(--brand) 15%, transparent);
        }

        .ugc-preview-card p {
          margin: 0;
          font-size: 12px;
          color: var(--muted);
        }

        .ugc-preview-meta {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
          color: var(--muted);
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .ugc-preview-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          font-size: 12px;
          font-weight: 700;
        }

        .captions-control-label {
          display: flex;
          flex-direction: column;
          gap: 6px;
          font-size: 12px;
          font-weight: 700;
          color: var(--muted);
        }

        .captions-select {
          border: 1px solid var(--line);
          border-radius: 10px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          color: var(--fg);
          padding: 8px 28px 8px 10px;
          font: inherit;
          font-size: 13px;
          cursor: pointer;
        }

        .captions-generate-btn {
          border: 1px solid color-mix(in oklab, var(--brand) 70%, var(--line));
          border-radius: 10px;
          background: color-mix(in oklab, var(--brand) 16%, transparent);
          color: var(--fg);
          font-weight: 700;
          padding: 9px 18px;
          cursor: pointer;
          font-size: 13px;
          align-self: flex-end;
        }

        .captions-generate-btn-strong {
          background: linear-gradient(120deg, #0f766e, #0ea5a4);
          border-color: color-mix(in oklab, #0f766e 65%, var(--line));
          color: white;
        }

        .captions-generate-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .captions-pack-description {
          font-size: 12px;
          color: var(--muted);
          font-weight: 600;
          max-width: 320px;
          align-self: center;
        }

        .captions-video-config-note {
          font-size: 12px;
          color: var(--muted);
          font-weight: 600;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 8px 10px;
          background: color-mix(in oklab, var(--bg-soft) 97%, white 3%);
          align-self: center;
        }

        .captions-preset-row {
          display: flex;
          align-items: center;
          gap: 8px;
          align-self: flex-end;
          border: 0;
          margin: 0;
          padding: 0;
        }

        .captions-sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        .captions-preset-btn {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          color: var(--fg);
          font-size: 12px;
          font-weight: 700;
          padding: 6px 11px;
          cursor: pointer;
        }

        .captions-preset-btn:hover {
          border-color: color-mix(in oklab, var(--brand) 58%, var(--line));
          background: color-mix(in oklab, var(--brand) 16%, transparent);
        }

        .captions-platform-preset-row {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          max-width: 620px;
        }

        .captions-preset-btn-platform {
          border-style: dashed;
        }

        .captions-toggle-label {
          display: inline-flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          min-width: 120px;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 8px 10px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
        }

        .captions-list {
          display: grid;
          gap: 14px;
        }

        .captions-item {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          overflow: hidden;
        }

        .captions-item.selected {
          border-color: color-mix(in oklab, #10b981 70%, var(--line));
        }

        .captions-check {
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding: 16px 8px;
          background: transparent;
          border: 0;
          border-right: 1px solid var(--line);
          color: #10b981;
          font-size: 20px;
          font-weight: 900;
          cursor: pointer;
          min-height: 52px;
        }

        .captions-item.selected .captions-check {
          background: color-mix(in oklab, #10b981 16%, transparent);
        }

        .captions-textarea-wrap {
          display: grid;
        }

        .captions-textarea {
          width: 100%;
          border: 0;
          background: transparent;
          color: var(--fg);
          padding: 14px 14px 8px;
          font: inherit;
          font-size: 14px;
          line-height: 1.7;
          resize: none;
          min-height: 90px;
        }

        .captions-footer {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 10px;
          padding: 6px 12px 10px;
          border-top: 1px solid var(--line);
        }

        .captions-char-count {
          font-size: 11px;
          color: var(--muted);
          font-weight: 600;
          margin-left: auto;
        }

        .captions-emoji-btn {
          border: 0;
          background: transparent;
          font-size: 20px;
          cursor: pointer;
          padding: 2px 4px;
          border-radius: 6px;
          line-height: 1;
        }

        .captions-emoji-btn:hover {
          background: color-mix(in oklab, var(--brand) 12%, transparent);
        }

        /* Hashtags */
        .hashtags-shell {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 16px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          display: grid;
          gap: 0;
        }

        .hashtags-topbar {
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 24px;
          padding-bottom: 14px;
          border-bottom: 1px solid var(--line);
          margin-bottom: 16px;
        }

        .hashtags-by-group,
        .hashtags-sort-group {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .hashtags-group-label {
          font-size: 12px;
          font-weight: 800;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          white-space: nowrap;
        }

        .hashtags-radio-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          font-weight: 600;
          color: var(--fg);
          cursor: pointer;
        }

        .hashtags-radio-label input[type='radio'] {
          accent-color: var(--brand);
          width: 15px;
          height: 15px;
          cursor: pointer;
        }

        .hashtags-reload-group {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .hashtags-reload-btn {
          border: 0;
          background: transparent;
          color: #6366f1;
          font-weight: 700;
          font-size: 13px;
          cursor: pointer;
          padding: 4px 0;
        }

        .hashtags-added-count {
          font-size: 13px;
          color: var(--muted);
          font-weight: 600;
        }

        .hashtags-body {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 320px;
          gap: 16px;
          align-items: start;
        }

        .hashtags-main {
          display: grid;
          gap: 12px;
        }

        .hashtags-keyword-row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
        }

        .hashtags-keyword-input {
          border: 1px solid var(--line);
          border-radius: 10px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          color: var(--fg);
          padding: 10px 14px;
          font: inherit;
          font-size: 14px;
        }

        .hashtags-keyword-input::placeholder {
          color: var(--muted);
        }

        .hashtags-generate-btn {
          border: 1px solid var(--line);
          border-radius: 10px;
          background: transparent;
          color: var(--muted);
          font-weight: 700;
          padding: 10px 16px;
          cursor: pointer;
          font-size: 13px;
          white-space: nowrap;
        }

        .hashtags-generate-btn:not(:disabled):hover {
          border-color: color-mix(in oklab, var(--brand) 60%, var(--line));
          color: var(--fg);
        }

        .hashtags-generate-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .hashtags-chips-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .hashtag-chip {
          border: 1px solid var(--line);
          border-radius: 999px;
          background: transparent;
          color: var(--fg);
          padding: 6px 12px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 5px;
        }

        .hashtag-chip:hover {
          border-color: color-mix(in oklab, var(--brand) 60%, var(--line));
          background: color-mix(in oklab, var(--brand) 8%, transparent);
        }

        .hashtag-chip.added {
          border-color: color-mix(in oklab, var(--brand) 70%, var(--line));
          background: color-mix(in oklab, var(--brand) 18%, transparent);
        }

        .hashtag-count {
          font-size: 10px;
          font-weight: 700;
          color: var(--muted);
          letter-spacing: 0.02em;
        }

        .hashtag-chip.added .hashtag-count {
          color: color-mix(in oklab, var(--brand) 80%, var(--muted));
        }

        .hashtags-edit-panel {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: color-mix(in oklab, var(--bg-soft) 98%, white 2%);
          padding: 12px;
          display: grid;
          gap: 8px;
          align-content: start;
          min-height: 320px;
        }

        .hashtags-edit-label {
          font-size: 12px;
          font-weight: 800;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .hashtags-edit-textarea {
          border: 0;
          background: transparent;
          color: var(--fg);
          font: inherit;
          font-size: 13px;
          line-height: 1.6;
          resize: none;
          min-height: 240px;
          width: 100%;
        }

        .hashtags-edit-textarea::placeholder {
          color: var(--muted);
        }

        /* Suggestions */
        .suggestions-shell {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 20px;
          background: color-mix(in oklab, var(--bg-soft) 96%, white 4%);
          min-height: 300px;
        }

        .suggestions-placeholder {
          color: var(--muted);
          font-size: 13px;
          margin: 0;
        }

        .suggestions-success {
          margin: 0;
          color: var(--ok);
          font-size: 13px;
          font-weight: 700;
        }

        .suggestions-layout {
          display: grid;
          grid-template-columns: 320px minmax(0, 1fr);
          gap: 12px;
        }

        .suggestions-controls {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 12px;
          display: grid;
          gap: 10px;
          align-content: start;
          background: color-mix(in oklab, var(--bg-soft) 92%, white 8%);
        }

        .suggestions-platforms {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .suggestions-results {
          display: grid;
          gap: 10px;
          align-content: start;
        }

        .suggestion-card {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 12px;
          background: color-mix(in oklab, var(--bg-soft) 92%, white 8%);
          display: grid;
          gap: 8px;
        }

        .suggestion-card header {
          display: flex;
          justify-content: space-between;
          gap: 8px;
        }

        .suggestion-platform,
        .suggestion-score,
        .suggestion-caption,
        .suggestion-hashtags {
          margin: 0;
        }

        .suggestion-platform {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--muted);
        }

        .suggestion-score {
          font-size: 12px;
          font-weight: 700;
          color: var(--brand);
        }

        .suggestion-caption {
          font-size: 14px;
          line-height: 1.5;
          color: var(--fg);
        }

        .suggestion-hashtags {
          font-size: 12px;
          line-height: 1.5;
          color: var(--muted);
        }

        .suggestion-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        @media (max-width: 1080px) {
          .suggestions-layout {
            grid-template-columns: 1fr;
          }
        }

        .schedule-shell {
          margin-top: 12px;
          border-radius: 14px;
          padding: 12px;
          background: color-mix(in oklab, var(--bg-soft) 95%, white 5%);
          display: grid;
          gap: 10px;
          min-height: 80vh;
        }

        .schedule-topbar {
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 10px;
        }

        .schedule-topbar h3 {
          margin: 0;
          text-align: center;
          font-size: 18px;
        }

        .schedule-nav {
          display: inline-flex;
          gap: 6px;
        }

        .schedule-body {
          display: grid;
          grid-template-columns: 200px minmax(0, 1fr);
          gap: 10px;
          min-height: 680px;
          flex: 1;
        }

        .draft-lane {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          background: rgba(255, 255, 255, 0.03);
          display: grid;
          align-content: start;
          gap: 8px;
        }

        .draft-lane h4,
        .draft-lane p {
          margin: 0;
        }

        .draft-lane p {
          font-size: 12px;
          color: var(--muted);
        }

        .draft-cards {
          display: grid;
          gap: 8px;
          overflow: auto;
          max-height: 460px;
          padding-right: 4px;
        }

        .draft-card {
          border: 1px solid color-mix(in oklab, var(--brand) 45%, var(--line));
          border-radius: 12px;
          padding: 9px;
          display: grid;
          gap: 6px;
          background: linear-gradient(130deg, rgba(37, 99, 235, 0.24), rgba(2, 132, 199, 0.2));
          cursor: grab;
        }

        .draft-card strong,
        .scheduled-post strong {
          font-size: 12px;
          letter-spacing: 0.04em;
        }

        .draft-card span,
        .scheduled-post span {
          font-size: 11px;
          color: var(--muted);
        }

        .calendar-wrap {
          border: 1px solid var(--line);
          border-radius: 12px;
          overflow: auto;
          background: rgba(255, 255, 255, 0.03);
        }

        .calendar-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          min-width: 980px;
        }

        .calendar-time-head,
        .calendar-day-head,
        .calendar-time-cell,
        .calendar-drop-cell {
          border-right: 1px solid var(--line);
          border-bottom: 1px solid var(--line);
        }

        .calendar-time-head,
        .calendar-day-head {
          padding: 8px;
          background: rgba(0, 0, 0, 0.12);
          position: sticky;
          top: 0;
          z-index: 2;
        }

        .calendar-time-head {
          width: 78px;
          text-align: center;
          font-size: 12px;
          color: var(--muted);
          font-weight: 700;
        }

        .calendar-day-head {
          display: grid;
          justify-items: center;
          gap: 2px;
        }

        .calendar-day-head span {
          color: var(--muted);
          font-size: 11px;
        }

        .calendar-time-cell {
          width: 78px;
          padding: 8px;
          text-align: center;
          color: var(--muted);
          font-size: 12px;
          background: rgba(0, 0, 0, 0.07);
        }

        .calendar-drop-cell {
          min-height: 120px;
          padding: 8px;
          display: grid;
          align-content: start;
          gap: 6px;
          background: rgba(255, 255, 255, 0.01);
          transition:
            background 120ms ease,
            box-shadow 120ms ease;
        }

        .calendar-drop-cell.active {
          background: color-mix(in oklab, var(--brand) 26%, transparent);
          box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--brand) 55%, var(--line));
        }

        .scheduled-post {
          border: 1px solid color-mix(in oklab, var(--brand-2) 48%, var(--line));
          border-radius: 10px;
          padding: 7px;
          display: grid;
          gap: 5px;
          cursor: grab;
          background: linear-gradient(140deg, rgba(14, 165, 233, 0.24), rgba(37, 99, 235, 0.17));
        }

        .scheduled-post .ghost-btn {
          justify-self: start;
          font-size: 11px;
          padding: 5px 8px;
        }

        .publish-preview {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 12px;
          background: color-mix(in oklab, var(--bg-soft) 94%, white 6%);
        }

        .publish-preview h3 {
          margin: 0 0 8px;
        }

        .publish-asset-links {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 10px;
        }

        .publish-preview pre {
          margin: 0;
          white-space: pre-wrap;
          color: var(--muted);
          font-size: 12px;
        }

        .publish-error {
          margin: 0 0 8px;
          color: #ef4444;
          font-weight: 700;
          font-size: 13px;
        }

        .publish-history {
          margin-top: 12px;
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 12px;
          background: color-mix(in oklab, var(--bg-soft) 94%, white 6%);
        }

        .publish-history h3 {
          margin: 0 0 10px;
        }

        .publish-history-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          margin-bottom: 10px;
        }

        .publish-history-list {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
          gap: 8px;
        }

        .history-card {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 10px;
          display: grid;
          gap: 6px;
          background: rgba(255, 255, 255, 0.03);
        }

        .history-card p {
          margin: 0;
        }

        .muted-line {
          color: var(--muted);
          font-size: 12px;
        }

        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        @media (max-width: 1320px) {
          .insights-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .editor-workspace {
            grid-template-columns: 70px 310px minmax(0, 1fr);
          }

          .editor-workspace-modern {
            grid-template-columns: 70px 240px minmax(0, 1fr);
          }

          .publish-toolbar {
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          }

          .publish-mode-switch {
            grid-column: 1 / -1;
          }

          .property-panel {
            grid-column: 1 / -1;
            max-height: none;
          }

          .property-panel-modern {
            grid-column: 1 / -1;
          }

          .creative-preview-modal-editor {
            grid-template-columns: 1fr;
          }

          .schedule-body {
            grid-template-columns: 1fr;
          }

          .draft-cards {
            max-height: 220px;
          }

          .template-card-actions,
          .template-customizer-row {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 960px) {
          .insights-head,
          .insight-pill-row,
          .insight-post-meta {
            flex-direction: column;
          }

          .insights-grid,
          .metric-pair-grid {
            grid-template-columns: 1fr;
          }

          .editor-topbar {
            grid-template-columns: 1fr;
          }

          .mode-tabs {
            justify-self: stretch;
          }

          .editor-workspace {
            grid-template-columns: 1fr;
          }

          .editor-workspace-modern {
            grid-template-columns: 1fr;
          }

          .publish-toolbar {
            grid-template-columns: 1fr;
          }

          .tool-rail {
            grid-auto-flow: column;
            grid-auto-columns: minmax(min(100%, 90px), 1fr);
            overflow: auto;
          }

          .editor-sidebar-rail {
            grid-auto-flow: column;
            grid-auto-columns: minmax(min(100%, 110px), 1fr);
            overflow: auto;
          }

          .creative-library-header,
          .creative-library-actions,
          .creative-preview-meta-row,
          .creative-preview-meta-actions,
          .editor-canvas-topbar {
            flex-direction: column;
            align-items: stretch;
          }

          .creative-library-search {
            min-width: 0;
          }

          .creative-library-grid {
            grid-template-columns: 1fr;
          }

          .text-style-grid {
            grid-template-columns: 1fr;
            max-height: none;
          }

          .text-quick-btn-primary {
            font-size: 24px;
          }

          .canvas-stage {
            min-height: 420px;
          }

          .creative-artboard.editable {
            width: 100%;
          }

          .canvas-board {
            min-height: 460px;
          }

          .headline {
            max-width: 100%;
            font-size: clamp(34px, 8vw, 62px);
          }

          .subheadline {
            max-width: 100%;
            font-size: 18px;
          }

          .uploaded-image,
          .image-placeholder {
            position: static;
            width: 100%;
            height: 220px;
            margin-top: 18px;
          }

          .schedule-topbar {
            grid-template-columns: 1fr;
          }

          .schedule-topbar h3 {
            text-align: left;
          }

          .calendar-header-row,
          .calendar-row {
            display: table-row;
          }

          .calendar-time-head,
          .calendar-time-cell {
            width: 64px;
          }
        }
      `}</style>
    </main>
  );
}
