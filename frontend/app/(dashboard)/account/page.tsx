'use client';

import AccountNav from '@/app/components/account-nav';
import { useEffect, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

export default function AccountOverviewPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [plan, setPlan] = useState('Growth');
  const [credits, setCredits] = useState('0');
  const [orders, setOrders] = useState('0');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      setError('');
      try {
        const [usage, profile, orderData] = await Promise.all([
          apiGet('/billing/usage', tenantId),
          apiGet('/white-label/profile', tenantId),
          apiGet('/money-printers/commerce-pro/orders', tenantId),
        ]);
        if (!active) return;
        const rawPlan = usage.plan_display ?? usage.current_plan;
        const planText = typeof rawPlan === 'string' ? rawPlan : 'Starter';
        const rawCredits = usage.credit_balance;
        const creditsText = typeof rawCredits === 'number' || typeof rawCredits === 'string' ? String(rawCredits) : '0';
        const rawOrders = orderData.count;
        const ordersText = typeof rawOrders === 'number' || typeof rawOrders === 'string' ? String(rawOrders) : '0';
        const whiteLabel = profile.white_label as Record<string, unknown> | undefined;
        const whiteLabelProfile = whiteLabel?.profile as Record<string, unknown> | undefined;
        const rawStage = whiteLabelProfile?.stage;
        const stage = typeof rawStage === 'string' ? rawStage : 'foundation';

        setPlan(`${planText} (${stage})`);
        setCredits(creditsText);
        setOrders(ordersText);
      } catch (ex) {
        if (!active) return;
        setError(ex instanceof Error ? ex.message : 'Failed to load account overview.');
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [tenantId]);

  return (
    <main className="account-shell">
      <AccountNav />
      <section>
        <div className="hero">
          <p className="eyebrow">Account</p>
          <h1>Account Overview</h1>
          <p>Manage personal details, orders, credits wallet, and platform settings.</p>
          <label className="auth-form" style={{ maxWidth: 360 }}>
            <span>Tenant ID</span>
            <input value={tenantId} readOnly />
          </label>
          {error ? <p className="auth-errors">{error}</p> : null}
        </div>
        <div className="grid dashboard-kpis">
          <article className="card kpi-card">
            <p className="kpi-label">Current Plan</p>
            <h3>{plan}</h3>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Wallet Credits</p>
            <h3>{credits}</h3>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Open Orders</p>
            <h3>{orders}</h3>
          </article>
        </div>
      </section>
    </main>
  );
}
