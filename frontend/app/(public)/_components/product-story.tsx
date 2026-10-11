"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  ArrowRight,
  Check,
  FileText,
  Search,
  CalendarDays,
  Pause,
  Play,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import styles from "../home.module.css";

const steps = [
  {
    id: "research",
    label: "Find the opportunity",
    icon: Search,
    title: "Start with a better question.",
    caption: "Search & AI visibility",
    prompt: "Where does our brand show up in search?",
    rows: [
      "Explore a domain",
      "Compare search visibility",
      "Review keywords and citations",
    ],
    detail: "Connect research to the work that comes next.",
  },
  {
    id: "create",
    label: "Shape the response",
    icon: FileText,
    title: "Turn context into content.",
    caption: "Content workspace",
    prompt: "Build a brief around what our audience needs.",
    rows: [
      "Collect the research",
      "Develop a content brief",
      "Review the first draft",
    ],
    detail: "Keep your research and brand context beside the draft.",
  },
  {
    id: "publish",
    label: "Plan the delivery",
    icon: CalendarDays,
    title: "Give good work a destination.",
    caption: "Social workspace",
    prompt: "Bring this content into our publishing plan.",
    rows: [
      "Choose a connected channel",
      "Review with your team",
      "Schedule the approved post",
    ],
    detail: "See the next step, from first draft to publishing.",
  },
] as const;

/** A finite, controllable explanation—not simulated live account activity. */
export function ProductStory() {
  const [active, setActive] = useState("research");
  const [playing, setPlaying] = useState(false);
  const stage = useRef<HTMLDivElement>(null);
  const keyboard = useRef(false);
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const stop = () => {
      if (preference.matches) {
        setPlaying(false);
        setAnimate(false);
      }
    };
    preference.addEventListener("change", stop);
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          if (!preference.matches) {
            setPlaying(true);
            setAnimate(true);
          }
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      preference.removeEventListener("change", stop);
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const id = window.setTimeout(() => {
      if (document.hidden) {
        setPlaying(false);
        return;
      }
      const index = steps.findIndex((step) => step.id === active);
      if (index === steps.length - 1) {
        setPlaying(false);
        return;
      }
      setAnimate(true);
      setActive(steps[index + 1]!.id);
    }, 3200);
    return () => window.clearTimeout(id);
  }, [active, playing]);

  return (
    <div ref={stage} className={styles.productStage}>
      <div className={styles.stageCaption}>
        <span>A connected workflow</span>
        <span>Illustrative product tour</span>
      </div>
      <Tabs
        value={active}
        onValueChange={(value) => {
          setPlaying(false);
          setAnimate(
            !keyboard.current &&
              !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
          );
          setActive(value);
        }}
        className={styles.productWindow}
      >
        <div className={styles.windowTop}>
          <span className={styles.wordmark}>
            <span className={styles.brandMark}>n</span> Nuxtron
          </span>
          <span>Research → Content → Publishing</span>
          <button
            type="button"
            aria-label={playing ? "Pause product tour" : "Replay product tour"}
            onClick={() => {
              if (playing) setPlaying(false);
              else {
                setActive("research");
                setAnimate(
                  !window.matchMedia("(prefers-reduced-motion: reduce)")
                    .matches,
                );
                setPlaying(true);
              }
            }}
          >
            {playing ? <Pause size={14} /> : <Play size={14} />}
          </button>
        </div>
        <div className={styles.tourBody}>
          <TabsList
            className={styles.tourTabs}
            aria-label="Product workflow"
            data-playing={playing}
            onKeyDown={() => {
              keyboard.current = true;
            }}
            onPointerDown={() => {
              keyboard.current = false;
            }}
          >
            {steps.map((step, i) => (
              <TabsTrigger
                value={step.id}
                key={step.id}
                className={styles.tourTab}
              >
                <step.icon size={17} aria-hidden="true" />
                <span>{step.label}</span>
                <small>0{i + 1}</small>
                <span className={styles.tourTabProgress} aria-hidden="true" />
              </TabsTrigger>
            ))}
          </TabsList>
          <div className={styles.tourPanels} data-animate={animate}>
            {steps.map((step) => (
              <TabsContent
                key={step.id}
                value={step.id}
                className={styles.tourPanel}
              >
                <p className={styles.tourEyebrow}>{step.caption}</p>
                <h2>{step.title}</h2>
                <div className={styles.prompt}>
                  <span className={styles.promptMark} aria-hidden="true">
                    ↗
                  </span>
                  {step.prompt}
                </div>
                <div className={styles.tourChecklist}>
                  {step.rows.map((row, i) => (
                    <div
                      key={row}
                      style={{ ["--row-index"]: i } as CSSProperties}
                    >
                      <span>
                        <Check size={13} aria-hidden="true" />
                      </span>
                      <p>{row}</p>
                      <ArrowRight size={14} aria-hidden="true" />
                    </div>
                  ))}
                </div>
                <p className={styles.tourDetail}>{step.detail}</p>
              </TabsContent>
            ))}
          </div>
        </div>
      </Tabs>
    </div>
  );
}
