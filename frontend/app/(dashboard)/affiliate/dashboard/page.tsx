'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Button, Card, CardTitle, DataStatus, Page, PageHeader, Stat, StatGrid, TableWrap } from '@/app/(dashboard)/_ui/kit';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

type LeaderboardItem = {
  tenant_id: string;
  successful_referrals: number;
  total_credits_earned: number;
  last_referral_at?: string;
};

function isPreviewResponse(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

function parseLeaderboard(value: unknown): LeaderboardItem[] | null {
  if (!Array.isArray(value)) return null;
  const rows: LeaderboardItem[] = [];
  for (const item of value) {
    if (!item || typeof item !== 'object') return null;
    const row = item as Record<string, unknown>;
    if (
      typeof row.tenant_id !== 'string' || !row.tenant_id.trim() ||
      typeof row.successful_referrals !== 'number' || !Number.isFinite(row.successful_referrals) || row.successful_referrals < 0 ||
      typeof row.total_credits_earned !== 'number' || !Number.isFinite(row.total_credits_earned) || row.total_credits_earned < 0
    ) return null;
    rows.push({
      tenant_id: row.tenant_id,
      successful_referrals: row.successful_referrals,
      total_credits_earned: row.total_credits_earned,
      last_referral_at: typeof row.last_referral_at === 'string' ? row.last_referral_at : undefined,
    });
  }
  return rows;
}

function formatDate(value?: string): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}

export default function AffiliateDashboardPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [board, setBoard] = useState<LeaderboardItem[] | null>(null);
  const [refresh, setRefresh] = useState(0);

  const load = useCallback(async (isActive: () => boolean) => {
    try {
      const response = await apiGet('/engagement/referrals/leaderboard', tenantId);
      if (!isActive()) return;
      if (isPreviewResponse(response)) throw new Error('Live referral leaderboard data is unavailable.');
      const rows = parseLeaderboard(response.leaderboard);
      if (!rows) throw new Error('The referral leaderboard returned incomplete data.');
      setBoard(rows);
      setError('');
    } catch (ex) {
      if (!isActive()) return;
      setError(ex instanceof Error ? ex.message : 'Failed to load leaderboard.');
    } finally {
      if (isActive()) setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    let active = true;
    window.queueMicrotask(() => {
      if (active) void load(() => active);
    });
    return () => {
      active = false;
    };
  }, [load, refresh]);

  const totals = board?.reduce((acc, item) => ({
    referrals: acc.referrals + item.successful_referrals,
    credits: acc.credits + item.total_credits_earned,
  }), { referrals: 0, credits: 0 });

  function retry() {
    setLoading(true);
    setError('');
    setBoard(null);
    setRefresh((value) => value + 1);
  }

  return (
    <Page>
      <PageHeader
        title="Partner Performance"
        subtitle="A platform-wide ranking by successful referrals and credits awarded."
      />
      {loading ? <p role="status" aria-live="polite">Loading referral leaderboard…</p> : !error ? <DataStatus state="live" /> : null}
      {error ? (
        <Card>
          <div role="alert" aria-live="assertive">
            <p>{error}</p>
            <Button onClick={retry}>Retry leaderboard</Button>
          </div>
        </Card>
      ) : null}
      <section aria-label="Leaderboard totals" aria-busy={loading}>
        <StatGrid>
          <Stat label="Partners listed" value={loading || error ? '—' : board?.length ?? '—'} />
          <Stat label="Successful referrals · leaderboard total" value={loading || error ? '—' : totals?.referrals ?? '—'} />
          <Stat label="Credits awarded · leaderboard total" value={loading || error ? '—' : totals?.credits ?? '—'} />
        </StatGrid>
      </section>
      <Card>
        <CardTitle>Referral leaderboard</CardTitle>
        <p className="muted">Totals below describe the listed partners as a group. They are not your personal earnings or conversion metrics.</p>
        {!loading && !error && board?.length === 0 ? (
          <div role="status" className="account-empty-state">
            <h2>No referral activity yet</h2>
            <p>Partner results will appear once referrals are recorded.</p>
            <Link href="/affiliate">Set up your referral link</Link>
          </div>
        ) : null}
        {!error && board && board.length > 0 ? (
          <TableWrap>
            <table>
              <caption className="sr-only">Up to ten partners ranked by referrals</caption>
              <thead>
                <tr>
                  <th scope="col">Rank</th>
                  <th scope="col">Successful referrals</th>
                  <th scope="col">Credits awarded</th>
                  <th scope="col">Last referral</th>
                </tr>
              </thead>
              <tbody>
                {board.map((item, index) => (
                  <tr key={item.tenant_id}>
                    <th scope="row">{index + 1}</th>
                    <td>{item.successful_referrals}</td>
                    <td>{item.total_credits_earned}</td>
                    <td>{formatDate(item.last_referral_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        ) : null}
      </Card>
      <p><Link href="/affiliate">Go to referral setup</Link></p>
    </Page>
  );
}
