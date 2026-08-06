'use client';

import { useEffect, useState } from 'react';

import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type VendorReportRow = {
  source: string;
  vendor: string;
  category: string;
  integration: string;
  configured_units: number;
  total_units: number;
  runtime_dependency: boolean;
};

type VendorReportResponse = {
  status: string;
  summary: {
    domains: number;
    vendors: number;
    categories: number;
  };
  domain_chart: Array<{
    domain: string;
    configured_units: number;
    total_units: number;
    coverage_pct: number;
  }>;
  category_chart: Array<{
    category: string;
    vendors: number;
    configured_units: number;
    total_units: number;
  }>;
  vendor_chart: Array<{
    source: string;
    vendor: string;
    category: string;
    integration: string;
    configured_units: number;
    total_units: number;
    runtime_dependency: boolean;
  }>;
  export_rows: VendorReportRow[];
};

type VendorReportCsvResponse = {
  status: string;
  format: 'csv';
  count: number;
  filename: string;
  csv: string;
};

type VendorReportJsonResponse = {
  status: string;
  format: 'json';
  count: number;
  filename: string;
  json: VendorReportRow[];
};

function barGradient(percent: number): string {
  const safe = Math.max(0, Math.min(percent, 100));
  return `linear-gradient(90deg, #0f766e 0%, #14b8a6 ${safe}%, rgba(20, 184, 166, 0.14) ${safe}%, rgba(20, 184, 166, 0.08) 100%)`;
}

function downloadTextFile(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function VendorInventoryReportPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState<VendorReportResponse | null>(null);
  const [exportStatus, setExportStatus] = useState('');

  async function loadReport() {
    setLoading(true);
    setError('');
    try {
      const response = await apiGet<VendorReportResponse>('/search-everywhere/vendors/report', tenantId);
      setReport(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load vendor inventory report');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadReport();
  }, []);

  async function copyExportRows() {
    if (!report) return;
    const json = JSON.stringify(report.export_rows, null, 2);
    try {
      await navigator.clipboard.writeText(json);
      setExportStatus(`Copied ${report.export_rows.length} export rows as JSON.`);
    } catch {
      setExportStatus('Clipboard copy failed in this browser context.');
    }
  }

  async function downloadCsv() {
    if (!report) return;
    try {
      const response = await apiGet<VendorReportCsvResponse>(
        '/search-everywhere/vendors/report/export?format=csv',
        tenantId
      );
      downloadTextFile(response.filename, response.csv, 'text/csv;charset=utf-8');
      setExportStatus(`Downloaded ${response.count} export rows as canonical CSV.`);
    } catch (e) {
      setExportStatus(e instanceof Error ? e.message : 'CSV export failed.');
    }
  }

  async function downloadJson() {
    if (!report) return;
    try {
      const response = await apiGet<VendorReportJsonResponse>(
        '/search-everywhere/vendors/report/export?format=json',
        tenantId
      );
      downloadTextFile(response.filename, JSON.stringify(response.json, null, 2), 'application/json;charset=utf-8');
      setExportStatus(`Downloaded ${response.count} export rows as canonical JSON.`);
    } catch (e) {
      setExportStatus(e instanceof Error ? e.message : 'JSON export failed.');
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Vendor Inventory</p>
        <h1>Unified Third-Party Vendor Report</h1>
        <p>
          Review cross-domain vendor coverage for search automation, AI crawler enablement, CMS connections, and
          platform integrations from one live backend report.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 6 }}>Live Report</h2>
            <p style={{ margin: 0, opacity: 0.82 }}>
              This page consumes <strong>/search-everywhere/vendors/report</strong> and is intended for
              production-readiness and third-party inventory reviews.
            </p>
          </div>
          <button onClick={() => void loadReport()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Report'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p> : null}
      </section>

      {report ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Domains</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{report.summary.domains}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Vendor Rows</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{report.summary.vendors}</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Categories</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{report.summary.categories}</p>
          </article>
        </section>
      ) : null}

      {report ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Domain Coverage</h3>
            <div style={{ display: 'grid', gap: 12 }}>
              {report.domain_chart.map((item) => (
                <div key={item.domain}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 4 }}>
                    <strong>{item.domain.replaceAll('_', ' ')}</strong>
                    <span>{item.coverage_pct}%</span>
                  </div>
                  <div style={{ height: 12, borderRadius: 999, background: barGradient(item.coverage_pct) }} />
                  <p style={{ margin: '6px 0 0', opacity: 0.72 }}>
                    {item.configured_units}/{item.total_units} configured units
                  </p>
                </div>
              ))}
            </div>
          </article>

          <article className="card">
            <h3 style={{ marginTop: 0 }}>Category Mix</h3>
            <div style={{ display: 'grid', gap: 12 }}>
              {report.category_chart.map((item) => {
                const percent = Math.round((item.configured_units / Math.max(item.total_units, 1)) * 1000) / 10;
                return (
                  <div key={item.category}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 4 }}>
                      <strong>{item.category.replaceAll('_', ' ')}</strong>
                      <span>{item.vendors} vendors</span>
                    </div>
                    <div style={{ height: 12, borderRadius: 999, background: barGradient(percent) }} />
                    <p style={{ margin: '6px 0 0', opacity: 0.72 }}>
                      {item.configured_units}/{item.total_units} configured units
                    </p>
                  </div>
                );
              })}
            </div>
          </article>
        </section>
      ) : null}

      {report ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Unified Vendor Chart</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {report.vendor_chart.map((item) => (
              <div
                key={`${item.source}:${item.vendor}:${item.integration}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'minmax(140px, 180px) minmax(180px, 1.4fr) minmax(min(100%, 140px), 1fr) minmax(min(100%, 140px), 1fr) auto',
                  gap: 12,
                  padding: '12px 14px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 16,
                  background: item.runtime_dependency ? 'rgba(20, 184, 166, 0.08)' : 'rgba(255,255,255,0.02)',
                }}
              >
                <strong>{item.source.replaceAll('_', ' ')}</strong>
                <span>{item.vendor}</span>
                <span>{item.category.replaceAll('_', ' ')}</span>
                <span>{item.integration}</span>
                <span>
                  {item.configured_units}/{item.total_units}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {report ? (
        <section className="card" style={{ marginTop: 20 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 16,
              alignItems: 'flex-start',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <h3 style={{ marginTop: 0 }}>Export Rows</h3>
              <p style={{ marginTop: 0, opacity: 0.78 }}>
                Structured rows intended for chart pipelines, export tooling, and operational reporting.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={() => void copyExportRows()}>Copy JSON</button>
              <button onClick={() => void downloadJson()}>Download JSON</button>
              <button onClick={() => void downloadCsv()}>Download CSV</button>
            </div>
          </div>
          {exportStatus ? <p style={{ marginTop: 0, color: '#99f6e4' }}>{exportStatus}</p> : null}
          <ul className="bullet-list">
            {report.export_rows.slice(0, 12).map((item) => (
              <li key={`${item.source}-${item.vendor}-${item.integration}`}>
                <strong>{item.vendor}</strong> via {item.source} • {item.integration} • {item.configured_units}/
                {item.total_units} configured
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
