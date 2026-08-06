import type { ReactNode } from 'react';
import { MarketingHeader } from '@/app/components/marketing/marketing-header';
import { MarketingFooter } from '@/app/components/marketing/marketing-footer';
import './marketing.css';

const AUTH_ROUTES = ['/login', '/register', '/reset-password'];

export default function PublicLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="mk-root">
      <a className="mk-skip" href="#main-content">
        Skip to content
      </a>
      <div className="mk-bg" aria-hidden="true">
        <div className="mk-bg-glow" />
      </div>
      <MarketingHeader />
      <main id="main-content" className="mk-main">
        {children}
      </main>
      <MarketingFooter authRoutes={AUTH_ROUTES} />
    </div>
  );
}
