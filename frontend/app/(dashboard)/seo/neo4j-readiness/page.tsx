import { redirect } from 'next/navigation';

/**
 * Neo4j has a purpose-built connection health and capability workspace. The
 * former readiness screen exposed internal completion and release-gate data.
 */
export default function Neo4jReadinessPage() {
  redirect('/seo/neo4j-integrations');
}
