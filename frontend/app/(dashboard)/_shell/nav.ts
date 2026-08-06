/**
 * Dashboard navigation model — mirrors the approved reference.
 * The icon rail lists top-level sections; each section (except Home) opens a
 * flyout whose items are grouped *by function*. Rail sections link to a valid
 * base route; flyout groups organise the tools within that section.
 */

export type RailKey =
  | 'dashboard'
  | 'seo'
  | 'ai'
  | 'traffic'
  | 'local'
  | 'content'
  | 'social'
  | 'apps'
  | 'settings';

export type FlyoutItem = { label: string; href: string };
export type FlyoutGroup = { label: string; items: FlyoutItem[] };
export type FlyoutMenu = { title: string; groups: FlyoutGroup[] };

export type RailItem = {
  key: RailKey;
  label: string;
  href: string;
  /** Whether clicking opens a function-grouped flyout. */
  hasMenu: boolean;
};

export const RAIL_ITEMS: readonly RailItem[] = [
  { key: 'dashboard', label: 'Home', href: '/dashboard', hasMenu: false },
  { key: 'seo', label: 'SEO', href: '/seo', hasMenu: true },
  { key: 'ai', label: 'AI', href: '/seo/seo-ai', hasMenu: true },
  { key: 'traffic', label: 'Traffic', href: '/seo/analytics', hasMenu: true },
  { key: 'local', label: 'Local', href: '/seo/local-seo', hasMenu: true },
  { key: 'content', label: 'Content', href: '/content-generation', hasMenu: true },
  { key: 'social', label: 'Social', href: '/seo/social', hasMenu: true },
  { key: 'apps', label: 'Apps', href: '/platform', hasMenu: true },
];

export const SETTINGS_ITEM: RailItem = {
  key: 'settings',
  label: 'Settings',
  href: '/account/settings',
  hasMenu: true,
};

const seo = (slug: string) => `/seo/${slug}`;

