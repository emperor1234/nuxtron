'use client';

import { useMemo, useState } from 'react';
import { OwlyWriterGeneration, OwlyWriterGeneratePayload, SocialNetwork, socialApi } from '@/app/lib/social-api';

const NETWORKS: SocialNetwork[] = ['linkedin', 'twitter', 'instagram', 'facebook', 'tiktok', 'youtube'];

const DEFAULT_PAYLOAD: OwlyWriterGeneratePayload = {
  topic: '',
  goal: 'engagement',
  style: 'professional',
  audience: 'SaaS founders',
  platforms: ['linkedin', 'twitter'],
  include_hashtags: true,
  include_emoji: true,
  include_cta: true,
  campaign_tag: '',
  destination_url: '',
  variations_per_platform: 3,
};

export default function OwlyWriterAiPage() {
  const [form, setForm] = useState<OwlyWriterGeneratePayload>(DEFAULT_PAYLOAD);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState<OwlyWriterGeneration | null>(null);

  const groupedItems = useMemo(() => {
    const groups: Record<string, OwlyWriterGeneration['items']> = {};
    for (const item of generation?.items || []) {
      if (!groups[item.platform]) groups[item.platform] = [];
      groups[item.platform].push(item);
    }
    return groups;
  }, [generation]);

  function togglePlatform(network: SocialNetwork): void {
    setForm((current) => {
      const exists = current.platforms.includes(network);
      const next = exists ? current.platforms.filter((p) => p !== network) : [...current.platforms, network];
      return { ...current, platforms: next };
    });
  }

  async function runGeneration(): Promise<void> {
    if (!form.topic.trim() || form.platforms.length === 0) {
      setError('Topic and at least one platform are required.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await socialApi.generateOwlyWriter({
        ...form,
        topic: form.topic.trim(),
        campaign_tag: form.campaign_tag?.trim() || undefined,
        destination_url: form.destination_url?.trim() || undefined,
      });
      setGeneration(result);
    } catch {
      setError('OwlyWriter generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">OwlyWriter AI</p>
        <h1>Generate platform-ready copy with quality scoring</h1>
        <p>
          Build campaign-grade captions tailored to each social network, then send the best variant into scheduling.
        </p>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginTop: 20 }}>
        <section className="card" style={{ padding: 18, height: 'fit-content' }}>
          <h3 style={{ marginTop: 0 }}>Generation Brief</h3>

          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 700 }}>Topic</label>
          <textarea
            value={form.topic}
            onChange={(event) => setForm((current) => ({ ...current, topic: event.target.value }))}
            placeholder="Launching our AI social scheduler for B2B teams"
            rows={3}
            style={{ width: '100%', borderRadius: 8, border: '1px solid var(--line)', padding: 10, marginBottom: 12 }}
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginBottom: 12 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 700 }}>Goal</label>
              <input
                value={form.goal}
                onChange={(event) => setForm((current) => ({ ...current, goal: event.target.value }))}
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--line)', padding: '8px 10px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 700 }}>Style</label>
              <select
                value={form.style}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    style: event.target.value as OwlyWriterGeneratePayload['style'],
                  }))
                }
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--line)', padding: '8px 10px' }}
              >
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="humorous">Humorous</option>
                <option value="inspirational">Inspirational</option>
              </select>
            </div>
          </div>

          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 700 }}>Audience</label>
          <input
            value={form.audience}
            onChange={(event) => setForm((current) => ({ ...current, audience: event.target.value }))}
            style={{
              width: '100%',
              borderRadius: 8,
              border: '1px solid var(--line)',
              padding: '8px 10px',
              marginBottom: 12,
            }}
          />

          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 700 }}>Platforms</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {NETWORKS.map((network) => {
              const active = form.platforms.includes(network);
              return (
                <button
                  key={network}
                  type="button"
                  onClick={() => togglePlatform(network)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: 999,
                    border: '1px solid var(--line)',
                    background: active ? 'var(--brand)' : 'transparent',
                    color: active ? '#00101e' : 'var(--text)',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {network}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10, marginBottom: 12 }}>
            <label style={{ fontSize: 12 }}>
              <input
                type="checkbox"
                checked={Boolean(form.include_hashtags)}
                onChange={(event) => setForm((current) => ({ ...current, include_hashtags: event.target.checked }))}
              />{' '}
              Include hashtags
            </label>
            <label style={{ fontSize: 12 }}>
              <input
                type="checkbox"
                checked={Boolean(form.include_cta)}
                onChange={(event) => setForm((current) => ({ ...current, include_cta: event.target.checked }))}
              />{' '}
              Include CTA
            </label>
            <label style={{ fontSize: 12 }}>
              <input
                type="checkbox"
                checked={Boolean(form.include_emoji)}
                onChange={(event) => setForm((current) => ({ ...current, include_emoji: event.target.checked }))}
              />{' '}
              Include emoji
            </label>
            <label style={{ fontSize: 12 }}>
              Variations per platform
              <input
                type="number"
                min={1}
                max={5}
                value={form.variations_per_platform || 3}
                onChange={(event) =>
                  setForm((current) => ({ ...current, variations_per_platform: Number(event.target.value) || 1 }))
                }
                style={{
                  width: '100%',
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  padding: '6px 8px',
                  marginTop: 4,
                }}
              />
            </label>
          </div>

          <button
            onClick={() => void runGeneration()}
            disabled={loading}
            style={{
              width: '100%',
              border: 'none',
              borderRadius: 8,
              padding: '10px 12px',
              background: loading ? 'var(--muted)' : 'var(--brand)',
              color: '#00101e',
              fontWeight: 800,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Generating...' : 'Generate with OwlyWriter AI'}
          </button>

          {error && <p style={{ color: '#f44', marginTop: 10, fontSize: 12 }}>{error}</p>}
        </section>

        <section className="card" style={{ padding: 18 }}>
          <h3 style={{ marginTop: 0 }}>Output</h3>
          {!generation ? (
            <p style={{ color: 'var(--muted)' }}>Run generation to view platform-specific copy and quality scores.</p>
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                Generation ID: {generation.id} · Provider: {generation.provider} · Created:{' '}
                {new Date(generation.generated_at).toLocaleString()}
              </div>
              {Object.entries(groupedItems).map(([platform, items]) => (
                <div key={platform} style={{ border: '1px solid var(--line)', borderRadius: 10, padding: 12 }}>
                  <h4 style={{ margin: '0 0 10px', textTransform: 'capitalize' }}>{platform}</h4>
                  <div style={{ display: 'grid', gap: 10 }}>
                    {items.map((item) => (
                      <article
                        key={item.variation_id}
                        style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: 10 }}
                      >
                        <div
                          style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12 }}
                        >
                          <strong>{item.variation_id}</strong>
                          <span>Quality {item.quality.overall}%</span>
                        </div>
                        <p style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>{item.caption}</p>
                      </article>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
