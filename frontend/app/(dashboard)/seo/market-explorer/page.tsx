'use client';

import { useState } from 'react';

interface TopPlayer {
  domain: string;
  market_share_pct: number;
  monthly_visits: number;
  traffic_change_pct: number;
  top_category: string;
  authority_score?: number;
}

interface GrowthPoint {
  domain: string;
  traffic_growth_pct: number;
  market_share_pct: number;
  quadrant: 'Leaders' | 'Game Changers' | 'Niche Players' | 'Emerging';
}

const QUADRANT_COLORS: Record<string, string> = {
  Leaders: 'bg-blue-100 text-blue-800',
  'Game Changers': 'bg-green-100 text-green-800',
  'Niche Players': 'bg-yellow-100 text-yellow-800',
  Emerging: 'bg-purple-100 text-purple-800',
};

export default function MarketExplorerPage() {
  const [domain, setDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [topPlayers, setTopPlayers] = useState<TopPlayer[]>([]);
  const [growthData, setGrowthData] = useState<GrowthPoint[]>([]);
  const [error, setError] = useState('');
  const [analysed, setAnalysed] = useState(false);

  async function analyze() {
    if (!domain.trim()) return;
    setLoading(true);
    setError('');
    try {
      const [playersRes, growthRes] = await Promise.all([
        fetch(`/api/market-explorer/top-players?domain=${encodeURIComponent(domain.trim())}`),
        fetch(`/api/market-explorer/growth-quadrant?domain=${encodeURIComponent(domain.trim())}`),
      ]);
      const [players, growth] = await Promise.all([playersRes.json(), growthRes.json()]);
      setTopPlayers(players.players || players.top_players || []);
      setGrowthData(growth.quadrant || growth.players || []);
      setAnalysed(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  const fmt = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(0)}K` : String(n);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 004 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Market Explorer</h1>
          <p className="text-sm text-gray-500">Market size, top players, growth quadrant, audience overlap</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Explore Market Around Domain</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && analyze()}
              placeholder="e.g. semrush.com"
              className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-teal-400 focus:outline-none"
            />
            <button
              onClick={analyze}
              disabled={loading || !domain.trim()}
              className="bg-teal-600 hover:bg-teal-700 text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
            >
              {loading ? 'Exploring…' : 'Explore Market'}
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>

        {analysed && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Players */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
              <h2 className="font-semibold text-gray-800 mb-4">Top Market Players</h2>
              <div className="space-y-3">
                {topPlayers.slice(0, 10).map((p, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-[var(--muted)] w-5 text-center">{i + 1}</span>
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{p.domain}</p>
                        <p className="text-xs text-[var(--muted)]">{p.top_category}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-sm">{fmt(p.monthly_visits)} visits</p>
                      <p
                        className={`text-xs font-medium ${p.traffic_change_pct >= 0 ? 'text-green-600' : 'text-red-500'}`}
                      >
                        {p.traffic_change_pct >= 0 ? '+' : ''}
                        {p.traffic_change_pct?.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Growth Quadrant */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
              <h2 className="font-semibold text-gray-800 mb-4">Growth Quadrant</h2>
              <div className="grid grid-cols-2 gap-3">
                {(['Leaders', 'Game Changers', 'Niche Players', 'Emerging'] as const).map((q) => {
                  const members = growthData.filter((d) => d.quadrant === q);
                  return (
                    <div key={q} className="border rounded-lg p-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${QUADRANT_COLORS[q]}`}>{q}</span>
                      <ul className="mt-2 space-y-1">
                        {members.slice(0, 4).map((m, i) => (
                          <li key={i} className="text-xs text-gray-700 truncate">
                            {m.domain}
                          </li>
                        ))}
                        {members.length === 0 && <li className="text-xs text-[var(--muted)] italic">No data</li>}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
