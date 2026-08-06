'use client';

import { useEffect } from 'react';

/** Root-level error boundary — catches anything not caught by a nested
 * (dashboard)/error.tsx or (public)/error.tsx, so no route is ever left
 * fully unguarded. */
export default function RootError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('[app-error]', error.digest ?? error.message);
  }, [error]);

  return (
    <div style={{ padding: '4rem 1.5rem', textAlign: 'center', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Something went wrong</h1>
      <p style={{ color: '#666', marginBottom: '1.5rem' }}>This page hit an unexpected error.</p>
      <button
        type="button"
        onClick={() => reset()}
        style={{ padding: '0.6rem 1.4rem', borderRadius: 8, border: '1px solid #ccc', cursor: 'pointer' }}
      >
        Try again
      </button>
    </div>
  );
}
