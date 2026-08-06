'use client';

/**
 * MediaUploader — Sandboxed Media Processing Pipeline (NEW)
 * ----------------------------------------------------------
 * Implements the client-side flow from the Sandboxed Media SaaS Architecture doc:
 *
 *  1. User picks a file
 *  2. First 16 bytes are read and sent to /media/validate-file (magic-byte check)
 *  3. /storage/presign is called to get a presigned upload URL
 *  4. File is uploaded DIRECTLY from browser to storage (API never sees bytes — Rule 1)
 *  5. /media/jobs is called to queue the processing job (metadata only)
 *  6. SSE stream from /media/jobs/{id}/stream provides real-time progress
 *  7. On completion, /media/jobs/{id}/output-url is called for a signed CDN URL
 */

import { useCallback, useRef, useState, type ChangeEvent } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

type JobStatus =
  | 'idle'
  | 'validating'
  | 'presigning'
  | 'uploading'
  | 'queued'
  | 'processing'
  | 'complete'
  | 'failed'
  | 'cancelled';

type MediaJob = {
  id: number;
  status: string;
  progress_pct: number;
  storage_key: string;
  media_type: string;
  output_key: string | null;
  error: string | null;
  created_at: string;
};

type UploaderState = {
  phase: JobStatus;
  progress: number; // 0–100
  job: MediaJob | null;
  outputUrl: string | null;
  errorMessage: string | null;
  fileName: string | null;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const FASTAPI_PROXY_URL = '/api/fastapi';
// Falls back to a dev tenant when NEXT_PUBLIC_DEFAULT_TENANT_ID is unset so the
// app runs locally without crashing.
const TENANT_ID = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || 'default').trim();

// Supported MIME types with their input-accept strings
const SUPPORTED_MEDIA: Record<string, string> = {
  'image/jpeg': 'image',
  'image/png': 'image',
  'image/gif': 'image',
  'image/webp': 'image',
  'video/mp4': 'video',
  'video/webm': 'video',
  'audio/mpeg': 'audio',
  'audio/wav': 'audio',
  'audio/ogg': 'audio',
  'application/pdf': 'document',
};

const ACCEPT_STRING = Object.keys(SUPPORTED_MEDIA).join(',');

// Max file size per media type (bytes) — enforced client-side before presigning
const MAX_FILE_SIZES: Record<string, number> = {
  image: 25 * 1024 * 1024,     // 25 MB — images
  video: 500 * 1024 * 1024,    // 500 MB — video
  audio: 100 * 1024 * 1024,    // 100 MB — audio
  document: 50 * 1024 * 1024,  // 50 MB — documents
};

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Tenant-Id': TENANT_ID,
  };
}

