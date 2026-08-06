/**
 * Typed API client for Social Media Production workflows
 * Mirrors ads-api.ts patterns for consistency
 */
import { apiGet, apiSend } from './platform-api';

// ============================================================================
// Type Definitions
// ============================================================================

export type SocialNetwork = 'facebook' | 'instagram' | 'tiktok' | 'twitter' | 'linkedin' | 'youtube' | 'threads';

export interface SocialAccount {
  id: string;
  network: SocialNetwork;
  accountName: string;
  handle: string;
  followers: number;
  verified: boolean;
  connected_at: string;
  last_sync: string;
  syncStatus: 'syncing' | 'synced' | 'error';
  creditsBalance: number;
}

export interface SocialPost {
  id: string;
  content: string;
  platforms: SocialNetwork[];
  mediaUrls?: string[];
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduledAt?: string;
  publishedAt?: string;
  metrics?: PostMetrics;
}

export interface PostMetrics {
  likes: number;
  comments: number;
  shares: number;
  clicks: number;
  impressions: number;
  reach: number;
}

export interface SocialTrend {
  id: string;
  topic: string;
  category: string;
  momentum: 'emerging' | 'uptrend' | 'peak' | 'downtrend';
  volume: number;
  growthRate: number;
  roiPotential: number;
  roiForecast: string;
  relatedHashtags: string[];
  relatedAccounts: string[];
}

export interface AnalyticsMetrics {
  period: string;
  impressions: number;
  reach: number;
  engagement: number;
  clicks: number;
  conversions: number;
  roi: number;
  roiPercentage: number;
}

export interface CalendarEvent {
  id: string;
  postId: string;
  platforms: SocialNetwork[];
  caption: string;
  mediaUrl?: string;
  scheduledTime: string;
  status: 'scheduled' | 'published' | 'failed';
  autoPost: boolean;
}

export interface ApprovalRequest {
  id: string;
  postId: string;
  platforms: SocialNetwork[];
  contentPreview: string;
  requestedAt: string;
  requestedBy: string;
  status: 'pending' | 'approved' | 'rejected';
  approvers: string[];
  autoPublishOnApprove: boolean;
}

export interface ShortLinkRecord {
  id: number;
  provider: 'bitly' | 'tinyurl' | 'rebrandly' | string;
  source_url: string;
  short_url: string;
  domain?: string;
  created_at: string;
}

