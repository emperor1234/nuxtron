'use client';

import { useEffect } from 'react';

/**
 * Route-group error boundary for every authenticated page. Renders inside
 * DashboardShell (app/(dashboard)/layout.tsx), so the nav stays usable and a
 * failure in one page never takes the rest of the dashboard down with it —
 * previously there was no boundary here at all, so any thrown error crashed
 * to Next's default screen for every user hitting that route.
 */
export default function DashboardError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('[dashboard-error]', error.digest ?? error.message);
  }, [error]);

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        padding: '4rem 1.5rem',
        textAlign: 'center',
        minHeight: '40vh',
      }}
    >
      <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>This page couldn't load</h2>
      <p style={{ color: 'var(--nx-muted, #666)', maxWidth: '32rem' }}>
        Something went wrong loading this section. The rest of the dashboard is unaffected — try again, or pick
        another page from the sidebar.
      </p>
      <button
        type="button"
        onClick={() => reset()}
        style={{
          padding: '0.6rem 1.4rem',
          borderRadius: 8,
          border: '1px solid var(--nx-border, #ccc)',
          cursor: 'pointer',
        }}
      >
        Try again
      </button>
    </div>
  );
}
