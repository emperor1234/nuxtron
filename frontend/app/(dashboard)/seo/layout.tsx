import type { ReactNode } from 'react';
import SeoRouteIdentityBanner from './components/seo-route-identity-banner';

export default function SeoLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="seo-product-surface">
      <SeoRouteIdentityBanner />
      {children}
    </div>
  );
}
