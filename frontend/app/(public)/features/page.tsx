import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Layers,
  MessageSquareText,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Star,
  Users,
} from 'lucide-react';
import { Reveal } from '../_components/reveal';
import { Counter } from '../_components/counter';
import FeaturesClient from './FeaturesClient';

export const metadata: Metadata = {
  title: 'Features | Nuxtron',
  description: 'Everything inside the Nuxtron workspace: CRM, SEO & AI visibility, social operations, reviews, security, and autonomous AI agents.',
  alternates: { canonical: '/features' },
};

export default function FeaturesPage() {
  return <FeaturesClient />;
}