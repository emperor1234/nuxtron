import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Integrations | Nuxtron',
  description:
    'Connect Nuxtron to the CRM, social, SEO, and communication tools your team already uses — Google, Meta, HubSpot, Slack, and more.',
  alternates: { canonical: '/integrations' },
};

const CATEGORIES = [
  {
    title: 'Social & content',
    items: ['Instagram', 'TikTok', 'YouTube', 'X (Twitter)', 'LinkedIn', 'Facebook'],
  },
  {
    title: 'Search & AI visibility',
    items: ['Google Search Console', 'Google Business Profile', 'Bing Webmaster', 'ChatGPT / AEO citations'],
  },
  {
    title: 'CRM & revenue',
    items: ['HubSpot', 'Salesforce', 'Stripe', 'QuickBooks'],
  },
  {
    title: 'Communication & support',
    items: ['Slack', 'Gmail', 'Outlook', 'Twilio', 'Zendesk'],
  },
  {
    title: 'Reviews & reputation',
    items: ['Google Reviews', 'Trustpilot', 'Yelp', 'G2'],
  },
  {
    title: 'Security & infrastructure',
    items: ['SAML SSO', 'SIEM webhook export', 'Audit-log export (S3/GCS)'],
  },
];

export default function IntegrationsPage() {
  return (
    <>
      <section className="mk-section pt-40 text-center">
        <div className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">Integrations</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Connects to the tools you already run
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            Nuxtron plugs into your social channels, search consoles, CRM, and support stack — so switching to one
            workspace doesn&apos;t mean ripping anything else out.
          </p>
        </div>
      </section>

      <section className="mk-section pt-0">
        <div className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {CATEGORIES.map((category) => (
            <div key={category.title} className="mk-card p-8">
              <h2 className="mb-4 text-lg font-semibold text-[#0b1b2b]">{category.title}</h2>
              <ul className="flex flex-wrap gap-2">
                {category.items.map((item) => (
                  <li
                    key={item}
                    className="rounded-full border border-[#dbe6ee] bg-[#f6fafd] px-3 py-1.5 text-sm text-[#33475b]"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
            Don&apos;t see what you need?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-[#55677c]">
            Enterprise plans include full API access and custom connector support.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/contact" className="mk-shiny-cta">
              Request an integration <ArrowRight size={16} />
            </Link>
            <Link href="/pricing" className="mk-btn-secondary">
              View pricing
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
