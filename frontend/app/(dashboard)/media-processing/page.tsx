'use client';

/**
 * Media Processing Page — Sandboxed Media SaaS Architecture
 * ==========================================================
 * Full end-to-end page wiring together:
 *   - MediaUploader component (presigned upload → magic-byte validation → queue → SSE progress)
 *   - Managed provider catalog (Cloudinary, Mux, Bunny.net, AssemblyAI, Deepgram, Adobe PDF)
 *   - Job history table with live polling
 *   - Sandbox config panel (security rules + isolation layers)
 *   - Architecture flow diagram
 *
 * Third-party vendors and what they do:
 *   • Cloudinary  — image/video transformation, resizing, format conversion (managed sandbox)
 *   • Mux         — video transcoding, adaptive bitrate streaming, player analytics
 *   • Bunny.net   — cost-effective image/video CDN and streaming
 *   • AssemblyAI  — audio transcription, speaker diarisation, sentiment analysis
 *   • Deepgram    — real-time and batch speech-to-text, low-latency voice apps
 *   • Adobe PDF   — enterprise document conversion, extraction, OCR, compression
 */

import { useEffect, useRef, useState } from 'react';
import MediaUploader from '@/app/media-uploader';

// ── Types ─────────────────────────────────────────────────────────────────────

type ProviderInfo = {
  id: string;
  name: string;
  media_types: string[];
  what_it_replaces: string;
  best_for: string;
  configured: boolean;
  status: string;
  supports_operations: string[];
  docs_url: string;
};

type JobRecord = {
  id: number;
  status: string;
  media_type: string;
  provider: string;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  storage_key: string;
};

type SandboxConfig = {
  execution_mode: string;
  available_executors: Record<string, boolean>;
  isolation_layers: Record<string, { name: string; technology: string; active: boolean; description: string }>;
  security_rules: Record<string, { name: string; enforced: boolean; description: string }>;
  max_concurrent_jobs_per_tenant: number;
  raw_input_ttl_hours: number;
};

type Stats = {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  dlq_depth: number;
  by_status: Record<string, number>;
  by_media_type: Record<string, number>;
  by_provider: Record<string, number>;
  concurrent_limit: number;
  utilization_pct: number;
};

type DispatchState = {
  loading: boolean;
  error: string | null;
  result: string | number | boolean | Record<string, unknown> | null;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const FASTAPI = '/api/fastapi';
const TENANT_ID = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || 'default-tenant').trim();
const HEADERS = { 'Content-Type': 'application/json', 'X-Tenant-Id': TENANT_ID };
const POLL_INTERVAL_MS = 5000;

const PROVIDER_ICONS: Record<string, string> = {
  cloudinary: '🖼',
  mux: '🎬',
  bunny: '🐰',
  assemblyai: '🎙',
  deepgram: '🔊',
  adobe_pdf: '📄',
};

