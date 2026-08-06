'use client';

import { useEffect, useOptimistic, useTransition, useState } from 'react';
import { adsApi, AdsCampaign, AdsPlatform, AdsKeyword, PLATFORM_LABELS } from '@/app/lib/ads-api';

function parseKeywords(raw: string): AdsKeyword[] {
  return raw
    .split(',')
    .map((kw) => kw.trim())
    .filter(Boolean)
    .map((kw) => ({ keyword: kw, cpc_bid: 1.5, cost_today: 0, rank: 0 }));
}

const PLATFORMS: AdsPlatform[] = ['google_ads', 'microsoft_ads', 'amazon_ads', 'apple_search_ads', 'youtube_ads'];

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e',
  draft: '#f59e0b',
  paused: '#6b7280',
};

function Badge({ status }: Readonly<{ status: string }>) {
  const color = STATUS_COLORS[status] ?? '#6b7280';
  return (
    <span
      style={{
        borderRadius: 999,
        padding: '3px 9px',
        fontSize: 11,
        fontWeight: 800,
        background: `${color}22`,
        color,
        border: `1px solid ${color}55`,
      }}
    >
      {status}
    </span>
  );
}

function MetricCell({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontWeight: 800, fontSize: 14, marginTop: 2 }}>{value}</div>
    </div>
  );
}

