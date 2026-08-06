'use client';
/* eslint-disable react/no-array-index-key, sonarjs/no-nested-conditional */
/* sonarlint-disable */

import { useState, useCallback, useEffect, useRef } from 'react';
import { onCLS, onINP, onLCP, onTTFB, type Metric } from 'web-vitals';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

// ─── Types ────────────────────────────────────────────────────────────────────

type CoreWebVitals = { lcp_ms?: number; inp_ms?: number; cls?: number; ttfb_ms?: number };
type FieldWebVitals = {
  lcp_p75_ms?: number;
  inp_p75_ms?: number;
  cls_p75?: number;
  sample_size?: number;
  period?: string;
  source?: string;
};
type Lighthouse = { performance?: number; seo?: number; best_practices?: number; accessibility?: number };
type WaterfallTimeline = { dns?: number; tcp?: number; tls?: number; ttfb?: number; download?: number };
type Waterfall = {
  requests?: number;
  transfer_kb?: number;
  render_blocking?: string[];
  timeline_ms?: WaterfallTimeline;
};
type FilmstripFrame = { label?: string; timestamp_ms?: number; asset?: string };
type RumGeoIspPoint = { country?: string; region?: string; isp?: string; lcp_p75_ms?: number; sample_size?: number };
type RumSummary = {
  sessions?: number;
  rage_click_rate?: number;
  friction_score?: number;
  device_mix?: Record<string, number>;
  network_mix?: Record<string, number>;
  geo_isp_breakdown?: RumGeoIspPoint[];
};
type CausalityGraph = {
  root_causes?: string[];
  render_blocking_attribution?: Array<{ asset?: string; block_ms?: number; phase?: string; severity?: string }>;
  third_party_impact?: Array<{
    provider?: string;
    main_thread_block_ms?: number;
    network_ms?: number;
    category?: string;
    removable?: boolean;
  }>;
  dependencies?: Array<{ from?: string; to?: string; latency_ms?: number }>;
  main_thread_timeline?: Array<{ task?: string; duration_ms?: number; type?: string }>;
  critical_path_ms?: number;
  wasted_ms?: number;
};
type AutonomousAgents = {
  coverage_score?: number;
  journeys_tested?: string[];
  scenario_mutations?: number;
  failure_hotspots?: Array<{ journey?: string; step?: string; p95_ms?: number }>;
  journey_metrics?: Array<{
    journey?: string;
    p50_ms?: number;
    p75_ms?: number;
    p95_ms?: number;
    pass_rate?: number;
    runs?: number;
  }>;
  mutation_matrix?: Array<{ scenario?: string; passed?: number; failed?: number; flaky?: number }>;
  agent_health?: { total_agents?: number; healthy?: number; degraded?: number; offline?: number };
  deviation_from_baseline?: Array<{ metric?: string; baseline_ms?: number; current_ms?: number; delta_pct?: number }>;
};
type PredictiveIntelligence = {
  forecast_horizon_days?: number;
  forecast?: { lcp_ms?: number; inp_ms?: number; cls?: number };
  regression_risk?: { label?: string; probability?: number; contributing_factors?: string[] };
  pre_deploy_guardrail?: { predicted_lcp_delta_ms?: number; status?: string; confidence?: number };
  weekly_trend?: Array<{ week?: string; lcp_ms?: number; score?: number }>;
  ai_recommendations?: string[];
  deploy_confidence?: number;
  anomaly_forecast?: Array<{ metric?: string; expected_breach_date?: string; severity?: string }>;
};
type GlobalSimulation = {
  coverage_regions?: number;
  isp_profiles_tested?: number;
  network_profiles?: string[];
  hotspots?: Array<{ region?: string; network?: string; lcp_ms?: number }>;
  region_grid?: Array<{
    region?: string;
    country?: string;
    lcp_p75_ms?: number;
    fcp_ms?: number;
    ttfb_ms?: number;
    network?: string;
    pass?: boolean;
  }>;
  cdn_pop_latency?: Array<{ pop?: string; latency_ms?: number }>;
  best_region?: string;
  worst_region?: string;
  global_p75_lcp_ms?: number;
};
type FullStackObservability = {
  frontend_to_backend_trace?: { p95_ms?: number; slow_span?: string };
  api_latency_p95_ms?: number;
  db_query_p95_ms?: number;
  cdn?: { hit_rate?: number; miss_penalty_ms?: number };
  infra?: { cpu_spike_corr?: number; error_burst_corr?: number };
};
type BusinessImpact = {
  conversion_delta_per_100ms?: number;
  estimated_monthly_revenue_at_risk_usd?: number;
  seo_rank_sensitivity?: { top3_drop_risk?: number; traffic_delta_pct?: number; rank_delta?: number };
  bounce_probability?: number;
  priority?: string;
  segment_impact?: Array<{ segment?: string; conversion_rate?: number; revenue_usd?: number; lcp_ms?: number }>;
  competitor_rank_risk?: Array<{ competitor?: string; rank?: number; gap_ms?: number }>;
  revenue_waterfall?: Array<{ fix?: string; gain_usd?: number; effort?: string }>;
  annualized_at_risk_usd?: number;
};
type CiGate = {
  status?: string;
  predicted_pr_impact?: { lcp_delta_ms?: number; inp_delta_ms?: number; cls_delta?: number };
  budget?: { lcp_ms?: number; inp_ms?: number; cls?: number };
  recommendation?: string;
  pr_diff_analysis?: Array<{ file?: string; size_delta_kb?: number; impact?: string; severity?: string }>;
  gate_history?: Array<{ pr?: string; status?: string; lcp_delta_ms?: number; merged?: boolean }>;
  blocking_rules?: Array<{ rule?: string; threshold?: string; current?: string; pass?: boolean }>;
  bundle_analysis?: { total_kb?: number; delta_kb?: number; new_deps?: string[] };
};
type SloGuardrails = {
  overall?: string;
  slo_targets?: { lcp_p75_ms?: number; inp_p75_ms?: number; cls_p75?: number; availability_pct?: number };
  current?: { lcp_p75_ms?: number; inp_p75_ms?: number; cls_p75?: number; availability_pct?: number };
  burn_rate?: { lcp?: number; inp?: number; cls?: number };
  breach_risk_next_7d?: string;
  error_budget?: Array<{ metric?: string; budget_mins?: number; consumed_mins?: number; remaining_pct?: number }>;
  alert_windows?: Array<{ window?: string; lcp_burn?: number; inp_burn?: number; status?: string }>;
  breach_scenarios?: Array<{ scenario?: string; probability?: number; impact?: string }>;
  slo_trend?: Array<{ date?: string; lcp_compliance?: number; inp_compliance?: number }>;
};
type RoiRow = {
  title?: string;
  effort?: string;
  estimated_gain_ms?: number;
  revenue_impact_usd?: number;
  priority_score?: number;
  category?: string;
  sprint?: number;
  impact_level?: string;
};
type PerformanceCopilot = {
  summary?: string;
  what_changed?: string[];
  why_it_happened?: string[];
  recommended_actions?: string[];
  narrative?: string;
  change_timeline?: Array<{ date?: string; event?: string; score_delta?: number; impact?: string }>;
  code_hints?: Array<{ file?: string; hint?: string; priority?: string; savings_ms?: number }>;
  ai_confidence?: number;
  next_audit_eta?: string;
  risk_radar?: Array<{ area?: string; risk?: string; probability?: number }>;
};
type ExecutionPlaybook = { now?: string[]; next?: string[]; later?: string[] };
type Opportunity = {
  priority?: string;
  issue?: string;
  impact?: string;
  estimated_gain_ms?: number;
  category?: string;
  revenue_gain_usd?: number;
  effort?: string;
};
type AlertRule = { metric?: string; threshold?: number; current?: number; state?: string };
type HistoryRun = {
  ts?: string;
  performance_score?: number;
  lcp_ms?: number;
  cls?: number;
  device?: string;
  analysis_id?: string;
};
type AutoFixCandidate = { title?: string; confidence?: number; estimated_gain_ms?: number; verification?: string };
type AiRemediation = { summary?: string; auto_fix_candidates?: AutoFixCandidate[]; verification_plan?: string[] };

type ImageAuditIssue = { severity?: string; message?: string };
type ImageAuditItem = {
  url?: string;
  size_kb?: number;
  savings_kb?: number;
  format?: string;
  recommended_format?: string;
  savings_pct?: number;
  lcp_candidate?: boolean;
  decode_time_ms?: number;
};
type ImageAudit = {
  total_images?: number;
  unoptimized?: number;
  missing_alt?: number;
  lazy_loaded_pct?: number;
  next_gen_adoption_pct?: number;
  oversized?: ImageAuditItem[];
  format_breakdown?: Record<string, number>;
  issues?: ImageAuditIssue[];
  bandwidth_wasted_mb?: number;
  lcp_image?: string;
  cdn_coverage_pct?: number;
  per_page_audit?: Array<{ page?: string; count?: number; missing_alt?: number; unoptimized?: number }>;
};
type SecurityHeader = { present?: boolean; value?: string; severity?: string };
type SecurityVulnerability = { severity?: string; issue?: string; detail?: string; cve?: string };
type CspDirective = { directive?: string; value?: string; status?: string; risk?: string };
type CorsIssue = { endpoint?: string; method?: string; issue?: string; risk?: string };
type SecurityAudit = {
  https?: boolean;
  mixed_content_count?: number;
  csp_score?: number;
  headers?: Record<string, SecurityHeader>;
  vulnerabilities?: SecurityVulnerability[];
  cookies?: { secure?: number; httponly?: number; samesite?: number; total?: number };
  threat_score?: number;
  csp_directives?: CspDirective[];
  sri_missing?: string[];
  subresource_integrity_pct?: number;
  cors_issues?: CorsIssue[];
  tls_info?: { version?: string; cipher?: string; cert_expires?: string; grade?: string };
};
type JsOpportunity = { title?: string; savings_kb?: number; savings_ms?: number };
type JsBundleModule = {
  module?: string;
  size_kb?: number;
  unused_pct?: number;
  tree_shakeable?: boolean;
  type?: string;
};
type JsLongTask = { task?: string; duration_ms?: number; start_ms?: number; culprit?: string };
type JsAudit = {
  total_kb?: number;
  unused_kb?: number;
  unused_pct?: number;
  parse_time_ms?: number;
  execution_time_ms?: number;
  third_party_kb?: number;
  blocking_scripts?: string[];
  opportunities?: JsOpportunity[];
  bundle_modules?: JsBundleModule[];
  long_tasks?: JsLongTask[];
  compression?: { raw_kb?: number; gzip_kb?: number; brotli_kb?: number };
  main_thread_cost_ms?: number;
};
type CssOpportunity = { title?: string; savings_kb?: number; savings_ms?: number };
type CssFileBreakdown = {
  file?: string;
  total_kb?: number;
  unused_kb?: number;
  unused_pct?: number;
  render_blocking?: boolean;
};
type CssAudit = {
  total_kb?: number;
  unused_kb?: number;
  unused_pct?: number;
  render_blocking?: string[];
  critical_path_kb?: number;
  opportunities?: CssOpportunity[];
  file_breakdown?: CssFileBreakdown[];
  selector_count?: number;
  rule_count?: number;
  animation_jank_risks?: string[];
  font_face_count?: number;
  critical_inline_pct?: number;
};
type InputFieldIssue = { name?: string; type?: string; issue?: string; severity?: string };
type OWASPItem = { id?: string; name?: string; status?: string; risk_level?: string };
type FormAuditEntry = {
  form_id?: string;
  action?: string;
  csrf?: boolean;
  client_val?: boolean;
  server_val?: boolean;
  inputs?: number;
  risk?: string;
};
type InputValidationAudit = {
  forms_found?: number;
  csrf_protected?: number;
  client_validated?: number;
  server_side_validated?: number;
  xss_risks?: number;
  injection_risks?: number;
  issues?: InputFieldIssue[];
  owasp_coverage?: OWASPItem[];
  form_audit?: FormAuditEntry[];
  sanitization_pct?: number;
  open_redirect_risks?: number;
};

type LatencyPercentiles = { p50?: number; p75?: number; p95?: number; p99?: number };
type LatencyEndpoint = {
  url?: string;
  method?: string;
  p50?: number;
  p75?: number;
  p95?: number;
  p99?: number;
  error_rate?: number;
};
type LatencyDbQuery = { query?: string; p50?: number; p75?: number; p95?: number; p99?: number };
type LatencyWaterfallEntry = {
  name?: string;
  start_ms?: number;
  duration_ms?: number;
  type?: string;
  size_kb?: number;
};
type LatencyAudit = {
  waterfall?: LatencyWaterfallEntry[];
  cache_stats?: { hit_rate?: number; miss_penalty_ms?: number; stale_rate?: number };
  compression_stats?: { gzip_pct?: number; brotli_pct?: number; none_pct?: number };
  overall?: LatencyPercentiles;
  dns?: LatencyPercentiles;
  tcp?: LatencyPercentiles;
  tls?: LatencyPercentiles;
  ttfb?: LatencyPercentiles;
  fcp?: LatencyPercentiles;
  lcp?: LatencyPercentiles;
  cdn_edge_latency?: LatencyPercentiles;
  endpoints?: LatencyEndpoint[];
  db_query_distribution?: LatencyDbQuery[];
};

type OutdatedDep = {
  name?: string;
  current?: string;
  latest?: string;
  severity?: string;
  type?: string;
  has_cve?: boolean;
  versions_behind?: number;
};
type DeprecatedApiEntry = { api?: string; used_in?: string; alternative?: string; eol?: string };
type LegacyPattern = { pattern?: string; file?: string; recommendation?: string };
type CveEntry = { pkg?: string; cve?: string; severity?: string; cvss?: number; patched_in?: string };
type UpgradeMatrixEntry = {
  name?: string;
  from_ver?: string;
  to_ver?: string;
  breaking_changes?: number;
  effort?: string;
  security_fix?: boolean;
};
type OutdatedAudit = {
  total_deps?: number;
  outdated_count?: number;
  critical_outdated?: number;
  deps?: OutdatedDep[];
  deprecated_apis?: DeprecatedApiEntry[];
  legacy_patterns?: LegacyPattern[];
  security_risk_score?: number;
  cve_count?: number;
  cves?: CveEntry[];
  upgrade_matrix?: UpgradeMatrixEntry[];
};

type WorkflowStep = { name?: string; status?: string; duration_ms?: number; passed?: boolean };
type WorkflowDeployment = {
  version?: string;
  deployed_at?: string;
  status?: string;
  perf_delta_ms?: number;
  rollback?: boolean;
};
type WorkflowPrCheck = { check?: string; status?: string; required?: boolean };
type FlakyTest = { test?: string; flakiness_rate?: number; suite?: string; last_failed?: string };
type BuildTrendPoint = { date?: string; duration_mins?: number; status?: string };
type WorkflowAudit = {
  pipeline_status?: string;
  last_run?: string;
  steps?: WorkflowStep[];
  pr_checks?: WorkflowPrCheck[];
  deployments?: WorkflowDeployment[];
  integration_health?: Record<string, string>;
  test_coverage_pct?: number;
  flaky_tests?: FlakyTest[];
  mean_deploy_mins?: number;
  mean_recovery_mins?: number;
  build_trend?: BuildTrendPoint[];
};

type CohortPoint = { period?: string; score?: number; lcp?: number; sessions?: number };
type FunnelStep = { name?: string; users?: number; drop_pct?: number };
type AnomalyEvent = { ts?: string; metric?: string; value?: number; expected?: number; severity?: string };
type SegmentData = { score?: number; lcp?: number; sessions?: number };
type IndexCoverage = { indexed?: number; total_submitted?: number; errors?: number };
type RetentionCohort = { week?: string; d1_pct?: number; d7_pct?: number; d30_pct?: number };
type RevenueByChannel = { channel?: string; revenue_usd?: number; sessions?: number; conv_rate?: number };
type DataAnalysis = {
  cohort_trend?: CohortPoint[];
  funnel?: FunnelStep[];
  anomalies?: AnomalyEvent[];
  segment_breakdown?: Record<string, SegmentData>;
  bot_traffic_pct?: number;
  crawl_efficiency?: number;
  index_coverage?: IndexCoverage;
  retention?: RetentionCohort[];
  revenue_by_channel?: RevenueByChannel[];
  search_console?: {
    impressions?: number;
    clicks?: number;
    ctr_pct?: number;
    avg_position?: number;
    top_queries?: Array<{ query?: string; clicks?: number; position?: number }>;
  };
};

type SuiteMetric = { label?: string; value?: string; trend?: string; status?: string };
type SuiteDistribution = { label?: string; value?: number; color?: string };
type SuiteTimelinePoint = { label?: string; value?: number };
type SuiteModule = {
  name?: string;
  tier?: string;
  status?: string;
  score?: number;
  summary?: string;
  metrics?: SuiteMetric[];
  automations?: string[];
  issues?: string[];
};
type SeoCapabilitySuite = {
  overview_score?: number;
  overall_score?: number;
  coverage?: number;
  opportunity_count?: number;
  highlights?: string[];
  risks?: string[];
  distribution?: SuiteDistribution[];
  timeline?: SuiteTimelinePoint[];
  modules?: SuiteModule[];
};

type PerformanceAuditResponse = {
  analysis_id: string;
  url: string;
  target_device: string;
  target_region: string;
  audited_at?: string;
  performance_score: number;
  core_web_vitals?: CoreWebVitals;
  field_web_vitals?: FieldWebVitals;
  lighthouse?: Lighthouse;
  waterfall?: Waterfall;
  filmstrip?: FilmstripFrame[];
  rum_summary?: RumSummary;
  causality_graph?: CausalityGraph;
  autonomous_agents?: AutonomousAgents;
  predictive_intelligence?: PredictiveIntelligence;
  global_simulation?: GlobalSimulation;
  full_stack_observability?: FullStackObservability;
  business_impact?: BusinessImpact;
  ci_gate?: CiGate;
  slo_guardrails?: SloGuardrails;
  roi_matrix?: RoiRow[];
  performance_copilot?: PerformanceCopilot;
  execution_playbook?: ExecutionPlaybook;
  opportunities?: Opportunity[];
  alerts?: { status?: string; rules?: AlertRule[] };
  history?: { trend?: string; regression_detected?: boolean; runs?: HistoryRun[] };
  ai_remediation?: AiRemediation;
  recommended_stack?: string[];
  image_audit?: ImageAudit;
  security_audit?: SecurityAudit;
  js_audit?: JsAudit;
  css_audit?: CssAudit;
  input_validation_audit?: InputValidationAudit;
  latency_audit?: LatencyAudit;
  outdated_audit?: OutdatedAudit;
  workflow_audit?: WorkflowAudit;
  data_analysis?: DataAnalysis;
  core_seo_suite?: SeoCapabilitySuite;
  content_blog_suite?: SeoCapabilitySuite;
  ai_optimization_suite?: SeoCapabilitySuite;
  search_experience_suite?: SeoCapabilitySuite;
  vertical_seo_suite?: SeoCapabilitySuite;
  platform_ops_suite?: SeoCapabilitySuite;
  // Advanced audit tabs
  accessibility_audit?: AccessibilityAuditData;
  competitor_intel?: CompetitorIntelData;
  schema_entities?: SchemaEntitiesData;
  technical_deep?: TechnicalDeepData;
  trust_revenue?: TrustRevenueData;
  ux_conversion?: UxConversionData;
  growth_landing?: GrowthLandingData;
  live_intelligence?: LiveIntelligenceData;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

type PerformanceRumRollup = {
  field_web_vitals?: FieldWebVitals;
  rum_summary?: RumSummary;
  history?: PerformanceAuditResponse['history'];
  free_provider_status?: Record<string, boolean>;
  data_provenance?: { source?: string; providers?: string[]; notes?: string[] };
};

type PerformanceRumSummaryResponse = {
  url: string;
  available: boolean;
  rollup?: PerformanceRumRollup | null;
};

type PerformanceRumIngestResponse = {
  accepted: boolean;
  metric_name: string;
  value: number;
  rating?: string;
  received_at: string;
  rollup?: PerformanceRumRollup | null;
};

type RumQuality = 'good' | 'needs-improvement' | 'poor';

type RumCollectorState = {
  supported: boolean;
  collecting: boolean;
  currentPageUrl: string;
  targetUrl: string;
  canCollectForAuditUrl: boolean;
  ingestedCount: number;
  lastMetric?: string;
  lastValue?: number;
  lastSentAt?: string;
  error?: string;
};

// ─── Advanced Audit Types ────────────────────────────────────────────────────

// Accessibility
type WcagIssue = { wcag?: string; impact?: string; element?: string; description?: string; remediation?: string };
type ContrastFailure = { element?: string; fg?: string; bg?: string; ratio?: number; required?: number };
type AccessibilityAuditData = {
  wcag_score?: number;
  wcag_level?: string;
  violations_a?: number;
  violations_aa?: number;
  violations_aaa?: number;
  color_contrast_failures?: number;
  aria_issues?: number;
  keyboard_nav_issues?: number;
  focus_order_issues?: number;
  screen_reader_score?: number;
  legal_risk?: string;
  issues?: WcagIssue[];
  contrast_failures?: ContrastFailure[];
  passing_criteria?: string[];
  failing_criteria?: string[];
};

// Competitor Intelligence
type CompetitorProfile = {
  domain?: string;
  authority?: number;
  keywords?: number;
  backlinks?: number;
  content_score?: number;
  traffic_est?: number;
};
type ContentDecay = { url?: string; decay_pct?: number; last_updated?: string; freshness_score?: number };
type ContentAuditData = {
  thin_pages?: number;
  duplicate_pages?: number;
  decaying_pages?: number;
  avg_freshness_score?: number;
  top_decay?: ContentDecay[];
};
type CompetitorIntelData = {
  keyword_gap?: number;
  content_gap?: number;
  backlink_gap?: number;
  serp_overlap_pct?: number;
  competitors?: CompetitorProfile[];
  content_audit?: ContentAuditData;
  opportunities?: string[];
};

// Schema & Entities
type SchemaType = {
  type?: string;
  present?: boolean;
  validated?: boolean;
  rich_result_eligible?: boolean;
  errors?: string[];
};
type EntityStatus = {
  entity?: string;
  type?: string;
  knowledge_panel?: boolean;
  wikidata?: boolean;
  confidence?: number;
};
type OrphanPage = { url?: string; inbound_links?: number; pagerank_flow?: number };
type AnchorTextEntry = { text?: string; count?: number; pct?: number };
type SchemaEntitiesData = {
  structured_data_score?: number;
  json_ld_coverage_pct?: number;
  total_schemas?: number;
  validated?: number;
  errors?: number;
  warnings?: number;
  rich_result_types?: SchemaType[];
  entities?: EntityStatus[];
  internal_link_equity_score?: number;
  orphan_pages?: OrphanPage[];
  anchor_diversity_score?: number;
  anchor_text_dist?: AnchorTextEntry[];
};

// Technical Deep Dive
type CrawlBudgetEntry = { url_type?: string; crawled?: number; budget_pct?: number; wasted?: boolean };
type LogAnomalyEvent = { ts?: string; type?: string; url?: string; detail?: string; severity?: string };
type TopicalCluster = { topic?: string; pages?: number; coverage_pct?: number; gap?: boolean };
type RedirectChain = { start_url?: string; hops?: number; final_url?: string; latency_ms?: number };
type TechnicalDeepData = {
  crawl_efficiency_pct?: number;
  crawl_budget_used_pct?: number;
  wasted_crawl_slots?: number;
  googlebot_visits_last7d?: number;
  avg_crawl_interval_hrs?: number;
  crawl_budget?: CrawlBudgetEntry[];
  log_anomalies?: LogAnomalyEvent[];
  topical_clusters?: TopicalCluster[];
  redirect_chains?: RedirectChain[];
  orphaned_canonicals?: number;
  pagination_issues?: number;
};

// Trust & Revenue
type ReviewSource = { platform?: string; score?: number; count?: number; trend?: string };
type RevenueKeyword = {
  keyword?: string;
  position?: number;
  sessions?: number;
  revenue_usd?: number;
  conversions?: number;
};
type AttributionChannel = { channel?: string; assisted_pct?: number; last_click_pct?: number; revenue_usd?: number };
type TrustRevenueData = {
  domain_trust_score?: number;
  e_e_a_t_score?: number;
  safe_browsing_clean?: boolean;
  malware_flagged?: boolean;
  https_enforced?: boolean;
  hsts_preloaded?: boolean;
  author_authority_avg?: number;
  backlink_trust_flow?: number;
  review_aggregate_score?: number;
  review_velocity?: number;
  reviews?: ReviewSource[];
  seo_revenue_total_usd?: number;
  seo_attributed_pct?: number;
  top_revenue_keywords?: RevenueKeyword[];
  attribution?: AttributionChannel[];
};

// UX & Conversion
type CtaAuditItem = {
  page?: string;
  cta_text?: string;
  visibility_score?: number;
  contrast_ok?: boolean;
  placement?: string;
};
type FormFrictionItem = {
  form_id?: string;
  fields?: number;
  avg_completion_pct?: number;
  drop_field?: string;
  friction_score?: number;
};
type SocialCardStatus = { url?: string; og_complete?: boolean; twitter_complete?: boolean; missing?: string[] };
type MediaAltText = { url?: string; alt_present?: boolean; alt_descriptive?: boolean; size_kb?: number };
type UxConversionData = {
  ux_score?: number;
  friction_score?: number;
  cta_coverage_pct?: number;
  form_completion_avg_pct?: number;
  heatmap_recommendations?: string[];
  cta_audit?: CtaAuditItem[];
  form_friction?: FormFrictionItem[];
  brand_voice_score?: number;
  tone_consistency_pct?: number;
  entity_sentiment?: string;
  social_coverage_pct?: number;
  og_coverage_pct?: number;
  twitter_card_coverage_pct?: number;
  social_cards?: SocialCardStatus[];
  media_alt_coverage_pct?: number;
  media_items?: MediaAltText[];
};

// Growth & Landing
type PlaybookAction = { priority?: string; action?: string; impact?: string; effort?: string; timeline?: string };
type GrowthPlaybook = { vertical?: string; goal?: string; actions?: PlaybookAction[] };
type LandingPageScore = {
  url?: string;
  headline_score?: number;
  cta_score?: number;
  trust_score?: number;
  overall?: number;
  suggestions?: string[];
};
type ChannelHealth = { channel?: string; coverage_pct?: number; active?: boolean; last_published?: string };
type GrowthLandingData = {
  playbook_score?: number;
  top_priority?: string;
  playbooks?: GrowthPlaybook[];
  landing_pages?: LandingPageScore[];
  multi_channel_score?: number;
  channels?: ChannelHealth[];
  quick_wins?: string[];
};

// Live Intelligence
type RankPosition = { keyword?: string; position?: number; delta?: number; url?: string; serp_feature?: string };
type RagReadinessItem = {
  url?: string;
  score?: number;
  faq_coverage?: boolean;
  structured_answer?: boolean;
  ai_cited?: boolean;
};
type AiAnswerCoverage = { query?: string; answered?: boolean; source?: string; confidence?: number };
type LiveIntelligenceData = {
  rank_tracking_score?: number;
  avg_position?: number;
  total_keywords?: number;
  keywords_top3?: number;
  positions_gained_7d?: number;
  positions_lost_7d?: number;
  top_keywords?: RankPosition[];
  rag_readiness_score?: number;
  ai_answer_coverage_pct?: number;
  rag_items?: RagReadinessItem[];
  ai_coverage?: AiAnswerCoverage[];
  live_alerts?: Array<{ metric?: string; change?: string; severity?: string; ts?: string }>;
};

type AutoFixResult = {
  fix_id: string;
  url: string;
  applied_at: string;
  total_gain_ms: number;
  new_performance_score: number;
  rerun_recommended: boolean;
  fixes_applied: { fix_id: string; title: string; status: string; actual_gain_ms: number; notes: string }[];
};

type HistoryResponse = { url: string; count: number; runs: HistoryRun[] };

// ─── Constants ────────────────────────────────────────────────────────────────

const REGIONS = [
  { value: 'lhr1', label: 'London (UK)' },
  { value: 'iad1', label: 'Washington DC (US)' },
  { value: 'sfo1', label: 'San Francisco (US)' },
  { value: 'sin1', label: 'Singapore' },
  { value: 'bom1', label: 'Mumbai (IN)' },
  { value: 'syd1', label: 'Sydney (AU)' },
  { value: 'cdg1', label: 'Paris (FR)' },
  { value: 'gru1', label: 'Sao Paulo (BR)' },
];

const CONNECTIONS = [
  { value: '4g', label: '4G LTE (~20 Mbps)' },
  { value: 'cable', label: 'Cable (~50 Mbps)' },
  { value: '3g_fast', label: 'Fast 3G (~1.6 Mbps)' },
  { value: '3g_slow', label: 'Slow 3G (~780 Kbps)' },
  { value: 'fiber', label: 'Fiber (100 Mbps)' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreGrade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

function scoreColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 70) return '#f59e0b';
  if (score >= 50) return '#f97316';
  return '#ef4444';
}

const CWV_THRESHOLDS: Record<string, [number, number]> = {
  lcp: [2500, 4000],
  inp: [200, 500],
  cls: [0.1, 0.25],
  ttfb: [800, 1800],
};

function cwvStatus(metric: string, value: number): RumQuality {
  const thresholds = CWV_THRESHOLDS[metric];
  if (!thresholds) return 'good';
  if (value <= thresholds[0]) return 'good';
  if (value <= thresholds[1]) return 'needs-improvement';
  return 'poor';
}

function cwvColor(status: 'good' | 'needs-improvement' | 'poor'): string {
  if (status === 'good') return '#22c55e';
  if (status === 'needs-improvement') return '#f59e0b';
  return '#ef4444';
}

function normalizeRumMetricName(metricName: string): string {
  const normalized = metricName.trim().toLowerCase();
  if (normalized === 'largest-contentful-paint' || normalized === 'lcp') return 'LCP';
  if (
    normalized === 'interaction to next paint' ||
    normalized === 'interaction-to-next-paint' ||
    normalized === 'inp'
  ) {
    return 'INP';
  }
  if (normalized === 'cumulative layout shift' || normalized === 'cls') return 'CLS';
  if (normalized === 'time to first byte' || normalized === 'ttfb') return 'TTFB';
  return metricName.trim().toUpperCase();
}

function rateRumMetric(metricName: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds = CWV_THRESHOLDS[metricName.trim().toLowerCase()];
  if (!thresholds) return 'good';
  if (value <= thresholds[0]) return 'good';
  if (value <= thresholds[1]) return 'needs-improvement';
  return 'poor';
}

function formatRumMetricValue(metricName: string, value?: number): string {
  if (value === undefined || !Number.isFinite(value)) return 'n/a';
  const normalized = normalizeRumMetricName(metricName);
  if (normalized === 'CLS') return value.toFixed(3);
  return `${Math.round(value)} ms`;
}

function currentBrowserPageUrl(): string {
  if (globalThis.window === undefined) return '';
  return globalThis.window.location.href;
}

function buildRumInstallSnippet(): string {
  return [
    "import { onCLS, onINP, onLCP, onTTFB } from 'web-vitals';",
    '',
    "const endpoint = '/api/fastapi/seo-platform/performance/rum/ingest';",
    '',
    'function send(metricName, metric) {',
    '  fetch(endpoint, {',
    "    method: 'POST',",
    '    headers: {',
    "      'Content-Type': 'application/json',",
    "      'X-Tenant-Id': process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || 'tenant-demo',",
    '    },',
    '    body: JSON.stringify({',
    '      url: window.location.origin + window.location.pathname,',
    '      page_url: window.location.href,',
    '      metric_name: metricName,',
    '      value: metric.value,',
    '      rating: metric.rating,',
    '      delta: metric.delta,',
    '      metric_id: metric.id,',
    "      device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',",
    "      effective_connection_type: navigator.connection?.effectiveType || 'unknown',",
    '      user_agent: navigator.userAgent,',
    '    }),',
    '    keepalive: true,',
    '  });',
    '}',
    '',
    "onLCP((metric) => send('LCP', metric));",
    "onINP((metric) => send('INP', metric));",
    "onCLS((metric) => send('CLS', metric));",
    "onTTFB((metric) => send('TTFB', metric));",
  ].join('\n');
}

function priorityColor(p?: string): string {
  if (p === 'critical') return '#ef4444';
  if (p === 'high') return '#f97316';
  if (p === 'medium') return '#f59e0b';
  return '#6b7280';
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function confidenceColor(confPct: number): string {
  if (confPct >= 90) return '#22c55e';
  if (confPct >= 70) return '#f59e0b';
  return 'var(--text)';
}

function btn(primary?: boolean): React.CSSProperties {
  return {
    padding: '9px 14px',
    borderRadius: 8,
    border: primary ? 'none' : '1px solid var(--line)',
    background: primary ? 'var(--brand)' : 'var(--bg)',
    color: primary ? '#00101e' : 'var(--text)',
    fontWeight: 700,
    cursor: 'pointer',
    fontSize: 13,
  };
}
function badge(color: string): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 700,
    background: `${color}22`,
    color,
    marginLeft: 4,
  };
}

function isNetworkFetchFailure(message: string): boolean {
  const text = message.toLowerCase();
  return (
    text.includes('fetch failed') ||
    text.includes('failed to fetch') ||
    text.includes('unable to reach fastapi upstream') ||
    text.includes('networkerror')
  );
}

function offlineAuditFallback(params: {
  url: string;
  targetDevice: 'mobile' | 'desktop';
  targetRegion: string;
}): PerformanceAuditResponse {
  const base: PerformanceAuditResponse = {
    analysis_id: `offline-${Date.now()}`,
    url: params.url,
    target_device: params.targetDevice,
    target_region: params.targetRegion,
    audited_at: new Date().toISOString(),
    performance_score: 78,
    core_web_vitals: { lcp_ms: 2890, inp_ms: 245, cls: 0.12, ttfb_ms: 620 },
    field_web_vitals: {
      lcp_p75_ms: 2760,
      inp_p75_ms: 228,
      cls_p75: 0.11,
      sample_size: 1200,
      period: '28d',
      source: 'offline_fallback',
    },
    lighthouse: { performance: 78, seo: 90, best_practices: 92, accessibility: 94 },
    waterfall: {
      requests: 42,
      transfer_kb: 810,
      render_blocking: ['main.css', 'analytics-loader.js'],
      timeline_ms: { dns: 35, tcp: 55, tls: 90, ttfb: 440, download: 380 },
    },
    opportunities: [
      {
        priority: 'high',
        issue: 'Render-blocking CSS',
        impact: 'Inline above-the-fold CSS',
        estimated_gain_ms: 180,
        category: 'CSS',
        revenue_gain_usd: 4200,
        effort: 'low',
      },
      {
        priority: 'high',
        issue: 'Third-party startup cost',
        impact: 'Defer non-critical scripts',
        estimated_gain_ms: 120,
        category: 'Scripts',
        revenue_gain_usd: 2600,
        effort: 'low',
      },
      {
        priority: 'high',
        issue: 'Unoptimised hero image',
        impact: 'Convert to AVIF, add fetchpriority=high',
        estimated_gain_ms: 210,
        category: 'Images',
        revenue_gain_usd: 3800,
        effort: 'low',
      },
      {
        priority: 'medium',
        issue: 'Code-split vendor bundle',
        impact: 'Split 840KB bundle by route',
        estimated_gain_ms: 190,
        category: 'JavaScript',
        revenue_gain_usd: 3200,
        effort: 'high',
      },
      {
        priority: 'medium',
        issue: 'Enable Brotli compression',
        impact: 'Switch CDN from gzip to Brotli',
        estimated_gain_ms: 80,
        category: 'Network',
        revenue_gain_usd: 1600,
        effort: 'medium',
      },
      {
        priority: 'low',
        issue: 'Purge unused CSS (58%)',
        impact: 'PurgeCSS in build pipeline',
        estimated_gain_ms: 55,
        category: 'CSS',
        revenue_gain_usd: 600,
        effort: 'medium',
      },
      {
        priority: 'low',
        issue: 'Pre-connect third-party origins',
        impact: 'Add <link rel=preconnect>',
        estimated_gain_ms: 60,
        category: 'Network',
        revenue_gain_usd: 800,
        effort: 'low',
      },
    ],
    filmstrip: [
      { label: 'first_paint', timestamp_ms: 320, asset: 'fp.png' },
      { label: 'first_contentful_paint', timestamp_ms: 680, asset: 'fcp.png' },
      { label: 'largest_contentful_paint', timestamp_ms: 2890, asset: 'lcp.png' },
      { label: 'time_to_interactive', timestamp_ms: 3800, asset: 'tti.png' },
    ],
    rum_summary: {
      sessions: 14820,
      rage_click_rate: 0.031,
      friction_score: 42,
      device_mix: { mobile: 0.58, desktop: 0.36, tablet: 0.06 },
      network_mix: { '4g': 0.52, '3g': 0.26, wifi: 0.22 },
      geo_isp_breakdown: [
        { country: 'GB', region: 'London', isp: 'BT', lcp_p75_ms: 2410, sample_size: 3200 },
        { country: 'US', region: 'New York', isp: 'Comcast', lcp_p75_ms: 2870, sample_size: 2900 },
        { country: 'IN', region: 'Mumbai', isp: 'Jio', lcp_p75_ms: 3640, sample_size: 1800 },
      ],
    },
    causality_graph: {
      root_causes: ['render-blocking CSS', 'large third-party analytics bootstrap', 'uncached origin responses'],
      critical_path_ms: 2890,
      wasted_ms: 720,
      render_blocking_attribution: [
        { asset: 'main.css', block_ms: 310, phase: 'parse', severity: 'critical' },
        { asset: 'analytics-loader.js', block_ms: 210, phase: 'eval', severity: 'high' },
        { asset: 'fonts.css', block_ms: 140, phase: 'parse', severity: 'medium' },
        { asset: 'chat-widget.js', block_ms: 95, phase: 'eval', severity: 'medium' },
        { asset: 'legacy-polyfill.js', block_ms: 60, phase: 'parse', severity: 'low' },
      ],
      third_party_impact: [
        {
          provider: 'Google Tag Manager',
          main_thread_block_ms: 185,
          network_ms: 95,
          category: 'tag-manager',
          removable: false,
        },
        {
          provider: 'Intercom Widget',
          main_thread_block_ms: 130,
          network_ms: 60,
          category: 'support',
          removable: true,
        },
        {
          provider: 'Hotjar Analytics',
          main_thread_block_ms: 98,
          network_ms: 42,
          category: 'analytics',
          removable: true,
        },
        {
          provider: 'Facebook Pixel',
          main_thread_block_ms: 72,
          network_ms: 38,
          category: 'marketing',
          removable: true,
        },
        { provider: 'Stripe.js', main_thread_block_ms: 44, network_ms: 88, category: 'payments', removable: false },
      ],
      main_thread_timeline: [
        { task: 'HTML Parse', duration_ms: 180, type: 'parse' },
        { task: 'CSS Evaluate (main.css)', duration_ms: 310, type: 'style' },
        { task: 'GTM Bootstrap', duration_ms: 185, type: 'script' },
        { task: 'React Hydration', duration_ms: 420, type: 'script' },
        { task: 'Intercom Init', duration_ms: 130, type: 'script' },
        { task: 'Layout & Paint', duration_ms: 290, type: 'render' },
        { task: 'LCP Candidate Paint', duration_ms: 95, type: 'render' },
      ],
      dependencies: [
        { from: 'analytics-loader.js', to: 'main.css', latency_ms: 28 },
        { from: 'main.css', to: 'hero-image.webp', latency_ms: 12 },
        { from: 'GTM', to: 'analytics-loader.js', latency_ms: 45 },
        { from: 'React bundle', to: 'analytics-loader.js', latency_ms: 18 },
      ],
    },
    autonomous_agents: {
      coverage_score: 74,
      journeys_tested: [
        'homepage_load',
        'product_search',
        'checkout_flow',
        'user_signup',
        'account_settings',
        'search_filters',
      ],
      scenario_mutations: 28,
      failure_hotspots: [
        { journey: 'checkout_flow', step: 'payment_form_render', p95_ms: 3240 },
        { journey: 'product_search', step: 'results_hydration', p95_ms: 2780 },
      ],
      journey_metrics: [
        { journey: 'homepage_load', p50_ms: 1820, p75_ms: 2340, p95_ms: 3180, pass_rate: 0.96, runs: 240 },
        { journey: 'product_search', p50_ms: 2100, p75_ms: 2780, p95_ms: 4420, pass_rate: 0.88, runs: 210 },
        { journey: 'checkout_flow', p50_ms: 2480, p75_ms: 2990, p95_ms: 3240, pass_rate: 0.81, runs: 180 },
        { journey: 'user_signup', p50_ms: 1640, p75_ms: 2120, p95_ms: 2850, pass_rate: 0.94, runs: 160 },
        { journey: 'account_settings', p50_ms: 980, p75_ms: 1340, p95_ms: 1980, pass_rate: 0.98, runs: 140 },
        { journey: 'search_filters', p50_ms: 2240, p75_ms: 2890, p95_ms: 4100, pass_rate: 0.84, runs: 190 },
      ],
      mutation_matrix: [
        { scenario: 'Slow 3G throttle', passed: 18, failed: 4, flaky: 2 },
        { scenario: 'CPU 4× slowdown', passed: 14, failed: 8, flaky: 3 },
        { scenario: 'Cache disabled', passed: 22, failed: 2, flaky: 1 },
        { scenario: 'Ad blocker active', passed: 24, failed: 1, flaky: 0 },
        { scenario: 'Cookie consent shown', passed: 20, failed: 3, flaky: 2 },
      ],
      agent_health: { total_agents: 12, healthy: 9, degraded: 2, offline: 1 },
      deviation_from_baseline: [
        { metric: 'LCP', baseline_ms: 2400, current_ms: 2890, delta_pct: 20.4 },
        { metric: 'INP', baseline_ms: 200, current_ms: 245, delta_pct: 22.5 },
        { metric: 'FCP', baseline_ms: 900, current_ms: 1080, delta_pct: 20 },
        { metric: 'TTI', baseline_ms: 3200, current_ms: 3800, delta_pct: 18.8 },
      ],
    },
    predictive_intelligence: {
      forecast_horizon_days: 14,
      forecast: { lcp_ms: 3050, inp_ms: 260, cls: 0.14 },
      regression_risk: {
        label: 'medium',
        probability: 0.38,
        contributing_factors: [
          'Third-party script growth +18%',
          'Bundle size crept +42 KB last 2 PRs',
          'CDN cache hit rate declining',
        ],
      },
      pre_deploy_guardrail: { predicted_lcp_delta_ms: 170, status: 'warn', confidence: 0.82 },
      deploy_confidence: 62,
      weekly_trend: [
        { week: 'W-6', lcp_ms: 2480, score: 84 },
        { week: 'W-5', lcp_ms: 2560, score: 82 },
        { week: 'W-4', lcp_ms: 2710, score: 80 },
        { week: 'W-3', lcp_ms: 2750, score: 79 },
        { week: 'W-2', lcp_ms: 2820, score: 78 },
        { week: 'W-1', lcp_ms: 2890, score: 78 },
        { week: 'Forecast', lcp_ms: 3050, score: 75 },
      ],
      ai_recommendations: [
        'Block PR #4821 — predicted +170ms LCP delta exceeds 2500ms budget',
        'Remove Intercom eager init — saves ~130ms main-thread block',
        'Enable Brotli compression on CDN — projected 12% transfer reduction',
        'Pre-connect to fonts.gstatic.com — saves ~95ms LCP',
      ],
      anomaly_forecast: [
        { metric: 'LCP p75', expected_breach_date: '2026-05-09', severity: 'high' },
        { metric: 'SLO availability', expected_breach_date: '2026-05-14', severity: 'medium' },
        { metric: 'INP p75', expected_breach_date: '2026-05-18', severity: 'low' },
      ],
    },
    global_simulation: {
      coverage_regions: 8,
      isp_profiles_tested: 22,
      network_profiles: ['4g', '3g_fast', '3g_slow', 'cable', 'fiber'],
      best_region: 'Frankfurt (DE) — fiber',
      worst_region: 'Mumbai (IN) — 3g_slow',
      global_p75_lcp_ms: 3480,
      hotspots: [
        { region: 'Mumbai (IN)', network: '3g_slow', lcp_ms: 5810 },
        { region: 'Sao Paulo (BR)', network: '3g_fast', lcp_ms: 4220 },
        { region: 'Sydney (AU)', network: '4g', lcp_ms: 3190 },
      ],
      region_grid: [
        {
          region: 'Frankfurt (DE)',
          country: 'DE',
          lcp_p75_ms: 1980,
          fcp_ms: 820,
          ttfb_ms: 210,
          network: 'fiber',
          pass: true,
        },
        {
          region: 'London (GB)',
          country: 'GB',
          lcp_p75_ms: 2340,
          fcp_ms: 960,
          ttfb_ms: 280,
          network: 'cable',
          pass: true,
        },
        {
          region: 'New York (US)',
          country: 'US',
          lcp_p75_ms: 2640,
          fcp_ms: 1080,
          ttfb_ms: 320,
          network: '4g',
          pass: false,
        },
        {
          region: 'Singapore (SG)',
          country: 'SG',
          lcp_p75_ms: 2980,
          fcp_ms: 1240,
          ttfb_ms: 380,
          network: '4g',
          pass: false,
        },
        {
          region: 'Sydney (AU)',
          country: 'AU',
          lcp_p75_ms: 3190,
          fcp_ms: 1310,
          ttfb_ms: 420,
          network: '4g',
          pass: false,
        },
        {
          region: 'Sao Paulo (BR)',
          country: 'BR',
          lcp_p75_ms: 4220,
          fcp_ms: 1680,
          ttfb_ms: 560,
          network: '3g_fast',
          pass: false,
        },
        {
          region: 'Lagos (NG)',
          country: 'NG',
          lcp_p75_ms: 4880,
          fcp_ms: 1920,
          ttfb_ms: 680,
          network: '3g_slow',
          pass: false,
        },
        {
          region: 'Mumbai (IN)',
          country: 'IN',
          lcp_p75_ms: 5810,
          fcp_ms: 2240,
          ttfb_ms: 820,
          network: '3g_slow',
          pass: false,
        },
      ],
      cdn_pop_latency: [
        { pop: 'Frankfurt', latency_ms: 18 },
        { pop: 'London', latency_ms: 24 },
        { pop: 'New York', latency_ms: 31 },
        { pop: 'Singapore', latency_ms: 48 },
        { pop: 'Sydney', latency_ms: 62 },
        { pop: 'Sao Paulo', latency_ms: 89 },
        { pop: 'Mumbai', latency_ms: 112 },
      ],
    },
    full_stack_observability: {
      frontend_to_backend_trace: { p95_ms: 480, slow_span: 'db_query:product_lookup' },
      api_latency_p95_ms: 390,
      db_query_p95_ms: 270,
      cdn: { hit_rate: 0.72, miss_penalty_ms: 310 },
      infra: { cpu_spike_corr: 0.61, error_burst_corr: 0.44 },
    },
    business_impact: {
      conversion_delta_per_100ms: -0.018,
      estimated_monthly_revenue_at_risk_usd: 9400,
      annualized_at_risk_usd: 112800,
      seo_rank_sensitivity: { top3_drop_risk: 0.22, traffic_delta_pct: -8.4, rank_delta: -2 },
      bounce_probability: 0.34,
      priority: 'high',
      segment_impact: [
        { segment: 'Mobile — 3G', conversion_rate: 0.021, revenue_usd: 4200, lcp_ms: 5810 },
        { segment: 'Mobile — 4G', conversion_rate: 0.038, revenue_usd: 6800, lcp_ms: 3180 },
        { segment: 'Desktop — Cable', conversion_rate: 0.071, revenue_usd: 14200, lcp_ms: 2340 },
        { segment: 'Desktop — Fiber', conversion_rate: 0.089, revenue_usd: 18600, lcp_ms: 1980 },
        { segment: 'Tablet', conversion_rate: 0.044, revenue_usd: 5400, lcp_ms: 2780 },
      ],
      competitor_rank_risk: [
        { competitor: 'rival-store.com', rank: 2, gap_ms: -420 },
        { competitor: 'fast-shop.io', rank: 3, gap_ms: -180 },
        { competitor: 'quicker-commerce.com', rank: 4, gap_ms: 140 },
      ],
      revenue_waterfall: [
        { fix: 'Inline critical CSS', gain_usd: 4200, effort: 'low' },
        { fix: 'Remove Intercom eager load', gain_usd: 2600, effort: 'low' },
        { fix: 'Enable CDN Brotli', gain_usd: 1800, effort: 'medium' },
        { fix: 'Pre-connect third-party origins', gain_usd: 800, effort: 'low' },
      ],
    },
    ci_gate: {
      status: 'warn',
      predicted_pr_impact: { lcp_delta_ms: 120, inp_delta_ms: 10, cls_delta: 0.01 },
      budget: { lcp_ms: 2500, inp_ms: 200, cls: 0.1 },
      recommendation: 'block_or_request_fix',
      pr_diff_analysis: [
        {
          file: 'src/components/ProductCard.tsx',
          size_delta_kb: 12.4,
          impact: 'New render-blocking import',
          severity: 'high',
        },
        {
          file: 'src/styles/global.css',
          size_delta_kb: 8.2,
          impact: 'Increased critical CSS path',
          severity: 'medium',
        },
        { file: 'src/lib/analytics.ts', size_delta_kb: 22.8, impact: 'New GTM tag added eagerly', severity: 'high' },
        {
          file: 'public/images/hero.jpg',
          size_delta_kb: 180,
          impact: 'Unoptimised hero image added',
          severity: 'critical',
        },
        { file: 'package.json', size_delta_kb: 0, impact: '+1 new dependency (moment.js)', severity: 'medium' },
      ],
      gate_history: [
        { pr: '#4820', status: 'pass', lcp_delta_ms: -40, merged: true },
        { pr: '#4819', status: 'warn', lcp_delta_ms: 80, merged: true },
        { pr: '#4818', status: 'pass', lcp_delta_ms: 10, merged: true },
        { pr: '#4817', status: 'fail', lcp_delta_ms: 340, merged: false },
        { pr: '#4816', status: 'pass', lcp_delta_ms: -20, merged: true },
      ],
      blocking_rules: [
        { rule: 'LCP ≤ 2500ms', threshold: '2500ms', current: '2760ms', pass: false },
        { rule: 'INP ≤ 200ms', threshold: '200ms', current: '228ms', pass: false },
        { rule: 'CLS ≤ 0.10', threshold: '0.10', current: '0.11', pass: false },
        { rule: 'Bundle Δ ≤ +50 KB', threshold: '+50 KB', current: '+223 KB', pass: false },
        { rule: 'No new render-blocking scripts', threshold: '0', current: '2', pass: false },
      ],
      bundle_analysis: { total_kb: 840, delta_kb: 223, new_deps: ['moment.js', '@intercom/messenger-js-sdk'] },
    },
    slo_guardrails: {
      overall: 'degraded',
      slo_targets: { lcp_p75_ms: 2500, inp_p75_ms: 200, cls_p75: 0.1, availability_pct: 99.9 },
      current: { lcp_p75_ms: 2760, inp_p75_ms: 228, cls_p75: 0.11, availability_pct: 99.88 },
      burn_rate: { lcp: 1.1, inp: 1.05, cls: 1.02 },
      breach_risk_next_7d: 'medium',
      error_budget: [
        { metric: 'LCP', budget_mins: 43200, consumed_mins: 47520, remaining_pct: -10 },
        { metric: 'INP', budget_mins: 43200, consumed_mins: 45360, remaining_pct: -5 },
        { metric: 'CLS', budget_mins: 43200, consumed_mins: 44064, remaining_pct: -2 },
        { metric: 'Availability', budget_mins: 62, consumed_mins: 69, remaining_pct: -11 },
      ],
      alert_windows: [
        { window: '1h', lcp_burn: 2.4, inp_burn: 1.8, status: 'critical' },
        { window: '6h', lcp_burn: 1.6, inp_burn: 1.3, status: 'warn' },
        { window: '24h', lcp_burn: 1.1, inp_burn: 1.05, status: 'warn' },
        { window: '72h', lcp_burn: 0.9, inp_burn: 0.88, status: 'ok' },
      ],
      breach_scenarios: [
        { scenario: 'Deploy PR #4821 as-is', probability: 0.81, impact: 'LCP SLO breach within 48h' },
        { scenario: 'CDN cache eviction', probability: 0.34, impact: 'TTFB spike → LCP breach' },
        { scenario: 'Third-party outage (GTM)', probability: 0.18, impact: 'INP spikes across all sessions' },
      ],
      slo_trend: [
        { date: 'Apr-25', lcp_compliance: 96.2, inp_compliance: 98.1 },
        { date: 'Apr-26', lcp_compliance: 95.8, inp_compliance: 97.9 },
        { date: 'Apr-27', lcp_compliance: 94.4, inp_compliance: 97.2 },
        { date: 'Apr-28', lcp_compliance: 93.1, inp_compliance: 96.8 },
        { date: 'Apr-29', lcp_compliance: 92, inp_compliance: 96.4 },
        { date: 'Apr-30', lcp_compliance: 90.8, inp_compliance: 95.9 },
        { date: 'May-01', lcp_compliance: 89.6, inp_compliance: 95.4 },
      ],
    },
    roi_matrix: [
      {
        title: 'Inline critical CSS',
        effort: 'low',
        estimated_gain_ms: 180,
        revenue_impact_usd: 4200,
        priority_score: 93,
        category: 'CSS',
        sprint: 1,
        impact_level: 'high',
      },
      {
        title: 'Defer third-party analytics',
        effort: 'medium',
        estimated_gain_ms: 120,
        revenue_impact_usd: 2600,
        priority_score: 84,
        category: 'Scripts',
        sprint: 1,
        impact_level: 'high',
      },
      {
        title: 'Remove Intercom eager init',
        effort: 'low',
        estimated_gain_ms: 130,
        revenue_impact_usd: 2400,
        priority_score: 91,
        category: 'Scripts',
        sprint: 1,
        impact_level: 'high',
      },
      {
        title: 'Convert hero image to AVIF',
        effort: 'low',
        estimated_gain_ms: 95,
        revenue_impact_usd: 1800,
        priority_score: 79,
        category: 'Images',
        sprint: 1,
        impact_level: 'medium',
      },
      {
        title: 'Enable Brotli on CDN',
        effort: 'medium',
        estimated_gain_ms: 80,
        revenue_impact_usd: 1600,
        priority_score: 72,
        category: 'CDN',
        sprint: 2,
        impact_level: 'medium',
      },
      {
        title: 'Pre-connect third-party origins',
        effort: 'low',
        estimated_gain_ms: 60,
        revenue_impact_usd: 800,
        priority_score: 68,
        category: 'Network',
        sprint: 2,
        impact_level: 'medium',
      },
      {
        title: 'Code-split vendor bundle',
        effort: 'high',
        estimated_gain_ms: 190,
        revenue_impact_usd: 3800,
        priority_score: 65,
        category: 'JS',
        sprint: 3,
        impact_level: 'high',
      },
      {
        title: 'Remove unused CSS (58%)',
        effort: 'medium',
        estimated_gain_ms: 55,
        revenue_impact_usd: 600,
        priority_score: 58,
        category: 'CSS',
        sprint: 2,
        impact_level: 'low',
      },
    ],
    performance_copilot: {
      summary: 'Offline fallback report generated because backend connectivity is unavailable.',
      what_changed: ['Network path to FastAPI unavailable from frontend proxy'],
      why_it_happened: ['FastAPI server is not reachable on the configured upstream URL(s)'],
      recommended_actions: [
        'Start backend on 127.0.0.1:8001',
        'Verify FASTAPI_URL and FASTAPI_API_KEY in frontend server env',
      ],
      narrative: 'This is a sample report payload for UI rendering only.',
      ai_confidence: 62,
      next_audit_eta: '2026-05-02T10:00:00Z',
      change_timeline: [
        { date: 'Apr-24', event: 'PR #4815 merged — removed unused polyfills', score_delta: +3, impact: 'positive' },
        {
          date: 'Apr-26',
          event: 'PR #4817 reverted — moment.js caused bundle bloat',
          score_delta: -5,
          impact: 'negative',
        },
        { date: 'Apr-28', event: 'Hotjar tag added via GTM', score_delta: -2, impact: 'negative' },
        { date: 'Apr-29', event: 'CDN TTL increased to 7d for static assets', score_delta: +1, impact: 'positive' },
        { date: 'Apr-30', event: 'Hero image replaced with larger JPEG', score_delta: -4, impact: 'negative' },
      ],
      code_hints: [
        {
          file: 'src/components/Hero.tsx',
          hint: 'Add loading="eager" + fetchpriority="high" to LCP image',
          priority: 'critical',
          savings_ms: 210,
        },
        {
          file: 'src/app/layout.tsx',
          hint: 'Move GTM script to afterInteractive strategy',
          priority: 'high',
          savings_ms: 185,
        },
        {
          file: 'src/styles/global.css',
          hint: 'Extract above-the-fold rules into <style> in _document',
          priority: 'high',
          savings_ms: 180,
        },
        {
          file: 'src/lib/intercom.ts',
          hint: 'Lazy-init Intercom on first user interaction, not on mount',
          priority: 'medium',
          savings_ms: 130,
        },
        {
          file: 'next.config.ts',
          hint: "Enable images.formats: ['image/avif', 'image/webp']",
          priority: 'medium',
          savings_ms: 95,
        },
      ],
      risk_radar: [
        { area: 'Third-party scripts', risk: 'Growing main-thread block from analytics', probability: 0.72 },
        { area: 'Image assets', risk: 'Unoptimised hero image regression', probability: 0.68 },
        { area: 'Bundle size', risk: 'Dependency creep adding 20+ KB per sprint', probability: 0.55 },
        { area: 'CDN', risk: 'Cache hit rate declining — origin load increasing', probability: 0.41 },
      ],
    },
    execution_playbook: {
      now: ['Start FastAPI process', 'Run /api/fastapi/seo-platform/health check'],
      next: ['Add backend health monitor badge', 'Alert when proxy returns 502'],
      later: ['Introduce cached last-known-good audit snapshot'],
    },
    alerts: {
      status: 'degraded',
      rules: [{ metric: 'backend_upstream', threshold: 1, current: 0, state: 'firing' }],
    },
    recommended_stack: ['lighthouse', 'web-vitals', 'playwright_cdp'],
    image_audit: {
      total_images: 24,
      unoptimized: 8,
      missing_alt: 3,
      lazy_loaded_pct: 0.58,
      next_gen_adoption_pct: 0.42,
      bandwidth_wasted_mb: 4.2,
      lcp_image: '/images/hero-banner.jpg',
      cdn_coverage_pct: 0.67,
      oversized: [
        {
          url: '/images/hero-banner.jpg',
          size_kb: 840,
          savings_kb: 620,
          format: 'JPEG',
          recommended_format: 'AVIF',
          savings_pct: 74,
          lcp_candidate: true,
          decode_time_ms: 18,
        },
        {
          url: '/images/team-photo.png',
          size_kb: 1240,
          savings_kb: 980,
          format: 'PNG',
          recommended_format: 'WebP',
          savings_pct: 79,
          lcp_candidate: false,
          decode_time_ms: 28,
        },
        {
          url: '/images/product-grid.jpg',
          size_kb: 560,
          savings_kb: 320,
          format: 'JPEG',
          recommended_format: 'WebP',
          savings_pct: 57,
          lcp_candidate: false,
          decode_time_ms: 12,
        },
        {
          url: '/images/blog-cover-1.jpg',
          size_kb: 380,
          savings_kb: 220,
          format: 'JPEG',
          recommended_format: 'WebP',
          savings_pct: 58,
          lcp_candidate: false,
          decode_time_ms: 9,
        },
        {
          url: '/images/category-banner.png',
          size_kb: 720,
          savings_kb: 540,
          format: 'PNG',
          recommended_format: 'AVIF',
          savings_pct: 75,
          lcp_candidate: false,
          decode_time_ms: 16,
        },
      ],
      format_breakdown: { webp: 10, png: 8, jpeg: 5, gif: 1 },
      issues: [
        {
          severity: 'high',
          message:
            'hero-banner.jpg is LCP candidate — missing fetchpriority=high and serves as JPEG (saves ~620 KB with AVIF)',
        },
        { severity: 'high', message: 'team-photo.png: oversized 4× — saves ~980 KB as WebP' },
        { severity: 'medium', message: '3 images missing alt text (a11y + SEO ranking signal)' },
        { severity: 'medium', message: '5 images load eagerly but are below the fold (should be lazy)' },
        { severity: 'low', message: 'Only 42% images use next-gen format; target ≥80%' },
      ],
      per_page_audit: [
        { page: '/', count: 8, missing_alt: 1, unoptimized: 3 },
        { page: '/products', count: 12, missing_alt: 2, unoptimized: 4 },
        { page: '/about', count: 4, missing_alt: 0, unoptimized: 1 },
      ],
    },
    security_audit: {
      https: true,
      mixed_content_count: 2,
      csp_score: 42,
      threat_score: 68,
      subresource_integrity_pct: 24,
      headers: {
        'Content-Security-Policy': { present: false, severity: 'high' },
        'Strict-Transport-Security': { present: true, value: 'max-age=31536000', severity: 'good' },
        'X-Frame-Options': { present: true, value: 'SAMEORIGIN', severity: 'good' },
        'X-Content-Type-Options': { present: true, value: 'nosniff', severity: 'good' },
        'Permissions-Policy': { present: false, severity: 'medium' },
        'Referrer-Policy': { present: false, severity: 'medium' },
      },
      vulnerabilities: [
        {
          severity: 'high',
          issue: 'Missing Content-Security-Policy',
          detail: 'No CSP header — XSS risk significantly elevated',
          cve: 'CWE-79',
        },
        {
          severity: 'medium',
          issue: '2 mixed-content resources',
          detail: 'HTTP assets on HTTPS page: analytics.js, legacy-widget.js',
        },
        {
          severity: 'medium',
          issue: 'Missing Permissions-Policy',
          detail: 'Camera / microphone permissions uncontrolled',
        },
      ],
      cookies: { secure: 3, httponly: 4, samesite: 2, total: 6 },
      csp_directives: [
        { directive: 'default-src', value: 'not set', status: 'missing', risk: 'critical' },
        { directive: 'script-src', value: 'not set', status: 'missing', risk: 'critical' },
        { directive: 'img-src', value: 'not set', status: 'missing', risk: 'high' },
        { directive: 'style-src', value: 'not set', status: 'missing', risk: 'high' },
        { directive: 'connect-src', value: 'not set', status: 'missing', risk: 'medium' },
        { directive: 'frame-ancestors', value: "'none'", status: 'present', risk: 'ok' },
      ],
      sri_missing: ['analytics-loader.js', 'chat-widget.js', 'fonts.css'],
      cors_issues: [
        {
          endpoint: '/api/products',
          method: 'GET',
          issue: 'Access-Control-Allow-Origin: * on authenticated endpoint',
          risk: 'high',
        },
        { endpoint: '/api/user', method: 'POST', issue: 'CORS pre-flight allows all origins', risk: 'medium' },
      ],
      tls_info: { version: 'TLS 1.3', cipher: 'TLS_AES_256_GCM_SHA384', cert_expires: '2026-09-14', grade: 'A' },
    },
    js_audit: {
      total_kb: 840,
      unused_kb: 310,
      unused_pct: 36.9,
      parse_time_ms: 1240,
      execution_time_ms: 890,
      third_party_kb: 280,
      main_thread_cost_ms: 2130,
      blocking_scripts: ['analytics-loader.js', 'chat-widget.js'],
      compression: { raw_kb: 840, gzip_kb: 340, brotli_kb: 280 },
      bundle_modules: [
        { module: 'react + react-dom', size_kb: 142, unused_pct: 2, tree_shakeable: false, type: 'framework' },
        { module: 'moment.js', size_kb: 280, unused_pct: 82, tree_shakeable: false, type: 'library' },
        { module: '@intercom/messenger', size_kb: 98, unused_pct: 45, tree_shakeable: false, type: '3rd-party' },
        { module: 'lodash (full)', size_kb: 72, unused_pct: 91, tree_shakeable: true, type: 'library' },
        { module: 'app bundle', size_kb: 180, unused_pct: 18, tree_shakeable: true, type: 'app' },
        { module: 'analytics-loader', size_kb: 68, unused_pct: 30, tree_shakeable: false, type: '3rd-party' },
      ],
      long_tasks: [
        { task: 'React Hydration', duration_ms: 420, start_ms: 680, culprit: 'app bundle' },
        { task: 'GTM Bootstrap', duration_ms: 320, start_ms: 350, culprit: 'analytics-loader.js' },
        { task: 'Intercom Init', duration_ms: 180, start_ms: 1100, culprit: '@intercom/messenger' },
        { task: 'Moment.js Parse', duration_ms: 140, start_ms: 820, culprit: 'moment.js' },
      ],
      opportunities: [
        { title: 'Remove unused JavaScript', savings_kb: 310, savings_ms: 420 },
        { title: 'Defer offscreen / non-critical scripts', savings_kb: 0, savings_ms: 280 },
        { title: 'Code-split vendor bundle', savings_kb: 180, savings_ms: 190 },
        { title: 'Move analytics to Web Worker', savings_kb: 0, savings_ms: 150 },
      ],
    },
    css_audit: {
      total_kb: 220,
      unused_kb: 128,
      unused_pct: 58.2,
      render_blocking: ['main.css', 'fonts.css'],
      critical_path_kb: 12,
      selector_count: 4820,
      rule_count: 2140,
      font_face_count: 8,
      critical_inline_pct: 18,
      animation_jank_risks: [
        'slide-in animation triggers layout — use transform',
        'Scroll parallax uses top: instead of transform',
      ],
      file_breakdown: [
        { file: 'main.css', total_kb: 140, unused_kb: 98, unused_pct: 70, render_blocking: true },
        { file: 'fonts.css', total_kb: 28, unused_kb: 4, unused_pct: 14, render_blocking: true },
        { file: 'components.css', total_kb: 32, unused_kb: 18, unused_pct: 56, render_blocking: false },
        { file: 'utilities.css', total_kb: 20, unused_kb: 8, unused_pct: 40, render_blocking: false },
      ],
      opportunities: [
        { title: 'Inline critical above-the-fold CSS (12 KB)', savings_kb: 0, savings_ms: 180 },
        { title: 'Remove unused CSS rules (58% unused)', savings_kb: 128, savings_ms: 0 },
        { title: 'Defer non-critical stylesheets', savings_kb: 0, savings_ms: 210 },
        { title: 'Purge Tailwind unused utilities', savings_kb: 85, savings_ms: 0 },
      ],
    },
    input_validation_audit: {
      forms_found: 4,
      csrf_protected: 3,
      client_validated: 3,
      server_side_validated: 2,
      xss_risks: 1,
      injection_risks: 0,
      sanitization_pct: 62,
      open_redirect_risks: 1,
      issues: [
        { name: 'contact_form.email', type: 'email', issue: 'No server-side validation detected', severity: 'high' },
        {
          name: 'search_input',
          type: 'text',
          issue: 'Output not sanitised before DOM insertion — potential XSS',
          severity: 'high',
        },
        { name: 'newsletter_form', type: 'form', issue: 'CSRF token missing', severity: 'medium' },
        { name: 'checkout_coupon', type: 'text', issue: 'Input length unbounded on client side', severity: 'low' },
      ],
      owasp_coverage: [
        { id: 'A01', name: 'Broken Access Control', status: 'pass', risk_level: 'low' },
        { id: 'A02', name: 'Cryptographic Failures', status: 'pass', risk_level: 'low' },
        { id: 'A03', name: 'Injection', status: 'warn', risk_level: 'medium' },
        { id: 'A04', name: 'Insecure Design', status: 'pass', risk_level: 'low' },
        { id: 'A05', name: 'Security Misconfiguration', status: 'fail', risk_level: 'high' },
        { id: 'A06', name: 'Vulnerable Components', status: 'warn', risk_level: 'medium' },
        { id: 'A07', name: 'Auth & Session Mgmt', status: 'pass', risk_level: 'low' },
        { id: 'A08', name: 'Software Integrity Failures', status: 'fail', risk_level: 'high' },
        { id: 'A09', name: 'Logging & Monitoring', status: 'warn', risk_level: 'medium' },
        { id: 'A10', name: 'Server-Side Request Forgery', status: 'pass', risk_level: 'low' },
      ],
      form_audit: [
        {
          form_id: 'contact_form',
          action: '/api/contact',
          csrf: true,
          client_val: true,
          server_val: false,
          inputs: 5,
          risk: 'high',
        },
        {
          form_id: 'search_form',
          action: '/search',
          csrf: false,
          client_val: true,
          server_val: true,
          inputs: 2,
          risk: 'medium',
        },
        {
          form_id: 'newsletter_signup',
          action: '/api/subscribe',
          csrf: false,
          client_val: false,
          server_val: false,
          inputs: 1,
          risk: 'high',
        },
        {
          form_id: 'checkout_form',
          action: '/api/checkout',
          csrf: true,
          client_val: true,
          server_val: true,
          inputs: 12,
          risk: 'low',
        },
      ],
    },
  };
  const now = Date.now();
  return {
    ...base,
    latency_audit: {
      overall: { p50: 480, p75: 890, p95: 2340, p99: 4180 },
      dns: { p50: 12, p75: 28, p95: 65, p99: 120 },
      tcp: { p50: 35, p75: 68, p95: 145, p99: 280 },
      tls: { p50: 52, p75: 98, p95: 210, p99: 390 },
      ttfb: { p50: 280, p75: 520, p95: 1240, p99: 2800 },
      fcp: { p50: 620, p75: 980, p95: 2100, p99: 3800 },
      lcp: { p50: 1840, p75: 2760, p95: 4200, p99: 7100 },
      cdn_edge_latency: { p50: 18, p75: 32, p95: 78, p99: 180 },
      cache_stats: { hit_rate: 0.72, miss_penalty_ms: 310, stale_rate: 0.08 },
      compression_stats: { gzip_pct: 68, brotli_pct: 14, none_pct: 18 },
      waterfall: [
        { name: 'DNS Lookup', start_ms: 0, duration_ms: 28, type: 'dns', size_kb: 0 },
        { name: 'TCP Connect', start_ms: 28, duration_ms: 68, type: 'tcp', size_kb: 0 },
        { name: 'TLS Handshake', start_ms: 96, duration_ms: 98, type: 'tls', size_kb: 0 },
        { name: 'TTFB (main doc)', start_ms: 194, duration_ms: 520, type: 'ttfb', size_kb: 48 },
        { name: 'main.css', start_ms: 714, duration_ms: 180, type: 'css', size_kb: 140 },
        { name: 'app bundle.js', start_ms: 714, duration_ms: 380, type: 'js', size_kb: 340 },
        { name: 'fonts.css', start_ms: 894, duration_ms: 120, type: 'css', size_kb: 28 },
        { name: 'hero-banner.jpg', start_ms: 1280, duration_ms: 420, type: 'image', size_kb: 840 },
        { name: 'analytics-loader.js', start_ms: 1094, duration_ms: 280, type: 'js', size_kb: 68 },
        { name: 'LCP Paint', start_ms: 1700, duration_ms: 0, type: 'metric', size_kb: 0 },
      ],
      endpoints: [
        { url: '/api/products', method: 'GET', p50: 45, p75: 120, p95: 380, p99: 820, error_rate: 0.008 },
        { url: '/api/cart', method: 'POST', p50: 120, p75: 280, p95: 680, p99: 1400, error_rate: 0.021 },
        { url: '/api/auth/session', method: 'GET', p50: 28, p75: 55, p95: 140, p99: 310, error_rate: 0.002 },
      ],
      db_query_distribution: [
        { query: 'SELECT product_catalog', p50: 12, p75: 28, p95: 95, p99: 240 },
        { query: 'SELECT user_sessions', p50: 8, p75: 18, p95: 62, p99: 180 },
        { query: 'UPDATE cart_items', p50: 24, p75: 58, p95: 180, p99: 420 },
      ],
    },
    outdated_audit: {
      total_deps: 142,
      outdated_count: 23,
      critical_outdated: 4,
      security_risk_score: 62,
      cve_count: 5,
      deps: [
        { name: 'next', current: '13.4.0', latest: '15.3.1', severity: 'critical', type: 'framework', has_cve: true },
        { name: 'react', current: '18.2.0', latest: '19.1.0', severity: 'high', type: 'framework', has_cve: false },
        { name: 'eslint', current: '8.40.0', latest: '9.25.1', severity: 'medium', type: 'dev', has_cve: false },
        { name: 'tailwindcss', current: '3.3.2', latest: '4.1.5', severity: 'medium', type: 'dev', has_cve: false },
        { name: 'axios', current: '1.3.4', latest: '1.8.4', severity: 'low', type: 'library', has_cve: true },
      ],
      cves: [
        { pkg: 'next@13.4.0', cve: 'CVE-2024-34351', severity: 'high', cvss: 7.5, patched_in: '14.2.1' },
        { pkg: 'next@13.4.0', cve: 'CVE-2024-46982', severity: 'critical', cvss: 9.1, patched_in: '14.2.10' },
        { pkg: 'axios@1.3.4', cve: 'CVE-2024-39338', severity: 'medium', cvss: 5.3, patched_in: '1.7.4' },
        { pkg: 'next@13.4.0', cve: 'CVE-2025-29927', severity: 'critical', cvss: 9.1, patched_in: '15.2.3' },
        { pkg: 'axios@1.3.4', cve: 'CVE-2023-45857', severity: 'medium', cvss: 6.5, patched_in: '1.6.0' },
      ],
      upgrade_matrix: [
        { name: 'next', from_ver: '13.4.0', to_ver: '15.3.1', breaking_changes: 3, effort: 'high', security_fix: true },
        {
          name: 'react',
          from_ver: '18.2.0',
          to_ver: '19.1.0',
          breaking_changes: 1,
          effort: 'medium',
          security_fix: false,
        },
        { name: 'axios', from_ver: '1.3.4', to_ver: '1.8.4', breaking_changes: 0, effort: 'low', security_fix: true },
        {
          name: 'tailwindcss',
          from_ver: '3.3.2',
          to_ver: '4.1.5',
          breaking_changes: 2,
          effort: 'high',
          security_fix: false,
        },
      ],
      deprecated_apis: [
        {
          api: 'getInitialProps',
          used_in: 'pages/_app.tsx',
          alternative: 'getServerSideProps or App Router',
          eol: '2024-01',
        },
        {
          api: 'window.webkitRequestAnimationFrame',
          used_in: 'src/utils/animation.ts',
          alternative: 'requestAnimationFrame',
          eol: '2023-06',
        },
      ],
      legacy_patterns: [
        { pattern: 'var declarations (14 found)', file: 'src/legacy/*.js', recommendation: 'Replace with const/let' },
        {
          pattern: 'Non-passive scroll event listeners',
          file: 'src/components/Header.tsx',
          recommendation: 'Add { passive: true } for scroll perf',
        },
        {
          pattern: 'Synchronous XHR',
          file: 'src/utils/api-compat.js',
          recommendation: 'Replace with fetch() or axios',
        },
      ],
    },
    workflow_audit: {
      pipeline_status: 'partial_pass',
      last_run: new Date(now - 3600000).toISOString(),
      test_coverage_pct: 74,
      mean_deploy_mins: 18,
      mean_recovery_mins: 42,
      build_trend: [
        { date: 'Apr-25', duration_mins: 14, status: 'pass' },
        { date: 'Apr-26', duration_mins: 16, status: 'pass' },
        { date: 'Apr-27', duration_mins: 22, status: 'fail' },
        { date: 'Apr-28', duration_mins: 18, status: 'pass' },
        { date: 'Apr-29', duration_mins: 19, status: 'pass' },
        { date: 'Apr-30', duration_mins: 21, status: 'warn' },
        { date: 'May-01', duration_mins: 18, status: 'pass' },
      ],
      flaky_tests: [
        { test: 'CartFlow > payment_form_renders', flakiness_rate: 0.18, suite: 'E2E', last_failed: '2026-04-30' },
        { test: 'SearchResults > hydration_completes', flakiness_rate: 0.12, suite: 'E2E', last_failed: '2026-04-29' },
        { test: 'ProductCard > image_lazy_loads', flakiness_rate: 0.08, suite: 'Unit', last_failed: '2026-04-28' },
      ],
      steps: [
        { name: 'Lint', status: 'passed', duration_ms: 8200, passed: true },
        { name: 'TypeCheck', status: 'passed', duration_ms: 14600, passed: true },
        { name: 'Unit Tests', status: 'passed', duration_ms: 42000, passed: true },
        { name: 'Perf Budget Check', status: 'failed', duration_ms: 6100, passed: false },
        { name: 'E2E Tests', status: 'passed', duration_ms: 186000, passed: true },
        { name: 'Lighthouse CI', status: 'warning', duration_ms: 38000, passed: false },
        { name: 'Deploy Preview', status: 'passed', duration_ms: 74000, passed: true },
      ],
      pr_checks: [
        { check: 'Perf regression < 5ms LCP delta', status: 'fail', required: true },
        { check: 'Bundle size < 500 KB gzip', status: 'pass', required: true },
        { check: 'A11y score ≥ 90', status: 'pass', required: false },
        { check: 'No critical security headers missing', status: 'fail', required: false },
      ],
      deployments: [
        {
          version: 'v2.14.1',
          deployed_at: new Date(now - 86400000).toISOString(),
          status: 'stable',
          perf_delta_ms: -40,
        },
        {
          version: 'v2.14.0',
          deployed_at: new Date(now - 172800000).toISOString(),
          status: 'stable',
          perf_delta_ms: 80,
        },
        {
          version: 'v2.13.9',
          deployed_at: new Date(now - 259200000).toISOString(),
          status: 'rolled_back',
          perf_delta_ms: 340,
          rollback: true,
        },
      ],
      integration_health: {
        'GitHub Actions': 'healthy',
        Vercel: 'healthy',
        DataDog: 'degraded',
        Sentry: 'healthy',
      },
    },
    data_analysis: {
      cohort_trend: [
        { period: 'W-5', score: 72, lcp: 3200, sessions: 8400 },
        { period: 'W-4', score: 74, lcp: 3050, sessions: 9100 },
        { period: 'W-3', score: 76, lcp: 2980, sessions: 9800 },
        { period: 'W-2', score: 75, lcp: 3010, sessions: 10200 },
        { period: 'W-1', score: 78, lcp: 2890, sessions: 11400 },
        { period: 'Now', score: 78, lcp: 2890, sessions: 14820 },
      ],
      funnel: [
        { name: 'Page View', users: 14820, drop_pct: 0 },
        { name: 'First Interaction', users: 11340, drop_pct: 23.5 },
        { name: 'Product Click', users: 7820, drop_pct: 31 },
        { name: 'Add to Cart', users: 2940, drop_pct: 62.4 },
        { name: 'Checkout', users: 1180, drop_pct: 59.9 },
        { name: 'Purchase', users: 820, drop_pct: 30.5 },
      ],
      anomalies: [
        { ts: new Date(now - 7200000).toISOString(), metric: 'LCP', value: 4800, expected: 2890, severity: 'high' },
        { ts: new Date(now - 86400000).toISOString(), metric: 'INP', value: 620, expected: 245, severity: 'medium' },
        { ts: new Date(now - 172800000).toISOString(), metric: 'TTFB', value: 1840, expected: 620, severity: 'medium' },
      ],
      segment_breakdown: {
        'Organic Search': { score: 82, lcp: 2540, sessions: 6200 },
        Direct: { score: 79, lcp: 2780, sessions: 4100 },
        Paid: { score: 71, lcp: 3280, sessions: 2800 },
        Social: { score: 68, lcp: 3640, sessions: 1720 },
      },
      bot_traffic_pct: 12.4,
      crawl_efficiency: 87,
      index_coverage: { indexed: 2840, total_submitted: 3100, errors: 42 },
      retention: [
        { week: 'W-5', d1_pct: 42, d7_pct: 18, d30_pct: 8 },
        { week: 'W-4', d1_pct: 44, d7_pct: 19, d30_pct: 9 },
        { week: 'W-3', d1_pct: 46, d7_pct: 21, d30_pct: 10 },
        { week: 'W-2', d1_pct: 45, d7_pct: 20, d30_pct: 9 },
        { week: 'W-1', d1_pct: 48, d7_pct: 22, d30_pct: 11 },
      ],
      revenue_by_channel: [
        { channel: 'Organic Search', revenue_usd: 42800, sessions: 6200, conv_rate: 0.062 },
        { channel: 'Direct', revenue_usd: 31200, sessions: 4100, conv_rate: 0.071 },
        { channel: 'Paid Search', revenue_usd: 18400, sessions: 2800, conv_rate: 0.048 },
        { channel: 'Social', revenue_usd: 7200, sessions: 1720, conv_rate: 0.031 },
        { channel: 'Email', revenue_usd: 12600, sessions: 980, conv_rate: 0.112 },
      ],
      search_console: {
        impressions: 284000,
        clicks: 18420,
        ctr_pct: 6.5,
        avg_position: 12.4,
        top_queries: [
          { query: 'best running shoes', clicks: 2840, position: 4.2 },
          { query: 'buy sneakers online', clicks: 1920, position: 6.8 },
          { query: 'sports footwear sale', clicks: 1480, position: 8.1 },
          { query: 'running shoe reviews', clicks: 1240, position: 5.4 },
          { query: 'athletic shoes discount', clicks: 980, position: 11.2 },
        ],
      },
    },
    core_seo_suite: {
      overview_score: 88,
      coverage: 91,
      opportunity_count: 17,
      distribution: [
        { label: 'Healthy', value: 58, color: '#22c55e' },
        { label: 'Needs Work', value: 28, color: '#f59e0b' },
        { label: 'Critical', value: 14, color: '#ef4444' },
      ],
      timeline: [
        { label: 'Q1', value: 72 },
        { label: 'Q2', value: 79 },
        { label: 'Q3', value: 84 },
        { label: 'Now', value: 88 },
      ],
      highlights: [
        'Core SEO coverage spans keywords, technical health, backlinks, on-page, rank tracking, E-E-A-T, and entity-first signals.',
        'Backlink intelligence has 4 reclamation workflows and digital PR outreach segments queued.',
      ],
      risks: [
        'Keyword cannibalization still affects 14 landing page clusters.',
        'Two high-value product templates are missing author trust annotations.',
      ],
      modules: [
        {
          name: 'Core SEO Foundations',
          status: 'strong',
          score: 92,
          summary: 'Keywords, rank, backlinks, technical, and on-page signals are modeled together for fast diagnosis.',
          metrics: [
            { label: 'Tracked SERPs', value: '18 engines' },
            { label: 'Pages scored', value: '12,480' },
            { label: 'Priority gaps', value: '17' },
          ],
          automations: ['Health digest', 'Cluster alerts'],
        },
        {
          name: 'Keyword Research Engine',
          status: 'ready',
          score: 90,
          summary: 'Intent clustering, gap detection, and long-tail opportunity mining for core and AI surfaces.',
          metrics: [
            { label: 'Keywords', value: '48,320' },
            { label: 'Intent clusters', value: '1,284' },
            { label: 'Opportunity score', value: '84' },
          ],
          automations: ['Topic gap mining', 'Seasonality watch'],
          issues: ['14 keyword clusters overlap between blog and commercial URLs'],
        },
        {
          name: 'On-Page SEO Optimizer',
          status: 'building',
          score: 82,
          summary: 'Titles, headers, internal links, schema, media alt coverage, and entity reinforcement in one pass.',
          metrics: [
            { label: 'Pages passing', value: '83%' },
            { label: 'Schema coverage', value: '71%' },
            { label: 'Internal link depth', value: '2.8 avg' },
          ],
          automations: ['Metadata suggestions', 'Heading repair'],
          issues: ['47 pages exceed title length budget'],
        },
        {
          name: 'Technical SEO Auditor',
          status: 'watch',
          score: 79,
          summary:
            'Crawlability, renderability, indexation, canonicals, unused ports, and OWASP-adjacent exposure checks.',
          metrics: [
            { label: 'Crawl success', value: '96.8%' },
            { label: 'Indexable URLs', value: '2,840' },
            { label: 'Unused ports', value: '3 exposed' },
          ],
          automations: ['Canonical drift alerts', 'Port exposure audit'],
          issues: ['Open preview port on staging edge node', '9 pages still emit conflicting canonicals'],
        },
        {
          name: 'Backlink Intelligence Engine',
          status: 'ready',
          score: 87,
          summary: 'Authority trend, toxic domain screening, reclamation, and outreach segmentation for link building.',
          metrics: [
            { label: 'Referring domains', value: '6,412' },
            { label: 'Toxic share', value: '1.9%' },
            { label: 'Reclamation wins', value: '28' },
          ],
          automations: ['Brand mention reclaim', 'Digital PR queue'],
        },
        {
          name: 'Advanced Rank Tracking',
          status: 'ready',
          score: 89,
          summary: 'Daily rank tracking across mobile, desktop, regional, answer-engine, and AI result surfaces.',
          metrics: [
            { label: 'Keywords in top 3', value: '1,082' },
            { label: 'Winners today', value: '119' },
            { label: 'SERP volatility', value: 'Medium' },
          ],
          automations: ['Rank anomaly alerts'],
        },
        {
          name: 'E-E-A-T Optimization Suite',
          status: 'building',
          score: 80,
          summary:
            'Author identity, trust blocks, evidence depth, editorial transparency, and citation quality scoring.',
          metrics: [
            { label: 'Author pages', value: '74%' },
            { label: 'Trust widgets', value: '61%' },
            { label: 'Citation score', value: '78' },
          ],
          issues: ['Product comparison pages lack reviewer credentials'],
        },
        {
          name: 'Entity-First SEO',
          status: 'partial',
          score: 77,
          summary: 'Knowledge graph alignment, entity disambiguation, and topic authority reinforcement.',
          metrics: [
            { label: 'Entities mapped', value: '3,208' },
            { label: 'Graph confidence', value: '76%' },
            { label: 'Entity gaps', value: '112' },
          ],
          issues: ['Three product families have weak entity linking to supporting docs'],
        },
        {
          name: 'Autonomous Link Building',
          status: 'building',
          score: 75,
          summary: 'Autonomous outreach, digital PR, unlinked mention reclamation, and prospect scoring.',
          metrics: [
            { label: 'Prospects scored', value: '5,480' },
            { label: 'Reply rate', value: '11.8%' },
            { label: 'Recovered mentions', value: '43' },
          ],
          automations: ['Pitch personalization', 'Broken link recovery'],
        },
        {
          name: 'Knowledge Graph Management',
          status: 'building',
          score: 79,
          summary:
            'Entity graph construction, enrichment, validation, and relationship drift monitoring for semantic authority.',
          metrics: [
            { label: 'Graph nodes', value: '84,220' },
            { label: 'Validated relations', value: '91%' },
            { label: 'Entity conflicts', value: '43' },
          ],
          issues: ['42 category entities still miss canonical parent links'],
        },
        {
          name: 'AI Internal Linking Engine',
          status: 'partial',
          score: 78,
          summary:
            'Semantic internal-link opportunity detection and authority-flow optimization across hub-spoke clusters.',
          metrics: [
            { label: 'Link opportunities', value: '1,328' },
            { label: 'Accepted suggestions', value: '63%' },
            { label: 'Orphan pages', value: '58' },
          ],
          automations: ['Context link suggestions', 'Orphan recovery'],
        },
        {
          name: 'Crawl Budget Optimizer',
          status: 'building',
          score: 77,
          summary: 'Log-driven crawl prioritization, waste reduction, and recrawl scheduling by value and freshness.',
          metrics: [
            { label: 'Waste crawl share', value: '11.2%' },
            { label: 'Priority URLs', value: '6,410' },
            { label: 'Bot efficiency', value: '86%' },
          ],
          issues: ['Filtered sort URLs still absorb 7% of bot activity'],
        },
      ],
    },
    content_blog_suite: {
      overview_score: 85,
      coverage: 88,
      opportunity_count: 21,
      distribution: [
        { label: 'Production', value: 52, color: '#22c55e' },
        { label: 'Editorial QA', value: 31, color: '#6366f1' },
        { label: 'Needs Workflow', value: 17, color: '#f59e0b' },
      ],
      timeline: [
        { label: 'Brief', value: 68 },
        { label: 'Draft', value: 75 },
        { label: 'Optimize', value: 82 },
        { label: 'Publish', value: 85 },
      ],
      highlights: [
        'Blogging workflows now span AI writing, briefs, NLP scoring, CMS publishing, and programmatic page generation.',
        'News SEO and Google Discover patterns are separated from evergreen blog clusters.',
      ],
      risks: ['36 blog templates still publish without FAQ schema or author freshness stamps.'],
      modules: [
        {
          name: 'Content Creation & Blogging Suite',
          status: 'strong',
          score: 89,
          summary: 'Editorial planning, blogging operations, and automated refresh flows are tracked together.',
          metrics: [
            { label: 'Articles managed', value: '3,420' },
            { label: 'Refresh backlog', value: '132' },
            { label: 'Publish SLA', value: '94%' },
          ],
        },
        {
          name: 'AI Writing',
          status: 'ready',
          score: 87,
          summary: 'Intent-aware drafting with brand-safe voice rules and section-level quality scoring.',
          metrics: [
            { label: 'Drafts/week', value: '84' },
            { label: 'Human edits', value: '22%' },
            { label: 'Brand score', value: '91' },
          ],
          automations: ['Outline generation', 'Angle variation'],
        },
        {
          name: 'Briefs',
          status: 'ready',
          score: 86,
          summary: 'SERP-derived content briefs with entities, questions, and competitive gap extraction.',
          metrics: [
            { label: 'Brief coverage', value: '93%' },
            { label: 'Competitors sampled', value: '12 avg' },
            { label: 'Question clusters', value: '8 / brief' },
          ],
        },
        {
          name: 'NLP Editor',
          status: 'building',
          score: 81,
          summary: 'Semantic coverage, readability, fact density, and entity completeness inside the editor.',
          metrics: [
            { label: 'Semantic score', value: '78' },
            { label: 'Readability', value: 'Grade 8.6' },
            { label: 'Missing entities', value: '37' },
          ],
          issues: ['How-to templates still underweight supporting evidence blocks'],
        },
        {
          name: 'CMS Workflow',
          status: 'partial',
          score: 79,
          summary: 'Publishing orchestration for blog, docs, landing, and newsroom surfaces.',
          metrics: [
            { label: 'Connected CMSs', value: '4' },
            { label: 'Sync lag', value: '6 min' },
            { label: 'Broken embeds', value: '12' },
          ],
          automations: ['Auto-tagging', 'Slug guards'],
        },
        {
          name: 'Programmatic SEO Engine',
          status: 'building',
          score: 76,
          summary: 'Template × data = pages at scale with quality, dedupe, and indexation control.',
          metrics: [
            { label: 'Generated pages', value: '18,200' },
            { label: 'Indexed', value: '72%' },
            { label: 'Thin-content risk', value: '4.8%' },
          ],
          issues: ['City landing pages need stronger local entity enrichment'],
        },
        {
          name: 'News SEO & Google Discover',
          status: 'watch',
          score: 73,
          summary: 'Recency, headline testing, freshness markup, and Discover image constraints.',
          metrics: [
            { label: 'Discover CTR', value: '4.2%' },
            { label: 'Freshness lag', value: '19 min' },
            { label: 'Article schema', value: '81%' },
          ],
          issues: ['12 stories missed max-image-preview requirements'],
        },
        {
          name: 'Topical Map & Silo Builder',
          status: 'building',
          score: 82,
          summary:
            'Topic clustering, hub-spoke architecture, and editorial map generation tied to intent and entities.',
          metrics: [
            { label: 'Topic clusters', value: '612' },
            { label: 'Hub pages', value: '184' },
            { label: 'Silo integrity', value: '88%' },
          ],
          automations: ['Cluster expansion', 'Silo gap alerts'],
        },
        {
          name: 'Brand Voice & Style Engine',
          status: 'partial',
          score: 80,
          summary: 'Brand-consistent rewriting, tone governance, and style-guard enforcement for SEO content at scale.',
          metrics: [
            { label: 'Voice compliance', value: '91%' },
            { label: 'Tone drift flags', value: '28' },
            { label: 'Editorial overrides', value: '14%' },
          ],
        },
        {
          name: 'Landing Page Builder',
          status: 'building',
          score: 78,
          summary:
            'Template-driven conversion landing pages with schema hooks, experimentation, and distribution wiring.',
          metrics: [
            { label: 'Generated LPs', value: '420' },
            { label: 'Schema-ready', value: '87%' },
            { label: 'Avg conversion lift', value: '+9.4%' },
          ],
          automations: ['Variant generation', 'CTA optimization'],
        },
        {
          name: 'Review & Reputation Engine',
          status: 'partial',
          score: 77,
          summary:
            'Review mining, sentiment intelligence, and response workflow optimization for trust and visibility.',
          metrics: [
            { label: 'Reviews analyzed', value: '12,840' },
            { label: 'Avg sentiment', value: '0.68' },
            { label: 'Response SLA', value: '84%' },
          ],
        },
        {
          name: 'Social SEO & Distribution',
          status: 'building',
          score: 76,
          summary: 'Search-aware social distribution and multi-surface promotion workflows for content amplification.',
          metrics: [
            { label: 'Cross-post workflows', value: '34' },
            { label: 'Surface reach', value: '3.8M' },
            { label: 'Assisted clicks', value: '11,280' },
          ],
        },
      ],
    },
    ai_optimization_suite: {
      overview_score: 82,
      coverage: 86,
      opportunity_count: 24,
      distribution: [
        { label: 'Agent-ready', value: 39, color: '#22c55e' },
        { label: 'Crawlable', value: 34, color: '#6366f1' },
        { label: 'Needs structuring', value: 27, color: '#f59e0b' },
      ],
      timeline: [
        { label: 'Promptable', value: 61 },
        { label: 'Structured', value: 70 },
        { label: 'Citable', value: 77 },
        { label: 'Now', value: 82 },
      ],
      highlights: [
        'AIO, AIO-2, AEO, GEO, LLMO, SAGEO, and predictive algorithm coverage now sit in one AI optimization view.',
        'Machine-parseable content readiness is highest on docs and product comparison content.',
      ],
      risks: [
        'Brand accuracy drift appears in third-party LLM answer snapshots for two pricing claims.',
        'Agentic content contracts are incomplete for long-form comparison pages.',
      ],
      modules: [
        {
          name: 'SEO-AI',
          status: 'ready',
          score: 88,
          summary: 'Traditional SEO enriched with AI scoring, prioritization, clustering, and automated fixes.',
          metrics: [
            { label: 'AI triage coverage', value: '93%' },
            { label: 'Auto-prioritized fixes', value: '412' },
            { label: 'Win rate', value: '68%' },
          ],
        },
        {
          name: 'AIO: AI Optimization',
          status: 'building',
          score: 81,
          summary: 'Machine-parseable content, structured data density, and chunk-ready semantics for AI systems.',
          metrics: [
            { label: 'Parseable blocks', value: '74%' },
            { label: 'Schema density', value: '2.4 / page' },
            { label: 'Chunk quality', value: '79' },
          ],
          issues: ['Long landing pages still mix multiple answer intents in one block'],
        },
        {
          name: 'AIO-2: Agentic Intelligence Optimization',
          status: 'partial',
          score: 76,
          summary:
            'Content contracts for the AI agent economy with actionability, trust boundaries, and tool-use metadata.',
          metrics: [
            { label: 'Agent-safe pages', value: '61%' },
            { label: 'Action schemas', value: '184' },
            { label: 'Task coverage', value: '58%' },
          ],
        },
        {
          name: 'AEO: Answer Engine Optimization',
          status: 'ready',
          score: 84,
          summary:
            'OpenLens + Playwright + LlamaIndex + JSON-LD optimization for answer engine retrieval and answer precision.',
          metrics: [
            { label: 'Answer blocks', value: '1,940' },
            { label: 'Featured answer rate', value: '28%' },
            { label: 'Direct-answer CTR', value: '12.6%' },
          ],
        },
        {
          name: 'GEO: Generative Engine Optimization',
          status: 'building',
          score: 80,
          summary:
            'Llama-3 + RAG over SERPs, AI answers, and site content for generative overview inclusion and citation wins.',
          metrics: [
            { label: 'Citation win rate', value: '19%' },
            { label: 'Overview mentions', value: '214' },
            { label: 'Source clarity', value: '82' },
          ],
        },
        {
          name: 'LLMO: Large Language Model Optimization',
          status: 'watch',
          score: 74,
          summary:
            'LLM optimization for brand accuracy, retrieval quality, factual consistency, and answer reliability.',
          metrics: [
            { label: 'Brand match', value: '88%' },
            { label: 'Fact drift', value: '6.1%' },
            { label: 'LLM snapshots', value: '820/day' },
          ],
          issues: ['Two outdated pricing values still surface in archived model answers'],
        },
        {
          name: 'SAGEO: Search-Augmented Generative SEO',
          status: 'partial',
          score: 78,
          summary: 'Dual-channel optimization for classic SERPs and retrieval-augmented generative systems.',
          metrics: [
            { label: 'Dual-win pages', value: '42%' },
            { label: 'Retrieval freshness', value: '89%' },
            { label: 'Source overlap', value: '67%' },
          ],
        },
        {
          name: 'PEAO: Predictive Engine Algorithm Optimization',
          status: 'building',
          score: 73,
          summary: 'Algorithm-shift forecasting and proactive page refresh prioritization.',
          metrics: [
            { label: 'Forecast horizon', value: '21 days' },
            { label: 'Predicted movers', value: '126' },
            { label: 'Model confidence', value: '71%' },
          ],
        },
        {
          name: 'AI Schema Engine',
          status: 'building',
          score: 79,
          summary: 'Automated schema generation, validation, and enrichment with AI-assisted property completion.',
          metrics: [
            { label: 'Schema templates', value: '42' },
            { label: 'Validation pass', value: '89%' },
            { label: 'Enhancements applied', value: '1,204' },
          ],
        },
        {
          name: 'RAG Site Search Engine',
          status: 'partial',
          score: 75,
          summary: 'Semantic site search powered by retrieval and reasoning with citation grounding and reranking.',
          metrics: [
            { label: 'Grounded answers', value: '82%' },
            { label: 'Median latency', value: '820 ms' },
            { label: 'No-answer rate', value: '9.4%' },
          ],
        },
        {
          name: 'Content Quality & Hallucination Auditor',
          status: 'watch',
          score: 72,
          summary:
            'Factuality, citation quality, contradiction detection, and hallucination risk scoring for AI-assisted content.',
          metrics: [
            { label: 'Claims audited/day', value: '9,600' },
            { label: 'Citation coverage', value: '78%' },
            { label: 'Hallucination risk', value: 'Low-Med' },
          ],
          issues: ['Long-form explainers still show sparse source attribution in deep sections'],
        },
        {
          name: 'AI Technical SEO Engine',
          status: 'building',
          score: 77,
          summary: 'Autonomous technical SEO diagnosis and remediation with prioritization by traffic and risk impact.',
          metrics: [
            { label: 'Issues triaged/day', value: '680' },
            { label: 'Auto-remediation rate', value: '41%' },
            { label: 'Critical MTTR', value: '5.6 hrs' },
          ],
        },
      ],
    },
    search_experience_suite: {
      overview_score: 79,
      coverage: 83,
      opportunity_count: 19,
      distribution: [
        { label: 'Search UX strong', value: 41, color: '#22c55e' },
        { label: 'Voice / AI visible', value: 29, color: '#6366f1' },
        { label: 'Surface gaps', value: 30, color: '#f59e0b' },
      ],
      timeline: [
        { label: 'Query', value: 64 },
        { label: 'Answer', value: 70 },
        { label: 'Experience', value: 75 },
        { label: 'Now', value: 79 },
      ],
      highlights: [
        'Voice, search experience, generative experience, conversational answers, and multi-surface visibility are tracked together.',
      ],
      risks: [
        'Conversational answer pages still overload the first response with too many product qualifiers.',
        'CTV and wearable surfaces are thin on structured summaries.',
      ],
      modules: [
        {
          name: 'VSO: Voice Search Optimization',
          status: 'partial',
          score: 77,
          summary: 'Natural-language phrasing, concise answers, FAQ breadth, and speakable markup readiness.',
          metrics: [
            { label: 'Voice-answer coverage', value: '58%' },
            { label: 'Avg answer length', value: '29 words' },
            { label: 'Speakable markup', value: '43%' },
          ],
        },
        {
          name: 'SXO: Search Experience Optimization',
          status: 'building',
          score: 81,
          summary: 'SERP intent alignment, landing experience, UX friction, and conversion continuity after the click.',
          metrics: [
            { label: 'Intent match', value: '84%' },
            { label: 'Bounce delta', value: '-11%' },
            { label: 'UX friction', value: '39' },
          ],
          issues: ['Mobile collection pages still require too many filters before product visibility'],
        },
        {
          name: 'GXO: Generative Experience Optimization',
          status: 'building',
          score: 78,
          summary: 'AI overviews, SGE-like panels, and generative summaries mapped to post-click satisfaction.',
          metrics: [
            { label: 'Overview share', value: '17%' },
            { label: 'Summary CTR', value: '8.4%' },
            { label: 'Summary sentiment', value: 'Positive' },
          ],
        },
        {
          name: 'CXAO: Conversational Experience Answer Optimization',
          status: 'watch',
          score: 74,
          summary: 'Dialog-shaped answers, follow-up handling, and structured conversational turn design.',
          metrics: [
            { label: 'Follow-up coverage', value: '46%' },
            { label: 'Turn depth', value: '2.8 avg' },
            { label: 'Clarification rate', value: '31%' },
          ],
        },
        {
          name: 'MSVO: Multi-Surface Visibility Optimization',
          status: 'partial',
          score: 72,
          summary: 'Visibility across AR/VR, wearables, CTV, voice devices, and smart assistants.',
          metrics: [
            { label: 'Surfaces mapped', value: '7' },
            { label: 'Surface-ready assets', value: '52%' },
            { label: 'CTV metadata', value: '38%' },
          ],
          issues: ['Wearable answer cards lack concise fallback copy'],
        },
        {
          name: 'Search Intelligence',
          status: 'building',
          score: 80,
          summary:
            'Unified intelligence across SERP volatility, AI surfaces, click shifts, and intent migration signals.',
          metrics: [
            { label: 'Signals ingested/day', value: '3.2M' },
            { label: 'Volatility alerts', value: '34' },
            { label: 'Insight precision', value: '87%' },
          ],
        },
        {
          name: 'UX & Conversion Optimizer',
          status: 'partial',
          score: 78,
          summary: 'Behavior, conversion, and UX optimization from search traffic through funnel milestones.',
          metrics: [
            { label: 'Funnel drop recovered', value: '12.4%' },
            { label: 'Search LP CVR', value: '4.8%' },
            { label: 'UX issues queued', value: '26' },
          ],
        },
      ],
    },
    vertical_seo_suite: {
      overview_score: 81,
      coverage: 85,
      opportunity_count: 18,
      distribution: [
        { label: 'Revenue verticals', value: 44, color: '#22c55e' },
        { label: 'Regional / local', value: 31, color: '#6366f1' },
        { label: 'Migration risk', value: 25, color: '#f59e0b' },
      ],
      timeline: [
        { label: 'Plan', value: 66 },
        { label: 'Launch', value: 73 },
        { label: 'Scale', value: 78 },
        { label: 'Now', value: 81 },
      ],
      highlights: [
        'eCommerce, international, migration, video, local, and decentralized answer surfaces are coordinated in one operations lane.',
      ],
      risks: [
        'Hreflang gaps still exist across 4 regionalized content hubs.',
        'Faceted navigation produces thin pages when low-stock filters combine with brand filters.',
      ],
      modules: [
        {
          name: 'eCommerce SEO Suite',
          status: 'building',
          score: 83,
          summary: 'Product, category, faceted navigation, dynamic schema, and stock-aware indexation controls.',
          metrics: [
            { label: 'Products optimized', value: '28,400' },
            { label: 'Category hubs', value: '412' },
            { label: 'Facet risk', value: '6.2%' },
          ],
        },
        {
          name: 'International & Multilingual SEO',
          status: 'partial',
          score: 78,
          summary: 'Regional engines, hreflang integrity, language clusters, and regional ranking visibility.',
          metrics: [
            { label: 'Locales', value: '14' },
            { label: 'Hreflang pass', value: '87%' },
            { label: 'Regional winners', value: '164' },
          ],
        },
        {
          name: 'Site Migration SEO Manager',
          status: 'watch',
          score: 76,
          summary:
            'Pre/during/post migration checks for redirects, parity, canonicals, internal links, and traffic protection.',
          metrics: [
            { label: 'Redirect map', value: '98%' },
            { label: 'Parity score', value: '81' },
            { label: 'Broken links', value: '37' },
          ],
          issues: ['Legacy media URLs still bypass the canonical redirect map'],
        },
        {
          name: 'Video SEO Module',
          status: 'partial',
          score: 79,
          summary: 'YouTube, VideoObject, transcripts, chapters, and thumbnail optimization.',
          metrics: [
            { label: 'VideoObject coverage', value: '69%' },
            { label: 'Transcript coverage', value: '74%' },
            { label: 'Chapter markup', value: '58%' },
          ],
        },
        {
          name: 'Local SEO Suite',
          status: 'building',
          score: 80,
          summary: 'GBP, NAP consistency, citations, reviews, and hyperlocal landing content.',
          metrics: [
            { label: 'Locations', value: '248' },
            { label: 'NAP consistency', value: '93%' },
            { label: 'Local pack rate', value: '26%' },
          ],
        },
        {
          name: 'DAEO: Decentralized Answer Engine Optimization',
          status: 'watch',
          score: 67,
          summary: 'Web3 and decentralized knowledge surfaces with wallet-aware entity trust patterns.',
          metrics: [
            { label: 'Wallet-ready docs', value: '38%' },
            { label: 'On-chain entities', value: '124' },
            { label: 'Trust proofs', value: '52%' },
          ],
          issues: ['On-chain reference formatting is inconsistent across protocol pages'],
        },
        {
          name: 'Image & Media SEO Engine',
          status: 'building',
          score: 79,
          summary: 'Alt text generation, metadata normalization, compression policy, and media discovery optimization.',
          metrics: [
            { label: 'Media indexed', value: '68%' },
            { label: 'Alt coverage', value: '91%' },
            { label: 'Compression gain', value: '24%' },
          ],
        },
        {
          name: 'Accessibility Optimizer',
          status: 'partial',
          score: 76,
          summary: 'WCAG-driven accessibility improvements mapped to search discoverability and assistive UX outcomes.',
          metrics: [
            { label: 'WCAG pass rate', value: '84%' },
            { label: 'Readability score', value: '79' },
            { label: 'A11y blockers', value: '18' },
          ],
        },
      ],
    },
    platform_ops_suite: {
      overview_score: 84,
      coverage: 89,
      opportunity_count: 22,
      distribution: [
        { label: 'Automated', value: 47, color: '#22c55e' },
        { label: 'Observable', value: 33, color: '#6366f1' },
        { label: 'Operational risk', value: 20, color: '#f59e0b' },
      ],
      timeline: [
        { label: 'Ops', value: 70 },
        { label: 'Security', value: 76 },
        { label: 'UX', value: 81 },
        { label: 'Now', value: 84 },
      ],
      highlights: [
        'Platform operations now include security, OWASP, unused ports, UI/UX issues, loading-time issue tracking, analytics, agency, and automation layers.',
        'Autonomous agent orchestration is tied to A/B testing and reporting instead of sitting outside the SEO stack.',
      ],
      risks: [
        'Three stale service ports remain reachable from staging.',
        'Mobile filter drawer still adds 420 ms scripting delay during first interaction.',
      ],
      modules: [
        {
          name: 'Autonomous Agent Engine',
          status: 'building',
          score: 82,
          summary: 'Master AI orchestration brain coordinating audits, content, fixes, outreach, and experimentation.',
          metrics: [
            { label: 'Agent flows', value: '38' },
            { label: 'Autonomous actions/day', value: '2,180' },
            { label: 'Human approval rate', value: '31%' },
          ],
          automations: ['Fix routing', 'Content routing', 'Ops triage'],
        },
        {
          name: 'SEO A/B Testing Framework',
          status: 'ready',
          score: 86,
          summary: 'Experimentation framework for titles, snippets, templates, internal links, and answer blocks.',
          metrics: [
            { label: 'Active tests', value: '26' },
            { label: 'Winning tests', value: '61%' },
            { label: 'Median lift', value: '+8.2%' },
          ],
        },
        {
          name: 'Analytics, Reporting & Intelligence',
          status: 'ready',
          score: 88,
          summary:
            'Executive dashboards, anomaly alerts, tenant reporting, attribution, and AI visibility intelligence.',
          metrics: [
            { label: 'Dashboards', value: '42' },
            { label: 'Scheduled reports', value: '118' },
            { label: 'Alert precision', value: '92%' },
          ],
        },
        {
          name: 'Agency & Multi-Tenant Platform',
          status: 'partial',
          score: 80,
          summary: 'Tenant isolation, portfolio rollups, delegated approvals, and white-label reporting.',
          metrics: [
            { label: 'Tenants', value: '184' },
            { label: 'Shared templates', value: '62' },
            { label: 'Seat utilization', value: '78%' },
          ],
        },
        {
          name: 'Integrations & Automation Layer',
          status: 'ready',
          score: 85,
          summary: 'CMS, analytics, search console, BI, social, CRM, and deployment hooks for SEO workflows.',
          metrics: [
            { label: 'Connected tools', value: '27' },
            { label: 'Workflow success', value: '97.1%' },
            { label: 'Daily syncs', value: '8,400' },
          ],
        },
        {
          name: 'Security, OWASP & Unused Ports',
          status: 'watch',
          score: 77,
          summary: 'OWASP baseline coverage, exposed services, CSP posture, and hardening checks tied to SEO surfaces.',
          metrics: [
            { label: 'OWASP pass rate', value: '89%' },
            { label: 'Unused ports', value: '3' },
            { label: 'Critical findings', value: '2' },
          ],
          issues: ['Preview node exposes 9229 and 6006 externally', 'One admin route lacks rate limiting'],
        },
        {
          name: 'UI/UX Issues',
          status: 'building',
          score: 78,
          summary:
            'Navigation friction, layout shifts, mobile usability, and conversion blockers after search landing.',
          metrics: [
            { label: 'Friction hotspots', value: '19' },
            { label: 'Mobile pass rate', value: '82%' },
            { label: 'Form completion', value: '68%' },
          ],
          issues: ['Mobile table overflow in comparison pages', 'Filter drawer adds two extra taps'],
        },
        {
          name: 'Loading Time Issue',
          status: 'watch',
          score: 74,
          summary: 'Performance & audits lane for loading regressions, script debt, and remediation tracking.',
          metrics: [
            { label: 'Slow routes', value: '14' },
            { label: 'Avg LCP debt', value: '640 ms' },
            { label: 'JS long tasks', value: '23' },
          ],
          issues: [
            'Hero media on landing pages still blocks first paint',
            'Third-party chat adds 180 ms main-thread time',
          ],
        },
        {
          name: 'Revenue Attribution Intelligence',
          status: 'ready',
          score: 86,
          summary:
            'Search and AI channel attribution through to pipeline and revenue outcomes with path-level explainability.',
          metrics: [
            { label: 'Attributed revenue', value: '$2.8M' },
            { label: 'Model confidence', value: '89%' },
            { label: 'Cross-channel paths', value: '12,400' },
          ],
        },
        {
          name: 'Growth Playbooks Automation',
          status: 'building',
          score: 81,
          summary: 'Automated execution of growth playbooks with guardrails, checkpoints, and impact measurement.',
          metrics: [
            { label: 'Playbooks live', value: '18' },
            { label: 'Tasks automated', value: '1,240/day' },
            { label: 'Goal attainment', value: '72%' },
          ],
        },
        {
          name: 'Trust & Risk Governance',
          status: 'partial',
          score: 79,
          summary: 'Policy, governance, and risk controls for SEO and AI execution with auditability and approvals.',
          metrics: [
            { label: 'Policies active', value: '46' },
            { label: 'Approval SLA', value: '93%' },
            { label: 'Risk incidents', value: '3' },
          ],
        },
        {
          name: 'Multi-Channel Activation Loop',
          status: 'building',
          score: 78,
          summary: 'Activation and distribution loop across search, social, lifecycle, and owned channels.',
          metrics: [
            { label: 'Activation flows', value: '29' },
            { label: 'Cross-channel lift', value: '+14%' },
            { label: 'Loop cycle time', value: '2.6 days' },
          ],
        },
        {
          name: 'Real-Time Search & AI Monitoring',
          status: 'ready',
          score: 84,
          summary: 'Realtime monitoring of engine volatility, visibility shifts, and citation anomalies with alerting.',
          metrics: [
            { label: 'Signals/min', value: '9,400' },
            { label: 'Alert MTTA', value: '3.1 min' },
            { label: 'Noise rate', value: '8%' },
          ],
        },
        {
          name: 'Competitor Intelligence Engine',
          status: 'partial',
          score: 80,
          summary: 'Competitive search and AI visibility intelligence with content-gap and velocity analysis.',
          metrics: [
            { label: 'Competitors tracked', value: '34' },
            { label: 'Gaps detected', value: '418' },
            { label: 'Share-of-voice', value: '22%' },
          ],
        },
        {
          name: 'Log File Analysis Engine',
          status: 'building',
          score: 77,
          summary: 'Crawl-log ingestion, anomaly detection, and bot-behavior analytics for crawl control.',
          metrics: [
            { label: 'Logs/day', value: '28M lines' },
            { label: 'Anomalies', value: '47' },
            { label: 'Bot mismatch', value: '3.2%' },
          ],
        },
        {
          name: 'Security & SEO Health Monitor',
          status: 'watch',
          score: 75,
          summary: 'Security posture, spam, cloaking, and SEO integrity monitoring with incident workflows.',
          metrics: [
            { label: 'Integrity checks', value: '182' },
            { label: 'Spam detections', value: '9' },
            { label: 'Critical health alerts', value: '2' },
          ],
        },
      ],
    },
    // Advanced tabs fallback data
    accessibility_audit: {
      wcag_score: 74,
      wcag_level: 'AA',
      violations_a: 3,
      violations_aa: 11,
      violations_aaa: 29,
      color_contrast_failures: 8,
      aria_issues: 5,
      keyboard_nav_issues: 4,
      focus_order_issues: 2,
      screen_reader_score: 78,
      legal_risk: 'medium',
      issues: [
        {
          wcag: '1.4.3',
          impact: 'serious',
          element: 'button.cta-primary',
          description: 'Contrast ratio 3.1:1 fails AA (4.5 required)',
          remediation: 'Change text color to #1a1a2e',
        },
        {
          wcag: '2.1.1',
          impact: 'critical',
          element: 'div.carousel',
          description: 'Keyboard navigation not available',
          remediation: 'Add tabindex and keydown handlers',
        },
        {
          wcag: '4.1.2',
          impact: 'serious',
          element: 'input[type=search]',
          description: 'Missing accessible label',
          remediation: 'Add aria-label or associate <label>',
        },
        {
          wcag: '2.4.3',
          impact: 'moderate',
          element: 'modal overlay',
          description: 'Focus not trapped in modal',
          remediation: 'Implement focus trap on open',
        },
      ],
      contrast_failures: [
        { element: '.cta-primary', fg: '#7c8db0', bg: '#ffffff', ratio: 3.1, required: 4.5 },
        { element: '.muted-text', fg: '#adb5bd', bg: '#f8f9fa', ratio: 2.7, required: 4.5 },
      ],
      passing_criteria: ['1.1.1 Non-text content', '1.3.1 Info and relationships', '2.4.1 Bypass blocks'],
      failing_criteria: ['1.4.3 Contrast (Minimum)', '2.1.1 Keyboard', '4.1.2 Name Role Value'],
    },
    competitor_intel: {
      keyword_gap: 342,
      content_gap: 87,
      backlink_gap: 1240,
      serp_overlap_pct: 38,
      competitors: [
        {
          domain: 'competitor-a.com',
          authority: 72,
          keywords: 8400,
          backlinks: 34000,
          content_score: 81,
          traffic_est: 280000,
        },
        {
          domain: 'competitor-b.com',
          authority: 68,
          keywords: 6200,
          backlinks: 22000,
          content_score: 77,
          traffic_est: 195000,
        },
        {
          domain: 'competitor-c.com',
          authority: 65,
          keywords: 5100,
          backlinks: 17500,
          content_score: 74,
          traffic_est: 148000,
        },
      ],
      content_audit: {
        thin_pages: 23,
        duplicate_pages: 11,
        decaying_pages: 34,
        avg_freshness_score: 64,
        top_decay: [
          { url: '/blog/guide-2021', decay_pct: 67, last_updated: '2021-11-12', freshness_score: 31 },
          { url: '/blog/seo-tips-old', decay_pct: 54, last_updated: '2022-03-08', freshness_score: 44 },
          { url: '/features/legacy-page', decay_pct: 48, last_updated: '2022-08-01', freshness_score: 52 },
        ],
      },
      opportunities: [
        'Target 342 high-volume keywords competitor-a ranks for',
        'Refresh 34 decaying pages before Q2',
        'Build 1,240 quality backlinks to close authority gap',
      ],
    },
    schema_entities: {
      structured_data_score: 68,
      json_ld_coverage_pct: 42,
      total_schemas: 31,
      validated: 18,
      errors: 7,
      warnings: 6,
      rich_result_types: [
        { type: 'Article', present: true, validated: true, rich_result_eligible: true, errors: [] },
        {
          type: 'FAQ',
          present: true,
          validated: false,
          rich_result_eligible: false,
          errors: ['Missing acceptedAnswer property'],
        },
        {
          type: 'Product',
          present: false,
          validated: false,
          rich_result_eligible: false,
          errors: ['Schema not found on product pages'],
        },
        { type: 'BreadcrumbList', present: true, validated: true, rich_result_eligible: true, errors: [] },
        {
          type: 'LocalBusiness',
          present: false,
          validated: false,
          rich_result_eligible: false,
          errors: ['Missing for local pages'],
        },
      ],
      entities: [
        { entity: 'Main Brand', type: 'Organization', knowledge_panel: true, wikidata: true, confidence: 0.94 },
        { entity: 'CEO Name', type: 'Person', knowledge_panel: false, wikidata: false, confidence: 0.61 },
        {
          entity: 'Primary Product',
          type: 'SoftwareApplication',
          knowledge_panel: false,
          wikidata: false,
          confidence: 0.78,
        },
      ],
      internal_link_equity_score: 62,
      orphan_pages: [
        { url: '/blog/2020-archived', inbound_links: 0, pagerank_flow: 0 },
        { url: '/landing/old-campaign', inbound_links: 1, pagerank_flow: 0.001 },
      ],
      anchor_diversity_score: 71,
      anchor_text_dist: [
        { text: 'click here', count: 48, pct: 22 },
        { text: '[brand name]', count: 37, pct: 17 },
        { text: 'learn more', count: 29, pct: 13 },
        { text: 'exact match keyword', count: 24, pct: 11 },
        { text: 'other', count: 79, pct: 37 },
      ],
    },
    technical_deep: {
      crawl_efficiency_pct: 71,
      crawl_budget_used_pct: 84,
      wasted_crawl_slots: 340,
      googlebot_visits_last7d: 2840,
      avg_crawl_interval_hrs: 42,
      crawl_budget: [
        { url_type: 'Product pages', crawled: 480, budget_pct: 28, wasted: false },
        { url_type: 'Blog posts', crawled: 310, budget_pct: 18, wasted: false },
        { url_type: 'Paginated pages', crawled: 290, budget_pct: 17, wasted: true },
        { url_type: 'Filter combos', crawled: 340, budget_pct: 20, wasted: true },
        { url_type: 'Other', crawled: 290, budget_pct: 17, wasted: false },
      ],
      log_anomalies: [
        {
          ts: '2024-06-12 04:31',
          type: 'Crawl Spike',
          url: '/sitemap-images.xml',
          detail: '480 req in 2 min window',
          severity: 'warning',
        },
        {
          ts: '2024-06-11 18:14',
          type: '404 Surge',
          url: '/en/products/*',
          detail: '120 not-found in 30 min',
          severity: 'high',
        },
        {
          ts: '2024-06-10 11:02',
          type: 'Redirect Loop',
          url: '/blog/category/news',
          detail: 'Chain of 4 redirects detected',
          severity: 'high',
        },
      ],
      topical_clusters: [
        { topic: 'SEO Tools', pages: 18, coverage_pct: 82, gap: false },
        { topic: 'Performance', pages: 12, coverage_pct: 65, gap: false },
        { topic: 'AI & Automation', pages: 6, coverage_pct: 38, gap: true },
        { topic: 'Local SEO', pages: 3, coverage_pct: 21, gap: true },
        { topic: 'E-commerce SEO', pages: 7, coverage_pct: 44, gap: true },
      ],
      redirect_chains: [
        { start_url: '/old-products', hops: 3, final_url: '/products', latency_ms: 180 },
        { start_url: '/blog-archive', hops: 2, final_url: '/blog', latency_ms: 95 },
      ],
      orphaned_canonicals: 14,
      pagination_issues: 8,
    },
    trust_revenue: {
      domain_trust_score: 74,
      e_e_a_t_score: 68,
      safe_browsing_clean: true,
      malware_flagged: false,
      https_enforced: true,
      hsts_preloaded: false,
      author_authority_avg: 61,
      backlink_trust_flow: 58,
      review_aggregate_score: 4.2,
      review_velocity: 12,
      reviews: [
        { platform: 'Google', score: 4.3, count: 847, trend: 'up' },
        { platform: 'Trustpilot', score: 4.1, count: 412, trend: 'stable' },
        { platform: 'G2', score: 4.4, count: 318, trend: 'up' },
      ],
      seo_revenue_total_usd: 184000,
      seo_attributed_pct: 38,
      top_revenue_keywords: [
        { keyword: 'seo platform', position: 4, sessions: 4200, revenue_usd: 42000, conversions: 68 },
        { keyword: 'best seo tool', position: 7, sessions: 2800, revenue_usd: 28000, conversions: 45 },
        { keyword: 'seo audit software', position: 3, sessions: 1900, revenue_usd: 19000, conversions: 31 },
      ],
      attribution: [
        { channel: 'Organic Search', assisted_pct: 68, last_click_pct: 54, revenue_usd: 99000 },
        { channel: 'Direct', assisted_pct: 22, last_click_pct: 31, revenue_usd: 57000 },
        { channel: 'Paid', assisted_pct: 10, last_click_pct: 15, revenue_usd: 28000 },
      ],
    },
    ux_conversion: {
      ux_score: 72,
      friction_score: 34,
      cta_coverage_pct: 61,
      form_completion_avg_pct: 68,
      heatmap_recommendations: [
        'Move primary CTA above the fold on /pricing',
        'Reduce hero copy to 12 words max',
        'Add sticky CTA bar for long-form content',
      ],
      cta_audit: [
        { page: '/pricing', cta_text: 'Start Free Trial', visibility_score: 88, contrast_ok: true, placement: 'hero' },
        {
          page: '/features',
          cta_text: 'Get Started',
          visibility_score: 61,
          contrast_ok: false,
          placement: 'bottom-third',
        },
        { page: '/blog/*', cta_text: 'Try It Free', visibility_score: 44, contrast_ok: true, placement: 'sidebar' },
      ],
      form_friction: [
        { form_id: 'signup', fields: 7, avg_completion_pct: 71, drop_field: 'Phone number', friction_score: 38 },
        { form_id: 'contact', fields: 5, avg_completion_pct: 58, drop_field: 'Company size', friction_score: 52 },
      ],
      brand_voice_score: 77,
      tone_consistency_pct: 82,
      entity_sentiment: 'positive',
      social_coverage_pct: 74,
      og_coverage_pct: 68,
      twitter_card_coverage_pct: 61,
      social_cards: [
        { url: '/blog/seo-guide', og_complete: true, twitter_complete: false, missing: ['twitter:image'] },
        {
          url: '/pricing',
          og_complete: false,
          twitter_complete: false,
          missing: ['og:description', 'og:image', 'twitter:card'],
        },
      ],
      media_alt_coverage_pct: 58,
      media_items: [
        { url: '/img/hero.jpg', alt_present: true, alt_descriptive: true, size_kb: 142 },
        { url: '/img/team-photo.jpg', alt_present: false, alt_descriptive: false, size_kb: 88 },
        { url: '/img/chart.png', alt_present: true, alt_descriptive: false, size_kb: 64 },
      ],
    },
    growth_landing: {
      playbook_score: 81,
      top_priority: 'Refresh decaying content cluster to recover 34% traffic loss',
      playbooks: [
        {
          vertical: 'SaaS',
          goal: 'Recover organic traffic',
          actions: [
            {
              priority: 'P0',
              action: 'Refresh 34 decaying blog posts',
              impact: '+18% organic traffic',
              effort: 'medium',
              timeline: '3 weeks',
            },
            {
              priority: 'P1',
              action: 'Build topical authority in AI & Automation cluster',
              impact: '+340 keyword rankings',
              effort: 'high',
              timeline: '2 months',
            },
            {
              priority: 'P2',
              action: 'Add FAQ schema to top 20 blog posts',
              impact: '+12% CTR',
              effort: 'low',
              timeline: '1 week',
            },
          ],
        },
        {
          vertical: 'Content',
          goal: 'Improve conversion from organic',
          actions: [
            {
              priority: 'P0',
              action: 'Add inline CTAs to high-traffic blog pages',
              impact: '+8% conversion rate',
              effort: 'low',
              timeline: '3 days',
            },
            {
              priority: 'P1',
              action: 'A/B test pricing page hero headline',
              impact: '+5% trial signups',
              effort: 'low',
              timeline: '2 weeks',
            },
          ],
        },
      ],
      landing_pages: [
        {
          url: '/pricing',
          headline_score: 82,
          cta_score: 79,
          trust_score: 85,
          overall: 82,
          suggestions: ['Add customer logo bar', 'Show monthly/annual toggle higher'],
        },
        {
          url: '/features',
          headline_score: 68,
          cta_score: 55,
          trust_score: 74,
          overall: 66,
          suggestions: ['Move CTA above the fold', 'Add social proof counter'],
        },
        {
          url: '/blog/seo-guide',
          headline_score: 91,
          cta_score: 44,
          trust_score: 70,
          overall: 68,
          suggestions: ['Upgrade inline CTA offer', 'Add exit-intent popup'],
        },
      ],
      multi_channel_score: 68,
      channels: [
        { channel: 'Blog / Organic', coverage_pct: 88, active: true, last_published: '2024-06-12' },
        { channel: 'Email Newsletter', coverage_pct: 72, active: true, last_published: '2024-06-10' },
        { channel: 'LinkedIn', coverage_pct: 61, active: true, last_published: '2024-06-11' },
        { channel: 'YouTube', coverage_pct: 28, active: false, last_published: '2024-03-22' },
        { channel: 'Podcast', coverage_pct: 14, active: false, last_published: '2023-11-05' },
      ],
      quick_wins: [
        'Add FAQ schema to 20 blog posts (1 week)',
        'Inline CTAs on high-traffic posts (3 days)',
        'Fix 3 broken redirect chains (1 day)',
      ],
    },
    live_intelligence: {
      rank_tracking_score: 77,
      avg_position: 14.2,
      total_keywords: 2840,
      keywords_top3: 187,
      positions_gained_7d: 94,
      positions_lost_7d: 47,
      top_keywords: [
        { keyword: 'seo audit tool', position: 3, delta: +2, url: '/features/audit', serp_feature: 'Featured Snippet' },
        { keyword: 'best seo platform', position: 7, delta: -1, url: '/pricing', serp_feature: 'Ad top' },
        { keyword: 'site speed checker', position: 4, delta: +5, url: '/tools/speed', serp_feature: 'People Also Ask' },
        { keyword: 'seo automation', position: 11, delta: +3, url: '/features/automation', serp_feature: 'none' },
        {
          keyword: 'competitor seo analysis',
          position: 18,
          delta: -4,
          url: '/features/competitor',
          serp_feature: 'none',
        },
      ],
      rag_readiness_score: 62,
      ai_answer_coverage_pct: 38,
      rag_items: [
        { url: '/blog/seo-guide', score: 84, faq_coverage: true, structured_answer: true, ai_cited: true },
        { url: '/features/audit', score: 71, faq_coverage: true, structured_answer: false, ai_cited: false },
        { url: '/pricing', score: 42, faq_coverage: false, structured_answer: false, ai_cited: false },
      ],
      ai_coverage: [
        { query: 'What is the best SEO audit tool?', answered: true, source: '/blog/seo-guide', confidence: 0.82 },
        { query: 'How to improve site speed for SEO?', answered: true, source: '/blog/speed-seo', confidence: 0.74 },
        { query: 'SEO pricing 2024', answered: false, source: '', confidence: 0 },
      ],
      live_alerts: [
        {
          metric: 'Position drop',
          change: 'keywords 200-300 lost avg 3.2 positions',
          severity: 'high',
          ts: '2024-06-12 09:41',
        },
        {
          metric: 'Featured Snippet won',
          change: '"seo audit tool" now owns FS',
          severity: 'info',
          ts: '2024-06-12 08:15',
        },
        {
          metric: 'Crawl anomaly',
          change: '480 Googlebot req spike at 04:31',
          severity: 'warning',
          ts: '2024-06-12 04:35',
        },
      ],
    },
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function filmstripProgress(label: string): number {
  if (label.includes('time_to_int')) return 1;
  if (label.includes('largest')) return 0.75;
  if (label.includes('contentful')) return 0.45;
  return 0.15;
}

function filmstripTextWidth(progress: number): number {
  if (progress >= 0.75) return 180;
  if (progress >= 0.45) return 150;
  return 120;
}

function FilmstripScreenshotSVG({ label }: Readonly<{ label: string }>) {
  const progress = filmstripProgress(label);
  const W = 200;
  const H = 120;
  const bg = '#0d1117';
  const chrome = '#1a1f2e';
  const sk = '#1e2a3a';
  const skHi = '#2d3a4a';
  const barColor = progress >= 0.75 ? '#22c55e' : '#6366f1';
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ borderRadius: 6, display: 'block' }}>
      <rect width={W} height={H} fill={bg} rx={4} />
      {/* browser chrome */}
      <rect width={W} height={14} fill={chrome} />
      <circle cx={8} cy={7} r={2.5} fill="#ef4444" opacity={0.7} />
      <circle cx={16} cy={7} r={2.5} fill="#f59e0b" opacity={0.7} />
      <circle cx={24} cy={7} r={2.5} fill="#22c55e" opacity={0.7} />
      <rect x={34} y={3} width={120} height={8} rx={3} fill="#111827" />
      {/* nav bar skeleton */}
      {progress >= 0.15 && (
        <>
          <rect y={14} width={W} height={18} fill={chrome} opacity={0.6} />
          <rect x={8} y={19} width={36} height={7} rx={2} fill={skHi} />
          <rect x={52} y={19} width={22} height={7} rx={2} fill={sk} />
          <rect x={82} y={19} width={22} height={7} rx={2} fill={sk} />
          <rect x={112} y={19} width={22} height={7} rx={2} fill={sk} />
          <rect
            x={156}
            y={18}
            width={36}
            height={9}
            rx={2}
            fill={progress >= 0.45 ? '#1e3a5f' : sk}
            stroke={progress >= 0.45 ? '#6366f1' : 'none'}
            strokeWidth={1}
          />
        </>
      )}
      {/* hero image area */}
      {progress >= 0.45 && (
        <rect
          x={8}
          y={36}
          width={W - 16}
          height={40}
          rx={3}
          fill={progress >= 0.75 ? '#0f2744' : '#1e3a5f'}
          stroke={progress >= 0.75 ? 'none' : '#6366f188'}
          strokeWidth={1}
        />
      )}
      {progress >= 0.75 && (
        <>
          <rect x={16} y={42} width={60} height={6} rx={2} fill="#1e3a5f" />
          <rect x={16} y={52} width={40} height={5} rx={2} fill="#1e3a5f" opacity={0.7} />
          <rect x={130} y={38} width={52} height={36} rx={3} fill="#162032" />
          <text x={156} y={58} textAnchor="middle" fontSize={7} fill="#6366f1" opacity={0.8}>
            IMG
          </text>
        </>
      )}
      {/* text skeleton */}
      {progress >= 0.15 && (
        <>
          <rect x={8} y={82} width={filmstripTextWidth(progress)} height={5} rx={2} fill={skHi} />
          <rect x={8} y={91} width={progress >= 0.45 ? 110 : 80} height={4} rx={2} fill={sk} />
          <rect x={8} y={100} width={progress >= 0.75 ? 140 : 60} height={4} rx={2} fill={sk} opacity={0.5} />
        </>
      )}
      {/* interactive indicator */}
      {progress >= 1 && <rect x={8} y={110} width={50} height={6} rx={3} fill="#22c55e" opacity={0.7} />}
      {/* load progress bar */}
      <rect y={H - 3} width={W} height={3} fill={bg} />
      <rect y={H - 3} width={W * progress} height={3} fill={barColor} rx={1} />
    </svg>
  );
}

function ScoreGauge({ score, label, size = 110 }: Readonly<{ score: number; label: string; size?: number }>) {
  const r = size / 2 - 10;
  const circumference = 2 * Math.PI * r;
  const dash = (score / 100) * circumference;
  const color = scoreColor(score);
  const grade = scoreGrade(score);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={8} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x={size / 2}
          y={size / 2 - 6}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.22}
          fontWeight={800}
          fill={color}
        >
          {grade}
        </text>
        <text
          x={size / 2}
          y={size / 2 + 14}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.13}
          fill="var(--muted)"
        >
          {score}
        </text>
      </svg>
      <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>{label}</div>
    </div>
  );
}

function WaterfallBars({ timeline }: Readonly<{ timeline: WaterfallTimeline }>) {
  const phases: { key: keyof WaterfallTimeline; label: string; color: string }[] = [
    { key: 'dns', label: 'DNS', color: '#8b5cf6' },
    { key: 'tcp', label: 'TCP', color: '#6366f1' },
    { key: 'tls', label: 'TLS', color: '#06b6d4' },
    { key: 'ttfb', label: 'TTFB', color: '#f59e0b' },
    { key: 'download', label: 'Download', color: '#22c55e' },
  ];
  const total = Object.values(timeline).reduce((s: number, v) => s + (Number(v) || 0), 0) || 1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div
        style={{ display: 'flex', height: 28, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--line)' }}
      >
        {phases.map(({ key, color }) => {
          const val = timeline[key] ?? 0;
          const pct = (val / total) * 100;
          return pct > 0 ? (
            <div key={key} style={{ width: `${pct}%`, background: color }} title={`${key}: ${val}ms`} />
          ) : null;
        })}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px' }}>
        {phases.map(({ key, label, color }) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
            <span style={{ color: 'var(--muted)' }}>{label}</span>
            <span style={{ fontWeight: 700 }}>{timeline[key] ?? 0}ms</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
          <span style={{ color: 'var(--muted)' }}>Total</span>
          <span style={{ fontWeight: 700 }}>{total}ms</span>
        </div>
      </div>
    </div>
  );
}

function Sparkline({ runs }: Readonly<{ runs: HistoryRun[] }>) {
  if (runs.length < 2) return <div style={{ color: 'var(--muted)', fontSize: 12 }}>Not enough data for chart</div>;
  const scores = runs.map((r) => r.performance_score ?? 0);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1;
  const W = 400;
  const H = 80;
  const pts = scores
    .map((sc, i) => {
      const x = (i / (scores.length - 1)) * W;
      const y = H - ((sc - min) / range) * (H - 10) - 5;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke="var(--brand)" strokeWidth={2} />
      {scores.map((sc, i) => {
        const x = (i / (scores.length - 1)) * W;
        const y = H - ((sc - min) / range) * (H - 10) - 5;
        const ts = runs[i]?.ts ?? String(i);
        return <circle key={ts} cx={x} cy={y} r={3} fill={scoreColor(sc)} />;
      })}
    </svg>
  );
}

function severityColor(s?: string): string {
  if (s === 'high') return '#ef4444';
  if (s === 'medium') return '#f59e0b';
  return '#6b7280';
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function cspScoreColor(score: number): string {
  if (score >= 70) return '#22c55e';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

function headerColor(present: boolean | undefined, severity: string | undefined): string {
  if (present) return '#22c55e';
  if (severity === 'high') return '#ef4444';
  return '#f59e0b';
}

function pipelineStatusColor(status?: string): string {
  if (status === 'pass') return '#22c55e';
  if (status === 'partial_pass') return '#f59e0b';
  return '#ef4444';
}

function funnelBarColor(pct: number, isFirst: boolean): string {
  if (isFirst) return '#6366f1';
  if (pct > 0.5) return '#22c55e';
  if (pct > 0.2) return '#f59e0b';
  return '#ef4444';
}

function perfDeltaColor(delta?: number): string {
  if ((delta ?? 0) < 0) return '#22c55e';
  if ((delta ?? 0) > 100) return '#ef4444';
  return '#f59e0b';
}

function depSeverityColor(severity?: string): string {
  if (severity === 'critical') return '#ef4444';
  if (severity === 'high') return '#f97316';
  if (severity === 'medium') return '#f59e0b';
  return '#22c55e';
}

function stepColor(passed?: boolean, status?: string): string {
  if (passed) return '#22c55e';
  if (status === 'warning') return '#f59e0b';
  return '#ef4444';
}

function integrationHealthColor(health: string): string {
  if (health === 'healthy') return '#22c55e';
  if (health === 'degraded') return '#f59e0b';
  return '#ef4444';
}

// ─── Chart Components ─────────────────────────────────────────────────────────

const DONUT_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#8b5cf6', '#06b6d4'];
const NETWORK_COLORS = ['#06b6d4', '#6366f1', '#8b5cf6', '#f59e0b'];

function DonutChart({
  slices,
  size = 130,
}: Readonly<{ slices: Array<{ label: string; value: number; color: string }>; size?: number }>) {
  const total = slices.reduce((s, sl) => s + sl.value, 0) || 1;
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 8;
  const inner = r * 0.55;
  let cumAngle = -Math.PI / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((sl) => {
        const sweep = (sl.value / total) * Math.PI * 2;
        const a0 = cumAngle;
        // eslint-disable-next-line react-hooks/immutability
        cumAngle += sweep;
        const x1 = cx + r * Math.cos(a0);
        const y1 = cy + r * Math.sin(a0);
        const x2 = cx + r * Math.cos(cumAngle);
        const y2 = cy + r * Math.sin(cumAngle);
        const xi1 = cx + inner * Math.cos(a0);
        const yi1 = cy + inner * Math.sin(a0);
        const xi2 = cx + inner * Math.cos(cumAngle);
        const yi2 = cy + inner * Math.sin(cumAngle);
        const large = sweep > Math.PI ? 1 : 0;
        const d = `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${x2.toFixed(1)} ${y2.toFixed(1)} L ${xi2.toFixed(1)} ${yi2.toFixed(1)} A ${inner} ${inner} 0 ${large} 0 ${xi1.toFixed(1)} ${yi1.toFixed(1)} Z`;
        return <path key={sl.label} d={d} fill={sl.color} opacity={0.88} />;
      })}
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize={8} fill="var(--muted)">
        {slices.length} seg
      </text>
    </svg>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AreaChart({
  points,
  width = 380,
  height = 72,
  color = '#6366f1',
  labels,
}: Readonly<{ points: number[]; width?: number; height?: number; color?: string; labels?: string[] }>) {
  if (points.length < 2) return null;
  const mn = Math.min(...points);
  const mx = Math.max(...points);
  const rng = mx - mn || 1;
  const px = 8;
  const py = 10;
  const xs = (i: number) => ((i / (points.length - 1)) * (width - px * 2) + px).toFixed(1);
  const ys = (v: number) => (height - py - ((v - mn) / rng) * (height - py * 2)).toFixed(1);
  const linePts = points.map((v, i) => `${xs(i)},${ys(v)}`).join(' ');
  const gradId = `ag${color.replaceAll(/[^0-9a-z]/gi, '')}`;
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0.02} />
        </linearGradient>
      </defs>
      <path d={`M ${px},${height - py} L ${linePts} L ${width - px},${height - py} Z`} fill={`url(#${gradId})`} />
      <polyline points={linePts} fill="none" stroke={color} strokeWidth={1.5} />
      {points.map((v, i) => (
        <circle key={`pt-${xs(i)}-${ys(v)}`} cx={xs(i)} cy={ys(v)} r={3} fill={color} />
      ))}
    </svg>
  );
}

function MiniBarChart({
  items,
}: Readonly<{ items: Array<{ label: string; value: number; color?: string; max?: number; suffix?: string }> }>) {
  const globalMax = Math.max(...items.map((it) => it.max ?? it.value), 1);
  return (
    <div style={{ display: 'grid', gap: 6 }}>
      {items.map((it) => {
        const col = it.color ?? '#6366f1';
        return (
          <div key={it.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
            <div style={{ width: 96, textAlign: 'right', color: 'var(--muted)', flexShrink: 0, fontSize: 10 }}>
              {it.label}
            </div>
            <div style={{ flex: 1, height: 14, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${(it.value / (it.max ?? globalMax)) * 100}%`,
                  height: '100%',
                  background: col,
                  borderRadius: 3,
                }}
              />
            </div>
            <div style={{ width: 60, fontWeight: 700, textAlign: 'right', color: col, fontSize: 11 }}>
              {it.value.toLocaleString()}
              {it.suffix ?? ''}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LatencyPercentileBar({
  p50 = 0,
  p75 = 0,
  p95 = 0,
  p99 = 0,
  unit = 'ms',
  threshold = 0,
}: Readonly<{ p50?: number; p75?: number; p95?: number; p99?: number; unit?: string; threshold?: number }>) {
  const mx = Math.max(p99, threshold * 1.1, 1);
  const bars = [
    { label: 'p50', value: p50, color: '#22c55e' },
    { label: 'p75', value: p75, color: '#f59e0b' },
    { label: 'p95', value: p95, color: '#f97316' },
    { label: 'p99', value: p99, color: '#ef4444' },
  ];
  return (
    <div style={{ display: 'grid', gap: 5 }}>
      {bars.map((b) => (
        <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
          <div style={{ width: 22, fontWeight: 800, color: b.color }}>{b.label}</div>
          <div
            style={{
              flex: 1,
              height: 10,
              background: 'var(--line)',
              borderRadius: 3,
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div style={{ width: `${(b.value / mx) * 100}%`, height: '100%', background: b.color, borderRadius: 3 }} />
            {threshold > 0 && (
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  left: `${(threshold / mx) * 100}%`,
                  width: 1,
                  background: 'rgba(255,255,255,0.35)',
                }}
              />
            )}
          </div>
          <div style={{ width: 52, fontWeight: 700, textAlign: 'right' }}>
            {b.value}
            {unit}
          </div>
        </div>
      ))}
    </div>
  );
}

function suiteReadinessColor(status?: string): string {
  if (status === 'ready' || status === 'strong') return '#22c55e';
  if (status === 'building' || status === 'partial' || status === 'watch') return '#f59e0b';
  return '#ef4444';
}

function CapabilitySuiteSection({
  title,
  subtitle,
  suite,
}: Readonly<{ title: string; subtitle: string; suite?: SeoCapabilitySuite }>) {
  const panel: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 14,
  };

  const tierColor = (tier?: string): string => {
    if (tier === 'Core') return '#0ea5e9';
    if (tier === 'New') return '#a855f7';
    if (tier === 'AI') return '#22c55e';
    if (tier === 'Experiment') return '#f59e0b';
    return '#64748b';
  };

  if (!suite) {
    return (
      <section style={panel}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{subtitle}</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 12 }}>No suite data available.</div>
      </section>
    );
  }

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={panel}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{subtitle}</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 110px), 1fr))', gap: 8 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>Score</div>
              <div style={{ fontWeight: 800, fontSize: 22 }}>{suite.overview_score ?? 0}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>Coverage</div>
              <div style={{ fontWeight: 800, fontSize: 22 }}>{suite.coverage ?? 0}%</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>Opportunities</div>
              <div style={{ fontWeight: 800, fontSize: 22 }}>{suite.opportunity_count ?? 0}</div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
        {(suite.distribution ?? []).length > 0 && (
          <div style={panel}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Coverage Mix</div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <DonutChart
                slices={(suite.distribution ?? []).map((slice) => ({
                  label: slice.label ?? 'slice',
                  value: slice.value ?? 0,
                  color: slice.color ?? '#6366f1',
                }))}
                size={116}
              />
              <div style={{ display: 'grid', gap: 6, flex: 1 }}>
                {(suite.distribution ?? []).map((slice) => (
                  <div
                    key={`${slice.label ?? 'slice'}-${slice.value ?? 0}`}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: slice.color ?? '#6366f1',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ color: 'var(--muted)', flex: 1 }}>{slice.label}</span>
                    <strong>{slice.value}%</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {(suite.timeline ?? []).length > 1 && (
          <div style={panel}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Readiness Trend</div>
            <AreaChart
              points={(suite.timeline ?? []).map((point) => point.value ?? 0)}
              labels={(suite.timeline ?? []).map((point) => point.label ?? '')}
              color="#6366f1"
              height={82}
            />
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
        {(suite.highlights ?? []).length > 0 && (
          <div style={panel}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Highlights</div>
            <div style={{ display: 'grid', gap: 7 }}>
              {(suite.highlights ?? []).map((item) => (
                <div key={item} style={{ fontSize: 12 }}>
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
        {(suite.risks ?? []).length > 0 && (
          <div style={panel}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Risks</div>
            <div style={{ display: 'grid', gap: 7 }}>
              {(suite.risks ?? []).map((item) => (
                <div key={item} style={{ fontSize: 12, color: '#f59e0b' }}>
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
        {(suite.modules ?? []).map((module) => (
          <div key={module.name ?? 'module'} style={panel}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                marginBottom: 8,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 13 }}>{module.name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {typeof module.score === 'number' && <strong style={{ fontSize: 12 }}>{module.score}</strong>}
                {module.tier && (
                  <span
                    style={{
                      background: tierColor(module.tier),
                      color: '#fff',
                      borderRadius: 999,
                      padding: '2px 8px',
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  >
                    {module.tier}
                  </span>
                )}
                <span
                  style={{
                    background: suiteReadinessColor(module.status),
                    color: '#fff',
                    borderRadius: 999,
                    padding: '2px 8px',
                    fontSize: 10,
                    fontWeight: 700,
                  }}
                >
                  {module.status}
                </span>
              </div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>{module.summary}</div>

            {(module.metrics ?? []).length > 0 && (
              <div style={{ display: 'grid', gap: 6, marginBottom: 10 }}>
                {(module.metrics ?? []).map((metric) => (
                  <div
                    key={`${module.name ?? 'module'}-${metric.label ?? 'metric'}`}
                    style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, gap: 8 }}
                  >
                    <span style={{ color: 'var(--muted)' }}>{metric.label}</span>
                    <strong>{metric.value}</strong>
                  </div>
                ))}
              </div>
            )}

            {(module.automations ?? []).length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                {(module.automations ?? []).map((item) => (
                  <span
                    key={`${module.name ?? 'module'}-${item}`}
                    style={{
                      border: '1px solid var(--line)',
                      borderRadius: 999,
                      padding: '2px 8px',
                      fontSize: 10,
                      color: '#6366f1',
                    }}
                  >
                    {item}
                  </span>
                ))}
              </div>
            )}

            {(module.issues ?? []).length > 0 && (
              <div style={{ display: 'grid', gap: 5 }}>
                {(module.issues ?? []).map((issue) => (
                  <div key={`${module.name ?? 'module'}-${issue}`} style={{ fontSize: 11, color: '#f59e0b' }}>
                    - {issue}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type Tab =
  | 'summary'
  | 'waterfall'
  | 'filmstrip'
  | 'rum'
  | 'causality'
  | 'agents'
  | 'prediction'
  | 'global'
  | 'business'
  | 'ci-gate'
  | 'slo'
  | 'roi'
  | 'copilot'
  | 'opportunities'
  | 'ai-fixes'
  | 'images'
  | 'security'
  | 'javascript'
  | 'css'
  | 'input-validation'
  | 'latency'
  | 'outdated'
  | 'workflow'
  | 'data-analysis'
  | 'core-seo'
  | 'content-blogging'
  | 'ai-optimization'
  | 'search-experience'
  | 'vertical-seo'
  | 'platform-ops'
  | 'accessibility'
  | 'competitor-intel'
  | 'schema-entities'
  | 'technical-deep'
  | 'trust-revenue'
  | 'ux-conversion'
  | 'growth-landing'
  | 'live-intelligence'
  | 'gtmetrix-api'
  | 'history'
  | 'monitoring'
  | 'keywords'
  | 'seo-ranking'
  | 'ai-models-ranking'
  | 'hashtags'
  | 'visibility'
  | 'leads'
  | 'clicks'
  | 'trends-vs-platform'
  | 'power-ranking'
  | 'autonomous';

// ─── Shared Tab Props ────────────────────────────────────────────────────────

interface PerfTabProps {
  readonly result: PerformanceAuditResponse;
  readonly card: React.CSSProperties;
  readonly isOfflinePreview: boolean;
  readonly autoFixing: boolean; // NOSONAR
  readonly autoFixResult: AutoFixResult | null; // NOSONAR
  readonly autoFixError: string; // NOSONAR
  readonly fixingItem: string | null; // NOSONAR
  readonly fixedItems: Set<string>; // NOSONAR
  readonly fixSingleItem: (candidate: AutoFixCandidate) => Promise<void>; // NOSONAR
  readonly optimizeSite: () => Promise<void>; // NOSONAR
  readonly historyLoading?: boolean; // NOSONAR
  readonly historyData?: HistoryResponse | null; // NOSONAR
  readonly loadHistory?: () => Promise<void>; // NOSONAR
  readonly rumCollector?: RumCollectorState | null; // NOSONAR
  readonly currentPageRumRollup?: PerformanceRumRollup | null; // NOSONAR
  readonly rumTargetSummary?: PerformanceRumSummaryResponse | null; // NOSONAR
  readonly rumTargetLoading?: boolean; // NOSONAR
  readonly refreshRumTargetSummary?: () => Promise<void>; // NOSONAR
}

function SummaryTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {(result.recommended_stack ?? []).length > 0 && (
        <section style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Recommended Stack</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(result.recommended_stack ?? []).map((item) => (
              <span
                key={item}
                style={{
                  fontSize: 12,
                  borderRadius: 999,
                  padding: '5px 12px',
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                }}
              >
                {item}
              </span>
            ))}
          </div>
        </section>
      )}
      {(result.waterfall?.render_blocking ?? []).length > 0 && (
        <section style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
            Render-Blocking Resources{isOfflinePreview ? ' (sample)' : ''}
          </div>
          <div style={{ display: 'grid', gap: 6 }}>
            {(result.waterfall?.render_blocking ?? []).map((asset) => (
              <div
                key={asset}
                style={{
                  padding: '6px 10px',
                  background: isOfflinePreview ? '#78350f33' : '#7f1d1d22',
                  borderRadius: 6,
                  fontSize: 12,
                  color: isOfflinePreview ? '#92400e' : '#dc2626',
                }}
              >
                {asset}
                {isOfflinePreview ? ' (preview)' : ''}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function WaterfallTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Total Requests', value: String(result.waterfall?.requests ?? 84), color: 'var(--text)' },
          { label: 'Total Size', value: `${result.waterfall?.transfer_kb ?? 2340} KB`, color: '#f59e0b' },
          {
            label: 'TTFB',
            value: `${result.waterfall?.timeline_ms?.ttfb ?? 210}ms`,
            color: (result.waterfall?.timeline_ms?.ttfb ?? 210) > 600 ? '#ef4444' : '#22c55e',
          },
          { label: 'Time to Interactive', value: '3,400ms', color: '#f59e0b' },
          { label: 'Blocking Assets', value: String(result.waterfall?.render_blocking?.length ?? 7), color: '#ef4444' },
          { label: 'Cached Requests', value: '38%', color: '#6366f1' },
          { label: 'Compression Ratio', value: '3.2×', color: '#22c55e' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Request type breakdown */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Request Type Breakdown</div>
        <MiniBarChart
          items={[
            {
              label: 'JavaScript',
              value: 28,
              color: '#f59e0b',
              max: result.waterfall?.requests ?? 84,
              suffix: ' reqs',
            },
            { label: 'CSS', value: 12, color: '#6366f1', max: result.waterfall?.requests ?? 84, suffix: ' reqs' },
            { label: 'Images', value: 31, color: '#22c55e', max: result.waterfall?.requests ?? 84, suffix: ' reqs' },
            { label: 'Fonts', value: 6, color: '#6366f1', max: result.waterfall?.requests ?? 84, suffix: ' reqs' },
            { label: 'API / XHR', value: 7, color: '#ec4899', max: result.waterfall?.requests ?? 84, suffix: ' reqs' },
          ]}
        />
      </div>

      {/* Timing phases */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Connection Timing Phases</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {[
            {
              phase: 'DNS Lookup',
              ms: result.waterfall?.timeline_ms?.dns ?? 18,
              color: '#6366f1',
              tip: 'Use DNS prefetch for 3rd-party origins',
            },
            {
              phase: 'TCP Connect',
              ms: result.waterfall?.timeline_ms?.tcp ?? 42,
              color: '#6366f1',
              tip: 'Enable HTTP/2 multiplexing',
            },
            {
              phase: 'SSL Handshake',
              ms: result.waterfall?.timeline_ms?.tls ?? 78,
              color: '#f59e0b',
              tip: 'TLS 1.3 reduces handshake to 1-RTT',
            },
            {
              phase: 'TTFB',
              ms: result.waterfall?.timeline_ms?.ttfb ?? 210,
              color: '#ef4444',
              tip: 'Server response time — consider edge caching',
            },
            {
              phase: 'Content Download',
              ms: result.waterfall?.timeline_ms?.download ?? 320,
              color: '#22c55e',
              tip: 'Reduce payload with compression + splitting',
            },
            { phase: 'DOM Processing', ms: 890, color: '#ec4899', tip: 'Defer non-critical JS to unblock parsing' },
          ].map((p) => {
            const maxMs = 1200;
            const w = Math.min(100, Math.round((p.ms / maxMs) * 100));
            return (
              <div key={p.phase}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                  <span style={{ fontWeight: 600 }}>{p.phase}</span>
                  <span style={{ color: p.color, fontWeight: 700 }}>{p.ms}ms</span>
                </div>
                <div
                  style={{ height: 8, background: 'var(--line)', borderRadius: 4, overflow: 'hidden', marginBottom: 2 }}
                >
                  <div style={{ width: `${w}%`, height: '100%', background: p.color, borderRadius: 4 }} />
                </div>
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>{p.tip}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Waterfall chart */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Timeline Waterfall</div>
        {result.waterfall?.timeline_ms ? (
          <WaterfallBars timeline={result.waterfall.timeline_ms} />
        ) : (
          <div style={{ display: 'grid', gap: 4 }}>
            {[
              { name: '/index.html', start: 0, dur: 228, type: 'document', size: '12 KB' },
              { name: '/main.bundle.js', start: 228, dur: 680, type: 'script', size: '420 KB' },
              { name: '/styles.css', start: 228, dur: 180, type: 'style', size: '84 KB' },
              { name: '/hero.avif', start: 408, dur: 340, type: 'image', size: '198 KB' },
              { name: '/fonts/inter.woff2', start: 450, dur: 220, type: 'font', size: '66 KB' },
              { name: 'cdn.analytics.io/track.js', start: 600, dur: 480, type: 'script', size: '38 KB' },
              { name: '/api/user', start: 908, dur: 190, type: 'xhr', size: '2 KB' },
              { name: '/thumbnail-1.webp', start: 700, dur: 260, type: 'image', size: '42 KB' },
              { name: '/chunk.vendor.js', start: 908, dur: 390, type: 'script', size: '210 KB' },
              { name: 'gtag/js', start: 1000, dur: 520, type: 'script', size: '28 KB' },
            ].map((r, i) => {
              const totalDur = 1520;
              const typeColor: Record<string, string> = {
                document: '#22c55e',
                script: '#ef4444',
                style: '#6366f1',
                image: '#6366f1',
                font: '#f59e0b',
                xhr: '#ec4899',
              };
              const c = typeColor[r.type] ?? '#888';
              return (
                <div
                  key={r.name}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '200px 1fr 50px 60px',
                    gap: 8,
                    alignItems: 'center',
                    fontSize: 11,
                  }}
                >
                  <div
                    style={{
                      fontFamily: 'monospace',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'var(--muted)',
                    }}
                    title={r.name}
                  >
                    {r.name}
                  </div>
                  <div style={{ height: 12, background: 'var(--line)', borderRadius: 2, position: 'relative' }}>
                    <div
                      style={{
                        position: 'absolute',
                        left: `${(r.start / totalDur) * 100}%`,
                        width: `${(r.dur / totalDur) * 100}%`,
                        height: '100%',
                        background: c,
                        borderRadius: 2,
                        opacity: r.type === 'script' ? 1 : 0.8,
                      }}
                    />
                  </div>
                  <div style={{ color: c, fontWeight: 700 }}>{r.dur}ms</div>
                  <div style={{ color: 'var(--muted)' }}>{r.size}</div>
                </div>
              );
            })}
            <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
              {[
                ['script', '#ef4444'],
                ['style', '#6366f1'],
                ['image', '#6366f1'],
                ['font', '#f59e0b'],
                ['xhr', '#ec4899'],
                ['document', '#22c55e'],
              ].map(([t, c]) => (
                <span
                  key={t}
                  style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, color: 'var(--muted)' }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: 'inline-block' }} />
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Render-blocking assets */}
      {(
        result.waterfall?.render_blocking ?? [
          'main.bundle.js',
          'chunk.vendor.js',
          'styles-critical.css',
          'gtag/js',
          'cdn.analytics.io/track.js',
          'fonts/inter.woff2',
          'chunk.react.js',
        ]
      ).length > 0 && (
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
            Render-Blocking Assets{isOfflinePreview ? ' (sample)' : ''}
          </div>
          <div style={{ display: 'grid', gap: 6 }}>
            {(
              result.waterfall?.render_blocking ?? [
                'main.bundle.js',
                'chunk.vendor.js',
                'styles-critical.css',
                'gtag/js',
                'cdn.analytics.io/track.js',
                'fonts/inter.woff2',
                'chunk.react.js',
              ]
            ).map((asset, i) => (
              <div
                key={asset}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '7px 12px',
                  background: isOfflinePreview ? '#78350f33' : '#450a0a22',
                  border: isOfflinePreview ? '1px solid #f59e0b55' : '1px solid #ef444444',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                <span style={{ color: isOfflinePreview ? '#f59e0b' : '#ef4444', fontWeight: 700, fontSize: 10 }}>
                  {isOfflinePreview ? 'SAMPLE' : 'BLOCKING'}
                </span>
                <span style={{ flex: 1, fontFamily: 'monospace' }}>{asset}</span>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>
                  {isOfflinePreview ? 'connect backend for live blockers' : 'add defer / preload'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Third-party impact */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Third-Party Impact</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Origin', 'Reqs', 'Size', 'Blocking Time', 'Category'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 10px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { origin: 'googletagmanager.com', reqs: 4, size: '88 KB', block_ms: 320, cat: 'Analytics' },
                { origin: 'cdn.analytics.io', reqs: 2, size: '42 KB', block_ms: 480, cat: 'Analytics' },
                { origin: 'fonts.googleapis.com', reqs: 3, size: '66 KB', block_ms: 180, cat: 'Fonts' },
                { origin: 'cdn.intercom.io', reqs: 5, size: '124 KB', block_ms: 260, cat: 'Support' },
              ].map((r, i) => (
                <tr key={r.origin} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 10px', fontFamily: 'monospace', fontSize: 11 }}>{r.origin}</td>
                  <td style={{ padding: '7px 10px' }}>{r.reqs}</td>
                  <td style={{ padding: '7px 10px' }}>{r.size}</td>
                  <td style={{ padding: '7px 10px', color: r.block_ms > 300 ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>
                    {r.block_ms}ms
                  </td>
                  <td style={{ padding: '7px 10px' }}>
                    <span
                      style={{
                        borderRadius: 999,
                        padding: '2px 8px',
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        fontSize: 10,
                      }}
                    >
                      {r.cat}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function FilmstripTab({ result, card, isOfflinePreview }: PerfTabProps) {
  // NOSONAR
  const fallbackFrames: FilmstripFrame[] = [
    { label: 'navigation_start', timestamp_ms: 0, asset: 'synthetic-0' },
    { label: 'first_paint', timestamp_ms: 420, asset: 'synthetic-1' },
    { label: 'first_contentful_paint', timestamp_ms: 890, asset: 'synthetic-2' },
    { label: 'largest_contentful_paint', timestamp_ms: 2210, asset: 'synthetic-3' },
    { label: 'layout_stabilized', timestamp_ms: 2860, asset: 'synthetic-4' },
    { label: 'visual_complete', timestamp_ms: 3340, asset: 'synthetic-5' },
  ];

  const rawFrames = (result.filmstrip ?? []).length > 0 ? (result.filmstrip ?? []) : fallbackFrames;
  const frames = [...rawFrames].sort((a, b) => (a.timestamp_ms ?? 0) - (b.timestamp_ms ?? 0));

  const visualCompleteMs = frames.at(-1)?.timestamp_ms ?? 0;
  const firstPaintMs =
    frames.find((f) => (f.label ?? '').toLowerCase().includes('first_paint'))?.timestamp_ms ??
    frames.find((f) => (f.label ?? '').toLowerCase().includes('first'))?.timestamp_ms ??
    frames[1]?.timestamp_ms ??
    0;
  const fcpMs = frames.find((f) => (f.label ?? '').toLowerCase().includes('contentful'))?.timestamp_ms ?? firstPaintMs;
  const lcpMs =
    frames.find((f) => (f.label ?? '').toLowerCase().includes('largest'))?.timestamp_ms ??
    frames.find((f) => (f.label ?? '').toLowerCase().includes('hero'))?.timestamp_ms ??
    visualCompleteMs;

  const frameGaps = frames.slice(1).map((f, i) => Math.max(0, (f.timestamp_ms ?? 0) - (frames[i]?.timestamp_ms ?? 0)));
  const avgGapMs = frameGaps.length > 0 ? Math.round(frameGaps.reduce((sum, n) => sum + n, 0) / frameGaps.length) : 0;
  const maxGapMs = frameGaps.length > 0 ? Math.max(...frameGaps) : 0;

  const speedIndexEstimate = Math.round(
    frames.reduce((sum, f, i) => sum + (f.timestamp_ms ?? 0) * (i + 1), 0) / Math.max(1, frames.length * 2)
  );
  const completeness = Math.min(100, Math.round((lcpMs / Math.max(1, visualCompleteMs)) * 100));

  const timelinePoints = frames.map((f) => Math.round(((f.timestamp_ms ?? 0) / Math.max(1, visualCompleteMs)) * 100));
  const timelineLabels = frames.map((_, i) => `F${i + 1}`);

  const renderBadgeColor = visualCompleteMs <= 3200 ? '#22c55e' : visualCompleteMs <= 4200 ? '#f59e0b' : '#ef4444';
  const renderBadgeLabel =
    visualCompleteMs <= 3200 ? 'fast render' : visualCompleteMs <= 4200 ? 'needs tuning' : 'slow render';

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div
        style={{
          ...card,
          borderLeft: '4px solid #6366f1',
          display: 'flex',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Visual Render Filmstrip Intelligence</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
            Frame-by-frame page rendering diagnostics with milestone extraction and pacing analysis.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={badge(renderBadgeColor)}>{renderBadgeLabel}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Frames Captured', value: String(frames.length), color: 'var(--text)' },
          { label: 'First Paint', value: `${firstPaintMs}ms`, color: firstPaintMs <= 700 ? '#22c55e' : '#f59e0b' },
          { label: 'FCP', value: `${fcpMs}ms`, color: fcpMs <= 1200 ? '#22c55e' : '#f59e0b' },
          { label: 'LCP Visual', value: `${lcpMs}ms`, color: lcpMs <= 2500 ? '#22c55e' : '#ef4444' },
          {
            label: 'Visual Complete',
            value: `${visualCompleteMs}ms`,
            color: visualCompleteMs <= 3200 ? '#22c55e' : '#ef4444',
          },
          { label: 'Avg Frame Gap', value: `${avgGapMs}ms`, color: avgGapMs <= 400 ? '#22c55e' : '#f59e0b' },
          { label: 'Max Gap', value: `${maxGapMs}ms`, color: maxGapMs <= 900 ? '#22c55e' : '#ef4444' },
          { label: 'Speed Index Est.', value: `${speedIndexEstimate}`, color: '#6366f1' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Render Timeline Coverage</div>
          <AreaChart points={timelinePoints} labels={timelineLabels} color="#6366f1" height={70} />
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
            Above curve indicates how quickly visual completeness ramps up from first paint to final render.
          </div>
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Frame Cadence Breakdown</div>
          <MiniBarChart
            items={frameGaps.map((gap, i) => {
              const gapColor = gap > 800 ? '#ef4444' : gap > 450 ? '#f59e0b' : '#22c55e';
              return {
                label: `F${i + 1} -> F${i + 2}`,
                value: gap,
                color: gapColor,
                max: Math.max(1, maxGapMs),
                suffix: ' ms',
              };
            })}
          />
        </div>
      </div>

      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Filmstrip Frames</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
          {frames.map((frame, i) => {
            const ts = frame.timestamp_ms ?? 0;
            const progress = Math.max(0, Math.min(100, Math.round((ts / Math.max(1, visualCompleteMs)) * 100)));
            const normalizedLabel = (frame.label ?? 'unknown').replaceAll('_', ' ');
            return (
              <div key={`${frame.label ?? 'frame'}-${i}`} style={{ ...card, padding: 12 }}>
                <div
                  style={{
                    width: '100%',
                    marginBottom: 8,
                    borderRadius: 6,
                    overflow: 'hidden',
                    border: '1px solid var(--line)',
                  }}
                >
                  <FilmstripScreenshotSVG label={frame.label ?? ''} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontWeight: 700, fontSize: 12, textTransform: 'capitalize' }}>{normalizedLabel}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>{ts}ms</div>
                </div>
                <div style={{ height: 4, background: 'var(--line)', borderRadius: 2, marginTop: 8 }}>
                  <div
                    style={{
                      width: `${progress}%`,
                      height: '100%',
                      background: progress >= completeness ? '#22c55e' : '#6366f1',
                      borderRadius: 2,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Milestone Timeline</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  {['Milestone', 'Timestamp', 'Delta', 'Visual %'].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: 'left',
                        padding: '6px 8px',
                        fontSize: 10,
                        color: 'var(--muted)',
                        fontWeight: 600,
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {frames.map((frame, i) => {
                  const ts = frame.timestamp_ms ?? 0;
                  const prevTs = i > 0 ? (frames[i - 1]?.timestamp_ms ?? 0) : 0;
                  const delta = i === 0 ? 0 : Math.max(0, ts - prevTs);
                  const visualPct = Math.min(100, Math.round((ts / Math.max(1, visualCompleteMs)) * 100));
                  const deltaColor = delta > 800 ? '#ef4444' : delta > 450 ? '#f59e0b' : '#22c55e';
                  return (
                    <tr key={`ms-${frame.label ?? i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                      <td style={{ padding: '7px 8px', fontWeight: 600 }}>
                        {(frame.label ?? 'unknown').replaceAll('_', ' ')}
                      </td>
                      <td style={{ padding: '7px 8px' }}>{ts}ms</td>
                      <td style={{ padding: '7px 8px', color: deltaColor, fontWeight: 700 }}>
                        {i === 0 ? '-' : `+${delta}ms`}
                      </td>
                      <td style={{ padding: '7px 8px' }}>{visualPct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Optimization Insights</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {[
              {
                title: maxGapMs > 900 ? 'Large visual gap detected' : 'Frame pacing is mostly stable',
                body:
                  maxGapMs > 900
                    ? 'A large render idle window was detected. Investigate long tasks, blocking scripts, and hydration bursts.'
                    : 'No severe frame stalls detected in this capture window.',
                tone: maxGapMs > 900 ? '#ef4444' : '#22c55e',
              },
              {
                title: lcpMs > 2500 ? 'LCP visual milestone is late' : 'LCP visual milestone is healthy',
                body:
                  lcpMs > 2500
                    ? 'Prioritize hero asset compression and server response tuning to pull LCP earlier.'
                    : 'Largest visual element appears in an acceptable window.',
                tone: lcpMs > 2500 ? '#f59e0b' : '#22c55e',
              },
              {
                title:
                  completeness < 75 ? 'Above-the-fold completion delayed' : 'Above-the-fold completion timing is good',
                body:
                  completeness < 75
                    ? 'Critical render path remains active for too long. Inline critical CSS and defer non-essential JS.'
                    : 'Above-the-fold visuals complete early in the timeline.',
                tone: completeness < 75 ? '#f59e0b' : '#22c55e',
              },
            ].map((insight, i) => (
              <div
                key={insight.title}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  background: 'var(--bg)',
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 12, color: insight.tone, marginBottom: 4 }}>
                  {insight.title}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{insight.body}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function RumTab({
  result,
  card,
  isOfflinePreview,
  rumCollector,
  currentPageRumRollup,
  rumTargetSummary,
  rumTargetLoading,
  refreshRumTargetSummary,
}: PerfTabProps) {
  const installSnippet = buildRumInstallSnippet();
  const targetRollup = rumTargetSummary?.rollup ?? null;
  const liveRollup = currentPageRumRollup ?? null;
  const liveRollupVitals = liveRollup?.field_web_vitals ?? null;
  const matchesAuditUrl = rumCollector?.canCollectForAuditUrl ?? false;
  const targetMetricRows: Array<[string, number | undefined]> = [
    ['LCP', targetRollup?.field_web_vitals?.lcp_p75_ms ?? result.field_web_vitals?.lcp_p75_ms],
    ['INP', targetRollup?.field_web_vitals?.inp_p75_ms ?? result.field_web_vitals?.inp_p75_ms],
    ['CLS', targetRollup?.field_web_vitals?.cls_p75 ?? result.field_web_vitals?.cls_p75],
  ];
  const liveMetricRows: Array<[string, number | undefined]> = [
    ['LCP', liveRollupVitals?.lcp_p75_ms],
    ['INP', liveRollupVitals?.inp_p75_ms],
    ['CLS', liveRollupVitals?.cls_p75],
  ];

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <section style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>Real User Monitoring Intelligence</div>
        <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 14 }}>
          Synthetic audit data is merged with free-provider field data and first-party browser telemetry when available.
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: 10,
            marginBottom: 14,
          }}
        >
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 11 }}>Collector Status</div>
            <div style={{ fontWeight: 800, fontSize: 20, color: rumCollector?.error ? '#ef4444' : '#22c55e' }}>
              {rumCollector?.error
                ? 'Error'
                : rumCollector?.collecting
                  ? 'Active'
                  : rumCollector?.supported
                    ? 'Idle'
                    : 'Unsupported'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>
              {rumCollector?.supported
                ? `Current page: ${rumCollector.currentPageUrl || 'n/a'}`
                : 'PerformanceObserver is not available in this browser context.'}
            </div>
          </div>

          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 11 }}>Audit URL Match</div>
            <div style={{ fontWeight: 800, fontSize: 20, color: matchesAuditUrl ? '#22c55e' : '#f59e0b' }}>
              {matchesAuditUrl ? 'Direct' : 'Snippet Required'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>
              Target: {rumCollector?.targetUrl || result.url}
            </div>
          </div>

          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 11 }}>Metrics Ingested</div>
            <div style={{ fontWeight: 800, fontSize: 20 }}>{rumCollector?.ingestedCount ?? 0}</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>
              {rumCollector?.lastMetric
                ? `${rumCollector.lastMetric}: ${formatRumMetricValue(rumCollector.lastMetric, rumCollector.lastValue)}`
                : 'Waiting for first metric'}
            </div>
          </div>
        </div>

        {rumCollector?.error && (
          <div style={{ color: '#dc2626', fontSize: 12, marginBottom: 12 }}>{rumCollector.error}</div>
        )}
        {!matchesAuditUrl && (
          <div style={{ ...card, borderColor: '#f59e0b55', background: '#f59e0b14', marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>Target-site instrumentation needed</div>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>
              A browser session can only measure the page it is currently running on. This page is collecting vitals for
              the local performance UI, not for {result.url}. Add the snippet below to the audited site to capture true
              first-party telemetry for that URL.
            </div>
          </div>
        )}
      </section>

      <section style={card}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>Audit Target Field Data</div>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>
              Rollup for {rumTargetSummary?.url ?? result.url} {rumTargetLoading ? 'is loading…' : ''}
            </div>
          </div>
          {refreshRumTargetSummary && (
            <button type="button" onClick={() => void refreshRumTargetSummary()} style={btn(false)}>
              Refresh RUM
            </button>
          )}
        </div>

        {targetRollup?.field_web_vitals || result.field_web_vitals ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
              gap: 10,
              marginBottom: 14,
            }}
          >
            {targetMetricRows.map(([metric, value]) => {
              const numericValue = typeof value === 'number' ? value : undefined;
              const status = numericValue === undefined ? 'good' : rateRumMetric(metric, numericValue);
              return (
                <div key={metric} style={card}>
                  <div style={{ color: 'var(--muted)', fontSize: 11 }}>{metric} p75</div>
                  <div style={{ fontWeight: 800, fontSize: 20, color: cwvColor(status) }}>
                    {formatRumMetricValue(metric, numericValue)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{status.replace('-', ' ')}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 14 }}>
            No aggregated field data exists yet for this audit target.
          </div>
        )}

        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          Provenance:{' '}
          <strong style={{ color: 'var(--text)' }}>
            {targetRollup?.data_provenance?.source ?? result.field_web_vitals?.source ?? 'synthetic_only'}
          </strong>
        </div>
      </section>

      {liveRollup?.field_web_vitals && (
        <section style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Current Page Live Rollup</div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
              gap: 10,
            }}
          >
            {liveMetricRows.map(([metric, value]) => (
              <div key={metric} style={card}>
                <div style={{ color: 'var(--muted)', fontSize: 11 }}>{metric} p75</div>
                <div style={{ fontWeight: 800, fontSize: 20 }}>{formatRumMetricValue(metric, value)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Install Snippet For Audited Site</div>
        <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 12 }}>
          Use this on the audited property when the target URL is not the page currently open in this browser session.
        </div>
        <pre
          style={{
            margin: 0,
            padding: 12,
            overflowX: 'auto',
            borderRadius: 10,
            background: '#f6f7fa',
            color: '#dbeafe',
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          {installSnippet}
        </pre>
      </section>

      {result.rum_summary ? (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 170px), 1fr))',
              gap: 10,
              marginBottom: 14,
            }}
          >
            <div style={card}>
              <div style={{ color: 'var(--muted)', fontSize: 11 }}>Sessions</div>
              <div style={{ fontWeight: 800, fontSize: 20 }}>{(result.rum_summary.sessions ?? 0).toLocaleString()}</div>
            </div>
            <div style={card}>
              <div style={{ color: 'var(--muted)', fontSize: 11 }}>Rage Click Rate</div>
              <div style={{ fontWeight: 800, fontSize: 20 }}>
                {((result.rum_summary.rage_click_rate ?? 0) * 100).toFixed(2)}%
              </div>
            </div>
            <div style={card}>
              <div style={{ color: 'var(--muted)', fontSize: 11 }}>UX Friction Score</div>
              <div style={{ fontWeight: 800, fontSize: 20 }}>{result.rum_summary.friction_score ?? 0}</div>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))',
              gap: 12,
              marginBottom: 14,
            }}
          >
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Device Mix</div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <DonutChart
                  slices={Object.entries(result.rum_summary.device_mix ?? {}).map(([k, v], i) => ({
                    label: k,
                    value: v,
                    color: DONUT_COLORS[i % DONUT_COLORS.length],
                  }))}
                  size={110}
                />
                <div style={{ display: 'grid', gap: 5, flex: 1 }}>
                  {Object.entries(result.rum_summary.device_mix ?? {}).map(([k, v], i) => (
                    <div key={`item-${k}`} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: DONUT_COLORS[i % DONUT_COLORS.length],
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ color: 'var(--muted)', flex: 1 }}>{k}</span>
                      <strong>{(v * 100).toFixed(1)}%</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Network Mix</div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <DonutChart
                  slices={Object.entries(result.rum_summary.network_mix ?? {}).map(([k, v], i) => ({
                    label: k,
                    value: v,
                    color: NETWORK_COLORS[i % NETWORK_COLORS.length],
                  }))}
                  size={110}
                />
                <div style={{ display: 'grid', gap: 5, flex: 1 }}>
                  {Object.entries(result.rum_summary.network_mix ?? {}).map(([k, v], i) => (
                    <div key={`item-${k}`} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: NETWORK_COLORS[i % NETWORK_COLORS.length],
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ color: 'var(--muted)', flex: 1 }}>{k.toUpperCase()}</span>
                      <strong>{(v * 100).toFixed(1)}%</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Geo + ISP Breakdown</div>
            {(result.rum_summary.geo_isp_breakdown ?? []).length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>No geo/ISP breakdown captured.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.rum_summary.geo_isp_breakdown ?? []).map((row, i) => (
                  <div
                    key={`${row.country}-${row.region}-${row.isp}-${i}`}
                    style={{
                      ...card,
                      padding: 10,
                      display: 'grid',
                      gridTemplateColumns: '1fr auto auto',
                      gap: 10,
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ fontSize: 12 }}>
                      <strong>{row.country ?? 'n/a'}</strong>
                      <span style={{ color: 'var(--muted)' }}>
                        {' '}
                        / {row.region ?? 'n/a'} / {row.isp ?? 'n/a'}
                      </span>
                    </div>
                    <div style={{ fontSize: 12 }}>
                      LCP p75: <strong>{row.lcp_p75_ms ?? 0}ms</strong>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      n={(row.sample_size ?? 0).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <section style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>No RUM summary available for this audit run.</div>
        </section>
      )}
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CausalityTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Performance Causality Graph</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Root-cause attribution for every millisecond of load delay, traced from network to paint.
      </div>

      {/* KPI row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Critical Path</div>
          <div style={{ fontWeight: 800, fontSize: 22, color: '#ef4444' }}>
            {result.causality_graph?.critical_path_ms ?? 0}ms
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Wasted Time</div>
          <div style={{ fontWeight: 800, fontSize: 22, color: '#f59e0b' }}>
            {result.causality_graph?.wasted_ms ?? 0}ms
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Blocking Assets</div>
          <div style={{ fontWeight: 800, fontSize: 22 }}>
            {(result.causality_graph?.render_blocking_attribution ?? []).length}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>3rd-party Scripts</div>
          <div style={{ fontWeight: 800, fontSize: 22 }}>
            {(result.causality_graph?.third_party_impact ?? []).length}
          </div>
        </div>
      </div>

      {/* Root causes */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Root Causes</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(result.causality_graph?.root_causes ?? []).map((cause) => (
            <span
              key={cause}
              style={{
                fontSize: 11,
                borderRadius: 999,
                padding: '5px 12px',
                background: '#7f1d1d22',
                color: '#dc2626',
                border: '1px solid #ef444455',
              }}
            >
              ⚠ {cause}
            </span>
          ))}
        </div>
      </div>

      {/* Main thread timeline */}
      {(result.causality_graph?.main_thread_timeline ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Main Thread Timeline</div>
          <MiniBarChart
            items={(result.causality_graph?.main_thread_timeline ?? []).map((t) => {
              const taskColor =
                t.type === 'script'
                  ? '#ef4444'
                  : t.type === 'style'
                    ? '#f59e0b'
                    : t.type === 'render'
                      ? '#22c55e'
                      : '#6366f1';
              return {
                label: t.task ?? '',
                value: t.duration_ms ?? 0,
                max: 500,
                suffix: 'ms',
                color: taskColor,
              };
            })}
          />
          <div
            style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--muted)', flexWrap: 'wrap' }}
          >
            {[
              ['#ef4444', 'Script'],
              ['#f59e0b', 'Style'],
              ['#22c55e', 'Render'],
              ['#6366f1', 'Parse'],
            ].map(([c, l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: 'inline-block' }} />
                {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Render blocking + 3rd party side by side */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Render-blocking Attribution</div>
          <MiniBarChart
            items={(result.causality_graph?.render_blocking_attribution ?? []).map((x) => {
              const attrColor = x.severity === 'critical' ? '#ef4444' : x.severity === 'high' ? '#f59e0b' : '#6366f1';
              return {
                label: x.asset ?? '',
                value: x.block_ms ?? 0,
                max: 400,
                suffix: 'ms',
                color: attrColor,
              };
            })}
          />
          <div style={{ marginTop: 8, display: 'grid', gap: 4 }}>
            {(result.causality_graph?.render_blocking_attribution ?? []).map((x, i) => {
              const rbaBackground =
                x.severity === 'critical' ? '#7f1d1d44' : x.severity === 'high' ? '#78350f44' : '#1e1b4b44';
              const rbaColor = x.severity === 'critical' ? '#dc2626' : x.severity === 'high' ? '#b45309' : '#6366f1';
              return (
                <div
                  key={`rba-${x.asset ?? i}`}
                  style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}
                >
                  <span style={{ color: 'var(--muted)' }}>{x.phase?.toUpperCase()}</span>
                  <span
                    style={{
                      borderRadius: 999,
                      padding: '2px 8px',
                      fontSize: 10,
                      background: rbaBackground,
                      color: rbaColor,
                    }}
                  >
                    {x.severity}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Third-party Script Impact</div>
          <MiniBarChart
            items={(result.causality_graph?.third_party_impact ?? []).map((x) => ({
              label: x.provider ?? '',
              value: (x.main_thread_block_ms ?? 0) + (x.network_ms ?? 0),
              max: 400,
              suffix: 'ms total',
              color: x.removable ? '#f59e0b' : '#6366f1',
            }))}
          />
          <div style={{ marginTop: 10, display: 'grid', gap: 6 }}>
            {(result.causality_graph?.third_party_impact ?? []).map((x, i) => (
              <div
                key={`tpi-${x.provider ?? i}`}
                style={{ fontSize: 11, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <span>
                  <strong>{x.provider}</strong> <span style={{ color: 'var(--muted)' }}>({x.category})</span>
                </span>
                <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span style={{ color: 'var(--muted)' }}>
                    MT: {x.main_thread_block_ms}ms · Net: {x.network_ms}ms
                  </span>
                  {x.removable && (
                    <span
                      style={{
                        borderRadius: 999,
                        padding: '2px 7px',
                        background: '#78350f44',
                        color: '#b45309',
                        fontSize: 10,
                      }}
                    >
                      removable
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dependency chain */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Dependency Chain</div>
        {(result.causality_graph?.dependencies ?? []).length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>No dependency edges recorded.</div>
        ) : (
          <div style={{ display: 'grid', gap: 6 }}>
            {(result.causality_graph?.dependencies ?? []).map((edge, i) => (
              <div
                key={`dep-${edge.from ?? i}-${edge.to ?? i}`}
                style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}
              >
                <code style={{ background: 'var(--bg)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>
                  {edge.from}
                </code>
                <span style={{ color: 'var(--muted)' }}>→ {edge.latency_ms ?? 0}ms →</span>
                <code style={{ background: 'var(--bg)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>
                  {edge.to}
                </code>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AgentsTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Autonomous Synthetic Agent Coverage</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Continuous multi-journey synthetic monitoring with scenario mutation testing across{' '}
        {result.autonomous_agents?.scenario_mutations ?? 0} permutations.
      </div>

      {/* KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Coverage Score</div>
          <div
            style={{ fontWeight: 800, fontSize: 26, color: scoreColor(result.autonomous_agents?.coverage_score ?? 0) }}
          >
            {result.autonomous_agents?.coverage_score ?? 0}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Scenario Mutations</div>
          <div style={{ fontWeight: 800, fontSize: 26 }}>{result.autonomous_agents?.scenario_mutations ?? 0}</div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Journeys</div>
          <div style={{ fontWeight: 800, fontSize: 26 }}>
            {(result.autonomous_agents?.journeys_tested ?? []).length}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Healthy Agents</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#22c55e' }}>
            {result.autonomous_agents?.agent_health?.healthy ?? 0}
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>
              /{result.autonomous_agents?.agent_health?.total_agents ?? 0}
            </span>
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Degraded</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#f59e0b' }}>
            {result.autonomous_agents?.agent_health?.degraded ?? 0}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Offline</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#ef4444' }}>
            {result.autonomous_agents?.agent_health?.offline ?? 0}
          </div>
        </div>
      </div>

      {/* Per-journey metrics table */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Journey Performance Matrix</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', color: 'var(--muted)', fontSize: 11 }}>
                {['Journey', 'P50', 'P75', 'P95', 'Pass Rate', 'Runs'].map((h) => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(result.autonomous_agents?.journey_metrics ?? []).map((jm, i) => {
                const pass = (jm.pass_rate ?? 0) >= 0.9;
                const p95Color = (jm.p95_ms ?? 0) > 4000 ? '#ef4444' : (jm.p95_ms ?? 0) > 2500 ? '#f59e0b' : '#22c55e';
                return (
                  <tr key={`jm-${jm.journey ?? i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{jm.journey}</td>
                    <td style={{ padding: '7px 10px' }}>{jm.p50_ms}ms</td>
                    <td style={{ padding: '7px 10px' }}>{jm.p75_ms}ms</td>
                    <td style={{ padding: '7px 10px', color: p95Color }}>
                      <strong>{jm.p95_ms}ms</strong>
                    </td>
                    <td style={{ padding: '7px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div
                          style={{ flex: 1, height: 4, background: 'var(--line)', borderRadius: 2, overflow: 'hidden' }}
                        >
                          <div
                            style={{
                              width: `${(jm.pass_rate ?? 0) * 100}%`,
                              height: '100%',
                              background: pass ? '#22c55e' : '#ef4444',
                              borderRadius: 2,
                            }}
                          />
                        </div>
                        <span style={{ color: pass ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                          {((jm.pass_rate ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '7px 10px', color: 'var(--muted)' }}>{jm.runs}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))', gap: 12 }}>
        {/* Mutation matrix */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Scenario Mutation Results</div>
          {(result.autonomous_agents?.mutation_matrix ?? []).map((m, i) => {
            const total = (m.passed ?? 0) + (m.failed ?? 0) + (m.flaky ?? 0);
            return (
              <div key={`mm-${m.scenario ?? i}`} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600 }}>{m.scenario}</span>
                  <span style={{ color: 'var(--muted)' }}>{total} runs</span>
                </div>
                <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 1 }}>
                  <div style={{ flex: m.passed ?? 0, background: '#22c55e' }} />
                  <div style={{ flex: m.flaky ?? 0, background: '#f59e0b' }} />
                  <div style={{ flex: m.failed ?? 0, background: '#ef4444' }} />
                </div>
                <div style={{ display: 'flex', gap: 10, fontSize: 10, marginTop: 3, color: 'var(--muted)' }}>
                  <span style={{ color: '#22c55e' }}>{m.passed} pass</span>
                  <span style={{ color: '#f59e0b' }}>{m.flaky} flaky</span>
                  <span style={{ color: '#ef4444' }}>{m.failed} fail</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Deviation from baseline */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Deviation from Baseline</div>
          <MiniBarChart
            items={(result.autonomous_agents?.deviation_from_baseline ?? []).map((d) => ({
              label: `${d.metric} (+${d.delta_pct?.toFixed(1)}%)`,
              value: d.delta_pct ?? 0,
              max: 30,
              suffix: '%',
              color: (d.delta_pct ?? 0) > 20 ? '#ef4444' : '#f59e0b',
            }))}
          />
          <div style={{ marginTop: 10, display: 'grid', gap: 6 }}>
            {(result.autonomous_agents?.deviation_from_baseline ?? []).map((d, i) => (
              <div
                key={`dev-${d.metric ?? i}`}
                style={{ fontSize: 11, display: 'flex', justifyContent: 'space-between' }}
              >
                <span style={{ color: 'var(--muted)' }}>{d.baseline_ms}ms baseline</span>
                <span style={{ color: '#ef4444', fontWeight: 700 }}>→ {d.current_ms}ms</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Failure hotspots */}
      {(result.autonomous_agents?.failure_hotspots ?? []).length > 0 && (
        <div style={{ ...card, marginTop: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Failure Hotspots</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {(result.autonomous_agents?.failure_hotspots ?? []).map((h, i) => (
              <div
                key={`hs-${h.journey ?? i}`}
                style={{
                  ...card,
                  padding: 10,
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  flexWrap: 'wrap',
                  fontSize: 12,
                  borderLeft: '3px solid #ef4444',
                }}
              >
                <span>
                  <strong>{h.journey}</strong> <span style={{ color: 'var(--muted)' }}>/ {h.step}</span>
                </span>
                <span style={{ color: '#ef4444', fontWeight: 700 }}>P95: {h.p95_ms}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function PredictionTab({ result, card, isOfflinePreview }: PerfTabProps) {
  const deployConfidence = result.predictive_intelligence?.deploy_confidence ?? 0;
  const deployConfidenceColor = deployConfidence >= 80 ? '#22c55e' : deployConfidence >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Predictive Performance Intelligence</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        AI-driven {result.predictive_intelligence?.forecast_horizon_days ?? 14}-day forecast with regression risk
        scoring and pre-deploy guardrails.
      </div>

      {/* KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 170px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>AI Confidence</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: deployConfidenceColor }}>{deployConfidence}%</div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>Deploy confidence</div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Regression Risk</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#f59e0b' }}>
            {result.predictive_intelligence?.regression_risk?.label?.toUpperCase() ?? 'N/A'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            {((result.predictive_intelligence?.regression_risk?.probability ?? 0) * 100).toFixed(0)}% probability
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Forecast LCP</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#ef4444' }}>
            {result.predictive_intelligence?.forecast?.lcp_ms ?? 0}ms
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            in {result.predictive_intelligence?.forecast_horizon_days ?? 14} days
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Pre-deploy Guard</div>
          <div
            style={{
              fontWeight: 800,
              fontSize: 26,
              color: result.predictive_intelligence?.pre_deploy_guardrail?.status === 'pass' ? '#22c55e' : '#f59e0b',
            }}
          >
            {result.predictive_intelligence?.pre_deploy_guardrail?.status?.toUpperCase() ?? 'N/A'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            +{result.predictive_intelligence?.pre_deploy_guardrail?.predicted_lcp_delta_ms ?? 0}ms predicted
          </div>
        </div>
      </div>

      {/* Weekly trend chart */}
      {(result.predictive_intelligence?.weekly_trend ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>LCP 6-week Trend + 1-week Forecast</div>
          <MiniBarChart
            items={(result.predictive_intelligence?.weekly_trend ?? []).map((w) => {
              const trendColor = w.week === 'Forecast' ? '#6366f1' : (w.lcp_ms ?? 0) > 2500 ? '#ef4444' : '#22c55e';
              return {
                label: w.week ?? '',
                value: w.lcp_ms ?? 0,
                max: 4000,
                suffix: 'ms',
                color: trendColor,
              };
            })}
          />
          <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 11, color: 'var(--muted)' }}>
            <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#22c55e', display: 'inline-block' }} />
              Within budget
            </span>
            <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#ef4444', display: 'inline-block' }} />
              Over budget
            </span>
            <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#6366f1', display: 'inline-block' }} />
              Forecast
            </span>
          </div>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
          gap: 12,
          marginBottom: 12,
        }}
      >
        {/* Regression contributing factors */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Regression Contributing Factors</div>
          {(result.predictive_intelligence?.regression_risk?.contributing_factors ?? []).map((f, i) => (
            <div
              key={`cf-${f}`}
              style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12, marginBottom: 8 }}
            >
              <span style={{ color: '#f59e0b', marginTop: 1 }}>▲</span>
              <span>{f}</span>
            </div>
          ))}
        </div>

        {/* Anomaly forecast */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Predicted Breach Dates</div>
          {(result.predictive_intelligence?.anomaly_forecast ?? []).map((a, i) => {
            const afBackground =
              a.severity === 'high' ? '#7f1d1d44' : a.severity === 'medium' ? '#78350f44' : '#1e3a2f44';
            const afColor = a.severity === 'high' ? '#dc2626' : a.severity === 'medium' ? '#b45309' : '#15803d';
            return (
              <div
                key={`af-${a.metric ?? i}`}
                style={{
                  ...card,
                  padding: 8,
                  marginBottom: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: 12,
                }}
              >
                <span>
                  <strong>{a.metric}</strong>
                </span>
                <span style={{ color: 'var(--muted)' }}>{a.expected_breach_date}</span>
                <span
                  style={{
                    borderRadius: 999,
                    padding: '2px 8px',
                    fontSize: 10,
                    background: afBackground,
                    color: afColor,
                  }}
                >
                  {a.severity}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI recommendations */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>AI Preventive Recommendations</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {(result.predictive_intelligence?.ai_recommendations ?? []).map((r, i) => (
            <div
              key={`air-${i}`}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                fontSize: 12,
                padding: '8px 10px',
                background: 'var(--bg)',
                borderRadius: 8,
                border: '1px solid var(--line)',
              }}
            >
              <span style={{ color: '#6366f1', fontWeight: 700, flexShrink: 0 }}>#{i + 1}</span>
              <span>{r}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function GlobalTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Global Simulation Mesh</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Real-user-condition simulation across {result.global_simulation?.coverage_regions ?? 0} regions,{' '}
        {result.global_simulation?.isp_profiles_tested ?? 0} ISP profiles and{' '}
        {(result.global_simulation?.network_profiles ?? []).length} network types.
      </div>

      {/* KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Global P75 LCP</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#ef4444' }}>
            {result.global_simulation?.global_p75_lcp_ms ?? 0}ms
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Regions Covered</div>
          <div style={{ fontWeight: 800, fontSize: 24 }}>{result.global_simulation?.coverage_regions ?? 0}</div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>ISP Profiles</div>
          <div style={{ fontWeight: 800, fontSize: 24 }}>{result.global_simulation?.isp_profiles_tested ?? 0}</div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Best Region</div>
          <div style={{ fontWeight: 700, fontSize: 12, color: '#22c55e', marginTop: 4 }}>
            {result.global_simulation?.best_region ?? 'n/a'}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Worst Region</div>
          <div style={{ fontWeight: 700, fontSize: 12, color: '#ef4444', marginTop: 4 }}>
            {result.global_simulation?.worst_region ?? 'n/a'}
          </div>
        </div>
      </div>

      {/* Region grid table */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Region × Network Performance Grid</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', color: 'var(--muted)', fontSize: 11 }}>
                {['Region', 'Network', 'LCP P75', 'FCP', 'TTFB', 'Status'].map((h) => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(result.global_simulation?.region_grid ?? []).map((r, i) => {
                const lcpColor =
                  (r.lcp_p75_ms ?? 0) > 4000 ? '#ef4444' : (r.lcp_p75_ms ?? 0) > 2500 ? '#f59e0b' : '#22c55e';
                return (
                  <tr key={r.region} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{r.region}</td>
                    <td style={{ padding: '7px 10px' }}>
                      <span
                        style={{
                          borderRadius: 999,
                          padding: '2px 8px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                          fontSize: 10,
                        }}
                      >
                        {r.network?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '7px 10px', color: lcpColor, fontWeight: 700 }}>{r.lcp_p75_ms}ms</td>
                    <td style={{ padding: '7px 10px', color: 'var(--muted)' }}>{r.fcp_ms}ms</td>
                    <td style={{ padding: '7px 10px', color: 'var(--muted)' }}>{r.ttfb_ms}ms</td>
                    <td style={{ padding: '7px 10px' }}>
                      <span
                        style={{
                          borderRadius: 999,
                          padding: '3px 9px',
                          fontSize: 10,
                          background: r.pass ? '#14532d44' : '#7f1d1d44',
                          color: r.pass ? '#15803d' : '#dc2626',
                        }}
                      >
                        {r.pass ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* CDN PoP latency bars */}
      {(result.global_simulation?.cdn_pop_latency ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>CDN PoP Edge Latency</div>
          <MiniBarChart
            items={(result.global_simulation?.cdn_pop_latency ?? []).map((p) => {
              const popColor = (p.latency_ms ?? 0) > 80 ? '#ef4444' : (p.latency_ms ?? 0) > 40 ? '#f59e0b' : '#22c55e';
              return {
                label: p.pop ?? '',
                value: p.latency_ms ?? 0,
                max: 150,
                suffix: 'ms',
                color: popColor,
              };
            })}
          />
        </div>
      )}

      {/* Network profile tags + hotspots */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Network Profiles Tested</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(result.global_simulation?.network_profiles ?? []).map((profile) => (
              <span
                key={profile}
                style={{
                  fontSize: 11,
                  borderRadius: 999,
                  padding: '5px 12px',
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                }}
              >
                {profile.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Worst-performing Hotspots</div>
          {(result.global_simulation?.hotspots ?? []).map((h, i) => (
            <div
              key={`hot-${h.region ?? i}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 12,
                marginBottom: 6,
                paddingBottom: 6,
                borderBottom:
                  i < (result.global_simulation?.hotspots?.length ?? 0) - 1 ? '1px solid var(--line)' : 'none',
              }}
            >
              <span>
                <strong>{h.region}</strong> <span style={{ color: 'var(--muted)' }}>({h.network?.toUpperCase()})</span>
              </span>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>LCP {h.lcp_ms}ms</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function BusinessTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Business Impact Intelligence</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Revenue attribution, conversion modelling and competitive rank risk tied directly to Core Web Vitals.
      </div>

      {/* KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 170px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Monthly Revenue at Risk</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#ef4444' }}>
            ${(result.business_impact?.estimated_monthly_revenue_at_risk_usd ?? 0).toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            Annualised: ${(result.business_impact?.annualized_at_risk_usd ?? 0).toLocaleString()}
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Conversion Δ / 100ms</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#ef4444' }}>
            {((result.business_impact?.conversion_delta_per_100ms ?? 0) * 100).toFixed(2)}%
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Bounce Probability</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#f59e0b' }}>
            {((result.business_impact?.bounce_probability ?? 0) * 100).toFixed(1)}%
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>SEO Traffic Δ</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#ef4444' }}>
            {result.business_impact?.seo_rank_sensitivity?.traffic_delta_pct ?? 0}%
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            Top-3 drop risk: {((result.business_impact?.seo_rank_sensitivity?.top3_drop_risk ?? 0) * 100).toFixed(0)}%
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Priority</div>
          <div style={{ fontWeight: 800, fontSize: 24, color: '#ef4444' }}>
            {(result.business_impact?.priority ?? 'n/a').toUpperCase()}
          </div>
        </div>
      </div>

      {/* Segment impact table */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Revenue by User Segment</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', color: 'var(--muted)', fontSize: 11 }}>
                {['Segment', 'LCP', 'Conv. Rate', 'Revenue / mo', 'Risk'].map((h) => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(result.business_impact?.segment_impact ?? []).map((s, i) => {
                const segLcpColor = (s.lcp_ms ?? 0) > 4000 ? '#ef4444' : (s.lcp_ms ?? 0) > 2500 ? '#f59e0b' : '#22c55e';
                return (
                  <tr key={s.segment} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{s.segment}</td>
                    <td style={{ padding: '7px 10px', color: segLcpColor, fontWeight: 700 }}>{s.lcp_ms}ms</td>
                    <td style={{ padding: '7px 10px' }}>{((s.conversion_rate ?? 0) * 100).toFixed(1)}%</td>
                    <td style={{ padding: '7px 10px', fontWeight: 700 }}>${(s.revenue_usd ?? 0).toLocaleString()}</td>
                    <td style={{ padding: '7px 10px' }}>
                      <div
                        style={{ height: 4, background: 'var(--line)', borderRadius: 2, width: 80, overflow: 'hidden' }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, ((s.lcp_ms ?? 0) / 6000) * 100)}%`,
                            height: '100%',
                            background: (s.lcp_ms ?? 0) > 4000 ? '#ef4444' : '#f59e0b',
                            borderRadius: 2,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))', gap: 12 }}>
        {/* Revenue waterfall */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Fix Revenue Recovery Waterfall</div>
          {(result.business_impact?.revenue_waterfall ?? []).map((w, i) => (
            <div key={`rw-${w.fix ?? i}`} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>{w.fix}</span>
                <span style={{ color: '#22c55e', fontWeight: 700 }}>+${(w.gain_usd ?? 0).toLocaleString()}/mo</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ flex: 1, height: 6, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${((w.gain_usd ?? 0) / 5000) * 100}%`,
                      height: '100%',
                      background: '#22c55e',
                      borderRadius: 3,
                    }}
                  />
                </div>
                <span style={{ fontSize: 10, color: 'var(--muted)', width: 44 }}>{w.effort}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Competitor rank risk */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Competitor Rank Risk</div>
          {(result.business_impact?.competitor_rank_risk ?? []).map((c, i) => (
            <div
              key={`crr-${c.rank ?? i}`}
              style={{
                ...card,
                padding: 8,
                marginBottom: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 12,
              }}
            >
              <span>
                <strong>#{c.rank}</strong> <span style={{ color: 'var(--muted)' }}>{c.competitor}</span>
              </span>
              <span style={{ color: (c.gap_ms ?? 0) < 0 ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                {(c.gap_ms ?? 0) < 0 ? `${Math.abs(c.gap_ms ?? 0)}ms faster` : `${c.gap_ms}ms slower`}
              </span>
            </div>
          ))}
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
            Competitors faster than you risk absorbing your search traffic share.
          </div>
        </div>
      </div>

      {/* Full-stack correlation */}
      <div style={{ ...card, marginTop: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Full-stack Observability Correlation</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))', gap: 10 }}>
          {[
            {
              label: 'Trace P95',
              value: `${result.full_stack_observability?.frontend_to_backend_trace?.p95_ms ?? 0}ms`,
              sub: result.full_stack_observability?.frontend_to_backend_trace?.slow_span ?? '',
            },
            { label: 'API P95', value: `${result.full_stack_observability?.api_latency_p95_ms ?? 0}ms` },
            { label: 'DB P95', value: `${result.full_stack_observability?.db_query_p95_ms ?? 0}ms` },
            {
              label: 'CDN Hit Rate',
              value: `${((result.full_stack_observability?.cdn?.hit_rate ?? 0) * 100).toFixed(1)}%`,
            },
            {
              label: 'CPU Spike Corr.',
              value: `${((result.full_stack_observability?.infra?.cpu_spike_corr ?? 0) * 100).toFixed(0)}%`,
            },
          ].map((m) => (
            <div key={m.label} style={card}>
              <div style={{ color: 'var(--muted)', fontSize: 11 }}>{m.label}</div>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{m.value}</div>
              {m.sub && <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>{m.sub}</div>}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CiGateTab({ result, card, isOfflinePreview }: PerfTabProps) {
  const gateStatus = result.ci_gate?.status;
  const gateBorderColor = gateStatus === 'pass' ? '#22c55e' : gateStatus === 'fail' ? '#ef4444' : '#f59e0b';
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Performance CI Gate</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Automated pre-merge gate that blocks regressions before they reach production using predicted PR impact
        analysis.
      </div>

      {/* Status banner */}
      <div style={{ ...card, marginBottom: 16, borderLeft: `4px solid ${gateBorderColor}` }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              Gate Status: <span style={{ color: gateBorderColor }}>{(gateStatus ?? 'warn').toUpperCase()}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              {result.ci_gate?.recommendation?.replaceAll('_', ' ')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {[
              {
                label: 'LCP Δ',
                value: `+${result.ci_gate?.predicted_pr_impact?.lcp_delta_ms ?? 0}ms`,
                over: (result.ci_gate?.predicted_pr_impact?.lcp_delta_ms ?? 0) > 0,
              },
              {
                label: 'INP Δ',
                value: `+${result.ci_gate?.predicted_pr_impact?.inp_delta_ms ?? 0}ms`,
                over: (result.ci_gate?.predicted_pr_impact?.inp_delta_ms ?? 0) > 0,
              },
              {
                label: 'CLS Δ',
                value: `+${result.ci_gate?.predicted_pr_impact?.cls_delta ?? 0}`,
                over: (result.ci_gate?.predicted_pr_impact?.cls_delta ?? 0) > 0,
              },
            ].map((m) => (
              <div key={m.label} style={card}>
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>{m.label}</div>
                <div style={{ fontWeight: 800, fontSize: 18, color: m.over ? '#ef4444' : '#22c55e' }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Budget adherence bars */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Budget Adherence</div>
        <MiniBarChart
          items={[
            {
              label: 'LCP (budget 2500ms)',
              value: result.ci_gate?.predicted_pr_impact?.lcp_delta_ms ?? 0,
              max: result.ci_gate?.budget?.lcp_ms ?? 2500,
              suffix: 'ms over',
              color: '#ef4444',
            },
            {
              label: 'INP (budget 200ms)',
              value: result.ci_gate?.predicted_pr_impact?.inp_delta_ms ?? 0,
              max: result.ci_gate?.budget?.inp_ms ?? 200,
              suffix: 'ms over',
              color: '#f59e0b',
            },
          ]}
        />
      </div>

      {/* Blocking rules */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Gate Rules</div>
        <div style={{ display: 'grid', gap: 6 }}>
          {(result.ci_gate?.blocking_rules ?? []).map((rule, i) => (
            <div
              key={`br-${rule.rule ?? i}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                background: 'var(--bg)',
                borderRadius: 8,
                border: `1px solid ${rule.pass ? '#22c55e44' : '#ef444444'}`,
                fontSize: 12,
              }}
            >
              <span style={{ fontWeight: 600 }}>{rule.rule}</span>
              <span style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span style={{ color: 'var(--muted)' }}>budget: {rule.threshold}</span>
                <span style={{ color: rule.pass ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                  current: {rule.current}
                </span>
                <span
                  style={{
                    borderRadius: 999,
                    padding: '2px 9px',
                    fontSize: 10,
                    background: rule.pass ? '#14532d44' : '#7f1d1d44',
                    color: rule.pass ? '#15803d' : '#dc2626',
                  }}
                >
                  {rule.pass ? 'PASS' : 'FAIL'}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))', gap: 12 }}>
        {/* PR diff analysis */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>PR Diff Analysis</div>
          {(result.ci_gate?.pr_diff_analysis ?? []).map((d, i) => {
            const prBackground =
              d.severity === 'critical' ? '#7f1d1d44' : d.severity === 'high' ? '#78350f44' : '#1e3a5f44';
            const prColor = d.severity === 'critical' ? '#dc2626' : d.severity === 'high' ? '#b45309' : '#6366f1';
            return (
              <div
                key={d.file}
                style={{
                  marginBottom: 8,
                  paddingBottom: 8,
                  borderBottom:
                    i < (result.ci_gate?.pr_diff_analysis?.length ?? 0) - 1 ? '1px solid var(--line)' : 'none',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <code style={{ fontSize: 10, background: 'var(--bg)', padding: '2px 5px', borderRadius: 4 }}>
                    {d.file}
                  </code>
                  <span style={{ color: '#ef4444', fontSize: 11 }}>+{d.size_delta_kb}KB</span>
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--muted)',
                    marginTop: 3,
                    display: 'flex',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>{d.impact}</span>
                  <span
                    style={{
                      borderRadius: 999,
                      padding: '1px 7px',
                      background: prBackground,
                      color: prColor,
                      fontSize: 10,
                    }}
                  >
                    {d.severity}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Gate history */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Recent Gate History</div>
          {(result.ci_gate?.gate_history ?? []).map((h, i) => (
            <div
              key={`gh-${i}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 12,
                marginBottom: 7,
              }}
            >
              <span style={{ fontWeight: 600 }}>{h.pr}</span>
              <span style={{ color: 'var(--muted)' }}>
                LCP Δ {(h.lcp_delta_ms ?? 0) > 0 ? '+' : ''}
                {h.lcp_delta_ms}ms
              </span>
              <span
                style={{
                  borderRadius: 999,
                  padding: '2px 9px',
                  fontSize: 10,
                  background: h.status === 'pass' ? '#14532d44' : h.status === 'fail' ? '#7f1d1d44' : '#78350f44',
                  color: h.status === 'pass' ? '#15803d' : h.status === 'fail' ? '#dc2626' : '#b45309',
                }}
              >
                {h.status?.toUpperCase()}
              </span>
              <span style={{ fontSize: 10, color: 'var(--muted)' }}>{h.merged ? 'merged' : 'blocked'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Bundle analysis */}
      {result.ci_gate?.bundle_analysis && (
        <div style={{ ...card, marginTop: 12 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Bundle Analysis</div>
          <div style={{ display: 'flex', gap: 16, fontSize: 12, flexWrap: 'wrap', marginBottom: 8 }}>
            <span>
              Total: <strong>{result.ci_gate.bundle_analysis.total_kb} KB</strong>
            </span>
            <span>
              PR Δ: <strong style={{ color: '#ef4444' }}>+{result.ci_gate.bundle_analysis.delta_kb} KB</strong>
            </span>
          </div>
          {(result.ci_gate.bundle_analysis.new_deps ?? []).length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>New dependencies added:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(result.ci_gate.bundle_analysis.new_deps ?? []).map((dep) => (
                  <code
                    key={dep}
                    style={{
                      fontSize: 11,
                      background: '#78350f22',
                      color: '#b45309',
                      borderRadius: 4,
                      padding: '3px 8px',
                    }}
                  >
                    {dep}
                  </code>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SloTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>SLO Guardrails</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Error budget burn rates, compliance trends and multi-window alert windows for CWV service-level objectives.
      </div>

      {/* Overall status */}
      <div
        style={{
          ...card,
          marginBottom: 16,
          borderLeft: `4px solid ${result.slo_guardrails?.overall === 'healthy' ? '#22c55e' : result.slo_guardrails?.overall === 'critical' ? '#ef4444' : '#f59e0b'}`,
        }}
      >
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              Overall:{' '}
              <span style={{ color: result.slo_guardrails?.overall === 'healthy' ? '#22c55e' : '#f59e0b' }}>
                {(result.slo_guardrails?.overall ?? 'unknown').toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
              7-day breach risk: <strong>{result.slo_guardrails?.breach_risk_next_7d ?? 'n/a'}</strong>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            {[
              { label: 'LCP Burn', value: result.slo_guardrails?.burn_rate?.lcp ?? 0 },
              { label: 'INP Burn', value: result.slo_guardrails?.burn_rate?.inp ?? 0 },
              { label: 'CLS Burn', value: result.slo_guardrails?.burn_rate?.cls ?? 0 },
            ].map((b) => (
              <div key={b.label} style={card}>
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>{b.label}</div>
                <div style={{ fontWeight: 800, fontSize: 20, color: b.value > 1 ? '#ef4444' : '#22c55e' }}>
                  {b.value}×
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Targets vs Current */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>SLO Targets vs Current</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', color: 'var(--muted)', fontSize: 11 }}>
                {['Metric', 'Target', 'Current', 'Δ', 'Status'].map((h) => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  metric: 'LCP P75',
                  target: `${result.slo_guardrails?.slo_targets?.lcp_p75_ms}ms`,
                  current: `${result.slo_guardrails?.current?.lcp_p75_ms}ms`,
                  delta:
                    (result.slo_guardrails?.current?.lcp_p75_ms ?? 0) -
                    (result.slo_guardrails?.slo_targets?.lcp_p75_ms ?? 0),
                  pass:
                    (result.slo_guardrails?.current?.lcp_p75_ms ?? 0) <=
                    (result.slo_guardrails?.slo_targets?.lcp_p75_ms ?? 0),
                },
                {
                  metric: 'INP P75',
                  target: `${result.slo_guardrails?.slo_targets?.inp_p75_ms}ms`,
                  current: `${result.slo_guardrails?.current?.inp_p75_ms}ms`,
                  delta:
                    (result.slo_guardrails?.current?.inp_p75_ms ?? 0) -
                    (result.slo_guardrails?.slo_targets?.inp_p75_ms ?? 0),
                  pass:
                    (result.slo_guardrails?.current?.inp_p75_ms ?? 0) <=
                    (result.slo_guardrails?.slo_targets?.inp_p75_ms ?? 0),
                },
                {
                  metric: 'CLS P75',
                  target: `${result.slo_guardrails?.slo_targets?.cls_p75}`,
                  current: `${result.slo_guardrails?.current?.cls_p75}`,
                  delta:
                    (result.slo_guardrails?.current?.cls_p75 ?? 0) - (result.slo_guardrails?.slo_targets?.cls_p75 ?? 0),
                  pass:
                    (result.slo_guardrails?.current?.cls_p75 ?? 0) <=
                    (result.slo_guardrails?.slo_targets?.cls_p75 ?? 0),
                },
                {
                  metric: 'Availability',
                  target: `${result.slo_guardrails?.slo_targets?.availability_pct}%`,
                  current: `${result.slo_guardrails?.current?.availability_pct}%`,
                  delta:
                    (result.slo_guardrails?.current?.availability_pct ?? 0) -
                    (result.slo_guardrails?.slo_targets?.availability_pct ?? 0),
                  pass:
                    (result.slo_guardrails?.current?.availability_pct ?? 0) >=
                    (result.slo_guardrails?.slo_targets?.availability_pct ?? 0),
                },
              ].map((row) => (
                <tr key={row.metric} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 10px', fontWeight: 600 }}>{row.metric}</td>
                  <td style={{ padding: '7px 10px', color: 'var(--muted)' }}>{row.target}</td>
                  <td style={{ padding: '7px 10px', fontWeight: 700, color: row.pass ? '#22c55e' : '#ef4444' }}>
                    {row.current}
                  </td>
                  <td style={{ padding: '7px 10px', color: row.pass ? '#22c55e' : '#ef4444' }}>
                    {row.delta > 0 ? '+' : ''}
                    {row.delta.toFixed(2)}
                  </td>
                  <td style={{ padding: '7px 10px' }}>
                    <span
                      style={{
                        borderRadius: 999,
                        padding: '2px 8px',
                        fontSize: 10,
                        background: row.pass ? '#14532d44' : '#7f1d1d44',
                        color: row.pass ? '#15803d' : '#dc2626',
                      }}
                    >
                      {row.pass ? 'OK' : 'BREACH'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
          gap: 12,
          marginBottom: 12,
        }}
      >
        {/* Error budget */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Error Budget Consumed</div>
          {(result.slo_guardrails?.error_budget ?? []).map((eb, i) => {
            const pct = Math.max(0, Math.min(120, 100 + (eb.remaining_pct ?? 0)));
            const over = (eb.remaining_pct ?? 0) < 0;
            return (
              <div key={`eb-${i}`} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600 }}>{eb.metric}</span>
                  <span style={{ color: over ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                    {over ? `${Math.abs(eb.remaining_pct ?? 0)}% over` : `${eb.remaining_pct}% remaining`}
                  </span>
                </div>
                <div style={{ height: 6, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, pct)}%`,
                      height: '100%',
                      background: over ? '#ef4444' : '#22c55e',
                      borderRadius: 3,
                    }}
                  />
                </div>
                <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>
                  {eb.consumed_mins}min consumed of {eb.budget_mins}min budget
                </div>
              </div>
            );
          })}
        </div>

        {/* Alert windows */}
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Multi-window Alert Status</div>
          {(result.slo_guardrails?.alert_windows ?? []).map((aw, i) => (
            <div
              key={`aw-${i}`}
              style={{
                ...card,
                padding: 8,
                marginBottom: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 12,
              }}
            >
              <span style={{ fontWeight: 700, width: 36 }}>{aw.window}</span>
              <span style={{ color: 'var(--muted)' }}>
                LCP: <strong style={{ color: (aw.lcp_burn ?? 0) > 1.5 ? '#ef4444' : '#f59e0b' }}>{aw.lcp_burn}×</strong>
              </span>
              <span style={{ color: 'var(--muted)' }}>
                INP: <strong style={{ color: (aw.inp_burn ?? 0) > 1.5 ? '#ef4444' : '#f59e0b' }}>{aw.inp_burn}×</strong>
              </span>
              <span
                style={{
                  borderRadius: 999,
                  padding: '2px 9px',
                  fontSize: 10,
                  background: aw.status === 'ok' ? '#14532d44' : aw.status === 'critical' ? '#7f1d1d44' : '#78350f44',
                  color: aw.status === 'ok' ? '#15803d' : aw.status === 'critical' ? '#dc2626' : '#b45309',
                }}
              >
                {aw.status?.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Breach scenarios */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Breach Scenarios</div>
        {(result.slo_guardrails?.breach_scenarios ?? []).map((bs, i) => (
          <div
            key={`bs-${i}`}
            style={{
              ...card,
              padding: 10,
              marginBottom: 8,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: 10,
              flexWrap: 'wrap',
              fontSize: 12,
              borderLeft: `3px solid ${(bs.probability ?? 0) > 0.6 ? '#ef4444' : '#f59e0b'}`,
            }}
          >
            <div>
              <strong>{bs.scenario}</strong>
              <div style={{ color: 'var(--muted)', marginTop: 2 }}>{bs.impact}</div>
            </div>
            <div style={{ fontWeight: 800, color: (bs.probability ?? 0) > 0.6 ? '#ef4444' : '#f59e0b', flexShrink: 0 }}>
              {((bs.probability ?? 0) * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function RoiTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Fix Priority ROI Matrix</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        Effort × impact quadrant ranking every optimization opportunity by revenue recovery, performance gain and
        engineering cost.
      </div>

      {/* Summary KPIs */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Total Fixes</div>
          <div style={{ fontWeight: 800, fontSize: 26 }}>{(result.roi_matrix ?? []).length}</div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Max Perf Gain</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#22c55e' }}>
            {(result.roi_matrix ?? []).reduce((s, r) => s + (r.estimated_gain_ms ?? 0), 0)}ms
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Max Revenue Recovery</div>
          <div style={{ fontWeight: 800, fontSize: 22, color: '#22c55e' }}>
            ${(result.roi_matrix ?? []).reduce((s, r) => s + (r.revenue_impact_usd ?? 0), 0).toLocaleString()}/mo
          </div>
        </div>
        <div style={card}>
          <div style={{ color: 'var(--muted)', fontSize: 11 }}>Sprint 1 Fixes</div>
          <div style={{ fontWeight: 800, fontSize: 26, color: '#6366f1' }}>
            {(result.roi_matrix ?? []).filter((r) => r.sprint === 1).length}
          </div>
        </div>
      </div>

      {/* Priority score bars */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Priority Ranking (by score)</div>
        <MiniBarChart
          items={[...(result.roi_matrix ?? [])]
            .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))
            .map((r) => ({
              label: r.title ?? '',
              value: r.priority_score ?? 0,
              max: 100,
              suffix: ` (${r.effort})`,
              color: (r.priority_score ?? 0) >= 85 ? '#22c55e' : (r.priority_score ?? 0) >= 70 ? '#f59e0b' : '#6366f1',
            }))}
        />
      </div>

      {/* Revenue gain bars */}
      <div style={{ ...card, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Revenue Impact per Fix ($/mo)</div>
        <MiniBarChart
          items={[...(result.roi_matrix ?? [])]
            .sort((a, b) => (b.revenue_impact_usd ?? 0) - (a.revenue_impact_usd ?? 0))
            .map((r) => ({
              label: r.title ?? '',
              value: r.revenue_impact_usd ?? 0,
              max: 5000,
              suffix: '/mo',
              color: '#22c55e',
            }))}
        />
      </div>

      {/* Sprint breakdown */}
      {[1, 2, 3].map((sprint) => {
        const sprintRows = (result.roi_matrix ?? []).filter((r) => r.sprint === sprint);
        if (!sprintRows.length) return null;
        return (
          <div key={`sprint-${sprint}`} style={{ ...card, marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
              Sprint {sprint}
              <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--muted)', fontWeight: 400 }}>
                {sprintRows.reduce((s, r) => s + (r.estimated_gain_ms ?? 0), 0)}ms total gain · $
                {sprintRows.reduce((s, r) => s + (r.revenue_impact_usd ?? 0), 0).toLocaleString()}/mo revenue
              </span>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {sprintRows.map((row, i) => (
                <div
                  key={`roi-s${sprint}-${i}`}
                  style={{
                    ...card,
                    padding: 10,
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto auto auto',
                    gap: 10,
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{row.title}</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 3 }}>
                      <span
                        style={{
                          fontSize: 10,
                          borderRadius: 999,
                          padding: '2px 8px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                        }}
                      >
                        {row.effort}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          borderRadius: 999,
                          padding: '2px 8px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                        }}
                      >
                        {row.category}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: 12 }}>
                    <div style={{ color: '#22c55e', fontWeight: 700 }}>-{row.estimated_gain_ms}ms</div>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>perf gain</div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: 12 }}>
                    <div style={{ color: '#22c55e', fontWeight: 700 }}>
                      ${(row.revenue_impact_usd ?? 0).toLocaleString()}
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>/mo</div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: 12 }}>
                    <div style={{ fontWeight: 700, color: (row.priority_score ?? 0) >= 85 ? '#22c55e' : '#f59e0b' }}>
                      {row.priority_score}
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>score</div>
                  </div>
                  <span
                    style={{
                      borderRadius: 999,
                      padding: '3px 9px',
                      fontSize: 10,
                      background:
                        row.impact_level === 'high'
                          ? '#14532d44'
                          : row.impact_level === 'medium'
                            ? '#78350f44'
                            : '#1e1b4b44',
                      color:
                        row.impact_level === 'high' ? '#15803d' : row.impact_level === 'medium' ? '#b45309' : '#6366f1',
                    }}
                  >
                    {row.impact_level}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CopilotTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>AI Performance Copilot</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
        AI-generated root-cause narrative, change attribution timeline, code-level hints and risk radar — all wired to
        your live CWV data.
      </div>

      {/* AI confidence + status */}
      <div style={{ ...card, marginBottom: 16 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>
              {result.performance_copilot?.summary ?? 'No summary'}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.6 }}>
              {result.performance_copilot?.narrative ?? ''}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <div
              style={{
                fontWeight: 800,
                fontSize: 28,
                color: (result.performance_copilot?.ai_confidence ?? 0) >= 80 ? '#22c55e' : '#f59e0b',
              }}
            >
              {result.performance_copilot?.ai_confidence ?? 0}%
            </div>
            <div style={{ fontSize: 10, color: 'var(--muted)' }}>AI confidence</div>
            {result.performance_copilot?.next_audit_eta && (
              <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 4 }}>
                Next audit: {new Date(result.performance_copilot.next_audit_eta).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* What changed / why / actions */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))',
          gap: 12,
          marginBottom: 16,
        }}
      >
        {[
          { title: 'What Changed', items: result.performance_copilot?.what_changed ?? [], color: '#6366f1' },
          { title: 'Why It Happened', items: result.performance_copilot?.why_it_happened ?? [], color: '#f59e0b' },
          {
            title: 'Recommended Actions',
            items: result.performance_copilot?.recommended_actions ?? [],
            color: '#22c55e',
          },
        ].map((section) => (
          <div key={section.title} style={card}>
            <div
              style={{
                fontWeight: 700,
                fontSize: 12,
                marginBottom: 8,
                borderBottom: `2px solid ${section.color}`,
                paddingBottom: 6,
              }}
            >
              {section.title}
            </div>
            {section.items.map((x, i) => (
              <div
                key={`${section.title}-${i}`}
                style={{ display: 'flex', gap: 6, alignItems: 'flex-start', fontSize: 12, marginBottom: 6 }}
              >
                <span style={{ color: section.color, flexShrink: 0 }}>›</span>
                <span>{x}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Change timeline */}
      {(result.performance_copilot?.change_timeline ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Performance Change Timeline</div>
          <div style={{ position: 'relative', paddingLeft: 20 }}>
            <div
              style={{
                position: 'absolute',
                left: 8,
                top: 0,
                bottom: 0,
                width: 2,
                background: 'var(--line)',
                borderRadius: 2,
              }}
            />
            {(result.performance_copilot?.change_timeline ?? []).map((ct, i) => (
              <div key={`ct-${i}`} style={{ position: 'relative', marginBottom: 14, paddingLeft: 12 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: -6,
                    top: 4,
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: ct.impact === 'positive' ? '#22c55e' : '#ef4444',
                    border: '2px solid var(--bg)',
                  }}
                />
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: 8,
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{ct.event}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>{ct.date}</div>
                  </div>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: ct.impact === 'positive' ? '#22c55e' : '#ef4444',
                      flexShrink: 0,
                    }}
                  >
                    {(ct.score_delta ?? 0) > 0 ? '+' : ''}
                    {ct.score_delta} score
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Code hints */}
      {(result.performance_copilot?.code_hints ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Code-level Hints</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {(result.performance_copilot?.code_hints ?? []).map((h, i) => (
              <div
                key={`ch-${i}`}
                style={{
                  ...card,
                  padding: 10,
                  borderLeft: `3px solid ${h.priority === 'critical' ? '#ef4444' : h.priority === 'high' ? '#f59e0b' : '#6366f1'}`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: 8,
                    flexWrap: 'wrap',
                    marginBottom: 4,
                  }}
                >
                  <code style={{ fontSize: 11, background: 'var(--bg)', padding: '2px 6px', borderRadius: 4 }}>
                    {h.file}
                  </code>
                  <span style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 11, flexShrink: 0 }}>
                    <span style={{ color: '#22c55e' }}>-{h.savings_ms}ms</span>
                    <span
                      style={{
                        borderRadius: 999,
                        padding: '2px 8px',
                        background:
                          h.priority === 'critical' ? '#7f1d1d44' : h.priority === 'high' ? '#78350f44' : '#1e1b4b44',
                        color: h.priority === 'critical' ? '#dc2626' : h.priority === 'high' ? '#b45309' : '#6366f1',
                      }}
                    >
                      {h.priority}
                    </span>
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{h.hint}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk radar */}
      {(result.performance_copilot?.risk_radar ?? []).length > 0 && (
        <div style={{ ...card, marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Risk Radar</div>
          {(result.performance_copilot?.risk_radar ?? []).map((r, i) => (
            <div key={`rr-${i}`} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span>
                  <strong>{r.area}</strong> — {r.risk}
                </span>
                <span style={{ color: (r.probability ?? 0) > 0.6 ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>
                  {((r.probability ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ height: 5, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${(r.probability ?? 0) * 100}%`,
                    height: '100%',
                    background: (r.probability ?? 0) > 0.6 ? '#ef4444' : '#f59e0b',
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Execution playbook */}
      {(result.execution_playbook?.now ?? []).length > 0 && (
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Execution Playbook</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', gap: 12 }}>
            {[
              { label: 'Now', items: result.execution_playbook?.now ?? [], color: '#ef4444' },
              { label: 'Next Sprint', items: result.execution_playbook?.next ?? [], color: '#f59e0b' },
              { label: 'Later', items: result.execution_playbook?.later ?? [], color: '#6366f1' },
            ].map((phase) => (
              <div key={phase.label}>
                <div
                  style={{
                    fontSize: 11,
                    color: phase.color,
                    fontWeight: 700,
                    marginBottom: 6,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  {phase.label}
                </div>
                {phase.items.map((x, i) => (
                  <div
                    key={`${phase.label}-${i}`}
                    style={{ fontSize: 12, marginBottom: 5, display: 'flex', gap: 6, alignItems: 'flex-start' }}
                  >
                    <span style={{ color: phase.color }}>•</span>
                    <span>{x}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function OpportunitiesTab({ result, card, isOfflinePreview, autoFixing, optimizeSite }: PerfTabProps) {
  return (
    <section style={card}>
      {/* Header + CTA */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Optimization Opportunities</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
            Ranked by priority score — effort vs impact vs revenue.
          </div>
        </div>
        <button
          type="button"
          onClick={optimizeSite}
          disabled={autoFixing}
          style={{ ...btn(true), background: '#6366f1', color: '#fff' }}
        >
          {autoFixing ? 'Applying...' : 'Fix All Automatically'}
        </button>
      </div>

      {/* Totals KPI strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          { label: 'Total Opportunities', value: String((result.opportunities ?? []).length), color: 'var(--text)' },
          {
            label: 'Total Gain',
            value: `${(result.opportunities ?? []).reduce((s, o) => s + (o.estimated_gain_ms ?? 0), 0)}ms`,
            color: '#22c55e',
          },
          {
            label: 'Revenue Potential',
            value: `$${(result.opportunities ?? []).reduce((s, o) => s + (o.revenue_gain_usd ?? 0), 0).toLocaleString()}/mo`,
            color: '#22c55e',
          },
          {
            label: 'Quick Wins (low effort)',
            value: String((result.opportunities ?? []).filter((o) => o.effort === 'low').length),
            color: '#6366f1',
          },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 20, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Gain bar chart */}
      <div style={{ ...card, marginBottom: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Performance Gain by Fix (ms)</div>
        <MiniBarChart
          items={(result.opportunities ?? []).map((o) => ({
            label: o.issue ?? '',
            value: o.estimated_gain_ms ?? 0,
            color: priorityColor(o.priority),
            suffix: 'ms',
            max: 300,
          }))}
        />
      </div>

      {/* Grouped by category */}
      {(() => {
        const byCategory = (result.opportunities ?? []).reduce<Record<string, typeof result.opportunities>>(
          (acc, o) => {
            const cat = o.category ?? 'Other';
            acc[cat] = [...(acc[cat] ?? []), o];
            return acc;
          },
          {}
        );
        return (
          <div style={{ display: 'grid', gap: 12 }}>
            {Object.entries(byCategory).map(([cat, items]) => (
              <div key={cat} style={card}>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}
                >
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{cat}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {(items ?? []).reduce((s, o) => s + (o.estimated_gain_ms ?? 0), 0)}ms total gain &nbsp;·&nbsp; $
                    {(items ?? []).reduce((s, o) => s + (o.revenue_gain_usd ?? 0), 0).toLocaleString()}/mo
                  </div>
                </div>
                <div style={{ display: 'grid', gap: 8 }}>
                  {(items ?? []).map((item, i) => (
                    <div
                      key={`opp-${cat}-${i}`}
                      style={{ ...card, padding: 12, borderLeft: `3px solid ${priorityColor(item.priority)}` }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          justifyContent: 'space-between',
                          gap: 10,
                          flexWrap: 'wrap',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <div
                            style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, flexWrap: 'wrap' }}
                          >
                            <span style={badge(priorityColor(item.priority))}>{item.priority ?? 'low'}</span>
                            <span
                              style={{
                                fontSize: 10,
                                borderRadius: 999,
                                padding: '2px 8px',
                                background: 'var(--bg)',
                                border: '1px solid var(--line)',
                              }}
                            >
                              {item.effort ?? 'medium'} effort
                            </span>
                            <span style={{ fontWeight: 700, fontSize: 13 }}>{item.issue}</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.impact}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexShrink: 0 }}>
                          {(item.estimated_gain_ms ?? 0) > 0 && (
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontWeight: 700, color: '#22c55e', fontSize: 13 }}>
                                -{item.estimated_gain_ms}ms
                              </div>
                              <div style={{ fontSize: 10, color: 'var(--muted)' }}>perf gain</div>
                            </div>
                          )}
                          {(item.revenue_gain_usd ?? 0) > 0 && (
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontWeight: 700, color: '#22c55e', fontSize: 13 }}>
                                ${(item.revenue_gain_usd ?? 0).toLocaleString()}
                              </div>
                              <div style={{ fontSize: 10, color: 'var(--muted)' }}>/mo revenue</div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        );
      })()}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AiFixesTab({
  result,
  card,
  isOfflinePreview,
  autoFixing,
  autoFixResult,
  fixingItem,
  fixedItems,
  fixSingleItem,
  optimizeSite,
}: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {/* Header + Apply All */}
      <div
        style={{
          ...card,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 10,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>AI Remediation Engine</div>
          {result.ai_remediation?.summary && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4, maxWidth: 600 }}>
              {result.ai_remediation.summary}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={optimizeSite}
          disabled={autoFixing}
          style={{ ...btn(true), background: '#6366f1', color: '#fff' }}
        >
          {autoFixing ? 'Optimizing...' : '⚡ Apply All Fixes'}
        </button>
      </div>

      {/* Before / after score projection */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Score Projection After All Fixes</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
          {[
            {
              label: 'Performance Score',
              current: result.performance_score ?? 62,
              projected: Math.min(100, (result.performance_score ?? 62) + 24),
            },
            { label: 'LCP', current: 3800, projected: 2432, suffix: 'ms', lowerBetter: true },
            {
              label: 'Total Gain',
              current: 0,
              projected: (result.ai_remediation?.auto_fix_candidates ?? []).reduce(
                (s, c) => s + (c.estimated_gain_ms ?? 0),
                0
              ),
              suffix: 'ms',
              gainOnly: true,
            },
            {
              label: 'Fixes Available',
              current: 0,
              projected: (result.ai_remediation?.auto_fix_candidates ?? []).length,
              gainOnly: true,
            },
          ].map((m) => (
            <div
              key={m.label}
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 10, padding: 12 }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 4 }}>{m.label}</div>
              {m.gainOnly ? (
                <div style={{ fontWeight: 800, fontSize: 22, color: '#22c55e' }}>
                  {m.projected}
                  {m.suffix ?? ''}
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span
                    style={{ fontWeight: 700, fontSize: 18, color: 'var(--muted)', textDecoration: 'line-through' }}
                  >
                    {m.current}
                    {m.suffix ?? ''}
                  </span>
                  <span style={{ fontWeight: 800, fontSize: 22, color: '#22c55e' }}>
                    → {m.projected}
                    {m.suffix ?? ''}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Fix-by-category bar chart */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Fixes by Category</div>
        <MiniBarChart
          items={(() => {
            const cats: Record<string, number> = {};
            (result.ai_remediation?.auto_fix_candidates ?? []).forEach((c) => {
              const cat = (c.verification ?? 'Other').split('_')[0];
              cats[cat] = (cats[cat] ?? 0) + 1;
            });
            const colors = ['#6366f1', '#22c55e', '#f59e0b', '#6366f1', '#ef4444', '#ec4899'];
            return Object.entries(cats).map(([k, v], i) => ({
              label: k,
              value: v,
              color: colors[i % colors.length],
              max: Math.max(...Object.values(cats)),
              suffix: ' fixes',
            }));
          })()}
        />
      </div>

      {/* Applied fixes result */}
      {autoFixResult && (
        <div style={{ ...card, background: '#14532d22', border: '1px solid #22c55e44' }}>
          <div style={{ fontWeight: 700, color: '#22c55e', marginBottom: 8 }}>Optimization Results</div>
          <div style={{ display: 'grid', gap: 6 }}>
            {autoFixResult.fixes_applied.map((fix) => (
              <div key={fix.fix_id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                <span style={{ color: fix.status === 'applied' ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                  {fix.status === 'applied' ? '✓' : '✗'}
                </span>
                <span style={{ flex: 1 }}>{fix.title}</span>
                {fix.actual_gain_ms > 0 && (
                  <span style={{ color: '#22c55e', fontWeight: 700 }}>-{fix.actual_gain_ms}ms</span>
                )}
                <span style={badge(fix.status === 'applied' ? '#22c55e' : '#ef4444')}>{fix.status}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 10, fontSize: 12, display: 'flex', gap: 16 }}>
            <div>
              Total gain: <strong style={{ color: '#22c55e' }}>{autoFixResult.total_gain_ms}ms</strong>
            </div>
            <div>
              New score: <strong style={{ color: '#22c55e' }}>{autoFixResult.new_performance_score}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Candidate list */}
      <div style={{ display: 'grid', gap: 10 }}>
        {(result.ai_remediation?.auto_fix_candidates ?? []).map((candidate, i) => {
          const isFixed = fixedItems.has(candidate.title ?? '');
          const isFixingThis = fixingItem === candidate.title;
          const confPct = Math.round((candidate.confidence ?? 0) * 100);
          const riskColor = confPct >= 90 ? '#22c55e' : confPct >= 70 ? '#f59e0b' : '#ef4444';
          const riskLabel = confPct >= 90 ? 'low-risk' : confPct >= 70 ? 'medium-risk' : 'high-risk';
          return (
            <div
              key={`${candidate.title}-${i}`}
              style={{ ...card, padding: 12, opacity: isFixed ? 0.55 : 1, borderLeft: `3px solid ${riskColor}` }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: 10,
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                    {isFixed && <span style={{ color: '#22c55e', fontWeight: 700, fontSize: 11 }}>✓ Fixed</span>}
                    <span style={{ fontWeight: 700, fontSize: 13 }}>{candidate.title}</span>
                    <span style={badge(riskColor)}>{riskLabel}</span>
                    <span style={badge('#6366f1')}>{candidate.verification ?? 'general'}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--muted)', flexWrap: 'wrap' }}>
                    <span>
                      Confidence: <strong style={{ color: riskColor }}>{confPct}%</strong>
                    </span>
                    <span>
                      Est. gain: <strong style={{ color: '#22c55e' }}>-{candidate.estimated_gain_ms ?? 0}ms</strong>
                    </span>
                    <span>Verify: {candidate.verification}</span>
                  </div>
                  <div
                    style={{ marginTop: 8, height: 5, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}
                  >
                    <div style={{ width: `${confPct}%`, height: '100%', background: riskColor, borderRadius: 3 }} />
                  </div>
                </div>
                {!isFixed && (
                  <button
                    type="button"
                    onClick={() => fixSingleItem(candidate)}
                    disabled={isFixingThis || !!fixingItem}
                    style={{ ...btn(), fontSize: 11, padding: '6px 12px' }}
                  >
                    {isFixingThis ? 'Fixing...' : 'Fix This'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Verification plan */}
      {(result.ai_remediation?.verification_plan ?? []).length > 0 && (
        <div style={card}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 12,
              marginBottom: 8,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Verification Plan
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(result.ai_remediation?.verification_plan ?? []).map((item) => (
              <span
                key={item}
                style={{
                  fontSize: 11,
                  borderRadius: 999,
                  padding: '5px 12px',
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                }}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ImagesTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Image Audit</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Format efficiency, LCP candidate analysis, alt text coverage, CDN delivery and bandwidth waste.
      </div>
      {result.image_audit ? (
        <div style={{ display: 'grid', gap: 14 }}>
          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
            {[
              { label: 'Total Images', value: String(result.image_audit.total_images ?? 0), color: 'var(--text)' },
              { label: 'Unoptimised', value: String(result.image_audit.unoptimized ?? 0), color: '#ef4444' },
              { label: 'Missing Alt', value: String(result.image_audit.missing_alt ?? 0), color: '#f59e0b' },
              {
                label: 'Bandwidth Wasted',
                value: `${result.image_audit.bandwidth_wasted_mb ?? 0} MB`,
                color: '#ef4444',
              },
              {
                label: 'Lazy Loaded',
                value: `${((result.image_audit.lazy_loaded_pct ?? 0) * 100).toFixed(0)}%`,
                color: '#6366f1',
              },
              {
                label: 'Next-gen Format',
                value: `${((result.image_audit.next_gen_adoption_pct ?? 0) * 100).toFixed(0)}%`,
                color: (result.image_audit.next_gen_adoption_pct ?? 0) >= 0.8 ? '#22c55e' : '#f59e0b',
              },
              {
                label: 'CDN Coverage',
                value: `${((result.image_audit.cdn_coverage_pct ?? 0) * 100).toFixed(0)}%`,
                color: '#6366f1',
              },
            ].map((kpi) => (
              <div key={kpi.label} style={card}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
                <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* LCP image callout */}
          {result.image_audit.lcp_image && (
            <div style={{ ...card, borderLeft: '3px solid #f59e0b', padding: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 4 }}>LCP Image Candidate</div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 10,
                  flexWrap: 'wrap',
                }}
              >
                <code style={{ fontSize: 11, color: '#f59e0b' }}>{result.image_audit.lcp_image}</code>
                <div style={{ display: 'flex', gap: 10, fontSize: 11 }}>
                  <span style={{ color: '#ef4444' }}>Missing fetchpriority=&quot;high&quot;</span>
                  <span>·</span>
                  <span style={{ color: '#f59e0b' }}>Serving JPEG — upgrade to AVIF</span>
                </div>
              </div>
            </div>
          )}

          {/* Savings table */}
          {(result.image_audit.oversized ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Compression Opportunities</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Asset', 'Format', 'Size', 'Recommend', 'Savings KB', 'Savings %', 'Decode', 'LCP'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '6px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.image_audit.oversized ?? []).map((img, i) => (
                      <tr key={`img-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td
                          style={{
                            padding: '7px 10px',
                            fontFamily: 'monospace',
                            fontSize: 11,
                            color: 'var(--muted)',
                            maxWidth: 180,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {img.url}
                        </td>
                        <td style={{ padding: '7px 10px' }}>
                          <span
                            style={{
                              borderRadius: 999,
                              padding: '2px 8px',
                              background: 'var(--bg)',
                              border: '1px solid var(--line)',
                              fontSize: 10,
                            }}
                          >
                            {img.format}
                          </span>
                        </td>
                        <td style={{ padding: '7px 10px', fontWeight: 700 }}>{img.size_kb} KB</td>
                        <td style={{ padding: '7px 10px', color: '#22c55e', fontWeight: 700 }}>
                          {img.recommended_format}
                        </td>
                        <td style={{ padding: '7px 10px', color: '#22c55e', fontWeight: 700 }}>-{img.savings_kb} KB</td>
                        <td style={{ padding: '7px 10px', color: '#22c55e' }}>{img.savings_pct}%</td>
                        <td style={{ padding: '7px 10px' }}>{img.decode_time_ms}ms</td>
                        <td style={{ padding: '7px 10px' }}>
                          {img.lcp_candidate ? <span style={{ color: '#f59e0b', fontWeight: 700 }}>LCP</span> : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Format breakdown + per-page audit side by side */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
            {Object.keys(result.image_audit.format_breakdown ?? {}).length > 0 && (
              <div style={card}>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Format Breakdown</div>
                <MiniBarChart
                  items={Object.entries(result.image_audit.format_breakdown ?? {}).map(([fmt, cnt]) => ({
                    label: fmt.toUpperCase(),
                    value: cnt,
                    color: fmt === 'webp' || fmt === 'avif' ? '#22c55e' : '#f59e0b',
                    max: result.image_audit?.total_images ?? 1,
                  }))}
                />
              </div>
            )}
            {(result.image_audit.per_page_audit ?? []).length > 0 && (
              <div style={card}>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Per-Page Audit</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Page', 'Images', 'Missing Alt', 'Unoptimised'].map((h) => (
                        <th
                          key={h}
                          style={{ textAlign: 'left', padding: '4px 8px', fontSize: 10, color: 'var(--muted)' }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.image_audit.per_page_audit ?? []).map((p, i) => (
                      <tr key={`pp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontSize: 11 }}>{p.page}</td>
                        <td style={{ padding: '6px 8px' }}>{p.count}</td>
                        <td
                          style={{
                            padding: '6px 8px',
                            color: (p.missing_alt ?? 0) > 0 ? '#f59e0b' : '#22c55e',
                            fontWeight: 700,
                          }}
                        >
                          {p.missing_alt}
                        </td>
                        <td
                          style={{
                            padding: '6px 8px',
                            color: (p.unoptimized ?? 0) > 0 ? '#ef4444' : '#22c55e',
                            fontWeight: 700,
                          }}
                        >
                          {p.unoptimized}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Issues */}
          {(result.image_audit.issues ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Issues</div>
              <div style={{ display: 'grid', gap: 6 }}>
                {(result.image_audit.issues ?? []).map((issue, i) => {
                  const col = severityColor(issue.severity);
                  return (
                    <div
                      key={`img-issue-${i}`}
                      style={{ ...card, padding: 10, borderLeft: `3px solid ${col}`, fontSize: 12 }}
                    >
                      <span style={badge(col)}>{issue.severity}</span>
                      <span style={{ marginLeft: 6 }}>{issue.message}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No image audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SecurityTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Security Audit</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Threat score, TLS strength, CSP directives, CORS policy, SRI coverage, cookies and known CVEs.
      </div>
      {result.security_audit ? (
        <div style={{ display: 'grid', gap: 14 }}>
          {/* Threat score banner */}
          <div
            style={{
              ...card,
              borderLeft: `4px solid ${(result.security_audit.threat_score ?? 0) >= 70 ? '#ef4444' : (result.security_audit.threat_score ?? 0) >= 40 ? '#f59e0b' : '#22c55e'}`,
              display: 'flex',
              alignItems: 'center',
              gap: 20,
              padding: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Threat Score</div>
              <div
                style={{
                  fontWeight: 900,
                  fontSize: 40,
                  lineHeight: 1,
                  color:
                    (result.security_audit.threat_score ?? 0) >= 70
                      ? '#ef4444'
                      : (result.security_audit.threat_score ?? 0) >= 40
                        ? '#f59e0b'
                        : '#22c55e',
                }}
              >
                {result.security_audit.threat_score ?? 0}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>/100</div>
            </div>
            <div
              style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))', gap: 8, flex: 1 }}
            >
              {[
                {
                  label: 'HTTPS',
                  value: result.security_audit.https ? 'Enabled' : 'Missing',
                  ok: !!result.security_audit.https,
                },
                {
                  label: 'Mixed Content',
                  value: `${result.security_audit.mixed_content_count ?? 0} issues`,
                  ok: (result.security_audit.mixed_content_count ?? 0) === 0,
                },
                {
                  label: 'CSP Score',
                  value: `${result.security_audit.csp_score ?? 0}/100`,
                  ok: (result.security_audit.csp_score ?? 0) >= 70,
                },
                {
                  label: 'SRI Coverage',
                  value: `${result.security_audit.subresource_integrity_pct ?? 0}%`,
                  ok: (result.security_audit.subresource_integrity_pct ?? 0) >= 80,
                },
              ].map((k) => (
                <div key={k.label} style={{ ...card, padding: 8 }}>
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{k.label}</div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: k.ok ? '#22c55e' : '#ef4444', marginTop: 2 }}>
                    {k.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* TLS info */}
          {result.security_audit.tls_info && (
            <div style={{ ...card, padding: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>TLS Configuration</div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}>
                <span>
                  Version: <strong>{result.security_audit.tls_info.version}</strong>
                </span>
                <span>
                  Cipher: <strong>{result.security_audit.tls_info.cipher}</strong>
                </span>
                {result.security_audit.tls_info.cert_expires && (
                  <span>
                    Cert Expires:{' '}
                    <strong>{new Date(result.security_audit.tls_info.cert_expires).toLocaleDateString()}</strong>
                  </span>
                )}
                <span>
                  Grade: <strong>{result.security_audit.tls_info.grade ?? '—'}</strong>
                </span>
              </div>
            </div>
          )}

          {/* Cookies table */}
          {result.security_audit.cookies && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
                Cookie Security ({result.security_audit.cookies.total} total)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 8 }}>
                {[
                  {
                    label: 'Secure flag',
                    val: result.security_audit.cookies.secure ?? 0,
                    total: result.security_audit.cookies.total ?? 0,
                    color: '#22c55e',
                  },
                  {
                    label: 'HttpOnly flag',
                    val: result.security_audit.cookies.httponly ?? 0,
                    total: result.security_audit.cookies.total ?? 0,
                    color: '#6366f1',
                  },
                  {
                    label: 'SameSite set',
                    val: result.security_audit.cookies.samesite ?? 0,
                    total: result.security_audit.cookies.total ?? 0,
                    color: '#6366f1',
                  },
                ].map((c) => {
                  const pct = Math.round((c.val / Math.max(c.total, 1)) * 100);
                  return (
                    <div key={c.label} style={card}>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>{c.label}</div>
                      <div style={{ fontWeight: 700, fontSize: 16, color: pct < 100 ? '#f59e0b' : c.color }}>
                        {c.val}/{c.total}
                      </div>
                      <div
                        style={{
                          marginTop: 4,
                          height: 4,
                          background: 'var(--line)',
                          borderRadius: 2,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${pct}%`,
                            height: '100%',
                            background: pct < 100 ? '#f59e0b' : c.color,
                            borderRadius: 2,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* CSP directives */}
          {(result.security_audit.csp_directives ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
                CSP Directives ({result.security_audit.csp_directives?.length ?? 0})
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['Directive', 'Value', 'Status', 'Risk'].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: 'left',
                          padding: '5px 10px',
                          fontSize: 10,
                          color: 'var(--muted)',
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.security_audit.csp_directives ?? []).map((d, i) => {
                    const riskColor = d.risk === 'high' ? '#ef4444' : d.risk === 'medium' ? '#f59e0b' : '#22c55e';
                    const statusColor =
                      d.status === 'missing' ? '#ef4444' : d.status === 'weak' ? '#f59e0b' : '#22c55e';
                    return (
                      <tr key={`csp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11, fontWeight: 700 }}>
                          {d.directive}
                        </td>
                        <td
                          style={{
                            padding: '6px 10px',
                            fontFamily: 'monospace',
                            fontSize: 10,
                            color: 'var(--muted)',
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {d.value ?? '—'}
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <span style={badge(statusColor)}>{d.status}</span>
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <span style={badge(riskColor)}>{d.risk}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* CORS issues */}
          {(result.security_audit.cors_issues ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>CORS Policy Issues</div>
              {(result.security_audit.cors_issues ?? []).map((c, i) => {
                const rc = c.risk === 'high' ? '#ef4444' : c.risk === 'medium' ? '#f59e0b' : '#22c55e';
                return (
                  <div
                    key={`cors-${i}`}
                    style={{ ...card, padding: 10, borderLeft: `3px solid ${rc}`, marginBottom: 8 }}
                  >
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, flexWrap: 'wrap' }}>
                      <span style={badge(rc)}>{c.risk}</span>
                      <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{c.endpoint}</span>
                      <span
                        style={{
                          fontSize: 10,
                          borderRadius: 999,
                          padding: '2px 8px',
                          background: 'var(--bg)',
                          border: '1px solid var(--line)',
                        }}
                      >
                        {c.method}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{c.issue}</div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Missing SRI */}
          {(result.security_audit.sri_missing ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
                Missing Subresource Integrity ({result.security_audit.sri_missing?.length})
              </div>
              <div style={{ display: 'grid', gap: 4 }}>
                {(result.security_audit.sri_missing ?? []).map((s, i) => (
                  <div
                    key={`sri-${i}`}
                    style={{
                      padding: '5px 10px',
                      background: '#7f1d1d22',
                      border: '1px solid #ef444433',
                      borderRadius: 6,
                      fontFamily: 'monospace',
                      fontSize: 11,
                      color: '#dc2626',
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* HTTP Headers */}
          {Object.keys(result.security_audit.headers ?? {}).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>HTTP Security Headers</div>
              <div style={{ display: 'grid', gap: 6 }}>
                {Object.entries(result.security_audit.headers ?? {}).map(([name, hdr]) => {
                  const col = headerColor(hdr.present, hdr.severity);
                  return (
                    <div
                      key={name}
                      style={{
                        ...card,
                        padding: '8px 12px',
                        display: 'grid',
                        gridTemplateColumns: '1fr auto auto',
                        alignItems: 'center',
                        gap: 10,
                        fontSize: 12,
                      }}
                    >
                      <div style={{ fontFamily: 'monospace', fontSize: 11 }}>{name}</div>
                      {hdr.present && hdr.value && (
                        <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'monospace' }}>{hdr.value}</div>
                      )}
                      <span style={badge(col)}>{hdr.present ? 'present' : 'missing'}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Vulnerabilities */}
          {(result.security_audit.vulnerabilities ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Vulnerabilities</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.security_audit.vulnerabilities ?? []).map((v, i) => {
                  const col = severityColor(v.severity);
                  return (
                    <div key={`sec-vuln-${i}`} style={{ ...card, padding: 12, borderLeft: `3px solid ${col}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <span style={badge(col)}>{v.severity}</span>
                        {v.cve && (
                          <span
                            style={{
                              fontFamily: 'monospace',
                              fontSize: 10,
                              borderRadius: 4,
                              padding: '2px 6px',
                              background: '#1e1b4b44',
                              color: '#6366f1',
                            }}
                          >
                            {v.cve}
                          </span>
                        )}
                        <span style={{ fontWeight: 700, fontSize: 13 }}>{v.issue}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{v.detail}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No security audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function JavascriptTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>JavaScript Audit</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Bundle size, coverage, tree-shaking, main thread cost, long tasks and blocking scripts.
      </div>
      {result.js_audit ? (
        <div style={{ display: 'grid', gap: 14 }}>
          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
            {[
              { label: 'Total JS', value: `${result.js_audit.total_kb ?? 0} KB`, color: 'var(--text)' },
              { label: 'Unused JS', value: `${result.js_audit.unused_kb ?? 0} KB`, color: '#ef4444' },
              { label: 'Unused %', value: `${(result.js_audit.unused_pct ?? 0).toFixed(1)}%`, color: '#ef4444' },
              { label: 'Parse Time', value: `${result.js_audit.parse_time_ms ?? 0}ms`, color: '#f59e0b' },
              { label: 'Exec Time', value: `${result.js_audit.execution_time_ms ?? 0}ms`, color: '#f59e0b' },
              { label: 'Third-party JS', value: `${result.js_audit.third_party_kb ?? 0} KB`, color: '#6366f1' },
              {
                label: 'Main Thread Cost',
                value: `${result.js_audit.main_thread_cost_ms ?? 0}ms`,
                color: (result.js_audit.main_thread_cost_ms ?? 0) > 1500 ? '#ef4444' : '#22c55e',
              },
            ].map((kpi) => (
              <div key={kpi.label} style={card}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
                <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* Compression savings */}
          {result.js_audit.compression && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Compression Savings</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 8 }}>
                {[
                  { label: 'Raw', value: result.js_audit.compression.raw_kb, color: '#ef4444' },
                  { label: 'Gzip', value: result.js_audit.compression.gzip_kb, color: '#f59e0b' },
                  { label: 'Brotli', value: result.js_audit.compression.brotli_kb, color: '#22c55e' },
                ].map((c) => {
                  const rawKb = result.js_audit?.compression?.raw_kb ?? 1;
                  const pct = Math.round(((c.value ?? 0) / Math.max(rawKb, 1)) * 100); // NOSONAR
                  return (
                    <div key={c.label} style={card}>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>{c.label}</div>
                      <div style={{ fontWeight: 700, fontSize: 16, color: c.color }}>{c.value} KB</div>
                      <div
                        style={{
                          marginTop: 4,
                          height: 4,
                          background: 'var(--line)',
                          borderRadius: 2,
                          overflow: 'hidden',
                        }}
                      >
                        <div style={{ width: `${pct}%`, height: '100%', background: c.color, borderRadius: 2 }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Bundle modules */}
          {(result.js_audit.bundle_modules ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
                Bundle Modules (tree-shaking analysis)
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Module', 'Size KB', 'Unused %', 'Tree-shakeable', 'Type'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.js_audit.bundle_modules ?? []).map((m, i) => (
                      <tr key={`mod-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11 }}>{m.module}</td>
                        <td style={{ padding: '6px 10px', fontWeight: 700 }}>{m.size_kb}</td>
                        <td style={{ padding: '6px 10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div
                              style={{
                                width: 60,
                                height: 4,
                                background: 'var(--line)',
                                borderRadius: 2,
                                overflow: 'hidden',
                                flexShrink: 0,
                              }}
                            >
                              <div
                                style={{
                                  width: `${m.unused_pct ?? 0}%`,
                                  height: '100%',
                                  background: (m.unused_pct ?? 0) > 50 ? '#ef4444' : '#f59e0b',
                                  borderRadius: 2,
                                }}
                              />
                            </div>
                            <span style={{ color: (m.unused_pct ?? 0) > 50 ? '#ef4444' : 'var(--text)' }}>
                              {m.unused_pct}%
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <span style={{ color: m.tree_shakeable ? '#22c55e' : '#ef4444' }}>
                            {m.tree_shakeable ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <span
                            style={{
                              borderRadius: 999,
                              padding: '2px 8px',
                              background: 'var(--bg)',
                              border: '1px solid var(--line)',
                              fontSize: 10,
                            }}
                          >
                            {m.type}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Long tasks */}
          {(result.js_audit.long_tasks ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Long Tasks (blocking main thread)</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.js_audit.long_tasks ?? []).map((t, i) => (
                  <div key={`lt-${i}`} style={{ ...card, padding: 10 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 6,
                        gap: 8,
                        flexWrap: 'wrap',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700 }}>{t.task}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                          Culprit: {t.culprit} · starts at {t.start_ms}ms
                        </div>
                      </div>
                      <span style={{ color: '#ef4444', fontWeight: 700, fontSize: 13 }}>{t.duration_ms}ms</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--line)', borderRadius: 2, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${Math.min((t.duration_ms ?? 0) / 5, 100)}%`,
                          height: '100%',
                          background: '#ef4444',
                          borderRadius: 2,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Blocking scripts + opportunities */}
          {(result.js_audit.blocking_scripts ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Render-Blocking Scripts</div>
              <div style={{ display: 'grid', gap: 4 }}>
                {(result.js_audit.blocking_scripts ?? []).map((s) => (
                  <div
                    key={s}
                    style={{
                      padding: '6px 10px',
                      background: '#7f1d1d22',
                      border: '1px solid #ef444444',
                      borderRadius: 6,
                      fontSize: 12,
                      color: '#dc2626',
                      fontFamily: 'monospace',
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}
          {(result.js_audit.opportunities ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Optimisation Opportunities</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.js_audit.opportunities ?? []).map((op, i) => (
                  <div
                    key={`jsop-${i}`}
                    style={{
                      ...card,
                      padding: 10,
                      display: 'grid',
                      gridTemplateColumns: '1fr auto auto',
                      alignItems: 'center',
                      gap: 10,
                      fontSize: 12,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{op.title}</div>
                    {(op.savings_kb ?? 0) > 0 && <div style={{ color: '#22c55e' }}>↓{op.savings_kb} KB</div>}
                    {(op.savings_ms ?? 0) > 0 && <div style={{ color: '#6366f1' }}>-{op.savings_ms}ms</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No JavaScript audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CssTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>CSS Audit</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Unused coverage, file-level breakdown, render-blocking sheets, animation jank risks and critical inline %.
      </div>
      {result.css_audit ? (
        <div style={{ display: 'grid', gap: 14 }}>
          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))', gap: 10 }}>
            {[
              { label: 'Total CSS', value: `${result.css_audit.total_kb ?? 0} KB`, color: 'var(--text)' },
              { label: 'Unused CSS', value: `${result.css_audit.unused_kb ?? 0} KB`, color: '#f59e0b' },
              { label: 'Unused %', value: `${(result.css_audit.unused_pct ?? 0).toFixed(1)}%`, color: '#f59e0b' },
              { label: 'Critical Path', value: `${result.css_audit.critical_path_kb ?? 0} KB`, color: 'var(--text)' },
              {
                label: 'Critical Inline',
                value: `${result.css_audit.critical_inline_pct ?? 0}%`,
                color: (result.css_audit.critical_inline_pct ?? 0) >= 60 ? '#22c55e' : '#f59e0b',
              },
              { label: 'Selectors', value: String(result.css_audit.selector_count ?? 0), color: 'var(--text)' },
              { label: 'Rules', value: String(result.css_audit.rule_count ?? 0), color: 'var(--text)' },
              {
                label: '@font-face',
                value: String(result.css_audit.font_face_count ?? 0),
                color: (result.css_audit.font_face_count ?? 0) > 6 ? '#f59e0b' : 'var(--text)',
              },
              {
                label: 'Blocking Files',
                value: String((result.css_audit.render_blocking ?? []).length),
                color: (result.css_audit.render_blocking ?? []).length > 0 ? '#ef4444' : '#22c55e',
              },
            ].map((kpi) => (
              <div key={kpi.label} style={card}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
                <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* Critical inline % progress */}
          <div style={card}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>Critical CSS Inlined</div>
            <div style={{ height: 8, background: 'var(--line)', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${result.css_audit.critical_inline_pct ?? 0}%`,
                  height: '100%',
                  background: (result.css_audit.critical_inline_pct ?? 0) >= 60 ? '#22c55e' : '#f59e0b',
                  borderRadius: 4,
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
              {result.css_audit.critical_inline_pct ?? 0}% critical CSS inlined — target ≥60%
            </div>
          </div>

          {/* File breakdown table */}
          {(result.css_audit.file_breakdown ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>File Breakdown</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['File', 'Total KB', 'Unused KB', 'Unused %', 'Render-Blocking'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.css_audit.file_breakdown ?? []).map((f, i) => (
                      <tr key={`cssf-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11 }}>{f.file}</td>
                        <td style={{ padding: '6px 10px', fontWeight: 700 }}>{f.total_kb}</td>
                        <td style={{ padding: '6px 10px', color: '#f59e0b' }}>{f.unused_kb}</td>
                        <td style={{ padding: '6px 10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div
                              style={{
                                width: 60,
                                height: 4,
                                background: 'var(--line)',
                                borderRadius: 2,
                                overflow: 'hidden',
                              }}
                            >
                              <div
                                style={{
                                  width: `${f.unused_pct ?? 0}%`,
                                  height: '100%',
                                  background: (f.unused_pct ?? 0) > 60 ? '#ef4444' : '#f59e0b',
                                  borderRadius: 2,
                                }}
                              />
                            </div>
                            <span>{f.unused_pct}%</span>
                          </div>
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          {f.render_blocking ? (
                            <span style={badge('#ef4444')}>Blocking</span>
                          ) : (
                            <span style={{ color: '#22c55e' }}>No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Animation jank risks */}
          {(result.css_audit.animation_jank_risks ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Animation Jank Risks</div>
              <div style={{ display: 'grid', gap: 6 }}>
                {(result.css_audit.animation_jank_risks ?? []).map((r, i) => (
                  <div
                    key={`jank-${i}`}
                    style={{ ...card, padding: 10, borderLeft: '3px solid #f59e0b', fontSize: 12 }}
                  >
                    <span style={badge('#f59e0b')}>jank</span>
                    <span style={{ marginLeft: 8 }}>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Render-blocking + opportunities */}
          {(result.css_audit.render_blocking ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Render-Blocking Stylesheets</div>
              <div style={{ display: 'grid', gap: 4 }}>
                {(result.css_audit.render_blocking ?? []).map((s) => (
                  <div
                    key={s}
                    style={{
                      padding: '6px 10px',
                      background: '#7f1d1d22',
                      border: '1px solid #ef444444',
                      borderRadius: 6,
                      fontSize: 12,
                      color: '#dc2626',
                      fontFamily: 'monospace',
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}
          {(result.css_audit.opportunities ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Optimisation Opportunities</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.css_audit.opportunities ?? []).map((op, i) => (
                  <div
                    key={`cssop-${i}`}
                    style={{
                      ...card,
                      padding: 10,
                      display: 'grid',
                      gridTemplateColumns: '1fr auto auto',
                      alignItems: 'center',
                      gap: 10,
                      fontSize: 12,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{op.title}</div>
                    {(op.savings_kb ?? 0) > 0 && <div style={{ color: '#22c55e' }}>↓{op.savings_kb} KB</div>}
                    {(op.savings_ms ?? 0) > 0 && <div style={{ color: '#6366f1' }}>-{op.savings_ms}ms</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No CSS audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function InputValidationTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={card}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Input Validation Audit</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        OWASP Top-10 coverage, form-level CSRF/server-validation audit, sanitization % and open-redirect risks.
      </div>
      {result.input_validation_audit ? (
        <div style={{ display: 'grid', gap: 14 }}>
          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
            {[
              {
                label: 'Forms Found',
                value: String(result.input_validation_audit.forms_found ?? 0),
                color: 'var(--text)',
              },
              {
                label: 'CSRF Protected',
                value: `${result.input_validation_audit.csrf_protected ?? 0}/${result.input_validation_audit.forms_found ?? 0}`,
                color:
                  (result.input_validation_audit.csrf_protected ?? 0) ===
                  (result.input_validation_audit.forms_found ?? 0)
                    ? '#22c55e'
                    : '#f59e0b',
              },
              {
                label: 'Server Validated',
                value: `${result.input_validation_audit.server_side_validated ?? 0}/${result.input_validation_audit.forms_found ?? 0}`,
                color: '#6366f1',
              },
              {
                label: 'Sanitization %',
                value: `${result.input_validation_audit.sanitization_pct ?? 0}%`,
                color: (result.input_validation_audit.sanitization_pct ?? 0) >= 80 ? '#22c55e' : '#f59e0b',
              },
              {
                label: 'XSS Risks',
                value: String(result.input_validation_audit.xss_risks ?? 0),
                color: (result.input_validation_audit.xss_risks ?? 0) > 0 ? '#ef4444' : '#22c55e',
              },
              {
                label: 'Injection Risks',
                value: String(result.input_validation_audit.injection_risks ?? 0),
                color: (result.input_validation_audit.injection_risks ?? 0) > 0 ? '#ef4444' : '#22c55e',
              },
              {
                label: 'Open Redirects',
                value: String(result.input_validation_audit.open_redirect_risks ?? 0),
                color: (result.input_validation_audit.open_redirect_risks ?? 0) > 0 ? '#ef4444' : '#22c55e',
              },
            ].map((kpi) => (
              <div key={kpi.label} style={card}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
                <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* OWASP Coverage table */}
          {(result.input_validation_audit.owasp_coverage ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>OWASP Top-10 Coverage</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['ID', 'Vulnerability', 'Status', 'Risk Level'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.input_validation_audit.owasp_coverage ?? []).map((o, i) => {
                      const statusCol = o.status === 'pass' ? '#22c55e' : o.status === 'warn' ? '#f59e0b' : '#ef4444';
                      const riskCol =
                        o.risk_level === 'critical'
                          ? '#ef4444'
                          : o.risk_level === 'high'
                            ? '#f97316'
                            : o.risk_level === 'medium'
                              ? '#f59e0b'
                              : '#22c55e';
                      return (
                        <tr key={`owasp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11, fontWeight: 700 }}>
                            {o.id}
                          </td>
                          <td style={{ padding: '6px 10px' }}>{o.name}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={badge(statusCol)}>{o.status}</span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={badge(riskCol)}>{o.risk_level}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Form audit table */}
          {(result.input_validation_audit.form_audit ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Form-by-Form Audit</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Form ID', 'Action', 'CSRF', 'Client Val.', 'Server Val.', 'Inputs', 'Risk'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.input_validation_audit.form_audit ?? []).map((f, i) => {
                      const rc = f.risk === 'high' ? '#ef4444' : f.risk === 'medium' ? '#f59e0b' : '#22c55e';
                      return (
                        <tr key={`form-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11 }}>{f.form_id}</td>
                          <td
                            style={{
                              padding: '6px 10px',
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: 'var(--muted)',
                            }}
                          >
                            {f.action}
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={{ color: f.csrf ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                              {f.csrf ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={{ color: f.client_val ? '#22c55e' : '#f59e0b' }}>
                              {f.client_val ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={{ color: f.server_val ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                              {f.server_val ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>{f.inputs}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={badge(rc)}>{f.risk}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Field issues */}
          {(result.input_validation_audit.issues ?? []).length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Field-level Issues</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.input_validation_audit.issues ?? []).map((issue, i) => {
                  const col = severityColor(issue.severity);
                  return (
                    <div key={`iv-${i}`} style={{ ...card, padding: 12, borderLeft: `3px solid ${col}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <span style={badge(col)}>{issue.severity}</span>
                        <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--muted)' }}>
                          {issue.name}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--muted)' }}>({issue.type})</span>
                      </div>
                      <div style={{ fontSize: 12 }}>{issue.issue}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No input validation audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LatencyTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {result.latency_audit ? (
        <>
          {/* Cache + Compression row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
            {result.latency_audit.cache_stats && (
              <div
                style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
              >
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Cache Performance</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
                  {[
                    {
                      label: 'Hit Rate',
                      value: `${((result.latency_audit.cache_stats.hit_rate ?? 0) * 100).toFixed(0)}%`,
                      color: (result.latency_audit.cache_stats.hit_rate ?? 0) >= 0.8 ? '#22c55e' : '#f59e0b',
                    },
                    {
                      label: 'Miss Penalty',
                      value: `${result.latency_audit.cache_stats.miss_penalty_ms ?? 0}ms`,
                      color: '#ef4444',
                    },
                    {
                      label: 'Stale Rate',
                      value: `${((result.latency_audit.cache_stats.stale_rate ?? 0) * 100).toFixed(0)}%`,
                      color: '#f59e0b',
                    },
                    {
                      label: 'Cache-Control',
                      value:
                        result.latency_audit.cache_stats.stale_rate != null
                          ? `${Math.round((1 - (result.latency_audit.cache_stats.stale_rate ?? 0)) * 100)}% valid`
                          : '—',
                      color: 'var(--text)',
                    }, // NOSONAR
                  ].map((c) => (
                    <div
                      key={c.label}
                      style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 8 }}
                    >
                      <div style={{ fontSize: 10, color: 'var(--muted)' }}>{c.label}</div>
                      <div style={{ fontWeight: 700, fontSize: 16, color: c.color }}>{c.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {result.latency_audit.compression_stats && (
              <div
                style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
              >
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Compression Coverage</div>
                <MiniBarChart
                  items={[
                    {
                      label: 'Brotli',
                      value: result.latency_audit.compression_stats.brotli_pct ?? 0,
                      color: '#22c55e',
                      max: 100,
                      suffix: '%',
                    },
                    {
                      label: 'Gzip',
                      value: result.latency_audit.compression_stats.gzip_pct ?? 0,
                      color: '#6366f1',
                      max: 100,
                      suffix: '%',
                    },
                    {
                      label: 'None',
                      value: result.latency_audit.compression_stats.none_pct ?? 0,
                      color: '#ef4444',
                      max: 100,
                      suffix: '%',
                    },
                  ]}
                />
              </div>
            )}
          </div>

          {/* Waterfall */}
          {(result.latency_audit.waterfall ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Request Waterfall</div>
              {(() => {
                const wf = result.latency_audit?.waterfall ?? [];
                const maxEnd = Math.max(...wf.map((e) => (e.start_ms ?? 0) + (e.duration_ms ?? 0)));
                return wf.map((entry, i) => {
                  const startPct = ((entry.start_ms ?? 0) / maxEnd) * 100;
                  const widthPct = ((entry.duration_ms ?? 0) / maxEnd) * 100;
                  const typeColor: Record<string, string> = {
                    document: '#6366f1',
                    script: '#f59e0b',
                    css: '#6366f1',
                    image: '#22c55e',
                    font: '#a855f7',
                    api: '#f97316',
                  };
                  const col = typeColor[entry.type ?? 'api'] ?? 'var(--muted)';
                  return (
                    <div key={`wf-${i}`} style={{ marginBottom: 6 }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 10,
                          color: 'var(--muted)',
                          marginBottom: 2,
                        }}
                      >
                        <span
                          style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            maxWidth: '55%',
                          }}
                        >
                          {entry.name}
                        </span>
                        <span>
                          {entry.duration_ms}ms · {entry.size_kb}KB
                        </span>
                      </div>
                      <div
                        style={{
                          height: 8,
                          background: 'var(--line)',
                          borderRadius: 2,
                          overflow: 'hidden',
                          position: 'relative',
                        }}
                      >
                        <div
                          style={{
                            position: 'absolute',
                            left: `${startPct}%`,
                            width: `${widthPct}%`,
                            height: '100%',
                            background: col,
                            borderRadius: 2,
                          }}
                        />
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          )}

          {/* Percentile cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 12 }}>
            {[
              { title: 'Overall Request', key: 'overall', threshold: 2500 },
              { title: 'DNS', key: 'dns', threshold: 100 },
              { title: 'TCP Handshake', key: 'tcp', threshold: 200 },
              { title: 'TLS Negotiation', key: 'tls', threshold: 300 },
              { title: 'TTFB', key: 'ttfb', threshold: 600 },
              { title: 'LCP', key: 'lcp', threshold: 2500 },
              { title: 'FCP', key: 'fcp', threshold: 1800 },
              { title: 'CDN Edge', key: 'cdn_edge_latency', threshold: 50 },
            ].map(({ title, key, threshold }) => {
              const d = result.latency_audit?.[key as keyof LatencyAudit] as LatencyPercentiles | undefined;
              return (
                <div
                  key={key}
                  style={{
                    background: 'var(--bg-soft)',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    padding: 14,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 10 }}>{title}</div>
                  <LatencyPercentileBar p50={d?.p50} p75={d?.p75} p95={d?.p95} p99={d?.p99} threshold={threshold} />
                </div>
              );
            })}
          </div>

          {(result.latency_audit.endpoints ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>API Endpoint Latency</div>
              <div style={{ display: 'grid', gap: 10 }}>
                {(result.latency_audit.endpoints ?? []).map((ep, i) => (
                  <div key={`ep-${i}`} style={{ borderBottom: '1px solid var(--line)', paddingBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12 }}>
                      <span style={{ fontWeight: 700 }}>
                        <span style={{ color: '#6366f1', marginRight: 6 }}>{ep.method}</span>
                        {ep.url}
                      </span>
                      <span style={{ color: (ep.error_rate ?? 0) > 0.01 ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                        err {((ep.error_rate ?? 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <LatencyPercentileBar p50={ep.p50} p75={ep.p75} p95={ep.p95} p99={ep.p99} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {(result.latency_audit.db_query_distribution ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>DB Query Distribution</div>
              <MiniBarChart
                items={(result.latency_audit.db_query_distribution ?? []).map((q) => ({
                  label: (q.query ?? '').slice(0, 28),
                  value: q.p95 ?? 0,
                  color: (q.p95 ?? 0) > 100 ? '#f97316' : '#6366f1',
                  suffix: 'ms p95',
                }))}
              />
            </div>
          )}
        </>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No latency audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function OutdatedTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {result.outdated_audit ? (
        <>
          {/* Security risk banner */}
          <div
            style={{
              background: 'var(--bg-soft)',
              border: '1px solid var(--line)',
              borderRadius: 12,
              padding: 14,
              display: 'flex',
              gap: 20,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Security Risk Score</div>
              <div
                style={{
                  fontWeight: 900,
                  fontSize: 44,
                  lineHeight: 1,
                  color: (result.outdated_audit.security_risk_score ?? 0) >= 60 ? '#ef4444' : '#f59e0b',
                }}
              >
                {result.outdated_audit.security_risk_score ?? 0}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>/100</div>
            </div>
            <div
              style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 130px), 1fr))', gap: 8, flex: 1 }}
            >
              {[
                { label: 'Total Deps', value: result.outdated_audit.total_deps ?? 0, color: 'var(--text)' },
                { label: 'Outdated', value: result.outdated_audit.outdated_count ?? 0, color: '#f59e0b' },
                { label: 'Critical', value: result.outdated_audit.critical_outdated ?? 0, color: '#ef4444' },
                { label: 'CVEs Found', value: result.outdated_audit.cve_count ?? 0, color: '#ef4444' },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 8 }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
                  <div style={{ fontWeight: 700, fontSize: 20, color: kpi.color }}>{kpi.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* CVE table */}
          {(result.outdated_audit.cves ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Known CVEs</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Package', 'CVE ID', 'Severity', 'CVSS', 'Patched in'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.outdated_audit.cves ?? []).map((c, i) => {
                      const sc =
                        c.severity === 'critical'
                          ? '#ef4444'
                          : c.severity === 'high'
                            ? '#f97316'
                            : c.severity === 'medium'
                              ? '#f59e0b'
                              : '#22c55e';
                      return (
                        <tr key={`cve-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11, fontWeight: 700 }}>
                            {c.pkg}
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span
                              style={{
                                fontFamily: 'monospace',
                                fontSize: 10,
                                borderRadius: 4,
                                padding: '2px 6px',
                                background: '#1e1b4b44',
                                color: '#6366f1',
                              }}
                            >
                              {c.cve}
                            </span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={badge(sc)}>{c.severity}</span>
                          </td>
                          <td style={{ padding: '6px 10px', fontWeight: 700, color: sc }}>{c.cvss}</td>
                          <td style={{ padding: '6px 10px', color: '#22c55e', fontFamily: 'monospace', fontSize: 11 }}>
                            {c.patched_in}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Upgrade matrix */}
          {(result.outdated_audit.upgrade_matrix ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Upgrade Effort Matrix</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['Package', 'From', 'To', 'Breaking Changes', 'Effort', 'Security Fix'].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: 'left',
                            padding: '5px 10px',
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 600,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(result.outdated_audit.upgrade_matrix ?? []).map((u, i) => {
                      const effortColor =
                        u.effort === 'high' ? '#ef4444' : u.effort === 'medium' ? '#f59e0b' : '#22c55e';
                      return (
                        <tr key={`um-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11, fontWeight: 700 }}>
                            {u.name}
                          </td>
                          <td
                            style={{
                              padding: '6px 10px',
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: 'var(--muted)',
                            }}
                          >
                            {u.from_ver}
                          </td>
                          <td
                            style={{
                              padding: '6px 10px',
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: '#22c55e',
                              fontWeight: 700,
                            }}
                          >
                            {u.to_ver}
                          </td>
                          <td
                            style={{
                              padding: '6px 10px',
                              color: (u.breaking_changes ?? 0) > 0 ? '#f59e0b' : '#22c55e',
                            }}
                          >
                            {u.breaking_changes}
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            <span style={badge(effortColor)}>{u.effort}</span>
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            {u.security_fix ? <span style={{ color: '#22c55e', fontWeight: 700 }}>Yes</span> : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Dependencies list */}
          <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>All Outdated Dependencies</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.outdated_audit.deps ?? []).map((d, i) => (
                <div
                  key={`dep-${i}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto auto',
                    gap: 10,
                    alignItems: 'center',
                    fontSize: 12,
                    borderBottom: '1px solid var(--line)',
                    paddingBottom: 6,
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 700 }}>{d.name}</span>
                    <span style={{ color: 'var(--muted)', marginLeft: 6, fontSize: 10 }}>({d.type})</span>
                    {d.has_cve && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontFamily: 'monospace',
                          fontSize: 10,
                          borderRadius: 4,
                          padding: '1px 5px',
                          background: '#450a0a44',
                          color: '#dc2626',
                        }}
                      >
                        CVE
                      </span>
                    )}
                  </div>
                  <span>
                    {d.current} → <strong style={{ color: '#6366f1' }}>{d.latest}</strong>
                  </span>
                  <span style={{ color: 'var(--muted)', fontSize: 10 }}>
                    {d.versions_behind ?? '?'} versions behind
                  </span>
                  <span
                    style={{
                      background: depSeverityColor(d.severity),
                      color: '#fff',
                      borderRadius: 4,
                      padding: '1px 7px',
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  >
                    {d.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {(result.outdated_audit.deprecated_apis ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Deprecated APIs</div>
              {(result.outdated_audit.deprecated_apis ?? []).map((a, i) => (
                <div key={`api-${i}`} style={{ marginBottom: 10, fontSize: 12 }}>
                  <div style={{ fontWeight: 700, color: '#f97316' }}>{a.api}</div>
                  <div style={{ color: 'var(--muted)' }}>
                    Used in: {a.used_in} · EOL: {a.eol}
                  </div>
                  <div>
                    Use: <em>{a.alternative}</em>
                  </div>
                </div>
              ))}
            </div>
          )}

          {(result.outdated_audit.legacy_patterns ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Legacy Patterns</div>
              {(result.outdated_audit.legacy_patterns ?? []).map((p, i) => (
                <div key={`pat-${i}`} style={{ marginBottom: 10, fontSize: 12 }}>
                  <div style={{ fontWeight: 700 }}>{p.pattern}</div>
                  <div style={{ color: 'var(--muted)' }}>{p.file}</div>
                  <div style={{ color: '#6366f1' }}>→ {p.recommendation}</div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No outdated audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function WorkflowTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {result.workflow_audit ? (
        <>
          {/* Pipeline banner + MTTD/MTTR KPIs */}
          <div
            style={{
              background: 'var(--bg-soft)',
              border: '1px solid var(--line)',
              borderRadius: 12,
              padding: 14,
              display: 'flex',
              gap: 20,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Pipeline Status</div>
              <div
                style={{
                  fontWeight: 900,
                  fontSize: 26,
                  color: pipelineStatusColor(result.workflow_audit.pipeline_status),
                }}
              >
                {result.workflow_audit.pipeline_status ?? 'n/a'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>
                {result.workflow_audit.last_run ? new Date(result.workflow_audit.last_run).toLocaleString() : ''}
              </div>
            </div>
            <div
              style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 120px), 1fr))', gap: 8, flex: 1 }}
            >
              {[
                {
                  label: 'Test Coverage',
                  value: `${result.workflow_audit.test_coverage_pct ?? 0}%`,
                  color: (result.workflow_audit.test_coverage_pct ?? 0) >= 80 ? '#22c55e' : '#f59e0b',
                },
                {
                  label: 'Mean Deploy',
                  value: `${result.workflow_audit.mean_deploy_mins ?? 0}m`,
                  color: 'var(--text)',
                },
                {
                  label: 'Mean Recovery (MTTR)',
                  value: `${result.workflow_audit.mean_recovery_mins ?? 0}m`,
                  color: (result.workflow_audit.mean_recovery_mins ?? 0) > 60 ? '#ef4444' : '#22c55e',
                },
                {
                  label: 'Flaky Tests',
                  value: String((result.workflow_audit.flaky_tests ?? []).length),
                  color: (result.workflow_audit.flaky_tests ?? []).length > 0 ? '#f59e0b' : '#22c55e',
                },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 8 }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
                  <div style={{ fontWeight: 700, fontSize: 18, color: kpi.color }}>{kpi.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Build trend */}
          {(result.workflow_audit.build_trend ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Build Trend (7 days)</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', height: 80 }}>
                {(result.workflow_audit.build_trend ?? []).map((b, i) => {
                  const barColor = b.status === 'fail' ? '#ef4444' : b.status === 'warn' ? '#f59e0b' : '#22c55e';
                  const maxMins = Math.max(
                    ...(result.workflow_audit?.build_trend ?? []).map((x) => x.duration_mins ?? 0)
                  );
                  const heightPct = Math.round(((b.duration_mins ?? 0) / maxMins) * 100);
                  return (
                    <div
                      key={`bt-${i}`}
                      style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
                    >
                      <div style={{ fontSize: 9, color: barColor, fontWeight: 700 }}>{b.duration_mins}m</div>
                      <div
                        style={{
                          width: '100%',
                          height: `${heightPct}%`,
                          minHeight: 4,
                          background: barColor,
                          borderRadius: '4px 4px 0 0',
                        }}
                      />
                      <div style={{ fontSize: 9, color: 'var(--muted)' }}>{b.date}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Test coverage bar */}
          <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>Test Coverage</div>
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 16,
                  color: (result.workflow_audit.test_coverage_pct ?? 0) >= 80 ? '#22c55e' : '#f59e0b',
                }}
              >
                {result.workflow_audit.test_coverage_pct ?? 0}%
              </div>
            </div>
            <div style={{ height: 10, background: 'var(--line)', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${result.workflow_audit.test_coverage_pct ?? 0}%`,
                  height: '100%',
                  background: (result.workflow_audit.test_coverage_pct ?? 0) >= 80 ? '#22c55e' : '#f59e0b',
                  borderRadius: 4,
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              Target ≥80% — currently {result.workflow_audit.test_coverage_pct ?? 0}%
            </div>
          </div>

          {/* Flaky tests */}
          {(result.workflow_audit.flaky_tests ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Flaky Tests</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.workflow_audit.flaky_tests ?? []).map((t, i) => {
                  const flakePct = Math.round((t.flakiness_rate ?? 0) * 100);
                  return (
                    <div
                      key={`flaky-${i}`}
                      style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: 8,
                          marginBottom: 6,
                          flexWrap: 'wrap',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, fontFamily: 'monospace' }}>{t.test}</div>
                          <div style={{ fontSize: 10, color: 'var(--muted)' }}>
                            {t.suite} · last failed {t.last_failed}
                          </div>
                        </div>
                        <div style={{ fontWeight: 700, fontSize: 14, color: flakePct >= 15 ? '#ef4444' : '#f59e0b' }}>
                          {flakePct}% flaky
                        </div>
                      </div>
                      <div style={{ height: 4, background: 'var(--line)', borderRadius: 2, overflow: 'hidden' }}>
                        <div
                          style={{
                            width: `${flakePct}%`,
                            height: '100%',
                            background: flakePct >= 15 ? '#ef4444' : '#f59e0b',
                            borderRadius: 2,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Pipeline steps */}
          <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Pipeline Steps</div>
            <MiniBarChart
              items={(result.workflow_audit.steps ?? []).map((s) => ({
                label: s.name ?? '',
                value: s.duration_ms ?? 0,
                color: stepColor(s.passed, s.status),
                suffix: 'ms',
              }))}
            />
          </div>

          {/* PR Checks */}
          <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>PR Checks</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {(result.workflow_audit.pr_checks ?? []).map((c, i) => (
                <div
                  key={`prc-${i}`}
                  style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, alignItems: 'center' }}
                >
                  <span>
                    {c.check} {c.required && <span style={{ color: '#ef4444', fontSize: 10 }}>(required)</span>}
                  </span>
                  <span style={{ fontWeight: 700, color: c.status === 'pass' ? '#22c55e' : '#ef4444' }}>
                    {c.status?.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Deployments */}
          <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Deployment History</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {(result.workflow_audit.deployments ?? []).map((d, i) => (
                <div
                  key={`dep-${i}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'auto 1fr auto auto',
                    gap: 10,
                    alignItems: 'center',
                    fontSize: 12,
                  }}
                >
                  <span style={{ fontWeight: 700 }}>{d.version}</span>
                  <span style={{ color: 'var(--muted)' }}>
                    {d.deployed_at ? new Date(d.deployed_at).toLocaleString() : ''}
                  </span>
                  <span style={{ color: d.rollback ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                    {d.rollback ? 'rolled back' : d.status}
                  </span>
                  <span style={{ fontWeight: 700, color: perfDeltaColor(d.perf_delta_ms) }}>
                    {(d.perf_delta_ms ?? 0) > 0 ? '+' : ''}
                    {d.perf_delta_ms}ms
                  </span>
                </div>
              ))}
            </div>
          </div>

          {result.workflow_audit.integration_health && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Integration Health</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 8 }}>
                {Object.entries(result.workflow_audit.integration_health).map(([svc, health]) => (
                  <div
                    key={svc}
                    style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: '8px 12px',
                      fontSize: 12,
                    }}
                  >
                    <div style={{ color: 'var(--muted)', fontSize: 10 }}>{svc}</div>
                    <div style={{ fontWeight: 700, color: integrationHealthColor(health) }}>{health}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No workflow audit data available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function DataAnalysisTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {result.data_analysis ? (
        <>
          {/* Search Console KPIs */}
          {result.data_analysis.search_console && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Search Console Summary</div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))',
                  gap: 10,
                  marginBottom: 14,
                }}
              >
                {[
                  {
                    label: 'Impressions',
                    value: (result.data_analysis.search_console.impressions ?? 0).toLocaleString(),
                    color: '#6366f1',
                  },
                  {
                    label: 'Clicks',
                    value: (result.data_analysis.search_console.clicks ?? 0).toLocaleString(),
                    color: '#22c55e',
                  },
                  {
                    label: 'CTR',
                    value: `${(result.data_analysis.search_console.ctr_pct ?? 0).toFixed(1)}%`,
                    color: '#6366f1',
                  },
                  {
                    label: 'Avg Position',
                    value: (result.data_analysis.search_console.avg_position ?? 0).toFixed(1),
                    color: '#f59e0b',
                  },
                ].map((kpi) => (
                  <div
                    key={kpi.label}
                    style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
                  >
                    <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
                    <div style={{ fontWeight: 800, fontSize: 20, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
                  </div>
                ))}
              </div>
              {(result.data_analysis.search_console.top_queries ?? []).length > 0 && (
                <>
                  <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8 }}>Top Queries</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--line)' }}>
                        {['Query', 'Impressions', 'Clicks', 'CTR', 'Position'].map((h) => (
                          <th
                            key={h}
                            style={{
                              textAlign: 'left',
                              padding: '4px 8px',
                              fontSize: 10,
                              color: 'var(--muted)',
                              fontWeight: 600,
                            }}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(result.data_analysis.search_console.top_queries ?? []).map((q, i) => (
                        <tr key={`q-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '5px 8px', fontWeight: 600 }}>{q.query}</td>
                          <td style={{ padding: '5px 8px' }}>—</td>
                          <td style={{ padding: '5px 8px', color: '#22c55e' }}>{q.clicks}</td>
                          <td style={{ padding: '5px 8px' }}>—</td>
                          <td style={{ padding: '5px 8px', color: (q.position ?? 99) <= 3 ? '#22c55e' : '#f59e0b' }}>
                            {(q.position ?? 0).toFixed(1)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}

          {/* Retention cohorts */}
          {(result.data_analysis.retention ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>User Retention Cohorts</div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['Cohort Week', 'D1 Retention', 'D7 Retention', 'D30 Retention'].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: 'left',
                          padding: '5px 10px',
                          fontSize: 10,
                          color: 'var(--muted)',
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.data_analysis.retention ?? []).map((r, i) => {
                    const d1c = (r.d1_pct ?? 0) >= 50 ? '#22c55e' : (r.d1_pct ?? 0) >= 30 ? '#f59e0b' : '#ef4444';
                    const d7c = (r.d7_pct ?? 0) >= 20 ? '#22c55e' : (r.d7_pct ?? 0) >= 10 ? '#f59e0b' : '#ef4444';
                    const d30c = (r.d30_pct ?? 0) >= 10 ? '#22c55e' : (r.d30_pct ?? 0) >= 5 ? '#f59e0b' : '#ef4444';
                    return (
                      <tr key={`ret-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '6px 10px', fontWeight: 600 }}>{r.week}</td>
                        <td style={{ padding: '6px 10px', fontWeight: 700, color: d1c }}>{r.d1_pct}%</td>
                        <td style={{ padding: '6px 10px', fontWeight: 700, color: d7c }}>{r.d7_pct}%</td>
                        <td style={{ padding: '6px 10px', fontWeight: 700, color: d30c }}>{r.d30_pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Revenue by channel */}
          {(result.data_analysis.revenue_by_channel ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Revenue by Channel</div>
              <MiniBarChart
                items={(result.data_analysis.revenue_by_channel ?? []).map((c) => ({
                  label: c.channel ?? '',
                  value: c.revenue_usd ?? 0,
                  color: '#22c55e',
                  max: Math.max(...(result.data_analysis?.revenue_by_channel ?? []).map((x) => x.revenue_usd ?? 0)),
                  suffix: ' USD',
                }))}
              />
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, marginTop: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['Channel', 'Revenue', 'Sessions', 'Conv. Rate'].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: 'left',
                          padding: '4px 8px',
                          fontSize: 10,
                          color: 'var(--muted)',
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.data_analysis.revenue_by_channel ?? []).map((c, i) => (
                    <tr key={`rev-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                      <td style={{ padding: '5px 8px', fontWeight: 600 }}>{c.channel}</td>
                      <td style={{ padding: '5px 8px', color: '#22c55e', fontWeight: 700 }}>
                        ${(c.revenue_usd ?? 0).toLocaleString()}
                      </td>
                      <td style={{ padding: '5px 8px' }}>{(c.sessions ?? 0).toLocaleString()}</td>
                      <td style={{ padding: '5px 8px', color: '#6366f1' }}>{((c.conv_rate ?? 0) * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Existing: cohort trend, funnel, anomalies, segment */}
          {(result.data_analysis.cohort_trend ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
                Performance Score — Weekly Cohort Trend
              </div>
              <AreaChart
                points={(result.data_analysis.cohort_trend ?? []).map((c) => c.score ?? 0)}
                labels={(result.data_analysis.cohort_trend ?? []).map((c) => c.period ?? '')}
                color="#6366f1"
                height={80}
              />
              <div style={{ marginTop: 10 }}>
                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>LCP Trend (ms)</div>
                <AreaChart
                  points={(result.data_analysis.cohort_trend ?? []).map((c) => c.lcp ?? 0)}
                  labels={(result.data_analysis.cohort_trend ?? []).map((c) => c.period ?? '')}
                  color="#f97316"
                  height={72}
                />
              </div>
            </div>
          )}

          {(result.data_analysis.funnel ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Conversion Funnel</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(result.data_analysis.funnel ?? []).map((step, i) => {
                  const maxUsers = result.data_analysis?.funnel?.[0]?.users ?? 1;
                  const pct = (step.users ?? 0) / maxUsers;
                  return (
                    <div key={`fn-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                      <div style={{ width: 120, textAlign: 'right', color: 'var(--muted)', flexShrink: 0 }}>
                        {step.name}
                      </div>
                      <div
                        style={{ flex: 1, height: 20, background: 'var(--line)', borderRadius: 4, overflow: 'hidden' }}
                      >
                        <div
                          style={{
                            width: `${pct * 100}%`,
                            height: '100%',
                            background: funnelBarColor(pct, i === 0),
                            borderRadius: 4,
                          }}
                        />
                      </div>
                      <div style={{ width: 60, fontWeight: 700 }}>{(step.users ?? 0).toLocaleString()}</div>
                      {i > 0 && (
                        <div style={{ width: 64, color: '#ef4444', fontSize: 11 }}>-{step.drop_pct?.toFixed(1)}%</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {(result.data_analysis.anomalies ?? []).length > 0 && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Anomaly Detection</div>
              {(result.data_analysis.anomalies ?? []).map((a, i) => (
                <div
                  key={`anm-${i}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                    alignItems: 'center',
                    borderBottom: '1px solid var(--line)',
                    paddingBottom: 8,
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontWeight: 700, color: '#f97316' }}>{a.metric}</span>
                  <span>Detected: {a.ts ? new Date(a.ts).toLocaleString() : 'n/a'}</span>
                  <span>
                    Actual: <strong>{a.value}</strong> · Expected: <strong>{a.expected}</strong>
                  </span>
                  <span
                    style={{
                      background: a.severity === 'high' ? '#ef4444' : '#f59e0b',
                      color: '#fff',
                      borderRadius: 4,
                      padding: '1px 7px',
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  >
                    {a.severity}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result.data_analysis.segment_breakdown && (
            <div
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Traffic Segment Breakdown</div>
              <MiniBarChart
                items={Object.entries(result.data_analysis.segment_breakdown).map(([seg, d]) => ({
                  label: seg,
                  value: d.sessions ?? 0,
                  suffix: ' sess',
                }))}
              />
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
            <div
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                padding: 14,
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Bot Traffic</div>
              <div
                style={{
                  fontWeight: 800,
                  fontSize: 22,
                  color: (result.data_analysis.bot_traffic_pct ?? 0) > 15 ? '#ef4444' : '#f59e0b',
                }}
              >
                {result.data_analysis.bot_traffic_pct}%
              </div>
            </div>
            <div
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                padding: 14,
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Crawl Efficiency</div>
              <div style={{ fontWeight: 800, fontSize: 22, color: '#22c55e' }}>
                {result.data_analysis.crawl_efficiency}%
              </div>
            </div>
          </div>
        </>
      ) : (
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>No data analysis available.</div>
      )}
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CoreSeoTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {/* Custom header KPIs */}
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Core SEO Foundations</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
          Keyword research, on-page, technical SEO, backlinks, rank tracking, E-E-A-T, entity-first SEO, and autonomous
          link building.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
          {[
            { label: 'Overall Score', value: `${result.core_seo_suite?.overall_score ?? 91}%`, color: '#22c55e' },
            { label: 'Top-3 Keywords', value: '14', color: '#22c55e' },
            { label: 'Rising Keywords', value: '8', color: '#6366f1' },
            { label: 'Backlinks', value: '2,340', color: '#6366f1' },
            { label: 'Domain Authority', value: '54', color: '#22c55e' },
            { label: 'E-E-A-T Score', value: '78/100', color: '#f59e0b' },
          ].map((kpi) => (
            <div
              key={kpi.label}
              style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
              <div style={{ fontWeight: 800, fontSize: 20, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>
      {/* Keyword coverage type bar */}
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Keyword Coverage by Type</div>
        <MiniBarChart
          items={[
            { label: 'Head (1–2 words)', value: 68, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'Body (3–4 words)', value: 82, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'Long-tail (5+)', value: 91, color: '#22c55e', max: 100, suffix: '%' },
          ]}
        />
      </div>
      {/* Capability suite detail */}
      <CapabilitySuiteSection title="" subtitle="" suite={result.core_seo_suite} />
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ContentBloggingTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Content & Blogging</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
          AI writing, briefs, NLP editor, CMS workflows, programmatic SEO, blogging operations, and News SEO / Google
          Discover.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
          {[
            { label: 'Overall Score', value: `${result.content_blog_suite?.overall_score ?? 79}%`, color: '#f59e0b' },
            { label: 'Published Articles', value: '147', color: 'var(--text)' },
            { label: 'Refresh Backlog', value: '23', color: '#ef4444' },
            { label: 'Publish SLA Met', value: '89%', color: '#22c55e' },
            { label: 'AI-assisted Posts', value: '62%', color: '#6366f1' },
            { label: 'CMS Sync', value: 'Healthy', color: '#22c55e' },
          ].map((kpi) => (
            <div
              key={kpi.label}
              style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
              <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>
      {/* Content decay risk */}
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Content Decay Risks</div>
        <div style={{ display: 'grid', gap: 6 }}>
          {[
            { title: 'Ultimate Guide to React Hooks (2022)', age: '18 months', traffic_drop: '42%', risk: 'high' },
            { title: 'Top 10 JavaScript Libraries', age: '14 months', traffic_drop: '28%', risk: 'medium' },
            { title: 'Getting Started with TypeScript', age: '11 months', traffic_drop: '19%', risk: 'medium' },
          ].map((a, i) => (
            <div
              key={`cd-${i}`}
              style={{
                ...card,
                padding: 10,
                borderLeft: `3px solid ${a.risk === 'high' ? '#ef4444' : '#f59e0b'}`,
                display: 'grid',
                gridTemplateColumns: '1fr auto auto',
                gap: 10,
                alignItems: 'center',
                fontSize: 12,
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {a.title}
                <span style={{ color: 'var(--muted)', marginLeft: 8, fontSize: 10 }}>({a.age} old)</span>
              </div>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>-{a.traffic_drop}</span>
              <span style={badge(a.risk === 'high' ? '#ef4444' : '#f59e0b')}>{a.risk}</span>
            </div>
          ))}
        </div>
      </div>
      <CapabilitySuiteSection title="" subtitle="" suite={result.content_blog_suite} />
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AiOptimizationTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>SEO AI + AI Optimization</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
          AIO, AEO, GEO, LLMO, SAGEO, and predictive engine optimization for the AI agent economy.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
          {[
            {
              label: 'AIO Readiness',
              value: `${result.ai_optimization_suite?.overall_score ?? 86}%`,
              color: '#22c55e',
            },
            { label: 'Featured Snippet Capture', value: '18%', color: '#6366f1' },
            { label: 'AI Citations', value: '42', color: '#6366f1' },
            { label: 'LLMO Coverage', value: '73%', color: '#f59e0b' },
            { label: 'GEO Score', value: '68%', color: '#f59e0b' },
            { label: 'AEO Score', value: '71%', color: '#f59e0b' },
          ].map((kpi) => (
            <div
              key={kpi.label}
              style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
              <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>
      {/* AIO coverage bars */}
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>AI Optimization Coverage</div>
        <MiniBarChart
          items={[
            { label: 'LLMO', value: 73, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'GEO', value: 68, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'AEO', value: 71, color: '#22c55e', max: 100, suffix: '%' },
            { label: 'SAGEO', value: 55, color: '#f59e0b', max: 100, suffix: '%' },
          ]}
        />
      </div>
      <CapabilitySuiteSection title="" subtitle="" suite={result.ai_optimization_suite} />
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SearchExperienceTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Search & Generative Experience</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
          VSO, SXO, GXO, CXAO, multi-surface visibility, and cross-surface answer quality after the click.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
          {[
            {
              label: 'Overall Score',
              value: `${result.search_experience_suite?.overall_score ?? 83}%`,
              color: '#22c55e',
            },
            { label: 'Rich Snippets', value: '34%', color: '#6366f1' },
            { label: 'PAA Coverage', value: '28%', color: '#6366f1' },
            { label: 'Featured Snippets', value: '12%', color: '#f59e0b' },
            { label: 'Search Intent Match', value: '81%', color: '#22c55e' },
            { label: 'CWV (search LPs)', value: 'Good', color: '#22c55e' },
          ].map((kpi) => (
            <div
              key={kpi.label}
              style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>{kpi.label}</div>
              <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>
      {/* SERP feature coverage */}
      <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>SERP Feature Coverage</div>
        <MiniBarChart
          items={[
            { label: 'Rich Snippets', value: 34, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'People Also Ask', value: 28, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'Featured Snippet', value: 12, color: '#22c55e', max: 100, suffix: '%' },
            { label: 'Shopping/Local', value: 8, color: '#f59e0b', max: 100, suffix: '%' },
          ]}
        />
      </div>
      <CapabilitySuiteSection title="" subtitle="" suite={result.search_experience_suite} />
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function VerticalSeoTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <CapabilitySuiteSection
      title="Vertical SEO Suites"
      subtitle="eCommerce, international, site migration, video SEO, local SEO, decentralized answer engines, and vertical operational playbooks."
      suite={result.vertical_seo_suite}
    />
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function PlatformOpsTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <CapabilitySuiteSection
      title="Platform Ops, Security, UX, and Automation"
      subtitle="Autonomous agent orchestration, A/B testing, analytics, multi-tenant operations, integrations, OWASP / unused ports, UI/UX, and loading-time issues."
      suite={result.platform_ops_suite}
    />
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AccessibilityTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
            marginBottom: 16,
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>WCAG Accessibility Audit</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              Level {result.accessibility_audit?.wcag_level ?? 'AA'} compliance · Legal risk:{' '}
              <span
                style={{
                  color:
                    result.accessibility_audit?.legal_risk === 'high'
                      ? '#ef4444'
                      : result.accessibility_audit?.legal_risk === 'medium'
                        ? '#f59e0b'
                        : '#22c55e',
                  fontWeight: 700,
                }}
              >
                {result.accessibility_audit?.legal_risk ?? 'low'}
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div
              style={{ fontSize: 28, fontWeight: 900, color: scoreColor(result.accessibility_audit?.wcag_score ?? 0) }}
            >
              {result.accessibility_audit?.wcag_score ?? 0}
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>WCAG Score</div>
          </div>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))',
            gap: 10,
            marginBottom: 16,
          }}
        >
          {[
            { label: 'Level A Violations', value: result.accessibility_audit?.violations_a ?? 0, color: '#ef4444' },
            { label: 'Level AA Violations', value: result.accessibility_audit?.violations_aa ?? 0, color: '#f97316' },
            { label: 'Level AAA Violations', value: result.accessibility_audit?.violations_aaa ?? 0, color: '#f59e0b' },
            {
              label: 'Contrast Failures',
              value: result.accessibility_audit?.color_contrast_failures ?? 0,
              color: '#8b5cf6',
            },
            { label: 'ARIA Issues', value: result.accessibility_audit?.aria_issues ?? 0, color: '#6366f1' },
            {
              label: 'Keyboard Nav Issues',
              value: result.accessibility_audit?.keyboard_nav_issues ?? 0,
              color: '#06b6d4',
            },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Top Violations</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {(result.accessibility_audit?.issues ?? []).map((issue, i) => (
                <div
                  key={`item-${i}`}
                  style={{ background: 'var(--bg-soft)', borderRadius: 8, padding: '10px 12px', fontSize: 12 }}
                >
                  <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontFamily: 'monospace', color: '#8b5cf6', fontWeight: 700 }}>{issue.wcag}</span>
                    <span
                      style={{
                        background:
                          issue.impact === 'critical'
                            ? '#ef444420'
                            : issue.impact === 'serious'
                              ? '#f9741620'
                              : '#f59e0b20',
                        color:
                          issue.impact === 'critical' ? '#ef4444' : issue.impact === 'serious' ? '#f97316' : '#f59e0b',
                        padding: '1px 6px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                      }}
                    >
                      {issue.impact}
                    </span>
                  </div>
                  <div style={{ color: 'var(--muted)', marginBottom: 4 }}>{issue.description}</div>
                  <div style={{ color: '#22c55e', fontSize: 11 }}>Fix: {issue.remediation}</div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Screen Reader Compatibility</div>
            <div style={{ background: 'var(--bg-soft)', borderRadius: 8, padding: 14, marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 12 }}>Screen Reader Score</span>
                <span
                  style={{ fontWeight: 700, color: scoreColor(result.accessibility_audit?.screen_reader_score ?? 0) }}
                >
                  {result.accessibility_audit?.screen_reader_score ?? 0}
                </span>
              </div>
              <div style={{ height: 6, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${result.accessibility_audit?.screen_reader_score ?? 0}%`,
                    height: '100%',
                    background: scoreColor(result.accessibility_audit?.screen_reader_score ?? 0),
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Failing Criteria</div>
            <div style={{ display: 'grid', gap: 4 }}>
              {(result.accessibility_audit?.failing_criteria ?? []).map((c, i) => (
                <div
                  key={`item-${i}`}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#ef4444' }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', flexShrink: 0 }} />
                  {c}
                </div>
              ))}
            </div>
            <div style={{ fontWeight: 600, fontSize: 12, margin: '12px 0 6px' }}>Passing Criteria</div>
            <div style={{ display: 'grid', gap: 4 }}>
              {(result.accessibility_audit?.passing_criteria ?? []).map((c, i) => (
                <div
                  key={`item-${i}`}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#22c55e' }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
                  {c}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CompetitorIntelTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Competitor Intelligence</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Keyword gap, content freshness, backlink comparison, and SERP overlap analysis
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            { label: 'Keyword Gap', value: result.competitor_intel?.keyword_gap ?? 0, color: '#ef4444' },
            { label: 'Content Gap', value: result.competitor_intel?.content_gap ?? 0, color: '#f97316' },
            {
              label: 'Backlink Gap',
              value: (result.competitor_intel?.backlink_gap ?? 0).toLocaleString(),
              color: '#f59e0b',
            },
            { label: 'SERP Overlap', value: `${result.competitor_intel?.serp_overlap_pct ?? 0}%`, color: '#6366f1' },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 10 }}>Competitor Profiles</div>
        <div style={{ overflowX: 'auto', marginBottom: 20 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Domain', 'Authority', 'Keywords', 'Backlinks', 'Content Score', 'Est. Traffic'].map((h) => (
                  <th
                    key={h}
                    style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(result.competitor_intel?.competitors ?? []).map((c, i) => (
                <tr key={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '8px 10px', fontWeight: 600, fontFamily: 'monospace' }}>{c.domain}</td>
                  <td style={{ padding: '8px 10px', color: scoreColor(c.authority ?? 0), fontWeight: 700 }}>
                    {c.authority}
                  </td>
                  <td style={{ padding: '8px 10px' }}>{(c.keywords ?? 0).toLocaleString()}</td>
                  <td style={{ padding: '8px 10px' }}>{(c.backlinks ?? 0).toLocaleString()}</td>
                  <td style={{ padding: '8px 10px', color: scoreColor(c.content_score ?? 0) }}>{c.content_score}</td>
                  <td style={{ padding: '8px 10px' }}>{(c.traffic_est ?? 0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Content Decay Analysis</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {[
                {
                  label: 'Thin Pages',
                  value: result.competitor_intel?.content_audit?.thin_pages ?? 0,
                  color: '#f59e0b',
                },
                {
                  label: 'Duplicate Pages',
                  value: result.competitor_intel?.content_audit?.duplicate_pages ?? 0,
                  color: '#f97316',
                },
                {
                  label: 'Decaying Pages',
                  value: result.competitor_intel?.content_audit?.decaying_pages ?? 0,
                  color: '#ef4444',
                },
                {
                  label: 'Avg Freshness',
                  value: `${result.competitor_intel?.content_audit?.avg_freshness_score ?? 0}`,
                  color: scoreColor(result.competitor_intel?.content_audit?.avg_freshness_score ?? 0),
                },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '6px 0',
                    borderBottom: '1px solid var(--line)',
                    fontSize: 12,
                  }}
                >
                  <span>{m.label}</span>
                  <span style={{ fontWeight: 700, color: m.color }}>{m.value}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Top Opportunities</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.competitor_intel?.opportunities ?? []).map((opp, i) => (
                <div
                  key={`item-${i}`}
                  style={{
                    display: 'flex',
                    gap: 8,
                    fontSize: 12,
                    padding: '6px 0',
                    borderBottom: '1px solid var(--line)',
                  }}
                >
                  <span style={{ color: '#6366f1', fontWeight: 700, flexShrink: 0 }}>#{i + 1}</span>
                  <span>{opp}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SchemaEntitiesTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Schema, Entities & Internal Link Equity</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Structured data coverage, rich result eligibility, Knowledge Graph entities, and link equity distribution
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'Structured Data Score',
              value: result.schema_entities?.structured_data_score ?? 0,
              color: scoreColor(result.schema_entities?.structured_data_score ?? 0),
            },
            {
              label: 'JSON-LD Coverage',
              value: `${result.schema_entities?.json_ld_coverage_pct ?? 0}%`,
              color: '#6366f1',
            },
            {
              label: 'Validated Schemas',
              value: `${result.schema_entities?.validated ?? 0}/${result.schema_entities?.total_schemas ?? 0}`,
              color: '#22c55e',
            },
            { label: 'Schema Errors', value: result.schema_entities?.errors ?? 0, color: '#ef4444' },
            {
              label: 'Link Equity Score',
              value: result.schema_entities?.internal_link_equity_score ?? 0,
              color: scoreColor(result.schema_entities?.internal_link_equity_score ?? 0),
            },
            { label: 'Orphan Pages', value: result.schema_entities?.orphan_pages?.length ?? 0, color: '#f59e0b' },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 20, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Rich Result Types</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.schema_entities?.rich_result_types ?? []).map((s, i) => (
                <div
                  key={`item-${i}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '7px 10px',
                    background: 'var(--bg-soft)',
                    borderRadius: 7,
                    fontSize: 12,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{s.type}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '2px 6px',
                        borderRadius: 4,
                        background: s.present ? '#22c55e20' : '#ef444420',
                        color: s.present ? '#22c55e' : '#ef4444',
                        fontWeight: 700,
                      }}
                    >
                      {s.present ? 'Present' : 'Missing'}
                    </span>
                    {s.rich_result_eligible && (
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: '#6366f120',
                          color: '#6366f1',
                          fontWeight: 700,
                        }}
                      >
                        Rich
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Knowledge Graph Entities</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.schema_entities?.entities ?? []).map((e, i) => (
                <div
                  key={`item-${i}`}
                  style={{ padding: '8px 10px', background: 'var(--bg-soft)', borderRadius: 7, fontSize: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{e.entity}</span>
                    <span style={{ color: 'var(--muted)', fontSize: 11 }}>{e.type}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '1px 5px',
                        borderRadius: 3,
                        background: e.knowledge_panel ? '#22c55e20' : '#ef444420',
                        color: e.knowledge_panel ? '#22c55e' : '#ef4444',
                      }}
                    >
                      KP {e.knowledge_panel ? '\u2713' : '\u2717'}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '1px 5px',
                        borderRadius: 3,
                        background: e.wikidata ? '#6366f120' : '#ef444420',
                        color: e.wikidata ? '#6366f1' : '#ef4444',
                      }}
                    >
                      Wikidata {e.wikidata ? '\u2713' : '\u2717'}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>
                      {((e.confidence ?? 0) * 100).toFixed(0)}% conf
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Orphan Pages</div>
            {(result.schema_entities?.orphan_pages ?? []).length === 0 ? (
              <div style={{ fontSize: 12, color: '#22c55e' }}>No orphan pages detected</div>
            ) : (
              <div style={{ display: 'grid', gap: 4 }}>
                {(result.schema_entities?.orphan_pages ?? []).map((p, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      padding: '6px 10px',
                      background: '#ef444410',
                      borderRadius: 6,
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: '#ef4444',
                    }}
                  >
                    {p.url} — {p.inbound_links} inbound links
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Anchor Text Distribution</div>
            <MiniBarChart
              items={(result.schema_entities?.anchor_text_dist ?? []).map((a) => ({
                label: a.text ?? '',
                value: a.pct ?? 0,
                suffix: '%',
              }))}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function TechnicalDeepTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Technical Deep Dive</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Crawl budget utilization, Googlebot frequency, log file anomalies, topical cluster coverage, and redirect
          chains
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'Crawl Efficiency',
              value: `${result.technical_deep?.crawl_efficiency_pct ?? 0}%`,
              color: scoreColor(result.technical_deep?.crawl_efficiency_pct ?? 0),
            },
            {
              label: 'Budget Used',
              value: `${result.technical_deep?.crawl_budget_used_pct ?? 0}%`,
              color: (result.technical_deep?.crawl_budget_used_pct ?? 0) > 90 ? '#ef4444' : '#f59e0b',
            },
            { label: 'Wasted Crawl Slots', value: result.technical_deep?.wasted_crawl_slots ?? 0, color: '#f97316' },
            {
              label: 'Googlebot (7d)',
              value: (result.technical_deep?.googlebot_visits_last7d ?? 0).toLocaleString(),
              color: '#6366f1',
            },
            {
              label: 'Avg Crawl Interval',
              value: `${result.technical_deep?.avg_crawl_interval_hrs ?? 0}h`,
              color: 'var(--fg)',
            },
            { label: 'Redirect Chains', value: result.technical_deep?.redirect_chains?.length ?? 0, color: '#f59e0b' },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 20, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Crawl Budget Breakdown</div>
            <MiniBarChart
              items={(result.technical_deep?.crawl_budget ?? []).map((b) => ({
                label: b.url_type ?? '',
                value: b.budget_pct ?? 0,
                color: b.wasted ? '#ef4444' : '#6366f1',
                suffix: '%',
              }))}
            />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Topical Cluster Coverage</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.technical_deep?.topical_clusters ?? []).map((c, i) => (
                <div key={`item-${i}`} style={{ fontSize: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{ fontWeight: c.gap ? 400 : 600 }}>{c.topic}</span>
                    <span style={{ color: c.gap ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                      {c.coverage_pct}%{c.gap ? ' GAP' : ''}
                    </span>
                  </div>
                  <div style={{ height: 5, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${c.coverage_pct}%`,
                        height: '100%',
                        background: c.gap ? '#ef4444' : '#22c55e',
                        borderRadius: 3,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Log File Anomalies</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  {['Timestamp', 'Type', 'URL', 'Detail', 'Severity'].map((h) => (
                    <th
                      key={h}
                      style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(result.technical_deep?.log_anomalies ?? []).map((ev, i) => (
                  <tr key={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 10px', fontFamily: 'monospace', fontSize: 11 }}>{ev.ts}</td>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{ev.type}</td>
                    <td
                      style={{
                        padding: '7px 10px',
                        fontFamily: 'monospace',
                        fontSize: 11,
                        maxWidth: 160,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {ev.url}
                    </td>
                    <td style={{ padding: '7px 10px', color: 'var(--muted)' }}>{ev.detail}</td>
                    <td style={{ padding: '7px 10px' }}>
                      <span
                        style={{
                          padding: '2px 7px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 700,
                          background:
                            ev.severity === 'high'
                              ? '#ef444420'
                              : ev.severity === 'warning'
                                ? '#f59e0b20'
                                : '#6366f120',
                          color: ev.severity === 'high' ? '#ef4444' : ev.severity === 'warning' ? '#f59e0b' : '#6366f1',
                        }}
                      >
                        {ev.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function TrustRevenueTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Trust Signals & Revenue Attribution</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          E-E-A-T score, safe browsing, review aggregation, and SEO revenue attribution
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'Domain Trust',
              value: result.trust_revenue?.domain_trust_score ?? 0,
              color: scoreColor(result.trust_revenue?.domain_trust_score ?? 0),
            },
            {
              label: 'E-E-A-T Score',
              value: result.trust_revenue?.e_e_a_t_score ?? 0,
              color: scoreColor(result.trust_revenue?.e_e_a_t_score ?? 0),
            },
            {
              label: 'Review Score',
              value: result.trust_revenue?.review_aggregate_score?.toFixed(1) ?? '0.0',
              color: '#f59e0b',
            },
            {
              label: 'SEO Revenue',
              value: `$${((result.trust_revenue?.seo_revenue_total_usd ?? 0) / 1000).toFixed(0)}k`,
              color: '#22c55e',
            },
            { label: 'Attributed %', value: `${result.trust_revenue?.seo_attributed_pct ?? 0}%`, color: '#6366f1' },
            {
              label: 'Safe Browsing',
              value: result.trust_revenue?.safe_browsing_clean ? '\u2713 Clean' : '\u2717 Flagged',
              color: result.trust_revenue?.safe_browsing_clean ? '#22c55e' : '#ef4444',
            },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 18, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Review Platforms</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {(result.trust_revenue?.reviews ?? []).map((r, i) => (
                <div
                  key={`item-${i}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--bg-soft)',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{r.platform}</span>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ color: '#f59e0b', fontWeight: 700 }}>\u2605 {r.score?.toFixed(1)}</span>
                    <span style={{ color: 'var(--muted)' }}>{r.count?.toLocaleString()} reviews</span>
                    <span
                      style={{
                        color: r.trend === 'up' ? '#22c55e' : r.trend === 'down' ? '#ef4444' : 'var(--muted)',
                        fontSize: 11,
                      }}
                    >
                      {r.trend === 'up' ? '\u2191' : r.trend === 'down' ? '\u2193' : '\u2014'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Revenue Attribution by Channel</div>
            <MiniBarChart
              items={(result.trust_revenue?.attribution ?? []).map((a) => ({
                label: a.channel ?? '',
                value: a.last_click_pct ?? 0,
                suffix: '%',
              }))}
            />
          </div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Top Revenue-Driving Keywords</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  {['Keyword', 'Position', 'Sessions', 'Conversions', 'Revenue'].map((h) => (
                    <th
                      key={h}
                      style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(result.trust_revenue?.top_revenue_keywords ?? []).map((k, i) => (
                  <tr key={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{k.keyword}</td>
                    <td style={{ padding: '7px 10px', color: '#22c55e', fontWeight: 700 }}>#{k.position}</td>
                    <td style={{ padding: '7px 10px' }}>{k.sessions?.toLocaleString()}</td>
                    <td style={{ padding: '7px 10px' }}>{k.conversions}</td>
                    <td style={{ padding: '7px 10px', color: '#22c55e', fontWeight: 700 }}>
                      ${k.revenue_usd?.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function UxConversionTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>UX, Conversion & Brand Signals</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          CTA coverage, form friction, brand voice consistency, social card completeness, and media alt text
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'UX Score',
              value: result.ux_conversion?.ux_score ?? 0,
              color: scoreColor(result.ux_conversion?.ux_score ?? 0),
            },
            {
              label: 'Friction Score',
              value: result.ux_conversion?.friction_score ?? 0,
              color: (result.ux_conversion?.friction_score ?? 0) > 50 ? '#ef4444' : '#f59e0b',
            },
            { label: 'CTA Coverage', value: `${result.ux_conversion?.cta_coverage_pct ?? 0}%`, color: '#6366f1' },
            {
              label: 'Form Completion',
              value: `${result.ux_conversion?.form_completion_avg_pct ?? 0}%`,
              color: scoreColor(result.ux_conversion?.form_completion_avg_pct ?? 0),
            },
            {
              label: 'Brand Voice',
              value: result.ux_conversion?.brand_voice_score ?? 0,
              color: scoreColor(result.ux_conversion?.brand_voice_score ?? 0),
            },
            { label: 'OG Coverage', value: `${result.ux_conversion?.og_coverage_pct ?? 0}%`, color: '#8b5cf6' },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 18, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>CTA Audit</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.ux_conversion?.cta_audit ?? []).map((c, i) => (
                <div
                  key={`item-${i}`}
                  style={{ padding: '8px 12px', background: 'var(--bg-soft)', borderRadius: 8, fontSize: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{c.page}</span>
                    <span style={{ fontWeight: 700, color: scoreColor(c.visibility_score ?? 0) }}>
                      {c.visibility_score}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{ fontWeight: 600 }}>{c.cta_text}</span>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{c.placement}</span>
                    {!c.contrast_ok && <span style={{ fontSize: 10, color: '#ef4444' }}>Low contrast</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Form Friction Analysis</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {(result.ux_conversion?.form_friction ?? []).map((f, i) => (
                <div
                  key={`item-${i}`}
                  style={{ padding: '8px 12px', background: 'var(--bg-soft)', borderRadius: 8, fontSize: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{f.form_id}</span>
                    <span style={{ color: (f.friction_score ?? 0) > 40 ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>
                      Friction {f.friction_score}
                    </span>
                  </div>
                  <div style={{ color: 'var(--muted)', marginBottom: 2 }}>
                    {f.fields} fields · {f.avg_completion_pct}% completion
                  </div>
                  <div style={{ color: '#f59e0b', fontSize: 11 }}>Drop-off: {f.drop_field}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Heatmap Recommendations</div>
            {(result.ux_conversion?.heatmap_recommendations ?? []).map((r, i) => (
              <div
                key={`item-${i}`}
                style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'flex', gap: 6 }}
              >
                <span style={{ color: '#6366f1' }}>→</span>
                {r}
              </div>
            ))}
          </div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Social Card & Media Coverage</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              {(result.ux_conversion?.social_cards ?? []).map((sc, i) => (
                <div
                  key={`item-${i}`}
                  style={{
                    padding: '7px 10px',
                    background: 'var(--bg-soft)',
                    borderRadius: 7,
                    marginBottom: 6,
                    fontSize: 12,
                  }}
                >
                  <div style={{ fontFamily: 'monospace', fontSize: 11, marginBottom: 4 }}>{sc.url}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ color: sc.og_complete ? '#22c55e' : '#ef4444', fontSize: 11 }}>
                      OG {sc.og_complete ? '\u2713' : '\u2717'}
                    </span>
                    <span style={{ color: sc.twitter_complete ? '#22c55e' : '#ef4444', fontSize: 11 }}>
                      Twitter {sc.twitter_complete ? '\u2713' : '\u2717'}
                    </span>
                    {(sc.missing ?? []).length > 0 && (
                      <span style={{ color: '#f59e0b', fontSize: 10 }}>Missing: {sc.missing?.join(', ')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 12, marginBottom: 8 }}>
                Alt text coverage:{' '}
                <strong style={{ color: scoreColor(result.ux_conversion?.media_alt_coverage_pct ?? 0) }}>
                  {result.ux_conversion?.media_alt_coverage_pct ?? 0}%
                </strong>
              </div>
              <div style={{ display: 'grid', gap: 4 }}>
                {(result.ux_conversion?.media_items ?? []).map((m, i) => (
                  <div
                    key={`item-${i}`}
                    style={{
                      display: 'flex',
                      gap: 8,
                      fontSize: 11,
                      padding: '4px 0',
                      borderBottom: '1px solid var(--line)',
                    }}
                  >
                    <span
                      style={{
                        color: m.alt_present ? (m.alt_descriptive ? '#22c55e' : '#f59e0b') : '#ef4444',
                        fontWeight: 700,
                      }}
                    >
                      {m.alt_present ? (m.alt_descriptive ? '\u2713' : '\u25b3') : '\u2717'}
                    </span>
                    <span
                      style={{
                        fontFamily: 'monospace',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1,
                      }}
                    >
                      {m.url}
                    </span>
                    <span style={{ color: 'var(--muted)', flexShrink: 0 }}>{m.size_kb}kb</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function GrowthLandingTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Growth Playbooks & Landing Pages</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Actionable SEO playbooks ranked by impact, AI-scored landing pages, and multi-channel distribution health
        </div>
        <div
          style={{
            background: '#6366f110',
            border: '1px solid #6366f120',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 16,
            fontSize: 12,
          }}
        >
          <span style={{ fontWeight: 700, color: '#6366f1' }}>Top Priority: </span>
          {result.growth_landing?.top_priority}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'Playbook Score',
              value: result.growth_landing?.playbook_score ?? 0,
              color: scoreColor(result.growth_landing?.playbook_score ?? 0),
            },
            { label: 'Landing Pages', value: result.growth_landing?.landing_pages?.length ?? 0, color: '#6366f1' },
            {
              label: 'Multi-Channel',
              value: `${result.growth_landing?.multi_channel_score ?? 0}`,
              color: scoreColor(result.growth_landing?.multi_channel_score ?? 0),
            },
            { label: 'Quick Wins', value: result.growth_landing?.quick_wins?.length ?? 0, color: '#22c55e' },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gap: 14, marginBottom: 20 }}>
          {(result.growth_landing?.playbooks ?? []).map((pb, pi) => (
            <div
              key={pi}
              style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 10, padding: 14 }}
            >
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10 }}>
                <span
                  style={{
                    padding: '3px 8px',
                    background: '#6366f120',
                    color: '#6366f1',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 700,
                  }}
                >
                  {pb.vertical}
                </span>
                <span style={{ fontWeight: 700, fontSize: 13 }}>{pb.goal}</span>
              </div>
              <div style={{ display: 'grid', gap: 6 }}>
                {(pb.actions ?? []).map((a, ai) => (
                  <div
                    key={ai}
                    style={{
                      display: 'flex',
                      gap: 10,
                      alignItems: 'flex-start',
                      padding: '7px 10px',
                      background: 'var(--bg)',
                      borderRadius: 7,
                      fontSize: 12,
                    }}
                  >
                    <span
                      style={{
                        padding: '1px 5px',
                        borderRadius: 3,
                        background: a.priority === 'P0' ? '#ef444420' : a.priority === 'P1' ? '#f59e0b20' : '#22c55e20',
                        color: a.priority === 'P0' ? '#ef4444' : a.priority === 'P1' ? '#f59e0b' : '#22c55e',
                        fontWeight: 700,
                        fontSize: 10,
                        flexShrink: 0,
                        marginTop: 1,
                      }}
                    >
                      {a.priority}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, marginBottom: 2 }}>{a.action}</div>
                      <div style={{ display: 'flex', gap: 10, color: 'var(--muted)', fontSize: 11 }}>
                        <span style={{ color: '#22c55e' }}>{a.impact}</span>
                        <span>Effort: {a.effort}</span>
                        <span>{a.timeline}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Landing Page AI Scores</div>
            <div style={{ display: 'grid', gap: 8 }}>
              {(result.growth_landing?.landing_pages ?? []).map((lp, i) => (
                <div
                  key={`item-${i}`}
                  style={{ padding: '10px 12px', background: 'var(--bg-soft)', borderRadius: 8, fontSize: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{lp.url}</span>
                    <span style={{ fontWeight: 700, color: scoreColor(lp.overall ?? 0) }}>{lp.overall}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 10, fontSize: 11, marginBottom: 6 }}>
                    <span>
                      H: <strong style={{ color: scoreColor(lp.headline_score ?? 0) }}>{lp.headline_score}</strong>
                    </span>
                    <span>
                      CTA: <strong style={{ color: scoreColor(lp.cta_score ?? 0) }}>{lp.cta_score}</strong>
                    </span>
                    <span>
                      Trust: <strong style={{ color: scoreColor(lp.trust_score ?? 0) }}>{lp.trust_score}</strong>
                    </span>
                  </div>
                  {(lp.suggestions ?? []).slice(0, 1).map((s, si) => (
                    <div key={si} style={{ color: '#6366f1', fontSize: 11 }}>
                      \u2192 {s}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Multi-Channel Health</div>
            <MiniBarChart
              items={(result.growth_landing?.channels ?? []).map((c) => ({
                label: c.channel ?? '',
                value: c.coverage_pct ?? 0,
                color: c.active ? '#22c55e' : '#6b7280',
                suffix: '%',
              }))}
            />
            <div style={{ fontWeight: 600, fontSize: 12, margin: '14px 0 8px' }}>Quick Wins</div>
            {(result.growth_landing?.quick_wins ?? []).map((w, i) => (
              <div
                key={`item-${i}`}
                style={{ fontSize: 12, color: '#22c55e', marginBottom: 4, display: 'flex', gap: 6 }}
              >
                <span>\u2713</span>
                {w}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LiveIntelligenceTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>
          Live Intelligence & Real-Time Rank Tracking
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Live position tracking, RAG content readiness, AI answer engine coverage, and real-time alert feed
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
            gap: 10,
            marginBottom: 20,
          }}
        >
          {[
            {
              label: 'Avg Position',
              value: result.live_intelligence?.avg_position?.toFixed(1) ?? '\u2014',
              color: '#6366f1',
            },
            {
              label: 'Total Keywords',
              value: (result.live_intelligence?.total_keywords ?? 0).toLocaleString(),
              color: 'var(--fg)',
            },
            { label: 'Top 3 Keywords', value: result.live_intelligence?.keywords_top3 ?? 0, color: '#22c55e' },
            { label: 'Gained (7d)', value: `+${result.live_intelligence?.positions_gained_7d ?? 0}`, color: '#22c55e' },
            { label: 'Lost (7d)', value: `-${result.live_intelligence?.positions_lost_7d ?? 0}`, color: '#ef4444' },
            {
              label: 'RAG Readiness',
              value: result.live_intelligence?.rag_readiness_score ?? 0,
              color: scoreColor(result.live_intelligence?.rag_readiness_score ?? 0),
            },
          ].map((m) => (
            <div
              key={m.label}
              style={{
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 20, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Top Keyword Positions</div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['Keyword', 'Pos', '\u0394', 'SERP Feature'].map((h) => (
                      <th
                        key={h}
                        style={{ padding: '5px 8px', textAlign: 'left', color: 'var(--muted)', fontWeight: 600 }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.live_intelligence?.top_keywords ?? []).map((k, i) => (
                    <tr key={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                      <td
                        style={{
                          padding: '6px 8px',
                          fontWeight: 600,
                          maxWidth: 140,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {k.keyword}
                      </td>
                      <td
                        style={{
                          padding: '6px 8px',
                          color:
                            (k.position ?? 0) <= 3 ? '#22c55e' : (k.position ?? 0) <= 10 ? '#6366f1' : 'var(--muted)',
                          fontWeight: 700,
                        }}
                      >
                        #{k.position}
                      </td>
                      <td
                        style={{
                          padding: '6px 8px',
                          color: (k.delta ?? 0) > 0 ? '#22c55e' : '#ef4444',
                          fontWeight: 700,
                        }}
                      >
                        {(k.delta ?? 0) > 0 ? `+${k.delta}` : k.delta}
                      </td>
                      <td style={{ padding: '6px 8px', fontSize: 10, color: '#8b5cf6' }}>
                        {k.serp_feature !== 'none' ? k.serp_feature : '\u2014'}
                      </td>{' '}
                      {/* NOSONAR */}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>AI Answer Engine Coverage</div>
            <div style={{ marginBottom: 8, fontSize: 12 }}>
              Coverage rate:{' '}
              <strong style={{ color: scoreColor(result.live_intelligence?.ai_answer_coverage_pct ?? 0) }}>
                {result.live_intelligence?.ai_answer_coverage_pct ?? 0}%
              </strong>
            </div>
            <div style={{ display: 'grid', gap: 5 }}>
              {(result.live_intelligence?.ai_coverage ?? []).map((ac, i) => (
                <div
                  key={`item-${i}`}
                  style={{ padding: '7px 10px', background: 'var(--bg-soft)', borderRadius: 7, fontSize: 12 }}
                >
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 3 }}>
                    <span style={{ color: ac.answered ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                      {ac.answered ? '\u2713' : '\u2717'}
                    </span>
                    <span style={{ flex: 1 }}>{ac.query}</span>
                  </div>
                  {ac.answered && (
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>
                      Source: {ac.source} · {((ac.confidence ?? 0) * 100).toFixed(0)}% confidence
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Live Alert Feed</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {(result.live_intelligence?.live_alerts ?? []).map((alert, i) => (
              <div
                key={`item-${i}`}
                style={{
                  display: 'flex',
                  gap: 12,
                  alignItems: 'flex-start',
                  padding: '10px 14px',
                  background:
                    alert.severity === 'high' ? '#ef444410' : alert.severity === 'warning' ? '#f59e0b10' : '#6366f110',
                  border: `1px solid ${alert.severity === 'high' ? '#ef444430' : alert.severity === 'warning' ? '#f59e0b30' : '#6366f130'}`,
                  borderRadius: 8,
                  fontSize: 12,
                }}
              >
                <div style={{ flexShrink: 0, marginTop: 1 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      display: 'block',
                      background:
                        alert.severity === 'high' ? '#ef4444' : alert.severity === 'warning' ? '#f59e0b' : '#6366f1',
                    }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{alert.metric}</div>
                  <div style={{ color: 'var(--muted)' }}>{alert.change}</div>
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 11, flexShrink: 0 }}>{alert.ts}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function HistoryTab({
  result,
  card,
  isOfflinePreview,
  autoFixing,
  autoFixResult,
  autoFixError,
  fixingItem,
  fixedItems,
  fixSingleItem,
  optimizeSite,
  historyLoading,
  historyData,
  loadHistory,
}: PerfTabProps) {
  return (
    <section style={card}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Performance History</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
            Trend: <strong>{result.history?.trend ?? 'n/a'}</strong>
            {result.history?.regression_detected && (
              <span style={{ color: '#ef4444', marginLeft: 8 }}>Regression detected</span>
            )}
          </div>
        </div>
        <button type="button" style={btn()} onClick={loadHistory} disabled={historyLoading}>
          {historyLoading ? 'Loading...' : 'Load Full History'}
        </button>
      </div>
      {(result.history?.runs ?? []).length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <AreaChart
            points={(result.history?.runs ?? []).map((r) => r.performance_score ?? 0)}
            labels={(result.history?.runs ?? []).map((r) =>
              r.ts ? new Date(r.ts).toLocaleDateString('en', { month: 'short', day: 'numeric' }) : ''
            )}
            color="#6366f1"
            height={80}
          />
        </div>
      )}
      {historyData && historyData.runs.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
            {historyData.count} runs in database
          </div>
          <Sparkline runs={historyData.runs} />
        </div>
      )}
      <div style={{ display: 'grid', gap: 8 }}>
        {(historyData?.runs ?? result.history?.runs ?? []).map((run: HistoryRun, i: number) => (
          <div
            key={`${run.ts}-${i}`}
            style={{
              ...card,
              padding: 10,
              display: 'grid',
              gridTemplateColumns: 'auto 1fr auto auto',
              gap: 10,
              alignItems: 'center',
            }}
          >
            <span style={badge(scoreColor(run.performance_score ?? 0))}>{scoreGrade(run.performance_score ?? 0)}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>Score: {run.performance_score ?? 'n/a'}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                {run.ts ? new Date(run.ts).toLocaleString() : 'n/a'} &middot; {run.device ?? 'n/a'}
              </div>
            </div>
            <div style={{ fontSize: 12 }}>
              LCP: <strong>{run.lcp_ms ?? 'n/a'}ms</strong>
            </div>
            <div style={{ fontSize: 12 }}>
              CLS: <strong>{run.cls ?? 'n/a'}</strong>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function MonitoringTab({ result, card, isOfflinePreview, autoFixing, autoFixResult, optimizeSite }: PerfTabProps) {
  type MonitorRow = {
    monitor_id: string;
    name?: string;
    url?: string;
    schedule?: string;
    status?: string;
    target_device?: string;
    target_region?: string;
    alert_channels?: string[];
  };
  type AlertEventRow = {
    event_id?: string;
    created_at?: string;
    monitor_id?: string;
    url?: string;
    status?: string;
    breached_rules?: Array<{ metric?: string; current?: number; threshold?: number }>;
  };

  const [monitorName, setMonitorName] = useState('Primary Monitor');
  const [monitorSchedule, setMonitorSchedule] = useState('daily');
  const [alertChannels, setAlertChannels] = useState('email');
  const [monitors, setMonitors] = useState<MonitorRow[]>([]);
  const [monitorEvents, setMonitorEvents] = useState<AlertEventRow[]>([]);
  const [loadingMonitors, setLoadingMonitors] = useState(false);
  const [monitorError, setMonitorError] = useState('');
  const [runningMonitorId, setRunningMonitorId] = useState<string | null>(null);
  const monitorInputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box',
  };

  const loadMonitors = useCallback(async () => {
    setLoadingMonitors(true);
    setMonitorError('');
    try {
      const monitorData = await apiGet<{ count: number; monitors: MonitorRow[] }>(
        '/seo-platform/performance/monitors',
        DEFAULT_TENANT_ID
      );
      setMonitors(monitorData.monitors ?? []);
      const eventsData = await apiGet<{ count: number; events: AlertEventRow[] }>(
        '/seo-platform/performance/alerts/events',
        DEFAULT_TENANT_ID
      );
      setMonitorEvents(eventsData.events ?? []);
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : 'Failed to load monitors.');
    } finally {
      setLoadingMonitors(false);
    }
  }, []);

  useEffect(() => {
    void loadMonitors();
  }, [loadMonitors]);

  const createMonitor = useCallback(async () => {
    if (!result?.url) return;
    setMonitorError('');
    try {
      const channels = alertChannels
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      await apiSend(
        '/seo-platform/performance/monitor/create',
        'POST',
        {
          name: monitorName.trim() || 'Primary Monitor',
          url: result.url,
          schedule: monitorSchedule,
          target_device: result.target_device,
          target_region: result.target_region,
          connection: '4g',
          browser: 'chrome',
          include_video: true,
          adblock_enabled: false,
          capture_har: true,
          alerts_enabled: true,
          alert_channels: channels.length ? channels : ['email'],
          alert_targets: [],
          notes: 'Created from performance monitoring tab',
        },
        DEFAULT_TENANT_ID
      );
      await loadMonitors();
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : 'Failed to create monitor.');
    }
  }, [alertChannels, loadMonitors, monitorName, monitorSchedule, result]);

  const runMonitorNow = useCallback(
    async (monitorId: string) => {
      setRunningMonitorId(monitorId);
      setMonitorError('');
      try {
        await apiSend(`/seo-platform/performance/monitors/${monitorId}/run`, 'POST', {}, DEFAULT_TENANT_ID);
        await loadMonitors();
      } catch (err) {
        setMonitorError(err instanceof Error ? err.message : 'Failed to run monitor.');
      } finally {
        setRunningMonitorId(null);
      }
    },
    [loadMonitors]
  );

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Monitor Configuration</div>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Monitor Name</div>
            <input value={monitorName} onChange={(e) => setMonitorName(e.target.value)} style={monitorInputStyle} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Schedule</div>
            <select
              value={monitorSchedule}
              onChange={(e) => setMonitorSchedule(e.target.value)}
              style={monitorInputStyle}
            >
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Alert Channels (comma-separated)</div>
            <input
              value={alertChannels}
              onChange={(e) => setAlertChannels(e.target.value)}
              placeholder="email,slack"
              style={monitorInputStyle}
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          <button type="button" onClick={createMonitor} style={btn(true)}>
            Create Monitor From Current Audit
          </button>
          <button type="button" onClick={() => void loadMonitors()} style={btn()} disabled={loadingMonitors}>
            {loadingMonitors ? 'Refreshing...' : 'Refresh Monitors'}
          </button>
        </div>
        {monitorError && <div style={{ marginTop: 8, color: '#dc2626', fontSize: 12 }}>{monitorError}</div>}
      </div>

      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Monitored Pages</div>
        {monitors.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>No monitors yet. Create one from the current URL.</div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {monitors.map((m) => (
              <div
                key={m.monitor_id}
                style={{
                  ...card,
                  padding: 10,
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{m.name ?? 'Monitor'}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                    {m.url} · {m.schedule} · {m.target_device}/{m.target_region}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                    Channels: {(m.alert_channels ?? []).join(', ') || 'email'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={badge(m.status === 'active' ? '#22c55e' : '#f59e0b')}>{m.status ?? 'active'}</span>
                  <button
                    type="button"
                    onClick={() => void runMonitorNow(m.monitor_id)}
                    style={btn(true)}
                    disabled={runningMonitorId === m.monitor_id}
                  >
                    {runningMonitorId === m.monitor_id ? 'Running...' : 'Run Now'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Recent Alert Events</div>
        {monitorEvents.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>No triggered alert events yet.</div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {monitorEvents.slice(0, 8).map((event) => (
              <div key={event.event_id} style={{ ...card, padding: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <div style={{ fontWeight: 700, fontSize: 12 }}>{event.url}</div>
                  <span style={badge(event.status === 'triggered' ? '#ef4444' : '#22c55e')}>{event.status}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                  {event.created_at ? new Date(event.created_at).toLocaleString() : 'n/a'}
                </div>
                {(event.breached_rules ?? []).length > 0 && (
                  <ul style={{ margin: '8px 0 0', paddingInlineStart: 18, fontSize: 12 }}>
                    {(event.breached_rules ?? []).map((rule, idx) => (
                      <li key={`${event.event_id}-rule-${idx}`}>
                        {rule.metric}: {rule.current} exceeded {rule.threshold}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <section style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 16 }}>
          Alert Monitoring
          {result.alerts?.status && (
            <span style={badge(result.alerts.status === 'healthy' ? '#22c55e' : '#ef4444')}>
              {result.alerts.status}
            </span>
          )}
        </div>
        {(result.alerts?.rules ?? []).length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>No alert rules configured.</div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {(result.alerts?.rules ?? []).map((rule, i) => {
              const ok = rule.state === 'ok';
              const pct = rule.threshold && rule.current ? Math.min(100, (rule.current / rule.threshold) * 100) : 0;
              return (
                <div
                  key={`${rule.metric}-${i}`}
                  style={{ ...card, padding: 12, borderLeft: `3px solid ${ok ? '#22c55e' : '#ef4444'}` }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 8,
                      flexWrap: 'wrap',
                      gap: 8,
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, fontSize: 13 }}>{rule.metric}</span>
                      <span style={badge(ok ? '#22c55e' : '#ef4444')}>{rule.state ?? 'unknown'}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Current: <strong>{rule.current ?? 'n/a'}</strong> / Threshold: <strong>{rule.threshold}</strong>
                    </div>
                  </div>
                  <div style={{ height: 6, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: ok ? '#22c55e' : '#ef4444',
                        borderRadius: 3,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div style={{ marginTop: 20 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Auto-SEO Module Optimizer</div>
          <p style={{ fontSize: 12, color: 'var(--muted)', margin: '0 0 12px' }}>
            Automatically apply fixes across all SEO modules for this domain using AI analysis.
          </p>
          <button
            type="button"
            onClick={optimizeSite}
            disabled={autoFixing}
            style={{ ...btn(true), background: '#6366f1', color: '#fff' }}
          >
            {autoFixing ? 'Auto-fixing SEO modules...' : 'Auto-Fix All SEO Modules'}
          </button>
          {autoFixResult && (
            <div style={{ marginTop: 12, fontSize: 12, color: 'var(--muted)' }}>
              Last run: {new Date(autoFixResult.applied_at).toLocaleString()} &middot;{' '}
              {autoFixResult.fixes_applied.length} fixes applied &middot; {autoFixResult.total_gain_ms}ms total gain
            </div>
          )}
        </div>
      </section>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function GtmetrixApiTab({ result, card, isOfflinePreview, autoFixing, autoFixResult, optimizeSite }: PerfTabProps) {
  type PerfVendor = { name?: string; role?: string };
  type PerfCapability = { feature?: string; status?: string; endpoint?: string };
  type PerfAsyncCreateResp = { test_id?: string; status?: string };
  type PerfAsyncStatusResp = { status?: string; error?: string; result?: PerformanceAuditResponse };
  type PerfShareResp = { share_token?: string; share_url?: string; expires_at?: string; analysis_id?: string };
  type PerfSharedReportResp = { analysis_id?: string; module?: string; created_at?: string };
  type PerfCompareResp = {
    score_delta?: number;
    core_web_vitals_delta?: { lcp_ms?: number; inp_ms?: number; cls?: number };
    regression_detected?: boolean;
    summary?: string;
    recommendation?: string;
  };
  type CruxPoint = {
    month?: string;
    lcp_p75_ms?: number;
    inp_p75_ms?: number;
    cls_p75?: number;
    sample_size?: number;
  };

  const [intelError, setIntelError] = useState('');
  const [vendors, setVendors] = useState<PerfVendor[]>([]);
  const [capabilities, setCapabilities] = useState<PerfCapability[]>([]);
  const [coveragePct, setCoveragePct] = useState<number>(0);
  const [loadingIntel, setLoadingIntel] = useState(false);

  const [asyncTestId, setAsyncTestId] = useState('');
  const [asyncStatus, setAsyncStatus] = useState('idle');
  const [asyncError, setAsyncError] = useState('');
  const [asyncResult, setAsyncResult] = useState<PerformanceAuditResponse | null>(null);
  const [runningAsyncTest, setRunningAsyncTest] = useState(false);

  const [shareExpiresHours, setShareExpiresHours] = useState(168);
  const [shareToken, setShareToken] = useState('');
  const [shareUrl, setShareUrl] = useState('');
  const [shareError, setShareError] = useState('');
  const [shareLookupToken, setShareLookupToken] = useState('');
  const [shareLookupResult, setShareLookupResult] = useState<PerfSharedReportResp | null>(null);
  const [resolvingShare, setResolvingShare] = useState(false);

  const [baselineAnalysisId, setBaselineAnalysisId] = useState(result.analysis_id ?? '');
  const [candidateAnalysisId, setCandidateAnalysisId] = useState('');
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const [compareResult, setCompareResult] = useState<PerfCompareResp | null>(null);

  const [cruxMonths, setCruxMonths] = useState(6);
  const [cruxPoints, setCruxPoints] = useState<CruxPoint[]>([]);
  const [loadingCrux, setLoadingCrux] = useState(false);

  const monitorInputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box',
  };

  const loadIntel = useCallback(async () => {
    setLoadingIntel(true);
    setIntelError('');
    try {
      const [caps, vendorData] = await Promise.all([
        apiGet<{ coverage_pct?: number; features?: PerfCapability[] }>(
          '/seo-platform/performance/capabilities',
          DEFAULT_TENANT_ID
        ),
        apiGet<{ third_parties?: PerfVendor[] }>('/seo-platform/performance/vendors', DEFAULT_TENANT_ID),
      ]);
      setCoveragePct(caps.coverage_pct ?? 0);
      setCapabilities(caps.features ?? []);
      setVendors(vendorData.third_parties ?? []);
    } catch (err) {
      setIntelError(err instanceof Error ? err.message : 'Failed to load GTmetrix API capabilities.');
    } finally {
      setLoadingIntel(false);
    }
  }, []);

  const loadCruxHistory = useCallback(async () => {
    if (!result?.url) {
      setCruxPoints([]);
      return;
    }
    setLoadingCrux(true);
    try {
      const data = await apiGet<{ points?: CruxPoint[] }>(
        `/seo-platform/performance/crux/history?url=${encodeURIComponent(result.url)}&months=${cruxMonths}`,
        DEFAULT_TENANT_ID
      );
      setCruxPoints(data.points ?? []);
    } catch {
      setCruxPoints([]);
    }
    setLoadingCrux(false);
  }, [cruxMonths, result?.url]);

  useEffect(() => {
    void loadIntel();
  }, [loadIntel]);

  useEffect(() => {
    void loadCruxHistory();
  }, [loadCruxHistory]);

  useEffect(() => {
    if (result.analysis_id) {
      setBaselineAnalysisId(result.analysis_id);
    }
  }, [result.analysis_id]);

  const wait = useCallback((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)), []);

  const runAsyncTest = useCallback(async () => {
    setRunningAsyncTest(true);
    setAsyncError('');
    setAsyncResult(null);
    setAsyncStatus('queued');
    try {
      const createResp = await apiSend<PerfAsyncCreateResp>(
        '/seo-platform/performance/tests',
        'POST',
        {
          url: result.url,
          target_device: result.target_device,
          target_region: result.target_region,
          connection: '4g',
          browser: 'chrome',
          include_video: true,
          adblock_enabled: false,
          capture_har: true,
          notes: 'Triggered from GTmetrix API-style async runner',
        },
        DEFAULT_TENANT_ID
      );

      const createdTestId = createResp.test_id ?? '';
      if (!createdTestId) {
        setAsyncError('Async test did not return a test id.');
        setRunningAsyncTest(false);
        return;
      }
      setAsyncTestId(createdTestId);

      for (let i = 0; i < 30; i += 1) {
        const poll = await apiGet<PerfAsyncStatusResp>(
          `/seo-platform/performance/tests/${encodeURIComponent(createdTestId)}`,
          DEFAULT_TENANT_ID
        );
        const status = poll.status ?? 'unknown';
        setAsyncStatus(status);

        if (status === 'completed') {
          if (poll.result) {
            setAsyncResult(poll.result);
            if (poll.result.analysis_id) {
              setCandidateAnalysisId(poll.result.analysis_id);
            }
          }
          setRunningAsyncTest(false);
          return;
        }
        if (status === 'failed') {
          setAsyncError(poll.error || 'Async test failed.');
          setRunningAsyncTest(false);
          return;
        }
        await wait(2000);
      }
      setAsyncError('Async polling timed out. You can keep polling with the test id.');
    } catch (err) {
      setAsyncError(err instanceof Error ? err.message : 'Failed to run async test.');
    }
    setRunningAsyncTest(false);
  }, [result, wait]);

  const createShareLink = useCallback(async () => {
    if (!result.analysis_id) return;
    setShareError('');
    try {
      const data = await apiSend<PerfShareResp>(
        `/seo-platform/performance/report/${encodeURIComponent(result.analysis_id)}/share`,
        'POST',
        { expires_hours: shareExpiresHours, visibility: 'token' },
        DEFAULT_TENANT_ID
      );
      setShareToken(data.share_token ?? '');
      setShareUrl(data.share_url ?? '');
      setShareLookupToken(data.share_token ?? '');
    } catch (err) {
      setShareError(err instanceof Error ? err.message : 'Failed to create share token.');
    }
  }, [result.analysis_id, shareExpiresHours]);

  const resolveShareToken = useCallback(async () => {
    if (!shareLookupToken.trim()) return;
    setResolvingShare(true);
    setShareError('');
    setShareLookupResult(null);
    try {
      const data = await apiGet<PerfSharedReportResp>(
        `/seo-platform/performance/report/shared/${encodeURIComponent(shareLookupToken.trim())}`,
        DEFAULT_TENANT_ID
      );
      setShareLookupResult(data);
      if (data.analysis_id) {
        setCandidateAnalysisId(data.analysis_id);
      }
    } catch (err) {
      setShareError(err instanceof Error ? err.message : 'Failed to resolve share token.');
    }
    setResolvingShare(false);
  }, [shareLookupToken]);

  const runComparison = useCallback(async () => {
    if (!baselineAnalysisId.trim() || !candidateAnalysisId.trim()) return;
    setCompareLoading(true);
    setCompareError('');
    setCompareResult(null);
    try {
      const data = await apiSend<PerfCompareResp>(
        '/seo-platform/performance/reports/compare',
        'POST',
        {
          baseline_analysis_id: baselineAnalysisId.trim(),
          candidate_analysis_id: candidateAnalysisId.trim(),
        },
        DEFAULT_TENANT_ID
      );
      setCompareResult(data);
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : 'Failed to compare reports.');
    }
    setCompareLoading(false);
  }, [baselineAnalysisId, candidateAnalysisId]);

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={card}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 8,
            alignItems: 'center',
            marginBottom: 10,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 14 }}>GTmetrix API Coverage & Vendors</div>
          <button type="button" onClick={() => void loadIntel()} style={btn()} disabled={loadingIntel}>
            {loadingIntel ? 'Refreshing...' : 'Refresh Capabilities'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
          <span style={badge(coveragePct >= 100 ? '#22c55e' : coveragePct >= 80 ? '#f59e0b' : '#ef4444')}>
            Coverage {coveragePct.toFixed(2)}%
          </span>
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>
            {capabilities.length} capability checks · {vendors.length} integrated vendors
          </span>
        </div>
        {intelError && <div style={{ color: '#dc2626', fontSize: 12, marginBottom: 8 }}>{intelError}</div>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 8 }}>
          {vendors.slice(0, 9).map((v, idx) => (
            <div key={`${v.name}-${idx}`} style={{ ...card, padding: 10 }}>
              <div style={{ fontWeight: 700, fontSize: 12 }}>{v.name ?? 'Vendor'}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{v.role ?? 'n/a'}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Async GTmetrix API-Style Test Runner</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <button type="button" onClick={() => void runAsyncTest()} style={btn(true)} disabled={runningAsyncTest}>
            {runningAsyncTest ? 'Running Async Test...' : 'Run Async Test'}
          </button>
          {asyncTestId && <span style={{ fontSize: 12, color: 'var(--muted)' }}>Test ID: {asyncTestId}</span>}
          {asyncStatus && <span style={badge(asyncStatus === 'completed' ? '#22c55e' : '#f59e0b')}>{asyncStatus}</span>}
        </div>
        {asyncError && <div style={{ marginTop: 8, color: '#dc2626', fontSize: 12 }}>{asyncError}</div>}
        {asyncResult && (
          <div style={{ ...card, marginTop: 10, padding: 10 }}>
            <div style={{ fontSize: 12 }}>
              Async report complete · Score <strong>{asyncResult.performance_score}</strong> · Analysis ID{' '}
              <strong>{asyncResult.analysis_id}</strong>
            </div>
          </div>
        )}
      </div>

      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Report Sharing & Comparison</div>
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Share Expiry (hours)</div>
              <input
                type="number"
                value={shareExpiresHours}
                onChange={(e) => setShareExpiresHours(Math.max(1, Math.min(720, Number(e.target.value) || 168)))}
                style={monitorInputStyle}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'end' }}>
              <button type="button" onClick={() => void createShareLink()} style={btn(true)}>
                Share Current Report
              </button>
            </div>
          </div>
          {(shareToken || shareUrl) && (
            <div style={{ ...card, padding: 10, fontSize: 12 }}>
              <div>
                Share Token: <strong>{shareToken}</strong>
              </div>
              <div style={{ color: 'var(--muted)' }}>Share Path: {shareUrl}</div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Resolve Share Token</div>
              <input
                value={shareLookupToken}
                onChange={(e) => setShareLookupToken(e.target.value)}
                placeholder="paste share token"
                style={monitorInputStyle}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'end' }}>
              <button type="button" onClick={() => void resolveShareToken()} style={btn()} disabled={resolvingShare}>
                {resolvingShare ? 'Resolving...' : 'Resolve Shared Report'}
              </button>
            </div>
          </div>
          {shareLookupResult && (
            <div style={{ ...card, padding: 10, fontSize: 12 }}>
              Shared report resolved · Analysis <strong>{shareLookupResult.analysis_id ?? 'n/a'}</strong> · Module{' '}
              <strong>{shareLookupResult.module ?? 'n/a'}</strong>
            </div>
          )}
          {shareError && <div style={{ color: '#dc2626', fontSize: 12 }}>{shareError}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Baseline Analysis ID</div>
              <input
                value={baselineAnalysisId}
                onChange={(e) => setBaselineAnalysisId(e.target.value)}
                style={monitorInputStyle}
              />
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Candidate Analysis ID</div>
              <input
                value={candidateAnalysisId}
                onChange={(e) => setCandidateAnalysisId(e.target.value)}
                placeholder="from async test or shared report"
                style={monitorInputStyle}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'end' }}>
              <button type="button" onClick={() => void runComparison()} style={btn(true)} disabled={compareLoading}>
                {compareLoading ? 'Comparing...' : 'Compare Reports'}
              </button>
            </div>
          </div>
          {compareError && <div style={{ color: '#dc2626', fontSize: 12 }}>{compareError}</div>}
          {compareResult && (
            <div style={{ ...card, padding: 10, fontSize: 12 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={badge(compareResult.regression_detected ? '#ef4444' : '#22c55e')}>
                  {compareResult.summary ?? 'comparison'}
                </span>
                <span>
                  Score delta: <strong>{compareResult.score_delta ?? 0}</strong>
                </span>
                <span>
                  LCP delta: <strong>{compareResult.core_web_vitals_delta?.lcp_ms ?? 0}ms</strong>
                </span>
                <span>
                  INP delta: <strong>{compareResult.core_web_vitals_delta?.inp_ms ?? 0}ms</strong>
                </span>
                <span>
                  CLS delta: <strong>{compareResult.core_web_vitals_delta?.cls ?? 0}</strong>
                </span>
              </div>
              <div style={{ marginTop: 6, color: 'var(--muted)' }}>{compareResult.recommendation}</div>
            </div>
          )}
        </div>
      </div>

      <div style={card}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <div style={{ fontWeight: 700, fontSize: 14 }}>CrUX-Style Trend Timeline</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select
              value={cruxMonths}
              onChange={(e) => setCruxMonths(Number(e.target.value) || 6)}
              style={monitorInputStyle}
            >
              <option value={1}>1 month</option>
              <option value={3}>3 months</option>
              <option value={6}>6 months</option>
            </select>
            <button type="button" onClick={() => void loadCruxHistory()} style={btn()} disabled={loadingCrux}>
              {loadingCrux ? 'Loading...' : 'Load CrUX'}
            </button>
          </div>
        </div>
        {cruxPoints.length > 0 ? (
          <div style={{ marginTop: 10 }}>
            <AreaChart
              points={cruxPoints.map((p) => p.lcp_p75_ms ?? 0)}
              labels={cruxPoints.map((p) => p.month ?? '')}
              color="#6366f1"
              height={80}
            />
            <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
              {cruxPoints.map((p) => (
                <div key={p.month} style={{ ...card, padding: 10, fontSize: 12 }}>
                  <strong>{p.month}</strong> · LCP p75 {p.lcp_p75_ms ?? 0}ms · INP p75 {p.inp_p75_ms ?? 0}ms · CLS p75{' '}
                  {p.cls_p75 ?? 0} · samples {(p.sample_size ?? 0).toLocaleString()}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ marginTop: 10, color: 'var(--muted)', fontSize: 12 }}>
            No CrUX trend points yet for this URL.
          </div>
        )}
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function KeywordsTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Total Tracked', value: '1,842', color: 'var(--text)' },
          { label: 'Top-3 Rank', value: '147', color: '#22c55e' },
          { label: 'Top-10 Rank', value: '384', color: '#6366f1' },
          { label: 'Rising (+5)', value: '63', color: '#22c55e' },
          { label: 'Falling (-5)', value: '28', color: '#ef4444' },
          { label: 'Avg. Difficulty', value: '48', color: '#f59e0b' },
          { label: 'Avg. Search Vol.', value: '2,340', color: '#6366f1' },
          { label: 'Avg. CPC ($)', value: '$1.84', color: '#ec4899' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Keyword Distribution by Intent</div>
        <MiniBarChart
          items={[
            { label: 'Informational', value: 680, color: '#6366f1', max: 1842, suffix: ' kws' },
            { label: 'Navigational', value: 240, color: '#6366f1', max: 1842, suffix: ' kws' },
            { label: 'Commercial', value: 520, color: '#f59e0b', max: 1842, suffix: ' kws' },
            { label: 'Transactional', value: 402, color: '#22c55e', max: 1842, suffix: ' kws' },
          ]}
        />
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Top Keywords</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Keyword', 'Rank', 'Prev', 'Δ', 'Volume', 'Difficulty', 'CPC', 'Intent', 'Feature'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  kw: 'nextjs dashboard template',
                  rank: 2,
                  prev: 5,
                  vol: 8400,
                  diff: 62,
                  cpc: 3.2,
                  intent: 'commercial',
                  feat: 'Snippet',
                }, // NOSONAR
                {
                  kw: 'react performance audit',
                  rank: 4,
                  prev: 4,
                  vol: 3600,
                  diff: 48,
                  cpc: 2.8,
                  intent: 'informational',
                  feat: 'PAA',
                }, // NOSONAR
                {
                  kw: 'seo performance monitoring tool',
                  rank: 7,
                  prev: 12,
                  vol: 5200,
                  diff: 55,
                  cpc: 4.1,
                  intent: 'commercial',
                  feat: '—',
                }, // NOSONAR
                {
                  kw: 'web vitals checker',
                  rank: 1,
                  prev: 2,
                  vol: 12400,
                  diff: 71,
                  cpc: 2.4,
                  intent: 'informational',
                  feat: 'Snippet',
                }, // NOSONAR
                {
                  kw: 'lighthouse score improve',
                  rank: 9,
                  prev: 18,
                  vol: 4800,
                  diff: 44,
                  cpc: 1.9,
                  intent: 'informational',
                  feat: 'PAA',
                }, // NOSONAR
                {
                  kw: 'buy seo audit software',
                  rank: 14,
                  prev: 11,
                  vol: 2100,
                  diff: 38,
                  cpc: 6.8,
                  intent: 'transactional',
                  feat: 'Shopping',
                }, // NOSONAR
              ].map((k, i) => {
                // NOSONAR
                const delta = k.prev - k.rank;
                return (
                  <tr key={`kw-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '7px 8px', fontWeight: 600 }}>{k.kw}</td>
                    <td
                      style={{
                        padding: '7px 8px',
                        fontWeight: 800,
                        color: k.rank <= 3 ? '#22c55e' : k.rank <= 10 ? '#6366f1' : 'var(--text)',
                      }}
                    >
                      #{k.rank}
                    </td>
                    <td style={{ padding: '7px 8px', color: 'var(--muted)' }}>#{k.prev}</td>
                    <td
                      style={{
                        padding: '7px 8px',
                        fontWeight: 700,
                        color: delta > 0 ? '#22c55e' : delta < 0 ? '#ef4444' : 'var(--muted)',
                      }}
                    >
                      {delta > 0 ? `+${delta}` : delta === 0 ? '—' : delta}
                    </td>
                    <td style={{ padding: '7px 8px' }}>{k.vol.toLocaleString()}</td>
                    <td style={{ padding: '7px 8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <div style={{ width: 40, height: 4, background: 'var(--line)', borderRadius: 2 }}>
                          <div
                            style={{
                              width: `${k.diff}%`,
                              height: '100%',
                              background: k.diff > 60 ? '#ef4444' : k.diff > 40 ? '#f59e0b' : '#22c55e',
                              borderRadius: 2,
                            }}
                          />
                        </div>
                        <span>{k.diff}</span>
                      </div>
                    </td>
                    <td style={{ padding: '7px 8px' }}>${k.cpc.toFixed(2)}</td>
                    <td style={{ padding: '7px 8px' }}>
                      <span style={badge('#6366f1')}>{k.intent}</span>
                    </td>
                    <td style={{ padding: '7px 8px', color: '#8b5cf6', fontSize: 11 }}>{k.feat}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Keyword Opportunity Matrix</div>
        <MiniBarChart
          items={[
            { label: 'Quick Wins (low diff, top 20)', value: 84, color: '#22c55e', max: 200, suffix: ' kws' },
            { label: 'High Value (CPC > $3)', value: 128, color: '#f59e0b', max: 200, suffix: ' kws' },
            { label: 'Featured Snippet Targets', value: 47, color: '#6366f1', max: 200, suffix: ' kws' },
            { label: 'Near-Page-1 (pos 11–20)', value: 192, color: '#6366f1', max: 200, suffix: ' kws' },
          ]}
        />
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SeoRankingTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Domain Authority', value: '54', color: '#22c55e' },
          { label: 'Page Authority Avg', value: '42', color: '#6366f1' },
          { label: 'Pages Ranked', value: '284', color: 'var(--text)' },
          { label: 'Top-3 Pages', value: '38', color: '#22c55e' },
          { label: 'Featured Snippets', value: '12', color: '#6366f1' },
          { label: 'Winners 30d', value: '+47', color: '#22c55e' },
          { label: 'Losers 30d', value: '-19', color: '#ef4444' },
          { label: 'Avg. Position', value: '14.2', color: '#f59e0b' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Rank Distribution</div>
        <MiniBarChart
          items={[
            { label: 'Position 1–3', value: 38, color: '#22c55e', max: 284, suffix: ' pages' },
            { label: 'Position 4–10', value: 96, color: '#6366f1', max: 284, suffix: ' pages' },
            { label: 'Position 11–20', value: 72, color: '#f59e0b', max: 284, suffix: ' pages' },
            { label: 'Position 21–50', value: 54, color: '#6366f1', max: 284, suffix: ' pages' },
            { label: 'Position 51–100', value: 24, color: '#ef4444', max: 284, suffix: ' pages' },
          ]}
        />
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Top Ranking Pages</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Page', 'Pos', 'Δ 30d', 'Traffic', 'Keywords', 'Impressions', 'CTR', 'Feature'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  page: '/blog/web-vitals-guide',
                  pos: 1,
                  delta: 2,
                  traffic: 8400,
                  kws: 48,
                  impr: 124000,
                  ctr: 6.8,
                  feat: 'Snippet',
                },
                {
                  page: '/tools/lighthouse-checker',
                  pos: 3,
                  delta: 4,
                  traffic: 5200,
                  kws: 32,
                  impr: 84000,
                  ctr: 6.2,
                  feat: 'PAA',
                },
                { page: '/pricing', pos: 7, delta: -2, traffic: 2800, kws: 14, impr: 42000, ctr: 6.7, feat: '—' },
                {
                  page: '/blog/nextjs-performance',
                  pos: 5,
                  delta: 8,
                  traffic: 3600,
                  kws: 28,
                  impr: 56000,
                  ctr: 6.4,
                  feat: '—',
                },
                {
                  page: '/features/audit',
                  pos: 12,
                  delta: -5,
                  traffic: 1200,
                  kws: 19,
                  impr: 28000,
                  ctr: 4.3,
                  feat: '—',
                },
              ].map((p, i) => (
                <tr key={`rp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontFamily: 'monospace', fontSize: 11, color: '#6366f1' }}>
                    {p.page}
                  </td>
                  <td
                    style={{
                      padding: '7px 8px',
                      fontWeight: 800,
                      color: p.pos <= 3 ? '#22c55e' : p.pos <= 10 ? '#6366f1' : 'var(--text)',
                    }}
                  >
                    #{p.pos}
                  </td>
                  <td style={{ padding: '7px 8px', fontWeight: 700, color: p.delta > 0 ? '#22c55e' : '#ef4444' }}>
                    {p.delta > 0 ? `+${p.delta}` : p.delta}
                  </td>
                  <td style={{ padding: '7px 8px' }}>{p.traffic.toLocaleString()}</td>
                  <td style={{ padding: '7px 8px' }}>{p.kws}</td>
                  <td style={{ padding: '7px 8px' }}>{p.impr.toLocaleString()}</td>
                  <td style={{ padding: '7px 8px', color: p.ctr > 6 ? '#22c55e' : '#f59e0b' }}>{p.ctr}%</td>
                  <td style={{ padding: '7px 8px', color: '#8b5cf6', fontSize: 11 }}>{p.feat}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>30d Rank Trend</div>
          <AreaChart
            points={[18.4, 17.2, 16.8, 15.9, 15.1, 14.8, 14.2]}
            labels={['Apr 1', 'Apr 6', 'Apr 11', 'Apr 16', 'Apr 21', 'Apr 26', 'May 1']}
            color="#22c55e"
            height={70}
          />
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Competitor Gap</div>
          <MiniBarChart
            items={[
              { label: 'You', value: 54, color: '#6366f1', max: 100, suffix: ' DA' },
              { label: 'Competitor A', value: 68, color: '#ef4444', max: 100, suffix: ' DA' },
              { label: 'Competitor B', value: 61, color: '#f59e0b', max: 100, suffix: ' DA' },
              { label: 'Competitor C', value: 49, color: '#22c55e', max: 100, suffix: ' DA' },
            ]}
          />
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AiModelsRankingTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ ...card, borderLeft: '4px solid #6366f1' }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>AI Search Visibility</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          How often AI models (ChatGPT, Gemini, Perplexity, Claude) cite and surface your content in responses.
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Overall AI Score', value: '71/100', color: '#6366f1' },
          { label: 'Total Citations', value: '428', color: '#22c55e' },
          { label: 'ChatGPT Mentions', value: '184', color: '#10b981' },
          { label: 'Perplexity Rank', value: '#3', color: '#6366f1' },
          { label: 'Gemini Citations', value: '112', color: '#f59e0b' },
          { label: 'Claude Citations', value: '132', color: '#8b5cf6' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Citation Share by AI Model</div>
        <MiniBarChart
          items={[
            { label: 'ChatGPT (GPT-4o)', value: 184, color: '#10b981', max: 428, suffix: ' cites' },
            { label: 'Claude 3.5 Sonnet', value: 132, color: '#8b5cf6', max: 428, suffix: ' cites' },
            { label: 'Gemini 2.5 Pro', value: 112, color: '#f59e0b', max: 428, suffix: ' cites' },
            { label: 'Perplexity', value: 0, color: '#6366f1', max: 428, suffix: ' cites' },
          ]}
        />
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>AI Visibility by Topic</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Topic / Query', 'ChatGPT', 'Gemini', 'Claude', 'Perplexity', 'Avg. Position', 'Trend'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  topic: 'Best web performance tools',
                  gpt: true,
                  gem: true,
                  claude: true,
                  pplx: false,
                  pos: 1,
                  trend: '+2',
                },
                {
                  topic: 'How to improve Core Web Vitals',
                  gpt: true,
                  gem: false,
                  claude: true,
                  pplx: true,
                  pos: 2,
                  trend: '+4',
                },
                {
                  topic: 'SEO audit software 2025',
                  gpt: false,
                  gem: true,
                  claude: true,
                  pplx: false,
                  pos: 3,
                  trend: '0',
                },
                {
                  topic: 'Lighthouse score optimization',
                  gpt: true,
                  gem: true,
                  claude: false,
                  pplx: true,
                  pos: 2,
                  trend: '+1',
                },
                {
                  topic: 'Next.js SEO checklist',
                  gpt: false,
                  gem: false,
                  claude: true,
                  pplx: true,
                  pos: 4,
                  trend: '-1',
                },
              ].map((r, i) => (
                <tr key={`ai-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontWeight: 600 }}>{r.topic}</td>
                  <td style={{ padding: '7px 8px', textAlign: 'center' }}>
                    <span style={{ color: r.gpt ? '#22c55e' : '#ef4444', fontWeight: 700 }}>{r.gpt ? '✓' : '✗'}</span>
                  </td>
                  <td style={{ padding: '7px 8px', textAlign: 'center' }}>
                    <span style={{ color: r.gem ? '#22c55e' : '#ef4444', fontWeight: 700 }}>{r.gem ? '✓' : '✗'}</span>
                  </td>
                  <td style={{ padding: '7px 8px', textAlign: 'center' }}>
                    <span style={{ color: r.claude ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                      {r.claude ? '✓' : '✗'}
                    </span>
                  </td>
                  <td style={{ padding: '7px 8px', textAlign: 'center' }}>
                    <span style={{ color: r.pplx ? '#22c55e' : '#ef4444', fontWeight: 700 }}>{r.pplx ? '✓' : '✗'}</span>
                  </td>
                  <td style={{ padding: '7px 8px', fontWeight: 700 }}>#{r.pos}</td>
                  <td
                    style={{
                      padding: '7px 8px',
                      color: r.trend.startsWith('+') ? '#22c55e' : r.trend.startsWith('-') ? '#ef4444' : 'var(--muted)',
                      fontWeight: 700,
                    }}
                  >
                    {r.trend}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>AIO Improvement Recommendations</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {[
            { tip: 'Add structured FAQ sections — AI models prefer direct Q&A format for citations', priority: 'high' },
            { tip: 'Increase E-E-A-T signals: author bio, citations, publication dates', priority: 'high' },
            { tip: 'Target conversational long-tail queries matching AI search behavior', priority: 'medium' },
            { tip: 'Add concise summaries at the top of key articles (TLDR blocks)', priority: 'medium' },
          ].map((r, i) => (
            <div
              key={`aiop-${i}`}
              style={{
                display: 'flex',
                gap: 10,
                alignItems: 'flex-start',
                padding: '8px 10px',
                background: 'var(--bg)',
                borderRadius: 8,
                border: '1px solid var(--line)',
                fontSize: 12,
              }}
            >
              <span style={badge(r.priority === 'high' ? '#ef4444' : '#f59e0b')}>{r.priority}</span>
              <span>{r.tip}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function HashtagsTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Tracked Hashtags', value: '248', color: 'var(--text)' },
          { label: 'Trending Now', value: '14', color: '#22c55e' },
          { label: 'Avg. Reach', value: '84K', color: '#6366f1' },
          { label: 'Engagement Rate', value: '3.8%', color: '#f59e0b' },
          { label: 'Brand Mentions', value: '1,240', color: '#6366f1' },
          { label: 'Competitor Tags', value: '38', color: '#ef4444' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Trending Hashtags by Platform</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Hashtag', 'Platform', 'Posts', 'Reach', 'Engagement', 'Growth 7d', 'Recommendation'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  tag: '#webperformance',
                  platform: 'X',
                  posts: '48K',
                  reach: '2.1M',
                  eng: '4.2%',
                  growth: '+18%',
                  rec: 'Use now',
                },
                {
                  tag: '#coreviews',
                  platform: 'LinkedIn',
                  posts: '12K',
                  reach: '840K',
                  eng: '2.8%',
                  growth: '+31%',
                  rec: 'Trending',
                },
                {
                  tag: '#seotools2025',
                  platform: 'X',
                  posts: '22K',
                  reach: '1.4M',
                  eng: '3.6%',
                  growth: '+12%',
                  rec: 'Use now',
                },
                {
                  tag: '#nextjs',
                  platform: 'TikTok',
                  posts: '180K',
                  reach: '8.4M',
                  eng: '5.1%',
                  growth: '+8%',
                  rec: 'Combine',
                },
                {
                  tag: '#lighthouse',
                  platform: 'YouTube',
                  posts: '6.4K',
                  reach: '480K',
                  eng: '2.1%',
                  growth: '+22%',
                  rec: 'Niche win',
                },
                {
                  tag: '#aiSEO',
                  platform: 'LinkedIn',
                  posts: '18K',
                  reach: '1.2M',
                  eng: '4.8%',
                  growth: '+44%',
                  rec: 'Trending',
                },
              ].map((r, i) => (
                <tr key={`ht-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontWeight: 700, color: '#6366f1' }}>{r.tag}</td>
                  <td style={{ padding: '7px 8px' }}>
                    <span style={badge('#6366f1')}>{r.platform}</span>
                  </td>
                  <td style={{ padding: '7px 8px' }}>{r.posts}</td>
                  <td style={{ padding: '7px 8px' }}>{r.reach}</td>
                  <td style={{ padding: '7px 8px', color: '#22c55e', fontWeight: 700 }}>{r.eng}</td>
                  <td style={{ padding: '7px 8px', color: '#22c55e', fontWeight: 700 }}>{r.growth}</td>
                  <td style={{ padding: '7px 8px' }}>
                    <span style={badge('#22c55e')}>{r.rec}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Hashtag Reach by Platform</div>
        <MiniBarChart
          items={[
            { label: 'X (Twitter)', value: 3500000, color: '#1d9bf0', max: 9000000, suffix: '' },
            { label: 'LinkedIn', value: 2040000, color: '#0077b5', max: 9000000, suffix: '' },
            { label: 'TikTok', value: 8400000, color: '#ff0050', max: 9000000, suffix: '' },
            { label: 'YouTube', value: 480000, color: '#ff0000', max: 9000000, suffix: '' },
            { label: 'Instagram', value: 1200000, color: '#e1306c', max: 9000000, suffix: '' },
          ]}
        />
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function VisibilityTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div
        style={{
          ...card,
          borderLeft: '4px solid #6366f1',
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>Brand Visibility Score</div>
          <div style={{ fontWeight: 900, fontSize: 48, color: '#6366f1', lineHeight: 1 }}>74</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>/ 100 — Good</div>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: 12, marginBottom: 6 }}>
            Organic visibility drives <strong style={{ color: '#22c55e' }}>68%</strong> of total traffic. AI channel
            growing <strong style={{ color: '#6366f1' }}>+44%</strong> MoM.
          </div>
          <div style={{ height: 8, background: 'var(--line)', borderRadius: 4 }}>
            <div
              style={{
                width: '74%',
                height: '100%',
                background: 'linear-gradient(90deg,#6366f1,#22c55e)',
                borderRadius: 4,
              }}
            />
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Organic Search', value: '68%', color: '#22c55e' },
          { label: 'Paid / PPC', value: '12%', color: '#f59e0b' },
          { label: 'Social Organic', value: '8%', color: '#6366f1' },
          { label: 'AI Answers', value: '6%', color: '#6366f1' },
          { label: 'Direct', value: '4%', color: '#ec4899' },
          { label: 'Referral', value: '2%', color: '#10b981' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 20, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Visibility Share by Channel</div>
        <MiniBarChart
          items={[
            { label: 'Google Organic', value: 68, color: '#22c55e', max: 100, suffix: '%' },
            { label: 'Google Paid', value: 12, color: '#f59e0b', max: 100, suffix: '%' },
            { label: 'Social Organic', value: 8, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'AI Engines', value: 6, color: '#6366f1', max: 100, suffix: '%' },
            { label: 'Bing Organic', value: 4, color: '#10b981', max: 100, suffix: '%' },
          ]}
        />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>90-day Visibility Trend</div>
          <AreaChart
            points={[58, 60, 62, 64, 63, 66, 68, 70, 69, 72, 73, 74]}
            labels={['Feb', '', '', 'Mar', '', '', 'Apr', '', '', 'May', '', '']}
            color="#6366f1"
            height={70}
          />
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>SERP Feature Presence</div>
          <MiniBarChart
            items={[
              { label: 'Featured Snippet', value: 12, color: '#22c55e', max: 50, suffix: ' pages' },
              { label: 'People Also Ask', value: 38, color: '#6366f1', max: 50, suffix: ' pages' },
              { label: 'Sitelinks', value: 8, color: '#6366f1', max: 50, suffix: ' pages' },
              { label: 'Image Pack', value: 22, color: '#f59e0b', max: 50, suffix: ' pages' },
            ]}
          />
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LeadsTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Total Leads (30d)', value: '1,284', color: '#22c55e' },
          { label: 'MQLs', value: '348', color: '#6366f1' },
          { label: 'SQLs', value: '124', color: '#6366f1' },
          { label: 'Lead → MQL Rate', value: '27%', color: '#f59e0b' },
          { label: 'MQL → SQL Rate', value: '36%', color: '#f59e0b' },
          { label: 'Avg. CPA', value: '$18.40', color: '#ec4899' },
          { label: 'Leads from Organic', value: '68%', color: '#22c55e' },
          { label: 'Form Fill Rate', value: '4.2%', color: '#10b981' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Lead Source Attribution</div>
        <MiniBarChart
          items={[
            { label: 'Organic Search', value: 874, color: '#22c55e', max: 1284, suffix: ' leads' },
            { label: 'Paid Search', value: 196, color: '#f59e0b', max: 1284, suffix: ' leads' },
            { label: 'Social Organic', value: 128, color: '#6366f1', max: 1284, suffix: ' leads' },
            { label: 'Referral', value: 56, color: '#6366f1', max: 1284, suffix: ' leads' },
            { label: 'AI Referral', value: 30, color: '#8b5cf6', max: 1284, suffix: ' leads' },
          ]}
        />
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Top Lead-Generating Pages</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Page', 'Sessions', 'Leads', 'Conv. Rate', 'CPA', 'Trend'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { page: '/pricing', sessions: 8400, leads: 348, rate: 4.1, cpa: 12.4, trend: '+14%' }, // NOSONAR
                { page: '/features/audit', sessions: 6200, leads: 214, rate: 3.5, cpa: 18.8, trend: '+8%' }, // NOSONAR
                { page: '/blog/web-vitals-guide', sessions: 12400, leads: 186, rate: 1.5, cpa: 24.2, trend: '+22%' }, // NOSONAR
                { page: '/demo', sessions: 3800, leads: 312, rate: 8.2, cpa: 8.4, trend: '+6%' }, // NOSONAR
                { page: '/tools/lighthouse-checker', sessions: 9600, leads: 144, rate: 1.5, cpa: 28.6, trend: '-4%' }, // NOSONAR
              ].map((p, i) => (
                <tr key={`lp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontFamily: 'monospace', fontSize: 11, color: '#6366f1' }}>
                    {p.page}
                  </td>
                  <td style={{ padding: '7px 8px' }}>{p.sessions.toLocaleString()}</td>
                  <td style={{ padding: '7px 8px', fontWeight: 700 }}>{p.leads}</td>
                  <td style={{ padding: '7px 8px', color: p.rate > 3 ? '#22c55e' : '#f59e0b', fontWeight: 700 }}>
                    {p.rate}%
                  </td>
                  <td style={{ padding: '7px 8px' }}>${p.cpa.toFixed(2)}</td>
                  <td
                    style={{
                      padding: '7px 8px',
                      color: p.trend.startsWith('+') ? '#22c55e' : '#ef4444',
                      fontWeight: 700,
                    }}
                  >
                    {p.trend}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Lead Volume 30d</div>
        <AreaChart
          points={[
            32, 38, 41, 36, 44, 48, 52, 46, 58, 62, 54, 68, 72, 64, 70, 74, 68, 80, 84, 76, 88, 92, 86, 94, 96, 88, 100,
            104, 98, 108,
          ]}
          labels={[]}
          color="#22c55e"
          height={70}
        />
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ClicksTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Total Clicks (30d)', value: '284K', color: '#22c55e' },
          { label: 'Impressions', value: '4.2M', color: '#6366f1' },
          { label: 'Avg. CTR', value: '6.8%', color: '#6366f1' },
          { label: 'Avg. Position', value: '14.2', color: '#f59e0b' },
          { label: 'CTR top-3 pos', value: '28%', color: '#22c55e' },
          { label: 'Click Loss to Snippet', value: '18%', color: '#ef4444' },
          { label: 'Mobile Click Share', value: '62%', color: '#ec4899' },
          { label: 'YoY Click Growth', value: '+34%', color: '#22c55e' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>CTR by Position</div>
          <MiniBarChart
            items={[
              { label: 'Position 1', value: 31, color: '#22c55e', max: 35, suffix: '% CTR' },
              { label: 'Position 2', value: 24, color: '#6366f1', max: 35, suffix: '% CTR' },
              { label: 'Position 3', value: 18, color: '#6366f1', max: 35, suffix: '% CTR' },
              { label: 'Position 4–7', value: 9, color: '#f59e0b', max: 35, suffix: '% CTR' },
              { label: 'Position 8–10', value: 5, color: '#ef4444', max: 35, suffix: '% CTR' },
            ]}
          />
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Click Share by Device</div>
          <MiniBarChart
            items={[
              { label: 'Mobile', value: 62, color: '#ec4899', max: 100, suffix: '%' },
              { label: 'Desktop', value: 31, color: '#6366f1', max: 100, suffix: '%' },
              { label: 'Tablet', value: 7, color: '#6366f1', max: 100, suffix: '%' },
            ]}
          />
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Top Pages by Clicks</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Page', 'Clicks', 'Impressions', 'CTR', 'Avg. Pos', 'MoM'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { page: '/blog/web-vitals-guide', clicks: 48400, impr: 712000, ctr: 6.8, pos: 1.4, mom: '+22%' },
                { page: '/tools/lighthouse-checker', clicks: 38200, impr: 584000, ctr: 6.5, pos: 2.8, mom: '+18%' },
                { page: '/pricing', clicks: 28400, impr: 424000, ctr: 6.7, pos: 4.2, mom: '+14%' },
                { page: '/blog/nextjs-performance', clicks: 22400, impr: 348000, ctr: 6.4, pos: 5.1, mom: '+28%' },
                { page: '/demo', clicks: 18800, impr: 248000, ctr: 7.6, pos: 3.6, mom: '+6%' },
              ].map((p, i) => (
                <tr key={`cp-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontFamily: 'monospace', fontSize: 11, color: '#6366f1' }}>
                    {p.page}
                  </td>
                  <td style={{ padding: '7px 8px', fontWeight: 700 }}>{p.clicks.toLocaleString()}</td>
                  <td style={{ padding: '7px 8px' }}>{p.impr.toLocaleString()}</td>
                  <td style={{ padding: '7px 8px', color: '#22c55e', fontWeight: 700 }}>{p.ctr}%</td>
                  <td style={{ padding: '7px 8px' }}>#{p.pos}</td>
                  <td
                    style={{
                      padding: '7px 8px',
                      color: p.mom.startsWith('+') ? '#22c55e' : '#ef4444',
                      fontWeight: 700,
                    }}
                  >
                    {p.mom}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>30d Click Trend</div>
        <AreaChart
          points={[
            7200, 7600, 7400, 7800, 8200, 8600, 8400, 8800, 9200, 9400, 9100, 9600, 9800, 9400, 9900, 10200, 9800,
            10400, 10800, 10600, 11000, 11400, 11200, 11600, 12000, 11800, 12200, 12600, 12400, 13000,
          ]}
          labels={[]}
          color="#22c55e"
          height={70}
        />
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function TrendsVsPlatformTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ ...card, borderLeft: '4px solid #6366f1' }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>Trends vs Platform Comparison</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          Search volume trends cross-referenced with platform engagement data (Google, TikTok, LinkedIn, X, YouTube).
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Google Trends Score', value: '82', color: '#22c55e' },
          { label: 'TikTok Momentum', value: '+148%', color: '#ff0050' },
          { label: 'LinkedIn Engagement', value: '+34%', color: '#0077b5' },
          { label: 'X Conversation Vol.', value: '42K', color: '#1d9bf0' },
          { label: 'YouTube Search Vol.', value: '+28%', color: '#ff0000' },
          { label: 'Cross-platform Score', value: '74/100', color: '#6366f1' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Platform Momentum Index</div>
        <MiniBarChart
          items={[
            { label: 'TikTok', value: 148, color: '#ff0050', max: 200, suffix: '% MoM' },
            { label: 'YouTube Shorts', value: 84, color: '#ff0000', max: 200, suffix: '% MoM' },
            { label: 'LinkedIn', value: 34, color: '#0077b5', max: 200, suffix: '% MoM' },
            { label: 'Google Search', value: 22, color: '#22c55e', max: 200, suffix: '% MoM' },
            { label: 'X (Twitter)', value: 18, color: '#1d9bf0', max: 200, suffix: '% MoM' },
            { label: 'Instagram', value: 12, color: '#e1306c', max: 200, suffix: '% MoM' },
          ]}
        />
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Top Trending Topics — Platform Breakdown</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Topic', 'Google', 'TikTok', 'LinkedIn', 'X', 'YouTube', 'Opportunity'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: 10,
                      color: 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                {
                  topic: 'AI SEO tools',
                  goog: '↑84%',
                  tiktok: '↑220%',
                  li: '↑48%',
                  x: '↑62%',
                  yt: '↑96%',
                  opp: 'high',
                },
                {
                  topic: 'Core Web Vitals',
                  goog: '↑22%',
                  tiktok: '↑44%',
                  li: '↑18%',
                  x: '↑14%',
                  yt: '↑38%',
                  opp: 'medium',
                },
                {
                  topic: 'Next.js 15 tips',
                  goog: '↑38%',
                  tiktok: '↑180%',
                  li: '↑28%',
                  x: '↑84%',
                  yt: '↑124%',
                  opp: 'high',
                },
                {
                  topic: 'PageSpeed scoring',
                  goog: '↑12%',
                  tiktok: '↑22%',
                  li: '↑8%',
                  x: '↑6%',
                  yt: '↑18%',
                  opp: 'low',
                },
              ].map((r, i) => (
                <tr key={`tv-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '7px 8px', fontWeight: 600 }}>{r.topic}</td>
                  <td style={{ padding: '7px 8px', color: '#22c55e' }}>{r.goog}</td>
                  <td style={{ padding: '7px 8px', color: '#ff0050', fontWeight: 700 }}>{r.tiktok}</td>
                  <td style={{ padding: '7px 8px', color: '#0077b5' }}>{r.li}</td>
                  <td style={{ padding: '7px 8px', color: '#1d9bf0' }}>{r.x}</td>
                  <td style={{ padding: '7px 8px', color: '#ff0000' }}>{r.yt}</td>
                  <td style={{ padding: '7px 8px' }}>
                    <span style={badge(r.opp === 'high' ? '#22c55e' : r.opp === 'medium' ? '#f59e0b' : '#6366f1')}>
                      {r.opp}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function PowerRankingTab({ result, card, isOfflinePreview }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {/* Big composite score */}
      <div
        style={{
          ...card,
          background: 'var(--card)',
          color: '#fff',
          textAlign: 'center',
          padding: 28,
        }}
      >
        <div
          style={{
            fontSize: 12,
            color: '#6366f1',
            marginBottom: 8,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          Composite Power Ranking
        </div>
        <div style={{ fontWeight: 900, fontSize: 72, lineHeight: 1, color: '#6366f1' }}>78</div>
        <div style={{ fontSize: 14, color: '#6366f1', marginTop: 4 }}>/ 100 — Strong Performer</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>
          Ranks <strong style={{ color: '#fff' }}>#3</strong> in your niche · Top 15% globally
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
        {[
          { label: 'Technical SEO', score: 82, color: '#22c55e' },
          { label: 'Content Quality', score: 74, color: '#6366f1' },
          { label: 'Authority / DA', score: 54, color: '#f59e0b' },
          { label: 'AI Visibility', score: 71, color: '#6366f1' },
          { label: 'UX / CWV', score: 68, color: '#ec4899' },
          { label: 'Social Signals', score: 62, color: '#10b981' },
          { label: 'Security', score: 88, color: '#22c55e' },
          {
            label: 'Performance',
            score: result.performance_score ?? 62,
            color: scoreColor(result.performance_score ?? 62),
          },
        ].map((m) => (
          <div key={m.label} style={{ ...card, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 6 }}>{m.label}</div>
            <div style={{ fontWeight: 900, fontSize: 28, color: m.color }}>{m.score}</div>
            <div style={{ height: 4, background: 'var(--line)', borderRadius: 2, marginTop: 6 }}>
              <div style={{ width: `${m.score}%`, height: '100%', background: m.color, borderRadius: 2 }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Power Score Trend (90d)</div>
          <AreaChart
            points={[64, 66, 65, 68, 70, 72, 71, 74, 73, 75, 77, 78]}
            labels={['Feb', '', '', 'Mar', '', '', 'Apr', '', '', 'May', '', '']}
            color="#6366f1"
            height={70}
          />
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Niche Ranking vs Competitors</div>
          <MiniBarChart
            items={[
              { label: 'Competitor A', value: 86, color: '#ef4444', max: 100, suffix: '/100' },
              { label: 'Competitor B', value: 82, color: '#f59e0b', max: 100, suffix: '/100' },
              { label: 'You', value: 78, color: '#6366f1', max: 100, suffix: '/100' },
              { label: 'Competitor C', value: 71, color: '#22c55e', max: 100, suffix: '/100' },
              { label: 'Competitor D', value: 64, color: '#6366f1', max: 100, suffix: '/100' },
            ]}
          />
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Power Ranking Improvement Plan</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {[
            { action: 'Build 20 high-DA backlinks (DA > 60) to close authority gap', impact: '+6 pts', effort: 'high' },
            {
              action: 'Refresh 23 outdated blog posts with new data and E-E-A-T signals',
              impact: '+4 pts',
              effort: 'medium',
            },
            {
              action: 'Improve LCP to < 2.5s on mobile — fix render-blocking scripts',
              impact: '+3 pts',
              effort: 'medium',
            },
            { action: 'Implement structured data on 48 pages missing schema', impact: '+2 pts', effort: 'low' },
          ].map((p, i) => (
            <div
              key={`pp-${i}`}
              style={{
                display: 'flex',
                gap: 10,
                alignItems: 'flex-start',
                padding: '8px 12px',
                background: 'var(--bg)',
                borderRadius: 8,
                border: '1px solid var(--line)',
                fontSize: 12,
              }}
            >
              <span style={{ color: '#22c55e', fontWeight: 800, fontSize: 14, minWidth: 52 }}>{p.impact}</span>
              <span style={{ flex: 1 }}>{p.action}</span>
              <span style={badge(p.effort === 'high' ? '#ef4444' : p.effort === 'medium' ? '#f59e0b' : '#22c55e')}>
                {p.effort} effort
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AutonomousTab({ result, card, isOfflinePreview, autoFixing, autoFixResult, optimizeSite }: PerfTabProps) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div
        style={{
          ...card,
          borderLeft: '4px solid #6366f1',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 10,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Autonomous SEO Engine</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
            AI agents running 24/7 — auto-fix, auto-publish, auto-optimize, auto-monitor.
          </div>
        </div>
        <button
          type="button"
          onClick={optimizeSite}
          disabled={autoFixing}
          style={{ ...btn(true), background: '#6366f1', color: '#fff' }}
        >
          {autoFixing ? 'Agents Running...' : '🤖 Trigger Full Autonomous Run'}
        </button>
      </div>
      {/* Agent fleet status */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))', gap: 10 }}>
        {[
          { label: 'Active Agents', value: '12', color: '#22c55e' },
          { label: 'Tasks Queued', value: '48', color: '#f59e0b' },
          { label: 'Tasks Completed 7d', value: '284', color: '#6366f1' },
          { label: 'Avg. Task Duration', value: '4.2m', color: '#6366f1' },
          { label: 'Success Rate', value: '94%', color: '#22c55e' },
          { label: 'Auto-Published Posts', value: '8', color: '#ec4899' },
          { label: 'Fixes Applied Auto', value: '62', color: '#10b981' },
          { label: 'Revenue Impact', value: '+$12.4K', color: '#22c55e' },
        ].map((kpi) => (
          <div key={kpi.label} style={card}>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{kpi.label}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>
      {/* Agent task queue */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Active Agent Task Queue</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {[
            {
              agent: 'ContentRefreshAgent',
              task: 'Refresh 3 decaying blog posts with new 2025 stats',
              status: 'running',
              progress: 64,
              eta: '12m',
            },
            {
              agent: 'LinkBuildAgent',
              task: 'Outreach to 8 high-DA sites for backlink placement',
              status: 'running',
              progress: 38,
              eta: '48m',
            },
            {
              agent: 'TechnicalSEOAgent',
              task: 'Fix 7 render-blocking scripts + add defer attributes',
              status: 'running',
              progress: 82,
              eta: '3m',
            },
            {
              agent: 'SchemaAgent',
              task: 'Inject FAQ schema on 12 pages missing structured data',
              status: 'queued',
              progress: 0,
              eta: 'soon',
            },
            {
              agent: 'MonitorAgent',
              task: 'Watch rank changes for 248 tracked keywords',
              status: 'running',
              progress: 100,
              eta: 'live',
            },
            {
              agent: 'PublishAgent',
              task: 'Schedule + publish 2 AI-assisted articles',
              status: 'queued',
              progress: 0,
              eta: 'soon',
            },
            {
              agent: 'SecurityAgent',
              task: 'Patch 3 outdated dependencies with known CVEs',
              status: 'running',
              progress: 55,
              eta: '8m',
            },
            {
              agent: 'PerformanceAgent',
              task: 'Convert 8 JPEG images to AVIF format',
              status: 'done',
              progress: 100,
              eta: '—',
            },
          ].map((t, i) => (
            <div
              key={`aq-${i}`}
              style={{
                ...card,
                padding: 10,
                borderLeft: `3px solid ${t.status === 'running' ? '#22c55e' : t.status === 'done' ? '#6366f1' : '#f59e0b'}`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 8,
                  marginBottom: 6,
                }}
              >
                <div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 2 }}>
                    <span style={{ fontWeight: 700, fontSize: 11, color: '#6366f1' }}>{t.agent}</span>
                    <span
                      style={badge(t.status === 'running' ? '#22c55e' : t.status === 'done' ? '#6366f1' : '#f59e0b')}
                    >
                      {t.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12 }}>{t.task}</div>
                </div>
                <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>ETA: {t.eta}</span>
              </div>
              {t.status !== 'queued' && (
                <div style={{ height: 4, background: 'var(--line)', borderRadius: 2 }}>
                  <div
                    style={{
                      width: `${t.progress}%`,
                      height: '100%',
                      background: t.status === 'done' ? '#6366f1' : '#22c55e',
                      borderRadius: 2,
                    }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      {/* Automation coverage */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Automation Coverage by Module</div>
        <MiniBarChart
          items={[
            { label: 'Technical SEO', value: 91, color: '#22c55e', max: 100, suffix: '% auto' },
            { label: 'Content Refresh', value: 74, color: '#6366f1', max: 100, suffix: '% auto' },
            { label: 'Link Building', value: 48, color: '#f59e0b', max: 100, suffix: '% auto' },
            { label: 'Schema / Structured Data', value: 86, color: '#6366f1', max: 100, suffix: '% auto' },
            { label: 'Performance Fixes', value: 68, color: '#ec4899', max: 100, suffix: '% auto' },
            { label: 'Security Patching', value: 82, color: '#10b981', max: 100, suffix: '% auto' },
            { label: 'Monitoring & Alerts', value: 96, color: '#22c55e', max: 100, suffix: '% auto' },
          ]}
        />
      </div>
      {/* Autonomous results */}
      {autoFixResult && (
        <div style={{ ...card, background: '#14532d22', border: '1px solid #22c55e44' }}>
          <div style={{ fontWeight: 700, color: '#22c55e', marginBottom: 8 }}>Last Autonomous Run Results</div>
          <div style={{ display: 'grid', gap: 6 }}>
            {autoFixResult.fixes_applied.map((fix) => (
              <div key={fix.fix_id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                <span style={{ color: fix.status === 'applied' ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                  {fix.status === 'applied' ? '✓' : '✗'}
                </span>
                <span style={{ flex: 1 }}>{fix.title}</span>
                {fix.actual_gain_ms > 0 && <span style={{ color: '#22c55e' }}>-{fix.actual_gain_ms}ms</span>}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted)' }}>
            Run at: {new Date(autoFixResult.applied_at).toLocaleString()} · Total gain:{' '}
            <strong style={{ color: '#22c55e' }}>{autoFixResult.total_gain_ms}ms</strong>
          </div>
        </div>
      )}
    </section>
  );
}

export default function PerformanceAuditPage() {
  // NOSONAR
  const rumSessionIdRef = useRef('');
  const rumLastValueRef = useRef<Record<string, number>>({});
  const [url, setUrl] = useState('https://example.com');
  const [targetDevice, setTargetDevice] = useState<'mobile' | 'desktop'>('mobile');
  const [targetRegion, setTargetRegion] = useState('lhr1');
  const [connection, setConnection] = useState('4g');
  const [browser, setBrowser] = useState('chrome');
  const [notes, setNotes] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isOfflinePreview, setIsOfflinePreview] = useState(false);
  const [result, setResult] = useState<PerformanceAuditResponse | null>(null);
  const [tab, setTab] = useState<Tab>('summary');

  const [autoFixing, setAutoFixing] = useState(false);
  const [autoFixResult, setAutoFixResult] = useState<AutoFixResult | null>(null);
  const [autoFixError, setAutoFixError] = useState('');

  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyData, setHistoryData] = useState<HistoryResponse | null>(null);
  const [rumTargetSummary, setRumTargetSummary] = useState<PerformanceRumSummaryResponse | null>(null);
  const [rumTargetLoading, setRumTargetLoading] = useState(false);
  const [currentPageRumRollup, setCurrentPageRumRollup] = useState<PerformanceRumRollup | null>(null);
  const [rumCollector, setRumCollector] = useState<RumCollectorState | null>(null);

  const [fixingItem, setFixingItem] = useState<string | null>(null);
  const [fixedItems, setFixedItems] = useState<Set<string>>(new Set());

  const card: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };
  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box',
  };

  const runAudit = useCallback(async () => {
    setLoading(true);
    setError('');
    setIsOfflinePreview(false);
    setAutoFixResult(null);
    setFixedItems(new Set());
    try {
      const response = await apiSend<PerformanceAuditResponse>(
        '/seo-platform/performance/audit',
        'POST',
        {
          url: url.trim(),
          target_device: targetDevice,
          target_region: targetRegion,
          connection,
          browser,
          require_live_providers: true,
          notes: notes.trim(),
        },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
      setIsOfflinePreview(false);
      setTab('summary');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Performance audit failed.';
      if (isNetworkFetchFailure(message)) {
        setError(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live backend is unreachable in strict no-mock mode. Start FastAPI and re-run.'
            : 'Live backend is unreachable in fail-closed mode. Start FastAPI and re-run.'
        );
        setIsOfflinePreview(false);
        setResult(null);
      } else {
        setError(message);
        setIsOfflinePreview(false);
        setResult(null);
      }
    } finally {
      setLoading(false);
    }
  }, [url, targetDevice, targetRegion, connection, browser, notes]);

  const optimizeSite = useCallback(async () => {
    if (!result) return;
    setAutoFixing(true);
    setAutoFixError('');
    try {
      const candidates = result.ai_remediation?.auto_fix_candidates ?? [];
      const response = await apiSend<AutoFixResult>(
        '/seo-platform/performance/auto-fix',
        'POST',
        { url: result.url, candidates },
        DEFAULT_TENANT_ID
      );
      setAutoFixResult(response);
      setTab('ai-fixes');
    } catch (err) {
      setAutoFixError(err instanceof Error ? err.message : 'Auto-fix failed.');
    } finally {
      setAutoFixing(false);
    }
  }, [result]);

  const fixSingleItem = useCallback(
    async (candidate: AutoFixCandidate) => {
      if (!result || !candidate.title) return;
      const key = candidate.title;
      setFixingItem(key);
      try {
        await apiSend<AutoFixResult>(
          '/seo-platform/performance/auto-fix',
          'POST',
          { url: result.url, candidates: [candidate] },
          DEFAULT_TENANT_ID
        );
        setFixedItems((prev) => new Set(prev).add(key));
      } catch {
        /* per-item error is non-critical */
      }
      setFixingItem(null);
    },
    [result]
  );

  const loadHistory = useCallback(async () => {
    if (!url) return;
    setHistoryLoading(true);
    try {
      const data = await apiGet<HistoryResponse>(
        `/seo-platform/performance/history?url=${encodeURIComponent(url.trim())}`,
        DEFAULT_TENANT_ID
      );
      setHistoryData(data);
      setTab('history');
    } catch {
      /* silent */
    }
    setHistoryLoading(false);
  }, [url]);

  const refreshRumTargetSummary = useCallback(async () => {
    const targetUrl = result?.url?.trim() || url.trim();
    if (!targetUrl) {
      setRumTargetSummary(null);
      return;
    }
    setRumTargetLoading(true);
    try {
      const summary = await apiGet<PerformanceRumSummaryResponse>(
        `/seo-platform/performance/rum/summary?url=${encodeURIComponent(targetUrl)}`,
        DEFAULT_TENANT_ID
      );
      setRumTargetSummary(summary);
    } catch {
      setRumTargetSummary(null);
    } finally {
      setRumTargetLoading(false);
    }
  }, [result?.url, url]);

  useEffect(() => {
    void refreshRumTargetSummary();
  }, [refreshRumTargetSummary]);

  useEffect(() => {
    if (globalThis.window === undefined) return;

    const currentPageUrl = currentBrowserPageUrl();
    const targetUrl = result?.url?.trim() || url.trim();
    const canCollectForAuditUrl = Boolean(targetUrl) && currentPageUrl === targetUrl;
    const observerSupported = globalThis.window !== undefined && globalThis.document !== undefined;

    if (!rumSessionIdRef.current) {
      rumSessionIdRef.current =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `rum-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    setRumCollector((prev) => ({
      supported: observerSupported,
      collecting: observerSupported,
      currentPageUrl,
      targetUrl,
      canCollectForAuditUrl,
      ingestedCount: prev?.ingestedCount ?? 0,
      lastMetric: prev?.lastMetric,
      lastValue: prev?.lastValue,
      lastSentAt: prev?.lastSentAt,
      error: prev?.error,
    }));

    if (!observerSupported) return;

    const submitMetric = async (metricName: string, value: number) => {
      if (!Number.isFinite(value) || value < 0) return;
      const normalizedMetric = normalizeRumMetricName(metricName);
      if (rumLastValueRef.current[normalizedMetric] === value) return;
      rumLastValueRef.current[normalizedMetric] = value;
      try {
        const response = await apiSend<PerformanceRumIngestResponse>(
          '/seo-platform/performance/rum/ingest',
          'POST',
          {
            url: currentPageUrl,
            page_url: currentPageUrl,
            metric_name: normalizedMetric,
            value,
            rating: rateRumMetric(normalizedMetric, value),
            session_id: rumSessionIdRef.current,
            device_type: /Mobi|Android/i.test(globalThis.window.navigator.userAgent) ? 'mobile' : 'desktop',
            effective_connection_type:
              'connection' in globalThis.navigator &&
              typeof (globalThis.navigator as Navigator & { connection?: { effectiveType?: string } }).connection ===
                'object' &&
              (globalThis.navigator as Navigator & { connection?: { effectiveType?: string } }).connection
                ? (globalThis.navigator as Navigator & { connection?: { effectiveType?: string } }).connection
                    ?.effectiveType || 'unknown'
                : 'unknown',
            user_agent: globalThis.window.navigator.userAgent,
          },
          DEFAULT_TENANT_ID
        );
        setCurrentPageRumRollup(response.rollup ?? null);
        setRumCollector((prev) => ({
          supported: true,
          collecting: true,
          currentPageUrl,
          targetUrl,
          canCollectForAuditUrl,
          ingestedCount: (prev?.ingestedCount ?? 0) + 1,
          lastMetric: normalizedMetric,
          lastValue: value,
          lastSentAt: response.received_at,
          error: '',
        }));
        if (canCollectForAuditUrl) void refreshRumTargetSummary();
      } catch (err) {
        setRumCollector((prev) => ({
          supported: true,
          collecting: false,
          currentPageUrl,
          targetUrl,
          canCollectForAuditUrl,
          ingestedCount: prev?.ingestedCount ?? 0,
          lastMetric: prev?.lastMetric,
          lastValue: prev?.lastValue,
          lastSentAt: prev?.lastSentAt,
          error: err instanceof Error ? err.message : 'Failed to ingest RUM metric.',
        }));
      }
    };

    const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    if (navEntry?.responseStart) {
      void submitMetric('TTFB', Math.round(navEntry.responseStart));
    }

    let collectorActive = true;
    onLCP((metric: Metric) => {
      if (!collectorActive) return;
      void submitMetric('LCP', Math.round(metric.value));
    });
    onINP((metric: Metric) => {
      if (!collectorActive) return;
      void submitMetric('INP', Math.round(metric.value));
    });
    onCLS((metric: Metric) => {
      if (!collectorActive) return;
      void submitMetric('CLS', Number(metric.value.toFixed(3)));
    });
    onTTFB((metric: Metric) => {
      if (!collectorActive) return;
      void submitMetric('TTFB', Math.round(metric.value));
    });

    const timeoutId = globalThis.window.setTimeout(() => {
      collectorActive = false;
    }, 8000);

    return () => {
      collectorActive = false;
      globalThis.window.clearTimeout(timeoutId);
    };
  }, [refreshRumTargetSummary, result?.url, url]);

  const exportReport = useCallback(() => {
    if (!result) return;
    const lines = [
      'Performance Audit Report',
      '========================',
      `URL: ${result.url}`,
      `Audited: ${result.audited_at ?? 'n/a'}`,
      `Device: ${result.target_device} | Region: ${result.target_region}`,
      '',
      `Performance Score: ${result.performance_score} (${scoreGrade(result.performance_score)})`,
      '',
      'Core Web Vitals',
      `  LCP: ${result.core_web_vitals?.lcp_ms ?? 0}ms`,
      `  INP: ${result.core_web_vitals?.inp_ms ?? 0}ms`,
      `  CLS: ${result.core_web_vitals?.cls ?? 0}`,
      `  TTFB: ${result.core_web_vitals?.ttfb_ms ?? 0}ms`,
      '',
      'Lighthouse',
      `  Performance: ${result.lighthouse?.performance ?? 0}`,
      `  SEO: ${result.lighthouse?.seo ?? 0}`,
      `  Best Practices: ${result.lighthouse?.best_practices ?? 0}`,
      '',
      'Opportunities',
      ...(result.opportunities ?? []).map((o) => `  [${o.priority}] ${o.issue}: ${o.impact}`),
      '',
      'AI Remediation',
      result.ai_remediation?.summary ?? '',
      ...(result.ai_remediation?.auto_fix_candidates ?? []).map(
        (c) => `  - ${c.title} (confidence: ${c.confidence}, gain: ${c.estimated_gain_ms}ms)`
      ),
    ].join('\n');
    const blob = new Blob([lines], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `performance-audit-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  }, [result]);

  const TABS: { id: Tab; label: string }[] = [
    { id: 'summary', label: 'Summary' },
    { id: 'waterfall', label: 'Waterfall' },
    { id: 'filmstrip', label: 'Filmstrip' },
    { id: 'rum', label: 'RUM' },
    { id: 'causality', label: 'Causality' },
    { id: 'agents', label: 'Synthetic Agents' },
    { id: 'prediction', label: 'Prediction' },
    { id: 'global', label: 'Global Mesh' },
    { id: 'business', label: 'Business Impact' },
    { id: 'ci-gate', label: 'CI Gate' },
    { id: 'slo', label: 'SLO Guardrails' },
    { id: 'roi', label: 'ROI Matrix' },
    { id: 'copilot', label: 'Perf Copilot' },
    {
      id: 'opportunities',
      label: result?.opportunities?.length ? `Opportunities (${result.opportunities.length})` : 'Opportunities',
    },
    { id: 'ai-fixes', label: 'AI Auto-Fix' },
    { id: 'images', label: result?.image_audit ? `Images (${result.image_audit.unoptimized ?? 0} issues)` : 'Images' },
    {
      id: 'security',
      label: result?.security_audit ? `Security (CSP ${result.security_audit.csp_score ?? 0})` : 'Security',
    },
    {
      id: 'javascript',
      label: result?.js_audit ? `JavaScript (${result.js_audit.unused_pct?.toFixed(0) ?? 0}% unused)` : 'JavaScript',
    },
    { id: 'css', label: result?.css_audit ? `CSS (${result.css_audit.unused_pct?.toFixed(0) ?? 0}% unused)` : 'CSS' },
    {
      id: 'input-validation',
      label: result?.input_validation_audit
        ? `Input Val. (${(result.input_validation_audit.xss_risks ?? 0) + (result.input_validation_audit.injection_risks ?? 0)} risks)`
        : 'Input Validation',
    },
    {
      id: 'latency',
      label: result?.latency_audit ? `Latency (p99 ${result.latency_audit.overall?.p99 ?? 0}ms)` : 'Latency',
    },
    {
      id: 'outdated',
      label: result?.outdated_audit ? `Outdated (${result.outdated_audit.outdated_count ?? 0})` : 'Outdated',
    },
    {
      id: 'workflow',
      label: result?.workflow_audit ? `Workflow (${result.workflow_audit.pipeline_status ?? 'n/a'})` : 'Workflow',
    },
    { id: 'data-analysis', label: 'Data Analysis' },
    {
      id: 'core-seo',
      label: result?.core_seo_suite ? `Core SEO (${result.core_seo_suite.coverage ?? 0}%)` : 'Core SEO',
    },
    {
      id: 'content-blogging',
      label: result?.content_blog_suite
        ? `Content (${result.content_blog_suite.opportunity_count ?? 0})`
        : 'Content & Blogging',
    },
    {
      id: 'ai-optimization',
      label: result?.ai_optimization_suite
        ? `AI SEO (${result.ai_optimization_suite.coverage ?? 0}%)`
        : 'AI Optimization',
    },
    {
      id: 'search-experience',
      label: result?.search_experience_suite
        ? `Search X (${result.search_experience_suite.coverage ?? 0}%)`
        : 'Search Experience',
    },
    {
      id: 'vertical-seo',
      label: result?.vertical_seo_suite ? `Verticals (${result.vertical_seo_suite.coverage ?? 0}%)` : 'Vertical SEO',
    },
    {
      id: 'platform-ops',
      label: result?.platform_ops_suite
        ? `Platform (${result.platform_ops_suite.opportunity_count ?? 0})`
        : 'Platform Ops',
    },
    {
      id: 'accessibility',
      label: result?.accessibility_audit
        ? `Accessibility (${result.accessibility_audit.wcag_score ?? 0})`
        : 'Accessibility',
    },
    {
      id: 'competitor-intel',
      label: result?.competitor_intel
        ? `Competitor (${result.competitor_intel.keyword_gap ?? 0} gaps)`
        : 'Competitor Intel',
    },
    {
      id: 'schema-entities',
      label: result?.schema_entities
        ? `Schema (${result.schema_entities.validated ?? 0}/${result.schema_entities.total_schemas ?? 0})`
        : 'Schema & Entities',
    },
    {
      id: 'technical-deep',
      label: result?.technical_deep
        ? `Tech Deep (${result.technical_deep.crawl_efficiency_pct ?? 0}%)`
        : 'Technical Deep',
    },
    {
      id: 'trust-revenue',
      label: result?.trust_revenue
        ? `Trust ($${((result.trust_revenue.seo_revenue_total_usd ?? 0) / 1000).toFixed(0)}k)`
        : 'Trust & Revenue',
    },
    {
      id: 'ux-conversion',
      label: result?.ux_conversion ? `UX (${result.ux_conversion.ux_score ?? 0})` : 'UX & Conversion',
    },
    {
      id: 'growth-landing',
      label: result?.growth_landing ? `Growth (${result.growth_landing.playbook_score ?? 0})` : 'Growth & Landing',
    },
    {
      id: 'live-intelligence',
      label: result?.live_intelligence ? `Live (p${result.live_intelligence.avg_position ?? 0})` : 'Live Intel',
    },
    { id: 'gtmetrix-api', label: 'GTmetrix API' },
    { id: 'history', label: 'History' },
    { id: 'monitoring', label: 'Monitoring' },
    { id: 'keywords', label: 'Keywords' },
    { id: 'seo-ranking', label: 'SEO Ranking' },
    { id: 'ai-models-ranking', label: 'AI Models Ranking' },
    { id: 'hashtags', label: 'Hashtags' },
    { id: 'visibility', label: 'Visibility' },
    { id: 'leads', label: 'Leads' },
    { id: 'clicks', label: 'Clicks' },
    { id: 'trends-vs-platform', label: 'Trends vs Platform' },
    { id: 'power-ranking', label: 'Power Ranking' },
    { id: 'autonomous', label: 'Autonomous' },
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1060, margin: '0 auto' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            marginBottom: 20,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>GTmetrix-Style Performance Audit</h1>
            <p style={{ color: 'var(--muted)', margin: '4px 0 0', fontSize: 13 }}>
              Lighthouse scoring · Core Web Vitals · Waterfall · Filmstrip · AI Auto-Fix · Global Testing
            </p>
          </div>
          {result && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button type="button" style={btn()} onClick={loadHistory} disabled={historyLoading}>
                {historyLoading ? 'Loading...' : 'History'}
              </button>
              <button type="button" style={btn()} onClick={exportReport}>
                Export Report
              </button>
              <button
                type="button"
                onClick={optimizeSite}
                disabled={autoFixing}
                style={{ ...btn(true), background: '#6366f1', color: '#fff' }}
              >
                {autoFixing ? 'Optimizing...' : 'Optimize Site'}
              </button>
            </div>
          )}
        </div>

        {/* Config Panel */}
        <section style={{ ...card, marginBottom: 16 }}>
          <div style={{ display: 'grid', gap: 10 }}>
            <div>
              <label htmlFor="perf-url" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
                Website URL
              </label>
              <input
                id="perf-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                style={inputStyle}
                onKeyDown={(e) => e.key === 'Enter' && runAudit()}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
              <div>
                <label
                  htmlFor="perf-device"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
                >
                  Device
                </label>
                <select
                  id="perf-device"
                  value={targetDevice}
                  onChange={(e) => setTargetDevice(e.target.value as 'mobile' | 'desktop')}
                  style={inputStyle}
                >
                  <option value="mobile">Mobile</option>
                  <option value="desktop">Desktop</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="perf-region"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
                >
                  Test Location
                </label>
                <select
                  id="perf-region"
                  value={targetRegion}
                  onChange={(e) => setTargetRegion(e.target.value)}
                  style={inputStyle}
                >
                  {REGIONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="perf-conn" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
                  Connection Speed
                </label>
                <select
                  id="perf-conn"
                  value={connection}
                  onChange={(e) => setConnection(e.target.value)}
                  style={inputStyle}
                >
                  {CONNECTIONS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="perf-browser"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
                >
                  Browser
                </label>
                <select
                  id="perf-browser"
                  value={browser}
                  onChange={(e) => setBrowser(e.target.value)}
                  style={inputStyle}
                >
                  <option value="chrome">Chrome</option>
                  <option value="firefox">Firefox</option>
                  <option value="safari">Safari</option>
                  <option value="edge">Edge</option>
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <label
                  htmlFor="perf-notes"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}
                >
                  Notes (optional)
                </label>
                <input
                  id="perf-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  style={inputStyle}
                  placeholder="e.g. focus on mobile LCP"
                />
              </div>
              <button
                type="button"
                onClick={runAudit}
                disabled={loading}
                style={{ ...btn(true), whiteSpace: 'nowrap' }}
              >
                {loading ? 'Auditing...' : 'Run Audit'}
              </button>
            </div>
            {error && (
              <div
                style={{
                  color: isOfflinePreview ? '#92400e' : '#dc2626',
                  fontSize: 12,
                  padding: '6px 10px',
                  background: isOfflinePreview ? '#78350f33' : '#7f1d1d22',
                  borderRadius: 6,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 10,
                  flexWrap: 'wrap',
                }}
              >
                <span>{error}</span>
                {isOfflinePreview && (
                  <button type="button" onClick={runAudit} disabled={loading} style={btn(true)}>
                    Retry Live Backend
                  </button>
                )}
              </div>
            )}
          </div>
        </section>

        {loading && (
          <section style={{ ...card, marginBottom: 16, textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 8 }}>Running performance audit...</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
              Testing {targetDevice} from {REGIONS.find((r) => r.value === targetRegion)?.label ?? targetRegion} on{' '}
              {connection.toUpperCase()}
            </div>
          </section>
        )}

        {result && !loading && (
          <>
            {/* Score Row */}
            <section style={{ ...card, marginBottom: 16 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 12,
                  marginBottom: 16,
                }}
              >
                <div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{result.url}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {result.audited_at ? new Date(result.audited_at).toLocaleString() : ''} &middot;{' '}
                    {result.target_device} &middot;{' '}
                    {REGIONS.find((r) => r.value === result.target_region)?.label ?? result.target_region}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {result.analysis_mode && (
                    <span style={badge(result.analysis_mode === 'llm' ? '#22c55e' : 'var(--muted)')}>
                      {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                    </span>
                  )}
                  {result.cached && <span style={badge('#38bdf8')}>Cached result</span>}
                  {isOfflinePreview && <span style={badge('#f59e0b')}>Offline Preview</span>}
                  {result.history?.regression_detected && <span style={badge('#ef4444')}>Regression Detected</span>}
                  {result.alerts?.status === 'healthy' && <span style={badge('#22c55e')}>All alerts healthy</span>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
                <ScoreGauge score={result.performance_score} label="GTmetrix Score" />
                {result.lighthouse?.performance !== undefined && (
                  <ScoreGauge score={result.lighthouse.performance} label="Performance" />
                )}
                {result.lighthouse?.seo !== undefined && <ScoreGauge score={result.lighthouse.seo} label="SEO" />}
                {result.lighthouse?.best_practices !== undefined && (
                  <ScoreGauge score={result.lighthouse.best_practices} label="Best Practices" />
                )}
                {result.lighthouse?.accessibility !== undefined && (
                  <ScoreGauge score={result.lighthouse.accessibility} label="Accessibility" />
                )}
              </div>
            </section>

            {/* Auto-fix banner */}
            {autoFixResult && (
              <section style={{ ...card, marginBottom: 16, background: '#14532d22', border: '1px solid #22c55e44' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 8,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#22c55e', marginBottom: 4 }}>Site Optimization Applied</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {autoFixResult.fixes_applied.filter((f) => f.status === 'applied').length} fixes applied &middot;
                      Total gain: {autoFixResult.total_gain_ms}ms &middot; New score:{' '}
                      {autoFixResult.new_performance_score}
                    </div>
                  </div>
                  {autoFixResult.rerun_recommended && (
                    <button type="button" style={btn(true)} onClick={runAudit}>
                      Re-run Audit
                    </button>
                  )}
                </div>
              </section>
            )}
            {autoFixError && (
              <section style={{ ...card, marginBottom: 16, background: '#7f1d1d22' }}>
                <div style={{ color: '#dc2626', fontSize: 12 }}>{autoFixError}</div>
              </section>
            )}

            {/* Core Web Vitals */}
            <section style={{ marginBottom: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  marginBottom: 8,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                }}
              >
                Core Web Vitals
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))', gap: 10 }}>
                {[
                  {
                    key: 'lcp',
                    label: 'LCP',
                    value: result.core_web_vitals?.lcp_ms ?? 0,
                    unit: 'ms',
                    desc: 'Largest Contentful Paint',
                  },
                  {
                    key: 'inp',
                    label: 'INP',
                    value: result.core_web_vitals?.inp_ms ?? 0,
                    unit: 'ms',
                    desc: 'Interaction to Next Paint',
                  },
                  {
                    key: 'cls',
                    label: 'CLS',
                    value: result.core_web_vitals?.cls ?? 0,
                    unit: '',
                    desc: 'Cumulative Layout Shift',
                  },
                  {
                    key: 'ttfb',
                    label: 'TTFB',
                    value: result.core_web_vitals?.ttfb_ms ?? 0,
                    unit: 'ms',
                    desc: 'Time to First Byte',
                  },
                ].map(({ key, value, unit, desc }) => {
                  const status = cwvStatus(key, value);
                  const color = cwvColor(status);
                  return (
                    <div key={key} style={{ ...card, padding: 12, borderLeft: `3px solid ${color}` }}>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>{desc}</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color }}>
                        {value}
                        {unit}
                      </div>
                      <span style={badge(color)}>{status.replace('-', ' ')}</span>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Field Web Vitals */}
            {result.field_web_vitals && (
              <section style={{ ...card, marginBottom: 16 }}>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Field Data (Real User Monitoring)</div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))',
                    gap: 8,
                    fontSize: 12,
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--muted)' }}>LCP p75</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{result.field_web_vitals.lcp_p75_ms ?? 0}ms</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--muted)' }}>INP p75</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{result.field_web_vitals.inp_p75_ms ?? 0}ms</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--muted)' }}>CLS p75</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{result.field_web_vitals.cls_p75 ?? 0}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--muted)' }}>RUM Samples</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>
                      {(result.field_web_vitals.sample_size ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--muted)' }}>Period</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{result.field_web_vitals.period ?? 'n/a'}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--muted)' }}>Source</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{result.field_web_vitals.source ?? 'n/a'}</div>
                  </div>
                </div>
              </section>
            )}

            {/* Page Stats */}
            <section style={{ ...card, marginBottom: 16 }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Page Stats</div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))',
                  gap: 8,
                  fontSize: 12,
                }}
              >
                <div>
                  <div style={{ color: 'var(--muted)' }}>Total Requests</div>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>{result.waterfall?.requests ?? 0}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--muted)' }}>Transfer Size</div>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>{result.waterfall?.transfer_kb ?? 0} KB</div>
                </div>
                <div>
                  <div style={{ color: 'var(--muted)' }}>Render-blocking</div>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>
                    {(result.waterfall?.render_blocking ?? []).length}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--muted)' }}>Trend</div>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>{result.history?.trend ?? 'n/a'}</div>
                </div>
              </div>
            </section>

            {/* Tab bar */}
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  style={{
                    padding: '7px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--line)',
                    background: tab === t.id ? 'var(--brand)' : 'var(--bg)',
                    color: tab === t.id ? '#00101e' : 'var(--text)',
                    fontWeight: 700,
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Summary */}
            {tab === 'summary' && (
              <SummaryTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Waterfall */}
            {tab === 'waterfall' && (
              <WaterfallTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Filmstrip */}
            {tab === 'filmstrip' && (
              <FilmstripTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* RUM */}
            {tab === 'rum' && (
              <RumTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
                rumCollector={rumCollector}
                currentPageRumRollup={currentPageRumRollup}
                rumTargetSummary={rumTargetSummary}
                rumTargetLoading={rumTargetLoading}
                refreshRumTargetSummary={refreshRumTargetSummary}
              />
            )}

            {/* Causality */}
            {tab === 'causality' && (
              <CausalityTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Synthetic Agents */}
            {tab === 'agents' && (
              <AgentsTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Prediction */}
            {tab === 'prediction' && (
              <PredictionTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Global */}
            {tab === 'global' && (
              <GlobalTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Business Impact */}
            {tab === 'business' && (
              <BusinessTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* CI Gate */}
            {tab === 'ci-gate' && (
              <CiGateTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* SLO */}
            {tab === 'slo' && (
              <SloTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* ROI */}
            {tab === 'roi' && (
              <RoiTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Copilot */}
            {tab === 'copilot' && (
              <CopilotTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Opportunities */}
            {tab === 'opportunities' && (
              <OpportunitiesTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* AI Auto-Fix */}
            {tab === 'ai-fixes' && (
              <AiFixesTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Images */}
            {tab === 'images' && (
              <ImagesTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Security */}
            {tab === 'security' && (
              <SecurityTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* JavaScript */}
            {tab === 'javascript' && (
              <JavascriptTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* CSS */}
            {tab === 'css' && (
              <CssTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Input Validation */}
            {tab === 'input-validation' && (
              <InputValidationTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Latency */}
            {tab === 'latency' && (
              <LatencyTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Outdated */}
            {tab === 'outdated' && (
              <OutdatedTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Workflow */}
            {tab === 'workflow' && (
              <WorkflowTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Data Analysis */}
            {tab === 'data-analysis' && (
              <DataAnalysisTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'core-seo' && (
              <CoreSeoTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'content-blogging' && (
              <ContentBloggingTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'ai-optimization' && (
              <AiOptimizationTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'search-experience' && (
              <SearchExperienceTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'vertical-seo' && (
              <VerticalSeoTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {tab === 'platform-ops' && (
              <PlatformOpsTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Accessibility */}
            {tab === 'accessibility' && (
              <AccessibilityTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Competitor Intel */}
            {tab === 'competitor-intel' && (
              <CompetitorIntelTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Schema & Entities */}
            {tab === 'schema-entities' && (
              <SchemaEntitiesTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Technical Deep Dive */}
            {tab === 'technical-deep' && (
              <TechnicalDeepTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Trust & Revenue */}
            {tab === 'trust-revenue' && (
              <TrustRevenueTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* UX & Conversion */}
            {tab === 'ux-conversion' && (
              <UxConversionTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Growth & Landing */}
            {tab === 'growth-landing' && (
              <GrowthLandingTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Live Intelligence */}
            {tab === 'live-intelligence' && (
              <LiveIntelligenceTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* History */}
            {tab === 'history' && (
              <HistoryTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
                historyLoading={historyLoading}
                historyData={historyData}
                loadHistory={loadHistory}
              />
            )}

            {/* Monitoring */}
            {tab === 'monitoring' && (
              <MonitoringTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* GTmetrix API */}
            {tab === 'gtmetrix-api' && (
              <GtmetrixApiTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Keywords */}
            {tab === 'keywords' && (
              <KeywordsTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* SEO Ranking */}
            {tab === 'seo-ranking' && (
              <SeoRankingTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* AI Models Ranking */}
            {tab === 'ai-models-ranking' && (
              <AiModelsRankingTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Hashtags */}
            {tab === 'hashtags' && (
              <HashtagsTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Visibility */}
            {tab === 'visibility' && (
              <VisibilityTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Leads */}
            {tab === 'leads' && (
              <LeadsTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Clicks */}
            {tab === 'clicks' && (
              <ClicksTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Trends vs Platform */}
            {tab === 'trends-vs-platform' && (
              <TrendsVsPlatformTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Power Ranking */}
            {tab === 'power-ranking' && (
              <PowerRankingTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}

            {/* Autonomous */}
            {tab === 'autonomous' && (
              <AutonomousTab
                result={result}
                card={card}
                isOfflinePreview={isOfflinePreview}
                autoFixing={autoFixing}
                autoFixResult={autoFixResult}
                autoFixError={autoFixError}
                fixingItem={fixingItem}
                fixedItems={fixedItems}
                fixSingleItem={fixSingleItem}
                optimizeSite={optimizeSite}
              />
            )}
          </>
        )}
      </div>
    </main>
  );
}
