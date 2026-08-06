'use client';

import { useEffect } from 'react';

/**
 * Catches errors thrown by the root layout itself (the one place a normal
 * error.tsx cannot reach, since it renders inside that same layout). Must
 * render its own <html>/<body> — Next replaces the entire tree here.
 *
 * There was previously no error boundary anywhere in the app: an unhandled
 * throw in any route took down that route to Next's default dev/prod error
 * screen with no recovery path and no server-side record of what happened.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // TODO: replace with a real error tracker (e.g. Sentry) once a DSN is
    // provisioned — see backend fallback payload's `sentry_enabled: false`.
    // eslint-disable-next-line no-console
    console.error('[global-error]', error.digest ?? error.message);
  }, [error]);

  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', padding: '4rem 1.5rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Something went wrong</h1>
        <p style={{ color: '#666', marginBottom: '1.5rem' }}>
          We hit an unexpected error loading the app. Try again, or reload the page.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          style={{
            padding: '0.6rem 1.4rem',
            borderRadius: 8,
            border: '1px solid #ccc',
            background: '#111',
            color: '#fff',
            cursor: 'pointer',
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
