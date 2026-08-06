import type { Metadata } from 'next';
import MarketingOverview from './_components/marketing-overview';

export const metadata: Metadata = {
  title: 'Marketing Overview · Nuxtron',
  description: 'Organic traffic, keyword rankings, social engagement, conversion funnel, and AI insights at a glance.',
};

export default function DashboardPage() {
  return <MarketingOverview />;
}
