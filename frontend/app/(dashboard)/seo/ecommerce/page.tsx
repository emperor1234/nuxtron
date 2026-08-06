'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type EcommerceResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  seo_score?: number;
  ecommerce_score?: number;
  optimized_title?: string;
  optimized_description?: string;
  bullet_points?: string[];
  category_keywords?: string[];
  product_schema?: Record<string, unknown>;
  review_schema_eligible?: boolean;
  recommendations?: string[];
};

export default function EcommerceSEOPage() {
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [keywords, setKeywords] = useState('');
  const [result, setResult] = useState<EcommerceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!productName) {
      setError('Product name is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<EcommerceResult>(
        '/seo-platform/ecommerce/optimize',
        'POST',
        {
          product_name: productName,
          category,
          description,
          keywords: keywords
            .split(',')
            .map((k) => k.trim())
            .filter(Boolean),
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
      setError(e instanceof Error ? e.message : 'eCommerce SEO failed');
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
  const inp = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };
  const bullets = result?.bullet_points;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>eCommerce SEO</h1>
        <p style={{ color: 'var(--muted)' }}>
          Optimize product titles, bullet points, descriptions, and Product Schema for maximum visibility.
        </p>
        {error && <div style={{ ...card, color: '#dc2626' }}>{error}</div>}
        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Product Name</label>
              <input
                style={inp}
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Wireless Noise-Cancelling Headphones"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Category</label>
              <input
                style={inp}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g. Electronics / Audio"
              />
            </div>
          </div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Target Keywords (comma-separated)
          </label>
          <input
            style={inp}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="wireless headphones, noise cancelling, bluetooth"
          />
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Current Description (optional)
          </label>
          <textarea
            style={{ ...inp, minHeight: 120 }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Paste current product description..."
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
            {loading ? 'Optimizing product…' : 'Optimize eCommerce SEO'}
          </button>
        </section>
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
            ⏳ AI is optimizing your product SEO — this typically takes 20–40 s on local inference. Please wait…
          </div>
        )}
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

            <section style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>SEO Score</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#22c55e' }}>
                  {result.seo_score ?? result.ecommerce_score ?? '—'}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Review Schema Eligible</div>
                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 800,
                    color: result.review_schema_eligible ? '#22c55e' : '#94a3b8',
                  }}
                >
                  {result.review_schema_eligible ? '✓ Yes' : '— No'}
                </div>
              </div>
            </section>
            <section style={card}>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Optimized Title</div>
              <strong style={{ fontSize: 15, display: 'block', marginBottom: 14 }}>
                {result.optimized_title}
              </strong>
              {bullets && bullets.length > 0 && (
                <>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>Bullet Points</div>
                  <ul style={{ margin: '0 0 12px', paddingLeft: 18 }}>
                    {bullets.map((b, i) => (
                      <li key={`item-${i}`} style={{ fontSize: 13, marginBottom: 4 }}>
                        {b}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {result.optimized_description && (
                <>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>Optimized Description</div>
                  <div
                    style={{
                      background: 'var(--bg)',
                      borderRadius: 8,
                      padding: 12,
                      fontSize: 13,
                      lineHeight: 1.6,
                      border: '1px solid var(--line)',
                      marginBottom: 12,
                    }}
                  >
                    {result.optimized_description}
                  </div>
                </>
              )}
            </section>
            {result.category_keywords?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 10 }}>🏷️ Category Keywords</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {result.category_keywords.map((k) => (
                    <span
                      key={`item-${k}`}
                      style={{
                        fontSize: 12,
                        padding: '4px 12px',
                        background: 'rgba(167,139,250,0.1)',
                        border: '1px solid rgba(167,139,250,0.3)',
                        borderRadius: 99,
                        color: '#a78bfa',
                      }}
                    >
                      {k}
                    </span>
                  ))}
                </div>
              </section>
            ) : null}
            {result.product_schema && (
              <section style={card}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Product Schema (JSON-LD)</div>
                <pre
                  style={{
                    fontSize: 11,
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: 12,
                    border: '1px solid var(--line)',
                    overflowX: 'auto',
                    maxHeight: 240,
                    margin: 0,
                    color: 'var(--muted)',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {JSON.stringify(result.product_schema, null, 2)}
                </pre>
              </section>
            )}
            {result.recommendations?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>🚀 Recommendations</p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {result.recommendations.map((r, i) => (
                    <li key={`item-${i}`} style={{ fontSize: 13, marginBottom: 8 }}>
                      {r}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>
              Analysis ID: {result.analysis_id}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
