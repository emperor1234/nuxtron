import type { Metadata } from 'next';
import { UNAVAILABLE_QUERY_PARAM } from '@/app/lib/product-line';
import MarketingOverview from './_components/marketing-overview';
import ProductUnavailableNotice from './_components/product-unavailable-notice';

export const metadata: Metadata = {
  title: 'Workspace overview · Nuxtron',
  description: 'Workspace usage, SEO analyses, and module coverage from live APIs.',
};

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // proxy.ts lands here with ?unavailable=<product> when a deep link belonged
  // to the product this session is not signed in to. The notice validates it.
  const params = await searchParams;
  return (
    <>
      <ProductUnavailableNotice requested={params[UNAVAILABLE_QUERY_PARAM]} />
      <MarketingOverview />
    </>
  );
}
