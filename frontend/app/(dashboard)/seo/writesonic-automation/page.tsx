'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Project = { id: string; name: string; primary_domain: string };
type Run = { id: string; project_id: string; strict_probe_status: string; completed_at: string };

type ProjectsResponse = { status: string; projects: Project[] };
type RunsResponse = { status: string; runs: Run[] };

type Product = {
  key: string;
  name: string;
  description: string;
  premium_features: string[];
  vendors: string[];
  implemented?: boolean;
  e2e_verified?: boolean;
  production_grade_ready?: boolean;
};

type ProductsResponse = {
  status: string;
  tenant_id?: string;
  count: number;
  products: Product[];
  generated_at?: string;
};

type ProductDetailResponse = {
  status: string;
  tenant_id?: string;
  product: Product;
  generated_at?: string;
};

type GateResponse = {
  status: string;
  gate: { passed: boolean; blockers: string[] };
};

type FeatureRow = {
  key: string;
  feature: string;
  product: string;
  vendors: string[];
  production_grade_ready: boolean;
  automation_depth: string;
};

type FeatureResponse = {
  status: string;
  chart: FeatureRow[];
  summary: {
    features_total: number;
    features_implemented: number;
    features_e2e_verified: number;
    implementation_pct: number;
    e2e_verified_pct: number;
    integration_configured_pct: number;
    vendors_covered: number;
  };
};

type CompletionChartRow = {
  key: string;
  product: string;
  implemented: boolean;
  e2e_verified: boolean;
  integration_ready: boolean;
  production_grade_ready: boolean;
  premium_features_total: number;
  vendors: string[];
};

type CompletionChartResponse = {
  status: string;
  tenant_id?: string;
  chart: CompletionChartRow[];
  summary: {
    modules_total: number;
    modules_implemented: number;
    modules_e2e_verified: number;
    implementation_pct: number;
    e2e_verified_pct: number;
    integration_configured_pct: number;
    products_total: number;
    premium_features_total: number;
  };
  generated_at?: string;
};

type ParityAuditResponse = {
  status: string;
  tenant_id?: string;
  summary: {
    implementation_pct: number;
    integration_configured_pct: number;
    modules_total: number;
    modules_implemented: number;
  };
  writesonic_feature_chart: FeatureRow[];
  writesonic_parity_chart: CompletionChartRow[];
  vendor_inventory: Array<{
    domain: string;
    vendor: string;
    capability: string;
    configured: boolean;
    evidence: string;
  }>;
  generated_at?: string;
};

type VerificationResponse = {
  status: string;
  tenant_id?: string;
  verification: {
    slice_ready: boolean;
    slice_gate: {
      passed: boolean;
      blockers: string[];
    };
    evidence_table: CompletionChartRow[];
    feature_evidence_table: FeatureRow[];
    validation_boundaries: {
      validated_slice: string;
      not_validated: string[];
    };
  };
  generated_at?: string;
};

type FullAutomationResponse = {
  status: string;
  run_mode?: string;
  results?: {
    demand_and_prompt_intelligence?: Record<string, unknown>;
    long_form_content_pipeline?: Record<string, unknown>;
    authority_and_distribution_context?: Record<string, unknown>;
    prioritized_growth_actions?: Record<string, unknown>;
    parity_summary?: Record<string, unknown>;
  };
  writesonic_modules?: Record<string, string[]>;
  third_parties_and_vendors?: Array<{ vendor?: string }>;
  how_it_works?: string[];
  completion_summary?: {
    modules_total?: number;
    modules_implemented?: number;
    modules_e2e_verified?: number;
    implementation_pct?: number;
    e2e_verified_pct?: number;
    integration_configured_pct?: number;
    products_total?: number;
    premium_features_total?: number;
  };
  feature_registry_summary?: {
    features_total?: number;
    features_implemented?: number;
    features_e2e_verified?: number;
    implementation_pct?: number;
    e2e_verified_pct?: number;
    integration_configured_pct?: number;
    vendors_covered?: number;
  };
  feature_registry_chart?: FeatureRow[];
  production_gate?: {
    passed?: boolean;
    blockers?: string[];
  };
};

