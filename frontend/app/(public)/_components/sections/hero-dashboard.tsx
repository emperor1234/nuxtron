"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type ComponentRef, type CSSProperties } from "react";
import Image from "next/image";
import {
  Bell,
  ChevronDown,
  Clapperboard,
  Home,
  LayoutGrid,
  Menu,
  Pause,
  Play,
  Plus,
  Search,
  Settings,
  Share2,
} from "lucide-react";
import { MARKETING_VIEWS, SEO_VIEWS, type DashboardView, type RailSection } from "./hero-dashboard-views";
import styles from "./hero-dashboard.module.css";

/** The app is laid out at this size and scaled to fit, like a screenshot. */
const APP_W = 1200;
const APP_H = 640;
/** Smallest scale before the frame crops instead of shrinking further. */
const MIN_SCALE = 0.5;

const REDUCED = "(prefers-reduced-motion: reduce)";
function subscribeReduced(onChange: () => void) {
  const query = globalThis.matchMedia?.(REDUCED);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}
const readReduced = () => globalThis.matchMedia?.(REDUCED).matches ?? false;

type RailEntry = {
  key: RailSection | "settings";
  label: string;
  Icon: typeof Search;
  /** What the section shows when opened — real group labels and tools. */
  groups?: readonly { label: string; items: readonly string[] }[];
};

/** Each product's sidebar, as the real dashboard renders it for that product. */
const RAILS: Record<"seo" | "marketing", readonly RailEntry[]> = {
  seo: [
    {
      key: "seo",
      label: "SEO",
      Icon: Search,
      groups: [
        { label: "Content & on-page", items: ["On-Page Optimizer", "Content Brief", "AI Article Writer"] },
        { label: "AI search visibility", items: ["Answer Engine (AEO)", "Prompt Research"] },
      ],
    },
    {
      key: "apps",
      label: "Business",
      Icon: LayoutGrid,
      groups: [{ label: "Customer operations", items: ["CRM", "Workflows"] }],
    },
  ],
  marketing: [
    {
      key: "social",
      label: "Social",
      Icon: Share2,
      groups: [
        { label: "Publish", items: ["Post Scheduler", "Content Calendar"] },
        { label: "Engage", items: ["Social Inbox", "Comment Replies"] },
      ],
    },
    {
      key: "studio",
      label: "Studio",
      Icon: Clapperboard,
      groups: [{ label: "Create", items: ["Editor", "Image Studio", "Short Video Factory"] }],
    },
    {
      key: "apps",
      label: "Business",
      Icon: LayoutGrid,
      groups: [{ label: "Customer operations", items: ["CRM", "Workflows"] }],
    },
  ],
};

/** Ms from a screen appearing: use something on it, then navigate on. */
const T_USE_MOVE = 500;
const T_USE_ON = 1300;
const T_NAV = 3200;
const STEP = 700;

/**
 * Hero product shot: the real Nuxtron dashboard, navigating itself the way a
 * person would — use the page, open a sidebar section, pick the tool. Plays
 * only while visible, pauses with the tab, can be paused (WCAG 2.2.2), and is
 * a still frame under reduced motion.
 */