async function readFirstBytesAsBase64(file: File, count = 16): Promise<string> {
  const slice = file.slice(0, count);
  const buf = await slice.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let binary = '';
  for (const b of bytes) binary += String.fromCodePoint(b);
  return btoa(binary);
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${FASTAPI_PROXY_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error((data?.detail as string) || `Request failed: ${res.status}`);
  }
  return data as T;
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${FASTAPI_PROXY_URL}${path}`, {
    method: 'GET',
    headers: authHeaders(),
    cache: 'no-store',
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error((data?.detail as string) || `Request failed: ${res.status}`);
  }
  return data as T;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function MediaUploader() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploaderState>({
    phase: 'idle',
    progress: 0,
    job: null,
    outputUrl: null,
    errorMessage: null,
    fileName: null,
  });
  const [showDlq, setShowDlq] = useState(false);
  const [dlqItems, setDlqItems] = useState<unknown[]>([]);

  const setPhase = useCallback((phase: JobStatus, extra?: Partial<UploaderState>) => {
    setState((prev) => ({ ...prev, phase, ...extra }));
  }, []);

  const handleError = useCallback((message: string) => {
    setState((prev) => ({ ...prev, phase: 'failed', errorMessage: message }));
  }, []);

  // ── Main upload pipeline ──────────────────────────────────────────────────

  const handleFileChange = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setState({
        phase: 'validating',
        progress: 0,
        job: null,
        outputUrl: null,
        errorMessage: null,
        fileName: file.name,
      });

      try {
        // ── Step 1: Detect MIME from browser File object ──────────────────────
        const mime = file.type || 'application/octet-stream';
        const mediaType = SUPPORTED_MEDIA[mime];

        if (!mediaType) {
          throw new Error(`Unsupported file type: ${mime}. Supported: ${Object.keys(SUPPORTED_MEDIA).join(', ')}`);
        }

        // ── Client-side file size enforcement ────────────────────────────────
        const maxSize = MAX_FILE_SIZES[mediaType] ?? 50 * 1024 * 1024;
        if (file.size > maxSize) {
          throw new Error(
            `File too large: ${formatBytes(file.size)}. Max for ${mediaType}: ${formatBytes(maxSize)}`,
          );
        }

        // ── Step 2: Magic-byte validation (Rule 2 — validate before upload) ──
        const firstBytesB64 = await readFirstBytesAsBase64(file, 16);
        const validationResult = await apiPost<{ validation_token: string; mime_type: string }>(
          '/media/validate-file',
          { first_bytes_b64: firstBytesB64, expected_mime: mime }
        );
        const { validation_token: validationToken } = validationResult;

        // ── Step 3: Request presigned upload URL (Rule 1 — direct upload) ────
        setPhase('presigning', { progress: 15 });
        const storageKey = `raw-input/${TENANT_ID}/${Date.now()}-${file.name.replaceAll(/[^a-zA-Z0-9._-]/g, '_')}`;
        const presignResult = await apiPost<{ result: { presigned_url: string | null } }>('/storage/presign', {
          bucket: 'raw-input',
          object_key: storageKey,
          method: 'PUT',
          expires_seconds: 900,
        });

        const presignedUrl = presignResult.result?.presigned_url;

        // ── Step 4: Upload directly to storage (API never sees bytes) ─────────
        setPhase('uploading', { progress: 25 });

        if (presignedUrl) {
          // Real presigned upload — browser sends bytes directly to MinIO/S3
          const uploadRes = await fetch(presignedUrl, {
            method: 'PUT',
            body: file,
            headers: { 'Content-Type': mime },
          });
          if (!uploadRes.ok) {
            throw new Error(`Storage upload failed: ${uploadRes.status}`);
          }
        }
        // If no presigned URL (dev/memory-fallback mode), skip direct upload and
        // proceed with job creation using the storage key as metadata reference.

        // ── Step 5: Queue processing job (metadata only, not bytes) ──────────
        setPhase('queued', { progress: 40 });
        const jobResult = await apiPost<{ job: MediaJob }>('/media/jobs', {
          storage_key: storageKey,
          media_type: mediaType,
          output_bucket: 'processed-output',
          processing_options: {},
          validation_token: validationToken,
        });
        const job = jobResult.job;
        setState((prev) => ({ ...prev, job, phase: 'queued', progress: 45 }));

        // ── Step 6: SSE stream for real-time progress ─────────────────────────
        const streamUrl = new URL(`${FASTAPI_PROXY_URL}/media/jobs/${job.id}/stream`, globalThis.location.origin);
        streamUrl.searchParams.set('tenant_id', TENANT_ID);

        const eventSource = new EventSource(streamUrl);

        eventSource.addEventListener('job.snapshot', (e: MessageEvent<string>) => {
          try {
            const updated = JSON.parse(e.data) as MediaJob;
            setState((prev) => ({
              ...prev,
              job: updated,
              phase: (updated.status as JobStatus) || prev.phase,
              progress: updated.progress_pct ?? prev.progress,
            }));
          } catch {
            /* ignore parse errors */
          }
        });

        eventSource.addEventListener('job.updated', (e: MessageEvent<string>) => {
          try {
            const updated = JSON.parse(e.data) as MediaJob & { _message?: string };
            const { _message: _, ...clean } = updated;
            setState((prev) => ({
              ...prev,
              job: clean,
              phase: (clean.status as JobStatus) || prev.phase,
              progress: clean.progress_pct ?? prev.progress,
            }));

            if (clean.status === 'complete') {
              eventSource.close();
              // Fetch signed output URL
              void fetchOutputUrl(job.id);
            } else if (clean.status === 'failed' || clean.status === 'cancelled') {
              eventSource.close();
            }
          } catch {
            /* ignore */
          }
        });

        eventSource.onerror = () => {
          eventSource.close();
        };
      } catch (err) {
        handleError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
      } finally {
        // Reset file input so the same file can be re-selected after failure
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [setPhase, handleError]
  );

  // ── Fetch signed output URL after completion ──────────────────────────────

  async function fetchOutputUrl(jobId: number) {
    try {
      const result = await apiPost<{ signed_url: string; expires_at: number }>(`/media/jobs/${jobId}/output-url`, {
        expires_seconds: 900,
      });
      setState((prev) => ({
        ...prev,
        outputUrl: result.signed_url,
        phase: 'complete',
      }));
    } catch {
      // Output URL failure is non-fatal — job is still complete
    }
  }

  // ── Cancel job ────────────────────────────────────────────────────────────

  async function cancelJob() {
    if (!state.job) return;
    try {
      await fetch(`${FASTAPI_PROXY_URL}/media/jobs/${state.job.id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setState((prev) => ({
        ...prev,
        phase: 'cancelled',
        job: prev.job ? { ...prev.job, status: 'cancelled' } : null,
      }));
    } catch {
      /* ignore */
    }
  }

  // ── Retry failed job ──────────────────────────────────────────────────────

  async function retryJob() {
    if (!state.job) return;
    try {
      const result = await apiPost<{ job: MediaJob }>(`/media/jobs/${state.job.id}/retry`, {});
      setState((prev) => ({
        ...prev,
        job: result.job,
        phase: 'queued',
        progress: 0,
        errorMessage: null,
        outputUrl: null,
      }));
    } catch (err) {
      handleError(err instanceof Error ? err.message : 'Retry failed.');
    }
  }

  // ── Load DLQ ─────────────────────────────────────────────────────────────

  async function loadDlq() {
    try {
      const result = await apiGet<{ dlq: unknown[] }>('/media/jobs/dlq');
      setDlqItems(result.dlq);
      setShowDlq(true);
    } catch {
      /* ignore */
    }
  }

  // ── Reset ─────────────────────────────────────────────────────────────────

  function resetUploader() {
    setState({ phase: 'idle', progress: 0, job: null, outputUrl: null, errorMessage: null, fileName: null });
    setShowDlq(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const { phase, progress, job, outputUrl, errorMessage, fileName } = state;
  const isActive = phase !== 'idle';
  const isTerminal = phase === 'complete' || phase === 'failed' || phase === 'cancelled';
  let progressBarColor = '#3b82f6';
  if (phase === 'failed') {
    progressBarColor = '#ef4444';
  } else if (phase === 'complete') {
    progressBarColor = '#10b981';
  }

  const phaseLabel: Record<JobStatus, string> = {
    idle: 'Select a file to begin',
    validating: 'Validating file type (magic-byte check)…',
    presigning: 'Requesting secure upload URL…',
    uploading: 'Uploading directly to storage…',
    queued: 'Job queued — awaiting sandbox…',
    processing: 'Sandbox processing in progress…',
    complete: 'Processing complete',
    failed: 'Processing failed',
    cancelled: 'Job cancelled',
  };

  return (
    <section className="media-uploader-shell">
      <div className="media-uploader-card">
        <div className="media-uploader-header">
          <h3>Sandboxed Media Processor</h3>
          <p className="muted">Files are uploaded directly to storage — this server never reads your bytes.</p>
        </div>

        {/* Drop zone / file picker */}
        <label
          className={`media-drop-zone${isActive && !isTerminal ? ' active' : ''}`}
          htmlFor="mediaFileInput"
          onDragOver={(e) => {
            e.preventDefault();
          }}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file && fileInputRef.current) {
              const dt = new DataTransfer();
              dt.items.add(file);
              fileInputRef.current.files = dt.files;
              void handleFileChange({ target: fileInputRef.current } as ChangeEvent<HTMLInputElement>);
            }
          }}
        >
          <input
            id="mediaFileInput"
            ref={fileInputRef}
            type="file"
            className="media-file-input"
            onChange={handleFileChange}
            disabled={isActive && !isTerminal}
            aria-label="Upload media file"
          />
          <div className="media-drop-label">
            {fileName ? (
              <span>{fileName}</span>
            ) : (
              <>
                <span className="media-drop-icon">+</span>
                <span>Drop a file or click to browse</span>
                <span className="muted" style={{ fontSize: '12px' }}>
                  JPEG, PNG, GIF, WebP, MP4, WebM, MP3, WAV, OGG, PDF
                </span>
              </>
            )}
          </div>
        </label>

        {/* Status bar */}
        {isActive && (
          <div className="media-status">
            <div className="media-status-row">
              <span className={`media-status-label media-status-${phase}`}>{phaseLabel[phase]}</span>
              <span className="muted">{progress}%</span>
            </div>
            <div
              className="media-progress-track"
              // ENHANCED: keep progress UI visible/stable even if external class styles are missing.
              style={{
                width: '100%',
                minHeight: '8px',
                background: 'rgba(148, 163, 184, 0.24)',
                borderRadius: '999px',
                overflow: 'hidden',
              }}
            >
              <div
                className={`media-progress-bar${phase === 'complete' ? ' done' : ''}${phase === 'failed' ? ' error' : ''}`}
                // ENHANCED: explicit height/color prevents zero-height hidden bars in E2E runs.
                style={{
                  width: `${progress}%`,
                  minHeight: '8px',
                  background: progressBarColor,
                  transition: 'width 120ms ease-out',
                }}
              />
            </div>

            {errorMessage && <p className="media-error">{errorMessage}</p>}

            {phase === 'complete' && outputUrl && (
              <div className="media-output">
                <span className="media-output-label">Signed output URL (expires 15 min):</span>
                <a href={outputUrl} target="_blank" rel="noopener noreferrer" className="media-output-link">
                  View processed file
                </a>
              </div>
            )}

            {job && (
              <div className="media-job-meta">
                <span>Job #{job.id}</span>
                <span className={`media-job-status-chip status-${job.status ?? 'unknown'}`}>{job.status}</span>
                {job.media_type && <span className="muted">{job.media_type}</span>}
              </div>
            )}

            {/* Action buttons */}
            <div className="media-actions">
              {(phase === 'queued' || phase === 'processing') && (
                <button type="button" className="media-btn media-btn-cancel" onClick={cancelJob}>
                  Cancel
                </button>
              )}
              {phase === 'failed' && (
                <button type="button" className="media-btn media-btn-retry" onClick={retryJob}>
                  Retry
                </button>
              )}
              {isTerminal && (
                <button type="button" className="media-btn media-btn-reset" onClick={resetUploader}>
                  Upload another
                </button>
              )}
            </div>
          </div>
        )}

        {/* DLQ inspector */}
        <div className="media-dlq-row">
          <button type="button" className="media-btn media-btn-ghost" onClick={loadDlq}>
            View failed jobs (DLQ)
          </button>
        </div>
        {showDlq && (
          <div className="media-dlq-panel">
            <div className="media-dlq-header">
              <strong>Dead-Letter Queue</strong>
              <button type="button" className="media-btn-close" onClick={() => setShowDlq(false)}>
                ×
              </button>
            </div>
            {dlqItems.length === 0 ? (
              <p className="muted">No failed jobs in DLQ.</p>
            ) : (
              <ul className="media-dlq-list">
                {dlqItems.map((item, i) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <li key={i} className="media-dlq-item">
                    <pre>{JSON.stringify(item, null, 2)}</pre>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
