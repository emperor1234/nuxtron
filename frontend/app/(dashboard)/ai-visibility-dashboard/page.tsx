'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import {
  Badge,
  Button,
  Card,
  CardTitle,
  Field,
  FieldSelect,
  Page,
  PageHeader,
  Stat,
  StatGrid,
  TableWrap,
  tableClass,
} from '../_ui/kit';
import {
  parseBulkSnippetPlan,
  parseCloudflarePlan,
  parseCrawlerDashboard,
  parseCrawlerReadiness,
  parseCrawlerSites,
  parseRegisteredSite,
  parseSiteSnippet,
  type BulkSnippetPlan,
  type CrawlerDashboard,
  type CrawlerReadiness,
  type CrawlerSite,
  type CloudflarePlan,
  type SiteSnippet,
} from './visibility-model';
import styles from './visibility.module.css';

const CMS_TYPES = [
  ['wordpress', 'WordPress'], ['shopify', 'Shopify'], ['wix', 'Wix'], ['webflow', 'Webflow'],
  ['next_js', 'Next.js'], ['nuxt', 'Nuxt'], ['angular', 'Angular'], ['vue', 'Vue'], ['react', 'React'],
  ['gatsby', 'Gatsby'], ['hugo', 'Hugo'], ['jekyll', 'Jekyll'], ['custom', 'Other / custom'],
] as const;

const JS_FRAMEWORKS = [
  ['none', 'No JavaScript framework'], ['react', 'React'], ['vue', 'Vue'], ['angular', 'Angular'],
  ['next', 'Next.js'], ['nuxt', 'Nuxt'], ['svelte', 'Svelte'], ['other', 'Other'],
] as const;

function sessionWorkspace(): string {
  try {
    return resolveSessionTenant();
  } catch {
    return '';
  }
}

function normalizeRootDomain(value: string): string | null {
  const raw = value.trim().toLowerCase().replace(/^https?:\/\//, '').split(/[/?#]/, 1)[0] ?? '';
  if (!raw || raw.includes('@') || raw.includes(':') || raw.length > 253) return null;
  try {
    const hostname = new URL(`https://${raw}`).hostname.toLowerCase();
    const labels = hostname.split('.');
    if (labels.length < 2 || labels.some((label) => !label || label.length > 63)) return null;
    if (labels.some((label) => !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(label))) return null;
    return hostname;
  } catch {
    return null;
  }
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value);
}

