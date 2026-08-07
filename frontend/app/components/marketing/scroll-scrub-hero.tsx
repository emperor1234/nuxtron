'use client';

import { useEffect, useRef } from 'react';

type ScrollScrubHeroProps = {
  src: string;
  poster: string;
  alt: string;
};

const LERP = 0.18; // matches the skill engine's per-frame ease toward target
const SEEK_EPSILON = 0.02;

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Scroll-scrubbed hero clip: scroll position drives video.currentTime directly
 * (scroll down = camera dives forward, scroll up = it reverses) — the video
 * never plays on its own. Follows scroll-world's SKILL.md on the two things
 * that make this actually work smoothly:
 *   - load the clip as a Blob and play from an object URL, so seeking never
 *     depends on the host serving HTTP byte-range requests
 *   - coalesce seeks (never queue a new currentTime while the decoder is
 *     still resolving the last one) so a fast scroll can't pile up and freeze
 * Under prefers-reduced-motion the clip is never fetched at all — just the
 * static poster, no scroll runway, no motion forced on anyone.
 */
export function ScrollScrubHero({ src, poster, alt }: ScrollScrubHeroProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const reducedMotionRef = useRef(false);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    reducedMotionRef.current = reduced;
    if (reduced) return;

    const wrap = wrapRef.current;
    const video = videoRef.current;
    if (!wrap || !video) return;

    let objectUrl: string | null = null;
    let ready = false;
    let cur = 0;
    let target = 0;
    let rafId = 0;
    let cancelled = false;

    fetch(src)
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`${r.status}`))))
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        video.src = objectUrl;
        video.addEventListener(
          'loadedmetadata',
          () => {
            ready = true;
            video.currentTime = 0;
          },
          { once: true }
        );
      })
      .catch(() => {
        // Network hiccup or blocked request: leave the poster showing, no scrub.
      });

    function readProgress(): number {
      const rect = wrap!.getBoundingClientRect();
      const total = wrap!.offsetHeight - window.innerHeight;
      if (total <= 0) return 0;
      return clamp(-rect.top / total);
    }

    function onScroll() {
      target = readProgress();
    }

    function tick() {
      if (ready && video && !video.seeking) {
        cur += (target - cur) * LERP;
        const duration = video.duration || 1;
        const t = clamp(cur) * duration;
        if (Math.abs(video.currentTime - t) > SEEK_EPSILON) {
          try {
            video.currentTime = t;
          } catch {
            // Seeking before the decoder is ready throws in some browsers; safe to ignore.
          }
        }
      }
      rafId = requestAnimationFrame(tick);
    }

    // iOS refuses to paint a seeked frame on a muted video that has never
    // played — prime it (play→immediately pause) on the first user gesture.
    function primeOnFirstGesture() {
      if (!video) return;
      const p = video.play();
      if (p && typeof p.then === 'function') {
        p.then(() => video.pause()).catch(() => {
          // A blocked/interrupted priming play() is harmless — the real
          // scrub-driven seeks below don't depend on this succeeding.
        });
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointerdown', primeOnFirstGesture, { once: true, passive: true });
    window.addEventListener('touchstart', primeOnFirstGesture, { once: true, passive: true });
    onScroll();
    rafId = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pointerdown', primeOnFirstGesture);
      window.removeEventListener('touchstart', primeOnFirstGesture);
      cancelAnimationFrame(rafId);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  return (
    <div ref={wrapRef} className="mk-scrub-wrap">
      <div className="mk-scrub-sticky">
        <div className="mk-hero-video-shell mk-fade-up mx-auto w-full max-w-4xl">
          <video
            ref={videoRef}
            className="mk-hero-video"
            muted
            playsInline
            preload="none"
            poster={poster}
            aria-hidden="true"
          />
          <img src={poster} alt={alt} className="mk-hero-video-poster" />
        </div>
      </div>
    </div>
  );
}
