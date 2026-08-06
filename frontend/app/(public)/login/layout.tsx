import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Sign in | Nuxtron',
  description: 'Sign in to your Nuxtron command center.',
  // Auth pages must not be indexed.
  robots: { index: false, follow: false },
};

export default function LoginLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
