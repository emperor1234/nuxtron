'use client';

import { useState, useMemo } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Layers, RefreshCw, Download, Plus, Trash2 } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type TemplateVariable = { key: string; values: string[] };
type GeneratedPage = {
  url_slug: string;
  title: string;
  meta_description: string;
  estimated_traffic: number;
  target_keyword: string;
};
type ProgrammaticResult = {
  analysis_id: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  total_pages_generated: number;
  pages: GeneratedPage[];
  template_score: number;
  template_quality_score?: number;
  seo_coverage_estimate: number;
  cannibalization_risk: 'low' | 'medium' | 'high';
  deduplication_applied: number;
  recommendations: string[];
};

export default function ProgrammaticPage() {
  const [template, setTemplate] = useState('/[location]-[service]');
  const [titleTemplate, setTitleTemplate] = useState('Best [service] in [location] | [brand]');
  const [metaTemplate, setMetaTemplate] = useState(
    'Find the best [service] in [location]. Get quotes, reviews, and pricing from top providers.'
  );
  const [variables, setVariables] = useState<TemplateVariable[]>([
    { key: 'location', values: ['New York', 'Los Angeles', 'Chicago'] },
    { key: 'service', values: ['plumbers', 'electricians', 'cleaners'] },
    { key: 'brand', values: ['OmniSEO'] },
  ]);
  const [result, setResult] = useState<ProgrammaticResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'pages' | 'config' | 'recommendations'>('pages');
  const [search, setSearch] = useState('');

  function addVariable() {
    setVariables((v) => [...v, { key: 'new_var', values: ['value1'] }]);
  }
  function updateVarKey(i: number, key: string) {
    setVariables((v) => v.map((x, j) => (j === i ? { ...x, key } : x)));
  }
  function updateVarValues(i: number, raw: string) {
    setVariables((v) =>
      v.map((x, j) =>
        j === i
          ? {
              ...x,
              values: raw
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
            }
          : x
      )
    );
  }
  function removeVar(i: number) {
    setVariables((v) => v.filter((_, j) => j !== i));
  }

  const previewCount = useMemo(() => {
    return variables.reduce((acc, v) => acc * Math.max(v.values.length, 1), 1);
  }, [variables]);

  async function run() {
    if (!template) {
      setError('URL template is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const payload = {
        url_template: template,
        title_template: titleTemplate,
        meta_description_template: metaTemplate,
        variables: Object.fromEntries(variables.map((v) => [v.key, v.values])),
      };
      const data = await apiSend<ProgrammaticResult>(
        '/seo-platform/programmatic/generate',
        'POST',
        payload,
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }

      const normalized: ProgrammaticResult = {
        ...data,
        total_pages_generated: data.total_pages_generated ?? data.pages?.length ?? 0,
        template_score: data.template_score ?? data.template_quality_score ?? 0,
        pages: data.pages ?? [],
        recommendations: data.recommendations ?? [],
        seo_coverage_estimate: data.seo_coverage_estimate ?? 0,
        cannibalization_risk: data.cannibalization_risk ?? 'medium',
        deduplication_applied: data.deduplication_applied ?? 0,
      };
      setResult(normalized);
      setActiveTab('pages');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setLoading(false);
    }
  }

  const filteredPages = useMemo(() => {
    if (!result?.pages) return [];
    const q = search.toLowerCase();
    return q
      ? result.pages.filter((p) => p.url_slug.toLowerCase().includes(q) || p.target_keyword.toLowerCase().includes(q))
      : result.pages;
  }, [result, search]);

  function csvExport() {
    if (!result?.pages) return;
    const rows = [
      'url_slug,title,meta_description,target_keyword,estimated_traffic',
      ...result.pages.map(
        (p) => `"${p.url_slug}","${p.title}","${p.meta_description}","${p.target_keyword}",${p.estimated_traffic}`
      ),
    ];
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv' }));
    a.download = 'programmatic-pages.csv';
    a.click();
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
  const th: React.CSSProperties = {
    textAlign: 'left',
    padding: '8px 12px',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    color: 'var(--muted)',
    borderBottom: '1px solid var(--line)',
  };
  const td: React.CSSProperties = { padding: '9px 12px', fontSize: 12, borderBottom: '1px solid var(--line)' };
  const RISK_COLORS = { low: '#15803d', medium: '#ffb867', high: '#f87171' };

  const tabs = [
    { key: 'pages' as const, label: `Generated Pages (${result?.total_pages_generated ?? 0})` },
    { key: 'config' as const, label: 'Template Config' },
    { key: 'recommendations' as const, label: 'Recommendations' },
  ];

  return (
    <main
      className="seo-advanced-page"
      style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <h1
          style={{ margin: '0 0 4px', fontSize: 24, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <Layers size={24} color="var(--brand)" />
          Programmatic SEO
        </h1>
        <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
          Template-driven bulk page generation with variable matrix, de-duplication, and traffic estimates
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
                marginBottom: 5,
                color: 'var(--muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              URL Template
            </label>
            <input
              style={input}
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="/[location]-[service]"
            />
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
              Title Template
            </label>
            <input
              style={input}
              value={titleTemplate}
              onChange={(e) => setTitleTemplate(e.target.value)}
              placeholder="Best [service] in [location]"
            />
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
              Meta Description Template
            </label>
            <input
              style={input}
              value={metaTemplate}
              onChange={(e) => setMetaTemplate(e.target.value)}
              placeholder="Find top [service] in [location]..."
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <label
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Variable Matrix
              </label>
              <button
                onClick={addVariable}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '5px 12px',
                  border: '1px dashed var(--line)',
                  borderRadius: 7,
                  background: 'transparent',
                  color: 'var(--brand)',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                <Plus size={12} />
                Add Variable
              </button>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {variables.map((v, i) => (
                <div
                  key={i}
                  style={{ display: 'grid', gridTemplateColumns: '140px 1fr auto', gap: 8, alignItems: 'center' }}
                >
                  <input
                    value={v.key}
                    onChange={(e) => updateVarKey(i, e.target.value)}
                    style={{
                      ...input,
                      marginBottom: 0,
                      fontFamily: 'monospace',
                      color: 'var(--brand)',
                      fontWeight: 700,
                      fontSize: 12,
                    }}
                    placeholder="variable_name"
                  />
                  <input
                    value={v.values.join(', ')}
                    onChange={(e) => updateVarValues(i, e.target.value)}
                    style={{ ...input, marginBottom: 0 }}
                    placeholder="val1, val2, val3..."
                  />
                  <button
                    onClick={() => removeVar(i)}
                    style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', padding: 6 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <div
              style={{
                marginTop: 10,
                padding: '8px 14px',
                background: 'rgba(27,199,255,0.06)',
                borderRadius: 8,
                border: '1px solid rgba(27,199,255,0.2)',
                fontSize: 12,
                color: 'var(--brand)',
                fontWeight: 700,
              }}
            >
              Preview: <strong>{previewCount.toLocaleString()}</strong> pages will be generated from current matrix
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
                Generating Pages...
              </>
            ) : (
              <>
                <Layers size={15} />
                Generate Pages
              </>
            )}
          </button>
        </section>

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
                  Pages Generated
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--brand)' }}>
                  {result.total_pages_generated.toLocaleString()}
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
                  Template Score
                </div>
                <div
                  style={{ fontSize: 32, fontWeight: 800, color: result.template_score >= 75 ? '#15803d' : '#ffb867' }}
                >
                  {result.template_score}
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
                  SEO Coverage Est.
                </div>
                <div style={{ fontSize: 32, fontWeight: 800 }}>{result.seo_coverage_estimate}%</div>
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
                  Cannibalization Risk
                </div>
                <span
                  style={{
                    padding: '4px 12px',
                    borderRadius: 999,
                    fontSize: 12,
                    fontWeight: 700,
                    background: RISK_COLORS[result.cannibalization_risk] + '22',
                    color: RISK_COLORS[result.cannibalization_risk],
                    border: `1px solid ${RISK_COLORS[result.cannibalization_risk]}44`,
                  }}
                >
                  {result.cannibalization_risk}
                </span>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: '#15803d',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Dupes Removed
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: '#15803d' }}>{result.deduplication_applied}</div>
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

            {activeTab === 'pages' && (
              <div style={card}>
                <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search pages..."
                    style={{ ...input, width: 280, marginBottom: 0 }}
                  />
                  <button
                    onClick={csvExport}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '8px 14px',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      background: 'transparent',
                      color: 'var(--muted)',
                      cursor: 'pointer',
                      fontSize: 12,
                      marginLeft: 'auto',
                    }}
                  >
                    <Download size={12} />
                    Export CSV
                  </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={th}>URL Slug</th>
                        <th style={th}>Title</th>
                        <th style={th}>Target Keyword</th>
                        <th style={{ ...th, textAlign: 'right' }}>Est. Traffic</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPages.map((p, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                          <td style={{ ...td, fontFamily: 'monospace', color: 'var(--brand)', fontSize: 11 }}>
                            {p.url_slug}
                          </td>
                          <td style={td}>{p.title}</td>
                          <td style={{ ...td, color: 'var(--muted)' }}>{p.target_keyword}</td>
                          <td
                            style={{
                              ...td,
                              textAlign: 'right',
                              fontWeight: 700,
                              color: p.estimated_traffic > 500 ? '#15803d' : 'var(--muted)',
                            }}
                          >
                            {p.estimated_traffic.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'config' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Template Preview</h3>
                <div style={{ background: '#f6f7fa', borderRadius: 10, padding: '16px 20px', marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--muted)',
                      marginBottom: 6,
                      textTransform: 'uppercase',
                      fontWeight: 700,
                    }}
                  >
                    URL Pattern
                  </div>
                  <code style={{ color: '#0e7490', fontSize: 14 }}>{template}</code>
                </div>
                <div style={{ background: '#f6f7fa', borderRadius: 10, padding: '16px 20px', marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--muted)',
                      marginBottom: 6,
                      textTransform: 'uppercase',
                      fontWeight: 700,
                    }}
                  >
                    Title Pattern
                  </div>
                  <code style={{ color: '#15803d', fontSize: 14 }}>{titleTemplate}</code>
                </div>
                <div style={{ background: '#f6f7fa', borderRadius: 10, padding: '16px 20px' }}>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--muted)',
                      marginBottom: 6,
                      textTransform: 'uppercase',
                      fontWeight: 700,
                    }}
                  >
                    Meta Description Pattern
                  </div>
                  <code style={{ color: '#ffb867', fontSize: 13, lineHeight: 1.5 }}>{metaTemplate}</code>
                </div>
              </div>
            )}

            {activeTab === 'recommendations' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Optimization Recommendations</h3>
                {result.recommendations?.map((rec, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 12,
                      background: 'var(--bg)',
                      borderRadius: 10,
                      padding: '12px 16px',
                      border: '1px solid var(--line)',
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: 6,
                        background: 'rgba(27,199,255,0.15)',
                        color: 'var(--brand)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: 11,
                        fontWeight: 800,
                      }}
                    >
                      {i + 1}
                    </div>
                    <span style={{ fontSize: 13, lineHeight: 1.5 }}>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </main>
  );
}