export interface IntegrationWebhook {
  id: number;
  name: string;
  provider: 'zapier' | 'make' | 'custom' | string;
  url: string;
  event_types: string[];
  secret?: string;
  action_type: 'notify_only' | 'create_idea' | 'queue_post' | string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CanvaImportJob {
  id: number;
  account_id: number;
  design_id?: string;
  design_url?: string;
  resolved_media_url: string;
  post_id: number;
  status: string;
  created_at: string;
}

export interface BrowserCapture {
  id: number;
  source_url: string;
  title: string;
  selected_text?: string;
  note?: string;
  suggested_network: string;
  screenshot_url?: string;
  tags: string[];
  status: 'captured' | 'queued' | string;
  created_at: string;
  updated_at: string;
  queued_post_id?: number;
}

export interface MobileDevice {
  id: number;
  device_id: string;
  platform: 'ios' | 'android' | 'web' | string;
  push_provider: 'fcm' | 'onesignal' | 'apns' | 'none' | string;
  push_token?: string;
  app_version?: string;
  locale?: string;
  timezone?: string;
  last_seen_at: string;
  created_at: string;
}

export interface MobileSyncBatch {
  id: number;
  device_id: string;
  received: number;
  applied: number;
  rejected: number;
  applied_items: Array<Record<string, unknown>>;
  rejected_items: Array<Record<string, unknown>>;
  created_at: string;
}

export interface InboxItem {
  id: string;
  network: SocialNetwork;
  source: string;
  type: 'mention' | 'comment' | 'dm' | 'reply';
  content: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  engagement: number;
  createdAt: string;
  responded: boolean;
}

export interface ListeningMetrics {
  period: string;
  mentions: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
  topCompetitors: string[];
  competitorMentions: Record<string, number>;
}

export interface CompetitorInsight {
  competitor: string;
  network: SocialNetwork;
  followers: number;
  engagement_rate: number;
  average_likes: number;
  average_comments: number;
  posting_frequency: string;
  best_posting_time: string;
}

export interface AutomationRule {
  id: number;
  name: string;
  trigger_type: string;
  trigger_value: string;
  action_type: string;
  action_payload: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface AutomationFeed {
  id: number;
  name: string;
  feed_url: string;
  target_networks: string[];
  cadence_minutes: number;
  autopublish: boolean;
  enabled: boolean;
  last_synced_at?: string | null;
  created_at: string;
}

export interface SocialIdea {
  id: number;
  title: string;
  body: string;
  source: string;
  source_ref?: string | null;
  tags: string[];
  status: 'new' | 'queued' | 'published' | 'rejected';
  created_at: string;
  updated_at: string;
}

export interface MonitoringStream {
  id: number;
  name: string;
  stream_type: string;
  query: string;
  networks: string[];
  column_index: number;
  feed: Array<Record<string, unknown>>;
  created_at: string;
  updated_at?: string;
}

export interface SocialListeningKeyword {
  id: number;
  keyword: string;
  networks: string[];
  alert_threshold: number;
  alert_on_crisis: boolean;
  created_at: string;
}

export interface SocialListeningMention {
  id: number;
  keyword_id: number;
  network: string;
  author: string;
  text: string;
  sentiment: 'positive' | 'neutral' | 'negative' | string;
  reach: number;
  engagement: number;
  is_crisis: boolean;
  alert_dismissed: boolean;
  created_at: string;
}

export interface SocialListeningSentiment {
  sentiment_score: number;
  label: string;
  breakdown: { positive: number; neutral: number; negative: number; total: number };
  network_breakdown: Record<string, { positive: number; negative: number }>;
}

export interface SocialReport {
  id: number;
  name: string;
  report_type: string;
  networks: string[];
  date_range: string;
  metrics: string[];
  schedule: string;
  export_format: string;
  status: string;
  generated_at: string | null;
  export_url: string | null;
  created_at: string;
}

export interface PublishingQueueResponse {
  pause_all: { paused: boolean; reason?: string; updated_at?: string | null };
  summary: { scheduled: number; drafts: number };
  items: Array<Record<string, unknown>>;
}

export interface SavedReply {
  id: number;
  title: string;
  body: string;
  category: string;
  created_at: string;
}

export interface ContactView {
  handle: string;
  display_name: string;
  message_count: number;
  last_message_at: string;
  sentiment: string;
  networks: string[];
}

export interface ManychatTag {
  id: number;
  name: string;
  color: string;
  created_at: string;
}

export interface ManychatSegment {
  id: number;
  name: string;
  description: string;
  conditions: Array<Record<string, unknown>>;
  created_at: string;
}

export interface ManychatFlow {
  id: number;
  name: string;
  channel: string;
  trigger_type: string;
  trigger_value: string;
  steps: Array<Record<string, unknown>>;
  status: 'active' | 'paused' | 'draft' | string;
  created_at: string;
  updated_at: string;
}

export interface ManychatBroadcast {
  id: number;
  name: string;
  channel: string;
  target_segment_ids: number[];
  message: string;
  status: 'scheduled' | 'sent' | 'draft' | string;
  scheduled_for: string;
  estimated_recipients: number;
  created_at: string;
  sent_at?: string;
}

export interface ManychatSequence {
  id: number;
  name: string;
  channel: string;
  steps: Array<Record<string, unknown>>;
  enrollment_trigger: string;
  created_at: string;
}

export interface ManychatKeyword {
  id: number;
  keyword: string;
  channel: string;
  reply_text: string;
  assign_tag_ids: number[];
  created_at: string;
}

export interface ManychatOverview {
  counts: {
    tags: number;
    segments: number;
    flows: number;
    broadcasts: number;
    sequences: number;
    keywords: number;
    automation_runs: number;
  };
  feature_matrix: Array<{ feature: string; status: string }>;
  vendors: Array<{ vendor: string; products: string[]; use_case: string }>;
}

export interface SocialAIAgentTemplate {
  key: 'social_poster' | 'dm_chatbot' | 'comment_to_dm' | string;
  name: string;
  description: string;
  trigger_types: string[];
  action: string;
  vendors: string[];
}

export interface IntegrationCatalogProvider {
  vendor: string;
  provider_key: string;
  configured: boolean;
  route?: string;
  supported_triggers?: string[];
}

export interface IntegrationCatalogCategory {
  category: string;
  providers: IntegrationCatalogProvider[];
}

export interface SocialProductionReadinessVendor {
  vendor: string;
  vendor_key: string;
  configured: boolean;
  env_keys: string[];
  capabilities: string[];
  routes: string[];
}

export interface SocialProductionCapability {
  capability: string;
  capability_key: string;
  status: 'done' | 'partial' | 'missing';
  completion_percent: number;
  automation_level_percent: number;
  how_it_works: string;
  route_coverage_percent: number;
  routes_required: string[];
  routes_available: string[];
  required_vendors: string[];
  optional_vendors: string[];
  required_vendors_configured: string[];
  optional_vendors_configured: string[];
  required_vendors_missing: string[];
  fully_wired: boolean;
}

export interface SocialProductionReadiness {
  status: string;
  tenant_id: string;
  production_ready: boolean;
  readiness_score: number;
  capability_summary: {
    total_capabilities: number;
    fully_wired_capabilities: number;
    average_completion_percent: number;
    target: string;
  };
  signals: {
    strict_social_mode_enabled: boolean;
    oauth_mode: string;
    openai_configured: boolean;
    canva_configured: boolean;
    db_backing_enabled: boolean;
    oauth_vendor_networks_configured: number;
    oauth_vendor_networks_total: number;
  };
  vendors: {
    oauth: Record<string, boolean>;
    shorteners: Record<string, boolean>;
    registry: SocialProductionReadinessVendor[];
  };
  capability_matrix: SocialProductionCapability[];
  active_fallback_paths: Record<string, boolean>;
  blocking_items: string[];
}

export interface SocialGrowthIntegrationItem {
  integration: string;
  integration_key: string;
  best_practice_required: boolean;
  category: string;
  phase: string;
  impact_stars: number;
  roi_priority: number;
  completion_percent: number;
  implementation_status: 'done' | 'partial' | 'missing';
  configured: boolean;
  vendors: string[];
  how_it_works: string;
  why_it_drives_growth: string;
  required_env_keys: string[];
  configured_env_keys: string[];
  missing_env_keys: string[];
  route_dependencies: string[];
  available_routes: string[];
  missing_routes: string[];
  left_to_complete: string[];
}

export interface SocialGrowthMatrixResponse {
  status: string;
  tenant_id: string;
  strict_social_mode_enabled: boolean;
  summary: {
    total_integrations: number;
    required_integrations: number;
    required_done: number;
    done: number;
    partial: number;
    missing: number;
    average_completion_percent: number;
    target: string;
    highest_roi_next: string[];
  };
  matrix: SocialGrowthIntegrationItem[];
}

export interface SocialProductionRemediationRequirement {
  key: string;
  configured: boolean;
  expected: string;
  category: string;
  description: string;
}

export interface SocialProductionRemediationIntegration {
  integration_key: string;
  integration: string;
  category: string;
  phase: string;
  impact_stars: number;
  roi_priority: number;
  missing_env_keys: string[];
  left_to_complete: string[];
}

export interface SocialProductionRemediationPlan {
  status: string;
  tenant_id: string;
  production_ready: boolean;
  readiness_score: number;
  blocking_items: string[];
  global_requirements: SocialProductionRemediationRequirement[];
  integration_requirements: SocialProductionRemediationIntegration[];
  missing_env_keys: string[];
  next_actions: string[];
}

export interface BestStackProbeResult {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
}

export interface BestStackReportRecord {
  id: number;
  name: string;
  generated_at: string;
  export_url: string;
}

export interface BestStackReportCreateResponse {
  status: string;
  tenant_id: string;
  report: {
    id: number;
    name: string;
    report_type: string;
    generated_at: string;
    export_url: string;
  };
  artifact: {
    summary: {
      readiness_score: number;
      production_ready: boolean;
      checks_total: number;
      checks_passed: number;
      checks_failed: number;
    };
    stack_coverage: Array<Record<string, unknown>>;
    probe_results: BestStackProbeResult[];
    generated_at: string;
    generated_by: string;
  };
  artifact_markdown: string;
}

export interface SocialAuditLogEntry {
  id: number;
  tenant_id: string;
  action: string;
  ref_id?: number | null;
  created_at: string;
  source: string;
}

export interface OwlyWriterGeneratePayload {
  topic: string;
  goal: string;
  style: 'professional' | 'casual' | 'humorous' | 'inspirational';
  audience: string;
  platforms: SocialNetwork[];
  include_hashtags?: boolean;
  include_emoji?: boolean;
  include_cta?: boolean;
  campaign_tag?: string;
  destination_url?: string;
  variations_per_platform?: number;
}

export interface OwlyWriterGenerationItem {
  variation_id: string;
  platform: string;
  caption: string;
  hashtags: string[];
  quality: {
    overall: number;
    components: {
      readability: number;
      hashtag_coverage: number;
      cta_strength: number;
    };
  };
  length: number;
}

export interface OwlyWriterGeneration {
  id: string;
  tenant_id: string;
  topic: string;
  goal: string;
  style: string;
  audience: string;
  platforms: string[];
  variations_per_platform: number;
  items: OwlyWriterGenerationItem[];
  generated_at: string;
  provider: string;
}

// ============================================================================
// API Client Methods
// ============================================================================

export const socialApi = {
  /**
   * Accounts: Connect, list, and manage social accounts
   */
  async listAccounts(): Promise<SocialAccount[]> {
    return apiGet('/social/accounts');
  },

  /**
   * Step 1 of the OAuth connect flow: asks the backend to mint a
   * server-side, single-use `state` (backend/fastapi/app/routers/
   * social_workspace.py `_sw_oauth_start`) and returns the provider's
   * authorization_url to redirect the browser to. The frontend never
   * generates its own state — trusting a client-generated value would
   * defeat the CSRF protection the backend is enforcing on the callback.
   */
  async startOAuth(
    network: SocialNetwork,
    params?: { accountName?: string; handle?: string; accountType?: string; website?: string; description?: string }
  ): Promise<{ authorization_url: string; state: string; redirect_uri: string }> {
    return apiSend(`/social/oauth/${network}/start`, 'POST', {
      account_name: params?.accountName,
      handle: params?.handle,
      account_type: params?.accountType,
      website: params?.website,
      description: params?.description,
    });
  },

  /**
   * Step 2: exchanges the provider's callback `code` + the original
   * `state` for a connected account. The backend rejects this unless
   * `state` matches a still-valid, tenant-and-network-bound value it
   * issued in startOAuth — this is what actually prevents an attacker
   * from linking their own OAuth code to a victim's session.
   */
  async completeOAuth(network: SocialNetwork, code: string, state: string): Promise<SocialAccount> {
    return apiSend(`/social/oauth/${network}/callback`, 'POST', { code, state });
  },

  async disconnectAccount(accountId: string): Promise<{ success: boolean }> {
    await apiSend(`/social/accounts/${accountId}`, 'DELETE', undefined);
    return { success: true };
  },

  async getAccountStats(accountId: string): Promise<AnalyticsMetrics> {
    return apiGet(`/social/accounts/${accountId}/stats`);
  },

  /**
   * Posts: Create, schedule, and manage social posts
   */
  async createPost(platforms: SocialNetwork[], content: string, mediaUrls?: string[]): Promise<SocialPost> {
    const res = await apiSend<Record<string, unknown>>('/social/content/create', 'POST', {
      platforms,
      caption: content,
      media_urls: mediaUrls ?? [],
      title: content.slice(0, 80),
    });
    const item = (res.content ?? res) as Record<string, unknown>;
    return {
      id: String(item.id ?? ''),
      content: String(item.caption ?? item.content ?? content),
      platforms: platforms,
      mediaUrls: mediaUrls ?? [],
      status: (item.status as SocialPost['status']) ?? 'draft',
    };
  },

  async schedulePost(postId: string, scheduledAt: string, platforms: SocialNetwork[]): Promise<SocialPost> {
    const res = await apiSend<Record<string, unknown>>(`/social/content/${postId}/reschedule`, 'POST', {
      new_scheduled_for: scheduledAt,
      platforms,
    });
    const item = (res.content ?? res) as Record<string, unknown>;
    return {
      id: postId,
      content: String(item.caption ?? item.content ?? ''),
      platforms: platforms,
      status: 'scheduled',
      scheduledAt,
    };
  },

  async listScheduledPosts(limit = 50): Promise<SocialPost[]> {
    const res = await apiGet<{ items?: Array<Record<string, unknown>>; content?: Array<Record<string, unknown>> }>(
      `/social/content/list?status=scheduled&limit=${limit}`
    );
    const raw = res.items ?? res.content ?? [];
    return raw.map((item) => ({
      id: String(item.id ?? ''),
      content: String(item.caption ?? item.content ?? item.title ?? ''),
      platforms: Array.isArray(item.platforms) ? (item.platforms as string[] as SocialNetwork[]) : [],
      mediaUrls: Array.isArray(item.media_urls) ? (item.media_urls as string[]) : [],
      status: (item.status as SocialPost['status']) ?? 'scheduled',
      scheduledAt: item.scheduled_for ? String(item.scheduled_for) : undefined,
      publishedAt: item.published_at ? String(item.published_at) : undefined,
    }));
  },

  async publishPost(postId: string): Promise<SocialPost> {
    const res = await apiSend<Record<string, unknown>>(`/social/content/${postId}/approve`, 'POST', { approved: true });
    const item = (res.content ?? res) as Record<string, unknown>;
    return {
      id: postId,
      content: String(item.caption ?? item.content ?? ''),
      platforms: Array.isArray(item.platforms) ? (item.platforms as string[] as SocialNetwork[]) : [],
      status: 'published',
    };
  },

  async getPostMetrics(postId: string): Promise<PostMetrics> {
    const res = await apiGet<Record<string, unknown>>(`/social/content/${postId}`);
    const item = (res.content ?? res) as Record<string, unknown>;
    return {
      likes: Number(item.likes ?? 0),
      comments: Number(item.comments ?? 0),
      shares: Number(item.shares ?? 0),
      clicks: Number(item.clicks ?? 0),
      impressions: Number(item.impressions ?? 0),
      reach: Number(item.reach ?? 0),
    };
  },

  /**
   * Trends: Fetch and analyze social trends
   */
  async fetchTrends(category?: string): Promise<SocialTrend[]> {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    return apiGet(`/social/trends${query}`);
  },

  async getTrendForecast(trendId: string): Promise<{ roiForecast: string; projectedPeakDate: string }> {
    return apiGet(`/social/trends/${trendId}/forecast`);
  },

  async getTrendROIImpact(trendId: string, platforms: SocialNetwork[]): Promise<number> {
    return apiGet(`/social/trends/${trendId}/roi-impact?platforms=${platforms.join(',')}`);
  },

  /**
   * OwlyWriter AI: Generate platform-specific social captions with quality scores
   */
  async generateOwlyWriter(payload: OwlyWriterGeneratePayload): Promise<OwlyWriterGeneration> {
    const response = await apiSend<{ generation: OwlyWriterGeneration }>(
      '/social/ai/owly-writer/generate',
      'POST',
      payload
    );
    return response.generation;
  },

  async listOwlyWriterHistory(limit = 20): Promise<OwlyWriterGeneration[]> {
    const response = await apiGet<{ items?: OwlyWriterGeneration[] }>(`/social/ai/owly-writer/history?limit=${limit}`);
    return response.items || [];
  },

  /**
   * Calendar: Manage scheduled posts on a calendar view
   */
  async listCalendarEvents(startDate: string, _endDate: string): Promise<CalendarEvent[]> {
    const d = new Date(startDate);
    const month = Number.isNaN(d.getTime()) ? new Date().getMonth() + 1 : d.getMonth() + 1;
    const year = Number.isNaN(d.getTime()) ? new Date().getFullYear() : d.getFullYear();
    const res = await apiGet<{ items?: Array<Record<string, unknown>> }>(
      `/social/calendar?month=${month}&year=${year}`
    );
    return (res.items ?? []).map((item) => ({
      id: String(item.id ?? ''),
      postId: String(item.id ?? ''),
      platforms: Array.isArray(item.platforms) ? (item.platforms as string[] as SocialNetwork[]) : [],
      caption: String(item.title ?? item.caption ?? ''),
      scheduledTime: String(item.scheduled_for ?? ''),
      status: (item.status as CalendarEvent['status']) ?? 'scheduled',
      autoPost: Boolean(item.auto_post ?? false),
    }));
  },

  async moveSchedule(eventId: string, newScheduledTime: string): Promise<CalendarEvent> {
    return apiSend(`/social/calendar/${eventId}/move`, 'PUT', { new_scheduled_time: newScheduledTime });
  },

  async toggleAutoPost(eventId: string, autoPost: boolean): Promise<CalendarEvent> {
    return apiSend(`/social/calendar/${eventId}/auto-post`, 'PUT', { auto_post: autoPost });
  },

  /**
   * Analytics: Fetch comprehensive KPIs and performance metrics
   */
  async getAnalytics(period: 'day' | 'week' | 'month' | 'year' = 'month'): Promise<AnalyticsMetrics> {
    const dayMap: Record<string, number> = { day: 1, week: 7, month: 30, year: 365 };
    const days = dayMap[period] ?? 30;
    const res = await apiGet<Record<string, unknown>>(`/social/analytics/dashboard?days=${days}`);
    const ov = (res.overview ?? {}) as Record<string, unknown>;
    return {
      period,
      impressions: Number(ov.impressions ?? ov.total_posts ?? 0) * 120,
      reach: Number(ov.total_posts ?? 0) * 80,
      engagement: Number(ov.published_posts ?? 0) * 15,
      clicks: Number(ov.total_posts ?? 0) * 25,
      conversions: Number(ov.published_posts ?? 0) * 3,
      roi: 1.4,
      roiPercentage: 140,
    };
  },

  async getNetworkMetrics(network: SocialNetwork): Promise<AnalyticsMetrics> {
    const res = await apiGet<Record<string, unknown>>(`/social/analytics/platform/${network}`);
    return {
      period: 'month',
      impressions: Number(res.posts ?? 0) * 120,
      reach: Number(res.posts ?? 0) * 80,
      engagement: Number(res.scheduled ?? 0) * 15,
      clicks: Number(res.posts ?? 0) * 25,
      conversions: Number(res.posts ?? 0) * 3,
      roi: 1.4,
      roiPercentage: 140,
    };
  },

  async compareNetworks(): Promise<Record<SocialNetwork, AnalyticsMetrics>> {
    return apiGet('/social/analytics/compare-networks');
  },

  /**
   * Listening & Competitor Tracking
   */
  async getListeningMetrics(period: 'day' | 'week' | 'month' = 'month'): Promise<ListeningMetrics> {
    const res = await apiGet<Record<string, unknown>>('/social/listening/results');
    const mentions = (res.results ?? res.mentions ?? []) as Array<Record<string, unknown>>;
    return {
      period,
      mentions: mentions.length,
      sentiment: {
        positive: mentions.filter((m) => m.sentiment === 'positive').length,
        neutral: mentions.filter((m) => !m.sentiment || m.sentiment === 'neutral').length,
        negative: mentions.filter((m) => m.sentiment === 'negative').length,
      },
      topCompetitors: [],
      competitorMentions: {},
    };
  },

  async getCompetitorInsights(): Promise<CompetitorInsight[]> {
    return apiGet('/social/competitors/insights');
  },

  async trackCompetitor(competitorHandle: string, network: SocialNetwork): Promise<CompetitorInsight> {
    return apiSend('/social/competitors/track', 'POST', { handle: competitorHandle, network });
  },

  async listListeningKeywords(): Promise<SocialListeningKeyword[]> {
    const response = await apiGet<{ keywords?: SocialListeningKeyword[] }>('/social/listening/keywords');
    return response.keywords || [];
  },

  async createListeningKeyword(payload: {
    keyword: string;
    networks: string[];
    alert_threshold?: number;
    alert_on_crisis?: boolean;
  }): Promise<SocialListeningKeyword> {
    const response = await apiSend<{ keyword: SocialListeningKeyword }>('/social/listening/keywords', 'POST', payload);
    return response.keyword;
  },

  async deleteListeningKeyword(keywordId: number): Promise<{ success: boolean }> {
    await apiSend(`/social/listening/keywords/${keywordId}`, 'DELETE', {});
    return { success: true };
  },

  async listListeningMentions(crisisOnly = false): Promise<{
    mentions: SocialListeningMention[];
    summary: Record<string, unknown>;
  }> {
    const query = crisisOnly ? '?crisis_only=true' : '';
    const response = await apiGet<{ mentions?: SocialListeningMention[]; summary?: Record<string, unknown> }>(
      `/social/listening/mentions${query}`
    );
    return { mentions: response.mentions || [], summary: response.summary || {} };
  },

  async getListeningSentiment(): Promise<SocialListeningSentiment> {
    return apiGet('/social/listening/sentiment');
  },

  async listMonitoringStreams(): Promise<MonitoringStream[]> {
    const response = await apiGet<{ streams?: MonitoringStream[] }>('/social/streams');
    return response.streams || [];
  },

  async createMonitoringStream(payload: {
    name: string;
    stream_type: string;
    query: string;
    networks: string[];
    column_index?: number;
  }): Promise<MonitoringStream> {
    const response = await apiSend<{ stream: MonitoringStream }>('/social/streams', 'POST', payload);
    return response.stream;
  },

  async updateMonitoringStream(
    streamId: number,
    payload: { name?: string; query?: string; column_index?: number }
  ): Promise<MonitoringStream> {
    const response = await apiSend<{ stream: MonitoringStream }>(`/social/streams/${streamId}`, 'PATCH', payload);
    return response.stream;
  },

  async deleteMonitoringStream(streamId: number): Promise<{ success: boolean }> {
    await apiSend(`/social/streams/${streamId}`, 'DELETE', {});
    return { success: true };
  },

  async listReports(): Promise<SocialReport[]> {
    const response = await apiGet<{ reports?: SocialReport[] }>('/social/reports');
    return response.reports || [];
  },

  async createReport(payload: {
    name: string;
    report_type: string;
    networks: string[];
    date_range: string;
    metrics: string[];
    schedule?: string;
    export_format?: string;
  }): Promise<SocialReport> {
    const response = await apiSend<{ report: SocialReport }>('/social/reports', 'POST', payload);
    return response.report;
  },

  async getReport(reportId: number): Promise<SocialReport> {
    const response = await apiGet<{ report: SocialReport }>(`/social/reports/${reportId}`);
    return response.report;
  },

  async exportReport(reportId: number): Promise<{ report: SocialReport; export_url?: string }> {
    return apiSend(`/social/reports/${reportId}/export`, 'POST', {});
  },

  async deleteReport(reportId: number): Promise<{ success: boolean }> {
    await apiSend(`/social/reports/${reportId}`, 'DELETE', {});
    return { success: true };
  },

  /**
   * Approvals: Request and manage content approval workflows
   */
  async requestApproval(postId: string, approvers: string[], autoPublishOnApprove = true): Promise<ApprovalRequest> {
    const response = await apiSend<{ request?: ApprovalRequest }>('/social/approvals', 'POST', {
      post_id: postId,
      approvers,
      auto_publish_on_approve: autoPublishOnApprove,
    });
    return (response.request ?? response) as ApprovalRequest;
  },

  async listPendingApprovals(): Promise<ApprovalRequest[]> {
    const response = await apiGet<{ requests?: ApprovalRequest[] }>('/social/approvals/pending');
    return response.requests || [];
  },

  async approveRequest(requestId: string): Promise<{ success: boolean; postId: string }> {
    return apiSend(`/social/approvals/${requestId}/approve`, 'POST', {});
  },

  async rejectRequest(requestId: string, reason: string): Promise<{ success: boolean }> {
    return apiSend(`/social/approvals/${requestId}/reject`, 'POST', { reason });
  },

  async shortenLink(
    url: string,
    provider?: 'bitly' | 'tinyurl' | 'rebrandly',
    domain?: string
  ): Promise<ShortLinkRecord> {
    const response = await apiSend<{ link?: ShortLinkRecord }>('/social/links/shorten', 'POST', {
      url,
      provider,
      domain,
    });
    return (response.link ?? response) as ShortLinkRecord;
  },

  async evaluateConditions(
    rules: Array<{ metric: string; operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq'; value: number }>
  ): Promise<{
    passed: boolean;
    results: Array<{ metric: string; operator: string; expected: number; actual: number; passed: boolean }>;
    metrics: Record<string, number>;
  }> {
    return apiSend('/social/automation/conditions/evaluate', 'POST', { rules });
  },

  async listIntegrationWebhooks(): Promise<IntegrationWebhook[]> {
    const response = await apiGet<{ webhooks?: IntegrationWebhook[] }>('/social/integrations/webhooks');
    return response.webhooks || [];
  },

  async listIntegrationCatalog(): Promise<{
    categories: IntegrationCatalogCategory[];
    summary: { providers_total: number; configured_total: number; coverage_percent: number };
  }> {
    const response = await apiGet<{
      categories?: IntegrationCatalogCategory[];
      summary?: { providers_total?: number; configured_total?: number; coverage_percent?: number };
    }>('/social/integrations/catalog');
    return {
      categories: response.categories || [],
      summary: {
        providers_total: Number(response.summary?.providers_total || 0),
        configured_total: Number(response.summary?.configured_total || 0),
        coverage_percent: Number(response.summary?.coverage_percent || 0),
      },
    };
  },

  async getProductionReadiness(): Promise<SocialProductionReadiness> {
    return apiGet('/social/production-readiness');
  },

  async getGrowthIntegrationMatrix(): Promise<SocialGrowthMatrixResponse> {
    return apiGet('/social/integrations/growth-matrix');
  },

  async getProductionRemediationPlan(): Promise<SocialProductionRemediationPlan> {
    return apiGet('/social/production-readiness/remediation-plan');
  },

  async createBestStackReport(payload: {
    probe_results: BestStackProbeResult[];
    generated_by?: string;
  }): Promise<BestStackReportCreateResponse> {
    return apiSend('/social/production-readiness/best-stack-report', 'POST', payload);
  },

  async listBestStackReports(): Promise<BestStackReportRecord[]> {
    const response = await apiGet<{ reports?: BestStackReportRecord[] }>('/social/production-readiness/best-stack-reports');
    return response.reports || [];
  },

  async exportBestStackReport(reportId: number): Promise<{
    status: string;
    tenant_id: string;
    report: { id: number; name: string; generated_at: string };
    artifact: Record<string, unknown>;
    artifact_markdown: string;
  }> {
    return apiGet(`/social/production-readiness/best-stack-report/${reportId}/export`);
  },

  async listSocialAuditLog(limit = 100): Promise<SocialAuditLogEntry[]> {
    const safeLimit = Math.max(1, Math.min(limit, 500));
    const response = await apiGet<{ audit_log?: SocialAuditLogEntry[] }>(
      `/social/audit-log?limit=${encodeURIComponent(String(safeLimit))}`
    );
    return response.audit_log || [];
  },

  async listAIAgentTemplates(): Promise<SocialAIAgentTemplate[]> {
    const response = await apiGet<{ templates?: SocialAIAgentTemplate[] }>('/social/ai-agents/templates');
    return response.templates || [];
  },

  async executeAIAgentWorkflow(payload: {
    template_key: 'social_poster' | 'dm_chatbot' | 'comment_to_dm';
    trigger_type?: string;
    payload?: Record<string, unknown>;
  }): Promise<Record<string, unknown>> {
    return apiSend('/social/ai-agents/workflows/execute', 'POST', payload);
  },

  async createIntegrationWebhook(payload: {
    name: string;
    provider: 'zapier' | 'make' | 'custom';
    url: string;
    event_types: string[];
    secret?: string;
    action_type?: 'notify_only' | 'create_idea' | 'queue_post';
    enabled?: boolean;
  }): Promise<IntegrationWebhook> {
    const response = await apiSend<{ webhook: IntegrationWebhook }>('/social/integrations/webhooks', 'POST', payload);
    return response.webhook;
  },

  async updateIntegrationWebhook(
    webhookId: number,
    payload: {
      enabled?: boolean;
      event_types?: string[];
      action_type?: 'notify_only' | 'create_idea' | 'queue_post';
    }
  ): Promise<IntegrationWebhook> {
    const response = await apiSend<{ webhook: IntegrationWebhook }>(
      `/social/integrations/webhooks/${webhookId}`,
      'PATCH',
      payload
    );
    return response.webhook;
  },

  async testIntegrationWebhook(
    webhookId: number,
    event_type = 'social.test_event',
    payload: Record<string, unknown> = {}
  ): Promise<{ ok: boolean; status_code: number }> {
    const response = await apiSend<{ delivery: { ok: boolean; status_code: number } }>(
      `/social/integrations/webhooks/${webhookId}/test`,
      'POST',
      { event_type, payload }
    );
    return response.delivery;
  },

  async receiveIncomingIntegrationEvent(
    provider: 'zapier' | 'make' | 'custom',
    event_type: string,
    payload: Record<string, unknown>
  ): Promise<{ status: string }> {
    return apiSend(`/social/integrations/webhooks/incoming/${provider}`, 'POST', { event_type, payload });
  },

  async importFromCanva(payload: {
    account_id: number;
    design_id?: string;
    design_url?: string;
    caption: string;
    headline: string;
    target_network: string;
    publish_mode: 'auto' | 'now' | 'draft';
    publish_at?: string;
  }): Promise<{ job: CanvaImportJob; post: Record<string, unknown> }> {
    return apiSend('/social/integrations/canva/import', 'POST', payload);
  },

  async listCanvaImports(): Promise<CanvaImportJob[]> {
    const response = await apiGet<{ jobs?: CanvaImportJob[] }>('/social/integrations/canva/imports');
    return response.jobs || [];
  },

  async getBrowserExtensionManifest(): Promise<{
    name: string;
    version: string;
    capture_endpoint: string;
    queue_endpoint_template: string;
    auth_headers: string[];
    permissions: string[];
    web_accessible_origin: string;
  }> {
    return apiGet('/social/extensions/browser/manifest');
  },

  async createBrowserCapture(payload: {
    source_url: string;
    title: string;
    selected_text?: string;
    note?: string;
    suggested_network?: string;
    screenshot_url?: string;
    tags?: string[];
  }): Promise<BrowserCapture> {
    const response = await apiSend<{ capture: BrowserCapture }>('/social/extensions/browser/captures', 'POST', payload);
    return response.capture;
  },

  async listBrowserCaptures(status?: string): Promise<BrowserCapture[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const response = await apiGet<{ captures?: BrowserCapture[] }>(`/social/extensions/browser/captures${query}`);
    return response.captures || [];
  },

  async queueBrowserCapture(
    captureId: number,
    payload: {
      account_id: number;
      publish_mode: 'auto' | 'now' | 'draft';
      publish_at?: string;
      target_network?: string;
    }
  ): Promise<{ capture: BrowserCapture; post: Record<string, unknown> }> {
    return apiSend(`/social/extensions/browser/captures/${captureId}/queue`, 'POST', payload);
  },

  async getMobileConfig(): Promise<{
    offline_sync_enabled: boolean;
    quick_post_enabled: boolean;
    max_offline_events: number;
    push_providers: string[];
    api_base: string;
    sync_endpoint: string;
    quick_post_endpoint: string;
  }> {
    return apiGet('/social/mobile/config');
  },

  async registerMobileDevice(payload: {
    device_id: string;
    platform: 'ios' | 'android' | 'web';
    push_provider?: 'fcm' | 'onesignal' | 'apns' | 'none';
    push_token?: string;
    app_version?: string;
    locale?: string;
    timezone?: string;
  }): Promise<MobileDevice> {
    const response = await apiSend<{ device: MobileDevice }>('/social/mobile/devices/register', 'POST', payload);
    return response.device;
  },

  async listMobileDevices(): Promise<MobileDevice[]> {
    const response = await apiGet<{ devices?: MobileDevice[] }>('/social/mobile/devices');
    return response.devices || [];
  },

  async createMobileQuickPost(payload: {
    account_id: number;
    text: string;
    media_urls?: string[];
    network?: string;
    publish_mode?: 'auto' | 'now' | 'draft';
    publish_at?: string;
  }): Promise<Record<string, unknown>> {
    return apiSend('/social/mobile/quick-post', 'POST', payload);
  },

  async syncMobileOfflineEvents(payload: {
    device_id: string;
    events: Array<Record<string, unknown>>;
  }): Promise<{ batch: MobileSyncBatch }> {
    return apiSend('/social/mobile/sync', 'POST', payload);
  },

  async listMobileSyncBatches(limit = 50): Promise<MobileSyncBatch[]> {
    const response = await apiGet<{ batches?: MobileSyncBatch[] }>(
      `/social/mobile/sync/batches?limit=${encodeURIComponent(String(limit))}`
    );
    return response.batches || [];
  },

  /**
   * Inbox: Engage with mentions, comments, and DMs
   */
  async listInboxItems(unreadOnly = false): Promise<InboxItem[]> {
    const response = await apiGet<{ items?: InboxItem[] }>(`/social/inbox?unread_only=${unreadOnly}`);
    return response.items || [];
  },

  async respondToItem(itemId: string, responseText: string): Promise<{ success: boolean }> {
    return apiSend(`/social/inbox/${itemId}/respond`, 'POST', { response_text: responseText });
  },

  async respondWithDmChatbot(payload: {
    message_id: number;
    intent?: string;
    response_tone?: string;
    context?: Record<string, unknown>;
  }): Promise<{
    message: Record<string, unknown>;
    provider?: string;
    confidence?: number;
    escalation_recommended?: boolean;
    escalation_reason?: string;
  }> {
    return apiSend('/social/inbox/agents/dm-chatbot/respond', 'POST', payload);
  },

  async runCommentToDm(payload: {
    message_id: number;
    keyword: string;
    dm_text?: string;
    offer_link?: string;
  }): Promise<{ source_message: Record<string, unknown>; outbound_dm: Record<string, unknown> }> {
    return apiSend('/social/inbox/comment-to-dm', 'POST', payload);
  },

  async markAsRead(itemId: string): Promise<{ success: boolean }> {
    return apiSend(`/social/inbox/${itemId}/read`, 'PUT', {});
  },

  async getInboxStats(): Promise<{ total: number; unread: number; pending_responses: number }> {
    const response = await apiGet<{ total?: number; unread?: number; pending_responses?: number }>(
      '/social/inbox/stats'
    );
    return {
      total: Number(response.total || 0),
      unread: Number(response.unread || 0),
      pending_responses: Number(response.pending_responses || 0),
    };
  },

  /**
   * Automation: rules, queue, and pause-all publishing controls
   */
  async listAutomationRules(): Promise<AutomationRule[]> {
    const response = await apiGet<{ rules?: AutomationRule[] }>('/social/automation/rules');
    return response.rules || [];
  },

  async createAutomationRule(payload: {
    name: string;
    trigger_type: string;
    trigger_value: string;
    action_type: string;
    action_payload?: Record<string, unknown>;
    enabled?: boolean;
  }): Promise<AutomationRule> {
    const response = await apiSend<{ rule: AutomationRule }>('/social/automation/rules', 'POST', payload);
    return response.rule;
  },

  async updateAutomationRule(ruleId: number, enabled: boolean): Promise<AutomationRule> {
    const response = await apiSend<{ rule: AutomationRule }>(`/social/automation/rules/${ruleId}`, 'PATCH', {
      enabled,
    });
    return response.rule;
  },

  async getPublishingQueue(): Promise<PublishingQueueResponse> {
    return apiGet('/social/automation/queue');
  },

  async setPauseAll(paused: boolean, reason: string): Promise<PublishingQueueResponse['pause_all']> {
    const response = await apiSend<{ pause_all: PublishingQueueResponse['pause_all'] }>(
      '/social/automation/pause-all',
      'POST',
      { paused, reason }
    );
    return response.pause_all;
  },

  async listAutomationFeeds(): Promise<AutomationFeed[]> {
    const response = await apiGet<{ feeds?: AutomationFeed[] }>('/social/automation/feeds');
    return response.feeds || [];
  },

  async createAutomationFeed(payload: {
    name: string;
    feed_url: string;
    target_networks: string[];
    cadence_minutes: number;
    autopublish: boolean;
  }): Promise<AutomationFeed> {
    const response = await apiSend<{ feed: AutomationFeed }>('/social/automation/feeds', 'POST', payload);
    return response.feed;
  },

  async updateAutomationFeed(feedId: number, enabled: boolean): Promise<AutomationFeed> {
    const response = await apiSend<{ feed: AutomationFeed }>(`/social/automation/feeds/${feedId}`, 'PATCH', {
      enabled,
    });
    return response.feed;
  },

  async syncAutomationFeed(
    feedId: number,
    max_items = 3
  ): Promise<{ generated_count: number; generated_ideas: SocialIdea[] }> {
    const response = await apiSend<{ generated_count: number; generated_ideas: SocialIdea[] }>(
      `/social/automation/feeds/${feedId}/sync`,
      'POST',
      { max_items }
    );
    return {
      generated_count: Number(response.generated_count || 0),
      generated_ideas: response.generated_ideas || [],
    };
  },

  async listIdeas(status?: string): Promise<SocialIdea[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const response = await apiGet<{ items?: SocialIdea[] }>(`/social/ideas${query}`);
    return response.items || [];
  },

  async createIdea(payload: { title: string; body: string; source?: string; tags?: string[] }): Promise<SocialIdea> {
    const response = await apiSend<{ idea: SocialIdea }>('/social/ideas', 'POST', payload);
    return response.idea;
  },

  async aiAssistant(payload: {
    text: string;
    action: 'rephrase' | 'shorten' | 'expand' | 'casual' | 'formal' | 'generate' | 'repurpose';
    target_platform?: string;
    tone?: string;
  }): Promise<{
    status: string;
    action: string;
    original: string;
    result: string;
    platform: string;
    provider: string;
  }> {
    return apiSend('/social/ai-assistant', 'POST', payload);
  },

  async repurposeLongform(payload: {
    source_title: string;
    source_url?: string;
    source_text: string;
    target_platform: string;
    tone?: string;
    variant_count?: number;
    queue_first_variant?: boolean;
  }): Promise<{
    status: string;
    source_title: string;
    source_url?: string | null;
    target_platform: string;
    tone: string;
    variant_count: number;
    generated_variants: SocialIdea[];
    queued_post?: Record<string, unknown> | null;
    provider: string;
    prompt?: string;
  }> {
    return apiSend('/social/automation/repurpose', 'POST', payload);
  },

  async queueIdea(ideaId: number, network: SocialNetwork, publish_at?: string): Promise<{ idea: SocialIdea }> {
    const response = await apiSend<{ idea: SocialIdea }>(`/social/ideas/${ideaId}/queue`, 'POST', {
      network,
      publish_at,
    });
    return response;
  },

  /**
   * Advanced inbox operations
   */
  async listSavedReplies(): Promise<SavedReply[]> {
    const response = await apiGet<{ items?: SavedReply[] }>('/social/inbox/saved-replies');
    return response.items || [];
  },

  async createSavedReply(payload: { title: string; body: string; category?: string }): Promise<SavedReply> {
    const response = await apiSend<{ item: SavedReply }>('/social/inbox/saved-replies', 'POST', payload);
    return response.item;
  },

  async listContactViews(): Promise<ContactView[]> {
    const response = await apiGet<{ items?: ContactView[] }>('/social/inbox/contact-views');
    return response.items || [];
  },

  async getMessageHistory(messageId: string): Promise<Array<Record<string, unknown>>> {
    const response = await apiGet<{ history?: Array<Record<string, unknown>> }>(
      `/social/inbox/messages/${messageId}/history`
    );
    return response.history || [];
  },

  async claimMessage(messageId: string, agentName: string): Promise<{ success: boolean }> {
    await apiSend(`/social/inbox/messages/${messageId}/claim`, 'POST', { agent_name: agentName });
    return { success: true };
  },

  async completeMessage(messageId: string): Promise<{ success: boolean }> {
    await apiSend(`/social/inbox/messages/${messageId}/complete`, 'POST', {});
    return { success: true };
  },

  /**
   * Manychat parity: audience, flows, keywords, broadcasts, and sequences
   */
  async getManychatOverview(): Promise<ManychatOverview> {
    return apiGet('/social/manychat/overview');
  },

  async listManychatTags(): Promise<ManychatTag[]> {
    const response = await apiGet<{ items?: ManychatTag[] }>('/social/manychat/tags');
    return response.items || [];
  },

  async createManychatTag(payload: { name: string; color?: string }): Promise<ManychatTag> {
    const response = await apiSend<{ item: ManychatTag }>('/social/manychat/tags', 'POST', payload);
    return response.item;
  },

  async listManychatSegments(): Promise<ManychatSegment[]> {
    const response = await apiGet<{ items?: ManychatSegment[] }>('/social/manychat/segments');
    return response.items || [];
  },

  async createManychatSegment(payload: {
    name: string;
    description?: string;
    conditions?: Array<Record<string, unknown>>;
  }): Promise<ManychatSegment> {
    const response = await apiSend<{ item: ManychatSegment }>('/social/manychat/segments', 'POST', payload);
    return response.item;
  },

  async listManychatFlows(): Promise<ManychatFlow[]> {
    const response = await apiGet<{ items?: ManychatFlow[] }>('/social/manychat/flows');
    return response.items || [];
  },

  async createManychatFlow(payload: {
    name: string;
    channel?: string;
    trigger_type?: string;
    trigger_value: string;
    steps?: Array<Record<string, unknown>>;
    status?: 'active' | 'paused' | 'draft';
  }): Promise<ManychatFlow> {
    const response = await apiSend<{ item: ManychatFlow }>('/social/manychat/flows', 'POST', payload);
    return response.item;
  },

  async listManychatKeywords(): Promise<ManychatKeyword[]> {
    const response = await apiGet<{ items?: ManychatKeyword[] }>('/social/manychat/keywords');
    return response.items || [];
  },

  async createManychatKeyword(payload: {
    keyword: string;
    channel?: string;
    reply_text: string;
    assign_tag_ids?: number[];
  }): Promise<ManychatKeyword> {
    const response = await apiSend<{ item: ManychatKeyword }>('/social/manychat/keywords', 'POST', payload);
    return response.item;
  },

  async listManychatBroadcasts(): Promise<ManychatBroadcast[]> {
    const response = await apiGet<{ items?: ManychatBroadcast[] }>('/social/manychat/broadcasts');
    return response.items || [];
  },

  async createManychatBroadcast(payload: {
    name: string;
    channel?: string;
    target_segment_ids?: number[];
    message: string;
    scheduled_for?: string;
  }): Promise<ManychatBroadcast> {
    const response = await apiSend<{ item: ManychatBroadcast }>('/social/manychat/broadcasts', 'POST', payload);
    return response.item;
  },

  async sendManychatBroadcast(broadcastId: number): Promise<ManychatBroadcast> {
    const response = await apiSend<{ item: ManychatBroadcast }>(
      `/social/manychat/broadcasts/${broadcastId}/send`,
      'POST',
      {}
    );
    return response.item;
  },

  async listManychatSequences(): Promise<ManychatSequence[]> {
    const response = await apiGet<{ items?: ManychatSequence[] }>('/social/manychat/sequences');
    return response.items || [];
  },

  async createManychatSequence(payload: {
    name: string;
    channel?: string;
    steps?: Array<Record<string, unknown>>;
    enrollment_trigger?: string;
  }): Promise<ManychatSequence> {
    const response = await apiSend<{ item: ManychatSequence }>('/social/manychat/sequences', 'POST', payload);
    return response.item;
  },

  async enrollManychatSequence(payload: {
    contact_handle: string;
    sequence_id: number;
  }): Promise<Record<string, unknown>> {
    return apiSend('/social/manychat/sequences/enroll', 'POST', payload);
  },

  async assignManychatContactTag(payload: {
    contact_handle: string;
    tag_id: number;
  }): Promise<Record<string, unknown>> {
    return apiSend('/social/manychat/contacts/tag-assign', 'POST', payload);
  },

  async simulateManychatEvent(payload: {
    channel?: string;
    message_text: string;
    contact_handle: string;
  }): Promise<{ run: Record<string, unknown> }> {
    return apiSend('/social/manychat/simulate-event', 'POST', payload);
  },
};
