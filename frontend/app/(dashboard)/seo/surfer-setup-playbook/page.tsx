'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

type ProviderPlaybook = {
  provider: string;
  priority: 'P0' | 'P1' | 'P2';
  setup_notes: string[];
  preflight_commands_powershell: string[];
  verify_with: string[];
};

type SetupPlaybookResponse = {
  status: string;
  setup_playbook: {
    summary: {
      configured: number;
      total: number;
      integration_configured_pct: number;
    };
    providers: ProviderPlaybook[];
    final_validation: string[];
  };
};

export default function SurferSetupPlaybookPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<SetupPlaybookResponse | null>(null);

  async function loadPlaybook() {
    setLoading(true);
    setError('');
    try {
      const response = await apiGet<SetupPlaybookResponse>('/search-everywhere/surfer/setup-playbook', tenantId);
      setData(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load setup playbook');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPlaybook();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Surfer Readiness</p>
        <h1>Surfer Setup Playbook</h1>
        <p>Provider-level setup notes, PowerShell preflight commands, and verification steps.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <button onClick={() => void loadPlaybook()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      {data ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Providers</h3>
          <ul className="bullet-list">
            {data.setup_playbook.providers.map((provider) => (
              <li key={provider.provider}>
                <strong>{provider.priority}</strong> {provider.provider} - verify via {provider.verify_with.join(' + ')}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {data && data.setup_playbook.providers.length > 0 ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>First Provider Command Checklist</h3>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 13,
              background: 'rgba(0,0,0,0.35)',
              padding: 12,
              borderRadius: 12,
            }}
          >
            {data.setup_playbook.providers[0].preflight_commands_powershell.join('\n')}
          </pre>
        </section>
      ) : null}
    </main>
  );
}
