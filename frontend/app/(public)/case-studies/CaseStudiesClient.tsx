'use client';

import Link from 'next/link';
import { ArrowRight, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

const STUDIES = [
  {
    company: 'Mid-market SaaS company',
    role: 'Head of Revenue Operations',
    headline: 'Replaced four tools and a spreadsheet with one workspace',
    stats: [
      { label: 'Tools consolidated', value: '4 → 1' },
      { label: 'Time to first report', value: '-62%' },
      { label: 'CRM data accuracy', value: '+34%' },
    ],
    quote:
      'We replaced four tools and a spreadsheet with Nuxtron. Our team finally works from one source of truth instead of reconciling exports every Monday.',
  },
  {
    company: 'Regional e-commerce brand',
    role: 'Director of Marketing',
    headline: 'Caught an AI-visibility gap traditional rank tracking missed',
    stats: [
      { label: 'AI citation share', value: '+41%' },
      { label: 'Organic assisted revenue', value: '+18%' },
      { label: 'Content briefs shipped/mo', value: '3x' },
    ],
    quote:
      'Our keyword rankings looked fine, but AEO tracking showed we were nearly invisible in AI answer engines. Fixing that moved revenue traditional SEO tools never would have flagged.',
  },
  {
    company: 'B2B services agency',
    role: 'Founder',
    headline: 'Runs every client workspace from one tenant-isolated platform',
    stats: [
      { label: 'Client workspaces', value: '22' },
      { label: 'Onboarding time per client', value: '-70%' },
      { label: 'Security review pass rate', value: '100%' },
    ],
    quote:
      'Tenant isolation was the deciding factor — we needed to prove to every client that their data couldn\'t leak into another account\'s workspace, and Nuxtron\'s architecture made that an easy answer.',
  },
];

function StaggeredStudy({ study, index }: { study: typeof STUDIES[0]; index: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: index * 0.1 }}
      className="mk-card p-8 sm:p-10 group"
    >
      <p className="text-xs font-bold uppercase tracking-widest text-[#0c8fcc]">{study.company}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#0b1b2b] sm:text-3xl">{study.headline}</h2>

      <div className="mt-6 grid grid-cols-3 gap-4 border-y border-[#dbe6ee] py-6">
        {study.stats.map((stat) => (
          <div key={stat.label} className="transition-all duration-300 group-hover:scale-105 group-hover:text-[#0ea5e9]">
            <div className="flex items-center gap-1.5 text-2xl font-bold text-[#0ea5e9]">
              <TrendingUp size={18} className="text-[#f59e0b]" aria-hidden="true" />
              {stat.value}
            </div>
            <p className="mt-1 text-xs text-[#8595a8]">{stat.label}</p>
          </div>
        ))}
      </div>

      <blockquote className="mt-6 text-lg leading-relaxed text-[#33475b]">
        &ldquo;{study.quote}&rdquo;
      </blockquote>
      <p className="mt-4 text-sm font-semibold text-[#8595a8]">{study.role}</p>
    </motion.article>
  );
}

export default function CaseStudiesClient() {
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
          <span className="mk-eyebrow mb-5">Case studies</span>
          <h1 className="text-5xl font-semibold tracking-tight text-[#0b1b2b] sm:text-6xl">
            Teams running on Nuxtron
          </h1>
          <p className="mt-5 text-lg text-[#55677c]">
            A look at how growth and security teams use Nuxtron to consolidate tools, catch what other platforms
            miss, and move faster with AI agents doing real work.
          </p>
        </motion.div>
      </section>

      <section className="mk-section mk-pt-flush">
        <div className="mk-container max-w-4xl space-y-8">
          {STUDIES.map((study, index) => (
            <StaggeredStudy key={study.headline} study={study} index={index} />
          ))}
        </div>
      </section>

      <section className="mk-section text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="mk-container max-w-2xl"
        >
          <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">Want results like these?</h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta group">
              Start free <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/contact" className="mk-btn-secondary group">
              Talk to sales <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}