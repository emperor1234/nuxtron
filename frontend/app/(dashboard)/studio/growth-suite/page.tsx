'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { apiGet, apiPost } from '@/app/lib/api-client';

type GrowthSuiteFeature = {
  key: string;
  name: string;
  status: string;
  headline: string;
  updated_at?: string | null;
  metrics: { label: string; value: string | number | boolean }[];
};

type GrowthSuiteResponse = {
  features: GrowthSuiteFeature[];
  totals: { features: number; configured: number; db_ready: boolean };
};

type BannerState = {
  kind: 'idle' | 'loading' | 'ready' | 'error';
  message: string;
};

const FEATURE_LINKS: Record<string, { href: string; label: string }> = {
  brand_voice_dna: { href: '/studio/lately/brand-voice', label: 'Open Brand Voice DNA' },
  auto_ab_testing: { href: '/studio/lately/ab-testing', label: 'Open A/B Testing' },
  roi_forecaster: { href: '/studio/lately/roi-forecast', label: 'Open ROI Forecaster' },
  ai_content_calendar: { href: '/studio/social-calendar', label: 'Open Content Calendar' },
  smart_scheduler: { href: '/studio/social-best-time', label: 'Open Smart Scheduler' },
  link_in_bio_builder: { href: '/studio/social-link-in-bio', label: 'Open Link-in-Bio Builder' },
  advanced_reports: { href: '/studio/social-reports', label: 'Open Advanced Reports' },
};

