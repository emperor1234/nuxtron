'use client';

/**
 * ProductVisuals — real, JSX-rendered UI snippets that show what
 * Nuxtron actually does. No stock illustrations, no external images.
 * Each visual is a small, self-contained "screenshot" of a feature.
 *
 * Uses a shared card class (defined inline) to avoid Tailwind arbitrary-
 * value parsing issues with the shadow utility.
 */

const CARD =
  'overflow-hidden rounded-2xl border border-line bg-white shadow-[0_12px_32px_-12px_rgba(31,31,31,0.12)]';
const HEADER =
  'flex items-center gap-2 border-b border-line-soft bg-surface px-4 py-2.5';

/* ── SEO rank-tracking visual ── */
export function SeoVisual() {
  const keywords = [
    { kw: 'marketing automation software', pos: 3, prev: 7, vol: '18.2K' },
    { kw: 'ai content generator', pos: 1, prev: 4, vol: '32.1K' },
    { kw: 'social media scheduling', pos: 5, prev: 12, vol: '24.7K' },
  ];
  return (
    <div className={CARD}>
      <div className={HEADER}>
        <span className="text-sm font-semibold text-ink">Position Tracking</span>
        <span className="ml-auto rounded-full bg-line-soft px-2 py-0.5 text-xs font-semibold text-warning-ink">
          Live
        </span>
      </div>
      <div className="divide-y divide-line-soft">
        {keywords.map((k) => (
          <div key={k.kw} className="flex items-center gap-4 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-ink">{k.kw}</div>
              <div className="text-xs text-info">{k.vol} searches/mo</div>
            </div>
            <div className="text-right">
              <div className="flex items-center justify-end gap-1.5">
                <span className="text-lg font-bold text-ink">#{k.pos}</span>
                <span className="flex items-center text-xs font-semibold text-success-ink">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <path d="M7 17L17 7M17 7H8M17 7v9" />
                  </svg>
                  {k.prev - k.pos}
                </span>
              </div>
              <div className="text-xs text-info">was #{k.prev}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Social calendar visual ── */
export function SocialVisual() {
  const channels = [
    { name: 'LinkedIn', icon: 'in', color: '#0A66C2', posts: 3 },
    { name: 'X / Twitter', icon: 'X', color: '#1F1F1F', posts: 5 },
    { name: 'Instagram', icon: 'IG', color: '#E1306C', posts: 4 },
    { name: 'TikTok', icon: 'TT', color: '#000000', posts: 2 },
  ];
  return (
    <div className={CARD}>
      <div className={HEADER}>
        <span className="text-sm font-semibold text-ink">This week</span>
        <span className="ml-auto text-xs text-info">14 posts scheduled</span>
      </div>
      <div className="space-y-2 p-4">
        {channels.map((c) => (
          <div key={c.name} className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 flex-none items-center justify-center rounded-lg text-xs font-bold text-white"
              style={{ background: c.color }}
            >
              {c.icon}
            </div>
            <span className="flex-1 text-sm font-medium text-ink">{c.name}</span>
            <div className="flex gap-1">
              {Array.from({ length: 7 }).map((_, i) => (
                <div
                  key={i}
                  className={
                    i < c.posts
                      ? 'h-6 w-3 rounded-sm bg-warning'
                      : 'h-6 w-3 rounded-sm bg-line-soft'
                  }
                />
              ))}
            </div>
            <span className="w-6 text-right text-sm font-semibold text-info-ink">{c.posts}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 border-t border-line-soft bg-line-soft px-4 py-2.5 text-xs font-semibold text-warning-ink">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
        AI suggests posting today at 2:00 PM for max reach
      </div>
    </div>
  );
}

/* ── Ads performance visual ── */
export function AdsVisual() {
  const campaigns = [
    { name: 'Brand Search', spend: '$1,240', roas: '6.8×', status: 'optimized' },
    { name: 'Retargeting', spend: '$890', roas: '4.2×', status: 'optimized' },
    { name: 'Lookalike Audience', spend: '$2,100', roas: '2.1×', status: 'action needed' },
  ];
  return (
    <div className={CARD}>
      <div className={HEADER}>
        <span className="text-sm font-semibold text-ink">Ad Campaigns</span>
        <span className="ml-auto text-xs text-info">3 active</span>
      </div>
      <div className="divide-y divide-line-soft">
        {campaigns.map((c) => (
          <div key={c.name} className="px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">{c.name}</span>
              <span
                className={
                  c.status === 'optimized'
                    ? 'rounded-full bg-line-soft px-2 py-0.5 text-xs font-semibold text-success-ink'
                    : 'rounded-full bg-warning-soft px-2 py-0.5 text-xs font-semibold text-warning-ink'
                }
              >
                {c.status}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-4 text-xs">
              <span className="text-info">
                Spend: <span className="font-semibold text-info-ink">{c.spend}</span>
              </span>
              <span className="text-info">
                ROAS: <span className="font-semibold text-warning-ink">{c.roas}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-line-soft bg-line-soft px-4 py-2.5 text-xs font-semibold text-warning-ink">
        {'⚡ AI reallocated $500 from “Lookalike” to “Brand Search” — projected +$1,840 revenue'}
      </div>
    </div>
  );
}
