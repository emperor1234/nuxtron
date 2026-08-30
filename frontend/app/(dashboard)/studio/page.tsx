import type { Metadata } from 'next';
import Link from 'next/link';
import type { Route } from 'next';

import { Card, Page, PageHeader } from '@/app/(dashboard)/_ui/kit';
import { ROUTE_INDEX } from '@/app/(dashboard)/_shell/route-index.generated';

import styles from './studio-hub.module.css';

export const metadata: Metadata = {
  title: 'Studio · Nuxtron',
  description: 'Create, brand, grow and operate — every Nuxtron Studio workspace in one place.',
};

/**
 * Curated ordering and copy for the hub. Anything in the route index that is
 * missing here still renders (under "More in Studio"), so a newly added Studio
 * page can never become unreachable — which is how this section ended up with
 * 34 orphaned pages and a landing that linked nowhere.
 */
const SECTIONS: readonly { title: string; blurb: string; routes: readonly string[] }[] = [
  {
    title: 'Create',
    blurb: 'Produce on-brand copy, images and video.',
    routes: [
      '/studio/editor',
      '/studio/image-studio',
      '/studio/image-direction',
      '/studio/short-video-factory',
      '/studio/reels-factory',
      '/studio/faceless-video-engine',
      '/studio/avatar-builder',
    ],
  },
  {
    title: 'Brand',
    blurb: 'Keep every asset consistent with your identity.',
    routes: ['/studio/brands', '/studio/brand-kit', '/studio/lately/brand-voice', '/studio/lately/brand-hierarchy', '/studio/template-system'],
  },
  {
    title: 'Publish & engage',
    blurb: 'Schedule, approve and respond across every channel.',
    routes: [
      '/studio/social-studio',
      '/studio/scheduler',
      '/studio/social-studio/calendar',
      '/studio/social-studio/inbox',
      '/studio/social-studio/approvals',
    ],
  },
  {
    title: 'Grow',
    blurb: 'Rank higher, earn links and win answer engines.',
    routes: [
      '/studio/growth-suite',
      '/studio/seo-suite',
      '/studio/rank-tracker',
      '/studio/backlink-intelligence',
      '/studio/answer-engine',
      '/studio/lately/repurpose',
    ],
  },
  {
    title: 'Advertise',
    blurb: 'Test creative and stretch budget further.',
    routes: ['/studio/ads-engine', '/studio/multilingual-ads', '/studio/lately/ab-testing'],
  },
  {
    title: 'Measure',
    blurb: 'See what worked, and what it earned.',
    routes: [
      '/studio/analytics',
      '/studio/agent-analytics',
      '/studio/intelligence',
      '/studio/lately/roi-forecast',
      '/studio/prompt-volumes',
      '/studio/lately/word-cloud',
    ],
  },
  {
    title: 'Operate',
    blurb: 'Coordinate people, approvals and automation.',
    routes: ['/studio/workspace', '/studio/workflow-orchestrator', '/studio/team', '/studio/cdn-analytics'],
  },
];

const BY_ROUTE = new Map(ROUTE_INDEX.map((entry) => [entry.route, entry]));

function summarise(route: string) {
  const entry = BY_ROUTE.get(route);
  if (!entry) return null;
  return { route, title: entry.title, group: entry.group };
}

export default function StudioHubPage() {
  const curated = SECTIONS.map((section) => ({
    ...section,
    items: section.routes.map(summarise).filter((item): item is NonNullable<typeof item> => item !== null),
  })).filter((section) => section.items.length > 0);

  const placed = new Set(curated.flatMap((section) => section.items.map((item) => item.route)));
  const leftovers = ROUTE_INDEX.filter(
    (entry) =>
      (entry.section === 'studio' || entry.section === 'social') && entry.route !== '/studio' && !placed.has(entry.route)
  );

  return (
    <Page>
      <PageHeader
        title="Studio"
        subtitle="Create, brand, publish, grow and measure — every Studio workspace in one place."
      />

      <div className={styles.sections}>
        {curated.map((section) => (
          <section key={section.title} className={styles.section}>
            <div className={styles.sectionHead}>
              <h2 className={styles.sectionTitle}>{section.title}</h2>
              <p className={styles.sectionBlurb}>{section.blurb}</p>
            </div>
            <ul className={styles.grid}>
              {section.items.map((item) => (
                <li key={item.route}>
                  <Link href={item.route as Route} className={styles.tile}>
                    <span className={styles.tileTitle}>{item.title}</span>
                    <span className={styles.tileMeta}>{item.group}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {leftovers.length > 0 ? (
        <Card>
          <h2 className={styles.sectionTitle}>More in Studio</h2>
          <ul className={styles.chips}>
            {leftovers.map((entry) => (
              <li key={entry.route}>
                <Link href={entry.route as Route} className={styles.chip}>
                  {entry.title}
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </Page>
  );
}
