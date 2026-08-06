'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost } from '@/app/lib/api-client';
import InstitutionalAiWidgets from '@/app/components/institutional-ai-widgets';
import { Page, PageHeader, Card, CardTitle, Button, Badge, Stat, StatGrid, TableWrap, Field, tableClass } from '../_ui/kit';

type Json = Record<string, unknown>;

// Tenant is resolved from the authenticated session inside the API client
// (A01: Broken Access Control). Passing an empty tenant here forces that
// resolution and removes the previous free-text tenant override, which let a
// user pivot to any tenant's governance data.
const SESSION_TENANT = '';

function asNumber(v: unknown, fb = 0): number {
  return typeof v === 'number' ? v : fb;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

  const postureScore = asNumber(posture.posture_score, -1);
  const openIncidents = asNumber(posture.open_incidents, 0);
  const criticalOpen = asNumber(posture.critical_open_incidents, 0);
  const activeChains = asNumber(posture.active_approval_chains, 0);
  const policyCount = asNumber(posture.policy_changes_recorded, 0);

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
      setError(String(e));
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
    setIncMsg('');
    try {
      const res = await apiPost(
        '/trust-center/incidents',
        { title: incTitle, description: incDesc, severity: incSeverity, affected_module: incModule },
        SESSION_TENANT
      );
      setIncMsg(`Created incident ${asString((res as Json).incident_id)}`);
      setIncTitle('');
      setIncDesc('');
      await load();
    } catch (e) {
      setIncMsg(`Error: ${String(e)}`);
    }
  }

  async function createChain() {
    if (!chainName.trim()) return;
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
      setChainMsg(`Created chain ${asString((res as Json).chain_id)}`);
      setChainName('');
      await load();
    } catch (e) {
      setChainMsg(`Error: ${String(e)}`);
    }
  }

  async function takeSnapshot() {
    try {
      await apiPost(
        '/trust-center/snapshots',
        {
          autonomy_enabled: true,
          allow_high_impact_actions: false,
          strict_policy_lock: true,
          policy_change_human_validation: false,
          active_approval_chains: activeChains,
          open_incidents: openIncidents,
          notes: 'Snapshot captured from Trust Center dashboard',
        },
        SESSION_TENANT
      );
      alert('Governance snapshot captured');
    } catch (e) {
      alert(`Error: ${String(e)}`);
    }
  }

  return (
    <Page>
      <PageHeader
        title="Trust Center"
        subtitle="Governance posture, policy history, approval chains, and incident metrics with institutional control flows."
        actions={
          <>
            <Button onClick={load} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </Button>
            <Button variant="primary" onClick={takeSnapshot}>
              Capture Snapshot
            </Button>
          </>
        }
      />

      {error ? (
        <Card>
          <Badge tone="danger">{error}</Badge>
        </Card>
      ) : null}

      {postureScore >= 0 ? (
        <StatGrid>
          <Stat label="Posture Score" value={<Badge tone={postureTone}>{postureScore}</Badge>} />
          <Stat label="Open Incidents" value={openIncidents} />
          <Stat label="Critical Open" value={criticalOpen} />
          <Stat label="Approval Chains" value={activeChains} />
          <Stat label="Policy Changes" value={policyCount} />
        </StatGrid>
      ) : null}

      <Card>
        <CardTitle>Incidents</CardTitle>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, margin: '14px 0' }}>
          <Field placeholder="Title" value={incTitle} onChange={(e) => setIncTitle(e.target.value)} />
          <Field placeholder="Description" value={incDesc} onChange={(e) => setIncDesc(e.target.value)} />
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
          <Field placeholder="Module" value={incModule} onChange={(e) => setIncModule(e.target.value)} />
          <Button variant="primary" onClick={createIncident}>
            Report
          </Button>
        </div>
        {incMsg ? <p style={{ color: 'var(--nx-muted)', fontSize: 13 }}>{incMsg}</p> : null}
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
              {!loading && incidents.length === 0 ? (
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
          <Field placeholder="Chain name" value={chainName} onChange={(e) => setChainName(e.target.value)} />
          <Field placeholder="Action type" value={chainAction} onChange={(e) => setChainAction(e.target.value)} />
          <Button variant="primary" onClick={createChain}>
            Add Chain
          </Button>
        </div>
        {chainMsg ? <p style={{ color: 'var(--nx-muted)', fontSize: 13 }}>{chainMsg}</p> : null}
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
