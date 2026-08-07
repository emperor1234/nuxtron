import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Reset password | Nuxtron',
  description: 'Reset the password for your Nuxtron account.',
  // Auth pages must not be indexed.
  robots: { index: false, follow: false },
};

export default function ResetPasswordLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
