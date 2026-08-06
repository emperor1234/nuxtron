'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

type CapabilitiesResponse = {
  status: string;
  configured: boolean;
  capabilities: Array<{ capability: string; implemented: boolean }>;
  third_parties: {
    primary_graph_vendor: string;
    deployment_options: string[];
    cloud_partners: string[];
    ecosystem_integrations: string[];
  };
};

type VendorsResponse = {
  status: string;
  vendors: Array<{
    name: string;
    role: string;
    integration_mode: string;
  }>;
};

type ProbeResponse = {
  status: string;
  probe: {
    connected: boolean;
    ok: boolean;
    timestamp: string | null;
  };
};

export default function Neo4jIntegrationsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [vendors, setVendors] = useState<VendorsResponse | null>(null);
  const [probe, setProbe] = useState<ProbeResponse | null>(null);

  async function refreshIntegrations() {
    setLoading(true);
    setError('');
    try {
      const [capabilityData, vendorData] = await Promise.all([
        apiGet<CapabilitiesResponse>('/search-everywhere/neo4j/capabilities', tenantId),
        apiGet<VendorsResponse>('/search-everywhere/neo4j/vendors', tenantId),
      ]);
      setCapabilities(capabilityData);
      setVendors(vendorData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Neo4j integration state');
    } finally {
      setLoading(false);
    }
  }

  async function runProbe() {
    setLoading(true);
    setError('');
    try {
      const result = await apiGet<ProbeResponse>('/search-everywhere/neo4j/health/probe', tenantId);
      setProbe(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Neo4j probe failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshIntegrations();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Neo4j Integrations</p>
        <h1>Vendor Mapping and Connectivity Probe</h1>
        <p>
          Validate third-party graph integrations and run a live probe against the Neo4j backend connection. Use this
          surface to confirm cloud partner and connector coverage.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshIntegrations()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button onClick={() => void runProbe()} disabled={loading}>
            {loading ? 'Probing...' : 'Run Live Probe'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      {capabilities ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Configuration Snapshot</h3>
          <p>
            Runtime configured: <strong>{capabilities.configured ? 'YES' : 'NO'}</strong>
          </p>
          <ul className="bullet-list">
            {capabilities.capabilities.map((item) => (
              <li key={item.capability}>
                <strong>{item.capability}</strong> - {item.implemented ? 'implemented' : 'missing'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Cloud Partners</h3>
          <ul className="bullet-list">
            {(capabilities?.third_parties.cloud_partners ?? []).map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3 style={{ marginTop: 0 }}>Ecosystem Connectors</h3>
          <ul className="bullet-list">
            {(capabilities?.third_parties.ecosystem_integrations ?? []).map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3 style={{ marginTop: 0 }}>Live Probe</h3>
          {!probe ? (
            <p style={{ opacity: 0.8 }}>Probe not run yet.</p>
          ) : (
            <>
              <p>
                Connected: <strong>{probe.probe.connected ? 'YES' : 'NO'}</strong>
              </p>
              <p>
                Health: <strong>{probe.probe.ok ? 'OK' : 'FAILED'}</strong>
              </p>
              <p style={{ opacity: 0.8 }}>Timestamp: {probe.probe.timestamp ?? 'n/a'}</p>
            </>
          )}
        </article>
      </section>

      {vendors ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Vendors and Roles</h3>
          <ul className="bullet-list">
            {vendors.vendors.map((vendor) => (
              <li key={vendor.name + vendor.integration_mode}>
                <strong>{vendor.name}</strong> - {vendor.role} ({vendor.integration_mode})
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
