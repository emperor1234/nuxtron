import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import FaqClient from './FaqClient';

export const metadata: Metadata = {
  title: 'FAQ | Nuxtron',
  description: 'Answers to common questions about Nuxtron: the platform, security, billing, and how the AI agents work.',
  alternates: { canonical: '/faq' },
};

const FAQ_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'What is Nuxtron, exactly?',
      acceptedAnswer: { '@type': 'Answer', text: 'Nuxtron is a single workspace that combines CRM, SEO & AI-visibility tracking, social media operations, review management, and security monitoring — with AI agents that can act across all of it, not just report on it.' },
    },
    {
      '@type': 'Question',
      name: 'Do I have to use every module?',
      acceptedAnswer: { '@type': 'Answer', text: 'No. Every module works independently — most teams start with one or two (usually CRM or social) and add more once the rest of the team sees the value of shared data.' },
    },
    {
      '@type': 'Question',
      name: 'What is the IRA agent?',
      acceptedAnswer: { '@type': 'Answer', text: 'IRA is Nuxtron\'s supervised autonomous agent. It plans and executes multi-step work across your connected modules — every action is logged, attributable, and reversible, and you control which actions require approval before they run.' },
    },
    {
      '@type': 'Question',
      name: 'What is AEO/GEO tracking?',
      acceptedAnswer: { '@type': 'Answer', text: 'Answer-Engine Optimization and Generative-Engine Optimization: tracking how AI answer engines like ChatGPT and Gemini cite and represent your brand, alongside traditional search-engine keyword rankings.' },
    },
    {
      '@type': 'Question',
      name: 'Is my data isolated from other tenants?',
      acceptedAnswer: { '@type': 'Answer', text: 'Yes — every query is scoped to your tenant and enforced at the database layer with row-level security, not just application logic. See our Trust & Security page for details.' },
    },
    {
      '@type': 'Question',
      name: 'Do you train AI models on my data?',
      acceptedAnswer: { '@type': 'Answer', text: 'No. We do not use your workspace data to train models shared across other customers.' },
    },
    {
      '@type': 'Question',
      name: 'How is sensitive data protected?',
      acceptedAnswer: { '@type': 'Answer', text: 'Sensitive fields use application-level encryption in addition to disk-level encryption at rest, and passwords are hashed with bcrypt or Argon2id plus a server-side pepper.' },
    },
    {
      '@type': 'Question',
      name: 'Is there a free plan?',
      acceptedAnswer: { '@type': 'Answer', text: 'Yes — the Starter plan is free for a single user with a smaller usage allowance, so you can try Nuxtron on real work before upgrading.' },
    },
    {
      '@type': 'Question',
      name: 'Can I cancel anytime?',
      acceptedAnswer: { '@type': 'Answer', text: 'Yes, from your billing settings at any time. Downgrades take effect at your next billing cycle; there is no cancellation fee.' },
    },
    {
      '@type': 'Question',
      name: 'Do you offer discounts for nonprofits or startups?',
      acceptedAnswer: { '@type': 'Answer', text: 'Yes — contact sales with details about your organization and we\'ll follow up with eligibility and pricing.' },
    },
  ],
};

export default function FaqPage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD) }} />
      <FaqClient />
    </>
  );
}