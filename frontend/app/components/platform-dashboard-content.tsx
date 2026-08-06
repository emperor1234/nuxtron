import Link from 'next/link';

import InstitutionalAiWidgets from './institutional-ai-widgets';
import PlatformHybridStackSections from '@/app/(dashboard)/platform/components/platform-hybrid-stack-sections';

type QueueRow = {
  name: string;
  value: number;
  width: number;
};

type IntegrationRow = {
  key: string;
  ready: boolean;
};

type TrendRow = {
  id: string;
  label: string;
  value: string;
};

type SnapshotHistoryItem = {
  id: number;
  generated_at: string;
  integrations_ready: number;
  integrations_total: number;
  queue_total_events: number;
};

type CapabilityFeature = {
  id: string;
  name: string;
  ready: boolean;
};

type CapabilityCategory = {
  id: string;
  name: string;
  features: CapabilityFeature[];
};

type GrowthSuiteFeature = {
  key: string;
  name: string;
  status: string;
  headline: string;
  metrics: { label: string; value: string | number | boolean }[];
};

type ProductionReadinessCheck = {
  id: string;
  label: string;
  ready: boolean;
};

type HybridRecommendation = {
  hybrid: string;
  score: string;
  benefits: string[];
  positioning: string;
};

type HybridTool = {
  name: string;
  score: number;
  capabilities: string[];
};

type HybridStack = {
  id: string;
  category: string;
  goal: string;
  constraint: string;
  freeTools: HybridTool[];
  openSourceTools: HybridTool[];
  hybridStack: string;
  outcomes: string[];
  hybridScore: string;
};

type HybridSummary = {
  category: string;
  stack: string;
  score: string;
};

type Props = Readonly<{
  status: {
    db_ready?: boolean;
    fallback_buffers?: { any_buffer_hot?: boolean };
  } | null;
  coverage: { coverage_percent?: number } | null;
  metrics: { rate_limiter: { active_keys: number } } | null;
  antiFailure: { summary: { healthy_count: number; total: number } } | null;
  capabilities: { totals: { features: number }; categories: CapabilityCategory[] } | null;
  attribution: {
    totals: {
      attributed_revenue: number;
      revenue: number;
      tracked_conversions: number;
      unattributed_revenue: number;
    };
    top_posts: { post_id: string; attributed_revenue: number }[];
    channels: { channel: string; attributed_revenue: number }[];
  } | null;
  growthSuite: { totals: { configured: number; features: number }; features: GrowthSuiteFeature[] } | null;
  systemOverview: {
    generated_at?: string;
    frontend: { runtime?: string; status?: string; site_url?: string };
    backend: { runtime?: string; status?: string; environment?: string; rate_limiter_active_keys?: number };
    database: { db_ready?: boolean; status?: string; engine?: string };
    security: { strict_mode?: boolean; vault_configured?: boolean };
    integrations: { ready: number; total: number };
    queues: { active_queues: number; total_events: number };
    capabilities: { features_ready_estimate: number; features_total: number };
  } | null;
  systemHistory: { items: SnapshotHistoryItem[] } | null;
  queueRows: QueueRow[];
  integrationRows: IntegrationRow[];
  queueTrendRows: TrendRow[];
  integrationTrendRows: TrendRow[];
  coverageTrendRows: TrendRow[];
  generatedTrackedUrl: string;
  isGeneratingTrackedUrl: boolean;
  isBootstrappingGrowthSuite: boolean;
  touchpointPostId: string;
  touchpointPlatform: string;
  touchpointCampaign: string;
  touchpointUrl: string;
  productionReadinessChecks: ProductionReadinessCheck[];
  hybridRecommendation?: HybridRecommendation;
  hybridStacks?: HybridStack[];
  hybridSummary?: HybridSummary[];
  setTouchpointPostId: (value: string) => void;
  setTouchpointPlatform: (value: string) => void;
  setTouchpointCampaign: (value: string) => void;
  setTouchpointUrl: (value: string) => void;
  onGenerateTrackedLink: () => void;
  onBootstrapGrowthSuite: () => void;
  onCaptureSystemSnapshot: () => void;
}>;

type KpiGridProps = Pick<
  Props,
  'status' | 'coverage' | 'metrics' | 'antiFailure' | 'capabilities' | 'attribution' | 'growthSuite'
>;

