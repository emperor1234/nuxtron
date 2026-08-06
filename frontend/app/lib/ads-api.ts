/**
 * Ads Control Tower — typed API client
 *
 * Wraps the generic platform-api helpers with domain-specific
 * request/response types for connector OAuth, campaign CRUD,
 * calendar, metrics, KPIs, forecast, credits, and notifications.
 */

import { apiGet, apiSend, DEFAULT_TENANT_ID } from './platform-api';

// ─── Shared primitives ───────────────────────────────────────────────────────

type AdsStatus = 'ok' | 'error';

export type AdsPlatform = 'google_ads' | 'microsoft_ads' | 'amazon_ads' | 'apple_search_ads' | 'youtube_ads';

export const PLATFORM_LABELS: Record<AdsPlatform, string> = {
  google_ads: 'Google Ads',
  microsoft_ads: 'Microsoft Advertising',
  amazon_ads: 'Amazon Advertising',
  apple_search_ads: 'Apple Search Ads',
  youtube_ads: 'YouTube Ads',
};

export type AdsConnector = {
  id: string;
  tenant_id: string;
  platform: AdsPlatform;
  platform_description?: string;
  platform_accent?: string;
  status: 'connected' | 'disconnected' | 'auth_pending';
  connected: boolean;
  account_name: string;
  account_id: string;
  scopes: string[];
  token_fingerprint: string | null;
  refresh_token_present: boolean;
  credit_currency: string;
  credit_total: number;
  credit_remaining: number;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdsKeyword = {
  keyword: string;
  cpc_bid: number;
  cost_today: number;
  rank: number;
};

type AdsCreative = {
  title: string;
  description: string;
  cta: string;
  media_urls: string[];
};

type AdsSchedule = {
  timezone: string;
  start_at: string | null;
  end_at: string | null;
  auto_post: boolean;
  posting_dates: string[];
};

export type CampaignMetrics = {
  likes: number;
  description_views: number;
  shares: number;
  comments: number;
  clicks: number;
  impressions: number;
  conversions: number;
  spend: number;
  revenue: number;
  roi_pct: number;
  success_ratio_pct: number;
  updated_at: string;
};

export type AdsCampaign = {
  id: string;
  tenant_id: string;
  platform: AdsPlatform;
  campaign_name: string;
  objective: string;
  status: 'draft' | 'active' | 'paused';
  budget_daily: number;
  budget_total: number;
  currency: string;
  keywords: AdsKeyword[];
  creative: AdsCreative;
  schedule: AdsSchedule;
  connected_accounts: string[];
  metrics: CampaignMetrics;
  created_at: string;
  updated_at: string;
  published_at?: string;
  // Approval workflow
  approval_status?: 'pending_approval' | 'approved' | 'rejected' | null;
  approval_requested_at?: string | null;
  reviewer_email?: string;
  approval_message?: string;
  approval_reason?: string;
  approver_name?: string;
  auto_publish_on_approve?: boolean;
};

export type CalendarEvent = {
  campaign_id: string;
  campaign_name: string;
  platform: AdsPlatform;
  date: string;
  timezone: string;
  auto_post: boolean;
};

export type KpiSummary = {
  campaigns_total: number;
  campaigns_active: number;
  budget_daily: number;
  budget_total: number;
  spend: number;
  revenue: number;
  roi_pct: number;
  success_ratio_pct: number;
  ctr_pct: number;
  cpc: number;
  cpa: number;
};

export type KpiEngagement = {
  likes: number;
  shares: number;
  comments: number;
  clicks: number;
  impressions: number;
  conversions: number;
};

type AdsNotification = {
  id: number;
  tenant_id: string;
  title: string;
  message: string;
  category: string;
  priority: string;
  is_read: boolean;
  source: string;
  created_at: string;
};

type CreditAccount = {
  platform: AdsPlatform;
  account_name: string;
  account_id: string;
  currency: string;
  credit_total: number;
  credit_remaining: number;
  connected: boolean;
};

// ─── API helpers ─────────────────────────────────────────────────────────────

const BASE = '/ads-control-tower';
const tid = DEFAULT_TENANT_ID;

export const adsApi = {
  // --- Health ------------------------------------------------------------------
  health: () =>
    apiGet<{
      status: AdsStatus;
      connectors_total: number;
      connectors_connected: number;
      campaigns_total: number;
      campaigns_overdue_sync: number;
    }>(`${BASE}/health`, tid),

  // --- Connectors --------------------------------------------------------------
  listConnectors: () => apiGet<{ status: AdsStatus; connectors: AdsConnector[] }>(`${BASE}/connectors`, tid),

  oauthStart: (platform: AdsPlatform) =>
    apiSend<{
      platform: AdsPlatform;
      state: string;
      authorization_url: string;
      callback_path: string;
    }>(`${BASE}/connectors/${platform}/oauth/start`, 'POST', undefined, tid),

  oauthCallback: (
    platform: AdsPlatform,
    body: {
      state: string;
      code: string;
      account_name?: string;
      account_id?: string;
      scopes?: string[];
      credit_total?: number;
      credit_remaining?: number;
      credit_currency?: string;
    }
  ) =>
    apiSend<{ status: AdsStatus; connector: AdsConnector }>(
      `${BASE}/connectors/${platform}/oauth/callback`,
      'POST',
      body,
      tid
    ),

  disconnectConnector: (platform: AdsPlatform) =>
    apiSend<{ status: AdsStatus; connector: AdsConnector }>(`${BASE}/connectors/${platform}`, 'DELETE', undefined, tid),

  // --- Credits -----------------------------------------------------------------
  credits: () =>
    apiGet<{
      status: AdsStatus;
      accounts: CreditAccount[];
      portfolio_credit_total: number;
      portfolio_credit_remaining: number;
    }>(`${BASE}/credits`, tid),

  // --- Campaigns ---------------------------------------------------------------
  listCampaigns: (filters?: { platform?: AdsPlatform; status?: string }) => {
    const params = new URLSearchParams();
    if (filters?.platform) params.set('platform', filters.platform);
    if (filters?.status) params.set('status', filters.status);
    const qs = params.size ? `?${params.toString()}` : '';
    return apiGet<{ status: AdsStatus; total: number; campaigns: AdsCampaign[] }>(`${BASE}/campaigns${qs}`, tid);
  },

  createCampaign: (payload: {
    platform: AdsPlatform;
    campaign_name: string;
    objective: string;
    status: 'draft' | 'active' | 'paused';
    budget_daily: number;
    budget_total: number;
    currency: string;
    keywords: AdsKeyword[];
    creative: AdsCreative;
    schedule: Partial<AdsSchedule>;
    connected_accounts?: string[];
  }) => apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/campaigns`, 'POST', payload, tid),

  getCampaign: (id: string) => apiGet<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/campaigns/${id}`, tid),

  updateCampaign: (
    id: string,
    patch: Partial<
      Pick<
        AdsCampaign,
        | 'campaign_name'
        | 'objective'
        | 'status'
        | 'budget_daily'
        | 'budget_total'
        | 'keywords'
        | 'creative'
        | 'schedule'
      >
    >
  ) => apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/campaigns/${id}`, 'PATCH', patch, tid),

  deleteCampaign: (id: string) =>
    apiSend<{ status: AdsStatus; deleted: string }>(`${BASE}/campaigns/${id}`, 'DELETE', undefined, tid),

  publishCampaign: (id: string, publishAll = true) =>
    apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(
      `${BASE}/campaigns/${id}/publish`,
      'POST',
      { publish_all_connected_accounts: publishAll },
      tid
    ),

  patchMetrics: (
    id: string,
    metrics: {
      likes?: number;
      shares?: number;
      comments?: number;
      clicks?: number;
      impressions?: number;
      conversions?: number;
      spend?: number;
      revenue?: number;
    }
  ) => apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/campaigns/${id}/metrics`, 'POST', metrics, tid),

  // --- Calendar ----------------------------------------------------------------
  calendar: () => apiGet<{ status: AdsStatus; events: CalendarEvent[] }>(`${BASE}/calendar`, tid),

  dragReschedule: (payload: {
    campaign_id: string;
    from_date: string;
    to_date: string;
    auto_select_window_days?: number;
  }) => apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/calendar/drag-reschedule`, 'POST', payload, tid),

  // --- Asset auto-resize -------------------------------------------------------
  autoResize: (asset_url: string, platforms: AdsPlatform[]) =>
    apiSend<{
      status: AdsStatus;
      variants: { platform: AdsPlatform; width: number; height: number; output_url: string }[];
    }>(`${BASE}/assets/auto-resize`, 'POST', { asset_url, platforms }, tid),

  // --- KPIs & forecast ---------------------------------------------------------
  kpis: () =>
    apiGet<{
      status: AdsStatus;
      summary: KpiSummary;
      engagement: KpiEngagement;
    }>(`${BASE}/kpis`, tid),

  forecast: (days = 30) =>
    apiGet<{
      status: AdsStatus;
      horizon_days: number;
      projected_spend: number;
      projected_clicks: number;
      projected_conversions: number;
      projected_roi_pct: number;
    }>(`${BASE}/forecast?days=${days}`, tid),

  // --- Notifications -----------------------------------------------------------
  notifications: (limit = 20) =>
    apiGet<{
      status: AdsStatus;
      total: number;
      notifications: AdsNotification[];
    }>(`${BASE}/notifications?limit=${limit}`, tid),

  // --- Best time recommendation ------------------------------------------------
  bestTime: (platform: AdsPlatform, objective = 'conversions') =>
    apiGet<BestTimeRecommendation>(`${BASE}/best-time?platform=${platform}&objective=${objective}`, tid),

  // --- Approval workflow -------------------------------------------------------
  requestApproval: (id: string, payload: ApprovalRequest) =>
    apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(
      `${BASE}/campaigns/${id}/request-approval`,
      'POST',
      payload,
      tid
    ),

  approveOrReject: (id: string, payload: ApprovalDecision) =>
    apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(`${BASE}/campaigns/${id}/approve`, 'POST', payload, tid),

  // --- Campaign duplicate -------------------------------------------------------
  duplicateCampaign: (id: string, newName: string, status: 'draft' | 'active' | 'paused' = 'draft') =>
    apiSend<{ status: AdsStatus; campaign: AdsCampaign }>(
      `${BASE}/campaigns/${id}/duplicate`,
      'POST',
      { new_name: newName, status },
      tid
    ),

  // --- A/B test suggestions ---------------------------------------------------
  abTestSuggestions: (id: string) => apiGet<AbTestSuggestions>(`${BASE}/ab-test/${id}/suggestions`, tid),

  // --- Audience insights -------------------------------------------------------
  audienceInsights: () => apiGet<AudienceInsights>(`${BASE}/audience-insights`, tid),
};

// ─── New feature types ────────────────────────────────────────────────────────

export type BestTimeRecommendation = {
  status: AdsStatus;
  platform: AdsPlatform;
  objective: string;
  best_days: string[];
  /** day abbrev → hour string → score 0–100 (JSON keys are strings) */
  heatmap: Record<string, Record<string, number>>;
  peak_hour: number;
  avoid_hours: number[];
  human_review_window: number[];
  rationale: string;
  all_platforms_peak: Record<string, number>;
};

type ApprovalRequest = {
  reviewer_email: string;
  message?: string;
  auto_publish_on_approve?: boolean;
};

type ApprovalDecision = {
  decision: 'approved' | 'rejected';
  reason?: string;
  reviewer_name?: string;
};

type AbTestVariant = {
  variant: string;
  label: string;
  title: string;
  description: string;
  cta: string;
  predicted_ctr_lift_pct: number;
  rationale: string;
};

export type AbTestSuggestions = {
  status: AdsStatus;
  campaign_id: string;
  original: { title: string; description: string; cta: string };
  suggestions: AbTestVariant[];
};

export type AudienceInsights = {
  status: AdsStatus;
  platforms_active: AdsPlatform[];
  keywords_indexed: number;
  audience_overlap_pct: number;
  keyword_saturation_score: number;
  estimated_reach: number;
  recommendations: string[];
  top_keywords: string[];
  frequency_cap_suggestion: number;
};
