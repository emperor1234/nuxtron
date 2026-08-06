'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

export default function AdsGenerationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [product, setProduct] = useState('Nuxtron Growth Suite');
  const [audience, setAudience] = useState('SaaS founders');
  const [platform, setPlatform] = useState('linkedin');
  const [objective, setObjective] = useState('leads');
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  async function run() {
    try {
      setError('');
      const data = await apiSend<Record<string, unknown>>(
        '/ads/generate',
        'POST',
        {
          product,
          audience,
          platform,
          objective,
        },
        tenantId
      );
      setResult(JSON.stringify(data, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ads generation failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>AI Ads Generation</h1>
        <p style={{ color: 'var(--muted)' }}>Generate ad creatives and copy variants for each acquisition channel.</p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}
        <section style={card}>
          <input style={input} value={product} onChange={(e) => setProduct(e.target.value)} placeholder="product" />
          <input style={input} value={audience} onChange={(e) => setAudience(e.target.value)} placeholder="audience" />
          <select style={input} value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="google">google</option>
            <option value="meta">meta</option>
            <option value="linkedin">linkedin</option>
            <option value="tiktok">tiktok</option>
            <option value="facebook">facebook</option>
            <option value="x">x</option>
          </select>
          <select style={input} value={objective} onChange={(e) => setObjective(e.target.value)}>
            <option value="traffic">traffic</option>
            <option value="leads">leads</option>
            <option value="sales">sales</option>
            <option value="awareness">awareness</option>
          </select>
          <button
            onClick={() => void run()}
            style={{
              padding: '8px 12px',
              border: 'none',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
            }}
          >
            Generate Ads
          </button>
        </section>
        {result && (
          <pre
            style={{ ...card, marginTop: 10, color: 'var(--muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {result}
          </pre>
        )}
      </div>
    </main>
  );
}
