import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Contact | Nuxtron',
  description: 'Questions about plans, a security review, or want to see Nuxtron on your own data? Talk to our team.',
  alternates: { canonical: '/contact' },
};

export default function ContactLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
