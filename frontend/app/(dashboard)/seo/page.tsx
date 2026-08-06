'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import AnalyticsExecutiveBoard from '@/app/components/analytics-executive-board';
import DegradedModeBanner from '@/app/components/degraded-mode-banner';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { getCatalogByRoutePath } from './module-catalog';
import { getFallbackModulesResponse } from './module-registry-fallback';
import { getPillStyle, getTierBadgeStyle } from './tier-tone';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AnalysesResponse = {
  analyses: Array<Record<string, unknown>>;
  total: number;
  persistence?: string;
};

type HealthResponse = {
  modules?: number;
  ollama_connected?: boolean;
  ai_backend?: string;
};

type GatewayStatusResponse = {
  cache?: {
    metrics?: {
      hit_ratio?: number;
      lookups?: number;
      errors?: number;
    };
    trend_5m?: {
      avg_latency_ms?: number;
      error_rate?: number;
      requests?: number;
    };
  };
  observability?: {
    sentry_enabled?: boolean;
    otel_enabled?: boolean;
  };
};

type StrategySnapshotSummary = {
  site_id: string;
  total: number;
};

type RichResultSummary = {
  site_id: string;
  opportunities: number;
  total_impressions: number;
  average_ctr: number;
};

type ToolStatus = {
  key: string;
  display_name: string;
  tier: string;
  category: string;
  cost_label: string;
  why: string;
  configured: boolean;
  last_test_status: string;
};

type ToolsResponse = {
  total: number;
  configured: number;
  tools: ToolStatus[];
};

type SeoModule = {
  key: string;
  group: string;
  display_name: string;
  description: string;
  route_path: string;
  badge?: string | null;
  implemented: boolean;
  backend_ready: boolean;
  frontend_ready: boolean;
  database_ready: boolean;
  integrations: string[];
  supported_channels?: string[];
  architecture_layers?: string[];
  automation_features?: string[];
  analytics_features?: string[];
  enterprise_features?: string[];
  ai_models?: string[];
  delivery_constraints?: string[];
};

type SeoModuleGroup = {
  group: string;
  items: SeoModule[];
};

type ModulesResponse = {
  total: number;
  implemented: number;
  groups: SeoModuleGroup[];
  modules: SeoModule[];
};

type GroupTone = {
  accent: string;
  soft: string;
  glow: string;
};

type SeoModuleCardProps = Readonly<{
  item: SeoModule;
  tone: GroupTone;
}>;

