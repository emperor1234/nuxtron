'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Code2, RefreshCw, Copy, CheckCircle, AlertTriangle } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const SCHEMA_TYPES = [
  { type: 'Article', icon: '📄', desc: 'Blog posts, news, editorial content' },
  { type: 'Product', icon: '🛒', desc: 'E-commerce products with price, availability' },
  { type: 'FAQPage', icon: '❓', desc: 'Frequently asked questions' },
  { type: 'HowTo', icon: '🔧', desc: 'Step-by-step guides and tutorials' },
  { type: 'LocalBusiness', icon: '📍', desc: 'Local business with address, hours, phone' },
  { type: 'Review', icon: '⭐', desc: 'Reviews with ratings and reviewer info' },
  { type: 'Event', icon: '📅', desc: 'Events with date, location, organizer' },
  { type: 'Person', icon: '👤', desc: 'Author and person profiles' },
  { type: 'Organization', icon: '🏢', desc: 'Company and organization info' },
  { type: 'BreadcrumbList', icon: '🍞', desc: 'Navigation breadcrumb trail' },
  { type: 'VideoObject', icon: '🎥', desc: 'Video content with duration, thumbnail' },
  { type: 'Recipe', icon: '🍳', desc: 'Recipes with ingredients and instructions' },
];

type ValidationIssue = { property: string; message: string; severity: 'error' | 'warning' | 'info' };
type SchemaResult = {
  analysis_id: string;
  schema_type: string;
  json_ld: string;
  validation_score: number;
  is_valid: boolean;
  validation_issues: ValidationIssue[];
  rich_result_types: string[];
  properties_used: string[];
  missing_recommended: string[];
  google_preview_hints: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function SchemasPage() {
  const [pageUrl, setPageUrl] = useState('');
  const [content, setContent] = useState('');
  const [schemaType, setSchemaType] = useState('Article');
  const [result, setResult] = useState<SchemaResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'code' | 'validation' | 'rich_results'>('code');

  async function run() {
    if (!content && !pageUrl) {
      setError('URL or content is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<SchemaResult>(
        '/seo-platform/schemas/generate',
        'POST',
        { page_url: pageUrl || undefined, content: content || undefined, schema_type: schemaType },
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
      setActiveTab('code');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setLoading(false);
    }
  }

  function copyJsonLd() {
    if (!result?.json_ld) return;
    void navigator.clipboard.writeText(result.json_ld).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const card: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
  };
  const input: React.CSSProperties = {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box',
    fontSize: 14,
  };
  const SEVERITY_COLORS = { error: '#f87171', warning: '#ffb867', info: '#1bc7ff' };

  const tabs = [
    { key: 'code' as const, label: 'JSON-LD Code' },
    { key: 'validation' as const, label: `Validation (${result?.validation_issues?.length ?? 0})` },
    { key: 'rich_results' as const, label: 'Rich Results' },
  ];

  return (
    <main
      className="seo-advanced-page"
      style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}
    >
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h1
          style={{ margin: '0 0 4px', fontSize: 24, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <Code2 size={24} color="var(--brand)" />
          Schema Markup Generator
        </h1>
        <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
          AI-powered JSON-LD schema generator with validation, rich result eligibility, and Google preview hints
        </p>

        {error && (
          <div style={{ ...card, color: '#f87171', borderColor: '#f8717144', background: '#f8717111' }}>{error}</div>
        )}

        <section style={card}>
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: 'block',
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 8,
                color: 'var(--muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Schema Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 8 }}>
              {SCHEMA_TYPES.map((s) => (
                <button
                  key={s.type}
                  onClick={() => setSchemaType(s.type)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 10,
                    border: `1px solid ${schemaType === s.type ? 'var(--brand)' : 'var(--line)'}`,
                    background: schemaType === s.type ? 'rgba(27,199,255,0.08)' : 'var(--bg)',
                    color: schemaType === s.type ? 'var(--brand)' : 'var(--text)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontSize: 16, marginBottom: 3 }}>{s.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{s.type}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{s.desc}</div>
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: 12,
                  fontWeight: 600,
                  marginBottom: 5,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Page URL
              </label>
              <input
                style={input}
                value={pageUrl}
                onChange={(e) => setPageUrl(e.target.value)}
                placeholder="https://example.com/article"
              />
            </div>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: 12,
                  fontWeight: 600,
                  marginBottom: 5,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Page Content (optional)
              </label>
              <textarea
                style={{ ...input, minHeight: 90, resize: 'vertical' }}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste relevant page content for better accuracy..."
              />
            </div>
          </div>
          <button
            onClick={() => void run()}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 28px',
              border: 'none',
              borderRadius: 8,
              background: loading ? 'var(--muted)' : 'var(--brand)',
              color: '#00101e',
              fontWeight: 800,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 14,
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
                Generating...
              </>
            ) : (
              <>
                <Code2 size={15} />
                Generate Schema
              </>
            )}
          </button>
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
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
                gap: 12,
                marginBottom: 20,
              }}
            >
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Validation Score
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 800,
                    color:
                      result.validation_score >= 80 ? '#26d78e' : result.validation_score >= 60 ? '#ffb867' : '#f87171',
                  }}
                >
                  {result.validation_score}
                </div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Status
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {result.is_valid ? (
                    <CheckCircle size={20} color="#26d78e" />
                  ) : (
                    <AlertTriangle size={20} color="#f87171" />
                  )}
                  <span style={{ fontSize: 14, fontWeight: 700, color: result.is_valid ? '#26d78e' : '#f87171' }}>
                    {result.is_valid ? 'Valid' : 'Has Issues'}
                  </span>
                </div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Rich Results
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--brand)' }}>
                  {result.rich_result_types?.length ?? 0}
                </div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: '#ffb867',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Missing Recommended
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#ffb867' }}>
                  {result.missing_recommended?.length ?? 0}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--line)' }}>
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '8px 8px 0 0',
                    background: activeTab === t.key ? 'var(--bg-soft)' : 'transparent',
                    color: activeTab === t.key ? 'var(--brand)' : 'var(--muted)',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: 'pointer',
                    borderBottom: activeTab === t.key ? '2px solid var(--brand)' : '2px solid transparent',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {activeTab === 'code' && (
              <div style={card}>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}
                >
                  <span style={{ fontSize: 13, fontWeight: 700 }}>Generated JSON-LD — {result.schema_type}</span>
                  <button
                    onClick={copyJsonLd}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '7px 14px',
                      border: '1px solid var(--line)',
                      borderRadius: 7,
                      background: copied ? 'rgba(38,215,142,0.1)' : 'transparent',
                      color: copied ? '#26d78e' : 'var(--muted)',
                      cursor: 'pointer',
                      fontSize: 12,
                      fontWeight: 700,
                    }}
                  >
                    <Copy size={12} />
                    {copied ? 'Copied!' : 'Copy Code'}
                  </button>
                </div>
                <pre
                  style={{
                    margin: 0,
                    padding: '16px 20px',
                    background: '#f6f7fa',
                    borderRadius: 10,
                    border: '1px solid var(--line)',
                    color: 'var(--text)',
                    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace",
                    fontSize: 12,
                    lineHeight: 1.7,
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {result.json_ld}
                </pre>
              </div>
            )}

            {activeTab === 'validation' && (
              <div style={card}>
                {result.missing_recommended?.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#ffb867',
                        marginBottom: 10,
                      }}
                    >
                      Missing Recommended Properties
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {result.missing_recommended.map((p) => (
                        <span
                          key={p}
                          style={{
                            padding: '4px 12px',
                            borderRadius: 999,
                            background: 'rgba(255,184,103,0.1)',
                            color: '#ffb867',
                            fontSize: 12,
                            fontWeight: 700,
                            border: '1px solid rgba(255,184,103,0.3)',
                          }}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: 'var(--muted)',
                      marginBottom: 10,
                    }}
                  >
                    Validation Issues
                  </div>
                  {result.validation_issues?.length === 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#26d78e', fontSize: 13 }}>
                      <CheckCircle size={16} />
                      No validation issues — schema is clean!
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: 8 }}>
                      {result.validation_issues?.map((issue, i) => (
                        <div
                          key={i}
                          style={{
                            background: 'var(--bg)',
                            borderRadius: 8,
                            padding: '10px 14px',
                            border: `1px solid ${SEVERITY_COLORS[issue.severity]}44`,
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: 10,
                          }}
                        >
                          <span
                            style={{
                              padding: '2px 7px',
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 700,
                              background: SEVERITY_COLORS[issue.severity] + '22',
                              color: SEVERITY_COLORS[issue.severity],
                              flexShrink: 0,
                              textTransform: 'uppercase',
                            }}
                          >
                            {issue.severity}
                          </span>
                          <div>
                            <div
                              style={{
                                fontSize: 12,
                                fontWeight: 700,
                                marginBottom: 2,
                                fontFamily: 'monospace',
                                color: 'var(--brand)',
                              }}
                            >
                              {issue.property}
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--muted)' }}>{issue.message}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'rich_results' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Rich Result Eligibility</h3>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))',
                    gap: 10,
                    marginBottom: 20,
                  }}
                >
                  {result.rich_result_types?.map((r) => (
                    <div
                      key={r}
                      style={{
                        background: 'rgba(38,215,142,0.08)',
                        border: '1px solid rgba(38,215,142,0.25)',
                        borderRadius: 10,
                        padding: '12px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                      }}
                    >
                      <CheckCircle size={14} color="#26d78e" />
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#26d78e' }}>{r}</span>
                    </div>
                  ))}
                </div>
                <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700 }}>Google Preview Hints</h3>
                <div style={{ display: 'grid', gap: 8 }}>
                  {result.google_preview_hints?.map((hint, i) => (
                    <div
                      key={i}
                      style={{
                        background: 'var(--bg)',
                        borderRadius: 8,
                        padding: '10px 14px',
                        border: '1px solid var(--line)',
                        fontSize: 13,
                        lineHeight: 1.5,
                      }}
                    >
                      {hint}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </main>
  );
}
