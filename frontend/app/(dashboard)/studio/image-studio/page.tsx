'use client';

import { ChangeEvent, useMemo, useState } from 'react';
import { apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type ImageEditOperation = 'select-subject' | 'sky-segment' | 'gen-fill' | 'upscale' | 'neural-filter' | 'harmonize';

type ImageEditResponse = {
  status: string;
  operation: string;
  image_url?: string;
  mask_url?: string;
  metadata?: Record<string, unknown>;
};

const OPERATIONS: Array<{ id: ImageEditOperation; label: string; help: string }> = [
  {
    id: 'select-subject',
    label: 'Select Subject',
    help: 'Build a subject mask you can reuse for fills and harmonization.',
  },
  { id: 'sky-segment', label: 'Sky Segment', help: 'Extract a sky mask for replacement, grading, or ad overlays.' },
  { id: 'gen-fill', label: 'Generative Fill', help: 'Fill masked regions with context-aware synthesis.' },
  { id: 'upscale', label: 'Upscale', help: 'Upscale and sharpen to high-resolution output.' },
  { id: 'neural-filter', label: 'Neural Filter', help: 'Apply cinematic, mono, vivid, glow, or clarity filters.' },
  { id: 'harmonize', label: 'Harmonize', help: 'Match subject tone with background for composited realism.' },
];

async function toDataUrl(file: File): Promise<string> {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

export default function ImageStudioPage() {
  const [tenantId] = useState(() => resolveSessionTenant() || 'tenant-demo');
  const [operation, setOperation] = useState<ImageEditOperation>('select-subject');
  const [imageData, setImageData] = useState('');
  const [maskData, setMaskData] = useState('');
  const [prompt, setPrompt] = useState('');
  const [filterName, setFilterName] = useState('clarity');
  const [upscaleFactor, setUpscaleFactor] = useState(2);
  const [resultImageUrl, setResultImageUrl] = useState('');
  const [resultMaskUrl, setResultMaskUrl] = useState('');
  const [metadata, setMetadata] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);

  const operationHelp = useMemo(() => OPERATIONS.find((item) => item.id === operation)?.help || '', [operation]);

  async function onImageSelected(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    setError('');
    const file = event.target.files?.[0];
    if (!file) return;
    setImageData(await toDataUrl(file));
  }

  async function onMaskSelected(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    setError('');
    const file = event.target.files?.[0];
    if (!file) return;
    setMaskData(await toDataUrl(file));
  }

  async function runOperation(): Promise<void> {
    setError('');
    setRunning(true);
    try {
      if (!imageData) {
        throw new Error('Upload a source image first.');
      }

      const payload: Record<string, unknown> = {
        image_data: imageData,
        prompt,
        filter_name: filterName,
        upscale_factor: upscaleFactor,
      };
      if (maskData) {
        payload.mask_data = maskData;
      }

      const response = (await apiPost(`/ai/image/${operation}`, payload, tenantId)) as ImageEditResponse;
      if (response.status !== 'success') {
        throw new Error('Image operation failed.');
      }

      setResultImageUrl(String(response.image_url || ''));
      setResultMaskUrl(String(response.mask_url || ''));
      setMetadata((response.metadata || {}) as Record<string, unknown>);
      if (response.mask_url) {
        setMaskData(String(response.mask_url));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Image operation failed');
    } finally {
      setRunning(false);
    }
  }

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 20px', display: 'grid', gap: 20 }}>
      <section style={{ display: 'grid', gap: 8 }}>
        <h1 style={{ margin: 0 }}>AI Image Studio</h1>
        <p style={{ margin: 0, color: 'var(--muted)' }}>
          Production image operations wired to FastAPI endpoints: subject selection, sky segmentation, generative fill,
          upscale, neural filters, and harmonization.
        </p>
      </section>

      <section
        style={{
          border: '1px solid var(--line)',
          borderRadius: 12,
          background: 'var(--panel)',
          padding: 16,
          display: 'grid',
          gap: 12,
        }}
      >
        <div style={{ display: 'grid', gap: 6 }}>
          <label htmlFor="tenant">Tenant ID</label>
          <input id="tenant" value={tenantId} readOnly />
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          <label htmlFor="source-image">Source image</label>
          <input id="source-image" type="file" accept="image/*" onChange={onImageSelected} />
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          <label htmlFor="mask-image">Mask image (required for generative fill; optional for harmonize)</label>
          <input id="mask-image" type="file" accept="image/*" onChange={onMaskSelected} />
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          <label htmlFor="op">Operation</label>
          <select
            id="op"
            value={operation}
            onChange={(event) => setOperation(event.target.value as ImageEditOperation)}
          >
            {OPERATIONS.map((item) => (
              <option value={item.id} key={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          <small style={{ color: 'var(--muted)' }}>{operationHelp}</small>
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          <label htmlFor="prompt">Prompt (used by generative fill)</label>
          <textarea
            id="prompt"
            rows={3}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe how masked regions should be generated"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>Neural filter</span>
            <input value={filterName} onChange={(event) => setFilterName(event.target.value)} placeholder="clarity" />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>Upscale factor</span>
            <input
              type="number"
              min={1}
              max={4}
              value={upscaleFactor}
              onChange={(event) =>
                setUpscaleFactor(Math.max(1, Math.min(4, Number.parseInt(event.target.value || '2', 10))))
              }
            />
          </label>
        </div>

        <button type="button" disabled={running} onClick={() => void runOperation()}>
          {running ? 'Running...' : 'Run image operation'}
        </button>

        {error ? <p style={{ margin: 0, color: '#ef4444' }}>{error}</p> : null}
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 16 }}>
        <article style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12, background: 'var(--panel)' }}>
          <h2 style={{ marginTop: 0, fontSize: 18 }}>Source</h2>
          {imageData ? (
            <img src={imageData} alt="Source" style={{ width: '100%', borderRadius: 8 }} />
          ) : (
            <p>No source image</p>
          )}
        </article>

        <article style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12, background: 'var(--panel)' }}>
          <h2 style={{ marginTop: 0, fontSize: 18 }}>Mask</h2>
          {resultMaskUrl || maskData ? (
            <img src={resultMaskUrl || maskData} alt="Mask" style={{ width: '100%', borderRadius: 8 }} />
          ) : (
            <p>No mask available</p>
          )}
        </article>

        <article style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12, background: 'var(--panel)' }}>
          <h2 style={{ marginTop: 0, fontSize: 18 }}>Result</h2>
          {resultImageUrl ? (
            <img src={resultImageUrl} alt="Result" style={{ width: '100%', borderRadius: 8 }} />
          ) : (
            <p>No result yet</p>
          )}
        </article>
      </section>

      <section style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12, background: 'var(--panel)' }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Metadata</h2>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(metadata, null, 2)}</pre>
      </section>
    </main>
  );
}
