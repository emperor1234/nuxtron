export type CrawlerSite = {
  id: string;
  domain: string;
  displayName: string;
  cmsType: string;
  jsFramework: string;
  snippetInstalled: boolean;
  ssrEnabled: boolean;
  aiCrawlerHits: number;
};

export type CrawlerDashboard = {
  windowHours: number;
  summary: {
    totalHits: number;
    aiCrawlerHits: number;
    ssrServedHits: number;
    blockedHits: number;
    averageRenderTimeMs: number;
    visibilityScore: number;
    sitesRegistered: number;
    sitesWithSnippet: number;
  };
  topCrawlers: Array<{ name: string; hits: number }>;
  topPages: Array<{ url: string; hits: number }>;
};

export type CrawlerReadiness = {
  score: number;
  grade: string;
  productionReady: boolean;
  totalSites: number;
  coverage: {
    snippetInstalledPct: number;
    ssrEnabledPct: number;
    cloudflareZoneConfiguredPct: number;
    deploymentWebhookConfiguredPct: number;
  };
};

export type BulkSnippetPlan = {
  deployments: Array<{
    domain: string;
    status: 'planned';
    mode: string;
    webhookConfigured: boolean;
  }>;
  summary: {
    sitesTargeted: number;
    planned: number;
  };
};

export type CloudflarePlan = {
  action: string;
  sitesTargeted: number;
  results: Array<{ domain: string; eligible: boolean }>;
};

export type RegisteredSite = { site: CrawlerSite; snippet: string };
export type SiteSnippet = { domain: string; snippet: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && Number.isFinite(value) && value >= 0;
}

function isFiniteNonNegative(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

function isPercentage(value: unknown): value is number {
  return isFiniteNonNegative(value) && value <= 100;
}

function parseSite(value: unknown): CrawlerSite | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.id !== 'string' || !value.id.trim() ||
    typeof value.domain !== 'string' || !value.domain.trim() ||
    typeof value.display_name !== 'string' ||
    typeof value.cms_type !== 'string' ||
    typeof value.js_framework !== 'string' ||
    typeof value.snippet_installed !== 'boolean' ||
    typeof value.ssr_enabled !== 'boolean' ||
    !isCount(value.ai_crawlers_detected_total)
  ) return null;
  return {
    id: value.id,
    domain: value.domain,
    displayName: value.display_name,
    cmsType: value.cms_type,
    jsFramework: value.js_framework,
    snippetInstalled: value.snippet_installed,
    ssrEnabled: value.ssr_enabled,
    aiCrawlerHits: value.ai_crawlers_detected_total,
  };
}

export function parseCrawlerSites(value: unknown): CrawlerSite[] | null {
  if (!isRecord(value) || value.status !== 'ok' || !isCount(value.count) || !Array.isArray(value.sites)) return null;
  if (value.count !== value.sites.length) return null;
  const sites = value.sites.map(parseSite);
  return sites.every((site) => site !== null) ? sites as CrawlerSite[] : null;
}

export function parseRegisteredSite(value: unknown): RegisteredSite | null {
  if (!isRecord(value) || value.status !== 'ok' || typeof value.snippet !== 'string') return null;
  const site = parseSite(value.site);
  return site ? { site, snippet: value.snippet } : null;
}

export function parseSiteSnippet(value: unknown): SiteSnippet | null {
  if (
    !isRecord(value) || value.status !== 'ok' ||
    typeof value.site_id !== 'string' || !value.site_id.trim() ||
    typeof value.domain !== 'string' || !value.domain.trim() ||
    typeof value.snippet !== 'string' || !value.snippet.trim()
  ) return null;
  return { domain: value.domain, snippet: value.snippet };
}

