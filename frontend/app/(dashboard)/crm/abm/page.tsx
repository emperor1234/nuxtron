'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type TargetAccount = {
  id: number;
  company_id: number | null;
  name: string;
  owner: string;
  tier: 'tier_1' | 'tier_2' | 'tier_3';
  status: 'active' | 'paused' | 'archived';
  icp_fit_score: number;
  intent_score: number;
  notes: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

type CommitteeMember = {
  id: number;
  target_account_id: number;
  contact_id: number | null;
  name: string;
  role: string;
  title: string;
  influence_score: number;
  buying_power_score: number;
  engagement_level: 'low' | 'medium' | 'high';
  status: 'active' | 'inactive';
  notes: string;
};

type EngagementEvent = {
  id: number;
  target_account_id: number;
  channel: string;
  event_type: string;
  weight: number;
  actor: string;
  occurred_at: string;
  created_at: string;
};

type AccountScore = {
  fit_score: number;
  intent_score: number;
  engagement_score: number;
  committee_coverage_pct: number;
  committee_avg_influence: number;
  pipeline_signal: number;
  open_deals: number;
  won_deals: number;
  deal_value: number;
  composite_score: number;
  priority: 'high' | 'medium' | 'low';
};

type AbmSummary = {
  target_accounts: number;
  committee_members: number;
  engagement_events: number;
  avg_account_score: number;
  priority_counts: { high: number; medium: number; low: number };
};

