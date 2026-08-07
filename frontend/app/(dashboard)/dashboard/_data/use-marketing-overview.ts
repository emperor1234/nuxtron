'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';
import {
  difficultyFromScore,
  type AiInsight,
  type DonutSlice,
  type FunnelStage,
  type Kpi,
  type KeywordRow,
  type SocialPlatform,
  type TrendPoint,
} from './marketing-data';

/** Domain the SEO cards report on. Override per-deployment via env. */
const TRACKED_DOMAIN = (process.env.NEXT_PUBLIC_DASHBOARD_DOMAIN || 'nuxtron.io').trim();

const SOCIAL_PLATFORMS: readonly { key: string; name: string; color: string }[] = [
  { key: 'instagram', name: 'Instagram', color: 'linear-gradient(90deg,#f59e0b,#ec4899)' },
  { key: 'linkedin', name: 'LinkedIn', color: '#0a66c2' },
  { key: 'tiktok', name: 'TikTok', color: '#0e1525' },
  { key: 'twitter', name: 'X', color: '#3d4456' },
  { key: 'youtube', name: 'YouTube', color: '#ef4444' },
  { key: 'facebook', name: 'Facebook', color: '#1877f2' },
];

const PIPELINE_COLORS: Record<string, string> = {
  prospect: 'linear-gradient(90deg,#2563eb,#3b82f6)',
  qualified: 'linear-gradient(90deg,#3b82f6,#0ea5e9)',
  proposal: 'linear-gradient(90deg,#0ea5e9,#0d9488)',
  negotiation: 'linear-gradient(90deg,#0d9488,#10b981)',
  closed_won: 'linear-gradient(90deg,#10b981,#059669)',
};

type DomainSummary = {
  domain: string;
  authority_score: number;
  organic_traffic_monthly: number;
  organic_keywords: number;
  _source: string;
};

type TrafficTrendResponse = {
  domain: string;
  trend: Array<{ month: string; organic_traffic: number }>;
};

type OrganicKeywordsResponse = {
  keywords: Array<{
    keyword: string;
    position: number;
    search_volume: number;
    keyword_difficulty: number;
    cpc_usd: number;
  }>;
};

type BacklinksSnapshot = {
  total_backlinks: number;
};

type PipelineResponse = {
  pipeline: Array<{ stage: string; display: string; probability: number; count: number; total_value: number }>;
  total_pipeline_value: number;
  total_closed_won: number;
  total_deals: number;
};

type SocialDashboardResponse = {
  overview: { total_posts: number; scheduled_posts: number; draft_posts: number; published_posts: number };
};

type PlatformAnalyticsResponse = { platform: string; posts: number };

export type MarketingOverviewData = {
  domain: string;
  kpis: Kpi[];
  trend: TrendPoint[];
  trendDeltaPct: number;
  pipelineDonut: DonutSlice[];
  pipelineTotalValue: number;
  keywords: KeywordRow[];
  social: SocialPlatform[];
  funnel: FunnelStage[];
  insights: AiInsight[];
  sources: Set<string>;
};

function monthLabel(iso: string): string {
  const [, m] = iso.split('-');
  const idx = Number(m) - 1;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return months[idx] ?? iso;
}

function formatCompact(n: number): { value: number; suffix?: string; decimals?: number } {
  if (n >= 1_000_000) return { value: Number((n / 1_000_000).toFixed(1)), suffix: 'M', decimals: 1 };
  if (n >= 1_000) return { value: Number((n / 1_000).toFixed(1)), suffix: 'K', decimals: 1 };
  return { value: n, decimals: 0 };
}

