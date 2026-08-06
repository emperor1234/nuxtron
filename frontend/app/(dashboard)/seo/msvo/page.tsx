'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type MsvoSurfaceCoverage = {
  surface?: string;
  presence_score?: number;
  priority_action?: string;
};

type MsvoGap =
  | string
  | {
      channel?: string;
      gap_type?: string;
      fix?: string;
    };

type MsvoSequenceItem =
  | string
  | {
      step?: number;
      surface?: string;
      content?: string;
      timing?: string;
    };

type MsvoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  visibility_score?: number;
  surface_coverage?: MsvoSurfaceCoverage[];
  owned_channel_gaps?: MsvoGap[];
  message_alignment_score?: number;
  distribution_sequence?: MsvoSequenceItem[];
  next_actions?: Array<string | { action?: string; priority?: string }>;
  fallback?: boolean;
};

function formatGap(item: MsvoGap): string {
  if (typeof item === 'string') return item;
  const channel = item.channel ?? 'channel';
  const fix = item.fix ? ` — ${item.fix}` : '';
  return `${channel} (${item.gap_type ?? 'gap'})${fix}`;
}

function formatSequenceItem(item: MsvoSequenceItem): string {
  if (typeof item === 'string') return item;
  const surface = item.surface ?? 'surface';
  const timing = item.timing ? ` · ${item.timing}` : '';
  return `Step ${item.step ?? '?'}: ${surface}${timing}`;
}

export default function MsvoPage() {
  const [brand, setBrand] = useState('');
  const [topic, setTopic] = useState('');
  const [targetSurfaces, setTargetSurfaces] = useState('google, chatgpt, perplexity, linkedin');
  const [ownedChannels, setOwnedChannels] = useState('blog, email, linkedin');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<MsvoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!brand.trim() || !topic.trim()) {
      setError('Brand and topic are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<MsvoResult>(
        '/seo-platform/msvo/analyze',
        'POST',
        {
          brand: brand.trim(),
          topic: topic.trim(),
          target_surfaces: targetSurfaces
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          owned_channels: ownedChannels
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          notes: notes.trim(),
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }

      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'MSVO analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>MSVO</h1>
        <p style={{ color: 'var(--muted)' }}>
          Multi-surface visibility optimization across search, AI, and owned channels.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Brand</label>
          <input style={input} value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Nuxtron" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Topic</label>
          <input style={input} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="AI SEO platform" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Target Surfaces</label>
          <input
            style={input}
            value={targetSurfaces}
            onChange={(e) => setTargetSurfaces(e.target.value)}
            placeholder="google, chatgpt, perplexity, linkedin"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Owned Channels</label>
          <input
            style={input}
            value={ownedChannels}
            onChange={(e) => setOwnedChannels(e.target.value)}
            placeholder="blog, email, linkedin"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 90 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Message priorities, current gaps, launch sequencing"
          />

          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Mapping visibility...' : 'Analyze MSVO'}
          </button>
        </section>

        {result && (
          <>
            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Visibility Score</div>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{result.visibility_score ?? '--'}</div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (surface + channel signals)'}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Message Alignment</div>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{result.message_alignment_score ?? '--'}</div>
              </div>
            </section>

            {(result.surface_coverage ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Surface Coverage</h3>
                {(result.surface_coverage ?? []).map((item, index) => (
                  <div
                    key={`surface-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.surface_coverage ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.surface ?? '--'} · {item.presence_score ?? '--'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.priority_action ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.owned_channel_gaps ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Owned Channel Gaps</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.owned_channel_gaps ?? []).map((item, index) => (
                    <li key={`gap-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatGap(item)}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.distribution_sequence ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Distribution Sequence</h3>
                <ol style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.distribution_sequence ?? []).map((item, index) => (
                    <li key={`sequence-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatSequenceItem(item)}
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
