import AdvancedModulePage from '@/app/(dashboard)/seo/components/advanced-module-page';

export default function AttributionConversionIntelligencePage() {
  return (
    <AdvancedModulePage
      moduleKey="attribution-conversion-intelligence"
      eyebrow="Attribution Fabric"
      title="Attribution & Conversion Intelligence"
      summary="A server-side measurement and attribution layer that unifies paid media, organic assists, CRM outcomes, and revenue signals into decision-grade reporting. It does not pretend attribution is perfect; it makes it operationally useful."
      heroMetrics={[
        {
          label: 'Tracking Mode',
          value: 'Server-side',
          hint: 'Designed for post-cookie measurement resilience and cleaner event quality.',
        },
        {
          label: 'Attribution Lens',
          value: 'Multi-touch',
          hint: 'Support assisted conversion analysis instead of only last-click reporting.',
        },
        {
          label: 'Revenue Join',
          value: 'Online + Offline',
          hint: 'Bridge ad spend to CRM and downstream revenue events.',
        },
        {
          label: 'Warehouse Ready',
          value: 'Yes',
          hint: 'Structured for PostgreSQL, BigQuery, and long-horizon analytics workloads.',
        },
      ]}
      executionLanes={[
        'Capture and deduplicate conversion events from multiple entry points without overstating performance.',
        'Resolve identity carefully enough to support reporting, while respecting consent and regional privacy requirements.',
        'Refresh attribution models on a controlled schedule so finance, growth, and campaign operations share the same logic.',
        'Expose transparent metric definitions and lineage so operators can defend numbers in client, finance, and audit contexts.',
      ]}
      operatingModel={[
        'Attribution should be presented as a model with assumptions, not as absolute truth.',
        'Identity resolution must remain bounded by privacy posture, consent state, and regional compliance rules.',
        'Reporting marts should normalize network-specific quirks before they reach executive dashboards.',
      ]}
    />
  );
}