export function parseCrawlerDashboard(value: unknown): CrawlerDashboard | null {
  if (!isRecord(value) || value.status !== 'ok' || !isRecord(value.summary)) return null;
  const summary = value.summary;
  if (
    !isCount(summary.total_hits) || !isCount(summary.ai_crawler_hits) ||
    !isCount(summary.ssr_served_hits) || !isCount(summary.blocked_hits) ||
    !isFiniteNonNegative(summary.avg_render_time_ms) || !isPercentage(summary.visibility_score) ||
    !isCount(summary.sites_registered) || !isCount(summary.sites_with_snippet) ||
    !isCount(value.window_hours) || value.window_hours < 1 || value.window_hours > 168 ||
    !Array.isArray(value.top_crawlers) || !Array.isArray(value.top_pages)
  ) return null;

  const topCrawlers: Array<{ name: string; hits: number }> = [];
  for (const raw of value.top_crawlers) {
    if (!isRecord(raw) || typeof raw.name !== 'string' || !isCount(raw.hits)) return null;
    topCrawlers.push({ name: raw.name, hits: raw.hits });
  }
  const topPages: Array<{ url: string; hits: number }> = [];
  for (const raw of value.top_pages) {
    if (!isRecord(raw) || typeof raw.url !== 'string' || !isCount(raw.hits)) return null;
    topPages.push({ url: raw.url, hits: raw.hits });
  }

  return {
    windowHours: value.window_hours,
    summary: {
      totalHits: summary.total_hits,
      aiCrawlerHits: summary.ai_crawler_hits,
      ssrServedHits: summary.ssr_served_hits,
      blockedHits: summary.blocked_hits,
      averageRenderTimeMs: summary.avg_render_time_ms,
      visibilityScore: summary.visibility_score,
      sitesRegistered: summary.sites_registered,
      sitesWithSnippet: summary.sites_with_snippet,
    },
    topCrawlers,
    topPages,
  };
}

export function parseCrawlerReadiness(value: unknown): CrawlerReadiness | null {
  if (!isRecord(value) || value.status !== 'ok' || !isRecord(value.readiness) || !isRecord(value.coverage)) return null;
  const readiness = value.readiness;
  const coverage = value.coverage;
  if (
    !isPercentage(readiness.score) || typeof readiness.grade !== 'string' ||
    typeof readiness.production_ready !== 'boolean' || !isCount(readiness.total_sites) ||
    !isPercentage(coverage.snippet_installed_pct) || !isPercentage(coverage.ssr_enabled_pct) ||
    !isPercentage(coverage.cloudflare_zone_configured_pct) || !isPercentage(coverage.deployment_webhook_configured_pct)
  ) return null;
  return {
    score: readiness.score,
    grade: readiness.grade,
    productionReady: readiness.production_ready,
    totalSites: readiness.total_sites,
    coverage: {
      snippetInstalledPct: coverage.snippet_installed_pct,
      ssrEnabledPct: coverage.ssr_enabled_pct,
      cloudflareZoneConfiguredPct: coverage.cloudflare_zone_configured_pct,
      deploymentWebhookConfiguredPct: coverage.deployment_webhook_configured_pct,
    },
  };
}

export function parseBulkSnippetPlan(value: unknown): BulkSnippetPlan | null {
  if (!isRecord(value) || value.status !== 'ok' || value.dry_run !== true || !isRecord(value.summary) || !Array.isArray(value.deployments)) {
    return null;
  }
  const summary = value.summary;
  if (!isCount(summary.sites_targeted) || !isCount(summary.planned) || summary.sites_targeted !== value.deployments.length) return null;
  const deployments: BulkSnippetPlan['deployments'] = [];
  for (const raw of value.deployments) {
    if (
      !isRecord(raw) || typeof raw.domain !== 'string' || raw.status !== 'planned' ||
      typeof raw.mode !== 'string' || typeof raw.webhook_configured !== 'boolean'
    ) return null;
    deployments.push({ domain: raw.domain, status: 'planned', mode: raw.mode, webhookConfigured: raw.webhook_configured });
  }
  return { deployments, summary: { sitesTargeted: summary.sites_targeted, planned: summary.planned } };
}

export function parseCloudflarePlan(value: unknown): CloudflarePlan | null {
  if (!isRecord(value) || value.status !== 'ok' || value.dry_run !== true || typeof value.action !== 'string') return null;
  if (!isCount(value.sites_targeted) || !Array.isArray(value.results) || value.sites_targeted !== value.results.length) return null;
  const results: CloudflarePlan['results'] = [];
  for (const raw of value.results) {
    if (!isRecord(raw) || typeof raw.domain !== 'string' || typeof raw.eligible !== 'boolean') return null;
    results.push({ domain: raw.domain, eligible: raw.eligible });
  }
  return { action: value.action, sitesTargeted: value.sites_targeted, results };
}
