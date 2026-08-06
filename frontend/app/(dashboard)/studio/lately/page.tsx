'use client';

import Link from 'next/link';

type LatelyModule = {
  id: string;
  title: string;
  description: string;
  icon: string;
  href: string;
  vendor: string;
  badge?: string;
};

const LATELY_MODULES: LatelyModule[] = [
  {
    id: 'brand-voice',
    title: 'Brand Voice DNA',
    description:
      'AI writing model that learns your brand signature words, tone, and voice from past content. Thumbs-up / thumbs-down to improve accuracy.',
    icon: '🧬',
    href: '/studio/lately/brand-voice',
    vendor: 'OpenAI GPT-4o / Claude 3.5',
    badge: 'Core',
  },
  {
    id: 'repurpose',
    title: 'Longform Content Repurposer',
    description:
      'Upload a blog post, podcast transcript, or video script and generate dozens of platform-specific social posts automatically.',
    icon: '♻️',
    href: '/studio/lately/repurpose',
    vendor: 'Internal AI + platform formatters',
    badge: 'Core',
  },
  {
    id: 'word-cloud',
    title: 'Keyword Intelligence',
    description:
      'Visual word cloud showing which keywords and phrases drive the highest reach and engagement across all channels.',
    icon: '☁️',
    href: '/studio/lately/word-cloud',
    vendor: 'Internal analytics engine',
  },
  {
    id: 'ab-testing',
    title: 'A/B Testing Engine',
    description:
      'Generate 5 content variants from a single base post. Evaluate with engagement scores and auto-republish the winner.',
    icon: '🔬',
    href: '/studio/lately/ab-testing',
    vendor: 'Internal multivariate engine',
  },
  {
    id: 'roi-forecast',
    title: 'ROI Forecaster',
    description:
      'Predict projected engagement, clicks, conversions, and revenue before publishing. Anchored to historical performance data.',
    icon: '📈',
    href: '/studio/lately/roi-forecast',
    vendor: 'Internal revenue attribution model',
  },
  {
    id: 'brand-hierarchy',
    title: 'Parent-Child Brand Hierarchy',
    description:
      'Enterprise brand management with parent-child dashboards. Coordinate messaging across regions, franchises, and employee networks.',
    icon: '🏢',
    href: '/studio/lately/brand-hierarchy',
    vendor: 'Internal multi-tenant hierarchy',
    badge: 'Enterprise',
  },
  {
    id: 'advocacy',
    title: 'Employee Advocacy Hub',
    description:
      'Create individualized, compliance-controlled content for employee advocates. Amplify brand message across employee networks.',
    icon: '📣',
    href: '/studio/social-studio/advocacy',
    vendor: 'Internal advocacy engine',
  },
  {
    id: 'smart-scheduler',
    title: 'Optimal Time Scheduler',
    description:
      'AI-powered smart fill: distributes your content queue into the posting windows that maximize reach for each channel.',
    icon: '⏰',
    href: '/studio/social-studio/best-time',
    vendor: 'Internal scheduling intelligence',
  },
  {
    id: 'approvals',
    title: 'Approval Workflows',
    description:
      'Review and approve every post before it publishes. Multi-level approval chains with role-based permissions.',
    icon: '✅',
    href: '/studio/social-studio/approvals',
    vendor: 'Internal workflow engine',
  },
  {
    id: 'analytics',
    title: 'Social Media Analytics',
    description:
      'Content reach, engagement, clicks, conversions, and ROI across all channels. Export to CSV for custom reporting.',
    icon: '📊',
    href: '/studio/social-studio/analytics',
    vendor: 'Internal analytics + export',
  },
];

