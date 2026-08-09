'use client';

import { useState } from 'react';
import Image from 'next/image';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Bot, Radar, Share2 } from 'lucide-react';

const TOOLS = [
  {
    key: 'agents',
    label: 'AI Agents',
    icon: Bot,
    title: 'Autonomous agents, reviewable by default',
    body: 'IRA plans multi-step work — drafting content, updating records, triaging alerts — and shows you exactly what it intends to do before it acts. Approve, edit, or auto-approve by rule.',
  },
  {
    key: 'seo',
    label: 'SEO & AI Visibility',
    icon: Radar,
    title: 'Track rankings and AI answer citations together',
    body: 'See classic search rankings next to how AI answer engines describe and cite your brand, so you know where visibility is actually coming from.',
  },
  {
    key: 'social',
    label: 'Social',
    icon: Share2,
    title: 'One calendar for every channel',
    body: 'Schedule, publish, and listen across your social accounts from a single shared calendar, with drafts your team can review before anything goes live.',
  },
] as const;

export function KeyToolsTabs() {
  const [active, setActive] = useState<(typeof TOOLS)[number]['key']>('agents');
  const current = TOOLS.find((t) => t.key === active) ?? TOOLS[0];
  const reduced = useReducedMotion();

  return (
    <div>
      <div
        role="tablist"
        aria-label="Key tools"
        className="mb-8 flex flex-wrap justify-center gap-2 rounded-full border border-[#18181814] bg-[#fafafa] p-1.5 mx-auto w-fit"
      >
        {TOOLS.map((tool) => (
          <button
            key={tool.key}
            type="button"
            role="tab"
            aria-selected={active === tool.key}
            onClick={() => setActive(tool.key)}
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors duration-200 ${
              active === tool.key ? 'bg-[#181818] text-white' : 'text-[#46484d] hover:text-[#181818]'
            }`}
          >
            <tool.icon size={15} aria-hidden="true" />
            {tool.label}
          </button>
        ))}
      </div>

      <div className="mk-card relative mx-auto grid max-w-4xl min-h-[19rem] grid-cols-1 items-center gap-8 overflow-hidden p-8 sm:p-10 md:grid-cols-2">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={current.key}
            initial={reduced ? undefined : { opacity: 0, y: 8 }}
            animate={reduced ? undefined : { opacity: 1, y: 0 }}
            exit={reduced ? undefined : { opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="mb-5 inline-flex w-fit rounded-lg border border-[#18181814] bg-[#466cf314] p-3 text-[#466cf3]">
              <current.icon size={22} strokeWidth={1.75} aria-hidden="true" />
            </div>
            <h3 className="mb-3 text-2xl font-semibold tracking-tight text-[#181818]">{current.title}</h3>
            <p className="text-[15px] leading-relaxed text-[#46484d]">{current.body}</p>
          </motion.div>
        </AnimatePresence>
        <div className="relative hidden overflow-hidden rounded-2xl border border-[#18181814] shadow-[0_16px_40px_rgba(24,24,24,0.1)] md:block" aria-hidden="true">
          <div className="flex items-center gap-1.5 border-b border-[#18181814] bg-[#fafafa] px-3 py-2.5">
            <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
            <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
            <span className="h-2 w-2 rounded-full bg-[#e5e7eb]" />
          </div>
          <Image
            src="/images/marketing-hub-mockup.png"
            alt=""
            width={1536}
            height={1024}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
}
