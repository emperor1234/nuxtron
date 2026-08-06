'use client';

import { useState } from 'react';

interface PLAAdvertiser {
  rank: number;
  domain: string;
  pla_keywords?: number;
  monthly_traffic?: number;
  avg_cpc_usd?: number;
  estimated_spend_usd?: number;
  product_title?: string;
  price_usd?: number;
  seller?: string;
}

interface PLAAd {
  id: string;
  product_title: string;
  price_usd: number;
  category: string;
  impressions: number;
  clicks: number;
  ctr_pct: number;
  position: number;
  rating: number;
}

const fmt = (n: number | undefined) =>
  n === undefined
    ? '—'
    : n >= 1_000_000
      ? `${(n / 1_000_000).toFixed(1)}M`
      : n >= 1_000
        ? `${(n / 1_000).toFixed(0)}K`
        : String(n);

export default function PLAResearchPage() {
  const [keyword, setKeyword] = useState('');
  const [domain, setDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [advertisers, setAdvertisers] = useState<PLAAdvertiser[]>([]);
  const [adCopies, setAdCopies] = useState<PLAAd[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'ad-copies'>('overview');
  const [error, setError] = useState('');

  async function search() {
    if (!keyword.trim() && !domain.trim()) return;
    setLoading(true);
    setError('');
    try {
      const promises: Promise<Response>[] = [];
      if (keyword) promises.push(fetch(`/api/pla-research/overview?keyword=${encodeURIComponent(keyword.trim())}`));
      if (domain) promises.push(fetch(`/api/pla-research/ad-copies?domain=${encodeURIComponent(domain.trim())}`));
      const results = await Promise.all(promises);
      const jsons = await Promise.all(results.map((r) => r.json()));
      if (keyword && jsons[0]) setAdvertisers(jsons[0].advertisers || []);
      if (domain && jsons[jsons.length - 1]) setAdCopies(jsons[jsons.length - 1].ads || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">PLA Research</h1>
          <p className="text-sm text-gray-500">Product Listing Ads competitor intelligence — Google Shopping</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search */}
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product Keyword</label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && search()}
                placeholder="e.g. wireless headphones"
                className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-yellow-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Competitor Domain</label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && search()}
                placeholder="amazon.com"
                className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-yellow-400 focus:outline-none"
              />
            </div>
          </div>
          <button
            onClick={search}
            disabled={loading || (!keyword.trim() && !domain.trim())}
            className="bg-yellow-500 hover:bg-yellow-600 text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
          >
            {loading ? 'Researching…' : 'Research PLAs'}
          </button>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>

        {(advertisers.length > 0 || adCopies.length > 0) && (
          <>
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
              {[
                { id: 'overview', label: 'Top Advertisers' },
                { id: 'ad-copies', label: 'Ad Creatives' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id as 'overview' | 'ad-copies')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-white shadow text-yellow-700' : 'text-gray-600'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Advertisers */}
            {activeTab === 'overview' && advertisers.length > 0 && (
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <h2 className="font-semibold text-gray-800 mb-4">Top PLA Advertisers for "{keyword}"</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-gray-500 text-xs uppercase">
                        <th className="py-2 text-left w-8">#</th>
                        <th className="py-2 text-left">Domain / Product</th>
                        <th className="py-2 text-right">Monthly Traffic</th>
                        <th className="py-2 text-right">Avg CPC</th>
                        <th className="py-2 text-right">Est. Spend</th>
                        <th className="py-2 text-right">PLA Keywords</th>
                      </tr>
                    </thead>
                    <tbody>
                      {advertisers.map((a, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-3 text-gray-500 font-medium">{a.rank ?? i + 1}</td>
                          <td className="py-3">
                            <p className="font-medium text-gray-900">{a.domain || a.seller}</p>
                            {a.product_title && (
                              <p className="text-xs text-[var(--muted)] truncate max-w-xs">{a.product_title}</p>
                            )}
                          </td>
                          <td className="py-3 text-right">{fmt(a.monthly_traffic)}</td>
                          <td className="py-3 text-right">
                            {a.avg_cpc_usd !== undefined
                              ? `$${a.avg_cpc_usd.toFixed(2)}`
                              : a.price_usd !== undefined
                                ? `$${a.price_usd}`
                                : '—'}
                          </td>
                          <td className="py-3 text-right">
                            {a.estimated_spend_usd !== undefined ? `$${fmt(a.estimated_spend_usd)}` : '—'}
                          </td>
                          <td className="py-3 text-right">{fmt(a.pla_keywords)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Ad Copies */}
            {activeTab === 'ad-copies' && adCopies.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {adCopies.map((ad, i) => (
                  <div key={i} className="bg-white rounded-xl border shadow-sm p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs bg-yellow-100 text-yellow-700 font-semibold px-2 py-0.5 rounded">
                        Pos #{ad.position}
                      </span>
                      <span className="text-xs text-[var(--muted)]">{ad.category}</span>
                    </div>
                    <p className="font-semibold text-sm text-gray-900 mb-1 line-clamp-2">{ad.product_title}</p>
                    <p className="text-lg font-bold text-green-600 mb-2">${ad.price_usd?.toFixed(2)}</p>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>⭐ {ad.rating?.toFixed(1)}</span>
                      <span>{fmt(ad.impressions)} impr</span>
                      <span>CTR {ad.ctr_pct?.toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
