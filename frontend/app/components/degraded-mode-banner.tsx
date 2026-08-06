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
        border: '1px solid #f59e0b',
        borderRadius: 12,
        padding: '14px 16px',
        color: '#fde68a',
      }}
    >
      {message}
    </div>
  );
}
