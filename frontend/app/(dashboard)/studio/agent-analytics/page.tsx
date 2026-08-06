/**
 * Agent Analytics Dashboard
 *
 * Real-time tracking of AI bot traffic:
 * - ChatGPT, Gemini, Perplexity, Claude bots
 * - Pages crawled by each bot
 * - Geographic distribution
 * - HTTP status codes
 * - Period comparison
 */

'use client';

import { useState, useEffect } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

interface DashboardData {
  period_days: number;
  total_requests: number;
  unique_bots: number;
  total_crawled_pages: number;
  requests_by_bot: Array<{ bot: string; count: number }>;
  avg_response_time_ms: number;
  total_bandwidth_gb: number;
  top_pages: string[];
  status_codes: Array<{ code: number; count: number }>;
}

interface BotDetails {
  bot_name: string;
  total_visits: number;
  pages: Array<{
    path: string;
    count: number;
    status_codes: Record<string, number>;
  }>;
  hourly_distribution: Record<string, number>;
  first_seen: string;
  last_seen: string;
}

export default function AgentAnalyticsDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [selectedBot, setSelectedBot] = useState<string | null>(null);
  const [botDetails, setBotDetails] = useState<BotDetails | null>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);

  // Fetch dashboard
  useEffect(() => {
    fetchDashboard();
  }, [days]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await apiGet<DashboardData>(`/api/v1/agent-analytics/dashboard?days=${days}`, DEFAULT_TENANT_ID);
      setDashboard(response);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBotDetails = async (botName: string) => {
    try {
      const response = await apiGet<BotDetails>(
        `/api/v1/agent-analytics/bots/${botName}?days=${days}`,
        DEFAULT_TENANT_ID
      );
      setBotDetails(response);
      setSelectedBot(botName);
    } catch (error) {
      console.error('Failed to fetch bot details:', error);
    }
  };

  const getBotIcon = (bot: string) => {
    const icons: Record<string, string> = {
      ChatGPT: '🤖',
      Gemini: '🔮',
      Perplexity: '🔎',
      Claude: '🧠',
      'Brave Search': '🦁',
      GoogleBot: '🔍',
      BingBot: 'Ⓑ',
      CCBot: '🕷️',
      AmazonBot: '📦',
    };
    return icons[bot] || '🤖';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Agent Analytics</h1>
            <p className="text-sm text-gray-600 mt-1">Real-time AI bot traffic tracking</p>
          </div>
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      <div className="p-6">
        {dashboard ? (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {/* Total Requests */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Total Bot Requests</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{dashboard.total_requests.toLocaleString()}</div>
                <div className="text-xs text-gray-500 mt-2">in {days} days</div>
              </div>

              {/* Unique Bots */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Unique Bots</div>
                <div className="text-3xl font-bold text-green-600 mt-2">{dashboard.unique_bots}</div>
                <div className="text-xs text-gray-500 mt-2">detected</div>
              </div>

              {/* Pages Crawled */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Pages Crawled</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{dashboard.total_crawled_pages}</div>
                <div className="text-xs text-gray-500 mt-2">unique paths</div>
              </div>

              {/* Avg Response Time */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Avg Response Time</div>
                <div className="text-3xl font-bold text-orange-600 mt-2">
                  {dashboard.avg_response_time_ms.toFixed(0)}ms
                </div>
                <div className="text-xs text-gray-500 mt-2">per request</div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Requests by Bot */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Requests by Bot</h3>
                <div className="space-y-3">
                  {dashboard.requests_by_bot.map(({ bot, count }) => (
                    <button
                      key={bot}
                      onClick={() => fetchBotDetails(bot)}
                      className={`w-full text-left p-3 rounded-lg transition ${
                        selectedBot === bot
                          ? 'bg-blue-50 border-2 border-[var(--brand)]'
                          : 'bg-gray-50 border-2 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-900">
                          <span className="text-lg mr-2">{getBotIcon(bot)}</span>
                          {bot}
                        </span>
                        <span className="text-sm font-bold text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div
                          className="bg-[var(--brand)] h-2 rounded-full"
                          style={{
                            width: `${(count / Math.max(...dashboard.requests_by_bot.map((b) => b.count))) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Status Codes */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">HTTP Status Codes</h3>
                <div className="space-y-3">
                  {dashboard.status_codes.map(({ code, count }) => (
                    <div key={code}>
                      <div className="flex justify-between text-sm mb-1">
                        <span
                          className={`font-medium ${
                            code < 300
                              ? 'text-green-600'
                              : code < 400
                                ? 'text-[var(--brand)]'
                                : code < 500
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                          }`}
                        >
                          {code}
                        </span>
                        <span className="text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            code < 300
                              ? 'bg-green-600'
                              : code < 400
                                ? 'bg-[var(--brand)]'
                                : code < 500
                                  ? 'bg-yellow-600'
                                  : 'bg-red-600'
                          }`}
                          style={{
                            width: `${(count / Math.max(...dashboard.status_codes.map((s) => s.count))) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Top Pages */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Pages Crawled</h3>
              <div className="space-y-2">
                {dashboard.top_pages.slice(0, 10).map((page, idx) => (
                  <div key={idx} className="flex items-center p-3 bg-gray-50 rounded hover:bg-gray-100">
                    <span className="text-sm font-medium text-gray-500 mr-3 min-w-6">{idx + 1}.</span>
                    <span className="text-sm text-gray-700 truncate">{page}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Bot Details */}
            {botDetails && (
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {getBotIcon(botDetails.bot_name)} {botDetails.bot_name} Details
                  </h3>
                  <button
                    onClick={() => {
                      setSelectedBot(null);
                      setBotDetails(null);
                    }}
                    className="text-[var(--muted)] hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="p-3 bg-blue-50 rounded">
                    <div className="text-sm text-[var(--brand)]">Total Visits</div>
                    <div className="text-2xl font-bold text-blue-900">{botDetails.total_visits}</div>
                  </div>
                  <div className="p-3 bg-green-50 rounded">
                    <div className="text-sm text-green-600">First Seen</div>
                    <div className="text-sm text-green-900">{new Date(botDetails.first_seen).toLocaleDateString()}</div>
                  </div>
                  <div className="p-3 bg-purple-50 rounded">
                    <div className="text-sm text-[var(--brand)]">Last Seen</div>
                    <div className="text-sm text-purple-900">{new Date(botDetails.last_seen).toLocaleDateString()}</div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h4 className="font-semibold text-gray-900 mb-3">Top Pages for {botDetails.bot_name}</h4>
                  <div className="space-y-2">
                    {botDetails.pages.slice(0, 5).map((page, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-sm font-medium text-gray-900">{page.path}</span>
                          <span className="text-xs font-bold text-gray-600">{page.count}</span>
                        </div>
                        <div className="flex gap-1 flex-wrap">
                          {Object.entries(page.status_codes).map(([code, cnt]) => (
                            <span key={code} className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded">
                              {code}: {cnt}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="animate-spin text-4xl mb-2">⏳</div>
            <p className="text-gray-600">Loading analytics data...</p>
          </div>
        )}
      </div>
    </div>
  );
}
