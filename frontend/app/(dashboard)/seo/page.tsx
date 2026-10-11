import type { Metadata, Route } from "next";
import Link from "next/link";
import { ArrowUpRight, BarChart3, MapPin, ScanEye, Search, type LucideIcon } from "lucide-react";
import { MENUS, RAIL_ITEMS, type FlyoutItem, type RailKey } from "../_shell/nav";
import { Card, Page, PageHeader } from "../_ui/kit";
import styles from "./seo-home.module.css";

export const metadata: Metadata = {
  title: "SEO · Nuxtron",
  description: "Your search and AI visibility tools, organised the way you work.",
};

/** Sidebar sections that make up Nuxtron SEO, in sidebar order. */
const SECTIONS: readonly { key: RailKey; Icon: LucideIcon; summary: string }[] = [
  { key: "seo", Icon: Search, summary: "Audit the site, track rankings and research competitors." },
  { key: "ai", Icon: ScanEye, summary: "See and improve how AI assistants describe your brand." },
  { key: "traffic", Icon: BarChart3, summary: "Size the market and benchmark traffic." },
  { key: "local", Icon: MapPin, summary: "Listings, reviews and local rankings." },
];

/** Shortcuts at the top of the page, looked up by their sidebar label. */
const START_WITH = ["Site Audit", "Position Tracking", "AI Visibility Overview", "Domain Overview"];

function findItem(label: string): FlyoutItem | undefined {
  for (const menu of Object.values(MENUS)) {
    for (const group of menu?.groups ?? []) {
      const item = group.items.find((candidate) => candidate.label === label);
      if (item) return item;
    }
  }
  return undefined;
}

/**
 * SEO home. Built from the same navigation model as the sidebar
 * (app/(dashboard)/_shell/nav.ts), so every tool listed here is a real page
 * and the page can never drift from the menus.
 */
export default function SeoHomePage() {
  const shortcuts = START_WITH.map(findItem).filter((item): item is FlyoutItem => Boolean(item));

  return (
    <Page>
      <PageHeader
        title="SEO"
        subtitle="Your search and AI visibility tools, organised the way you work."
      />

      <section aria-labelledby="seo-start" className={styles.start}>
        <h2 id="seo-start" className={styles.kicker}>
          Start with
        </h2>
        <div className={styles.shortcuts}>
          {shortcuts.map((item) => (
            <Link key={item.href} href={item.href} className={styles.shortcut} data-testid="seo-shortcut">
              <span>{item.label}</span>
              <ArrowUpRight size={15} aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>

      {SECTIONS.map(({ key, Icon, summary }) => {
        const menu = MENUS[key];
        const rail = RAIL_ITEMS.find((item) => item.key === key);
        if (!menu || !rail) return null;
        const groups = menu.groups.filter((group) => group.items.length > 0);
        const toolCount = groups.reduce((sum, group) => sum + group.items.length, 0);
        return (
          <section key={key} aria-labelledby={`seo-${key}`} className={styles.section}>
            <header className={styles.sectionHead}>
              <span className={styles.sectionIcon}>
                <Icon size={18} aria-hidden="true" />
              </span>
              <div>
                <h2 id={`seo-${key}`} className={styles.sectionTitle}>
                  {rail.label}
                  <span className={styles.count}>{toolCount} tools</span>
                </h2>
                <p className={styles.sectionSummary}>{summary}</p>
              </div>
            </header>
            <div className={styles.groups}>
              {groups.map((group) => (
                <Card key={group.label} className={styles.group}>
                  <h3 className={styles.groupTitle}>{group.label}</h3>
                  <ul className={styles.tools}>
                    {group.items.map((item) => (
                      <li key={`${group.label}:${item.href}:${item.label}`}>
                        <Link href={item.href as Route} className={styles.tool} data-testid="seo-tool-link">
                          {item.label}
                          <ArrowUpRight size={14} aria-hidden="true" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </Card>
              ))}
            </div>
          </section>
        );
      })}
    </Page>
  );
}
