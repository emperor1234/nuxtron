"use client";

import type { CSSProperties, ReactNode } from "react";
import styles from "./hero-dashboard.module.css";

/**
 * Sample-free screens for the self-navigating product preview. No customer
 * records, connected-account metrics, or fabricated business outcomes appear.
 */

export type RailSection = "home" | "seo" | "ai" | "content" | "social" | "studio";

export type DashboardView = {
  id: string;
  /** Rail section that owns the page ("home" for the workspace overview). */
  section: RailSection;
  /** The sub-item clicked inside the opened section (real menu label). */
  item?: string;
  /** Breadcrumb as the real page renders it. */
  breadcrumb: readonly string[];
  path: string;
  title: string;
  subtitle: string;
  render: (hovered: boolean) => ReactNode;
};

function Card({ title, aside, children, i = 0 }: { title: string; aside?: ReactNode; children: ReactNode; i?: number }) {
  return (
    <section className={styles.card} style={{ "--i": i } as CSSProperties}>
      <header className={styles.cardHead}>
        <span>{title}</span>
        {aside}
      </header>
      {children}
    </section>
  );
}

/** The real /dashboard "Workspace overview" page. */
function homeView(product: "seo" | "marketing"): DashboardView {
  const productName = product === "seo" ? "SEO" : "Marketing";
  return {
    id: "home",
    section: "home",
    breadcrumb: ["Home"],
    path: "dashboard",
    title: "Workspace overview",
    subtitle: "A sample-free preview with no account data or business metrics.",
    render: () => (
      <>
        <div className={styles.statusRow}>
          <span className={styles.muted}>Product preview · no connected account</span>
          <span className={styles.refresh}>No workspace data loaded</span>
        </div>
        <div className={styles.kpis}>
          <PlainKpi i={0} label="Workspace plan" value="Not shown" caption="Configured in your account" />
          <PlainKpi i={1} label="Credits" value="—" caption="No balance displayed here" />
          <PlainKpi i={2} label="Saved research" value="—" caption="No workspace records loaded" />
          <PlainKpi i={3} label="Connected tools" value="—" caption="Configured per workspace" />
        </div>
        <div className={styles.homeRow}>
          <section className={styles.card} style={{ "--i": 4 } as CSSProperties}>
            <span className={styles.kicker}>{productName} workspace</span>
            <h4 className={styles.homeTitle}>Start with your team&apos;s inputs.</h4>
            <p className={styles.homeBody}>Connect supported sources or review data your team already has. This preview includes no sample records.</p>
          </section>
          <section className={styles.cardSoft} style={{ "--i": 5 } as CSSProperties}>
            <span className={styles.kicker}>Workspace setup</span>
            <h4 className={styles.homeTitle}>Bring your context together.</h4>
            <p className={styles.homeBody}>Choose your workspace details and the channels your team is authorized to connect.</p>
            {["Configure workspace identity", "Connect supported channels", "Invite teammates"].map((link) => (
              <span key={link} className={styles.homeLink}>{link}</span>
            ))}
          </section>
        </div>
      </>
    ),
  };
}

