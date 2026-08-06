'use client';

import { useState, useEffect } from 'react';

interface Client {
  id: string;
  name: string;
  email?: string;
  company?: string;
  brand_color?: string;
  logo_url?: string;
  created_at: string;
}

interface Report {
  id: string;
  client_id: string;
  client_name?: string;
  title: string;
  type: string;
  status: string;
  period_start?: string;
  period_end?: string;
  domains?: string[];
  created_at: string;
}

interface ShareLinkResponse {
  share_url: string;
  token: string;
  expires_at?: string;
}

const defaultColor = '#f97316';

export default function ClientPortalPage() {
  const [activeTab, setActiveTab] = useState<'clients' | 'reports'>('clients');
  const [clients, setClients] = useState<Client[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // New client form
  const [showClientForm, setShowClientForm] = useState(false);
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [clientCompany, setClientCompany] = useState('');
  const [clientColor, setClientColor] = useState(defaultColor);

  // New report form
  const [showReportForm, setShowReportForm] = useState(false);
  const [reportClientId, setReportClientId] = useState('');
  const [reportTitle, setReportTitle] = useState('');
  const [reportType, setReportType] = useState('overview');
  const [reportDomains, setReportDomains] = useState('');
  const [reportPeriodStart, setReportPeriodStart] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 1);
    return d.toISOString().slice(0, 10);
  });
  const [reportPeriodEnd, setReportPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10));

  // Share link
  const [shareLink, setShareLink] = useState<Record<string, string>>({});

  useEffect(() => {
    loadClients();
  }, []);

  async function loadClients() {
    setLoading(true);
    try {
      const res = await fetch('/api/client-portal/clients');
      const data = await res.json();
      setClients(data.clients || []);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function loadReports() {
    setLoading(true);
    try {
      const res = await fetch('/api/client-portal/reports');
      const data = await res.json();
      setReports(data.reports || []);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function createClient() {
    if (!clientName.trim()) return;
    setError('');
    try {
      const res = await fetch('/api/client-portal/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: clientName.trim(),
          email: clientEmail.trim() || undefined,
          company: clientCompany.trim() || undefined,
          brand_color: clientColor,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const newClient = await res.json();
      setClients((prev) => [newClient, ...prev]);
      setShowClientForm(false);
      setClientName('');
      setClientEmail('');
      setClientCompany('');
      setClientColor(defaultColor);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  }

  async function deleteClient(id: string) {
    await fetch(`/api/client-portal/clients/${id}`, { method: 'DELETE' });
    setClients((prev) => prev.filter((c) => c.id !== id));
  }

  async function createReport() {
    if (!reportClientId || !reportTitle.trim()) return;
    setError('');
    try {
      const res = await fetch('/api/client-portal/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: reportClientId,
          title: reportTitle.trim(),
          type: reportType,
          period_start: reportPeriodStart,
          period_end: reportPeriodEnd,
          domains: reportDomains
            .split(',')
            .map((d) => d.trim())
            .filter(Boolean),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const r = await res.json();
      setReports((prev) => [r, ...prev]);
      setShowReportForm(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  }

  async function generateShareLink(reportId: string) {
    try {
      const res = await fetch('/api/client-portal/share-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      const data: ShareLinkResponse = await res.json();
      setShareLink((prev) => ({ ...prev, [reportId]: data.share_url }));
    } catch {}
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Client Portal</h1>
          <p className="text-sm text-gray-500">White-label reporting, client management &amp; shareable dashboards</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {[
            { id: 'clients', label: 'Clients' },
            { id: 'reports', label: 'Reports' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id as 'clients' | 'reports');
                if (t.id === 'reports') loadReports();
              }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium ${activeTab === t.id ? 'bg-white shadow text-slate-700' : 'text-gray-600'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && (
          <p className="text-red-500 text-sm mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
        )}

        {/* Clients */}
        {activeTab === 'clients' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold text-gray-800">Your Clients ({clients.length})</h2>
              <button
                onClick={() => setShowClientForm((p) => !p)}
                className="bg-[var(--brand)] hover:bg-[var(--brand-2)] text-white text-sm font-semibold px-4 py-2 rounded-lg"
              >
                + Add Client
              </button>
            </div>

            {showClientForm && (
              <div className="bg-white rounded-xl border shadow-sm p-5 mb-5">
                <h3 className="font-medium text-gray-800 mb-3">New Client</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                  <input
                    type="text"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="Client Name *"
                    className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                  />
                  <input
                    type="email"
                    value={clientEmail}
                    onChange={(e) => setClientEmail(e.target.value)}
                    placeholder="Email"
                    className="border rounded-lg px-3 py-2 text-sm focus:outline-none"
                  />
                  <input
                    type="text"
                    value={clientCompany}
                    onChange={(e) => setClientCompany(e.target.value)}
                    placeholder="Company"
                    className="border rounded-lg px-3 py-2 text-sm focus:outline-none"
                  />
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Brand Color</label>
                    <input
                      type="color"
                      value={clientColor}
                      onChange={(e) => setClientColor(e.target.value)}
                      className="h-9 w-16 rounded cursor-pointer border"
                    />
                    <span className="text-xs text-[var(--muted)] font-mono">{clientColor}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={createClient}
                    disabled={!clientName.trim()}
                    className="bg-[var(--brand)] text-white text-sm font-semibold px-5 py-2 rounded-lg disabled:opacity-50"
                  >
                    Save Client
                  </button>
                  <button
                    onClick={() => setShowClientForm(false)}
                    className="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {loading ? (
              <p className="text-[var(--muted)] text-sm">Loading…</p>
            ) : clients.length === 0 ? (
              <div className="bg-white rounded-xl border p-12 text-center text-[var(--muted)]">
                <p className="text-4xl mb-3">👥</p>
                <p className="text-sm">No clients yet. Add your first client.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {clients.map((c) => (
                  <div key={c.id} className="bg-white rounded-xl border shadow-sm overflow-hidden">
                    <div className="h-2" style={{ backgroundColor: c.brand_color || defaultColor }} />
                    <div className="p-4">
                      <div className="flex justify-between">
                        <div>
                          <p className="font-semibold text-gray-900">{c.name}</p>
                          {c.company && <p className="text-sm text-gray-500">{c.company}</p>}
                          {c.email && <p className="text-xs text-[var(--muted)]">{c.email}</p>}
                        </div>
                        <button
                          onClick={() => deleteClient(c.id)}
                          className="text-[var(--muted)] hover:text-red-500 text-sm ml-2"
                        >
                          ✕
                        </button>
                      </div>
                      <p className="text-xs text-[var(--muted)] mt-2">{new Date(c.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Reports */}
        {activeTab === 'reports' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold text-gray-800">Reports ({reports.length})</h2>
              <button
                onClick={() => setShowReportForm((p) => !p)}
                className="bg-[var(--brand)] hover:bg-[var(--brand-2)] text-white text-sm font-semibold px-4 py-2 rounded-lg"
              >
                + Generate Report
              </button>
            </div>

            {showReportForm && (
              <div className="bg-white rounded-xl border shadow-sm p-5 mb-5">
                <h3 className="font-medium text-gray-800 mb-3">New Report</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Client *</label>
                    <select
                      value={reportClientId}
                      onChange={(e) => setReportClientId(e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    >
                      <option value="">Select client…</option>
                      {clients.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Report Title *</label>
                    <input
                      type="text"
                      value={reportTitle}
                      onChange={(e) => setReportTitle(e.target.value)}
                      placeholder="Monthly SEO Report — May 2025"
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Type</label>
                    <select
                      value={reportType}
                      onChange={(e) => setReportType(e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm"
                    >
                      {['overview', 'seo', 'ppc', 'content', 'backlinks', 'local', 'custom'].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Domains (comma-separated)</label>
                    <input
                      type="text"
                      value={reportDomains}
                      onChange={(e) => setReportDomains(e.target.value)}
                      placeholder="example.com, shop.example.com"
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Period Start</label>
                    <input
                      type="date"
                      value={reportPeriodStart}
                      onChange={(e) => setReportPeriodStart(e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Period End</label>
                    <input
                      type="date"
                      value={reportPeriodEnd}
                      onChange={(e) => setReportPeriodEnd(e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={createReport}
                    disabled={!reportClientId || !reportTitle.trim()}
                    className="bg-[var(--brand)] text-white text-sm font-semibold px-5 py-2 rounded-lg disabled:opacity-50"
                  >
                    Generate Report
                  </button>
                  <button
                    onClick={() => setShowReportForm(false)}
                    className="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {loading ? (
              <p className="text-[var(--muted)] text-sm">Loading…</p>
            ) : reports.length === 0 ? (
              <div className="bg-white rounded-xl border p-12 text-center text-[var(--muted)]">
                <p className="text-4xl mb-3">📊</p>
                <p className="text-sm">No reports yet. Generate your first report.</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                      <th className="py-3 px-4 text-left">Title</th>
                      <th className="py-3 px-4 text-left">Client</th>
                      <th className="py-3 px-4 text-left">Type</th>
                      <th className="py-3 px-4 text-left">Period</th>
                      <th className="py-3 px-4 text-left">Status</th>
                      <th className="py-3 px-4 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((r) => (
                      <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium text-gray-900 max-w-xs truncate">{r.title}</td>
                        <td className="py-3 px-4 text-gray-600">{r.client_name || r.client_id}</td>
                        <td className="py-3 px-4">
                          <span className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded capitalize">
                            {r.type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-500 text-xs">
                          {r.period_start} – {r.period_end}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`text-xs font-medium px-2 py-0.5 rounded ${r.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-[var(--brand)]'}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <a
                              href={`/api/client-portal/reports/${r.id}/download`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-[var(--brand)] hover:underline"
                            >
                              Download
                            </a>
                            {shareLink[r.id] ? (
                              <span
                                className="text-xs text-green-600 font-mono truncate max-w-[120px]"
                                title={shareLink[r.id]}
                              >
                                Copied!
                              </span>
                            ) : (
                              <button
                                onClick={() => generateShareLink(r.id)}
                                className="text-xs text-slate-600 hover:underline"
                              >
                                Share
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
