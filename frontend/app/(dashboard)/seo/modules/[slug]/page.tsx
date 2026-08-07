'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { getCatalogByModuleKey, getCatalogByRoutePath, getCatalogBySlug } from '../../module-catalog';
import { getTierBadgeStyle } from '../../tier-tone';

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

export default function SeoModuleDetailPage({ params }: Readonly<{ params: Promise<{ slug: string }> }>) {
  const router = useRouter();
  const [slug, setSlug] = useState('');
  const [moduleDetail, setModuleDetail] = useState<SeoModule | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadModule() {
      try {
        const resolved = await params;
        if (!active) return;

        const legacyRouteOverrides: Record<string, string> = {
          'seo-ai': '/seo/seo-ai',
          sageo: '/seo/sageo',
          peao: '/seo/peao',
          msvo: '/seo/msvo',
          daeo: '/seo/daeo',
          'news-seo-google-discover': '/seo/news-discover',
          'analytics-reporting-intelligence': '/seo/history',
          'agency-multi-tenant-platform': '/seo/agency-platform',
          'international-multilingual-seo': '/seo/international-multilingual',
          'site-migration-seo-manager': '/seo/site-migration',
          cxao: '/seo/cxao',
          'seo-ab-testing': '/seo/seo-ab-testing',
          'revenue-attribution-intelligence': '/seo/revenue-attribution',
          'growth-playbooks-automation': '/seo/growth-playbooks',
          'trust-risk-governance': '/seo/trust-risk-governance',
          'multi-channel-activation-loop': '/seo/multi-channel-activation',
        };
        const redirectPath = legacyRouteOverrides[resolved.slug];
        if (redirectPath) {
          router.replace(redirectPath);
          return;
        }

        setSlug(resolved.slug);
        const response = await apiGet<ModuleDetailResponse>(
          `/seo-platform/modules/${resolved.slug}`,
          DEFAULT_TENANT_ID
        );
        if (active) setModuleDetail(response.module);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Module unavailable.');
      }
    }

    void loadModule();
    return () => {
      active = false;
    };
  }, [params, router]);

  const card = {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: 16,
    boxShadow: 'var(--shadow-sm)',
  };
  const tone = getModuleTone(moduleDetail?.group);
  const catalog =
    getCatalogByModuleKey(moduleDetail?.key) ??
    getCatalogByRoutePath(moduleDetail?.route_path) ??
    getCatalogBySlug(slug);

  const renderPills = (title: string, items: string[] | undefined, accent = 'var(--brand)') => {
    if (!items || items.length === 0) return null;
    return (
      <div style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 14, marginBottom: 10 }}>{title}</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {items.map((item) => (
            <span
              key={`${title}-${item}`}
              style={{
                fontSize: 12,
                borderRadius: 999,
                padding: '5px 9px',
                background: 'var(--bg)',
                border: `1px solid ${accent}`,
              }}
            >
              {item}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderChecklist = (title: string, items: string[] | undefined, color = 'var(--muted)') => {
    if (!items || items.length === 0) return null;
    return (
      <div style={{ ...card }}>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>{title}</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {items.map((item) => (
            <div key={`${title}-${item}`} style={{ fontSize: 12, lineHeight: 1.45, color }}>
              {item}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <Link href="/seo" style={{ color: 'var(--brand)', textDecoration: 'none', fontSize: 13 }}>
          Back to SEO Platform
        </Link>

        <section
          style={{
            ...card,
            marginTop: 16,
            position: 'relative',
            overflow: 'hidden',
            background: 'var(--card)',
            borderRadius: 16,
            boxShadow: `0 28px 80px -56px ${tone.accent}99`,
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
            {catalog?.category ?? 'Module Intelligence Profile'}
          </div>

          <h1 style={{ marginTop: 10, marginBottom: 6, fontSize: 34, lineHeight: 1.1 }}>
            {catalog?.title ?? moduleDetail?.display_name ?? slug}
          </h1>
          <p style={{ color: 'var(--muted)', marginTop: 0, lineHeight: 1.6 }}>
            {catalog?.summary ?? moduleDetail?.description ?? 'Registry-backed SEO module.'}
          </p>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
            Advanced module profile for orchestration, analytics, automation, and enterprise controls.
          </div>

          {catalog?.tier && (
            <div style={{ marginTop: 8 }}>
              <span style={getTierBadgeStyle(catalog.tier)}>{catalog.tier}</span>
            </div>
          )}

          {error && <div style={{ color: '#dc2626', fontSize: 12 }}>{error}</div>}

          {moduleDetail && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))',
                gap: 10,
                marginTop: 14,
              }}
            >
              <div style={{ ...card, borderRadius: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Group</div>
                <div style={{ fontWeight: 700 }}>{moduleDetail.group}</div>
              </div>
              <div style={{ ...card, borderRadius: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Frontend</div>
                <div style={{ fontWeight: 700 }}>{moduleDetail.frontend_ready ? 'Ready' : 'Registry only'}</div>
              </div>
              <div style={{ ...card, borderRadius: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Backend</div>
                <div style={{ fontWeight: 700 }}>{moduleDetail.backend_ready ? 'Ready' : 'Registry only'}</div>
              </div>
              <div style={{ ...card, borderRadius: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Database</div>
                <div style={{ fontWeight: 700 }}>{moduleDetail.database_ready ? 'Seeded' : 'Pending'}</div>
              </div>
            </div>
          )}

          {moduleDetail &&
            moduleDetail.integrations.length > 0 &&
            renderPills('Required Integrations', moduleDetail.integrations)}

          {moduleDetail && renderPills('Supported Channels', moduleDetail.supported_channels, '#22c55e')}
          {moduleDetail && renderPills('AI Models', moduleDetail.ai_models, '#2563eb')}

          {moduleDetail && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))',
                gap: 10,
                marginTop: 16,
              }}
            >
              {renderChecklist('Architecture Blueprint', moduleDetail.architecture_layers, 'var(--text)')}
              {renderChecklist('Automation Engine', moduleDetail.automation_features, 'var(--text)')}
              {renderChecklist('Analytics & Attribution', moduleDetail.analytics_features, 'var(--text)')}
              {renderChecklist('Enterprise Controls', moduleDetail.enterprise_features, 'var(--text)')}
              {renderChecklist('Delivery Constraints', moduleDetail.delivery_constraints, 'var(--text)')}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