function SeoModuleCard({ item, tone }: SeoModuleCardProps) {
  const catalog = getCatalogByRoutePath(item.route_path);
  const featurePills = [
    (item.supported_channels?.length ?? 0) > 0 ? { label: `Channels ${item.supported_channels?.length ?? 0}`, color: '#0ea5e9' } : null,
    (item.automation_features?.length ?? 0) > 0 ? { label: `Automation ${item.automation_features?.length ?? 0}`, color: '#22c55e' } : null,
    (item.analytics_features?.length ?? 0) > 0 ? { label: `Analytics ${item.analytics_features?.length ?? 0}`, color: '#6366f1' } : null,
    (item.ai_models?.length ?? 0) > 0 ? { label: `AI ${item.ai_models?.length ?? 0}`, color: '#f59e0b' } : null,
    (item.enterprise_features?.length ?? 0) > 0 ? { label: `Governance ${item.enterprise_features?.length ?? 0}`, color: '#f43f5e' } : null,
  ].filter(Boolean) as Array<{ label: string; color: string }>;

  return (
    <Link
      href={item.route_path}
      aria-label={`${item.display_name} module`}
      data-testid="seo-module-card"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 16,
        padding: '14px 16px',
        textDecoration: 'none',
        color: 'inherit',
        display: 'block',
        position: 'relative',
        borderColor: tone.soft,
        boxShadow: `0 18px 44px -36px ${tone.glow}`,
      }}
    >
      <span
        style={{
          position: 'absolute',
          left: 10,
          right: 10,
          top: 0,
          height: 2,
          borderRadius: 999,
          background: tone.accent,
          opacity: 0.85,
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <strong style={{ fontSize: 14 }}>{catalog?.title ?? item.display_name}</strong>
        {catalog?.tier && <span style={getTierBadgeStyle(catalog.tier)}>{catalog.tier}</span>}
        {item.badge && (
          <span style={getPillStyle({ bg: tone.soft, color: tone.accent, border: tone.soft }, 'xs', { uppercase: false })}>
            {item.badge}
          </span>
        )}
        {!item.implemented && (
          <span
            style={getPillStyle(
              {
                bg: 'rgba(31,41,55,0.9)',
                color: '#d1d5db',
                border: 'rgba(107,114,128,0.45)',
              },
              'xs',
              { uppercase: false }
            )}
          >
            Registry
          </span>
        )}
      </div>
      <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>{catalog?.summary ?? item.description}</p>
      {featurePills.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          {featurePills.map((pill) => (
            <span
              key={pill.label}
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.02em',
                borderRadius: 999,
                padding: '3px 8px',
                border: `1px solid ${pill.color}55`,
                background: `${pill.color}1a`,
                color: pill.color,
              }}
            >
              {pill.label}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}

function hasUsableModuleRegistry(data: ModulesResponse | null): data is ModulesResponse {
  if (!data) return false;
  const hasModules = Array.isArray(data.modules) && data.modules.length > 0;
  const hasGroups = Array.isArray(data.groups) && data.groups.length > 0;
  const hasTotal = typeof data.total === 'number' && data.total > 0;
  return hasModules && hasGroups && hasTotal;
}

function isFulfilled(result: PromiseSettledResult<unknown>): result is PromiseFulfilledResult<unknown> {
  return result.status === 'fulfilled';
}

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
  return isFulfilled(result) ? result.value : fallback;
}

function getSettledReasonMessage(result: PromiseRejectedResult): string {
  const reason = result.reason;
  if (reason instanceof Error) return reason.message;
  if (typeof reason === 'string') return reason;
  return 'Unknown modules feed error';
}

type ModuleResolution = {
  modules: ModulesResponse;
  usedFallback: boolean;
  fallbackReason: string;
};

function classifyModulesFallbackReason(message: string): string {
  if (/timed out/i.test(message)) return 'modules feed timed out';
  if (/(401|403|unauthorized|forbidden)/i.test(message)) return 'modules feed authorization failed';
  return 'modules feed request failed';
}

function resolveModulesResponse(modulesResult: PromiseSettledResult<ModulesResponse>): ModuleResolution {
  if (modulesResult.status === 'fulfilled' && hasUsableModuleRegistry(modulesResult.value)) {
    return {
      modules: modulesResult.value,
      usedFallback: false,
      fallbackReason: '',
    };
  }

  if (modulesResult.status === 'rejected') {
    const message = getSettledReasonMessage(modulesResult);
    return {
      modules: getFallbackModulesResponse(),
      usedFallback: true,
      fallbackReason: classifyModulesFallbackReason(message),
    };
  }

  return {
    modules: getFallbackModulesResponse(),
    usedFallback: true,
    fallbackReason: 'modules feed payload malformed',
  };
}

async function withTimeout<T>(promise: Promise<T>, label: string, timeoutMs = 6000): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<T>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`${label} request timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

const SAAS_ROUTE_OVERRIDES: Record<string, string> = {
  'news-seo-google-discover': '/seo/news-discover',
  'analytics-reporting-intelligence': '/seo/history',
  'agency-multi-tenant-platform': '/seo/agency-platform',
};

function normalizeModule(item: SeoModule): SeoModule {
  const overrideRoute = SAAS_ROUTE_OVERRIDES[item.key];
  if (!overrideRoute) return item;
  return {
    ...item,
    route_path: overrideRoute,
    implemented: true,
    backend_ready: true,
    frontend_ready: true,
  };
}

function normalizeModulesResponse(data: ModulesResponse): ModulesResponse {
  const normalizedModules = data.modules.map(normalizeModule);
  const normalizedGroups = data.groups.map((group) => ({
    ...group,
    items: group.items.map(normalizeModule),
  }));
  return {
    ...data,
    implemented: normalizedModules.filter((module) => module.implemented).length,
    modules: normalizedModules,
    groups: normalizedGroups,
  };
}

function getGroupTone(groupName: string | undefined): GroupTone {
  const name = (groupName ?? '').toLowerCase();
  if (name.includes('ads') || name.includes('retail')) {
    return { accent: '#f59e0b', soft: 'rgba(245,158,11,0.28)', glow: 'rgba(245,158,11,0.35)' };
  }
  if (name.includes('experience')) {
    return { accent: '#22c55e', soft: 'rgba(34,197,94,0.28)', glow: 'rgba(34,197,94,0.35)' };
  }
  if (name.includes('performance') || name.includes('audit')) {
    return { accent: '#6366f1', soft: 'rgba(99,102,241,0.28)', glow: 'rgba(99,102,241,0.35)' };
  }
  if (name.includes('governance') || name.includes('enterprise')) {
    return { accent: '#f43f5e', soft: 'rgba(244,63,94,0.28)', glow: 'rgba(244,63,94,0.35)' };
  }
  if (name.includes('intelligence')) {
    return { accent: '#38bdf8', soft: 'rgba(56,189,248,0.28)', glow: 'rgba(56,189,248,0.35)' };
  }
  return { accent: '#06b6d4', soft: 'rgba(6,182,212,0.28)', glow: 'rgba(6,182,212,0.35)' };
}

export default function SEOHubPage() {
  const [historyTotal, setHistoryTotal] = useState(0);
  const [persistenceMode, setPersistenceMode] = useState('memory');
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState('');
  const [analyticsWarning, setAnalyticsWarning] = useState('');
  const [gatewayStatus, setGatewayStatus] = useState<GatewayStatusResponse | null>(null);
  const [strategySnapshots, setStrategySnapshots] = useState(0);
  const [richResultOpportunities, setRichResultOpportunities] = useState(0);
  const [richResultCtr, setRichResultCtr] = useState(0);
  const [toolsData, setToolsData] = useState<ToolsResponse | null>(null);
  const [modulesData, setModulesData] = useState<ModulesResponse | null>(null);
  const [isModuleFallbackActive, setIsModuleFallbackActive] = useState(false);
  const [moduleFallbackReason, setModuleFallbackReason] = useState('');

  useEffect(() => {
    async function loadSeoAnalytics() {
      setLoading(true);
      setAnalyticsError('');
      setAnalyticsWarning('');
      try {
        const [
          historyResult,
          healthResult,
          gatewayResult,
          snapshotResult,
          richResultResult,
          toolsResult,
          modulesResult,
        ] = await Promise.allSettled([
          withTimeout(apiGet<AnalysesResponse>('/seo-platform/analyses?limit=100', DEFAULT_TENANT_ID), 'Analyses'),
          withTimeout(apiGet<HealthResponse>('/seo-platform/health', DEFAULT_TENANT_ID), 'Health'),
          withTimeout(apiGet<GatewayStatusResponse>('/ai/gateway/status', DEFAULT_TENANT_ID), 'Gateway status'),
          withTimeout(
            apiGet<StrategySnapshotSummary>(
              `/v1/loop/strategy-snapshots/${DEFAULT_TENANT_ID}?limit=20`,
              DEFAULT_TENANT_ID
            ),
            'Strategy snapshots'
          ),
          withTimeout(
            apiGet<RichResultSummary>(`/v1/loop/rich-results/${DEFAULT_TENANT_ID}?limit=100`, DEFAULT_TENANT_ID),
            'Rich results'
          ),
          withTimeout(apiGet<ToolsResponse>('/integrations/tools', DEFAULT_TENANT_ID), 'Tools'),
          withTimeout(apiGet<ModulesResponse>('/seo-platform/modules', DEFAULT_TENANT_ID), 'Modules', 12000),
        ]);
        const history = settledValue(historyResult, {
          analyses: [],
          total: 0,
          persistence: 'memory',
        });
        const health = settledValue(healthResult, {});
        const gateway = isFulfilled(gatewayResult) ? gatewayResult.value : null;
        const snapshotSummary = settledValue(snapshotResult, {
          site_id: DEFAULT_TENANT_ID,
          total: 0,
        });
        const richResultSummary = settledValue(richResultResult, {
          site_id: DEFAULT_TENANT_ID,
          opportunities: 0,
          total_impressions: 0,
          average_ctr: 0,
        });
        const tools = isFulfilled(toolsResult) ? toolsResult.value : null;
        const moduleResolution = resolveModulesResponse(modulesResult);

        setHistoryTotal(typeof history.total === 'number' ? history.total : 0);
        setPersistenceMode(typeof history.persistence === 'string' ? history.persistence : 'memory');
        setOllamaConnected(Boolean(health.ollama_connected));
        setGatewayStatus(gateway);
        setStrategySnapshots(typeof snapshotSummary.total === 'number' ? snapshotSummary.total : 0);
        setRichResultOpportunities(
          typeof richResultSummary.opportunities === 'number' ? richResultSummary.opportunities : 0
        );
        setRichResultCtr(typeof richResultSummary.average_ctr === 'number' ? richResultSummary.average_ctr : 0);
        setToolsData(tools ?? { total: 0, configured: 0, tools: [] });
        setModulesData(normalizeModulesResponse(moduleResolution.modules));
        setIsModuleFallbackActive(moduleResolution.usedFallback);
        setModuleFallbackReason(moduleResolution.fallbackReason);

        const moduleFeedFailed = moduleResolution.usedFallback;

        if (moduleFeedFailed || moduleResolution.usedFallback) {
          setAnalyticsWarning('Live module registry feed is unstable. Refresh to retry.');
        } else {
          setAnalyticsWarning('');
        }
      } catch (error) {
        setHistoryTotal(0);
        setPersistenceMode('memory');
        setOllamaConnected(false);
        setGatewayStatus(null);
        setStrategySnapshots(0);
        setRichResultOpportunities(0);
        setRichResultCtr(0);
        setToolsData(null);
        setModulesData(null);
        setIsModuleFallbackActive(false);
        setModuleFallbackReason('');
        setAnalyticsWarning('');
        setAnalyticsError(error instanceof Error ? error.message : 'Unable to load analytics right now.');
      } finally {
        setLoading(false);
      }
    }

    void loadSeoAnalytics();
  }, []);

  const totalModules = modulesData?.total ?? 0;
  const categoryCounts = (modulesData?.groups ?? []).map((group) => ({
    label: group.group,
    value: group.items.length,
  }));
  const modules = modulesData?.modules ?? [];
  const adsControlTowerCount = categoryCounts.find((c) => c.label === 'Ads Orchestration & Retail Media')?.value ?? 0;
  const adNetworkCoverage = modules.filter((module) => (module.supported_channels?.length ?? 0) > 0).length;
  const automationEngineCount = modules.filter((module) => (module.automation_features?.length ?? 0) > 0).length;
  const aiModelCoverage = modules.reduce((count, module) => count + (module.ai_models?.length ?? 0), 0);
  const enterpriseControlledCount = modules.filter((module) => (module.enterprise_features?.length ?? 0) > 0).length;
  const advancedSignalModules = modules.filter(
    (module) =>
      (module.supported_channels?.length ?? 0) +
        (module.automation_features?.length ?? 0) +
        (module.analytics_features?.length ?? 0) +
        (module.enterprise_features?.length ?? 0) +
        (module.ai_models?.length ?? 0) >
      0
  ).length;
  let ollamaStatusLabel = 'Offline';
  if (loading) {
    ollamaStatusLabel = 'Checking...';
  } else if (ollamaConnected) {
    ollamaStatusLabel = 'Connected';
  }
  const card = {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: '14px 16px',
    boxShadow: 'var(--shadow-sm)',
  };
  const botifyQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/botify-readiness',
      title: 'Botify Readiness Hub',
      summary: 'Track parity, integration coverage, and production gate outcomes for the Botify slice.',
    },
    {
      href: '/seo/botify-automation',
      title: 'Botify Automation',
      summary: 'Create projects, trigger runs, and operate schedule-driven execution workflows.',
    },
    {
      href: '/seo/botify-integrations',
      title: 'Botify Integrations',
      summary: 'View provider checklist, preflight blockers, remediation bundles, and export actions.',
    },
    {
      href: '/seo/botify-assist',
      title: 'Botify Assist Console',
      summary: 'Submit Assist prompts against latest gate and vendor context for operational guidance.',
    },
  ];
  const seoAiQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/seo-ai-readiness',
      title: 'SEO.AI Readiness Hub',
      summary: 'Track parity, integration coverage, and production gate outcomes for the SEO.AI slice.',
    },
    {
      href: '/seo/seo-ai-automation',
      title: 'SEO.AI Automation',
      summary: 'Create projects, trigger runs, and operate schedule-driven execution workflows.',
    },
    {
      href: '/seo/seo-ai-integrations',
      title: 'SEO.AI Integrations',
      summary: 'View provider checklist, preflight blockers, remediation bundles, and export actions.',
    },
    {
      href: '/seo/seo-ai-assist',
      title: 'SEO.AI Assist Console',
      summary: 'Submit Assist prompts against latest gate and vendor context for operational guidance.',
    },
  ];
  const hootsuiteQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/hootsuite-readiness',
      title: 'Hootsuite Readiness Hub',
      summary: 'Track parity, integration coverage, and production gate outcomes for the Hootsuite slice.',
    },
    {
      href: '/seo/hootsuite-automation',
      title: 'Hootsuite Automation',
      summary: 'Create projects, trigger runs, and operate schedule-driven execution workflows.',
    },
    {
      href: '/seo/hootsuite-integrations',
      title: 'Hootsuite Integrations',
      summary: 'View provider checklist, preflight blockers, remediation bundles, and export actions.',
    },
    {
      href: '/seo/sproutsocial-automation',
      title: 'Sprout Social Automation',
      summary: 'Live end-to-end status for publishing, inbox, listening, analytics, and automation workflows.',
    },
  ];
  const yextQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/yext-readiness',
      title: 'Yext Readiness Hub',
      summary: 'Track parity, vendor coverage, and production gate outcomes for the Yext slice.',
    },
    {
      href: '/seo/yext-automation',
      title: 'Yext Automation',
      summary: 'Create projects, trigger runs, and execute product-level Yext automation blueprints.',
    },
    {
      href: '/seo/yext-integrations',
      title: 'Yext Integrations',
      summary: 'View provider checklist, apply wiring, inspect remediation bundles, and export gaps.',
    },
    {
      href: '/seo/yext-assist',
      title: 'Yext Assist Console',
      summary: 'Generate operator guidance, workflow handoffs, and rollout actions for the Yext command center.',
    },
  ];
  const brightedgeQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/brightedge-readiness',
      title: 'BrightEdge Readiness Hub',
      summary: 'Track parity, vendor coverage, and production gate outcomes for the BrightEdge slice.',
    },
    {
      href: '/seo/brightedge-automation',
      title: 'BrightEdge Automation',
      summary: 'Create projects, trigger runs, and execute product-level BrightEdge automation blueprints.',
    },
    {
      href: '/seo/brightedge-integrations',
      title: 'BrightEdge Integrations',
      summary: 'View provider checklist, apply wiring, inspect remediation bundles, and export gaps.',
    },
    {
      href: '/seo/brightedge-assist',
      title: 'BrightEdge Assist Console',
      summary: 'Generate operator guidance, workflow handoffs, and rollout actions for the BrightEdge command center.',
    },
  ];
  const writesonicQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/writesonic-readiness',
      title: 'Writesonic Readiness Hub',
      summary: 'Track parity, vendor coverage, and production gate outcomes for the Writesonic slice.',
    },
    {
      href: '/seo/writesonic-automation',
      title: 'Writesonic Automation',
      summary: 'Create projects, trigger runs, and execute product-level Writesonic automation blueprints.',
    },
    {
      href: '/seo/writesonic-integrations',
      title: 'Writesonic Integrations',
      summary: 'View provider checklist, apply wiring, inspect remediation bundles, and export gaps.',
    },
    {
      href: '/seo/writesonic-assist',
      title: 'Writesonic Assist Console',
      summary: 'Generate operator guidance, workflow handoffs, and rollout actions for the Writesonic command center.',
    },
  ];
  const semrushQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/semrush-command-center',
      title: 'Semrush Command Center',
      summary: 'Live Semrush parity, provider bootstrap, production gate, env template, and full automation.',
    },
    {
      href: '/seo/rank-tracking',
      title: 'Rank Tracking',
      summary: 'SERP movement, volatility, and forecast workflows for keyword monitoring.',
    },
    {
      href: '/seo/backlink-intelligence',
      title: 'Backlink Intelligence',
      summary: 'Toxicity, gap analysis, and authority signal workflows.',
    },
    {
      href: '/seo/domain-overview',
      title: 'Domain Overview',
      summary: 'Competitive domain intelligence and visibility snapshots.',
    },
  ];
  const ahrefsQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/ahrefs-command-center',
      title: 'Ahrefs Command Center',
      summary: 'Live Ahrefs parity, e2e verification, provider bootstrap, production gate, and full automation.',
    },
    {
      href: '/seo/site-explorer',
      title: 'Site Explorer',
      summary: 'Domain intelligence and backlink reconnaissance workflows.',
    },
    {
      href: '/seo/keywords-explorer',
      title: 'Keywords Explorer',
      summary: 'Keyword clustering, SERP opportunities, and strategy discovery.',
    },
    {
      href: '/seo/site-audit',
      title: 'Site Audit',
      summary: 'Technical crawl diagnostics and remediation workflows.',
    },
  ];
  const surferQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/surfer-command-center',
      title: 'Surfer Command Center',
      summary: 'Live Surfer parity, wiring plan, setup playbook, production gate, and full automation orchestration.',
    },
    {
      href: '/seo/surfer-readiness',
      title: 'Surfer Readiness Hub',
      summary: 'Track parity, provider wiring, and gate outcomes for the Surfer slice.',
    },
    {
      href: '/seo/surfer-wiring-plan',
      title: 'Surfer Wiring Plan',
      summary: 'Priority sequencing for strict-live readiness and integration closure.',
    },
    {
      href: '/seo/surfer-setup-playbook',
      title: 'Surfer Setup Playbook',
      summary: 'Provider setup notes, preflight commands, and verification endpoints.',
    },
  ];
  const geoptieQuickLinks: Array<{ href: Route; title: string; summary: string }> = [
    {
      href: '/seo/geoptie-readiness',
      title: 'Geoptie Readiness Hub',
      summary: 'Track parity, vendor coverage, and production gate outcomes for the Geoptie slice.',
    },
    {
      href: '/seo/geoptie-automation',
      title: 'Geoptie Automation',
      summary: 'Create projects, trigger runs, and execute product-level Geoptie automation blueprints.',
    },
    {
      href: '/seo/geoptie-integrations',
      title: 'Geoptie Integrations',
      summary: 'View provider checklist, apply wiring, inspect remediation bundles, and export gaps.',
    },
    {
      href: '/seo/geoptie-assist',
      title: 'Geoptie Assist Console',
      summary: 'Generate operator guidance, workflow handoffs, and rollout actions for the Geoptie command center.',
    },
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <section
          style={{
            marginBottom: 28,
            position: 'relative',
            overflow: 'hidden',
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            padding: 20,
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              right: -120,
              top: -110,
              width: 320,
              height: 320,
              borderRadius: 999,
              background: 'radial-gradient(circle, rgba(56,189,248,0.35) 0%, rgba(56,189,248,0) 72%)',
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: -120,
              bottom: -130,
              width: 300,
              height: 300,
              borderRadius: 999,
              background: 'radial-gradient(circle, rgba(59,130,246,0.26) 0%, rgba(59,130,246,0) 72%)',
              pointerEvents: 'none',
            }}
          />

          <div
            style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--brand)',
                border: '1px solid rgba(147,197,253,0.45)',
                borderRadius: 999,
                padding: '3px 10px',
                background: 'rgba(96,165,250,0.14)',
              }}
            >
              Enterprise SEO Command Center
            </span>
            <h1 style={{ margin: 0, fontSize: 30, fontWeight: 800 }}>SEO Platform</h1>
            {isModuleFallbackActive && (
              <span
                title={`Fallback reason: ${moduleFallbackReason || 'unknown'}`}
                aria-label={`Fallback reason: ${moduleFallbackReason || 'unknown'}`}
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 999,
                  padding: '3px 8px',
                border: '1px solid #f59e0b',
                background: '#fef3c7',
                color: '#92400e',
                }}
              >
                Local registry fallback active
              </span>
            )}
          </div>
          <p style={{ color: 'var(--muted)', marginTop: 8, marginBottom: 0 }}>
            Registry-driven SEO and ads control tower with advanced modules spanning AEO/GEO/CXAO, cross-network media
            buying, retail media, analytics, and autonomous planning flows.
          </p>
          {analyticsError && (
            <div style={{ marginTop: 10, ...card, borderColor: '#ef4444', color: '#dc2626' }}>{analyticsError}</div>
          )}
          {analyticsWarning && <DegradedModeBanner message={analyticsWarning} marginTop={10} />}
        </section>

        <section className="card" style={{ marginTop: 28 }}>
          <h2 style={{ marginTop: 0, marginBottom: 8 }}>Semrush Command Center</h2>
          <p style={{ margin: 0, opacity: 0.82 }}>
            Production-grade Semrush parity, provider wiring, and full automation live here with real backend endpoints.
          </p>
          <div
            style={{ display: 'grid', gap: 12, marginTop: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}
          >
            {semrushQuickLinks.map((item) => (
              <a key={item.href} className="card" href={item.href} style={{ textDecoration: 'none' }}>
                <h3 style={{ marginTop: 0 }}>{item.title}</h3>
                <p style={{ opacity: 0.8, marginBottom: 0 }}>{item.summary}</p>
              </a>
            ))}
          </div>
        </section>

        <section className="card" style={{ marginTop: 28 }}>
          <h2 style={{ marginTop: 0, marginBottom: 8 }}>Ahrefs Command Center</h2>
          <p style={{ margin: 0, opacity: 0.82 }}>
            Production-grade Ahrefs parity, e2e verification, provider readiness, and full automation live here with real backend endpoints.
          </p>
          <div
            style={{ display: 'grid', gap: 12, marginTop: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}
          >
            {ahrefsQuickLinks.map((item) => (
              <a key={item.href} className="card" href={item.href} style={{ textDecoration: 'none' }}>
                <h3 style={{ marginTop: 0 }}>{item.title}</h3>
                <p style={{ opacity: 0.8, marginBottom: 0 }}>{item.summary}</p>
              </a>
            ))}
          </div>
        </section>

        <section className="card" style={{ marginTop: 28 }}>
          <h2 style={{ marginTop: 0, marginBottom: 8 }}>Surfer Command Center</h2>
          <p style={{ margin: 0, opacity: 0.82 }}>
            Production-grade Surfer parity, wiring plan, setup playbook, provider readiness, and full automation live here with real backend endpoints.
          </p>
          <div
            style={{ display: 'grid', gap: 12, marginTop: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}
          >
            {surferQuickLinks.map((item) => (
              <a key={item.href} className="card" href={item.href} style={{ textDecoration: 'none' }}>
                <h3 style={{ marginTop: 0 }}>{item.title}</h3>
                <p style={{ opacity: 0.8, marginBottom: 0 }}>{item.summary}</p>
              </a>
            ))}
          </div>
        </section>

        <AnalyticsExecutiveBoard
          title="SEO Command Analytics"
          subtitle="Portfolio-level visibility across SEO execution tracks, AI optimization domains, retail media, and autonomous ad control tower operations."
          kpis={[
            { label: 'Active Modules', value: String(totalModules), delta: '+100% coverage', trend: 'up' },
            {
              label: 'Search Intel',
              value: String(categoryCounts.find((c) => c.label === 'Search Intelligence')?.value ?? 0),
              delta: 'GEO/AEO/AIO/LLMO/GXO',
              trend: 'up',
            },
            {
              label: 'Ads Control Tower',
              value: String(adsControlTowerCount),
              delta: 'Google, Amazon, Apple, Bing, YouTube',
              trend: 'up',
            },
            {
              label: 'Automation Engines',
              value: String(automationEngineCount),
              delta: 'Rules, pacing, sync, orchestration',
              trend: 'up',
            },
            {
              label: 'Ad Network Coverage',
              value: String(adNetworkCoverage),
              delta: 'Live channel-aware modules',
              trend: 'up',
            },
            { label: 'AI Model Pool', value: String(aiModelCoverage), delta: 'LLM + embedding coverage', trend: 'up' },
            {
              label: 'Enterprise-Controlled',
              value: String(enterpriseControlledCount),
              delta: 'RBAC, audit, governance',
              trend: 'up',
            },
            {
              label: 'Analysis History',
              value: loading ? '...' : String(historyTotal),
              delta: `persistence: ${persistenceMode}`,
              trend: persistenceMode === 'postgres' ? 'up' : 'flat',
            },
            {
              label: 'AI Backend',
              value: ollamaStatusLabel,
              delta: 'Ollama health',
              trend: ollamaConnected ? 'up' : 'down',
            },
            {
              label: 'Strategy Snapshots',
              value: loading ? '...' : String(strategySnapshots),
              delta: 'Cluster/gap artifacts',
              trend: strategySnapshots > 0 ? 'up' : 'flat',
            },
            {
              label: 'Rich Result Opportunities',
              value: loading ? '...' : String(richResultOpportunities),
              delta: `avg CTR ${(richResultCtr * 100).toFixed(2)}%`,
              trend: richResultCtr > 0 ? 'up' : 'flat',
            },
          ]}
          bars={categoryCounts}
          line={[32, 38, 41, 49, 58, 63, 71, 68, 76, 88]}
          ring={[
            {
              label: 'Search',
              value: categoryCounts.find((c) => c.label === 'Search Intelligence')?.value ?? 0,
              color: '#0ea5e9',
            },
            {
              label: 'Experience',
              value: categoryCounts.find((c) => c.label === 'Experience Optimization')?.value ?? 0,
              color: '#22c55e',
            },
            { label: 'Ads Tower', value: adsControlTowerCount, color: '#f43f5e' },
            {
              label: 'Performance',
              value: categoryCounts.find((c) => c.label === 'Performance & Audits')?.value ?? 0,
              color: '#6366f1',
            },
          ]}
        />

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Ultimate SEO Operating System
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
            {[
              {
                title: 'Autonomous execution',
                value: String(automationEngineCount),
                summary: 'Planning, rules, orchestration, and synchronized workflows across the stack.',
              },
              {
                title: 'Advanced signals',
                value: String(advancedSignalModules),
                summary: 'Modules carrying AI, analytics, channels, or governance metadata.',
              },
              {
                title: 'Model depth',
                value: String(aiModelCoverage),
                summary: 'LLM and embedding surfaces used for generation, analysis, and evaluation.',
              },
              {
                title: 'Enterprise control',
                value: String(enterpriseControlledCount),
                summary: 'RBAC, auditability, controls, and governance-aware automation.',
              },
              {
                title: 'Network coverage',
                value: String(adNetworkCoverage),
                summary: 'Channel-aware modules that span SEO, ads, retail media, and owned surfaces.',
              },
            ].map((item) => (
              <div key={item.title} style={{ ...card, borderColor: 'rgba(59,130,246,0.28)' }}>
                <div
                  style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}
                >
                  {item.title}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4 }}>{item.value}</div>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Geoptie Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {geoptieQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(132,204,22,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(132,204,22,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            SEO.AI Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {seoAiQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(34,197,94,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(34,197,94,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Writesonic Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {writesonicQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(249,115,22,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(249,115,22,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Yext Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {yextQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(20,184,166,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(20,184,166,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            BrightEdge Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {brightedgeQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(244,114,182,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(244,114,182,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Hootsuite Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {hootsuiteQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(251,191,36,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(251,191,36,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Botify Command Center
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
            {botifyQuickLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.title}
                style={{
                  ...card,
                  textDecoration: 'none',
                  color: 'inherit',
                  borderColor: 'rgba(56,189,248,0.35)',
                  boxShadow: '0 18px 44px -36px rgba(56,189,248,0.75)',
                }}
              >
                <strong style={{ fontSize: 14 }}>{item.title}</strong>
                <p style={{ marginTop: 6, marginBottom: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 }}>
                  {item.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Runtime Health
          </h2>
          <div
            style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}
          >
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Cache Hit Ratio</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>
                {Math.round((gatewayStatus?.cache?.metrics?.hit_ratio ?? 0) * 100 * 100) / 100}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>5m Requests</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>{gatewayStatus?.cache?.trend_5m?.requests ?? 0}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Avg Latency</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>
                {gatewayStatus?.cache?.trend_5m?.avg_latency_ms ?? 0}ms
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Error Rate</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>
                {Math.round((gatewayStatus?.cache?.trend_5m?.error_rate ?? 0) * 100 * 100) / 100}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Sentry</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>
                {gatewayStatus?.observability?.sentry_enabled ? 'On' : 'Off'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>OpenTelemetry</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>
                {gatewayStatus?.observability?.otel_enabled ? 'On' : 'Off'}
              </div>
            </div>
          </div>
        </section>

        {(modulesData?.groups ?? []).map((group) => {
          const tone = getGroupTone(group.group);
          return (
            <section key={group.group} style={{ marginBottom: 28 }}>
              <h2
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: tone.accent,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginBottom: 10,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: tone.accent,
                    boxShadow: `0 0 16px ${tone.glow}`,
                  }}
                />
                {group.group}
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 10 }}>
                {group.items.map((item) => (
                  <SeoModuleCard key={item.key} item={item} tone={tone} />
                ))}
              </div>
            </section>
          );
        })}

        {!modulesData && !loading && (
          <section style={{ marginBottom: 28 }}>
            <div style={{ ...card, color: 'var(--muted)', fontSize: 13 }}>SEO module registry unavailable.</div>
          </section>
        )}

        {/* Tool Integrations Panel */}
        <section style={{ marginBottom: 28 }}>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 10,
            }}
          >
            Tool Integrations ({toolsData ? `${toolsData.configured}/${toolsData.total} configured` : 'Loading...'})
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', gap: 10 }}>
            {(toolsData?.tools ?? []).map((tool) => (
              <div key={tool.key} style={{ ...card, borderColor: tool.configured ? '#22c55e' : 'var(--line)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: tool.configured ? '#22c55e' : '#ef4444',
                      flexShrink: 0,
                    }}
                  />
                  <strong style={{ fontSize: 13 }}>{tool.display_name}</strong>
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>
                  {tool.cost_label} · {tool.category}
                </div>
                <div style={{ fontSize: 11, color: tool.configured ? '#86efac' : '#dc2626' }}>
                  {tool.last_test_status}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{tool.why}</div>
              </div>
            ))}
            {loading && <div style={{ ...card, color: 'var(--muted)', fontSize: 13 }}>Loading integrations...</div>}
            {!loading && toolsData?.tools.length === 0 && (
              <div style={{ ...card, color: 'var(--muted)', fontSize: 13 }}>No integrations configured.</div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
