'use client';

import type { CSSProperties, HTMLAttributes } from 'react';
import styles from './shine-border.module.css';

type ShineBorderProps = HTMLAttributes<HTMLDivElement> & {
  borderWidth?: number;
  duration?: number;
  shineColor?: string | string[];
};

/** Magic UI shine border, token-aligned. Decorative only. */
export function ShineBorder({
  borderWidth = 1,
  duration = 14,
  shineColor = 'var(--nx-brand)',
  className,
  style,
  ...props
}: ShineBorderProps) {
  const colors = Array.isArray(shineColor) ? shineColor.join(',') : shineColor;
  return (
    <div
      aria-hidden="true"
      className={[styles.shine, className].filter(Boolean).join(' ')}
      style={
        {
          '--border-width': `${borderWidth}px`,
          '--duration': `${duration}s`,
          backgroundImage: `radial-gradient(transparent,transparent, ${colors},transparent,transparent)`,
          ...style,
        } as CSSProperties
      }
      {...props}
    />
  );
}
