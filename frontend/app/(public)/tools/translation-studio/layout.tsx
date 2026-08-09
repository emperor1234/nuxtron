import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Translation Studio | Nuxtron',
  description:
    'AI-assisted translation workflow with glossaries, translation memory, and document translation, powered by live vendor connections.',
  alternates: { canonical: '/tools/translation-studio' },
};

export default function TranslationStudioLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
