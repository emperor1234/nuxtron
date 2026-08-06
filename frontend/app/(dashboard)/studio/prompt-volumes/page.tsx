/**
 * Prompt Volumes Dashboard
 *
 * Keyword analytics and opportunity discovery:
 * - Trending keywords
 * - Question analysis
 * - Long-tail phrases
 * - Competitor mentions
 * - Emerging opportunities
 */

'use client';

import { useState, useEffect } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

interface KeywordData {
  keyword: string;
  volume: number;
  relevance?: number;
  sources?: string[];
  type?: string;
}

interface AnalysisData {
  period_days: number;
  total_unique_keywords: number;
  total_prompt_volume: number;
  trending_count: number;
  question_keywords: KeywordData[];
  long_tail_keywords: KeywordData[];
  branded_keywords: KeywordData[];
  competitor_keywords: KeywordData[];
  trending: KeywordData[];
  emerging: KeywordData[];
  by_source: Record<string, number>;
  top_words: Array<{ word: string; count: number }>;
}

export default function PromptVolumesDashboard() {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [brandName, setBrandName] = useState('');
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'trending' | 'questions' | 'opportunities' | 'competitors'>('trending');

  const fetchAnalysis = async () => {
    if (!brandName) return;

    try {
      setLoading(true);
      const response = await apiGet<AnalysisData>(
        `/api/v1/prompt-volumes/analysis?days=${days}&brand_name=${brandName}`,
        DEFAULT_TENANT_ID
      );
      setAnalysis(response);
    } catch (error) {
      console.error('Failed to fetch analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAnalysis();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prompt Volumes</h1>
          <p className="text-sm text-gray-600 mt-1">Track search keywords and discover AI search opportunities</p>
        </div>
      </div>

      <div className="p-6">
        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="Enter brand name (e.g., Profound)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[var(--brand)]"
              />
              <select
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>
              <button type="submit" className="px-4 py-2 bg-[var(--brand)] text-white rounded-lg hover:bg-[var(--brand)]">
                Analyze
              </button>
            </div>
          </div>
        </form>

        {analysis ? (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Unique Keywords</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{analysis.total_unique_keywords}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Total Volume</div>
                <div className="text-3xl font-bold text-green-600 mt-2">
                  {analysis.total_prompt_volume.toLocaleString()}
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Trending Keywords</div>
                <div className="text-3xl font-bold text-[var(--brand)] mt-2">{analysis.trending_count}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Top Source</div>
                <div className="text-2xl font-bold text-orange-600 mt-2">
                  {Object.entries(analysis.by_source).length > 0
                    ? Object.entries(analysis.by_source).sort((a, b) => b[1] - a[1])[0][0]
                    : 'N/A'}
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="bg-white rounded-lg shadow mb-6">
              <div className="flex border-b border-gray-200">
                {[
                  { id: 'trending', label: '📈 Trending', count: analysis.trending.length },
                  { id: 'questions', label: '❓ Questions', count: analysis.question_keywords.length },
                  { id: 'opportunities', label: '🎯 Opportunities', count: analysis.long_tail_keywords.length },
                  { id: 'competitors', label: '👥 Competitors', count: analysis.competitor_keywords.length },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition ${
                      activeTab === tab.id
                        ? 'border-[var(--brand)] text-[var(--brand)]'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {tab.label} ({tab.count})
                  </button>
                ))}
              </div>

              <div className="p-4">
                {activeTab === 'trending' && (
                  <div className="space-y-3">
                    {analysis.trending.slice(0, 10).map((kw, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-gradient-to-r from-orange-50 to-red-50 rounded-lg border-l-4 border-orange-600"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium text-gray-900">{kw.keyword}</span>
                          <span className="text-xs font-bold text-orange-600">📈 {kw.volume} searches</span>
                        </div>
                        <div className="text-xs text-gray-600">Sources: {kw.sources?.join(', ') || 'Unknown'}</div>
                      </div>
                    ))}
                    {analysis.trending.length === 0 && (
                      <div className="text-center py-8 text-gray-500">No trending keywords yet</div>
                    )}
                  </div>
                )}

                {activeTab === 'questions' && (
                  <div className="space-y-3">
                    {analysis.question_keywords.slice(0, 10).map((kw, idx) => (
                      <div key={idx} className="p-3 bg-blue-50 rounded-lg border-l-4 border-[var(--brand)]">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium text-gray-900">{kw.keyword}</span>
                          <span className="text-xs font-bold text-[var(--brand)]">{kw.volume}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-[var(--brand)] h-2 rounded-full"
                              style={{
                                width: `${(kw.relevance || 0) * 100}%`,
                              }}
                            ></div>
                          </div>
                          <span className="text-xs text-gray-600">
                            {((kw.relevance || 0) * 100).toFixed(0)}% relevant
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'opportunities' && (
                  <div className="space-y-3">
                    {analysis.long_tail_keywords.slice(0, 10).map((kw, idx) => (
                      <div key={idx} className="p-3 bg-green-50 rounded-lg border-l-4 border-green-600">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium text-gray-900">{kw.keyword}</span>
                          <span className="text-xs font-bold text-green-600">💡 {kw.volume} volume</span>
                        </div>
                        <div className="text-xs text-gray-600">
                          {kw.keyword.split(' ').length}-word phrase • Untapped opportunity
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'competitors' && (
                  <div className="space-y-3">
                    {analysis.competitor_keywords.slice(0, 10).map((kw, idx) => (
                      <div key={idx} className="p-3 bg-red-50 rounded-lg border-l-4 border-red-600">
                        <div className="flex justify-between items-start">
                          <span className="font-medium text-gray-900">{kw.keyword}</span>
                          <span className="text-xs font-bold text-red-600">👥 {kw.volume}</span>
                        </div>
                      </div>
                    ))}
                    {analysis.competitor_keywords.length === 0 && (
                      <div className="text-center py-8 text-gray-500">No competitor keywords detected</div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Top Words Cloud */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Words</h3>
              <div className="flex flex-wrap gap-2">
                {analysis.top_words.slice(0, 30).map((item, idx) => {
                  const maxCount = Math.max(...analysis.top_words.map((w) => w.count));
                  const size = 0.8 + (item.count / maxCount) * 1.2;
                  return (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium hover:bg-blue-200 cursor-default"
                      style={{ fontSize: `${size}rem` }}
                    >
                      {item.word}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Sources */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Volume by Source</h3>
              <div className="space-y-3">
                {Object.entries(analysis.by_source).map(([source, volume]) => (
                  <div key={source}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{source}</span>
                      <span className="font-bold text-gray-900">{volume}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-blue-600 to-purple-600 h-3 rounded-full"
                        style={{
                          width: `${(volume / Math.max(...Object.values(analysis.by_source))) * 100}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="text-[var(--muted)] text-4xl mb-2">🔍</div>
            <p className="text-gray-600">Enter a brand name to analyze prompt volumes</p>
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="animate-spin text-4xl mb-2">⏳</div>
            <p className="text-gray-600">Analyzing keywords...</p>
          </div>
        )}
      </div>
    </div>
  );
}
