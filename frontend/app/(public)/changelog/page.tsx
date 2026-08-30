import type { Metadata } from 'next';
import ChangelogClient from './ChangelogClient';

export const metadata: Metadata = {
  title: 'Changelog | Nuxtron',
  description: 'What shipped recently in Nuxtron — new features, improvements, and fixes across CRM, SEO, social, and security.',
  alternates: { canonical: '/changelog' },
};

export default function ChangelogPage() {
  return <ChangelogClient />;
}