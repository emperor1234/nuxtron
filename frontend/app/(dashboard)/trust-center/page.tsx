'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost } from '@/app/lib/api-client';
import InstitutionalAiWidgets from '@/app/components/institutional-ai-widgets';
import { Page, PageHeader, Card, CardTitle, Button, Badge, Stat, StatGrid, TableWrap, Field, FieldSelect, tableClass } from '../_ui/kit';
import { buildGovernanceSnapshotRequest, type GovernancePolicySelection } from './snapshot-request';

type Json = Record<string, unknown>;

// Tenant is resolved from the authenticated session inside the API client
// (A01: Broken Access Control). Passing an empty tenant here forces that
// resolution and removes the previous free-text tenant override, which let a
// user pivot to any tenant's governance data.
const SESSION_TENANT = '';

function asNumber(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function asString(v: unknown, fb = ''): string {
  return typeof v === 'string' ? v : fb;
}
function asBoolean(v: unknown, fb = false): boolean {
  return typeof v === 'boolean' ? v : fb;
}
function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

const POSTURE_LABEL: Record<string, string> = {
  critical: '🔴 Critical',
  high: '🟠 High',
  medium: '🟡 Medium',
  low: '🟢 Low',
};

export default function TrustCenterPage() {
  const [posture, setPosture] = useState<Json>({});
  const [incidents, setIncidents] = useState<unknown[]>([]);
  const [chains, setChains] = useState<unknown[]>([]);
  const [policies, setPolicies] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotSaving, setSnapshotSaving] = useState(false);
  const [snapshotError, setSnapshotError] = useState('');
  const [snapshotMessage, setSnapshotMessage] = useState('');
  const [snapshotConfirmed, setSnapshotConfirmed] = useState(false);
  const [snapshotNotes, setSnapshotNotes] = useState('');
  const [snapshotPolicy, setSnapshotPolicy] = useState<GovernancePolicySelection>({
    autonomy_enabled: null,
    allow_high_impact_actions: null,
    strict_policy_lock: null,
    policy_change_human_validation: null,
  });
  const [incidentSaving, setIncidentSaving] = useState(false);
  const [chainSaving, setChainSaving] = useState(false);

  // New incident form
  const [incTitle, setIncTitle] = useState('');
  const [incDesc, setIncDesc] = useState('');
  const [incSeverity, setIncSeverity] = useState('medium');
  const [incModule, setIncModule] = useState('ira');
  const [incMsg, setIncMsg] = useState('');

  // New approval chain form
  const [chainName, setChainName] = useState('');
  const [chainAction, setChainAction] = useState('billing_change');
  const [chainMsg, setChainMsg] = useState('');

  const postureScore = asNumber(posture.posture_score) ?? -1;
  const openIncidents = asNumber(posture.open_incidents);
  const criticalOpen = asNumber(posture.critical_open_incidents);
  const activeChains = asNumber(posture.active_approval_chains);
  const policyCount = asNumber(posture.policy_changes_recorded);

  const postureTone = useMemo<'neutral' | 'success' | 'danger'>(() => {
    if (postureScore < 0) return 'neutral';
    if (postureScore >= 80) return 'success';
    return 'danger';
  }, [postureScore]);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [postureData, incData, chainData, policyData] = await Promise.all([
        apiGet('/trust-center/posture', SESSION_TENANT),
        apiGet('/trust-center/incidents', SESSION_TENANT),
        apiGet('/trust-center/approval-chains', SESSION_TENANT),
        apiGet('/trust-center/policies', SESSION_TENANT),
      ]);
      setPosture(postureData as Json);
      setIncidents(asArray((incData as Json).incidents));
      setChains(asArray((chainData as Json).chains));
      setPolicies(asArray((policyData as Json).history));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load Trust Center data.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  async function createIncident() {
    if (!incTitle.trim() || !incDesc.trim()) return;
    setIncidentSaving(true);
    setIncMsg('');
    try {
      const res = await apiPost(
        '/trust-center/incidents',
        { title: incTitle, description: incDesc, severity: incSeverity, affected_module: incModule },
        SESSION_TENANT
      );
      setIncMsg(asString((res as Json).incident_id) ? `Created incident ${asString((res as Json).incident_id)}` : 'Incident created.');
      setIncTitle('');
      setIncDesc('');
      await load();
    } catch (e) {
      setIncMsg(`Error: ${String(e)}`);
    } finally {
      setIncidentSaving(false);
    }
  }

  async function createChain() {
    if (!chainName.trim()) return;
    setChainSaving(true);
    setChainMsg('');
    try {
      const res = await apiPost(
        '/trust-center/approval-chains',
        {
          chain_name: chainName,
          action_type: chainAction,
          steps: [{ role: 'admin', label: 'Admin approval required' }],
          require_all: true,
        },
        SESSION_TENANT
      );
      setChainMsg(asString((res as Json).chain_id) ? `Created chain ${asString((res as Json).chain_id)}` : 'Approval chain created.');
      setChainName('');
      await load();
    } catch (e) {
      setChainMsg(`Error: ${String(e)}`);
    } finally {
      setChainSaving(false);
    }
  }

  function openSnapshotReview() {
    setSnapshotPolicy({
      autonomy_enabled: null,
      allow_high_impact_actions: null,
      strict_policy_lock: null,
      policy_change_human_validation: null,
    });
    setSnapshotNotes('');
    setSnapshotConfirmed(false);
    setSnapshotError('');
    setSnapshotMessage('');
    setSnapshotOpen(true);
  }

  function chooseSnapshotPolicy(key: keyof GovernancePolicySelection, value: string) {
    setSnapshotPolicy((current) => ({ ...current, [key]: value === '' ? null : value === 'true' }));
  }

  async function takeSnapshot() {
    const payload = buildGovernanceSnapshotRequest(
      snapshotPolicy,
      [
        'Customer-attested policy values; enforcement is not independently verified by Nuxtron.',
        snapshotNotes.trim(),
      ].filter(Boolean).join(' '),
    );
    if (!payload) {
      setSnapshotError('Choose a value for each policy setting before capturing the snapshot.');
      return;
    }
    if (!snapshotConfirmed) {
      setSnapshotError('Confirm that these values reflect the current configured policies.');
      return;
    }
    setSnapshotSaving(true);
    setSnapshotError('');
    setSnapshotMessage('');
    try {
      const response = await apiPost('/trust-center/snapshots', payload, SESSION_TENANT);
      const snapshotId = asString((response as Json).snapshot_id);
      if (!snapshotId) throw new Error('The service did not return a snapshot ID.');
      setSnapshotMessage(`Snapshot ${snapshotId} captured. Policy values are customer-attested, not independently verified.`);
      setSnapshotOpen(false);
    } catch (e) {
      setSnapshotError(e instanceof Error ? e.message : 'Unable to capture the governance snapshot.');
    } finally {
      setSnapshotSaving(false);
    }
  }

  return (
    <Page>
      <PageHeader
        title="Trust Center"
        subtitle="Review live incident and approval counts, record policy history, and capture customer-attested governance settings."
        actions={
          <>
            <Button onClick={load} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </Button>
            <Button variant="primary" onClick={openSnapshotReview} disabled={loading || postureScore < 0}>
              Capture Snapshot
            </Button>
          </>
        }
      />

      {error ? (
        <Card>
          <div role="alert" aria-live="assertive" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <Badge tone="danger">{error}</Badge>
            <Button onClick={load} disabled={loading}>Retry</Button>
          </div>
        </Card>
      ) : null}

      {snapshotMessage ? <p role="status" aria-live="polite">{snapshotMessage}</p> : null}

      {snapshotOpen ? (
        <Card>
          <CardTitle sub="These values are recorded from your confirmation. Nuxtron does not independently verify that enforcement matches the selections.">
            Review governance snapshot
          </CardTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12, marginTop: 14 }}>
            <FieldSelect label="Autonomy enabled" id="snapshot-autonomy" value={snapshotPolicy.autonomy_enabled === null ? '' : String(snapshotPolicy.autonomy_enabled)} onChange={(event) => chooseSnapshotPolicy('autonomy_enabled', event.target.value)}>
              <option value="">Choose current setting…</option>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </FieldSelect>
            <FieldSelect label="High-impact actions allowed" id="snapshot-high-impact" value={snapshotPolicy.allow_high_impact_actions === null ? '' : String(snapshotPolicy.allow_high_impact_actions)} onChange={(event) => chooseSnapshotPolicy('allow_high_impact_actions', event.target.value)}>
              <option value="">Choose current setting…</option>
              <option value="true">Allowed</option>
              <option value="false">Not allowed</option>
            </FieldSelect>
            <FieldSelect label="Strict policy lock" id="snapshot-policy-lock" value={snapshotPolicy.strict_policy_lock === null ? '' : String(snapshotPolicy.strict_policy_lock)} onChange={(event) => chooseSnapshotPolicy('strict_policy_lock', event.target.value)}>
              <option value="">Choose current setting…</option>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </FieldSelect>
            <FieldSelect label="Human validation for policy changes" id="snapshot-human-validation" value={snapshotPolicy.policy_change_human_validation === null ? '' : String(snapshotPolicy.policy_change_human_validation)} onChange={(event) => chooseSnapshotPolicy('policy_change_human_validation', event.target.value)}>
              <option value="">Choose current setting…</option>
              <option value="true">Required</option>
              <option value="false">Not required</option>
            </FieldSelect>
          </div>
          <Field label="Notes (optional)" id="snapshot-notes" value={snapshotNotes} onChange={(event) => setSnapshotNotes(event.target.value)} maxLength={700} />
          <label style={{ display: 'flex', gap: 9, alignItems: 'flex-start', marginTop: 14, fontSize: 13 }}>
            <input type="checkbox" checked={snapshotConfirmed} onChange={(event) => setSnapshotConfirmed(event.target.checked)} />
            <span>I confirm these values reflect the currently configured policies.</span>
          </label>
          {snapshotError ? <p role="alert" aria-live="assertive">{snapshotError}</p> : null}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
            <Button variant="primary" onClick={takeSnapshot} disabled={snapshotSaving || loading || !snapshotConfirmed || !buildGovernanceSnapshotRequest(snapshotPolicy, snapshotNotes)}>
              {snapshotSaving ? 'Capturing…' : 'Capture this snapshot'}
            </Button>
            <Button onClick={() => setSnapshotOpen(false)} disabled={snapshotSaving}>Cancel</Button>
          </div>
        </Card>
      ) : null}

      {postureScore >= 0 ? (
        <StatGrid>
          <Stat label="Posture Score" value={<Badge tone={postureTone}>{postureScore}</Badge>} />
          <Stat label="Open Incidents" value={openIncidents ?? '—'} />
          <Stat label="Critical Open" value={criticalOpen ?? '—'} />
          <Stat label="Approval Chains" value={activeChains ?? '—'} />
          <Stat label="Policy Changes" value={policyCount ?? '—'} />
        </StatGrid>
      ) : null}

      <Card>
        <CardTitle>Incidents</CardTitle>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, margin: '14px 0' }}>
          <Field label="Incident title" placeholder="Describe the incident" value={incTitle} onChange={(e) => setIncTitle(e.target.value)} />
          <Field label="Incident description" placeholder="Provide useful context" value={incDesc} onChange={(e) => setIncDesc(e.target.value)} />
          <select
            value={incSeverity}
            onChange={(e) => setIncSeverity(e.target.value)}
            aria-label="Severity"
            style={{ height: 38, padding: '0 12px', border: '1px solid var(--nx-border)', borderRadius: 10, background: 'var(--nx-card)', fontFamily: 'inherit', fontSize: 13.5 }}
          >
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <Field label="Affected module" placeholder="Module name" value={incModule} onChange={(e) => setIncModule(e.target.value)} />
          <Button variant="primary" onClick={createIncident} disabled={incidentSaving || !incTitle.trim() || !incDesc.trim()}>
            {incidentSaving ? 'Reporting…' : 'Report incident'}
          </Button>
        </div>
        {incMsg ? <p role={incMsg.startsWith('Error:') ? 'alert' : 'status'} aria-live={incMsg.startsWith('Error:') ? 'assertive' : 'polite'} style={{ color: 'var(--nx-muted)', fontSize: 13 }}>{incMsg}</p> : null}
        <TableWrap>
          <table className={tableClass}>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Title</th>
                <th>Module</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc, idx) => {
                const i = inc as Json;
                return (
                  <tr key={`${asString(i.id)}-${idx}`}>
                    <td>{POSTURE_LABEL[asString(i.severity)] ?? asString(i.severity)}</td>
                    <td>{asString(i.title)}</td>
                    <td>{asString(i.affected_module)}</td>
                    <td>{asBoolean(i.resolved) ? 'Resolved' : 'Open'}</td>
                    <td>{asString(i.created_at).slice(0, 10)}</td>
                  </tr>
                );
              })}
              {!loading && !error && incidents.length === 0 ? (
                <tr>
                  <td colSpan={5}>No incidents recorded</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </TableWrap>
      </Card>

      <Card>
        <CardTitle>Approval Chains</CardTitle>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, margin: '14px 0' }}>
          <Field label="Approval chain name" placeholder="Name this approval chain" value={chainName} onChange={(e) => setChainName(e.target.value)} />
          <Field label="Action type" placeholder="Action type" value={chainAction} onChange={(e) => setChainAction(e.target.value)} />
          <Button variant="primary" onClick={createChain} disabled={chainSaving || !chainName.trim()}>
            {chainSaving ? 'Adding…' : 'Add chain'}
          </Button>
        </div>
        {chainMsg ? <p role={chainMsg.startsWith('Error:') ? 'alert' : 'status'} aria-live={chainMsg.startsWith('Error:') ? 'assertive' : 'polite'} style={{ color: 'var(--nx-muted)', fontSize: 13 }}>{chainMsg}</p> : null}
        <StatGrid>
          {chains.map((c, idx) => {
            const ch = c as Json;
            return (
              <Stat
                key={`${asString(ch.id)}-${idx}`}
                label={asString(ch.chain_name)}
                value={<span style={{ fontSize: 15 }}>{asString(ch.action_type)}</span>}
                hint={`Require all: ${asBoolean(ch.require_all) ? 'Yes' : 'No'}`}
              />
            );
          })}
          {!loading && chains.length === 0 ? <p style={{ color: 'var(--nx-muted)' }}>No approval chains defined</p> : null}
        </StatGrid>
      </Card>

      <Card>
        <CardTitle>Policy History</CardTitle>
        <TableWrap>
          <table className={tableClass}>
            <thead>
              <tr>
                <th>Policy Key</th>
                <th>Changed By</th>
                <th>Reason</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((p, idx) => {
                const pol = p as Json;
                return (
                  <tr key={`${asString(pol.id)}-${idx}`}>
                    <td>{asString(pol.policy_key)}</td>
                    <td>{asString(pol.actor_role)}</td>
                    <td>{asString(pol.change_reason)}</td>
                    <td>{asString(pol.created_at).slice(0, 10)}</td>
                  </tr>
                );
              })}
              {!loading && policies.length === 0 ? (
                <tr>
                  <td colSpan={4}>No policy changes recorded</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </TableWrap>
      </Card>

      <InstitutionalAiWidgets />
    </Page>
  );
}
