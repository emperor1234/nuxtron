import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend } = vi.hoisted(() => ({ apiGet: vi.fn(), apiSend: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-test' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import AiVisibilityDashboardPage from './page';

afterEach(() => cleanup());
beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
});

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
const sitesResponse = { status: 'ok', count: 1, sites: [site] };
const emptySitesResponse = { status: 'ok', count: 0, sites: [] };
const dashboardResponse = {
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
const readinessResponse = {
  status: 'ok',
  readiness: { score: 0, grade: 'D', production_ready: false, total_sites: 1 },
  coverage: {
    snippet_installed_pct: 0,
    ssr_enabled_pct: 0,
    cloudflare_zone_configured_pct: 0,
    deployment_webhook_configured_pct: 0,
  },
};

function selectSite() {
  fireEvent.change(screen.getByLabelText('Website scope'), { target: { value: 'site-123' } });
}

describe('AI Crawler Visibility Dashboard', () => {
  it('shows a real no-site onboarding state and does not load crawler metrics automatically', async () => {
    apiGet.mockResolvedValue(emptySitesResponse);
    render(<AiVisibilityDashboardPage />);

    expect(await screen.findByText(/No sites are registered in this workspace yet/)).toBeTruthy();
    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith('/ai-crawler/sites', 'workspace-test');
    expect((screen.getByRole('button', { name: 'Load 24-hour visibility' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('registers a user-provided site in the session workspace and displays the returned install snippet safely', async () => {
    apiGet.mockResolvedValueOnce(emptySitesResponse).mockResolvedValueOnce(sitesResponse);
    apiSend.mockResolvedValue({ status: 'ok', site, snippet: '<script>install-example</script>' });
    render(<AiVisibilityDashboardPage />);
    expect(await screen.findByText(/No sites are registered in this workspace yet/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Root domain'), { target: { value: 'https://example.com/path' } });
    fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'Example' } });
    fireEvent.change(screen.getByLabelText('Platform or CMS'), { target: { value: 'custom' } });
    fireEvent.change(screen.getByLabelText('JavaScript framework'), { target: { value: 'none' } });
    fireEvent.click(screen.getByRole('button', { name: 'Register site' }));

    expect(await screen.findByText(/example\.com was added to this workspace/)).toBeTruthy();
    expect(screen.getByText('<script>install-example</script>')).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/ai-crawler/sites', 'POST', {
      domain: 'example.com',
      display_name: 'Example',
      cms_type: 'custom',
      js_framework: 'none',
    }, 'workspace-test');
  });

  it('loads site-scoped 24-hour telemetry and shows zero counts as an actual empty event window', async () => {
    apiGet
      .mockResolvedValueOnce(sitesResponse)
      .mockResolvedValueOnce(dashboardResponse)
      .mockResolvedValueOnce(readinessResponse);
    render(<AiVisibilityDashboardPage />);
    expect(await screen.findByRole('option', { name: 'Example · example.com' })).toBeTruthy();
    selectSite();
    fireEvent.click(screen.getByRole('button', { name: 'Load 24-hour visibility' }));

    expect(await screen.findByText(/No crawler events were recorded for example\.com/)).toBeTruthy();
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getByText('AI crawl SSR/cache coverage')).toBeTruthy();
    expect(apiGet).toHaveBeenNthCalledWith(2, '/ai-crawler/dashboard?window_hours=24&site_id=site-123', 'workspace-test');
    expect(apiGet).toHaveBeenNthCalledWith(3, '/ai-crawler/readiness', 'workspace-test');
    expect(screen.queryByText('workspace-test')).toBeNull();
  });

  it('shows per-site outcomes from dry-run-only deployment and Cloudflare plans', async () => {
    apiGet
      .mockResolvedValueOnce(sitesResponse)
      .mockResolvedValueOnce(dashboardResponse)
      .mockResolvedValueOnce(readinessResponse);
    apiSend
      .mockResolvedValueOnce({
        status: 'ok',
        dry_run: true,
        summary: { sites_targeted: 1, planned: 1, deployed: 0, failed: 0, manual_required: 0 },
        deployments: [{ site_id: 'site-123', domain: 'example.com', status: 'planned', mode: 'manual', webhook_configured: false }],
      })
      .mockResolvedValueOnce({
        status: 'ok',
        dry_run: true,
        action: 'allow_ai_crawlers',
        sites_targeted: 1,
        results: [{ site_id: 'site-123', domain: 'example.com', eligible: false }],
      });
    render(<AiVisibilityDashboardPage />);
    expect(await screen.findByRole('option', { name: 'Example · example.com' })).toBeTruthy();
    selectSite();
    fireEvent.click(screen.getByRole('button', { name: 'Plan bulk snippet deployment' }));

    expect(await screen.findByText('Bulk snippet deployment plan')).toBeTruthy();
    expect(screen.getByText('Manual installation will be needed.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Plan Cloudflare allowlist' }));
    expect(await screen.findByText('Cloudflare allowlist plan')).toBeTruthy();
    expect(screen.getByText('Not eligible yet')).toBeTruthy();
    expect(apiSend).toHaveBeenNthCalledWith(1, '/ai-crawler/snippets/deploy-bulk', 'POST', { dry_run: true, site_ids: ['site-123'] }, 'workspace-test');
    expect(apiSend).toHaveBeenNthCalledWith(2, '/ai-crawler/cloudflare/auto-sync', 'POST', { action: 'allow_ai_crawlers', dry_run: true, site_ids: ['site-123'] }, 'workspace-test');
    expect(screen.queryByText('Synced')).toBeNull();
  });

  it('keeps readiness visible when the telemetry response is malformed instead of showing fallback zeros', async () => {
    apiGet
      .mockResolvedValueOnce(sitesResponse)
      .mockResolvedValueOnce({ status: 'ok', summary: { total_hits: 0 } })
      .mockResolvedValueOnce(readinessResponse);
    render(<AiVisibilityDashboardPage />);
    expect(await screen.findByRole('option', { name: 'Example · example.com' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Load 24-hour visibility' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/crawler dashboard response was incomplete/i)).toBeTruthy();
    expect(screen.getByText('Configuration coverage')).toBeTruthy();
    expect(screen.queryByText('Recorded crawler activity')).toBeNull();
  });
});
