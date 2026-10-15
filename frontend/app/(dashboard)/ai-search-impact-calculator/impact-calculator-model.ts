export type CostSavingsForm = {
  sites_count: string;
  pages_per_site: string;
  monthly_deployments: string;
  manual_minutes_per_page: string;
  hourly_rate_usd: string;
  automation_coverage_pct: string;
  tool_monthly_cost_usd: string;
};

export type CostSavingsPayload = {
  sites_count: number;
  pages_per_site: number;
  monthly_deployments: number;
  manual_minutes_per_page: number;
  hourly_rate_usd: number;
  automation_coverage_pct: number;
  tool_monthly_cost_usd: number;
};

export type AiImpactForm = {
  monthly_sessions: string;
  current_ai_visibility_pct: string;
  target_ai_visibility_pct: string;
  ai_ctr_pct: string;
  conversion_rate_pct: string;
  avg_order_value_usd: string;
  gross_margin_pct: string;
};

export type AiImpactPayload = {
  monthly_sessions: number;
  current_ai_visibility_pct: number;
  target_ai_visibility_pct: number;
  ai_ctr_pct: number;
  conversion_rate_pct: number;
  avg_order_value_usd: number;
  gross_margin_pct: number;
};

export type CostSavingsOutput = {
  total_pages_in_scope: number;
  manual_hours_per_deployment: number;
  manual_monthly_hours: number;
  automated_monthly_hours_saved: number;
  monthly_labor_cost_saved_usd: number;
  tool_monthly_cost_usd: number;
  net_monthly_savings_usd: number;
  annual_net_savings_usd: number;
  payback_days: number;
};

export type AiImpactOutput = {
  current_ai_impressions_monthly: number;
  target_ai_impressions_monthly: number;
  incremental_ai_impressions_monthly: number;
  incremental_clicks_monthly: number;
  incremental_conversions_monthly: number;
  incremental_revenue_monthly_usd: number;
  incremental_gross_profit_monthly_usd: number;
  incremental_revenue_annual_usd: number;
  incremental_gross_profit_annual_usd: number;
};

export type Projection<T> = { output: T; assumptionsNote: string };

export type VendorItem = {
  key: string;
  display_name: string;
  category: string;
  configured: boolean;
  mode: string;
};

export type VendorInventory = {
  configured: number;
  total: number;
  vendors: VendorItem[];
};

export type ReadinessInventory = {
  configured_integrations: number;
  total_integrations: number;
  configured_pct: number;
  grade: string;
  production_ready: boolean;
};

const EMPTY_COST_SAVINGS_FORM: CostSavingsForm = {
  sites_count: '',
  pages_per_site: '',
  monthly_deployments: '',
  manual_minutes_per_page: '',
  hourly_rate_usd: '',
  automation_coverage_pct: '',
  tool_monthly_cost_usd: '',
};

const EMPTY_AI_IMPACT_FORM: AiImpactForm = {
  monthly_sessions: '',
  current_ai_visibility_pct: '',
  target_ai_visibility_pct: '',
  ai_ctr_pct: '',
  conversion_rate_pct: '',
  avg_order_value_usd: '',
  gross_margin_pct: '',
};

export function createEmptyCostSavingsForm(): CostSavingsForm {
  return { ...EMPTY_COST_SAVINGS_FORM };
}

export function createEmptyAiImpactForm(): AiImpactForm {
  return { ...EMPTY_AI_IMPACT_FORM };
}

function boundedNumber(value: string, minimum: number, maximum: number, integer = false): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < minimum || parsed > maximum || (integer && !Number.isInteger(parsed))) {
    return null;
  }
  return parsed;
}

export function buildCostSavingsPayload(form: CostSavingsForm): CostSavingsPayload | null {
  const sites_count = boundedNumber(form.sites_count, 1, 10_000, true);
  const pages_per_site = boundedNumber(form.pages_per_site, 1, 5_000_000, true);
  const monthly_deployments = boundedNumber(form.monthly_deployments, 1, 1_000, true);
  const manual_minutes_per_page = boundedNumber(form.manual_minutes_per_page, 0.05, 120);
  const hourly_rate_usd = boundedNumber(form.hourly_rate_usd, 1, 10_000);
  const automation_coverage_pct = boundedNumber(form.automation_coverage_pct, 1, 100);
  const tool_monthly_cost_usd = boundedNumber(form.tool_monthly_cost_usd, 0, 1_000_000);

  if (
    sites_count === null || pages_per_site === null || monthly_deployments === null ||
    manual_minutes_per_page === null || hourly_rate_usd === null ||
    automation_coverage_pct === null || tool_monthly_cost_usd === null
  ) return null;

  return {
    sites_count,
    pages_per_site,
    monthly_deployments,
    manual_minutes_per_page,
    hourly_rate_usd,
    automation_coverage_pct,
    tool_monthly_cost_usd,
  };
}

