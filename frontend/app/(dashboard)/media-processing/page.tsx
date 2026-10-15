'use client';

import { useCallback, useEffect, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import MediaUploader from '@/app/media-uploader';
import { Badge, Button, Card, CardTitle, DataStatus, Page, PageHeader, TableWrap, tableClass } from '../_ui/kit';

type JobRecord = {
  id: number;
  status: string;
  media_type: string;
  provider: string;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  error: string | null;
};

type MediaStats = {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
};

type JobsResponse = { jobs: JobRecord[] };
type StatsResponse = { stats: MediaStats };

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
}

function formatCount(value?: number): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : '—';
}

function statusTone(status: string): 'neutral' | 'success' | 'brand' | 'danger' {
  if (status === 'complete' || status === 'completed') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'danger';
  if (status === 'processing' || status === 'queued' || status === 'uploading') return 'brand';
  return 'neutral';
}

export default function MediaProcessingPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [stats, setStats] = useState<MediaStats | null>(null);
  const [loading, setLoading] = useState(Boolean(tenantId));
  const [hasLoaded, setHasLoaded] = useState(!tenantId);
  const [error, setError] = useState(tenantId ? '' : 'Sign in and select a workspace to view media jobs.');

  const load = useCallback(async () => {
    if (!tenantId) return;
    try {
      const [jobsResponse, statsResponse] = await Promise.all([
        apiGet<JobsResponse>('/media/jobs', tenantId),
        apiGet<StatsResponse>('/media/jobs/stats', tenantId),
      ]);
      const metrics = statsResponse.stats;
      if (
        !Array.isArray(jobsResponse.jobs) ||
        !metrics ||
        ![metrics.total_jobs, metrics.active_jobs, metrics.completed_jobs, metrics.failed_jobs].every(Number.isFinite)
      ) {
        throw new Error('The media service returned an incomplete workspace response.');
      }
      setError('');
      setJobs(jobsResponse.jobs);
      setStats(metrics);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load media jobs.');
      setJobs([]);
      setStats(null);
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;
    let active = true;
    window.queueMicrotask(() => {
      if (active) void load();
    });
    return () => {
      active = false;
    };
  }, [load, tenantId]);

  const refresh = () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    void load();
  };

  const dataActions = loading
    ? <span role="status" style={{ color: 'var(--nx-muted)', fontSize: 12 }}>Loading workspace data…</span>
    : hasLoaded
      ? <DataStatus state={error ? 'unavailable' : 'live'} provider="media service" />
      : undefined;

  return (
    <Page>
      <PageHeader
        title="Media Processing"
        subtitle="Upload assets, follow processing progress, and review recent jobs."
        actions={dataActions}
      />

      {error ? (
        <Card>
          <div role="alert" style={{ color: 'var(--nx-red)', lineHeight: 1.6 }}>{error}</div>
        </Card>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 12 }}>
        <Card><CardTitle sub="All jobs in this workspace">Total jobs</CardTitle><p style={{ fontSize: 24, fontWeight: 700, margin: '10px 0 0' }}>{formatCount(stats?.total_jobs)}</p></Card>
        <Card><CardTitle sub="Waiting or in progress">Active</CardTitle><p style={{ fontSize: 24, fontWeight: 700, margin: '10px 0 0' }}>{formatCount(stats?.active_jobs)}</p></Card>
        <Card><CardTitle sub="Completed successfully">Completed</CardTitle><p style={{ fontSize: 24, fontWeight: 700, margin: '10px 0 0' }}>{formatCount(stats?.completed_jobs)}</p></Card>
        <Card><CardTitle sub="Jobs that need attention">Failed</CardTitle><p style={{ fontSize: 24, fontWeight: 700, margin: '10px 0 0' }}>{formatCount(stats?.failed_jobs)}</p></Card>
      </div>

      <Card>
        <CardTitle sub="Select a supported file to start a workspace-scoped processing job.">Upload media</CardTitle>
        <div style={{ marginTop: 16 }}>
          <MediaUploader onComplete={refresh} />
        </div>
      </Card>

      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
          <CardTitle sub="Processing state and timestamps returned by the media service.">Recent jobs</CardTitle>
          <Button onClick={refresh} disabled={loading || !tenantId}>Refresh</Button>
        </div>
        {loading && !hasLoaded ? <p role="status" style={{ color: 'var(--nx-muted)' }}>Loading jobs…</p> : null}
        {!loading && !error && jobs.length === 0 ? <p style={{ color: 'var(--nx-muted)', lineHeight: 1.6 }}>No media jobs yet.</p> : null}
        {jobs.length > 0 ? (
          <TableWrap>
            <table className={tableClass}>
              <caption style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 }}>Media processing jobs</caption>
              <thead>
                <tr><th scope="col">Job</th><th scope="col">Media</th><th scope="col">Provider</th><th scope="col">Status</th><th scope="col">Progress</th><th scope="col">Created</th></tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>#{job.id}</td>
                    <td>{job.media_type || '—'}</td>
                    <td>{job.provider || '—'}</td>
                    <td><Badge tone={statusTone(job.status)}>{job.status || 'Unknown'}</Badge></td>
                    <td>{Number.isFinite(job.progress_pct) ? `${Math.max(0, Math.min(100, job.progress_pct))}%` : '—'}</td>
                    <td>{formatDate(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        ) : null}
      </Card>
    </Page>
  );
}