function PlainKpi({ label, value, caption, i }: { label: string; value: string; caption: string; i: number }) {
  return (
    <div className={styles.kpi} style={{ "--i": i } as CSSProperties}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{value}</span>
      <span className={styles.kpiCaption}>{caption}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Nuxtron SEO
// ---------------------------------------------------------------------------

export const SEO_VIEWS: readonly DashboardView[] = [
  homeView("seo"),
  {
    id: "ai-visibility",
    section: "ai",
    item: "AI Visibility Overview",
    breadcrumb: ["AI", "Research & optimize", "AI Visibility Overview"],
    path: "seo/seo-ai",
    title: "AI Visibility",
    subtitle: "No verified observations are loaded in this sample-free preview.",
    render: () => (
      <div className={styles.row2}>
        <Card i={0} title="Prompt evidence" aside={<span className={styles.muted}>No source data</span>}>
          <p className={styles.muted}>Connected observations and user-provided prompt evidence would appear here. No prompt counts or citation results are fabricated.</p>
        </Card>
        <Card i={1} title="Answer share" aside={<span className={styles.muted}>Not calculated</span>}>
          <p className={styles.muted}>Share-of-answer metrics require verified, comparable source observations; none are shown in this preview.</p>
        </Card>
      </div>
    ),
  },
  {
    id: "keywords",
    section: "seo",
    item: "Rank Position Review",
    breadcrumb: ["SEO", "Research & visibility", "Rank Position Review"],
    path: "seo/rank-tracking",
    title: "Rank Position Review",
    subtitle: "Review positions from an export you provide; processing stays in your browser.",
    render: () => (
      <Card i={0} title="Position export" aside={<span className={styles.muted}>Browser-local · no file loaded</span>}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Keyword</th>
              <th>Position</th>
              <th>Observed date</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={3} className={styles.muted}>No export loaded</td>
            </tr>
          </tbody>
        </table>
        <p className={styles.muted}>Choose a CSV to review supplied positions. No live provider data or forecasts are shown.</p>
      </Card>
    ),
  },
  {
    id: "traffic-analytics",
    section: "seo",
    item: "Traffic Analytics",
    breadcrumb: ["SEO", "Market & research", "Traffic Analytics"],
    path: "seo/analytics",
    title: "Traffic Analytics",
    subtitle: "Compare two periods using values you supply; no analytics provider is connected.",
    render: () => (
      <div className={styles.row2}>
        <Card i={0} title="Comparison source" aside={<span className={styles.muted}>Not supplied</span>}>
          <p className={styles.muted}>Choose an export or report you trust, then enter two period labels and the observed values.</p>
        </Card>
        <Card i={1} title="Metrics in scope" aside={<span className={styles.muted}>Manual input</span>}>
          <ul className={styles.issues}>
            {[
              "Clicks and impressions",
              "Click-through rate",
              "Average position",
            ].map((metric) => (
              <li key={metric}>
                <span className={styles.chip} data-status="mentioned">Input</span>
                <span className={styles.issueText}>{metric}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    ),
  },
];

// ---------------------------------------------------------------------------
// Nuxtron Marketing
// ---------------------------------------------------------------------------

export const MARKETING_VIEWS: readonly DashboardView[] = [
  homeView("marketing"),
  {
    id: "calendar",
    section: "social",
    item: "Content Calendar",
    breadcrumb: ["Social", "Publish", "Content Calendar"],
    path: "studio/social-studio/calendar",
    title: "Content Calendar",
    subtitle: "A sample-free calendar preview with no scheduled posts.",
    render: () => (
      <Card i={0} title="Content Calendar" aside={<span className={styles.muted}>No posts loaded</span>}>
        <div className={styles.week}>
          {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day) => (
            <div key={day} className={styles.dayCol}>
              <span className={styles.dayName}>{day}</span>
              <span className={styles.muted}>No scheduled posts</span>
            </div>
          ))}
        </div>
      </Card>
    ),
  },
  {
    id: "inbox",
    section: "social",
    item: "Smart Inbox",
    breadcrumb: ["Social", "Engage", "Smart Inbox"],
    path: "studio/social-studio/inbox",
    title: "Smart Inbox",
    subtitle: "No connected messages or comments are displayed in this preview.",
    render: () => (
      <div className={styles.inbox}>
        <div className={styles.threads}>
          <p className={styles.muted}>No channel data loaded.</p>
        </div>
        <div className={styles.thread}>
          <p className={styles.muted}>Connect an authorized channel to review incoming messages. No sample conversations or replies are shown.</p>
        </div>
      </div>
    ),
  },
  {
    id: "studio",
    section: "studio",
    item: "AI Image Studio",
    breadcrumb: ["Studio", "Create", "AI Image Studio"],
    path: "studio/image-studio",
    title: "AI Image Studio",
    subtitle: "No generated or approved assets are shown in this preview.",
    render: () => (
      <Card i={0} title="Creative assets" aside={<span className={styles.muted}>No assets loaded</span>}>
        <p className={styles.muted}>Start a draft in your workspace to see its real status. Nothing in this preview is presented as generated, reviewed, or approved.</p>
      </Card>
    ),
  },
];
