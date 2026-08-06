'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost } from '@/app/lib/api-client';
import PlatformDashboardContent from '@/app/components/platform-dashboard-content';
import { FINAL_HYBRID_SUMMARY, OPEN_SOURCE_HYBRID_STACKS } from './hybrid-stacks';

type AnyObject = Record<string, unknown>;

type StatusResponse = {
  status: string;
  db_ready: boolean;
  integrations: Record<string, boolean | string>;
  fallback_buffers?: {
    any_buffer_hot?: boolean;
    hot_buffers?: string[];
  };
};

type CoverageResponse = {
  coverage_percent: number;
  covered_count: number;
  total_use_cases: number;
};

type MetricsResponse = {
  queues: Record<string, number>;
  rate_limiter: { active_keys: number; sample_count: number };
};

type AntiFailureResponse = {
  summary: { total: number; healthy_count: number; degraded_count: number };
};

type SystemComponentStatus = {
  status: string;
  [key: string]: unknown;
};

type SystemOverviewResponse = {
  generated_at: string;
  frontend: SystemComponentStatus;
  backend: SystemComponentStatus;
  database: SystemComponentStatus;
  security: { strict_mode: boolean; jwt_configured: boolean; vault_configured: boolean };
  integrations: { ready: number; total: number; ratio: number };
  queues: { total_events: number; active_queues: number };
  capabilities: { coverage_percent: number; features_ready_estimate: number; features_total: number };
};

type SnapshotHistoryItem = {
  id: number;
  generated_at: string;
  frontend_status: string;
  backend_status: string;
  database_status: string;
  strict_security_mode: boolean;
  db_ready: boolean;
  integrations_ready: number;
  integrations_total: number;
  integration_ratio: number;
  queue_total_events: number;
  active_queues: number;
  capabilities_ready_estimate: number;
  capabilities_total: number;
  coverage_percent: number;
  fallback_buffer_hot: boolean;
};

type SnapshotHistoryResponse = {
  count: number;
  items: SnapshotHistoryItem[];
  trends: {
    time_labels: string[];
    queue_events: number[];
    integration_ratio_percent: number[];
    coverage_percent: number[];
  };
};

type CapabilityFeature = {
  id: string;
  name: string;
  path: string;
  ready: boolean;
};

type CapabilityCategory = {
  id: string;
  name: string;
  features: CapabilityFeature[];
};

type CapabilitiesResponse = {
  categories: CapabilityCategory[];
  totals: { features: number; categories: number; db_ready: boolean };
};

type RevenueAttributionResponse = {
  totals: {
    conversions: number;
    tracked_conversions: number;
    revenue: number;
    attributed_revenue: number;
    unattributed_revenue: number;
  };
  channels: { channel: string; attributed_revenue: number }[];
  top_posts: { post_id: string; attributed_revenue: number }[];
};

type GrowthSuiteFeature = {
  key: string;
  name: string;
  status: string;
  headline: string;
  updated_at?: string | null;
  metrics: { label: string; value: string | number | boolean }[];
};

type GrowthSuiteResponse = {
  features: GrowthSuiteFeature[];
  totals: { features: number; configured: number; db_ready: boolean };
};

type HybridStacksApiTool = {
  name?: string;
  score?: number;
  capabilities?: unknown;
};

type HybridStacksApiStack = {
  id?: string;
  category?: string;
  goal?: string;
  constraint?: string;
  free_tools?: HybridStacksApiTool[];
  open_source_tools?: HybridStacksApiTool[];
  hybrid_stack?: string;
  outcomes?: unknown;
  hybrid_score?: string;
};

type HybridStacksApiSummary = {
  category?: string;
  stack?: string;
  score?: string;
};

type HybridStacksApiResponse = {
  recommendation?: {
    hybrid?: string;
    score?: string;
    benefits?: unknown;
    positioning?: string;
  };
  stacks?: HybridStacksApiStack[];
  summary?: HybridStacksApiSummary[];
};

type TrendRow = {
  id: string;
  label: string;
  value: string;
};

function buildTrendRows(
  labels: string[],
  values: number[],
  prefix: string,
  formatter?: (value: number) => string
): TrendRow[] {
  return values.slice(-8).map((value, index) => {
    const label = labels.slice(-8)[index] || `T${index + 1}`;
    return {
      id: `${prefix}-${label}-${index}`,
      label,
      value: formatter ? formatter(value) : String(value),
    };
  });
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
}

