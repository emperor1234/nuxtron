'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { STORAGE_TOKEN_KEY } from '@/app/lib/api-client';

/**
 * Gates every dashboard route on a client session token (A01: Broken Access
 * Control). Without a token the user is redirected to `/login` and no
 * protected UI is rendered — closing the previous pass-through hole.
 *
 * Enforcement is on by default. Set `NEXT_PUBLIC_DISABLE_AUTH_GUARD=true` to
 * bypass it for local development only; it must never be set in production.
 */
const AUTH_DISABLED = process.env.NEXT_PUBLIC_DISABLE_AUTH_GUARD === 'true';

export default function ClientAuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(AUTH_DISABLED);

  useEffect(() => {
    if (AUTH_DISABLED) return;
    const token = globalThis.localStorage?.getItem(STORAGE_TOKEN_KEY)?.trim();
    if (token) {
      // Reading the session token is a one-time mount check against an external
      // store (localStorage), not derivable render state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthorized(true);
    } else {
      router.replace('/login');
    }
  }, [router]);

  // Render nothing until a session is confirmed to avoid flashing protected
  // content to unauthenticated visitors.
  if (!authorized) return null;

  return <>{children}</>;
}
