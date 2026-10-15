import { describe, expect, it } from 'vitest';
import {
  parseBulkSnippetPlan,
  parseCloudflarePlan,
  parseCrawlerDashboard,
  parseCrawlerReadiness,
  parseCrawlerSites,
  parseRegisteredSite,
  parseSiteSnippet,
} from './visibility-model';

const site = {
  id: 'site-123',
  domain: 'example.com',
  display_name: 'Example',
  cms_type: 'custom',
  js_framework: 'none',
  snippet_installed: false,
  ssr_enabled: false,
  ai_crawlers_detected_total: 0,
};

const dashboard = {
  status: 'ok',
  window_hours: 24,
  summary: {
    total_hits: 0,
    ai_crawler_hits: 0,
    ssr_served_hits: 0,
    blocked_hits: 0,
    avg_render_time_ms: 0,
    visibility_score: 0,
    sites_registered: 1,
    sites_with_snippet: 0,
  },
  top_crawlers: [],
  top_pages: [],
};

describe('AI crawler visibility model', () => {
  it('accepts a genuinely empty event window and an empty registered-site list', () => {
    expect(parseCrawlerDashboard(dashboard)?.summary.totalHits).toBe(0);
    expect(parseCrawlerSites({ status: 'ok', count: 0, sites: [] })).toEqual([]);
  });

  it('rejects missing counters, malformed crawler data, and invalid site identifiers', () => {
    expect(parseCrawlerDashboard({ ...dashboard, summary: { ...dashboard.summary, blocked_hits: undefined } })).toBeNull();
    expect(parseCrawlerDashboard({ ...dashboard, top_pages: [{ url: '/page', hits: -1 }] })).toBeNull();
    expect(parseCrawlerSites({ status: 'ok', count: 1, sites: [{ ...site, id: '' }] })).toBeNull();
    expect(parseCrawlerSites({ status: 'ok', count: 2, sites: [site] })).toBeNull();
  });

  it('parses readiness only when all configuration metrics are explicit and bounded', () => {
    expect(parseCrawlerReadiness({
      status: 'ok',
      readiness: { score: 0, grade: 'D', production_ready: false, total_sites: 0 },
      coverage: {
        snippet_installed_pct: 0,
        ssr_enabled_pct: 0,
        cloudflare_zone_configured_pct: 0,
        deployment_webhook_configured_pct: 0,
      },
    })?.totalSites).toBe(0);
    expect(parseCrawlerReadiness({ status: 'ok', readiness: {}, coverage: {} })).toBeNull();
  });

  it('accepts only per-site dry-run deployment and Cloudflare plans', () => {
    const bulk = {
      status: 'ok',
      dry_run: true,
      summary: { sites_targeted: 1, planned: 1, deployed: 0, failed: 0, manual_required: 0 },
      deployments: [{ site_id: 'site-123', domain: 'example.com', status: 'planned', mode: 'manual', webhook_configured: false }],
    };
    expect(parseBulkSnippetPlan(bulk)?.deployments[0]?.domain).toBe('example.com');
    expect(parseBulkSnippetPlan({ ...bulk, dry_run: false })).toBeNull();
    expect(parseBulkSnippetPlan({ ...bulk, deployments: [{ ...bulk.deployments[0], status: 'deployed' }] })).toBeNull();

    const cloudflare = {
      status: 'ok',
      dry_run: true,
      action: 'allow_ai_crawlers',
      sites_targeted: 1,
      results: [{ site_id: 'site-123', domain: 'example.com', eligible: false }],
    };
    expect(parseCloudflarePlan(cloudflare)?.results[0]?.eligible).toBe(false);
    expect(parseCloudflarePlan({ ...cloudflare, dry_run: false })).toBeNull();
  });

  it('validates the newly registered site before using its identifier for follow-up actions', () => {
    expect(parseRegisteredSite({ status: 'ok', site, snippet: '<script></script>' })?.site.id).toBe('site-123');
    expect(parseRegisteredSite({ status: 'ok', site: { ...site, id: '' }, snippet: '<script></script>' })).toBeNull();
    expect(parseSiteSnippet({ status: 'ok', site_id: 'site-123', domain: 'example.com', snippet: '<script></script>' })?.domain).toBe('example.com');
    expect(parseSiteSnippet({ status: 'ok', site_id: '', domain: 'example.com', snippet: '<script></script>' })).toBeNull();
  });
});
