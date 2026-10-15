"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { getProviderMark } from "@/app/lib/provider-marks";
import { ProviderLogo } from "@/app/components/marketing/provider-logo";

const CATEGORIES = [
  {
    title: "Social & content",
    items: [
      "Instagram",
      "TikTok",
      "YouTube",
      "X (Twitter)",
      "LinkedIn",
      "Facebook",
    ],
  },
  {
    title: "Search & AI visibility",
    items: [
      "Google Search Console",
      "Google Business Profile",
      "Bing Webmaster",
      "ChatGPT / AEO citations",
    ],
  },
  {
    title: "CRM & revenue",
    items: ["HubSpot", "Salesforce", "Stripe", "QuickBooks"],
  },
  {
    title: "Communication & support",
    items: ["Slack", "Gmail", "Outlook", "Twilio", "Zendesk"],
  },
  {
    title: "Security & infrastructure",
    items: ["SAML SSO", "SIEM webhook export", "Audit-log export (S3/GCS)"],
  },
];

function StaggeredCategory({
  category,
  index,
}: {
  category: (typeof CATEGORIES)[0];
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{
        duration: 0.5,
        ease: [0.16, 1, 0.3, 1],
        delay: index * 0.08,
      }}
      className="mk-card p-8 group"
    >
      <h2 className="mb-4 text-lg font-semibold text-info-ink">
        {category.title}
      </h2>
      <ul className="flex flex-wrap gap-2">
        {category.items.map((item) => (
          <li
            key={item}
            title={item}
            className={
              getProviderMark(item)
                ? "grid h-11 w-11 place-items-center rounded-2xl border border-line-soft bg-surface transition-colors duration-300 group-hover:border-info group-hover:bg-info/10"
                : "rounded-full border border-line-soft bg-surface px-3 py-1.5 text-sm text-info-ink transition-colors duration-300 group-hover:border-info group-hover:bg-info/10 group-hover:text-info-ink"
            }
          >
            <ProviderLogo label={item} />
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

export default function IntegrationsClient() {
  return (
    <>
      <section className="mk-section mk-pt-hero text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="mk-container max-w-2xl"
        >
          <span className="mk-eyebrow mb-5">Integrations</span>
          <h1 className="text-5xl font-semibold tracking-tight text-info-ink sm:text-6xl">
            Connects to the tools you already run
          </h1>
          <p className="mt-5 text-lg text-info-ink">
            Nuxtron plugs into your social channels, search consoles, CRM, and
            support stack — so switching to one workspace doesn&apos;t mean
            ripping anything else out.
          </p>
        </motion.div>
      </section>

      <section className="mk-section mk-pt-flush">
        <p className="mk-container mb-5 text-center text-xs text-info-ink">
          Provider marks identify the tools listed; each mark belongs to its
          respective owner. No endorsement is implied.
        </p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="mk-container grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 stagger-children"
        >
          {CATEGORIES.map((category, index) => (
            <StaggeredCategory
              key={category.title}
              category={category}
              index={index}
            />
          ))}
        </motion.div>
      </section>

      <section className="mk-section text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="mk-container max-w-2xl"
        >
          <h2 className="text-4xl font-semibold tracking-tight text-info-ink sm:text-5xl">
            Don&apos;t see what you need?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-info-ink">
            Enterprise plans include full API access and custom connector
            support.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/contact" className="mk-shiny-cta group">
              Request an integration{" "}
              <ArrowRight
                size={16}
                className="transition-transform group-hover:translate-x-1"
              />
            </Link>
            <Link href="/pricing" className="mk-btn-secondary group">
              View pricing{" "}
              <ArrowRight
                size={16}
                className="transition-transform group-hover:translate-x-1"
              />
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}
