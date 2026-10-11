import type { Metadata } from 'next';
import { AuthLayout, type AuthProductCopy } from '@/app/components/auth/auth-layout';
import { LoginForm } from '@/app/components/auth/login-form';
import { PRODUCT_QUERY_PARAM, parseProductLine } from '@/app/lib/product-line';

export const metadata: Metadata = {
  title: 'Log in | Nuxtron',
  description: 'Sign in to your Nuxtron command center.',
  alternates: { canonical: '/login' },
};

const COPY: AuthProductCopy = {
  seo: {
    subheading: 'Sign in to Nuxtron SEO.',
    panelTitle: 'Pick up your search and AI visibility work where you left it.',
    panelPoints: [
      'Site audits, rank tracking and keyword research in one workspace.',
      'See how AI answer engines describe your brand, next to classic search.',
      'Local listings, reviews and traffic reports alongside the rest.',
    ],
  },
  marketing: {
    subheading: 'Sign in to Nuxtron Marketing.',
    panelTitle: 'Pick up your content, social and customer work where you left it.',
    panelPoints: [
      'Draft, review and schedule content from one workspace.',
      'Plan and publish social posts with the studio tools.',
      'Keep campaigns and customer records next to the work they produce.',
    ],
  },
};

type LoginPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LoginPageRoute({ searchParams }: LoginPageProps) {
  const initialProduct = parseProductLine((await searchParams)[PRODUCT_QUERY_PARAM]);
  return (
    <AuthLayout heading="Welcome back" initialProduct={initialProduct} copy={COPY}>
      <LoginForm />
    </AuthLayout>
  );
}
