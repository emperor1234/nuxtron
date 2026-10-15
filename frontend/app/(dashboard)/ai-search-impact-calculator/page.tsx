'use client';

import { useState, type ChangeEvent, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader, Stat, StatGrid } from '../_ui/kit';
import {
  buildAiImpactPayload,
  buildCostSavingsPayload,
  createEmptyAiImpactForm,
  createEmptyCostSavingsForm,
  parseAiImpactProjection,
  parseCostSavingsProjection,
  parseReadinessInventory,
  parseVendorInventory,
  type AiImpactForm,
  type AiImpactOutput,
  type CostSavingsForm,
  type CostSavingsOutput,
  type Projection,
  type ReadinessInventory,
  type VendorInventory,
} from './impact-calculator-model';
import styles from './impact-calculator.module.css';

type NumberFieldProps = {
  id: string;
  label: string;
  value: string;
  minimum: number;
  maximum: number;
  step?: number | 'any';
  helper: string;
  onChange: (value: string) => void;
};

function NumberField({ id, label, value, minimum, maximum, step = 1, helper, onChange }: NumberFieldProps) {
  return (
    <div className={styles.numberField}>
      <Field
        id={id}
        label={label}
        type="number"
        value={value}
        min={minimum}
        max={maximum}
        step={step}
        required
        onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
      />
      <p className={styles.fieldHint}>{helper} Allowed range: {minimum}–{maximum}.</p>
    </div>
  );
}

