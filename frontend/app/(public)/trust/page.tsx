import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Database, KeyRound, Lock, ScrollText, ShieldCheck, Users } from 'lucide-react';
import TrustClient from './TrustClient';

export const metadata: Metadata = {
  title: 'Trust & Security | Nuxtron',
  description: 'How Nuxtron protects tenant data: encryption, tenant isolation, role-based access control, and audit logging.',
  alternates: { canonical: '/trust' },
};

export default function TrustPage() {
  return <TrustClient />;
}