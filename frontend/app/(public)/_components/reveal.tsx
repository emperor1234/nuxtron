"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

/** Content is visible without JS. Animate once only when a section enters view. */
export function Reveal({
  children,
  delay = 0,
  className,
  style,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (
      !element ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    let animation: ReturnType<HTMLElement["animate"]> | undefined;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const stop = () => {
      if (preference.matches) animation?.cancel();
    };
    preference.addEventListener("change", stop);
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return;
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
          animation = element.animate(
            [
              { opacity: 0, transform: "translateY(12px)" },
              { opacity: 1, transform: "translateY(0)" },
            ],
            {
              duration: 550,
              delay: Math.min(delay, 0.2) * 1000,
              easing: "cubic-bezier(0.23, 1, 0.32, 1)",
              fill: "backwards",
            },
          );
        }
        observer.disconnect();
      },
      { threshold: 0.08 },
    );
    observer.observe(element);
    return () => {
      observer.disconnect();
      animation?.cancel();
      preference.removeEventListener("change", stop);
    };
  }, [delay]);
  const cleanClass = className?.replace(
    /\b(?:mk-fade-up|animate-slide-in-left|animate-slide-in-right|animate-scale-in|stagger-children)\b/g,
    "",
  );
  return (
    <div ref={ref} className={cleanClass} style={style}>
      {children}
    </div>
  );
}
