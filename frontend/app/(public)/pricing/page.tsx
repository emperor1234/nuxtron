import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Building2, Check, Rocket, ShieldCheck, Zap } from 'lucide-react';
import { Reveal } from '../_components/reveal';

export const metadata: Metadata = {
  title: 'Pricing | Nuxtron',
  description: 'Simple, transparent pricing for CRM, SEO & AI visibility, social operations, and security — from free to enterprise.',
  alternates: { canonical: '/pricing' },
};

type Plan = {
  id: string;
  name: string;
  icon: typeof Rocket;
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
    icon: Rocket,
    price: 0,
    cadence: '/mo',
    description: 'For solo operators trying Nuxtron on real work.',
    features: ['1 user', '3 social accounts', '500 CRM contacts', '100 AI credits/mo', '100 tracked SEO keywords', 'Community support'],
    cta: { label: 'Start free', href: '/register' },
  },
  {
    id: 'pro',
    name: 'Pro',
    icon: Zap,
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
    icon: Building2,
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
    icon: ShieldCheck,
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

      <section className="mk-section mk-pt-hero text-center">
        <Reveal className="mk-container animate-slide-in-left">
          <span className="mk-eyebrow mb-5">Pricing</span>
          <h1 className="mx-auto max-w-2xl text-5xl font-semibold tracking-tight text-[#181818] sm:text-6xl">
            Plans that scale with your team
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-[#46484d]">
            Start free. Every plan includes CRM, SEO & AI visibility tracking, and social scheduling — upgrade for
            more seats, more AI credits, and deeper automation.
          </p>
        </Reveal>
      </section>

      <section className="mk-section mk-pt-flush">
        <Reveal className="mk-container stagger-children">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {PLANS.map((plan, i) => (
              <Reveal
                key={plan.id}
                delay={i * 0.06}
                className={`relative flex flex-col rounded-2xl border p-8 transition-all ${
                  plan.highlighted
                    ? 'z-10 border-[#466cf3] bg-[#466cf308] shadow-[0_0_40px_rgba(70,108,243,0.12)] lg:scale-105'
                    : 'border-[#18181814] bg-white hover:border-[#1818181f] hover:shadow-lg hover:shadow-[#466cf3]/10'
                }`}
              >
                {plan.highlighted ? (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#466cf3] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white">
                    Most popular
                  </span>
                ) : null}

                <div className="mb-5 inline-flex w-fit rounded-lg border border-[#18181814] bg-[#466cf314] p-2.5 text-[#466cf3]">
                  <plan.icon size={20} strokeWidth={1.75} aria-hidden="true" />
                </div>

                <h2 className="text-xl font-bold text-[#181818]">{plan.name}</h2>
                <p className="mb-8 mt-2 h-10 text-sm text-[#8a8d93]">{plan.description}</p>

                <div className="mb-8 flex items-baseline gap-1">
                  <span className="text-[#8a8d93]">$</span>
                  <span className="text-5xl font-bold tabular-nums text-[#181818]">{plan.price}</span>
                  <span className="text-sm text-[#8a8d93]">{plan.cadence}</span>
                </div>

                <ul className="mb-8 flex-1 space-y-3.5">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm text-[#46484d] transition-colors group-hover:text-[#181818]">
                      <Check size={16} className="mt-0.5 shrink-0 text-[#466cf3]" aria-hidden="true" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link
                  href={plan.cta.href}
                  className={`w-full rounded-lg px-4 py-3 text-center text-sm font-bold uppercase tracking-wider transition-all ${
                    plan.highlighted
                      ? 'bg-[#181818] text-white hover:bg-black'
                      : 'border border-[#18181814] bg-[#18181808] text-[#181818] hover:bg-[#1818180f]'
                  }`}
                >
                  {plan.cta.label}
                </Link>
              </Reveal>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <Reveal className="animate-slide-in-left">
            <h2 className="mb-10 text-center text-3xl font-semibold tracking-tight text-[#181818] sm:text-4xl">
              Frequently asked questions
            </h2>
            <dl className="divide-y divide-[#18181814] rounded-2xl border border-[#18181814] stagger-children">
              {FAQS.map((item) => (
                <div key={item.q} className="p-6 transition-colors hover:bg-[#18181803]">
                  <dt className="mb-2 font-semibold text-[#181818]">{item.q}</dt>
                  <dd className="text-sm leading-relaxed text-[#46484d]">{item.a}</dd>
                </div>
              ))}
            </dl>
          </Reveal>
        </div>
      </section>

      <section className="mk-section mk-section-alt text-center">
        <Reveal className="mk-container max-w-2xl animate-scale-in">
          <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">Still deciding?</h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-[#46484d]">
            Talk to our team about which plan fits your workflow — no pressure, no scripted demo.
          </p>
          <Link href="/contact" className="mk-shiny-cta mt-8 group">
            Talk to sales <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </Reveal>
      </section>
    </>
  );
}
