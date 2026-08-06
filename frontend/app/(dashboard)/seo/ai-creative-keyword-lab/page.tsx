import AdvancedModulePage from '@/app/(dashboard)/seo/components/advanced-module-page';

export default function AiCreativeKeywordLabPage() {
  return (
    <AdvancedModulePage
      moduleKey="ai-creative-keyword-lab"
      eyebrow="AI Optimization Workspace"
      title="AI Creative & Keyword Lab"
      summary="A controlled AI workspace for generating ad copy, keyword clusters, negative-keyword sets, landing-page angles, and experiment-ready creative variants with operator approval and performance lineage."
      heroMetrics={[
        {
          label: 'Generation Scope',
          value: 'Copy + Keywords',
          hint: 'Supports creative, keyword, and landing-angle iteration in one loop.',
        },
        {
          label: 'Model Strategy',
          value: 'Multi-model',
          hint: 'Blend instruction, reasoning, and embedding models by task type.',
        },
        {
          label: 'Approval Mode',
          value: 'Human-gated',
          hint: 'Brand and policy review stay in the loop before publication.',
        },
        {
          label: 'Experiment Readiness',
          value: 'Built-in',
          hint: 'Outputs are structured for testing, not just ideation.',
        },
      ]}
      executionLanes={[
        'Generate channel-aware ad variants and keyword expansions aligned to audience intent and landing context.',
        'Mine negative keywords and thematic clusters using embeddings so campaign hygiene improves as scale grows.',
        'Track prompt, model, output, and performance lineage to learn which creative systems actually win.',
        'Constrain the workspace with brand, safety, and editorial rules so operators can trust generated outputs.',
      ]}
      operatingModel={[
        'Creative generation is a decision-support layer, not an excuse to skip human review or policy checks.',
        'Prompt registries and performance lineage matter more than raw generation volume.',
        'The best AI workflow is one that improves campaign velocity without destroying brand consistency.',
      ]}
    />
  );
}