function buildInsights(args: {
  keywords: OrganicKeywordsResponse['keywords'];
  backlinks: number;
  socialPosts30d: number;
  socialPosts60d: number;
  pipeline: PipelineResponse;
}): AiInsight[] {
  const { keywords, backlinks, socialPosts30d, socialPosts60d, pipeline } = args;
  const insights: AiInsight[] = [];

  const nearMiss = keywords.filter((k) => k.position > 10 && k.position <= 20);
  if (nearMiss.length > 0) {
    insights.push({
      tag: 'Opportunity',
      tagBg: '#e7f8f1',
      tagColor: '#059669',
      impact: 'High impact',
      text: `${nearMiss.length} tracked keyword${nearMiss.length === 1 ? '' : 's'} rank on page 2 (positions 11–20) — a content refresh could push them into the top 10.`,
    });
  }

  const priorWindow = Math.max(0, socialPosts60d - socialPosts30d);
  const cadenceDelta = priorWindow > 0 ? Math.round(((socialPosts30d - priorWindow) / priorWindow) * 100) : null;
  insights.push({
    tag: 'Social',
    tagBg: '#eaf1ff',
    tagColor: '#2563eb',
    impact: socialPosts30d === 0 ? 'Watch' : 'Medium',
    text:
      socialPosts30d === 0
        ? 'No posts scheduled across connected platforms in the last 30 days — connect a channel or queue content to start tracking engagement.'
        : `${socialPosts30d} posts published across connected platforms in the last 30 days${
            cadenceDelta !== null ? ` (${cadenceDelta >= 0 ? '+' : ''}${cadenceDelta}% vs the prior 30 days)` : ''
          }.`,
  });

  const openValue = pipeline.total_pipeline_value;
  insights.push({
    tag: 'Pipeline',
    tagBg: '#fef3e0',
    tagColor: '#b45309',
    impact: openValue > 0 ? 'High impact' : 'Watch',
    text:
      openValue > 0
        ? `$${Math.round(openValue).toLocaleString('en-US')} in open pipeline across ${pipeline.total_deals} deals, with $${Math.round(pipeline.total_closed_won).toLocaleString('en-US')} closed-won.`
        : 'No open deals in the CRM pipeline yet — log deals to unlock pipeline forecasting here.',
  });

  if (insights.length < 3 && backlinks > 0) {
    insights.push({
      tag: 'Backlinks',
      tagBg: '#fdecec',
      tagColor: '#dc2626',
      impact: 'Watch',
      text: `${backlinks.toLocaleString('en-US')} tracked backlinks. Keep building referring domains to defend authority score.`,
    });
  }

  return insights.slice(0, 3);
}

