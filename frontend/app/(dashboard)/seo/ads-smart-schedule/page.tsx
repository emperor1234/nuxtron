'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  adsApi,
  AdsCampaign,
  AdsPlatform,
  PLATFORM_LABELS,
  BestTimeRecommendation,
  AudienceInsights,
  AbTestSuggestions,
} from '@/app/lib/ads-api';

// ─── Constants ────────────────────────────────────────────────────────────────
const PLATFORMS: AdsPlatform[] = ['google_ads', 'microsoft_ads', 'amazon_ads', 'apple_search_ads', 'youtube_ads'];
const OBJECTIVES = ['conversions', 'brand_awareness', 'traffic'];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

// ─── Helpers ─────────────────────────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score === 0) return 'var(--neutral-soft)';
  if (score < 40) return 'var(--success-soft)';
  if (score < 60) return 'var(--success-line)';
  if (score < 75) return 'var(--success)';
  if (score < 85) return 'var(--success)';
  if (score < 93) return 'var(--success)';
  return 'var(--success-ink)';
}

function fmtHour(h: number): string {
  if (h === 0) return '12a';
  if (h < 12) return `${h}a`;
  if (h === 12) return '12p';
  return `${h - 12}p`;
}

function fmtReach(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M`;
  return n.toLocaleString();
}

function hourLabelColor(h: number, humanWindow: number[], avoidHours: number[]): string {
  if (humanWindow.includes(h)) return 'var(--info)';
  if (avoidHours.includes(h)) return 'var(--danger)';
  return 'var(--neutral)';
}

function cellBorder(isHuman: boolean, isAvoid: boolean): string {
  if (isHuman) return '1px solid var(--info)';
  if (isAvoid) return '1px solid var(--danger-ink)';
  return '1px solid transparent';
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function Section({ title, children }: Readonly<{ title: string; children: React.ReactNode }>) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontSize: 16,
          fontWeight: 800,
          marginBottom: 14,
          color: 'var(--text)',
          borderBottom: '1px solid var(--line)',
          paddingBottom: 8,
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function HeatmapGrid({
  heatmap,
  humanWindow,
  avoidHours,
}: Readonly<{
  heatmap: Record<string, Record<string, number>>;
  humanWindow: number[];
  avoidHours: number[];
}>) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `56px repeat(24, 26px)`, gap: 2, marginBottom: 2 }}>
        <div />
        {HOURS.map((h) => (
          <div
            key={h}
            style={{
              fontSize: 9,
              textAlign: 'center',
              fontWeight: humanWindow.includes(h) ? 800 : 400,
              color: hourLabelColor(h, humanWindow, avoidHours),
            }}
          >
            {fmtHour(h)}
          </div>
        ))}
      </div>
      {DAYS.map((day) => {
        const dayData = heatmap[day] ?? {};
        return (
          <div
            key={day}
            style={{ display: 'grid', gridTemplateColumns: `56px repeat(24, 26px)`, gap: 2, marginBottom: 2 }}
          >
            <div style={{ fontSize: 11, color: 'var(--muted)', display: 'flex', alignItems: 'center' }}>{day}</div>
            {HOURS.map((h) => {
              const score = dayData[String(h)] ?? 0;
              const isHuman = humanWindow.includes(h);
              const isAvoid = avoidHours.includes(h);
              return (
                <div
                  key={h}
                  title={score > 0 ? `${day} ${fmtHour(h)}: score ${score}` : `${day} ${fmtHour(h)}: low activity`}
                  style={{
                    height: 20,
                    borderRadius: 3,
                    background: scoreColor(score),
                    border: cellBorder(isHuman, isAvoid),
                    opacity: isAvoid && score === 0 ? 0.3 : 1,
                  }}
                />
              );
            })}
          </div>
        );
      })}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 10, fontSize: 10, flexWrap: 'wrap' }}>
        <span style={{ color: "var(--muted)" }}>Low</span>
        {[0, 30, 55, 72, 85, 93].map((s) => (
          <div
            key={s}
            style={{ width: 14, height: 14, borderRadius: 3, background: scoreColor(s), border: '1px solid var(--line)' }}
          />
        ))}
        <span style={{ color: "var(--muted)" }}>High</span>
        <span style={{ width: 1, background: 'var(--ink-2)', height: 14, display: 'inline-block', margin: '0 6px' }} />
        <div style={{ width: 14, height: 14, borderRadius: 3, background: 'var(--info-soft)', border: "1px solid var(--brand)" }} />
        <span style={{ color: 'var(--info)' }}>Human review window</span>
        <div style={{ width: 14, height: 14, borderRadius: 3, background: 'var(--danger-soft)', border: '1px solid var(--danger-ink)' }} />
        <span style={{ color: 'var(--danger)' }}>Avoid</span>
      </div>
    </div>
  );
}

function ApprovalBadge({ status }: Readonly<{ status: string | null | undefined }>) {
  if (!status) return null;
  const cfg: Record<string, { label: string; color: string }> = {
    pending_approval: { label: 'Pending Review', color: 'var(--warning)' },
    approved: { label: 'Approved', color: 'var(--success)' },
    rejected: { label: 'Rejected', color: 'var(--danger)' },
  };
  const c = cfg[status];
  if (!c) return null;
  return (
    <span
      style={{
        borderRadius: 999,
        padding: '2px 8px',
        fontSize: 10,
        fontWeight: 700,
        background: `color-mix(in srgb, ${c.color} 13.33%, transparent)`,
        color: c.color,
        border: `1px solid color-mix(in srgb, ${c.color} 33.33%, transparent)`,
      }}
    >
      {c.label}
    </span>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function SmartSchedulePage() {
  const [platform, setPlatform] = useState<AdsPlatform>('google_ads');
  const [objective, setObjective] = useState('conversions');
  const [bestTime, setBestTime] = useState<BestTimeRecommendation | null>(null);
  const [loadingBT, setLoadingBT] = useState(false);

  const [campaigns, setCampaigns] = useState<AdsCampaign[]>([]);
  const [insights, setInsights] = useState<AudienceInsights | null>(null);
  const [abData, setAbData] = useState<AbTestSuggestions | null>(null);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [loadingAb, setLoadingAb] = useState(false);

  // Approval form state
  const [approvalTarget, setApprovalTarget] = useState<string | null>(null);
  const [approvalEmail, setApprovalEmail] = useState('');
  const [approvalMsg, setApprovalMsg] = useState('');
  const [autoPublish, setAutoPublish] = useState(true);
  const [approvalSaving, setApprovalSaving] = useState(false);

  // Decide form state
  const [decideTarget, setDecideTarget] = useState<string | null>(null);
  const [decideReason, setDecideReason] = useState('');
  const [decideName, setDecideName] = useState('');
  const [decideSaving, setDecideSaving] = useState(false);

  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const loadBestTime = useCallback(async () => {
    setLoadingBT(true);
    setError('');
    try {
      const res = await adsApi.bestTime(platform, objective);
      setBestTime(res);
    } catch {
      setError('Failed to load best time data.');
    } finally {
      setLoadingBT(false);
    }
  }, [platform, objective]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadBestTime();
  }, [loadBestTime]);

  useEffect(() => {
    async function loadSidePanels() {
      try {
        const [cRes, insRes] = await Promise.all([adsApi.listCampaigns(), adsApi.audienceInsights()]);
        setCampaigns(cRes.campaigns);
        setInsights(insRes);
        if (cRes.campaigns.length > 0) {
          setSelectedCampaign(cRes.campaigns[0].id);
        }
      } catch {
        /* non-critical */
      }
    }
    void loadSidePanels();
  }, []);

  async function loadAbTest(id: string) {
    setLoadingAb(true);
    setAbData(null);
    try {
      const res = await adsApi.abTestSuggestions(id);
      setAbData(res);
    } catch {
      setError('Failed to load A/B suggestions.');
    } finally {
      setLoadingAb(false);
    }
  }

  async function handleRequestApproval(campaignId: string) {
    if (!approvalEmail.trim()) {
      setError('Reviewer email is required.');
      return;
    }
    setApprovalSaving(true);
    setError('');
    try {
      const res = await adsApi.requestApproval(campaignId, {
        reviewer_email: approvalEmail,
        message: approvalMsg,
        auto_publish_on_approve: autoPublish,
      });
      setCampaigns((prev) => prev.map((c) => (c.id === campaignId ? res.campaign : c)));
      setApprovalTarget(null);
      setApprovalEmail('');
      setApprovalMsg('');
      setInfo(`Approval request sent to ${approvalEmail}`);
    } catch {
      setError('Failed to send approval request.');
    } finally {
      setApprovalSaving(false);
    }
  }

  async function handleDecide(campaignId: string, decision: 'approved' | 'rejected') {
    setDecideSaving(true);
    setError('');
    try {
      const res = await adsApi.approveOrReject(campaignId, {
        decision,
        reason: decideReason,
        reviewer_name: decideName || 'Reviewer',
      });
      setCampaigns((prev) => prev.map((c) => (c.id === campaignId ? res.campaign : c)));
      setDecideTarget(null);
      setDecideReason('');
      setDecideName('');
      setInfo(`Campaign ${decision}.`);
    } catch {
      setError(`Failed to ${decision} campaign.`);
    } finally {
      setDecideSaving(false);
    }
  }

  const pending = campaigns.filter((c) => c.approval_status === 'pending_approval');

  return (
    <main style={{ padding: '28px 32px', maxWidth: 1180, margin: '0 auto', fontFamily: 'inherit', color: 'var(--text)' }}>
      <h1 style={{ fontSize: 26, fontWeight: 900, marginBottom: 4 }}>Smart Schedule &amp; Approval</h1>
      <p style={{ color: "var(--muted)", marginBottom: 28, fontSize: 14 }}>
        Best-time heatmap · Human touch windows · Approval workflow · A/B creative testing · Audience insights
      </p>

      {error && (
        <div
          style={{
            background: 'var(--danger-soft)',
            color: 'var(--danger)',
            borderRadius: 10,
            padding: '10px 16px',
            marginBottom: 14,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}
      {info && (
        <div
          style={{
            background: 'var(--success-soft)',
            color: 'var(--success-ink)',
            borderRadius: 10,
            padding: '10px 16px',
            marginBottom: 14,
            fontSize: 13,
          }}
        >
          {info}
        </div>
      )}

      {/* ── Best Time Heatmap ───────────────────────────────────────────────── */}
      <Section title="Best Time to Run Ads">
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="bt-platform" style={{ fontSize: 11, color: "var(--muted)", display: 'block', marginBottom: 4 }}>
              Platform
            </label>
            <select
              id="bt-platform"
              value={platform}
              onChange={(e) => setPlatform(e.target.value as AdsPlatform)}
              style={{
                background: "var(--bg)",
                border: '1px solid var(--ink-2)',
                borderRadius: 8,
                color: 'var(--text)',
                padding: '6px 10px',
                fontSize: 13,
              }}
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {PLATFORM_LABELS[p]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="bt-objective" style={{ fontSize: 11, color: "var(--muted)", display: 'block', marginBottom: 4 }}>
              Objective
            </label>
            <select
              id="bt-objective"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              style={{
                background: "var(--bg)",
                border: '1px solid var(--ink-2)',
                borderRadius: 8,
                color: 'var(--text)',
                padding: '6px 10px',
                fontSize: 13,
              }}
            >
              {OBJECTIVES.map((o) => (
                <option key={o} value={o}>
                  {o.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loadingBT && <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading heatmap…</div>}
        {bestTime && !loadingBT && (
          <>
            <HeatmapGrid
              heatmap={bestTime.heatmap}
              humanWindow={bestTime.human_review_window}
              avoidHours={bestTime.avoid_hours}
            />
            <div style={{ marginTop: 14, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <div
                style={{
                  background: 'var(--card)fff',
                  border: '1px solid var(--line)',
                  borderRadius: 10,
                  padding: '10px 16px',
                  flex: 1,
                  minWidth: 200,
                }}
              >
                <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Peak Hour
                </div>
                <div style={{ fontSize: 22, fontWeight: 900, color: 'var(--success)' }}>{fmtHour(bestTime.peak_hour)}</div>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>across {bestTime.best_days.join(', ')}</div>
              </div>
              <div
                style={{
                  background: 'var(--card)fff',
                  border: '1px solid var(--line)',
                  borderRadius: 10,
                  padding: '10px 16px',
                  flex: 1,
                  minWidth: 200,
                }}
              >
                <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Human Review Window
                </div>
                <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--info)' }}>
                  {bestTime.human_review_window.map(fmtHour).join(' – ')}
                </div>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Schedule human check-in here</div>
              </div>
              <div
                style={{
                  background: 'var(--card)fff',
                  border: '1px solid var(--line)',
                  borderRadius: 10,
                  padding: '10px 16px',
                  flex: 2,
                  minWidth: 240,
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--muted)",
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 4,
                  }}
                >
                  AI Rationale
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>{bestTime.rationale}</div>
              </div>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: '10px 14px',
                background: 'var(--card)fff',
                borderRadius: 10,
                border: '1px solid var(--line)',
                fontSize: 12,
              }}
            >
              <span style={{ color: "var(--muted)", marginRight: 8 }}>Peak hour per platform:</span>
              {Object.entries(bestTime.all_platforms_peak).map(([p, h]) => (
                <span key={p} style={{ marginRight: 12, color: 'var(--text)' }}>
                  <span style={{ color: "var(--muted)" }}>{PLATFORM_LABELS[p as AdsPlatform] ?? p}: </span>
                  <strong>{fmtHour(h)}</strong>
                </span>
              ))}
            </div>
          </>
        )}
      </Section>

      {/* ── Human Approval Queue ─────────────────────────────────────────────── */}
      <Section title={pending.length > 0 ? `Approval Queue (${pending.length})` : 'Approval Queue'}>
        {pending.length === 0 && (
          <div style={{ color: "var(--muted)", fontSize: 13, padding: '10px 0' }}>No campaigns pending review.</div>
        )}
        {pending.map((c) => (
          <div
            key={c.id}
            style={{
              background: 'var(--card)fff',
              border: '1px solid var(--ink-2)',
              borderRadius: 12,
              padding: '14px 18px',
              marginBottom: 10,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              <div>
                <span style={{ fontWeight: 800, fontSize: 15 }}>{c.campaign_name}</span>
                <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 10 }}>{PLATFORM_LABELS[c.platform]}</span>
                {c.reviewer_email && (
                  <span style={{ fontSize: 11, color: 'var(--muted)', marginLeft: 10 }}>→ {c.reviewer_email}</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => {
                    setDecideTarget(c.id);
                  }}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 8,
                    background: 'var(--info-soft)',
                    border: "1px solid var(--brand)",
                    color: 'var(--info-line)',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Review
                </button>
              </div>
            </div>
            {c.approval_message && (
              <div style={{ marginTop: 8, fontSize: 12, color: "var(--muted)", fontStyle: 'italic' }}>
                {'“'}
                {c.approval_message}
                {'”'}
              </div>
            )}
            {decideTarget === c.id && (
              <div
                style={{
                  marginTop: 12,
                  padding: '12px 14px',
                  background: "var(--bg)",
                  borderRadius: 10,
                  border: '1px solid var(--line)',
                }}
              >
                <div style={{ display: 'flex', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
                  <input
                    placeholder="Your name"
                    value={decideName}
                    onChange={(e) => setDecideName(e.target.value)}
                    style={{
                      flex: 1,
                      minWidth: 140,
                      background: "var(--bg)",
                      border: '1px solid var(--ink-2)',
                      borderRadius: 8,
                      color: 'var(--text)',
                      padding: '6px 10px',
                      fontSize: 12,
                    }}
                  />
                  <input
                    placeholder="Reason / notes (optional)"
                    value={decideReason}
                    onChange={(e) => setDecideReason(e.target.value)}
                    style={{
                      flex: 2,
                      minWidth: 200,
                      background: "var(--bg)",
                      border: '1px solid var(--ink-2)',
                      borderRadius: 8,
                      color: 'var(--text)',
                      padding: '6px 10px',
                      fontSize: 12,
                    }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    disabled={decideSaving}
                    onClick={() => void handleDecide(c.id, 'approved')}
                    style={{
                      padding: '6px 16px',
                      borderRadius: 8,
                      background: 'var(--success-soft)',
                      border: '1px solid var(--success)',
                      color: 'var(--success-ink)',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {decideSaving ? '…' : 'Approve'}
                  </button>
                  <button
                    type="button"
                    disabled={decideSaving}
                    onClick={() => void handleDecide(c.id, 'rejected')}
                    style={{
                      padding: '6px 16px',
                      borderRadius: 8,
                      background: 'var(--danger-soft)',
                      border: '1px solid var(--danger)',
                      color: 'var(--danger)',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {decideSaving ? '…' : 'Reject'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecideTarget(null)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 8,
                      background: 'transparent',
                      border: '1px solid var(--ink-2)',
                      color: "var(--muted)",
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Request approval for any campaign */}
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>Send a campaign for human review:</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <select
              value={approvalTarget ?? ''}
              onChange={(e) => setApprovalTarget(e.target.value || null)}
              style={{
                background: "var(--bg)",
                border: '1px solid var(--ink-2)',
                borderRadius: 8,
                color: 'var(--text)',
                padding: '6px 10px',
                fontSize: 12,
                flex: 1,
                minWidth: 160,
              }}
            >
              <option value="">— Select campaign —</option>
              {campaigns
                .filter((c) => c.approval_status !== 'pending_approval')
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.campaign_name}
                  </option>
                ))}
            </select>
            {approvalTarget && (
              <>
                <input
                  placeholder="Reviewer email"
                  value={approvalEmail}
                  onChange={(e) => setApprovalEmail(e.target.value)}
                  style={{
                    flex: 1,
                    minWidth: 180,
                    background: "var(--bg)",
                    border: '1px solid var(--ink-2)',
                    borderRadius: 8,
                    color: 'var(--text)',
                    padding: '6px 10px',
                    fontSize: 12,
                  }}
                />
                <input
                  placeholder="Message (optional)"
                  value={approvalMsg}
                  onChange={(e) => setApprovalMsg(e.target.value)}
                  style={{
                    flex: 2,
                    minWidth: 180,
                    background: "var(--bg)",
                    border: '1px solid var(--ink-2)',
                    borderRadius: 8,
                    color: 'var(--text)',
                    padding: '6px 10px',
                    fontSize: 12,
                  }}
                />
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    fontSize: 12,
                    color: 'var(--muted)',
                    cursor: 'pointer',
                  }}
                >
                  <input type="checkbox" checked={autoPublish} onChange={(e) => setAutoPublish(e.target.checked)} />{' '}
                  Auto-publish on approve
                </label>
                <button
                  type="button"
                  disabled={approvalSaving}
                  onClick={() => void handleRequestApproval(approvalTarget)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 8,
                    background: 'var(--info-soft)',
                    border: "1px solid var(--brand)",
                    color: 'var(--info-line)',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {approvalSaving ? 'Sending…' : 'Send for Review'}
                </button>
              </>
            )}
          </div>
        </div>
      </Section>

      {/* ── A/B Creative Test ────────────────────────────────────────────────── */}
      <Section title="A/B Creative Suggestions">
        <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label htmlFor="ab-campaign" style={{ fontSize: 11, color: "var(--muted)", display: 'block', marginBottom: 4 }}>
              Campaign
            </label>
            <select
              id="ab-campaign"
              value={selectedCampaign}
              onChange={(e) => setSelectedCampaign(e.target.value)}
              style={{
                background: "var(--bg)",
                border: '1px solid var(--ink-2)',
                borderRadius: 8,
                color: 'var(--text)',
                padding: '6px 10px',
                fontSize: 12,
                minWidth: 200,
              }}
            >
              <option value="">— Select —</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.campaign_name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            disabled={!selectedCampaign || loadingAb}
            onClick={() => selectedCampaign && void loadAbTest(selectedCampaign)}
            style={{
              padding: '7px 16px',
              borderRadius: 8,
              background: "var(--bg)",
              border: '1px solid var(--ink-2)',
              color: 'var(--text)',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {loadingAb ? 'Generating…' : 'Generate Variants'}
          </button>
        </div>

        {abData && (
          <div>
            <div
              style={{
                marginBottom: 10,
                padding: '10px 14px',
                background: 'var(--card)fff',
                borderRadius: 10,
                border: '1px solid var(--line)',
                fontSize: 12,
              }}
            >
              <span style={{ color: "var(--muted)" }}>Original: </span>
              <strong>{abData.original.title}</strong>
              <span style={{ color: "var(--muted)", marginLeft: 10 }}>CTA: </span>
              {abData.original.cta}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 10 }}>
              {abData.suggestions.map((v) => (
                <div
                  key={v.variant}
                  style={{ background: 'var(--card)fff', border: '1px solid var(--line)', borderRadius: 12, padding: '12px 14px' }}
                >
                  <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}
                  >
                    <span style={{ fontWeight: 800, fontSize: 13, color: 'var(--info)' }}>Variant {v.variant}</span>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{v.label}</span>
                    <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--success)' }}>
                      +{v.predicted_ctr_lift_pct}% CTR
                    </span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{v.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6, lineHeight: 1.4 }}>
                    {v.description}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--info)' }}>CTA: {v.cta}</div>
                  <div style={{ fontSize: 10, color: 'var(--ink-2)', marginTop: 6, lineHeight: 1.4 }}>{v.rationale}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>

      {/* ── Audience Insights ────────────────────────────────────────────────── */}
      <Section title="Audience Insights">
        {!insights && <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading insights…</div>}
        {insights && (
          <div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 170px), 1fr))',
                gap: 10,
                marginBottom: 14,
              }}
            >
              {[
                { label: 'Est. Total Reach', value: fmtReach(insights.estimated_reach), color: 'var(--success)' },
                {
                  label: 'Audience Overlap',
                  value: `${insights.audience_overlap_pct}%`,
                  color: insights.audience_overlap_pct > 60 ? 'var(--warning)' : 'var(--success)',
                },
                {
                  label: 'Keyword Saturation',
                  value: `${insights.keyword_saturation_score}/100`,
                  color: insights.keyword_saturation_score > 70 ? 'var(--danger)' : 'var(--success)',
                },
                { label: 'Keywords Indexed', value: String(insights.keywords_indexed), color: 'var(--text)' },
                { label: 'Freq Cap Suggestion', value: `${insights.frequency_cap_suggestion}×/day`, color: 'var(--text)' },
                { label: 'Active Platforms', value: String(insights.platforms_active.length), color: 'var(--text)' },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  style={{
                    background: 'var(--card)fff',
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: '10px 14px',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: 10, color: "var(--muted)", textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {kpi.label}
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 900, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
                </div>
              ))}
            </div>
            {insights.top_keywords.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 11, color: "var(--muted)", marginRight: 8 }}>Top keywords:</span>
                {insights.top_keywords.map((kw) => (
                  <span
                    key={kw}
                    style={{
                      display: 'inline-block',
                      margin: '2px 4px',
                      padding: '2px 8px',
                      borderRadius: 999,
                      background: "var(--bg)",
                      border: '1px solid var(--ink-2)',
                      fontSize: 11,
                      color: 'var(--muted)',
                    }}
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {insights.recommendations.map((rec, _i) => (
                <div
                  key={rec.slice(0, 40)}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                    padding: '8px 12px',
                    background: 'var(--card)fff',
                    borderRadius: 8,
                    border: '1px solid var(--line)',
                    fontSize: 12,
                  }}
                >
                  <span style={{ color: 'var(--warning)', fontWeight: 800, flexShrink: 0 }}>⚡</span>
                  <span style={{ color: 'var(--muted)' }}>{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>

      {/* ── Campaign Approval Status Overview ────────────────────────────────── */}
      <Section title="Campaign Approval Status">
        {campaigns.filter((c) => c.approval_status).length === 0 && (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No campaigns have been submitted for approval yet.</div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {campaigns
            .filter((c) => c.approval_status)
            .map((c) => (
              <div
                key={c.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: 'var(--card)fff',
                  borderRadius: 10,
                  border: '1px solid var(--line)',
                  flexWrap: 'wrap',
                  gap: 8,
                }}
              >
                <div>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{c.campaign_name}</span>
                  <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: 10 }}>{PLATFORM_LABELS[c.platform]}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <ApprovalBadge status={c.approval_status} />
                  {c.approver_name && <span style={{ fontSize: 11, color: "var(--muted)" }}>by {c.approver_name}</span>}
                  {c.approval_reason && (
                    <span style={{ fontSize: 11, color: "var(--muted)", fontStyle: 'italic' }}>
                      {'“'}
                      {c.approval_reason}
                      {'”'}
                    </span>
                  )}
                </div>
              </div>
            ))}
        </div>
      </Section>
    </main>
  );
}
