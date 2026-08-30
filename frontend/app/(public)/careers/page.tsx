import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Globe, HeartHandshake, Rocket, Users } from 'lucide-react';
import CareersClient from './CareersClient';

export const metadata: Metadata = {
  title: 'Careers | Nuxtron',
  description: 'Help build the AI-native command center for growth and security teams. See open roles and how we work at Nuxtron.',
  alternates: { canonical: '/careers' },
};

export default function CareersPage() {
  return <CareersClient />;
}