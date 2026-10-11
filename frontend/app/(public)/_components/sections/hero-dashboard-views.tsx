"use client";

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Check, MessageCircle, Send, Sparkles } from "lucide-react";
import styles from "./hero-dashboard.module.css";

/**
 * Screens for the self-navigating hero dashboard. Data belongs to a fictional
 * generic customer account and is presented as a product view, never as a result
 * customers should expect.
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

const REDUCED = "(prefers-reduced-motion: reduce)";

/** Counts up to `target` once on mount (instant under reduced motion). */
function useCountUp(target: number, durationMs = 900): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (globalThis.matchMedia?.(REDUCED).matches) {
      const id = requestAnimationFrame(() => setValue(target));
      return () => cancelAnimationFrame(id);
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs]);
  return value;
}

/** Smooth line path through points, scaled into a w×h box. */
function linePath(points: readonly number[], w: number, h: number, max: number): string {
  const step = w / (points.length - 1);
  const xy = points.map((p, i) => [i * step, h - (p / max) * h] as const);
  return xy
    .map(([x, y], i) => {
      if (i === 0) return `M${x},${y}`;
      const [px, py] = xy[i - 1]!;
      const cx = (px + x) / 2;
      return `C${cx},${py} ${cx},${y} ${x},${y}`;
    })
    .join(" ");
}

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

function Bars({ items, i0 = 0 }: { items: readonly (readonly [string, number])[]; i0?: number }) {
  const max = Math.max(...items.map(([, v]) => v));
  return (
    <ul className={styles.bars}>
      {items.map(([label, value], i) => (
        <li key={label} className={styles.barRow}>
          <span className={styles.barLabel}>{label}</span>
          <span className={styles.barTrack}>
            <span className={styles.barFill} style={{ "--v": value / max, "--i": i + i0 } as CSSProperties} />
          </span>
          <span className={styles.barValue}>{value}</span>
        </li>
      ))}
    </ul>
  );
}