export default function CrmAbmPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [accounts, setAccounts] = useState<TargetAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [committee, setCommittee] = useState<CommitteeMember[]>([]);
  const [timeline, setTimeline] = useState<EngagementEvent[]>([]);
  const [score, setScore] = useState<AccountScore | null>(null);
  const [summary, setSummary] = useState<AbmSummary | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [accountForm, setAccountForm] = useState({
    name: '',
    owner: 'revops@nuxtron.local',
    tier: 'tier_2',
    icp_fit_score: 70,
    intent_score: 60,
    notes: '',
    tags: 'strategic,b2b',
  });

  const [memberForm, setMemberForm] = useState({
    name: '',
    role: 'influencer',
    title: '',
    influence_score: 65,
    buying_power_score: 55,
    engagement_level: 'medium',
    notes: '',
  });

  const [eventForm, setEventForm] = useState({
    channel: 'email',
    event_type: 'reply',
    weight: 20,
    actor: 'sdr-01',
  });

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedAccountId) ?? null,
    [accounts, selectedAccountId]
  );

  async function loadAccounts() {
    const res = await apiGet<{ target_accounts: TargetAccount[] }>('/crm/abm/target-accounts', tenantId);
    setAccounts(res.target_accounts ?? []);
  }

  async function loadReport() {
    const res = await apiGet<{ summary: AbmSummary }>('/crm/reports/abm', tenantId);
    setSummary(res.summary);
  }

  async function loadAccountDetail(accountId: number) {
    const [committeeRes, timelineRes, scoreRes] = await Promise.all([
      apiGet<{ committee: CommitteeMember[] }>(`/crm/abm/target-accounts/${accountId}/committee`, tenantId),
      apiGet<{ timeline: EngagementEvent[] }>(
        `/crm/abm/target-accounts/${accountId}/engagement-timeline?limit=25`,
        tenantId
      ),
      apiGet<{ score: AccountScore }>(`/crm/abm/target-accounts/${accountId}/score`, tenantId),
    ]);
    setCommittee(committeeRes.committee ?? []);
    setTimeline(timelineRes.timeline ?? []);
    setScore(scoreRes.score ?? null);
  }

  async function refreshAll() {
    try {
      setError('');
      await Promise.all([loadAccounts(), loadReport()]);
      if (selectedAccountId !== null) {
        await loadAccountDetail(selectedAccountId);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load ABM workspace');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createAccount() {
    try {
      setSaving(true);
      setError('');
      await apiSend(
        '/crm/abm/target-accounts',
        'POST',
        {
          name: accountForm.name,
          owner: accountForm.owner,
          tier: accountForm.tier,
          icp_fit_score: Number(accountForm.icp_fit_score),
          intent_score: Number(accountForm.intent_score),
          notes: accountForm.notes,
          tags: accountForm.tags
            .split(',')
            .map((tag) => tag.trim())
            .filter(Boolean),
        },
        tenantId
      );
      setAccountForm((prev) => ({ ...prev, name: '', notes: '' }));
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create target account');
    } finally {
      setSaving(false);
    }
  }

  async function selectAccount(accountId: number) {
    setSelectedAccountId(accountId);
    try {
      setError('');
      await loadAccountDetail(accountId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load account details');
    }
  }

  async function addCommitteeMember() {
    if (selectedAccountId === null) return;
    try {
      setSaving(true);
      await apiSend(
        `/crm/abm/target-accounts/${selectedAccountId}/committee`,
        'POST',
        {
          name: memberForm.name,
          role: memberForm.role,
          title: memberForm.title,
          influence_score: Number(memberForm.influence_score),
          buying_power_score: Number(memberForm.buying_power_score),
          engagement_level: memberForm.engagement_level,
          notes: memberForm.notes,
        },
        tenantId
      );
      setMemberForm((prev) => ({ ...prev, name: '', title: '', notes: '' }));
      await loadAccountDetail(selectedAccountId);
      await loadReport();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upsert committee member');
    } finally {
      setSaving(false);
    }
  }

  async function addEngagementEvent() {
    if (selectedAccountId === null) return;
    try {
      setSaving(true);
      await apiSend(
        `/crm/abm/target-accounts/${selectedAccountId}/engagement-events`,
        'POST',
        {
          channel: eventForm.channel,
          event_type: eventForm.event_type,
          weight: Number(eventForm.weight),
          actor: eventForm.actor,
        },
        tenantId
      );
      await loadAccountDetail(selectedAccountId);
      await loadReport();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create engagement event');
    } finally {
      setSaving(false);
    }
  }

  const card: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  const input: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1300, margin: '0 auto', display: 'grid', gap: 12 }}>
        <section style={card}>
          <h1 style={{ margin: 0 }}>CRM ABM Command Center</h1>
          <p style={{ color: 'var(--muted)', marginBottom: 0 }}>
            Target account scoring, buying committee mapping, and engagement telemetry with operator-grade reporting.
          </p>
        </section>

        {summary && (
          <section
            style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: 10 }}
          >
            <Metric label="Target Accounts" value={summary.target_accounts} />
            <Metric label="Committee Members" value={summary.committee_members} />
            <Metric label="Engagement Events" value={summary.engagement_events} />
            <Metric label="Average Score" value={summary.avg_account_score} />
            <Metric label="Priority: High" value={summary.priority_counts.high} />
            <Metric label="Priority: Medium" value={summary.priority_counts.medium} />
            <Metric label="Priority: Low" value={summary.priority_counts.low} />
          </section>
        )}

        {error && <section style={{ ...card, borderColor: '#b91c1c', color: '#fca5a5' }}>{error}</section>}

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Create Target Account</h3>
              <input
                style={input}
                value={accountForm.name}
                onChange={(e) => setAccountForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="Company / account name"
              />
              <input
                style={input}
                value={accountForm.owner}
                onChange={(e) => setAccountForm((p) => ({ ...p, owner: e.target.value }))}
                placeholder="Owner"
              />
              <select
                style={input}
                value={accountForm.tier}
                onChange={(e) => setAccountForm((p) => ({ ...p, tier: e.target.value }))}
              >
                <option value="tier_1">Tier 1</option>
                <option value="tier_2">Tier 2</option>
                <option value="tier_3">Tier 3</option>
              </select>
              <div style={{ fontSize: 12, marginBottom: 4 }}>ICP Fit Score</div>
              <input
                style={input}
                type="number"
                min={0}
                max={100}
                value={accountForm.icp_fit_score}
                onChange={(e) => setAccountForm((p) => ({ ...p, icp_fit_score: Number(e.target.value) }))}
              />
              <div style={{ fontSize: 12, marginBottom: 4 }}>Intent Score</div>
              <input
                style={input}
                type="number"
                min={0}
                max={100}
                value={accountForm.intent_score}
                onChange={(e) => setAccountForm((p) => ({ ...p, intent_score: Number(e.target.value) }))}
              />
              <input
                style={input}
                value={accountForm.tags}
                onChange={(e) => setAccountForm((p) => ({ ...p, tags: e.target.value }))}
                placeholder="Tags (comma separated)"
              />
              <textarea
                style={{ ...input, minHeight: 90, resize: 'vertical' }}
                value={accountForm.notes}
                onChange={(e) => setAccountForm((p) => ({ ...p, notes: e.target.value }))}
                placeholder="Strategic notes"
              />
              <button
                disabled={!accountForm.name.trim() || saving}
                onClick={() => void createAccount()}
                style={primaryButton}
              >
                {saving ? 'Saving...' : 'Create Target Account'}
              </button>
            </div>

            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Target Accounts ({accounts.length})</h3>
              <div style={{ maxHeight: 380, overflow: 'auto', display: 'grid', gap: 8 }}>
                {accounts.map((account) => (
                  <button
                    key={account.id}
                    onClick={() => void selectAccount(account.id)}
                    style={{
                      textAlign: 'left',
                      border: selectedAccountId === account.id ? '1px solid var(--brand)' : '1px solid var(--line)',
                      borderRadius: 10,
                      background: 'transparent',
                      color: 'var(--text)',
                      padding: 10,
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{account.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {account.tier.toUpperCase()} · owner: {account.owner || 'unassigned'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      fit {account.icp_fit_score} · intent {account.intent_score}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Account Intelligence</h3>
              {selectedAccount ? (
                <>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
                      gap: 8,
                      marginBottom: 12,
                    }}
                  >
                    <Metric label="Account" value={selectedAccount.name} />
                    <Metric label="Tier" value={selectedAccount.tier.toUpperCase()} />
                    <Metric label="Status" value={selectedAccount.status} />
                    <Metric label="Owner" value={selectedAccount.owner || 'unassigned'} />
                    <Metric label="ABM Score" value={score ? score.composite_score : '-'} />
                    <Metric label="Priority" value={score ? score.priority.toUpperCase() : '-'} />
                    <Metric label="Committee Coverage" value={score ? `${score.committee_coverage_pct}%` : '-'} />
                    <Metric label="Engagement" value={score ? score.engagement_score : '-'} />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
                    <div>
                      <h4 style={{ margin: '0 0 8px 0' }}>Buying Committee ({committee.length})</h4>
                      <div
                        style={{ maxHeight: 210, overflow: 'auto', border: '1px solid var(--line)', borderRadius: 8 }}
                      >
                        {committee.map((member) => (
                          <div key={member.id} style={{ padding: 8, borderBottom: '1px solid var(--line)' }}>
                            <div style={{ fontWeight: 600 }}>{member.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                              {member.role} · influence {member.influence_score} · buying {member.buying_power_score}
                            </div>
                          </div>
                        ))}
                        {committee.length === 0 && (
                          <div style={{ padding: 10, color: 'var(--muted)' }}>No committee members mapped yet.</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <h4 style={{ margin: '0 0 8px 0' }}>Engagement Timeline ({timeline.length})</h4>
                      <div
                        style={{ maxHeight: 210, overflow: 'auto', border: '1px solid var(--line)', borderRadius: 8 }}
                      >
                        {timeline.map((event) => (
                          <div key={event.id} style={{ padding: 8, borderBottom: '1px solid var(--line)' }}>
                            <div style={{ fontWeight: 600 }}>{event.event_type}</div>
                            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                              {event.channel} · weight {event.weight} · {event.actor}
                            </div>
                          </div>
                        ))}
                        {timeline.length === 0 && (
                          <div style={{ padding: 10, color: 'var(--muted)' }}>No engagement events yet.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--muted)', marginBottom: 0 }}>
                  Select a target account to work on committee and engagement intelligence.
                </p>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Add / Update Committee Member</h3>
                <input
                  style={input}
                  value={memberForm.name}
                  onChange={(e) => setMemberForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="Name"
                />
                <input
                  style={input}
                  value={memberForm.title}
                  onChange={(e) => setMemberForm((p) => ({ ...p, title: e.target.value }))}
                  placeholder="Title"
                />
                <select
                  style={input}
                  value={memberForm.role}
                  onChange={(e) => setMemberForm((p) => ({ ...p, role: e.target.value }))}
                >
                  {['champion', 'decision_maker', 'budget_holder', 'influencer', 'legal', 'procurement', 'blocker'].map(
                    (role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    )
                  )}
                </select>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Influence Score</div>
                <input
                  style={input}
                  type="number"
                  min={0}
                  max={100}
                  value={memberForm.influence_score}
                  onChange={(e) => setMemberForm((p) => ({ ...p, influence_score: Number(e.target.value) }))}
                />
                <div style={{ fontSize: 12, marginBottom: 4 }}>Buying Power Score</div>
                <input
                  style={input}
                  type="number"
                  min={0}
                  max={100}
                  value={memberForm.buying_power_score}
                  onChange={(e) => setMemberForm((p) => ({ ...p, buying_power_score: Number(e.target.value) }))}
                />
                <select
                  style={input}
                  value={memberForm.engagement_level}
                  onChange={(e) => setMemberForm((p) => ({ ...p, engagement_level: e.target.value }))}
                >
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
                <textarea
                  style={{ ...input, minHeight: 70, resize: 'vertical' }}
                  value={memberForm.notes}
                  onChange={(e) => setMemberForm((p) => ({ ...p, notes: e.target.value }))}
                  placeholder="Notes"
                />
                <button
                  disabled={selectedAccountId === null || !memberForm.name.trim() || saving}
                  onClick={() => void addCommitteeMember()}
                  style={primaryButton}
                >
                  Upsert Committee Member
                </button>
              </div>

              <div style={card}>
                <h3 style={{ marginTop: 0 }}>Log Engagement Event</h3>
                <select
                  style={input}
                  value={eventForm.channel}
                  onChange={(e) => setEventForm((p) => ({ ...p, channel: e.target.value }))}
                >
                  {['email', 'call', 'meeting', 'chat', 'linkedin', 'web', 'event', 'ad', 'ticket'].map((channel) => (
                    <option key={channel} value={channel}>
                      {channel}
                    </option>
                  ))}
                </select>
                <input
                  style={input}
                  value={eventForm.event_type}
                  onChange={(e) => setEventForm((p) => ({ ...p, event_type: e.target.value }))}
                  placeholder="Event type (reply, meeting_booked...)"
                />
                <div style={{ fontSize: 12, marginBottom: 4 }}>Weight</div>
                <input
                  style={input}
                  type="number"
                  min={1}
                  max={100}
                  value={eventForm.weight}
                  onChange={(e) => setEventForm((p) => ({ ...p, weight: Number(e.target.value) }))}
                />
                <input
                  style={input}
                  value={eventForm.actor}
                  onChange={(e) => setEventForm((p) => ({ ...p, actor: e.target.value }))}
                  placeholder="Actor"
                />
                <button
                  disabled={selectedAccountId === null || saving}
                  onClick={() => void addEngagementEvent()}
                  style={primaryButton}
                >
                  Add Engagement Event
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{label}</div>
      <div style={{ fontWeight: 700 }}>{value}</div>
    </div>
  );
}

const primaryButton: React.CSSProperties = {
  border: 'none',
  borderRadius: 8,
  background: 'var(--brand)',
  color: '#00101e',
  fontWeight: 700,
  padding: '8px 12px',
};
