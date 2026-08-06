'use client';

import { useEffect, useState } from 'react';
import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type AnalyticsMetrics = {
  content_pieces_generated: number;
  social_posts_scheduled: number;
  email_campaigns: number;
  crm_contacts: number;
  seo_analyses: number;
  ad_campaigns: number;
};

type DashboardData = {
  social_posts_scheduled: number;
  notifications_unread: number;
  reviews_total: number;
  listening_mentions: number;
  email_campaigns: number;
  crm_contacts: number;
  crm_deals: number;
  influencer_campaigns: number;
  chatbots_active: number;
  cms_connections: number;
};

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    void (async () => {
      try {
        const [mRes, dRes] = await Promise.all([
          apiGet<{ metrics: AnalyticsMetrics }>('/analytics/metrics', DEFAULT_TENANT_ID),
          apiGet<{ dashboard: DashboardData }>('/analytics/dashboard', DEFAULT_TENANT_ID),
        ]);
        setMetrics(mRes.metrics);
        setDashboard(dRes.dashboard);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const kpiCards = metrics
    ? [
        { label: 'Content Generated', value: metrics.content_pieces_generated.toLocaleString() },
        { label: 'Posts Scheduled', value: metrics.social_posts_scheduled.toLocaleString() },
        { label: 'Email Campaigns', value: metrics.email_campaigns.toLocaleString() },
        { label: 'CRM Contacts', value: metrics.crm_contacts.toLocaleString() },
        { label: 'SEO Analyses', value: metrics.seo_analyses.toLocaleString() },
        { label: 'Ad Campaigns', value: metrics.ad_campaigns.toLocaleString() },
      ]
    : [];

  const queueCards = dashboard
    ? [
        { label: 'CRM Deals', value: dashboard.crm_deals },
        { label: 'Unread Notifications', value: dashboard.notifications_unread },
        { label: 'Social Mentions', value: dashboard.listening_mentions },
        { label: 'Reviews', value: dashboard.reviews_total },
        { label: 'Influencer Campaigns', value: dashboard.influencer_campaigns },
        { label: 'Active Chatbots', value: dashboard.chatbots_active },
        { label: 'CMS Connections', value: dashboard.cms_connections },
      ]
    : [];

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Analytics Control Center</p>
        <h1>Live KPI & Platform Dashboards</h1>
        <p>Real-time platform metrics across content, CRM, social, and campaigns.</p>
      </section>

      {error && (
        <div
          style={{
            margin: '12px 0',
            padding: 12,
            borderRadius: 10,
            border: '1px solid #ef4444',
            color: '#dc2626',
            background: '#fee2e222',
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ marginTop: 40, textAlign: 'center', color: 'var(--muted)' }}>Loading analytics…</div>
      ) : (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
              gap: 14,
              marginTop: 20,
              marginBottom: 20,
            }}
          >
            {kpiCards.map((card) => (
              <div key={card.label} className="card" style={{ padding: 20, textAlign: 'center' }}>
                <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--muted)', textTransform: 'uppercase' }}>
                  {card.label}
                </p>
                <p style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>{card.value}</p>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
            <section className="card" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>Platform Queue Snapshot</h3>
              <div style={{ display: 'grid', gap: 10 }}>
                {queueCards.map((item) => (
                  <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ color: 'var(--muted)' }}>{item.label}</span>
                    <span style={{ fontWeight: 600 }}>{item.value.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="card" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>Activity Breakdown</h3>
              <div style={{ display: 'grid', gap: 10 }}>
                {[
                  { label: 'Social Posts', value: dashboard?.social_posts_scheduled ?? 0, color: 'var(--brand)' },
                  { label: 'Email Campaigns', value: dashboard?.email_campaigns ?? 0, color: 'var(--brand-2)' },
                  { label: 'CRM Contacts', value: dashboard?.crm_contacts ?? 0, color: '#ffb852' },
                  { label: 'CRM Deals', value: dashboard?.crm_deals ?? 0, color: '#ff6b6b' },
                ].map((item) => {
                  const total =
                    (dashboard?.social_posts_scheduled ?? 0) +
                    (dashboard?.email_campaigns ?? 0) +
                    (dashboard?.crm_contacts ?? 0) +
                    (dashboard?.crm_deals ?? 0);
                  const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
                  return (
                    <div key={item.label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 12 }}>{item.label}</span>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>{item.value.toLocaleString()}</span>
                      </div>
                      <div
                        style={{
                          height: 8,
                          background: 'rgba(255, 255, 255, 0.1)',
                          borderRadius: 4,
                          overflow: 'hidden',
                        }}
                      >
                        <div style={{ width: `${pct}%`, height: '100%', background: item.color, borderRadius: 4 }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        </>
      )}
    </main>
  );
}
