import './globals.css';
import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { headers } from 'next/headers';
import Script from 'next/script';
import { Partytown } from '@builder.io/partytown/react';
import { Manrope, Sora, Inter } from 'next/font/google';
import IraChat from './components/ira-chat';
import PwaBootstrap from './components/pwa-bootstrap';

const bodyFont = Manrope({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

const displayFont = Sora({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

// Open-source substitute for the proprietary Sohne tier used on the
// marketing homepage: Inter at thin/regular/medium with ss01 + tnum support.
const interFont = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  variable: '--font-inter',
  display: 'swap',
});

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.NEXT_PUBLIC_APP_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:4173');

export const metadata: Metadata = {
  title: 'Nuxtron Autonomous AI Platform',
  description: 'Autonomous AI platform for Social Media, Ads, SEO, and conversion growth.',
  metadataBase: new URL(siteUrl),
  manifest: '/manifest.json',
  openGraph: {
    title: 'Nuxtron Autonomous AI Platform',
    description: 'Autonomous AI platform for Social Media, Ads, SEO, and conversion growth.',
    siteName: 'Nuxtron',
    type: 'website',
    images: [{ url: '/brand/og-image.png', width: 1200, height: 630, alt: 'Nuxtron Platform' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Nuxtron Autonomous AI Platform',
    description: 'Autonomous AI platform for Social Media, Ads, SEO, and conversion growth.',
    images: ['/brand/og-image.png'],
  },
  icons: {
    icon: '/brand/nuxtron-icon-square.png',
    apple: '/brand/nuxtron-icon-square.png',
  },
};

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const clarityId = process.env.NEXT_PUBLIC_CLARITY_PROJECT_ID;
  // Set per-request by proxy.ts alongside the nonce'd CSP header — required
  // for this page's own inline <Script> to be allowed to execute at all.
  const nonce = (await headers()).get('x-nonce') ?? undefined;

  return (
    <html lang="en" data-theme="light" className={`${bodyFont.variable} ${displayFont.variable} ${interFont.variable}`} style={{ colorScheme: 'light' }}>
      <body>
        {children}
        
        <Partytown forward={['clarity']} nonce={nonce} />
        <PwaBootstrap />
        {clarityId ? (
          <Script id="ms-clarity" type="text/partytown" nonce={nonce}>
            {`(function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
})(window, document, "clarity", "script", "${clarityId}");`}
          </Script>
        ) : null}
        <IraChat />
      </body>
    </html>
  );
}
