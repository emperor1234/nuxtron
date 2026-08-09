import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  Building2,
  CheckCircle2,
  ChevronDown,
  Layers,
  MessageSquareText,
  Radar,
  ShieldCheck,
  Share2,
} from 'lucide-react';
import { KeyToolsTabs } from './_components/key-tools-tabs';
import { SolutionsGrid } from './_components/solutions-grid';
import { Reveal } from './_components/reveal';
import { TestimonialSlider, type Testimonial } from './_components/testimonial-slider';

export const metadata: Metadata = {
  title: 'Nuxtron — The command center for growth and security teams',
  description:
    'CRM, SEO & AI-visibility intelligence, social operations, and security monitoring — run by your team and your AI agents, in one workspace.',
  alternates: { canonical: '/' },
};

// No aggregateRating here: we don't have real review data to back one, and
// fabricating one in structured data (vs. just on-page copy) risks a Google
// manual action for fake review markup on top of being misleading.
const ORG_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Nuxtron',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Web',
  description:
    'CRM, SEO & AI-visibility intelligence, social operations, and security monitoring — run by your team and your AI agents, in one workspace.',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
};

const CONNECTED = [
  { icon: Building2, label: 'CRM' },
  { icon: Radar, label: 'SEO & AEO' },
  { icon: Share2, label: 'Social' },
  { icon: MessageSquareText, label: 'Reviews' },
  { icon: ShieldCheck, label: 'SIEM' },
  { icon: Bot, label: 'IRA Agent' },
] as const;

const STATS = [
  { icon: Layers, value: '6', label: 'Connected surfaces', body: 'CRM, SEO & AI visibility, social, reviews, security, and AI agents — one workspace.' },
  { icon: CheckCircle2, value: '1', label: 'Shared data model', body: 'Every pillar reads and writes the same tenant record. Nothing gets re-explained between tools.' },
  { icon: ShieldCheck, value: '100%', label: 'AI actions logged', body: 'Every autonomous action IRA takes is attributable and reversible, on a full audit trail.' },
  { icon: Bot, value: '0', label: 'Unsupervised by default', body: 'Nothing runs without your rules. You choose what IRA can auto-approve.' },
];

const TESTIMONIALS: Testimonial[] = [
  {
    quote: 'We replaced four tools and a spreadsheet with Nuxtron. Our team finally works from one source of truth.',
    role: 'Head of Revenue Operations',
    company: 'Mid-market SaaS company',
    initials: 'RM',
    name: 'revenue-ops-lead',
  },
];

const RESOURCES = [
  { tag: 'Product', title: 'Explore the platform', href: '/features' },
  { tag: 'Pricing', title: 'See plans & pricing', href: '/pricing' },
  { tag: 'Security', title: 'Trust & compliance center', href: '/trust' },
  { tag: 'Free tool', title: 'Try Translation Studio', href: '/tools/translation-studio' },
  { tag: 'Company', title: 'Our story', href: '/about' },
  { tag: 'Sales', title: 'Talk to our team', href: '/contact' },
] as const;

