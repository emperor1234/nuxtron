import { describe, expect, it } from 'vitest';
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
  type CostSavingsForm,
} from './impact-calculator-model';

const costForm: CostSavingsForm = {
  sites_count: '20',
  pages_per_site: '1000',
  monthly_deployments: '4',
  manual_minutes_per_page: '1.25',
  hourly_rate_usd: '100',
  automation_coverage_pct: '80',
  tool_monthly_cost_usd: '500',
};

const impactForm: AiImpactForm = {
  monthly_sessions: '100000',
  current_ai_visibility_pct: '0',
  target_ai_visibility_pct: '10',
  ai_ctr_pct: '15',
  conversion_rate_pct: '2.5',
  avg_order_value_usd: '120',
  gross_margin_pct: '60',
};

const costResponse = {
  status: 'ok',
  output: {
    total_pages_in_scope: 20_000,
    manual_hours_per_deployment: 416.67,
    manual_monthly_hours: 1666.67,
    automated_monthly_hours_saved: 1333.33,
    monthly_labor_cost_saved_usd: 133333.33,
    tool_monthly_cost_usd: 500,
    net_monthly_savings_usd: 132833.33,
    annual_net_savings_usd: 1594000,
    payback_days: 0.11,
  },
  assumptions: { note: 'Directional labor-hour replacement model.' },
};

const impactResponse = {
  status: 'ok',
  output: {
    current_ai_impressions_monthly: 0,
    target_ai_impressions_monthly: 10_000,
    incremental_ai_impressions_monthly: 10_000,
    incremental_clicks_monthly: 1500,
    incremental_conversions_monthly: 37.5,
    incremental_revenue_monthly_usd: 4500,
    incremental_gross_profit_monthly_usd: 2700,
    incremental_revenue_annual_usd: 54_000,
    incremental_gross_profit_annual_usd: 32_400,
  },
};

describe('impact calculator model', () => {
  it('starts with no customer assumptions prefilled', () => {
    expect(Object.values(createEmptyCostSavingsForm()).every((value) => value === '')).toBe(true);
    expect(Object.values(createEmptyAiImpactForm()).every((value) => value === '')).toBe(true);
  });

  it('builds bounded numeric cost and AI-impact payloads', () => {
    expect(buildCostSavingsPayload(costForm)).toEqual({
      sites_count: 20,
      pages_per_site: 1000,
      monthly_deployments: 4,
      manual_minutes_per_page: 1.25,
      hourly_rate_usd: 100,
      automation_coverage_pct: 80,
      tool_monthly_cost_usd: 500,
    });
    expect(buildAiImpactPayload(impactForm)).toEqual({
      monthly_sessions: 100000,
      current_ai_visibility_pct: 0,
      target_ai_visibility_pct: 10,
      ai_ctr_pct: 15,
      conversion_rate_pct: 2.5,
      avg_order_value_usd: 120,
      gross_margin_pct: 60,
    });
  });

  it('rejects blank, out-of-range, and non-integer whole-count assumptions', () => {
    expect(buildCostSavingsPayload(createEmptyCostSavingsForm())).toBeNull();
    expect(buildCostSavingsPayload({ ...costForm, sites_count: '1.5' })).toBeNull();
    expect(buildCostSavingsPayload({ ...costForm, automation_coverage_pct: '101' })).toBeNull();
    expect(buildAiImpactPayload({ ...impactForm, monthly_sessions: '0' })).toBeNull();
    expect(buildAiImpactPayload({ ...impactForm, gross_margin_pct: 'NaN' })).toBeNull();
  });

  it('accepts a real zero projection and rejects missing or malformed output metrics', () => {
    expect(parseAiImpactProjection(impactResponse)?.output.incremental_clicks_monthly).toBe(1500);
    expect(parseCostSavingsProjection({
      ...costResponse,
      output: { ...costResponse.output, net_monthly_savings_usd: 0 },
    })?.output.net_monthly_savings_usd).toBe(0);
    expect(parseAiImpactProjection({ ...impactResponse, output: { ...impactResponse.output, incremental_clicks_monthly: undefined } })).toBeNull();
    expect(parseCostSavingsProjection({ ...costResponse, output: { ...costResponse.output, payback_days: Number.NaN } })).toBeNull();
    expect(parseCostSavingsProjection({ ...costResponse, status: 'preview' })).toBeNull();
  });

  it('distinguishes tracked crawler references from configured server integrations', () => {
    const vendors = parseVendorInventory({
      status: 'ok',
      configured: 1,
      total: 2,
      vendors: [
        { key: 'cloudflare', display_name: 'Cloudflare', category: 'WAF', configured: true, mode: 'api' },
        { key: 'openai', display_name: 'OpenAI crawler', category: 'Crawler target', configured: true, mode: 'crawler-target' },
      ],
    });
    expect(vendors?.vendors[1]?.mode).toBe('crawler-target');
    expect(parseVendorInventory({ status: 'ok', configured: 2, total: 1, vendors: [] })).toBeNull();
    expect(parseReadinessInventory({
      status: 'ok',
      readiness: { configured_integrations: 1, total_integrations: 2, configured_pct: 50, grade: 'C', production_ready: false },
    })?.production_ready).toBe(false);
    expect(parseReadinessInventory({ status: 'ok', readiness: { configured_pct: 50 } })).toBeNull();
  });
});