export function buildAiImpactPayload(form: AiImpactForm): AiImpactPayload | null {
  const monthly_sessions = boundedNumber(form.monthly_sessions, 1, 1_000_000_000, true);
  const current_ai_visibility_pct = boundedNumber(form.current_ai_visibility_pct, 0, 100);
  const target_ai_visibility_pct = boundedNumber(form.target_ai_visibility_pct, 0, 100);
  const ai_ctr_pct = boundedNumber(form.ai_ctr_pct, 0, 100);
  const conversion_rate_pct = boundedNumber(form.conversion_rate_pct, 0, 100);
  const avg_order_value_usd = boundedNumber(form.avg_order_value_usd, 0, 1_000_000);
  const gross_margin_pct = boundedNumber(form.gross_margin_pct, 0, 100);

  if (
    monthly_sessions === null || current_ai_visibility_pct === null || target_ai_visibility_pct === null ||
    ai_ctr_pct === null || conversion_rate_pct === null || avg_order_value_usd === null || gross_margin_pct === null
  ) return null;

  return {
    monthly_sessions,
    current_ai_visibility_pct,
    target_ai_visibility_pct,
    ai_ctr_pct,
    conversion_rate_pct,
    avg_order_value_usd,
    gross_margin_pct,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function parseProjection<T extends object>(value: unknown, requiredKeys: readonly (keyof T)[]): Projection<T> | null {
  if (!isRecord(value) || value.status !== 'ok') return null;
  const output = value.output;
  if (!isRecord(output)) return null;
  if (requiredKeys.some((key) => typeof output[key as string] !== 'number' || !Number.isFinite(output[key as string]))) {
    return null;
  }
  const assumptions = isRecord(value.assumptions) ? value.assumptions : null;
  return {
    output: output as T,
    assumptionsNote: typeof assumptions?.note === 'string' ? assumptions.note : '',
  };
}

export function parseCostSavingsProjection(value: unknown): Projection<CostSavingsOutput> | null {
  return parseProjection<CostSavingsOutput>(value, [
    'total_pages_in_scope',
    'manual_hours_per_deployment',
    'manual_monthly_hours',
    'automated_monthly_hours_saved',
    'monthly_labor_cost_saved_usd',
    'tool_monthly_cost_usd',
    'net_monthly_savings_usd',
    'annual_net_savings_usd',
    'payback_days',
  ]);
}

export function parseAiImpactProjection(value: unknown): Projection<AiImpactOutput> | null {
  return parseProjection<AiImpactOutput>(value, [
    'current_ai_impressions_monthly',
    'target_ai_impressions_monthly',
    'incremental_ai_impressions_monthly',
    'incremental_clicks_monthly',
    'incremental_conversions_monthly',
    'incremental_revenue_monthly_usd',
    'incremental_gross_profit_monthly_usd',
    'incremental_revenue_annual_usd',
    'incremental_gross_profit_annual_usd',
  ]);
}

export function parseVendorInventory(value: unknown): VendorInventory | null {
  if (!isRecord(value) || value.status !== 'ok' || !Array.isArray(value.vendors)) return null;
  if (!Number.isInteger(value.configured) || !Number.isInteger(value.total)) return null;
  if ((value.configured as number) < 0 || (value.total as number) < 0 || (value.configured as number) > (value.total as number)) {
    return null;
  }
  const vendors: VendorItem[] = [];
  for (const raw of value.vendors) {
    if (
      !isRecord(raw) || typeof raw.key !== 'string' || typeof raw.display_name !== 'string' ||
      typeof raw.category !== 'string' || typeof raw.configured !== 'boolean' || typeof raw.mode !== 'string'
    ) return null;
    vendors.push({
      key: raw.key,
      display_name: raw.display_name,
      category: raw.category,
      configured: raw.configured,
      mode: raw.mode,
    });
  }
  return { configured: value.configured as number, total: value.total as number, vendors };
}

export function parseReadinessInventory(value: unknown): ReadinessInventory | null {
  if (!isRecord(value) || value.status !== 'ok' || !isRecord(value.readiness)) return null;
  const readiness = value.readiness;
  if (
    !Number.isInteger(readiness.configured_integrations) || !Number.isInteger(readiness.total_integrations) ||
    typeof readiness.configured_pct !== 'number' || !Number.isFinite(readiness.configured_pct) ||
    typeof readiness.grade !== 'string' || typeof readiness.production_ready !== 'boolean'
  ) return null;
  return {
    configured_integrations: readiness.configured_integrations as number,
    total_integrations: readiness.total_integrations as number,
    configured_pct: readiness.configured_pct,
    grade: readiness.grade,
    production_ready: readiness.production_ready,
  };
}