const FAQS = [
  {
    q: 'Is my data safe on Nuxtron?',
    a: 'Every AI agent action is logged and reversible, and access is scoped by role. See the Trust Center for our full security posture.',
  },
  {
    q: 'How do I get started?',
    a: 'Create a free workspace in minutes — no credit card required. You can connect your first channel right away.',
  },
  {
    q: 'Does IRA run automatically without approval?',
    a: 'No. IRA plans and proposes actions and shows you what it intends to do before it acts. Nothing runs unsupervised by default — you choose what to auto-approve.',
  },
  {
    q: 'How much does Nuxtron cost?',
    a: 'Pricing scales with team size and the tools you use. See the full pricing page for current plans and what is included.',
  },
];

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ORG_JSON_LD) }} />

      <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pb-20 pt-40">
        <div className="mk-fade-up mx-auto max-w-4xl text-center">
          <span className="mk-eyebrow mb-8 inline-flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#466cf3] opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#466cf3]" />
            </span>
            Now live: autonomous AI agent orchestration
          </span>

          <h1 className="text-5xl font-semibold leading-[1.08] tracking-tighter text-[#181818] sm:text-7xl">
            One command center for
            <br />
            <span className="relative inline-block text-[#466cf3]">
              growth &amp; security
              <svg
                className="absolute -bottom-2 left-0 h-3 w-full text-[#466cf3] opacity-60"
                viewBox="0 0 100 10"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path d="M0 5 Q 50 10 100 5" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            </span>
          </h1>

          <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-[#46484d] sm:text-xl">
            Nuxtron connects your CRM, SEO &amp; AI-visibility data, social channels, and security monitoring — then
            gives your team AI agents that can act on all of it, with a full audit trail.
          </p>

          <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/contact" className="mk-btn-secondary">
              Talk to sales
            </Link>
          </div>
          <p className="mt-5 text-sm text-[#8a8d93]">No credit card required</p>
        </div>

        <div className="relative mx-auto mt-16 w-full max-w-5xl px-2">
          <div
            aria-hidden="true"
            className="absolute inset-x-8 -top-6 h-full rounded-[28px] opacity-40 blur-3xl"
            style={{ background: 'linear-gradient(90deg, #21ccee, #466cf3, #f83d69)' }}
          />
          <div className="relative overflow-hidden rounded-2xl border border-[#18181814] bg-white shadow-[0_30px_80px_rgba(24,24,24,0.14)]">
            <div className="flex items-center gap-1.5 border-b border-[#18181814] bg-[#fafafa] px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
            </div>
            <Image
              src="/images/sales-crm-mockup.png"
              alt="Nuxtron CRM pipeline view showing deals, forecast, and revenue insights"
              width={1536}
              height={1024}
              className="w-full"
              priority
            />
          </div>
        </div>

        <div className="mt-16 w-full border-y border-[#18181814] bg-[#18181803] py-8 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 md:flex-row md:gap-12">
            <p className="shrink-0 text-xs font-bold uppercase tracking-widest text-[#8a8d93]">
              One workspace, connected:
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2.5">
              {CONNECTED.map((item) => (
                <span
                  key={item.label}
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#18181814] bg-white px-3.5 py-1.5 text-sm font-semibold text-[#46484d]"
                >
                  <item.icon size={14} className="text-[#466cf3]" aria-hidden="true" />
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pitch panel 1 — SEO & AI visibility */}
      <section className="relative overflow-hidden px-6 py-20" style={{ background: 'linear-gradient(160deg, #eef4ff, #f7fbff)' }}>
        <div className="mk-container grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <Reveal>
            <span className="mk-eyebrow-brand mb-5 inline-flex">Be found</span>
            <h2 className="text-3xl font-semibold leading-tight tracking-tight text-[#181818] sm:text-4xl">
              Get found in search and AI answers
            </h2>
            <p className="mt-5 max-w-md text-lg leading-relaxed text-[#46484d]">
              Track classic rankings next to AEO/GEO citations, so you know exactly where your visibility comes from
              — and where you&rsquo;re losing ground to AI answer engines.
            </p>
            <Link href="/features" className="mk-btn-primary mt-8 inline-flex">
              Explore SEO &amp; AI visibility <ArrowRight size={16} />
            </Link>
          </Reveal>
          <Reveal delay={0.1} className="relative mx-auto aspect-square w-full max-w-sm">
            <div aria-hidden="true">
              <div className="absolute inset-0 rounded-full border border-[#466cf322]" />
              <div className="absolute inset-8 rounded-full border border-[#466cf333]" />
              <div className="absolute inset-16 rounded-full border border-[#466cf344]" />
              <div className="absolute inset-0 grid place-items-center">
                <div className="grid h-20 w-20 place-items-center rounded-2xl bg-white text-[#466cf3] shadow-[0_20px_50px_rgba(70,108,243,0.25)]">
                  <Radar size={36} strokeWidth={1.5} />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Pitch panel 2 — AI agents */}
      <section className="relative overflow-hidden px-6 py-20" style={{ background: 'linear-gradient(160deg, #fdeef5, #fff7fb)' }}>
        <div className="mk-container grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <Reveal className="order-2 mx-auto w-full max-w-sm lg:order-1">
            <div className="space-y-3">
              {['Plan the work', 'Show what will change', 'Wait for your approval', 'Execute & log every step'].map((step, i) => (
                <div key={step} className="mk-card flex items-center gap-3 px-4 py-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#f83d6914] text-xs font-bold text-[#f83d69]">
                    {i + 1}
                  </span>
                  <span className="text-sm font-medium text-[#181818]">{step}</span>
                </div>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.1} className="order-1 lg:order-2">
            <span className="mk-eyebrow-brand mb-5 inline-flex">Act automatically</span>
            <h2 className="text-3xl font-semibold leading-tight tracking-tight text-[#181818] sm:text-4xl">
              Let AI do the work, safely
            </h2>
            <p className="mt-5 max-w-md text-lg leading-relaxed text-[#46484d]">
              IRA plans multi-step work and shows you exactly what it intends to do before it acts. Approve, edit, or
              auto-approve by rule — nothing runs unsupervised by default.
            </p>
            <Link href="/features" className="mk-btn-primary mt-8 inline-flex">
              See how IRA works <ArrowRight size={16} />
            </Link>
          </Reveal>
        </div>
      </section>

      {/* Pitch panel 3 — security / scale, dark */}
      <section className="relative overflow-hidden bg-[#181818] px-6 py-20">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />
        <div className="mk-container relative grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <Reveal>
            <span className="mb-5 inline-flex rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs font-bold uppercase tracking-widest text-[#f83d69]">
              Built for scale
            </span>
            <h2 className="text-3xl font-semibold leading-tight tracking-tight text-white sm:text-4xl">
              Security your team can&rsquo;t cut corners on
            </h2>
            <p className="mt-5 max-w-md text-lg leading-relaxed text-white/60">
              Real-time threat detection and role-scoped access sit in the same workspace as the work itself — every
              AI action logged and reviewable alongside it.
            </p>
            <Link
              href="/contact"
              className="mt-8 inline-flex items-center gap-2 rounded-full border border-white/20 px-7 py-3.5 font-semibold text-white transition-colors hover:bg-white/10"
            >
              Book a demo <ArrowRight size={16} />
            </Link>
          </Reveal>
          <Reveal
            delay={0.1}
            className="relative mx-auto grid w-full max-w-sm gap-3"
            style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}
          >
            <div style={{ display: 'contents' }} aria-hidden="true">
              {Array.from({ length: 16 }).map((_, i) => (
                <div
                  key={i}
                  className="grid aspect-square place-items-center rounded-xl border border-white/10"
                  style={{ background: i % 5 === 0 ? 'rgba(248,61,105,0.12)' : 'rgba(255,255,255,0.03)' }}
                >
                  {i % 5 === 0 ? <ShieldCheck size={16} className="text-[#f83d69]" /> : null}
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <Reveal className="mx-auto mb-16 max-w-2xl text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">Solutions</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              One workspace. Every growth surface.
            </h2>
            <p className="mt-5 text-lg text-[#46484d]">
              Every pillar shares the same data, the same tenant, the same AI agents — so nothing you build in one
              tool has to be re-explained to the next.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <SolutionsGrid />
          </Reveal>
        </div>
      </section>

      <section className="mk-section mk-section-alt">
        <div className="mk-container">
          <Reveal className="mx-auto mb-14 max-w-2xl text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">Key Tools</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              AI that moves work forward &amp; faster
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <KeyToolsTabs />
          </Reveal>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <Reveal className="mx-auto mb-14 max-w-2xl text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">How it&rsquo;s built</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              Designed as one system, not six
            </h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STATS.map((stat, i) => (
              <Reveal key={stat.label} delay={i * 0.06} className="mk-card p-7">
                <stat.icon size={20} strokeWidth={1.75} className="mb-4 text-[#466cf3]" aria-hidden="true" />
                <div className="text-4xl font-bold tracking-tight text-[#181818] [font-family:var(--font-geist-sans)]">
                  {stat.value}
                </div>
                <div className="mt-1 text-sm font-semibold text-[#181818]">{stat.label}</div>
                <p className="mt-2 text-sm leading-relaxed text-[#8a8d93]">{stat.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-[#18181814] bg-[#181818] px-6 py-20">
        <Reveal>
          <TestimonialSlider testimonials={TESTIMONIALS} />
        </Reveal>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <Reveal className="mx-auto mb-14 max-w-2xl text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">Resources</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              Everything you need to evaluate Nuxtron
            </h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {RESOURCES.map((resource) => (
              <Link key={resource.href} href={resource.href} className="mk-card group flex flex-col justify-between p-6">
                <div>
                  <span className="text-xs font-bold uppercase tracking-widest text-[#466cf3]">{resource.tag}</span>
                  <h3 className="mt-2 text-lg font-semibold tracking-tight text-[#181818]">{resource.title}</h3>
                </div>
                <ArrowUpRight
                  size={18}
                  className="mt-6 text-[#8a8d93] transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[#181818]"
                  aria-hidden="true"
                />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="mk-section mk-section-alt text-center">
        <Reveal className="mk-container">
          <span className="mk-eyebrow-brand mb-5 inline-flex">Pricing</span>
          <h2 className="mx-auto max-w-xl text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
            Simple plans that grow with you
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-lg text-[#46484d]">
            Start free. Upgrade when your team needs more seats, more automation, or dedicated support.
          </p>
          <Link href="/pricing" className="mk-btn-secondary mt-10 inline-flex">
            See full pricing <ArrowRight size={16} />
          </Link>
        </Reveal>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <Reveal className="mx-auto mb-14 text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">FAQ</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              Frequently asked questions
            </h2>
          </Reveal>
          <div className="space-y-3">
            {FAQS.map((faq) => (
              <details key={faq.q} className="mk-card group p-6 open:pb-6">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-[#181818] marker:content-none">
                  {faq.q}
                  <ChevronDown
                    size={18}
                    className="shrink-0 text-[#8a8d93] transition-transform group-open:rotate-180"
                    aria-hidden="true"
                  />
                </summary>
                <p className="mt-3 text-[15px] leading-relaxed text-[#46484d]">{faq.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="mk-section mk-section-alt text-center">
        <Reveal className="mk-container max-w-3xl">
          <h2 className="text-5xl font-bold tracking-tighter text-[#181818] sm:text-7xl">
            Ready to run everything <span className="text-[#466cf3]">from one place?</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-[#46484d]">
            Create your workspace in minutes. No credit card required to start.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
            </Link>
            <Link href="/contact" className="mk-btn-secondary">
              Talk to sales
            </Link>
          </div>
        </Reveal>
      </section>
    </>
  );
}
