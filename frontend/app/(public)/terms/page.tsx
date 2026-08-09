import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service | Nuxtron',
  description: 'The terms that govern your use of Nuxtron.',
  alternates: { canonical: '/terms' },
};

const SECTIONS = [
  {
    title: '1. Acceptance of terms',
    body: 'By creating a Nuxtron account or using the service, you agree to these terms. If you are using Nuxtron on behalf of an organization, you are agreeing on its behalf.',
  },
  {
    title: '2. Your account',
    body: 'You are responsible for maintaining the security of your account credentials and for all activity under your account. Notify us immediately of any unauthorized access.',
  },
  {
    title: '3. Acceptable use',
    body: 'You may not use Nuxtron to send spam, violate the terms of connected third-party platforms, attempt to access other tenants\' data, or use AI agent capabilities to take actions you are not authorized to take.',
  },
  {
    title: '4. AI agent actions',
    body: 'Nuxtron\'s AI agents act within the scope and approvals you configure. You are responsible for reviewing agent-proposed actions before they take effect where approval gates are enabled, and for the consequences of actions you authorize to run autonomously.',
  },
  {
    title: '5. Billing',
    body: 'Paid plans are billed in advance on a monthly or annual basis. Upgrades take effect immediately; downgrades take effect at the next billing cycle. Fees are non-refundable except as required by law.',
  },
  {
    title: '6. Data ownership',
    body: 'You retain ownership of the data you connect to and create in Nuxtron. We retain no rights to your data beyond what is necessary to provide the service.',
  },
  {
    title: '7. Termination',
    body: 'You may cancel your account at any time. We may suspend or terminate accounts that violate these terms or applicable law, with notice where reasonably possible.',
  },
  {
    title: '8. Disclaimers & limitation of liability',
    body: 'Nuxtron is provided "as is" without warranties of any kind. To the maximum extent permitted by law, our liability for any claim is limited to the amount you paid us in the preceding twelve months.',
  },
  {
    title: '9. Changes to these terms',
    body: 'We will notify active accounts of material changes before they take effect. Continued use of Nuxtron after changes take effect constitutes acceptance.',
  },
];

export default function TermsPage() {
  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <span className="mk-eyebrow mb-5">Legal</span>
        <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#181818] sm:text-5xl">Terms of Service</h1>
        <p className="mb-12 text-sm text-[#8a8d93]">Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>

        <div className="space-y-10">
          {SECTIONS.map((section) => (
            <div key={section.title}>
              <h2 className="mb-2.5 text-lg font-semibold text-[#181818]">{section.title}</h2>
              <p className="text-[15px] leading-relaxed text-[#46484d]">{section.body}</p>
            </div>
          ))}
        </div>

        <p className="mt-14 border-t border-[#18181814] pt-8 text-sm text-[#8a8d93]">
          Questions about these terms? Contact us at{' '}
          <a href="mailto:legal@nuxtron.app" className="text-[#466cf3] hover:underline">
            legal@nuxtron.app
          </a>
          .
        </p>
      </div>
    </section>
  );
}
