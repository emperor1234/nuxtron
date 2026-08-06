'use client';

import { useEffect, useRef, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type GeneratedAsset = {
  id: number;
  kind: string;
  mime_type: string;
  file_name: string;
  download_url: string;
  generation_status: string;
  provider_used: string;
  size_bytes: number;
};

type ContentGenerationItem = {
  generation_id: string;
  created_at: string;
  channel: string;
  tone: string;
  topic: string;
  audience: string;
  headline: string;
  body: string;
  provider_used: string;
  model_used: string;
  ai_status: string;
  asset_urls?: { image?: string; video?: string; voice?: string };
  generated_assets?: { image?: GeneratedAsset; voice?: GeneratedAsset; video?: GeneratedAsset };
  seo?: { meta_title: string; meta_description: string; focus_keyword: string } | null;
};

export type ContentGenerationJob = {
  job_id: string;
  status: string;
  progress_pct: number;
  stage: string;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
  is_terminal?: boolean;
  expires_at?: string | null;
};

type AsyncSubmitResponse = {
  status: string;
  job_id: string;
  poll_url: string;
  stream_url: string;
  cancel_url: string;
  retry_url: string;
};

type JobEnvelope = {
  status: string;
  tenant_id: string;
  job: ContentGenerationJob;
};

type JobListEnvelope = {
  status: string;
  tenant_id: string;
  count: number;
  items: ContentGenerationJob[];
  retention?: {
    terminal_seconds?: number;
  };
};

type JobStatusTab = 'all' | 'pending' | 'running' | 'failed' | 'completed' | 'cancelled';
type JobStatusCounts = Record<JobStatusTab, number>;
type QueueStageFilter = 'all' | 'timeout' | 'failed';

const QUEUE_AUTO_REFRESH_ENABLED_KEY = 'nuxtron:content-queue:auto-refresh-enabled';
const QUEUE_AUTO_REFRESH_SECONDS_KEY = 'nuxtron:content-queue:auto-refresh-seconds';
const DEFAULT_QUEUE_AUTO_REFRESH_ENABLED = true;
const DEFAULT_QUEUE_AUTO_REFRESH_SECONDS = 8;

function jobStatusBadgeStyle(status: string): Record<string, string | number> {
  const normalized = status.trim().toLowerCase();
  if (normalized === 'completed') {
    return { background: 'rgba(34,197,94,0.16)', color: '#4ade80', border: '1px solid rgba(34,197,94,0.35)' };
  }
  if (normalized === 'failed') {
    return { background: 'rgba(248,113,113,0.16)', color: '#f87171', border: '1px solid rgba(248,113,113,0.35)' };
  }
  if (normalized === 'pending' || normalized === 'running') {
    return { background: 'rgba(251,191,36,0.16)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.35)' };
  }
  if (normalized === 'cancelled') {
    return { background: 'rgba(148,163,184,0.16)', color: '#cbd5e1', border: '1px solid rgba(148,163,184,0.35)' };
  }
  return { background: 'rgba(148,163,184,0.12)', color: '#cbd5e1', border: '1px solid rgba(148,163,184,0.25)' };
}

function normalizeJobStage(stage: string): string {
  return stage.trim().toLowerCase();
}

function isFailedStage(stage: string): boolean {
  const normalized = normalizeJobStage(stage);
  return normalized === 'failed' || normalized === 'error';
}

export function filterQueueItemsByStage(
  items: ContentGenerationJob[],
  stageFilter: QueueStageFilter
): ContentGenerationJob[] {
  if (stageFilter === 'all') {
    return items;
  }
  if (stageFilter === 'timeout') {
    return items.filter((item) => normalizeJobStage(String(item.stage || '')) === 'timeout');
  }
  return items.filter((item) => isFailedStage(String(item.stage || '')));
}

function stageBadgeStyle(stage: string): Record<string, string | number> {
  const normalized = normalizeJobStage(stage);
  if (normalized === 'timeout') {
    return { background: 'rgba(249,115,22,0.16)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.35)' };
  }
  if (normalized === 'failed') {
    return { background: 'rgba(248,113,113,0.16)', color: '#f87171', border: '1px solid rgba(248,113,113,0.35)' };
  }
  return { background: 'rgba(148,163,184,0.12)', color: '#cbd5e1', border: '1px solid rgba(148,163,184,0.25)' };
}

function relativeTimeLabel(iso: string, nowMs: number): string {
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return 'just now';

  const diffMs = ts - nowMs;
  const isFuture = diffMs > 0;
  const absSec = Math.max(1, Math.round(Math.abs(diffMs) / 1000));

  const units: Array<[name: string, size: number]> = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
    ['second', 1],
  ];

  for (const [name, size] of units) {
    if (absSec >= size || name === 'second') {
      const value = Math.floor(absSec / size);
      const suffix = value === 1 ? name : `${name}s`;
      return isFuture ? `in ${value} ${suffix}` : `${value} ${suffix} ago`;
    }
  }

  return 'just now';
}

