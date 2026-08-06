'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type VideoJob = {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_pct?: number;
  video_url?: string | null;
  thumbnail_url?: string;
  platform?: string;
  format?: string;
  duration_s?: number;
  style?: string;
  prompt?: string;
  estimated_completion_s?: number;
};

type VideoJobResponse = {
  job: VideoJob;
};

const PLATFORMS = [
  { id: 'tiktok', label: 'TikTok', icon: '🎵', maxDuration: 60 },
  { id: 'youtube', label: 'YouTube Shorts', icon: '▶️', maxDuration: 60 },
  { id: 'instagram', label: 'Instagram Reels', icon: '📸', maxDuration: 90 },
  { id: 'snapchat', label: 'Snapchat Spotlight', icon: '👻', maxDuration: 60 },
];

const STYLES = ['ugc-style', 'cinematic', 'product-showcase', 'tutorial', 'vlog', 'animation'];
const DURATIONS = [15, 30, 45, 60];

const STATUS = {
  queued: { bg: '#eef0f4', color: 'var(--brand)', label: 'In Queue' },
  processing: { bg: '#fef3c7', color: '#F59E0B', label: 'Generating…' },
  completed: { bg: '#dcfce722', color: '#22c55e', label: 'Ready' },
  failed: { bg: '#fee2e222', color: '#EF4444', label: 'Failed' },
};

