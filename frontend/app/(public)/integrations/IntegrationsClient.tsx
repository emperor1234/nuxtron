'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

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

function StaggeredCategory({ category, index }: { category: typeof CATEGORIES[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: index * 0.08 }}
      className="mk-card p-8 group"
    >
      <h2 className="mb-4 text-lg font-semibold text-[#0b1b2b]">{category.title}</h2>
      <ul className="flex flex-wrap gap-2">
        {category.items.map((item) => (
          <li
            key={item}
            className="rounded-full border border-[#dbe6ee] bg-[#f6fafd] px-3 py-1.5 text-sm text-[#33475b] transition-all duration-300 group-hover:border-[#0ea5e9] group-hover:bg-[#0ea5e9]/10 group-hover:text-[#0c8fcc]"
          >
            {item}
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

export default function IntegrationsClient() {
  return (
    <>
      <section className="mk-section mk-pt-hero text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="mk-container max-w-2xl"
        >
          <span className="mk-eyebrow mb-5">Integrations</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Connects to the tools you already run
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            Nuxtron plugs into your social channels, search consoles, CRM, and support stack — so switching to one
            workspace doesn&apos;t mean ripping anything else out.
          </p>
        </motion.div>
      </section>

      <section className="mk-section mk-pt-flush">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 stagger-children"
        >
          {CATEGORIES.map((category, index) => (
            <StaggeredCategory key={category.title} category={category} index={index} />
          ))}
        </motion.div>
      </section>

      <section className="mk-section text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="mk-container max-w-2xl"
        >
          <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
            Don&apos;t see what you need?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-[#55677c]">
            Enterprise plans include full API access and custom connector support.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/contact" className="mk-shiny-cta group">
              Request an integration <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/pricing" className="mk-btn-secondary group">
              View pricing <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}