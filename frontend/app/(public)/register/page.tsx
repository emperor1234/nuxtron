import type { Metadata } from 'next';
import { AuthLayout } from '@/app/components/auth/auth-layout';
import { SignupForm } from '@/app/components/auth/signup-form';

export const metadata: Metadata = {
  title: 'Create your account | Nuxtron',
  description: 'Start your Nuxtron command center — CRM, SEO, social, and security in one place.',
  alternates: { canonical: '/register' },
};

const PANEL_POINTS = [
  'Invite your team once you are in — no seat limits to start.',
  'Cancel anytime; your plan is a separate step after signup.',
  'Elevated workspace access is granted by your admin, not by signup order.',
] as const;

export default function RegisterPageRoute() {
  return (
    <AuthLayout
      heading="Create your account"
      subheading="Set up your Nuxtron workspace in a couple of minutes."
      panelTitle="Everything your team needs to grow, secure, and scale — in one workspace."
      panelPoints={PANEL_POINTS}
    >
      <SignupForm />
    </AuthLayout>
  );
}
