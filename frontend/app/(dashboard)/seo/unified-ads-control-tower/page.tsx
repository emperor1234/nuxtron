'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { adsApi } from '@/app/lib/ads-api';

type HealthData = {
  connectors_total: number;
  connectors_connected: number;
  campaigns_total: number;
  campaigns_overdue_sync: number;
};

type NotifData = {
  total: number;
  notifications: { id: number; title: string; message: string; priority: string; created_at: string }[];
};

const NAV_ITEMS = [
  {
    href: '/seo/ads-connectors' as Route,
    icon: '🔌',
    title: 'Ad Network Connectors',
    description: 'Connect Google, Microsoft, Amazon, Apple, and YouTube Ads via OAuth.',
    color: '#6366f1',
  },
  {
    href: '/seo/ads-campaigns' as Route,
    icon: '📋',
    title: 'Campaign Manager',
    description: 'Create, publish, and manage campaigns with full CRUD across all connected networks.',
    color: '#22c55e',
  },
  {
    href: '/seo/ads-metrics' as Route,
    icon: '📊',
    title: 'Metrics & Tracking',
    description: 'Patch likes, shares, clicks, conversions, spend, revenue, ROI, and success ratio per campaign.',
    color: '#f59e0b',
  },
  {
    href: '/seo/ads-calendar' as Route,
    icon: '📅',
    title: 'Campaign Calendar',
    description: 'Visualize scheduled campaigns. Drag events to reschedule them automatically.',
    color: '#a855f7',
  },
  {
    href: '/seo/ads-kpis' as Route,
    icon: '📈',
    title: 'KPIs & Analytics',
    description: 'Cross-network performance overview, engagement breakdown, forecasting, and credit balances.',
    color: '#ef4444',
  },
  {
    href: '/seo/ads-smart-schedule' as Route,
    icon: '🧠',
    title: 'Smart Schedule & Approval',
    description:
      'Best-time heatmap, human review windows, approval workflow, A/B creative tests, and audience insights.',
    color: '#06b6d4',
  },
];

const PRIORITY_COLORS: Record<string, string> = {
  success: '#22c55e',
  warning: '#f59e0b',
  info: '#6366f1',
  error: '#ef4444',
};

export default function UnifiedAdsControlTowerPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [notifs, setNotifs] = useState<NotifData | null>(null);
  const [error, setError] = useState('');
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [h, n] = await Promise.all([adsApi.health(), adsApi.notifications(8)]);
        setHealth(h);
        setNotifs(n);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Backend unavailable.');
      }
    })();
  }, []);

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg, #0a0a0a)', color: 'var(--text, #f1f5f9)' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        {/* Back */}
        <Link href={'/seo' as Route} style={{ color: '#6366f1', textDecoration: 'none', fontSize: 13 }}>
          ← Back to SEO Platform
        </Link>

        {/* Hero */}
        <section
          style={{
            marginTop: 16,
            background: 'var(--card)',
            border: '1px solid var(--line)',
            boxShadow: 'var(--shadow-sm)',
            borderRadius: 16,
            padding: 28,
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: 'var(--brand)',
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              fontWeight: 800,
            }}
          >
            Advanced Ads Control Tower
          </div>
          <h1 style={{ margin: '10px 0 12px', fontSize: 36, lineHeight: 1.1 }}>Unified Ads Control Tower</h1>
          <p style={{ fontSize: 15, lineHeight: 1.65, color: 'var(--muted)', margin: 0, maxWidth: 740 }}>
            Centralized operating plane for agency-grade campaign orchestration across Google, Microsoft, Amazon, Apple
            Search Ads, and YouTube — with live OAuth, campaign CRUD, metrics tracking, calendar scheduling, and
            cross-network KPI analytics.
          </p>

          {/* Health strip */}
          {health && (
            <div style={{ display: 'flex', gap: 24, marginTop: 20, flexWrap: 'wrap' }}>
              {[
                {
                  label: 'Networks Connected',
                  value: `${health.connectors_connected} / ${health.connectors_total}`,
                  ok: health.connectors_connected > 0,
                },
                { label: 'Active Campaigns', value: String(health.campaigns_total), ok: true },
                {
                  label: 'Overdue Sync',
                  value: String(health.campaigns_overdue_sync),
                  ok: health.campaigns_overdue_sync === 0,
                },
              ].map((item) => (
                <div key={item.label}>
                  <div style={{ fontSize: 10, color: 'var(--brand)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {item.label}
                  </div>
                  <div style={{ fontWeight: 900, fontSize: 24, color: item.ok ? '#15803d' : '#dc2626', marginTop: 4 }}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          )}
          {!health && error && (
            <div style={{ marginTop: 14, fontSize: 13, color: '#dc2626' }}>
              {error} — some features may be unavailable.
            </div>
          )}
          {!health && !error && (
            <div style={{ marginTop: 14, fontSize: 13, color: '#64748b' }}>Connecting to backend…</div>
          )}
        </section>

        {/* Navigation cards */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))',
            gap: 14,
            marginTop: 24,
          }}
        >
          {NAV_ITEMS.map((item) =>
            (() => {
              const isHovered = hoveredCard === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{ textDecoration: 'none', color: 'inherit' }}
                  onMouseEnter={() => setHoveredCard(item.href)}
                  onMouseLeave={() => setHoveredCard(null)}
                  onFocus={() => setHoveredCard(item.href)}
                  onBlur={() => setHoveredCard(null)}
                >
                  <div
                    style={{
                      background: isHovered
                        ? `linear-gradient(135deg, ${item.color}14 0%, var(--card) 75%)`
                        : 'var(--bg-soft, #111)',
                      border: isHovered ? `1px solid ${item.color}` : `1px solid ${item.color}44`,
                      borderRadius: 16,
                      padding: 18,
                      height: '100%',
                      cursor: 'pointer',
                      transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
                      boxShadow: isHovered
                        ? `0 14px 28px ${item.color}33, 0 0 0 1px ${item.color}22 inset`
                        : '0 2px 8px rgba(2, 6, 23, 0.25)',
                      transition:
                        'transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.2s ease',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 28,
                        marginBottom: 10,
                        transform: isHovered ? 'scale(1.08)' : 'scale(1)',
                        transition: 'transform 0.18s ease',
                      }}
                    >
                      {item.icon}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <div style={{ fontWeight: 800, fontSize: 14, color: item.color }}>{item.title}</div>
                      <span
                        style={{
                          color: item.color,
                          fontSize: 14,
                          fontWeight: 900,
                          opacity: isHovered ? 1 : 0,
                          transform: isHovered ? 'translateX(0)' : 'translateX(-6px)',
                          transition: 'opacity 0.18s ease, transform 0.18s ease',
                        }}
                      >
                        →
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: isHovered ? 'var(--muted)' : '#64748b',
                        marginTop: 6,
                        lineHeight: 1.55,
                        transition: 'color 0.18s ease',
                      }}
                    >
                      {item.description}
                    </div>
                  </div>
                </Link>
              );
            })()
          )}
        </section>

        {/* Recent notifications */}
        {notifs && notifs.total > 0 && (
          <section
            style={{
              marginTop: 24,
              background: 'var(--bg-soft, #111)',
              border: '1px solid var(--line, #333)',
              borderRadius: 16,
              padding: 18,
            }}
          >
            <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 14 }}>
              Recent Activity ({notifs.total} events)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {notifs.notifications.map((n) => {
                const color = PRIORITY_COLORS[n.priority] ?? '#64748b';
                return (
                  <div
                    key={n.id}
                    style={{
                      display: 'flex',
                      gap: 12,
                      alignItems: 'flex-start',
                      padding: '8px 12px',
                      background: 'var(--bg, #0a0a0a)',
                      borderRadius: 10,
                    }}
                  >
                    <div
                      style={{ width: 8, height: 8, borderRadius: 999, background: color, flexShrink: 0, marginTop: 5 }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 13 }}>{n.title}</div>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{n.message}</div>
                    </div>
                    <div style={{ fontSize: 11, color: '#475569', flexShrink: 0 }}>
                      {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Architecture overview */}
        <section
          style={{
            marginTop: 20,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))',
            gap: 14,
            marginBottom: 28,
          }}
        >
          {[
            {
              title: 'Execution Lanes',
              color: '#6366f1',
              items: [
                'Normalize campaign objects into a shared cross-network schema.',
                'Push mutations through connector abstractions, not platform-specific UI logic.',
                'Reconcile live platform state vs planned state to detect drift and partial failures.',
                'Expose approval checkpoints for high-risk budget, bid, and creative changes.',
              ],
            },
            {
              title: 'Stack',
              color: '#22c55e',
              items: [
                'Next.js 15 — Control Tower UI (pages router, React 18)',
                'FastAPI — Campaign orchestration and connector OAuth layer',
                'PostgreSQL + Supabase — Control plane and audit persistence',
                'Redis + Celery — Async execution fabric and pacing workers',
              ],
            },
            {
              title: 'Operating Model',
              color: '#a855f7',
              items: [
                'Control tower orchestrates; ad networks remain the system of record for delivery.',
                'API approvals, quotas, and editorial rules are first-class operational constraints.',
                'High-frequency execution workers stay separate from admin and billing workflows.',
              ],
            },
          ].map((section) => (
            <div
              key={section.title}
              style={{
                background: 'var(--bg-soft, #111)',
                border: '1px solid var(--line, #333)',
                borderRadius: 16,
                padding: 18,
              }}
            >
              <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 12, color: section.color }}>
                {section.title}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {section.items.map((item) => (
                  <div key={item} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: 999,
                        background: section.color,
                        flexShrink: 0,
                        marginTop: 6,
                      }}
                    />
                    <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--muted)' }}>{item}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
