/**
 * Answer Engine Hub Dashboard
 *
 * Real-time brand mention tracking across 5 AI search engines
 * - Visibility score & trending direction
 * - Mentions by engine breakdown
 * - Sentiment analysis
 * - Top queries mentioning brand
 * - Competitor mentions
 */

'use client';

import { useState, useEffect } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

interface AnswerEngineInsight {
  total_mentions_7d: number;
  total_mentions_30d: number;
  trending_direction: string;
  visibility_score: number;
  mentions_by_engine: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  top_queries: string[];
  updated_at: string;
}

interface BrandMention {
  id: string;
  search_engine: string;
  query: string;
  answer_text: string;
  sentiment: string;
  confidence: number;
  timestamp: string;
}

export default function AnswerEngineHub() {
  const [selectedBrand, setSelectedBrand] = useState<string>('');
  const [insight, setInsight] = useState<AnswerEngineInsight | null>(null);
  const [mentions, setMentions] = useState<BrandMention[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [sentimentFilter, setSentimentFilter] = useState<string>('');
  const [engineFilter, setEngineFilter] = useState<string>('');

  // Fetch insight data
  const fetchInsight = async (brandName: string) => {
    try {
      setLoading(true);
      const response = await apiGet<AnswerEngineInsight>(
        `/api/v1/answer-engine/insights/${brandName}`,
        DEFAULT_TENANT_ID
      );
      setInsight(response);

      // Also fetch mentions
      const mentionsResponse = await apiGet<BrandMention[]>(
        `/api/v1/answer-engine/insights/${brandName}/mentions`,
        DEFAULT_TENANT_ID
      );
      setMentions(mentionsResponse);
    } catch (error) {
      console.error('Failed to fetch insight:', error);
    } finally {
      setLoading(false);
    }
  };

  // Trigger sync
  const handleSync = async () => {
    if (!selectedBrand) return;

    try {
      setSyncing(true);
      await apiSend(`/api/v1/answer-engine/sync/${selectedBrand}`, 'POST', undefined, DEFAULT_TENANT_ID);

      // Poll for results
      setTimeout(() => fetchInsight(selectedBrand), 2000);
    } catch (error) {
      console.error('Failed to trigger sync:', error);
    } finally {
      setSyncing(false);
    }
  };

  // Filter mentions
  const filteredMentions = mentions.filter((m) => {
    if (sentimentFilter && m.sentiment !== sentimentFilter) return false;
    if (engineFilter && m.search_engine !== engineFilter) return false;
    return true;
  });

  const getTrendingIcon = (direction: string) => {
    if (direction === 'up') return '📈';
    if (direction === 'down') return '📉';
    return '→';
  };

  const getSentimentColor = (sentiment: string) => {
    if (sentiment === 'positive') return 'text-green-600';
    if (sentiment === 'negative') return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Answer Engine Hub</h1>
            <p className="text-sm text-gray-600 mt-1">Track brand mentions across AI search engines</p>
          </div>
          <button
            onClick={handleSync}
            disabled={!selectedBrand || syncing}
            className="px-4 py-2 bg-[var(--brand)] text-white rounded-lg hover:bg-[var(--brand)] disabled:bg-gray-400"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </div>

      <div className="p-6">
        {/* Brand Selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Select Brand</label>
          <input
            type="text"
            value={selectedBrand}
            onChange={(e) => {
              setSelectedBrand(e.target.value);
              if (e.target.value) fetchInsight(e.target.value);
            }}
            placeholder="Enter brand name (e.g., Profound)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[var(--brand)] focus:border-transparent"
          />
        </div>

        {insight && (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {/* Visibility Score */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Visibility Score</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{insight.visibility_score.toFixed(1)}%</div>
                <div className="text-xs text-gray-500 mt-2">of AI responses</div>
              </div>

              {/* 7-Day Mentions */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Mentions (7d)</div>
                <div className="text-3xl font-bold text-green-600 mt-2">{insight.total_mentions_7d}</div>
                <div className="text-xs text-gray-500 mt-2">in past week</div>
              </div>

              {/* 30-Day Mentions */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Mentions (30d)</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{insight.total_mentions_30d}</div>
                <div className="text-xs text-gray-500 mt-2">in past month</div>
              </div>

              {/* Trending */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Trend</div>
                <div className="text-3xl font-bold mt-2">{getTrendingIcon(insight.trending_direction)}</div>
                <div className="text-xs text-gray-500 mt-2 capitalize">{insight.trending_direction}</div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Mentions by Engine */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Mentions by Engine</h3>
                <div className="space-y-3">
                  {Object.entries(insight.mentions_by_engine).map(([engine, count]) => (
                    <div key={engine}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">{engine}</span>
                        <span className="font-medium text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-[var(--brand)] h-2 rounded-full"
                          style={{
                            width: `${(count / Math.max(...Object.values(insight.mentions_by_engine))) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sentiment Breakdown */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment</h3>
                <div className="space-y-3">
                  {Object.entries(insight.sentiment_breakdown).map(([sentiment, count]) => (
                    <div key={sentiment}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className={`capitalize ${getSentimentColor(sentiment)}`}>{sentiment}</span>
                        <span className="font-medium text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            sentiment === 'positive'
                              ? 'bg-green-600'
                              : sentiment === 'negative'
                                ? 'bg-red-600'
                                : 'bg-gray-400'
                          }`}
                          style={{
                            width: `${(count / Math.max(...Object.values(insight.sentiment_breakdown))) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Top Queries */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Queries</h3>
              <div className="space-y-2">
                {insight.top_queries.slice(0, 5).map((query, idx) => (
                  <div key={idx} className="flex items-start p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium text-gray-500 mr-3">{idx + 1}.</span>
                    <span className="text-sm text-gray-700">{query}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Mentions List */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-4 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Mentions</h3>
                <div className="mt-3 flex gap-3">
                  <select
                    value={sentimentFilter}
                    onChange={(e) => setSentimentFilter(e.target.value)}
                    className="px-3 py-1 text-sm border border-gray-300 rounded"
                  >
                    <option value="">All Sentiments</option>
                    <option value="positive">Positive</option>
                    <option value="neutral">Neutral</option>
                    <option value="negative">Negative</option>
                  </select>
                  <select
                    value={engineFilter}
                    onChange={(e) => setEngineFilter(e.target.value)}
                    className="px-3 py-1 text-sm border border-gray-300 rounded"
                  >
                    <option value="">All Engines</option>
                    {Object.keys(insight.mentions_by_engine).map((engine) => (
                      <option key={engine} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="divide-y">
                {filteredMentions.map((mention) => (
                  <div key={mention.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {mention.search_engine}
                        </span>
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded capitalize ${
                            mention.sentiment === 'positive'
                              ? 'bg-green-100 text-green-800'
                              : mention.sentiment === 'negative'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {mention.sentiment}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">{new Date(mention.timestamp).toLocaleDateString()}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mb-1">Query: {mention.query}</p>
                    <p className="text-sm text-gray-600 line-clamp-2">{mention.answer_text}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        Confidence: {(mention.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {!selectedBrand && (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="text-[var(--muted)] text-4xl mb-2">🔍</div>
            <p className="text-gray-600">Enter a brand name to start tracking Answer Engine visibility</p>
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="animate-spin text-4xl mb-2">⏳</div>
            <p className="text-gray-600">Loading insight data...</p>
          </div>
        )}
      </div>
    </div>
  );
}
