import { NextRequest, NextResponse } from 'next/server';
import { getFallbackModulesResponse } from '@/app/(dashboard)/seo/module-registry-fallback';
import { SESSION_COOKIE_NAME } from '@/app/lib/auth/session-cookie';

const ALLOWED_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);
const FORCE_FALLBACK_TRUTHY = new Set(['1', 'true', 'yes', 'on', 'all', '*']);

function normalizeRouteToken(value: string): string {
  return value.trim().toLowerCase().replace(/^\/+/, '').replace(/\/+$/, '');
}

function routePatternMatches(pathKey: string, pattern: string): boolean {
  if (!pattern) return false;
  if (pattern === '*' || pattern === 'all') return true;
  if (pattern.endsWith('*')) {
    return pathKey.startsWith(pattern.slice(0, -1));
  }
  return pathKey === pattern;
}

function routeRuleMatches(method: string, pathKey: string, rule: string): boolean {
  const normalizedRule = normalizeRouteToken(rule);
  if (!normalizedRule) return false;

  const firstSpace = normalizedRule.indexOf(' ');
  if (firstSpace > 0) {
    const ruleMethod = normalizedRule.slice(0, firstSpace).toUpperCase();
    const rulePath = normalizeRouteToken(normalizedRule.slice(firstSpace + 1));
    return method === ruleMethod && routePatternMatches(pathKey, rulePath);
  }

  return routePatternMatches(pathKey, normalizedRule);
}

function isFallbackForced(method: string, path: string[]): boolean {
  const globalToggle = (process.env.NUXTRON_PROXY_FORCE_FALLBACK || process.env.FASTAPI_FORCE_FALLBACK || '')
    .trim()
    .toLowerCase();
  if (FORCE_FALLBACK_TRUTHY.has(globalToggle)) return true;

  const routeRules = (process.env.NUXTRON_PROXY_FORCE_FALLBACK_ROUTES || '')
    .split(',')
    .map((rule) => rule.trim())
    .filter(Boolean);
  if (!routeRules.length) return false;

  const pathKey = path.join('/').toLowerCase();
  return routeRules.some((rule) => routeRuleMatches(method, pathKey, rule));
}

function isProductionRuntime(): boolean {
  return (process.env.NODE_ENV || '').trim().toLowerCase() === 'production';
}

function getUpstreamBaseUrls(): string[] {
  const envCandidates = [
    process.env.FASTAPI_URL || '',
    process.env.NEXT_PUBLIC_FASTAPI_URL || '',
    process.env.LOCAL_FASTAPI_URL || '',
  ]
    .map((value) => value.trim().replace(/\/$/, ''))
    .filter(Boolean);

  if (isProductionRuntime()) {
    return Array.from(new Set(envCandidates));
  }

  const localhostFallbacks = [
    'http://127.0.0.1:8001',
    'http://localhost:8001',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ]
    .map((value) => value.trim().replace(/\/$/, ''))
    .filter(Boolean);

  return Array.from(new Set([...envCandidates, ...localhostFallbacks]));
}

function getServiceApiKey(): string {
  // Server-only secret. Deliberately does not fall back to a NEXT_PUBLIC_*
  // variant — that would ship the backend service key inside the client JS
  // bundle (A02: Cryptographic/Secrets Failure).
  return (process.env.FASTAPI_API_KEY || '').trim();
}

function getTenantId(request: NextRequest): string {
  const headerTenant = request.headers.get('x-tenant-id')?.trim() || '';
  const queryTenant = request.nextUrl.searchParams.get('tenant_id')?.trim() || '';
  const fallback = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || '').trim();
  return headerTenant || queryTenant || fallback;
}

function getUpstreamTimeoutMs(path: string[]): number {
  // NOSONAR - simple route timeout policy map for proxy behavior.
  const joined = path.join('/');
  // AI inference routes can take significantly longer than CRUD endpoints.
  if (
    joined.startsWith('ira/agent/brain/reason') ||
    joined.startsWith('ai/gateway/generate') ||
    joined.startsWith('vse/')
  ) {
    return 45_000;
  }
  if (joined === 'seo-platform/performance/audit') {
    return 120_000;
  }
  return 12_000;
}

function cookieAuthorization(request: NextRequest): string | null {
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value?.trim();
  return token ? `Bearer ${token}` : null;
}

function buildUpstreamHeaders(request: NextRequest, serviceApiKey: string, tenantId: string): Headers {
  const contentType = request.headers.get('content-type') || undefined;
  const requestId = request.headers.get('x-request-id');
  // EventSource (used for SSE job streams) cannot set custom headers, so
  // those requests arrive with no Authorization header — fall back to the
  // httpOnly session cookie, which the browser attaches automatically on
  // same-origin requests including EventSource.
  const authorization = request.headers.get('authorization') || cookieAuthorization(request);

  const upstreamHeaders = new Headers();
  upstreamHeaders.set('X-API-Key', serviceApiKey);
  upstreamHeaders.set('X-Tenant-Id', tenantId);
  if (requestId) upstreamHeaders.set('X-Request-ID', requestId);
  if (contentType) upstreamHeaders.set('Content-Type', contentType);
  // Forward the caller's session token so the backend can authenticate the
  // actual user, not just the shared service key + a client-supplied tenant
  // id (A01: Broken Access Control — a valid X-Tenant-Id alone must not be
  // sufficient to act as that tenant).
  if (authorization) upstreamHeaders.set('Authorization', authorization);

  return upstreamHeaders;
}

