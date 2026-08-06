'use client';

import { useState } from 'react';

export default function SEOSuitePage() {
  const [topics, setTopics] = useState<
    Array<{ id: string; keyword: string; volume: number; difficulty: number; status: string }>
  >([]);
  const [newKeyword, setNewKeyword] = useState('');

  function addKeyword() {
    if (!newKeyword.trim()) return;
    setTopics([
      {
        id: Date.now().toString(),
        keyword: newKeyword,
        volume: Math.floor(Math.random() * 50000),
        difficulty: Math.floor(Math.random() * 100),
        status: 'analyzing',
      },
      ...topics,
    ]);
    setNewKeyword('');
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">AI SEO Suite</p>
        <h1>Topic Clustering & On-Page Optimization</h1>
        <p>Technical SEO monitoring, content clustering, and ranking optimization powered by AI.</p>
        <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
          <a
            href="/seo"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '8px 12px',
              borderRadius: 8,
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              textDecoration: 'none',
            }}
          >
            Open Full SEO Platform
          </a>
          <a
            href="/seo/history"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '8px 12px',
              borderRadius: 8,
              border: '1px solid var(--line)',
              background: 'var(--bg-soft)',
              color: 'var(--text)',
              fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            View Analysis History
          </a>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginTop: 20 }}>
        <section className="card" style={{ height: 'fit-content', padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Keyword Research</h3>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Target Keyword</label>
            <input
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addKeyword()}
              placeholder="e.g., AI content generation"
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>

          <button
            onClick={() => addKeyword()}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              marginBottom: 12,
            }}
          >
            Analyze
          </button>

          <div style={{ padding: 10, background: 'rgba(27, 199, 255, 0.1)', borderRadius: 8, fontSize: 12 }}>
            <strong>Tools:</strong>
            <ul style={{ margin: '8px 0 0', paddingLeft: 16 }}>
              <li>Keyword intent analysis</li>
              <li>Topic clustering</li>
              <li>SERP analysis</li>
              <li>Backlink opportunities</li>
              <li>Technical audits</li>
            </ul>
          </div>
        </section>

        <section className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Keyword Opportunities ({topics.length})</h3>

          {topics.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>Add keywords to analyze SEO potential.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {topics.map((topic) => (
                <div
                  key={topic.id}
                  style={{
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: 12,
                    background: 'rgba(255, 255, 255, 0.03)',
                  }}
                >
                  <strong>{topic.keyword}</strong>
                  <div
                    style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 8, marginTop: 8, fontSize: 12 }}
                  >
                    <div>
                      <span style={{ color: 'var(--muted)' }}>Volume</span>
                      <p style={{ margin: 0 }}>{topic.volume.toLocaleString()}</p>
                    </div>
                    <div>
                      <span style={{ color: 'var(--muted)' }}>Difficulty</span>
                      <p style={{ margin: 0 }}>{topic.difficulty}</p>
                    </div>
                    <div>
                      <span style={{ color: 'var(--muted)' }}>Status</span>
                      <p style={{ margin: 0 }}>{topic.status}</p>
                    </div>
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
