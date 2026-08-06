import {
  FINAL_HYBRID_SUMMARY,
  type HybridSummaryRow,
  type OpenSourceHybridStack,
  OPEN_SOURCE_HYBRID_STACKS,
} from '../hybrid-stacks';

type ProductionReadinessCheck = {
  id: string;
  label: string;
  ready: boolean;
};

type Props = Readonly<{
  productionReadinessChecks: ProductionReadinessCheck[];
  recommendation?: {
    hybrid: string;
    score: string;
    benefits: string[];
    positioning: string;
  };
  stacks?: OpenSourceHybridStack[];
  summary?: HybridSummaryRow[];
}>;

export default function PlatformHybridStackSections({
  productionReadinessChecks,
  recommendation,
  stacks,
  summary,
}: Props) {
  const defaultRecommendation = {
    hybrid: 'OpenLens (Free) + Promptwatch (Paid)',
    score: '100/100 (100%)',
    benefits: [
      'Multi-LLM monitoring (OpenLens)',
      'Full optimisation workflows (Promptwatch)',
      'Crawler logs (Promptwatch)',
      'Visitor analytics (Promptwatch)',
      'Zero monitoring cost (OpenLens)',
      'Lowest possible full-stack spend',
    ],
    positioning: 'This is the only configuration that gives complete GEO + LLMO coverage at the lowest cost.',
  };

  const resolvedRecommendation = recommendation
    ? {
        hybrid: recommendation.hybrid || defaultRecommendation.hybrid,
        score: recommendation.score || defaultRecommendation.score,
        benefits: recommendation.benefits.length > 0 ? recommendation.benefits : defaultRecommendation.benefits,
        positioning: recommendation.positioning || defaultRecommendation.positioning,
      }
    : defaultRecommendation;

  const resolvedStacks = stacks || OPEN_SOURCE_HYBRID_STACKS;
  const resolvedSummary = summary || FINAL_HYBRID_SUMMARY;
  const categoryNameByCode = new Map(
    resolvedStacks.map((stack) => {
      const code = stack.category.split(' (')[0];
      return [code, stack.category];
    })
  );

  return (
    <>
      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Hybrid GEO + LLMO Stack Recommendation</h3>
        <p className="muted">Hybrid = {resolvedRecommendation.hybrid}</p>
        <div className="platform-feature-grid" style={{ marginTop: 12 }}>
          <article className="platform-feature-card">
            <h4>This gives you</h4>
            <ul className="bullet-list">
              {resolvedRecommendation.benefits.map((benefit) => (
                <li key={benefit}>{benefit}</li>
              ))}
            </ul>
          </article>

          <article className="platform-feature-card">
            <h4>Hybrid Rating</h4>
            <ul className="bullet-list">
              <li>
                <span>Score</span>
                <strong className="platform-ready">{resolvedRecommendation.score}</strong>
              </li>
              <li>{resolvedRecommendation.positioning}</li>
            </ul>
          </article>
        </div>
      </section>

      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Production Readiness Wiring</h3>
        <p className="muted">
          Live readiness checks wired to platform telemetry. Use this gate before promoting stack changes.
        </p>
        <div className="platform-feature-grid" style={{ marginTop: 12 }}>
          {productionReadinessChecks.map((check) => (
            <article key={check.id} className="platform-feature-card">
              <h4>{check.label}</h4>
              <strong className={check.ready ? 'platform-ready' : 'platform-degraded'}>
                {check.ready ? 'Ready' : 'Action required'}
              </strong>
            </article>
          ))}
        </div>
      </section>

      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>100/100 Hybrid Stacks (Free + Open-Source Only)</h3>
        <p className="muted">
          Build 100/100 hybrid stacks using only free and open-source tools across SEO-AI, GEO, AIO-2, LLMO, SAGEO, VSO,
          SXO, GXO, Entity-First SEO, PEAO, MSVO, DAEO, CXAO, E-E-A-T, Autonomous Agent Engine, Programmatic SEO, SEO
          A/B Testing, Ecommerce SEO, Autonomous Link Building, International & Multilingual SEO, Site Migration SEO,
          Video SEO, Local SEO, News SEO & Google Discover, Analytics, Reporting & Intelligence, Agency & Multi-Tenant
          Platform, and Integrations & Automation Layer.
        </p>
        <div className="platform-feature-grid" style={{ marginTop: 12 }}>
          {resolvedStacks.map((stack) => (
            <article key={stack.id} className="platform-feature-card">
              <h4>{stack.category}</h4>
              <p className="muted">Goal: {stack.goal}</p>
              <p className="muted">Constraint: {stack.constraint}</p>
              <ul className="bullet-list">
                <li>
                  <span>Hybrid stack</span>
                  <strong>{stack.hybridStack}</strong>
                </li>
                <li>
                  <span>Hybrid score</span>
                  <strong className="platform-ready">{stack.hybridScore}</strong>
                </li>
              </ul>
              <h4 style={{ marginTop: 10 }}>Best Free Tools</h4>
              <ul className="bullet-list">
                {stack.freeTools.map((tool) => (
                  <li key={`${stack.id}-free-${tool.name}`}>
                    <span>{tool.name}</span>
                    <strong>{tool.score}/100</strong>
                  </li>
                ))}
              </ul>
              <h4 style={{ marginTop: 10 }}>Best Open-Source Tools</h4>
              <ul className="bullet-list">
                {stack.openSourceTools.map((tool) => (
                  <li key={`${stack.id}-oss-${tool.name}`}>
                    <span>{tool.name}</span>
                    <strong>{tool.score}/100</strong>
                  </li>
                ))}
              </ul>
              <h4 style={{ marginTop: 10 }}>Coverage outcomes</h4>
              <ul className="bullet-list">
                {stack.outcomes.map((outcome) => (
                  <li key={`${stack.id}-outcome-${outcome}`}>{outcome}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Final Summary: 100/100 Hybrid Stacks</h3>
        <div className="platform-integration-grid" style={{ marginTop: 12 }}>
          {resolvedSummary.map((row) => (
            <article key={row.category} className="platform-integration-item">
              <span>{row.category}</span>
              <span>{row.stack}</span>
              <strong className="platform-ready">{row.score}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>All Categories Table</h3>
        <p className="muted">Compact view of the free/open-source hybrid stack catalog and coverage.</p>
        <div style={{ marginTop: 12, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>Code</th>
                <th style={{ textAlign: 'left', padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>
                  Hybrid Stack
                </th>
                <th style={{ textAlign: 'left', padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>
                  Coverage
                </th>
              </tr>
            </thead>
            <tbody>
              {resolvedSummary.map((row) => (
                <tr key={`table-${row.category}`}>
                  <td style={{ padding: '10px 8px', borderBottom: '1px solid var(--line)', fontWeight: 700 }}>
                    {row.category}
                  </td>
                  <td style={{ padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>
                    {categoryNameByCode.get(row.category) || row.category}
                  </td>
                  <td style={{ padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>{row.stack}</td>
                  <td style={{ padding: '10px 8px', borderBottom: '1px solid var(--line)' }}>
                    <strong className="platform-ready">{row.score}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
