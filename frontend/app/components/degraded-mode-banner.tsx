type DegradedModeBannerProps = {
  message: string;
  marginTop?: number;
};

export default function DegradedModeBanner({ message, marginTop = 0 }: DegradedModeBannerProps) {
  return (
    <div
      style={{
        marginTop,
        background: 'var(--bg-soft)',
        border: '1px solid var(--warning-line)',
        borderRadius: 12,
        padding: '14px 16px',
        color: 'var(--warning-ink)',
      }}
    >
      {message}
    </div>
  );
}
