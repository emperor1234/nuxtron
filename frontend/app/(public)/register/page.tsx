import type { Metadata } from 'next';
import { AuthLayout, type AuthProductCopy } from '@/app/components/auth/auth-layout';
import { SignupForm } from '@/app/components/auth/signup-form';
import { PRODUCT_QUERY_PARAM, parseProductLine } from '@/app/lib/product-line';

export const metadata: Metadata = {
  title: 'Create your account | Nuxtron',
  description: 'Start your Nuxtron command center — CRM, SEO, social, and security in one place.',
  alternates: { canonical: '/register' },
};

const COPY: AuthProductCopy = {
  seo: {
    subheading: 'Set up your Nuxtron SEO workspace in a couple of minutes.',
    panelTitle: 'Search and AI answer-engine visibility, in one workspace.',
    panelPoints: [
      'Set up your profile and invite your team.',
      'Cancel anytime; your plan is a separate step after signup.',
      'Audits, rankings and AI visibility reports in one place.',
    ],
  },
  marketing: {
    subheading: 'Set up your Nuxtron Marketing workspace in a couple of minutes.',
    panelTitle: 'Content, social and customer work, in one workspace.',
    panelPoints: [
      'Set up your profile and invite your team.',
      'Cancel anytime; your plan is a separate step after signup.',
      'Keep content, social and customer work together.',
    ],
  },
};

type RegisterPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function RegisterPageRoute({ searchParams }: RegisterPageProps) {
  const initialProduct = parseProductLine((await searchParams)[PRODUCT_QUERY_PARAM]);
  return (
    <AuthLayout heading="Create your account" initialProduct={initialProduct} copy={COPY}>
      <SignupForm />
    </AuthLayout>
  );
}
