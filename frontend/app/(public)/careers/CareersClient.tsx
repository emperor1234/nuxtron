'use client';

import Link from 'next/link';
import { ArrowRight, Globe, HeartHandshake, Rocket, Users } from 'lucide-react';
import { motion } from 'framer-motion';

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

function StaggeredValue({ value, index }: { value: typeof VALUES[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: index * 0.1 }}
      className="mk-card p-8 group"
    >
      <div className="mk-icon-tile mb-5 transition-transform group-hover:scale-105 group-hover:rotate-2">
        <value.icon size={22} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <h2 className="mb-2.5 text-xl font-semibold text-[#0b1b2b]">{value.title}</h2>
      <p className="text-[15px] leading-relaxed text-[#55677c]">{value.body}</p>
    </motion.div>
  );
}

function StaggeredRole({ role, index }: { role: typeof ROLES[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      className="flex flex-col gap-2 p-6 sm:flex-row sm:items-center sm:justify-between transition-colors hover:bg-[#0b1b2b]/3"
    >
      <div>
        <h3 className="text-base font-semibold text-[#0b1b2b]">{role.title}</h3>
        <p className="mt-1 text-sm text-[#8595a8]">
          {role.team} · {role.location}
        </p>
      </div>
      <Link
        href="/contact"
        className="inline-flex items-center gap-1.5 self-start text-sm font-semibold text-[#0c8fcc] sm:self-auto transition-transform hover:translate-x-1"
      >
        Apply <ArrowRight size={14} />
      </Link>
    </motion.div>
  );
}

export default function CareersClient() {
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
          <span className="mk-eyebrow mb-5">Careers</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">Build the workspace</h1>
          <p className="mt-5 text-lg text-[#55677c]">
            We&apos;re a small remote team replacing the six-tool tax with one connected system — and we&apos;re
            looking for people who want real ownership over what they build.
          </p>
        </motion.div>
      </section>

      <section className="mk-section mk-pt-flush">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="mk-container grid grid-cols-1 gap-6 sm:grid-cols-2 stagger-children"
        >
          {VALUES.map((value, index) => (
            <StaggeredValue key={value.title} value={value} index={index} />
          ))}
        </motion.div>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <h2 className="mb-8 text-center text-3xl font-semibold tracking-tight text-[#0b1b2b] sm:text-4xl">
              Open roles
            </h2>
            <div className="divide-y divide-[#dbe6ee] rounded-2xl border border-[#dbe6ee] bg-white">
              {ROLES.map((role, index) => (
                <StaggeredRole key={role.title} role={role} index={index} />
              ))}
            </div>
            <p className="mt-8 text-center text-sm text-[#55677c]">
              Don&apos;t see a fit but think you should be here anyway?{' '}
              <Link href="/contact" className="font-semibold text-[#0c8fcc] hover:underline">
                Reach out
              </Link>
              .
            </p>
          </motion.div>
        </div>
      </section>
    </>
  );
}