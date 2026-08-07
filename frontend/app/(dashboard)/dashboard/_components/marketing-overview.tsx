'use client';

import styles from '../dashboard.module.css';
import { useMarketingOverview } from '../_data/use-marketing-overview';
import PageHeader from './page-header';
import KpiRow from './kpi-row';
import TrafficTrendCard from './traffic-trend-card';
import PipelineDonut from './traffic-sources-donut';
import TopKeywordsCard from './top-keywords-card';
import SocialEngagementCard from './social-engagement-card';
import ConversionFunnelCard from './conversion-funnel-card';
import AiInsightsCard from './ai-insights-card';

type MarketingOverviewProps = {
  className?: string;
};

function formatUpdatedLabel(updatedAt: number | null, loading: boolean): string {
  if (loading && !updatedAt) return 'Loading…';
  if (!updatedAt) return 'Not yet loaded';
  const seconds = Math.max(0, Math.round((Date.now() - updatedAt) / 1000));
  if (seconds < 5) return 'Updated just now';
  if (seconds < 60) return `Updated ${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return `Updated ${minutes} min ago`;
}

/**
 * Marketing Overview — composes the dashboard sections around live data
 * fetched from the domain-overview, CRM pipeline, and social analytics APIs.
 * Client component: the whole page depends on tenant-scoped fetches.
 */
function exportData(data: NonNullable<ReturnType<typeof useMarketingOverview>['data']>) {
  const blob = new Blob([JSON.stringify(data, (_key, value) => (value instanceof Set ? Array.from(value) : value), 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `marketing-overview-${data.domain}-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  // Defer revocation past the current task: some browsers haven't finished
  // consuming the object URL for the download by the time click() returns,
  // and revoking synchronously can intermittently cancel it.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function MarketingOverview({ className }: MarketingOverviewProps) {
  const { data, loading, error, updatedAt, refresh } = useMarketingOverview();

  return (
    <div className={`${styles.root}${className ? ` ${className}` : ''}`}>
      <PageHeader
        title="Marketing Overview"
        domain={data?.domain ?? '—'}
        scope="Worldwide"
        updatedLabel={formatUpdatedLabel(updatedAt, loading)}
        sourceLabel={data ? Array.from(data.sources).join(', ') : undefined}
        onRefresh={refresh}
        refreshing={loading}
        onExport={data ? () => exportData(data) : undefined}
      />

      {error ? (
        <div className={styles.errorBanner} role="alert">
          {error}
          <button type="button" className={styles.errorRetry} onClick={() => void refresh()}>
            Retry
          </button>
        </div>
      ) : null}

      {!data ? (
        <div className={`${styles.card} ${styles.cardPad}`}>
          <p className="muted">{loading ? 'Loading live marketing data…' : 'No data available.'}</p>
        </div>
      ) : (
        <>
          <KpiRow kpis={data.kpis} />

          <section className={styles.gridTrend} aria-label="Traffic trend and pipeline mix">
            <TrafficTrendCard trend={data.trend} deltaPct={data.trendDeltaPct} />
            <PipelineDonut segments={data.pipelineDonut} totalValue={data.pipelineTotalValue} />
          </section>

          <section className={styles.gridKeywords} aria-label="Keywords and social publishing">
            <TopKeywordsCard keywords={data.keywords} />
            <SocialEngagementCard platforms={data.social} />
          </section>

          <section className={styles.gridFunnel} aria-label="Deal funnel and marketing insights">
            <ConversionFunnelCard funnel={data.funnel} />
            <AiInsightsCard insights={data.insights} />
          </section>
        </>
      )}
    </div>
  );
}
