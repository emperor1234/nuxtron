'use client';

import { motion } from 'framer-motion';

type Entry = {
  date: string;
  tag: 'New' | 'Improved' | 'Fixed';
  title: string;
  body: string;
};

const ENTRIES: Entry[] = [
  {
    date: 'August 2026',
    tag: 'New',
    title: 'AI answer-engine citation tracking (AEO/GEO)',
    body: 'Track how ChatGPT, Gemini, and other AI answer engines cite and represent your brand, alongside traditional keyword rankings.',
  },
  {
    date: 'August 2026',
    tag: 'New',
    title: 'Translation Studio',
    body: 'Glossary-aware, translation-memory-backed text and document translation, wired to live vendor providers.',
  },
  {
    date: 'July 2026',
    tag: 'Improved',
    title: 'IRA agent approval gates',
    body: 'Autonomous agent actions above a configurable risk threshold now require explicit human approval before they run.',
  },
  {
    date: 'July 2026',
    tag: 'Improved',
    title: 'Field-level encryption everywhere',
    body: 'Sensitive fields across CRM and social modules now use application-level encryption, not just disk-level encryption at rest.',
  },
  {
    date: 'June 2026',
    tag: 'New',
    title: 'Role-based access control (RBAC)',
    body: 'Assign granular roles per teammate — session tokens carry signed role claims verified independently by app and API layers.',
  },
  {
    date: 'June 2026',
    tag: 'Fixed',
    title: 'Social scheduling timezone handling',
    body: 'Scheduled posts now consistently resolve to the connected account\'s configured timezone across daylight-saving transitions.',
  },
  {
    date: 'May 2026',
    tag: 'New',
    title: 'SIEM audit-log export',
    body: 'Stream audit-grade event logs to your own SIEM or object storage for long-term retention and compliance review.',
  },
];

const TAG_STYLES: Record<Entry['tag'], string> = {
  New: 'bg-[#0ea5e9]/10 text-[#0c8fcc] border-[#0ea5e9]/30',
  Improved: 'bg-[#f59e0b]/10 text-[#b45309] border-[#f59e0b]/30',
  Fixed: 'bg-[#55677c]/10 text-[#33475b] border-[#55677c]/25',
};

function StaggeredEntry({ entry, index }: { entry: Entry; index: number }) {
  return (
    <motion.li
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      className="relative border-l-2 border-[#dbe6ee] pl-8 transition-all duration-300 hover:border-[#0ea5e9] hover:pl-10"
    >
      <span
        className="absolute -left-[7px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-[#0ea5e9]"
        aria-hidden="true"
      />
      <p className="text-xs font-bold uppercase tracking-widest text-[#8595a8]">{entry.date}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <span
          className={`inline-block rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${TAG_STYLES[entry.tag]}`}
        >
          {entry.tag}
        </span>
        <h2 className="text-lg font-semibold text-[#0b1b2b]">{entry.title}</h2>
      </div>
      <p className="mt-2 text-[15px] leading-relaxed text-[#55677c]">{entry.body}</p>
    </motion.li>
  );
}

export default function ChangelogClient() {
  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="mk-eyebrow mb-5">Changelog</span>
          <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">What&apos;s new</h1>
          <p className="mb-12 text-lg leading-relaxed text-[#55677c]">
            Notable features, improvements, and fixes as they ship — newest first.
          </p>
        </motion.div>

        <ol className="space-y-8 stagger-children">
          {ENTRIES.map((entry, index) => (
            <StaggeredEntry key={`${entry.date}-${entry.title}`} entry={entry} index={index} />
          ))}
        </ol>
      </div>
    </section>
  );
}