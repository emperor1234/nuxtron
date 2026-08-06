'use client';

import { useMemo, useState } from 'react';
import { apiPost, DEFAULT_TENANT_ID } from '../lib/api-client';

type WorkspaceMode = 'social' | 'ads' | 'seo';

type FeatureItem = {
  id: string;
  title: string;
  summary: string;
  tools: string[];
};

const SOCIAL_FEATURES: FeatureItem[] = [
  {
    id: 'image-gen',
    title: 'AI Image Studio',
    summary: 'Generate from prompt or image upload, then refine with editor controls.',
    tools: ['Prompt to image', 'Magic brush', 'Remove background', 'Masking', 'Hue/brightness', 'Typography tools'],
  },
  {
    id: 'video-gen',
    title: 'AI Video Studio',
    summary: 'Generate, re-style, and edit long or short form video from prompts and references.',
    tools: ['Prompt to video', 'Sample upload', 'Timeline editor', 'Scene trim', 'Subtitles', 'Lighting control'],
  },
  {
    id: 'voice-gen',
    title: 'AI Voice Studio',
    summary: 'Create voiceovers, clone style from sample, and apply advanced audio edits.',
    tools: ['Prompt to voice', 'Sample upload', 'Voice styles', 'Celebrity-like tone mapping', 'EQ and cleanup'],
  },
  {
    id: 'text-gen',
    title: 'AI Copy And Blog Studio',
    summary: 'Generate blogs, captions, scripts, and emails from prompts or files.',
    tools: ['Prompt editor', 'Upload image/PDF context', 'Long-form generation', 'SEO scoring', 'Inline rewrite'],
  },
];

const ADS_FEATURES: FeatureItem[] = [
  {
    id: 'ad-creative',
    title: 'AI Ad Creative Engine',
    summary: 'Produce social and search ad variations with brand-safe messaging.',
    tools: ['Creative matrix', 'Angle testing', 'Platform formatting', 'CTA optimizer'],
  },
  {
    id: 'ad-audience',
    title: 'Audience And Offer Builder',
    summary: 'Define segments and offer mapping for paid campaigns.',
    tools: ['Persona builder', 'Offer ladder', 'Intent scoring', 'Lookalike-ready exports'],
  },
  {
    id: 'ad-budget',
    title: 'Budget Autopilot',
    summary: 'Auto-shift spend to top-performing campaigns by objective.',
    tools: ['ROAS monitor', 'CAC guardrails', 'Bid strategy suggestions', 'Daily pacing'],
  },
];

const SEO_FEATURES: FeatureItem[] = [
  {
    id: 'seo-cluster',
    title: 'Topic Cluster Planner',
    summary: 'Build authority maps and content clusters from core keywords.',
    tools: ['Cluster map', 'SERP intent tagging', 'Priority queue', 'Difficulty overlays'],
  },
  {
    id: 'seo-onpage',
    title: 'On-Page Optimizer',
    summary: 'Optimize titles, metadata, schema, and semantic structure.',
    tools: ['Meta generator', 'Schema assistant', 'Internal link assistant', 'Readability tuning'],
  },
  {
    id: 'seo-technical',
    title: 'Technical SEO Monitor',
    summary: 'Track indexability, speed, structured data, and crawl issues.',
    tools: ['Core web vitals', 'Crawl diagnostics', 'Canonical checks', 'Health alerts'],
  },
];

function featuresFor(mode: WorkspaceMode): FeatureItem[] {
  if (mode === 'social') return SOCIAL_FEATURES;
  if (mode === 'ads') return ADS_FEATURES;
  return SEO_FEATURES;
}

