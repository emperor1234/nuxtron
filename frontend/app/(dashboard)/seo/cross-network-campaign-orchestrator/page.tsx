import AdvancedModulePage from '@/app/(dashboard)/seo/components/advanced-module-page';

export default function CrossNetworkCampaignOrchestratorPage() {
  return (
    <AdvancedModulePage
      moduleKey="cross-network-campaign-orchestrator"
      eyebrow="Campaign Orchestration"
      title="Cross-Network Campaign Orchestrator"
      summary="An advanced synchronization engine for distributing campaign structures, targeting, creative variants, and budget policies across multiple ad networks without turning operations into spreadsheet-driven chaos."
      heroMetrics={[
        {
          label: 'Sync Model',
          value: 'Bi-dir',
          hint: 'Push planned state outbound and compare live state inbound for drift control.',
        },
        {
          label: 'Rollback',
          value: 'Safe',
          hint: 'Failed sync waves can be retried or rolled back with operator visibility.',
        },
        {
          label: 'Templates',
          value: 'Market-aware',
          hint: 'Regional campaign cloning with audience and landing-page adaptations.',
        },
        {
          label: 'Queue Fabric',
          value: 'Async',
          hint: 'Connector jobs run through worker queues to absorb API variability.',
        },
      ]}
      executionLanes={[
        'Clone market-specific campaign blueprints from a shared template registry rather than rebuilding manually per network.',
        'Translate budget, targeting, and creative settings into each network’s object model while preserving a shared business intent.',
        'Detect sync collisions, stale campaign structures, or partial API failures and route them into retry and approval queues.',
        'Generate an operator-readable execution timeline so agencies can explain every mutation and rollback action.',
      ]}
      operatingModel={[
        'Campaign templates should be versioned assets, not ad hoc config blobs buried in code or spreadsheets.',
        'Connector abstractions must isolate network-specific quirks so rollout logic remains reusable across platforms.',
        'Every bulk mutation should emit auditable events for compliance, troubleshooting, and client-facing reporting.',
      ]}
    />
  );
}
