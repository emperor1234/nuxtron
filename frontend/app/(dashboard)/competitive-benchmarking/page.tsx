'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Profile = { id: number; name: string; network: string; handle: string; snapshot_count: number };
type CompetitorEntry = {
  profile: Profile;
  latest_snapshot: { followers: number; engagement_rate: number; estimated_mentions: number } | null;
};
type SOV = { brand: string; estimated_mentions: number; share_pct: number };
type ScrapeJob = {
  id: number;
  network: string;
  trigger: string;
  status: string;
  generated_snapshots: number;
  created_at: string;
};

export default function CompetitiveBenchmarkingPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [report, setReport] = useState<CompetitorEntry[]>([]);
  const [sov, setSov] = useState<SOV[]>([]);
  const [scrapeJobs, setScrapeJobs] = useState<ScrapeJob[]>([]);
  const [name, setName] = useState('Competitor A');
  const [network, setNetwork] = useState('linkedin');
  const [handle, setHandle] = useState('competitor-a');
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [followers, setFollowers] = useState('10000');
  const [engagementRate, setEngagementRate] = useState('2.4');
  const [mentions, setMentions] = useState('200');
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const [profilesRes, reportRes, sovRes] = await Promise.all([
        apiGet<{ profiles: Profile[] }>('/competitive/profiles', tenantId),
        apiGet<{ competitors: CompetitorEntry[] }>('/competitive/report', tenantId),
        apiGet<{ breakdown: SOV[] }>('/competitive/share-of-voice', tenantId),
      ]);
      const jobsRes = await apiGet<{ jobs: ScrapeJob[] }>('/competitive/scrape/jobs?limit=10', tenantId);
      setProfiles(profilesRes.profiles ?? []);
      setReport(reportRes.competitors ?? []);
      setSov(sovRes.breakdown ?? []);
      setScrapeJobs(jobsRes.jobs ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load competitive data');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addProfile() {
    try {
      await apiSend('/competitive/profiles', 'POST', { name, network, handle }, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Add profile failed');
    }
  }

  async function addSnapshot() {
    if (!selectedProfileId) return;
    try {
      await apiSend(
        `/competitive/profiles/${selectedProfileId}/snapshots`,
        'POST',
        {
          followers: Number.parseInt(followers, 10) || 0,
          engagement_rate: Number.parseFloat(engagementRate) || 0,
          estimated_mentions: Number.parseInt(mentions, 10) || 0,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Snapshot add failed');
    }
  }

  async function addOwnSnapshot() {
    try {
      await apiSend(
        '/competitive/own-profile',
        'POST',
        {
          network,
          followers: Number.parseInt(followers, 10) || 0,
          engagement_rate: Number.parseFloat(engagementRate) || 0,
          estimated_mentions: Number.parseInt(mentions, 10) || 0,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Own profile snapshot failed');
    }
  }

  async function runScraper() {
    try {
      await apiSend('/competitive/scrape/jobs', 'POST', { network, trigger: 'manual' }, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scraper run failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Competitive Benchmarking</h1>
        <p style={{ color: 'var(--muted)' }}>
          Track competitor profiles, snapshots, side-by-side comparison, and share of voice.
        </p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Add Competitor</h3>
            <input style={input} value={name} onChange={(e) => setName(e.target.value)} placeholder="name" />
            <select style={input} value={network} onChange={(e) => setNetwork(e.target.value)}>
              <option value="linkedin">linkedin</option>
              <option value="x">x</option>
              <option value="instagram">instagram</option>
              <option value="facebook">facebook</option>
              <option value="youtube">youtube</option>
            </select>
            <input style={input} value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="handle" />
            <button
              onClick={() => void addProfile()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
                marginBottom: 10,
              }}
            >
              Add Profile
            </button>
            <h3>Record Snapshot</h3>
            <select style={input} value={selectedProfileId} onChange={(e) => setSelectedProfileId(e.target.value)}>
              <option value="">Select competitor</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.network})
                </option>
              ))}
            </select>
            <input
              style={input}
              type="number"
              value={followers}
              onChange={(e) => setFollowers(e.target.value)}
              placeholder="followers"
            />
            <input
              style={input}
              type="number"
              value={engagementRate}
              onChange={(e) => setEngagementRate(e.target.value)}
              placeholder="engagement %"
            />
            <input
              style={input}
              type="number"
              value={mentions}
              onChange={(e) => setMentions(e.target.value)}
              placeholder="mentions"
            />
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => void addSnapshot()}
                style={{
                  padding: '8px 12px',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                }}
              >
                Add Competitor Snapshot
              </button>
              <button
                onClick={() => void addOwnSnapshot()}
                style={{
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: 8,
                  background: 'var(--brand)',
                  color: '#00101e',
                  fontWeight: 700,
                }}
              >
                Add Own Snapshot
              </button>
            </div>
            <h3>Automated Scraping</h3>
            <button
              onClick={() => void runScraper()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Run Competitor Scraper
            </button>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Competitor Report ({report.length})</h3>
            {report.map((r) => (
              <div key={r.profile.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <div style={{ fontWeight: 700 }}>
                  {r.profile.name} · {r.profile.network} · @{r.profile.handle}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  Followers: {r.latest_snapshot?.followers ?? 0} · Engagement: {r.latest_snapshot?.engagement_rate ?? 0}
                  % · Mentions: {r.latest_snapshot?.estimated_mentions ?? 0}
                </div>
              </div>
            ))}
            <h4>Share of Voice</h4>
            {sov.map((row) => (
              <div key={row.brand} style={{ borderBottom: '1px solid var(--line)', padding: '6px 0' }}>
                {row.brand}: {row.share_pct}% ({row.estimated_mentions} mentions)
              </div>
            ))}
            <h4>Recent Scrape Jobs</h4>
            {scrapeJobs.map((job) => (
              <div
                key={job.id}
                style={{ borderBottom: '1px solid var(--line)', padding: '6px 0', fontSize: 12, color: 'var(--muted)' }}
              >
                #{job.id} · {job.status} · {job.network} · {job.generated_snapshots} snapshots ·{' '}
                {new Date(job.created_at).toLocaleString()}
              </div>
            ))}
          </section>
        </div>
      </div>
    </main>
  );
}
