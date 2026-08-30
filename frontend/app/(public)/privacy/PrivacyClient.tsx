'use client';

import { motion } from 'framer-motion';

const SECTIONS = [
  {
    title: '1. Information we collect',
    body: 'We collect account information you provide directly (name, email, company), data you connect from third-party platforms (social accounts, CRM records, search console data), and usage data about how you interact with Nuxtron.',
  },
  {
    title: '2. How we use your information',
    body: 'We use your data to operate and improve the platform, to power the features you enable (scheduling, analytics, AI agent actions), to communicate with you about your account, and to maintain security and prevent abuse.',
  },
  {
    title: '3. Data isolation between tenants',
    body: 'Your workspace data is logically isolated from every other tenant on Nuxtron, enforced at the database layer. We do not use your data to train models shared across other customers.',
  },
  {
    title: '4. Third-party sharing',
    body: 'We share data with subprocessors only as needed to provide the service (hosting, email delivery, payment processing) under contractual data-protection terms. We do not sell your data.',
  },
  {
    title: '5. Data retention',
    body: 'We retain your data for as long as your account is active. You may request deletion of your account and associated data at any time by contacting us.',
  },
  {
    title: '6. Your rights',
    body: 'Depending on your jurisdiction, you may have rights to access, correct, export, or delete your personal data. Contact privacy@nuxtron.app to exercise these rights.',
  },
  {
    title: '7. Security',
    body: 'We use field-level encryption for sensitive data, role-based access control, and audit logging. See our Trust & Security page for details.',
  },
  {
    title: '8. Changes to this policy',
    body: 'We will notify active accounts by email of material changes to this policy before they take effect.',
  },
];

function StaggeredSection({ section, index }: { section: typeof SECTIONS[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 }}
    >
      <h2 className="mb-2.5 text-lg font-semibold text-[#181818]">{section.title}</h2>
      <p className="text-[15px] leading-relaxed text-[#46484d]">{section.body}</p>
    </motion.div>
  );
}

export default function PrivacyClient() {
  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="mk-eyebrow mb-5">Legal</span>
          <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">Privacy Policy</h1>
          <p className="mb-12 text-sm text-[#8a8d93]">Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="space-y-10 stagger-children"
        >
          {SECTIONS.map((section, index) => (
            <StaggeredSection key={section.title} section={section} index={index} />
          ))}
        </motion.div>

        <p className="mt-14 border-t border-[#18181814] pt-8 text-sm text-[#8a8d93]">
          Questions about this policy? Contact us at{' '}
          <a href="mailto:privacy@nuxtron.app" className="text-[#466cf3] hover:underline">
            privacy@nuxtron.app
          </a>
          .
        </p>
      </div>
    </section>
  );
}