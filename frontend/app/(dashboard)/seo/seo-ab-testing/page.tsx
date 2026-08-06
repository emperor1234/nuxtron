'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SeoAbVariant = {
  variant?: string;
  expected_lift_pct?: number;
  rationale?: string;
};

type SeoAbDesign = {
  traffic_split?: string;
  sample_size_estimate?: number;
  guardrail_metrics?: string[];
};

type SeoAbTestingResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  experiment_readiness_score?: number;
  test_design?: SeoAbDesign;
  variant_recommendations?: SeoAbVariant[];
  measurement_plan?: string[];
  risk_flags?: string[];
};

export default function SeoAbTestingPage() {
  const [url, setUrl] = useState('');
  const [hypothesis, setHypothesis] = useState(
    'A clearer hero message and CTA hierarchy will improve conversion rate from organic sessions.'
  );
  const [primaryMetric, setPrimaryMetric] = useState('conversion_rate');
  const [variantA, setVariantA] = useState('Current headline and CTA placement.');
  const [variantB, setVariantB] = useState('Intent-focused headline with proof-point subhead and above-the-fold CTA.');
  const [testDurationDays, setTestDurationDays] = useState(21);
  const [notes, setNotes] = useState('Guardrail metrics include bounce rate and indexation stability.');
  const [featureFlagProvider, setFeatureFlagProvider] = useState('posthog');
  const [experimentPlatform, setExperimentPlatform] = useState('posthog');
  const [aiAnalystModel, setAiAnalystModel] = useState('llama3');

  const [result, setResult] = useState<SeoAbTestingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!url.trim() || !hypothesis.trim() || !variantA.trim() || !variantB.trim()) {
      setError('URL, hypothesis, and both variants are required.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await apiSend<SeoAbTestingResult>(
        '/seo-platform/seo-ab-testing/analyze',
        'POST',
        {
          url: url.trim(),
          hypothesis: hypothesis.trim(),
          primary_metric: primaryMetric.trim(),
          variant_a: variantA.trim(),
          variant_b: variantB.trim(),
          test_duration_days: testDurationDays,
          notes: notes.trim(),
          feature_flag_provider: featureFlagProvider.trim(),
          experiment_platform: experimentPlatform.trim(),
          ai_analyst_model: aiAnalystModel.trim(),
          variant_payloads: [
            { key: 'A', label: 'control', content: variantA.trim() },
            { key: 'B', label: 'treatment', content: variantB.trim() },
          ],
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
      setError(e instanceof Error ? e.message : 'SEO A/B testing analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  const card = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(99, 102, 241, 0.65)',
  };
  const input = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid rgba(129,140,248,0.35)',
            background:
              'var(--card)',
            padding: '22px 24px',
            marginBottom: 20,
          }}
        >
          <div style={{ display: 'inline-flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--brand)',
                border: '1px solid rgba(165,180,252,0.45)',
                borderRadius: 999,
                padding: '3px 10px',
                background: 'rgba(129,140,248,0.16)',
              }}
            >
              Experiment Design Lab
            </span>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--muted)',
                border: '1px solid rgba(148,163,184,0.3)',
                borderRadius: 999,
                padding: '3px 10px',
                background: 'rgba(148,163,184,0.12)',
              }}
            >
              SEO + UX Statistical Testing
            </span>
          </div>
          <h1 style={{ marginTop: 0, marginBottom: 4, fontSize: 30, fontWeight: 800, color: 'var(--text)' }}>
            SEO A/B Testing
          </h1>
          <p style={{ color: 'var(--muted)', margin: 0 }}>Statistical testing and guardrails for SEO and UX variants.</p>
        </section>

        {error && <div style={{ ...card, color: '#b91c1c' }}>{error}</div>}

        <form style={card} onSubmit={handleSubmit}>
          <label htmlFor="seo-ab-url" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            URL
          </label>
          <input
            id="seo-ab-url"
            style={input}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/pricing"
          />

          <label
            htmlFor="seo-ab-hypothesis"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Hypothesis
          </label>
          <textarea
            id="seo-ab-hypothesis"
            style={{ ...input, minHeight: 70 }}
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            placeholder="What are you testing and why?"
          />

          <label
            htmlFor="seo-ab-primary-metric"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Primary Metric
          </label>
          <input
            id="seo-ab-primary-metric"
            style={input}
            value={primaryMetric}
            onChange={(e) => setPrimaryMetric(e.target.value)}
            placeholder="conversion_rate"
          />

          <label
            htmlFor="seo-ab-variant-a"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Variant A
          </label>
          <textarea
            id="seo-ab-variant-a"
            style={{ ...input, minHeight: 70 }}
            value={variantA}
            onChange={(e) => setVariantA(e.target.value)}
            placeholder="Describe control variant"
          />

          <label
            htmlFor="seo-ab-variant-b"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Variant B
          </label>
          <textarea
            id="seo-ab-variant-b"
            style={{ ...input, minHeight: 70 }}
            value={variantB}
            onChange={(e) => setVariantB(e.target.value)}
            placeholder="Describe treatment variant"
          />

          <label htmlFor="seo-ab-duration" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Test Duration (days)
          </label>
          <input
            id="seo-ab-duration"
            type="number"
            min={7}
            max={90}
            style={{ ...input, width: 180 }}
            value={testDurationDays}
            onChange={(e) => setTestDurationDays(Number(e.target.value || 21))}
          />

          <label
            htmlFor="seo-ab-feature-flag-provider"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Feature Flag Provider
          </label>
          <input
            id="seo-ab-feature-flag-provider"
            style={{ ...input, maxWidth: 280 }}
            value={featureFlagProvider}
            onChange={(e) => setFeatureFlagProvider(e.target.value)}
            placeholder="posthog"
          />

          <label
            htmlFor="seo-ab-experiment-platform"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Experiment Platform
          </label>
          <input
            id="seo-ab-experiment-platform"
            style={{ ...input, maxWidth: 280 }}
            value={experimentPlatform}
            onChange={(e) => setExperimentPlatform(e.target.value)}
            placeholder="posthog"
          />

          <label htmlFor="seo-ab-ai-model" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            AI Analyst Model
          </label>
          <input
            id="seo-ab-ai-model"
            style={{ ...input, maxWidth: 280 }}
            value={aiAnalystModel}
            onChange={(e) => setAiAnalystModel(e.target.value)}
            placeholder="llama3"
          />

          <label htmlFor="seo-ab-notes" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Notes
          </label>
          <textarea
            id="seo-ab-notes"
            style={{ ...input, minHeight: 70 }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any constraints, rollout notes, or guardrails"
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: 10,
              border: '1px solid rgba(165,180,252,0.45)',
              background: 'linear-gradient(90deg, rgba(99,102,241,0.9) 0%, rgba(6,182,212,0.85) 100%)',
              color: 'var(--brand)',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Designing experiment...' : 'Generate SEO A/B Test Plan'}
          </button>
          {loading && (
            <div
              style={{
                marginTop: 12,
                padding: '10px 14px',
                borderRadius: 8,
                background: 'rgba(27,199,255,0.08)',
                border: '1px solid rgba(27,199,255,0.2)',
                fontSize: 13,
                color: 'var(--muted)',
              }}
            >
              AI is designing your test plan and guardrails. This may take 20-40 s.
            </div>
          )}
        </form>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background:
                        result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: 'rgba(56,189,248,0.12)',
                      color: '#38bdf8',
                    }}
                  >
                    Cached result
                  </span>
                )}
              </div>
            )}

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
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Experiment Readiness</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.experiment_readiness_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Traffic Split</div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{result.test_design?.traffic_split ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Sample Size Estimate</div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{result.test_design?.sample_size_estimate ?? '--'}</div>
              </div>
            </section>

            {(result.variant_recommendations ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Variant Recommendations</h3>
                {(result.variant_recommendations ?? []).map((item) => (
                  <div
                    key={`${item.variant ?? 'variant'}-${item.rationale ?? 'rationale'}`}
                    style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      Variant {item.variant ?? '--'} · Expected lift {item.expected_lift_pct ?? 0}%
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.rationale ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.measurement_plan ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Measurement Plan</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.measurement_plan ?? []).map((item) => (
                    <li key={item} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.risk_flags ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Risk Flags</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.risk_flags ?? []).map((item) => (
                    <li key={item} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
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
