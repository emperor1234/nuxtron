import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Globe, HeartHandshake, Rocket, Users } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Careers | Nuxtron',
  description: 'Help build the AI-native command center for growth and security teams. See open roles and how we work at Nuxtron.',
  alternates: { canonical: '/careers' },
};

const VALUES = [
  {
    icon: Rocket,
    title: 'Ship what actually replaces a tool',
    body: 'We measure ourselves by whether a feature genuinely lets a customer cancel another subscription — not by lines shipped.',
  },
  {
    icon: Users,
    title: 'Small team, real ownership',
    body: 'Every engineer owns a slice of the product end to end, from schema to UI to the on-call pager for it.',
  },
  {
    icon: Globe,
    title: 'Remote-first, async by default',
    body: 'We write things down. Meetings are for decisions that genuinely need a room, not status updates.',
  },
  {
    icon: HeartHandshake,
    title: 'Security and trust are everyone\'s job',
    body: 'Tenant isolation and data protection aren\'t one team\'s problem — every engineer is expected to reason about them.',
  },
];

const ROLES = [
  { title: 'Senior Full-Stack Engineer', team: 'Platform', location: 'Remote (US/EU hours)' },
  { title: 'AI/ML Engineer — Agent Systems', team: 'IRA Agent', location: 'Remote (US/EU hours)' },
  { title: 'Product Designer', team: 'Design', location: 'Remote' },
  { title: 'Security Engineer', team: 'Trust & Security', location: 'Remote (US hours)' },
  { title: 'Customer Success Manager', team: 'Revenue', location: 'Remote' },
];

export default function CareersPage() {
  return (
    <>
      <section className="mk-section mk-pt-hero text-center">
        <div className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">Careers</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">Build the workspace</h1>
          <p className="mt-5 text-lg text-[#55677c]">
            We&apos;re a small remote team replacing the six-tool tax with one connected system — and we&apos;re
            looking for people who want real ownership over what they build.
          </p>
        </div>
      </section>

      <section className="mk-section mk-pt-flush">
        <div className="mk-container grid grid-cols-1 gap-6 sm:grid-cols-2">
          {VALUES.map((value) => (
            <div key={value.title} className="mk-card p-8">
              <div className="mk-icon-tile mb-5">
                <value.icon size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <h2 className="mb-2.5 text-xl font-semibold text-[#0b1b2b]">{value.title}</h2>
              <p className="text-[15px] leading-relaxed text-[#55677c]">{value.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <h2 className="mb-8 text-center text-3xl font-semibold tracking-tight text-[#0b1b2b] sm:text-4xl">
            Open roles
          </h2>
          <div className="divide-y divide-[#dbe6ee] rounded-2xl border border-[#dbe6ee] bg-white">
            {ROLES.map((role) => (
              <div key={role.title} className="flex flex-col gap-2 p-6 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-base font-semibold text-[#0b1b2b]">{role.title}</h3>
                  <p className="mt-1 text-sm text-[#8595a8]">
                    {role.team} · {role.location}
                  </p>
                </div>
                <Link
                  href="/contact"
                  className="inline-flex items-center gap-1.5 self-start text-sm font-semibold text-[#0c8fcc] sm:self-auto"
                >
                  Apply <ArrowRight size={14} />
                </Link>
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-[#55677c]">
            Don&apos;t see a fit but think you should be here anyway?{' '}
            <Link href="/contact" className="font-semibold text-[#0c8fcc] hover:underline">
              Reach out
            </Link>
            .
          </p>
        </div>
      </section>
    </>
  );
}
