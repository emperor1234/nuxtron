'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type RoiSummary = {
  totals?: {
    revenue?: number;
    spend?: number;
    net_profit?: number;
    roas?: number;
    roi_pct?: number;
    tracked_conversions?: number;
    touchpoints?: number;
    spend_entries?: number;
    tracking_coverage_pct?: number;
  };
  channels?: Array<{
    channel: string;
    revenue: number;
    spend: number;
    net_profit: number;
    roas: number;
    roi_pct: number;
  }>;
  campaigns?: Array<{
    campaign: string;
    revenue: number;
    spend: number;
    net_profit: number;
    roas: number;
    roi_pct: number;
  }>;
};

type CalculatorResult = {
  totals?: {
    revenue?: number;
    spend?: number;
    net_profit?: number;
    roas?: number;
    roi_pct?: number;
  };
};

function currency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function pct(value: number): string {
  return `${value.toFixed(2)}%`;
}

export default function SocialMediaRoiPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [summary, setSummary] = useState<RoiSummary>({});
  const [calc, setCalc] = useState<CalculatorResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [postId, setPostId] = useState('post_001');
  const [platform, setPlatform] = useState('linkedin');
  const [campaign, setCampaign] = useState('spring_launch');
  const [destinationUrl, setDestinationUrl] = useState('https://example.com/pricing');
  const [trackedUrl, setTrackedUrl] = useState('');

  const [spendChannel, setSpendChannel] = useState('linkedin');
  const [spendCampaign, setSpendCampaign] = useState('spring_launch');
  const [spendAmount, setSpendAmount] = useState(250);

  const [rev, setRev] = useState(5000);
  const [paidSpend, setPaidSpend] = useState(1200);
  const [teamCost, setTeamCost] = useState(600);
  const [toolsCost, setToolsCost] = useState(180);
  const [agencyCost, setAgencyCost] = useState(0);

  const totals = summary.totals ?? {};

  const cards = useMemo(
    () => [
      { label: 'Attributed Revenue', value: currency(Number(totals.revenue ?? 0)) },
      { label: 'Total Spend', value: currency(Number(totals.spend ?? 0)) },
      { label: 'Net Profit', value: currency(Number(totals.net_profit ?? 0)) },
      { label: 'ROAS', value: Number(totals.roas ?? 0).toFixed(2) },
      { label: 'ROI', value: pct(Number(totals.roi_pct ?? 0)) },
      { label: 'Tracking Coverage', value: pct(Number(totals.tracking_coverage_pct ?? 0)) },
    ],
    [totals]
  );

  async function loadSummary() {
    setError('');
    try {
      const data = (await apiGet(`/analytics/social-roi/summary?window_days=90`, tenantId)) as RoiSummary;
      setSummary(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load ROI summary');
    }
  }

  useEffect(() => {
    setLoading(true);
    void loadSummary().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  async function createTrackedUrl() {
    setError('');
    try {
      const data = (await apiPost(
        '/analytics/revenue-attribution/touchpoints',
        {
          post_id: postId,
          platform,
          campaign,
          destination_url: destinationUrl,
        },
        tenantId
      )) as { touchpoint?: { tracked_url?: string } };
      setTrackedUrl(data.touchpoint?.tracked_url ?? '');
      await loadSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create tracked URL');
    }
  }

  async function recordSpend() {
    setError('');
    try {
      await apiPost(
        '/analytics/social-roi/spend',
        {
          channel: spendChannel,
          campaign: spendCampaign,
          amount: spendAmount,
          currency: 'USD',
        },
        tenantId
      );
      await loadSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to record spend');
    }
  }

  async function runCalculator() {
    setError('');
    try {
      const data = (await apiPost(
        '/analytics/social-roi/calculator',
        {
          attributed_revenue: rev,
          paid_social_spend: paidSpend,
          team_cost: teamCost,
          tools_cost: toolsCost,
          agency_cost: agencyCost,
        },
        tenantId
      )) as CalculatorResult;
      setCalc(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run calculator');
    }
  }

  const panel: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  const input: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '8px 10px',
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1140, margin: '0 auto', display: 'grid', gap: 12 }}>
        <section style={panel}>
          <h1 style={{ marginTop: 0 }}>Social Media ROI</h1>
          <p style={{ color: 'var(--muted)', marginBottom: 0 }}>
            Boosting social media ROI starts with simplified tracking: generate tracked URLs, record spend, and monitor
            revenue-based ROI in one workflow.
          </p>
        </section>

        {error && <section style={{ ...panel, color: '#ef4444' }}>{error}</section>}

        <section style={panel}>
          <label htmlFor="tenant-id" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
            Tenant ID
          </label>
          <input id="tenant-id" value={tenantId} readOnly style={input} />
        </section>

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))',
            gap: 10,
          }}
        >
          {cards.map((card) => (
            <article key={card.label} style={panel}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>{card.label}</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{loading ? '...' : card.value}</div>
            </article>
          ))}
        </section>

        <section style={{ ...panel, display: 'grid', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>1) Simplified Tracking</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 8 }}>
            <input style={input} value={postId} onChange={(e) => setPostId(e.target.value)} placeholder="Post ID" />
            <input
              style={input}
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              placeholder="Platform"
            />
            <input
              style={input}
              value={campaign}
              onChange={(e) => setCampaign(e.target.value)}
              placeholder="Campaign"
            />
            <input
              style={{ ...input, gridColumn: '1 / -1' }}
              value={destinationUrl}
              onChange={(e) => setDestinationUrl(e.target.value)}
              placeholder="Destination URL"
            />
          </div>
          <button onClick={() => void createTrackedUrl()} style={{ ...input, cursor: 'pointer', fontWeight: 700 }}>
            Generate Tracked URL
          </button>
          {trackedUrl && (
            <div style={{ fontSize: 13 }}>
              Tracked URL: <a href={trackedUrl}>{trackedUrl}</a>
            </div>
          )}
        </section>

        <section style={{ ...panel, display: 'grid', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>2) Record Social Spend</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 8 }}>
            <input
              style={input}
              value={spendChannel}
              onChange={(e) => setSpendChannel(e.target.value)}
              placeholder="Channel"
            />
            <input
              style={input}
              value={spendCampaign}
              onChange={(e) => setSpendCampaign(e.target.value)}
              placeholder="Campaign"
            />
            <input
              style={input}
              type="number"
              min={0}
              value={spendAmount}
              onChange={(e) => setSpendAmount(Number(e.target.value))}
              placeholder="Amount"
            />
          </div>
          <button onClick={() => void recordSpend()} style={{ ...input, cursor: 'pointer', fontWeight: 700 }}>
            Record Spend
          </button>
        </section>

        <section style={{ ...panel, display: 'grid', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>3) ROI Calculator</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 8 }}>
            <input
              style={input}
              type="number"
              value={rev}
              onChange={(e) => setRev(Number(e.target.value))}
              placeholder="Revenue"
            />
            <input
              style={input}
              type="number"
              value={paidSpend}
              onChange={(e) => setPaidSpend(Number(e.target.value))}
              placeholder="Paid spend"
            />
            <input
              style={input}
              type="number"
              value={teamCost}
              onChange={(e) => setTeamCost(Number(e.target.value))}
              placeholder="Team cost"
            />
            <input
              style={input}
              type="number"
              value={toolsCost}
              onChange={(e) => setToolsCost(Number(e.target.value))}
              placeholder="Tools cost"
            />
            <input
              style={input}
              type="number"
              value={agencyCost}
              onChange={(e) => setAgencyCost(Number(e.target.value))}
              placeholder="Agency cost"
            />
          </div>
          <button onClick={() => void runCalculator()} style={{ ...input, cursor: 'pointer', fontWeight: 700 }}>
            Calculate ROI
          </button>
          {calc?.totals && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 13 }}>
              <span>Revenue: {currency(Number(calc.totals.revenue ?? 0))}</span>
              <span>Spend: {currency(Number(calc.totals.spend ?? 0))}</span>
              <span>Net: {currency(Number(calc.totals.net_profit ?? 0))}</span>
              <span>ROAS: {Number(calc.totals.roas ?? 0).toFixed(2)}</span>
              <span>ROI: {pct(Number(calc.totals.roi_pct ?? 0))}</span>
            </div>
          )}
        </section>

        <section style={{ ...panel, display: 'grid', gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Channel ROI</h2>
          {(summary.channels ?? []).length === 0 ? (
            <div style={{ color: 'var(--muted)' }}>No channel ROI data yet.</div>
          ) : (
            (summary.channels ?? []).slice(0, 8).map((row) => (
              <div key={row.channel} style={{ borderBottom: '1px solid var(--line)', paddingBottom: 8 }}>
                <strong>{row.channel}</strong> · Revenue {currency(row.revenue)} · Spend {currency(row.spend)} · ROI{' '}
                {pct(row.roi_pct)}
              </div>
            ))
          )}
        </section>
      </div>
    </main>
  );
}
