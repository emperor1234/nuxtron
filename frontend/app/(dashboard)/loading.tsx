/**
 * Route-group loading UI, shown during the RSC navigation transition into
 * any dashboard page (all of which are `force-dynamic` and fetch on
 * mount — see app/(dashboard)/layout.tsx). Previously there was no loading
 * boundary anywhere, so navigation showed a blank page until the next
 * page's own client code mounted and started fetching.
 */
export default function DashboardLoading() {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        padding: '1.5rem',
      }}
    >
      {[220, 160, 280, 140].map((width, index) => (
        <div
          key={index}
          style={{
            height: index === 0 ? 32 : 16,
            width,
            maxWidth: '100%',
            borderRadius: 6,
            background: 'var(--nx-border, #e5e7eb)',
            opacity: 0.6,
            animation: 'nx-skeleton-pulse 1.4s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`
        @keyframes nx-skeleton-pulse {
          0%, 100% { opacity: 0.35; }
          50% { opacity: 0.7; }
        }
        @media (prefers-reduced-motion: reduce) {
          [aria-busy="true"] div { animation: none !important; }
        }
      `}</style>
    </div>
  );
}
