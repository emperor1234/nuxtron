'use client';

import { useState } from 'react';

interface Monitor {
  id: string;
  domain: string;
  label: string;
  status: string;
  created_at: string;
}

interface FeedEvent {
  id: string;
  domain: string;
  event_type: string;
  detected_at: string;
  severity: 'info' | 'warning' | 'critical';
  details: Record<string, unknown>;
}

const EVENT_ICONS: Record<string, string> = {
  content_published: '📄',
  ad_started: '📣',
  ad_stopped: '🔇',
  keyword_rank_change: '📈',
  backlink_acquired: '🔗',
  page_changed: '✏️',
  meta_changed: '🏷️',
  social_post: '💬',
  pricing_changed: '💰',
};

const SEVERITY_STYLES: Record<string, string> = {
  info: 'bg-blue-50 border-blue-200',
  warning: 'bg-yellow-50 border-yellow-200',
  critical: 'bg-red-50 border-red-200',
};

const BADGE_STYLES: Record<string, string> = {
  info: 'bg-blue-100 text-[var(--brand)]',
  warning: 'bg-yellow-100 text-yellow-700',
  critical: 'bg-red-100 text-red-700',
};

export default function EyeOnPage() {
  const [newDomain, setNewDomain] = useState('');
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [feedLoading, setFeedLoading] = useState(false);
  const [error, setError] = useState('');

  async function addMonitor() {
    if (!newDomain.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/eyeon/monitors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: newDomain.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const mon = await res.json();
      setMonitors((prev) => [...prev, mon]);
      setNewDomain('');
      await loadFeed();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to add monitor');
    } finally {
      setLoading(false);
    }
  }

  async function loadFeed() {
    setFeedLoading(true);
    try {
      const res = await fetch('/api/eyeon/feed?limit=50');
      if (res.ok) {
        const data = await res.json();
        setFeed(data.events || []);
      }
    } catch {
    } finally {
      setFeedLoading(false);
    }
  }

  async function deleteMonitor(id: string) {
    await fetch(`/api/eyeon/monitors/${id}`, { method: 'DELETE' });
    setMonitors((prev) => prev.filter((m) => m.id !== id));
    setFeed((prev) => prev.filter((e) => (e as unknown as { monitor_id?: string }).monitor_id !== id));
  }

  const relativeTime = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const h = Math.floor(diff / 3_600_000);
    const d = Math.floor(h / 24);
    if (d > 0) return `${d}d ago`;
    if (h > 0) return `${h}h ago`;
    return 'just now';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <span className="text-2xl">👁</span>
        <div>
          <h1 className="text-xl font-bold text-gray-900">EyeOn Competitor Monitor</h1>
          <p className="text-sm text-gray-500">
            Real-time tracking of competitor content, ads, rankings &amp; backlinks
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Monitors panel */}
          <div className="lg:col-span-1 space-y-4">
            {/* Add Monitor */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Add Competitor</h2>
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addMonitor()}
                placeholder="competitor.com"
                className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
              />
              <button
                onClick={addMonitor}
                disabled={loading || !newDomain.trim()}
                className="w-full bg-[var(--brand)] hover:bg-[var(--brand)] text-white font-semibold py-2 rounded-lg disabled:opacity-50 text-sm"
              >
                {loading ? 'Adding…' : 'Monitor Domain'}
              </button>
              {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
            </div>

            {/* Monitor List */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Monitored Domains ({monitors.length})</h2>
              {monitors.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-4">Add competitors to monitor</p>
              ) : (
                <ul className="space-y-2">
                  {monitors.map((m) => (
                    <li key={m.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="font-medium text-sm text-gray-900">{m.domain}</p>
                        <p className="text-xs text-[var(--muted)]">{relativeTime(m.created_at)}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">{m.status}</span>
                        <button
                          onClick={() => deleteMonitor(m.id)}
                          className="text-[var(--muted)] hover:text-red-500 text-xs"
                          title="Remove monitor"
                        >
                          ✕
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Right: Activity Feed */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-800">Activity Feed</h2>
                <button
                  onClick={loadFeed}
                  disabled={feedLoading}
                  className="text-sm text-[var(--brand)] hover:underline disabled:opacity-50"
                >
                  {feedLoading ? 'Loading…' : 'Refresh'}
                </button>
              </div>

              {feed.length === 0 ? (
                <div className="text-center py-12 text-[var(--muted)]">
                  <p className="text-4xl mb-3">👁</p>
                  <p className="text-sm">Add competitors to start monitoring their activity</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                  {feed.map((event) => (
                    <div
                      key={event.id}
                      className={`border rounded-lg p-4 ${SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.info}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2">
                          <span className="text-lg mt-0.5">{EVENT_ICONS[event.event_type] || '📌'}</span>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-sm text-gray-900">{event.domain}</span>
                              <span
                                className={`text-xs px-2 py-0.5 rounded-full font-medium ${BADGE_STYLES[event.severity]}`}
                              >
                                {event.severity}
                              </span>
                            </div>
                            <p className="text-sm text-gray-700">
                              {event.event_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                            </p>
                            {event.details && Object.keys(event.details).length > 0 && (
                              <div className="mt-2 text-xs text-gray-600 space-y-0.5">
                                {Object.entries(event.details)
                                  .slice(0, 3)
                                  .map(([k, v]) => (
                                    <p key={k}>
                                      <span className="font-medium text-gray-500">{k.replace(/_/g, ' ')}: </span>
                                      {Array.isArray(v) ? v.join(', ') : String(v)}
                                    </p>
                                  ))}
                              </div>
                            )}
                          </div>
                        </div>
                        <span className="text-xs text-[var(--muted)] shrink-0">{relativeTime(event.detected_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