function buildUpstreamUrl(
  base: string,
  pathname: string,
  query: string,
  isStreamRequest: boolean,
  serviceApiKey: string
): string {
  const baseUrl = query ? `${base}/${pathname}?${query}` : `${base}/${pathname}`;
  if (!isStreamRequest || !serviceApiKey) return baseUrl;

  const url = new URL(baseUrl);
  if (!url.searchParams.get('api_key')) {
    url.searchParams.set('api_key', serviceApiKey);
  }
  return url.toString();
}

async function fetchUpstreamWithFallback({
  upstreamBases,
  pathname,
  query,
  isStreamRequest,
  serviceApiKey,
  init,
  timeoutMs,
}: {
  upstreamBases: string[];
  pathname: string;
  query: string;
  isStreamRequest: boolean;
  serviceApiKey: string;
  init: RequestInit;
  timeoutMs: number;
}): Promise<{ upstreamRes: Response | null; lastError: unknown }> {
  let upstreamRes: Response | null = null;
  let lastError: unknown = null;

  for (const base of upstreamBases) {
    const upstreamUrl = buildUpstreamUrl(base, pathname, query, isStreamRequest, serviceApiKey);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      upstreamRes = await fetch(upstreamUrl, { ...init, signal: controller.signal });
      clearTimeout(timeoutId);
      break;
    } catch (error) {
      lastError = error;
    }
  }

  return { upstreamRes, lastError };
}

function parseJsonBody(body: string | undefined): Record<string, unknown> {
  if (!body) return {};
  try {
    const parsed = JSON.parse(body) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Ignore malformed body and continue with empty fallback inputs.
  }
  return {};
}

function isTruthyEnv(value: string | undefined): boolean {
  const normalized = (value || '').trim().toLowerCase();
  if (!normalized) return false;
  return !['0', 'false', 'no', 'off'].includes(normalized);
}

function isPerformanceAuditLiveOnlyRequest(method: string, path: string[], requestBody: string | undefined): boolean {
  if (method !== 'POST' || path.join('/') !== 'seo-platform/performance/audit') {
    return false;
  }

  if (isTruthyEnv(process.env.NEXT_PUBLIC_STRICT_NO_MOCK) || isTruthyEnv(process.env.SEO_STRICT_NO_MOCK)) {
    return true;
  }

  const body = parseJsonBody(requestBody);
  return body.require_live_providers === true;
}

