'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';

export default function BillingSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    async function activate() {
      if (!sessionId) {
        setStatus('error');
        setMessage('No session found. Please return to pricing and try again.');
        return;
      }
      try {
        // Entitlements are granted only by the signed Stripe webhook. This
        // endpoint verifies that the returned Session belongs to this tenant.
        const result = await apiSend<{ payment_status: string }>(
          '/billing/stripe/session-status',
          'POST',
          { session_id: sessionId },
          resolveSessionTenant()
        );
        if (result.payment_status === 'paid' || result.payment_status === 'no_payment_required') {
          setStatus('success');
          setMessage('Payment received. Stripe is finalizing your account now.');
        } else {
          setStatus('error');
          setMessage('Stripe has not confirmed payment yet. Please check Billing again shortly.');
        }
      } catch {
        setStatus('error');
        setMessage('We could not verify this Checkout Session. No account changes were made.');
      }
    }
    void activate();
  }, [sessionId]);

  return (
    <main style={{ textAlign: 'center', padding: '80px 24px' }}>
      {status === 'loading' && (
        <>
          <h1>Activating your plan…</h1>
          <p>Please wait while we set up your subscription.</p>
        </>
      )}
      {status === 'success' && (
        <>
          <h1 style={{ color: '#26d78e' }}>You&apos;re all set! 🎉</h1>
          <p>{message || 'Your subscription is now active. Welcome aboard!'}</p>
          <a
            href="/dashboard"
            style={{
              display: 'inline-block',
              marginTop: 24,
              padding: '12px 32px',
              background: '#1bc7ff',
              borderRadius: 8,
              color: '#000',
              fontWeight: 700,
              textDecoration: 'none',
            }}
          >
            Go to Dashboard
          </a>
        </>
      )}
      {status === 'error' && (
        <>
          <h1 style={{ color: '#f87171' }}>Something went wrong</h1>
          <p>{message}</p>
          <a
            href="/pricing"
            style={{
              display: 'inline-block',
              marginTop: 24,
              padding: '12px 32px',
              background: '#374151',
              borderRadius: 8,
              color: '#fff',
              textDecoration: 'none',
            }}
          >
            Back to Pricing
          </a>
        </>
      )}
    </main>
  );
}
