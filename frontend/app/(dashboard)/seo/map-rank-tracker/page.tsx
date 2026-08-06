'use client';

import { useState } from 'react';

interface GridPoint {
  row: number;
  col: number;
  lat: number;
  lng: number;
  rank: number;
  in_local_pack: boolean;
  weight: number;
}

interface GridData {
  keyword: string;
  center_lat: number;
  center_lng: number;
  grid_size: number;
  points: GridPoint[];
  avg_rank: number;
  in_top3_pct: number;
}

function rankColor(rank: number): string {
  if (rank <= 3) return 'bg-green-500 text-white';
  if (rank <= 7) return 'bg-yellow-400 text-white';
  if (rank <= 12) return 'bg-orange-400 text-white';
  return 'bg-red-500 text-white';
}

export default function MapRankTrackerPage() {
  const [keyword, setKeyword] = useState('');
  const [lat, setLat] = useState('40.7128');
  const [lng, setLng] = useState('-74.0060');
  const [gridSize, setGridSize] = useState(5);
  const [loading, setLoading] = useState(false);
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [error, setError] = useState('');

  async function runScan() {
    if (!keyword.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(
        `/api/map-rank-tracker/grid?keyword=${encodeURIComponent(keyword.trim())}&lat=${lat}&lng=${lng}&grid_size=${gridSize}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setGridData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Scan failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
          />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Map Rank Tracker</h1>
          <p className="text-sm text-gray-500">Google Maps / local pack rankings across a geographic grid</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Config */}
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Search Keyword</label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="plumber near me"
                className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
              <input
                type="number"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                step="0.0001"
                className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
              <input
                type="number"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                step="0.0001"
                className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Grid Size</label>
              <select
                value={gridSize}
                onChange={(e) => setGridSize(Number(e.target.value))}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                {[3, 5, 7, 9].map((n) => (
                  <option key={n} value={n}>
                    {n}×{n}
                  </option>
                ))}
              </select>
            </div>
            <div className="mt-5">
              <button
                onClick={runScan}
                disabled={loading || !keyword.trim()}
                className="bg-red-500 hover:bg-red-600 text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
              >
                {loading ? 'Scanning…' : 'Scan Grid'}
              </button>
            </div>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>

        {gridData && (
          <>
            {/* Metrics */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-xl border p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Avg Rank</p>
                <p className="text-2xl font-bold text-gray-800">{gridData.avg_rank?.toFixed(1)}</p>
              </div>
              <div className="bg-white rounded-xl border p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">In Top 3</p>
                <p className="text-2xl font-bold text-green-600">{gridData.in_top3_pct?.toFixed(0)}%</p>
              </div>
              <div className="bg-white rounded-xl border p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Grid Points</p>
                <p className="text-2xl font-bold text-gray-800">{gridData.points?.length}</p>
              </div>
            </div>

            {/* Grid Heatmap */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
              <h2 className="font-semibold text-gray-800 mb-4">Rank Grid — "{gridData.keyword}"</h2>
              <div className="flex justify-center">
                <div
                  className="grid gap-2"
                  style={{ gridTemplateColumns: `repeat(${gridData.grid_size}, minmax(0, 1fr))` }}
                >
                  {gridData.points.map((pt, i) => (
                    <div
                      key={i}
                      title={`Lat: ${pt.lat}, Lng: ${pt.lng}\nRank: #${pt.rank}`}
                      className={`w-12 h-12 rounded-lg flex items-center justify-center text-sm font-bold cursor-default transition-transform hover:scale-105 ${rankColor(pt.rank)}`}
                    >
                      {pt.rank}
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-center gap-4 mt-4 text-xs text-gray-500">
                {[
                  { label: 'Top 3', color: 'bg-green-500' },
                  { label: '4–7', color: 'bg-yellow-400' },
                  { label: '8–12', color: 'bg-orange-400' },
                  { label: '13+', color: 'bg-red-500' },
                ].map((leg) => (
                  <div key={leg.label} className="flex items-center gap-1">
                    <div className={`w-3 h-3 rounded ${leg.color}`} />
                    <span>{leg.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
