import type { Metadata } from 'next';
import BlogIndexClient from './BlogIndexClient';

export const metadata: Metadata = {
  title: 'Blog | Nuxtron',
  description: 'Notes on AI visibility, running a connected growth stack, and building supervised autonomous agents.',
  alternates: { canonical: '/blog' },
};

export default function BlogIndexPage() {
  return <BlogIndexClient />;
}