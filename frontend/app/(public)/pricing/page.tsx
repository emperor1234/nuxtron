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

export default function PricingPage() {
  return (
    <>
      <section className="mk-section pt-40 text-center">
        <div className="mk-container">
          <span className="mk-eyebrow mb-5">Pricing</span>
          <h1 className="mx-auto max-w-2xl text-5xl font-semibold tracking-tight text-white sm:text-6xl">
            Plans that scale with your team
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-zinc-400">
            Start free. Every plan includes CRM, SEO &amp; AI visibility tracking, and social scheduling — upgrade for
            more seats, more AI credits, and deeper automation.
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
                  ? 'z-10 border-[#ef233c] bg-zinc-900/50 shadow-[0_0_40px_rgba(239,35,60,0.12)] lg:scale-105'
                  : 'border-white/10 bg-black hover:border-white/20'
              } transition-all`}
            >
              {plan.highlighted ? (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#ef233c] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white">
                  Most popular
                </span>
              ) : null}

              <h2 className="text-xl font-bold text-white">{plan.name}</h2>
              <p className="mb-8 mt-2 h-10 text-sm text-zinc-500">{plan.description}</p>

              <div className="mb-8 flex items-baseline gap-1">
                <span className="text-zinc-500">$</span>
                <span className="text-5xl font-bold tabular-nums text-white">{plan.price}</span>
                <span className="text-sm text-zinc-500">{plan.cadence}</span>
              </div>

              <ul className="mb-8 flex-1 space-y-3.5">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-zinc-300">
                    <Check size={16} className="mt-0.5 shrink-0 text-[#ef233c]" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href={plan.cta.href}
                className={`w-full rounded-lg px-4 py-3 text-center text-sm font-bold uppercase tracking-wider transition-all ${
                  plan.highlighted
                    ? 'bg-[#ef233c] text-white hover:bg-[#d81f36]'
                    : 'border border-white/10 bg-white/5 text-white hover:bg-white/10'
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
          <h2 className="mb-10 text-center text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Frequently asked questions
          </h2>
          <dl className="divide-y divide-white/10 rounded-2xl border border-white/10">
            {FAQS.map((item) => (
              <div key={item.q} className="p-6">
                <dt className="mb-2 font-semibold text-white">{item.q}</dt>
                <dd className="text-sm leading-relaxed text-zinc-400">{item.a}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">Still deciding?</h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-zinc-400">
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
