'use client';

import { useState } from 'react';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type DashboardResponse = {
  summary: {
    total_hits: number;
    ai_crawler_hits: number;
    ssr_served_hits: number;
    blocked_hits: number;
    avg_render_time_ms: number;
    visibility_score: number;
    sites_registered: number;
    sites_with_snippet: number;
  };
  top_crawlers: Array<{ name: string; hits: number }>;
  top_pages: Array<{ url: string; hits: number }>;
};

type SitesResponse = {
  count: number;
  sites: Array<{
    id: string;
    domain: string;
    snippet_installed: boolean;
    ssr_enabled: boolean;
    ai_crawlers_detected_total: number;
  }>;
};

type ReadinessResponse = {
  readiness: {
    score: number;
    grade: string;
    production_ready: boolean;
    total_sites: number;
  };
  coverage: {
    snippet_installed_pct: number;
    ssr_enabled_pct: number;
    cloudflare_zone_configured_pct: number;
    deployment_webhook_configured_pct: number;
  };
};

type BulkDeployResponse = {
  summary: {
    sites_targeted: number;
    deployed: number;
    failed: number;
    manual_required: number;
    planned: number;
  };
};

type CloudflareAutoSyncResponse = {
  sites_targeted?: number;
  summary?: {
    sites_targeted: number;
    synced: number;
    skipped: number;
    failed: number;
  };
};

export default function AiVisibilityDashboardPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [sites, setSites] = useState<SitesResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [bulkPlan, setBulkPlan] = useState<BulkDeployResponse | null>(null);
  const [cloudflarePlan, setCloudflarePlan] = useState<CloudflareAutoSyncResponse | null>(null);

  async function loadVisibility() {
    setLoading(true);
    setError('');
    try {
      const [dashboardRes, sitesRes] = await Promise.all([
        apiGet<DashboardResponse>('/ai-crawler/dashboard?window_hours=24', tenantId),
        apiGet<SitesResponse>('/ai-crawler/sites', tenantId),
      ]);
      setDashboard(dashboardRes);
      setSites(sitesRes);

      const readinessRes = await apiGet<ReadinessResponse>('/ai-crawler/readiness', tenantId);
      setReadiness(readinessRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load AI visibility dashboard');
    } finally {
      setLoading(false);
    }
  }

  async function runBulkDeployPlan() {
    setError('');
    try {
      const response = await apiSend<BulkDeployResponse>(
        '/ai-crawler/snippets/deploy-bulk',
        'POST',
        { dry_run: true },
        tenantId
      );
      setBulkPlan(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run bulk deployment plan');
    }
  }

  async function runCloudflarePlan() {
    setError('');
    try {
      const response = await apiSend<CloudflareAutoSyncResponse>(
        '/ai-crawler/cloudflare/auto-sync',
        'POST',
        { action: 'allow_ai_crawlers', dry_run: true },
        tenantId
      );
      setCloudflarePlan(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Cloudflare sync plan');
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Visibility Engine</p>
        <h1>AI Crawler Visibility Dashboard</h1>
        <p>
          Monitor crawler traffic, SSR coverage, blocked hits, and site-level snippet readiness for AI-search access.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <button onClick={() => void loadVisibility()} disabled={loading}>
          {loading ? 'Loading...' : 'Load Visibility Data'}
        </button>
        <button onClick={() => void runBulkDeployPlan()} style={{ marginLeft: 12 }}>
          Plan Bulk Snippet Deploy
        </button>
        <button onClick={() => void runCloudflarePlan()} style={{ marginLeft: 12 }}>
          Plan Cloudflare Auto-Sync
        </button>
        {error ? <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p> : null}
      </section>

      {readiness ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Readiness Grade</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{readiness.readiness.grade}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Readiness Score</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{readiness.readiness.score}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Snippet Coverage</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{readiness.coverage.snippet_installed_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Cloudflare Zone Coverage</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{readiness.coverage.cloudflare_zone_configured_pct}%</p>
          </article>
        </section>
      ) : null}

      {bulkPlan ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Bulk Snippet Deployment Plan</h3>
          <p style={{ marginTop: 0 }}>
            Targeted: {bulkPlan.summary.sites_targeted} | Planned: {bulkPlan.summary.planned} | Manual:{' '}
            {bulkPlan.summary.manual_required}
          </p>
        </section>
      ) : null}

      {cloudflarePlan ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Cloudflare Auto-Sync Plan</h3>
          <p style={{ marginTop: 0 }}>
            Targeted: {cloudflarePlan.sites_targeted ?? cloudflarePlan.summary?.sites_targeted ?? 0}
          </p>
        </section>
      ) : null}

      {dashboard ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Visibility Score</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.visibility_score}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>AI Crawler Hits</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.ai_crawler_hits.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>SSR Served</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.ssr_served_hits.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Blocked Hits</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.blocked_hits.toLocaleString()}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Avg Render Time</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.avg_render_time_ms.toLocaleString()} ms</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Registered Sites</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{dashboard.summary.sites_registered.toLocaleString()}</p>
          </article>
        </section>
      ) : null}

      {dashboard ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Top Crawlers</h3>
            <ul className="bullet-list">
              {dashboard.top_crawlers.map((crawler) => (
                <li key={crawler.name}>
                  {crawler.name}: {crawler.hits.toLocaleString()} hits
                </li>
              ))}
            </ul>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Top Pages</h3>
            <ul className="bullet-list">
              {dashboard.top_pages.map((page, idx) => (
                <li key={`${idx}-${page.url}`}>
                  {page.url}: {page.hits.toLocaleString()} hits
                </li>
              ))}
            </ul>
          </article>
        </section>
      ) : null}

      {sites ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Site Coverage</h3>
          <p style={{ marginTop: 0 }}>Total Sites: {sites.count}</p>
          <ul className="bullet-list">
            {sites.sites.map((site) => (
              <li key={site.id}>
                {site.domain} - snippet: {site.snippet_installed ? 'installed' : 'not installed'}, ssr:{' '}
                {site.ssr_enabled ? 'enabled' : 'disabled'}, ai hits: {site.ai_crawlers_detected_total}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