/** The real /dashboard "Workspace overview" page. */
function homeView(product: "seo" | "marketing"): DashboardView {
  return {
    id: "home",
    section: "home",
    breadcrumb: ["Home"],
    path: "dashboard",
    title: "Workspace overview",
    subtitle: "Your tools, recent research, and next steps.",
    render: (hovered) => (
      <>
        <div className={styles.statusRow}>
          <span className={styles.status}>
            <i /> Live data
          </span>
          <span className={styles.refresh}>Refresh</span>
        </div>
        <div className={styles.kpis}>
          <PlainKpi i={0} label="Current plan" value="Growth" caption="Workspace subscription" />
          <CountKpi i={1} label="Available credits" value={8420} caption="Your current balance" />
          <CountKpi i={2} label="Domain analyses" value={product === "seo" ? 36 : 14} caption="Saved research" />
          <CountKpi i={3} label="Available tools" value={product === "seo" ? 24 : 22} caption="Ready in your workspace" />
        </div>
        <div className={styles.homeRow}>
          <section className={styles.card} style={{ "--i": 4 } as CSSProperties}>
            <span className={styles.kicker}>Domain research</span>
            <h4 className={styles.homeTitle}>Start with your website.</h4>
            <p className={styles.homeBody}>Explore your search presence and find the next opportunity to investigate.</p>
            <span className={styles.fieldLabel}>Website or domain</span>
            <div className={styles.domainRow}>
              <span className={styles.input} data-on={hovered || undefined}>
                <span className={styles.placeholder}>example.com</span>
                <span className={styles.typed}>customer.com</span>
              </span>
              <span className={styles.analyze} data-hover-target data-on={hovered || undefined}>
                Analyze →
              </span>
            </div>
          </section>
          <section className={styles.cardSoft} style={{ "--i": 5 } as CSSProperties}>
            <span className={styles.kicker}>Make it your workspace</span>
            <h4 className={styles.homeTitle}>Bring your context together.</h4>
            <p className={styles.homeBody}>Set up your brand and connect your channels to get more from your tools.</p>
            {["Set up your brand", "Connect social accounts", "Manage your team"].map((link) => (
              <span key={link} className={styles.homeLink}>
                {link} <span aria-hidden="true">↗</span>
              </span>
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

function CountKpi({ label, value, caption, i }: { label: string; value: number; caption: string; i: number }) {
  const shown = useCountUp(value);
  return (
    <div className={styles.kpi} style={{ "--i": i } as CSSProperties}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{Math.round(shown).toLocaleString("en-US")}</span>
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
    subtitle: "How AI assistants mention, cite and describe your brand.",
    render: (hovered) => (
      <div className={styles.row2}>
        <Card i={0} title="Tracked prompts" aside={<span className={styles.muted}>312 prompts · 5 engines</span>}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Prompt</th>
                <th>Engines</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(
                [
                  ["best payroll software for small teams", "5/5", "cited"],
                  ["payroll vs PEO for 20 employees", "3/5", "mentioned"],
                  ["run payroll in two states", "4/5", "cited"],
                  ["payroll software with time tracking", "1/5", "missing"],
                  ["cheapest payroll for startups", "2/5", "mentioned"],
                ] as const
              ).map(([prompt, engines, status], i) => (
                <tr
                  key={prompt}
                  style={{ "--i": i } as CSSProperties}
                  data-hover-target={i === 3 || undefined}
                  data-on={(i === 3 && hovered) || undefined}
                >
                  <td>{prompt}</td>
                  <td className={styles.num}>{engines}</td>
                  <td>
                    <span className={styles.chip} data-status={status}>
                      {status === "cited" ? "Cited" : status === "mentioned" ? "Mentioned" : "Missing"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card i={1} title="Share of AI answers">
          <Donut
            segments={[
              ["You", 31],
              ["Competitor A", 26],
              ["Competitor B", 19],
              ["Others", 24],
            ]}
          />
        </Card>
      </div>
    ),
  },
  {
    id: "keywords",
    section: "seo",
    item: "Position Tracking",
    breadcrumb: ["SEO", "Site Performance", "Position Tracking"],
    path: "seo/rank-tracking",
    title: "Position Tracking",
    subtitle: "Daily rankings for your tracked keywords.",
    render: (hovered) => (
      <Card i={0} title="Tracked keywords" aside={<span className={styles.muted}>Desktop · United States</span>}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Keyword</th>
              <th>Position</th>
              <th>Change</th>
              <th>Volume</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                ["payroll software", 3, "+2", "74,000", [9, 8, 7, 6, 5, 4, 3]],
                ["small business payroll", 1, "+1", "27,100", [4, 3, 3, 2, 2, 1, 1]],
                ["online payroll services", 5, "+4", "14,800", [12, 11, 10, 9, 7, 6, 5]],
                ["payroll for contractors", 2, "+3", "9,900", [8, 7, 6, 5, 4, 3, 2]],
                ["multi state payroll", 4, "−1", "6,600", [3, 3, 4, 3, 3, 4, 4]],
                ["payroll tax calculator", 7, "+5", "60,500", [15, 14, 12, 11, 9, 8, 7]],
              ] as const
            ).map(([kw, pos, change, vol, trend], i) => (
              <tr
                key={kw}
                style={{ "--i": i } as CSSProperties}
                data-hover-target={i === 2 || undefined}
                data-on={(i === 2 && hovered) || undefined}
              >
                <td>{kw}</td>
                <td className={styles.num}>
                  <span className={styles.pos}>{pos}</span>
                </td>
                <td className={styles.num} data-down={change.startsWith("−") || undefined}>
                  {change}
                </td>
                <td className={styles.num}>{vol}</td>
                <td>
                  <Spark points={trend} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    ),
  },
  {
    id: "site-audit",
    section: "seo",
    item: "Site Audit",
    breadcrumb: ["SEO", "Site Performance", "Site Audit"],
    path: "seo/technical",
    title: "Site Audit",
    subtitle: "Crawl health, ranked issues and the fixes in progress.",
    render: (hovered) => (
      <div className={styles.row2}>
        <Card i={0} title="Site health">
          <Gauge value={92} />
          <Bars i0={1} items={[["Errors", 3], ["Warnings", 41], ["Notices", 120]]} />
        </Card>
        <Card i={1} title="Top issues" aside={<span className={styles.muted}>4,812 pages crawled</span>}>
          <ul className={styles.issues}>
            {(
              [
                ["3 pages return 404 from internal links", "Error"],
                ["12 product pages missing structured data", "Warning"],
                ["48 pages with duplicate title tags", "Warning"],
                ["LCP above 2.5s on 6 templates", "Warning"],
              ] as const
            ).map(([issue, level], i) => (
              <li key={issue} style={{ "--i": i } as CSSProperties}>
                <span className={styles.chip} data-status={level === "Error" ? "missing" : "mentioned"}>
                  {level}
                </span>
                <span className={styles.issueText}>{issue}</span>
                <span className={styles.fix} data-hover-target={i === 0 || undefined} data-on={(i === 0 && hovered) || undefined}>
                  {i === 0 && hovered ? (
                    <>
                      <Check size={11} /> Queued
                    </>
                  ) : (
                    "Fix"
                  )}
                </span>
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

const WEEK = ["Mon 12", "Tue 13", "Wed 14", "Thu 15", "Fri 16"];
const POSTS: readonly (readonly [number, string, string])[] = [
  [0, "LinkedIn", "Webinar announcement"],
  [1, "Instagram", "Customer story reel"],
  [1, "Email", "October newsletter"],
  [2, "X", "Launch thread"],
  [3, "LinkedIn", "Product update carousel"],
  [3, "Instagram", "Behind the scenes"],
  [4, "LinkedIn", "Webinar reminder"],
];

export const MARKETING_VIEWS: readonly DashboardView[] = [
  homeView("marketing"),
  {
    id: "calendar",
    section: "social",
    item: "Content Calendar",
    breadcrumb: ["Social", "Publish", "Content Calendar"],
    path: "studio/social-studio/calendar",
    title: "Content Calendar",
    subtitle: "Every channel on one calendar, with briefs attached.",
    render: (hovered) => (
      <Card i={0} title="Week of 12 October" aside={<span className={styles.muted}>24 scheduled · 7 in review</span>}>
        <div className={styles.week}>
          {WEEK.map((day, d) => (
            <div key={day} className={styles.dayCol}>
              <span className={styles.dayName}>{day}</span>
              {POSTS.filter(([pd]) => pd === d).map(([, channel, title], i) => {
                const first = d === 1 && i === 0;
                return (
                  <span
                    key={title}
                    className={styles.post}
                    data-channel={channel}
                    style={{ "--i": d + i } as CSSProperties}
                    data-hover-target={first || undefined}
                    data-on={(first && hovered) || undefined}
                  >
                    <b>{channel}</b>
                    {title}
                  </span>
                );
              })}
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
    subtitle: "Comments, mentions and messages from every channel.",
    render: (hovered) => (
      <div className={styles.inbox}>
        <ul className={styles.threads}>
          {(
            [
              ["Maya R.", "LinkedIn", "Is the webinar recording shared after?"],
              ["Dev Patel", "Instagram", "Loved the carousel — do you integrate with Slack?"],
              ["Google review", "Business Profile", "Smooth onboarding, great support."],
              ["Sam O.", "X", "Can my whole team join the session?"],
            ] as const
          ).map(([who, channel, text], i) => (
            <li key={who} style={{ "--i": i } as CSSProperties} data-active={i === 0 || undefined}>
              <span className={styles.avatar}>{who.slice(0, 1)}</span>
              <span className={styles.threadText}>
                <b>
                  {who} <em>{channel}</em>
                </b>
                {text}
              </span>
            </li>
          ))}
        </ul>
        <div className={styles.thread}>
          <p className={styles.msgIn}>
            <MessageCircle size={12} /> Is the webinar recording shared after?
          </p>
          <p className={styles.msgOut} data-on={hovered || undefined}>
            Yes — everyone who registers gets the recording the next day. See you there!
          </p>
          <div className={styles.composer}>
            <span className={styles.saved}>
              <Sparkles size={11} /> Saved reply · Webinar recording
            </span>
            <span className={styles.send} data-hover-target data-on={hovered || undefined}>
              <Send size={12} /> {hovered ? "Sent" : "Send"}
            </span>
          </div>
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
    subtitle: "Campaign creative, on brand and ready for review.",
    render: (hovered) => (
      <Card i={0} title="Webinar launch · assets" aside={<span className={styles.muted}>Brand kit applied</span>}>
        <div className={styles.assets}>
          {(
            [
              ["Carousel", "5 slides", "approved"],
              ["Reel", "0:30", "review"],
              ["Story", "3 frames", "approved"],
              ["Newsletter", "180 words", "review"],
            ] as const
          ).map(([name, meta, state], i) => (
            <figure key={name} className={styles.asset} style={{ "--i": i } as CSSProperties} data-variant={i}>
              <span className={styles.assetArt} aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <figcaption>
                <b>{name}</b>
                <span>{meta}</span>
                <span
                  className={styles.chip}
                  data-status={i === 1 && hovered ? "cited" : state === "approved" ? "cited" : "mentioned"}
                  data-hover-target={i === 1 || undefined}
                  data-on={(i === 1 && hovered) || undefined}
                >
                  {i === 1 && hovered ? "Approved" : state === "approved" ? "Approved" : "In review"}
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      </Card>
    ),
  },
];

// ---------------------------------------------------------------------------
// Small charts
// ---------------------------------------------------------------------------

function Donut({ segments }: { segments: readonly (readonly [string, number])[] }) {
  const R = 54;
  const C = 2 * Math.PI * R;
  const lengths = segments.map(([, value]) => (value / 100) * C);
  const starts = lengths.map((_, i) => lengths.slice(0, i).reduce((sum, l) => sum + l, 0));
  return (
    <div className={styles.donutWrap}>
      <svg viewBox="0 0 140 140" className={styles.donut}>
        {segments.map(([label], i) => (
          <circle
            key={label}
            cx="70"
            cy="70"
            r={R}
            className={styles.donutSeg}
            data-i={i}
            strokeDasharray={`${lengths[i]} ${C - lengths[i]!}`}
            strokeDashoffset={-starts[i]!}
            style={{ "--i": i } as CSSProperties}
          />
        ))}
        <text x="70" y="68" className={styles.donutValue}>
          31%
        </text>
        <text x="70" y="86" className={styles.donutLabel}>
          your share
        </text>
      </svg>
      <ul className={styles.donutLegend}>
        {segments.map(([label, value], i) => (
          <li key={label}>
            <i data-i={i} />
            {label}
            <b>{value}%</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Gauge({ value }: { value: number }) {
  const R = 46;
  const C = Math.PI * R;
  return (
    <div className={styles.gauge}>
      <svg viewBox="0 0 120 70">
        <path d="M14 62 A46 46 0 0 1 106 62" className={styles.gaugeTrack} />
        <path
          d="M14 62 A46 46 0 0 1 106 62"
          className={styles.gaugeFill}
          strokeDasharray={`${(value / 100) * C} ${C}`}
        />
      </svg>
      <span className={styles.gaugeValue}>{value}</span>
      <span className={styles.gaugeLabel}>Health score</span>
    </div>
  );
}

function Spark({ points }: { points: readonly number[] }) {
  // Lower position numbers are better, so invert for an upward line.
  const max = Math.max(...points);
  const inverted = points.map((p) => max + 1 - p);
  return (
    <svg viewBox="0 0 60 18" className={styles.spark}>
      <path d={linePath(inverted, 60, 16, max + 1)} pathLength={1} />
    </svg>
  );
}
