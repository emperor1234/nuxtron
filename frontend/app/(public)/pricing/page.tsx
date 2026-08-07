import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Check } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Pricing | Nuxtron',
  description: 'Simple, transparent pricing for CRM, SEO & AI visibility, social operations, and security — from free to enterprise.',
  alternates: { canonical: '/pricing' },
};

type Plan = {
  id: string;
  name: string;
  price: number | null;
  cadence: string;
  description: string;
  features: string[];
  cta: { label: string; href: string };
  highlighted?: boolean;
};

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    price: 0,
    cadence: '/mo',
    description: 'For solo operators trying Nuxtron on real work.',
    features: ['1 user', '3 social accounts', '500 CRM contacts', '100 AI credits/mo', '100 tracked SEO keywords', 'Community support'],
    cta: { label: 'Start free', href: '/register' },
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 79,
    cadence: '/mo',
    description: 'For small teams running growth and support day to day.',
    features: [
      '3 users',
      '15 social accounts across 15 platforms',
      '5,000 CRM contacts',
      '5,000 AI credits/mo',
      '2,500 tracked SEO keywords',
      '1 AI chatbot, 1 review platform',
      'Email support',
    ],
    cta: { label: 'Start free trial', href: '/register' },
  },
  {
    id: 'studio',
    name: 'Studio',
    price: 199,
    cadence: '/mo',
    description: 'For growing teams and agencies managing multiple brands.',
    features: [
      '10 users',
      '50 social accounts across 25 platforms',
      '50,000 CRM contacts',
      '25,000 AI credits/mo',
      '5 AI chatbots, 5 review platforms',
      'Standard API access',
      'Priority email & chat support',
    ],
    cta: { label: 'Start free trial', href: '/register' },
    highlighted: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 699,
    cadence: '/mo',
    description: 'For organizations that need scale, white-label, and a dedicated CSM.',
    features: [
      'Unlimited users & CRM contacts',
      '200 social accounts',
      '100,000 AI credits/mo',
      'Full API access',
      'White-label',
      'Dedicated customer success manager',
    ],
    cta: { label: 'Talk to sales', href: '/contact' },
  },
];

const FAQS = [
  {
    q: 'Can I change plans later?',
    a: 'Yes — upgrade or downgrade anytime from your billing settings. Changes apply to your next billing cycle.',
  },
  {
    q: 'What counts as an AI credit?',
    a: 'Every AI agent action — a generated report, a drafted post, an autonomous IRA task — consumes credits based on the work involved. Unused credits do not roll over.',
  },
  {
    q: 'Is there an annual discount?',
    a: 'Yes — paying annually saves roughly 20% versus monthly billing on Pro, Studio, and Enterprise plans.',
  },
  {
    q: 'Do you offer a plan for agencies reselling Nuxtron?',
    a: 'Yes — our Agency plan includes white-label and multi-client management. Contact sales for pricing.',
  },
];

const FAQ_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: { '@type': 'Answer', text: item.a },
  })),
};

export default function PricingPage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD) }} />

      <section className="mk-section pt-40 text-center">
        <div className="mk-container">
          <span className="mk-eyebrow mb-5">Pricing</span>
          <h1 className="mx-auto max-w-2xl text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Plans that scale with your team
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-[#55677c]">
            Start free. Every plan includes CRM, SEO &amp; AI visibility tracking, and social scheduling — upgrade
            for more seats, more AI credits, and deeper automation.
          </p>
        </div>
      </section>

      <section className="mk-section pt-0">
        <div className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-2xl border p-8 ${
                plan.highlighted
                  ? 'z-10 border-[#0ea5e9] bg-[#f0f8fd] shadow-[0_0_40px_rgba(14,165,233,0.14)] lg:scale-105'
                  : 'border-[#dbe6ee] bg-white hover:border-[#0ea5e9]/40'
              } transition-all`}
            >
              {plan.highlighted ? (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#0ea5e9] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white">
                  Most popular
                </span>
              ) : null}

              <h2 className="text-xl font-bold text-[#0b1b2b]">{plan.name}</h2>
              <p className="mb-8 mt-2 h-10 text-sm text-[#8595a8]">{plan.description}</p>

              <div className="mb-8 flex items-baseline gap-1">
                <span className="text-[#8595a8]">$</span>
                <span className="text-5xl font-bold tabular-nums text-[#0b1b2b]">{plan.price}</span>
                <span className="text-sm text-[#8595a8]">{plan.cadence}</span>
              </div>

              <ul className="mb-8 flex-1 space-y-3.5">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-[#33475b]">
                    <Check size={16} className="mt-0.5 shrink-0 text-[#0ea5e9]" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href={plan.cta.href}
                className={`w-full rounded-lg px-4 py-3 text-center text-sm font-bold uppercase tracking-wider transition-all ${
                  plan.highlighted
                    ? 'bg-[#0ea5e9] text-white hover:bg-[#0c8fcc]'
                    : 'border border-[#dbe6ee] bg-white text-[#0b1b2b] hover:border-[#0ea5e9]/50 hover:bg-[#f0f8fd]'
                }`}
              >
                {plan.cta.label}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <h2 className="mb-10 text-center text-3xl font-semibold tracking-tight text-[#0b1b2b] sm:text-4xl">
            Frequently asked questions
          </h2>
          <dl className="divide-y divide-[#dbe6ee] rounded-2xl border border-[#dbe6ee] bg-white">
            {FAQS.map((item) => (
              <div key={item.q} className="p-6">
                <dt className="mb-2 font-semibold text-[#0b1b2b]">{item.q}</dt>
                <dd className="text-sm leading-relaxed text-[#55677c]">{item.a}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-6 text-center text-sm text-[#55677c]">
            More questions? See the full <Link href="/faq" className="font-semibold text-[#0c8fcc] hover:underline">FAQ</Link>.
          </p>
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">Still deciding?</h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-[#55677c]">
            Talk to our team about which plan fits your workflow — no pressure, no scripted demo.
          </p>
          <Link href="/contact" className="mk-shiny-cta mt-8">
            Talk to sales <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </>
  );
}
