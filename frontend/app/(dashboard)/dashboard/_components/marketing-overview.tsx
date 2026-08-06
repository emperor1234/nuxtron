import styles from '../dashboard.module.css';
import PageHeader from './page-header';
import KpiRow from './kpi-row';
import TrafficTrendCard from './traffic-trend-card';
import TrafficSourcesDonut from './traffic-sources-donut';
import TopKeywordsCard from './top-keywords-card';
import SocialEngagementCard from './social-engagement-card';
import ConversionFunnelCard from './conversion-funnel-card';
import AiInsightsCard from './ai-insights-card';

type MarketingOverviewProps = {
  className?: string;
};

/**
 * Marketing Overview — composes the dashboard sections into the reference
 * layout. Server component: only the trend tabs and KPI count-ups opt into
 * client interactivity, keeping the initial payload light.
 */
export default function MarketingOverview({ className }: MarketingOverviewProps) {
  return (
    <div className={`${styles.root}${className ? ` ${className}` : ''}`}>
      <PageHeader title="Marketing Overview" domain="nuxtron.io" scope="Worldwide" updatedLabel="Updated 4 min ago" />

      <KpiRow />

      <section className={styles.gridTrend} aria-label="Traffic trend and sources">
        <TrafficTrendCard />
        <TrafficSourcesDonut />
      </section>

      <section className={styles.gridKeywords} aria-label="Keywords and social engagement">
        <TopKeywordsCard />
        <SocialEngagementCard />
      </section>

      <section className={styles.gridFunnel} aria-label="Conversion funnel and AI insights">
        <ConversionFunnelCard />
        <AiInsightsCard />
      </section>
    </div>
  );
}
