'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type NetworkAnalytics = {
  network: string;
  followers: number;
  follower_growth: number;
  impressions: number;
  reach: number;
  engagement: number;
  engagement_rate: number;
  clicks: number;
  link_clicks: number;
  saves: number;
  shares: number;
  posts_count: number;
  best_post_type: string;
};

type OverviewResponse = {
  networks?: NetworkAnalytics[];
  totals?: {
    total_impressions: number;
    total_reach: number;
    total_engagement: number;
    avg_engagement_rate: number;
  };
};

type BestTimeSlot = {
  day: string;
  time: string;
  engagement_rate: number;
  recommended: boolean;
};

type AudienceResponse = {
  followers?: { total: number; growth_30d: number; growth_pct: number };
  age_distribution?: Array<{ range: string; pct: number }>;
  gender_distribution?: Array<{ gender: string; pct: number }>;
  top_countries?: Array<{ country: string; pct: number }>;
};

type ReportItem = {
  id: string | number;
  name: string;
  export_format: string;
  status: string;
  created_at?: string;
  download_url?: string;
};

const shell = {
  background: 'var(--bg-soft, #f8fafc)',
  border: '1px solid var(--line, #e2e8f0)',
  borderRadius: 12,
  padding: 16,
} as const;

export default function BufferAnalyzePage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [network, setNetwork] = useState('instagram');
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<OverviewResponse>({});
  const [bestTime, setBestTime] = useState<BestTimeSlot[]>([]);
  const [audience, setAudience] = useState<AudienceResponse>({});
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [reportName, setReportName] = useState('Monthly social performance');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [overviewRes, bestRes, audienceRes, reportsRes] = await Promise.all([
        apiGet<OverviewResponse>(
          `/social/analytics/overview?networks=instagram,facebook,linkedin,x,tiktok&days=${days}`,
          tenantId
        ),
        apiGet<{ recommended_slots?: BestTimeSlot[] }>(`/social/analytics/best-time/${network}`, tenantId),
        apiGet<AudienceResponse>(`/social/analytics/audience/${network}`, tenantId),
        apiGet<{ reports?: ReportItem[] }>('/social/analytics/reports', tenantId),
      ]);
      setOverview(overviewRes);
      setBestTime(bestRes.recommended_slots ?? []);
      setAudience(audienceRes);
      setReports(reportsRes.reports ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [days, network, tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const overviewRows = overview.networks ?? [];
  const totals = overview.totals;
  const genderRows = useMemo(() => audience.gender_distribution ?? [], [audience.gender_distribution]);

  async function createReport() {
    try {
      await apiSend(
        '/social/analytics/custom-report',
        'POST',
        {
          name: reportName,
          networks: ['instagram', 'facebook', 'linkedin', 'x', 'tiktok'],
          metrics: ['followers', 'impressions', 'reach', 'engagement_rate', 'clicks'],
          date_range_days: days,
          include_logo: true,
          accent_color: '#6366f1',
          export_format: 'pdf',
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report generation failed');
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg, #f8fafc)', color: 'var(--text, #0f172a)', padding: 24 }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 16,
            alignItems: 'flex-start',
            marginBottom: 20,
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 28 }}>Analyze</h1>
            <p style={{ margin: '6px 0 0', color: '#64748b' }}>
              Cross-channel performance, audience insights, best-time guidance, and custom reporting.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <select
              value={network}
              onChange={(event) => setNetwork(event.target.value)}
              style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
            >
              {['instagram', 'facebook', 'linkedin', 'x', 'tiktok'].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select
              value={String(days)}
              onChange={(event) => setDays(Number(event.target.value))}
              style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
            >
              {[7, 30, 90].map((value) => (
                <option key={value} value={value}>
                  {value} days
                </option>
              ))}
            </select>
          </div>
        </div>

        {error ? <div style={{ ...shell, color: '#b91c1c', marginBottom: 14 }}>{error}</div> : null}
        {loading ? <div style={{ color: '#64748b', padding: 30, textAlign: 'center' }}>Loading analytics…</div> : null}

        <div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))', gap: 12, marginBottom: 18 }}
        >
          <div style={shell}>
            <div style={{ fontSize: 12, color: '#64748b' }}>Impressions</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totals?.total_impressions ?? 0}</div>
          </div>
          <div style={shell}>
            <div style={{ fontSize: 12, color: '#64748b' }}>Reach</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totals?.total_reach ?? 0}</div>
          </div>
          <div style={shell}>
            <div style={{ fontSize: 12, color: '#64748b' }}>Engagement</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totals?.total_engagement ?? 0}</div>
          </div>
          <div style={shell}>
            <div style={{ fontSize: 12, color: '#64748b' }}>Avg engagement rate</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totals?.avg_engagement_rate ?? 0}%</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 18 }}>
          <section style={shell}>
            <h2 style={{ marginTop: 0 }}>Channel overview</h2>
            <div style={{ display: 'grid', gap: 8 }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1.2fr repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
                  gap: 8,
                  fontSize: 12,
                  color: '#64748b',
                  fontWeight: 700,
                }}
              >
                <span>Network</span>
                <span>Followers</span>
                <span>Growth</span>
                <span>Impressions</span>
                <span>Reach</span>
                <span>Eng. rate</span>
                <span>Best format</span>
              </div>
              {overviewRows.map((row) => (
                <div
                  key={row.network}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.2fr repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
                    gap: 8,
                    padding: '10px 0',
                    borderTop: '1px solid #e2e8f0',
                  }}
                >
                  <strong>{row.network}</strong>
                  <span>{row.followers}</span>
                  <span>{row.follower_growth}</span>
                  <span>{row.impressions}</span>
                  <span>{row.reach}</span>
                  <span>{row.engagement_rate}%</span>
                  <span>{row.best_post_type}</span>
                </div>
              ))}
            </div>
          </section>

          <section style={shell}>
            <h2 style={{ marginTop: 0 }}>Best time to post</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {bestTime.map((slot) => (
                <div
                  key={`${slot.day}-${slot.time}`}
                  style={{
                    padding: 12,
                    borderRadius: 10,
                    background: slot.recommended ? '#eff6ff' : '#fff7ed',
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 10,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {slot.day} {slot.time}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>{network}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700 }}>{slot.engagement_rate}%</div>
                    <div style={{ fontSize: 12, color: slot.recommended ? '#6366f1' : '#9a3412' }}>
                      {slot.recommended ? 'Recommended' : 'Secondary'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 16 }}>
          <section style={shell}>
            <h2 style={{ marginTop: 0 }}>Audience insights</h2>
            <div style={{ fontSize: 13, color: '#475569', marginBottom: 12 }}>
              Followers: {audience.followers?.total ?? 0} · Growth 30d: {audience.followers?.growth_pct ?? 0}%
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Age distribution</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(audience.age_distribution ?? []).map((item) => (
                  <div key={item.range}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span>{item.range}</span>
                      <span>{item.pct}%</span>
                    </div>
                    <div style={{ height: 8, borderRadius: 999, background: '#e2e8f0' }}>
                      <div
                        style={{ width: `${item.pct}%`, height: '100%', borderRadius: 999, background: '#6366f1' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Top countries</div>
              <div style={{ display: 'grid', gap: 6 }}>
                {(audience.top_countries ?? []).map((item) => (
                  <div key={item.country} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span>{item.country}</span>
                    <span>{item.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section style={shell}>
            <h2 style={{ marginTop: 0 }}>Gender split</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {genderRows.map((item) => (
                <div key={item.gender} style={{ padding: 12, borderRadius: 10, background: '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                    <strong>{item.gender}</strong>
                    <span>{item.pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section style={shell}>
            <h2 style={{ marginTop: 0 }}>Custom reports</h2>
            <input
              value={reportName}
              onChange={(event) => setReportName(event.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid #cbd5e1',
                marginBottom: 10,
                boxSizing: 'border-box',
              }}
              placeholder="Report name"
            />
            <button
              onClick={() => void createReport()}
              style={{
                border: 'none',
                borderRadius: 10,
                padding: '10px 12px',
                background: '#6366f1',
                color: '#fff',
                fontWeight: 700,
                cursor: 'pointer',
                marginBottom: 14,
              }}
            >
              Generate report
            </button>
            <div style={{ display: 'grid', gap: 10 }}>
              {reports.map((report) => (
                <div key={String(report.id)} style={{ padding: 12, borderRadius: 10, background: '#fff' }}>
                  <div style={{ fontWeight: 700 }}>{report.name}</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                    {report.export_format} · {report.status}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>
                    {report.created_at ? new Date(report.created_at).toLocaleString() : 'no date'}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