type RuntimeOverviewProps = Pick<Props, 'systemOverview' | 'onCaptureSystemSnapshot'>;
type RuntimeTrajectoryProps = Pick<
  Props,
  'queueTrendRows' | 'integrationTrendRows' | 'coverageTrendRows' | 'systemHistory'
>;
type QueueAndCapabilityProps = Pick<Props, 'queueRows' | 'capabilities' | 'integrationRows'>;
type RevenueAttributionProps = Pick<
  Props,
  | 'attribution'
  | 'generatedTrackedUrl'
  | 'isGeneratingTrackedUrl'
  | 'touchpointPostId'
  | 'touchpointPlatform'
  | 'touchpointCampaign'
  | 'touchpointUrl'
  | 'setTouchpointPostId'
  | 'setTouchpointPlatform'
  | 'setTouchpointCampaign'
  | 'setTouchpointUrl'
  | 'onGenerateTrackedLink'
>;
type GrowthSuiteProps = Pick<Props, 'growthSuite' | 'isBootstrappingGrowthSuite' | 'onBootstrapGrowthSuite'>;

function KpiGrid({ status, coverage, metrics, antiFailure, capabilities, attribution, growthSuite }: KpiGridProps) {
  return (
    <section className="grid dashboard-kpis" style={{ marginTop: 20 }}>
      <article className="card kpi-card">
        <p className="kpi-label">Database</p>
        <h3>{status?.db_ready ? 'Ready' : 'Fallback mode'}</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Use-case coverage</p>
        <h3>{coverage?.coverage_percent ?? 0}%</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Anti-failure systems</p>
        <h3>
          {antiFailure?.summary.healthy_count ?? 0}/{antiFailure?.summary.total ?? 0}
        </h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Feature modules</p>
        <h3>{capabilities?.totals.features ?? 0}</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Rate keys</p>
        <h3>{metrics?.rate_limiter.active_keys ?? 0}</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Attributed revenue</p>
        <h3>${(attribution?.totals.attributed_revenue ?? 0).toFixed(2)}</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Hot buffers</p>
        <h3>{status?.fallback_buffers?.any_buffer_hot ? 'Attention needed' : 'Healthy'}</h3>
      </article>
      <article className="card kpi-card">
        <p className="kpi-label">Growth suite</p>
        <h3>
          {growthSuite?.totals.configured ?? 0}/{growthSuite?.totals.features ?? 0}
        </h3>
      </article>
    </section>
  );
}

function RuntimeOverviewSection({ systemOverview, onCaptureSystemSnapshot }: RuntimeOverviewProps) {
  return (
    <section className="card dashboard-chart" style={{ marginTop: 20 }}>
      <div className="platform-controls" style={{ marginBottom: 12 }}>
        <div>
          <h3>Full-Stack Runtime Overview</h3>
          <p className="muted">
            Unified health model across frontend, backend, and database with live readiness, queue pressure, and
            integration posture.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button type="button" className="cta-link" onClick={onCaptureSystemSnapshot}>
            Capture Snapshot
          </button>
          <span className="platform-last-updated">
            Snapshot:{' '}
            {systemOverview?.generated_at ? new Date(systemOverview.generated_at).toLocaleTimeString() : 'n/a'}
          </span>
        </div>
      </div>
      <div className="platform-feature-grid">
        <article className="platform-feature-card">
          <h4>Frontend</h4>
          <ul className="bullet-list">
            <li>
              <span>Runtime</span>
              <strong>{systemOverview?.frontend.runtime ?? 'nextjs'}</strong>
            </li>
            <li>
              <span>Status</span>
              <strong className={systemOverview?.frontend.status === 'ready' ? 'platform-ready' : 'platform-degraded'}>
                {systemOverview?.frontend.status ?? 'unknown'}
              </strong>
            </li>
            <li>
              <span>Site URL</span>
              <strong>{systemOverview?.frontend.site_url ?? 'n/a'}</strong>
            </li>
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Backend</h4>
          <ul className="bullet-list">
            <li>
              <span>Runtime</span>
              <strong>{systemOverview?.backend.runtime ?? 'fastapi'}</strong>
            </li>
            <li>
              <span>Status</span>
              <strong className={systemOverview?.backend.status === 'ready' ? 'platform-ready' : 'platform-degraded'}>
                {systemOverview?.backend.status ?? 'unknown'}
              </strong>
            </li>
            <li>
              <span>Environment</span>
              <strong>{systemOverview?.backend.environment ?? 'local'}</strong>
            </li>
            <li>
              <span>Rate keys</span>
              <strong>{Number(systemOverview?.backend.rate_limiter_active_keys ?? 0)}</strong>
            </li>
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Database & Security</h4>
          <ul className="bullet-list">
            <li>
              <span>Database mode</span>
              <strong className={systemOverview?.database.db_ready ? 'platform-ready' : 'platform-degraded'}>
                {systemOverview?.database.status ?? 'unknown'}
              </strong>
            </li>
            <li>
              <span>Engine</span>
              <strong>{systemOverview?.database.engine ?? 'postgresql'}</strong>
            </li>
            <li>
              <span>Strict security</span>
              <strong className={systemOverview?.security.strict_mode ? 'platform-ready' : 'platform-degraded'}>
                {systemOverview?.security.strict_mode ? 'Enabled' : 'Disabled'}
              </strong>
            </li>
            <li>
              <span>Vault configured</span>
              <strong className={systemOverview?.security.vault_configured ? 'platform-ready' : 'platform-degraded'}>
                {systemOverview?.security.vault_configured ? 'Yes' : 'No'}
              </strong>
            </li>
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Platform Capacity</h4>
          <ul className="bullet-list">
            <li>
              <span>Integrations ready</span>
              <strong>
                {systemOverview?.integrations.ready ?? 0}/{systemOverview?.integrations.total ?? 0}
              </strong>
            </li>
            <li>
              <span>Active queues</span>
              <strong>{systemOverview?.queues.active_queues ?? 0}</strong>
            </li>
            <li>
              <span>Queue events</span>
              <strong>{systemOverview?.queues.total_events ?? 0}</strong>
            </li>
            <li>
              <span>Feature readiness</span>
              <strong>
                {systemOverview?.capabilities.features_ready_estimate ?? 0}/
                {systemOverview?.capabilities.features_total ?? 0}
              </strong>
            </li>
          </ul>
        </article>
      </div>
    </section>
  );
}

