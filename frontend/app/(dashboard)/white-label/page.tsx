import { AiranklabFeatureShell } from '@/app/components/airanklab-feature-shell';

export default function WhiteLabelPage() {
  return (
    <AiranklabFeatureShell
      eyebrow="Agency"
      title="White-Label Reports"
      description="Agency-grade reporting is wired to live vendor report endpoints and verification APIs to support branded exports backed by real data."
      probes={[
        { label: 'Vendor report', path: '/search-everywhere/vendors/report' },
        { label: 'Report export csv', path: '/search-everywhere/vendors/report/export?format=csv' },
        { label: 'Verification', path: '/search-everywhere/airanklab/verification-report' },
      ]}
      links={[
        { href: '/studio/social-reports', label: 'Executive Reports' },
        { href: '/vendor-inventory-report', label: 'Vendor Inventory Report' },
        { href: '/pricing', label: 'Agency Pricing' },
      ]}
    />
  );
}