export default function ShortVideoFactoryPage() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'library'>('create');

  // Form
  const [prompt, setPrompt] = useState('');
  const [platform, setPlatform] = useState('tiktok');
  const [style, setStyle] = useState('ugc-style');
  const [duration, setDuration] = useState(30);
  const [addCaptions, setAddCaptions] = useState(true);
  const [addVoiceover, setAddVoiceover] = useState(false);
  const [brandColors, setBrandColors] = useState('');

  useEffect(() => {
    if (!pollingJobId) return;
    const iv = setInterval(async () => {
      try {
        const data = await apiGet<VideoJobResponse>(`/ai/social-studio/video-job/${pollingJobId}`, DEFAULT_TENANT_ID);
        const job: VideoJob = data.job;
        setJobs((prev) => prev.map((j) => (j.id === pollingJobId ? job : j)));
        if (job.status === 'completed' || job.status === 'failed') {
          setPollingJobId(null);
          setSuccessMsg(job.status === 'completed' ? '✅ Video ready!' : '❌ Generation failed.');
          setTimeout(() => setSuccessMsg(null), 5000);
        }
      } catch { /* keep polling */ }
    }, 3000);
    return () => clearInterval(iv);
  }, [pollingJobId]);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) { setError('Please enter a prompt or script.'); return; }
    setGenerating(true); setError(null);
    try {
      const colors = brandColors.split(',').map((c) => c.trim()).filter(Boolean);
      const data = await apiSend<VideoJobResponse>('/ai/social-studio/text-to-video', 'POST', {
        prompt, platform, style, duration_s: duration, format: 'short',
        add_captions: addCaptions, add_voiceover: addVoiceover,
        aspect_ratio: '9:16',
        brand_colors: colors,
      }, DEFAULT_TENANT_ID);
      setJobs((prev) => [data.job, ...prev]);
      setPollingJobId(data.job.id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setGenerating(false); }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>📱 Short Video Factory</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>AI-POWERED</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link href="/studio/reels-factory" style={{ background: 'var(--card)', color: 'var(--text)', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Reels Factory →</Link>
          <Link href="/studio/faceless-video-engine" style={{ background: '#6366f1', color: '#fff', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Faceless Videos →</Link>
        </div>
      </div>

      <div style={{ background: 'var(--card)', padding: '12px 32px', display: 'flex', gap: 32, borderBottom: '1px solid var(--line)' }}>
        {[{ label: 'Videos This Session', value: `${jobs.length}` }, { label: 'Max Duration', value: '60s' }, { label: 'Output Format', value: '9:16' }, { label: 'Aspect Ratio', value: 'Vertical' }].map((s) => (
          <div key={s.label}><div style={{ fontSize: 20, fontWeight: 700, color: 'var(--brand)' }}>{s.value}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</div></div>
        ))}
      </div>

      <div style={{ padding: '0 32px', borderBottom: '1px solid var(--line)', background: 'var(--card)', display: 'flex' }}>
        {(['create', 'library'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: 'none', border: 'none', color: activeTab === tab ? 'var(--brand)' : 'var(--muted)', padding: '14px 20px', cursor: 'pointer', fontSize: 14, fontWeight: activeTab === tab ? 600 : 400, borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent' }}>
            {{ create: '✨ Create', library: '📚 My Videos' }[tab]}
          </button>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 900, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}
        {successMsg && <div style={{ background: '#dcfce733', border: '1px solid #22c55e', borderRadius: 8, padding: 12, marginBottom: 16, color: '#15803d' }}>{successMsg}</div>}

        {activeTab === 'create' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 24 }}>
            <form onSubmit={handleGenerate}>
              {/* Platform */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>PLATFORM</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {PLATFORMS.map((p) => (
                    <button key={p.id} type="button" onClick={() => { setPlatform(p.id); setDuration(Math.min(duration, p.maxDuration)); }} style={{ background: platform === p.id ? '#6366f1' : '#eef0f4', color: platform === p.id ? '#fff' : 'var(--text)', border: `1px solid ${platform === p.id ? '#6366f1' : '#e7e9ef'}`, padding: '8px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>
                      {p.icon} {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Prompt */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PROMPT / SCRIPT *</label>
                <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Describe your short video... e.g. A trending TikTok-style video showing our new skincare product with before/after shots and bold captions" rows={4} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
              </div>

              {/* Style & Duration */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 20 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>VIDEO STYLE</label>
                  <select value={style} onChange={(e) => setStyle(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                    {STYLES.map((s) => <option key={s} value={s}>{s.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>DURATION</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {DURATIONS.filter((d) => d <= (PLATFORMS.find((p) => p.id === platform)?.maxDuration ?? 60)).map((d) => (
                      <button key={d} type="button" onClick={() => setDuration(d)} style={{ flex: 1, background: duration === d ? '#6366f1' : '#eef0f4', color: duration === d ? '#fff' : 'var(--text)', border: `1px solid ${duration === d ? '#6366f1' : '#e7e9ef'}`, padding: '8px 6px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>{d}s</button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Brand Colors */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>BRAND COLORS (comma-separated hex, optional)</label>
                <input value={brandColors} onChange={(e) => setBrandColors(e.target.value)} placeholder="#6366f1, #22c55e, #F59E0B" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
              </div>

              {/* Toggles */}
              <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
                {[{ id: 'captions', label: 'Auto-captions', checked: addCaptions, onChange: setAddCaptions }, { id: 'voiceover', label: 'AI voiceover', checked: addVoiceover, onChange: setAddVoiceover }].map((tog) => (
                  <label key={tog.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, color: 'var(--text)' }}>
                    <input type="checkbox" checked={tog.checked} onChange={(e) => tog.onChange(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#6366f1' }} />
                    {tog.label}
                  </label>
                ))}
              </div>

              <button type="submit" disabled={generating} style={{ width: '100%', background: generating ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer' }}>
                {generating ? '⏳ Generating Short Video…' : '📱 Generate Short Video'}
              </button>

              {/* Jobs */}
              {jobs.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Recent Videos</div>
                  {jobs.slice(0, 3).map((job) => {
                    const s = STATUS[job.status] ?? STATUS.queued;
                    return (
                      <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 14, marginBottom: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{job.platform} · {job.duration_s ?? duration}s · {job.style ?? style}</div>
                          <span style={{ background: s.bg, color: s.color, fontSize: 11, padding: '2px 10px', borderRadius: 12, fontWeight: 600 }}>{s.label}</span>
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>{String(job.prompt ?? prompt).slice(0, 80)}…</div>
                        {job.status === 'processing' && <div style={{ height: 3, background: '#e7e9ef', borderRadius: 2 }}><div style={{ height: '100%', width: `${job.progress_pct ?? 35}%`, background: '#6366f1' }} /></div>}
                        {job.status === 'completed' && job.video_url && <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ background: '#22c55e', color: '#fff', padding: '5px 14px', borderRadius: 6, fontSize: 12, textDecoration: 'none', fontWeight: 600 }}>⬇ Download</a>}
                      </div>
                    );
                  })}
                </div>
              )}
            </form>

            {/* Sidebar */}
            <div style={{ position: 'sticky', top: 24, alignSelf: 'start' }}>
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--brand)' }}>📐 Platform Specs</div>
                {PLATFORMS.map((p) => (
                  <div key={p.id} style={{ marginBottom: 10, padding: 10, background: platform === p.id ? '#6366f122' : '#eef0f4', borderRadius: 8, border: `1px solid ${platform === p.id ? '#6366f1' : '#eef0f4'}` }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{p.icon} {p.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>Max {p.maxDuration}s · 9:16 · 1080×1920</div>
                  </div>
                ))}
              </div>

              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600, letterSpacing: 1 }}>AI PROVIDERS</div>
                {[{ name: 'Runway ML', env: 'RUNWAY_API_KEY' }, { name: 'Pika Labs', env: 'PIKA_API_KEY' }, { name: 'Kling AI', env: 'KLING_API_KEY' }, { name: 'ElevenLabs', env: 'ELEVENLABS_API_KEY' }].map((v) => (
                  <div key={v.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: 'var(--text)' }}>{v.name}</span>
                    <span style={{ fontSize: 10, color: '#6366f1' }}>{v.env}</span>
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
                <div style={{ fontSize: 48, marginBottom: 12 }}>📱</div>
                <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No videos yet</div>
                <button onClick={() => setActiveTab('create')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>Start Creating</button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 16 }}>
                {jobs.map((job) => {
                  const s = STATUS[job.status] ?? STATUS.queued;
                  return (
                    <div key={job.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden' }}>
                      <div style={{ height: 150, background: `#e7e9ef url(${job.thumbnail_url}) center/cover no-repeat`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ fontSize: 28 }}>{job.status === 'completed' ? '▶' : '⏳'}</div>
                      </div>
                      <div style={{ padding: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ fontSize: 12, fontWeight: 600 }}>{job.platform} · {job.duration_s ?? '?'}s</span>
                          <span style={{ background: s.bg, color: s.color, fontSize: 10, padding: '1px 8px', borderRadius: 10 }}>{s.label}</span>
                        </div>
                        {job.status === 'completed' && job.video_url && <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', background: '#6366f1', color: '#fff', padding: '5px 0', borderRadius: 6, fontSize: 11, textDecoration: 'none', textAlign: 'center', marginTop: 6, fontWeight: 600 }}>⬇ Download</a>}
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
