'use client';

import Link from 'next/link';
import { ArrowRight, Database, KeyRound, Lock, ScrollText, ShieldCheck, Users } from 'lucide-react';
import { motion } from 'framer-motion';

const CONTROLS = [
  {
    icon: Lock,
    title: 'Encrypted at the field level',
    body: 'Sensitive fields — emails, names, social content — are encrypted with application-level encryption, not just disk-level encryption at rest.',
  },
  {
    icon: Database,
    title: 'Tenant isolation by design',
    body: 'Every query is scoped to a tenant, enforced at the database layer with row-level security policies — not just application logic that could be bypassed.',
  },
  {
    icon: KeyRound,
    title: 'Modern password hashing',
    body: 'Passwords are hashed with bcrypt or Argon2id plus a server-side pepper, never stored or logged in plain text.',
  },
  {
    icon: Users,
    title: 'Role-based access control',
    body: 'Session tokens carry signed role claims, verified independently by both the app layer and the API — a compromised session can\'t grant itself admin access.',
  },
  {
    icon: ScrollText,
    title: 'Audit trails on sensitive actions',
    body: 'Login, registration, and admin-level changes are logged with enough context to investigate — without storing raw credentials.',
  },
  {
    icon: ShieldCheck,
    title: 'Rate limiting on every sensitive endpoint',
    body: 'Login, registration, and password-reset flows are rate-limited per account and per IP, independently, so one noisy tenant can\'t exhaust another\'s budget.',
  },
];

function StaggeredControl({ control, index }: { control: typeof CONTROLS[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: index * 0.08 }}
      className="mk-card p-8 group"
    >
      <div className="mb-5 inline-flex w-fit rounded-lg border border-[#18181814] bg-[#18181808] p-3 text-[#466cf3] transition-all duration-300 group-hover:scale-105 group-hover:border-[#466cf3]/50">
        <control.icon size={22} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <h2 className="mb-2.5 text-lg font-semibold text-[#181818]">{control.title}</h2>
      <p className="text-[15px] leading-relaxed text-[#46484d]">{control.body}</p>
    </motion.div>
  );
}

export default function TrustClient() {
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
          <span className="mk-eyebrow mb-5">Trust & security</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#181818] sm:text-6xl">
            Security is not an afterthought
          </h1>
          <p className="mt-5 text-lg text-[#46484d]">
            The same tenant isolation and access controls that protect your data protect every other tenant on
            Nuxtron — here&apos;s what that actually means underneath the product.
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
          {CONTROLS.map((control, index) => (
            <StaggeredControl key={control.title} control={control} index={index} />
          ))}
        </motion.div>
      </section>

      <section className="mk-section">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="mk-container max-w-3xl"
        >
          <div className="mk-card p-10 group">
            <h2 className="mb-3 text-2xl font-semibold text-[#181818]">Have a security question?</h2>
            <p className="mb-6 text-[15px] leading-relaxed text-[#46484d]">
              For security disclosures, questionnaires, or a deeper technical review, reach out and we&apos;ll loop
              in the right person.
            </p>
            <Link href="/contact" className="inline-flex items-center gap-2 font-semibold text-[#466cf3] group">
              Contact security <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}