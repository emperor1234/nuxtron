'use client';

import Link from 'next/link';
import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type RepurposedOutput = {
  format: string;
  title: string;
  summary: string;
};

type RepurposeResult = {
  outputs: RepurposedOutput[];
  hours_saved: number;
};

const PLATFORMS = ['linkedin', 'x', 'instagram', 'threads', 'tiktok', 'facebook', 'youtube', 'reddit'];
const FORMAT_ICONS: Record<string, string> = {
  thread: '🧵',
  carousel: '🖼️',
  newsletter: '📧',
  podcast_script: '🎙️',
  faq: '❓',
  press_release: '📰',
  video_script: '🎬',
  reddit_post: '🔴',
  quote_cards: '💬',
  case_study: '📋',
  landing_page: '🌐',
  sales_email: '📨',
  drip_email: '📮',
  webinar_outline: '🎤',
  community_post: '👥',
  founder_note: '✍️',
  ad_copy: '📢',
  lead_magnet: '🧲',
  sms_teaser: '📱',
  comment_replies: '💭',
};

export default function RepurposePage() {
  const [sourceContent, setSourceContent] = useState(
    'Lately.ai built a neuroscience-driven AI that analyses engagement patterns from social posts and uses them to repurpose longform content into dozens of platform-optimised posts. The result: 84% less writing time, 200% more leads, and 12,000% more engagement for their customers.'
  );
  const [result, setResult] = useState<RepurposeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFormats, setSelectedFormats] = useState<Set<string>>(new Set());
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  async function repurpose() {
    if (sourceContent.trim().length < 20) {
      setError('Please paste at least 20 characters of source content.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiSend<{ repurpose?: RepurposeResult }>(
        '/content/repurpose',
        'POST',
        { source_content: sourceContent },
        DEFAULT_TENANT_ID
      );
      setResult(res.repurpose ?? null);
      setSelectedFormats(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Repurpose failed');
    } finally {
      setLoading(false);
    }
  }

  function toggleFormat(fmt: string) {
    setSelectedFormats((prev) => {
      const next = new Set(prev);
      if (next.has(fmt)) next.delete(fmt);
      else next.add(fmt);
      return next;
    });
  }

  function copyText(text: string, idx: number) {
    void navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1800);
  }

  let displayedOutputs: RepurposedOutput[] = [];
  if (result) {
    displayedOutputs = selectedFormats.size > 0
      ? result.outputs.filter((o) => selectedFormats.has(o.format))
      : result.outputs;
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>Longform Content Repurposer</h1>
        <p style={s.subtitle}>
          Paste any blog post, podcast transcript, video script, press release, or white paper. The AI atomises it into
          up to 20 pre-tested social media formats — threads, carousels, newsletters, video scripts, ad copy, and more.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      <section style={s.card}>
        <h2 style={s.sectionTitle}>Source Content</h2>
        <p style={s.hint}>
          Works with: blog posts · podcast transcripts · press releases · webinar outlines · white papers · case studies
        </p>
        <textarea
          value={sourceContent}
          onChange={(e) => setSourceContent(e.target.value)}
          style={s.textarea}
          placeholder="Paste your longform content here (min 20 chars)…"
          rows={8}
        />
        <div style={s.metaRow}>
          <span style={s.charCount}>{sourceContent.length} chars</span>
          <button onClick={repurpose} disabled={loading} style={s.btn}>
            {loading ? 'Repurposing…' : '♻️ Repurpose into 20 Formats'}
          </button>
        </div>
      </section>

      {result ? (
        <>
          <div style={s.statsRow}>
            <div style={s.statChip}>📦 {result.outputs.length} formats generated</div>
            <div style={s.statChip}>⏱ {result.hours_saved} hours saved</div>
            <div style={s.statChip}>📱 {PLATFORMS.length} platforms covered</div>
          </div>

          {/* Format filter */}
          <div style={s.filterRow}>
            <span style={s.filterLabel}>Filter by format:</span>
            {result.outputs.map((o) => (
              <button
                key={o.format}
                onClick={() => toggleFormat(o.format)}
                style={{
                  ...s.filterChip,
                  ...(selectedFormats.has(o.format) ? s.filterChipActive : {}),
                }}
              >
                {FORMAT_ICONS[o.format] ?? '📄'} {o.format.replaceAll('_', ' ')}
              </button>
            ))}
            {selectedFormats.size > 0 ? (
              <button onClick={() => setSelectedFormats(new Set())} style={s.clearBtn}>
                Clear filter
              </button>
            ) : null}
          </div>

          <div style={s.outputGrid}>
            {displayedOutputs.map((output, idx) => (
              <div key={output.format} style={s.outputCard}>
                <div style={s.outputHeader}>
                  <span style={s.outputIcon}>{FORMAT_ICONS[output.format] ?? '📄'}</span>
                  <span style={s.outputFormat}>{output.format.replaceAll('_', ' ')}</span>
                  <button
                    onClick={() => copyText(output.summary, idx)}
                    style={s.copyBtn}
                    title="Copy to clipboard"
                  >
                    {copiedIdx === idx ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
                <div style={s.outputTitle}>{output.title}</div>
                <div style={s.outputBody}>{output.summary}</div>
                <div style={s.platformRow}>
                  {PLATFORMS.slice(0, 3).map((p) => (
                    <span key={p} style={s.platformBadge}>{p}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { maxWidth: 1100, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 32 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 28, fontWeight: 800, margin: '10px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 14, color: 'var(--muted)', maxWidth: 720 },
  errorBanner: { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8, padding: '10px 14px', color: '#dc2626', marginBottom: 20, fontSize: 13 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 24 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: '0 0 8px', color: 'var(--text)' },
  hint: { fontSize: 12, color: 'var(--muted)', marginBottom: 12 },
  textarea: { width: '100%', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '10px 14px', color: 'var(--text)', fontSize: 13, lineHeight: 1.6, boxSizing: 'border-box' as const, resize: 'vertical' as const },
  metaRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 },
  charCount: { fontSize: 12, color: 'var(--muted)' },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  statsRow: { display: 'flex', gap: 12, marginBottom: 20 },
  statChip: { background: 'rgba(99,102,241,0.12)', color: 'var(--brand)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, padding: '6px 14px', fontSize: 13, fontWeight: 600 },
  filterRow: { display: 'flex', flexWrap: 'wrap' as const, gap: 6, marginBottom: 20, alignItems: 'center' },
  filterLabel: { fontSize: 12, color: 'var(--muted)', marginRight: 4 },
  filterChip: { background: 'var(--card)', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 16, padding: '4px 10px', cursor: 'pointer', fontSize: 12 },
  filterChipActive: { background: 'rgba(99,102,241,0.2)', color: 'var(--brand)', borderColor: '#6366f1' },
  clearBtn: { background: 'transparent', color: '#dc2626', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 16, padding: '4px 10px', cursor: 'pointer', fontSize: 12 },
  outputGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: 16 },
  outputCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 16 },
  outputHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 },
  outputIcon: { fontSize: 20 },
  outputFormat: { fontSize: 13, fontWeight: 600, color: 'var(--brand)', flex: 1 },
  copyBtn: { background: 'transparent', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 6, padding: '2px 8px', cursor: 'pointer', fontSize: 11 },
  outputTitle: { fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 6 },
  outputBody: { fontSize: 12, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 10 },
  platformRow: { display: 'flex', gap: 4 },
  platformBadge: { fontSize: 10, background: 'var(--card)', color: 'var(--muted)', borderRadius: 4, padding: '1px 6px', border: '1px solid var(--line)' },
};
