import type { Metadata } from 'next';
import Link from 'next/link';
import {
  ArrowRight,
  Bot,
  MessageSquareText,
  Radar,
  ShieldAlert,
  Star,
  Users,
} from 'lucide-react';

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
  },
  {
    icon: Radar,
    title: 'SEO & AI visibility',
    body: 'Traditional keyword rankings alongside AEO/GEO — how AI answer engines like ChatGPT and Gemini cite and represent your brand.',
    points: ['Keyword rank tracking', 'AI citation monitoring', 'Core Web Vitals audits', 'Content brief generation'],
  },
  {
    icon: MessageSquareText,
    title: 'Social operations',
    body: 'Schedule, publish, and listen across every connected channel from a single calendar, with AI-assisted drafting.',
    points: ['Cross-platform scheduling', 'Social listening & alerts', 'Bulk scheduling', 'Approval workflows'],
  },
  {
    icon: Star,
    title: 'Reviews & reputation',
    body: 'Monitor and respond to reviews across platforms, with AI-drafted responses your team approves before they go out.',
    points: ['Multi-platform review feed', 'AI-drafted responses', 'Sentiment tracking'],
  },
  {
    icon: ShieldAlert,
    title: 'Security & SIEM',
    body: 'Real-time threat detection, rate-limit enforcement, and a full audit trail — built into the same workspace as the work itself.',
    points: ['Real-time alerting', 'Audit-grade event logs', 'Role-based access control'],
  },
  {
    icon: Bot,
    title: 'IRA — autonomous agent',
    body: 'A supervised AI agent that plans and executes multi-step work across CRM, SEO, and social — every action attributable and reversible.',
    points: ['Multi-step task planning', 'Human approval gates', 'Full action audit trail'],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="mk-section pt-40 text-center">
        <div className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">Features</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Everything in one workspace
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            Six systems that used to live in six separate tools — now sharing one tenant, one data model, and one set
            of AI agents.
          </p>
        </div>
      </section>

      <section className="mk-section pt-0">
        <div className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2">
          {CAPABILITIES.map((cap) => (
            <div key={cap.title} className="mk-card p-8">
              <div className="mk-icon-tile mb-5">
                <cap.icon size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <h2 className="mb-2.5 text-xl font-semibold text-[#0b1b2b]">{cap.title}</h2>
              <p className="mb-5 text-[15px] leading-relaxed text-[#55677c]">{cap.body}</p>
              <ul className="space-y-2 border-t border-[#dbe6ee] pt-5">
                {cap.points.map((point) => (
                  <li key={point} className="text-sm text-[#55677c]">
                    {point}
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
            See it running on your data
          </h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
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
