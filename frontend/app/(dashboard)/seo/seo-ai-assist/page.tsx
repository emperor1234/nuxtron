import { VendorOpsPage } from '../components/vendor-ops/vendor-ops-page';
import { vendorSpec } from '../components/vendor-ops/vendor-registry';

export default function Page() {
  return <VendorOpsPage vendor={vendorSpec('seo-ai')} view="assist" />;
}
