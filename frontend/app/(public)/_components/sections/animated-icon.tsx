"use client";

import { useEffect, useRef, type ComponentRef, type ReactNode } from "react";
import type { SectionIcon } from "../../_content/types";
import { SectionIconGlyph } from "./icon";
import styles from "./animated-icon.module.css";

// One observer for every icon on the page instead of one each.
let sharedObserver: IntersectionObserver | null = null;

function observe(element: HTMLElement): () => void {
  if (typeof IntersectionObserver === "undefined") {
    element.dataset.in = "true";
    return () => undefined;
  }
  sharedObserver ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        (entry.target as HTMLElement).dataset.in = "true";
        sharedObserver?.unobserve(entry.target);
      }
    },
    { threshold: 0.6 },
  );
  // Hidden only once JS is watching it, so no-JS visitors always see icons.
  element.dataset.in = "false";
  sharedObserver.observe(element);
  return () => sharedObserver?.unobserve(element);
}

/**
 * Icon tile that settles in once when it scrolls into view (the tile scales
 * up, the glyph turns into place, a cyan ring pings outward once) and
 * responds when its card is hovered. Mark the hovering card with
 * `data-icon-host`. Renders complete without JS or with reduced motion.
 */
export function AnimatedIcon({
  name,
  glyph,
  tone = "soft",
  size = 20,
}: {
  name?: SectionIcon;
  /** A custom glyph, when the icon is not a content-model name. */
  glyph?: ReactNode;
  tone?: "soft" | "solid";
  size?: number;
}) {
  const ref = useRef<ComponentRef<"span">>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    return observe(element);
  }, []);

  return (
    <span ref={ref} className={styles.tile} data-tone={tone} aria-hidden="true">
      <span className={styles.glyph}>{glyph ?? (name ? <SectionIconGlyph name={name} size={size} /> : null)}</span>
    </span>
  );
}