export function HeroDashboard({ product }: { product: "seo" | "marketing" }) {
  const views = product === "seo" ? SEO_VIEWS : MARKETING_VIEWS;
  const rail = RAILS[product];
  const reduced = useSyncExternalStore(subscribeReduced, readReduced, () => false);
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [pressed, setPressed] = useState<string | null>(null);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [clicking, setClicking] = useState(false);
  const [scale, setScale] = useState(1);
  const [onScreen, setOnScreen] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const [userPaused, setUserPaused] = useState(false);
  const shell = useRef<ComponentRef<"div">>(null);
  const app = useRef<ComponentRef<"div">>(null);
  // Read by the choreography without restarting it: the choreography itself
  // opens sections, and a dependency on `open` would cancel its own clicks.
  const openRef = useRef<string | null>(null);
  useEffect(() => {
    openRef.current = open;
  }, [open]);

  const playing = onScreen && pageVisible && !userPaused && !reduced;
  const view = views[index] ?? views[0]!;
  const next = views[(index + 1) % views.length]!;

  useEffect(() => {
    const element = shell.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      const width = entry?.contentRect.width ?? APP_W;
      setScale(Math.max(MIN_SCALE, Math.min(1, width / APP_W)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const element = shell.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => setOnScreen(Boolean(entry?.isIntersecting)), {
      threshold: 0.2,
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const sync = () => setPageVisible(!document.hidden);
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);

  // Choreography: use the page, then navigate to the next one.
  useEffect(() => {
    if (!playing) return;
    const root = app.current;
    if (!root) return;

    const pointAt = (selector: string) => {
      const target = root.querySelector(selector);
      if (!target) return null;
      const a = root.getBoundingClientRect();
      const r = target.getBoundingClientRect();
      return { x: (r.left - a.left + Math.min(r.width * 0.5, 60)) / scale, y: (r.top - a.top + r.height * 0.6) / scale };
    };
    const moveTo = (selector: string) => {
      const point = pointAt(selector);
      if (point) setCursor(point);
    };
    const click = (key: string) => {
      setClicking(true);
      setPressed(key);
      window.setTimeout(() => {
        setClicking(false);
        setPressed(null);
      }, 180);
    };
    const advance = () => {
      setHovered(false);
      setIndex((current) => (current + 1) % views.length);
    };

    const timers: number[] = [];
    const at = (ms: number, fn: () => void) => timers.push(window.setTimeout(fn, ms));

    at(T_USE_MOVE, () => moveTo(`[data-view="${view.id}"] [data-hover-target]`));
    at(T_USE_ON, () => setHovered(true));

    if (next.section === "home") {
      at(T_NAV, () => moveTo('[data-rail="home"]'));
      at(T_NAV + STEP, () => {
        click("home");
        setOpen(null);
      });
      at(T_NAV + STEP + 220, advance);
    } else {
      const item = `[data-item="${next.item}"]`;
      let t = T_NAV;
      if (openRef.current !== next.section) {
        at(t, () => moveTo(`[data-rail="${next.section}"]`));
        at(t + STEP, () => {
          click(next.section);
          setOpen(next.section);
        });
        t += STEP + 450;
      }
      at(t, () => moveTo(item));
      at(t + STEP, () => click(next.item ?? ""));
      at(t + STEP + 220, advance);
    }
    return () => timers.forEach(window.clearTimeout);
  }, [playing, view.id, next, scale, views.length]);

  return (
    <div className={styles.hero}>
      <div ref={shell} className={styles.shell} style={{ height: APP_H * scale } as CSSProperties}>
        <div
          ref={app}
          className={styles.app}
          role="img"
          aria-label={`The Nuxtron ${product === "seo" ? "SEO" : "Marketing"} dashboard moving through ${views
            .map((v) => v.title)
            .join(", ")}`}
          style={{ width: APP_W, height: APP_H, transform: `scale(${scale})` } as CSSProperties}
        >
          <div className={styles.body} aria-hidden="true">
            <aside className={styles.rail}>
              <span className={styles.brand}>
                <Image src="/brand/nuxtron-icon-square.svg" alt="" width={24} height={24} className={styles.mark} /> Nuxtron
              </span>
              <span className={styles.workspace}>
                <span className={styles.wsAvatar}>C</span>
                <span>
                  <b>Customer</b>
                  {product === "seo" ? "Nuxtron SEO" : "Nuxtron Marketing"}
                </span>
              </span>
              <span className={styles.railHeading}>Workspace</span>
              <span
                data-rail="home"
                className={styles.homeItem}
                data-active={view.section === "home" || undefined}
                data-pressed={pressed === "home" || undefined}
              >
                <Home size={15} /> Home
              </span>
              {rail.map(({ key, label, Icon, groups }) => {
                const isOpen = open === key && Boolean(groups);
                return (
                  <div key={key} className={styles.section}>
                    <span
                      data-rail={key}
                      className={styles.sectionButton}
                      data-open={isOpen || undefined}
                      data-active={view.section === key || undefined}
                      data-pressed={pressed === key || undefined}
                    >
                      <Icon size={16} />
                      {label}
                      <ChevronDown size={14} className={styles.chevron} />
                    </span>
                    {groups ? (
                      <div className={styles.flyout} data-open={isOpen || undefined}>
                        <div className={styles.flyoutInner}>
                          {groups.map((group) => (
                            <div key={group.label} className={styles.flyoutGroup}>
                              <span className={styles.flyoutLabel}>{group.label}</span>
                              {group.items.map((item) => (
                                <span
                                  key={item}
                                  data-item={item}
                                  className={styles.flyoutLink}
                                  data-active={view.item === item || undefined}
                                  data-pressed={pressed === item || undefined}
                                >
                                  {item}
                                </span>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })}
              <span className={styles.account}>
                Account settings <Settings size={13} />
              </span>
            </aside>

            <div className={styles.main}>
              <div className={styles.topbar}>
                <span className={styles.iconButton}>
                  <Menu size={16} />
                </span>
                <span className={styles.search}>
                  <Search size={14} /> Search your workspace <kbd>⌘ K</kbd>
                </span>
                <span className={styles.topAction}>
                  <Plus size={13} /> New analysis
                </span>
                <span className={styles.topAction}>
                  <Bell size={13} /> Alerts
                </span>
                <span className={styles.me}>C</span>
              </div>

              <div key={view.id} className={styles.view} data-view={view.id}>
                <span className={styles.breadcrumb}>
                  {view.breadcrumb.map((part, i) => (
                    <span key={part} data-last={i === view.breadcrumb.length - 1 || undefined}>
                      {part}
                    </span>
                  ))}
                </span>
                <h3 className={styles.viewTitle}>{view.title}</h3>
                <p className={styles.viewSubtitle}>{view.subtitle}</p>
                {view.render(hovered)}
              </div>

              <span className={styles.ira}>IRA AI AGENT</span>
            </div>
          </div>

          {!reduced && cursor ? (
            <span
              className={styles.cursor}
              data-clicking={clicking || undefined}
              style={{ transform: `translate(${cursor.x}px, ${cursor.y}px)` } as CSSProperties}
              aria-hidden="true"
            >
              <svg viewBox="0 0 20 20" width="20" height="20">
                <path d="M3 2l13 7-6 1.6L7.4 17z" />
              </svg>
              <span className={styles.ripple} />
            </span>
          ) : null}
        </div>
      </div>

      {!reduced ? (
        <button
          type="button"
          className={styles.pause}
          onClick={() => setUserPaused((value) => !value)}
          aria-label={userPaused ? "Play dashboard animation" : "Pause dashboard animation"}
        >
          {userPaused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
        </button>
      ) : null}
    </div>
  );
}

export type { DashboardView };
