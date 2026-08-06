'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Avatar = {
  id: string;
  name: string;
  gender: string;
  age_range: string;
  ethnicity: string;
  style: string;
  preview_url: string;
  languages: string[];
};

type VideoJob = {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_pct?: number;
  video_url?: string | null;
  thumbnail_url?: string;
  avatar?: Avatar;
  estimated_duration_s?: number;
  platform?: string;
};

type AvatarCatalogResponse = {
  avatars: Avatar[];
};

type VideoJobResponse = {
  job: VideoJob;
};

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', icon: '📸' },
  { id: 'tiktok', label: 'TikTok', icon: '🎵' },
  { id: 'youtube', label: 'YouTube', icon: '▶️' },
  { id: 'facebook', label: 'Facebook', icon: '👥' },
  { id: 'linkedin', label: 'LinkedIn', icon: '💼' },
];

const BACKGROUNDS = ['studio-white', 'office', 'outdoor', 'gradient-purple', 'gradient-blue', 'custom-green-screen'];
const VOICE_STYLES = ['conversational', 'professional', 'energetic', 'calm', 'authoritative', 'friendly'];

const STATUS = {
  queued: { bg: '#eef0f4', color: 'var(--brand)', label: 'In Queue' },
  processing: { bg: '#fef3c7', color: '#F59E0B', label: 'Generating…' },
  completed: { bg: '#dcfce722', color: '#22c55e', label: 'Ready' },
  failed: { bg: '#fee2e222', color: '#EF4444', label: 'Failed' },
};