export const MENUS: Partial<Record<RailKey, FlyoutMenu>> = {
  seo: {
    title: 'SEO',
    groups: [
      {
        label: 'Site Performance',
        items: [
          { label: 'Site Audit', href: seo('site-audit') },
          { label: 'Position Tracking', href: seo('rank-tracking') },
          { label: 'Log File Analyzer', href: seo('log-file') },
        ],
      },
      {
        label: 'Competitive Analysis',
        items: [
          { label: 'Domain Overview', href: seo('domain-overview') },
          { label: 'Organic Research', href: seo('keywords') },
          { label: 'Top Pages', href: seo('performance') },
          { label: 'Keyword Gap', href: seo('keywords-explorer') },
          { label: 'Backlink Gap', href: seo('backlink-intelligence') },
        ],
      },
      {
        label: 'Keyword Research',
        items: [
          { label: 'Keyword Overview', href: seo('keywords') },
          { label: 'Keyword Magic Tool', href: seo('keywords-explorer') },
          { label: 'Keyword Strategy Builder', href: seo('growth-playbooks') },
        ],
      },
      {
        label: 'Link Building',
        items: [
          { label: 'Backlinks', href: seo('backlink-intelligence') },
          { label: 'Referring Domains', href: seo('backlink-intelligence') },
          { label: 'Backlink Audit', href: seo('backlink-intelligence') },
          { label: 'Link Building Tool', href: seo('linkbuilding') },
        ],
      },
      {
        label: 'Content',
        items: [
          { label: 'SEO Writing Assistant', href: seo('writer') },
          { label: 'Topic Research', href: seo('content-brief') },
          { label: 'SEO Content Template', href: seo('content-brief') },
        ],
      },
    ],
  },
  ai: {
    title: 'AI Marketing',
    groups: [
      {
        label: 'Create',
        items: [
          { label: 'AI Content Generator', href: '/content-generation' },
          { label: 'AI Copywriter', href: seo('writer') },
          { label: 'Image Studio', href: '/media-processing' },
          { label: 'Brand Voice', href: seo('brand-voice') },
        ],
      },
      {
        label: 'Optimize',
        items: [
          { label: 'AI SEO Assistant', href: seo('seo-ai-assist') },
          { label: 'Smart Recommendations', href: seo('seo-ai') },
          { label: 'A/B Test Lab', href: seo('seo-ab-testing') },
        ],
      },
      {
        label: 'Automate',
        items: [
          { label: 'Campaign Autopilot', href: seo('seo-ai-automation') },
          { label: 'Smart Scheduler', href: seo('ads-smart-schedule') },
          { label: 'Auto Reports', href: seo('report-builder') },
        ],
      },
      {
        label: 'Insights',
        items: [
          { label: 'Trend Predictor', href: '/ai-analytics' },
          { label: 'Audience Intelligence', href: seo('one2target') },
        ],
      },
    ],
  },
  traffic: {
    title: 'Traffic & Market',
    groups: [
      {
        label: 'Market Analysis',
        items: [
          { label: 'Market Explorer', href: seo('market-explorer') },
          { label: 'Traffic Analytics', href: seo('analytics') },
          { label: 'One2Target', href: seo('one2target') },
        ],
      },
      {
        label: 'Benchmarking',
        items: [
          { label: 'Industry Benchmarks', href: '/benchmarks' },
          { label: 'Growth Quadrant', href: '/competitive-benchmarking' },
          { label: 'Trending Now', href: seo('news-discover') },
        ],
      },
      {
        label: 'Audience',
        items: [
          { label: 'Demographics', href: seo('one2target') },
          { label: 'Audience Overlap', href: seo('market-explorer') },
        ],
      },
    ],
  },
  local: {
    title: 'Local',
    groups: [
      {
        label: 'Local SEO',
        items: [
          { label: 'Listing Management', href: seo('local-seo') },
          { label: 'Map Rank Tracker', href: seo('map-rank-tracker') },
          { label: 'Review Management', href: seo('reviews') },
        ],
      },
      {
        label: 'Business Profile',
        items: [
          { label: 'GBP Optimization', href: seo('gbp-monitor') },
          { label: 'Local Heatmap', href: seo('local-heatmap') },
        ],
      },
    ],
  },
  content: {
    title: 'Content',
    groups: [
      {
        label: 'Plan',
        items: [
          { label: 'Content Calendar', href: seo('ads-calendar') },
          { label: 'Topic Research', href: seo('content-brief') },
          { label: 'Brief Generator', href: seo('content-brief') },
        ],
      },
      {
        label: 'Create',
        items: [
          { label: 'AI Writer', href: seo('writer') },
          { label: 'Content Templates', href: seo('content-creation-blogging') },
        ],
      },
      {
        label: 'Optimize',
        items: [
          { label: 'On-Page Checker', href: seo('on-page') },
          { label: 'Readability Score', href: seo('content-auditor') },
          { label: 'SEO Writing Assistant', href: seo('writer') },
        ],
      },
      {
        label: 'Distribute',
        items: [
          { label: 'Social Poster', href: seo('social') },
          { label: 'Newsletter Builder', href: '/content-generation' },
        ],
      },
    ],
  },
  social: {
    title: 'Social Media',
    groups: [
      {
        label: 'Publish',
        items: [
          { label: 'Post Scheduler', href: '/buffer-publish' },
          { label: 'Content Calendar', href: seo('ads-calendar') },
          { label: 'Bulk Upload', href: '/buffer-create' },
        ],
      },
      {
        label: 'Engage',
        items: [
          { label: 'Social Inbox', href: '/buffer-community' },
          { label: 'Comment Manager', href: '/buffer-community' },
        ],
      },
      {
        label: 'Analyze',
        items: [
          { label: 'Social Analytics', href: '/buffer-analyze' },
          { label: 'Competitor Tracking', href: seo('competitor') },
          { label: 'Brand Monitoring', href: '/social-listening' },
        ],
      },
      {
        label: 'Advertise',
        items: [
          { label: 'Ad Manager', href: seo('ads-campaigns') },
          { label: 'Ad Creative Lab', href: '/ads-generation' },
        ],
      },
    ],
  },
  apps: {
    title: 'Apps & More',
    groups: [
      {
        label: 'Marketplace',
        items: [
          { label: 'App Center', href: '/platform' },
          { label: 'Integrations', href: seo('integrations-automation') },
          { label: 'API Access', href: '/api-governance' },
        ],
      },
      {
        label: 'Resources',
        items: [
          { label: 'Agency Kit', href: seo('agency-platform') },
          { label: 'Academy', href: '/playbooks' },
          { label: 'Templates Gallery', href: seo('content-creation-blogging') },
        ],
      },
    ],
  },
  settings: {
    title: 'Settings',
    groups: [
      {
        label: 'Account',
        items: [
          { label: 'Profile', href: '/account/profile' },
          { label: 'Billing & Plans', href: '/billing' },
          { label: 'Team Members', href: '/account' },
        ],
      },
      {
        label: 'Preferences',
        items: [
          { label: 'Notifications', href: '/account/settings' },
          { label: 'Connected Apps', href: seo('integrations-automation') },
          { label: 'API Keys', href: '/api-governance' },
        ],
      },
    ],
  },
};
