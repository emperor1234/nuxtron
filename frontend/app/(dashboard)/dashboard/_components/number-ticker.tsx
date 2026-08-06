'use client';

import { useEffect, useRef } from 'react';
import { animate, useInView, useReducedMotion } from 'framer-motion';

type NumberTickerProps = {
  value: number;
  /** Text shown before the number (e.g. "$"). */
  prefix?: string;
  /** Text shown after the number (e.g. "K", "M"). */
  suffix?: string;
  decimals?: number;
  durationMs?: number;
  className?: string;
};

/**
 * MagicUI-style count-up. Animates from 0 → value the first time it
 * scrolls into view, then holds. Falls back to the final value instantly
 * when the user prefers reduced motion. Uses tabular figures upstream to
 * avoid layout shift while digits change.
 */
export default function NumberTicker({
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  durationMs = 1100,
  className,
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '0px 0px -10% 0px' });
  const prefersReducedMotion = useReducedMotion();

  const format = (n: number) =>
    `${prefix}${n.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}${suffix}`;

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (prefersReducedMotion) {
      node.textContent = format(value);
      return;
    }
    if (!inView) return;

    const controls = animate(0, value, {
      duration: durationMs / 1000,
      ease: [0.22, 1, 0.36, 1],
      onUpdate(latest) {
        node.textContent = format(latest);
      },
    });

    return () => controls.stop();
    // format derives only from stable props; intentionally minimal deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, prefersReducedMotion, value, decimals, prefix, suffix, durationMs]);

  // Render a deterministic starting value (server + first client paint) so
  // hydration always matches; the effect drives the animation or final value.
  return (
    <span ref={ref} className={className}>
      {format(0)}
    </span>
  );
}
