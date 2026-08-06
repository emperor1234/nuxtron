import type { ReactNode } from 'react';
import { Plus_Jakarta_Sans, Space_Grotesk } from 'next/font/google';
import AutoRecoveryBanner from '@/app/components/auto-recovery-banner';
import ClientAuthGuard from '@/app/components/client-auth-guard';
import DashboardShell from './_shell/dashboard-shell';

// The dashboard is an authenticated, client-data-driven app shell: every page
// fetches on mount and many read the URL via useSearchParams. Static
// prerendering these adds no value and trips the CSR-bailout error, so the
// whole (dashboard) group renders dynamically. Public/marketing SEO pages live
// in the (public) group and remain statically optimized.
export const dynamic = 'force-dynamic';

// Reference typography, applied to the whole dashboard via CSS variables.
const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-jakarta',
  display: 'swap',
});

const grotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-grotesk',
  display: 'swap',
});

export default function DashboardLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <ClientAuthGuard>
      <DashboardShell fontClassName={`${jakarta.variable} ${grotesk.variable}`}>
        <AutoRecoveryBanner />
        {children}
      </DashboardShell>
    </ClientAuthGuard>
  );
}
