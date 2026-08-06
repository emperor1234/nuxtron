'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

interface Anomaly {
  type: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  recommendation: string;
}

interface LogFileResult {
  analysis_id: string;
  crawl_health_score: number;
  total_requests: number;
  bot_breakdown: Record<string, number>;
  anomalies: Anomaly[];
  url_efficiency: { crawled: number; wasted_crawl_budget_pct: number; top_wasted_urls: string[] };
  response_codes: Record<string, number>;
  bot_behavior: { respects_robots: boolean; crawl_rate_normal: boolean; suspicious_patterns: string[] };
  quick_wins: string[];
  recommended_tools: string[];
  domain: string;
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-green-100 text-green-800 border-green-200',
};

export default function LogFileAnalysisPage() {
  const [logSnippet, setLogSnippet] = useState('');
  const [domain, setDomain] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LogFileResult | null>(null);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await apiSend<LogFileResult>(
        '/seo-platform/log-file/analyze',
        'POST',
        { log_snippet: logSnippet.trim(), domain: domain.trim(), notes: notes.trim() },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  const score = result?.crawl_health_score ?? 0;
  const scoreColor = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Log File Analysis Engine</h1>
        <p className="text-gray-500 mt-1">Crawl-log ingestion, anomaly detection, and bot behavior analysis.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Log Snippet *</label>
          <textarea
            value={logSnippet}
            onChange={(e) => setLogSnippet(e.target.value)}
            rows={8}
            placeholder={`Paste your access log lines here, e.g.:\n66.249.64.13 - - [29/Apr/2026:02:14:01 +0000] "GET /blog/ HTTP/1.1" 200 4523 "-" "Googlebot/2.1"\n66.249.64.15 - - [29/Apr/2026:02:14:02 +0000] "GET /page/2/ HTTP/1.1" 200 3821 "-" "Googlebot/2.1"`}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Domain (optional)</label>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="e.g. example.com"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Additional context..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !logSnippet}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Analyzing logs…' : 'Analyze Log File'}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {result && (
        <div className="space-y-4">
          {(result.analysis_mode || result.cached) && (
            <div className="flex gap-2 flex-wrap">
              {result.analysis_mode && (
                <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${result.analysis_mode === 'llm' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                  {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                </span>
              )}
              {result.cached && (
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-sky-100 text-[var(--brand)]">Cached result</span>
              )}
            </div>
          )}
          {/* Scores */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-6">
            <div className="text-center">
              <div className={`text-4xl font-bold ${scoreColor}`}>{score}</div>
              <div className="text-xs text-gray-500 mt-1">Crawl Health</div>
            </div>
            <div className="flex-1 grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-xl font-semibold text-gray-800">{result.total_requests.toLocaleString()}</div>
                <div className="text-xs text-gray-500">Total Requests</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-gray-800">
                  {result.url_efficiency.wasted_crawl_budget_pct}%
                </div>
                <div className="text-xs text-gray-500">Budget Wasted</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-gray-800">{result.anomalies.length}</div>
                <div className="text-xs text-gray-500">Anomalies</div>
              </div>
              <div>
                <div
                  className={`text-xl font-semibold ${result.bot_behavior.crawl_rate_normal ? 'text-green-600' : 'text-red-600'}`}
                >
                  {result.bot_behavior.crawl_rate_normal ? 'Normal' : 'Abnormal'}
                </div>
                <div className="text-xs text-gray-500">Crawl Rate</div>
              </div>
            </div>
          </div>

          {/* Anomalies */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Anomalies Detected</h2>
            <div className="space-y-3">
              {result.anomalies.map((a, i) => (
                <div
                  key={`item-${i}`}
                  className={`border rounded-lg p-3 ${SEVERITY_COLORS[a.severity] ?? 'bg-gray-50'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold uppercase">{a.severity}</span>
                    <span className="text-xs font-mono bg-white bg-opacity-60 px-1.5 py-0.5 rounded">{a.type}</span>
                  </div>
                  <p className="text-sm font-medium">{a.description}</p>
                  <p className="text-xs mt-1 opacity-80">→ {a.recommendation}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Bot Breakdown + Response Codes */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Bot Breakdown</h2>
              <div className="space-y-2">
                {Object.entries(result.bot_breakdown).map(([bot, count]) => (
                  <div key={bot} className="flex justify-between items-center text-sm">
                    <span className="text-gray-700 capitalize">{bot.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-800">{Number(count).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Response Codes</h2>
              <div className="space-y-2">
                {Object.entries(result.response_codes).map(([code, count]) => {
                  const color = code.startsWith('2')
                    ? 'text-green-600'
                    : code.startsWith('3')
                      ? 'text-[var(--brand)]'
                      : code.startsWith('4')
                        ? 'text-orange-600'
                        : 'text-red-600';
                  return (
                    <div key={code} className="flex justify-between items-center text-sm">
                      <span className={`font-mono font-medium ${color}`}>{code}</span>
                      <span className="text-gray-800">{Number(count).toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Wasted Budget URLs */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Top Crawl Budget Wasters</h2>
            <div className="space-y-1">
              {result.url_efficiency.top_wasted_urls.map((url, i) => (
                <div key={`item-${i}`} className="text-sm font-mono text-gray-600 bg-gray-50 rounded px-2 py-1">
                  {url}
                </div>
              ))}
            </div>
          </div>

          {/* Bot Behavior */}
          {result.bot_behavior.suspicious_patterns.length > 0 && (
            <div className="bg-orange-50 rounded-xl border border-orange-200 p-6">
              <h2 className="text-base font-semibold text-orange-800 mb-3">Suspicious Bot Patterns</h2>
              <ul className="space-y-1">
                {result.bot_behavior.suspicious_patterns.map((p, i) => (
                  <li key={`item-${i}`} className="text-sm text-orange-700 flex gap-2">
                    <span>⚠</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Wins */}
          <div className="bg-green-50 rounded-xl border border-green-200 p-6">
            <h2 className="text-base font-semibold text-green-800 mb-3">Quick Wins</h2>
            <ul className="space-y-2">
              {result.quick_wins.map((w, i) => (
                <li key={`item-${i}`} className="flex items-start gap-2 text-sm text-green-700">
                  <span className="mt-0.5">✓</span>
                  {w}
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-[var(--muted)] text-right">
            Analyzed: {new Date(result.analyzed_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