async function maybeBuildLiveOnlyPerformanceGuardResponse(
  method: string,
  path: string[],
  requestBody: string | undefined,
  upstreamRes: Response
): Promise<NextResponse | null> {
  if (!isPerformanceAuditLiveOnlyRequest(method, path, requestBody)) {
    return null;
  }
  if (upstreamRes.status < 200 || upstreamRes.status >= 300) {
    return null;
  }

  const contentType = (upstreamRes.headers.get('content-type') || '').toLowerCase();
  if (!contentType.includes('application/json')) {
    return NextResponse.json(
      { detail: 'Live-only mode requires provider-backed JSON audit output.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  try {
    const payload = await upstreamRes.clone().json();
    const provenance = payload?.data_provenance;
    const source = typeof provenance?.source === 'string' ? provenance.source.trim().toLowerCase() : '';
    const providerStatus = payload?.free_provider_status;
    const providerValues = providerStatus && typeof providerStatus === 'object' ? Object.values(providerStatus) : [];
    const hasLiveProviderData = providerValues.some(Boolean);

    if (source === 'ai_only' || !hasLiveProviderData) {
      return NextResponse.json(
        { detail: 'Live performance providers returned no usable data; refusing ai_only output in live-only mode.' },
        { status: 503, headers: { 'Cache-Control': 'no-store' } }
      );
    }
  } catch {
    return NextResponse.json(
      { detail: 'Live-only mode requires valid JSON performance audit output.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  return null;
}

type FallbackContext = {
  method: string;
  path: string[];
  pathKey: string;
  tenantId: string;
  requestBody: string | undefined;
  detail: string;
  fallbackKind: 'offline' | 'forced';
  cacheHeaders: { 'Cache-Control': string };
};

type FallbackHandler = (context: FallbackContext) => NextResponse | null;

function notificationsSnapshotFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'notifications') {
    return null;
  }

  return NextResponse.json(
    {
      notifications: [],
      unreadCount: 0,
      unreadTotal: 0,
      total: 0,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function notificationsStreamFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'notifications/stream') {
    return null;
  }

  return new NextResponse(
    'event: notifications.snapshot\n' + 'data: {"notifications":[],"unreadCount":0,"unreadTotal":0,"total":0}\n\n',
    {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-store, no-transform',
        Connection: 'keep-alive',
      },
    }
  );
}

function modulesFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'seo-platform/modules') {
    return null;
  }

  return NextResponse.json(getFallbackModulesResponse(), { status: 200, headers: context.cacheHeaders });
}

function healthFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'seo-platform/health') {
    return null;
  }

  return NextResponse.json(
    {
      status: 'degraded',
      service: 'seo-platform',
      modules: getFallbackModulesResponse().total,
      ai_backend: 'offline-fallback',
      persistence: 'memory',
      ollama_connected: false,
      model: 'fallback',
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function adsControlTowerHealthFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'ads-control-tower/health') {
    return null;
  }

  return NextResponse.json(
    {
      status: 'ok',
      connectors_total: 5,
      connectors_connected: 0,
      campaigns_total: 0,
      campaigns_overdue_sync: 0,
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function adsControlTowerNotificationsFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'ads-control-tower/notifications') {
    return null;
  }

  return NextResponse.json(
    {
      status: 'ok',
      total: 1,
      notifications: [
        {
          id: 1,
          tenant_id: context.tenantId,
          title: 'Offline fallback active',
          message: 'FastAPI is unreachable right now. Showing a local control-tower fallback snapshot.',
          category: 'system',
          priority: 'warning',
          is_read: false,
          source: 'ads-control-tower-fallback',
          created_at: new Date().toISOString(),
        },
      ],
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function buildAdsFallbackCampaign(id: string, platform = 'google_ads', overrides?: Record<string, unknown>) {
  return {
    id,
    tenant_id: 'tenant-demo',
    platform,
    campaign_name: 'Fallback Campaign',
    objective: 'conversions',
    status: 'draft',
    budget_daily: 0,
    budget_total: 0,
    currency: 'USD',
    keywords: [],
    creative: {
      title: 'Fallback creative',
      description: 'Offline fallback response',
      cta: 'Learn More',
      media_urls: [],
    },
    schedule: { timezone: 'UTC', start_at: null, end_at: null, auto_post: false, posting_dates: [] },
    connected_accounts: [],
    metrics: {
      likes: 0,
      description_views: 0,
      shares: 0,
      comments: 0,
      clicks: 0,
      impressions: 0,
      conversions: 0,
      spend: 0,
      revenue: 0,
      roi_pct: 0,
      success_ratio_pct: 0,
      updated_at: new Date().toISOString(),
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

// eslint-disable-next-line sonarjs/cognitive-complexity
function adsControlTowerGenericFallback(context: FallbackContext): NextResponse | null {
  const [root, a, b, c] = context.path;
  if (root !== 'ads-control-tower') return null;

  const body = parseJsonBody(context.requestBody);
  const json = (payload: unknown) =>
    NextResponse.json(
      { ...(payload as Record<string, unknown>), fallback: true, detail: context.detail },
      { status: 200, headers: context.cacheHeaders }
    );

  if (context.method === 'GET' && a === 'connectors') return json({ status: 'ok', connectors: [] });
  if (context.method === 'POST' && a === 'connectors' && b && c === 'oauth' && context.path[4] === 'start') {
    return json({
      platform: b,
      state: `fallback-${Date.now()}`,
      authorization_url: '#offline-fallback',
      callback_path: `/ads-control-tower/connectors/${b}/oauth/callback`,
    });
  }
  if (context.method === 'POST' && a === 'connectors' && b && c === 'oauth' && context.path[4] === 'callback') {
    return json({
      status: 'ok',
      connector: {
        id: `connector-${b}`,
        tenant_id: context.tenantId,
        platform: b,
        status: 'connected',
        connected: true,
        account_name: 'Fallback Account',
        account_id: 'fallback-account',
        scopes: [],
        token_fingerprint: null,
        refresh_token_present: false,
        credit_currency: 'USD',
        credit_total: 0,
        credit_remaining: 0,
        last_sync_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
  }
  if (context.method === 'DELETE' && a === 'connectors' && b) {
    return json({
      status: 'ok',
      connector: {
        id: `connector-${b}`,
        tenant_id: context.tenantId,
        platform: b,
        status: 'disconnected',
        connected: false,
        account_name: '',
        account_id: '',
        scopes: [],
        token_fingerprint: null,
        refresh_token_present: false,
        credit_currency: 'USD',
        credit_total: 0,
        credit_remaining: 0,
        last_sync_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
  }

  if (context.method === 'GET' && a === 'credits') {
    return json({ status: 'ok', accounts: [], portfolio_credit_total: 0, portfolio_credit_remaining: 0 });
  }

  if (context.method === 'GET' && a === 'campaigns' && !b) {
    return json({ status: 'ok', total: 0, campaigns: [] });
  }
  if (context.method === 'POST' && a === 'campaigns' && !b) {
    const platform = typeof body.platform === 'string' ? body.platform : 'google_ads';
    const name = typeof body.campaign_name === 'string' ? body.campaign_name : 'Fallback Campaign';
    return json({
      status: 'ok',
      campaign: buildAdsFallbackCampaign(`camp-${Date.now()}`, platform, { campaign_name: name }),
    });
  }
  if (context.method === 'GET' && a === 'campaigns' && b) {
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(b) });
  }
  if (context.method === 'PATCH' && a === 'campaigns' && b) {
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(b, 'google_ads', body) });
  }
  if (context.method === 'DELETE' && a === 'campaigns' && b) {
    return json({ status: 'ok', deleted: b });
  }
  if (context.method === 'POST' && a === 'campaigns' && b && c === 'publish') {
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(b, 'google_ads', { status: 'active' }) });
  }
  if (context.method === 'POST' && a === 'campaigns' && b && c === 'metrics') {
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(b) });
  }
  if (context.method === 'POST' && a === 'campaigns' && b && c === 'request-approval') {
    return json({
      status: 'ok',
      campaign: buildAdsFallbackCampaign(b, 'google_ads', { approval_status: 'pending_approval' }),
    });
  }
  if (context.method === 'POST' && a === 'campaigns' && b && c === 'approve') {
    const decision = typeof body.decision === 'string' ? body.decision : 'approved';
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(b, 'google_ads', { approval_status: decision }) });
  }
  if (context.method === 'POST' && a === 'campaigns' && b && c === 'duplicate') {
    const newName = typeof body.new_name === 'string' ? body.new_name : 'Fallback Duplicate';
    return json({
      status: 'ok',
      campaign: buildAdsFallbackCampaign(`camp-${Date.now()}`, 'google_ads', { campaign_name: newName }),
    });
  }

  if (context.method === 'GET' && a === 'calendar') {
    return json({ status: 'ok', events: [] });
  }
  if (context.method === 'POST' && a === 'calendar' && b === 'drag-reschedule') {
    const campaignId = typeof body.campaign_id === 'string' ? body.campaign_id : 'camp-fallback';
    return json({ status: 'ok', campaign: buildAdsFallbackCampaign(campaignId) });
  }

  if (context.method === 'POST' && a === 'assets' && b === 'auto-resize') {
    return json({ status: 'ok', variants: [] });
  }

  if (context.method === 'GET' && a === 'kpis') {
    return json({
      status: 'ok',
      summary: {
        campaigns_total: 0,
        campaigns_active: 0,
        budget_daily: 0,
        budget_total: 0,
        spend: 0,
        revenue: 0,
        roi_pct: 0,
        success_ratio_pct: 0,
        ctr_pct: 0,
        cpc: 0,
        cpa: 0,
      },
      engagement: { likes: 0, shares: 0, comments: 0, clicks: 0, impressions: 0, conversions: 0 },
    });
  }
  if (context.method === 'GET' && a === 'forecast') {
    const daysRaw = Number.parseInt(new URLSearchParams(context.pathKey.split('?')[1] || '').get('days') || '30', 10);
    return json({
      status: 'ok',
      horizon_days: Number.isFinite(daysRaw) ? daysRaw : 30,
      projected_spend: 0,
      projected_clicks: 0,
      projected_conversions: 0,
      projected_roi_pct: 0,
    });
  }
  if (context.method === 'GET' && a === 'best-time') {
    return json({
      status: 'ok',
      platform: 'google_ads',
      objective: 'conversions',
      best_days: ['Tuesday', 'Wednesday'],
      heatmap: {},
      peak_hour: 14,
      avoid_hours: [2, 3, 4],
      human_review_window: [9, 18],
      rationale: 'Fallback recommendation while backend is unavailable.',
      all_platforms_peak: { google_ads: 14, youtube_ads: 19 },
    });
  }
  if (context.method === 'GET' && a === 'ab-test' && c === 'suggestions') {
    return json({
      status: 'ok',
      campaign_id: b || 'camp-fallback',
      original: { title: 'Fallback title', description: 'Fallback description', cta: 'Learn More' },
      suggestions: [
        {
          variant: 'A',
          label: 'Value-driven',
          title: 'Scale with confidence',
          description: 'A fallback creative suggestion generated locally.',
          cta: 'Get started',
          predicted_ctr_lift_pct: 4.2,
          rationale: 'Short, benefit-first headline tends to improve CTR in cold audiences.',
        },
      ],
    });
  }
  if (context.method === 'GET' && a === 'audience-insights') {
    return json({
      status: 'ok',
      platforms_active: [],
      keywords_indexed: 0,
      audience_overlap_pct: 0,
      keyword_saturation_score: 0,
      estimated_reach: 0,
      recommendations: ['Backend unavailable; using cached strategy assumptions.'],
      top_keywords: [],
      frequency_cap_suggestion: 3,
    });
  }

  return null;
}

function socialWorkflowGenericFallback(context: FallbackContext): NextResponse | null {
  const [root, a, b, c] = context.path;
  const body = parseJsonBody(context.requestBody);
  const json = (payload: unknown) =>
    NextResponse.json(
      { ...(payload as Record<string, unknown>), fallback: true, detail: context.detail },
      { status: 200, headers: context.cacheHeaders }
    );

  if (root === 'social') {
    if (context.method === 'GET' && a === 'accounts' && b === 'catalog') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        providers: [
          { network: 'instagram', label: 'Instagram', supported_formats: ['image', 'video', 'reel'] },
          { network: 'tiktok', label: 'TikTok', supported_formats: ['video'] },
          { network: 'youtube', label: 'YouTube', supported_formats: ['video', 'short'] },
          { network: 'x', label: 'X', supported_formats: ['text', 'image'] },
          { network: 'linkedin', label: 'LinkedIn', supported_formats: ['text', 'image', 'video'] },
        ],
      });
    }

    if (context.method === 'POST' && a === 'accounts' && b === 'connect') {
      const network = typeof body.network === 'string' ? body.network : 'instagram';
      const handle = typeof body.handle === 'string' ? body.handle : 'nuxtron_official';
      const accountName = typeof body.account_name === 'string' ? body.account_name : 'Nuxtron Social Account';
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        connected: true,
        account: {
          id: Date.now(),
          tenant_id: context.tenantId,
          network,
          account_name: accountName,
          handle,
          status: 'connected',
        },
      });
    }

    if (context.method === 'GET' && a === 'accounts' && !b) {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        count: 1,
        connected_networks: ['instagram'],
        accounts: [
          {
            id: 1,
            tenant_id: context.tenantId,
            network: 'instagram',
            account_name: 'Nuxtron Social',
            handle: 'nuxtron_official',
            account_type: 'business',
            likes: 420,
            shares: 38,
            comments: 64,
          },
        ],
      });
    }

    if (context.method === 'POST' && a === 'oauth' && b === 'connect-all') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        connected_count: 5,
        already_connected_count: 0,
        connected_accounts: ['instagram', 'tiktok', 'youtube', 'x', 'linkedin'].map((network, index) => ({
          id: index + 1,
          tenant_id: context.tenantId,
          network,
          account_name: `Nuxtron ${network}`,
          handle: `nuxtron_${network}`,
        })),
        already_connected_networks: [],
      });
    }

    if (context.method === 'POST' && a === 'autopilot' && (b === 'preview' || b === 'publish')) {
      const headline = typeof body.headline === 'string' ? body.headline : 'Fallback autonomous social post';
      const caption =
        typeof body.caption === 'string' ? body.caption : 'AI manager generated this content in offline fallback mode.';
      return json({
        status: 'ok',
        mode: b,
        post: {
          id: Date.now(),
          headline,
          caption,
          publish_mode: typeof body.publish_mode === 'string' ? body.publish_mode : 'auto',
          publish_at: typeof body.publish_at === 'string' ? body.publish_at : new Date().toISOString(),
        },
      });
    }

    if (context.method === 'GET' && a === 'workspace' && b === 'overview') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        overview: {
          connected_accounts: 3,
          networks_connected: 3,
          inbox_open: 6,
          notifications_unread: 4,
          competitors_tracked: 5,
          competitor_snapshots: 12,
          scheduled_posts: 8,
          engagement_total: 1640,
        },
      });
    }

    if (context.method === 'POST' && a === 'schedule') {
      const platform = typeof body.platform === 'string' ? body.platform : 'linkedin';
      const text = typeof body.text === 'string' ? body.text : 'Fallback scheduled post';
      const publishAt =
        typeof body.publish_at === 'string' ? body.publish_at : new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
      return json({
        status: 'ok',
        job: {
          id: Date.now(),
          tenant_id: context.tenantId,
          platform,
          text,
          publish_at: publishAt,
          media_urls: Array.isArray(body.media_urls) ? body.media_urls : [],
          status: 'scheduled',
          created_at: new Date().toISOString(),
        },
      });
    }

    if (context.method === 'GET' && a === 'scheduled' && !b) {
      const now = Date.now();
      return json({
        status: 'ok',
        count: 3,
        items: [0, 1, 2].map((index) => ({
          id: index + 1,
          tenant_id: context.tenantId,
          platform: index === 1 ? 'instagram' : index === 2 ? 'x' : 'linkedin',
          text: `Fallback scheduled post ${index + 1}`,
          publish_at: new Date(now + (index + 1) * 90 * 60 * 1000).toISOString(),
          media_urls: [],
          status: 'scheduled',
          created_at: new Date(now - (index + 1) * 30 * 60 * 1000).toISOString(),
        })),
      });
    }

    if (context.method === 'PATCH' && a === 'scheduled' && b && c === 'move') {
      return json({
        status: 'ok',
        job: {
          id: Number.parseInt(b, 10) || 1,
          tenant_id: context.tenantId,
          platform: 'linkedin',
          text: 'Fallback moved scheduled post',
          publish_at: typeof body.publish_at === 'string' ? body.publish_at : new Date().toISOString(),
          media_urls: [],
          status: 'scheduled',
          created_at: new Date().toISOString(),
        },
      });
    }

    if (context.method === 'GET' && a === 'listening' && b === 'summary') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        summary: {
          total_mentions: 47,
          sentiment: { positive: 24, neutral: 15, negative: 8 },
          platforms: { instagram: 18, linkedin: 11, x: 10, tiktok: 8 },
          top_queries: [
            { query: 'nuxtron ai manager', mentions: 14 },
            { query: 'social automation', mentions: 11 },
            { query: 'roi forecast', mentions: 7 },
          ],
          avg_engagement: 37.9,
          alerts_open: 2,
          crisis: { triggered: false, level: 'none', negative_ratio: 0.17, high_negative_mentions: 1 },
        },
      });
    }

    if (context.method === 'GET' && a === 'listening' && b === 'mentions') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        count: 3,
        mentions: [
          {
            id: 1,
            platform: 'instagram',
            author_handle: 'creator_hub',
            query: 'nuxtron ai manager',
            sentiment: 'positive',
            engagement_count: 65,
          },
          {
            id: 2,
            platform: 'linkedin',
            author_handle: 'growth_ops',
            query: 'social automation',
            sentiment: 'neutral',
            engagement_count: 34,
          },
          {
            id: 3,
            platform: 'x',
            author_handle: 'martech_news',
            query: 'roi forecast',
            sentiment: 'negative',
            engagement_count: 51,
          },
        ],
      });
    }

    if (context.method === 'GET' && a === 'listening' && b === 'clusters') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        count: 3,
        clusters: [
          { query: 'nuxtron ai manager', platform: 'instagram', sentiment: 'positive', mentions: 14 },
          { query: 'social automation', platform: 'linkedin', sentiment: 'neutral', mentions: 11 },
          { query: 'roi forecast', platform: 'x', sentiment: 'negative', mentions: 7 },
        ],
      });
    }

    if (context.method === 'POST' && a === 'inbox' && b === 'messages' && c && context.path[4] === 'engage') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        message: {
          id: Number.parseInt(c, 10) || 1,
          status: 'complete',
          action: 'reply',
          responded_at: new Date().toISOString(),
        },
      });
    }
  }

  if (root === 'content' && a === 'approval') {
    if (context.method === 'PUT' && b === 'config') {
      return json({ status: 'ok', tenant_id: context.tenantId, config: body });
    }
    if (context.method === 'GET' && b === 'requests') {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        count: 1,
        requests: [
          {
            id: 1,
            tenant_id: context.tenantId,
            scheduled_post_id: 1,
            platform: 'linkedin',
            content_preview: 'Fallback approval request preview',
            status: 'pending',
            approval_levels: ['manager', 'legal'],
            created_at: new Date().toISOString(),
          },
        ],
      });
    }
    if (context.method === 'POST' && b === 'requests' && !c) {
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        request: {
          id: Date.now(),
          scheduled_post_id: typeof body.scheduled_post_id === 'number' ? body.scheduled_post_id : 1,
          platform: typeof body.platform === 'string' ? body.platform : 'linkedin',
          content_preview: typeof body.content_preview === 'string' ? body.content_preview : 'Fallback preview',
          requested_by: typeof body.requested_by === 'string' ? body.requested_by : 'social-manager',
          status: 'pending',
        },
      });
    }
    if (context.method === 'POST' && b === 'requests' && c && context.path[4] === 'decision') {
      const decision = typeof body.decision === 'string' ? body.decision : 'approved';
      return json({
        status: 'ok',
        tenant_id: context.tenantId,
        request: {
          id: Number.parseInt(c, 10) || 1,
          status: decision,
          reviewer_role: typeof body.reviewer_role === 'string' ? body.reviewer_role : 'manager',
          updated_at: new Date().toISOString(),
        },
      });
    }
  }

  return null;
}

function analysesFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'seo-platform/analyses') {
    return null;
  }

  return NextResponse.json(
    {
      analyses: [],
      total: 0,
      persistence: 'memory',
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function gatewayStatusFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'ai/gateway/status') {
    return null;
  }

  return NextResponse.json(
    {
      status: 'degraded',
      cache: {
        metrics: { hit_ratio: 0, lookups: 0, errors: 0 },
        trend_5m: { avg_latency_ms: 0, error_rate: 1, requests: 0 },
      },
      observability: {
        sentry_enabled: false,
        otel_enabled: false,
      },
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function integrationsToolsFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'GET' || context.pathKey !== 'integrations/tools') {
    return null;
  }

  return NextResponse.json(
    {
      total: 0,
      configured: 0,
      tools: [],
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function strategySnapshotsFallback(context: FallbackContext): NextResponse | null {
  if (
    context.method !== 'GET' ||
    context.path.length < 4 ||
    context.path[0] !== 'v1' ||
    context.path[1] !== 'loop' ||
    context.path[2] !== 'strategy-snapshots'
  ) {
    return null;
  }

  return NextResponse.json(
    {
      site_id: context.path[3] || context.tenantId,
      total: 0,
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function richResultsFallback(context: FallbackContext): NextResponse | null {
  if (
    context.method !== 'GET' ||
    context.path.length < 4 ||
    context.path[0] !== 'v1' ||
    context.path[1] !== 'loop' ||
    context.path[2] !== 'rich-results'
  ) {
    return null;
  }

  return NextResponse.json(
    {
      site_id: context.path[3] || context.tenantId,
      opportunities: 0,
      total_impressions: 0,
      average_ctr: 0,
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

function llmoAnalyzeFallback(context: FallbackContext): NextResponse | null {
  if (context.method !== 'POST' || context.pathKey !== 'seo-platform/llmo/analyze') {
    return null;
  }

  const body = parseJsonBody(context.requestBody);
  const brand = typeof body.brand === 'string' && body.brand.trim().length > 0 ? body.brand.trim() : 'Your brand';

  return NextResponse.json(
    {
      analysis_id: `proxy-fallback-${Date.now()}`,
      brand_ai_score: 52,
      accuracy_risk: 'high',
      model_representations: {
        gpt_4: `${brand} is recognized, but positioning detail depends on citation depth and freshness.`,
        claude: `${brand} appears in category-level context with incomplete differentiator coverage.`,
        gemini: `${brand} is surfaced when claims are explicit and repeatedly corroborated by trusted sources.`,
      },
      knowledge_gap_topics: [
        'Founding and timeline clarity',
        'Proof-backed performance claims',
        'Comparison narrative versus top alternatives',
      ],
      correction_strategy: [
        'Publish a canonical brand facts page with verifiable claims and timestamps.',
        'Create structured FAQ content that mirrors likely assistant prompts.',
        'Add third-party corroboration links for high-value differentiators.',
      ],
      citation_building_plan: [
        'Expand entity-consistent schema on core pages (Organization, Product, FAQ).',
        'Build claim-level citations from authoritative sources and analyst writeups.',
        'Refresh stale pages monthly to improve retrieval recency signals.',
      ],
      fallback: true,
      detail: context.detail,
    },
    { status: 200, headers: context.cacheHeaders }
  );
}

const OFFLINE_FALLBACK_HANDLERS: FallbackHandler[] = [
  notificationsSnapshotFallback,
  notificationsStreamFallback,
  modulesFallback,
  healthFallback,
  adsControlTowerHealthFallback,
  adsControlTowerNotificationsFallback,
  adsControlTowerGenericFallback,
  socialWorkflowGenericFallback,
  analysesFallback,
  gatewayStatusFallback,
  integrationsToolsFallback,
  strategySnapshotsFallback,
  richResultsFallback,
  llmoAnalyzeFallback,
];

function buildOfflineFallbackResponse({
  method,
  path,
  tenantId,
  requestBody,
  detail,
  fallbackKind,
}: {
  method: string;
  path: string[];
  tenantId: string;
  requestBody: string | undefined;
  detail: string;
  fallbackKind: 'offline' | 'forced';
}): NextResponse | null {
  const context: FallbackContext = {
    method,
    path,
    pathKey: path.join('/'),
    tenantId,
    requestBody,
    detail,
    fallbackKind,
    cacheHeaders: { 'Cache-Control': 'no-store' },
  };

  for (const handler of OFFLINE_FALLBACK_HANDLERS) {
    const response = handler(context);
    if (response) {
      response.headers.set('X-Nuxtron-Fallback', fallbackKind);
      return response;
    }
  }

  return null;
}

// NOSONAR - proxy orchestration intentionally centralizes fallback and upstream flow.
async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const method = request.method.toUpperCase();
  if (!ALLOWED_METHODS.has(method)) {
    return NextResponse.json({ detail: 'Method not allowed.' }, { status: 405 });
  }

  const upstreamBases = getUpstreamBaseUrls();
  const serviceApiKey = getServiceApiKey();
  const tenantId = getTenantId(request);

  const configError = getProxyConfigError(upstreamBases, serviceApiKey, tenantId);
  if (configError) return configError;

  const isStreamRequest = path.at(-1) === 'stream';
  const upstreamTimeoutMs = getUpstreamTimeoutMs(path);
  const pathname = path.map(encodeURIComponent).join('/');
  const query = request.nextUrl.searchParams.toString();

  const bodySizeError = checkRequestBodySize(request);
  if (bodySizeError) return bodySizeError;
  const requestBody = method === 'GET' || method === 'DELETE' ? undefined : await request.text();

  const forcedFallbackResponse = maybeBuildForcedFallbackResponse(method, path, tenantId, requestBody);
  if (forcedFallbackResponse) return forcedFallbackResponse;

  const init: RequestInit = {
    method,
    headers: buildUpstreamHeaders(request, serviceApiKey, tenantId),
    cache: 'no-store',
    body: requestBody,
  };

  const { upstreamRes, lastError } = await fetchUpstreamWithFallback({
    upstreamBases,
    pathname,
    query,
    isStreamRequest,
    serviceApiKey,
    init,
    timeoutMs: upstreamTimeoutMs,
  });

  const failureDetail = lastError instanceof Error ? lastError.message : 'Unable to reach FastAPI upstream.';

  if (!upstreamRes) {
    return buildUnavailableUpstreamResponse(method, path, tenantId, requestBody, failureDetail);
  }

  const upstreamErrorFallback = maybeBuildUpstreamErrorFallback(
    method,
    path,
    tenantId,
    requestBody,
    upstreamRes.status
  );
  if (upstreamErrorFallback) return upstreamErrorFallback;

  const liveOnlyGuardResponse = await maybeBuildLiveOnlyPerformanceGuardResponse(
    method,
    path,
    requestBody,
    upstreamRes
  );
  if (liveOnlyGuardResponse) return liveOnlyGuardResponse;

  const responseHeaders = new Headers();
  const passthrough = ['content-type', 'cache-control', 'x-request-id', 'x-process-time'];
  for (const key of passthrough) {
    const value = upstreamRes.headers.get(key);
    if (value) responseHeaders.set(key, value);
  }
  responseHeaders.set('Cache-Control', 'no-store');

  return new NextResponse(upstreamRes.body, {
    status: upstreamRes.status,
    headers: responseHeaders,
  });
}

// Bounds how much of a request body this route buffers into memory
// (`await request.text()` below) before forwarding it upstream. Without a
// cap, a large concurrent burst of uploads (e.g. social-scheduling media)
// can exhaust the server's memory. Checked via Content-Length, which a
// well-behaved client always sends and the underlying HTTP server enforces
// for chunked bodies too — this is a resource-exhaustion guard, not a
// substitute for real virus/content scanning on uploads.
const DEFAULT_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024;

function resolveMaxRequestBodyBytes(): number {
  const parsed = Number(process.env.NUXTRON_MAX_REQUEST_BODY_BYTES);
  // A non-numeric override must not silently disable the cap (NaN compares
  // false against everything, which would do exactly that) — fall back to
  // the default instead of trusting an unparseable env value.
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_REQUEST_BODY_BYTES;
}

const MAX_REQUEST_BODY_BYTES = resolveMaxRequestBodyBytes();

function checkRequestBodySize(request: NextRequest): NextResponse | null {
  const contentLength = Number(request.headers.get('content-length') || 0);
  if (contentLength > MAX_REQUEST_BODY_BYTES) {
    return NextResponse.json(
      { detail: `Request body exceeds the ${MAX_REQUEST_BODY_BYTES}-byte limit.` },
      { status: 413, headers: { 'Cache-Control': 'no-store' } }
    );
  }
  return null;
}

function getProxyConfigError(upstreamBases: string[], serviceApiKey: string, tenantId: string): NextResponse | null {
  if (!upstreamBases.length) {
    return NextResponse.json({ detail: 'FASTAPI_URL is not configured.' }, { status: 500 });
  }

  if (!serviceApiKey) {
    return NextResponse.json({ detail: 'FASTAPI_API_KEY is not configured on the server.' }, { status: 500 });
  }

  if (!tenantId) {
    return NextResponse.json({ detail: 'Tenant id is required.' }, { status: 400 });
  }

  return null;
}

function maybeBuildForcedFallbackResponse(
  method: string,
  path: string[],
  tenantId: string,
  requestBody: string | undefined
): NextResponse | null {
  if (!isFallbackForced(method, path)) {
    return null;
  }

  const detail = 'Fallback mode forced by environment configuration.';
  return (
    buildOfflineFallbackResponse({
      method,
      path,
      tenantId,
      requestBody,
      detail,
      fallbackKind: 'forced',
    }) || NextResponse.json({ detail }, { status: 503, headers: { 'Cache-Control': 'no-store' } })
  );
}

/**
 * In production, automatic (non-forced) fallback is off by default: a
 * backend outage should surface as a real error that paging/monitoring can
 * see, not a silently fabricated 200. It stays on by default outside
 * production for local DX when the backend isn't running. Set
 * NUXTRON_AUTO_FALLBACK=true to explicitly opt a production deployment into
 * degraded-mode UX (e.g. for a route where showing stale/synthetic data
 * beats an error screen) — this is a deliberate per-deployment choice, not
 * the default.
 */
function isAutoFallbackAllowed(): boolean {
  if (!isProductionRuntime()) return true;
  return isTruthyEnv(process.env.NUXTRON_AUTO_FALLBACK);
}

function buildUnavailableUpstreamResponse(
  method: string,
  path: string[],
  tenantId: string,
  requestBody: string | undefined,
  detail: string
): NextResponse {
  if (!isAutoFallbackAllowed()) {
    return NextResponse.json({ detail }, { status: 502, headers: { 'Cache-Control': 'no-store' } });
  }
  return (
    buildOfflineFallbackResponse({
      method,
      path,
      tenantId,
      requestBody,
      detail,
      fallbackKind: 'offline',
    }) || NextResponse.json({ detail }, { status: 502 })
  );
}

function maybeBuildUpstreamErrorFallback(
  method: string,
  path: string[],
  tenantId: string,
  requestBody: string | undefined,
  upstreamStatus: number
): NextResponse | null {
  if (upstreamStatus < 500 || !isAutoFallbackAllowed()) {
    return null;
  }

  return buildOfflineFallbackResponse({
    method,
    path,
    tenantId,
    requestBody,
    detail: `Upstream responded ${upstreamStatus}.`,
    fallbackKind: 'offline',
  });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export const __test__ = {
  isFallbackForced,
  buildOfflineFallbackResponse,
  getUpstreamBaseUrls,
  isProductionRuntime,
};