function apiLink(path: string): string {
  return `/api/fastapi${path}`;
}

export default function ContentGenerationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [topic, setTopic] = useState('AI workflow automation');
  const [audience, setAudience] = useState('Growth teams');
  const [channel, setChannel] = useState('linkedin');
  const [tone, setTone] = useState('professional');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [activeJob, setActiveJob] = useState<ContentGenerationJob | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [runningAsync, setRunningAsync] = useState(false);
  const [queueStatusTab, setQueueStatusTab] = useState<JobStatusTab>('all');
  const [queueStageFilter, setQueueStageFilter] = useState<QueueStageFilter>('all');
  const [queueItems, setQueueItems] = useState<ContentGenerationJob[]>([]);
  const [queueRetentionSeconds, setQueueRetentionSeconds] = useState(0);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueNowTick, setQueueNowTick] = useState(() => Date.now());
  const [queueAutoRefreshEnabled, setQueueAutoRefreshEnabled] = useState(DEFAULT_QUEUE_AUTO_REFRESH_ENABLED);
  const [queueAutoRefreshSeconds, setQueueAutoRefreshSeconds] = useState(DEFAULT_QUEUE_AUTO_REFRESH_SECONDS);
  const [queueLastRefreshAt, setQueueLastRefreshAt] = useState<string | null>(null);
  const [queueStatusCounts, setQueueStatusCounts] = useState<JobStatusCounts>({
    all: 0,
    pending: 0,
    running: 0,
    failed: 0,
    completed: 0,
    cancelled: 0,
  });
  const [queueStageCounts, setQueueStageCounts] = useState<Record<QueueStageFilter, number>>({
    all: 0,
    timeout: 0,
    failed: 0,
  });
  const [library, setLibrary] = useState<ContentGenerationItem[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [jobActionBusy, setJobActionBusy] = useState(false);
  const [usingPollingFallback, setUsingPollingFallback] = useState(false);
  const [error, setError] = useState('');
  const streamRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const streamErrorCountRef = useRef(0);

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  async function loadLibrary() {
    setLoadingLibrary(true);
    try {
      const data = await apiGet<{ items?: ContentGenerationItem[] }>('/content/library', tenantId);
      setLibrary(data.items ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load content library');
    } finally {
      setLoadingLibrary(false);
    }
  }

  useEffect(() => {
    void loadLibrary();
  }, [tenantId]);

  async function loadJobQueue(tab = queueStatusTab) {
    setLoadingQueue(true);
    try {
      const statusQuery = tab === 'all' ? '' : `&status=${encodeURIComponent(tab)}`;
      const [data, aggregate] = await Promise.all([
        apiGet<JobListEnvelope>(`/content/generate/jobs?limit=20${statusQuery}`, tenantId),
        apiGet<JobListEnvelope>('/content/generate/jobs?limit=100', tenantId),
      ]);
      const rawItems = Array.isArray(data.items) ? data.items : [];
      setQueueItems(filterQueueItemsByStage(rawItems, queueStageFilter));
      setQueueRetentionSeconds(Number(data.retention?.terminal_seconds ?? 0));

      const counts: JobStatusCounts = {
        all: 0,
        pending: 0,
        running: 0,
        failed: 0,
        completed: 0,
        cancelled: 0,
      };
      for (const item of aggregate.items ?? []) {
        const normalized = String(item.status || '')
          .trim()
          .toLowerCase() as JobStatusTab;
        if (normalized in counts && normalized !== 'all') {
          counts[normalized] += 1;
          counts.all += 1;
        }
      }
      const aggregateItems = Array.isArray(aggregate.items) ? aggregate.items : [];
      const timeoutCount = filterQueueItemsByStage(aggregateItems, 'timeout').length;
      const failedStageCount = filterQueueItemsByStage(aggregateItems, 'failed').length;
      setQueueStatusCounts(counts);
      setQueueStageCounts({
        all: counts.all,
        timeout: timeoutCount,
        failed: failedStageCount,
      });
      setQueueLastRefreshAt(new Date().toISOString());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load content job queue');
    } finally {
      setLoadingQueue(false);
    }
  }

  useEffect(() => {
    void loadJobQueue(queueStatusTab);
  }, [tenantId, queueStatusTab, queueStageFilter]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setQueueNowTick(Date.now());
    }, 30000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    try {
      const rawEnabled = window.localStorage.getItem(QUEUE_AUTO_REFRESH_ENABLED_KEY);
      if (rawEnabled === 'true' || rawEnabled === 'false') {
        setQueueAutoRefreshEnabled(rawEnabled === 'true');
      }

      const rawSeconds = window.localStorage.getItem(QUEUE_AUTO_REFRESH_SECONDS_KEY);
      const parsedSeconds = Number(rawSeconds || '');
      if ([5, 8, 10, 15].includes(parsedSeconds)) {
        setQueueAutoRefreshSeconds(parsedSeconds);
      }
    } catch {
      // Ignore storage access issues (private mode / strict browser policies).
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(QUEUE_AUTO_REFRESH_ENABLED_KEY, String(queueAutoRefreshEnabled));
    } catch {
      // Ignore persistence failures; runtime behavior still works.
    }
  }, [queueAutoRefreshEnabled]);

  useEffect(() => {
    try {
      window.localStorage.setItem(QUEUE_AUTO_REFRESH_SECONDS_KEY, String(queueAutoRefreshSeconds));
    } catch {
      // Ignore persistence failures; runtime behavior still works.
    }
  }, [queueAutoRefreshSeconds]);

  function resetQueuePreferences() {
    setQueueAutoRefreshEnabled(DEFAULT_QUEUE_AUTO_REFRESH_ENABLED);
    setQueueAutoRefreshSeconds(DEFAULT_QUEUE_AUTO_REFRESH_SECONDS);
    try {
      window.localStorage.removeItem(QUEUE_AUTO_REFRESH_ENABLED_KEY);
      window.localStorage.removeItem(QUEUE_AUTO_REFRESH_SECONDS_KEY);
    } catch {
      // Ignore storage removal failures; in-memory defaults still apply.
    }
  }

  useEffect(() => {
    if (!queueAutoRefreshEnabled) return;
    const intervalMs = Math.max(3, queueAutoRefreshSeconds) * 1000;
    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void loadJobQueue(queueStatusTab);
    }, intervalMs);
    return () => window.clearInterval(intervalId);
  }, [queueAutoRefreshEnabled, queueAutoRefreshSeconds, queueStatusTab, queueStageFilter]);

  function closeStream() {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  }

  function stopPollingFallback() {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setUsingPollingFallback(false);
  }

  function startPollingFallback(jobId: string) {
    if (pollTimerRef.current !== null) return;
    setUsingPollingFallback(true);
    pollTimerRef.current = window.setInterval(() => {
      void loadJob(jobId)
        .then((job) => {
          if (['completed', 'failed', 'cancelled'].includes(job.status)) {
            stopPollingFallback();
          }
        })
        .catch(() => {
          // Keep fallback alive through transient errors; user can still refresh manually.
        });
    }, 1000);
  }

  function updateJobAndResult(job: ContentGenerationJob) {
    setActiveJob(job);
    if (job.result && typeof job.result === 'object') {
      setResult(job.result);
    }
    if (['completed', 'failed', 'cancelled'].includes(job.status)) {
      setRunningAsync(false);
    }
  }

  function parseSsePayload(evt: MessageEvent) {
    try {
      const parsed = JSON.parse(String(evt.data ?? '{}')) as { payload?: ContentGenerationJob };
      if (parsed && parsed.payload && typeof parsed.payload === 'object') {
        updateJobAndResult(parsed.payload);
      }
    } catch {
      // Ignore malformed stream events and keep the current stream alive.
    }
  }

  function openJobStream(jobId: string) {
    closeStream();
    stopPollingFallback();
    streamErrorCountRef.current = 0;

    const streamUrl = new URL(apiLink(`/content/generate/jobs/${jobId}/stream`), window.location.origin);
    streamUrl.searchParams.set('tenant_id', tenantId);
    // The proxy route resolves and attaches the real service key
    // server-side; the browser must never hold or transmit it.

    const source = new EventSource(streamUrl.toString());
    const sseHandler = ((evt: MessageEvent) => {
      streamErrorCountRef.current = 0;
      parseSsePayload(evt);
    }) as EventListener;

    source.addEventListener('content-job.snapshot', sseHandler);
    source.addEventListener('content-job.updated', sseHandler);
    source.addEventListener('content-job.terminated', sseHandler);
    source.onerror = () => {
      streamErrorCountRef.current += 1;
      if (streamErrorCountRef.current >= 3) {
        closeStream();
        startPollingFallback(jobId);
      }
    };
    streamRef.current = source;
  }

  async function loadJob(jobId: string) {
    const data = await apiGet<JobEnvelope>(`/content/generate/jobs/${jobId}`, tenantId);
    updateJobAndResult(data.job);
    return data.job;
  }

  async function startAsyncGeneration() {
    try {
      setError('');
      setRunningAsync(true);
      setUsingPollingFallback(false);
      const accepted = await apiSend<AsyncSubmitResponse>(
        '/content/generate/async',
        'POST',
        {
          topic,
          audience,
          channel,
          tone,
          include_seo: true,
        },
        tenantId
      );
      setActiveJobId(accepted.job_id);
      const snapshot = await loadJob(accepted.job_id);
      if (!['completed', 'failed', 'cancelled'].includes(snapshot.status)) {
        openJobStream(accepted.job_id);
      } else {
        setRunningAsync(false);
        await loadLibrary();
      }
      await loadJobQueue();
    } catch (e) {
      setRunningAsync(false);
      setError(e instanceof Error ? e.message : 'Async content generation failed');
    }
  }

  async function cancelActiveJob() {
    if (!activeJobId) return;
    try {
      setJobActionBusy(true);
      setError('');
      const data = await apiSend<JobEnvelope>(`/content/generate/jobs/${activeJobId}`, 'DELETE', undefined, tenantId);
      updateJobAndResult(data.job);
      closeStream();
      stopPollingFallback();
      await loadLibrary();
      await loadJobQueue();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cancel the active job');
    } finally {
      setJobActionBusy(false);
    }
  }

  async function retryActiveJob() {
    if (!activeJobId) return;
    try {
      setJobActionBusy(true);
      setError('');
      const data = await apiSend<JobEnvelope>(`/content/generate/jobs/${activeJobId}/retry`, 'POST', {}, tenantId);
      updateJobAndResult(data.job);
      if (!['completed', 'failed', 'cancelled'].includes(data.job.status)) {
        setRunningAsync(true);
        setUsingPollingFallback(false);
        openJobStream(activeJobId);
      }
      await loadJobQueue();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to retry the active job');
    } finally {
      setJobActionBusy(false);
    }
  }

  useEffect(() => {
    if (!activeJob) return;
    if (['completed', 'failed', 'cancelled'].includes(activeJob.status)) {
      closeStream();
      stopPollingFallback();
      void loadLibrary();
      void loadJobQueue();
    }
  }, [activeJob]);

  useEffect(() => {
    return () => {
      closeStream();
      stopPollingFallback();
    };
  }, []);

  async function run() {
    try {
      setError('');
      const data = await apiSend<Record<string, unknown>>(
        '/content/generate',
        'POST',
        {
          topic,
          audience,
          channel,
          tone,
          include_seo: true,
        },
        tenantId
      );
      setResult(data);
      await loadLibrary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Content generation failed');
    }
  }

  const latest = library[0];
  const outputs = result && typeof result.outputs === 'object' ? (result.outputs as Record<string, unknown>) : null;
  const generatedAssets =
    result && typeof result.generated_assets === 'object'
      ? (result.generated_assets as Record<string, GeneratedAsset>)
      : null;
  const seo = result && typeof result.seo === 'object' ? (result.seo as Record<string, unknown>) : null;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 20 }}>
        <section
          style={{ ...card, background: 'linear-gradient(135deg, rgba(6,182,212,0.12), rgba(16,185,129,0.08))' }}
        >
          <h1 style={{ marginTop: 0, marginBottom: 8 }}>AI Content Generation</h1>
          <p style={{ color: 'var(--muted)', marginTop: 0, maxWidth: 760 }}>
            Generate channel-ready marketing content, persist the output history, and jump directly to downloadable
            assets from the same workflow.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 16 }}>
            <button
              onClick={() => void startAsyncGeneration()}
              disabled={runningAsync}
              style={{
                padding: '10px 14px',
                border: 'none',
                borderRadius: 10,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
                opacity: runningAsync ? 0.7 : 1,
              }}
            >
              {runningAsync ? 'Generating...' : 'Generate Async'}
            </button>
            <button
              onClick={() => void run()}
              style={{
                padding: '10px 14px',
                border: '1px solid var(--line)',
                borderRadius: 10,
                background: 'transparent',
                color: 'var(--text)',
                fontWeight: 600,
              }}
            >
              Generate Sync
            </button>
            <button
              onClick={() => void loadLibrary()}
              style={{
                padding: '10px 14px',
                border: '1px solid var(--line)',
                borderRadius: 10,
                background: 'transparent',
                color: 'var(--text)',
                fontWeight: 600,
              }}
            >
              {loadingLibrary ? 'Refreshing...' : 'Refresh Library'}
            </button>
          </div>
        </section>

        {activeJob && (
          <section style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <div>
                <h2 style={{ marginTop: 0, marginBottom: 6 }}>Active Async Job</h2>
                <div style={{ color: 'var(--muted)' }}>
                  Job {activeJob.job_id} • Status {activeJob.status} • Stage {activeJob.stage}
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                  <span
                    style={{
                      ...jobStatusBadgeStyle(String(activeJob.status || '')),
                      padding: '2px 8px',
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 700,
                      textTransform: 'capitalize',
                    }}
                  >
                    {activeJob.status}
                  </span>
                  <span
                    style={{
                      ...stageBadgeStyle(String(activeJob.stage || 'unknown')),
                      padding: '2px 8px',
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 700,
                      textTransform: 'capitalize',
                    }}
                  >
                    stage: {activeJob.stage || 'unknown'}
                  </span>
                </div>
                <div style={{ color: 'var(--muted)', marginTop: 4 }}>
                  Transport: {usingPollingFallback ? 'polling fallback' : 'live stream'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  onClick={() => void cancelActiveJob()}
                  disabled={jobActionBusy || !['pending', 'running'].includes(activeJob.status)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--line)',
                    background: 'transparent',
                    color: 'var(--text)',
                    opacity: jobActionBusy || !['pending', 'running'].includes(activeJob.status) ? 0.6 : 1,
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => void retryActiveJob()}
                  disabled={jobActionBusy || !['failed', 'cancelled'].includes(activeJob.status)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--line)',
                    background: 'transparent',
                    color: 'var(--text)',
                    opacity: jobActionBusy || !['failed', 'cancelled'].includes(activeJob.status) ? 0.6 : 1,
                  }}
                >
                  Retry
                </button>
                <button
                  onClick={() => {
                    if (activeJobId) {
                      void loadJob(activeJobId);
                    }
                    void loadJobQueue();
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--line)',
                    background: 'transparent',
                    color: 'var(--text)',
                  }}
                >
                  Refresh Status
                </button>
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <div
                style={{
                  width: '100%',
                  height: 10,
                  borderRadius: 999,
                  background: 'var(--bg-soft)',
                  border: '1px solid var(--line)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.max(0, Math.min(100, Number(activeJob.progress_pct) || 0))}%`,
                    height: '100%',
                    background: 'var(--brand)',
                    transition: 'width 220ms ease',
                  }}
                />
              </div>
              <div style={{ marginTop: 8, color: 'var(--muted)' }}>
                {Number(activeJob.progress_pct) || 0}% complete
                {activeJob.error ? ` • ${activeJob.error}` : ''}
              </div>
            </div>
          </section>
        )}

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 20 }}>
          <div style={card}>
            <h2 style={{ marginTop: 0 }}>Prompt Inputs</h2>
            <input style={input} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="topic" />
            <input
              style={input}
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="audience"
            />
            <select style={input} value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option value="linkedin">linkedin</option>
              <option value="x">x</option>
              <option value="instagram">instagram</option>
              <option value="facebook">facebook</option>
              <option value="blog">blog</option>
              <option value="youtube">youtube</option>
              <option value="tiktok">tiktok</option>
              <option value="threads">threads</option>
            </select>
            <select style={input} value={tone} onChange={(e) => setTone(e.target.value)}>
              <option value="professional">professional</option>
              <option value="casual">casual</option>
              <option value="bold">bold</option>
              <option value="friendly">friendly</option>
            </select>
          </div>

          <div style={card}>
            <h2 style={{ marginTop: 0 }}>Latest Result</h2>
            {result ? (
              <div style={{ display: 'grid', gap: 12 }}>
                <div>
                  <strong>{String(result.headline ?? 'Untitled')}</strong>
                  <div style={{ color: 'var(--muted)', marginTop: 4 }}>{String(result.body ?? '')}</div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, color: 'var(--muted)' }}>
                  <span>Generation: {String(result.generation_id ?? 'n/a')}</span>
                  <span>Provider: {String(result.provider_used ?? 'n/a')}</span>
                  <span>Model: {String(result.model_used ?? 'n/a')}</span>
                  <span>Status: {String(result.ai_status ?? 'unknown')}</span>
                </div>
                {seo && (
                  <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>SEO</div>
                    <div>{String(seo.meta_title ?? '')}</div>
                    <div style={{ color: 'var(--muted)' }}>{String(seo.meta_description ?? '')}</div>
                  </div>
                )}
                {outputs && (
                  <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12, display: 'grid', gap: 8 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>Asset Links</div>
                    {['image_url', 'video_url', 'voice_url'].map((key) => {
                      const raw = String(outputs[key] ?? '');
                      if (!raw) return null;
                      return (
                        <a
                          key={key}
                          href={apiLink(raw)}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--brand)' }}
                        >
                          Open {key.replace('_url', '')}
                        </a>
                      );
                    })}
                  </div>
                )}
                {generatedAssets && (
                  <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12, display: 'grid', gap: 8 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>Generated Assets</div>
                    {Object.entries(generatedAssets).map(([kind, asset]) => (
                      <a
                        key={kind}
                        href={apiLink(asset.download_url)}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--brand)' }}
                      >
                        {kind}: {asset.file_name}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--muted)' }}>Run a generation to see a structured result here.</div>
            )}
          </div>
        </section>

        <section style={card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 6 }}>Job Queue</h2>
              <p style={{ color: 'var(--muted)', margin: 0 }}>
                Recent tenant jobs with status filters and retention-aware visibility.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => setQueueAutoRefreshEnabled((current) => !current)}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: queueAutoRefreshEnabled ? 'rgba(34,197,94,0.16)' : 'transparent',
                  color: 'var(--text)',
                  fontWeight: 600,
                }}
              >
                Auto Refresh: {queueAutoRefreshEnabled ? 'On' : 'Off'}
              </button>
              <select
                value={String(queueAutoRefreshSeconds)}
                onChange={(event) => setQueueAutoRefreshSeconds(Number(event.target.value) || 8)}
                disabled={!queueAutoRefreshEnabled}
                style={{
                  padding: '8px 10px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'var(--bg)',
                  color: 'var(--text)',
                  opacity: queueAutoRefreshEnabled ? 1 : 0.6,
                }}
              >
                <option value="5">5s</option>
                <option value="8">8s</option>
                <option value="10">10s</option>
                <option value="15">15s</option>
              </select>
              <button
                onClick={() => void loadJobQueue()}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                {loadingQueue ? 'Refreshing...' : 'Refresh Queue'}
              </button>
              <button
                onClick={resetQueuePreferences}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                Reset Preferences
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
            {(['all', 'pending', 'running', 'failed', 'completed', 'cancelled'] as JobStatusTab[]).map((tab) => {
              const active = queueStatusTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setQueueStatusTab(tab)}
                  style={{
                    padding: '7px 11px',
                    borderRadius: 999,
                    border: '1px solid var(--line)',
                    background: active ? 'var(--brand)' : 'transparent',
                    color: active ? '#00101e' : 'var(--text)',
                    fontWeight: 600,
                  }}
                >
                  {tab} ({queueStatusCounts[tab] ?? 0})
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
            {(['all', 'timeout', 'failed'] as QueueStageFilter[]).map((stageFilter) => {
              const active = queueStageFilter === stageFilter;
              const count = queueStageCounts[stageFilter] ?? 0;
              return (
                <button
                  key={stageFilter}
                  onClick={() => setQueueStageFilter(stageFilter)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: 999,
                    border: '1px solid var(--line)',
                    background: active ? 'rgba(249,115,22,0.2)' : 'transparent',
                    color: active ? '#fb923c' : 'var(--text)',
                    fontWeight: 600,
                  }}
                >
                  stage:{stageFilter} ({count})
                </button>
              );
            })}
          </div>

          <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
            {queueItems.length > 0 ? (
              queueItems.map((job) => (
                <article
                  key={job.job_id}
                  style={{
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: 12,
                    display: 'grid',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                    <strong>{job.job_id}</strong>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                      <span
                        style={{
                          ...jobStatusBadgeStyle(String(job.status || '')),
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: 12,
                          fontWeight: 700,
                          textTransform: 'capitalize',
                        }}
                      >
                        {job.status}
                      </span>
                      <span
                        style={{
                          ...stageBadgeStyle(String(job.stage || 'unknown')),
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: 12,
                          fontWeight: 700,
                          textTransform: 'capitalize',
                        }}
                      >
                        stage: {job.stage || 'unknown'}
                      </span>
                      <span style={{ color: 'var(--muted)' }}>{Number(job.progress_pct) || 0}%</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', color: 'var(--muted)', fontSize: 12 }}>
                    {job.updated_at && (
                      <span>
                        Updated: {new Date(job.updated_at).toLocaleString()} (
                        {relativeTimeLabel(job.updated_at, queueNowTick)})
                      </span>
                    )}
                    {job.expires_at && (
                      <span>
                        Expires: {new Date(job.expires_at).toLocaleString()} (
                        {relativeTimeLabel(job.expires_at, queueNowTick)})
                      </span>
                    )}
                    {job.error && <span>Error: {job.error}</span>}
                  </div>
                </article>
              ))
            ) : (
              <div style={{ color: 'var(--muted)' }}>
                {loadingQueue ? 'Loading queue...' : 'No jobs found for this filter.'}
              </div>
            )}
          </div>

          {queueRetentionSeconds > 0 && (
            <div style={{ marginTop: 12, color: 'var(--muted)', fontSize: 12 }}>
              Terminal job retention: {queueRetentionSeconds} seconds.
            </div>
          )}
          {queueLastRefreshAt && (
            <div style={{ marginTop: 4, color: 'var(--muted)', fontSize: 12 }}>
              Last queue refresh: {new Date(queueLastRefreshAt).toLocaleTimeString()} (
              {relativeTimeLabel(queueLastRefreshAt, queueNowTick)})
            </div>
          )}
        </section>

        <section style={card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 6 }}>Content Library</h2>
              <p style={{ color: 'var(--muted)', margin: 0 }}>Persisted generation history for the current tenant.</p>
            </div>
            <div style={{ color: 'var(--muted)' }}>{library.length} item(s)</div>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))',
              gap: 14,
              marginTop: 16,
            }}
          >
            {library.length > 0 ? (
              library.map((item) => (
                <article
                  key={item.generation_id}
                  style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <strong>{item.headline}</strong>
                    <span style={{ color: 'var(--muted)' }}>{item.channel}</span>
                  </div>
                  <div style={{ color: 'var(--muted)', marginTop: 6, lineHeight: 1.5 }}>{item.body}</div>
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: 8,
                      marginTop: 12,
                      fontSize: 12,
                      color: 'var(--muted)',
                    }}
                  >
                    <span>{item.tone}</span>
                    <span>{item.provider_used}</span>
                    <span>{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                    <a
                      href={apiLink(`/content/library/${item.generation_id}`)}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: 'var(--brand)' }}
                    >
                      Open generation
                    </a>
                    {item.generated_assets &&
                      Object.values(item.generated_assets).map((asset) => (
                        <a
                          key={asset.id}
                          href={apiLink(asset.download_url)}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--brand)' }}
                        >
                          Download {asset.kind} asset
                        </a>
                      ))}
                  </div>
                </article>
              ))
            ) : (
              <div style={{ color: 'var(--muted)' }}>No content has been generated yet.</div>
            )}
          </div>
          {latest && (
            <div style={{ marginTop: 16, color: 'var(--muted)' }}>
              Latest generation: {latest.generation_id} from {new Date(latest.created_at).toLocaleString()}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