export default function LatelyHubPage() {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <Link href="/studio/social-studio" style={styles.backLink}>
          ← Back to Social Studio
        </Link>
        <h1 style={styles.title}>Lately AI</h1>
        <p style={styles.subtitle}>
          World-class AI social media content creation, repurposing, analytics, and employee advocacy — 100% end-to-end.
        </p>
        <div style={styles.vendorBadge}>
          Powered by: OpenAI GPT-4o · Anthropic Claude 3.5 · HubSpot · Hootsuite · Sprinklr · Salesforce integrations
        </div>
      </div>

      <div style={styles.grid}>
        {LATELY_MODULES.map((mod) => (
          <Link key={mod.id} href={mod.href} style={styles.card}>
            <div style={styles.cardTop}>
              <span style={styles.icon}>{mod.icon}</span>
              {mod.badge ? <span style={styles.badge}>{mod.badge}</span> : null}
            </div>
            <h2 style={styles.cardTitle}>{mod.title}</h2>
            <p style={styles.cardDesc}>{mod.description}</p>
            <div style={styles.vendorChip}>{mod.vendor}</div>
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

        <h2 style={styles.sectionTitle}>Third-Party Integrations</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Integration</th>
              <th style={styles.th}>Purpose</th>
              <th style={styles.th}>Vendor</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['HubSpot Marketing Hub', 'CRM sync, contact enrichment, campaign attribution', 'HubSpot'],
              ['Hootsuite', 'Social publishing, team scheduling, analytics', 'Hootsuite'],
              ['Sprinklr', 'Enterprise social management, compliance', 'Sprinklr'],
              ['Salesforce', 'Revenue attribution, lead scoring, CRM', 'Salesforce'],
              ['OpenAI GPT-4o', 'Content generation, voice rewriting, summarization', 'OpenAI'],
              ['Anthropic Claude 3.5', 'Longform analysis, editorial quality, safety', 'Anthropic'],
              ['Twilio', 'SMS notifications, advocacy alerts', 'Twilio'],
              ['Resend', 'Transactional emails, advocacy invites', 'Resend'],
            ].map(([name, purpose, vendor]) => (
              <tr key={name} style={styles.tr}>
                <td style={styles.td}>{name}</td>
                <td style={styles.td}>{purpose}</td>
                <td style={styles.td}>{vendor}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
  vendorBadge: { display: 'inline-block', fontSize: 12, color: 'var(--muted)', background: 'rgba(100,116,139,0.1)', border: '1px solid var(--line)', borderRadius: 6, padding: '4px 10px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 310px), 1fr))', gap: 20, marginBottom: 48 },
  card: { display: 'block', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, textDecoration: 'none', color: 'inherit', transition: 'border-color 0.2s', boxShadow: 'var(--shadow-sm)' },
  cardTop: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 },
  icon: { fontSize: 28 },
  badge: { fontSize: 11, fontWeight: 700, background: 'rgba(109,94,252,0.12)', color: 'var(--brand)', border: '1px solid rgba(109,94,252,0.28)', borderRadius: 4, padding: '2px 6px' },
  cardTitle: { fontSize: 16, fontWeight: 700, margin: '0 0 8px', color: 'var(--text)' },
  cardDesc: { fontSize: 13, color: 'var(--muted)', margin: '0 0 12px', lineHeight: 1.5 },
  vendorChip: { fontSize: 11, color: 'var(--muted)', borderTop: '1px solid var(--line)', paddingTop: 10 },
  footer: { borderTop: '1px solid var(--line)', paddingTop: 32 },
  sectionTitle: { fontSize: 20, fontWeight: 700, margin: '0 0 16px', color: 'var(--text)' },
  stepList: { paddingLeft: 20, margin: '0 0 40px' },
  step: { color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, marginBottom: 12 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13, marginBottom: 40 },
  th: { background: '#f6f7fa', color: 'var(--muted)', padding: '10px 14px', textAlign: 'left', borderBottom: '1px solid var(--line)' },
  td: { padding: '10px 14px', borderBottom: '1px solid var(--line)', color: 'var(--muted)' },
  tr: {},
};