export default function AiVisibilityDashboardPage() {
  const [tenantId] = useState(sessionWorkspace);
  const hasWorkspace = tenantId.trim().length > 0;

  const [sites, setSites] = useState<CrawlerSite[] | null>(null);
  const [sitesStatus, setSitesStatus] = useState<'loading' | 'ready' | 'error'>(() => hasWorkspace ? 'loading' : 'error');
  const [sitesError, setSitesError] = useState(() => hasWorkspace ? '' : 'Workspace context is unavailable.');
  const [selectedSiteId, setSelectedSiteId] = useState('');

  const [dashboard, setDashboard] = useState<CrawlerDashboard | null>(null);
  const [readiness, setReadiness] = useState<CrawlerReadiness | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState('');
  const [readinessError, setReadinessError] = useState('');

  const [bulkPlan, setBulkPlan] = useState<BulkSnippetPlan | null>(null);
  const [cloudflarePlan, setCloudflarePlan] = useState<CloudflarePlan | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [cloudflareLoading, setCloudflareLoading] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [cloudflareError, setCloudflareError] = useState('');

  const [displayName, setDisplayName] = useState('');
  const [domainInput, setDomainInput] = useState('');
  const [cmsType, setCmsType] = useState('');
  const [jsFramework, setJsFramework] = useState('');
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState('');
  const [registerSuccess, setRegisterSuccess] = useState('');
  const [activeSnippet, setActiveSnippet] = useState<SiteSnippet | null>(null);
  const [snippetLoadingId, setSnippetLoadingId] = useState('');
  const [snippetError, setSnippetError] = useState('');
  const [snippetCopyStatus, setSnippetCopyStatus] = useState('');

  useEffect(() => {
    if (!hasWorkspace) return;
    let isActive = true;
    apiGet<unknown>('/ai-crawler/sites', tenantId)
      .then((response) => {
        const parsed = parseCrawlerSites(response);
        if (!parsed) throw new Error('The registered-site response was incomplete.');
        if (!isActive) return;
        setSites(parsed);
        setSitesStatus('ready');
        setSitesError('');
      })
      .catch((cause: unknown) => {
        if (!isActive) return;
        setSites(null);
        setSitesStatus('error');
        setSitesError(cause instanceof Error ? cause.message : 'Registered sites are unavailable.');
      });
    return () => { isActive = false; };
  }, [hasWorkspace, tenantId]);

  async function refreshSites(): Promise<CrawlerSite[] | null> {
    if (!hasWorkspace) return null;
    setSitesStatus('loading');
    setSitesError('');
    try {
      const response = await apiGet<unknown>('/ai-crawler/sites', tenantId);
      const parsed = parseCrawlerSites(response);
      if (!parsed) throw new Error('The registered-site response was incomplete.');
      setSites(parsed);
      setSitesStatus('ready');
      if (selectedSiteId && !parsed.some((site) => site.id === selectedSiteId)) setSelectedSiteId('');
      return parsed;
    } catch (cause) {
      setSites(null);
      setSitesStatus('error');
      setSitesError(cause instanceof Error ? cause.message : 'Registered sites are unavailable.');
      return null;
    }
  }

  function changeSiteScope(nextSiteId: string) {
    setSelectedSiteId(nextSiteId);
    setDashboard(null);
    setReadiness(null);
    setDashboardError('');
    setReadinessError('');
    setBulkPlan(null);
    setCloudflarePlan(null);
    setBulkError('');
    setCloudflareError('');
  }

  async function loadVisibility() {
    if (!hasWorkspace || sitesStatus !== 'ready' || !sites?.length) return;
    setDashboard(null);
    setReadiness(null);
    setDashboardError('');
    setReadinessError('');
    setDashboardLoading(true);
    const query = new URLSearchParams({ window_hours: '24' });
    if (selectedSiteId) query.set('site_id', selectedSiteId);
    try {
      const [dashboardResponse, readinessResponse] = await Promise.allSettled([
        apiGet<unknown>(`/ai-crawler/dashboard?${query.toString()}`, tenantId),
        apiGet<unknown>('/ai-crawler/readiness', tenantId),
      ]);

      if (dashboardResponse.status === 'fulfilled') {
        const parsed = parseCrawlerDashboard(dashboardResponse.value);
        if (parsed) setDashboard(parsed);
        else setDashboardError('The crawler dashboard response was incomplete.');
      } else {
        setDashboardError(dashboardResponse.reason instanceof Error ? dashboardResponse.reason.message : 'Crawler telemetry is unavailable.');
      }

      if (readinessResponse.status === 'fulfilled') {
        const parsed = parseCrawlerReadiness(readinessResponse.value);
        if (parsed) setReadiness(parsed);
        else setReadinessError('The site-readiness response was incomplete.');
      } else {
        setReadinessError(readinessResponse.reason instanceof Error ? readinessResponse.reason.message : 'Site-readiness data is unavailable.');
      }
    } finally {
      setDashboardLoading(false);
    }
  }

  async function runBulkDeployPlan() {
    if (!hasWorkspace || sitesStatus !== 'ready' || !sites?.length) return;
    setBulkPlan(null);
    setBulkError('');
    setBulkLoading(true);
    try {
      const response = await apiSend<unknown>(
        '/ai-crawler/snippets/deploy-bulk',
        'POST',
        { dry_run: true, site_ids: selectedSiteId ? [selectedSiteId] : [] },
        tenantId
      );
      const parsed = parseBulkSnippetPlan(response);
      if (!parsed) throw new Error('The service did not return a valid dry-run deployment plan.');
      setBulkPlan(parsed);
    } catch (cause) {
      setBulkError(cause instanceof Error ? cause.message : 'The deployment plan is unavailable.');
    } finally {
      setBulkLoading(false);
    }
  }

  async function runCloudflarePlan() {
    if (!hasWorkspace || sitesStatus !== 'ready' || !sites?.length) return;
    setCloudflarePlan(null);
    setCloudflareError('');
    setCloudflareLoading(true);
    try {
      const response = await apiSend<unknown>(
        '/ai-crawler/cloudflare/auto-sync',
        'POST',
        { action: 'allow_ai_crawlers', dry_run: true, site_ids: selectedSiteId ? [selectedSiteId] : [] },
        tenantId
      );
      const parsed = parseCloudflarePlan(response);
      if (!parsed) throw new Error('The service did not return a valid dry-run Cloudflare plan.');
      setCloudflarePlan(parsed);
    } catch (cause) {
      setCloudflareError(cause instanceof Error ? cause.message : 'The Cloudflare plan is unavailable.');
    } finally {
      setCloudflareLoading(false);
    }
  }

  async function registerSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasWorkspace) {
      setRegisterError('Workspace context is unavailable. Sign in or select a workspace before adding a site.');
      return;
    }
    const domain = normalizeRootDomain(domainInput);
    const cleanName = displayName.trim();
    if (!domain) {
      setRegisterError('Enter a valid root domain, such as example.com, without a path or port.');
      return;
    }
    if (!cleanName || !cmsType || !jsFramework) {
      setRegisterError('Complete the display name and select the site platform and JavaScript framework.');
      return;
    }

    setRegisterError('');
    setRegisterSuccess('');
    setRegistering(true);
    try {
      const response = await apiSend<unknown>(
        '/ai-crawler/sites',
        'POST',
        { domain, display_name: cleanName, cms_type: cmsType, js_framework: jsFramework },
        tenantId
      );
      const registered = parseRegisteredSite(response);
      if (!registered) throw new Error('The site-registration service returned an incomplete response.');
      setSelectedSiteId(registered.site.id);
      setActiveSnippet({ domain: registered.site.domain, snippet: registered.snippet });
      setSnippetCopyStatus('');
      setRegisterSuccess(`${registered.site.domain} was added to this workspace. Review and install its snippet before expecting crawler events.`);
      setDisplayName('');
      setDomainInput('');
      setCmsType('');
      setJsFramework('');
      setDashboard(null);
      setReadiness(null);
      setBulkPlan(null);
      setCloudflarePlan(null);
      await refreshSites();
    } catch (cause) {
      setRegisterError(cause instanceof Error ? cause.message : 'The site could not be registered.');
    } finally {
      setRegistering(false);
    }
  }

  async function loadSiteSnippet(site: CrawlerSite) {
    setSnippetError('');
    setSnippetCopyStatus('');
    setSnippetLoadingId(site.id);
    try {
      const response = await apiGet<unknown>(`/ai-crawler/sites/${encodeURIComponent(site.id)}/snippet`, tenantId);
      const parsed = parseSiteSnippet(response);
      if (!parsed) throw new Error('The site snippet response was incomplete.');
      setActiveSnippet(parsed);
    } catch (cause) {
      setSnippetError(cause instanceof Error ? cause.message : 'The site snippet is unavailable.');
    } finally {
      setSnippetLoadingId('');
    }
  }

  async function copySnippet() {
    if (!activeSnippet) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(activeSnippet.snippet);
      setSnippetCopyStatus('Install snippet copied to clipboard.');
    } catch {
      setSnippetCopyStatus('Copy is unavailable here. Select the snippet below and copy it manually.');
    }
  }

  const selectedSite = sites?.find((site) => site.id === selectedSiteId) ?? null;
  const canRunSiteActions = hasWorkspace && sitesStatus === 'ready' && (sites?.length ?? 0) > 0;
  const siteActionPending = dashboardLoading || bulkLoading || cloudflareLoading;
  const dashboardScope = selectedSite?.domain ?? 'All registered sites';

  return (
    <Page className={styles.layout}>
      <PageHeader
        title="AI crawler visibility"
        subtitle="Review crawler events, site setup coverage, and safe deployment plans for this workspace."
        actions={<Badge tone="neutral">24-hour event window</Badge>}
      />

      {!hasWorkspace ? <p role="alert" className={styles.error}>Workspace context is unavailable. Sign in or select a workspace before reviewing crawler visibility.</p> : null}
      <p className={styles.intro}>
        Event counts reflect requests recorded by the crawler service for this workspace. AI-crawl coverage describes SSR/cache handling of observed crawler requests; it is not a search ranking or AI-answer visibility measurement.
      </p>

      <Card>
        <div className={styles.scopeRow}>
          <div className={styles.scopeSelect}>
            <FieldSelect
              id="visibility-site-scope"
              label="Website scope"
              value={selectedSiteId}
              onChange={(event) => changeSiteScope(event.target.value)}
              disabled={sitesStatus !== 'ready' || siteActionPending}
            >
              <option value="">All registered sites</option>
              {(sites ?? []).map((site) => <option key={site.id} value={site.id}>{site.displayName || site.domain} · {site.domain}</option>)}
            </FieldSelect>
          </div>
          <div className={styles.actionRow}>
            <Button type="button" variant="primary" onClick={() => void loadVisibility()} disabled={!canRunSiteActions || siteActionPending}>
              {dashboardLoading ? 'Loading visibility…' : 'Load 24-hour visibility'}
            </Button>
            <Button type="button" variant="ghost" onClick={() => void refreshSites()} disabled={!hasWorkspace || sitesStatus === 'loading' || siteActionPending}>
              {sitesStatus === 'loading' ? 'Loading sites…' : 'Refresh sites'}
            </Button>
          </div>
        </div>
        <div className={`${styles.actionRow} ${styles.secondaryActionRow}`}>
          <Button type="button" variant="ghost" onClick={() => void runBulkDeployPlan()} disabled={!canRunSiteActions || siteActionPending}>
            {bulkLoading ? 'Planning…' : 'Plan bulk snippet deployment'}
          </Button>
          <Button type="button" variant="ghost" onClick={() => void runCloudflarePlan()} disabled={!canRunSiteActions || siteActionPending}>
            {cloudflareLoading ? 'Checking eligibility…' : 'Plan Cloudflare allowlist'}
          </Button>
        </div>
        <p className={styles.fieldHint}>Both plan actions are dry runs only; they do not install snippets or change Cloudflare rules.</p>
      </Card>

      {sitesStatus === 'loading' ? <p role="status" className={styles.loading}>Loading registered sites…</p> : null}
      {sitesStatus === 'error' ? (
        <p role="alert" className={styles.error}>
          {sitesError} <Button type="button" variant="ghost" onClick={() => void refreshSites()} disabled={!hasWorkspace}>Retry site list</Button>
        </p>
      ) : null}
      {sitesStatus === 'ready' && sites?.length === 0 ? (
        <p role="status" className={styles.empty}>No sites are registered in this workspace yet. Add the website below to start collecting crawler events.</p>
      ) : null}

      {dashboardError ? <p role="alert" className={styles.error}>{dashboardError}</p> : null}
      {readinessError ? <p role="status" className={styles.partial}>Workspace setup coverage could not be loaded: {readinessError}</p> : null}
      {dashboardLoading ? <p role="status" className={styles.loading}>Loading crawler telemetry and workspace readiness…</p> : null}

      {readiness ? (
        <Card>
          <div className={styles.siteHeader}>
            <CardTitle sub="Workspace-wide setup coverage; calculated from site fields and server configuration presence, not a live connectivity test.">
              Configuration coverage
            </CardTitle>
            {readiness.totalSites > 0 ? <Badge tone="neutral">Heuristic grade {readiness.grade}</Badge> : <Badge tone="neutral">No registered sites</Badge>}
          </div>
          <StatGrid>
            <Stat label="Setup score" value={readiness.totalSites > 0 ? `${formatDecimal(readiness.score)}%` : '—'} hint="Backend heuristic, not a certification." />
            <Stat label="Snippet installed" value={readiness.totalSites > 0 ? `${formatDecimal(readiness.coverage.snippetInstalledPct)}%` : '—'} />
            <Stat label="SSR enabled" value={readiness.totalSites > 0 ? `${formatDecimal(readiness.coverage.ssrEnabledPct)}%` : '—'} />
            <Stat label="Cloudflare zone configured" value={readiness.totalSites > 0 ? `${formatDecimal(readiness.coverage.cloudflareZoneConfiguredPct)}%` : '—'} />
            <Stat label="Deployment webhook configured" value={readiness.totalSites > 0 ? `${formatDecimal(readiness.coverage.deploymentWebhookConfiguredPct)}%` : '—'} />
          </StatGrid>
        </Card>
      ) : null}

      {dashboard ? (
        <section className={styles.sectionStack} aria-label={`Crawler telemetry for ${dashboardScope}`}>
          <Card>
            <div className={styles.siteHeader}>
              <CardTitle sub={`${dashboardScope} · previous ${dashboard.windowHours} hours`}>
                Recorded crawler activity
              </CardTitle>
              <Badge tone="neutral">Service event window</Badge>
            </div>
            <StatGrid>
              <Stat label="Total crawler requests" value={formatCount(dashboard.summary.totalHits)} hint="Recorded in the selected window." />
              <Stat label="AI crawler requests" value={formatCount(dashboard.summary.aiCrawlerHits)} />
              <Stat label="SSR-served requests" value={formatCount(dashboard.summary.ssrServedHits)} />
              <Stat label="Blocked requests" value={formatCount(dashboard.summary.blockedHits)} />
              <Stat label="AI crawl SSR/cache coverage" value={dashboard.summary.aiCrawlerHits > 0 ? `${formatDecimal(dashboard.summary.visibilityScore)}%` : '—'} hint={dashboard.summary.aiCrawlerHits > 0 ? 'Share of observed AI crawler requests served via SSR or cache.' : 'No AI crawler requests in this window.'} />
              <Stat label="Average reported render time" value={dashboard.summary.totalHits > 0 ? `${formatDecimal(dashboard.summary.averageRenderTimeMs)} ms` : '—'} hint={dashboard.summary.totalHits > 0 ? 'Aggregated by the crawler service.' : 'No crawler requests in this window.'} />
            </StatGrid>
            {dashboard.summary.totalHits === 0 ? (
              <p className={`${styles.empty} ${styles.zeroWindowNotice}`}>No crawler events were recorded for {dashboardScope} in the previous {dashboard.windowHours} hours. Counts are zero for this returned event window; they are not missing data.</p>
            ) : null}
          </Card>

          <div className={styles.siteFormGrid}>
            <Card>
              <CardTitle sub="Top user-agent names observed in the selected event window.">Top crawlers</CardTitle>
              {dashboard.topCrawlers.length ? (
                <ul className={styles.siteList}>
                  {dashboard.topCrawlers.map((crawler) => (
                    <li key={crawler.name} className={styles.siteItem}>
                      <span className={styles.planDomain}>{crawler.name}</span>
                      <Badge tone="neutral">{formatCount(crawler.hits)} requests</Badge>
                    </li>
                  ))}
                </ul>
              ) : <p className={styles.empty}>No crawler names were recorded in this window.</p>}
            </Card>
            <Card>
              <CardTitle sub="URLs with the most recorded crawler requests.">Top pages</CardTitle>
              {dashboard.topPages.length ? (
                <ul className={styles.siteList}>
                  {dashboard.topPages.map((page) => (
                    <li key={page.url} className={styles.siteItem}>
                      <span className={styles.planDomain}>{page.url}</span>
                      <Badge tone="neutral">{formatCount(page.hits)} requests</Badge>
                    </li>
                  ))}
                </ul>
              ) : <p className={styles.empty}>No page URLs were recorded in this window.</p>}
            </Card>
          </div>
        </section>
      ) : null}

      {sitesStatus === 'ready' && sites?.length ? (
        <Card>
          <div className={styles.siteHeader}>
            <CardTitle sub="Installation and rendering settings for registered sites. IDs are kept internal to workspace-scoped actions.">
              Registered sites
            </CardTitle>
            <Badge tone="neutral">{formatCount(sites.length)} sites</Badge>
          </div>
          <TableWrap>
            <table className={tableClass}>
              <caption className="sr-only">Registered websites, snippet status, SSR status, crawler events, and install-snippet action</caption>
              <thead>
                <tr>
                  <th scope="col">Website</th>
                  <th scope="col">Snippet</th>
                  <th scope="col">SSR</th>
                  <th scope="col">AI crawler hits (all-time)</th>
                  <th scope="col">Install help</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((site) => (
                  <tr key={site.id}>
                    <td>{site.displayName || site.domain}<br /><span className={styles.siteMeta}>{site.domain}</span></td>
                    <td><Badge tone={site.snippetInstalled ? 'success' : 'neutral'}>{site.snippetInstalled ? 'Installed' : 'Not verified'}</Badge></td>
                    <td><Badge tone={site.ssrEnabled ? 'success' : 'neutral'}>{site.ssrEnabled ? 'Enabled' : 'Disabled'}</Badge></td>
                    <td>{formatCount(site.aiCrawlerHits)}</td>
                    <td>
                      <Button type="button" variant="ghost" onClick={() => void loadSiteSnippet(site)} disabled={snippetLoadingId === site.id}>
                        {snippetLoadingId === site.id ? 'Loading…' : `View snippet for ${site.domain}`}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Card>
      ) : null}

      {bulkError ? <p role="alert" className={styles.error}>{bulkError}</p> : null}
      {bulkPlan ? (
        <Card>
          <div className={styles.planHeader}>
            <CardTitle sub="Dry run only. No snippet was deployed or webhook called.">Bulk snippet deployment plan</CardTitle>
            <Badge tone="neutral">Dry run</Badge>
          </div>
          <StatGrid>
            <Stat label="Sites targeted" value={formatCount(bulkPlan.summary.sitesTargeted)} />
            <Stat label="Planned" value={formatCount(bulkPlan.summary.planned)} />
          </StatGrid>
          {bulkPlan.deployments.length ? (
            <ul className={styles.planList}>
              {bulkPlan.deployments.map((deployment) => (
                <li className={styles.planItem} key={`${deployment.domain}-${deployment.mode}`}>
                  <span><span className={styles.planDomain}>{deployment.domain}</span><span className={styles.planMeta}>{deployment.webhookConfigured ? 'A deployment webhook is configured.' : 'Manual installation will be needed.'}</span></span>
                  <Badge tone="neutral">Planned · {deployment.mode}</Badge>
                </li>
              ))}
            </ul>
          ) : <p className={styles.empty}>No sites were included in this plan.</p>}
        </Card>
      ) : null}

      {cloudflareError ? <p role="alert" className={styles.error}>{cloudflareError}</p> : null}
      {cloudflarePlan ? (
        <Card>
          <div className={styles.planHeader}>
            <CardTitle sub="Dry run only. No Cloudflare rule was changed. Eligibility requires a site zone and server token configuration.">Cloudflare allowlist plan</CardTitle>
            <Badge tone="neutral">Dry run · {cloudflarePlan.action}</Badge>
          </div>
          <StatGrid><Stat label="Sites checked" value={formatCount(cloudflarePlan.sitesTargeted)} /></StatGrid>
          {cloudflarePlan.results.length ? (
            <ul className={styles.planList}>
              {cloudflarePlan.results.map((result) => (
                <li className={styles.planItem} key={result.domain}>
                  <span className={styles.planDomain}>{result.domain}</span>
                  <Badge tone={result.eligible ? 'success' : 'neutral'}>{result.eligible ? 'Eligible for a later sync' : 'Not eligible yet'}</Badge>
                </li>
              ))}
            </ul>
          ) : <p className={styles.empty}>No sites were included in this plan.</p>}
        </Card>
      ) : null}

      {snippetError ? <p role="alert" className={styles.error}>{snippetError}</p> : null}
      {activeSnippet ? (
        <Card>
          <div className={styles.snippetHeader}>
            <div><CardTitle sub={`Add this code to the ${activeSnippet.domain} site template. It is displayed as text and will not execute in this dashboard.`}>Install snippet</CardTitle></div>
            <Button type="button" variant="ghost" onClick={() => void copySnippet()}>Copy snippet</Button>
          </div>
          <pre className={styles.snippetCode}>{activeSnippet.snippet}</pre>
          {snippetCopyStatus ? <p role="status" className={styles.fieldHint}>{snippetCopyStatus}</p> : null}
        </Card>
      ) : null}

      <Card>
        <div className={styles.siteHeader}>
          <CardTitle sub="Register a root domain to scope crawler events, inspect install status, and preview setup plans.">
            Add a website
          </CardTitle>
        </div>
        {registerError ? <p role="alert" className={styles.error}>{registerError}</p> : null}
        {registerSuccess ? <p role="status" className={styles.success}>{registerSuccess}</p> : null}
        <form className={styles.siteForm} onSubmit={(event) => void registerSite(event)} aria-busy={registering}>
          <div className={styles.siteFormGrid}>
            <div>
              <Field
                id="crawler-site-domain"
                label="Root domain"
                value={domainInput}
                onChange={(event) => setDomainInput(event.target.value)}
                placeholder="Enter your root domain"
                maxLength={253}
                required
                disabled={registering}
                autoComplete="off"
                inputMode="url"
              />
              <p className={styles.fieldHint}>A scheme or path is stripped; ports and credentials are not accepted.</p>
            </div>
            <Field
              id="crawler-site-name"
              label="Display name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              maxLength={120}
              required
              disabled={registering}
              autoComplete="organization"
            />
            <FieldSelect id="crawler-site-cms" label="Platform or CMS" value={cmsType} onChange={(event) => setCmsType(event.target.value)} required disabled={registering}>
              <option value="" disabled>Choose a platform</option>
              {CMS_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </FieldSelect>
            <FieldSelect id="crawler-site-framework" label="JavaScript framework" value={jsFramework} onChange={(event) => setJsFramework(event.target.value)} required disabled={registering}>
              <option value="" disabled>Choose a framework</option>
              {JS_FRAMEWORKS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </FieldSelect>
          </div>
          <div className={styles.formActions}>
            <Button type="submit" variant="primary" disabled={!hasWorkspace || registering}>
              {registering ? 'Registering…' : 'Register site'}
            </Button>
            <p className={styles.fieldHint}>Registration does not install a snippet or change firewall rules.</p>
          </div>
        </form>
      </Card>
    </Page>
  );
}
