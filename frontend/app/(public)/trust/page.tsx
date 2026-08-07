import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Database, KeyRound, Lock, ScrollText, ShieldCheck, Users } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Trust & Security | Nuxtron',
  description: 'How Nuxtron protects tenant data: encryption, tenant isolation, role-based access control, and audit logging.',
  alternates: { canonical: '/trust' },
};

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

export default function TrustPage() {
  return (
    <>
      <section className="mk-section pt-40 text-center">
        <div className="mk-container max-w-2xl">
          <span className="mk-eyebrow mb-5">Trust &amp; security</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Security is not an afterthought
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            The same tenant isolation and access controls that protect your data protect every other tenant on
            Nuxtron — here&apos;s what that actually means underneath the product.
          </p>
        </div>
      </section>

      <section className="mk-section pt-0">
        <div className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {CONTROLS.map((control) => (
            <div key={control.title} className="mk-card p-8">
              <div className="mk-icon-tile mb-5">
                <control.icon size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <h2 className="mb-2.5 text-lg font-semibold text-[#0b1b2b]">{control.title}</h2>
              <p className="text-[15px] leading-relaxed text-[#55677c]">{control.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl">
          <div className="mk-card p-10">
            <h2 className="mb-3 text-2xl font-semibold text-[#0b1b2b]">Have a security question?</h2>
            <p className="mb-6 text-[15px] leading-relaxed text-[#55677c]">
              For security disclosures, questionnaires, or a deeper technical review, reach out and we&apos;ll loop
              in the right person.
            </p>
            <Link href="/contact" className="inline-flex items-center gap-2 font-semibold text-[#0c8fcc]">
              Contact security <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
