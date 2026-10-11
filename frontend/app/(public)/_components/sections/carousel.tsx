"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  Children,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import styles from "./carousel.module.css";

/** Slide widths per breakpoint, as CSS lengths relative to the track. */
export type CarouselSlideWidth = {
  /** Below 720px. Defaults to 85% so the next slide peeks in. */
  base?: string;
  /** 720px and up. Defaults to two slides per view. */
  md?: string;
  /** 1080px and up. Defaults to three slides per view. */
  lg?: string;
};

export type CarouselProps = {
  /** Accessible name of the carousel region, e.g. "Customer stories". */
  label: string;
  /** One child per slide. */
  children: ReactNode;
  slideWidth?: CarouselSlideWidth;
  className?: string;
};

type VisibleRange = { first: number; last: number };

/** Pixel tolerance for sub-pixel layout when comparing scroll positions. */
const EDGE_TOLERANCE = 2;

/**
 * Accessible, swipeable carousel built on CSS scroll-snap.
 *
 * Native scrolling handles touch, trackpad and drag momentum; the buttons and
 * arrow keys only move the scroll position by one slide. It never advances
 * on its own.
 */
export function Carousel({ label, children, slideWidth, className }: CarouselProps) {
  const slides = Children.toArray(children);
  const count = slides.length;
  const trackId = useId();
  const trackRef = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<VisibleRange>({ first: 0, last: 0 });
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(count <= 1);

  const measure = useCallback(() => {
    const track = trackRef.current;
    if (!track) return;
    const { scrollLeft, clientWidth, scrollWidth } = track;
    setAtStart(scrollLeft <= EDGE_TOLERANCE);
    setAtEnd(scrollLeft + clientWidth >= scrollWidth - EDGE_TOLERANCE);
    setRange(visibleRange(slideElements(track), scrollLeft, clientWidth));
  }, []);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    let frame = 0;
    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    measure();
    track.addEventListener("scroll", schedule, { passive: true });
    const resizeObserver = new ResizeObserver(schedule);
    resizeObserver.observe(track);
    return () => {
      cancelAnimationFrame(frame);
      track.removeEventListener("scroll", schedule);
      resizeObserver.disconnect();
    };
  }, [measure, count]);

  const scrollToSlide = useCallback((index: number) => {
    const track = trackRef.current;
    if (!track) return;
    const items = slideElements(track);
    const target = items[Math.max(0, Math.min(index, items.length - 1))];
    if (!target) return;
    const padding = Number.parseFloat(window.getComputedStyle(track).scrollPaddingLeft) || 0;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    track.scrollTo({
      left: target.offsetLeft - padding,
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }, []);

  const showPrevious = () => scrollToSlide(range.first - 1);
  const showNext = () => scrollToSlide(range.first + 1);

  const onTrackKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget) return;
    const moves: Record<string, () => void> = {
      ArrowLeft: showPrevious,
      ArrowRight: showNext,
      Home: () => scrollToSlide(0),
      End: () => scrollToSlide(count - 1),
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    move();
  };

  const widthVars = {
    ...(slideWidth?.base ? { "--carousel-slide-base": slideWidth.base } : {}),
    ...(slideWidth?.md ? { "--carousel-slide-md": slideWidth.md } : {}),
    ...(slideWidth?.lg ? { "--carousel-slide-lg": slideWidth.lg } : {}),
  } as CSSProperties;

  const first = range.first + 1;
  const last = Math.max(range.last, range.first) + 1;
  const visibleText = first === last ? `${first}` : `${first}–${last}`;
  const spokenText =
    first === last
      ? `Showing slide ${first} of ${count}`
      : `Showing slides ${first} to ${last} of ${count}`;

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label={label}
      className={[styles.carousel, className].filter(Boolean).join(" ")}
      style={widthVars}
    >
      <div
        ref={trackRef}
        id={trackId}
        className={styles.track}
        tabIndex={0}
        onKeyDown={onTrackKeyDown}
      >
        {slides.map((slide, index) => (
          <div
            key={index}
            role="group"
            aria-roledescription="slide"
            aria-label={`${index + 1} of ${count}`}
            className={styles.slide}
            data-carousel-slide=""
          >
            {slide}
          </div>
        ))}
      </div>

      {count > 1 ? (
        // When every slide already fits there is nothing to page through:
        // hide the controls (visibility keeps the layout stable and removes
        // them from the tab order and accessibility tree).
        <div className={styles.controls} data-fits={atStart && atEnd ? "true" : undefined}>
          <p className={styles.status} aria-live="polite" aria-atomic="true">
            <span aria-hidden="true">
              <strong>{visibleText}</strong> / {count}
            </span>
            <span className="sr-only">{spokenText}</span>
          </p>
          <div className={styles.buttons}>
            <button
              type="button"
              className={styles.button}
              aria-controls={trackId}
              aria-label="Previous slide"
              disabled={atStart}
              onClick={showPrevious}
            >
              <ChevronLeft size={18} strokeWidth={1.8} aria-hidden="true" />
            </button>
            <button
              type="button"
              className={styles.button}
              aria-controls={trackId}
              aria-label="Next slide"
              disabled={atEnd}
              onClick={showNext}
            >
              <ChevronRight size={18} strokeWidth={1.8} aria-hidden="true" />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function slideElements(track: HTMLElement): HTMLElement[] {
  return Array.from(track.querySelectorAll<HTMLElement>(":scope > [data-carousel-slide]"));
}

/**
 * First and last slides fully inside the viewport. When no slide fits fully
 * (a slide wider than the track), falls back to the slide nearest the start.
 */
function visibleRange(
  items: readonly HTMLElement[],
  scrollLeft: number,
  clientWidth: number,
): VisibleRange {
  const viewEnd = scrollLeft + clientWidth;
  const fullyVisible = items.flatMap((item, index) => {
    const start = item.offsetLeft;
    const end = start + item.offsetWidth;
    return start >= scrollLeft - EDGE_TOLERANCE && end <= viewEnd + EDGE_TOLERANCE
      ? [index]
      : [];
  });
  if (fullyVisible.length > 0) {
    return { first: fullyVisible[0], last: fullyVisible[fullyVisible.length - 1] };
  }
  const nearest = items.reduce(
    (best, item, index) =>
      Math.abs(item.offsetLeft - scrollLeft) < Math.abs((items[best]?.offsetLeft ?? 0) - scrollLeft)
        ? index
        : best,
    0,
  );
  return { first: nearest, last: nearest };
}
