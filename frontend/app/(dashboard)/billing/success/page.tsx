'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button, Card, Page, PageHeader } from '@/app/(dashboard)/_ui/kit';
import { apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';

type VerificationState = 'loading' | 'success' | 'pending' | 'error';

export default function BillingSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [state, setState] = useState<VerificationState>('loading');
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    async function verify() {
      if (!sessionId) {
        setState('error');
        setMessage('No checkout session was provided. Open Billing to review your account status.');
        return;
      }
      try {
        const result = await apiSend<{ payment_status: string }>(
          '/billing/stripe/session-status',
          'POST',
          { session_id: sessionId },
          resolveSessionTenant()
        );
        if (!active) return;
        if (result.payment_status === 'paid' || result.payment_status === 'no_payment_required') {
          setState('success');
          setMessage('Payment is verified. Subscription access is finalized by the billing service; check Billing if the plan does not appear shortly.');
        } else {
          setState('pending');
          setMessage('Stripe has not confirmed this payment yet. You do not need to start another checkout while this session is being resolved.');
        }
      } catch {
        if (!active) return;
        setState('error');
        setMessage('We could not verify this checkout session. No account changes were confirmed. You can safely check again or review Billing.');
      }
    }
    void verify();
    return () => {
      active = false;
    };
  }, [attempt, sessionId]);

  const loading = state === 'loading';
  const heading = state === 'success'
    ? 'Payment verified'
    : state === 'pending'
      ? 'Payment confirmation is pending'
      : state === 'error'
        ? 'We could not confirm this checkout'
        : 'Checking your payment';

  return (
    <Page>
      <PageHeader title={heading} subtitle="Checkout status for your current account." />
      <Card>
        <div aria-live={state === 'error' ? 'assertive' : 'polite'} role={state === 'error' ? 'alert' : 'status'}>
          {loading ? <p>Verifying the checkout session…</p> : <p>{message}</p>}
        </div>
        <div className="billing-result-actions">
          {(state === 'pending' || state === 'error') ? (
            <Button variant="primary" onClick={() => { setState('loading'); setAttempt((value) => value + 1); }} disabled={loading}>
              Check status again
            </Button>
          ) : null}
          <Link href="/billing">Open Billing</Link>
          {state === 'success' ? <Link href="/dashboard">Go to dashboard</Link> : null}
        </div>
      </Card>
    </Page>
  );
}