export default function FacelessVideoEnginePage() {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [loadingAvatars, setLoadingAvatars] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'library'>('create');

  // Form
  const [selectedAvatar, setSelectedAvatar] = useState<string>('');
  const [script, setScript] = useState('');
  const [productName, setProductName] = useState('');
  const [platform, setPlatform] = useState('instagram');
  const [background, setBackground] = useState('studio-white');
  const [voiceLanguage, setVoiceLanguage] = useState('en');
  const [voiceStyle, setVoiceStyle] = useState('conversational');
  const [addCaptions, setAddCaptions] = useState(true);
  const [addBrandWatermark, setAddBrandWatermark] = useState(false);
  const [filterGender, setFilterGender] = useState<string>('all');

  useEffect(() => { loadAvatars(); }, []);

  useEffect(() => {
    if (!pollingJobId) return;
    const iv = setInterval(async () => {
      try {
        const data = await apiGet<VideoJobResponse>(`/ai/social-studio/video-job/${pollingJobId}`, DEFAULT_TENANT_ID);
        const job: VideoJob = data.job;
        setJobs((prev) => prev.map((j) => (j.id === pollingJobId ? job : j)));
        if (job.status === 'completed' || job.status === 'failed') {
          setPollingJobId(null);
          setSuccessMsg(job.status === 'completed' ? '✅ Avatar video ready!' : '❌ Generation failed.');
          setTimeout(() => setSuccessMsg(null), 5000);
        }
      } catch { /* keep polling */ }
    }, 3000);
    return () => clearInterval(iv);
  }, [pollingJobId]);

  async function loadAvatars() {
    setLoadingAvatars(true);
    try {
      const data = await apiGet<AvatarCatalogResponse>('/ai/social-studio/avatar-catalog', DEFAULT_TENANT_ID);
      setAvatars(data.avatars ?? []);
      if (data.avatars?.length > 0) setSelectedAvatar(data.avatars[0].id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoadingAvatars(false); }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!script.trim()) { setError('Script is required.'); return; }
    if (!selectedAvatar) { setError('Please select an avatar.'); return; }
    setGenerating(true); setError(null);
    try {
      const data = await apiSend<VideoJobResponse>('/ai/social-studio/ugc-avatar-video', 'POST', {
        avatar_id: selectedAvatar, script, product_name: productName,
        platform, background, voice_language: voiceLanguage,
        voice_style: voiceStyle, add_captions: addCaptions,
        add_brand_watermark: addBrandWatermark,
      }, DEFAULT_TENANT_ID);
      setJobs((prev) => [data.job, ...prev]);
      setPollingJobId(data.job.id);
    } catch (e: unknown) { setError(String(e)); }
    finally { setGenerating(false); }
  }

  const filteredAvatars = filterGender === 'all' ? avatars : avatars.filter((a) => a.gender === filterGender);
  const wordCount = script.trim().split(/\s+/).filter(Boolean).length;
  const estimatedDuration = Math.max(10, Math.round(wordCount / 130 * 60));
  const activeAvatar = avatars.find((a) => a.id === selectedAvatar);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>🤖 Faceless Video Engine</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>NO REAL ACTORS NEEDED</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link href="/studio/reels-factory" style={{ background: 'var(--card)', color: 'var(--text)', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Reels Factory →</Link>
          <Link href="/studio/short-video-factory" style={{ background: '#6366f1', color: '#fff', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>Short Videos →</Link>
        </div>
      </div>

      {/* Stats */}
      <div style={{ background: 'var(--card)', padding: '12px 32px', display: 'flex', gap: 32, borderBottom: '1px solid var(--line)' }}>
        {[{ label: 'AI Avatars', value: `${avatars.length}` }, { label: 'Videos Created', value: `${jobs.length}` }, { label: 'Languages', value: '20+' }, { label: 'Providers', value: 'HeyGen/D-ID/Synthesia' }].map((s) => (
          <div key={s.label}><div style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>{s.value}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</div></div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ padding: '0 32px', borderBottom: '1px solid var(--line)', background: 'var(--card)', display: 'flex' }}>
        {(['create', 'library'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: 'none', border: 'none', color: activeTab === tab ? 'var(--brand)' : 'var(--muted)', padding: '14px 20px', cursor: 'pointer', fontSize: 14, fontWeight: activeTab === tab ? 600 : 400, borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent' }}>
            {{ create: '✨ Create', library: '📚 My Videos' }[tab]}
          </button>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}
        {successMsg && <div style={{ background: '#dcfce733', border: '1px solid #22c55e', borderRadius: 8, padding: 12, marginBottom: 16, color: '#15803d' }}>{successMsg}</div>}

        {activeTab === 'create' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 24 }}>
            <form onSubmit={handleGenerate}>
              {/* Avatar Selection */}
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <label style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600 }}>CHOOSE AI AVATAR</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {['all', 'female', 'male'].map((g) => (
                      <button key={g} type="button" onClick={() => setFilterGender(g)} style={{ background: filterGender === g ? '#6366f133' : '#eef0f4', border: `1px solid ${filterGender === g ? '#6366f1' : '#e7e9ef'}`, color: filterGender === g ? 'var(--brand)' : 'var(--muted)', padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                        {g.charAt(0).toUpperCase() + g.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
                {loadingAvatars ? (
                  <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading avatars…</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 10 }}>
                    {filteredAvatars.map((avatar) => (
                      <button key={avatar.id} type="button" onClick={() => setSelectedAvatar(avatar.id)} style={{ background: selectedAvatar === avatar.id ? '#6366f133' : '#eef0f4', border: `2px solid ${selectedAvatar === avatar.id ? '#6366f1' : '#e7e9ef'}`, borderRadius: 12, padding: 12, cursor: 'pointer', textAlign: 'center', color: 'var(--text)', transition: 'all 0.15s' }}>
                        <div style={{ width: 60, height: 60, borderRadius: '50%', background: `url(${avatar.preview_url}) center/cover`, margin: '0 auto 8px', border: `2px solid ${selectedAvatar === avatar.id ? '#6366f1' : '#e7e9ef'}` }} />
                        <div style={{ fontSize: 13, fontWeight: 600, color: selectedAvatar === avatar.id ? 'var(--brand)' : 'var(--text)' }}>{avatar.name}</div>
                        <div style={{ fontSize: 10, color: 'var(--muted)' }}>{avatar.age_range} · {avatar.style}</div>
                        <div style={{ fontSize: 10, color: '#6366f1', marginTop: 2 }}>{avatar.languages.slice(0, 3).join(', ')}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Platform */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>PLATFORM</label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {PLATFORMS.map((p) => (
                    <button key={p.id} type="button" onClick={() => setPlatform(p.id)} style={{ background: platform === p.id ? '#6366f1' : '#eef0f4', color: platform === p.id ? '#fff' : 'var(--text)', border: `1px solid ${platform === p.id ? '#6366f1' : '#e7e9ef'}`, padding: '7px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>
                      {p.icon} {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Product & Script */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>PRODUCT NAME (optional)</label>
                <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="e.g. GlowSkin Serum" style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }} />
              </div>

              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <label style={{ fontSize: 13, color: 'var(--muted)' }}>AVATAR SCRIPT *</label>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{wordCount} words · ~{estimatedDuration}s</span>
                </div>
                <textarea value={script} onChange={(e) => setScript(e.target.value)} placeholder="Write what the avatar should say... e.g. Hey! I've been using GlowSkin Serum for 30 days and my skin has never looked better. The formula is lightweight, fast-absorbing, and actually works. Try it today — link in bio!" rows={6} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
              </div>

              {/* Background & Voice */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 20 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>BACKGROUND</label>
                  <select value={background} onChange={(e) => setBackground(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                    {BACKGROUNDS.map((b) => <option key={b} value={b}>{b.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>VOICE STYLE</label>
                  <select value={voiceStyle} onChange={(e) => setVoiceStyle(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                    {VOICE_STYLES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                  </select>
                </div>
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>VOICE LANGUAGE</label>
                <select value={voiceLanguage} onChange={(e) => setVoiceLanguage(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                  {(activeAvatar?.languages ?? ['en']).map((lang) => (
                    <option key={lang} value={lang}>{lang.toUpperCase()}</option>
                  ))}
                </select>
              </div>

              {/* Toggles */}
              <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
                {[{ id: 'captions', label: 'Burned-in captions', checked: addCaptions, onChange: setAddCaptions }, { id: 'watermark', label: 'Brand watermark', checked: addBrandWatermark, onChange: setAddBrandWatermark }].map((tog) => (
                  <label key={tog.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, color: 'var(--text)' }}>
                    <input type="checkbox" checked={tog.checked} onChange={(e) => tog.onChange(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#6366f1' }} />
                    {tog.label}
                  </label>
                ))}
              </div>

              <button type="submit" disabled={generating} style={{ width: '100%', background: generating ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer' }}>
                {generating ? '⏳ Generating Avatar Video…' : '🤖 Generate Faceless Video'}
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
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{job.avatar?.name ?? 'Avatar'} · {job.platform} · {job.estimated_duration_s ?? '?'}s</div>
                          <span style={{ background: s.bg, color: s.color, fontSize: 11, padding: '2px 10px', borderRadius: 12, fontWeight: 600 }}>{s.label}</span>
                        </div>
                        {job.status === 'processing' && <div style={{ height: 3, background: '#e7e9ef', borderRadius: 2 }}><div style={{ height: '100%', width: `${job.progress_pct ?? 35}%`, background: '#6366f1' }} /></div>}
                        {job.status === 'completed' && job.video_url && <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ background: '#22c55e', color: '#fff', padding: '5px 14px', borderRadius: 6, fontSize: 12, textDecoration: 'none', fontWeight: 600 }}>⬇ Download</a>}
                      </div>
                    );
                  })}
                </div>
              )}
            </form>

            {/* Right Sidebar */}
            <div style={{ position: 'sticky', top: 24, alignSelf: 'start' }}>
              {activeAvatar && (
                <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: 'var(--brand)', fontWeight: 600, marginBottom: 12 }}>SELECTED AVATAR</div>
                  <div style={{ width: 80, height: 80, borderRadius: '50%', background: `url(${activeAvatar.preview_url}) center/cover`, margin: '0 auto 12px', border: '2px solid #6366f1' }} />
                  <div style={{ fontSize: 18, fontWeight: 700, textAlign: 'center', marginBottom: 4 }}>{activeAvatar.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', marginBottom: 12 }}>{activeAvatar.gender} · {activeAvatar.age_range} · {activeAvatar.style}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>Languages: {activeAvatar.languages.join(', ')}</div>
                </div>
              )}

              {/* Script estimator */}
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: 'var(--brand)', fontWeight: 600, marginBottom: 10 }}>SCRIPT ESTIMATOR</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>Word count</span>
                  <span style={{ fontSize: 12, color: 'var(--text)' }}>{wordCount}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>Est. duration</span>
                  <span style={{ fontSize: 12, color: '#22c55e' }}>{estimatedDuration}s</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>Speaking rate</span>
                  <span style={{ fontSize: 12, color: 'var(--text)' }}>130 wpm</span>
                </div>
              </div>

              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600, letterSpacing: 1 }}>AI PROVIDERS</div>
                {[{ name: 'HeyGen', env: 'HEYGEN_API_KEY', tier: 'Primary' }, { name: 'D-ID', env: 'D_ID_API_KEY', tier: 'Fallback' }, { name: 'Synthesia', env: 'SYNTHESIA_API_KEY', tier: 'Enterprise' }, { name: 'ElevenLabs', env: 'ELEVENLABS_API_KEY', tier: 'Voice' }].map((v) => (
                  <div key={v.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div><div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{v.name}</div><div style={{ fontSize: 10, color: '#6366f1' }}>{v.env}</div></div>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{v.tier}</span>
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
                <div style={{ fontSize: 48, marginBottom: 12 }}>🤖</div>
                <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No avatar videos yet</div>
                <button onClick={() => setActiveTab('create')} style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>Create First Video</button>
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
                          <span style={{ fontSize: 12, fontWeight: 600 }}>{job.avatar?.name ?? 'Avatar'} · {job.platform}</span>
                          <span style={{ background: s.bg, color: s.color, fontSize: 10, padding: '1px 8px', borderRadius: 10 }}>{s.label}</span>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>{job.estimated_duration_s ?? '?'}s video</div>
                        {job.status === 'completed' && job.video_url && <a href={job.video_url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', background: '#6366f1', color: '#fff', padding: '5px 0', borderRadius: 6, fontSize: 11, textDecoration: 'none', textAlign: 'center', fontWeight: 600 }}>⬇ Download</a>}
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
