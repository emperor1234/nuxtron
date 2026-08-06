'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SchemaMarkup = { type: string; json_ld: Record<string, unknown> };
type FaqPair = { question: string; answer: string };

type LandingPageResponse = {
  analysis_id: string;
  product_name: string;
  target_keyword: string;
  landing_page_score: number;
  hero: { headline: string; subheadline: string; cta: string };
  schema_markup: SchemaMarkup[];
  sections: string[];
  faq_pairs: FaqPair[];
  ab_test_variants: string[];
  seo_meta: { title: string; description: string; canonical: string };
  conversion_signals: string[];
  recommended_tools: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function LandingPageBuilderPage() {
  const [productName, setProductName] = useState('');
  const [targetKeyword, setTargetKeyword] = useState('');
  const [audience, setAudience] = useState('general');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<LandingPageResponse | null>(null);

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
  };

  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    boxSizing: 'border-box' as const,
  };

  async function generate() {
    if (!productName.trim() || !targetKeyword.trim()) {
      setError('Product name and target keyword are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<LandingPageResponse>(
        '/seo-platform/landing/generate',
        'POST',
        {
          product_name: productName.trim(),
          target_keyword: targetKeyword.trim(),
          audience,
          schema_types: ['Product', 'FAQPage'],
          notes: notes.trim(),
        },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Landing page generation failed.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <Link href={'/seo' as Route} style={{ color: 'var(--brand)', textDecoration: 'none', fontSize: 13 }}>
          ← Back to SEO Platform
        </Link>
        <h1 style={{ marginTop: 12, marginBottom: 6 }}>Landing Page Builder</h1>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 18 }}>
          Generate conversion-ready landing page briefs with JSON-LD schema, FAQ pairs, and A/B test variants.
        </p>

        <section style={{ ...card, marginBottom: 14, display: 'grid', gap: 10 }}>
          <div>
            <label htmlFor="lp-product" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Product / Brand Name <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="lp-product"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              style={input}
              placeholder="e.g. Nuxtron AI Platform"
            />
          </div>
          <div>
            <label htmlFor="lp-keyword" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Target Keyword <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="lp-keyword"
              value={targetKeyword}
              onChange={(e) => setTargetKeyword(e.target.value)}
              style={input}
              placeholder="e.g. AI-powered SEO platform"
            />
          </div>
          <div>
            <label htmlFor="lp-audience" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Target Audience
            </label>
            <input
              id="lp-audience"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              style={input}
              placeholder="e.g. marketing agencies, SaaS teams"
            />
          </div>
          <div>
            <label htmlFor="lp-notes" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
              Notes (optional)
            </label>
            <input
              id="lp-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={input}
              placeholder="Tone, USPs, competitors..."
            />
          </div>
          <button
            onClick={generate}
            disabled={loading}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Generating…' : 'Generate Landing Page Brief'}
          </button>
          {error && <div style={{ color: '#fca5a5', fontSize: 13 }}>{error}</div>}
        </section>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)', color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)' }}>
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.12)', color: '#38bdf8' }}>Cached result</span>
                )}
              </div>
            )}
            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, marginBottom: 6, fontSize: 15 }}>Hero Section</h2>
              <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 6 }}>{result.hero.headline}</div>
              <div style={{ color: 'var(--muted)', marginBottom: 10 }}>{result.hero.subheadline}</div>
              <span
                style={{
                  padding: '8px 20px',
                  borderRadius: 8,
                  background: 'var(--brand)',
                  color: '#00101e',
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                {result.hero.cta}
              </span>
            </section>

            <section style={{ ...card, marginBottom: 14 }}>
              <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>SEO Meta</h2>
              <div style={{ fontSize: 13, marginBottom: 4 }}>
                <strong>Title:</strong> {result.seo_meta.title}
              </div>
              <div style={{ fontSize: 13, marginBottom: 4 }}>
                <strong>Description:</strong> {result.seo_meta.description}
              </div>
              <div style={{ fontSize: 13 }}>
                <strong>Canonical:</strong> {result.seo_meta.canonical}
              </div>
            </section>

            {result.faq_pairs.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>FAQ Pairs ({result.faq_pairs.length})</h2>
                {result.faq_pairs.map((faq, i) => (
                  <div key={`item-${i}`} style={{ marginBottom: 10 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>Q: {faq.question}</div>
                    <div style={{ fontSize: 13, color: 'var(--muted)' }}>A: {faq.answer}</div>
                  </div>
                ))}
              </section>
            )}

            {result.ab_test_variants.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>A/B Test Variants</h2>
                {result.ab_test_variants.map((v, i) => (
                  <div key={`item-${i}`} style={{ ...card, marginBottom: 6, fontSize: 13 }}>
                    {v}
                  </div>
                ))}
              </section>
            )}

            {result.schema_markup.length > 0 && (
              <section style={{ ...card, marginBottom: 14 }}>
                <h2 style={{ marginTop: 0, marginBottom: 8, fontSize: 15 }}>Schema Markup Types</h2>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {result.schema_markup.map((s, i) => (
                    <span
                      key={`item-${i}`}
                      style={{
                        fontSize: 12,
                        borderRadius: 999,
                        padding: '4px 10px',
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                      }}
                    >
                      {s.type}
                    </span>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
