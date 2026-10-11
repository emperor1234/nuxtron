type CounterProps = { value: string; className?: string; delay?: number; duration?: number };

/** Display the complete value immediately; decorative counting hid meaningful text. */
export function Counter({ value, className }: CounterProps) {
  return <span className={className} style={{ fontVariantNumeric: 'tabular-nums' }}>{value}</span>;
}
