'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type VoiceFingerprint = {
  avg_sentence_length: number;
  signature_words: string[];
  punctuation_intensity: number;
  line_break_ratio: number;
};

type BrandVoiceProfile = {
  profile_key: string;
  headline: string;
  voice_score: number;
  fingerprint: VoiceFingerprint;
  rewrite: string;
  updated_at: string | null;
  thumbs_up: number;
  thumbs_down: number;
};

export default function BrandVoicePage() {
  const [profiles, setProfiles] = useState<BrandVoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedbackKey, setFeedbackKey] = useState<string | null>(null);
  const [editedOutput, setEditedOutput] = useState('');

  // Create profile form
  const [profileName, setProfileName] = useState('Primary Voice');
  const [samplePosts, setSamplePosts] = useState(
    'We publish proof-heavy growth content with sharp hooks and direct outcomes.\nIf a post cannot drive pipeline, it should not take up the slot.\nClarity wins. Specificity wins. Revenue wins.'
  );
  const [aiOutput, setAiOutput] = useState(
    'Grow your audience with AI-powered content that resonates at scale.'
  );

  useEffect(() => {
    void loadProfiles();
  }, []);

  async function loadProfiles() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{ profiles?: BrandVoiceProfile[] }>(
        '/ai/brand-voice/profiles',
        DEFAULT_TENANT_ID
      );
      setProfiles(res.profiles ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  }

  async function createProfile() {
    setSubmitting(true);
    setError(null);
    try {
      const posts = samplePosts.split('\n').map((p) => p.trim()).filter(Boolean);
      if (posts.length < 3) {
        setError('Please enter at least 3 sample posts (one per line).');
        return;
      }
      await apiSend(
        '/ai/brand-voice/profile',
        'POST',
        { profile_name: profileName, sample_posts: posts, ai_output: aiOutput },
        DEFAULT_TENANT_ID
      );
      await loadProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create profile');
    } finally {
      setSubmitting(false);
    }
  }

  async function sendFeedback(profileKey: string, signal: 'thumbs_up' | 'thumbs_down') {
    try {
      await apiSend(
        `/ai/brand-voice/${profileKey}/feedback`,
        'POST',
        { signal, edited_output: editedOutput || undefined },
        DEFAULT_TENANT_ID
      );
      setFeedbackKey(null);
      setEditedOutput('');
      await loadProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Feedback failed');
    }
  }

  let profilesContent: React.ReactNode;
  if (loading) {
    profilesContent = <div style={s.skeleton}>Loading profiles…</div>;
  } else if (profiles.length === 0) {
    profilesContent = <div style={s.empty}>No voice profiles yet. Create one above.</div>;
  } else {
    profilesContent = profiles.map((p) => (
      <div key={p.profile_key} style={s.profileCard}>
        <div style={s.profileHeader}>
          <div>
            <span style={s.profileKey}>{p.profile_key}</span>
            <span style={s.scoreChip}>{p.voice_score}/100</span>
          </div>
          <div style={s.feedbackRow}>
            <button
              onClick={() => sendFeedback(p.profile_key, 'thumbs_up')}
              style={s.thumbBtn}
              title="This rewrite captures my voice"
            >
              👍 {p.thumbs_up}
            </button>
            <button
              onClick={() => {
                setFeedbackKey(p.profile_key);
                setEditedOutput(p.rewrite);
              }}
              style={s.thumbBtnDown}
              title="Needs improvement"
            >
              👎 {p.thumbs_down}
            </button>
          </div>
        </div>

        <p style={s.headline}>{p.headline}</p>

        <div style={s.grid2}>
          <div>
            <div style={s.label}>Signature Words</div>
            <div style={s.chips}>
              {(p.fingerprint.signature_words ?? []).map((word) => (
                <span key={word} style={s.chip}>{word}</span>
              ))}
            </div>
          </div>
          <div>
            <div style={s.label}>Fingerprint</div>
            <div style={s.metaGrid}>
              <span>Avg sentence length: <b>{p.fingerprint.avg_sentence_length}</b></span>
              <span>Punctuation intensity: <b>{p.fingerprint.punctuation_intensity}</b></span>
              <span>Line-break ratio: <b>{p.fingerprint.line_break_ratio}</b></span>
            </div>
          </div>
        </div>

        <div style={s.field}>
          <div style={s.label}>AI Rewrite (in your voice)</div>
          <div style={s.rewrite}>{p.rewrite}</div>
        </div>

        {feedbackKey === p.profile_key ? (
          <div style={s.editPanel}>
            <div style={s.label}>Edit the rewrite to train the model:</div>
            <textarea
              value={editedOutput}
              onChange={(e) => setEditedOutput(e.target.value)}
              style={{ ...s.input, height: 100 }}
            />
            <div style={s.feedbackRow}>
              <button
                onClick={() => sendFeedback(p.profile_key, 'thumbs_down')}
                style={s.btn}
              >
                Submit Feedback
              </button>
              <button onClick={() => setFeedbackKey(null)} style={s.btnGhost}>
                Cancel
              </button>
            </div>
          </div>
        ) : null}
      </div>
    ));
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>Brand Voice DNA</h1>
        <p style={s.subtitle}>
          Build an AI writing model from your existing social content. The model learns your signature words, sentence
          cadence, and tone — then writes in a version of your voice optimised for your audience.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      {/* Create Profile */}
      <section style={s.card}>
        <h2 style={s.sectionTitle}>Create / Update Voice Profile</h2>
        <p style={s.hint}>
          Paste 3–30 sample posts (one per line). The AI will extract your fingerprint: signature words, sentence
          length, punctuation intensity, and more. Optionally paste an AI-generated draft to score against your voice.
        </p>
        <div style={s.field}>
          <label htmlFor="profile-name" style={s.label}>Profile Name</label>
          <input
            id="profile-name"
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
            style={s.input}
            placeholder="Primary Voice"
          />
        </div>
        <div style={s.field}>
          <label htmlFor="sample-posts" style={s.label}>Sample Posts (one per line, min 3)</label>
          <textarea
            id="sample-posts"
            value={samplePosts}
            onChange={(e) => setSamplePosts(e.target.value)}
            style={{ ...s.input, height: 120 }}
            placeholder="Paste your best-performing posts here…"
          />
        </div>
        <div style={s.field}>
          <label htmlFor="ai-draft" style={s.label}>AI Draft to Score (optional)</label>
          <textarea
            id="ai-draft"
            value={aiOutput}
            onChange={(e) => setAiOutput(e.target.value)}
            style={{ ...s.input, height: 72 }}
            placeholder="Paste a generic AI-written post to rewrite in your voice…"
          />
        </div>
        <button onClick={createProfile} disabled={submitting} style={s.btn}>
          {submitting ? 'Analysing…' : 'Analyse Voice & Save Profile'}
        </button>
      </section>

      {/* Profiles List */}
      <section>
        <h2 style={s.sectionTitle}>Saved Voice Models</h2>
        {profilesContent}
      </section>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { maxWidth: 900, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 32 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 28, fontWeight: 800, margin: '10px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 14, color: 'var(--muted)', maxWidth: 680 },
  errorBanner: { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8, padding: '10px 14px', color: '#dc2626', marginBottom: 20, fontSize: 13 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 32 },
  profileCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 },
  profileHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  profileKey: { fontWeight: 700, color: 'var(--text)', fontSize: 15, marginRight: 8 },
  scoreChip: { background: 'rgba(34,197,94,0.12)', color: '#15803d', border: '1px solid rgba(34,197,94,0.25)', borderRadius: 6, padding: '2px 8px', fontSize: 13, fontWeight: 700 },
  feedbackRow: { display: 'flex', gap: 8 },
  thumbBtn: { background: 'rgba(34,197,94,0.1)', color: '#15803d', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 14 },
  thumbBtnDown: { background: 'rgba(248,113,113,0.1)', color: '#dc2626', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 14 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: '0 0 16px', color: 'var(--text)' },
  hint: { fontSize: 13, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.6 },
  headline: { fontSize: 13, color: 'var(--muted)', margin: '0 0 12px' },
  field: { marginBottom: 14 },
  label: { fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'block' },
  input: { width: '100%', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box' as const, resize: 'vertical' as const },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 18px', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  btnGhost: { background: 'transparent', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 18px', cursor: 'pointer', fontSize: 14 },
  skeleton: { color: 'var(--muted)', fontSize: 13, padding: 20 },
  empty: { color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 40 },
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 12 },
  chips: { display: 'flex', flexWrap: 'wrap' as const, gap: 6, marginTop: 4 },
  chip: { background: 'rgba(99,102,241,0.15)', color: 'var(--brand)', borderRadius: 4, padding: '2px 8px', fontSize: 12 },
  metaGrid: { display: 'flex', flexDirection: 'column' as const, gap: 4, fontSize: 12, color: 'var(--muted)', marginTop: 4 },
  rewrite: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 },
  editPanel: { background: 'var(--card)', border: '1px dashed #6366f1', borderRadius: 8, padding: 16, marginTop: 12 },
};
