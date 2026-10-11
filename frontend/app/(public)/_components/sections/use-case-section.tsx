"use client";

import { useCallback, useEffect, useReducer, useRef, type CSSProperties } from "react";
import { Check, Pause, Play, RotateCcw } from "lucide-react";
// Radix primitives directly: the shared ui/tabs wrapper bakes in pill-tab
// utilities (h-9, justify-center, bg-muted) that fight this layout.
import * as Tabs from "@radix-ui/react-tabs";
import type { UseCaseContent, UseCaseStep } from "../../_content/types";
import { SectionIconGlyph } from "./icon";
import {
  USE_CASE_STEP_MS,
  initialTourState,
  parseAnswerItems,
  parseBarItem,
  tourControl,
  tourReducer,
} from "./use-case-tour";
import styles from "./use-case-section.module.css";

const TITLE_ID = "use-cases-title";

function prefersReducedMotion(): boolean {
  return globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/**
 * Animated use-case walkthrough. Once it scrolls into view it plays through
 * the steps a single time, showing a progress track on the active tab so the
 * viewer can see the timer. It is pausable, stops for good on any manual tab
 * change, pauses while the page is hidden, and never autoplays under reduced
 * motion. Transition logic lives in use-case-tour.ts and is unit-tested.
 */
export function UseCaseSection({ content }: { content: UseCaseContent }) {
  const count = content.steps.length;
  const [state, dispatch] = useReducer(tourReducer, initialTourState);
  const root = useRef<HTMLElement>(null);
  // Time left on the current step, so a pause resumes where it left off.
  const remaining = useRef(USE_CASE_STEP_MS);
  const startedAt = useRef(0);
  const keyboard = useRef(false);

  // Start once, when the section is properly in view.
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return;
        dispatch(prefersReducedMotion() ? { type: "stop" } : { type: "start", count });
        observer.disconnect();
      },
      { threshold: 0.35 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [count]);

  // A fresh step or a replay restarts the countdown.
  useEffect(() => {
    remaining.current = USE_CASE_STEP_MS;
  }, [state.index, state.run]);

  // Countdown while playing; bank the elapsed time when it stops.
  useEffect(() => {
    if (state.status !== "playing") return;
    startedAt.current = performance.now();
    const timer = window.setTimeout(() => dispatch({ type: "tick", count }), remaining.current);
    return () => {
      window.clearTimeout(timer);
      remaining.current = Math.max(0, remaining.current - (performance.now() - startedAt.current));
    };
  }, [state.status, state.index, state.run, count]);

  // Nobody watches a hidden tab; pause rather than skip steps unseen.
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) dispatch({ type: "pause" });
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  // Turning on reduced motion mid-tour ends the autoplay.
  useEffect(() => {
    const query = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) return;
    const onChange = () => {
      if (query.matches) dispatch({ type: "stop" });
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const onSelect = useCallback(
    (value: string) => {
      const index = content.steps.findIndex((step) => step.id === value);
      if (index < 0) return;
      // Keyboard users moving through tabs should not get a replayed entrance
      // on every arrow press.
      dispatch({ type: "select", index, animate: !keyboard.current && !prefersReducedMotion() });
    },
    [content.steps],
  );

  const control = tourControl(state.status);
  const onControl = () => {
    if (control === "pause") dispatch({ type: "pause" });
    else if (control === "resume") dispatch({ type: "resume" });
    else dispatch({ type: "replay", count });
  };
  const controlLabel = {
    play: "Play walkthrough",
    pause: "Pause walkthrough",
    resume: "Resume walkthrough",
    replay: "Replay walkthrough",
  }[control];
  const ControlIcon = control === "pause" ? Pause : control === "replay" ? RotateCcw : Play;
  const active = content.steps[state.index] ?? content.steps[0];

  if (!active) return null;

  return (
    <section ref={root} className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <header className={styles.header}>
          <p className={styles.eyebrow}>{content.eyebrow}</p>
          <h2 id={TITLE_ID} className={styles.title}>
            {content.title}
          </h2>
          <p className={styles.intro}>{content.intro}</p>
        </header>

        <Tabs.Root
          value={active.id}
          onValueChange={onSelect}
          className={styles.tour}
          style={{ "--step-ms": `${USE_CASE_STEP_MS}ms` } as CSSProperties}
        >
          <div className={styles.rail}>
            <Tabs.List
              className={styles.tabs}
              aria-label={content.title}
              data-status={state.status}
              onKeyDown={() => {
                keyboard.current = true;
              }}
              onPointerDown={() => {
                keyboard.current = false;
              }}
            >
              {content.steps.map((step, index) => (
                <Tabs.Trigger key={step.id} value={step.id} className={styles.tab}>
                  <SectionIconGlyph name={step.icon} size={18} className={styles.tabIcon} />
                  <span className={styles.tabLabel}>{step.label}</span>
                  <span className={styles.tabIndex} aria-hidden="true">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {/* Keyed by run so a replay restarts the CSS countdown. */}
                  <span key={state.run} className={styles.progress} aria-hidden="true" />
                </Tabs.Trigger>
              ))}
            </Tabs.List>
            <button type="button" className={styles.control} onClick={onControl}>
              <ControlIcon size={15} aria-hidden="true" />
              {controlLabel}
            </button>
          </div>

          <div className={styles.panels} data-animate={state.animate}>
            {content.steps.map((step) => (
              <Tabs.Content key={step.id} value={step.id} className={styles.panel}>
                <StepPanel key={`${step.id}:${state.run}`} step={step} />
              </Tabs.Content>
            ))}
          </div>
        </Tabs.Root>
      </div>
    </section>
  );
}

function StepPanel({ step }: { step: UseCaseStep }) {
  return (
    <div className={styles.stage}>
      <div className={styles.copy}>
        <p className={`${styles.stepEyebrow} ${styles.seq}`} style={seq(0)}>
          {step.label}
        </p>
        <h3 className={`${styles.stepTitle} ${styles.seq}`} style={seq(1)}>
          {step.title}
        </h3>
        <p className={`${styles.stepBody} ${styles.seq}`} style={seq(2)}>
          {step.body}
        </p>
      </div>
      <figure className={`${styles.surface} ${styles.seq}`} style={seq(3)}>
        <figcaption className={styles.caption}>{step.panel.caption}</figcaption>
        {step.panel.kind === "bars" ? (
          <BarsPanel items={step.panel.items} />
        ) : step.panel.kind === "answer" ? (
          <AnswerPanel items={step.panel.items} />
        ) : (
          <RowsPanel items={step.panel.items} />
        )}
      </figure>
    </div>
  );
}

/** Sequencing slot for the panel entrance; delays are set in CSS from --seq. */
function seq(index: number): CSSProperties {
  return { "--seq": index } as CSSProperties;
}

function RowsPanel({ items }: { items: readonly string[] }) {
  return (
    <ul className={styles.rows}>
      {items.map((item, index) => (
        <li key={`${index}:${item}`} className={styles.row} style={{ "--i": index } as CSSProperties}>
          <span className={styles.rowCheck} aria-hidden="true">
            <Check size={12} />
          </span>
          {item}
        </li>
      ))}
    </ul>
  );
}

function BarsPanel({ items }: { items: readonly string[] }) {
  const bars = items.map(parseBarItem).filter((bar) => bar !== null);
  return (
    <ul className={styles.bars}>
      {bars.map((bar, index) => (
        <li key={`${index}:${bar.label}`} className={styles.barItem}>
          <span className={styles.barTrack} aria-hidden="true">
            <span
              className={styles.barFill}
              style={{ "--value": bar.value / 100, "--i": index } as CSSProperties}
            />
          </span>
          <span className={styles.barLabel}>{bar.label}</span>
          <span className={styles.barValue}>{bar.value}</span>
        </li>
      ))}
    </ul>
  );
}

function AnswerPanel({ items }: { items: readonly string[] }) {
  const { question, lines } = parseAnswerItems(items);
  return (
    <div className={styles.answer}>
      <p className={styles.question}>{question}</p>
      <ul className={styles.answerLines}>
        {lines.map((line, index) => (
          <li
            key={`${index}:${line.text}`}
            className={styles.answerLine}
            style={{ "--i": index } as CSSProperties}
          >
            {line.text}
            {line.source ? <span className={styles.citation}>{line.source}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
