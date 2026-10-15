'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader } from '../_ui/kit';
import {
  buildSnapshotPayload,
  formatCompetitiveDate,
  parseComparisonReport,
  parseCompetitorProfiles,
  parseShareOfVoice,
  type ComparisonReport,
  type CompetitorProfile,
  type ShareOfVoiceEntry,
  type SnapshotDraft,
} from './competitive-model';

type LoadState = 'loading' | 'ready' | 'error';
type Action = 'profile' | 'competitor-snapshot' | 'own-snapshot' | null;

const EMPTY_DRAFT: SnapshotDraft = { followers: '', engagementRate: '', estimatedMentions: '', snapshotDate: '' };
const NETWORKS = ['linkedin', 'x', 'instagram', 'facebook', 'tiktok', 'youtube', 'pinterest', 'reddit'];

function isOkResponse(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) && (value as Record<string, unknown>).status === 'ok';
}

function formatCount(value: number | null): string {
  return value === null ? 'Not recorded' : new Intl.NumberFormat().format(value);
}

function formatPercent(value: number | null): string {
  return value === null ? 'Not recorded' : `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function MetricFields({
  idPrefix,
  draft,
  onChange,
}: {
  idPrefix: string;
  draft: SnapshotDraft;
  onChange: (next: SnapshotDraft) => void;
}) {
  const subject = idPrefix === 'own-snapshot' ? 'Your brand' : 'Competitor';
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 12 }}>
      <Field id={`${idPrefix}-followers`} label={`${subject} followers (count)`} type="number" min="0" step="1" required value={draft.followers} onChange={(event) => onChange({ ...draft, followers: event.target.value })} />
      <Field id={`${idPrefix}-engagement`} label={`${subject} engagement rate (%)`} type="number" min="0" max="100" step="0.01" required value={draft.engagementRate} onChange={(event) => onChange({ ...draft, engagementRate: event.target.value })} />
      <Field id={`${idPrefix}-mentions`} label={`${subject} estimated mentions (count)`} type="number" min="0" step="1" required value={draft.estimatedMentions} onChange={(event) => onChange({ ...draft, estimatedMentions: event.target.value })} />
      <Field id={`${idPrefix}-date`} label={`${subject} observation date (optional)`} type="date" value={draft.snapshotDate} onChange={(event) => onChange({ ...draft, snapshotDate: event.target.value })} />
    </div>
  );
}

function Observation({ snapshot }: { snapshot: NonNullable<ComparisonReport['ownBrand']> }) {
  return (
    <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 145px), 1fr))', gap: 12, margin: '12px 0 0' }}>
      <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Followers</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{formatCount(snapshot.followers)}</dd></div>
      <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Engagement rate</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{formatPercent(snapshot.engagementRate)}</dd></div>
      <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Estimated mentions</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{formatCount(snapshot.estimatedMentions)}</dd></div>
      <div><dt style={{ color: 'var(--muted)', fontSize: 13 }}>Observation date</dt><dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{formatCompetitiveDate(snapshot.snapshotDate) ?? 'Not reported'}</dd></div>
    </dl>
  );
}

export default function CompetitiveBenchmarkingPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [profiles, setProfiles] = useState<CompetitorProfile[]>([]);
  const [profilesState, setProfilesState] = useState<LoadState>('loading');
  const [profilesError, setProfilesError] = useState('');
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [reportState, setReportState] = useState<LoadState>('loading');
  const [reportError, setReportError] = useState('');
  const [share, setShare] = useState<{ totalEstimatedMentions: number; breakdown: ShareOfVoiceEntry[] } | null>(null);
  const [shareState, setShareState] = useState<LoadState>('loading');
  const [shareError, setShareError] = useState('');
  const [profileName, setProfileName] = useState('');
  const [profileNetwork, setProfileNetwork] = useState('');
  const [profileHandle, setProfileHandle] = useState('');
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [competitorDraft, setCompetitorDraft] = useState<SnapshotDraft>({ ...EMPTY_DRAFT });
  const [ownNetwork, setOwnNetwork] = useState('');
  const [ownDraft, setOwnDraft] = useState<SnapshotDraft>({ ...EMPTY_DRAFT });
  const [busyAction, setBusyAction] = useState<Action>(null);
  const [actionError, setActionError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const hasWorkspace = Boolean(tenantId);

  const loadProfiles = useCallback(async () => {
    if (!tenantId) {
      setProfilesState('error');
      setProfilesError('Sign in to a workspace to load competitor profiles.');
      return;
    }
    setProfilesState('loading');
    setProfilesError('');
    try {
      const response = await apiGet<unknown>('/competitive/profiles', tenantId);
      const parsed = parseCompetitorProfiles(response);
      if (!parsed) throw new Error('The competitor profile service returned an invalid response.');
      setProfiles(parsed);
      setProfilesState('ready');
    } catch (error) {
      setProfilesError(error instanceof Error ? error.message : 'Could not load competitor profiles.');
      setProfilesState('error');
    }
  }, [tenantId]);

  const loadReport = useCallback(async () => {
    if (!tenantId) {
      setReportState('error');
      setReportError('Sign in to a workspace to load comparison data.');
      return;
    }
    setReportState('loading');
    setReportError('');
    try {
      const response = await apiGet<unknown>('/competitive/report', tenantId);
      const parsed = parseComparisonReport(response);
      if (!parsed) throw new Error('The comparison service returned an invalid response.');
      setReport(parsed);
      setReportState('ready');
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Could not load comparison data.');
      setReportState('error');
    }
  }, [tenantId]);

  const loadShare = useCallback(async () => {
    if (!tenantId) {
      setShareState('error');
      setShareError('Sign in to a workspace to load share-of-voice data.');
      return;
    }
    setShareState('loading');
    setShareError('');
    try {
      const response = await apiGet<unknown>('/competitive/share-of-voice', tenantId);
      const parsed = parseShareOfVoice(response);
      if (!parsed) throw new Error('The share-of-voice service returned an invalid response.');
      setShare(parsed);
      setShareState('ready');
    } catch (error) {
      setShareError(error instanceof Error ? error.message : 'Could not load share-of-voice data.');
      setShareState('error');
    }
  }, [tenantId]);

  const refreshAll = useCallback(() => {
    void Promise.all([loadProfiles(), loadReport(), loadShare()]);
  }, [loadProfiles, loadReport, loadShare]);

  useEffect(() => {
    const timerId = window.setTimeout(refreshAll, 0);
    return () => window.clearTimeout(timerId);
  }, [refreshAll]);

  const sortedProfiles = useMemo(() => [...profiles].sort((a, b) => a.name.localeCompare(b.name)), [profiles]);

  async function addProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantId) return setActionError('Sign in to a workspace before adding a profile.');
    const normalizedName = profileName.trim();
    const normalizedHandle = profileHandle.trim().replace(/^@/, '');
    if (!normalizedName || !normalizedHandle || !profileNetwork) return setActionError('Complete the profile name, network, and handle.');
    setBusyAction('profile');
    setActionError('');
    setActionMessage('');
    try {
      const response = await apiSend<unknown>('/competitive/profiles', 'POST', { name: normalizedName, network: profileNetwork, handle: normalizedHandle }, tenantId);
      if (!isOkResponse(response)) throw new Error('The profile service did not confirm this change.');
      const profilesFromResponse = parseCompetitorProfiles({ status: 'ok', count: 1, profiles: [response.profile] });
      if (!profilesFromResponse) throw new Error('The profile service returned an invalid profile.');
      const created = response.created !== false;
      setActionMessage(created ? 'Competitor profile added.' : 'That network handle is already tracked; the existing profile is available below.');
      setProfileName('');
      setProfileHandle('');
      setProfileNetwork('');
      await Promise.all([loadProfiles(), loadReport(), loadShare()]);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not add the competitor profile.');
    } finally {
      setBusyAction(null);
    }
  }

  async function addCompetitorSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantId) return setActionError('Sign in to a workspace before recording an observation.');
    const profileId = Number(selectedProfileId);
    if (!Number.isInteger(profileId) || profileId < 1) return setActionError('Choose a competitor profile first.');
    const payload = buildSnapshotPayload(competitorDraft);
    if (!payload) return setActionError('Enter non-negative followers and estimated mentions, plus an engagement rate from 0% to 100%.');
    setBusyAction('competitor-snapshot');
    setActionError('');
    setActionMessage('');
    try {
      const response = await apiSend<unknown>(`/competitive/profiles/${profileId}/snapshots`, 'POST', payload, tenantId);
      if (!isOkResponse(response) || !response.snapshot) throw new Error('The snapshot service did not confirm this observation.');
      setCompetitorDraft({ ...EMPTY_DRAFT });
      setActionMessage('Manual competitor observation recorded.');
      await Promise.all([loadProfiles(), loadReport(), loadShare()]);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not record the competitor observation.');
    } finally {
      setBusyAction(null);
    }
  }

  async function addOwnSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantId) return setActionError('Sign in to a workspace before recording your brand observation.');
    if (!ownNetwork) return setActionError('Choose a network for your brand observation.');
    const payload = buildSnapshotPayload(ownDraft);
    if (!payload) return setActionError('Enter non-negative followers and estimated mentions, plus an engagement rate from 0% to 100%.');
    setBusyAction('own-snapshot');
    setActionError('');
    setActionMessage('');
    try {
      const response = await apiSend<unknown>('/competitive/own-profile', 'POST', { network: ownNetwork, ...payload }, tenantId);
      if (!isOkResponse(response) || !response.record) throw new Error('The own-profile service did not confirm this observation.');
      setOwnDraft({ ...EMPTY_DRAFT });
      setActionMessage('Manual observation for your brand recorded.');
      await Promise.all([loadReport(), loadShare()]);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not record your brand observation.');
    } finally {
      setBusyAction(null);
    }
  }

  const hasMetricError = profilesState === 'error' || reportState === 'error' || shareState === 'error';
  const hasPendingLoad = profilesState === 'loading' || reportState === 'loading' || shareState === 'loading';

  return (
    <Page>
      <PageHeader
        title="Competitive Benchmarking"
        subtitle="Compare manually recorded social observations for your brand and selected competitors."
        actions={<Button type="button" onClick={refreshAll} disabled={!hasWorkspace || hasPendingLoad}>Refresh data</Button>}
      />

      <Card>
        <CardTitle>Data source and availability</CardTitle>
        <div role="note" style={{ marginTop: 12, color: 'var(--muted)' }}>
          Metrics and mention estimates on this page are entered by your team. Automated social scraping is not available in the current service. Records currently use process-memory storage and may be lost when the service restarts; do not treat this history as durable until persistent storage is configured.
        </div>
      </Card>

      {(actionError || actionMessage) ? (
        <div role={actionError ? 'alert' : 'status'} style={{ color: actionError ? 'var(--danger)' : 'var(--success)' }}>
          {actionError || actionMessage}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: 16 }}>
        <Card>
          <CardTitle sub="Add a profile to organize manually entered competitor observations.">Competitor profiles</CardTitle>
          <form onSubmit={(event) => void addProfile(event)} style={{ display: 'grid', gap: 12, marginTop: 14 }}>
            <Field id="competitor-name" label="Competitor or brand name" value={profileName} onChange={(event) => setProfileName(event.target.value)} minLength={1} maxLength={160} required disabled={!hasWorkspace || busyAction !== null} />
            <FieldSelect id="competitor-network" label="Competitor social network" value={profileNetwork} onChange={(event) => setProfileNetwork(event.target.value)} required disabled={!hasWorkspace || busyAction !== null}>
              <option value="" disabled>Choose a network</option>
              {NETWORKS.map((value) => <option key={value} value={value}>{value === 'x' ? 'X' : value[0].toUpperCase() + value.slice(1)}</option>)}
            </FieldSelect>
            <Field id="competitor-handle" label="Profile handle" value={profileHandle} onChange={(event) => setProfileHandle(event.target.value)} placeholder="Enter a public handle" maxLength={120} required disabled={!hasWorkspace || busyAction !== null} />
            <Button type="submit" variant="primary" disabled={!hasWorkspace || busyAction !== null}>{busyAction === 'profile' ? 'Adding…' : 'Add competitor profile'}</Button>
          </form>
          <div style={{ borderTop: '1px solid var(--line)', marginTop: 18, paddingTop: 14 }}>
            <h3 style={{ fontSize: 15, margin: '0 0 8px' }}>Tracked profiles</h3>
            {profilesState === 'loading' ? <p role="status">Loading profiles…</p> : null}
            {profilesState === 'error' ? <div role="alert" style={{ color: 'var(--danger)' }}><p>{profilesError}</p><Button type="button" onClick={() => void loadProfiles()} disabled={!hasWorkspace}>Retry profiles</Button></div> : null}
            {profilesState === 'ready' && profiles.length === 0 ? <p style={{ color: 'var(--muted)' }}>No competitor profiles have been added to this workspace.</p> : null}
            {profilesState === 'ready' && sortedProfiles.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
                {sortedProfiles.map((profile) => <li key={profile.id} style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 10, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <span><strong>{profile.name}</strong><br /><span style={{ color: 'var(--muted)' }}>{profile.network} · @{profile.handle}</span></span>
                  <Badge>{profile.snapshotCount === null ? 'Snapshot count unavailable' : `${profile.snapshotCount} ${profile.snapshotCount === 1 ? 'snapshot' : 'snapshots'}`}</Badge>
                </li>)}
              </ul>
            ) : null}
          </div>
        </Card>

        <Card>
          <CardTitle sub="Enter values from an identified observation source; zero is accepted only when explicitly provided.">Competitor observation</CardTitle>
          <form onSubmit={(event) => void addCompetitorSnapshot(event)} style={{ display: 'grid', gap: 12, marginTop: 14 }}>
            <FieldSelect id="snapshot-profile" label="Competitor profile" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)} required disabled={!hasWorkspace || profilesState !== 'ready' || profiles.length === 0 || busyAction !== null}>
              <option value="" disabled>Choose a tracked profile</option>
              {sortedProfiles.map((profile) => <option key={profile.id} value={String(profile.id)}>{profile.name} · {profile.network}</option>)}
            </FieldSelect>
            <MetricFields idPrefix="competitor-snapshot" draft={competitorDraft} onChange={setCompetitorDraft} />
            <Button type="submit" disabled={!hasWorkspace || !selectedProfileId || busyAction !== null}>{busyAction === 'competitor-snapshot' ? 'Recording…' : 'Record competitor observation'}</Button>
          </form>
          {profilesState === 'error' ? <p style={{ color: 'var(--muted)' }}>Choose a profile after profile data loads.</p> : null}
        </Card>
      </div>

      <Card>
        <CardTitle sub="Store your own observations separately from competitor profiles.">Your brand observation</CardTitle>
        <form onSubmit={(event) => void addOwnSnapshot(event)} style={{ display: 'grid', gap: 12, marginTop: 14 }}>
          <FieldSelect id="own-network" label="Your brand social network" value={ownNetwork} onChange={(event) => setOwnNetwork(event.target.value)} required disabled={!hasWorkspace || busyAction !== null}>
            <option value="" disabled>Choose a network</option>
            {NETWORKS.map((value) => <option key={value} value={value}>{value === 'x' ? 'X' : value[0].toUpperCase() + value.slice(1)}</option>)}
          </FieldSelect>
          <MetricFields idPrefix="own-snapshot" draft={ownDraft} onChange={setOwnDraft} />
          <Button type="submit" variant="primary" disabled={!hasWorkspace || !ownNetwork || busyAction !== null}>{busyAction === 'own-snapshot' ? 'Recording…' : 'Record your brand observation'}</Button>
        </form>
      </Card>

      <Card>
        <CardTitle sub="A profile without a saved snapshot is shown as not recorded, never as zero.">Comparison</CardTitle>
        {reportState === 'loading' ? <p role="status">Loading comparison…</p> : null}
        {reportState === 'error' ? <div role="alert" style={{ color: 'var(--danger)' }}><p>{reportError}</p><Button type="button" onClick={() => void loadReport()} disabled={!hasWorkspace}>Retry comparison</Button></div> : null}
        {reportState === 'ready' && report ? (
          <div style={{ display: 'grid', gap: 14, marginTop: 14 }}>
            <article style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}><h3 style={{ margin: 0 }}>Your brand</h3><Badge tone={report.ownBrand ? 'success' : 'neutral'}>{report.ownBrand ? 'Observation recorded' : 'No observation'}</Badge></div>
              {report.ownBrand ? <Observation snapshot={report.ownBrand} /> : <p style={{ color: 'var(--muted)', marginBottom: 0 }}>No own-brand observation has been recorded.</p>}
            </article>
            {report.competitors.length === 0 ? <p style={{ color: 'var(--muted)' }}>No competitor profiles are available to compare.</p> : report.competitors.map((entry) => (
              <article key={entry.profile.id} style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}><h3 style={{ margin: 0 }}>{entry.profile.name}</h3><Badge>{entry.profile.network} · @{entry.profile.handle}</Badge></div>
                {entry.latestSnapshot ? <Observation snapshot={entry.latestSnapshot} /> : <p style={{ color: 'var(--muted)', marginBottom: 0 }}>No observation recorded for this profile.</p>}
              </article>
            ))}
          </div>
        ) : null}
      </Card>

      <Card>
        <CardTitle sub="Percentages are derived from each profile's latest manually estimated mention count.">Share of voice</CardTitle>
        {shareState === 'loading' ? <p role="status">Loading mention estimates…</p> : null}
        {shareState === 'error' ? <div role="alert" style={{ color: 'var(--danger)' }}><p>{shareError}</p><Button type="button" onClick={() => void loadShare()} disabled={!hasWorkspace}>Retry share of voice</Button></div> : null}
        {shareState === 'ready' && share ? (share.breakdown.length === 0 ? (
          <p style={{ color: 'var(--muted)', marginTop: 14 }}>No estimated mention counts have been recorded yet.</p>
        ) : (
          <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
            <p style={{ color: 'var(--muted)', margin: 0 }}>Total latest estimated mentions: {formatCount(share.totalEstimatedMentions)}</p>
            {share.breakdown.map((entry) => <div key={entry.brand} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
              <strong>{entry.brand}</strong><span>{formatCount(entry.estimatedMentions)} mentions · {entry.sharePct.toLocaleString(undefined, { maximumFractionDigits: 2 })}%</span>
            </div>)}
          </div>
        )) : null}
      </Card>

      {hasMetricError ? <p role="status" style={{ color: 'var(--muted)' }}>Some comparison data sources could not be loaded; unaffected sections remain available.</p> : null}
    </Page>
  );
}
