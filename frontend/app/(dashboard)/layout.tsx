import type { ReactNode } from 'react';
import AutoRecoveryBanner from '@/app/components/auto-recovery-banner';
import ClientAuthGuard from '@/app/components/client-auth-guard';
import DashboardShell from './_shell/dashboard-shell';

// The dashboard is an authenticated, client-data-driven app shell: every page
// fetches on mount and many read the URL via useSearchParams. Static
// prerendering these adds no value and trips the CSR-bailout error, so the
// whole (dashboard) group renders dynamically. Public/marketing SEO pages live
// in the (public) group and remain statically optimized.
export const dynamic = 'force-dynamic';

export default function DashboardLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <ClientAuthGuard>
      <DashboardShell>
        <AutoRecoveryBanner />
        {children}
      </DashboardShell>
    </ClientAuthGuard>
  );
}
