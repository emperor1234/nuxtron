import { redirect } from 'next/navigation';

/**
 * Provider secrets must be configured in the deployment secret manager, never
 * pasted into a browser form and forwarded through the application. Keep old
 * bookmarks working by routing to the customer-safe integrations workspace.
 */
export default function AiranklabWiringPage() {
  redirect('/seo/integrations-automation');
}
