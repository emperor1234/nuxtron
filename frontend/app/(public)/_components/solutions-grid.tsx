'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Bot, Building2, MessageSquareText, Plus, Radar, ShieldCheck, Share2 } from 'lucide-react';
import { Reveal } from './reveal';

const IMAGES = ['/images/sales-crm-mockup.png', '/images/marketing-hub-mockup.png'] as const;

const SOLUTIONS = [
  {
    key: 'crm',
    category: 'CRM',
    icon: Building2,
    title: 'Pipeline and deal tracking that everyone works from',
    body: 'Deals, contacts, and account activity live in one shared record — no more re-explaining context between sales, support, and marketing.',
  },
  {
    key: 'seo',
    category: 'SEO & AI Visibility',
    icon: Radar,
    title: 'Rank on search and get cited by AI answer engines',
    body: 'Track classic rankings next to AEO/GEO citations, so you know exactly where visibility is coming from and where it is slipping.',
  },
  {
    key: 'social',
    category: 'Social',
    icon: Share2,
    title: 'One calendar for every channel',
    body: 'Schedule, publish, and listen across your social accounts from a single shared calendar, with drafts your team can review first.',
  },
  {
    key: 'reviews',
    category: 'Reviews & Reputation',
    icon: MessageSquareText,
    title: 'Collect, respond to, and analyze reviews in one place',
    body: 'See every review across platforms, respond from the same workspace, and spot reputation trends before they become problems.',
  },
  {
    key: 'security',
    category: 'Security & SIEM',
    icon: ShieldCheck,
    title: 'Real-time threat detection with a full audit trail',
    body: 'Security monitoring lives in the same workspace as the work itself — every AI agent action is logged and reviewable alongside it.',
  },
  {
    key: 'agents',
    category: 'AI Agents',
    icon: Bot,
    title: 'Autonomous work, reviewable by default',
    body: 'IRA plans and executes multi-step work across the stack. Nothing runs unsupervised by default — approve, edit, or auto-approve by rule.',
  },
] as const;

export function SolutionsGrid() {
  const [open, setOpen] = useState<string | null>('crm');

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      {SOLUTIONS.map((solution, i) => {
        const isOpen = open === solution.key;
        const image = IMAGES[i % IMAGES.length];
        return (
          <Reveal key={solution.key} delay={i * 0.08} className="mk-card overflow-hidden p-8 sm:p-10">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="inline-flex w-fit shrink-0 rounded-lg border border-[#18181814] bg-[#466cf314] p-2.5 text-[#466cf3]">
                  <solution.icon size={20} strokeWidth={1.75} aria-hidden="true" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-widest text-[#466cf3]">
                    {solution.category}
                  </span>
                  <h3 className="mt-1 text-xl font-semibold leading-snug tracking-tight text-[#181818] sm:text-2xl">
                    {solution.title}
                  </h3>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : solution.key)}
                aria-expanded={isOpen}
                aria-label={isOpen ? `Collapse ${solution.category}` : `Expand ${solution.category}`}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-[#18181814] text-[#181818] transition-transform hover:bg-[#18181808]"
              >
                <Plus size={17} className={`transition-transform duration-300 ${isOpen ? 'rotate-45' : ''}`} aria-hidden="true" />
              </button>
            </div>

            <div
              className={`grid transition-all duration-300 ease-out ${isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}
            >
              <p className="overflow-hidden text-[15px] leading-relaxed text-[#46484d]">{solution.body}</p>
            </div>

            <div className={`overflow-hidden rounded-xl border border-[#18181814] ${isOpen ? 'mt-6' : ''}`}>
              <div className="flex items-center gap-1.5 border-b border-[#18181814] bg-[#fafafa] px-3.5 py-2.5">
                <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
                <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
                <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
              </div>
              <Image src={image} alt="" width={1536} height={1024} className="w-full" />
            </div>
          </Reveal>
        );
      })}
    </div>
  );
}
