"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type ReactNode } from "react";
import {
  BarChart3,
  Check,
  FileText,
  Image as ImageIcon,
  Mail,
  MessageCircle,
  Pause,
  Play,
  Search,
  Sparkles,
  Video,
  X,
} from "lucide-react";
import styles from "./motion-explainer.module.css";

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReduced(onChange: () => void): () => void {
  const query = globalThis.matchMedia?.(REDUCED_QUERY);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

function readReduced(): boolean {
  return globalThis.matchMedia?.(REDUCED_QUERY).matches ?? false;
}

/** Each scene plays this long; four scenes make a ten-second loop. */
export const SCENE_MS = 2500;

type Scene = { id: string; label: string; render: () => ReactNode };

/**
 * A short looping product story, built from DOM and CSS rather than a video
 * file: it costs a few kilobytes, stays sharp at any size and uses the brand
 * tokens. Plays only while on screen and while the tab is visible, can be
 * paused (WCAG 2.2.2), and under reduced motion shows a still frame the
 * viewer steps through with the timeline.
 *
 * Motion budget: scene contents enter with 280–420ms var(--ease-out) and
 * 60–90ms staggers; the typing reveal and progress fills are linear because
 * they represent constant progress.
 */
export function MotionExplainer({ story }: { story: "seo" | "marketing" }) {
  const scenes = story === "seo" ? SEO_SCENES : MARKETING_SCENES;
  const [index, setIndex] = useState(0);
  const [cycle, setCycle] = useState(0);
  const [userPaused, setUserPaused] = useState(false);
  const reduced = useSyncExternalStore(subscribeReduced, readReduced, () => false);
  // Under reduced motion the still frame shows the outcome until the viewer steps.
  const [stepped, setStepped] = useState(false);
  const [onScreen, setOnScreen] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const root = useRef<HTMLDivElement>(null);
  const remaining = useRef(SCENE_MS);
  const startedAt = useRef(0);

  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => setOnScreen(Boolean(entry?.isIntersecting)), {
      threshold: 0.3,
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const sync = () => setPageVisible(!document.hidden);
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);

  const playing = onScreen && pageVisible && !userPaused && !reduced;

  // A new scene starts a fresh countdown.
  useEffect(() => {
    remaining.current = SCENE_MS;
  }, [index, cycle]);

  useEffect(() => {
    if (!playing) return;
    startedAt.current = performance.now();
    const timer = window.setTimeout(() => {
      setIndex((current) => {
        const next = (current + 1) % scenes.length;
        if (next === 0) setCycle((value) => value + 1);
        return next;
      });
    }, remaining.current);
    return () => {
      window.clearTimeout(timer);
      remaining.current = Math.max(0, remaining.current - (performance.now() - startedAt.current));
    };
  }, [playing, index, cycle, scenes.length]);

  const shown = reduced && !stepped ? scenes.length - 1 : index;
  const active = scenes[shown] ?? scenes[0];
  if (!active) return null;

  return (
    <div
      ref={root}
      className={styles.player}
      data-playing={playing}
      data-reduced={reduced}
      style={{ "--scene-ms": `${SCENE_MS}ms` } as CSSProperties}
    >
      <div className={styles.stage} aria-hidden="true">
        {/* Keyed so every visit to a scene replays its entrance. */}
        <div key={`${active.id}:${cycle}`} className={styles.scene}>
          {active.render()}
        </div>
      </div>
      <p className={styles.srOnly} aria-live="polite">
        {`Step ${shown + 1} of ${scenes.length}: ${active.label}`}
      </p>

      <div className={styles.bar}>
        <button
          type="button"
          className={styles.play}
          onClick={() => setUserPaused((value) => !value)}
          aria-label={userPaused ? "Play product story" : "Pause product story"}
          disabled={reduced}
        >
          {userPaused || reduced ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
        </button>
        <ol className={styles.timeline}>
          {scenes.map((scene, i) => (
            <li key={scene.id}>
              <button
                type="button"
                className={styles.segment}
                data-state={i < shown ? "done" : i === shown ? "active" : "next"}
                aria-current={i === shown ? "step" : undefined}
                onClick={() => {
                  setStepped(true);
                  setIndex(i);
                  remaining.current = SCENE_MS;
                }}
              >
                <span className={styles.segmentLabel}>
                  <span className={styles.segmentIndex}>{i + 1}</span>
                  {scene.label}
                </span>
                <span className={styles.segmentTrack}>
                  <span key={`${shown}:${cycle}`} className={styles.segmentFill} />
                </span>
              </button>
            </li>
          ))}
        </ol>
        <span className={styles.tag}>Illustrative</span>
      </div>
    </div>
  );
}

/** Stagger slot for an element inside a scene. */
function at(step: number): CSSProperties {
  return { "--d": step } as CSSProperties;
}

// ---------------------------------------------------------------------------
// SEO story: invisible in the answer → found the gap → fixed → cited.
// ---------------------------------------------------------------------------

const QUESTION = "Best payroll software for a 20-person team?";

function ChatFrame({ children, title = "AI assistant" }: { children: ReactNode; title?: string }) {
  return (
    <div className={styles.window}>
      <div className={styles.windowBar}>
        <span className={styles.windowDots} />
        <span className={styles.windowTitle}>
          <Sparkles size={12} /> {title}
        </span>
      </div>
      <div className={styles.windowBody}>{children}</div>
    </div>
  );
}

const SEO_SCENES: readonly Scene[] = [
  {
    id: "ask",
    label: "A buyer asks AI",
    render: () => (
      <div className={styles.center}>
        <ChatFrame>
          <p className={`${styles.question} ${styles.typing}`}>{QUESTION}</p>
          <div className={styles.thinking} style={at(9)}>
            <span />
            <span />
            <span />
          </div>
        </ChatFrame>
      </div>
    ),
  },
  {
    id: "answer",
    label: "You're left out",
    render: () => (
      <div className={styles.center}>
        <ChatFrame>
          <p className={styles.question}>{QUESTION}</p>
          <ul className={styles.answer}>
            {["Competitor A — easiest setup", "Competitor B — best for startups", "Competitor C — multi-state filing"].map(
              (line, i) => (
                <li key={line} className={styles.rise} style={at(i)}>
                  <span className={styles.dot} />
                  {line}
                </li>
              ),
            )}
            <li className={`${styles.missing} ${styles.rise}`} style={at(4)}>
              <X size={13} /> Your brand — not mentioned
            </li>
          </ul>
        </ChatFrame>
      </div>
    ),
  },
  {
    id: "fix",
    label: "Nuxtron finds the fix",
    render: () => (
      <div className={styles.split}>
        <div className={`${styles.panel} ${styles.rise}`} style={at(0)}>
          <p className={styles.panelKicker}>
            <Search size={13} /> Gap found
          </p>
          <p className={styles.panelBig}>58 prompts</p>
          <p className={styles.panelSmall}>where competitors are cited instead</p>
          <div className={styles.scan}>
            {[72, 48, 86, 34, 60].map((h, i) => (
              <span key={i} className={styles.scanBar} style={{ "--h": h / 100, ...at(i) } as CSSProperties} />
            ))}
            <span className={styles.scanLine} />
          </div>
        </div>
        <ul className={styles.checklist}>
          {["Brief created from the prompts", "Comparison page rewritten", "FAQ schema added", "Page published"].map(
            (item, i) => (
              <li key={item} className={styles.rise} style={at(i + 2)}>
                <span className={styles.tick}>
                  <Check size={12} />
                </span>
                {item}
              </li>
            ),
          )}
        </ul>
      </div>
    ),
  },
  {
    id: "cited",
    label: "Now you're the answer",
    render: () => (
      <div className={styles.split}>
        <ChatFrame>
          <p className={styles.question}>{QUESTION}</p>
          <ul className={styles.answer}>
            <li className={`${styles.cited} ${styles.rise}`} style={at(0)}>
              <Check size={13} /> Your brand — recommended
              <span className={styles.cite}>cited</span>
            </li>
            <li className={styles.rise} style={at(1)}>
              <span className={styles.dot} />
              Competitor A — easiest setup
            </li>
          </ul>
        </ChatFrame>
        <div className={`${styles.panel} ${styles.rise}`} style={at(2)}>
          <p className={styles.panelKicker}>
            <BarChart3 size={13} /> AI answer share
          </p>
          <p className={styles.panelBig}>
            <span className={styles.from}>18%</span>
            <span className={styles.to}>31%</span>
          </p>
          <div className={styles.meter}>
            <span className={styles.meterFill} />
          </div>
          <p className={styles.panelSmall}>tracked across ChatGPT, Perplexity, Gemini and Claude</p>
        </div>
      </div>
    ),
  },
];

// ---------------------------------------------------------------------------
// Marketing story: brief → assets → calendar → replies.
// ---------------------------------------------------------------------------

const MARKETING_SCENES: readonly Scene[] = [
  {
    id: "brief",
    label: "Start with a brief",
    render: () => (
      <div className={styles.center}>
        <div className={styles.window}>
          <div className={styles.windowBar}>
            <span className={styles.windowDots} />
            <span className={styles.windowTitle}>
              <FileText size={12} /> Campaign brief
            </span>
          </div>
          <div className={styles.windowBody}>
            <p className={`${styles.briefTitle} ${styles.typing}`}>Webinar launch — October</p>
            {["Goal: 400 registrations", "Audience: operations leads", "Channels: LinkedIn, Instagram, email"].map(
              (line, i) => (
                <p key={line} className={`${styles.briefLine} ${styles.rise}`} style={at(i + 6)}>
                  {line}
                </p>
              ),
            )}
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "create",
    label: "Make every format",
    render: () => (
      <div className={styles.assets}>
        {[
          { icon: <ImageIcon size={18} />, name: "Carousel", meta: "5 slides" },
          { icon: <Video size={18} />, name: "Reel", meta: "30 seconds" },
          { icon: <Mail size={18} />, name: "Newsletter", meta: "180 words" },
        ].map((asset, i) => (
          <div key={asset.name} className={`${styles.asset} ${styles.fan}`} style={{ "--i": i - 1, ...at(i) } as CSSProperties}>
            <span className={styles.assetIcon}>{asset.icon}</span>
            <span className={styles.assetName}>{asset.name}</span>
            <span className={styles.assetMeta}>{asset.meta}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    id: "schedule",
    label: "Schedule it",
    render: () => (
      <div className={styles.calendar}>
        {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day, i) => (
          <div key={day} className={styles.day}>
            <span className={styles.dayName}>{day}</span>
            {i > 0 ? (
              <span className={`${styles.slot} ${styles.drop}`} style={at(i)}>
                {["LinkedIn", "Instagram", "Email", "LinkedIn"][i - 1]}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    ),
  },
  {
    id: "engage",
    label: "Answer every reply",
    render: () => (
      <div className={styles.split}>
        <ul className={styles.inbox}>
          {["Is the recording shared after?", "Can my team join too?", "Loved the carousel 👏"].map((msg, i) => (
            <li key={msg} className={styles.rise} style={at(i)}>
              <MessageCircle size={14} />
              {msg}
            </li>
          ))}
        </ul>
        <div className={`${styles.panel} ${styles.rise}`} style={at(2)}>
          <p className={styles.panelKicker}>
            <BarChart3 size={13} /> Engagement by channel
          </p>
          <div className={styles.bars}>
            {[["LinkedIn", 0.78], ["Instagram", 0.62], ["Email", 0.45]].map(([label, value], i) => (
              <div key={label as string} className={styles.barRow}>
                <span>{label}</span>
                <span className={styles.barTrack}>
                  <span className={styles.barFill} style={{ "--v": value, ...at(i + 3) } as CSSProperties} />
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
  },
];
