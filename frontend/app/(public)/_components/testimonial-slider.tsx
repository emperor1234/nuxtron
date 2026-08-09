'use client';

import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Star } from 'lucide-react';

export type Testimonial = {
  quote: string;
  name: string;
  role: string;
  company: string;
  initials: string;
};

export function TestimonialSlider({ testimonials }: { testimonials: Testimonial[] }) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const reduced = useReducedMotion();
  const current = testimonials[index];
  const multiple = testimonials.length > 1;

  function go(next: number) {
    setDirection(next > index ? 1 : -1);
    setIndex((next + testimonials.length) % testimonials.length);
  }

  return (
    <div className="relative mx-auto max-w-3xl text-center">
      <div className="relative min-h-[220px] overflow-hidden">
        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={index}
            custom={direction}
            initial={reduced ? undefined : { opacity: 0, x: direction * 24 }}
            animate={reduced ? undefined : { opacity: 1, x: 0 }}
            exit={reduced ? undefined : { opacity: 0, x: direction * -24 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="mb-6 flex justify-center gap-1 text-[#f83d69]" aria-hidden="true">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} size={22} fill="currentColor" />
              ))}
            </div>
            <p className="text-2xl font-semibold leading-tight text-white sm:text-4xl [font-family:var(--font-geist-sans)]">
              &ldquo;{current.quote}&rdquo;
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-full bg-white text-[#181818]">
                <span className="text-sm font-bold">{current.initials}</span>
              </div>
              <div className="text-left">
                <div className="text-sm font-bold text-white">{current.role}</div>
                <div className="text-sm font-medium text-white/60">{current.company}</div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {multiple ? (
        <div className="mt-10 flex items-center justify-center gap-6">
          <button
            type="button"
            onClick={() => go(index - 1)}
            aria-label="Previous review"
            className="grid h-10 w-10 place-items-center rounded-full border border-white/15 text-white transition-colors hover:bg-white/10"
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
          <div className="flex items-center gap-2">
            {testimonials.map((t, i) => (
              <button
                key={t.name + i}
                type="button"
                onClick={() => go(i)}
                aria-label={`Show review ${i + 1}`}
                aria-current={i === index}
                className={`h-2 rounded-full transition-all ${i === index ? 'w-6 bg-white' : 'w-2 bg-white/30 hover:bg-white/50'}`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => go(index + 1)}
            aria-label="Next review"
            className="grid h-10 w-10 place-items-center rounded-full border border-white/15 text-white transition-colors hover:bg-white/10"
          >
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </div>
  );
}