const PROVIDER_COLORS: Record<string, string> = {
  cloudinary: '#3448c5',
  mux: '#fb2491',
  bunny: '#fc7a1e',
  assemblyai: '#1f2aa4',
  deepgram: '#201cff',
  adobe_pdf: '#fa0f00',
};

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${FASTAPI}${path}`, {
    headers: HEADERS,
    cache: 'no-store',
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error((data?.detail as string) || `HTTP ${res.status}`);
  return data as T;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SecurityRuleBadge({ enforced }: Readonly<{ enforced: boolean }>) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '999px',
        fontSize: '11px',
        fontWeight: 600,
        background: enforced ? '#d1fae5' : '#fee2e2',
        color: enforced ? '#065f46' : '#991b1b',
      }}
    >
      {enforced ? '✓ enforced' : '✗ not enforced'}
    </span>
  );
}

function ProviderCard({
  provider,
  selected,
  onSelect,
}: Readonly<{
  provider: ProviderInfo;
  selected: boolean;
  onSelect: (id: string) => void;
}>) {
  const color = PROVIDER_COLORS[provider.id] ?? '#6366f1';
  return (
    <button
      type="button"
      onClick={() => onSelect(provider.id)}
      style={{
        border: selected ? `2px solid ${color}` : '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '16px',
        background: selected ? `${color}10` : '#fff',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'border-color 120ms',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '24px' }}>{PROVIDER_ICONS[provider.id] ?? '🔧'}</span>
        <strong style={{ fontSize: '15px', color: 'var(--text)' }}>{provider.name}</strong>
        {!provider.configured && (
          <span
            style={{
              marginLeft: 'auto',
              fontSize: '11px',
              background: '#fef3c7',
              color: '#92400e',
              padding: '2px 6px',
              borderRadius: '4px',
            }}
          >
            needs creds
          </span>
        )}
        {provider.configured && (
          <span
            style={{
              marginLeft: 'auto',
              fontSize: '11px',
              background: '#d1fae5',
              color: '#065f46',
              padding: '2px 6px',
              borderRadius: '4px',
            }}
          >
            ready
          </span>
        )}
      </div>
      <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>
        <strong>Media:</strong> {provider.media_types.join(', ')}
      </div>
      <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>
        <strong>Best for:</strong> {provider.best_for}
      </div>
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Replaces: {provider.what_it_replaces}</div>
    </button>
  );
}

function StatsBar({ stats }: Readonly<{ stats: Stats }>) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))',
        gap: '12px',
        marginBottom: '24px',
      }}
    >
      {[
        { label: 'Total Jobs', value: stats.total_jobs, color: '#6366f1' },
        { label: 'Active', value: stats.active_jobs, color: '#f59e0b' },
        { label: 'Completed', value: stats.completed_jobs, color: '#10b981' },
        { label: 'Failed', value: stats.failed_jobs, color: '#ef4444' },
        { label: 'DLQ Depth', value: stats.dlq_depth, color: '#f97316' },
        {
          label: `Concurrency ${stats.active_jobs}/${stats.concurrent_limit}`,
          value: `${stats.utilization_pct}%`,
          color: stats.utilization_pct > 80 ? '#ef4444' : '#10b981',
        },
      ].map((item) => (
        <div
          key={item.label}
          style={{
            background: '#f8fafc',
            borderRadius: '10px',
            padding: '14px',
            borderLeft: `4px solid ${item.color}`,
          }}
        >
          <div style={{ fontSize: '22px', fontWeight: 700, color: item.color }}>{item.value}</div>
          <div style={{ fontSize: '12px', color: '#64748b' }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

function JobsTable({ jobs }: Readonly<{ jobs: JobRecord[] }>) {
  if (jobs.length === 0) {
    return <p style={{ color: '#94a3b8', textAlign: 'center', padding: '24px' }}>No jobs yet. Upload a file to get started.</p>;
  }

  const statusColors: Record<string, string> = {
    complete: '#10b981',
    processing: '#6366f1',
    queued: '#f59e0b',
    failed: '#ef4444',
    cancelled: '#94a3b8',
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
            {['ID', 'Type', 'Provider', 'Status', 'Progress', 'Created', 'Error'].map((h) => (
              <th key={h} style={{ padding: '8px 12px', color: '#64748b', fontWeight: 600 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '8px 12px', color: '#475569', fontFamily: 'monospace' }}>#{job.id}</td>
              <td style={{ padding: '8px 12px' }}>{job.media_type}</td>
              <td style={{ padding: '8px 12px' }}>
                {PROVIDER_ICONS[job.provider] ?? ''} {job.provider}
              </td>
              <td style={{ padding: '8px 12px' }}>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '999px',
                    fontSize: '11px',
                    fontWeight: 600,
                    background: `${statusColors[job.status] ?? '#94a3b8'}20`,
                    color: statusColors[job.status] ?? '#64748b',
                  }}
                >
                  {job.status}
                </span>
              </td>
              <td style={{ padding: '8px 12px' }}>
                <div
                  style={{
                    height: '6px',
                    width: '80px',
                    background: '#e2e8f0',
                    borderRadius: '999px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${job.progress_pct}%`,
                      background: statusColors[job.status] ?? '#6366f1',
                    }}
                  />
                </div>
              </td>
              <td style={{ padding: '8px 12px', color: '#94a3b8', fontSize: '11px' }}>
                {new Date(job.created_at).toLocaleTimeString()}
              </td>
              <td
                style={{
                  padding: '8px 12px',
                  color: '#ef4444',
                  fontSize: '11px',
                  maxWidth: '180px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={job.error ?? ''}
              >
                {job.error ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MediaProcessingPage() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [sandboxConfig, setSandboxConfig] = useState<SandboxConfig | null>(null);
  const [activeTab, setActiveTab] = useState<'upload' | 'dispatch' | 'jobs' | 'config'>('upload');
  const [dispatchState, setDispatchState] = useState<DispatchState>({ loading: false, error: null, result: null });
  const [dispatchForm, setDispatchForm] = useState({ storage_key: '', operation: 'auto', source_url: '' });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load providers, config, and stats on mount
  useEffect(() => {
    void apiFetch<{ providers: ProviderInfo[] }>('/media/providers').then((d) => setProviders(d.providers));
    void apiFetch<{ sandbox: SandboxConfig }>('/media/sandbox/config').then((d) => setSandboxConfig(d.sandbox));
    void loadJobsAndStats();

    pollRef.current = setInterval(() => {
      void loadJobsAndStats();
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function loadJobsAndStats() {
    try {
      const [jobsData, statsData] = await Promise.all([
        apiFetch<{ jobs: JobRecord[] }>('/media/jobs'),
        apiFetch<{ stats: Stats }>('/media/jobs/stats'),
      ]);
      setJobs(jobsData.jobs);
      setStats(statsData.stats);
    } catch {
      // silent — background poll
    }
  }

  async function handleProviderDispatch() {
    if (!selectedProvider || !dispatchForm.storage_key) return;
    setDispatchState({ loading: true, error: null, result: null });

    const provider = providers.find((p) => p.id === selectedProvider);
    const mediaType = provider?.media_types[0] ?? 'image';

    try {
      const result = await apiFetch<Record<string, unknown>>('/media/sandbox/dispatch', {
        method: 'POST',
        body: JSON.stringify({
          storage_key: dispatchForm.storage_key,
          media_type: mediaType,
          provider: selectedProvider,
          operation: dispatchForm.operation,
          operation_params: {},
          source_url: dispatchForm.source_url || null,
        }),
      });
      setDispatchState({ loading: false, error: null, result });
      void loadJobsAndStats();
    } catch (err) {
      setDispatchState({
        loading: false,
        error: err instanceof Error ? err.message : 'Dispatch failed.',
        result: null,
      });
    }
  }

  const tabStyle = (tab: string) => ({
    padding: '8px 20px',
    border: 'none',
    borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent',
    background: 'none',
    cursor: 'pointer',
    fontWeight: activeTab === tab ? 700 : 400,
    color: activeTab === tab ? '#6366f1' : '#64748b',
    fontSize: '14px',
    transition: 'all 120ms',
  });

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>

      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text)', marginBottom: '8px' }}>
          Sandboxed Media Processing
        </h1>
        <p style={{ color: '#64748b', maxWidth: '680px' }}>
          Production-grade media pipeline: files travel directly from your browser to storage via
          presigned URLs — this server never reads file bytes. Every job runs in an isolated,
          ephemeral sandbox (Firecracker / gVisor / Lambda) and is destroyed on completion.
        </p>
      </div>

      {/* Architecture flow */}
      <div
        style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '28px',
          fontFamily: 'monospace',
          fontSize: '12px',
          color: '#475569',
          overflowX: 'auto',
        }}
      >
        <strong style={{ fontFamily: 'sans-serif', fontSize: '13px', color: 'var(--text)' }}>Data flow (unidirectional — zero-trust):</strong>
        <pre style={{ margin: '8px 0 0', lineHeight: 1.6 }}>
{`Browser → [magic-byte validate] → /storage/presign → S3/R2/MinIO (direct PUT)
       → [POST /media/jobs | POST /media/sandbox/dispatch]
       → Job Queue (BullMQ+Redis or AWS SQS)
       → Sandbox Executor (AWS Lambda / Cloud Run / Firecracker)
          ↳ Network: DISABLED  |  Filesystem: ephemeral  |  Destroyed on completion
       → processed-output bucket → CDN (time-limited signed URL)
       → SSE /media/jobs/{id}/stream  →  Browser progress update`}
        </pre>
      </div>

      {/* Stats bar */}
      {stats && <StatsBar stats={stats} />}

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #e2e8f0', marginBottom: '24px', display: 'flex', gap: '4px' }}>
        {(
          [
            { id: 'upload', label: '⬆ Upload & Process' },
            { id: 'dispatch', label: '🚀 Provider Dispatch' },
            { id: 'jobs', label: `📋 Job History (${jobs.length})` },
            { id: 'config', label: '🔒 Security Config' },
          ] as const
        ).map((t) => (
          <button key={t.id} type="button" style={tabStyle(t.id)} onClick={() => setActiveTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Upload & Process ── */}
      {activeTab === 'upload' && (
        <div>
          <MediaUploader />
          <div
            style={{
              marginTop: '24px',
              padding: '16px',
              background: '#f0fdf4',
              borderRadius: '10px',
              border: '1px solid #bbf7d0',
              fontSize: '13px',
              color: '#166534',
            }}
          >
            <strong>Security rules active:</strong> Rule 1 (zero-trust ingress) · Rule 2 (magic-byte
            validation) · Rule 5 (tenant isolation) · Rule 6 (signed output URLs)
          </div>
        </div>
      )}

      {/* ── Tab: Provider Dispatch ── */}
      {activeTab === 'dispatch' && (
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: 'var(--text)' }}>
            Managed Provider Catalog
          </h2>
          <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
            Select a provider to dispatch a file directly to their managed sandbox (replaces the
            internal executor layer — same API contract, different executor).
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))',
              gap: '14px',
              marginBottom: '24px',
            }}
          >
            {providers.map((p) => (
              <ProviderCard
                key={p.id}
                provider={p}
                selected={selectedProvider === p.id}
                onSelect={setSelectedProvider}
              />
            ))}
          </div>

          {selectedProvider && (
            <div
              style={{
                background: '#f8fafc',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
                padding: '20px',
              }}
            >
              <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '14px', color: 'var(--text)' }}>
                Dispatch to {providers.find((p) => p.id === selectedProvider)?.name}
              </h3>
              <div style={{ display: 'grid', gap: '12px' }}>
                <label style={{ display: 'grid', gap: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Storage Key</span>
                  <input
                    type="text"
                    placeholder="raw-input/tenant/filename.mp4"
                    value={dispatchForm.storage_key}
                    onChange={(e) => setDispatchForm((f) => ({ ...f, storage_key: e.target.value }))}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                    }}
                  />
                </label>
                <label style={{ display: 'grid', gap: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Source URL (optional)</span>
                  <input
                    type="url"
                    placeholder="https://example.com/file.mp4"
                    value={dispatchForm.source_url}
                    onChange={(e) => setDispatchForm((f) => ({ ...f, source_url: e.target.value }))}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                    }}
                  />
                </label>
                <label style={{ display: 'grid', gap: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Operation</span>
                  <select
                    value={dispatchForm.operation}
                    onChange={(e) => setDispatchForm((f) => ({ ...f, operation: e.target.value }))}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                    }}
                  >
                    {(providers.find((p) => p.id === selectedProvider)?.supports_operations ?? ['auto']).map((op) => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={handleProviderDispatch}
                  disabled={dispatchState.loading || !dispatchForm.storage_key}
                  style={{
                    padding: '10px 20px',
                    background: dispatchState.loading ? '#94a3b8' : '#6366f1',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    fontWeight: 600,
                    cursor: dispatchState.loading ? 'wait' : 'pointer',
                    fontSize: '14px',
                  }}
                >
                  {dispatchState.loading ? 'Dispatching…' : 'Dispatch Job'}
                </button>

                {dispatchState.error && (
                  <p style={{ color: '#ef4444', fontSize: '13px' }}>{dispatchState.error}</p>
                )}
                {dispatchState.result !== null && dispatchState.result !== undefined && (
                  <pre
                    style={{
                      background: '#f6f7fa',
                      color: 'var(--text)',
                      border: '1px solid var(--line)',
                      padding: '12px',
                      borderRadius: '8px',
                      fontSize: '11px',
                      overflow: 'auto',
                      maxHeight: '200px',
                    }}
                  >
                    {JSON.stringify(dispatchState.result, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Job History ── */}
      {activeTab === 'jobs' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text)' }}>Job History</h2>
            <button
              type="button"
              onClick={loadJobsAndStats}
              style={{
                padding: '6px 14px',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                background: '#fff',
                cursor: 'pointer',
                fontSize: '13px',
                color: '#475569',
              }}
            >
              ↻ Refresh
            </button>
          </div>
          <JobsTable jobs={jobs} />
        </div>
      )}

      {/* ── Tab: Security Config ── */}
      {activeTab === 'config' && sandboxConfig && (
        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>
              Sandbox Execution Config
            </h2>
            <p style={{ fontSize: '13px', color: '#64748b' }}>
              Mode: <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>{sandboxConfig.execution_mode}</code>
              {' | '}Max concurrent jobs/tenant: <strong>{sandboxConfig.max_concurrent_jobs_per_tenant}</strong>
              {' | '}Raw-input TTL: <strong>{sandboxConfig.raw_input_ttl_hours}h</strong>
            </p>
          </div>

          {/* Three isolation layers */}
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '12px' }}>
              The Three Security Layers
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '12px' }}>
              {Object.entries(sandboxConfig.isolation_layers).map(([key, layer]) => (
                <div
                  key={key}
                  style={{
                    padding: '16px',
                    border: `1px solid ${layer.active ? '#bbf7d0' : '#e2e8f0'}`,
                    borderRadius: '10px',
                    background: layer.active ? '#f0fdf4' : '#f8fafc',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <strong style={{ fontSize: '13px', color: 'var(--text)' }}>{layer.name}</strong>
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '999px',
                        background: layer.active ? '#d1fae5' : '#f3f4f6',
                        color: layer.active ? '#065f46' : '#6b7280',
                        fontWeight: 600,
                      }}
                    >
                      {layer.active ? '● active' : '○ inactive'}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#6366f1', marginBottom: '6px', fontWeight: 500 }}>
                    {layer.technology}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>{layer.description}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Six security rules */}
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '12px' }}>
              The Six Security Rules
            </h3>
            <div style={{ display: 'grid', gap: '10px' }}>
              {Object.entries(sandboxConfig.security_rules).map(([key, rule]) => (
                <div
                  key={key}
                  style={{
                    padding: '14px 16px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '10px',
                    display: 'flex',
                    gap: '12px',
                    alignItems: 'flex-start',
                    background: '#fff',
                  }}
                >
                  <SecurityRuleBadge enforced={rule.enforced} />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>
                      {rule.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>{rule.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Executor availability */}
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '12px' }}>
              Available Executors
            </h3>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {Object.entries(sandboxConfig.available_executors).map(([exec, available]) => (
                <span
                  key={exec}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '999px',
                    fontSize: '12px',
                    fontWeight: 600,
                    background: available ? '#d1fae5' : '#f3f4f6',
                    color: available ? '#065f46' : '#9ca3af',
                    border: `1px solid ${available ? '#a7f3d0' : '#e5e7eb'}`,
                  }}
                >
                  {available ? '✓' : '○'} {exec.replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