const DEFAULT_FORM = {
  platform: 'google_ads' as AdsPlatform,
  campaign_name: '',
  objective: 'conversions',
  status: 'draft' as 'draft' | 'active' | 'paused',
  budget_daily: '',
  budget_total: '',
  currency: 'USD',
  title: '',
  description: '',
  cta: 'Learn More',
  start_at: '',
  end_at: '',
  posting_dates: '',
  keywords: '',
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<AdsCampaign[]>([]);
  const [optimisticCampaigns, applyOptimistic] = useOptimistic(
    campaigns,
    (state, update: { id: string; patch: Partial<AdsCampaign> }) =>
      state.map((c) => (c.id === update.id ? { ...c, ...update.patch } : c))
  );
  const [, startTransition] = useTransition();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...DEFAULT_FORM });
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [approvalTarget, setApprovalTarget] = useState<string | null>(null);
  const [approvalEmail, setApprovalEmail] = useState('');
  const [budgetTarget, setBudgetTarget] = useState<string | null>(null);
  const [budgetValue, setBudgetValue] = useState('');
  const [budgetSaving, setBudgetSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const res = await adsApi.listCampaigns();
      setCampaigns(res.campaigns);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load campaigns.');
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    void refresh();
  }, []);

  function field(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const res = await adsApi.createCampaign({
        platform: form.platform,
        campaign_name: form.campaign_name,
        objective: form.objective,
        status: form.status,
        budget_daily: Number.parseFloat(form.budget_daily) || 0,
        budget_total: Number.parseFloat(form.budget_total) || 0,
        currency: form.currency,
        keywords: parseKeywords(form.keywords),
        creative: {
          title: form.title,
          description: form.description,
          cta: form.cta,
          media_urls: [],
        },
        schedule: {
          timezone: 'UTC',
          start_at: form.start_at || null,
          end_at: form.end_at || null,
          auto_post: true,
          posting_dates: form.posting_dates
            .split(',')
            .map((d) => d.trim())
            .filter(Boolean),
        },
      });
      setCampaigns((prev) => [res.campaign, ...prev]);
      setForm({ ...DEFAULT_FORM });
      setShowForm(false);
      setInfo(`Campaign "${res.campaign.campaign_name}" created.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed.');
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish(id: string) {
    setPublishing(id);
    setError('');
    startTransition(() => {
      applyOptimistic({ id, patch: { status: 'active' } });
    });
    try {
      const res = await adsApi.publishCampaign(id, true);
      setCampaigns((prev) => prev.map((c) => (c.id === id ? res.campaign : c)));
      setInfo(`Campaign "${res.campaign.campaign_name}" published.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Publish failed.');
    } finally {
      setPublishing(null);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!globalThis.confirm(`Delete campaign "${name}"? This cannot be undone.`)) return;
    setDeleting(id);
    setError('');
    try {
      await adsApi.deleteCampaign(id);
      setCampaigns((prev) => prev.filter((c) => c.id !== id));
      setInfo(`Campaign deleted.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed.');
    } finally {
      setDeleting(null);
    }
  }

  async function handleClone(id: string, name: string) {
    const newName = `${name} (copy)`;
    setError('');
    try {
      const res = await adsApi.duplicateCampaign(id, newName);
      setCampaigns((prev) => [res.campaign, ...prev]);
      setInfo(`Cloned as "${newName}".`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Clone failed.');
    }
  }

  async function handleBudgetUpdate(id: string) {
    const val = Number.parseFloat(budgetValue);
    if (!Number.isFinite(val) || val < 0) {
      setError('Enter a valid budget amount.');
      return;
    }
    setBudgetSaving(true);
    setError('');
    // Close editor and show new value immediately — reverts if the server call fails
    setBudgetTarget(null);
    setBudgetValue('');
    startTransition(() => {
      applyOptimistic({ id, patch: { budget_daily: val } });
    });
    try {
      const res = await adsApi.updateCampaign(id, { budget_daily: val });
      setCampaigns((prev) => prev.map((c) => (c.id === id ? res.campaign : c)));
      setInfo(`Daily budget updated to $${val.toFixed(2)}/day.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Budget update failed.');
    } finally {
      setBudgetSaving(false);
    }
  }

  async function handleRequestApproval(id: string, email: string) {
    if (!email.trim()) {
      setError('Reviewer email is required.');
      return;
    }
    setError('');
    try {
      const res = await adsApi.requestApproval(id, { reviewer_email: email, auto_publish_on_approve: true });
      setCampaigns((prev) => prev.map((c) => (c.id === id ? res.campaign : c)));
      setInfo(`Approval request sent to ${email}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.');
    }
  }

  function handleBudgetKeyDown(e: React.KeyboardEvent<HTMLInputElement>, id: string) {
    if (e.key === 'Enter') {
      void handleBudgetUpdate(id);
    }
    if (e.key === 'Escape') {
      setBudgetTarget(null);
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

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg, #0a0a0a)', color: 'var(--text, #f1f5f9)' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 26 }}>Campaign Manager</h1>
          <button
            onClick={() => setShowForm((v) => !v)}
            style={{
              padding: '8px 18px',
              borderRadius: 9,
              border: '1px solid #6366f1',
              color: '#93c5fd',
              background: '#6366f122',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: 13,
            }}
          >
            {showForm ? 'Cancel' : '+ New Campaign'}
          </button>
        </div>

        {error && (
          <div
            style={{
              marginTop: 14,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ef4444',
              color: '#dc2626',
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

        {showForm && (
          <form
            onSubmit={(e) => void handleCreate(e)}
            style={{
              marginTop: 18,
              background: 'var(--bg-soft, #111)',
              border: '1px solid var(--line, #333)',
              borderRadius: 16,
              padding: 20,
            }}
          >
            <h2 style={{ margin: '0 0 16px', fontSize: 16 }}>New Campaign</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 14 }}>
              <div>
                <div style={labelStyle}>Platform</div>
                <select
                  value={form.platform}
                  onChange={(e) => field('platform', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                >
                  {PLATFORMS.map((p) => (
                    <option key={p} value={p}>
                      {PLATFORM_LABELS[p]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <div style={labelStyle}>Campaign Name *</div>
                <input
                  required
                  value={form.campaign_name}
                  onChange={(e) => field('campaign_name', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="Spring Sale 2026"
                />
              </div>
              <div>
                <div style={labelStyle}>Objective</div>
                <input
                  value={form.objective}
                  onChange={(e) => field('objective', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="conversions"
                />
              </div>
              <div>
                <div style={labelStyle}>Status</div>
                <select
                  value={form.status}
                  onChange={(e) => field('status', e.target.value as typeof form.status)}
                  style={{ ...inputStyle, marginTop: 4 }}
                >
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
              </div>
              <div>
                <div style={labelStyle}>Daily Budget ($)</div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.budget_daily}
                  onChange={(e) => field('budget_daily', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="120"
                />
              </div>
              <div>
                <div style={labelStyle}>Total Budget ($)</div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.budget_total}
                  onChange={(e) => field('budget_total', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="3000"
                />
              </div>
              <div>
                <div style={labelStyle}>Ad Title *</div>
                <input
                  required
                  value={form.title}
                  onChange={(e) => field('title', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="Scale Paid Ads Fast"
                />
              </div>
              <div>
                <div style={labelStyle}>CTA</div>
                <input
                  value={form.cta}
                  onChange={(e) => field('cta', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="Learn More"
                />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <div style={labelStyle}>Ad Description *</div>
                <textarea
                  required
                  rows={3}
                  value={form.description}
                  onChange={(e) => field('description', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4, resize: 'vertical' }}
                  placeholder="Automate budgets, bids, and reporting from one command center."
                />
              </div>
              <div>
                <div style={labelStyle}>Start Date (ISO)</div>
                <input
                  value={form.start_at}
                  onChange={(e) => field('start_at', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="2026-05-02T08:00:00Z"
                />
              </div>
              <div>
                <div style={labelStyle}>End Date (ISO)</div>
                <input
                  value={form.end_at}
                  onChange={(e) => field('end_at', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="2026-06-01T20:00:00Z"
                />
              </div>
              <div>
                <div style={labelStyle}>Posting Dates (comma-sep, YYYY-MM-DD)</div>
                <input
                  value={form.posting_dates}
                  onChange={(e) => field('posting_dates', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="2026-05-02, 2026-05-05"
                />
              </div>
              <div>
                <div style={labelStyle}>Keywords (comma-sep)</div>
                <input
                  value={form.keywords}
                  onChange={(e) => field('keywords', e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                  placeholder="ai ads, enterprise campaigns"
                />
              </div>
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
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
                {saving ? 'Creating…' : 'Create Campaign'}
              </button>
            </div>
          </form>
        )}

        <div style={{ marginTop: 20 }}>
          {loading && <div style={{ textAlign: 'center', color: '#64748b', marginTop: 40 }}>Loading campaigns…</div>}
          {!loading && campaigns.length === 0 && (
            <div style={{ textAlign: 'center', color: '#64748b', marginTop: 40 }}>
              No campaigns yet. Create one above.
            </div>
          )}
          {!loading && campaigns.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {optimisticCampaigns.map((c) => (
                <div
                  key={c.id}
                  style={{
                    background: 'var(--bg-soft, #111)',
                    border: '1px solid var(--line, #333)',
                    borderRadius: 16,
                    padding: '14px 18px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      flexWrap: 'wrap',
                      gap: 8,
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                        <span style={{ fontWeight: 800, fontSize: 16 }}>{c.campaign_name}</span>
                        <Badge status={c.status} />
                        <ApprovalBadge status={c.approval_status} />
                        <span style={{ fontSize: 12, color: '#64748b' }}>{PLATFORM_LABELS[c.platform]}</span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                        Objective: {c.objective} · Budget:{' '}
                        <button
                          type="button"
                          title="Click to edit daily budget"
                          onClick={() => {
                            setBudgetTarget(budgetTarget === c.id ? null : c.id);
                            setBudgetValue(String(c.budget_daily));
                          }}
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            cursor: 'pointer',
                            color: '#38bdf8',
                            fontWeight: 700,
                            fontSize: 12,
                            textDecoration: 'underline dotted',
                          }}
                        >
                          ${c.budget_daily}/day
                        </button>{' '}
                        · ${c.budget_total} total
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {c.status !== 'active' && (
                        <button
                          type="button"
                          disabled={publishing === c.id}
                          onClick={() => void handlePublish(c.id)}
                          style={{
                            padding: '6px 14px',
                            borderRadius: 8,
                            border: '1px solid #22c55e',
                            color: '#86efac',
                            background: '#14532d22',
                            cursor: publishing === c.id ? 'not-allowed' : 'pointer',
                            fontSize: 12,
                            fontWeight: 700,
                          }}
                        >
                          {publishing === c.id ? 'Publishing…' : 'Publish'}
                        </button>
                      )}
                      {c.approval_status !== 'pending_approval' && (
                        <button
                          type="button"
                          onClick={() => {
                            setApprovalTarget(approvalTarget === c.id ? null : c.id);
                            setApprovalEmail('');
                          }}
                          style={{
                            padding: '6px 12px',
                            borderRadius: 8,
                            border: '1px solid #f59e0b',
                            color: '#fbbf24',
                            background: '#92400e22',
                            cursor: 'pointer',
                            fontSize: 12,
                            fontWeight: 700,
                          }}
                        >
                          Request Review
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => void handleClone(c.id, c.campaign_name)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 8,
                          border: '1px solid #334155',
                          color: 'var(--muted)',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 12,
                          fontWeight: 700,
                        }}
                      >
                        Clone
                      </button>
                      <button
                        type="button"
                        disabled={deleting === c.id}
                        onClick={() => void handleDelete(c.id, c.campaign_name)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 8,
                          border: '1px solid #ef4444',
                          color: '#dc2626',
                          background: 'transparent',
                          cursor: deleting === c.id ? 'not-allowed' : 'pointer',
                          fontSize: 12,
                          fontWeight: 700,
                        }}
                      >
                        {deleting === c.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>

                  {/* Inline daily budget editor */}
                  {budgetTarget === c.id && (
                    <div
                      style={{
                        marginTop: 10,
                        display: 'flex',
                        gap: 8,
                        alignItems: 'center',
                        padding: '10px 12px',
                        background: 'var(--bg, #0a0a0a)',
                        borderRadius: 10,
                        border: '1px solid #0ea5e9',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span style={{ fontSize: 12, color: '#7dd3fc', fontWeight: 700, whiteSpace: 'nowrap' }}>
                        Daily Budget ($)
                      </span>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={budgetValue}
                        onChange={(e) => setBudgetValue(e.target.value)}
                        onKeyDown={(e) => handleBudgetKeyDown(e, c.id)}
                        style={{
                          width: 110,
                          background: '#f6f7fa',
                          border: '1px solid #0ea5e9',
                          borderRadius: 8,
                          color: 'var(--text)',
                          padding: '6px 10px',
                          fontSize: 13,
                          fontWeight: 700,
                        }}
                        autoFocus
                      />
                      <button
                        type="button"
                        disabled={budgetSaving}
                        onClick={() => void handleBudgetUpdate(c.id)}
                        style={{
                          padding: '6px 14px',
                          borderRadius: 8,
                          border: '1px solid #0ea5e9',
                          color: '#7dd3fc',
                          background: '#0c4a6e22',
                          cursor: budgetSaving ? 'not-allowed' : 'pointer',
                          fontSize: 12,
                          fontWeight: 700,
                        }}
                      >
                        {budgetSaving ? 'Saving…' : 'Save'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setBudgetTarget(null)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: 8,
                          border: '1px solid #334155',
                          color: '#64748b',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 12,
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  {/* Inline approval request form */}
                  {approvalTarget === c.id && (
                    <div
                      style={{
                        marginTop: 10,
                        display: 'flex',
                        gap: 8,
                        alignItems: 'center',
                        padding: '10px 12px',
                        background: 'var(--bg, #0a0a0a)',
                        borderRadius: 10,
                        border: '1px solid #92400e',
                        flexWrap: 'wrap',
                      }}
                    >
                      <input
                        placeholder="Reviewer email"
                        value={approvalEmail}
                        onChange={(e) => setApprovalEmail(e.target.value)}
                        style={{
                          flex: 1,
                          minWidth: 180,
                          background: '#f6f7fa',
                          border: '1px solid #334155',
                          borderRadius: 8,
                          color: 'var(--text)',
                          padding: '6px 10px',
                          fontSize: 12,
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => void handleRequestApproval(c.id, approvalEmail)}
                        style={{
                          padding: '6px 14px',
                          borderRadius: 8,
                          border: '1px solid #f59e0b',
                          color: '#fbbf24',
                          background: '#92400e22',
                          cursor: 'pointer',
                          fontSize: 12,
                          fontWeight: 700,
                        }}
                      >
                        Send
                      </button>
                      <button
                        type="button"
                        onClick={() => setApprovalTarget(null)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: 8,
                          border: '1px solid #334155',
                          color: '#64748b',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 12,
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  {/* Metrics row */}
                  <div
                    style={{
                      display: 'flex',
                      gap: 20,
                      marginTop: 12,
                      padding: '10px 14px',
                      background: 'var(--bg, #0a0a0a)',
                      borderRadius: 10,
                      flexWrap: 'wrap',
                    }}
                  >
                    <MetricCell label="Likes" value={String(c.metrics.likes)} />
                    <MetricCell label="Shares" value={String(c.metrics.shares)} />
                    <MetricCell label="Comments" value={String(c.metrics.comments)} />
                    <MetricCell label="Clicks" value={String(c.metrics.clicks)} />
                    <MetricCell label="Impressions" value={String(c.metrics.impressions)} />
                    <MetricCell label="Conversions" value={String(c.metrics.conversions)} />
                    <MetricCell label="Spend" value={`$${c.metrics.spend.toFixed(0)}`} />
                    <MetricCell label="Revenue" value={`$${c.metrics.revenue.toFixed(0)}`} />
                    <MetricCell label="ROI" value={`${c.metrics.roi_pct.toFixed(1)}%`} />
                    <MetricCell label="Success" value={`${c.metrics.success_ratio_pct.toFixed(1)}%`} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

const APPROVAL_STYLES: Record<string, { bg: string; color: string; border: string; label: string }> = {
  pending_approval: { bg: '#92400e22', color: '#fbbf24', border: '#92400e', label: '⏳ Pending Review' },
  approved: { bg: '#14532d22', color: '#86efac', border: '#14532d', label: '✓ Approved' },
  rejected: { bg: '#7f1d1d22', color: '#dc2626', border: '#7f1d1d', label: '✗ Rejected' },
};

function ApprovalBadge({ status }: Readonly<{ status: string | null | undefined }>) {
  if (!status) return null;
  const s = APPROVAL_STYLES[status];
  if (!s) return null;
  return (
    <span
      style={{
        borderRadius: 999,
        padding: '2px 8px',
        fontSize: 10,
        fontWeight: 700,
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
      }}
    >
      {s.label}
    </span>
  );
}
