import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend } = vi.hoisted(() => ({ apiGet: vi.fn(), apiSend: vi.fn() }));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant: () => 'workspace-test' }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import AiSearchImpactCalculatorPage from './page';

afterEach(() => cleanup());
beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
});

function completeCostForm() {
  fireEvent.change(screen.getByLabelText('Sites in scope'), { target: { value: '20' } });
  fireEvent.change(screen.getByLabelText('Pages per site'), { target: { value: '1000' } });
  fireEvent.change(screen.getByLabelText('Monthly deployments'), { target: { value: '4' } });
  fireEvent.change(screen.getByLabelText('Manual minutes per page'), { target: { value: '1.25' } });
  fireEvent.change(screen.getByLabelText('Labor cost per hour (USD)'), { target: { value: '100' } });
  fireEvent.change(screen.getByLabelText('Automation coverage (%)'), { target: { value: '80' } });
  fireEvent.change(screen.getByLabelText('Tool cost per month (USD)'), { target: { value: '500' } });
}

function completeImpactForm() {
  fireEvent.change(screen.getByLabelText('Monthly site sessions'), { target: { value: '100000' } });
  fireEvent.change(screen.getByLabelText('Current AI visibility (%)'), { target: { value: '0' } });
  fireEvent.change(screen.getByLabelText('Target AI visibility (%)'), { target: { value: '10' } });
  fireEvent.change(screen.getByLabelText('AI-search click-through rate (%)'), { target: { value: '15' } });
  fireEvent.change(screen.getByLabelText('Conversion rate (%)'), { target: { value: '2.5' } });
  fireEvent.change(screen.getByLabelText('Average order value (USD)'), { target: { value: '120' } });
  fireEvent.change(screen.getByLabelText('Gross margin (%)'), { target: { value: '60' } });
}

const costResponse = {
  status: 'ok',
  output: {
    total_pages_in_scope: 20_000,
    manual_hours_per_deployment: 416.67,
    manual_monthly_hours: 1666.67,
    automated_monthly_hours_saved: 0,
    monthly_labor_cost_saved_usd: 0,
    tool_monthly_cost_usd: 500,
    net_monthly_savings_usd: -500,
    annual_net_savings_usd: -6000,
    payback_days: 0,
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

describe('AI Search Impact Calculator page', () => {
  it('does not prefill customer assumptions or call APIs before the user acts', () => {
    render(<AiSearchImpactCalculatorPage />);

    expect((screen.getByLabelText('Sites in scope') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Monthly site sessions') as HTMLInputElement).value).toBe('');
    expect((screen.getByRole('button', { name: 'Calculate savings scenario' }) as HTMLButtonElement).disabled).toBe(true);
    expect(apiSend).not.toHaveBeenCalled();
    expect(apiGet).not.toHaveBeenCalled();
    expect(screen.getByText(/not measured performance/i)).toBeTruthy();
  });

  it('submits the exact validated labor assumptions and labels the output as a model', async () => {
    apiSend.mockResolvedValue(costResponse);
    render(<AiSearchImpactCalculatorPage />);
    completeCostForm();
    fireEvent.click(screen.getByRole('button', { name: 'Calculate savings scenario' }));

    expect(await screen.findByText('Estimated labor savings')).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/search-everywhere/cost-savings-calculator', 'POST', {
      sites_count: 20,
      pages_per_site: 1000,
      monthly_deployments: 4,
      manual_minutes_per_page: 1.25,
      hourly_rate_usd: 100,
      automation_coverage_pct: 80,
      tool_monthly_cost_usd: 500,
    }, 'workspace-test');
    expect(screen.getByText('Modeled, not measured')).toBeTruthy();
    expect(screen.getByText('-$500.00')).toBeTruthy();
  });

  it('allows zero-valued assumptions where the backend accepts them and submits an AI-impact scenario', async () => {
    apiSend.mockResolvedValue(impactResponse);
    render(<AiSearchImpactCalculatorPage />);
    completeImpactForm();
    fireEvent.click(screen.getByRole('button', { name: 'Calculate AI-search scenario' }));

    expect(await screen.findByText('Estimated AI-search impact')).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/search-everywhere/ai-search-impact-calculator', 'POST', {
      monthly_sessions: 100000,
      current_ai_visibility_pct: 0,
      target_ai_visibility_pct: 10,
      ai_ctr_pct: 15,
      conversion_rate_pct: 2.5,
      avg_order_value_usd: 120,
      gross_margin_pct: 60,
    }, 'workspace-test');
    expect(screen.getByText('1,500')).toBeTruthy();
  });

  it('calls readiness endpoints separately and distinguishes server setup from live provider connectivity', async () => {
    apiGet
      .mockResolvedValueOnce({
        status: 'ok',
        configured: 1,
        total: 2,
        vendors: [
          { key: 'cloudflare', display_name: 'Cloudflare', category: 'WAF', configured: true, mode: 'api' },
          { key: 'openai', display_name: 'OpenAI crawler', category: 'Crawler target', configured: true, mode: 'crawler-target' },
        ],
      })
      .mockResolvedValueOnce({
        status: 'ok',
        readiness: { configured_integrations: 1, total_integrations: 2, configured_pct: 50, grade: 'C', production_ready: false },
      });
    render(<AiSearchImpactCalculatorPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Check server setup' }));

    expect(await screen.findByText('OpenAI crawler')).toBeTruthy();
    expect(screen.getByText('Tracked target')).toBeTruthy();
    expect(screen.getByText('Configured on server')).toBeTruthy();
    expect(screen.getByText(/not a production certification/i)).toBeTruthy();
    expect(apiGet).toHaveBeenNthCalledWith(1, '/search-everywhere/vendors', 'workspace-test');
    expect(apiGet).toHaveBeenNthCalledWith(2, '/search-everywhere/readiness', 'workspace-test');
  });
});
