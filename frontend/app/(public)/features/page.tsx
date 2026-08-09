import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Layers,
  MessageSquareText,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Star,
  Users,
} from 'lucide-react';
import { Reveal } from '../_components/reveal';

export const metadata: Metadata = {
  title: 'Features | Nuxtron',
  description: 'Everything inside the Nuxtron workspace: CRM, SEO & AI visibility, social operations, reviews, security, and autonomous AI agents.',
  alternates: { canonical: '/features' },
};

const CAPABILITIES = [
  {
    icon: Users,
    title: 'CRM & revenue',
    body: 'Contacts, deals, tasks, quotes, and invoices in one pipeline — scoped to your tenant, never mixed with anyone else\'s data.',
    points: ['Pipeline & deal tracking', 'Quotes and invoicing', 'Task automation', 'Custom entities & fields'],
    image: '/images/sales-crm-mockup.png',
  },
  {
    icon: Radar,
    title: 'SEO & AI visibility',
    body: 'Traditional keyword rankings alongside AEO/GEO — how AI answer engines like ChatGPT and Gemini cite and represent your brand.',
    points: ['Keyword rank tracking', 'AI citation monitoring', 'Core Web Vitals audits', 'Content brief generation'],
    image: '/images/marketing-hub-mockup.png',
  },
  {
    icon: MessageSquareText,
    title: 'Social operations',
    body: 'Schedule, publish, and listen across every connected channel from a single calendar, with AI-assisted drafting.',
    points: ['Cross-platform scheduling', 'Social listening & alerts', 'Bulk scheduling', 'Approval workflows'],
    image: null,
  },
  {
    icon: Star,
    title: 'Reviews & reputation',
    body: 'Monitor and respond to reviews across platforms, with AI-drafted responses your team approves before they go out.',
    points: ['Multi-platform review feed', 'AI-drafted responses', 'Sentiment tracking'],
    image: null,
  },
  {
    icon: ShieldAlert,
    title: 'Security & SIEM',
    body: 'Real-time threat detection, rate-limit enforcement, and a full audit trail — built into the same workspace as the work itself.',
    points: ['Real-time alerting', 'Audit-grade event logs', 'Role-based access control'],
    image: null,
  },
  {
    icon: Bot,
    title: 'IRA — autonomous agent',
    body: 'A supervised AI agent that plans and executes multi-step work across CRM, SEO, and social — every action attributable and reversible.',
    points: ['Multi-step task planning', 'Human approval gates', 'Full action audit trail'],
    image: null,
  },
];

const PRINCIPLES = [
  { icon: Layers, value: '1', label: 'Tenant per workspace', body: 'Every capability above reads and writes the same underlying tenant record.' },
  { icon: CheckCircle2, value: '0', label: 'Data silos', body: 'Nothing you build in CRM has to be re-explained to social, SEO, or security.' },
  { icon: ShieldCheck, value: '100%', label: 'Actions logged', body: 'Every AI agent action is attributable, reviewable, and reversible.' },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="relative px-6 pb-16 pt-40 text-center">
        <Reveal className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">Features</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#181818] sm:text-6xl">Everything in one workspace</h1>
          <p className="mt-5 text-lg text-[#46484d]">
            Six systems that used to live in six separate tools — now sharing one tenant, one data model, and one set
            of AI agents.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="relative mx-auto mt-14 w-full max-w-4xl px-2">
          <div
            aria-hidden="true"
            className="absolute inset-x-8 -top-6 h-full rounded-[28px] opacity-30 blur-3xl"
            style={{ background: 'linear-gradient(90deg, #21ccee, #466cf3, #f83d69)' }}
          />
          <div className="relative overflow-hidden rounded-2xl border border-[#18181814] bg-white shadow-[0_30px_80px_rgba(24,24,24,0.14)]">
            <div className="flex items-center gap-1.5 border-b border-[#18181814] bg-[#fafafa] px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#e5e7eb]" />
            </div>
            <Image src="/images/marketing-hub-mockup.png" alt="" width={1536} height={1024} className="w-full" />
          </div>
        </Reveal>
      </section>

      <section className="mk-section mk-pt-tight">
        <div className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2">
          {CAPABILITIES.map((cap, i) => (
            <Reveal key={cap.title} delay={(i % 2) * 0.08} className="mk-card overflow-hidden p-8">
              <div className="mb-5 inline-flex w-fit rounded-lg border border-[#18181814] bg-[#466cf314] p-3 text-[#466cf3]">
                <cap.icon size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <h2 className="mb-2.5 text-xl font-semibold text-[#181818]">{cap.title}</h2>
              <p className="mb-5 text-[15px] leading-relaxed text-[#46484d]">{cap.body}</p>
              <ul className="mb-5 space-y-2 border-t border-[#18181814] pt-5">
                {cap.points.map((point) => (
                  <li key={point} className="text-sm text-[#8a8d93]">
                    {point}
                  </li>
                ))}
              </ul>
              {cap.image ? (
                <div className="overflow-hidden rounded-xl border border-[#18181814]">
                  <div className="flex items-center gap-1.5 border-b border-[#18181814] bg-[#fafafa] px-3 py-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#e5e7eb]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#e5e7eb]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#e5e7eb]" />
                  </div>
                  <Image src={cap.image} alt="" width={1536} height={1024} className="w-full scale-[1.3] origin-top-left" />
                </div>
              ) : (
                <div
                  className="flex h-28 items-center justify-center rounded-xl border border-[#18181814]"
                  style={{ background: 'linear-gradient(135deg, #21ccee0f, #466cf314, #f83d690f)' }}
                  aria-hidden="true"
                >
                  <cap.icon size={36} strokeWidth={1.25} className="text-[#466cf3] opacity-70" />
                </div>
              )}
            </Reveal>
          ))}
        </div>
      </section>

      <section className="mk-section mk-section-alt">
        <div className="mk-container">
          <Reveal className="mx-auto mb-14 max-w-2xl text-center">
            <span className="mk-eyebrow-brand mb-5 inline-flex">Why one workspace</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">
              Built as one system from the start
            </h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {PRINCIPLES.map((p, i) => (
              <Reveal key={p.label} delay={i * 0.08} className="mk-card p-7">
                <p.icon size={20} strokeWidth={1.75} className="mb-4 text-[#466cf3]" aria-hidden="true" />
                <div className="text-4xl font-bold tracking-tight text-[#181818] [font-family:var(--font-geist-sans)]">
                  {p.value}
                </div>
                <div className="mt-1 text-sm font-semibold text-[#181818]">{p.label}</div>
                <p className="mt-2 text-sm leading-relaxed text-[#8a8d93]">{p.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="mk-section text-center">
        <Reveal className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">See it running on your data</h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
            </Link>
            <Link href="/pricing" className="mk-btn-secondary">
              View pricing
            </Link>
          </div>
        </Reveal>
      </section>
    </>
  );
}
