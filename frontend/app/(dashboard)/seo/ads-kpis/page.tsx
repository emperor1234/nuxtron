'use client';

import { useEffect, useState } from 'react';
import { adsApi, KpiSummary, KpiEngagement } from '@/app/lib/ads-api';

type ForecastData = {
  horizon_days: number;
  projected_spend: number;
  projected_clicks: number;
  projected_conversions: number;
  projected_roi_pct: number;
};

type CreditData = {
  portfolio_credit_total: number;
  portfolio_credit_remaining: number;
  accounts: {
    platform: string;
    account_name: string;
    credit_remaining: number;
    currency: string;
    connected: boolean;
  }[];
};

function KpiCard({
  label,
  value,
  subtext,
  color,
}: Readonly<{ label: string; value: string; subtext?: string; color?: string }>) {
  return (
    <div
      style={{
        background: 'var(--bg-soft)',
        border: '1px solid var(--line)',
        borderRadius: 16,
        padding: '16px 18px',
      }}
    >
      <div style={{ fontSize: 11, color: "var(--muted)", textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 900, marginTop: 8, color: color ?? 'var(--text)' }}>{value}</div>
      {subtext && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>{subtext}</div>}
    </div>
  );
}

function BarChart({
  label,
  items,
  max,
  color,
}: Readonly<{ label: string; items: { label: string; value: number }[]; max: number; color: string }>) {
  return (
    <div>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>{label}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((item) => {
          const pct = max > 0 ? Math.min(100, (item.value / max) * 100) : 0;
          return (
            <div key={item.label}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 12,
                  color: 'var(--muted)',
                  marginBottom: 4,
                }}
              >
                <span>{item.label}</span>
                <span style={{ fontWeight: 700 }}>{item.value.toLocaleString()}</span>
              </div>
              <div style={{ height: 8, background: "var(--line-soft)", borderRadius: 999 }}>
                <div
                  style={{
                    height: 8,
                    background: color,
                    borderRadius: 999,
                    width: `${pct}%`,
                    transition: 'width 0.5s ease',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AdsKpiPage() {
  const [kpis, setKpis] = useState<{ summary: KpiSummary; engagement: KpiEngagement } | null>(null);
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [credits, setCredits] = useState<CreditData | null>(null);
  const [forecastDays, setForecastDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [error, setError] = useState('');

  async function loadAll(days: number) {
    setLoading(true);
    setError('');
    try {
      const [kpiRes, fcRes, credRes] = await Promise.all([adsApi.kpis(), adsApi.forecast(days), adsApi.credits()]);
      setKpis({ summary: kpiRes.summary, engagement: kpiRes.engagement });
      setForecast(fcRes);
      setCredits(credRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load KPIs.');
    } finally {
      setLoading(false);
    }
  }

  async function refreshForecast(days: number) {
    setLoadingForecast(true);
    try {
      const res = await adsApi.forecast(days);
      setForecast(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Forecast failed.');
    } finally {
      setLoadingForecast(false);
    }
  }

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    void loadAll(forecastDays);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleForecastDays(days: number) {
    setForecastDays(days);
    void refreshForecast(days);
  }

  const s = kpis?.summary;
  const eng = kpis?.engagement;

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <h1 style={{ margin: 0, fontSize: 26 }}>Ads KPI & Analytics</h1>
        <p style={{ color: "var(--muted)", marginTop: 6, marginBottom: 0, fontSize: 14 }}>
          Cross-network performance overview, forecasting, and credit balances.
        </p>

        {error && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 10,
              border: '1px solid var(--danger)',
              color: 'var(--danger)',
              background: 'var(--danger-soft)',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <div style={{ marginTop: 40, textAlign: 'center', color: "var(--muted)" }}>Loading KPIs…</div>
        ) : (
          <>
            {/* Primary KPI grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
                gap: 12,
                marginTop: 20,
              }}
            >
              <KpiCard
                label="Campaigns"
                value={String(s?.campaigns_total ?? 0)}
                subtext={`${s?.campaigns_active ?? 0} active`}
              />
              <KpiCard
                label="ROI"
                value={`${(s?.roi_pct ?? 0).toFixed(1)}%`}
                color={(s?.roi_pct ?? 0) >= 0 ? 'var(--success)' : 'var(--danger)'}
                subtext="Revenue vs spend"
              />
              <KpiCard
                label="Success Ratio"
                value={`${(s?.success_ratio_pct ?? 0).toFixed(1)}%`}
                subtext="Conversions / clicks"
              />
              <KpiCard label="Spend" value={`$${(s?.spend ?? 0).toLocaleString()}`} />
              <KpiCard label="Revenue" value={`$${(s?.revenue ?? 0).toLocaleString()}`} color="var(--success)" />
              <KpiCard label="CPA" value={`$${(s?.cpa ?? 0).toFixed(2)}`} subtext="Cost per acquisition" />
              <KpiCard label="CPC" value={`$${(s?.cpc ?? 0).toFixed(2)}`} subtext="Cost per click" />
              <KpiCard label="CTR" value={`${(s?.ctr_pct ?? 0).toFixed(2)}%`} subtext="Click-through rate" />
            </div>

            {/* Engagement + forecast + credits */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginTop: 18 }}>
              {/* Left: engagement bars + forecast */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div
                  style={{
                    background: 'var(--bg-soft)',
                    border: '1px solid var(--line)',
                    borderRadius: 16,
                    padding: 18,
                  }}
                >
                  <BarChart
                    label="Engagement Breakdown"
                    items={[
                      { label: 'Impressions', value: eng?.impressions ?? 0 },
                      { label: 'Clicks', value: eng?.clicks ?? 0 },
                      { label: 'Conversions', value: eng?.conversions ?? 0 },
                      { label: 'Likes', value: eng?.likes ?? 0 },
                      { label: 'Shares', value: eng?.shares ?? 0 },
                      { label: 'Comments', value: eng?.comments ?? 0 },
                    ]}
                    max={Math.max(eng?.impressions ?? 1, 1)}
                    color="var(--info)"
                  />
                </div>

                {/* Forecast */}
                <div
                  style={{
                    background: 'var(--bg-soft)',
                    border: '1px solid var(--line)',
                    borderRadius: 16,
                    padding: 18,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>Forecast</span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {[7, 14, 30, 90].map((d) => (
                        <button
                          key={d}
                          disabled={loadingForecast}
                          onClick={() => handleForecastDays(d)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 700,
                            border: forecastDays === d ? "1px solid var(--brand)" : '1px solid var(--line)',
                            color: forecastDays === d ? 'var(--info-line)' : "var(--muted)",
                            background: forecastDays === d ? 'color-mix(in oklab, var(--info) 13%, transparent)' : 'transparent',
                            cursor: loadingForecast ? 'not-allowed' : 'pointer',
                          }}
                        >
                          {d}d
                        </button>
                      ))}
                    </div>
                  </div>

                  {forecast && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12, marginTop: 14 }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>
                          Projected Spend
                        </div>
                        <div style={{ fontWeight: 900, fontSize: 22, marginTop: 4 }}>
                          ${forecast.projected_spend.toLocaleString()}
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>Projected ROI</div>
                        <div
                          style={{
                            fontWeight: 900,
                            fontSize: 22,
                            marginTop: 4,
                            color: forecast.projected_roi_pct >= 0 ? 'var(--success)' : 'var(--danger)',
                          }}
                        >
                          {forecast.projected_roi_pct.toFixed(1)}%
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>
                          Projected Clicks
                        </div>
                        <div style={{ fontWeight: 900, fontSize: 22, marginTop: 4 }}>
                          {forecast.projected_clicks.toLocaleString()}
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>
                          Projected Conversions
                        </div>
                        <div style={{ fontWeight: 900, fontSize: 22, marginTop: 4 }}>
                          {forecast.projected_conversions.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: credits + pacing */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div
                  style={{
                    background: 'var(--bg-soft)',
                    border: '1px solid var(--line)',
                    borderRadius: 16,
                    padding: 18,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Credit Balances</div>
                  {credits && (
                    <>
                      <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
                        <div>
                          <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>
                            Portfolio Total
                          </div>
                          <div style={{ fontWeight: 900, fontSize: 22 }}>
                            ${credits.portfolio_credit_total.toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase' }}>Remaining</div>
                          <div style={{ fontWeight: 900, fontSize: 22, color: 'var(--success)' }}>
                            ${credits.portfolio_credit_remaining.toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <BarChart
                        label=""
                        items={credits.accounts
                          .filter((a) => a.connected)
                          .map((a) => ({ label: a.account_name || a.platform, value: a.credit_remaining }))}
                        max={credits.portfolio_credit_total || 1}
                        color="var(--success)"
                      />
                    </>
                  )}
                </div>

                {/* Budget pacing */}
                <div
                  style={{
                    background: 'var(--bg-soft)',
                    border: '1px solid var(--line)',
                    borderRadius: 16,
                    padding: 18,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Budget Pacing</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 12,
                          color: 'var(--muted)',
                          marginBottom: 4,
                        }}
                      >
                        <span>Spend vs Daily Budget</span>
                        <span style={{ fontWeight: 700 }}>
                          ${(s?.spend ?? 0).toFixed(0)} / ${(s?.budget_daily ?? 0).toFixed(0)}
                        </span>
                      </div>
                      <div style={{ height: 10, background: "var(--line-soft)", borderRadius: 999 }}>
                        <div
                          style={{
                            height: 10,
                            background: 'var(--warning)',
                            borderRadius: 999,
                            width: `${s?.budget_daily ? Math.min(100, (s.spend / s.budget_daily) * 100) : 0}%`,
                            transition: 'width 0.5s',
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 12,
                          color: 'var(--muted)',
                          marginBottom: 4,
                        }}
                      >
                        <span>Spend vs Total Budget</span>
                        <span style={{ fontWeight: 700 }}>
                          ${(s?.spend ?? 0).toFixed(0)} / ${(s?.budget_total ?? 0).toFixed(0)}
                        </span>
                      </div>
                      <div style={{ height: 10, background: "var(--line-soft)", borderRadius: 999 }}>
                        <div
                          style={{
                            height: 10,
                            background: "var(--brand)",
                            borderRadius: 999,
                            width: `${s?.budget_total ? Math.min(100, (s.spend / s.budget_total) * 100) : 0}%`,
                            transition: 'width 0.5s',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