function ProjectRunSummarySection({
  projects,
  runs,
}: Readonly<{
  projects: Project[];
  runs: Run[];
}>) {
  const hasProjects = projects.length > 0;
  const hasRuns = runs.length > 0;

  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Projects</h3>
        {hasProjects ? (
          <ul className="bullet-list">
            {projects.slice(-8).map((project) => (
              <li key={project.id}>
                <strong>{project.name}</strong> ({project.primary_domain})
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ opacity: 0.8 }}>No projects yet.</p>
        )}
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Runs</h3>
        {hasRuns ? (
          <ul className="bullet-list">
            {runs.slice(-8).map((run) => (
              <li key={run.id}>
                <strong>{run.id}</strong> - strict probe: {run.strict_probe_status}
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ opacity: 0.8 }}>No runs yet.</p>
        )}
      </article>
    </section>
  );
}

function WritesonicProductCatalogSection({
  products,
  loading,
  selectedProductKey,
  onSelectProduct,
}: Readonly<{
  products: Product[];
  loading: boolean;
  selectedProductKey: string;
  onSelectProduct: (productKey: string) => void;
}>) {
  if (products.length === 0) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h3 style={{ marginTop: 0, marginBottom: 6 }}>Product Catalog</h3>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Full Writesonic product inventory with premium feature depth and vendor coverage.
          </p>
        </div>
        <p style={{ margin: 0, opacity: 0.8 }}>
          Catalog: <strong>{products.length}</strong> products
        </p>
      </div>
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', marginTop: 14 }}>
        {products.map((product) => (
          <button
            key={product.key}
            type="button"
            onClick={() => onSelectProduct(product.key)}
            disabled={loading}
            style={{
              textAlign: 'left',
              padding: 0,
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
            }}
          >
            <div
              className="card"
              style={{
                height: '100%',
                border: product.key === selectedProductKey ? '1px solid rgba(56, 189, 248, 0.8)' : undefined,
                boxShadow: product.key === selectedProductKey ? '0 0 0 1px rgba(56, 189, 248, 0.35)' : undefined,
              }}
            >
              <h4 style={{ marginTop: 0 }}>{product.name}</h4>
              <p style={{ opacity: 0.85 }}>{product.description}</p>
              <p style={{ marginBottom: 8, opacity: 0.85 }}>
                Premium features: <strong>{product.premium_features.length}</strong>
              </p>
              <p style={{ marginBottom: 0, opacity: 0.85 }}>Vendors: {product.vendors.join(', ')}</p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function WritesonicProductDetailSection({ selectedProduct }: Readonly<{ selectedProduct: ProductDetailResponse | null }>) {
  if (!selectedProduct) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>{selectedProduct.product.name} Detail</h3>
      <p style={{ opacity: 0.85 }}>{selectedProduct.product.description}</p>
      <p>
        Implemented: <strong>{selectedProduct.product.implemented ? 'Yes' : 'No'}</strong> | E2E verified:{' '}
        <strong>{selectedProduct.product.e2e_verified ? 'Yes' : 'No'}</strong> | Production grade:{' '}
        <strong>{selectedProduct.product.production_grade_ready ? 'Yes' : 'No'}</strong>
      </p>
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
        <div className="card">
          <h4 style={{ marginTop: 0 }}>Premium Features</h4>
          <ul className="bullet-list">
            {selectedProduct.product.premium_features.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h4 style={{ marginTop: 0 }}>Vendor Stack</h4>
          <ul className="bullet-list">
            {selectedProduct.product.vendors.map((vendor) => (
              <li key={vendor}>{vendor}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function WritesonicCompletionChartSection({ chart }: Readonly<{ chart: CompletionChartResponse | null }>) {
  if (!chart) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Product Completion Chart</h3>
      <p style={{ opacity: 0.85 }}>
        Products: <strong>{chart.summary.modules_implemented}/{chart.summary.modules_total}</strong> | E2E:{' '}
        <strong>{chart.summary.e2e_verified_pct}%</strong> | Integration:{' '}
        <strong>{chart.summary.integration_configured_pct}%</strong> | Premium features:{' '}
        <strong>{chart.summary.premium_features_total}</strong>
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Product</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Implemented</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>E2E Verified</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Production Grade</th>
              <th style={{ textAlign: 'left', padding: '8px 6px' }}>Premium Features</th>
            </tr>
          </thead>
          <tbody>
            {chart.chart.map((row) => (
              <tr key={row.key} style={{ borderTop: '1px solid rgba(148, 163, 184, 0.2)' }}>
                <td style={{ padding: '8px 6px' }}>{row.product}</td>
                <td style={{ padding: '8px 6px' }}>{row.implemented ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{row.e2e_verified ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{row.production_grade_ready ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 6px' }}>{row.premium_features_total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function WritesonicParityAuditSection({ parityAudit }: Readonly<{ parityAudit: ParityAuditResponse | null }>) {
  if (!parityAudit) return null;

  return (
    <section className="grid" style={{ marginTop: 20 }}>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Parity Coverage</h3>
        <p style={{ fontSize: 28, fontWeight: 700 }}>{parityAudit.summary.implementation_pct}%</p>
        <p style={{ opacity: 0.8 }}>implemented across the Writesonic slice</p>
      </article>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Integration Wiring</h3>
        <p style={{ fontSize: 28, fontWeight: 700 }}>{parityAudit.summary.integration_configured_pct}%</p>
        <p style={{ opacity: 0.8 }}>providers configured for the tenant</p>
      </article>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Vendor Inventory</h3>
        <p style={{ fontSize: 28, fontWeight: 700 }}>{parityAudit.vendor_inventory.length}</p>
        <p style={{ opacity: 0.8 }}>third-party references in the execution graph</p>
      </article>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Feature Registry</h3>
        <p style={{ fontSize: 28, fontWeight: 700 }}>{parityAudit.writesonic_feature_chart.length}</p>
        <p style={{ opacity: 0.8 }}>feature-level e2e evidence rows</p>
      </article>
    </section>
  );
}

function WritesonicVerificationReportSection({ verification }: Readonly<{ verification: VerificationResponse | null }>) {
  if (!verification) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Verification Report</h3>
      <p>
        Slice ready: <strong>{verification.verification.slice_ready ? 'Yes' : 'No'}</strong> | Gate:{' '}
        <strong>{verification.verification.slice_gate.passed ? 'PASSED' : 'FAILED'}</strong>
      </p>
      {verification.verification.slice_gate.blockers.length > 0 ? (
        <ul className="bullet-list">
          {verification.verification.slice_gate.blockers.map((blocker) => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}
      <h4>Validated Slice</h4>
      <p style={{ opacity: 0.85 }}>{verification.verification.validation_boundaries.validated_slice}</p>
      <h4>Not Validated</h4>
      <ul className="bullet-list">
        {verification.verification.validation_boundaries.not_validated.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <h4>Evidence Table</h4>
      <ul className="bullet-list">
        {verification.verification.evidence_table.slice(0, 7).map((row) => (
          <li key={row.key}>
            <strong>{row.product}</strong> - {row.premium_features_total} premium features, vendors: {row.vendors.join(', ')}
          </li>
        ))}
      </ul>
      <h4>Feature Evidence</h4>
      <ul className="bullet-list">
        {verification.verification.feature_evidence_table.slice(0, 7).map((row) => (
          <li key={row.key}>
            <strong>{row.feature}</strong> ({row.product}) - {row.automation_depth} automation
          </li>
        ))}
      </ul>
    </section>
  );
}

function WritesonicFeatureRegistrySection({ features }: Readonly<{ features: FeatureResponse | null }>) {
  if (!features) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Feature Completion Chart</h3>
      <p>
        Features: <strong>{features.summary.features_implemented}/{features.summary.features_total}</strong> | E2E:{' '}
        <strong>{features.summary.e2e_verified_pct}%</strong> | Integration:{' '}
        <strong>{features.summary.integration_configured_pct}%</strong> | Vendors covered:{' '}
        <strong>{features.summary.vendors_covered}</strong>
      </p>
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))' }}>
        {features.chart.slice(0, 18).map((row) => (
          <div key={row.key} className="card">
            <h4 style={{ marginTop: 0 }}>{row.feature}</h4>
            <p style={{ marginBottom: 8, opacity: 0.85 }}>
              Product: <strong>{row.product}</strong>
            </p>
            <p style={{ marginBottom: 8, opacity: 0.85 }}>
              Automation depth: <strong>{row.automation_depth}</strong>
            </p>
            <p style={{ marginBottom: 0, opacity: 0.85 }}>Vendors: {row.vendors.join(', ')}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function WritesonicBlueprintSection({ automation }: Readonly<{ automation: FullAutomationResponse | null }>) {
  if (!automation) return null;

  return (
    <section className="card" style={{ marginTop: 20 }}>
      <h3 style={{ marginTop: 0 }}>Automation Blueprint</h3>
      <p>
        Run mode: <strong>{automation.run_mode ?? 'n/a'}</strong> | Vendors referenced:{' '}
        <strong>{automation.third_parties_and_vendors?.length ?? 0}</strong>
      </p>
      {automation.results ? (
        <>
          <h4>Execution Results</h4>
          <ul className="bullet-list">
            <li>
              Demand and prompt intelligence: {Object.keys(automation.results.demand_and_prompt_intelligence ?? {}).length} fields
            </li>
            <li>
              Long form content pipeline: {Object.keys(automation.results.long_form_content_pipeline ?? {}).length} fields
            </li>
            <li>
              Authority and distribution context: {Object.keys(automation.results.authority_and_distribution_context ?? {}).length} fields
            </li>
            <li>
              Prioritized growth actions: {Object.keys(automation.results.prioritized_growth_actions ?? {}).length} fields
            </li>
          </ul>
        </>
      ) : null}
      {automation.completion_summary ? (
        <p style={{ opacity: 0.85 }}>
          Completion: {automation.completion_summary.modules_implemented ?? 0}/{automation.completion_summary.modules_total ?? 0} modules,
          {' '}
          {automation.completion_summary.integration_configured_pct ?? 0}% integration ready.
        </p>
      ) : null}
      {automation.feature_registry_summary ? (
        <p style={{ opacity: 0.85 }}>
          Feature registry: {automation.feature_registry_summary.features_implemented ?? 0}/
          {automation.feature_registry_summary.features_total ?? 0} features, {automation.feature_registry_summary.vendors_covered ?? 0} vendors covered.
        </p>
      ) : null}
      {automation.how_it_works?.length ? (
        <>
          <h4>How It Works</h4>
          <ul className="bullet-list">
            {automation.how_it_works.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
      {automation.writesonic_modules ? (
        <>
          <h4>Module Coverage</h4>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
            {Object.entries(automation.writesonic_modules).map(([name, items]) => (
              <div key={name} className="card">
                <h5 style={{ marginTop: 0, textTransform: 'capitalize' }}>{name}</h5>
                <ul className="bullet-list">
                  {items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </>
      ) : null}
      {automation.third_parties_and_vendors?.length ? (
        <>
          <h4>Third Parties And Vendors</h4>
          <ul className="bullet-list">
            {automation.third_parties_and_vendors.map((vendor, index) => (
              <li key={`${vendor.vendor ?? 'vendor'}-${index}`}>{vendor.vendor ?? 'unknown vendor'}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

export default function WritesonicAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [gate, setGate] = useState<GateResponse | null>(null);
  const [features, setFeatures] = useState<FeatureResponse | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [completionChart, setCompletionChart] = useState<CompletionChartResponse | null>(null);
  const [parityAudit, setParityAudit] = useState<ParityAuditResponse | null>(null);
  const [verification, setVerification] = useState<VerificationResponse | null>(null);
  const [selectedProductKey, setSelectedProductKey] = useState('chatsonic');
  const [selectedProduct, setSelectedProduct] = useState<ProductDetailResponse | null>(null);
  const [automation, setAutomation] = useState<FullAutomationResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [projectData, runData, gateData, featureData, productData, completionData, parityData, verificationData] =
        await Promise.all([
        apiGet<ProjectsResponse>('/search-everywhere/writesonic/projects', tenantId),
        apiGet<RunsResponse>('/search-everywhere/writesonic/runs', tenantId),
        apiGet<GateResponse>('/search-everywhere/writesonic/production-gate', tenantId),
        apiGet<FeatureResponse>('/search-everywhere/writesonic/features', tenantId),
        apiGet<ProductsResponse>('/search-everywhere/writesonic/products', tenantId),
        apiGet<CompletionChartResponse>('/search-everywhere/writesonic/products/completion-chart', tenantId),
        apiGet<ParityAuditResponse>('/search-everywhere/writesonic/parity-audit', tenantId),
        apiGet<VerificationResponse>('/search-everywhere/writesonic/verification-report', tenantId),
      ]);
      setProjects(projectData.projects || []);
      setRuns(runData.runs || []);
      setGate(gateData);
      setFeatures(featureData);
      setProducts(productData.products || []);
      setCompletionChart(completionData);
      setParityAudit(parityData);
      setVerification(verificationData);
      const productDetail = await apiGet<ProductDetailResponse>(
        `/search-everywhere/writesonic/products/detail/${selectedProductKey}`,
        tenantId
      );
      setSelectedProduct(productDetail);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Writesonic automation state');
    } finally {
      setLoading(false);
    }
  }

  async function loadProductDetail(productKey: string) {
    setLoading(true);
    setError('');
    try {
      setSelectedProductKey(productKey);
      const detail = await apiGet<ProductDetailResponse>(`/search-everywhere/writesonic/products/detail/${productKey}`, tenantId);
      setSelectedProduct(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load product detail');
    } finally {
      setLoading(false);
    }
  }

  async function createDemoProject() {
    setLoading(true);
    setError('');
    try {
      await apiSend(
        '/search-everywhere/writesonic/projects',
        'POST',
        {
          name: 'Writesonic Automation Project',
          primary_domain: 'nuxtron.ai',
          crawl_urls: ['https://nuxtron.ai', 'https://nuxtron.ai/blog'],
          competitor_domains: ['writesonic.com', 'jasper.ai'],
          max_urls: 10000,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
      setLoading(false);
    }
  }

  async function runLatestProject() {
    if (!projects.length) {
      setError('Create a Writesonic project first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const projectId = projects.at(-1)?.id;
      await apiSend(
        `/search-everywhere/writesonic/projects/${projectId}/run`,
        'POST',
        {
          seed_keyword: 'ai content automation',
          competitor_domains: ['writesonic.com', 'jasper.ai'],
          max_results: 12,
          require_live_providers: false,
        },
        tenantId
      );
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run project');
      setLoading(false);
    }
  }

  async function runFullBlueprint() {
    setLoading(true);
    setError('');
    try {
      const result = await apiSend<FullAutomationResponse>(
        '/search-everywhere/writesonic/full-automation',
        'POST',
        {
          seed_keyword: 'ai content automation',
          your_domain: 'nuxtron.ai',
          competitor_domains: ['writesonic.com', 'jasper.ai'],
          max_results: 12,
          require_live_providers: false,
        },
        tenantId
      );
      setAutomation(result);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Writesonic automation blueprint');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Writesonic Automation</p>
        <h1>Writesonic Run And Product Control</h1>
        <p>
          Manage projects, execution runs, and product blueprints from the same API surface exposed by the backend
          Writesonic automation suite.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshAll()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button onClick={() => void createDemoProject()} disabled={loading}>
            {loading ? 'Working...' : 'Create Demo Project'}
          </button>
          <button onClick={() => void runLatestProject()} disabled={loading}>
            {loading ? 'Running...' : 'Run Latest Project'}
          </button>
          <button onClick={() => void runFullBlueprint()} disabled={loading}>
            {loading ? 'Executing...' : 'Run Full Automation Blueprint'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      <ProjectRunSummarySection projects={projects} runs={runs} />
      <WritesonicProductCatalogSection
        products={products}
        loading={loading}
        selectedProductKey={selectedProductKey}
        onSelectProduct={(productKey) => void loadProductDetail(productKey)}
      />
      <WritesonicProductDetailSection selectedProduct={selectedProduct} />
      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate Snapshot</h3>
          <p>
            Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          {gate.gate.passed ? null : (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
      <WritesonicCompletionChartSection chart={completionChart} />
      <WritesonicParityAuditSection parityAudit={parityAudit} />
      <WritesonicVerificationReportSection verification={verification} />
      <WritesonicFeatureRegistrySection features={features} />
      <WritesonicBlueprintSection automation={automation} />
    </main>
  );
}
