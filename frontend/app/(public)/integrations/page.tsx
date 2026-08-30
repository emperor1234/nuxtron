import type { Metadata } from 'next';
import IntegrationsClient from './IntegrationsClient';

export const metadata: Metadata = {
  title: 'Integrations | Nuxtron',
  description:
    'Connect Nuxtron to the CRM, social, SEO, and communication tools your team already uses — Google, Meta, HubSpot, Slack, and more.',
  alternates: { canonical: '/integrations' },
};

export default function IntegrationsPage() {
  return <IntegrationsClient />;
}