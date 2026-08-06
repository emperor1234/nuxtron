'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

type LeaderboardItem = {
  tenant_id: string;
  successful_referrals: number;
  total_credits_earned: number;
};

export default function AffiliateDashboardPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [board, setBoard] = useState<LeaderboardItem[]>([]);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const response = await apiGet('/engagement/referrals/leaderboard', tenantId);
        const items = (response.leaderboard as LeaderboardItem[] | undefined) || [];
        if (active) setBoard(items);
      } catch (ex) {
        if (active) setError(ex instanceof Error ? ex.message : 'Failed to load leaderboard.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [tenantId]);

  const totals = useMemo(() => {
    const referrals = board.reduce((acc, item) => acc + Number(item.successful_referrals || 0), 0);
    const credits = board.reduce((acc, item) => acc + Number(item.total_credits_earned || 0), 0);
    return { referrals, credits };
  }, [board]);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Affiliate Dashboard</p>
        <h1>Partner Performance</h1>
        <p>Monitor clicks, referrals, conversion, and earnings.</p>
        <label className="auth-form" style={{ maxWidth: 360 }}>
          <span>Tenant ID</span>
          <input value={tenantId} readOnly />
        </label>
      </section>
      <section className="grid dashboard-kpis">
        <article className="card kpi-card">
          <p className="kpi-label">Top 10 Partners</p>
          <h3>{board.length}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Total Referrals</p>
          <h3>{totals.referrals}</h3>
        </article>
        <article className="card kpi-card">
          <p className="kpi-label">Credits Earned</p>
          <h3>{totals.credits}</h3>
        </article>
      </section>
      <section className="card" style={{ marginTop: 16 }}>
        <h3>Referral Leaderboard</h3>
        {loading ? <p className="muted">Loading leaderboard...</p> : null}
        {error ? <p className="auth-errors">{error}</p> : null}
        {!loading && !error ? (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Tenant</th>
                  <th>Successful Referrals</th>
                  <th>Total Credits Earned</th>
                </tr>
              </thead>
              <tbody>
                {board.map((item) => (
                  <tr key={item.tenant_id}>
                    <td>{item.tenant_id}</td>
                    <td>{item.successful_referrals}</td>
                    <td>{item.total_credits_earned}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
