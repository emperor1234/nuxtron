'use client';

import { useState } from 'react';

import { DEFAULT_TENANT_ID, apiSend } from '@/app/lib/platform-api';

type UpsertResponse = {
  status: string;
  tenant_id: string;
  nodes_upserted: number;
  relationships_upserted: number;
};

type QueryResponse = {
  status: string;
  row_count: number;
  rows: Array<Record<string, unknown>>;
};

type GraphRagResponse = {
  status: string;
  entity_node_id: string;
  count: number;
  context: Array<Record<string, unknown>>;
};

export default function Neo4jAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [upsertResult, setUpsertResult] = useState<UpsertResponse | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [graphragResult, setGraphragResult] = useState<GraphRagResponse | null>(null);

  async function runDemoUpsert() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<UpsertResponse>(
        '/search-everywhere/neo4j/knowledge-graph/upsert',
        'POST',
        {
          nodes: [
            {
              node_id: 'acct-demo-1',
              labels: ['Account', 'Organization'],
              properties: { name: 'Nuxtron', tier: 'enterprise' },
            },
            {
              node_id: 'case-demo-1',
              labels: ['Case', 'FraudSignal'],
              properties: { severity: 'high', confidence: 0.92 },
            },
          ],
          relationships: [
            {
              source_id: 'acct-demo-1',
              target_id: 'case-demo-1',
              rel_type: 'RELATED_TO',
              properties: { source: 'automation-ui' },
            },
          ],
        },
        tenantId
      );
      setUpsertResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upsert demo graph');
    } finally {
      setLoading(false);
    }
  }

  async function runCypherDemo() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<QueryResponse>(
        '/search-everywhere/neo4j/cypher/query',
        'POST',
        {
          query: 'RETURN $tenant_id AS tenant_id, datetime() AS run_at',
          params: {},
          mode: 'read',
          allow_write: false,
        },
        tenantId
      );
      setQueryResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Cypher query');
    } finally {
      setLoading(false);
    }
  }

  async function runGraphRagDemo() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<GraphRagResponse>(
        '/search-everywhere/neo4j/graphrag/context',
        'POST',
        {
          entity_node_id: 'acct-demo-1',
          max_hops: 2,
          max_neighbors: 25,
        },
        tenantId
      );
      setGraphragResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch GraphRAG context');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Neo4j Automation</p>
        <h1>Graph Upsert, Cypher, and GraphRAG</h1>
        <p>
          Trigger end-to-end graph automation flows against the Neo4j command center. This page calls real backend
          endpoints with tenant-aware request routing.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void runDemoUpsert()} disabled={loading}>
            {loading ? 'Running...' : 'Run Demo Upsert'}
          </button>
          <button onClick={() => void runCypherDemo()} disabled={loading}>
            {loading ? 'Running...' : 'Run Cypher Demo'}
          </button>
          <button onClick={() => void runGraphRagDemo()} disabled={loading}>
            {loading ? 'Running...' : 'Run GraphRAG Demo'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Knowledge Graph Upsert</h3>
          {!upsertResult ? (
            <p style={{ opacity: 0.8 }}>No upsert execution yet.</p>
          ) : (
            <>
              <p>
                Nodes: <strong>{upsertResult.nodes_upserted}</strong>
              </p>
              <p>
                Relationships: <strong>{upsertResult.relationships_upserted}</strong>
              </p>
            </>
          )}
        </article>

        <article className="card">
          <h3 style={{ marginTop: 0 }}>Cypher Query</h3>
          {!queryResult ? (
            <p style={{ opacity: 0.8 }}>No query executed yet.</p>
          ) : (
            <>
              <p>
                Row count: <strong>{queryResult.row_count}</strong>
              </p>
              <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto', fontSize: 12 }}>
                {JSON.stringify(queryResult.rows, null, 2)}
              </pre>
            </>
          )}
        </article>

        <article className="card">
          <h3 style={{ marginTop: 0 }}>GraphRAG Context</h3>
          {!graphragResult ? (
            <p style={{ opacity: 0.8 }}>No context loaded yet.</p>
          ) : (
            <>
              <p>
                Neighborhood size: <strong>{graphragResult.count}</strong>
              </p>
              <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto', fontSize: 12 }}>
                {JSON.stringify(graphragResult.context, null, 2)}
              </pre>
            </>
          )}
        </article>
      </section>
    </main>
  );
}
