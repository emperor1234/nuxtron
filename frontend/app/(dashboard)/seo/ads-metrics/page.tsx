'use client';

import { useEffect, useState } from 'react';
import { adsApi, AdsCampaign, CampaignMetrics } from '@/app/lib/ads-api';

type MetricsForm = {
  likes: string;
  shares: string;
  comments: string;
  clicks: string;
  impressions: string;
  conversions: string;
  spend: string;
  revenue: string;
};

const EMPTY_FORM: MetricsForm = {
  likes: '0',
  shares: '0',
  comments: '0',
  clicks: '0',
  impressions: '0',
  conversions: '0',
  spend: '0',
  revenue: '0',
};

function MetricBlock({ label, value, color }: Readonly<{ label: string; value: string; color?: string }>) {
  return (
    <div
      style={{
        background: 'var(--bg, #0a0a0a)',
        border: '1px solid var(--line, #333)',
        borderRadius: 10,
        padding: '12px 16px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontWeight: 900, fontSize: 22, marginTop: 6, color: color ?? 'var(--text, #f1f5f9)' }}>{value}</div>
    </div>
  );
}

export default function MetricsPatchPage() {
  const [campaigns, setCampaigns] = useState<AdsCampaign[]>([]);
  const [selected, setSelected] = useState<AdsCampaign | null>(null);
  const [form, setForm] = useState<MetricsForm>({ ...EMPTY_FORM });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const res = await adsApi.listCampaigns();
        setCampaigns(res.campaigns);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load campaigns.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function selectCampaign(id: string) {
    const c = campaigns.find((item) => item.id === id) ?? null;
    setSelected(c);
    if (c) {
      const m = c.metrics;
      setForm({
        likes: String(m.likes),
        shares: String(m.shares),
        comments: String(m.comments),
        clicks: String(m.clicks),
        impressions: String(m.impressions),
        conversions: String(m.conversions),
        spend: String(m.spend),
        revenue: String(m.revenue),
      });
    }
    setError('');
    setInfo('');
  }

  function field(key: keyof MetricsForm, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    setError('');
    try {
      const res = await adsApi.patchMetrics(selected.id, {
        likes: Number.parseInt(form.likes, 10) || 0,
        shares: Number.parseInt(form.shares, 10) || 0,
        comments: Number.parseInt(form.comments, 10) || 0,
        clicks: Number.parseInt(form.clicks, 10) || 0,
        impressions: Number.parseInt(form.impressions, 10) || 0,
        conversions: Number.parseInt(form.conversions, 10) || 0,
        spend: Number.parseFloat(form.spend) || 0,
        revenue: Number.parseFloat(form.revenue) || 0,
      });
      setCampaigns((prev) => prev.map((c) => (c.id === selected.id ? res.campaign : c)));
      setSelected(res.campaign);
      const m: CampaignMetrics = res.campaign.metrics;
      setInfo(`Saved. ROI: ${m.roi_pct.toFixed(1)}% · Success ratio: ${m.success_ratio_pct.toFixed(1)}%`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.');
    } finally {
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg, #0a0a0a)',
    border: '1px solid var(--line, #333)',
    borderRadius: 8,
    color: 'var(--text, #f1f5f9)',
    padding: '8px 10px',
    fontSize: 13,
    boxSizing: 'border-box',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  };

  const m = selected?.metrics;

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg, #0a0a0a)', color: 'var(--text, #f1f5f9)' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ margin: 0, fontSize: 26 }}>Campaign Metrics</h1>
        <p style={{ color: '#64748b', marginTop: 6, marginBottom: 0, fontSize: 14 }}>
          Patch engagement and revenue data. ROI and success ratio are calculated automatically.
        </p>

        {error && (
          <div
            style={{
              marginTop: 14,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ef4444',
              color: '#fca5a5',
              background: '#7f1d1d22',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}
        {info && (
          <div
            style={{
              marginTop: 14,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #22c55e',
              color: '#86efac',
              background: '#14532d22',
              fontSize: 13,
            }}
          >
            {info}
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <div style={labelStyle}>Select Campaign</div>
          {loading ? (
            <div style={{ color: '#64748b', marginTop: 10 }}>Loading…</div>
          ) : (
            <select
              value={selected?.id ?? ''}
              onChange={(e) => selectCampaign(e.target.value)}
              style={{ ...inputStyle, marginTop: 6 }}
            >
              <option value="">— choose a campaign —</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.campaign_name} ({c.platform})
                </option>
              ))}
            </select>
          )}
        </div>

        {selected && (
          <>
            {/* Current computed KPIs */}
            {m && (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 110px), 1fr))',
                  gap: 10,
                  marginTop: 20,
                }}
              >
                <MetricBlock
                  label="ROI"
                  value={`${m.roi_pct.toFixed(1)}%`}
                  color={m.roi_pct >= 0 ? '#22c55e' : '#ef4444'}
                />
                <MetricBlock label="Success" value={`${m.success_ratio_pct.toFixed(1)}%`} />
                <MetricBlock label="Spend" value={`$${m.spend.toFixed(0)}`} />
                <MetricBlock label="Revenue" value={`$${m.revenue.toFixed(0)}`} />
                <MetricBlock label="Conversions" value={String(m.conversions)} />
                <MetricBlock label="Clicks" value={String(m.clicks)} />
                <MetricBlock label="Impressions" value={String(m.impressions)} />
                <MetricBlock label="Likes" value={String(m.likes)} />
                <MetricBlock label="Shares" value={String(m.shares)} />
                <MetricBlock label="Comments" value={String(m.comments)} />
              </div>
            )}

            {/* Edit form */}
            <form
              onSubmit={(e) => void handleSave(e)}
              style={{
                marginTop: 20,
                background: 'var(--bg-soft, #111)',
                border: '1px solid var(--line, #333)',
                borderRadius: 16,
                padding: 18,
              }}
            >
              <h2 style={{ margin: '0 0 16px', fontSize: 15 }}>
                Update Metrics for {'“'}
                {selected.campaign_name}
                {'”'}
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))', gap: 12 }}>
                {(
                  [
                    ['likes', 'Likes'],
                    ['shares', 'Shares'],
                    ['comments', 'Comments'],
                    ['clicks', 'Clicks'],
                    ['impressions', 'Impressions'],
                    ['conversions', 'Conversions'],
                    ['spend', 'Spend ($)'],
                    ['revenue', 'Revenue ($)'],
                  ] as [keyof MetricsForm, string][]
                ).map(([key, label]) => (
                  <div key={key}>
                    <div style={labelStyle}>{label}</div>
                    <input
                      type="number"
                      min="0"
                      step={key === 'spend' || key === 'revenue' ? '0.01' : '1'}
                      value={form[key]}
                      onChange={(e) => field(key, e.target.value)}
                      style={{ ...inputStyle, marginTop: 4 }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16 }}>
                <button
                  type="submit"
                  disabled={saving}
                  style={{
                    padding: '8px 22px',
                    borderRadius: 9,
                    border: '1px solid #22c55e',
                    color: '#86efac',
                    background: '#14532d33',
                    cursor: saving ? 'not-allowed' : 'pointer',
                    fontWeight: 800,
                    fontSize: 13,
                  }}
                >
                  {saving ? 'Saving…' : 'Save Metrics'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
