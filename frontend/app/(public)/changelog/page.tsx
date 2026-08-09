import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Changelog | Nuxtron',
  description: 'What shipped recently in Nuxtron — new features, improvements, and fixes across CRM, SEO, social, and security.',
  alternates: { canonical: '/changelog' },
};

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

export default function ChangelogPage() {
  return (
    <section className="mk-section pt-40">
      <div className="mk-container max-w-3xl">
        <span className="mk-eyebrow mb-5">Changelog</span>
        <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">What&apos;s new</h1>
        <p className="mb-12 text-lg leading-relaxed text-[#55677c]">
          Notable features, improvements, and fixes as they ship — newest first.
        </p>

        <ol className="space-y-8">
          {ENTRIES.map((entry) => (
            <li key={`${entry.date}-${entry.title}`} className="relative border-l-2 border-[#dbe6ee] pl-8">
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
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
