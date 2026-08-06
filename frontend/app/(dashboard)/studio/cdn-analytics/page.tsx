/**
 * CDN Analytics Dashboard
 *
 * Multi-CDN traffic monitoring and cost optimization:
 * - Real-time metrics from 9 providers (Vercel, CloudFront, Fastly, Netlify, Akamai, Google CDN, Cloudflare, Stackpath, Imperva)
 * - Performance comparison
 * - Cost analysis & optimization
 * - Failover & load distribution
 */

'use client';

import { useState, useEffect } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

interface ProviderMetrics {
  total_requests: number;
  bandwidth_gb: number;
  cache_hit_ratio: number;
  avg_latency_ms: number;
  error_rate: number;
  threat_count: number;
}

interface DashboardData {
  period_days: number;
  providers: Record<string, ProviderMetrics>;
  comparison: {
    fastest_provider: string;
    best_cache_hit: string;
    highest_traffic: string;
    most_reliable: string;
    metrics: {
      avg_latency_ms: number;
      avg_cache_hit_ratio: number;
      total_requests: number;
      total_threats: number;
    };
  };
  costs: Record<string, number>;
  recommendations: Array<{
    priority: string;
    category: string;
    recommendation: string;
  }>;
}

export default function CDNAnalyticsDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [providerDetails, setProviderDetails] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'overview' | 'comparison' | 'costs' | 'recommendations'>('overview');

  useEffect(() => {
    fetchDashboard();
  }, [days]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await apiGet<DashboardData>(`/api/v1/cdn/dashboard?days=${days}`, DEFAULT_TENANT_ID);
      setDashboard(response);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProviderDetails = async (provider: string) => {
    try {
      const response = await apiGet(`/api/v1/cdn/provider/${provider}?days=${days}`, DEFAULT_TENANT_ID);
      setProviderDetails(response);
      setSelectedProvider(provider);
    } catch (error) {
      console.error('Failed to fetch provider details:', error);
    }
  };

  const getCDNIcon = (provider: string) => {
    const icons: Record<string, string> = {
      vercel: '▲',
      cloudfront: '☁️',
      fastly: '⚡',
      netlify: '🌐',
      akamai: '🛡️',
      'google-cdn': '🔵',
      cloudflare: '🟠',
      stackpath: '📦',
      imperva: '🔐',
    };
    return icons[provider] || '📡';
  };

  const getRecommendationTone = (priority: string) => {
    if (priority === 'high') {
      return {
        card: 'bg-red-50 border-l-red-600',
        badge: 'bg-red-200 text-red-800',
      };
    }
    if (priority === 'medium') {
      return {
        card: 'bg-yellow-50 border-l-yellow-600',
        badge: 'bg-yellow-200 text-yellow-800',
      };
    }
    return {
      card: 'bg-blue-50 border-l-blue-600',
      badge: 'bg-blue-200 text-blue-800',
    };
  };

  if (loading && !dashboard) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-2">⏳</div>
          <p className="text-gray-600">Loading CDN analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CDN Analytics</h1>
            <p className="text-sm text-gray-600 mt-1">Multi-CDN traffic monitoring & optimization</p>
          </div>
          <select
            value={days}
            onChange={(e) => setDays(Number.parseInt(e.target.value, 10))}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-t pt-4">
          {(['overview', 'comparison', 'costs', 'recommendations'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 font-medium text-sm rounded-lg transition ${
                tab === t ? 'bg-blue-100 text-blue-900' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {tab === 'overview' && dashboard && (
          <>
            {/* Provider Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {Object.entries(dashboard.providers).map(([provider, metrics]) => (
                <button
                  key={provider}
                  onClick={() => fetchProviderDetails(provider)}
                  className={`p-4 rounded-lg border-2 transition text-left ${
                    selectedProvider === provider
                      ? 'border-[var(--brand)] bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-2">{getCDNIcon(provider)}</div>
                  <div className="font-semibold text-gray-900 capitalize mb-1">{provider}</div>
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>Requests: {(metrics.total_requests / 1000).toFixed(0)}K</div>
                    <div>Cache Hit: {(metrics.cache_hit_ratio * 100).toFixed(1)}%</div>
                    <div>Latency: {metrics.avg_latency_ms}ms</div>
                  </div>
                </button>
              ))}
            </div>

            {/* Provider Details */}
            {providerDetails && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {getCDNIcon(selectedProvider ?? 'cdn')} {(selectedProvider ?? 'cdn').toUpperCase()} Details
                  </h3>
                  <button
                    onClick={() => {
                      setSelectedProvider(null);
                      setProviderDetails(null);
                    }}
                    className="text-[var(--muted)] hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  {[
                    { label: 'Total Requests', value: providerDetails.summary.total_requests.toLocaleString() },
                    { label: 'Bandwidth', value: `${providerDetails.summary.bandwidth_gb.toFixed(1)} GB` },
                    { label: 'Cache Hit', value: `${(providerDetails.summary.cache_hit_ratio * 100).toFixed(1)}%` },
                    { label: 'Avg Latency', value: `${providerDetails.summary.avg_latency_ms}ms` },
                    { label: 'Error Rate', value: `${(providerDetails.summary.error_rate * 100).toFixed(2)}%` },
                    { label: 'Threats', value: providerDetails.summary.threats },
                  ].map((stat) => (
                    <div key={stat.label} className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-600 font-medium">{stat.label}</div>
                      <div className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</div>
                    </div>
                  ))}
                </div>

                {/* Regional Breakdown */}
                <div className="border-t pt-4">
                  <h4 className="font-semibold text-gray-900 mb-3">Regional Distribution</h4>
                  <div className="space-y-2">
                    {providerDetails.by_region?.map((region: any) => (
                      <div key={`${region.region}-${region.country}`} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex justify-between items-start mb-2">
                          <span className="font-medium text-gray-900">
                            {region.region} ({region.country})
                          </span>
                          <span className="text-sm text-gray-600">{region.requests.toLocaleString()} req</span>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-600">
                          <span>Cache: {(region.cache_hit * 100).toFixed(1)}%</span>
                          <span>Latency: {region.latency_ms}ms</span>
                          <span>Error: {(region.error_rate * 100).toFixed(2)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Paths */}
                <div className="border-t pt-4 mt-4">
                  <h4 className="font-semibold text-gray-900 mb-3">Top Paths</h4>
                  <div className="space-y-2">
                    {providerDetails.top_paths?.map((path: any) => (
                      <div key={path.path} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <span className="text-sm text-gray-900 font-medium">{path.path}</span>
                        <span className="text-sm text-gray-600">{path.requests.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {tab === 'comparison' && dashboard?.comparison && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Provider Comparison</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-[var(--brand)] font-medium">Fastest Provider</div>
                <div className="text-2xl font-bold text-blue-900 mt-1">{dashboard.comparison.fastest_provider}</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm text-green-600 font-medium">Best Cache Hit</div>
                <div className="text-2xl font-bold text-green-900 mt-1">{dashboard.comparison.best_cache_hit}</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-sm text-[var(--brand)] font-medium">Highest Traffic</div>
                <div className="text-2xl font-bold text-purple-900 mt-1">{dashboard.comparison.highest_traffic}</div>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                <div className="text-sm text-orange-600 font-medium">Most Reliable</div>
                <div className="text-2xl font-bold text-orange-900 mt-1">{dashboard.comparison.most_reliable}</div>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="font-semibold text-gray-900 mb-3">Average Metrics</h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">Average Latency</span>
                    <span className="font-bold">{dashboard.comparison.metrics.avg_latency_ms}ms</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-[var(--brand)] h-2 rounded-full"
                      style={{ width: `${Math.min(dashboard.comparison.metrics.avg_latency_ms / 200, 1) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">Average Cache Hit</span>
                    <span className="font-bold">
                      {(dashboard.comparison.metrics.avg_cache_hit_ratio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${dashboard.comparison.metrics.avg_cache_hit_ratio * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'costs' && dashboard?.costs && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Analysis</h3>

            <div className="space-y-3 mb-6">
              {Object.entries(dashboard.costs).map(([provider, cost]) => (
                <div key={provider} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getCDNIcon(provider)}</span>
                    <div>
                      <div className="font-medium text-gray-900 capitalize">{provider}</div>
                      <div className="text-xs text-gray-600">Monthly estimate</div>
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-gray-900">${cost.toFixed(2)}</div>
                </div>
              ))}
            </div>

            <div className="border-t pt-4">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm text-green-600 font-medium">Total Monthly Cost</div>
                <div className="text-3xl font-bold text-green-900 mt-1">
                  $
                  {Object.values(dashboard.costs)
                    .reduce((a, b) => a + b, 0)
                    .toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'recommendations' && dashboard?.recommendations && (
          <div className="space-y-3">
            {dashboard.recommendations.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <div className="text-2xl mb-2">✨</div>
                <p className="text-gray-600">Your CDN setup is optimized!</p>
              </div>
            ) : (
              dashboard.recommendations.map((rec) => {
                const tone = getRecommendationTone(rec.priority);
                return (
                  <div
                    key={`${rec.category}-${rec.recommendation}`}
                    className={`p-4 rounded-lg border-l-4 ${tone.card}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="font-semibold text-gray-900">{rec.recommendation}</div>
                      <span className={`text-xs font-bold px-2 py-1 rounded capitalize ${tone.badge}`}>
                        {rec.priority}
                      </span>
                    </div>
                    <div className="text-xs text-gray-600">{rec.category}</div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
