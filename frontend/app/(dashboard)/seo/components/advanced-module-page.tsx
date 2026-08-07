'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { getCatalogByModuleKey } from '../module-catalog';
import { getPillStyle, getTierBadgeStyle } from '../tier-tone';

type SeoModule = {
  key: string;
  group: string;
  display_name: string;
  description: string;
  route_path: string;
  badge?: string | null;
  implemented: boolean;
  backend_ready: boolean;
  frontend_ready: boolean;
  database_ready: boolean;
  integrations: string[];
  supported_channels?: string[];
  architecture_layers?: string[];
  automation_features?: string[];
  analytics_features?: string[];
  enterprise_features?: string[];
  ai_models?: string[];
  delivery_constraints?: string[];
};

type ModuleDetailResponse = {
  module: SeoModule;
};

type HeroMetric = {
  label: string;
  value: string;
  hint: string;
};

type AdvancedModulePageProps = {
  moduleKey: string;
  eyebrow: string;
  title: string;
  summary: string;
  heroMetrics: HeroMetric[];
  executionLanes: string[];
  operatingModel: string[];
};

type ModuleTone = {
  accent: string;
  heroGradient: string;
  glowA: string;
  glowB: string;
};

function getModuleTone(groupName: string | undefined): ModuleTone {
  const name = (groupName ?? '').toLowerCase();
  if (name.includes('ads') || name.includes('retail')) {
    return {
      accent: '#f59e0b',
      heroGradient: 'var(--card)',
      glowA: 'radial-gradient(circle, rgba(251,191,36,0.35) 0%, rgba(251,191,36,0) 72%)',
      glowB: 'radial-gradient(circle, rgba(245,158,11,0.26) 0%, rgba(245,158,11,0) 72%)',
    };
  }
  if (name.includes('experience')) {
    return {
      accent: '#22c55e',
      heroGradient:
        'var(--card)',
      glowA: 'radial-gradient(circle, rgba(74,222,128,0.35) 0%, rgba(74,222,128,0) 72%)',
      glowB: 'radial-gradient(circle, rgba(34,197,94,0.26) 0%, rgba(34,197,94,0) 72%)',
    };
  }
  if (name.includes('performance') || name.includes('audit')) {
    return {
      accent: '#6366f1',
      heroGradient:
        'var(--card)',
      glowA: 'radial-gradient(circle, rgba(129,140,248,0.35) 0%, rgba(129,140,248,0) 72%)',
      glowB: 'radial-gradient(circle, rgba(99,102,241,0.26) 0%, rgba(99,102,241,0) 72%)',
    };
  }
  if (name.includes('governance') || name.includes('enterprise')) {
    return {
      accent: '#f43f5e',
      heroGradient:
        'var(--card)',
      glowA: 'radial-gradient(circle, rgba(251,113,133,0.35) 0%, rgba(251,113,133,0) 72%)',
      glowB: 'radial-gradient(circle, rgba(244,63,94,0.26) 0%, rgba(244,63,94,0) 72%)',
    };
  }
  return {
    accent: '#38bdf8',
    heroGradient: 'var(--card)',
    glowA: 'radial-gradient(circle, rgba(56,189,248,0.35) 0%, rgba(56,189,248,0) 72%)',
    glowB: 'radial-gradient(circle, rgba(59,130,246,0.26) 0%, rgba(59,130,246,0) 72%)',
  };
}

function StatCard({ label, value, hint }: Readonly<HeroMetric>) {
  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid rgba(148,163,184,0.24)',
        borderRadius: 16,
        padding: 16,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, marginTop: 8 }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6, lineHeight: 1.45 }}>{hint}</div>
    </div>
  );
}

