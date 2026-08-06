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
  'overflow-hidden rounded-2xl border border-[#E4DCC9] bg-white shadow-[0_12px_32px_-12px_rgba(31,31,31,0.12)]';
const HEADER =
  'flex items-center gap-2 border-b border-[#EFE9DC] bg-[#FEFCF8] px-4 py-2.5';

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
        <span className="text-sm font-semibold text-[#1F1F1F]">Position Tracking</span>
        <span className="ml-auto rounded-full bg-[#FFF1EC] px-2 py-0.5 text-xs font-semibold text-[#FF4800]">
          Live
        </span>
      </div>
      <div className="divide-y divide-[#EFE9DC]">
        {keywords.map((k) => (
          <div key={k.kw} className="flex items-center gap-4 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-[#1F1F1F]">{k.kw}</div>
              <div className="text-xs text-[#899AA8]">{k.vol} searches/mo</div>
            </div>
            <div className="text-right">
              <div className="flex items-center justify-end gap-1.5">
                <span className="text-lg font-bold text-[#1F1F1F]">#{k.pos}</span>
                <span className="flex items-center text-xs font-semibold text-[#1F7A3D]">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <path d="M7 17L17 7M17 7H8M17 7v9" />
                  </svg>
                  {k.prev - k.pos}
                </span>
              </div>
              <div className="text-xs text-[#899AA8]">was #{k.prev}</div>
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
        <span className="text-sm font-semibold text-[#1F1F1F]">This week</span>
        <span className="ml-auto text-xs text-[#899AA8]">14 posts scheduled</span>
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
            <span className="flex-1 text-sm font-medium text-[#1F1F1F]">{c.name}</span>
            <div className="flex gap-1">
              {Array.from({ length: 7 }).map((_, i) => (
                <div
                  key={i}
                  className={
                    i < c.posts
                      ? 'h-6 w-3 rounded-sm bg-[#FF4800]'
                      : 'h-6 w-3 rounded-sm bg-[#FFF1EC]'
                  }
                />
              ))}
            </div>
            <span className="w-6 text-right text-sm font-semibold text-[#33475B]">{c.posts}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 border-t border-[#EFE9DC] bg-[#FFF1EC] px-4 py-2.5 text-xs font-semibold text-[#FF4800]">
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
        <span className="text-sm font-semibold text-[#1F1F1F]">Ad Campaigns</span>
        <span className="ml-auto text-xs text-[#899AA8]">3 active</span>
      </div>
      <div className="divide-y divide-[#EFE9DC]">
        {campaigns.map((c) => (
          <div key={c.name} className="px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-[#1F1F1F]">{c.name}</span>
              <span
                className={
                  c.status === 'optimized'
                    ? 'rounded-full bg-[#E6F4EC] px-2 py-0.5 text-xs font-semibold text-[#1F7A3D]'
                    : 'rounded-full bg-[#FFF4E0] px-2 py-0.5 text-xs font-semibold text-[#B87400]'
                }
              >
                {c.status}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-4 text-xs">
              <span className="text-[#899AA8]">
                Spend: <span className="font-semibold text-[#33475B]">{c.spend}</span>
              </span>
              <span className="text-[#899AA8]">
                ROAS: <span className="font-semibold text-[#FF4800]">{c.roas}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-[#EFE9DC] bg-[#FFF1EC] px-4 py-2.5 text-xs font-semibold text-[#FF4800]">
        {'⚡ AI reallocated $500 from “Lookalike” to “Brand Search” — projected +$1,840 revenue'}
      </div>
    </div>
  );
}