function RuntimeTrajectorySection({
  queueTrendRows,
  integrationTrendRows,
  coverageTrendRows,
  systemHistory,
}: RuntimeTrajectoryProps) {
  return (
    <section className="card dashboard-chart" style={{ marginTop: 20 }}>
      <h3>Runtime Trajectory (24 Snapshots)</h3>
      <div className="platform-feature-grid">
        <article className="platform-feature-card">
          <h4>Queue Throughput Trend</h4>
          <ul className="bullet-list">
            {queueTrendRows.map((row) => (
              <li key={row.id}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </li>
            ))}
            {queueTrendRows.length === 0 ? <li>No snapshot trend data yet.</li> : null}
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Integration Readiness Trend</h4>
          <ul className="bullet-list">
            {integrationTrendRows.map((row) => (
              <li key={row.id}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </li>
            ))}
            {integrationTrendRows.length === 0 ? <li>No snapshot trend data yet.</li> : null}
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Coverage Trend</h4>
          <ul className="bullet-list">
            {coverageTrendRows.map((row) => (
              <li key={row.id}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </li>
            ))}
            {coverageTrendRows.length === 0 ? <li>No snapshot trend data yet.</li> : null}
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Latest Snapshot Ledger</h4>
          <ul className="bullet-list">
            {(systemHistory?.items || []).slice(0, 6).map((item) => (
              <li key={`snapshot-row-${item.id}`}>
                <span>{new Date(item.generated_at).toLocaleTimeString()}</span>
                <strong>
                  {item.integrations_ready}/{item.integrations_total} · Q{item.queue_total_events}
                </strong>
              </li>
            ))}
            {(systemHistory?.items || []).length === 0 ? <li>No snapshots captured yet.</li> : null}
          </ul>
        </article>
      </div>
    </section>
  );
}

