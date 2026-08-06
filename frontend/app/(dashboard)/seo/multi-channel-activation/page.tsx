'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type ChannelPlanItem = {
  channel?: string;
  objective?: string;
  primary_asset?: string;
  launch_window?: string;
  kpi?: string;
};

type AudienceMapItem = {
  segment?: string;
  channel?: string;
  offer?: string;
};

type MultiChannelActivationResult = {
  activation_readiness_score?: number;
  message_consistency_score?: number;
  channel_plan?: ChannelPlanItem[];
  audience_mapping?: AudienceMapItem[];
  activation_loop?: string[];
  distribution_risks?: string[];
  priority_actions?: string[];
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function MultiChannelActivationPage() {
  const [campaignName, setCampaignName] = useState('Q3 Demand Expansion');
  const [primaryOffer, setPrimaryOffer] = useState('SEO + AI Growth Blueprint');
  const [channels, setChannels] = useState('search, social, email, community');
  const [audienceSegments, setAudienceSegments] = useState('new_visitors, returning_users, product_eval');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<MultiChannelActivationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!campaignName.trim()) {
      setError('Campaign name is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<MultiChannelActivationResult>(
        '/seo-platform/multi-channel-activation/analyze',
        'POST',
        {
          campaign_name: campaignName.trim(),
          primary_offer: primaryOffer.trim(),
          channels: channels
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          audience_segments: audienceSegments
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          notes,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(IS_STRICT_NO_MOCK_MODE ? 'Live LLM backend is unavailable in strict no-mock mode.' : 'Live LLM backend is unavailable in fail-closed mode.');
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Multi-channel activation analysis failed');
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
        <h1 style={{ marginTop: 0 }}>Multi-Channel Activation Loop</h1>
        <p style={{ color: 'var(--muted)' }}>
          Activation and distribution across search, social, and lifecycle channels.
        </p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Campaign Name</label>
          <input
            style={input}
            value={campaignName}
            onChange={(e) => setCampaignName(e.target.value)}
            placeholder="Q3 Demand Expansion"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Primary Offer</label>
          <input
            style={input}
            value={primaryOffer}
            onChange={(e) => setPrimaryOffer(e.target.value)}
            placeholder="Offer to activate across channels"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Channels</label>
          <input
            style={input}
            value={channels}
            onChange={(e) => setChannels(e.target.value)}
            placeholder="search, social, email"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Audience Segments</label>
          <input
            style={input}
            value={audienceSegments}
            onChange={(e) => setAudienceSegments(e.target.value)}
            placeholder="new_visitors, returning_users"
          />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Notes</label>
          <textarea
            style={{ ...input, minHeight: 80 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Launch constraints, sequencing, dependencies"
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
            {loading ? 'Building activation plan...' : 'Analyze Activation Loop'}
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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Activation Readiness</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.activation_readiness_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Message Consistency</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.message_consistency_score ?? '--'}</div>
              </div>
            </section>

            {(result.channel_plan ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Channel Plan</h3>
                {(result.channel_plan ?? []).map((item, index) => (
                  <div
                    key={`channel-${index}`}
                    style={{
                      padding: '8px 0',
                      borderBottom: index < (result.channel_plan ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.channel ?? '--'} · {item.launch_window ?? 'planned'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.objective ?? ''}</div>
                    <div style={{ fontSize: 12 }}>
                      Asset: {item.primary_asset ?? '--'} · KPI: {item.kpi ?? '--'}
                    </div>
                  </div>
                ))}
              </section>
            )}

            {(result.audience_mapping ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Audience Mapping</h3>
                {(result.audience_mapping ?? []).map((item, index) => (
                  <div
                    key={`audience-${index}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
                      gap: 8,
                      fontSize: 12,
                      padding: '6px 0',
                      borderBottom:
                        index < (result.audience_mapping ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <span style={{ fontWeight: 700 }}>{item.segment ?? '--'}</span>
                    <span>{item.channel ?? '--'}</span>
                    <span style={{ color: 'var(--brand)' }}>{item.offer ?? '--'}</span>
                  </div>
                ))}
              </section>
            )}

            {(result.activation_loop ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Activation Loop</h3>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {(result.activation_loop ?? []).map((step, index) => (
                    <span
                      key={`step-${index}`}
                      style={{
                        fontSize: 11,
                        border: '1px solid var(--line)',
                        borderRadius: 999,
                        padding: '4px 10px',
                        background: 'var(--bg)',
                      }}
                    >
                      {step}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {(result.distribution_risks ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Distribution Risks</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.distribution_risks ?? []).map((item, index) => (
                    <li key={`risk-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.priority_actions ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Priority Actions</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.priority_actions ?? []).map((item, index) => (
                    <li key={`action-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
