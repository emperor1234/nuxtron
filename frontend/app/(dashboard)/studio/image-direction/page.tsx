'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type PhotoshootStyle = {
  id: string;
  name: string;
  description: string;
  example_prompt: string;
  best_for: string[];
};

type PhotoshootJob = {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_pct?: number;
  output_images?: { url: string; resolution: string; slot: number }[];
  platform_variants?: { platform: string; aspect_ratio: string; url: string }[];
  product_name?: string;
  style?: string;
};

type PhotoshootStylesResponse = {
  styles: PhotoshootStyle[];
};

type PhotoshootJobResponse = {
  job: PhotoshootJob;
};

const PLATFORMS = ['instagram', 'facebook', 'amazon', 'shopify', 'pinterest', 'linkedin'];
const NUM_OUTPUT_OPTIONS = [1, 2, 4, 6, 8];

const STATUS = {
  queued: { bg: '#eef0f4', color: 'var(--brand)', label: 'In Queue' },
  processing: { bg: '#fef3c7', color: '#F59E0B', label: 'Generating…' },
  completed: { bg: '#dcfce722', color: '#22c55e', label: 'Ready' },
  failed: { bg: '#fee2e222', color: '#EF4444', label: 'Failed' },
};

export default function ProductPhotoshootPage() {
  const [styles, setStyles] = useState<PhotoshootStyle[]>([]);
  const [jobs, setJobs] = useState<PhotoshootJob[]>([]);
  const [loadingStyles, setLoadingStyles] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'gallery'>('create');

  // Form
  const [productImageUrl, setProductImageUrl] = useState('');
  const [productName, setProductName] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('');
  const [numOutputs, setNumOutputs] = useState(4);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['instagram']);
  const [customPrompt, setCustomPrompt] = useState('');
  const [removeBg, setRemoveBg] = useState(true);
  const [addShadows, setAddShadows] = useState(true);

  useEffect(() => { loadStyles(); }, []);

  useEffect(() => {
    if (!pollingJobId) return;
    const iv = setInterval(async () => {
      try {
        const data = await apiGet<PhotoshootJobResponse>(`/ai/social-studio/video-job/${pollingJobId}`, DEFAULT_TENANT_ID);
        const job: PhotoshootJob = data.job;
        setJobs((prev) => prev.map((j) => (j.id === pollingJobId ? job : j)));
        if (job.status === 'completed' || job.status === 'failed') {
          setPollingJobId(null);
          setSuccessMsg(job.status === 'completed' ? `✅ ${numOutputs} images ready!` : '❌ Generation failed.');
          setTimeout(() => setSuccessMsg(null), 6000);
        }
      } catch { /* keep polling */ }
    }, 3000);
    return () => clearInterval(iv);
  }, [pollingJobId, numOutputs]);

  async function loadStyles() {
    setLoadingStyles(true);
    try {
      const data = await apiGet<PhotoshootStylesResponse>('/ai/social-studio/photoshoot-styles', DEFAULT_TENANT_ID);
      setStyles(data.styles ?? []);
      if (data.styles?.length > 0) setSelectedStyle(data.styles[0].id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoadingStyles(false); }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!productName.trim()) { setError('Product name is required.'); return; }
    setGenerating(true); setError(null);
    try {
      const data = await apiSend<PhotoshootJobResponse>('/ai/social-studio/product-photoshoot', 'POST', {
        product_image_url: productImageUrl || undefined,
        product_name: productName,
        style: selectedStyle,
        num_outputs: numOutputs,
        platforms: selectedPlatforms,
        custom_prompt: customPrompt || undefined,
        remove_background: removeBg,
        add_shadows: addShadows,
      }, DEFAULT_TENANT_ID);
      setJobs((prev) => [data.job, ...prev]);
      setPollingJobId(data.job.id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setGenerating(false); }
  }

  const activeStyle = styles.find((s) => s.id === selectedStyle);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>📸 AI Product Photoshoot</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>STABILITY AI · DALL-E 3 · FAL.AI</span>
        </div>
        <Link href="/studio/image-studio" style={{ background: 'var(--card)', color: 'var(--text)', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Image Editor →</Link>
      </div>

      {/* Stats bar */}
      <div style={{ background: 'var(--card)', padding: '12px 32px', display: 'flex', gap: 32, borderBottom: '1px solid var(--line)' }}>
        {[{ label: 'Photo Styles', value: `${styles.length}` }, { label: 'Jobs Created', value: `${jobs.length}` }, { label: 'Platforms', value: `${PLATFORMS.length}` }, { label: 'Max Outputs', value: '8 images' }].map((s) => (
          <div key={s.label}><div style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>{s.value}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</div></div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ padding: '0 32px', borderBottom: '1px solid var(--line)', background: 'var(--card)', display: 'flex' }}>
        {(['create', 'gallery'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: 'none', border: 'none', color: activeTab === tab ? 'var(--brand)' : 'var(--muted)', padding: '14px 20px', cursor: 'pointer', fontSize: 14, fontWeight: activeTab === tab ? 600 : 400, borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent' }}>
            {{ create: '✨ Create Photoshoot', gallery: '🖼 My Photos' }[tab]}
          </button>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}
        {successMsg && <div style={{ background: '#dcfce733', border: '1px solid #22c55e', borderRadius: 8, padding: 12, marginBottom: 16, color: '#15803d' }}>{successMsg}</div>}

        {activeTab === 'create' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 24 }}>
            <form onSubmit={handleGenerate}>
              {/* Style picker */}
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 10, fontWeight: 600 }}>PHOTOSHOOT STYLE</label>
                {loadingStyles ? (
                  <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading styles…</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
                    {styles.map((s) => (
                      <button key={s.id} type="button" onClick={() => setSelectedStyle(s.id)} style={{ background: selectedStyle === s.id ? '#6366f133' : '#eef0f4', border: `2px solid ${selectedStyle === s.id ? '#6366f1' : '#e7e9ef'}`, borderRadius: 10, padding: 14, cursor: 'pointer', textAlign: 'left', color: 'var(--text)' }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: selectedStyle === s.id ? 'var(--brand)' : 'var(--text)', marginBottom: 4 }}>{s.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.4 }}>{s.description}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Product info */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PRODUCT NAME *</label>
                <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="e.g. GlowSkin Serum 30ml" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PRODUCT IMAGE URL (optional — AI generates without if blank)</label>
                <input value={productImageUrl} onChange={(e) => setProductImageUrl(e.target.value)} placeholder="https://example.com/product.png" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>CUSTOM PROMPT (optional)</label>
                <textarea value={customPrompt} onChange={(e) => setCustomPrompt(e.target.value)} placeholder={activeStyle?.example_prompt ?? 'Describe additional details for the scene…'} rows={3} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
              </div>

              {/* Platforms */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>OUTPUT PLATFORMS</label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {PLATFORMS.map((p) => (
                    <button key={p} type="button" onClick={() => setSelectedPlatforms((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p])} style={{ background: selectedPlatforms.includes(p) ? '#6366f133' : '#eef0f4', border: `1px solid ${selectedPlatforms.includes(p) ? '#6366f1' : '#e7e9ef'}`, color: selectedPlatforms.includes(p) ? 'var(--brand)' : 'var(--muted)', padding: '6px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 12, textTransform: 'capitalize' }}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Num outputs */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>NUMBER OF OUTPUTS</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {NUM_OUTPUT_OPTIONS.map((n) => (
                    <button key={n} type="button" onClick={() => setNumOutputs(n)} style={{ background: numOutputs === n ? '#6366f1' : '#eef0f4', color: numOutputs === n ? '#fff' : 'var(--text)', border: `1px solid ${numOutputs === n ? '#6366f1' : '#e7e9ef'}`, padding: '7px 18px', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
                {[{ id: 'bg', label: 'Remove background', checked: removeBg, onChange: setRemoveBg }, { id: 'shadow', label: 'Add natural shadows', checked: addShadows, onChange: setAddShadows }].map((tog) => (
                  <label key={tog.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, color: 'var(--text)' }}>
                    <input type="checkbox" checked={tog.checked} onChange={(e) => tog.onChange(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#6366f1' }} />
                    {tog.label}
                  </label>
                ))}
              </div>

              <button type="submit" disabled={generating} style={{ width: '100%', background: generating ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer' }}>
                {generating ? `⏳ Generating ${numOutputs} images…` : `📸 Generate ${numOutputs} Product Photos`}
              </button>

              {/* Active jobs */}
              {jobs.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Recent Jobs</div>
                  {jobs.slice(0, 3).map((job) => {
                    const s = STATUS[job.status] ?? STATUS.queued;
                    return (
                      <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 14, marginBottom: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{job.product_name} · {job.style} style</div>
                          <span style={{ background: s.bg, color: s.color, fontSize: 11, padding: '2px 10px', borderRadius: 12, fontWeight: 600 }}>{s.label}</span>
                        </div>
                        {job.status === 'processing' && <div style={{ height: 3, background: '#e7e9ef', borderRadius: 2 }}><div style={{ height: '100%', width: `${job.progress_pct ?? 40}%`, background: '#6366f1' }} /></div>}
                        {job.status === 'completed' && job.output_images && (
                          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                            {job.output_images.map((img) => (
                              <a key={img.slot} href={img.url} target="_blank" rel="noopener noreferrer" style={{ background: '#22c55e', color: '#fff', padding: '4px 10px', borderRadius: 6, fontSize: 11, textDecoration: 'none', fontWeight: 600 }}>
                                ⬇ Photo {img.slot + 1} ({img.resolution})
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </form>

            {/* Sidebar */}
            <div style={{ position: 'sticky', top: 24, alignSelf: 'start' }}>
              {activeStyle && (
                <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: 'var(--brand)', fontWeight: 600, marginBottom: 12 }}>SELECTED STYLE</div>
                  <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{activeStyle.name}</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 10, lineHeight: 1.5 }}>{activeStyle.description}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4, fontWeight: 600 }}>Best for:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {activeStyle.best_for.map((b) => (
                      <span key={b} style={{ background: '#e7e9ef', color: 'var(--text)', fontSize: 10, padding: '2px 8px', borderRadius: 10 }}>{b}</span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600, letterSpacing: 1 }}>AI PROVIDERS</div>
                {[{ name: 'Stability AI', env: 'STABILITY_API_KEY', tier: 'Primary' }, { name: 'fal.ai', env: 'FAL_API_KEY', tier: 'Fallback' }, { name: 'DALL-E 3', env: 'OPENAI_API_KEY', tier: 'Backup' }].map((v) => (
                  <div key={v.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div><div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{v.name}</div><div style={{ fontSize: 10, color: '#6366f1' }}>{v.env}</div></div>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{v.tier}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'gallery' && (
          <div>
            {jobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>📸</div>
                <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No photoshoots yet</div>
                <button onClick={() => setActiveTab('create')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>Create First Photoshoot</button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 20 }}>
                {jobs.map((job) => {
                  const s = STATUS[job.status] ?? STATUS.queued;
                  return (
                    <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 2, background: '#e7e9ef' }}>
                        {(job.output_images ?? Array.from({ length: 4 }, (_, i) => ({ slot: i, url: '', resolution: '' }))).slice(0, 4).map((img, i) => (
                          <div key={i} style={{ height: 100, background: img.url ? `url(${img.url}) center/cover` : '#e7e9ef', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {!img.url && <div style={{ fontSize: 20, color: '#e7e9ef' }}>📸</div>}
                          </div>
                        ))}
                      </div>
                      <div style={{ padding: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{job.product_name}</span>
                          <span style={{ background: s.bg, color: s.color, fontSize: 10, padding: '1px 8px', borderRadius: 10 }}>{s.label}</span>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>{job.style} · {job.output_images?.length ?? 0} images</div>
                        {job.status === 'completed' && job.output_images && (
                          <a href={job.output_images[0]?.url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', background: '#6366f1', color: '#fff', padding: '5px 0', borderRadius: 6, fontSize: 11, textDecoration: 'none', textAlign: 'center', fontWeight: 600 }}>
                            ⬇ Download All
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
