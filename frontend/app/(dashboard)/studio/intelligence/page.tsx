/**
 * God Intelligence — Next.js Page Wrapper
 * Location: frontend/app/studio/intelligence/page.tsx
 */

import { Suspense } from 'react';
import IntelligenceDashboard from '@/components/intelligence/IntelligenceDashboard';

export const metadata = {
  title: 'God Intelligence | Studio',
  description: 'Competitive intelligence & content optimization platform',
};

function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="h-20 w-full animate-pulse rounded-xl bg-slate-200" />
      <div className="h-80 w-full animate-pulse rounded-xl bg-slate-200" />
      <div className="h-96 w-full animate-pulse rounded-xl bg-slate-200" />
    </div>
  );
}

export default function IntelligencePage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <IntelligenceDashboard />
    </Suspense>
  );
}
