import type { Metadata } from 'next';
import MarketingOverview from './_components/marketing-overview';

export const metadata: Metadata = {
  title: 'Marketing Overview · Nuxtron',
  description: 'Workspace usage, SEO analyses, and module coverage from live APIs.',
};

export default function DashboardPage() {
  return <MarketingOverview />;
}
