'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

export default function SeoAnalysisPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [url, setUrl] = useState('https://example.com');
  const [keyword, setKeyword] = useState('marketing automation platform');
  const [content, setContent] = useState(
    'Nuxtron helps teams automate social scheduling, CRM, and intelligence workflows.'
  );
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  async function run() {
    try {
      setError('');
      const data = await apiSend<Record<string, unknown>>(
        '/seo/analyze',
        'POST',
        {
          url,
          target_keyword: keyword,
          content,
        },
        tenantId
      );
      setResult(JSON.stringify(data, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'SEO analysis failed');
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
        <h1 style={{ marginTop: 0 }}>AI SEO Analysis</h1>
        <p style={{ color: 'var(--muted)' }}>
          Run keyword and content optimization analysis against your URL and page copy.
        </p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}
        <section style={card}>
          <input style={input} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="url" />
          <input
            style={input}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="target keyword"
          />
          <textarea style={{ ...input, minHeight: 120 }} value={content} onChange={(e) => setContent(e.target.value)} />
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
            Analyze SEO
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