function PillCloud({ title, items, accent }: Readonly<{ title: string; items?: string[]; accent: string }>) {
  if (!items || items.length === 0) return null;
  return (
    <section
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 16,
        padding: 18,
      }}
    >
      <h2 style={{ margin: 0, fontSize: 15 }}>{title}</h2>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
        {items.map((item) => (
          <span
            key={`${title}-${item}`}
            style={{
              borderRadius: 999,
              padding: '6px 10px',
              border: `1px solid ${accent}`,
              background: `${accent}18`,
              color: accent,
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}

function ChecklistCard({ title, items, tone }: Readonly<{ title: string; items?: string[]; tone: string }>) {
  if (!items || items.length === 0) return null;
  return (
    <section
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 16,
        padding: 18,
      }}
    >
      <h2 style={{ margin: 0, fontSize: 15 }}>{title}</h2>
      <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
        {items.map((item) => (
          <div key={`${title}-${item}`} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <span style={{ width: 8, height: 8, borderRadius: 999, background: tone, marginTop: 6, flexShrink: 0 }} />
            <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--text)' }}>{item}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function AdvancedModulePage(props: Readonly<AdvancedModulePageProps>) {
  const [moduleDetail, setModuleDetail] = useState<SeoModule | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadModule() {
      try {
        const response = await apiGet<ModuleDetailResponse>(
          `/seo-platform/modules/${props.moduleKey}`,
          DEFAULT_TENANT_ID
        );
        if (active) {
          setModuleDetail(response.module);
          setError('');
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Module unavailable.');
      }
    }

    void loadModule();
    return () => {
      active = false;
    };
  }, [props.moduleKey]);

  const readiness = [
    { label: 'Frontend', ok: moduleDetail?.frontend_ready ?? false },
    { label: 'Backend', ok: moduleDetail?.backend_ready ?? false },
    { label: 'Database', ok: moduleDetail?.database_ready ?? false },
    { label: 'Implemented', ok: moduleDetail?.implemented ?? false },
  ];
  const tone = getModuleTone(moduleDetail?.group);
  const catalog = getCatalogByModuleKey(props.moduleKey);

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <Link href="/seo" style={{ color: 'var(--brand)', textDecoration: 'none', fontSize: 13 }}>
          Back to SEO Platform
        </Link>

        <section
          style={{
            marginTop: 16,
            position: 'relative',
            overflow: 'hidden',
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 22,
            padding: 24,
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              right: -120,
              top: -110,
              width: 320,
              height: 320,
              borderRadius: 999,
              background: tone.glowA,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: -120,
              bottom: -130,
              width: 300,
              height: 300,
              borderRadius: 999,
              background: tone.glowB,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              fontSize: 11,
              color: tone.accent,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              fontWeight: 800,
            }}
          >
            {catalog?.category ?? props.eyebrow}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap', marginTop: 10 }}>
            <div style={{ maxWidth: 760 }}>
              <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1 }}>{catalog?.title ?? props.title}</h1>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: 'var(--muted)', marginTop: 12, marginBottom: 0 }}>
                {catalog?.summary ?? props.summary}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              {catalog?.tier && <span style={getTierBadgeStyle(catalog.tier)}>{catalog.tier}</span>}
              {readiness.map((item) => (
                <span
                  key={item.label}
                  style={getPillStyle(
                    item.ok
                      ? { bg: '#dcfce7', color: '#15803d', border: '#86efac' }
                      : { bg: '#fee2e2', color: '#b91c1c', border: '#fca5a5' },
                    'sm',
                    { uppercase: false }
                  )}
                >
                  {item.label}: {item.ok ? 'Ready' : 'Pending'}
                </span>
              ))}
              {moduleDetail?.badge && (
                <span
                  style={getPillStyle({ bg: '#dbeafe', color: '#6366f1', border: '#93c5fd' }, 'sm', {
                    uppercase: false,
                  })}
                >
                  {moduleDetail.badge}
                </span>
              )}
            </div>
          </div>
        </section>

        {error && (
          <div
            style={{
              marginTop: 14,
              border: '1px solid #fca5a5',
              borderRadius: 12,
              padding: 14,
              color: '#b91c1c',
              background: '#fee2e2',
            }}
          >
            {error}
          </div>
        )}

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))',
            gap: 12,
            marginTop: 18,
          }}
        >
          {props.heroMetrics.map((metric) => (
            <StatCard key={metric.label} {...metric} />
          ))}
        </section>

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 0.85fr)',
            gap: 14,
            marginTop: 18,
          }}
        >
          <div
            style={{
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: 16,
              padding: 18,
            }}
          >
            <h2 style={{ margin: 0, fontSize: 15 }}>Execution Lanes</h2>
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
              {props.executionLanes.map((lane) => (
                <div
                  key={lane}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 10,
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    fontSize: 13,
                    lineHeight: 1.55,
                  }}
                >
                  {lane}
                </div>
              ))}
            </div>
          </div>
          <div
            style={{
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: 16,
              padding: 18,
            }}
          >
            <h2 style={{ margin: 0, fontSize: 15 }}>Operating Model</h2>
            <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
              {props.operatingModel.map((item, index) => (
                <div key={item} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <div
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: 999,
                      background: '#6366f1',
                      color: '#fff',
                      fontSize: 11,
                      fontWeight: 800,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {index + 1}
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.55 }}>{item}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))',
            gap: 14,
            marginTop: 18,
          }}
        >
          <PillCloud title="Supported Channels" items={moduleDetail?.supported_channels} accent="#22c55e" />
          <PillCloud title="Integrations" items={moduleDetail?.integrations} accent="#38bdf8" />
          <PillCloud title="AI Model Stack" items={moduleDetail?.ai_models} accent="#2563eb" />
        </section>

        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))',
            gap: 14,
            marginTop: 18,
            marginBottom: 28,
          }}
        >
          <ChecklistCard title="Architecture Blueprint" items={moduleDetail?.architecture_layers} tone="#60a5fa" />
          <ChecklistCard title="Automation Engine" items={moduleDetail?.automation_features} tone="#22c55e" />
          <ChecklistCard title="Analytics & Attribution" items={moduleDetail?.analytics_features} tone="#f59e0b" />
          <ChecklistCard title="Enterprise Controls" items={moduleDetail?.enterprise_features} tone="#2563eb" />
          <ChecklistCard title="Delivery Constraints" items={moduleDetail?.delivery_constraints} tone="#ef4444" />
        </section>
      </div>
    </main>
  );
}
