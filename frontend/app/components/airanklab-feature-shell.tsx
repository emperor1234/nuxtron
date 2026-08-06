'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { apiGet, DEFAULT_TENANT_ID } from '../lib/platform-api';

type ApiProbe = {
  label: string;
  path: string;
};

type ProbeStatus = {
  label: string;
  path: string;
  ok: boolean;
  detail: string;
};

type FeatureShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  probes: ApiProbe[];
  links: Array<{ href: string; label: string }>;
};

function toDetail(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return 'Live response received';
  const record = payload as Record<string, unknown>;
  const status = typeof record.status === 'string' ? record.status : 'ok';
  const generatedAt = typeof record.generated_at === 'string' ? ` at ${record.generated_at}` : '';
  return `${status}${generatedAt}`;
}

export function AiranklabFeatureShell({ eyebrow, title, description, probes, links }: FeatureShellProps) {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [probeStatus, setProbeStatus] = useState<ProbeStatus[]>([]);

  const total = probes.length;
  const successCount = useMemo(() => probeStatus.filter((row) => row.ok).length, [probeStatus]);
  const coveragePct = total > 0 ? Math.round((successCount / total) * 1000) / 10 : 0;

  async function runProbes() {
    setLoading(true);
    setError('');
    try {
      const rows = await Promise.all(
        probes.map(async (probe) => {
          try {
            const payload = await apiGet<Record<string, unknown>>(probe.path, tenantId);
            return {
              label: probe.label,
              path: probe.path,
              ok: true,
              detail: toDetail(payload),
            } satisfies ProbeStatus;
          } catch (e) {
            return {
              label: probe.label,
              path: probe.path,
              ok: false,
              detail: e instanceof Error ? e.message : 'Probe failed',
            } satisfies ProbeStatus;
          }
        })
      );
      setProbeStatus(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run live probes');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void runProbes();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 6 }}>Live Endpoint Coverage</h2>
            <p style={{ margin: 0, opacity: 0.8 }}>
              Verified now: {successCount}/{total} probes ({coveragePct}%).
            </p>
          </div>
          <button onClick={() => void runProbes()} disabled={loading}>
            {loading ? 'Checking...' : 'Re-check End-to-End'}
          </button>
        </div>
        {error ? <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p> : null}
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        {probeStatus.map((row) => (
          <article
            key={row.path}
            className="card"
            style={{ border: row.ok ? '1px solid rgba(52,211,153,0.45)' : '1px solid rgba(248,113,113,0.45)' }}
          >
            <h3 style={{ marginTop: 0 }}>{row.label}</h3>
            <p style={{ opacity: 0.8, marginTop: 0 }}>{row.path}</p>
            <p style={{ marginBottom: 0, color: row.ok ? '#86efac' : '#fca5a5' }}>{row.detail}</p>
          </article>
        ))}
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <h3 style={{ marginTop: 0 }}>Connected Workflows</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="button-secondary">
              {link.label}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
