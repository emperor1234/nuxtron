'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '../../app/lib/platform-api';

type IntelligenceTarget = {
  id: string;
  name: string;
  domain?: string;
  category?: string;
  priority?: number;
  is_active?: boolean;
  last_full_scan_at?: string | null;
};

type IntelligenceSummary = {
  active_targets?: number;
  content_alerts?: number;
  tracked_domains?: number;
  opportunities?: number;
};

type IntelligenceDashboardResponse = {
  summary?: IntelligenceSummary;
};

type IntelligenceTargetsResponse = {
  targets?: IntelligenceTarget[];
};

type CreateTargetResponse = {
  target?: IntelligenceTarget;
};

const pageStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)',
  color: '#0f172a',
};

const shellStyle: React.CSSProperties = {
  maxWidth: 1120,
  margin: '0 auto',
  padding: '32px 24px 56px',
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(148,163,184,0.22)',
  borderRadius: 20,
  boxShadow: '0 24px 60px -40px rgba(15,23,42,0.28)',
};

function metricValue(value: number | undefined): string {
  return typeof value === 'number' ? value.toLocaleString() : '0';
}

export default function IntelligenceDashboard() {
  const [summary, setSummary] = useState<IntelligenceSummary | null>(null);
  const [targets, setTargets] = useState<IntelligenceTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [category, setCategory] = useState('competitor');

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const dashboardPromise = apiGet<IntelligenceDashboardResponse>(
        '/api/v1/intelligence/dashboard',
        DEFAULT_TENANT_ID
      ).catch((): IntelligenceDashboardResponse => ({ summary: undefined }));
      const targetsPromise = apiGet<IntelligenceTargetsResponse>(
        '/api/v1/intelligence/targets',
        DEFAULT_TENANT_ID
      ).catch((): IntelligenceTargetsResponse => ({ targets: [] }));

      const [dashboardRes, targetsRes] = await Promise.all([dashboardPromise, targetsPromise]);
      setSummary(dashboardRes.summary ?? null);
      setTargets(targetsRes.targets ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load intelligence workspace.');
      setSummary(null);
      setTargets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const activeTargets = useMemo(() => targets.filter((target) => target.is_active !== false), [targets]);

  const addTarget = async () => {
    const trimmedName = name.trim();
    const trimmedDomain = domain.trim();
    if (!trimmedName) return;

    try {
      setSaving(true);
      setError(null);
      const response = await apiSend<CreateTargetResponse>(
        '/api/v1/intelligence/targets',
        'POST',
        {
          name: trimmedName,
          domain: trimmedDomain || undefined,
          category,
          priority: 3,
          is_active: true,
        },
        DEFAULT_TENANT_ID
      );

      if (response.target) {
        setTargets((prev) => [response.target as IntelligenceTarget, ...prev]);
      } else {
        await loadDashboard();
      }
      setName('');
      setDomain('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create intelligence target.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <main style={pageStyle}>
      <div style={shellStyle}>
        <section
          style={{
            ...cardStyle,
            padding: 28,
            background:
              'linear-gradient(145deg, rgba(15,23,42,0.94) 0%, rgba(30,41,59,0.92) 44%, rgba(30,64,175,0.86) 120%)',
            color: '#e2e8f0',
          }}
        >
          <div
            style={{
              fontSize: 12,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: '#93c5fd',
              fontWeight: 800,
            }}
          >
            Intelligence Control Surface
          </div>
          <h1 style={{ margin: '10px 0 8px', fontSize: 36, lineHeight: 1.05 }}>
            Competitive intelligence, targets, and execution context
          </h1>
          <p style={{ margin: 0, maxWidth: 760, lineHeight: 1.65, color: '#cbd5e1' }}>
            This production-safe dashboard uses the live intelligence API surface already registered in FastAPI. It
            focuses on target tracking, summary telemetry, and quick-add workflows without depending on missing UI
            libraries.
          </p>
        </section>

        {error && (
          <section
            style={{ ...cardStyle, marginTop: 18, padding: 16, borderColor: 'rgba(239,68,68,0.32)', color: '#991b1b' }}
          >
            {error}
          </section>
        )}

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 14,
            marginTop: 18,
          }}
        >
          {[
            { label: 'Active Targets', value: activeTargets.length },
            { label: 'Tracked Domains', value: summary?.tracked_domains },
            { label: 'Content Alerts', value: summary?.content_alerts },
            { label: 'Opportunities', value: summary?.opportunities },
          ].map((item) => (
            <article key={item.label} style={{ ...cardStyle, padding: 20 }}>
              <div
                style={{
                  fontSize: 12,
                  color: '#64748b',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  fontWeight: 700,
                }}
              >
                {item.label}
              </div>
              <div style={{ marginTop: 8, fontSize: 32, fontWeight: 800, color: '#0f172a' }}>
                {metricValue(item.value)}
              </div>
            </article>
          ))}
        </section>

        <section style={{ ...cardStyle, marginTop: 18, padding: 22 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 20,
              flexWrap: 'wrap',
              alignItems: 'flex-start',
            }}
          >
            <div style={{ maxWidth: 560 }}>
              <h2 style={{ margin: 0, fontSize: 22 }}>Add Intelligence Target</h2>
              <p style={{ margin: '6px 0 0', color: '#64748b', lineHeight: 1.6 }}>
                Register a live competitor, partner, or reference domain to expand the intelligence dataset.
              </p>
            </div>
            <button
              onClick={() => void loadDashboard()}
              disabled={loading}
              style={{
                borderRadius: 999,
                border: '1px solid rgba(59,130,246,0.24)',
                background: 'rgba(59,130,246,0.08)',
                color: '#1d4ed8',
                fontWeight: 700,
                padding: '10px 14px',
                cursor: 'pointer',
              }}
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 12,
              marginTop: 18,
            }}
          >
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Target name"
              style={inputStyle}
            />
            <input
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.com"
              style={inputStyle}
            />
            <select value={category} onChange={(event) => setCategory(event.target.value)} style={inputStyle}>
              <option value="competitor">Competitor</option>
              <option value="partner">Partner</option>
              <option value="reference">Reference</option>
              <option value="customer">Customer</option>
            </select>
            <button onClick={() => void addTarget()} disabled={saving} style={primaryButtonStyle}>
              {saving ? 'Saving...' : 'Create target'}
            </button>
          </div>
        </section>

        <section style={{ ...cardStyle, marginTop: 18, padding: 22 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 20,
              flexWrap: 'wrap',
              alignItems: 'baseline',
            }}
          >
            <h2 style={{ margin: 0, fontSize: 22 }}>Tracked Targets</h2>
            <span style={{ color: '#64748b', fontSize: 13 }}>{targets.length} total</span>
          </div>

          {loading ? (
            <div style={{ padding: '24px 0', color: '#64748b' }}>Loading targets...</div>
          ) : targets.length === 0 ? (
            <div style={{ padding: '24px 0', color: '#64748b' }}>No targets found yet.</div>
          ) : (
            <div style={{ display: 'grid', gap: 12, marginTop: 16 }}>
              {targets.map((target) => (
                <article
                  key={target.id}
                  style={{
                    borderRadius: 16,
                    border: '1px solid rgba(148,163,184,0.18)',
                    background: 'rgba(248,250,252,0.9)',
                    padding: 18,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <strong style={{ fontSize: 16 }}>{target.name}</strong>
                        <span
                          style={badgeStyle(
                            target.is_active !== false ? '#dcfce7' : '#e5e7eb',
                            target.is_active !== false ? '#166534' : '#475569'
                          )}
                        >
                          {target.is_active !== false ? 'Active' : 'Paused'}
                        </span>
                        {target.category && <span style={badgeStyle('#dbeafe', '#1d4ed8')}>{target.category}</span>}
                      </div>
                      <div style={{ marginTop: 8, color: '#475569', fontSize: 14 }}>
                        {target.domain || 'No domain set'}
                      </div>
                    </div>
                    <div style={{ display: 'grid', gap: 6, minWidth: 180 }}>
                      <span style={{ color: '#64748b', fontSize: 12 }}>Priority: {target.priority ?? 3}</span>
                      <span style={{ color: '#64748b', fontSize: 12 }}>
                        Last scan:{' '}
                        {target.last_full_scan_at
                          ? new Date(target.last_full_scan_at).toLocaleString()
                          : 'Not scanned yet'}
                      </span>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  borderRadius: 14,
  border: '1px solid rgba(148,163,184,0.34)',
  background: '#fff',
  color: '#0f172a',
  padding: '12px 14px',
  fontSize: 14,
  outline: 'none',
};

const primaryButtonStyle: React.CSSProperties = {
  borderRadius: 14,
  border: '1px solid rgba(37,99,235,0.22)',
  background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
  color: '#eff6ff',
  fontWeight: 800,
  padding: '12px 16px',
  cursor: 'pointer',
};

function badgeStyle(background: string, color: string): React.CSSProperties {
  return {
    borderRadius: 999,
    background,
    color,
    padding: '4px 10px',
    fontSize: 11,
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  };
}