function QueueAndCapabilitySection({ queueRows, capabilities, integrationRows }: QueueAndCapabilityProps) {
  return (
    <>
      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Top Queue Activity</h3>
        <div className="queue-list">
          {queueRows.map((row) => (
            <div key={row.name} className="queue-row">
              <div className="queue-head">
                <span>{row.name.replaceAll('_', ' ')}</span>
                <strong>{row.value}</strong>
              </div>
              <div className="queue-track">
                <div className="queue-fill" style={{ width: `${row.width}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Feature Capability Matrix</h3>
        <div className="platform-feature-grid">
          {(capabilities?.categories || []).map((category) => (
            <article key={category.id} className="platform-feature-card">
              <h4>{category.name}</h4>
              <ul className="bullet-list">
                {category.features.map((feature) => (
                  <li key={feature.id}>
                    <span>{feature.name}</span>
                    <span className={feature.ready ? 'platform-ready' : 'platform-degraded'}>
                      {feature.ready ? 'Ready' : 'Blocked'}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
      <section className="card dashboard-chart" style={{ marginTop: 20 }}>
        <h3>Integration Readiness</h3>
        <div className="platform-integration-grid">
          {integrationRows.map((item) => (
            <article key={item.key} className="platform-integration-item">
              <span>{item.key.replaceAll('_', ' ')}</span>
              <strong className={item.ready ? 'platform-ready' : 'platform-degraded'}>
                {item.ready ? 'Connected' : 'Not configured'}
              </strong>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function RevenueAttributionSection({
  attribution,
  generatedTrackedUrl,
  isGeneratingTrackedUrl,
  touchpointPostId,
  touchpointPlatform,
  touchpointCampaign,
  touchpointUrl,
  setTouchpointPostId,
  setTouchpointPlatform,
  setTouchpointCampaign,
  setTouchpointUrl,
  onGenerateTrackedLink,
}: RevenueAttributionProps) {
  const topPosts = (attribution?.top_posts || []).slice(0, 6);
  const channels = (attribution?.channels || []).slice(0, 6);

  return (
    <section className="card dashboard-chart" style={{ marginTop: 20 }}>
      <h3>Revenue Attribution</h3>
      <p className="muted">
        Shapley multi-touch attribution is active. Use the generator below to auto-inject UTM + touchpoint keys into
        post URLs, then ingest Stripe, Shopify, or WooCommerce sale webhooks to map revenue back to exact posts.
      </p>
      <div className="platform-attribution-grid" style={{ marginTop: 12 }}>
        <article className="platform-feature-card">
          <h4>Tracked Link Generator</h4>
          <div className="platform-form-grid">
            <input
              value={touchpointPostId}
              onChange={(event) => setTouchpointPostId(event.target.value)}
              placeholder="Post ID"
            />
            <input
              value={touchpointPlatform}
              onChange={(event) => setTouchpointPlatform(event.target.value)}
              placeholder="Platform"
            />
            <input
              value={touchpointCampaign}
              onChange={(event) => setTouchpointCampaign(event.target.value)}
              placeholder="Campaign"
            />
            <input
              value={touchpointUrl}
              onChange={(event) => setTouchpointUrl(event.target.value)}
              placeholder="Destination URL"
            />
          </div>
          <button type="button" className="cta-link" onClick={onGenerateTrackedLink} disabled={isGeneratingTrackedUrl}>
            {isGeneratingTrackedUrl ? 'Generating...' : 'Generate tracked URL'}
          </button>
          {generatedTrackedUrl ? (
            <p className="platform-tracked-url">
              <strong>Tracked URL:</strong> {generatedTrackedUrl}
            </p>
          ) : null}
        </article>
        <article className="platform-feature-card">
          <h4>Attribution Totals (90d)</h4>
          <ul className="bullet-list">
            <li>
              <span>Revenue</span>
              <strong>${(attribution?.totals.revenue ?? 0).toFixed(2)}</strong>
            </li>
            <li>
              <span>Attributed revenue</span>
              <strong>${(attribution?.totals.attributed_revenue ?? 0).toFixed(2)}</strong>
            </li>
            <li>
              <span>Tracked conversions</span>
              <strong>{attribution?.totals.tracked_conversions ?? 0}</strong>
            </li>
            <li>
              <span>Unattributed revenue</span>
              <strong>${(attribution?.totals.unattributed_revenue ?? 0).toFixed(2)}</strong>
            </li>
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Top Revenue Posts</h4>
          <ul className="bullet-list">
            {topPosts.map((row) => (
              <li key={row.post_id}>
                <span>{row.post_id}</span>
                <strong>${row.attributed_revenue.toFixed(2)}</strong>
              </li>
            ))}
            {topPosts.length === 0 ? <li>No attributed post revenue yet.</li> : null}
          </ul>
        </article>
        <article className="platform-feature-card">
          <h4>Revenue by Channel</h4>
          <ul className="bullet-list">
            {channels.map((row) => (
              <li key={row.channel}>
                <span>{row.channel}</span>
                <strong>${row.attributed_revenue.toFixed(2)}</strong>
              </li>
            ))}
            {channels.length === 0 ? <li>No channel attribution yet.</li> : null}
          </ul>
        </article>
      </div>
    </section>
  );
}

function GrowthSuiteSection({ growthSuite, isBootstrappingGrowthSuite, onBootstrapGrowthSuite }: GrowthSuiteProps) {
  const growthFeatures = growthSuite?.features || [];

  return (
    <section className="card dashboard-chart" style={{ marginTop: 20 }}>
      <div className="platform-controls" style={{ marginBottom: 12 }}>
        <div>
          <h3>AI Growth Suite</h3>
          <p className="muted">
            Brand Voice DNA, auto A/B testing, ROI forecasting, counter-strike, content planning, agency operations,
            audience segmentation, IRA automation, ads, repurposing, GEO/SEO, lead capture, email, smart scheduling,
            link-in-bio, podcast, video scripting, and advanced reports.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Link href="/studio/growth-suite" className="cta-link" style={{ textDecoration: 'none' }}>
            Open growth suite studio
          </Link>
          <button
            type="button"
            className="cta-link"
            onClick={onBootstrapGrowthSuite}
            disabled={isBootstrappingGrowthSuite}
          >
            {isBootstrappingGrowthSuite ? 'Running full suite...' : 'Run full growth suite'}
          </button>
        </div>
      </div>
      <div className="platform-feature-grid">
        {growthFeatures.map((feature) => (
          <article key={feature.key} className="platform-feature-card">
            <div className="queue-head">
              <h4>{feature.name}</h4>
              <strong className={feature.status === 'ready' ? 'platform-ready' : 'platform-degraded'}>
                {feature.status}
              </strong>
            </div>
            <p className="muted">{feature.headline}</p>
            <ul className="bullet-list">
              {feature.metrics.map((metric) => (
                <li key={`${feature.key}-${metric.label}`}>
                  <span>{metric.label}</span>
                  <strong>{String(metric.value)}</strong>
                </li>
              ))}
              {feature.metrics.length === 0 ? <li>No live metrics yet.</li> : null}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function PlatformDashboardContent(props: Props) {
  return (
    <>
      <KpiGrid
        status={props.status}
        coverage={props.coverage}
        metrics={props.metrics}
        antiFailure={props.antiFailure}
        capabilities={props.capabilities}
        attribution={props.attribution}
        growthSuite={props.growthSuite}
      />
      <RuntimeOverviewSection
        systemOverview={props.systemOverview}
        onCaptureSystemSnapshot={props.onCaptureSystemSnapshot}
      />
      <RuntimeTrajectorySection
        queueTrendRows={props.queueTrendRows}
        integrationTrendRows={props.integrationTrendRows}
        coverageTrendRows={props.coverageTrendRows}
        systemHistory={props.systemHistory}
      />
      <QueueAndCapabilitySection
        queueRows={props.queueRows}
        capabilities={props.capabilities}
        integrationRows={props.integrationRows}
      />
      <RevenueAttributionSection
        attribution={props.attribution}
        generatedTrackedUrl={props.generatedTrackedUrl}
        isGeneratingTrackedUrl={props.isGeneratingTrackedUrl}
        touchpointPostId={props.touchpointPostId}
        touchpointPlatform={props.touchpointPlatform}
        touchpointCampaign={props.touchpointCampaign}
        touchpointUrl={props.touchpointUrl}
        setTouchpointPostId={props.setTouchpointPostId}
        setTouchpointPlatform={props.setTouchpointPlatform}
        setTouchpointCampaign={props.setTouchpointCampaign}
        setTouchpointUrl={props.setTouchpointUrl}
        onGenerateTrackedLink={props.onGenerateTrackedLink}
      />
      <GrowthSuiteSection
        growthSuite={props.growthSuite}
        isBootstrappingGrowthSuite={props.isBootstrappingGrowthSuite}
        onBootstrapGrowthSuite={props.onBootstrapGrowthSuite}
      />
      <PlatformHybridStackSections
        productionReadinessChecks={props.productionReadinessChecks}
        recommendation={props.hybridRecommendation}
        stacks={props.hybridStacks}
        summary={props.hybridSummary}
      />
      <section style={{ marginTop: 20 }}>
        <InstitutionalAiWidgets />
      </section>
    </>
  );
}
