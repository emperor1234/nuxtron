'use client';

import { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

interface CounterProps {
  value: string;
  className?: string;
  delay?: number;
  duration?: number;
}

export function Counter({ value, className, delay = 0, duration = 1.2 }: CounterProps) {
  const reduced = useReducedMotion();
  const [count, setCount] = useState(() => (reduced ? parseFloat(value.replace(/[^0-9.]/g, '')) : 0));
  const [isInView, setIsInView] = useState(false);

  const numericValue = parseFloat(value.replace(/[^0-9.]/g, ''));
  const suffix = value.replace(/[0-9.]/g, '');

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3, rootMargin: '0px 0px -50px 0px' }
    );

    const element = document.querySelector(`[data-counter="${value}"]`);
    if (element) observer.observe(element);

    return () => observer.disconnect();
  }, [value]);

  useEffect(() => {
    if (reduced || !isInView) {
      return;
    }

    const startTime = performance.now();
    const startValue = 0;

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / (duration * 1000), 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (numericValue - startValue) * easedProgress;
      setCount(Math.floor(currentValue));

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setCount(numericValue);
      }
    }

    const timeoutId = setTimeout(() => {
      requestAnimationFrame(animate);
    }, delay * 1000);

    return () => clearTimeout(timeoutId);
  }, [isInView, numericValue, duration, delay, reduced]);

  return (
    <span
      data-counter={value}
      className={className}
      aria-hidden="true"
    >
      {count.toLocaleString()}{suffix}
    </span>
  );
}