function sessionWorkspace(): string {
  try {
    return resolveSessionTenant();
  } catch {
    return '';
  }
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function projectionNote<T>(projection: Projection<T>, fallback: string): string {
  return projection.assumptionsNote || fallback;
}

export default function AiSearchImpactCalculatorPage() {
  const [tenantId] = useState(sessionWorkspace);
  const [costForm, setCostForm] = useState<CostSavingsForm>(createEmptyCostSavingsForm);
  const [impactForm, setImpactForm] = useState<AiImpactForm>(createEmptyAiImpactForm);
  const [costResult, setCostResult] = useState<{ input: NonNullable<ReturnType<typeof buildCostSavingsPayload>>; projection: Projection<CostSavingsOutput> } | null>(null);
  const [impactResult, setImpactResult] = useState<{ input: NonNullable<ReturnType<typeof buildAiImpactPayload>>; projection: Projection<AiImpactOutput> } | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [impactLoading, setImpactLoading] = useState(false);
  const [costError, setCostError] = useState('');
  const [impactError, setImpactError] = useState('');
  const [vendorInventory, setVendorInventory] = useState<VendorInventory | null>(null);
  const [readinessInventory, setReadinessInventory] = useState<ReadinessInventory | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [vendorError, setVendorError] = useState('');
  const [readinessError, setReadinessError] = useState('');

  const hasWorkspace = tenantId.trim().length > 0;
  const costPayload = buildCostSavingsPayload(costForm);
  const impactPayload = buildAiImpactPayload(impactForm);

  function updateCostField<K extends keyof CostSavingsForm>(key: K, value: string) {
    setCostForm((previous) => ({ ...previous, [key]: value }));
    setCostResult(null);
  }

  function updateImpactField<K extends keyof AiImpactForm>(key: K, value: string) {
    setImpactForm((previous) => ({ ...previous, [key]: value }));
    setImpactResult(null);
  }

  async function calculateCostSavings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasWorkspace) {
      setCostError('Workspace context is unavailable. Sign in or select a workspace before calculating.');
      return;
    }
    const input = buildCostSavingsPayload(costForm);
    if (!input) {
      setCostError('Enter each assumption within its stated range before calculating.');
      return;
    }

    setCostError('');
    setCostResult(null);
    setCostLoading(true);
    try {
      const response = await apiSend<unknown>('/search-everywhere/cost-savings-calculator', 'POST', input, tenantId);
      const projection = parseCostSavingsProjection(response);
      if (!projection) throw new Error('The cost-savings service returned incomplete results. Please retry.');
      setCostResult({ input, projection });
    } catch (cause) {
      setCostError(cause instanceof Error ? cause.message : 'Could not calculate the labor-savings scenario.');
    } finally {
      setCostLoading(false);
    }
  }

  async function calculateAiImpact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasWorkspace) {
      setImpactError('Workspace context is unavailable. Sign in or select a workspace before calculating.');
      return;
    }
    const input = buildAiImpactPayload(impactForm);
    if (!input) {
      setImpactError('Enter each assumption within its stated range before calculating.');
      return;
    }

    setImpactError('');
    setImpactResult(null);
    setImpactLoading(true);
    try {
      const response = await apiSend<unknown>('/search-everywhere/ai-search-impact-calculator', 'POST', input, tenantId);
      const projection = parseAiImpactProjection(response);
      if (!projection) throw new Error('The AI-search impact service returned incomplete results. Please retry.');
      setImpactResult({ input, projection });
    } catch (cause) {
      setImpactError(cause instanceof Error ? cause.message : 'Could not calculate the AI-search scenario.');
    } finally {
      setImpactLoading(false);
    }
  }

  async function refreshReadiness() {
    if (!hasWorkspace) {
      setVendorError('Workspace context is unavailable. Sign in or select a workspace before checking server configuration.');
      setReadinessError('Workspace context is unavailable.');
      return;
    }
    setVendorInventory(null);
    setReadinessInventory(null);
    setVendorError('');
    setReadinessError('');
    setReadinessLoading(true);
    try {
      const [vendorsResponse, readinessResponse] = await Promise.allSettled([
        apiGet<unknown>('/search-everywhere/vendors', tenantId),
        apiGet<unknown>('/search-everywhere/readiness', tenantId),
      ]);

      if (vendorsResponse.status === 'fulfilled') {
        const parsed = parseVendorInventory(vendorsResponse.value);
        if (parsed) setVendorInventory(parsed);
        else setVendorError('The vendor inventory response was incomplete.');
      } else {
        setVendorError(vendorsResponse.reason instanceof Error ? vendorsResponse.reason.message : 'Vendor inventory is unavailable.');
      }

      if (readinessResponse.status === 'fulfilled') {
        const parsed = parseReadinessInventory(readinessResponse.value);
        if (parsed) setReadinessInventory(parsed);
        else setReadinessError('The server readiness response was incomplete.');
      } else {
        setReadinessError(readinessResponse.reason instanceof Error ? readinessResponse.reason.message : 'Server readiness is unavailable.');
      }
    } finally {
      setReadinessLoading(false);
    }
  }

  const updateCost = (key: keyof CostSavingsForm) => (value: string) => updateCostField(key, value);
  const updateImpact = (key: keyof AiImpactForm) => (value: string) => updateImpactField(key, value);

  return (
    <Page className={styles.layout}>
      <PageHeader
        title="AI search impact calculator"
        subtitle="Model operational savings and AI-search growth from assumptions you provide."
        actions={<Badge tone="neutral">Scenario estimate</Badge>}
      />

      {!hasWorkspace ? (
        <p role="alert" className={styles.error}>Workspace context is unavailable. Sign in or select a workspace to use these calculators.</p>
      ) : null}

      <Card>
        <p className={styles.disclaimer}>
          These are deterministic what-if calculations from your inputs—not measured performance, live AI visibility, or a guarantee of results. Review the assumptions before relying on a projection.
        </p>
      </Card>

      <section className={styles.sectionStack} aria-label="Scenario calculators">
        <Card>
          <form className={styles.form} onSubmit={(event) => void calculateCostSavings(event)} aria-busy={costLoading}>
            <CardTitle sub="Estimate how much manual page work could be offset by automation, after tool cost.">
              Labor-savings scenario
            </CardTitle>
            <div className={styles.fieldGrid}>
              <NumberField id="cost-sites" label="Sites in scope" value={costForm.sites_count} minimum={1} maximum={10_000} helper="Whole sites included in the scenario." onChange={updateCost('sites_count')} />
              <NumberField id="cost-pages" label="Pages per site" value={costForm.pages_per_site} minimum={1} maximum={5_000_000} helper="Whole pages per site." onChange={updateCost('pages_per_site')} />
              <NumberField id="cost-deployments" label="Monthly deployments" value={costForm.monthly_deployments} minimum={1} maximum={1_000} helper="Whole deployments in a typical month." onChange={updateCost('monthly_deployments')} />
              <NumberField id="cost-manual-minutes" label="Manual minutes per page" value={costForm.manual_minutes_per_page} minimum={0.05} maximum={120} step={0.05} helper="Minutes of manual work for each page and deployment." onChange={updateCost('manual_minutes_per_page')} />
              <NumberField id="cost-hourly-rate" label="Labor cost per hour (USD)" value={costForm.hourly_rate_usd} minimum={1} maximum={10_000} step="any" helper="Your fully loaded hourly labor cost." onChange={updateCost('hourly_rate_usd')} />
              <NumberField id="cost-coverage" label="Automation coverage (%)" value={costForm.automation_coverage_pct} minimum={1} maximum={100} step="any" helper="Share of modeled work automation can cover." onChange={updateCost('automation_coverage_pct')} />
              <NumberField id="cost-tool-cost" label="Tool cost per month (USD)" value={costForm.tool_monthly_cost_usd} minimum={0} maximum={1_000_000} step="any" helper="Monthly cost to subtract from estimated labor savings." onChange={updateCost('tool_monthly_cost_usd')} />
            </div>
            {costError ? <p role="alert" className={styles.error}>{costError}</p> : null}
            <div className={styles.formActions}>
              <p className={styles.fieldHint}>All assumptions are blank until you provide them.</p>
              <Button type="submit" variant="primary" disabled={!hasWorkspace || !costPayload || costLoading}>
                {costLoading ? 'Calculating…' : 'Calculate savings scenario'}
              </Button>
            </div>
          </form>
        </Card>

        {costResult ? (
          <Card>
            <div className={styles.resultHeader}>
              <CardTitle sub={`Based on ${formatNumber(costResult.input.sites_count)} sites, ${formatNumber(costResult.input.pages_per_site)} pages per site, and ${formatNumber(costResult.input.monthly_deployments)} deployments per month.`}>
                Estimated labor savings
              </CardTitle>
              <Badge tone="neutral">Modeled, not measured</Badge>
            </div>
            <StatGrid>
              <Stat label="Automated hours saved / month" value={formatNumber(costResult.projection.output.automated_monthly_hours_saved)} />
              <Stat label="Labor cost saved / month" value={formatCurrency(costResult.projection.output.monthly_labor_cost_saved_usd)} />
              <Stat label="Net savings / month" value={formatCurrency(costResult.projection.output.net_monthly_savings_usd)} hint="After the entered tool cost." />
              <Stat label="Net savings / year" value={formatCurrency(costResult.projection.output.annual_net_savings_usd)} />
              <Stat label="Payback period" value={`${formatNumber(costResult.projection.output.payback_days)} days`} />
            </StatGrid>
            <p className={styles.assumptionText}>{projectionNote(costResult.projection, 'Directional labor-hour replacement model; results depend on real workflow complexity.')}</p>
          </Card>
        ) : null}

        <Card>
          <form className={styles.form} onSubmit={(event) => void calculateAiImpact(event)} aria-busy={impactLoading}>
            <CardTitle sub="Estimate a potential AI-search traffic and revenue scenario from your own traffic and funnel assumptions.">
              AI-search growth scenario
            </CardTitle>
            <div className={styles.fieldGrid}>
              <NumberField id="impact-sessions" label="Monthly site sessions" value={impactForm.monthly_sessions} minimum={1} maximum={1_000_000_000} helper="Whole monthly sessions across the site." onChange={updateImpact('monthly_sessions')} />
              <NumberField id="impact-current-visibility" label="Current AI visibility (%)" value={impactForm.current_ai_visibility_pct} minimum={0} maximum={100} step="any" helper="Your current estimate; this tool does not measure it." onChange={updateImpact('current_ai_visibility_pct')} />
              <NumberField id="impact-target-visibility" label="Target AI visibility (%)" value={impactForm.target_ai_visibility_pct} minimum={0} maximum={100} step="any" helper="The scenario target to model." onChange={updateImpact('target_ai_visibility_pct')} />
              <NumberField id="impact-ctr" label="AI-search click-through rate (%)" value={impactForm.ai_ctr_pct} minimum={0} maximum={100} step="any" helper="Assumed share of visible impressions that click." onChange={updateImpact('ai_ctr_pct')} />
              <NumberField id="impact-conversion" label="Conversion rate (%)" value={impactForm.conversion_rate_pct} minimum={0} maximum={100} step="any" helper="Assumed share of clicks that convert." onChange={updateImpact('conversion_rate_pct')} />
              <NumberField id="impact-order-value" label="Average order value (USD)" value={impactForm.avg_order_value_usd} minimum={0} maximum={1_000_000} step="any" helper="Average revenue per modeled conversion." onChange={updateImpact('avg_order_value_usd')} />
              <NumberField id="impact-margin" label="Gross margin (%)" value={impactForm.gross_margin_pct} minimum={0} maximum={100} step="any" helper="Used to estimate gross profit, not revenue." onChange={updateImpact('gross_margin_pct')} />
            </div>
            {impactError ? <p role="alert" className={styles.error}>{impactError}</p> : null}
            <div className={styles.formActions}>
              <p className={styles.fieldHint}>The result is a scenario, not an observed AI-search metric.</p>
              <Button type="submit" variant="primary" disabled={!hasWorkspace || !impactPayload || impactLoading}>
                {impactLoading ? 'Calculating…' : 'Calculate AI-search scenario'}
              </Button>
            </div>
          </form>
        </Card>

        {impactResult ? (
          <Card>
            <div className={styles.resultHeader}>
              <CardTitle sub={`${formatNumber(impactResult.input.monthly_sessions)} monthly sessions · visibility ${formatNumber(impactResult.input.current_ai_visibility_pct)}% to ${formatNumber(impactResult.input.target_ai_visibility_pct)}%`}>
                Estimated AI-search impact
              </CardTitle>
              <Badge tone="neutral">Modeled, not measured</Badge>
            </div>
            <StatGrid>
              <Stat label="Incremental impressions / month" value={formatNumber(impactResult.projection.output.incremental_ai_impressions_monthly)} />
              <Stat label="Incremental clicks / month" value={formatNumber(impactResult.projection.output.incremental_clicks_monthly)} />
              <Stat label="Incremental conversions / month" value={formatNumber(impactResult.projection.output.incremental_conversions_monthly)} />
              <Stat label="Revenue lift / month" value={formatCurrency(impactResult.projection.output.incremental_revenue_monthly_usd)} />
              <Stat label="Revenue lift / year" value={formatCurrency(impactResult.projection.output.incremental_revenue_annual_usd)} />
              <Stat label="Gross profit / month" value={formatCurrency(impactResult.projection.output.incremental_gross_profit_monthly_usd)} />
            </StatGrid>
            <p className={styles.assumptionText}>{projectionNote(impactResult.projection, 'Projection assumes stable conversion behavior for AI-origin sessions.')}</p>
          </Card>
        ) : null}
      </section>

      <Card>
        <div className={styles.readinessHeader}>
          <div>
            <CardTitle sub="A secondary inventory of server-side configuration and tracked provider targets.">
              Server integration setup
            </CardTitle>
            <p className={styles.fieldHint}>
              Presence checks are not live credential probes. A configured flag does not confirm that a provider is reachable or working for your workspace.
            </p>
          </div>
          <Button type="button" variant="ghost" onClick={() => void refreshReadiness()} disabled={!hasWorkspace || readinessLoading}>
            {readinessLoading ? 'Checking…' : 'Check server setup'}
          </Button>
        </div>

        {vendorError ? <p role="alert" className={styles.error}>{vendorError}</p> : null}
        {readinessError ? <p role="alert" className={styles.partial}>{readinessError}</p> : null}
        {readinessLoading ? <p role="status" className={styles.fieldHint}>Loading configuration inventory…</p> : null}
        {!readinessLoading && !vendorInventory && !readinessInventory && !vendorError && !readinessError ? (
          <p className={styles.empty}>Configuration inventory has not been loaded. Check server setup to view it.</p>
        ) : null}

        {readinessInventory ? (
          <p className={styles.assumptionText}>
            Server configuration heuristic: {readinessInventory.configured_integrations}/{readinessInventory.total_integrations} counted as configured ({formatNumber(readinessInventory.configured_pct)}%), grade {readinessInventory.grade}. The backend&apos;s threshold is not a production certification.
          </p>
        ) : null}
        {vendorInventory ? (
          <>
            <p className={styles.assumptionText}>{vendorInventory.configured}/{vendorInventory.total} inventory entries are marked configured by the service. Crawler targets are tracked references, not connected customer accounts.</p>
            <ul className={styles.vendorList}>
              {vendorInventory.vendors.map((vendor) => {
                const isTarget = vendor.mode === 'crawler-target';
                const label = isTarget ? 'Tracked target' : vendor.configured ? 'Configured on server' : 'Missing server configuration';
                const tone = isTarget ? 'neutral' : vendor.configured ? 'success' : 'danger';
                return (
                  <li className={styles.vendorRow} key={vendor.key}>
                    <div className={styles.vendorInfo}>
                      <strong>{vendor.display_name}</strong>
                      <span className={styles.vendorCategory}>{vendor.category}</span>
                      <span className={styles.vendorMode}>Mode: {vendor.mode}</span>
                    </div>
                    <Badge tone={tone}>{label}</Badge>
                  </li>
                );
              })}
            </ul>
          </>
        ) : null}
      </Card>
    </Page>
  );
}
