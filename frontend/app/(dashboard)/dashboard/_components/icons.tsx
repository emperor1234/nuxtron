import type { SVGProps } from 'react';

/**
 * Inline SVG icon set for the Marketing Overview.
 * Single stroke language (1.8–2.2) to match the reference; theming via currentColor.
 */

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base({ size = 20, ...props }: IconProps): IconProps {
  return { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true, ...props };
}

export function StarIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3l2.5 6 6.5.5-5 4.3L17.5 21 12 17l-5.5 4 1.5-7.2-5-4.3 6.5-.5L12 3z" fill="currentColor" />
    </svg>
  );
}

export function TrendUpIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3 17l5-5 4 3 7-8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 7h4v4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ListIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 7h16M4 12h16M4 17h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function LinkIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path
        d="M9 12a3 3 0 013-3h3a3 3 0 010 6h-1.5M15 12a3 3 0 01-3 3H9a3 3 0 010-6h1.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ShareIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="6" cy="12" r="2.4" stroke="currentColor" strokeWidth="2" />
      <circle cx="18" cy="6" r="2.4" stroke="currentColor" strokeWidth="2" />
      <circle cx="18" cy="18" r="2.4" stroke="currentColor" strokeWidth="2" />
      <path d="M8.2 11l7.6-3.6M8.2 13l7.6 3.6" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function SparkleIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15.5 10.2 10.8 5.5 9l4.7-1.3L12 3z" fill="currentColor" />
    </svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3v12M7 10l5 5 5-5M5 21h14" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SlidersIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  );
}

export const KPI_ICONS = {
  authority: StarIcon,
  traffic: TrendUpIcon,
  keywords: ListIcon,
  backlinks: LinkIcon,
  social: ShareIcon,
} as const;
