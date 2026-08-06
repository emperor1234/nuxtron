'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

// ── Types ──────────────────────────────────────────────────────────────────
type ReelTemplate = {
  id: string;
  name: string;
  duration_s: number;
  structure: string[];
  best_for: string[];
};

type VideoJob = {
  id: string;
  type: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_pct?: number;
  video_url?: string | null;
  thumbnail_url?: string;
  captions_url?: string | null;
  duration_s?: number;
  aspect_ratio?: string;
  platform?: string;
  template?: ReelTemplate;
  script_segments?: { segment: string; duration_s: number; suggested_content: string }[];
  estimated_completion_s?: number;
  completed_at?: string;
};

type ResizePreset = {
  platform: string;
  format: string;
  width: number;
  height: number;
  aspect_ratio: string;
  resized_asset_url?: string;
};

type VideoJobResponse = {
  job: VideoJob;
};

type ReelTemplatesResponse = {
  templates: ReelTemplate[];
};

type AutoResizeResponse = {
  presets: ResizePreset[];
};

// ── Constants ──────────────────────────────────────────────────────────────
const PLATFORMS = [
  { id: 'instagram', label: 'Instagram Reels', icon: '📸' },
  { id: 'tiktok', label: 'TikTok', icon: '🎵' },
  { id: 'youtube', label: 'YouTube Shorts', icon: '▶️' },
  { id: 'facebook', label: 'Facebook Reels', icon: '👥' },
  { id: 'linkedin', label: 'LinkedIn Video', icon: '💼' },
];
const MUSIC_STYLES = ['upbeat', 'calm', 'dramatic', 'trending', 'cinematic', 'corporate'];
const CAPTION_STYLES = ['bold-subtitles', 'minimal', 'animated-pop', 'gradient', 'none'];
const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  queued: { bg: '#eef0f4', color: 'var(--brand)', label: 'In Queue' },
  processing: { bg: '#fef3c7', color: '#F59E0B', label: 'Generating…' },
  completed: { bg: '#dcfce722', color: '#22c55e', label: 'Ready' },
  failed: { bg: '#fee2e222', color: '#EF4444', label: 'Failed' },
};

