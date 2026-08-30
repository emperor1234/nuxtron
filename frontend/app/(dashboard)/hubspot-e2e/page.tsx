import { redirect } from 'next/navigation';

/**
 * The old route exposed internal implementation percentages and submitted
 * hard-coded placeholder provider credentials. HubSpot customer workflows live
 * in CRM; keep this URL as a safe compatibility redirect.
 */
export default function HubspotE2EPage() {
  redirect('/crm');
}
