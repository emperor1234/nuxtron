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
  New: 'bg-info/10 text-info-ink border-info/30',
  Improved: 'bg-warning/10 text-warning-ink border-warning/30',
  Fixed: 'bg-info/10 text-info-ink border-info/25',
};

function StaggeredEntry({ entry, index }: { entry: Entry; index: number }) {
  return (
    <motion.li
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      className="relative border-l-2 border-line-soft pl-8 transition-colors duration-300 hover:border-info hover:pl-10"
    >
      <span
        className="absolute -left-[7px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-info"
        aria-hidden="true"
      />
      <p className="text-xs font-bold uppercase tracking-widest text-info">{entry.date}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <span
          className={`inline-block rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${TAG_STYLES[entry.tag]}`}
        >
          {entry.tag}
        </span>
        <h2 className="text-lg font-semibold text-info-ink">{entry.title}</h2>
      </div>
      <p className="mt-2 text-[15px] leading-relaxed text-info-ink">{entry.body}</p>
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
          <h1 className="mb-4 text-4xl font-semibold tracking-tight text-info-ink sm:text-5xl">What&apos;s new</h1>
          <p className="mb-12 text-lg leading-relaxed text-info-ink">
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