export default function ReelsFactoryPage() {
  const [templates, setTemplates] = useState<ReelTemplate[]>([]);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const [topic, setTopic] = useState('');
  const [product, setProduct] = useState('');
  const [brand, setBrand] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('hook-reveal');
  const [platform, setPlatform] = useState('instagram');
  const [musicStyle, setMusicStyle] = useState('upbeat');
  const [captionStyle, setCaptionStyle] = useState('bold-subtitles');
  const [addVoiceover, setAddVoiceover] = useState(false);
  const [resizePlatforms, setResizePlatforms] = useState<string[]>(['instagram', 'tiktok']);
  const [resizePresets, setResizePresets] = useState<ResizePreset[]>([]);
  const [resizing, setResizing] = useState(false);
  const [resizeJobId, setResizeJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'library' | 'resize' | 'insights'>('create');

  useEffect(() => { loadTemplates(); }, []);

  useEffect(() => {
    if (!pollingJobId) return;
    const interval = setInterval(async () => {
      try {
        const data = await apiGet<VideoJobResponse>(`/ai/social-studio/video-job/${pollingJobId}`, DEFAULT_TENANT_ID);
        const job: VideoJob = data.job;
        setJobs((prev) => prev.map((j) => (j.id === pollingJobId ? job : j)));
        if (job.status === 'completed' || job.status === 'failed') {
          setPollingJobId(null);
          setSuccessMsg(job.status === 'completed' ? '✅ Reel generated successfully!' : '❌ Generation failed. Please try again.');
          setTimeout(() => setSuccessMsg(null), 5000);
        }
      } catch { /* keep polling */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [pollingJobId]);

  async function loadTemplates() {
    setLoading(true); setError(null);
    try {
      const data = await apiGet<ReelTemplatesResponse>('/ai/social-studio/reel-templates', DEFAULT_TENANT_ID);
      setTemplates(data.templates ?? []);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!topic && !product) { setError('Please enter a topic or product name.'); return; }
    setGenerating(true); setError(null);
    try {
      const data = await apiSend<VideoJobResponse>('/ai/social-studio/text-to-reel', 'POST', {
        topic, product, brand, template_id: selectedTemplate,
        platform, music_style: musicStyle, caption_style: captionStyle, add_voiceover: addVoiceover,
      }, DEFAULT_TENANT_ID);
      setJobs((prev) => [data.job, ...prev]);
      setPollingJobId(data.job.id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setGenerating(false); }
  }

  async function handleResize(jobId: string) {
    setResizing(true); setError(null); setResizeJobId(jobId);
    try {
      const data = await apiSend<AutoResizeResponse>('/ai/social-studio/auto-resize', 'POST', { asset_id: jobId, platforms: resizePlatforms }, DEFAULT_TENANT_ID);
      setResizePresets(data.presets ?? []);
    } catch (e: unknown) { setError(String(e)); }
    finally { setResizing(false); }
  }

  const tmpl = templates.find((t) => t.id === selectedTemplate) ?? templates[0];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>🎬 Reels Factory</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>AI-POWERED</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link href="/studio/faceless-video-engine" style={{ background: 'var(--card)', color: 'var(--text)', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>UGC Avatar Videos →</Link>
          <Link href="/studio/social-studio/ads" style={{ background: '#6366f1', color: '#fff', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Video Ads →</Link>
        </div>
      </div>

      {/* Stats Bar */}
      <div style={{ background: 'var(--card)', padding: '12px 32px', display: 'flex', gap: 32, borderBottom: '1px solid var(--line)' }}>
        {[{ label: 'Generated This Session', value: `${jobs.length}` }, { label: 'Avg Gen Time', value: '45s' }, { label: 'Platforms', value: '5' }, { label: 'Max Duration', value: '60s' }].map((s) => (
          <div key={s.label}><div style={{ fontSize: 20, fontWeight: 700, color: 'var(--brand)' }}>{s.value}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</div></div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ padding: '0 32px', borderBottom: '1px solid var(--line)', background: 'var(--card)', display: 'flex', gap: 0 }}>
        {(['create', 'library', 'resize', 'insights'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: 'none', border: 'none', color: activeTab === tab ? 'var(--brand)' : 'var(--muted)', padding: '14px 20px', cursor: 'pointer', fontSize: 14, fontWeight: activeTab === tab ? 600 : 400, borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent' }}>
            {{ create: '✨ Create', library: '📚 My Reels', resize: '⚡ Resize', insights: '📊 Insights' }[tab]}
          </button>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}
        {successMsg && <div style={{ background: '#dcfce733', border: '1px solid #22c55e', borderRadius: 8, padding: 12, marginBottom: 16, color: '#15803d' }}>{successMsg}</div>}

        {activeTab === 'create' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 24 }}>
            <div>
              <form onSubmit={handleGenerate}>
                {/* Platform */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>TARGET PLATFORM</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {PLATFORMS.map((p) => (
                      <button key={p.id} type="button" onClick={() => setPlatform(p.id)} style={{ background: platform === p.id ? '#6366f1' : '#eef0f4', color: platform === p.id ? '#fff' : 'var(--text)', border: `1px solid ${platform === p.id ? '#6366f1' : '#e7e9ef'}`, padding: '8px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>
                        {p.icon} {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Topic / Product / Brand */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>TOPIC *</label>
                    <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. 5 tips for better sleep" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PRODUCT (optional)</label>
                    <input value={product} onChange={(e) => setProduct(e.target.value)} placeholder="e.g. SleepWell Pillow" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
                  </div>
                </div>
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>BRAND NAME (optional)</label>
                  <input value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="e.g. Restful Co." style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
                </div>

                {/* Template */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>REEL TEMPLATE</label>
                  {loading ? <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading templates…</div> : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 10 }}>
                      {templates.map((t) => (
                        <button key={t.id} type="button" onClick={() => setSelectedTemplate(t.id)} style={{ background: selectedTemplate === t.id ? '#6366f133' : '#eef0f4', border: `1px solid ${selectedTemplate === t.id ? '#6366f1' : '#e7e9ef'}`, borderRadius: 10, padding: 12, cursor: 'pointer', textAlign: 'left', color: 'var(--text)' }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: selectedTemplate === t.id ? 'var(--brand)' : 'var(--text)', marginBottom: 4 }}>{t.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--muted)' }}>{t.duration_s}s · {t.best_for.slice(0, 2).join(', ')}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Music & Captions */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 20 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>MUSIC STYLE</label>
                    <select value={musicStyle} onChange={(e) => setMusicStyle(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                      {MUSIC_STYLES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>CAPTION STYLE</label>
                    <select value={captionStyle} onChange={(e) => setCaptionStyle(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                      {CAPTION_STYLES.map((s) => <option key={s} value={s}>{s.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</option>)}
                    </select>
                  </div>
                </div>

                {/* Voiceover */}
                <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input type="checkbox" id="voiceover" checked={addVoiceover} onChange={(e) => setAddVoiceover(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#6366f1' }} />
                  <label htmlFor="voiceover" style={{ fontSize: 14, color: 'var(--text)', cursor: 'pointer' }}>Add AI voiceover (ElevenLabs TTS)</label>
                </div>

                <button type="submit" disabled={generating} style={{ width: '100%', background: generating ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer' }}>
                  {generating ? '⏳ Generating Reel…' : '🎬 Generate Reel'}
                </button>
              </form>

              {/* Active jobs */}
              {jobs.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Recent Generations</div>
                  {jobs.slice(0, 3).map((job) => {
                    const s = STATUS_STYLES[job.status] ?? STATUS_STYLES.queued;
                    return (
                      <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 10 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{job.template?.name ?? 'Reel'} · {job.platform}</div>
                          <span style={{ background: s.bg, color: s.color, fontSize: 11, padding: '3px 10px', borderRadius: 12, fontWeight: 600 }}>{s.label}</span>
                        </div>
                        {job.status === 'processing' && (
                          <div style={{ height: 4, background: '#e7e9ef', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${job.progress_pct ?? 35}%`, background: '#6366f1', transition: 'width 0.5s' }} />
                          </div>
                        )}
                        {job.status === 'completed' && job.video_url && (
                          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                            <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ background: '#22c55e', color: '#fff', padding: '6px 14px', borderRadius: 6, fontSize: 12, textDecoration: 'none', fontWeight: 600 }}>⬇ Download MP4</a>
                            <button onClick={() => { setActiveTab('resize'); handleResize(job.id); }} style={{ background: '#e7e9ef', color: 'var(--text)', border: 'none', padding: '6px 14px', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>⚡ Resize for All Platforms</button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right sidebar */}
            <div style={{ position: 'sticky', top: 24, alignSelf: 'start' }}>
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--brand)' }}>📋 Template Structure</div>
                {tmpl ? (
                  <>
                    <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{tmpl.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>{tmpl.duration_s}s · {tmpl.best_for.join(', ')}</div>
                    {tmpl.structure.map((seg, i) => {
                      const parts = seg.split('_');
                      const name = parts.slice(0, -1).join(' ').replace(/\b\w/g, (c) => c.toUpperCase());
                      const dur = parts[parts.length - 1];
                      const colors = ['#6366f1', '#22c55e', '#F59E0B', '#EF4444', '#8B5CF6'];
                      return (
                        <div key={seg} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                          <div style={{ width: 26, height: 26, borderRadius: '50%', background: colors[i % colors.length] + '33', color: colors[i % colors.length], display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, flexShrink: 0 }}>{i + 1}</div>
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 600 }}>{name}</div>
                            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{dur}</div>
                          </div>
                        </div>
                      );
                    })}
                  </>
                ) : <div style={{ color: 'var(--muted)', fontSize: 13 }}>Select a template above</div>}
              </div>

              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600, letterSpacing: 1 }}>POWERED BY</div>
                {[
                  { name: 'Runway ML Gen-3', env: 'RUNWAY_API_KEY', use: 'Video generation' },
                  { name: 'Pika Labs', env: 'PIKA_API_KEY', use: 'Text-to-video fallback' },
                  { name: 'ElevenLabs', env: 'ELEVENLABS_API_KEY', use: 'AI voiceover' },
                  { name: 'Captions.ai', env: 'auto-subtitles', use: 'Burned-in captions' },
                ].map((v) => (
                  <div key={v.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div><div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{v.name}</div><div style={{ fontSize: 10, color: '#6366f1' }}>{v.env}</div></div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>{v.use}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'library' && (
          <div>
            {jobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🎬</div>
                <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No reels yet</div>
                <div style={{ fontSize: 14, marginBottom: 20 }}>Switch to Create tab to generate your first reel</div>
                <button onClick={() => setActiveTab('create')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>Start Creating</button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))', gap: 16 }}>
                {jobs.map((job) => {
                  const s = STATUS_STYLES[job.status] ?? STATUS_STYLES.queued;
                  return (
                    <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden' }}>
                      <div style={{ height: 160, background: `#e7e9ef url(${job.thumbnail_url}) center/cover no-repeat`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ fontSize: 32 }}>{job.status === 'completed' ? '▶' : '⏳'}</div>
                      </div>
                      <div style={{ padding: 14 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{job.template?.name ?? 'Reel'}</div>
                          <span style={{ background: s.bg, color: s.color, fontSize: 10, padding: '2px 8px', borderRadius: 10 }}>{s.label}</span>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>{job.platform} · {job.duration_s ?? '?'}s</div>
                        {job.status === 'completed' && job.video_url && (
                          <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', background: '#6366f1', color: '#fff', padding: '6px 0', borderRadius: 6, fontSize: 12, textDecoration: 'none', textAlign: 'center', fontWeight: 600 }}>⬇ Download</a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'resize' && (
          <div style={{ maxWidth: 700 }}>
            <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 20 }}>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>⚡ One-Click Multi-Platform Resize</div>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 20 }}>Automatically resize for all platforms with correct aspect ratios and safe zones.</div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8 }}>SELECT PLATFORMS</label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {PLATFORMS.map((p) => (
                    <button key={p.id} type="button" onClick={() => setResizePlatforms((prev) => prev.includes(p.id) ? prev.filter((x) => x !== p.id) : [...prev, p.id])} style={{ background: resizePlatforms.includes(p.id) ? '#6366f133' : '#eef0f4', border: `1px solid ${resizePlatforms.includes(p.id) ? '#6366f1' : '#e7e9ef'}`, color: resizePlatforms.includes(p.id) ? 'var(--brand)' : 'var(--muted)', padding: '7px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>
                      {p.icon} {p.label}
                    </button>
                  ))}
                </div>
              </div>
              {jobs.filter((j) => j.status === 'completed').length > 0 ? (
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8 }}>SELECT REEL TO RESIZE</label>
                  {jobs.filter((j) => j.status === 'completed').map((job) => (
                    <button key={job.id} onClick={() => handleResize(job.id)} disabled={resizing} style={{ display: 'block', width: '100%', background: resizeJobId === job.id ? '#6366f133' : '#eef0f4', border: `1px solid ${resizeJobId === job.id ? '#6366f1' : '#e7e9ef'}`, color: 'var(--text)', padding: '10px 16px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', fontSize: 13, marginBottom: 8 }}>
                      {resizing && resizeJobId === job.id ? '⏳ Resizing…' : `${job.template?.name ?? 'Reel'} (${job.id.slice(0, 8)}…)`}
                    </button>
                  ))}
                </div>
              ) : (
                <div style={{ color: 'var(--muted)', fontSize: 13 }}>Generate a reel first, then resize it here.</div>
              )}
            </div>
            {resizePresets.length > 0 && (
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#22c55e' }}>✅ {resizePresets.length} Variants Ready</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
                  {resizePresets.map((p, i) => (
                    <div key={i} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>{p.platform.toUpperCase()} · {p.format}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>{p.width}×{p.height} · {p.aspect_ratio}</div>
                      {p.resized_asset_url && <a href={p.resized_asset_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: '#6366f1', textDecoration: 'none' }}>⬇ Download</a>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'insights' && (
          <div style={{ maxWidth: 800 }}>
            <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>📊 Reel Performance Data</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 24 }}>
                {[{ metric: '3.1×', label: 'Higher ROAS vs static images', color: '#22c55e' }, { metric: '8.9%', label: 'Average engagement rate', color: 'var(--brand)' }, { metric: '< 3s', label: 'Hook must land in first 3 seconds', color: '#F59E0B' }, { metric: '60s', label: 'Max length for Instagram Reels', color: '#EF4444' }].map((s) => (
                  <div key={s.label} style={{ background: 'var(--card)', borderRadius: 10, padding: 20, textAlign: 'center' }}>
                    <div style={{ fontSize: 32, fontWeight: 800, color: s.color, marginBottom: 6 }}>{s.metric}</div>
                    <div style={{ fontSize: 13, color: 'var(--muted)' }}>{s.label}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>✅ AI Recommendations</div>
              {['Start with a pattern-interrupt hook in the first 2 seconds', 'Add bold captions — 80% of viewers watch without sound', 'Use trending audio from the platform\'s recommended library', 'Keep the CTA visible in the last 3 seconds', 'Post between 7-9am or 6-9pm for highest initial boost'].map((rec, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
                  <span style={{ color: '#22c55e', fontSize: 16, marginTop: 1 }}>▸</span>
                  <span style={{ fontSize: 13, color: 'var(--text)' }}>{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
