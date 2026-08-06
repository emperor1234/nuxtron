'use client';

import { useState } from 'react';

interface DomainSummary {
  domain: string;
  organic_traffic: number;
  organic_keywords: number;
  authority_score: number;
  backlinks: number;
  paid_keywords?: number;
  estimated_traffic_cost_usd?: number;
  traffic_trend_pct?: number;
  top_organic_keywords?: { keyword: string; position: number; volume: number }[];
  top_competitors?: { domain: string; common_keywords: number; authority_score: number }[];
  _source?: string;
}

export default function DomainOverviewPage() {
  const [domain, setDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DomainSummary | null>(null);
  const [error, setError] = useState('');

  async function fetchSummary() {
    if (!domain.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`/api/domain-overview/summary?domain=${encodeURIComponent(domain.trim())}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  const fmt = (n: number | undefined) =>
    n === undefined
      ? '—'
      : n >= 1_000_000
        ? `${(n / 1_000_000).toFixed(1)}M`
        : n >= 1_000
          ? `${(n / 1_000).toFixed(1)}K`
          : String(n);

  const pct = (n: number | undefined) => (n === undefined ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Domain Overview</h1>
          <p className="text-sm text-gray-500">
            Full domain metrics snapshot — traffic, keywords, backlinks, authority
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search Bar */}
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Analyze Domain</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchSummary()}
              placeholder="e.g. semrush.com"
              className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-orange-400 focus:outline-none"
            />
            <button
              onClick={fetchSummary}
              disabled={loading || !domain.trim()}
              className="bg-orange-500 hover:bg-orange-600 text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm transition-colors"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>

        {data && (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                {
                  label: 'Organic Traffic',
                  value: fmt(data.organic_traffic),
                  color: 'text-[var(--brand)]',
                  bg: 'bg-blue-50',
                },
                {
                  label: 'Organic Keywords',
                  value: fmt(data.organic_keywords),
                  color: 'text-green-600',
                  bg: 'bg-green-50',
                },
                {
                  label: 'Authority Score',
                  value: String(data.authority_score ?? '—'),
                  color: 'text-[var(--brand)]',
                  bg: 'bg-purple-50',
                },
                { label: 'Backlinks', value: fmt(data.backlinks), color: 'text-orange-600', bg: 'bg-orange-50' },
              ].map((kpi) => (
                <div key={kpi.label} className={`rounded-xl border p-5 ${kpi.bg}`}>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{kpi.label}</p>
                  <p className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</p>
                </div>
              ))}
            </div>

            {/* Secondary row */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-xl border p-5">
                <p className="text-xs text-gray-500 mb-1">Paid Keywords</p>
                <p className="text-xl font-bold text-gray-800">{fmt(data.paid_keywords)}</p>
              </div>
              <div className="bg-white rounded-xl border p-5">
                <p className="text-xs text-gray-500 mb-1">Traffic Cost / mo</p>
                <p className="text-xl font-bold text-gray-800">
                  {data.estimated_traffic_cost_usd !== undefined ? `$${fmt(data.estimated_traffic_cost_usd)}` : '—'}
                </p>
              </div>
              <div className="bg-white rounded-xl border p-5">
                <p className="text-xs text-gray-500 mb-1">Traffic Trend (30d)</p>
                <p
                  className={`text-xl font-bold ${(data.traffic_trend_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}
                >
                  {pct(data.traffic_trend_pct)}
                </p>
              </div>
            </div>

            {/* Top Keywords */}
            {data.top_organic_keywords && data.top_organic_keywords.length > 0 && (
              <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
                <h2 className="font-semibold text-gray-800 mb-4">Top Organic Keywords</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-gray-500 text-xs uppercase">
                        <th className="py-2 text-left">Keyword</th>
                        <th className="py-2 text-right">Position</th>
                        <th className="py-2 text-right">Volume</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_organic_keywords.map((kw, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-2.5 font-medium text-gray-900">{kw.keyword}</td>
                          <td className="py-2.5 text-right">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${kw.position <= 3 ? 'bg-green-100 text-green-700' : kw.position <= 10 ? 'bg-blue-100 text-[var(--brand)]' : 'bg-gray-100 text-gray-600'}`}
                            >
                              #{kw.position}
                            </span>
                          </td>
                          <td className="py-2.5 text-right text-gray-600">{fmt(kw.volume)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Competitors */}
            {data.top_competitors && data.top_competitors.length > 0 && (
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <h2 className="font-semibold text-gray-800 mb-4">Top Competitors</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-gray-500 text-xs uppercase">
                        <th className="py-2 text-left">Domain</th>
                        <th className="py-2 text-right">Common Keywords</th>
                        <th className="py-2 text-right">Authority Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_competitors.map((comp, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-2.5 font-medium text-[var(--brand)]">{comp.domain}</td>
                          <td className="py-2.5 text-right">{fmt(comp.common_keywords)}</td>
                          <td className="py-2.5 text-right">{comp.authority_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {data._source && <p className="text-xs text-[var(--muted)] mt-4 text-right">Data source: {data._source}</p>}
          </>
        )}
      </div>
    </div>
  );
}
