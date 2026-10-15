'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import {
  contentProvenance,
  parseContentLibrary,
  parseContentResult,
  parseJobList,
  type ContentGenerationJob,
  type ContentLibrarySummary,
} from './content-generation-model';

export type { ContentGenerationJob } from './content-generation-model';

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

type AsyncSubmitResponse = {
  status: string;
  job_id: string;
  poll_url: string;
};

type JobEnvelope = {
  status: string;
  job: ContentGenerationJob;
};

type JobStatusTab = 'all' | 'pending' | 'running' | 'failed' | 'completed' | 'cancelled';
type JobStatusCounts = Record<JobStatusTab, number>;
type QueueStageFilter = 'all' | 'timeout' | 'failed';

const DEFAULT_QUEUE_AUTO_REFRESH_ENABLED = false;
const DEFAULT_QUEUE_AUTO_REFRESH_SECONDS = 30;

function sessionWorkspace(): string {
  try {
    return resolveSessionTenant();
  } catch {
    return '';
  }
}

function jobStatusBadgeStyle(status: string): Record<string, string | number> {
  const normalized = status.trim().toLowerCase();
  if (normalized === 'completed') {
    return { background: 'rgba(34,197,94,0.16)', color: 'var(--success)', border: '1px solid rgba(34,197,94,0.35)' };
  }
  if (normalized === 'failed') {
    return { background: 'rgba(248,113,113,0.16)', color: 'var(--danger)', border: '1px solid rgba(248,113,113,0.35)' };
  }
  if (normalized === 'pending' || normalized === 'running') {
    return { background: 'rgba(251,191,36,0.16)', color: 'var(--warning)', border: '1px solid rgba(251,191,36,0.35)' };
  }
  if (normalized === 'cancelled') {
    return { background: 'rgba(148,163,184,0.16)', color: 'var(--neutral-line)', border: '1px solid rgba(148,163,184,0.35)' };
  }
  return { background: 'rgba(148,163,184,0.12)', color: 'var(--neutral-line)', border: '1px solid rgba(148,163,184,0.25)' };
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
    return { background: 'rgba(249,115,22,0.16)', color: 'var(--warning)', border: '1px solid rgba(249,115,22,0.35)' };
  }
  if (normalized === 'failed') {
    return { background: 'rgba(248,113,113,0.16)', color: 'var(--danger)', border: '1px solid rgba(248,113,113,0.35)' };
  }
  return { background: 'rgba(148,163,184,0.12)', color: 'var(--neutral-line)', border: '1px solid rgba(148,163,184,0.25)' };
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
  const localPath = path.trim();
  return localPath.startsWith('/') && !localPath.startsWith('//') ? `/api/fastapi${localPath}` : '#';
}