function mapHybridTool(tool: HybridStacksApiTool) {
  return {
    name: typeof tool.name === 'string' && tool.name.trim() ? tool.name : 'Unknown tool',
    score: typeof tool.score === 'number' ? tool.score : 0,
    capabilities: toStringArray(tool.capabilities),
  };
}

export default function PlatformPage() {
  // NOSONAR
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [antiFailure, setAntiFailure] = useState<AntiFailureResponse | null>(null);
  const [systemOverview, setSystemOverview] = useState<SystemOverviewResponse | null>(null);
  const [systemHistory, setSystemHistory] = useState<SnapshotHistoryResponse | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [attribution, setAttribution] = useState<RevenueAttributionResponse | null>(null);
  const [growthSuite, setGrowthSuite] = useState<GrowthSuiteResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [touchpointUrl, setTouchpointUrl] = useState('https://example.com/pricing');
  const [touchpointPlatform, setTouchpointPlatform] = useState('linkedin');
  const [touchpointCampaign, setTouchpointCampaign] = useState('spring_launch');
  const [touchpointPostId, setTouchpointPostId] = useState('post_001');
  const [generatedTrackedUrl, setGeneratedTrackedUrl] = useState('');
  const [isGeneratingTrackedUrl, setIsGeneratingTrackedUrl] = useState(false);
  const [isBootstrappingGrowthSuite, setIsBootstrappingGrowthSuite] = useState(false);
  const [hybridRecommendation, setHybridRecommendation] = useState<{
    hybrid: string;
    score: string;
    benefits: string[];
    positioning: string;
  } | null>(null);
  const [hybridStacks, setHybridStacks] = useState(OPEN_SOURCE_HYBRID_STACKS);
  const [hybridSummary, setHybridSummary] = useState(FINAL_HYBRID_SUMMARY);

  function applyHybridStacksResponse(payload: HybridStacksApiResponse) {
    if (payload.recommendation) {
      setHybridRecommendation({
        hybrid:
          typeof payload.recommendation.hybrid === 'string' && payload.recommendation.hybrid.trim()
            ? payload.recommendation.hybrid
            : 'OpenLens (Free) + Promptwatch (Paid)',
        score:
          typeof payload.recommendation.score === 'string' && payload.recommendation.score.trim()
            ? payload.recommendation.score
            : '100/100 (100%)',
        benefits: toStringArray(payload.recommendation.benefits),
        positioning:
          typeof payload.recommendation.positioning === 'string' && payload.recommendation.positioning.trim()
            ? payload.recommendation.positioning
            : 'This is the only configuration that gives complete GEO + LLMO coverage at the lowest cost.',
      });
    }

    if (Array.isArray(payload.stacks) && payload.stacks.length > 0) {
      setHybridStacks(
        payload.stacks.map((stack) => ({
          id: typeof stack.id === 'string' && stack.id.trim() ? stack.id : 'unknown',
          category: typeof stack.category === 'string' && stack.category.trim() ? stack.category : 'Unknown category',
          goal: typeof stack.goal === 'string' ? stack.goal : '',
          constraint: typeof stack.constraint === 'string' ? stack.constraint : '',
          freeTools: Array.isArray(stack.free_tools) ? stack.free_tools.map(mapHybridTool) : [],
          openSourceTools: Array.isArray(stack.open_source_tools) ? stack.open_source_tools.map(mapHybridTool) : [],
          hybridStack: typeof stack.hybrid_stack === 'string' ? stack.hybrid_stack : '',
          outcomes: toStringArray(stack.outcomes),
          hybridScore: typeof stack.hybrid_score === 'string' ? stack.hybrid_score : '',
        }))
      );
    }

    if (Array.isArray(payload.summary) && payload.summary.length > 0) {
      setHybridSummary(
        payload.summary.map((row) => ({
          category: typeof row.category === 'string' ? row.category : 'Unknown',
          stack: typeof row.stack === 'string' ? row.stack : '',
          score: typeof row.score === 'string' ? row.score : '',
        }))
      );
    }
  }

  async function loadPlatformTelemetry(showSpinner = true) {
    if (showSpinner) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError('');
    try {
      const [s, c, m, a, so, sh, caps, attr, growth, hybrid] = await Promise.all([
        apiGet('/ops/platform/status'),
        apiGet('/ops/platform/use-case-coverage'),
        apiGet('/ops/platform/metrics-summary'),
        apiGet('/ops/platform/anti-failure-status'),
        apiGet('/ops/platform/system-overview'),
        apiGet('/ops/platform/system-overview/history?limit=24'),
        apiGet('/ops/platform/capabilities'),
        apiGet('/analytics/revenue-attribution/report?window_days=90'),
        apiGet('/ops/platform/growth-suite'),
        apiGet('/ops/platform/hybrid-stacks'),
      ]);
      setStatus(s as unknown as StatusResponse);
      setCoverage(c as unknown as CoverageResponse);
      setMetrics(m as unknown as MetricsResponse);
      setAntiFailure(a as unknown as AntiFailureResponse);
      setSystemOverview(so as unknown as SystemOverviewResponse);
      setSystemHistory(sh as unknown as SnapshotHistoryResponse);
      setCapabilities(caps as unknown as CapabilitiesResponse);
      setAttribution(attr as unknown as RevenueAttributionResponse);
      setGrowthSuite(growth as unknown as GrowthSuiteResponse);
      applyHybridStacksResponse(hybrid as unknown as HybridStacksApiResponse);
      setLastUpdatedAt(new Date());
    } catch (e) {
      setError((e as Error).message || 'Failed to load platform telemetry.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadPlatformTelemetry(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      void loadPlatformTelemetry(false);
    }, 15000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh]);

  const queueRows = useMemo(() => {
    const items = Object.entries(metrics?.queues || {}).sort((a, b) => b[1] - a[1]);
    const max = Math.max(1, ...items.map(([, v]) => v));
    return items.slice(0, 8).map(([name, value]) => ({
      name,
      value,
      width: Math.max(4, Math.round((value / max) * 100)),
    }));
  }, [metrics]);

  const integrationRows = useMemo(() => {
    const items = Object.entries(status?.integrations || {});
    return items
      .filter(([, value]) => typeof value === 'boolean')
      .map(([key, value]) => ({ key, ready: Boolean(value) }))
      .sort((a, b) => Number(b.ready) - Number(a.ready));
  }, [status]);

  async function generateTrackedLink() {
    setIsGeneratingTrackedUrl(true);
    try {
      const response = (await apiPost('/analytics/revenue-attribution/touchpoints', {
        post_id: touchpointPostId,
        platform: touchpointPlatform,
        campaign: touchpointCampaign,
        destination_url: touchpointUrl,
      })) as AnyObject;
      const touchpoint = response.touchpoint as AnyObject;
      const trackedUrl = typeof touchpoint.tracked_url === 'string' ? touchpoint.tracked_url : '';
      setGeneratedTrackedUrl(trackedUrl);
      void loadPlatformTelemetry(false);
    } catch (e) {
      setError((e as Error).message || 'Failed to generate tracked URL.');
    } finally {
      setIsGeneratingTrackedUrl(false);
    }
  }

  async function bootstrapGrowthSuite() {
    setIsBootstrappingGrowthSuite(true);
    try {
      const response = (await apiPost('/ops/platform/growth-suite/bootstrap', {})) as unknown as GrowthSuiteResponse;
      setGrowthSuite(response);
      await loadPlatformTelemetry(false);
    } catch (e) {
      setError((e as Error).message || 'Failed to bootstrap the AI growth suite.');
    } finally {
      setIsBootstrappingGrowthSuite(false);
    }
  }

  async function captureSystemSnapshot() {
    try {
      await apiPost('/ops/platform/system-overview/capture', {});
      await loadPlatformTelemetry(false);
    } catch (e) {
      setError((e as Error).message || 'Failed to capture system snapshot.');
    }
  }

  const queueTrendRows = useMemo(
    () => buildTrendRows(systemHistory?.trends.time_labels || [], systemHistory?.trends.queue_events || [], 'queue'),
    [systemHistory]
  );
  const integrationTrendRows = useMemo(
    () =>
      buildTrendRows(
        systemHistory?.trends.time_labels || [],
        systemHistory?.trends.integration_ratio_percent || [],
        'integration',
        (value) => `${value.toFixed(2)}%`
      ),
    [systemHistory]
  );
  const coverageTrendRows = useMemo(
    () =>
      buildTrendRows(
        systemHistory?.trends.time_labels || [],
        systemHistory?.trends.coverage_percent || [],
        'coverage',
        (value) => `${value.toFixed(2)}%`
      ),
    [systemHistory]
  );
  const productionReadinessChecks = useMemo(
    () => [
      {
        id: 'frontend-ready',
        label: 'Frontend runtime healthy',
        ready: systemOverview?.frontend.status === 'ready',
      },
      {
        id: 'backend-ready',
        label: 'Backend runtime healthy',
        ready: systemOverview?.backend.status === 'ready',
      },
      {
        id: 'database-ready',
        label: 'Database ready',
        ready: Boolean(status?.db_ready),
      },
      {
        id: 'security-strict',
        label: 'Strict security mode enabled',
        ready: Boolean(systemOverview?.security.strict_mode),
      },
      {
        id: 'queue-active',
        label: 'Queue subsystem active',
        ready: (systemOverview?.queues.active_queues ?? 0) > 0,
      },
      {
        id: 'coverage-threshold',
        label: 'Coverage above production threshold',
        ready: (coverage?.coverage_percent ?? 0) >= 90,
      },
    ],
    [coverage?.coverage_percent, status?.db_ready, systemOverview]
  );

  return (
    <main>
      <section className="hero platform-hero">
        <p className="eyebrow">Live Control Center</p>
        <h1>Nuxtron Unified Platform Surface</h1>
        <p>
          Every major feature family, backend health signal, and operational readiness metric in one connected command
          page.
        </p>
        <div className="platform-controls">
          <button
            type="button"
            className="cta-link"
            onClick={() => {
              void loadPlatformTelemetry(false);
            }}
            disabled={refreshing || loading}
          >
            {refreshing ? 'Refreshing...' : 'Refresh now'}
          </button>
          <label className="platform-autorefresh-toggle">
            <input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />{' '}
            Auto refresh every 15s
          </label>
          <span className="platform-last-updated">
            Last updated: {lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : 'Not yet'}
          </span>
        </div>
      </section>

      {loading ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3>Loading platform telemetry...</h3>
        </section>
      ) : null}

      {error ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3>Platform telemetry unavailable</h3>
          <p className="muted">{error}</p>
        </section>
      ) : null}

      {!loading && !error ? (
        <PlatformDashboardContent
          status={status}
          coverage={coverage}
          metrics={metrics}
          antiFailure={antiFailure}
          capabilities={capabilities}
          attribution={attribution}
          growthSuite={growthSuite}
          systemOverview={systemOverview}
          systemHistory={systemHistory}
          queueRows={queueRows}
          integrationRows={integrationRows}
          queueTrendRows={queueTrendRows}
          integrationTrendRows={integrationTrendRows}
          coverageTrendRows={coverageTrendRows}
          generatedTrackedUrl={generatedTrackedUrl}
          isGeneratingTrackedUrl={isGeneratingTrackedUrl}
          isBootstrappingGrowthSuite={isBootstrappingGrowthSuite}
          touchpointPostId={touchpointPostId}
          touchpointPlatform={touchpointPlatform}
          touchpointCampaign={touchpointCampaign}
          touchpointUrl={touchpointUrl}
          productionReadinessChecks={productionReadinessChecks}
          hybridRecommendation={hybridRecommendation || undefined}
          hybridStacks={hybridStacks}
          hybridSummary={hybridSummary}
          setTouchpointPostId={setTouchpointPostId}
          setTouchpointPlatform={setTouchpointPlatform}
          setTouchpointCampaign={setTouchpointCampaign}
          setTouchpointUrl={setTouchpointUrl}
          onGenerateTrackedLink={() => {
            void generateTrackedLink();
          }}
          onBootstrapGrowthSuite={() => {
            void bootstrapGrowthSuite();
          }}
          onCaptureSystemSnapshot={() => {
            void captureSystemSnapshot();
          }}
        />
      ) : null}
    </main>
  );
}
