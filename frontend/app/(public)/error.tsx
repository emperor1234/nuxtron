'use client';

import { useEffect } from 'react';

/** Route-group error boundary for marketing/public pages. */
export default function PublicError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('[public-error]', error.digest ?? error.message);
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
        padding: '6rem 1.5rem',
        textAlign: 'center',
        minHeight: '50vh',
      }}
    >
      <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>This page couldn't load</h2>
      <p style={{ color: '#666', maxWidth: '32rem' }}>Something went wrong. Try again, or head back home.</p>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          type="button"
          onClick={() => reset()}
          style={{ padding: '0.6rem 1.4rem', borderRadius: 8, border: '1px solid #ccc', cursor: 'pointer' }}
        >
          Try again
        </button>
        <a
          href="/"
          style={{
            padding: '0.6rem 1.4rem',
            borderRadius: 8,
            border: '1px solid #ccc',
            textDecoration: 'none',
            color: 'inherit',
          }}
        >
          Go home
        </a>
      </div>
    </div>
  );
}
