'use client';

import { useState } from 'react';

interface HeatmapPoint {
  lat: number;
  lng: number;
  rank: number;
  in_top_3: boolean;
  in_top_10: boolean;
  weight: number;
  row: number;
  col: number;
}

interface ScanResult {
  scan_id?: string;
  id?: string;
  business_name: string;
  keyword: string;
  center_lat: number;
  center_lng: number;
  grid_size: number;
  avg_rank: number;
  best_rank: number;
  worst_rank: number;
  top3_pct: number;
  top10_pct: number;
  visibility_score: number;
  total_points: number;
  status: string;
}

interface ScanWithGrid extends ScanResult {
  grid: HeatmapPoint[];
}

function cellColor(rank: number) {
  if (rank <= 3) return '#22c55e';
  if (rank <= 7) return '#eab308';
  if (rank <= 12) return '#f97316';
  return '#ef4444';
}

export default function LocalHeatmapPage() {
  const [businessName, setBusinessName] = useState('');
  const [keyword, setKeyword] = useState('');
  const [lat, setLat] = useState('40.7128');
  const [lng, setLng] = useState('-74.0060');
  const [gridSize, setGridSize] = useState(5);
  const [radiusKm, setRadiusKm] = useState(5);
  const [loading, setLoading] = useState(false);
  const [scan, setScan] = useState<ScanWithGrid | null>(null);
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [activeTab, setActiveTab] = useState<'scan' | 'history'>('scan');
  const [error, setError] = useState('');

  async function runScan() {
    if (!businessName.trim() || !keyword.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/local-heatmap/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_name: businessName.trim(),
          keyword: keyword.trim(),
          center_lat: parseFloat(lat),
          center_lng: parseFloat(lng),
          grid_size: gridSize,
          radius_km: radiusKm,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const scanMeta: ScanResult = await res.json();
      // Fetch full grid
      const sid = scanMeta.id || scanMeta.scan_id;
      const gridRes = await fetch(`/api/local-heatmap/results/${sid}`);
      const gridData: { grid: HeatmapPoint[] } & ScanResult = await gridRes.json();
      setScan({ ...scanMeta, ...gridData });
      setScans((prev) => [scanMeta, ...prev]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Scan failed');
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    const res = await fetch('/api/local-heatmap/history');
    if (res.ok) {
      const data = await res.json();
      setScans(data.history || []);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-[var(--brand)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Local Heatmap</h1>
          <p className="text-sm text-gray-500">Geo-grid visibility heatmap for local pack rankings</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {[
            { id: 'scan', label: 'New Scan' },
            { id: 'history', label: 'Scan History' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id as 'scan' | 'history');
                if (t.id === 'history') loadHistory();
              }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium ${activeTab === t.id ? 'bg-white shadow text-[var(--brand)]' : 'text-gray-600'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === 'scan' && (
          <>
            <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
                  <input
                    type="text"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="Your Business Name"
                    className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Keyword</label>
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="plumber near me"
                    className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Center Latitude</label>
                  <input
                    type="number"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    step="0.0001"
                    className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Center Longitude</label>
                  <input
                    type="number"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                    step="0.0001"
                    className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Grid Size</label>
                  <select
                    value={gridSize}
                    onChange={(e) => setGridSize(Number(e.target.value))}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  >
                    {[3, 5, 7, 9].map((n) => (
                      <option key={n} value={n}>
                        {n}×{n}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Radius (km)</label>
                  <select
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(Number(e.target.value))}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  >
                    {[1, 2, 5, 10, 20].map((n) => (
                      <option key={n} value={n}>
                        {n} km
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={runScan}
                disabled={loading || !businessName.trim() || !keyword.trim()}
                className="bg-[var(--brand)] hover:bg-[var(--brand)] text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
              >
                {loading ? 'Scanning…' : 'Generate Heatmap'}
              </button>
              {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
            </div>

            {scan && (
              <>
                {/* Metrics */}
                <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
                  {[
                    { label: 'Avg Rank', value: scan.avg_rank?.toFixed(1) },
                    { label: 'Best Rank', value: `#${scan.best_rank}` },
                    { label: 'Worst Rank', value: `#${scan.worst_rank}` },
                    { label: 'Top 3 %', value: `${scan.top3_pct?.toFixed(0)}%` },
                    { label: 'Top 10 %', value: `${scan.top10_pct?.toFixed(0)}%` },
                    { label: 'Visibility', value: `${scan.visibility_score?.toFixed(0)}%` },
                  ].map((m) => (
                    <div key={m.label} className="bg-white rounded-xl border p-3 text-center">
                      <p className="text-xs text-gray-500">{m.label}</p>
                      <p className="text-lg font-bold text-gray-800">{m.value}</p>
                    </div>
                  ))}
                </div>

                {/* Heatmap Grid */}
                <div className="bg-white rounded-xl border shadow-sm p-6">
                  <h2 className="font-semibold text-gray-800 mb-4">Visibility Heatmap — "{scan.keyword}"</h2>
                  <div className="flex justify-center">
                    <div
                      className="grid gap-2"
                      style={{ gridTemplateColumns: `repeat(${scan.grid_size}, minmax(0, 1fr))` }}
                    >
                      {scan.grid?.map((pt, i) => (
                        <div
                          key={i}
                          title={`Lat: ${pt.lat}\nLng: ${pt.lng}\nRank: #${pt.rank}`}
                          className="w-12 h-12 rounded-lg flex items-center justify-center text-sm font-bold text-[var(--text)] cursor-default hover:scale-110 transition-transform"
                          style={{ backgroundColor: cellColor(pt.rank) }}
                        >
                          {pt.rank}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-center gap-4 mt-4 text-xs text-gray-500">
                    {[
                      { c: '#22c55e', l: 'Top 3' },
                      { c: '#eab308', l: '4–7' },
                      { c: '#f97316', l: '8–12' },
                      { c: '#ef4444', l: '13+' },
                    ].map((leg) => (
                      <div key={leg.l} className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded" style={{ backgroundColor: leg.c }} />
                        {leg.l}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {activeTab === 'history' && (
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-4">Scan History</h2>
            {scans.length === 0 ? (
              <p className="text-[var(--muted)] text-sm text-center py-8">No scans yet</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-gray-500 uppercase">
                    <th className="py-2 text-left">Business</th>
                    <th className="py-2 text-left">Keyword</th>
                    <th className="py-2 text-right">Avg Rank</th>
                    <th className="py-2 text-right">Top 3%</th>
                    <th className="py-2 text-right">Visibility</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((s, i) => (
                    <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-2.5 font-medium">{s.business_name}</td>
                      <td className="py-2.5 text-gray-600">{s.keyword}</td>
                      <td className="py-2.5 text-right">{s.avg_rank?.toFixed(1)}</td>
                      <td className="py-2.5 text-right text-green-600">{s.top3_pct?.toFixed(0)}%</td>
                      <td className="py-2.5 text-right font-semibold">{s.visibility_score?.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
