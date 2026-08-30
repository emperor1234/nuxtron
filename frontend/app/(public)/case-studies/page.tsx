import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, TrendingUp } from 'lucide-react';
import CaseStudiesClient from './CaseStudiesClient';

export const metadata: Metadata = {
  title: 'Case Studies | Nuxtron',
  description: 'How growth and security teams use Nuxtron to replace disconnected tools with one connected workspace.',
  alternates: { canonical: '/case-studies' },
};

export default function CaseStudiesPage() {
  return <CaseStudiesClient />;
}