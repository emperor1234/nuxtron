import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export const metadata: Metadata = {
  title: 'FAQ | Nuxtron',
  description: 'Answers to common questions about Nuxtron: the platform, security, billing, and how the AI agents work.',
  alternates: { canonical: '/faq' },
};

type FaqGroup = {
  title: string;
  items: { q: string; a: string }[];
};

const GROUPS: FaqGroup[] = [
  {
    title: 'Product',
    items: [
      {
        q: 'What is Nuxtron, exactly?',
        a: 'Nuxtron is a single workspace that combines CRM, SEO & AI-visibility tracking, social media operations, review management, and security monitoring — with AI agents that can act across all of it, not just report on it.',
      },
      {
        q: 'Do I have to use every module?',
        a: 'No. Every module works independently — most teams start with one or two (usually CRM or social) and add more once the rest of the team sees the value of shared data.',
      },
      {
        q: 'What is the IRA agent?',
        a: 'IRA is Nuxtron\'s supervised autonomous agent. It plans and executes multi-step work across your connected modules — every action is logged, attributable, and reversible, and you control which actions require approval before they run.',
      },
      {
        q: 'What is AEO/GEO tracking?',
        a: 'Answer-Engine Optimization and Generative-Engine Optimization: tracking how AI answer engines like ChatGPT and Gemini cite and represent your brand, alongside traditional search-engine keyword rankings.',
      },
    ],
  },
  {
    title: 'Security & data',
    items: [
      {
        q: 'Is my data isolated from other tenants?',
        a: 'Yes — every query is scoped to your tenant and enforced at the database layer with row-level security, not just application logic. See our Trust & Security page for details.',
      },
      {
        q: 'Do you train AI models on my data?',
        a: 'No. We do not use your workspace data to train models shared across other customers.',
      },
      {
        q: 'How is sensitive data protected?',
        a: 'Sensitive fields use application-level encryption in addition to disk-level encryption at rest, and passwords are hashed with bcrypt or Argon2id plus a server-side pepper.',
      },
    ],
  },
  {
    title: 'Billing',
    items: [
      {
        q: 'Is there a free plan?',
        a: 'Yes — the Starter plan is free for a single user with a smaller usage allowance, so you can try Nuxtron on real work before upgrading.',
      },
      {
        q: 'Can I cancel anytime?',
        a: 'Yes, from your billing settings at any time. Downgrades take effect at your next billing cycle; there is no cancellation fee.',
      },
      {
        q: 'Do you offer discounts for nonprofits or startups?',
        a: 'Yes — contact sales with details about your organization and we\'ll follow up with eligibility and pricing.',
      },
    ],
  },
];

const FAQ_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: GROUPS.flatMap((group) =>
    group.items.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    }))
  ),
};

export default function FaqPage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD) }} />

      <section className="mk-section pt-40 text-center">
        <div className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">FAQ</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Frequently asked questions
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            Can&apos;t find what you&apos;re looking for? <Link href="/contact" className="font-semibold text-[#0c8fcc] hover:underline">Talk to our team</Link>.
          </p>
        </div>
      </section>

      <section className="mk-section pt-0">
        <div className="mk-container max-w-3xl space-y-12">
          {GROUPS.map((group) => (
            <div key={group.title}>
              <h2 className="mb-4 text-2xl font-semibold tracking-tight text-[#0b1b2b]">{group.title}</h2>
              <dl className="divide-y divide-[#dbe6ee] rounded-2xl border border-[#dbe6ee] bg-white">
                {group.items.map((item) => (
                  <div key={item.q} className="p-6">
                    <dt className="mb-2 font-semibold text-[#0b1b2b]">{item.q}</dt>
                    <dd className="text-sm leading-relaxed text-[#55677c]">{item.a}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">Still have questions?</h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
            </Link>
            <Link href="/contact" className="mk-btn-secondary">
              Contact us
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
