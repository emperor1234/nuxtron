import { AiranklabFeatureShell } from '@/app/components/airanklab-feature-shell';

export default function SeoAeoGeoAuditToolPage() {
  return (
    <AiranklabFeatureShell
      eyebrow="Audit Core"
      title="SEO + AEO + GEO End-to-End Audit Tool"
      description="Runs live completion, readiness, and vendor verification APIs so this route reflects real automation wiring instead of static claims."
      probes={[
        { label: 'Airanklab completion chart', path: '/search-everywhere/airanklab/completion-chart' },
        { label: 'Airanklab verification report', path: '/search-everywhere/airanklab/verification-report' },
        { label: 'Wiring required keys', path: '/search-everywhere/airanklab/wiring/required-keys' },
        { label: 'Global readiness', path: '/search-everywhere/readiness' },
        { label: 'Unified vendor report', path: '/search-everywhere/vendors/report' },
      ]}
      links={[
        { href: '/airanklab/wiring', label: 'Provider Wiring Console' },
        { href: '/ai-search-impact-calculator', label: 'AI Search Impact Calculator' },
        { href: '/vendor-inventory-report', label: 'Vendor Inventory Report' },
        { href: '/ai-visibility-dashboard', label: 'AI Visibility Dashboard' },
      ]}
    />
  );
}
