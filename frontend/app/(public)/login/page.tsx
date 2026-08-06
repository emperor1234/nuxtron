import type { Metadata } from 'next';
import { AuthLayout } from '@/app/components/auth/auth-layout';
import { LoginForm } from '@/app/components/auth/login-form';

export const metadata: Metadata = {
  title: 'Log in | Nuxtron',
  description: 'Sign in to your Nuxtron command center.',
  alternates: { canonical: '/login' },
};

const PANEL_POINTS = [
  'One login for CRM, SEO, social, and security operations.',
  'Real-time visibility across every connected channel.',
  'AI agents that act on your behalf, with a full audit trail.',
] as const;

export default function LoginPageRoute() {
  return (
    <AuthLayout
      heading="Welcome back"
      subheading="Sign in to your command center."
      panelTitle="Run every growth and security workflow from one place."
      panelPoints={PANEL_POINTS}
    >
      <LoginForm />
    </AuthLayout>
  );
}
