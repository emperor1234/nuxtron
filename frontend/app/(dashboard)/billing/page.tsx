'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Page, PageHeader, Card, CardTitle, Button, Badge, Stat, StatGrid, Field } from '../_ui/kit';

type Plan = { id: string; display: string; price_monthly: number; price_annual: number; ai_credits: number };

type Usage = { credit_balance: number; current_plan: string; plan_display: string; pending_credit_topups?: number };

type Invoice = {
  id: number;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  payment_reference?: string;
};

type Quote = { credits: number; total_usd: number; unit_price_usd: number };

type Checkout = { id: number; amount: number; payment_reference: string; status: string };

const selectStyle: React.CSSProperties = {
  height: 38,
  width: '100%',
  padding: '0 12px',
  border: '1px solid var(--nx-border)',
  borderRadius: 10,
  background: 'var(--nx-card)',
  color: 'var(--nx-ink)',
  fontFamily: 'inherit',
  fontSize: 13.5,
};

export default function BillingPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [planId, setPlanId] = useState('pro');
  const [cycle, setCycle] = useState<'monthly' | 'annual'>('monthly');
  const [credits, setCredits] = useState('1000');
  const [quote, setQuote] = useState<Quote | null>(null);
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  async function load() {
    try {
      setError('');
      const [plansRes, usageRes, invoicesRes] = await Promise.all([
        apiGet<{ plans: Plan[] }>('/billing/plans', tenantId),
        apiGet<Usage & { status: string }>('/billing/usage', tenantId),
        apiGet<{ invoices: Invoice[] }>('/billing/invoices', tenantId),
      ]);
      setPlans(plansRes.plans ?? []);
      setUsage(usageRes);
      setInvoices(invoicesRes.invoices ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load billing');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function subscribe() {
    try {
      await apiSend('/billing/subscribe', 'POST', { plan_id: planId, billing_cycle: cycle, payment_method_id: 'manual-dev' }, tenantId);
      setStatus('Subscription updated.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Subscribe failed');
    }
  }

  async function quoteCredits() {
    try {
      setError('');
      setStatus('');
      const response = await apiSend<{ quote: Quote }>(
        '/billing/credits/quote',
        'POST',
        { amount: Number.parseInt(credits, 10) || 0 },
        tenantId
      );
      setQuote(response.quote);
      setStatus(`Quote ready for ${response.quote.credits} credits.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Credit quote failed');
    }
  }

  async function createCheckout() {
    try {
      setError('');
      setStatus('');
      const response = await apiSend<{ invoice: Checkout }>(
        '/billing/credits/checkout',
        'POST',
        { amount: Number.parseInt(credits, 10) || 0, payment_provider: 'manual', payment_method_id: 'billing-center-topup' },
        tenantId
      );
      setCheckout(response.invoice);
      setStatus(`Pending checkout created: ${response.invoice.payment_reference}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Credit checkout failed');
    }
  }

  async function confirmCredits() {
    if (!checkout) return;
    try {
      setError('');
      setStatus('');
      await apiSend(
        '/billing/credits/confirm',
        'POST',
        {
          invoice_id: checkout.id,
          payment_reference: checkout.payment_reference,
          provider_transaction_id: `billing-center-${checkout.id}`,
          amount_usd: checkout.amount,
        },
        tenantId
      );
      setCheckout(null);
      setStatus('Payment confirmed and credits applied.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Credit confirmation failed');
    }
  }

  return (
    <Page>
      <PageHeader title="Billing Center" subtitle="Plan subscriptions, credits, and invoice audit trail." />

      {error || status ? (
        <Card>
          <Badge tone={error ? 'danger' : 'success'}>{error || status}</Badge>
        </Card>
      ) : null}

      <StatGrid>
        <Stat label="Current Plan" value={usage?.plan_display ?? '—'} />
        <Stat label="Plan ID" value={usage?.current_plan ?? '—'} />
        <Stat label="AI Credits" value={usage?.credit_balance ?? 0} />
        <Stat label="Pending Top-ups" value={usage?.pending_credit_topups ?? 0} />
      </StatGrid>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 'var(--nx-gap)' }}>
        <Card>
          <CardTitle>Subscription Actions</CardTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
            <select value={planId} onChange={(e) => setPlanId(e.target.value)} style={selectStyle} aria-label="Plan">
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display} ({p.id})
                </option>
              ))}
            </select>
            <select value={cycle} onChange={(e) => setCycle(e.target.value as 'monthly' | 'annual')} style={selectStyle} aria-label="Billing cycle">
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
            </select>
            <Button variant="primary" onClick={() => void subscribe()}>
              Subscribe / Switch
            </Button>
            <Field label="Credits" type="number" min={1} value={credits} onChange={(e) => setCredits(e.target.value)} />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button onClick={() => void quoteCredits()}>Quote Credits</Button>
              <Button onClick={() => void createCheckout()}>Create Checkout</Button>
              <Button variant="primary" onClick={() => void confirmCredits()} disabled={!checkout}>
                Confirm Payment
              </Button>
            </div>
            {quote ? (
              <p style={{ fontSize: 12, color: 'var(--nx-muted)', margin: 0 }}>
                Quote: {quote.credits} credits for ${quote.total_usd.toFixed(2)} at ${quote.unit_price_usd.toFixed(2)}/credit.
              </p>
            ) : null}
            {checkout ? (
              <p style={{ fontSize: 12, color: 'var(--nx-muted)', margin: 0 }}>
                Pending invoice #{checkout.id} · {checkout.payment_reference} · ${checkout.amount.toFixed(2)}
              </p>
            ) : null}
          </div>
        </Card>

        <Card>
          <CardTitle>Plan Catalog</CardTitle>
          <div style={{ marginTop: 8 }}>
            {plans.map((p) => (
              <div key={p.id} style={{ borderBottom: '1px solid var(--nx-border-soft)', padding: '10px 0' }}>
                <div style={{ fontWeight: 700 }}>{p.display}</div>
                <div style={{ fontSize: 12, color: 'var(--nx-muted)' }}>
                  ${p.price_monthly}/mo · ${p.price_annual}/yr-month equiv · {p.ai_credits} credits
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>Invoices ({invoices.length})</CardTitle>
        <div style={{ marginTop: 8 }}>
          {invoices.map((inv) => (
            <div key={inv.id} style={{ borderBottom: '1px solid var(--nx-border-soft)', padding: '10px 0' }}>
              <div style={{ fontWeight: 700 }}>
                Invoice #{inv.id} — {inv.status}
              </div>
              <div style={{ fontSize: 12, color: 'var(--nx-muted)' }}>
                {inv.amount} {inv.currency} · {new Date(inv.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </Page>
  );
}
