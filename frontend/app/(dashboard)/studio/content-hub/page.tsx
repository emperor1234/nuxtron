'use client';

import type { Route } from 'next';
import Link from 'next/link';
import {
  ChartColumn,
  Building2,
  CircleCheck,
  Clock,
  Cloud,
  Dna,
  FlaskConical,
  Megaphone,
  Recycle,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react';

type HubModule = {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  href: string;
  badge?: string;
};

const HUB_MODULES: HubModule[] = [
  {
    id: 'brand-voice',
    title: 'Brand Voice DNA',
    description:
      'AI writing model that learns your brand signature words, tone, and voice from past content. Thumbs-up / thumbs-down to improve accuracy.',
    icon: Dna,
    href: '/studio/content-hub/brand-voice',
    badge: 'Core',
  },
  {
    id: 'repurpose',
    title: 'Content Repurposer',
    description:
      'Upload a blog post, podcast transcript, or video script and generate dozens of platform-specific social posts automatically.',
    icon: Recycle,
    href: '/studio/content-hub/repurpose',
    badge: 'Core',
  },
  {
    id: 'word-cloud',
    title: 'Keyword Intelligence',
    description:
      'Visual word cloud showing which keywords and phrases drive the highest reach and engagement across all channels.',
    icon: Cloud,
    href: '/studio/content-hub/word-cloud',
  },
  {
    id: 'ab-testing',
    title: 'A/B Testing Engine',
    description:
      'Generate 5 content variants from a single base post. Evaluate with engagement scores and auto-republish the winner.',
    icon: FlaskConical,
    href: '/studio/content-hub/ab-testing',
  },
  {
    id: 'roi-forecast',
    title: 'ROI Forecaster',
    description:
      'Predict projected engagement, clicks, conversions, and revenue before publishing. Anchored to historical performance data.',
    icon: TrendingUp,
    href: '/studio/content-hub/roi-forecast',
  },
  {
    id: 'brand-hierarchy',
    title: 'Brand Hierarchy',
    description:
      'Enterprise brand management with parent-child dashboards. Coordinate messaging across regions, franchises, and employee networks.',
    icon: Building2,
    href: '/studio/content-hub/brand-hierarchy',
    badge: 'Enterprise',
  },
  {
    id: 'advocacy',
    title: 'Employee Advocacy Hub',
    description:
      'Create individualized, compliance-controlled content for employee advocates. Amplify brand message across employee networks.',
    icon: Megaphone,
    href: '/studio/social-studio/advocacy',
  },
  {
    id: 'smart-scheduler',
    title: 'Optimal Time Scheduler',
    description:
      'AI-powered smart fill: distributes your content queue into the posting windows that maximize reach for each channel.',
    icon: Clock,
    href: '/studio/social-studio/best-time',
  },
  {
    id: 'approvals',
    title: 'Approval Workflows',
    description:
      'Review and approve every post before it publishes. Multi-level approval chains with role-based permissions.',
    icon: CircleCheck,
    href: '/studio/social-studio/approvals',
  },
  {
    id: 'analytics',
    title: 'Social Media Analytics',
    description:
      'Content reach, engagement, clicks, conversions, and ROI across all channels. Export to CSV for custom reporting.',
    icon: ChartColumn,
    href: '/studio/social-studio/analytics',
  },
];

export default function ContentHubPage() {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <Link href="/studio/social-studio" style={styles.backLink}>
          ← Back to Social Studio
        </Link>
        <h1 style={styles.title}>AI Content Hub</h1>
        <p style={styles.subtitle}>
          Write in your brand voice, turn long pieces into posts, and test and forecast them before they publish.
        </p>
      </div>

      <div style={styles.grid}>
        {HUB_MODULES.map((mod) => (
          <Link key={mod.id} href={mod.href as Route} style={styles.card}>
            <div style={styles.cardTop}>
              <span style={styles.icon}>
                <mod.icon size={20} aria-hidden="true" />
              </span>
              {mod.badge ? <span style={styles.badge}>{mod.badge}</span> : null}
            </div>
            <h2 style={styles.cardTitle}>{mod.title}</h2>
            <p style={styles.cardDesc}>{mod.description}</p>
          </Link>
        ))}
      </div>

      <div style={styles.footer}>
        <h2 style={styles.sectionTitle}>How It Works</h2>
        <ol style={styles.stepList}>
          <li style={styles.step}>
            <strong>Brand Voice DNA</strong> — Analyze past social posts to extract your unique writing fingerprint:
            signature words, sentence cadence, punctuation intensity, and tone.
          </li>
          <li style={styles.step}>
            <strong>Machine Learning with Human Touch</strong> — Thumbs-up / thumbs-down feedback adapts the AI model.
            Every edit you make trains the voice to better match your audience.
          </li>
          <li style={styles.step}>
            <strong>Longform Repurposing</strong> — Paste any blog, podcast script, press release, or transcript. The AI
            atomizes it into dozens of pre-tested social posts formatted for each platform (LinkedIn, X, Instagram,
            Threads, TikTok, Facebook).
          </li>
          <li style={styles.step}>
            <strong>Optimal Scheduling</strong> — Smart Scheduler fills your queue into the time windows that
            historically drive the most reach and engagement per channel.
          </li>
          <li style={styles.step}>
            <strong>Employee Advocacy</strong> — Brand-approved content is distributed to employee advocates in their
            own voice, coordinated from a central hub with compliance controls.
          </li>
          <li style={styles.step}>
            <strong>Analytics &amp; Export</strong> — Word cloud keyword insights, A/B test results, ROI forecasts, and
            full CSV export for executive reporting.
          </li>
        </ol>

      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { maxWidth: 1200, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 40 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 36, fontWeight: 800, margin: '12px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 16, color: 'var(--muted)', maxWidth: 700, margin: '0 0 12px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 310px), 1fr))', gap: 20, marginBottom: 48 },
  card: { display: 'block', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, textDecoration: 'none', color: 'inherit', transition: 'border-color 0.2s', boxShadow: 'var(--shadow-sm)' },
  cardTop: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 },
  icon: { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, borderRadius: 10, background: 'var(--brand-soft)', color: 'var(--brand)' },
  badge: { fontSize: 11, fontWeight: 700, background: 'rgba(109,94,252,0.12)', color: 'var(--brand)', border: '1px solid rgba(109,94,252,0.28)', borderRadius: 4, padding: '2px 6px' },
  cardTitle: { fontSize: 16, fontWeight: 700, margin: '0 0 8px', color: 'var(--text)' },
  cardDesc: { fontSize: 13, color: 'var(--muted)', margin: '0 0 12px', lineHeight: 1.5 },
  footer: { borderTop: '1px solid var(--line)', paddingTop: 32 },
  sectionTitle: { fontSize: 20, fontWeight: 700, margin: '0 0 16px', color: 'var(--text)' },
  stepList: { paddingLeft: 20, margin: '0 0 40px' },
  step: { color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, marginBottom: 12 },
};