export default function ContentGenerationPage() {
  const [tenantId] = useState(sessionWorkspace);
  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState('');
  const [channel, setChannel] = useState('');
  const [tone, setTone] = useState('');
  const [runInBackground, setRunInBackground] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [activeJob, setActiveJob] = useState<ContentGenerationJob | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [runningAsync, setRunningAsync] = useState(false);
  const [runningSync, setRunningSync] = useState(false);
  const [queueStatusTab, setQueueStatusTab] = useState<JobStatusTab>('all');
  const [queueStageFilter, setQueueStageFilter] = useState<QueueStageFilter>('all');
  const [queueItems, setQueueItems] = useState<ContentGenerationJob[]>([]);
  const [queueRetentionSeconds, setQueueRetentionSeconds] = useState(0);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueLoaded, setQueueLoaded] = useState(false);
  const [queueError, setQueueError] = useState('');
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
  const [library, setLibrary] = useState<ContentLibrarySummary[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [libraryLoaded, setLibraryLoaded] = useState(false);
  const [libraryError, setLibraryError] = useState('');
  const [loadingLibraryItemId, setLoadingLibraryItemId] = useState<string | null>(null);
  const [libraryItemError, setLibraryItemError] = useState('');
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

  const loadLibrary = useCallback(async () => {
    if (!tenantId) {
      setLibraryError('Sign in to a workspace to load saved content.');
      return;
    }
    setLoadingLibrary(true);
    setLibraryError('');
    try {
      const data = await apiGet<unknown>('/content/library', tenantId);
      const items = parseContentLibrary(data);
      if (!items) throw new Error('The content library returned an invalid response.');
      setLibrary(items);
    } catch (e) {
      setLibraryError(e instanceof Error ? e.message : 'Failed to load content library');
    } finally {
      setLoadingLibrary(false);
      setLibraryLoaded(true);
    }
  }, [tenantId]);

  async function loadLibraryItem(item: ContentLibrarySummary) {
    if (!tenantId) return;
    setLoadingLibraryItemId(item.generationId);
    setLibraryItemError('');
    setResult(null);
    try {
      const response = await apiGet<unknown>(`/content/library/${encodeURIComponent(item.generationId)}`, tenantId);
      const savedResult = parseContentResult(response);
      if (!savedResult) throw new Error('The saved generation did not include readable copy.');
      setResult(savedResult);
    } catch (e) {
      setLibraryItemError(e instanceof Error ? e.message : 'Failed to load the saved generation');
    } finally {
      setLoadingLibraryItemId(null);
    }
  }

  useEffect(() => {
    const timerId = window.setTimeout(() => void loadLibrary(), 0);
    return () => window.clearTimeout(timerId);
  }, [loadLibrary]);

  const loadJobQueue = useCallback(async (tab = queueStatusTab) => {
    if (!tenantId) {
      setQueueError('Sign in to a workspace to load generation jobs.');
      return;
    }
    setLoadingQueue(true);
    setQueueError('');
    try {
      const statusQuery = tab === 'all' ? '' : `&status=${encodeURIComponent(tab)}`;
      const [data, aggregate] = await Promise.all([
        apiGet<unknown>(`/content/generate/jobs?limit=20${statusQuery}`, tenantId),
        apiGet<unknown>('/content/generate/jobs?limit=100', tenantId),
      ]);
      const page = parseJobList(data);
      const aggregatePage = parseJobList(aggregate);
      if (!page || !aggregatePage) throw new Error('The generation queue returned an invalid response.');
      setQueueItems(filterQueueItemsByStage(page.items, queueStageFilter));
      setQueueRetentionSeconds(page.terminalRetentionSeconds ?? 0);

      const counts: JobStatusCounts = {
        all: 0,
        pending: 0,
        running: 0,
        failed: 0,
        completed: 0,
        cancelled: 0,
      };
      for (const item of aggregatePage.items) {
        const normalized = String(item.status || '')
          .trim()
          .toLowerCase() as JobStatusTab;
        if (normalized in counts && normalized !== 'all') {
          counts[normalized] += 1;
          counts.all += 1;
        }
      }
      const aggregateItems = aggregatePage.items;
      const timeoutCount = filterQueueItemsByStage(aggregateItems, 'timeout').length;
      const failedStageCount = filterQueueItemsByStage(aggregateItems, 'failed').length;
      setQueueStatusCounts(counts);
      setQueueStageCounts({
        all: counts.all,
        timeout: timeoutCount,
        failed: failedStageCount,
      });
      setQueueLastRefreshAt(new Date().toISOString());
      setQueueLoaded(true);
    } catch (e) {
      setQueueError(e instanceof Error ? e.message : 'Failed to load content job queue');
    } finally {
      setLoadingQueue(false);
    }
  }, [tenantId, queueStageFilter, queueStatusTab]);

  useEffect(() => {
    const timerId = window.setTimeout(() => void loadJobQueue(queueStatusTab), 0);
    return () => window.clearTimeout(timerId);
  }, [loadJobQueue, queueStatusTab]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setQueueNowTick(Date.now());
    }, 30000);
    return () => window.clearInterval(intervalId);
  }, []);

  function resetQueuePreferences() {
    setQueueAutoRefreshEnabled(DEFAULT_QUEUE_AUTO_REFRESH_ENABLED);
    setQueueAutoRefreshSeconds(DEFAULT_QUEUE_AUTO_REFRESH_SECONDS);
  }

  useEffect(() => {
    if (!queueAutoRefreshEnabled) return;
    const intervalMs = Math.max(30, queueAutoRefreshSeconds) * 1000;
    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void loadJobQueue(queueStatusTab);
    }, intervalMs);
    return () => window.clearInterval(intervalId);
  }, [queueAutoRefreshEnabled, queueAutoRefreshSeconds, queueStatusTab, loadJobQueue]);

  const closeStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  }, []);

  const clearPollingTimer = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const stopPollingFallback = useCallback(() => {
    clearPollingTimer();
    setUsingPollingFallback(false);
  }, [clearPollingTimer]);

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
      const generatedResult = parseContentResult(job.result);
      if (generatedResult) setResult(generatedResult);
      else if (job.status === 'completed') setError('The completed job did not return a readable content result.');
    }
    if (['completed', 'failed', 'cancelled'].includes(job.status)) {
      setRunningAsync(false);
      setUsingPollingFallback(false);
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
    if (!tenantId) {
      setError('Sign in to a workspace before generating content.');
      return;
    }
    try {
      setError('');
      setResult(null);
      setRunningAsync(true);
      setUsingPollingFallback(false);
      const accepted = await apiSend<AsyncSubmitResponse>(
        '/content/generate/async',
        'POST',
        {
          topic: topic.trim(),
          audience: audience.trim(),
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
    if (!activeJob || !['completed', 'failed', 'cancelled'].includes(activeJob.status)) return;
    closeStream();
    clearPollingTimer();
    const refreshId = window.setTimeout(() => {
      void loadLibrary();
      void loadJobQueue();
    }, 0);
    return () => window.clearTimeout(refreshId);
  }, [activeJob, clearPollingTimer, closeStream, loadJobQueue, loadLibrary]);

  useEffect(() => {
    return () => {
      closeStream();
      clearPollingTimer();
    };
  }, [clearPollingTimer, closeStream]);

  async function run() {
    if (!tenantId) {
      setError('Sign in to a workspace before generating content.');
      return;
    }
    try {
      setError('');
      setResult(null);
      setRunningSync(true);
      const data = await apiSend<unknown>(
        '/content/generate',
        'POST',
        {
          topic: topic.trim(),
          audience: audience.trim(),
          channel,
          tone,
          include_seo: true,
        },
        tenantId
      );
      const generatedResult = parseContentResult(data);
      if (!generatedResult) throw new Error('The generation service returned an invalid content response.');
      setResult(generatedResult);
      await loadLibrary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Content generation failed');
    } finally {
      setRunningSync(false);
    }
  }

  function submitGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    if (!tenantId) {
      setError('Sign in to a workspace before generating content.');
      return;
    }
    if (topic.trim().length < 3 || audience.trim().length < 3 || !channel || !tone) {
      setError('Complete the topic, audience, channel, and tone before generating.');
      return;
    }
    if (runInBackground) void startAsyncGeneration();
    else void run();
  }

  const latest = library[0];
  const generatedAssets =
    result && typeof result.generated_assets === 'object'
      ? (result.generated_assets as Record<string, GeneratedAsset>)
      : null;
  const seo = result && typeof result.seo === 'object' ? (result.seo as Record<string, unknown>) : null;
  const provenance = result ? contentProvenance(result) : 'unknown';
  const hasWorkspace = Boolean(tenantId);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 20 }}>
        <section
          style={{ ...card, background: 'linear-gradient(135deg, rgba(6,182,212,0.12), rgba(16,185,129,0.08))' }}
        >
          <h1 style={{ marginTop: 0, marginBottom: 8 }}>AI Content Generation</h1>
          <p style={{ color: 'var(--muted)', marginTop: 0, maxWidth: 760 }}>
            Create a brief first. Provider output and template fallbacks are identified separately so you can review the source before using the copy.
          </p>
        </section>

        <form onSubmit={submitGeneration} style={{ ...card, display: 'grid', gap: 12 }}>
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 6 }}>Content brief</h2>
            <p style={{ color: 'var(--muted)', margin: 0 }}>Provide the topic and audience; select a channel and tone to shape the result.</p>
          </div>
          <label htmlFor="content-topic" style={{ display: 'grid', gap: 6 }}>
            Topic
            <input id="content-topic" style={input} value={topic} onChange={(event) => { setTopic(event.target.value); setResult(null); }} placeholder="Describe the topic or campaign focus" maxLength={180} minLength={3} required disabled={runningAsync || runningSync} />
          </label>
          <label htmlFor="content-audience" style={{ display: 'grid', gap: 6 }}>
            Audience
            <input id="content-audience" style={input} value={audience} onChange={(event) => { setAudience(event.target.value); setResult(null); }} placeholder="Who should this content reach?" maxLength={120} minLength={3} required disabled={runningAsync || runningSync} />
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
            <label htmlFor="content-channel" style={{ display: 'grid', gap: 6 }}>
              Channel
              <select id="content-channel" style={input} value={channel} onChange={(event) => { setChannel(event.target.value); setResult(null); }} required disabled={runningAsync || runningSync}>
                <option value="" disabled>Choose a channel</option>
                <option value="linkedin">LinkedIn</option>
                <option value="x">X</option>
                <option value="instagram">Instagram</option>
                <option value="facebook">Facebook</option>
                <option value="blog">Blog</option>
                <option value="youtube">YouTube</option>
                <option value="tiktok">TikTok</option>
                <option value="threads">Threads</option>
                <option value="snapchat">Snapchat</option>
                <option value="pinterest">Pinterest</option>
                <option value="reddit">Reddit</option>
              </select>
            </label>
            <label htmlFor="content-tone" style={{ display: 'grid', gap: 6 }}>
              Tone
              <select id="content-tone" style={input} value={tone} onChange={(event) => { setTone(event.target.value); setResult(null); }} required disabled={runningAsync || runningSync}>
                <option value="" disabled>Choose a tone</option>
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="bold">Bold</option>
                <option value="friendly">Friendly</option>
              </select>
            </label>
          </div>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <input type="checkbox" checked={runInBackground} onChange={(event) => setRunInBackground(event.target.checked)} disabled={runningAsync || runningSync} />
            <span>Run as a background job and follow progress. This option may be unavailable when durable workers are not configured.</span>
          </label>
          {!hasWorkspace ? <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>Sign in to a workspace to generate content.</p> : null}
          <div>
            <button type="submit" disabled={!hasWorkspace || runningAsync || runningSync} style={{ padding: '10px 14px', border: 'none', borderRadius: 10, background: 'var(--brand)', color: 'var(--on-brand)', fontWeight: 700, opacity: !hasWorkspace || runningAsync || runningSync ? 0.7 : 1 }}>
              {runningAsync || runningSync ? 'Generating…' : 'Generate content'}
            </button>
          </div>
        </form>

        {activeJob && (
          <section style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <div>
                <h2 style={{ marginTop: 0, marginBottom: 6 }}>Active Async Job</h2>
                <div aria-live="polite" style={{ color: 'var(--muted)' }}>
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
                role="progressbar"
                aria-label={`Generation progress for job ${activeJob.job_id}`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.max(0, Math.min(100, Number(activeJob.progress_pct) || 0))}
                aria-valuetext={`${Math.max(0, Math.min(100, Number(activeJob.progress_pct) || 0))}% complete`}
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

        {error && <div role="alert" style={{ ...card, color: 'var(--danger)' }}>{error}</div>}

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 20 }}>
          <div style={card}>
            <h2 style={{ marginTop: 0 }}>Generation result</h2>
            {result ? (
              <div style={{ display: 'grid', gap: 12 }}>
                {provenance === 'template-fallback' ? (
                  <div role="alert" style={{ border: '1px solid var(--warning-line)', borderRadius: 8, padding: 12, color: 'var(--warning-ink)' }}>
                    Template fallback — this copy was not generated by an AI provider. Review provider availability before treating it as generated content.
                  </div>
                ) : provenance === 'unknown' ? (
                  <div role="status" style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 12, color: 'var(--muted)' }}>
                    The service did not report content provenance. Verify the source before using this copy.
                  </div>
                ) : (
                  <div role="status" style={{ color: 'var(--success)' }}>Provider-generated content</div>
                )}
                <div>
                  <strong>{String(result.headline ?? 'Untitled')}</strong>
                  <div style={{ color: 'var(--muted)', marginTop: 4 }}>{String(result.body ?? '')}</div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, color: 'var(--muted)' }}>
                  <span>Generation: {String(result.generation_id ?? 'n/a')}</span>
                  {provenance === 'ai-generated' ? <span>Provider: {String(result.provider_used ?? 'not reported')}</span> : null}
                  {provenance === 'ai-generated' ? <span>Model: {String(result.model_used ?? 'not reported')}</span> : null}
                </div>
                {seo && (
                  <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>SEO</div>
                    <div>{String(seo.meta_title ?? '')}</div>
                    <div style={{ color: 'var(--muted)' }}>{String(seo.meta_description ?? '')}</div>
                  </div>
                )}
                {generatedAssets && (
                  <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12, display: 'grid', gap: 8 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>Media asset status</div>
                    {Object.entries(generatedAssets).map(([kind, asset]) => {
                      const assetStatus = typeof asset?.generation_status === 'string' ? asset.generation_status : 'status unavailable';
                      const downloadUrl = typeof asset?.download_url === 'string' ? asset.download_url : '';
                      const isRealAsset = assetStatus === 'generated' && downloadUrl.startsWith('/') && !downloadUrl.startsWith('//');
                      return isRealAsset ? (
                        <a key={kind} href={apiLink(downloadUrl)} target="_blank" rel="noreferrer" style={{ color: 'var(--brand)' }}>
                          {kind}: {String(asset.file_name || 'Open asset')}
                        </a>
                      ) : (
                        <span key={kind} style={{ color: 'var(--muted)' }}>{kind}: {assetStatus}</span>
                      );
                    })}
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
                Recent workspace jobs. Background refresh is off until you enable it.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => void loadJobQueue()}
                disabled={loadingQueue || !hasWorkspace}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                {loadingQueue ? 'Refreshing…' : 'Refresh queue'}
              </button>
            </div>
          </div>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Filters and background refresh</summary>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 12 }}>
              <button
                type="button"
                role="switch"
                aria-checked={queueAutoRefreshEnabled}
                onClick={() => setQueueAutoRefreshEnabled((current) => !current)}
                style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'transparent', color: 'var(--text)', fontWeight: 600 }}
              >
                Background refresh: {queueAutoRefreshEnabled ? 'On' : 'Off'}
              </button>
              <label htmlFor="content-queue-refresh-interval">Refresh interval</label>
              <select
                id="content-queue-refresh-interval"
                aria-label="Background refresh interval"
                value={String(queueAutoRefreshSeconds)}
                onChange={(event) => setQueueAutoRefreshSeconds(Number(event.target.value) || 30)}
                disabled={!queueAutoRefreshEnabled}
                style={{ padding: '8px 10px', border: '1px solid var(--line)', borderRadius: 8, background: 'var(--bg)', color: 'var(--text)', opacity: queueAutoRefreshEnabled ? 1 : 0.6 }}
              >
                <option value="30">30 seconds</option>
                <option value="60">60 seconds</option>
                <option value="120">2 minutes</option>
              </select>
              <button type="button" onClick={resetQueuePreferences} style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'transparent', color: 'var(--text)' }}>
                Reset refresh preferences
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              {(['all', 'pending', 'running', 'failed', 'completed', 'cancelled'] as JobStatusTab[]).map((tab) => {
                const active = queueStatusTab === tab;
                return (
                  <button key={tab} aria-pressed={active} onClick={() => setQueueStatusTab(tab)} style={{ padding: '7px 11px', borderRadius: 999, border: '1px solid var(--line)', background: active ? 'var(--brand)' : 'transparent', color: active ? 'var(--on-brand)' : 'var(--text)', fontWeight: 600 }}>
                    {tab}{queueLoaded ? ` (${queueStatusCounts[tab]})` : ''}
                  </button>
                );
              })}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              {(['all', 'timeout', 'failed'] as QueueStageFilter[]).map((stageFilter) => {
                const active = queueStageFilter === stageFilter;
                return (
                  <button key={stageFilter} aria-pressed={active} onClick={() => setQueueStageFilter(stageFilter)} style={{ padding: '6px 10px', borderRadius: 999, border: '1px solid var(--line)', background: active ? 'rgba(249,115,22,0.2)' : 'transparent', color: active ? 'var(--warning)' : 'var(--text)', fontWeight: 600 }}>
                    Stage: {stageFilter}{queueLoaded ? ` (${queueStageCounts[stageFilter]})` : ''}
                  </button>
                );
              })}
            </div>
          </details>

          {queueError ? <p role="alert" style={{ color: 'var(--danger)' }}>{queueError}</p> : null}

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
                {loadingQueue ? 'Loading generation jobs…' : queueError ? 'Queue results are unavailable. Retry the request.' : queueLoaded ? 'No jobs match the selected filters.' : 'The generation queue has not loaded.'}
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
              <h2 style={{ marginTop: 0, marginBottom: 6 }}>Recent generations</h2>
              <p style={{ color: 'var(--muted)', margin: 0 }}>Content records currently returned for this workspace.</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--muted)' }}>{libraryError ? 'Count unavailable' : libraryLoaded ? `${library.length} items` : loadingLibrary ? 'Loading…' : 'Count unavailable'}</span>
              <button type="button" onClick={() => void loadLibrary()} disabled={loadingLibrary || !hasWorkspace} style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'transparent', color: 'var(--text)' }}>
                {loadingLibrary ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>
          </div>
          {libraryError ? <p role="alert" style={{ color: 'var(--danger)' }}>{libraryError}</p> : null}
          {libraryItemError ? <p role="alert" style={{ color: 'var(--danger)' }}>{libraryItemError}</p> : null}
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
                  key={item.generationId}
                  style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 14 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <strong>{item.headline}</strong>
                    <span style={{ color: 'var(--muted)' }}>{item.channel}</span>
                  </div>
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
                    <span>Topic: {item.topic}</span>
                    <span>{item.createdAt ? new Date(item.createdAt).toLocaleString() : 'Date not reported'}</span>
                  </div>
                  <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                    <button type="button" onClick={() => void loadLibraryItem(item)} disabled={loadingLibraryItemId !== null} style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'transparent', color: 'var(--text)', textAlign: 'left' }}>
                      {loadingLibraryItemId === item.generationId ? 'Loading saved content…' : 'View saved content'}
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <div style={{ color: 'var(--muted)' }}>
                {loadingLibrary ? 'Loading workspace content…' : libraryError ? 'Saved content is unavailable. Retry the request.' : libraryLoaded ? 'No content records were returned for this workspace.' : 'Content records have not loaded.'}
              </div>
            )}
          </div>
          {latest && (
            <div style={{ marginTop: 16, color: 'var(--muted)' }}>
              Latest returned record: {latest.headline}{latest.createdAt ? ` · ${new Date(latest.createdAt).toLocaleString()}` : ''}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
