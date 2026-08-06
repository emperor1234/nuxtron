import AdvancedModulePage from '@/app/(dashboard)/seo/components/advanced-module-page';

export default function RetailMediaAppGrowthHubPage() {
  return (
    <AdvancedModulePage
      moduleKey="retail-media-app-growth-hub"
      eyebrow="Retail Media & App Growth"
      title="Retail Media & App Growth Hub"
      summary="A specialized operating module for Amazon retail media, Apple Search Ads, and app-growth measurement where keyword profitability, cohort revenue, catalog state, and marketplace-specific controls all need to work together."
      heroMetrics={[
        {
          label: 'Retail Focus',
          value: 'Amazon',
          hint: 'Product, brand, and search-term loops for retail media execution.',
        },
        {
          label: 'App Growth',
          value: 'Apple Search Ads',
          hint: 'Keyword and geo-aware acquisition control for app portfolios.',
        },
        {
          label: 'Measurement',
          value: 'Cohort-based',
          hint: 'Connect installs and marketplace traffic to downstream revenue.',
        },
        {
          label: 'Budget Split',
          value: 'Portfolio',
          hint: 'Allocate spend between marketplace and app growth tracks intentionally.',
        },
      ]}
      executionLanes={[
        'Sync catalog, ASIN, and marketplace metadata so campaign structures match the real product inventory state.',
        'Harvest search terms and profitability signals continuously to refine targeting, negatives, and bid pressure.',
        'Measure app campaigns beyond installs by connecting acquisition cohorts to retention and revenue quality.',
        'Separate retail media and app growth governance so each business line can move quickly without creating reporting chaos.',
      ]}
      operatingModel={[
        'Retail and app growth workflows share some mechanics, but they need different profit and cohort lenses.',
        'Marketplace APIs expose different dimensions than search networks, so normalization must be explicit.',
        'Budget allocation should respond to portfolio-level profitability, not just siloed channel metrics.',
      ]}
    />
  );
}
