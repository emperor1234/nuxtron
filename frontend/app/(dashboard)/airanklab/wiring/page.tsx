'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type RequiredKeysResponse = {
  status: string;
  wiring_contract: {
    required_keys: string[];
    optional_keys: string[];
    option_groups: Array<{ name: string; one_of: string[] }>;
    allowlist: string[];
  };
};

type ApplyResponse = {
  status: string;
  applied_keys: string[];
  rejected_keys: string[];
  summary: {
    implementation_pct: number;
    integration_configured_pct: number;
    parity_vendor_avg_integration_pct: number;
    production_grade_ready: boolean;
  };
};

function parseEnvLines(raw: string): Record<string, string> {
  const entries: Record<string, string> = {};
  const lines = raw.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    if (!key || !value) continue;
    entries[key] = value;
  }
  return entries;
}

export default function AiranklabWiringPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [required, setRequired] = useState<RequiredKeysResponse | null>(null);
  const [rawEnv, setRawEnv] = useState('');
  const [applyResult, setApplyResult] = useState<ApplyResponse | null>(null);

  const parsedCount = useMemo(() => Object.keys(parseEnvLines(rawEnv)).length, [rawEnv]);

  async function loadRequired() {
    setLoading(true);
    setError('');
    try {
      const payload = await apiGet<RequiredKeysResponse>('/search-everywhere/airanklab/wiring/required-keys', tenantId);
      setRequired(payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load required keys');
    } finally {
      setLoading(false);
    }
  }

  async function applyWiring() {
    setLoading(true);
    setError('');
    try {
      const values = parseEnvLines(rawEnv);
      const payload = await apiSend<ApplyResponse>(
        '/search-everywhere/airanklab/wiring/apply',
        'POST',
        { values },
        tenantId
      );
      setApplyResult(payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply wiring');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRequired();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Airanklab Wiring</p>
        <h1>Provider Contract Wiring Console</h1>
        <p>
          Paste runtime provider credentials as KEY=VALUE lines, apply them to the backend wiring contract, then verify
          production-grade readiness from completion and parity checks.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>Apply Runtime Contracts</h2>
        <p style={{ marginTop: 0, opacity: 0.82 }}>Accepted entries: {parsedCount}</p>
        <textarea
          value={rawEnv}
          onChange={(event) => setRawEnv(event.target.value)}
          placeholder="DATAFORSEO_LOGIN=...\nDATAFORSEO_API_KEY=...\nSERPER_API_KEY=..."
          rows={14}
          style={{
            width: '100%',
            borderRadius: 16,
            padding: 12,
            background: 'rgba(0,0,0,0.22)',
            color: 'inherit',
            border: '1px solid rgba(255,255,255,0.12)',
          }}
        />
        <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
          <button onClick={() => void applyWiring()} disabled={loading || parsedCount === 0}>
            {loading ? 'Applying...' : 'Apply Wiring'}
          </button>
          <button onClick={() => void loadRequired()} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh Required Keys'}
          </button>
        </div>
        {error ? <p style={{ color: '#fca5a5', marginTop: 10 }}>{error}</p> : null}
      </section>

      {applyResult ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Implementation</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{applyResult.summary.implementation_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Integration</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{applyResult.summary.integration_configured_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Parity Integration</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{applyResult.summary.parity_vendor_avg_integration_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Production Grade</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {applyResult.summary.production_grade_ready ? 'READY' : 'BLOCKED'}
            </p>
          </article>
        </section>
      ) : null}

      {required ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Required Keys</h3>
          <ul className="bullet-list">
            {required.wiring_contract.required_keys.map((key) => (
              <li key={key}>
                <strong>{key}</strong>
              </li>
            ))}
          </ul>
          <h4>Option Groups (one-of)</h4>
          <ul className="bullet-list">
            {required.wiring_contract.option_groups.map((group) => (
              <li key={group.name}>
                <strong>{group.name}</strong>: {group.one_of.join(', ')}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