export default function GrowthSuitePage() {
  const [growthSuite, setGrowthSuite] = useState<GrowthSuiteResponse | null>(null);
  const [banner, setBanner] = useState<BannerState>({ kind: 'idle', message: 'Ready to load the live growth matrix.' });
  const [isBootstrapping, setIsBootstrapping] = useState(false);

  async function loadGrowthSuite(showSpinner = true) {
    if (showSpinner) {
      setBanner({ kind: 'loading', message: 'Loading live growth suite data...' });
    }

    try {
      const response = (await apiGet('/ops/platform/growth-suite')) as GrowthSuiteResponse;
      setGrowthSuite(response);
      setBanner({
        kind: 'ready',
        message: `Live matrix ready: ${response.totals.configured}/${response.totals.features} features configured.`,
      });
    } catch (error) {
      setBanner({ kind: 'error', message: (error as Error).message || 'Failed to load growth suite data.' });
    }
  }

  async function bootstrapGrowthSuite() {
    setIsBootstrapping(true);
    try {
      const response = (await apiPost('/ops/platform/growth-suite/bootstrap', {})) as GrowthSuiteResponse;
      setGrowthSuite(response);
      setBanner({
        kind: 'ready',
        message: `Bootstrapped ${response.totals.configured}/${response.totals.features} features for this tenant.`,
      });
    } catch (error) {
      setBanner({ kind: 'error', message: (error as Error).message || 'Failed to bootstrap the growth suite.' });
    } finally {
      setIsBootstrapping(false);
    }
  }

  useEffect(() => {
    void loadGrowthSuite();
  }, []);

  const featureCards = growthSuite?.features || [];

  return (
    <main style={styles.page}>
      <section style={styles.hero}>
        <div style={styles.heroCopy}>
          <p style={styles.eyebrow}>Live Control Center</p>
          <h1 style={styles.title}>AI Growth Suite</h1>
          <p style={styles.subtitle}>
            A live command center for the backend growth-suite matrix: brand voice, A/B testing, forecasting,
            calendar generation, scheduler intelligence, link-in-bio, agency operations, and executive reports.
          </p>
          <div style={styles.actions}>
            <button type="button" onClick={() => void bootstrapGrowthSuite()} disabled={isBootstrapping} style={styles.primaryButton}>
              {isBootstrapping ? 'Bootstrapping...' : 'Run full growth suite'}
            </button>
            <Link href="/platform" style={styles.secondaryButton}>
              Open Platform Overview
            </Link>
          </div>
          <p style={banner.kind === 'error' ? styles.errorBanner : styles.banner}>{banner.message}</p>
        </div>

        <aside style={styles.summaryPanel}>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>Configured</span>
            <strong style={styles.summaryValue}>{growthSuite?.totals.configured ?? 0}</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>Total features</span>
            <strong style={styles.summaryValue}>{growthSuite?.totals.features ?? 0}</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>Database</span>
            <strong style={styles.summaryValue}>{growthSuite?.totals.db_ready ? 'Ready' : 'Fallback'}</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>Route coverage</span>
            <strong style={styles.summaryValue}>Live E2E</strong>
          </div>
        </aside>
      </section>

      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <div>
            <p style={styles.eyebrow}>Feature Matrix</p>
            <h2 style={styles.sectionTitle}>Production-ready growth primitives</h2>
          </div>
          <p style={styles.sectionNote}>
            Each card is backed by the live `/ops/platform/growth-suite` payload and updates after bootstrap.
          </p>
        </div>

        <div style={styles.grid}>
          {featureCards.map((feature) => {
            const relatedLink = FEATURE_LINKS[feature.key];
            const isReady = feature.status === 'ready';

            return (
              <article key={feature.key} style={styles.card}>
                <div style={styles.cardTop}>
                  <div>
                    <h3 style={styles.cardTitle}>{feature.name}</h3>
                    <p style={styles.cardHeadline}>{feature.headline}</p>
                  </div>
                  <span style={isReady ? styles.readyBadge : styles.idleBadge}>{feature.status}</span>
                </div>

                <ul style={styles.metricList}>
                  {feature.metrics.map((metric) => (
                    <li key={`${feature.key}-${metric.label}`} style={styles.metricRow}>
                      <span>{metric.label}</span>
                      <strong>{String(metric.value)}</strong>
                    </li>
                  ))}
                  {feature.metrics.length === 0 ? <li style={styles.metricRow}>No live metrics yet.</li> : null}
                </ul>

                {relatedLink ? (
                  <Link href={relatedLink.href} style={styles.cardLink}>
                    {relatedLink.label}
                  </Link>
                ) : (
                  <span style={styles.cardFallback}>Available in the platform matrix only.</span>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <div>
            <p style={styles.eyebrow}>Coverage Notes</p>
            <h2 style={styles.sectionTitle}>What this route proves</h2>
          </div>
        </div>
        <div style={styles.noteGrid}>
          <div style={styles.noteCard}>
            <strong>Live backend data</strong>
            <p>Reads the platform growth-suite endpoint and renders the tenant-specific feature matrix.</p>
          </div>
          <div style={styles.noteCard}>
            <strong>Bootstrap workflow</strong>
            <p>Calls the bootstrap endpoint and refreshes the matrix in the same UI surface.</p>
          </div>
          <div style={styles.noteCard}>
            <strong>Direct drill-downs</strong>
            <p>Links Lately-aligned features into their existing studio routes instead of leaving them hidden in telemetry.</p>
          </div>
        </div>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: '100vh',
    padding: '32px 20px 56px',
    background:
      'radial-gradient(circle at top left, rgba(14,165,233,0.18), transparent 30%), radial-gradient(circle at top right, rgba(99,102,241,0.16), transparent 34%), linear-gradient(180deg, #07111f 0%, #0b1526 45%, #050b14 100%)',
    color: 'var(--text)',
  },
  hero: {
    maxWidth: 1280,
    margin: '0 auto',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
    gap: 20,
    alignItems: 'start',
  },
  heroCopy: {
    padding: 28,
    borderRadius: 28,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    boxShadow: '0 24px 80px rgba(0, 0, 0, 0.35)',
    backdropFilter: 'blur(18px)',
  },
  eyebrow: {
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.18em',
    fontSize: 11,
    color: 'var(--brand)',
    fontWeight: 700,
  },
  title: {
    margin: '12px 0 10px',
    fontSize: 'clamp(2.2rem, 4vw, 4rem)',
    lineHeight: 1.02,
    color: 'var(--text)',
    fontWeight: 900,
  },
  subtitle: {
    margin: 0,
    maxWidth: 760,
    color: 'var(--muted)',
    fontSize: 16,
    lineHeight: 1.7,
  },
  actions: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
    marginTop: 18,
  },
  primaryButton: {
    border: 'none',
    borderRadius: 999,
    padding: '12px 18px',
    background: 'linear-gradient(135deg, #22c55e, #06b6d4)',
    color: '#04111d',
    fontWeight: 800,
    cursor: 'pointer',
  },
  secondaryButton: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 999,
    padding: '12px 18px',
    border: '1px solid rgba(125,211,252,0.35)',
    background: 'rgba(8, 15, 28, 0.7)',
    color: 'var(--text)',
    textDecoration: 'none',
    fontWeight: 700,
  },
  banner: {
    marginTop: 16,
    marginBottom: 0,
    padding: '12px 14px',
    borderRadius: 16,
    background: 'rgba(14, 165, 233, 0.12)',
    border: '1px solid rgba(14, 165, 233, 0.2)',
    color: '#dbeafe',
  },
  errorBanner: {
    marginTop: 16,
    marginBottom: 0,
    padding: '12px 14px',
    borderRadius: 16,
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.22)',
    color: '#fecaca',
  },
  summaryPanel: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: 14,
  },
  summaryCard: {
    padding: 18,
    borderRadius: 22,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.18)',
  },
  summaryLabel: {
    display: 'block',
    color: 'var(--muted)',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
    marginBottom: 10,
  },
  summaryValue: {
    fontSize: 28,
    color: 'var(--text)',
    lineHeight: 1,
  },
  section: {
    maxWidth: 1280,
    margin: '26px auto 0',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'end',
    justifyContent: 'space-between',
    gap: 14,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  sectionTitle: {
    margin: '8px 0 0',
    fontSize: 'clamp(1.4rem, 2vw, 2rem)',
    color: 'var(--text)',
    fontWeight: 850,
  },
  sectionNote: {
    maxWidth: 520,
    color: 'var(--muted)',
    margin: 0,
    lineHeight: 1.6,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))',
    gap: 16,
  },
  card: {
    borderRadius: 24,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    padding: 18,
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.22)',
  },
  cardTop: {
    display: 'flex',
    alignItems: 'start',
    justifyContent: 'space-between',
    gap: 12,
  },
  cardTitle: {
    margin: 0,
    color: 'var(--text)',
    fontSize: 18,
    fontWeight: 800,
  },
  cardHeadline: {
    margin: '10px 0 0',
    color: 'var(--muted)',
    lineHeight: 1.6,
    fontSize: 14,
  },
  readyBadge: {
    borderRadius: 999,
    padding: '6px 10px',
    fontSize: 12,
    fontWeight: 800,
    background: 'rgba(34, 197, 94, 0.16)',
    color: '#15803d',
    border: '1px solid rgba(34, 197, 94, 0.22)',
    textTransform: 'capitalize',
  },
  idleBadge: {
    borderRadius: 999,
    padding: '6px 10px',
    fontSize: 12,
    fontWeight: 800,
    background: 'rgba(251, 191, 36, 0.14)',
    color: '#b45309',
    border: '1px solid rgba(251, 191, 36, 0.18)',
    textTransform: 'capitalize',
  },
  metricList: {
    listStyle: 'none',
    padding: 0,
    margin: '16px 0 0',
    display: 'grid',
    gap: 8,
  },
  metricRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    borderRadius: 16,
    padding: '10px 12px',
    background: 'rgba(148,163,184,0.07)',
    color: 'var(--muted)',
    fontSize: 14,
  },
  cardLink: {
    display: 'inline-flex',
    marginTop: 14,
    color: 'var(--brand)',
    textDecoration: 'none',
    fontWeight: 800,
  },
  cardFallback: {
    display: 'inline-flex',
    marginTop: 14,
    color: 'var(--muted)',
    fontSize: 13,
  },
  noteGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))',
    gap: 14,
  },
  noteCard: {
    borderRadius: 16,
    padding: 18,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: 'var(--muted)',
    lineHeight: 1.6,
  },
};
