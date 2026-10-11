"use client";

/**
 * Interactive product demo: a clickable miniature of the Nuxtron app.
 *
 * Pattern: the sidebar is a WAI-ARIA tablist, not a row of aria-pressed
 * buttons. Picking a view replaces the single content pane with that view's
 * panel and exactly one view is selected at a time — that is the tabs
 * pattern. aria-pressed describes independent on/off toggles, which would
 * leave screen-reader users without the tab ↔ panel relationship.
 * Activation is automatic (arrow keys select) because switching is instant
 * and local: no request, nothing to confirm.
 *
 * Motion: every panel is rendered into one grid cell and switched with CSS
 * transitions (not keyframes), so rapid clicks retarget instead of
 * restarting. The pane never changes height between views. All numbers are
 * data from a generic customer account.
 */

import {
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type KeyboardEvent,
} from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  FlaskConical,
  Minus,
  Pause,
  Play,
} from "lucide-react";
import Image from "next/image";
import { getProviderMark } from "@/app/lib/provider-marks";
import { ProviderLogo } from "@/app/components/marketing/provider-logo";
import type { DemoContent, DemoView } from "../../_content/types";
import { Reveal } from "../reveal";
import { SectionIconGlyph } from "./icon";
import styles from "./demo-section.module.css";

/* ---------------------------------------------------------------- helpers */

/** Bar heights as percentages of the largest value (min 4% so a bar stays visible). */
export function barHeights(values: readonly number[]): number[] {
  const finite = values.map((value) =>
    Number.isFinite(value) ? Math.max(0, value) : 0,
  );
  const max = Math.max(0, ...finite);
  if (max === 0) return finite.map(() => 4);
  return finite.map((value) =>
    Math.max(4, Math.round((value / max) * 1000) / 10),
  );
}

export type DeltaDirection = "up" | "down" | "flat";

/** Reads the sign of a delta label such as "+12%", "−3" or "-4 pts". */
export function deltaDirection(delta: string): DeltaDirection {
  const trimmed = delta.trim();
  if (trimmed.startsWith("+")) return "up";
  if (trimmed.startsWith("-") || trimmed.startsWith("−")) return "down";
  return "flat";
}

/** Stable 1–8 series index for a tag, so the same tag always gets the same dot colour. */
export function seriesForTag(tag: string): number {
  let hash = 0;
  for (const char of tag.toLowerCase())
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return (hash % 8) + 1;
}

/** Fixed locale so server and client render identical strings. */
const numberFormat = new Intl.NumberFormat("en-US");

/** Stagger stops growing after this many bars so long charts don't drag. */
const MAX_STAGGER_STEPS = 8;
const TOUR_STEP_MS = 6400;

/* ------------------------------------------------------- media query hook */

const WIDE_QUERY = "(min-width: 768px)";

