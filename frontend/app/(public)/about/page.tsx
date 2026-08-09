import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Bot, Layers, Radar, Shield } from 'lucide-react';

export const metadata: Metadata = {
  title: 'About | Nuxtron',
  description: 'Why Nuxtron exists, and what running one connected system instead of six disconnected tools actually looks like.',
  alternates: { canonical: '/about' },
};

const VALUES = [
  {
    icon: Layers,
    title: 'One system, not six tabs',
    body: 'CRM, SEO, social, and security share the same tenant and the same data model — nothing needs to be re-explained between tools.',
  },
  {
    icon: Bot,
    title: 'Agents that show their work',
    body: 'Every autonomous action is logged, attributable, and reversible. Automation you can audit, not a black box.',
  },
  {
    icon: Shield,
    title: 'Security is not a bolt-on',
    body: 'Tenant isolation, encrypted fields, and audit trails are part of the platform from day one, not a later compliance sprint.',
  },
  {
    icon: Radar,
    title: 'Built for how search actually works now',
    body: 'Traditional rankings and AI answer-engine visibility tracked side by side, because your customers use both.',
  },
];

export default function AboutPage() {
  return (
    <>
      <section className="mk-section mk-pt-hero text-center">
        <div className="mk-container max-w-3xl">
          <span className="mk-eyebrow mb-5">Company</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#181818] sm:text-6xl">
            We got tired of the six-tab tax
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-[#46484d]">
            Every growth and security team we talked to was stitching together a CRM, an SEO tool, a social
            scheduler, a review manager, and a security dashboard — paying for the integrations between them almost
            as much as the tools themselves. Nuxtron is what we built instead: one workspace, one data model, and AI
            agents that can act across all of it.
          </p>
        </div>
      </section>

      <section className="mk-section mk-pt-flush">
        <div className="mk-container grid grid-cols-1 gap-6 sm:grid-cols-2">
          {VALUES.map((value) => (
            <div key={value.title} className="mk-card p-8">
              <div className="mb-5 inline-flex w-fit rounded-lg border border-[#18181814] bg-[#18181808] p-3 text-[#466cf3]">
                <value.icon size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <h2 className="mb-2.5 text-xl font-semibold text-[#181818]">{value.title}</h2>
              <p className="text-[15px] leading-relaxed text-[#46484d]">{value.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container max-w-3xl rounded-2xl border border-[#18181814] bg-[#f5f6f8] p-10 sm:p-14">
          <h2 className="mb-4 text-3xl font-semibold tracking-tight text-[#181818]">How we build</h2>
          <div className="space-y-4 text-[15px] leading-relaxed text-[#46484d]">
            <p>
              We ship for teams who need to trust what the platform does on their behalf — which means every
              AI-driven action in Nuxtron is scoped, logged, and reviewable, and every tenant&apos;s data is isolated
              at the database layer, not just the application layer.
            </p>
            <p>
              We&apos;d rather ship one workflow that genuinely replaces a tool you&apos;re paying for than ten
              half-finished integrations. That&apos;s the bar for everything that ships.
            </p>
          </div>
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-2xl">
          <h2 className="text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">Come see it for yourself</h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
            </Link>
            <Link
              href="/contact"
              className="rounded-full border border-[#18181822] bg-white px-8 py-4 font-medium text-[#46484d] transition-all hover:border-[#181818] hover:bg-[#f5f6f8] hover:text-[#181818]"
            >
              Talk to us
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