export function useMarketingOverview() {
  const [data, setData] = useState<MarketingOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const tenantId = resolveSessionTenant();
      const domain = TRACKED_DOMAIN;

      const [summary, trafficTrend, organicKeywords, backlinksSnapshot, pipeline, social30, social60, ...platforms] =
        await Promise.all([
          apiGet(`/domain-overview/summary?domain=${encodeURIComponent(domain)}`, tenantId) as Promise<DomainSummary>,
          apiGet(`/domain-overview/traffic-trend?domain=${encodeURIComponent(domain)}`, tenantId) as Promise<TrafficTrendResponse>,
          apiGet(`/domain-overview/organic-keywords?domain=${encodeURIComponent(domain)}&limit=6`, tenantId) as Promise<OrganicKeywordsResponse>,
          apiGet(`/domain-overview/backlinks-snapshot?domain=${encodeURIComponent(domain)}`, tenantId) as Promise<BacklinksSnapshot>,
          apiGet('/crm/pipeline', tenantId) as Promise<PipelineResponse>,
          apiGet('/social/analytics/dashboard?days=30', tenantId) as Promise<SocialDashboardResponse>,
          apiGet('/social/analytics/dashboard?days=60', tenantId) as Promise<SocialDashboardResponse>,
          ...SOCIAL_PLATFORMS.map((p) => apiGet(`/social/analytics/platform/${p.key}?days=30`, tenantId) as Promise<PlatformAnalyticsResponse>),
        ]);

      const sources = new Set<string>();
      sources.add(summary._source === 'dataforseo' ? 'DataForSEO (live)' : 'domain model');

      const trend: TrendPoint[] = trafficTrend.trend.map((p) => ({ label: monthLabel(p.month), value: p.organic_traffic }));
      const last = trend.at(-1)?.value ?? 0;
      const prev = trend.at(-2)?.value ?? last;
      const trendDeltaPct = prev > 0 ? Number((((last - prev) / prev) * 100).toFixed(1)) : 0;

      const trafficFmt = formatCompact(summary.organic_traffic_monthly);
      const keywordsFmt = formatCompact(summary.organic_keywords);
      const backlinksFmt = formatCompact(backlinksSnapshot.total_backlinks);
      const socialFmt = formatCompact(social30.overview.total_posts);

      const kpis: Kpi[] = [
        {
          key: 'authority',
          label: 'Authority Score',
          value: summary.authority_score,
          decimals: 0,
          color: '#2563eb',
          iconBg: '#eaf1ff',
          icon: 'authority',
        },
        {
          key: 'traffic',
          label: 'Organic Traffic',
          value: trafficFmt.value,
          suffix: trafficFmt.suffix,
          decimals: trafficFmt.decimals,
          delta: Math.abs(trendDeltaPct),
          up: trendDeltaPct >= 0,
          color: '#10b981',
          iconBg: '#e7f8f1',
          icon: 'traffic',
          data: trend.map((p) => p.value),
        },
        {
          key: 'keywords',
          label: 'Organic Keywords',
          value: keywordsFmt.value,
          suffix: keywordsFmt.suffix,
          decimals: keywordsFmt.decimals,
          color: '#0ea5e9',
          iconBg: '#e4f4fd',
          icon: 'keywords',
        },
        {
          key: 'backlinks',
          label: 'Backlinks',
          value: backlinksFmt.value,
          suffix: backlinksFmt.suffix,
          decimals: backlinksFmt.decimals,
          color: '#f59e0b',
          iconBg: '#fef3e0',
          icon: 'backlinks',
        },
        {
          key: 'social',
          label: 'Social Posts (30d)',
          value: socialFmt.value,
          suffix: socialFmt.suffix,
          decimals: socialFmt.decimals,
          color: '#ec4899',
          iconBg: '#fde7f2',
          icon: 'social',
        },
      ];

      // "Open" means still in motion: excludes both closed_lost (not shown)
      // and closed_won (already closed, not open pipeline). The percentage
      // denominator is the same filtered set that's rendered, so slices sum
      // to ~100%.
      const openStages = pipeline.pipeline.filter((s) => s.stage !== 'closed_lost' && s.stage !== 'closed_won');
      const openTotal = openStages.reduce((sum, s) => sum + s.count, 0) || 1;
      const pipelineDonut: DonutSlice[] = openStages.map((s) => ({
        label: s.display,
        pct: Math.round((s.count / openTotal) * 100),
        color: PIPELINE_COLORS[s.stage] ?? '#6b7385',
      }));

      const keywords: KeywordRow[] = organicKeywords.keywords.map((k) => ({
        keyword: k.keyword,
        position: k.position,
        volume: k.search_volume,
        difficulty: difficultyFromScore(k.keyword_difficulty),
        cpc: k.cpc_usd,
      }));

      const socialTotal = platforms.reduce((sum, p) => sum + p.posts, 0) || 1;
      const social: SocialPlatform[] = platforms.map((p, i) => ({
        name: SOCIAL_PLATFORMS[i].name,
        posts: p.posts,
        pct: Math.round((p.posts / socialTotal) * 100),
        color: SOCIAL_PLATFORMS[i].color,
      }));

      const funnelStages = pipeline.pipeline.filter((s) => s.stage !== 'closed_lost');
      // Baseline off the largest stage, not the first (prospect can be 0
      // while later stages still have deals — using stage 0 as the
      // denominator would then produce >100% widths).
      const funnelBase = Math.max(...funnelStages.map((s) => s.count), 1);
      const funnel: FunnelStage[] = funnelStages.map((s) => ({
        stage: s.display,
        value: s.count.toLocaleString('en-US'),
        pct: Math.min(100, Math.max(6, Math.round((s.count / funnelBase) * 100))),
        rate: `$${Math.round(s.total_value).toLocaleString('en-US')}`,
        color: PIPELINE_COLORS[s.stage] ?? '#6b7385',
      }));

      const insights = buildInsights({
        keywords: organicKeywords.keywords,
        backlinks: backlinksSnapshot.total_backlinks,
        socialPosts30d: social30.overview.total_posts,
        socialPosts60d: social60.overview.total_posts,
        pipeline,
      });

      setData({
        domain,
        kpis,
        trend,
        trendDeltaPct,
        pipelineDonut,
        // total_pipeline_value already excludes closed_lost; subtract
        // closed_won too so this matches the donut's "open value" label.
        pipelineTotalValue: Math.max(0, pipeline.total_pipeline_value - pipeline.total_closed_won),
        keywords,
        social,
        funnel,
        insights,
        sources,
      });
      setUpdatedAt(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load marketing overview data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { data, loading, error, updatedAt, refresh: load };
}
