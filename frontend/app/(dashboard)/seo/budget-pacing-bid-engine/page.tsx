import AdvancedModulePage from '@/app/(dashboard)/seo/components/advanced-module-page';

export default function BudgetPacingBidEnginePage() {
  return (
    <AdvancedModulePage
      moduleKey="budget-pacing-bid-engine"
      eyebrow="Automation Engine"
      title="Budget Pacing & Bid Engine"
      summary="A rule-driven and model-assisted execution layer for pacing budgets, controlling bid pressure, and protecting ROAS across volatile campaign conditions. This is where the control tower turns reporting into action."
      heroMetrics={[
        {
          label: 'Primary Inputs',
          value: 'CTR / CPA / ROAS',
          hint: 'Decisioning uses delivery, efficiency, and profitability signals together.',
        },
        {
          label: 'Pacing Window',
          value: 'Intra-day',
          hint: 'Track spend against hourly targets instead of waiting for end-of-day surprises.',
        },
        {
          label: 'Actuation',
          value: 'Rule + ML',
          hint: 'Blend deterministic guardrails with model-assisted recommendations.',
        },
        {
          label: 'Controls',
          value: 'Thresholded',
          hint: 'High-risk changes can escalate to approval instead of firing blindly.',
        },
      ]}
      executionLanes={[
        'Monitor delivery pace against daily and intra-day budget envelopes to prevent early burn or under-delivery.',
        'Pause or repair weak entities when CTR collapses, quality decays, or conversion economics move outside tolerated bands.',
        'Apply daypart and seasonality logic so budget intent survives predictable traffic swings and promotional windows.',
        'Record bid-change impact so the engine becomes explainable instead of behaving like an opaque black box.',
      ]}
      operatingModel={[
        'Guardrails are mandatory: never let model-driven suggestions bypass budget, risk, or approval policies.',
        'Realtime loops need resilient caches and queues because platform APIs do not all refresh at the same cadence.',
        'Performance recommendations are only useful when every change can be traced back to the trigger condition that caused it.',
      ]}
    />
  );
}
