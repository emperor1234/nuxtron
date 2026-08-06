import { buildSparkPath } from '../_data/marketing-data';

type SparklineProps = {
  values: readonly number[];
  color: string;
  width?: number;
  height?: number;
  className?: string;
  /** Unique id used for the gradient fill; defaults to a color-derived key. */
  gradientId?: string;
};

/**
 * Compact trend line + soft area fill. Pure SVG so it renders on the server
 * with zero client JS. Decorative — labelled via the parent metric value.
 */
export default function Sparkline({ values, color, width = 120, height = 34, className, gradientId }: SparklineProps) {
  const { line, area } = buildSparkPath(values, width, height, 4);
  const id = gradientId ?? `spark-${color.replace(/[^a-z0-9]/gi, '')}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={className}
      role="presentation"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
