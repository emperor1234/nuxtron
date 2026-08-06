'use client';

import { useMemo, useState } from 'react';
import { Bot, Lightbulb, LoaderCircle, Search, Sparkles, WandSparkles, Zap } from 'lucide-react';

type ToastItem = {
  id: number;
  message: string;
};

const searchCorpus = [
  'Audience overlap by campaign',
  'Best-performing playbook this month',
  'High-risk disputes requiring review',
  'Forecasted ROI for next 14 days',
  'Trust-center incidents by severity',
  'Suggested media mix for budget shift',
];

const smartSuggestions = [
  'Shift 8% spend from low-performing social to search channels.',
  'Increase creative variant testing on high-conversion segments.',
  'Auto-escalate trust incidents with severity > 7 to governance.',
];

export default function InstitutionalAiWidgets() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragItems, setDragItems] = useState<string[]>([
    'Review AI-generated creative briefs',
    'Approve benchmark publication',
    'Resolve trust-center escalations',
    'Publish campaign playbook updates',
  ]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [generatedBrief, setGeneratedBrief] = useState('');
  const [dragAnnouncement, setDragAnnouncement] = useState('');

  const metricItems: string[] = loading
    ? ['Loading', 'Loading', 'Loading']
    : ['+22% qualified traffic', '13.8% CPA improvement', '2 high-risk incidents'];

  const filteredSearch = useMemo(() => {
    if (!query.trim()) return searchCorpus.slice(0, 4);
    return searchCorpus.filter((item) => item.toLowerCase().includes(query.toLowerCase()));
  }, [query]);

  const removeToastById = (id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const pushToast = (message: string) => {
    // eslint-disable-next-line react-hooks/purity
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      removeToastById(id);
    }, 2200);
  };

  const moveItem = (from: number, to: number) => {
    if (to < 0 || to >= dragItems.length || from === to) return;
    const next = [...dragItems];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setDragItems(next);
    setDragAnnouncement(`Moved item to position ${to + 1}`);
    pushToast('Queue reordered.');
  };

  const triggerRefresh = () => {
    setLoading(true);
    pushToast('Refreshing AI insights...');
    setTimeout(() => {
      setLoading(false);
      pushToast('Insights refreshed with latest data.');
    }, 1300);
  };

  const generateBrief = () => {
    const text =
      'AI brief: Prioritize retention campaigns for high-LTV cohorts, launch two fresh creative variants, and monitor trust signals every 4 hours for anomaly spikes.';
    setGeneratedBrief(text);
    pushToast('AI generated a new strategic brief.');
  };

  return (
    <section className="ai-widget-grid" aria-label="AI integrated widgets">
      <article className="card widget-card">
        <div className="widget-head">
          <h3>AI-Powered Search</h3>
          <Search size={18} aria-hidden="true" />
        </div>
        <div className="widget-input-shell">
          <input
            aria-label="Search AI forecasts, incidents, and playbooks"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search forecasts, incidents, playbooks..."
          />
        </div>
        <ul className="widget-list">
          {filteredSearch.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>

      <article className="card widget-card">
        <div className="widget-head">
          <h3>Smart Suggestions</h3>
          <Lightbulb size={18} aria-hidden="true" />
        </div>
        <div className="suggestion-stack">
          {smartSuggestions.map((item) => (
            <button key={item} type="button" className="suggestion-chip" onClick={() => pushToast(item)}>
              <Sparkles size={14} aria-hidden="true" />
              <span>{item}</span>
            </button>
          ))}
        </div>
      </article>

      <article className="card widget-card">
        <div className="widget-head">
          <h3>Live AI Insights</h3>
          <button type="button" className="widget-action" onClick={triggerRefresh}>
            {loading ? <LoaderCircle size={14} className="spin" /> : <Zap size={14} />}
            <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
        <div className="metric-card-grid">
          {metricItems.map((item, idx) => (
            <div key={String(item) + idx} className="metric-card">
              {loading ? <div className="skeleton-line" /> : <p>{item}</p>}
            </div>
          ))}
        </div>
      </article>

      <article className="card widget-card">
        <div className="widget-head">
          <h3>Priority Queue (Drag to Reorder)</h3>
          <Bot size={18} aria-hidden="true" />
        </div>
        <ul className="drag-list">
          {dragItems.map((item, index) => (
            <li key={item}>
              <button
                type="button"
                className="drag-item"
                draggable
                aria-label={`Queue item ${index + 1}: ${item}`}
                onDragStart={() => setDragIndex(index)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => {
                  if (dragIndex === null || dragIndex === index) return;
                  moveItem(dragIndex, index);
                  setDragIndex(null);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    moveItem(index, index - 1);
                  }
                  if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    moveItem(index, index + 1);
                  }
                }}
              >
                <span className="drag-handle" aria-hidden="true">
                  ::
                </span>
                <span>{item}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="sr-only" aria-live="polite">
          {dragAnnouncement}
        </p>
      </article>

      <article className="card widget-card widget-card-wide">
        <div className="widget-head">
          <h3>AI-Generated Content Brief</h3>
          <button type="button" className="widget-action" onClick={generateBrief}>
            <WandSparkles size={14} />
            <span>Generate</span>
          </button>
        </div>
        <p className="widget-copy">
          Use AI to draft campaign narratives, media priorities, and governance checkpoints tailored to current
          performance.
        </p>
        <div className="ai-brief-box">
          {generatedBrief || 'No brief generated yet. Click Generate to produce an AI-backed strategy draft.'}
        </div>
      </article>

      <div className="toast-stack" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast-item">
            {toast.message}
          </div>
        ))}
      </div>
    </section>
  );
}
