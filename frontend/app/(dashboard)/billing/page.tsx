'use client';

import { useEffect, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';
import { apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, DataStatus, Field, Page, PageHeader, Stat, StatGrid, TableWrap } from '../_ui/kit';
import { requireStripeUrl } from './stripe-url';

type Plan = { id: string; display: string; price_monthly: number; price_annual: number; ai_credits: number };
type Usage = {
  credit_balance: number | null;
  current_plan: string | null;
  plan_display: string | null;
  pending_credit_topups: number | null;
  billing_cycle: string | null;
};
type Invoice = {
  id: number | string;
  amount: number | string;
  currency: string;
  status: string;
  created_at: string;
  payment_reference?: string;
};
type Quote = { credits: number; total_usd: number; unit_price_usd: number };
type Wallet = { balance: number | null; transactions: number | null };

function isPreviewResponse(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

function asFiniteNumber(value: unknown): number | null {
  const number = typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : Number.NaN;
  return Number.isFinite(number) ? number : null;
}

function parsePlans(value: unknown): Plan[] {
  if (!value || typeof value !== 'object' || isPreviewResponse(value)) throw new Error('Live plan data is unavailable.');
  const raw = (value as Record<string, unknown>).plans;
  if (!Array.isArray(raw)) throw new Error('The plan catalog returned incomplete data.');
  return raw.map((item) => {
    if (!item || typeof item !== 'object') throw new Error('The plan catalog returned an invalid entry.');
    const row = item as Record<string, unknown>;
    const monthly = asFiniteNumber(row.price_monthly);
    const annual = asFiniteNumber(row.price_annual);
    const credits = asFiniteNumber(row.ai_credits);
    if (typeof row.id !== 'string' || typeof row.display !== 'string' || monthly === null || annual === null || credits === null) {
      throw new Error('The plan catalog returned an invalid entry.');
    }
    return { id: row.id, display: row.display, price_monthly: monthly, price_annual: annual, ai_credits: credits };
  });
}

function parseUsage(value: unknown): Usage {
  if (!value || typeof value !== 'object' || isPreviewResponse(value)) throw new Error('Live subscription data is unavailable.');
  const row = value as Record<string, unknown>;
  const currentPlan = typeof row.current_plan === 'string' && row.current_plan.trim() ? row.current_plan.trim() : null;
  const planDisplay = typeof row.plan_display === 'string' && row.plan_display.trim() ? row.plan_display.trim() : null;
  const credits = asFiniteNumber(row.credit_balance);
  const pending = asFiniteNumber(row.pending_credit_topups);
  const billingCycle = typeof row.billing_cycle === 'string' && row.billing_cycle.trim() ? row.billing_cycle.trim() : null;
  if (!currentPlan && !planDisplay && credits === null) throw new Error('The billing summary returned incomplete data.');
  return { current_plan: currentPlan, plan_display: planDisplay, credit_balance: credits, pending_credit_topups: pending, billing_cycle: billingCycle };
}

function parseInvoices(value: unknown): Invoice[] {
  if (!value || typeof value !== 'object' || isPreviewResponse(value)) throw new Error('Live invoice data is unavailable.');
  const raw = (value as Record<string, unknown>).invoices;
  if (!Array.isArray(raw)) throw new Error('Invoice history returned incomplete data.');
  return raw.map((item) => {
    if (!item || typeof item !== 'object') throw new Error('Invoice history contains an incomplete record.');
    const row = item as Record<string, unknown>;
    if (!((typeof row.id === 'string' || typeof row.id === 'number') &&
      (typeof row.amount === 'string' || typeof row.amount === 'number') &&
      typeof row.currency === 'string' && typeof row.status === 'string' && typeof row.created_at === 'string')) {
      throw new Error('Invoice history contains an incomplete record.');
    }
    return row as Invoice;
  });
}

function formatMoney(amount: number | string, currency: string): string {
  const value = asFiniteNumber(amount);
  if (value === null) return '—';
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency.toUpperCase() }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}

function formatPlanPrice(amount: number, period: 'month' | 'year'): string {
  return amount < 0 ? 'Custom pricing' : `${formatMoney(amount, 'USD')}/${period}`;
}

function formatCredits(amount: number): string {
  return amount < 0 ? 'Custom allowance' : `${amount.toLocaleString()} AI credits`;
}

export default function BillingPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoiceAvailable, setInvoiceAvailable] = useState(false);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [walletError, setWalletError] = useState('');
  const [loading, setLoading] = useState(true);
  const [billingError, setBillingError] = useState('');
  const [invoiceError, setInvoiceError] = useState('');
  const [planId, setPlanId] = useState('');
  const [cycle, setCycle] = useState<'monthly' | 'annual'>('monthly');
  const [credits, setCredits] = useState('');
  const [quote, setQuote] = useState<Quote | null>(null);
  const [busy, setBusy] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      const results = await Promise.allSettled([
        apiGet('/billing/plans', tenantId),
        apiGet('/billing/usage', tenantId),
        apiGet('/billing/invoices', tenantId),
        apiGet('/money-printers/nuxtron-bank/wallet', tenantId),
      ]);
      if (!active) return;

      let requiredError = '';
      try {
        if (results[0].status === 'rejected') throw results[0].reason;
        setPlans(parsePlans(results[0].value));
      } catch (ex) {
        requiredError = ex instanceof Error ? ex.message : 'Plan data is unavailable.';
        setPlans([]);
      }
      try {
        if (results[1].status === 'rejected') throw results[1].reason;
        setUsage(parseUsage(results[1].value));
      } catch (ex) {
        requiredError = requiredError || (ex instanceof Error ? ex.message : 'Subscription data is unavailable.');
        setUsage(null);
      }
      setBillingError(requiredError);

      try {
        if (results[2].status === 'rejected') throw results[2].reason;
        setInvoices(parseInvoices(results[2].value));
        setInvoiceAvailable(true);
        setInvoiceError('');
      } catch (ex) {
        setInvoices([]);
        setInvoiceAvailable(false);
        setInvoiceError(ex instanceof Error ? ex.message : 'Invoice history is unavailable.');
      }

      try {
        if (results[3].status === 'rejected') throw results[3].reason;
        const payload = results[3].value as Record<string, unknown>;
        if (isPreviewResponse(payload)) throw new Error('Live wallet data is unavailable.');
        const details = payload.wallet && typeof payload.wallet === 'object' ? payload.wallet as Record<string, unknown> : {};
        const balance = asFiniteNumber(details.available_balance_usd);
        const transactions = Array.isArray(details.recent_transactions) ? details.recent_transactions.length : null;
        if (balance === null && transactions === null) throw new Error('Wallet response is incomplete.');
        setWallet({ balance, transactions });
        setWalletError('');
      } catch (ex) {
        setWallet(null);
        setWalletError(ex instanceof Error ? ex.message : 'Bank wallet data is unavailable.');
      }
      setLoading(false);
    }
    window.queueMicrotask(() => {
      if (active) void load();
    });
    return () => {
      active = false;
    };
  }, [refresh, tenantId]);

  const selectedPlan = plans.find((item) => item.id === planId) ?? null;
  const creditAmount = Number(credits);
  const validCreditAmount = Number.isSafeInteger(creditAmount) && creditAmount > 0 && creditAmount <= 1_000_000;
  const quoteMatches = Boolean(quote && validCreditAmount && quote.credits === creditAmount);
  const canManageSubscription = !loading && !billingError && Boolean(selectedPlan);
  const canOpenPortal = !loading && !billingError && Boolean(usage?.current_plan && usage.current_plan !== 'starter');

  async function subscribe() {
    if (!canManageSubscription || !selectedPlan) return;
    setBusy(true);
    setError('');
    setStatus('');
    try {
      if (planId === 'starter') {
        await apiSend('/billing/subscribe', 'POST', { plan_id: planId, billing_cycle: cycle }, tenantId);
        setStatus('Starter plan update confirmed.');
        setRefresh((value) => value + 1);
        return;
      }
      const response = await apiSend<{ checkout_url: string | null }>(
        '/billing/stripe/checkout-session',
        'POST',
        { plan_id: planId, billing_cycle: cycle, request_id: crypto.randomUUID().replaceAll('-', '') },
        tenantId
      );
      if (!response.checkout_url) throw new Error('Secure checkout is unavailable for this plan.');
      window.location.assign(requireStripeUrl(response.checkout_url, 'checkout.stripe.com'));
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Subscription action failed.');
    } finally {
      setBusy(false);
    }
  }

  async function quoteCredits() {
    if (!validCreditAmount) {
      setError('Enter a whole credit amount from 1 to 1,000,000.');
      return;
    }
    setQuoting(true);
    setError('');
    setStatus('');
    setQuote(null);
    try {
      const response = await apiSend<{ quote: Quote }>('/billing/credits/quote', 'POST', { amount: creditAmount }, tenantId);
      const result = response.quote;
      if (!result || result.credits !== creditAmount || !Number.isFinite(result.total_usd) || result.total_usd < 0 || !Number.isFinite(result.unit_price_usd) || result.unit_price_usd < 0) {
        throw new Error('The credit quote was incomplete. Please try again.');
      }
      setQuote(result);
      setStatus(`Quote ready: ${result.credits.toLocaleString()} credits for ${formatMoney(result.total_usd, 'USD')}.`);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Credit quote failed.');
    } finally {
      setQuoting(false);
    }
  }

  async function buyCredits() {
    if (!quoteMatches || !quote) {
      setError('Request a current quote before continuing to checkout.');
      return;
    }
    setBusy(true);
    setError('');
    setStatus('');
    try {
      const response = await apiSend<{ checkout_url: string }>('/billing/stripe/credit-checkout-session', 'POST', {
        credits: creditAmount,
        request_id: crypto.randomUUID().replaceAll('-', ''),
      }, tenantId);
      if (!response.checkout_url) throw new Error('Secure credit checkout is unavailable.');
      window.location.assign(requireStripeUrl(response.checkout_url, 'checkout.stripe.com'));
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Credit checkout failed.');
    } finally {
      setBusy(false);
    }
  }

  async function openPortal() {
    if (!canOpenPortal) return;
    setBusy(true);
    setError('');
    setStatus('');
    try {
      const response = await apiSend<{ portal_url: string }>('/billing/stripe/portal-session', 'POST', {}, tenantId);
      if (!response.portal_url) throw new Error('The billing portal is unavailable.');
      window.location.assign(requireStripeUrl(response.portal_url, 'billing.stripe.com'));
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not open the billing portal.');
    } finally {
      setBusy(false);
    }
  }

  function retry() {
    setLoading(true);
    setBillingError('');
    setInvoiceError('');
    setWalletError('');
    setError('');
    setStatus('');
    setPlans([]);
    setUsage(null);
    setInvoices([]);
    setInvoiceAvailable(false);
    setWallet(null);
    setQuote(null);
    setRefresh((value) => value + 1);
  }

  return (
    <Page>
      <PageHeader title="Billing & Credits" subtitle="Understand your subscription, manage credits, and review payment history." />
      {loading ? <p role="status" aria-live="polite">Loading billing information…</p> : <DataStatus state={billingError ? 'unavailable' : 'live'} provider="plan and subscription" />}
      {billingError ? (
        <Card>
          <div role="alert" aria-live="assertive">
            <p>{billingError}</p>
            <Button onClick={retry}>Retry billing data</Button>
          </div>
        </Card>
      ) : null}
      {error || status ? (
        <Card>
          {error ? <p role="alert" aria-live="assertive">{error}</p> : null}
          {status ? <p role="status" aria-live="polite">{status}</p> : null}
        </Card>
      ) : null}

      <section aria-label="Current billing summary" aria-busy={loading}>
        <StatGrid>
          <Stat label="Current plan" value={loading ? '…' : usage?.plan_display ?? '—'} />
          <Stat label="Billing cycle" value={loading ? '…' : usage?.billing_cycle ?? '—'} />
          <Stat label="Available AI credits" value={loading ? '…' : usage?.credit_balance ?? '—'} />
          <Stat label="Pending credit top-ups" value={loading ? '…' : usage?.pending_credit_topups ?? '—'} />
          <Stat label="Bank wallet balance" value={loading ? '…' : wallet?.balance === null || !wallet ? '—' : formatMoney(wallet.balance, 'USD')} />
          <Stat label="Recent wallet transactions" value={loading ? '…' : wallet?.transactions ?? '—'} />
        </StatGrid>
      </section>
      {walletError ? <p className="muted" role="status" aria-live="polite">Bank wallet data unavailable: {walletError}</p> : null}

      <div className="billing-actions-grid">
        <Card>
          <CardTitle>Subscription</CardTitle>
          <p className="muted">Choose a plan and billing cycle. Review the price below before opening secure checkout.</p>
          <div className="billing-form-stack">
            <label htmlFor="billing-plan">Plan</label>
            <select id="billing-plan" value={planId} onChange={(event) => setPlanId(event.target.value)} disabled={loading || Boolean(billingError) || plans.length === 0}>
              <option value="">Select a plan</option>
              {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.display}</option>)}
            </select>
            <label htmlFor="billing-cycle">Billing cycle</label>
            <select id="billing-cycle" value={cycle} onChange={(event) => setCycle(event.target.value as 'monthly' | 'annual')} disabled={loading || Boolean(billingError)}>
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
            </select>
            {selectedPlan ? (
              <p className="billing-price-review" aria-live="polite">
                Selected plan: <strong>{selectedPlan.display}</strong> · {cycle === 'monthly' ? formatPlanPrice(selectedPlan.price_monthly, 'month') : formatPlanPrice(selectedPlan.price_annual * 12, 'year')}
              </p>
            ) : <p className="muted">Select a plan to review its price.</p>}
            <Button variant="primary" onClick={() => void subscribe()} disabled={!canManageSubscription || busy}>
              {busy ? 'Opening secure checkout…' : selectedPlan?.id === 'starter' ? 'Choose Starter' : 'Continue to secure checkout'}
            </Button>
            <Button onClick={() => void openPortal()} disabled={!canOpenPortal || busy}>Manage subscription</Button>
          </div>
          {!loading && plans.length === 0 && !billingError ? <p role="status">No plans are available right now.</p> : null}
        </Card>

        <Card>
          <CardTitle>Buy credits</CardTitle>
          <p className="muted">Enter an amount, request a current quote, then review the total before continuing.</p>
          <div className="billing-form-stack">
            <Field
              id="billing-credit-amount"
              label="Credit amount"
              type="number"
              min={1}
              max={1_000_000}
              step={1}
              inputMode="numeric"
              autoComplete="off"
              value={credits}
              onChange={(event) => {
                setCredits(event.target.value);
                setQuote(null);
                setError('');
                setStatus('');
              }}
              disabled={loading || Boolean(billingError) || busy || quoting}
            />
            <Button onClick={() => void quoteCredits()} disabled={loading || Boolean(billingError) || !validCreditAmount || quoting || busy}>
              {quoting ? 'Getting quote…' : 'Get credit quote'}
            </Button>
            {quoteMatches && quote ? (
              <div className="billing-price-review" aria-label="Credit purchase quote">
                <strong>{quote.credits.toLocaleString()} credits</strong>
                <span>Unit price: {formatMoney(quote.unit_price_usd, 'USD')}</span>
                <span>Total due: <strong>{formatMoney(quote.total_usd, 'USD')}</strong></span>
              </div>
            ) : null}
            <Button variant="primary" onClick={() => void buyCredits()} disabled={!quoteMatches || busy || loading || Boolean(billingError)}>
              {busy ? 'Opening secure checkout…' : quoteMatches && quote ? `Continue · ${formatMoney(quote.total_usd, 'USD')}` : 'Review a quote to continue'}
            </Button>
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>Available plans</CardTitle>
        {loading ? <p role="status">Loading plan options…</p> : plans.length > 0 ? (
          <div className="billing-plan-list">
            {plans.map((plan) => (
              <article key={plan.id} className="billing-plan-row">
                <div>
                  <h3>{plan.display}</h3>
                  <p className="muted">{formatCredits(plan.ai_credits)}</p>
                </div>
                <p>{formatPlanPrice(plan.price_monthly, 'month')} · {formatPlanPrice(plan.price_annual * 12, 'year')}</p>
              </article>
            ))}
          </div>
        ) : <p className="muted">Plan options are unavailable. Retry billing data to check again.</p>}
      </Card>

      <Card>
        <CardTitle>Invoices</CardTitle>
        {invoiceError ? (
          <div role="alert"><p>{invoiceError}</p><Button onClick={retry}>Retry billing information</Button></div>
        ) : loading ? <p role="status">Loading invoices…</p> : !invoiceAvailable ? <p className="muted">Invoice history is unavailable.</p> : invoices.length === 0 ? (
          <p className="muted" role="status">No invoices are available for this account yet.</p>
        ) : (
          <TableWrap>
            <table>
              <caption className="sr-only">Invoice history</caption>
              <thead><tr><th scope="col">Invoice</th><th scope="col">Date</th><th scope="col">Amount</th><th scope="col">Status</th></tr></thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <th scope="row">{`#${invoice.id}`}</th>
                    <td>{formatDate(invoice.created_at)}</td>
                    <td>{formatMoney(invoice.amount, invoice.currency)}</td>
                    <td><Badge tone={invoice.status.toLowerCase() === 'paid' ? 'success' : 'neutral'}>{invoice.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>
    </Page>
  );
}