function subscribeWide(onChange: () => void) {
  if (
    typeof window === "undefined" ||
    typeof window.matchMedia !== "function"
  ) {
    return () => {
      // Nothing was subscribed, so there is nothing to clean up.
    };
  }
  const query = window.matchMedia(WIDE_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function readWide() {
  if (typeof window.matchMedia !== "function") return true;
  return window.matchMedia(WIDE_QUERY).matches;
}

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void) {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function")
    return () => undefined;
  const query = window.matchMedia(REDUCED_MOTION_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function readReducedMotion() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia(REDUCED_MOTION_QUERY).matches
  );
}

/** Sidebar is vertical from 768px up and a horizontal tab row below it. */
function useTabOrientation(): "vertical" | "horizontal" {
  const wide = useSyncExternalStore(subscribeWide, readWide, () => true);
  return wide ? "vertical" : "horizontal";
}

/* -------------------------------------------------------------- component */

export function DemoSection({ content }: { content: DemoContent }) {
  const { views } = content;
  const baseId = useId();
  const headingId = `${baseId}-heading`;
  const disclaimerId = `${baseId}-disclaimer`;
  const tabId = (index: number) => `${baseId}-tab-${index}`;
  const panelId = (index: number) => `${baseId}-panel-${index}`;

  const [selectedId, setSelectedId] = useState(views[0]?.id ?? "");
  const activeIndex = Math.max(
    0,
    views.findIndex((view) => view.id === selectedId),
  );
  const activeView = views[activeIndex];

  const orientation = useTabOrientation();
  const prefersReducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    readReducedMotion,
    () => false,
  );
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const surfaceRef = useRef<HTMLDivElement>(null);
  /** True while the surface is still below the fold: bars wait, then grow on entry. */
  const [chartPrimed, setChartPrimed] = useState(false);
  const [inView, setInView] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(false);
  const [playbackMode, setPlaybackMode] = useState<
    "auto" | "paused" | "manual"
  >("auto");
  const isEffectivelyInView =
    inView || typeof IntersectionObserver === "undefined";
  const isPlaying =
    documentVisible &&
    (playbackMode === "manual" ||
      (isEffectivelyInView &&
        playbackMode === "auto" &&
        !prefersReducedMotion));

  useEffect(() => {
    const updateVisibility = () =>
      setDocumentVisible(document.visibilityState === "visible");
    updateVisibility();
    document.addEventListener("visibilitychange", updateVisibility);
    return () =>
      document.removeEventListener("visibilitychange", updateVisibility);
  }, []);

  useEffect(() => {
    const surface = surfaceRef.current;
    if (!surface || typeof IntersectionObserver === "undefined") return;
    let seenOutside = false;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) return;
        setInView(entry.isIntersecting);
        if (entry.isIntersecting) {
          setChartPrimed(false);
        } else if (!seenOutside) {
          // Only hide the bars when they start off-screen, so nothing visible
          // ever blinks out.
          seenOutside = true;
          setChartPrimed(true);
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(surface);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!activeView || !isPlaying || views.length < 2) return;
    const timer = window.setTimeout(() => {
      const next = (activeIndex + 1) % views.length;
      setSelectedId(views[next]?.id ?? views[0]?.id ?? "");
    }, TOUR_STEP_MS);
    return () => window.clearTimeout(timer);
  }, [activeIndex, activeView, isPlaying, views]);

  if (!activeView) return null;

  const select = (index: number) => {
    const view = views[index];
    if (!view) return;
    setPlaybackMode("paused");
    setSelectedId(view.id);
    tabRefs.current[index]?.focus();
  };

  const onTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    const last = views.length - 1;
    let next: number | null = null;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowRight":
        next = index === last ? 0 : index + 1;
        break;
      case "ArrowUp":
      case "ArrowLeft":
        next = index === 0 ? last : index - 1;
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = last;
        break;
      default:
        return;
    }
    event.preventDefault();
    select(next);
  };

  return (
    <section className={styles.section} aria-labelledby={headingId}>
      <Reveal className={styles.head}>
        <p className={styles.eyebrow}>
          <span aria-hidden="true" />
          {content.eyebrow}
        </p>
        <h2 id={headingId} className={styles.title}>
          {content.title}
        </h2>
        <p className={styles.intro}>{content.intro}</p>
      </Reveal>

      <Reveal delay={0.08} className={styles.frame}>
        <div
          ref={surfaceRef}
          className={styles.surface}
          data-primed={chartPrimed ? "true" : undefined}
          data-tour-playing={isPlaying ? "true" : undefined}
          style={{ "--tour-step": `${TOUR_STEP_MS}ms` } as CSSProperties}
        >
          <div className={styles.chrome}>
            <span className={styles.dots} aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span className={styles.address} aria-hidden="true">
              nuxtron / {activeView.id}
            </span>
            <button
              type="button"
              className={styles.playControl}
              aria-label={
                isPlaying ? "Pause product tour" : "Play product tour"
              }
              aria-pressed={isPlaying}
              title={isPlaying ? "Pause product tour" : "Play product tour"}
              onClick={() => {
                if (isPlaying) {
                  setPlaybackMode("paused");
                  return;
                }
                // Explicit playback is user-directed; auto-play alone depends on
                // the intersection observer. Sample visibility here as well as
                // in the effect so a just-visible page can start immediately.
                setDocumentVisible(document.visibilityState === "visible");
                setPlaybackMode("manual");
              }}
            >
              {isPlaying ? (
                <Pause size={14} aria-hidden="true" />
              ) : (
                <Play size={14} aria-hidden="true" />
              )}
              <span>{isPlaying ? "Pause tour" : "Play tour"}</span>
            </button>
            {content.disclaimer ? (
              <span id={disclaimerId} className={styles.disclaimer}>
                <FlaskConical size={13} strokeWidth={1.8} aria-hidden="true" />
                {content.disclaimer}
              </span>
            ) : null}
          </div>

          <div className={styles.body}>
            <div className={styles.sidebar}>
              <p className={styles.workspace} aria-hidden="true">
                <Image
                  src="/brand/nuxtron-icon-square.svg"
                  alt=""
                  width={18}
                  height={18}
                  className={styles.workspaceMark}
                />
                Nuxtron
              </p>
              <div
                role="tablist"
                aria-label={`${content.title}: demo views`}
                aria-orientation={orientation}
                className={styles.tablist}
              >
                {views.map((view, index) => {
                  const selected = index === activeIndex;
                  return (
                    <button
                      key={view.id}
                      ref={(node) => {
                        tabRefs.current[index] = node;
                      }}
                      type="button"
                      role="tab"
                      id={tabId(index)}
                      aria-selected={selected}
                      aria-controls={panelId(index)}
                      tabIndex={selected ? 0 : -1}
                      className={styles.tab}
                      onFocus={() => setPlaybackMode("paused")}
                      onClick={() => select(index)}
                      onKeyDown={(event) => onTabKeyDown(event, index)}
                    >
                      <SectionIconGlyph
                        name={view.icon}
                        size={16}
                        className={styles.tabIcon}
                      />
                      <span className={styles.tabLabel}>{view.label}</span>
                      <span
                        className={styles.tabProgress}
                        aria-hidden="true"
                        data-running={
                          selected && isPlaying ? "true" : undefined
                        }
                      />
                    </button>
                  );
                })}
              </div>
            </div>

            <div className={styles.panels}>
              {views.map((view, index) => (
                <DemoPanel
                  key={view.id}
                  view={view}
                  active={index === activeIndex}
                  id={panelId(index)}
                  labelledBy={tabId(index)}
                  describedBy={content.disclaimer ? disclaimerId : undefined}
                />
              ))}
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

/* ------------------------------------------------------------------ panel */

function DemoPanel({
  view,
  active,
  id,
  labelledBy,
  describedBy,
}: {
  view: DemoView;
  active: boolean;
  id: string;
  labelledBy: string;
  describedBy?: string;
}) {
  return (
    <div
      role="tabpanel"
      id={id}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      // Inactive panels are visibility:hidden after their fade (CSS), which
      // already removes them from focus order and the accessibility tree;
      // inert covers the fade window too.
      inert={!active}
      data-active={active ? "true" : "false"}
      className={styles.panel}
    >
      <header className={styles.panelHead}>
        <h3 className={styles.panelTitle}>{view.heading}</h3>
        <p className={styles.panelSub}>{view.subheading}</p>
      </header>

      {view.kpis.length > 0 ? (
        <dl className={styles.kpis}>
          {view.kpis.map((kpi) => (
            <div key={kpi.label} className={styles.kpi}>
              <dt className={styles.kpiLabel}>{kpi.label}</dt>
              <dd className={styles.kpiValue}>{kpi.value}</dd>
              {kpi.delta ? <Delta value={kpi.delta} /> : null}
            </div>
          ))}
        </dl>
      ) : null}

      {view.chart || view.list ? (
        <div className={styles.details}>
          {view.chart ? <BarChart chart={view.chart} /> : null}
          {view.list ? (
            <div className={styles.card}>
              <h4 className={styles.cardTitle}>{view.list.label}</h4>
              <ul className={styles.list}>
                {view.list.rows.map((row, index) => (
                  <li key={`${row.tag}-${index}`} className={styles.row}>
                    <span
                      className={styles.chip}
                      data-provider={getProviderMark(row.tag)?.key}
                      style={
                        {
                          "--chip-dot": `var(--series-${seriesForTag(row.tag)})`,
                        } as CSSProperties
                      }
                    >
                      {getProviderMark(row.tag) ? (
                        <>
                          <ProviderLogo label={row.tag} size={14} decorative />
                          <span className={styles.srOnly}>{row.tag}</span>
                        </>
                      ) : (
                        row.tag
                      )}
                    </span>
                    <span className={styles.rowText}>{row.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function Delta({ value }: { value: string }) {
  const direction = deltaDirection(value);
  const Icon =
    direction === "up"
      ? ArrowUpRight
      : direction === "down"
        ? ArrowDownRight
        : Minus;
  return (
    <dd className={styles.delta} data-direction={direction}>
      <Icon size={13} strokeWidth={2} aria-hidden="true" />
      {value}
    </dd>
  );
}

/* -------------------------------------------------------------- bar chart */

function BarChart({ chart }: { chart: NonNullable<DemoView["chart"]> }) {
  const heights = barHeights(chart.bars.map((bar) => bar.value));
  const last = chart.bars.length - 1;
  return (
    <div className={styles.card}>
      <h4 className={styles.cardTitle}>{chart.label}</h4>

      {/* Visual chart. Each bar is focusable and names its own value; the
          tooltip repeats it visually and is hidden from assistive tech. */}
      <div
        className={styles.chart}
        role="group"
        aria-label={`${chart.label} chart`}
      >
        {chart.bars.map((bar, index) => {
          const formatted = numberFormat.format(bar.value);
          const align =
            index === 0 ? "start" : index === last ? "end" : "center";
          return (
            <div
              key={`${bar.label}-${index}`}
              role="img"
              tabIndex={0}
              aria-label={`${bar.label}: ${formatted}`}
              className={styles.barColumn}
              data-align={align}
              style={
                {
                  "--h": `${heights[index]}%`,
                  "--i": Math.min(index, MAX_STAGGER_STEPS),
                } as CSSProperties
              }
            >
              <span className={styles.barTrack}>
                <span className={styles.bar} />
                <span className={styles.tooltip} aria-hidden="true">
                  <span className={styles.tooltipLabel}>{bar.label}</span>
                  <span className={styles.tooltipValue}>{formatted}</span>
                </span>
              </span>
              <span className={styles.barLabel} aria-hidden="true">
                {getProviderMark(bar.label) ? (
                  <ProviderLogo label={bar.label} size={16} decorative />
                ) : (
                  bar.label
                )}
              </span>
            </div>
          );
        })}
      </div>

      <table className={styles.srOnly}>
        <caption>{chart.label}</caption>
        <thead>
          <tr>
            <th scope="col">Label</th>
            <th scope="col">Value</th>
          </tr>
        </thead>
        <tbody>
          {chart.bars.map((bar, index) => (
            <tr key={`${bar.label}-${index}`}>
              <th scope="row">{bar.label}</th>
              <td>{numberFormat.format(bar.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
