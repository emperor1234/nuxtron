'use client';

import AccountNav from '@/app/components/account-nav';
import { useEffect, useState } from 'react';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';

type Usage = { credit_balance: number; pending_credit_topups?: number };
type Wallet = { wallet?: { available_balance_usd?: number; recent_transactions?: unknown[] } };
type Quote = { credits: number; total_usd: number; unit_price_usd: number };
type Checkout = { id: number; amount: number; payment_reference: string; status: string };

export default function AccountWalletPage() {
  // Bound to the authenticated session; not user-editable (A01/IDOR).
  const [tenantId] = useState(resolveSessionTenant);
  const [credits, setCredits] = useState(0);
  const [balance, setBalance] = useState(0);
  const [txCount, setTxCount] = useState(0);
  const [pendingTopups, setPendingTopups] = useState(0);
  const [creditAmount, setCreditAmount] = useState('250');
  const [quote, setQuote] = useState<Quote | null>(null);
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function loadWallet(currentTenant: string) {
    const [usage, wallet] = await Promise.all([
      apiGet<Usage>('/billing/usage', currentTenant),
      apiGet<Wallet>('/money-printers/nuxtron-bank/wallet', currentTenant),
    ]);
    setCredits(Number(usage.credit_balance || 0));
    setPendingTopups(Number(usage.pending_credit_topups || 0));
    const walletObj = wallet.wallet || {};
    setBalance(Number(walletObj.available_balance_usd || 0));
    setTxCount((walletObj.recent_transactions || []).length);
  }

  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError('');
    loadWallet(tenantId).catch((ex) => {
      if (active) setError(ex instanceof Error ? ex.message : 'Failed to load wallet.');
    });
    return () => {
      active = false;
    };
  }, [tenantId]);

  async function quoteCredits() {
    setBusy(true);
    setError('');
    try {
      const response = await apiSend<{ quote: Quote }>(
        '/billing/credits/quote',
        'POST',
        { amount: Number.parseInt(creditAmount, 10) || 0 },
        tenantId
      );
      setQuote(response.quote);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not quote credits.');
    } finally {
      setBusy(false);
    }
  }

  async function createCheckout() {
    setBusy(true);
    setError('');
    try {
      const response = await apiSend<{ invoice: Checkout }>(
        '/billing/credits/checkout',
        'POST',
        {
          amount: Number.parseInt(creditAmount, 10) || 0,
          payment_provider: 'manual',
          payment_method_id: 'wallet-topup-ui',
        },
        tenantId
      );
      setCheckout(response.invoice);
      await loadWallet(tenantId);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not create checkout.');
    } finally {
      setBusy(false);
    }
  }

  async function confirmCredits() {
    if (!checkout) return;
    setBusy(true);
    setError('');
    try {
      await apiSend(
        '/billing/credits/confirm',
        'POST',
        {
          invoice_id: checkout.id,
          payment_reference: checkout.payment_reference,
          provider_transaction_id: `wallet-${checkout.id}`,
          amount_usd: checkout.amount,
        },
        tenantId
      );
      setCheckout(null);
      await loadWallet(tenantId);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not confirm payment.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="account-shell">
      <AccountNav />
      <section className="card">
        <h1>Wallet For Credits</h1>
        <p className="muted">Use credits for generation workloads and AI processing units.</p>
        <label className="auth-form" style={{ maxWidth: 360 }}>
          <span>Tenant ID</span>
          <input value={tenantId} readOnly />
        </label>
        {error ? <p className="auth-errors">{error}</p> : null}
        <div className="grid dashboard-kpis">
          <article className="card kpi-card">
            <p className="kpi-label">Available Credits</p>
            <h3>{credits}</h3>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Bank Wallet Balance (USD)</p>
            <h3>{balance.toFixed(2)}</h3>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Recent Transactions</p>
            <h3>{txCount}</h3>
          </article>
          <article className="card kpi-card">
            <p className="kpi-label">Pending Top-ups</p>
            <h3>{pendingTopups}</h3>
          </article>
        </div>
        <div style={{ maxWidth: 320, display: 'grid', gap: 10 }}>
          <input value={creditAmount} onChange={(e) => setCreditAmount(e.target.value)} type="number" min={1} />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={quoteCredits} disabled={busy}>
              {busy ? 'Working...' : 'Quote Credits'}
            </button>
            <button onClick={createCheckout} disabled={busy}>
              {busy ? 'Working...' : 'Create Checkout'}
            </button>
            <button onClick={confirmCredits} disabled={busy || !checkout}>
              {busy ? 'Working...' : 'Confirm Payment'}
            </button>
          </div>
          {quote ? (
            <p className="muted">
              Quote: {quote.credits} credits for ${quote.total_usd.toFixed(2)}.
            </p>
          ) : null}
          {checkout ? (
            <p className="muted">
              Pending: {checkout.payment_reference} · ${checkout.amount.toFixed(2)}
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
