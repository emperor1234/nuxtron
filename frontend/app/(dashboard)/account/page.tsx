'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import AccountNav from '@/app/components/account-nav';
import { Button } from '@/app/(dashboard)/_ui/kit';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

function isPreviewResponse(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

function displayValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return null;
}

export default function AccountOverviewPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [plan, setPlan] = useState<string | null>(null);
  const [credits, setCredits] = useState<string | null>(null);
  const [orders, setOrders] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState<string[]>([]);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      const results = await Promise.allSettled([
        apiGet('/billing/usage', tenantId),
        apiGet('/money-printers/commerce-pro/orders', tenantId),
      ]);
      if (!active) return;

      const failures: string[] = [];
      const usage = results[0].status === 'fulfilled' && !isPreviewResponse(results[0].value)
        ? results[0].value
        : null;
      const orderData = results[1].status === 'fulfilled' && !isPreviewResponse(results[1].value)
        ? results[1].value
        : null;
      const planValue = usage ? displayValue(usage.plan_display ?? usage.current_plan) : null;
      const creditsValue = usage ? displayValue(usage.credit_balance) : null;
      const ordersValue = orderData ? displayValue(orderData.count) : null;

      if (!usage) failures.push('Billing summary');
      else if (planValue === null || creditsValue === null) failures.push('Plan or credit details');
      if (!orderData) failures.push('Order activity');
      else if (ordersValue === null) failures.push('Order count');
      setPlan(planValue);
      setCredits(creditsValue);
      setOrders(ordersValue);
      setFailed(failures);
      setLoading(false);
    }
    void load();
    return () => {
      active = false;
    };
  }, [refresh, tenantId]);

  function retry() {
    setLoading(true);
    setFailed([]);
    setPlan(null);
    setCredits(null);
    setOrders(null);
    setRefresh((value) => value + 1);
  }

  return (
    <div className="account-shell">
      <AccountNav />
      <section aria-labelledby="account-overview-title">
        <header className="hero">
          <p className="eyebrow">Account</p>
          <h1 id="account-overview-title">Account Overview</h1>
          <p>Review your subscription and recent activity, then continue to the account task you need.</p>
        </header>

        {failed.length > 0 && !loading ? (
          <div className="auth-errors" role="status" aria-live="polite" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <span>{failed.join(' and ')} {failed.length === 1 ? 'is' : 'are'} unavailable. Other account data remains visible.</span>
            <Button onClick={retry}>Retry account data</Button>
          </div>
        ) : null}

        <div className="grid dashboard-kpis" aria-busy={loading}>
          <article className="card kpi-card">
            <p className="kpi-label">Current Plan</p>
            <h2>{loading ? 'Loading…' : plan ?? '—'}</h2>
            <Link href="/billing">View billing and plans</Link>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Available Credits</p>
            <h2>{loading ? 'Loading…' : credits ?? '—'}</h2>
            <Link href="/billing">Manage credits</Link>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Order Records</p>
            <h2>{loading ? 'Loading…' : orders ?? '—'}</h2>
            <Link href="/account/orders">View orders</Link>
          </article>
        </div>
        {loading ? <p role="status" aria-live="polite" className="muted">Loading account summary…</p> : null}
      </section>
    </div>
  );
}