export default function AutonomousWorkspace() {
  const [mode, setMode] = useState<WorkspaceMode>('social');
  const features = useMemo(() => featuresFor(mode), [mode]);
  const [activeFeature, setActiveFeature] = useState(features[0]?.id || '');
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [prompt, setPrompt] = useState('Generate a growth campaign plan for Q2 with strong conversion hooks.');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const selected = useMemo(
    () => features.find((feature) => feature.id === activeFeature) || features[0],
    [features, activeFeature]
  );

  async function generate() {
    setLoading(true);
    setError('');
    try {
      if (mode === 'social') {
        const data = await apiPost(
          '/content/generate',
          {
            topic: prompt,
            audience: 'growth teams',
            channel: 'linkedin',
            tone: 'professional',
            include_seo: true,
          },
          tenantId
        );
        setResult(data);
      } else if (mode === 'ads') {
        const data = await apiPost(
          '/ads/generate',
          {
            product: 'Nuxtron AI platform',
            audience: 'marketing teams',
            platform: 'google',
            objective: prompt,
          },
          tenantId
        );
        setResult(data);
      } else {
        const data = await apiPost(
          '/seo/analyze',
          {
            target_keyword: 'autonomous ai growth platform',
            content: prompt,
          },
          tenantId
        );
        setResult(data);
      }
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Generation failed.');
    } finally {
      setLoading(false);
    }
  }

  async function optimize() {
    setLoading(true);
    setError('');
    try {
      const data = await apiPost(
        '/seo/analyze',
        {
          target_keyword: mode === 'ads' ? 'paid media optimization' : 'organic growth strategy',
          content: prompt,
        },
        tenantId
      );
      setResult(data);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Optimization failed.');
    } finally {
      setLoading(false);
    }
  }

  async function publish() {
    setLoading(true);
    setError('');
    try {
      const data = await apiPost(
        '/social/schedule',
        {
          platform: 'linkedin',
          text: prompt,
          publish_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          media_urls: [],
        },
        tenantId
      );
      setResult(data);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Publishing failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="workspace-shell" aria-label="Autonomous dashboard workspace">
      <header className="workspace-top-nav">
        <button
          className={mode === 'social' ? 'active' : ''}
          onClick={() => {
            setMode('social');
            setActiveFeature(SOCIAL_FEATURES[0].id);
          }}
        >
          AI Autonomous Social Media
        </button>
        <button
          className={mode === 'ads' ? 'active' : ''}
          onClick={() => {
            setMode('ads');
            setActiveFeature(ADS_FEATURES[0].id);
          }}
        >
          AI Autonomous Ads
        </button>
        <button
          className={mode === 'seo' ? 'active' : ''}
          onClick={() => {
            setMode('seo');
            setActiveFeature(SEO_FEATURES[0].id);
          }}
        >
          AI Autonomous SEO
        </button>
      </header>

      <div className="workspace-grid">
        <aside className="workspace-side-nav">
          <h3>{mode.toUpperCase()} Features</h3>
          {features.map((feature) => (
            <button
              key={feature.id}
              className={activeFeature === feature.id ? 'active' : ''}
              onClick={() => setActiveFeature(feature.id)}
            >
              {feature.title}
            </button>
          ))}
        </aside>

        <article className="workspace-main">
          <h2>{selected?.title}</h2>
          <p>{selected?.summary}</p>

          <div className="workspace-io-grid">
            <div>
              <label htmlFor="workspace-tenant">Tenant ID</label>
              <input id="workspace-tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
              <label htmlFor="workspace-prompt">Prompt</label>
              <textarea
                id="workspace-prompt"
                rows={6}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Describe exactly what you want IRA to generate."
              />
            </div>
            <div>
              <label htmlFor="workspace-upload">Reference Upload</label>
              <input id="workspace-upload" type="file" multiple />
              <p className="muted">Upload sample images, videos, voice clips, PDF briefs, or product docs.</p>
            </div>
          </div>

          <div className="workspace-tools">
            {selected?.tools.map((tool) => (
              <span key={tool}>{tool}</span>
            ))}
          </div>

          <div className="workspace-actions">
            <button onClick={generate} disabled={loading}>
              {loading ? 'Working...' : 'Generate'}
            </button>
            <button onClick={optimize} disabled={loading}>
              Optimize
            </button>
            <button onClick={publish} disabled={loading}>
              Publish
            </button>
          </div>
          {error ? <p className="auth-errors">{error}</p> : null}
          {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
        </article>
      </div>
    </section>
  );
}
