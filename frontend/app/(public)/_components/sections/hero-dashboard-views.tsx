"use client";

import type { CSSProperties, ReactNode } from "react";
import styles from "./hero-dashboard.module.css";

/**
 * Sample-free screens for the self-navigating product preview. No customer
 * records, connected-account metrics, or fabricated business outcomes appear.
 */

export type RailSection = "home" | "seo" | "social" | "studio" | "apps";

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
    id: "aeo",
    section: "seo",
    item: "Answer Engine (AEO)",
    breadcrumb: ["SEO", "AI search visibility", "Answer Engine (AEO)"],
    path: "seo/aeo",
    title: "Answer Engine Optimization",
    subtitle: "Paste content and a topic; results are AI guidance, not search-engine data.",
    render: () => (
      <div className={styles.row2}>
        <Card i={0} title="Inputs" aside={<span className={styles.muted}>Nothing submitted</span>}>
          <ul className={styles.issues}>
            {["Content to analyse", "Topic", "Questions to answer"].map((field) => (
              <li key={field}>
                <span className={styles.chip} data-status="mentioned">Input</span>
                <span className={styles.issueText}>{field}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card i={1} title="Results" aside={<span className={styles.muted}>No analysis run</span>}>
          <p className={styles.muted}>Scores, snippet opportunities and quick wins appear here after you run an analysis. Each result states whether an AI model produced it.</p>
        </Card>
      </div>
    ),
  },
  {
    id: "on-page",
    section: "seo",
    item: "On-Page Optimizer",
    breadcrumb: ["SEO", "Content & on-page", "On-Page Optimizer"],
    path: "seo/on-page",
    title: "On-Page Optimizer",
    subtitle: "Measure keyword use, word count and readability in the copy you paste.",
    render: () => (
      <Card i={0} title="Measurements" aside={<span className={styles.muted}>No page analysed</span>}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Measure</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Keyword density", "Computed from your text"],
              ["Word count", "Computed from your text"],
              ["Readability", "Computed from your text"],
            ].map(([measure, source]) => (
              <tr key={measure}>
                <td>{measure}</td>
                <td className={styles.muted}>{source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
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
    item: "Social Inbox",
    breadcrumb: ["Social", "Engage", "Social Inbox"],
    path: "studio/social-studio/inbox",
    title: "Social Inbox",
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
    item: "Image Studio",
    breadcrumb: ["Studio", "Create", "Image Studio"],
    path: "studio/image-studio",
    title: "Image Studio",
    subtitle: "No generated or approved assets are shown in this preview.",
    render: () => (
      <Card i={0} title="Creative assets" aside={<span className={styles.muted}>No assets loaded</span>}>
        <p className={styles.muted}>Start a draft in your workspace to see its real status. Nothing in this preview is presented as generated, reviewed, or approved.</p>
      </Card>
    ),
  },
];
